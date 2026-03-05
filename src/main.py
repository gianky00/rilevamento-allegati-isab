"""
Intelleo PDF Splitter - Applicazione principale (PySide6)
Gestisce la divisione di file PDF basata su regole OCR.
"""
# CRITICO: Inizializzare il logging PRIMA di tutto il resto
import app_logger
LOG_PATH = app_logger.initialize()

import logging
logger = logging.getLogger('MAIN')

# Ora importa il resto
try:
    logger.info("Importazione moduli PySide6...")
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QFrame, QTabWidget, QLineEdit, QTextEdit,
        QProgressBar, QTreeWidget, QTreeWidgetItem, QHeaderView,
        QListWidget, QListWidgetItem, QSplitter, QGroupBox,
        QFileDialog, QMessageBox, QDialog, QInputDialog, QColorDialog,
        QGraphicsView, QGraphicsScene, QCheckBox, QComboBox,
        QSizePolicy, QAbstractItemView
    )
    from PySide6.QtCore import Qt, QTimer, QUrl, QMimeData, QThread, Signal, QSize
    from PySide6.QtGui import (
        QFont, QColor, QIcon, QPixmap, QImage, QBrush, QPen,
        QClipboard, QDragEnterEvent, QDropEvent, QCursor, QShortcut, QKeySequence
    )
    logger.info("Importazione moduli applicazione...")
    import config_manager
    import pdf_processor
    import subprocess
    import os
    import sys
    import threading
    import queue
    import license_validator
    import license_updater
    import app_updater
    import version
    logger.info("Importazione PyMuPDF...")
    import pymupdf as fitz
    import shutil
    from datetime import datetime
    import json
    import notification_manager
    logger.info("Tutti i moduli importati con successo")
except Exception as e:
    logger.critical(f"Errore durante l'importazione dei moduli: {e}", exc_info=True)
    pass

# Segnale per comunicazione tra utility ROI e app principale
SIGNAL_FILE = ".update_signal"

# Costanti per la gestione della sessione
APP_DATA_DIR = config_manager.CONFIG_DIR
SESSION_FILE = os.path.join(APP_DATA_DIR, "session.json")

# ============================================================================
# COSTANTI STILE - TEMA CHIARO PROFESSIONALE (MODERN UI)
# ============================================================================
COLORS = {
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#F8F9FA',
    'bg_tertiary': '#E9ECEF',
    'accent': '#2563EB',
    'accent_hover': '#1D4ED8',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'text_primary': '#111827',
    'text_secondary': '#4B5563',
    'text_muted': '#9CA3AF',
    'border': '#E5E7EB',
    'card_shadow': '#9CA3AF',
}

FONTS = {
    'heading': QFont('Segoe UI', 16, QFont.Weight.Bold),
    'subheading': QFont('Segoe UI', 12, QFont.Weight.Bold),
    'body': QFont('Segoe UI', 10),
    'body_bold': QFont('Segoe UI', 10, QFont.Weight.Bold),
    'small': QFont('Segoe UI', 9),
    'mono': QFont('Consolas', 10),
    'mono_bold': QFont('Consolas', 10, QFont.Weight.Bold),
}

# ============================================================================
# GLOBAL STYLESHEET
# ============================================================================
GLOBAL_QSS = f"""
QMainWindow, QDialog {{ background-color: {COLORS['bg_primary']}; }}
QTabWidget::pane {{ background-color: {COLORS['bg_primary']}; border: none; }}
QTabBar::tab {{
    font: bold 10pt "Segoe UI"; padding: 10px 20px;
    background-color: {COLORS['bg_secondary']}; color: {COLORS['text_primary']};
    border: none; margin-right: 2px;
}}
QTabBar::tab:selected {{ background-color: {COLORS['accent']}; color: white; }}
QPushButton {{
    font: 10pt "Segoe UI"; padding: 8px 15px;
    border: 1px solid {COLORS['border']}; border-radius: 4px;
    background-color: {COLORS['bg_secondary']}; color: {COLORS['text_primary']};
}}
QPushButton:hover {{ background-color: {COLORS['accent']}; color: white; border-color: {COLORS['accent']}; }}
QLineEdit, QComboBox {{
    font: 10pt "Segoe UI"; padding: 8px;
    border: 1px solid {COLORS['border']}; border-radius: 4px;
    background-color: {COLORS['bg_primary']};
}}
QGroupBox {{
    font: bold 11pt "Segoe UI"; border: 1px solid {COLORS['border']};
    border-radius: 4px; margin-top: 10px; padding-top: 15px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
QTreeWidget {{
    font: 10pt "Segoe UI"; background-color: {COLORS['bg_primary']};
    border: 1px solid {COLORS['border']}; alternate-background-color: {COLORS['bg_secondary']};
}}
QTreeWidget::item:selected {{ background-color: {COLORS['accent']}; color: white; }}
QTreeWidget QHeaderView::section {{
    font: bold 10pt "Segoe UI"; background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']}; padding: 5px;
}}
QProgressBar {{
    border: none; border-radius: 4px; text-align: center;
    background-color: {COLORS['bg_tertiary']}; height: 18px;
}}
QProgressBar::chunk {{ background-color: {COLORS['success']}; border-radius: 4px; }}
QListWidget {{
    font: 10pt "Segoe UI"; background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']}; border-radius: 4px;
}}
QListWidget::item:selected {{ background-color: {COLORS['accent']}; color: white; }}
QTextEdit {{
    font: 10pt "Consolas"; background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}
"""


class PreviewGraphicsView(QGraphicsView):
    """Vista grafica per anteprima PDF nel dialog di revisione."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(COLORS['bg_tertiary'])))
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None

    def wheelEvent(self, event):
        self._zoom *= 1.1 if event.angleDelta().y() > 0 else 0.9
        self.resetTransform()
        self.scale(self._zoom, self._zoom)

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            super().mouseReleaseEvent(event)

    def show_pixmap(self, qpixmap):
        self._scene.clear()
        self._scene.addPixmap(qpixmap)
        self._scene.setSceneRect(0, 0, qpixmap.width(), qpixmap.height())


class UnknownFilesReviewDialog(QDialog):
    """Dialog per la revisione manuale (Splitter) dei file sconosciuti."""

    def __init__(self, parent, review_tasks, on_finish=None, odc=None, on_close_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Revisione Manuale - Divisione Allegati")
        self.showMaximized()
        self.review_tasks = review_tasks
        self.on_finish = on_finish
        self.odc = odc
        self.on_close_callback = on_close_callback
        self.task_index = 0
        self.current_doc = None
        self.current_doc_path = None
        self.available_pages = []
        self.preview_page_index = 0

        self._create_widgets()
        self.load_task(0)

    def _create_widgets(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left.setFixedWidth(300)

        self.lbl_file_info = QLabel("Caricamento...")
        self.lbl_file_info.setFont(FONTS['subheading'])
        self.lbl_file_info.setWordWrap(True)
        left_layout.addWidget(self.lbl_file_info)

        QLabel("Seleziona le pagine da unire:", font=FONTS['body_bold']).setParent(left)
        lbl_pages = QLabel("Seleziona le pagine da unire:")
        lbl_pages.setFont(FONTS['body_bold'])
        left_layout.addWidget(lbl_pages)

        self.pages_listbox = QListWidget()
        self.pages_listbox.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pages_listbox.itemSelectionChanged.connect(self._on_page_select)
        left_layout.addWidget(self.pages_listbox, 1)

        action_group = QGroupBox(" Azione ")
        action_layout = QVBoxLayout(action_group)
        btn_rename = QPushButton("RINOMINA (Estrai Pagine)")
        btn_rename.setFont(FONTS['body_bold'])
        btn_rename.setStyleSheet(f"background-color: {COLORS['accent']}; color: white; font-weight: bold;")
        btn_rename.clicked.connect(self.extract_and_rename)
        action_layout.addWidget(btn_rename)
        action_layout.addWidget(QLabel("Crea un nuovo file con le pagine selezionate."))
        left_layout.addWidget(action_group)

        self.btn_skip = QPushButton("Salta File >>")
        self.btn_skip.clicked.connect(self.skip_task)
        left_layout.addWidget(self.btn_skip)

        layout.addWidget(left)

        # Right panel - Preview
        self.preview = PreviewGraphicsView()
        layout.addWidget(self.preview, 1)

    def load_task(self, index):
        if index >= len(self.review_tasks):
            QMessageBox.information(self, "Completato", "Tutti i file sono stati revisionati con successo!")
            if os.path.exists(SESSION_FILE):
                try: os.remove(SESSION_FILE)
                except: pass
            if self.on_finish:
                self.on_finish()
            self.accept()
            return

        self.task_index = index
        self.task = self.review_tasks[index]
        self.current_doc_path = self.task['unknown_path']

        if self.current_doc:
            try: self.current_doc.close()
            except: pass
            self.current_doc = None

        try:
            self.current_doc = fitz.open(self.current_doc_path)
            self.available_pages = list(range(self.current_doc.page_count))
            self.lbl_file_info.setText(f"File {index+1}/{len(self.review_tasks)}\n{os.path.basename(self.current_doc_path)}")
            self._refresh_pages_list()
            if self.available_pages:
                self.pages_listbox.setCurrentRow(0)
                self._on_page_select()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file: {e}")
            self.skip_task()

    def _refresh_pages_list(self):
        self.pages_listbox.clear()
        for real_idx in self.available_pages:
            self.pages_listbox.addItem(f"Pagina {real_idx + 1}")

    def _on_page_select(self):
        items = self.pages_listbox.selectedItems()
        if not items: return
        last_row = self.pages_listbox.row(items[-1])
        if last_row < len(self.available_pages):
            self.preview_page_index = self.available_pages[last_row]
            self._render_preview()

    def _render_preview(self):
        if not self.current_doc: return
        try:
            page = self.current_doc[self.preview_page_index]
            pix = page.get_pixmap(dpi=150)
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            self.preview.show_pixmap(QPixmap.fromImage(qimage))
        except Exception as e:
            logger.error(f"Render error: {e}")

    def extract_and_rename(self):
        selected = self.pages_listbox.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Attenzione", "Seleziona almeno una pagina.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Definisci Nome File")
        dialog.setFixedSize(400, 200)
        dialog.setModal(True)
        dlayout = QVBoxLayout(dialog)
        dlayout.setContentsMargins(20, 20, 20, 20)

        grid = QGridLayout()
        grid.addWidget(QLabel("Codice ODC:"), 0, 0)
        odc_entry = QLineEdit()
        odc_entry.setFocus()
        grid.addWidget(odc_entry, 0, 1)
        grid.addWidget(QLabel("Suffisso:"), 1, 0)
        suffix_entry = QLineEdit()
        grid.addWidget(suffix_entry, 1, 1)
        dlayout.addLayout(grid)

        result = {}
        def on_ok():
            result['odc'] = odc_entry.text().strip()
            result['suffix'] = suffix_entry.text().strip()
            if not result['odc'] or not result['suffix']:
                QMessageBox.warning(dialog, "Dati Mancanti", "Sia ODC che Suffisso sono obbligatori.")
                return
            dialog.accept()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(on_ok)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        dlayout.addLayout(btn_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted or not result.get('odc'):
            return

        selected_indices = [self.pages_listbox.row(item) for item in selected]
        selected_real_indices = [self.available_pages[i] for i in selected_indices]
        new_filename = f"{result['odc']}_{result['suffix']}.pdf"
        dir_path = os.path.dirname(self.current_doc_path)
        output_path = os.path.join(dir_path, new_filename)

        if os.path.exists(output_path):
            reply = QMessageBox.question(self, "Sovrascrivi", "File esistente. Sovrascrivere?")
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                os.remove(output_path)
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile sovrascrivere:\n{e}")
                return

        try:
            new_doc = fitz.open()
            for idx in selected_real_indices:
                new_doc.insert_pdf(self.current_doc, from_page=idx, to_page=idx)
            new_doc.save(output_path)
            new_doc.close()
            self.available_pages = [p for p in self.available_pages if p not in selected_real_indices]
            self._refresh_pages_list()
            if not self.available_pages:
                self.finish_task()
            elif self.pages_listbox.count() > 0:
                self.pages_listbox.setCurrentRow(0)
                self._on_page_select()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore salvataggio:\n{e}")

    def finish_task(self):
        if self.current_doc:
            try: self.current_doc.close()
            except: pass
            self.current_doc = None
        try:
            if os.path.exists(self.current_doc_path):
                os.remove(self.current_doc_path)
        except Exception as e:
            logger.error(f"Impossibile cancellare file temp {self.current_doc_path}: {e}")

        if 0 <= self.task_index < len(self.review_tasks):
            del self.review_tasks[self.task_index]
            if self.review_tasks:
                try:
                    with open(SESSION_FILE, 'w') as f:
                        json.dump({'odc': self.odc, 'tasks': self.review_tasks}, f, indent=4)
                except: pass
            else:
                if os.path.exists(SESSION_FILE):
                    try: os.remove(SESSION_FILE)
                    except: pass
            self.load_task(self.task_index)
        else:
            self.load_task(0)

    def skip_task(self):
        self.load_task(self.task_index + 1)

    def closeEvent(self, event):
        if self.current_doc:
            try: self.current_doc.close()
            except: pass
            self.current_doc = None
        if self.review_tasks:
            try:
                os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
                with open(SESSION_FILE, 'w') as f:
                    json.dump({'odc': self.odc, 'tasks': self.review_tasks}, f, indent=4)
                logger.info(f"Sessione salvata: {len(self.review_tasks)} task rimasti.")
            except Exception as e:
                logger.error(f"Errore salvataggio sessione: {e}")
        if self.on_close_callback:
            try: self.on_close_callback()
            except Exception as e: logger.error(f"Error in on_close_callback: {e}")
        super().closeEvent(event)


class DropFrame(QFrame):
    """Frame che accetta il drag & drop di file PDF."""
    def __init__(self, on_drop_callback, parent=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback
        self.setAcceptDrops(True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border: 2px dashed {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        lbl = QLabel("Trascina file o cartelle qui per avviare l'elaborazione automatica", self)
        lbl.setFont(FONTS['small'])
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(lbl)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""QFrame {{ background-color: {COLORS['accent']}20;
                border: 2px dashed {COLORS['accent']}; border-radius: 8px; }}""")

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""QFrame {{ background-color: {COLORS['bg_tertiary']};
            border: 2px dashed {COLORS['border']}; border-radius: 8px; }}""")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(f"""QFrame {{ background-color: {COLORS['bg_tertiary']};
            border: 2px dashed {COLORS['border']}; border-radius: 8px; }}""")
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                if os.path.isdir(path):
                    for root_dir, _, fnames in os.walk(path):
                        for name in fnames:
                            if name.lower().endswith('.pdf'):
                                files.append(os.path.join(root_dir, name))
                elif path.lower().endswith('.pdf'):
                    files.append(path)
        if files:
            self.on_drop_callback(files)
        event.acceptProposedAction()


class MainApp(QMainWindow):
    def __init__(self, auto_file_path=None):
        super().__init__()
        logger.info("Inizializzazione MainApp...")
        self.setWindowTitle(f"Intelleo PDF Splitter v{version.__version__}")
        self.setStyleSheet(GLOBAL_QSS)
        self.setup_icon()

        self.config, self.pdf_files, self.log_queue = {}, [], queue.Queue()
        self.processing_start_time, self.files_processed_count, self.pages_processed_count = None, 0, 0
        self._target_progress = 0
        self._current_progress = 0
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0
        self._is_processing = False
        self._pending_completion_data = None

        # Notifiche
        try:
            self.notifier = notification_manager.NotificationManager(self)
        except Exception as e:
            self.notifier = None
            logger.error(f"Errore inizializzazione notifiche: {e}")

        logger.info("Configurazione UI...")
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.notebook = QTabWidget()
        main_layout.addWidget(self.notebook)

        self.dashboard_tab = QWidget()
        self.processing_tab = QWidget()
        self.config_tab = QWidget()
        self.help_tab = QWidget()
        self.notebook.addTab(self.dashboard_tab, " Dashboard ")
        self.notebook.addTab(self.processing_tab, " Elaborazione ")
        self.notebook.addTab(self.config_tab, " Configurazione ")
        self.notebook.addTab(self.help_tab, " Guida ")

        self._setup_dashboard_tab()
        self._setup_processing_tab()
        self._setup_config_tab()
        self._setup_help_tab()

        logger.info("Avvio logica applicazione...")
        self.update_last_access()
        self.load_settings()
        self._display_license_info()

        # Timers
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._process_log_queue)
        self._log_timer.start(50)

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._check_for_updates)
        self._update_timer.start(150)

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._smooth_progress_tick)
        self._progress_timer.start(30)

        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._spinner_tick)
        self._spinner_timer.start(100)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        QTimer.singleShot(500, self._check_for_restore)
        QTimer.singleShot(3000, lambda: app_updater.check_for_updates(
            silent=True, on_confirm=self._auto_save_settings))

        if auto_file_path and os.path.exists(auto_file_path):
            QTimer.singleShot(500, lambda: self._handle_cli_start(auto_file_path))
        logger.info("MainApp inizializzata con successo")

    def setup_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            logger.warning(f"Impossibile caricare icona: {e}")

    # ======== DASHBOARD ========
    def _setup_dashboard_tab(self):
        layout = QVBoxLayout(self.dashboard_tab)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Header
        header = QHBoxLayout()
        h_label = QLabel("SISTEMA DI ELABORAZIONE INTELLIGENTE")
        h_label.setFont(FONTS['heading'])
        h_label.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h_label)
        if self.notifier:
            self.notifier.setup_bell_icon(header)
        self.clock_label = QLabel("")
        self.clock_label.setFont(FONTS['mono_bold'])
        self.clock_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header.addWidget(self.clock_label)
        layout.addLayout(header)
        self._update_clock()

        # Stat cards
        cards = QHBoxLayout()
        self._create_stat_card(cards, "STATO LICENZA", "license_status", "Verificando...")
        self._create_stat_card(cards, "DOC ANALIZZATI", "files_count", "0")
        self._create_stat_card(cards, "PAGINE TOTALI", "pages_count", "0")
        self._create_stat_card(cards, "REGOLE ATTIVE", "rules_count", "0")
        layout.addLayout(cards)

        # Middle: License + Actions
        middle = QHBoxLayout()

        # License panel
        license_group = QGroupBox(" PARAMETRI DI AUTENTICAZIONE E SICUREZZA ")
        lic_layout = QGridLayout(license_group)
        self.license_fields = {}
        fields = [("UTENTE REGISTRATO", "cliente", "👤"), ("TERMINE VALIDITÀ", "scadenza", "📅"),
                  ("HARDWARE IDENTIFIER", "hwid", "🆔"), ("ULTIMO ACCESSO RILEVATO", "last_access", "🕒")]
        for i, (label, key, icon) in enumerate(fields):
            row, col = divmod(i, 2)
            card = QFrame()
            card.setStyleSheet(f"""QFrame {{ background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 12px; }}""")
            clayout = QVBoxLayout(card)
            top = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(QFont("Segoe UI Emoji", 11))
            top.addWidget(icon_lbl)
            label_lbl = QLabel(label)
            label_lbl.setFont(FONTS['small'])
            label_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
            top.addWidget(label_lbl)
            top.addStretch()
            clayout.addLayout(top)
            v_lab = QLabel("ATTESA DATI...")
            v_lab.setFont(FONTS['mono_bold'])
            v_lab.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
            clayout.addWidget(v_lab)
            self.license_fields[key] = v_lab
            lic_layout.addWidget(card, row, col)
        middle.addWidget(license_group, 3)

        # Actions
        actions_group = QGroupBox(" COMANDI RAPIDI ")
        act_layout = QVBoxLayout(actions_group)
        btn_new = QPushButton("NUOVA ANALISI")
        btn_new.setFont(FONTS['body_bold'])
        btn_new.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        btn_new.clicked.connect(self._quick_select_pdf)
        act_layout.addWidget(btn_new)
        btn_rules = QPushButton("GESTISCI REGOLE")
        btn_rules.clicked.connect(lambda: self.notebook.setCurrentWidget(self.config_tab))
        act_layout.addWidget(btn_rules)
        btn_roi = QPushButton("UTILITY ROI")
        btn_roi.clicked.connect(self._launch_roi_utility)
        act_layout.addWidget(btn_roi)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        act_layout.addWidget(sep)

        self.restore_btn = QPushButton("RECUPERO SESSIONE")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self._restore_session)
        act_layout.addWidget(self.restore_btn)
        act_layout.addStretch()
        middle.addWidget(actions_group, 1)
        layout.addLayout(middle, 1)

        # Activity log
        log_group = QGroupBox(" TERMINALE ATTIVITÀ ")
        log_layout = QVBoxLayout(log_group)
        self.recent_log = QTextEdit()
        self.recent_log.setReadOnly(True)
        self.recent_log.setFixedHeight(120)
        self.recent_log.setFont(FONTS['mono'])
        log_layout.addWidget(self.recent_log)
        layout.addWidget(log_group)

    def _create_stat_card(self, parent_layout, title, var_name, initial_value):
        card = QFrame()
        card.setStyleSheet(f"""QFrame {{ background-color: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border']}; border-radius: 4px; }}""")
        clayout = QVBoxLayout(card)
        clayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setFont(FONTS['small'])
        t.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clayout.addWidget(t)
        v = QLabel(initial_value)
        v.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clayout.addWidget(v)
        setattr(self, f'{var_name}_label', v)
        parent_layout.addWidget(card)

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%d %b %Y | %H:%M:%S"))

    def _quick_select_pdf(self):
        self.notebook.setCurrentWidget(self.processing_tab)
        QTimer.singleShot(100, self._select_pdf)

    # ======== PROCESSING TAB ========
    def _setup_processing_tab(self):
        layout = QVBoxLayout(self.processing_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        h_lbl = QLabel("Elaborazione PDF")
        h_lbl.setFont(FONTS['heading'])
        h_lbl.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h_lbl)
        self.spinner_label = QLabel("")
        self.spinner_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.spinner_label.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(self.spinner_label)
        header.addStretch()
        layout.addLayout(header)

        # Input
        input_group = QGroupBox(" Input ")
        ilayout = QVBoxLayout(input_group)
        odc_row = QHBoxLayout()
        odc_row.addWidget(QLabel("Codice ODC (default):"))
        self.odc_entry = QLineEdit("5400")
        self.odc_entry.setFixedWidth(200)
        odc_row.addWidget(self.odc_entry)
        odc_row.addStretch()
        ilayout.addLayout(odc_row)

        file_row = QHBoxLayout()
        btn_pdf = QPushButton("Seleziona PDF...")
        btn_pdf.clicked.connect(self._select_pdf)
        file_row.addWidget(btn_pdf)
        btn_folder = QPushButton("Seleziona Cartella...")
        btn_folder.clicked.connect(self._select_folder)
        file_row.addWidget(btn_folder)
        self.pdf_path_label = QLabel("Nessun file selezionato")
        self.pdf_path_label.setFont(FONTS['body'])
        self.pdf_path_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        file_row.addWidget(self.pdf_path_label)
        file_row.addStretch()
        ilayout.addLayout(file_row)

        self.drop_frame = DropFrame(self._on_drop)
        ilayout.addWidget(self.drop_frame)
        layout.addWidget(input_group)

        # Progress
        prog_group = QGroupBox(" Progresso ")
        playout = QVBoxLayout(prog_group)
        info_row = QHBoxLayout()
        self.progress_label = QLabel("Pronto")
        self.progress_label.setFont(FONTS['body_bold'])
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_row.addWidget(self.progress_label)
        self.eta_label = QLabel("--:--")
        self.eta_label.setFont(FONTS['mono_bold'])
        self.eta_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        info_row.addWidget(self.eta_label, 0, Qt.AlignmentFlag.AlignRight)
        playout.addLayout(info_row)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1000)  # Use 1000 for smooth animation
        self.progress_bar.setValue(0)
        playout.addWidget(self.progress_bar)
        layout.addWidget(prog_group)

        # Log
        log_group = QGroupBox(" Log Elaborazione ")
        llayout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(FONTS['mono'])
        llayout.addWidget(self.log_area)
        layout.addWidget(log_group, 1)

    # ======== CONFIG TAB ========
    def _setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        h = QLabel("Configurazione")
        h.setFont(FONTS['heading'])
        h.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(h)

        # Tesseract
        tess_group = QGroupBox(" Tesseract OCR ")
        tess_layout = QHBoxLayout(tess_group)
        tess_layout.addWidget(QLabel("Percorso:"))
        self.tesseract_path_entry = QLineEdit()
        self.tesseract_path_entry.textChanged.connect(self._on_tesseract_path_change)
        tess_layout.addWidget(self.tesseract_path_entry, 1)
        btn_browse = QPushButton("Sfoglia")
        btn_browse.clicked.connect(self._browse_tesseract)
        tess_layout.addWidget(btn_browse)
        btn_detect = QPushButton("Auto-Rileva")
        btn_detect.clicked.connect(self._auto_detect_tesseract)
        tess_layout.addWidget(btn_detect)
        layout.addWidget(tess_group)

        # Rules
        rules_group = QGroupBox(" Regole di Classificazione ")
        rlayout = QHBoxLayout(rules_group)

        # Tree
        self.rules_tree = QTreeWidget()
        self.rules_tree.setHeaderLabels(["Colore", "Categoria", "Suffisso"])
        self.rules_tree.setColumnWidth(0, 80)
        self.rules_tree.setColumnWidth(1, 150)
        self.rules_tree.setAlternatingRowColors(True)
        self.rules_tree.itemSelectionChanged.connect(self._update_rule_details_panel)
        rlayout.addWidget(self.rules_tree, 2)

        # Details
        det_widget = QWidget()
        det_layout = QVBoxLayout(det_widget)
        det_layout.addWidget(QLabel("Keywords:"))
        self.keywords_text = QTextEdit()
        self.keywords_text.setReadOnly(True)
        self.keywords_text.setFixedHeight(100)
        det_layout.addWidget(self.keywords_text)
        det_layout.addWidget(QLabel("Aree ROI:"))
        self.roi_details_label = QLabel("")
        self.roi_details_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        det_layout.addWidget(self.roi_details_label)
        det_layout.addStretch()
        rlayout.addWidget(det_widget, 2)

        # Buttons
        btns = QVBoxLayout()
        btn_add = QPushButton("Aggiungi")
        btn_add.clicked.connect(self._add_rule)
        btns.addWidget(btn_add)
        btn_mod = QPushButton("Modifica")
        btn_mod.clicked.connect(self._modify_rule)
        btns.addWidget(btn_mod)
        btn_rem = QPushButton("Rimuovi")
        btn_rem.clicked.connect(self._remove_rule)
        btns.addWidget(btn_rem)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        btns.addWidget(sep)
        btn_roi = QPushButton("Utility ROI")
        btn_roi.clicked.connect(self._launch_roi_utility)
        btns.addWidget(btn_roi)
        btns.addStretch()
        rlayout.addLayout(btns)
        layout.addWidget(rules_group, 1)

    # ======== HELP TAB ========
    def _setup_help_tab(self):
        layout = QVBoxLayout(self.help_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QHBoxLayout()
        h = QLabel("Guida all'Uso")
        h.setFont(FONTS['heading'])
        h.setStyleSheet(f"color: {COLORS['accent']};")
        header.addWidget(h)
        btn_open = QPushButton("Apri Cartella Dati")
        btn_open.clicked.connect(lambda: os.startfile(APP_DATA_DIR))
        header.addWidget(btn_open)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.help_topics_list = QListWidget()
        self.help_detail_text = QTextEdit()
        self.help_detail_text.setReadOnly(True)
        self.help_detail_text.setFont(FONTS['body'])
        splitter.addWidget(self.help_topics_list)
        splitter.addWidget(self.help_detail_text)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        self.help_data = {
            "🚀 Introduzione": "BENVENUTO IN INTELLEO PDF SPLITTER\n\nIntelleo è uno strumento professionale per l'automazione documentale.\nPermette di dividere massicci volumi di scansioni PDF in singoli documenti, classificandoli automaticamente.\n\n✨ FUNZIONALITÀ CHIAVE\n1. Smart Splitting: Riconoscimento intelligente delle pagine tramite parole chiave.\n2. Supporto ROI: Aree di interesse specifiche per aumentare la precisione.\n3. Analisi Ibrida: Combina estrazione testo nativa con OCR Tesseract.\n4. Revisione Manuale: Interfaccia dedicata per gestire i file non riconosciuti.",
            "⚙️ Configurazione Iniziale": "PRIMA CONFIGURAZIONE\n\n1. Installazione Tesseract OCR\n   Tab 'Configurazione' -> Seleziona il percorso di tesseract.exe.\n   Usa 'Auto-Rileva' per trovarlo automaticamente.\n\n2. Creazione Regole\n   Tab 'Configurazione' -> 'Regole di Classificazione' -> 'Aggiungi'.\n   Imposta Nome Categoria e Parole Chiave.",
            "🎯 Utility ROI": "UTILITY ROI (Region of Interest)\n\nSe la ricerca generica non basta, usa le ROI.\n\n1. Apri l'utility dal pulsante 'Utility ROI'.\n2. Carica un PDF di esempio.\n3. Disegna un rettangolo sull'area di interesse.\n4. Assegna la ROI alla categoria.",
            "📂 Elaborazione": "ELABORAZIONE DOCUMENTI\n\n1. Vai alla scheda Elaborazione.\n2. Trascina i file PDF nell'area tratteggiata.\n3. Verifica il codice ODC.\n4. La barra di progresso mostrerà l'avanzamento.",
            "📝 Revisione Manuale": "REVISIONE FILE SCONOSCIUTI\n\nSe pagine non corrispondono a nessuna regola:\n- Lista a Sinistra: Seleziona le pagine.\n- Anteprima a Destra: Controlla il contenuto.\n- RINOMINA: Crea il file PDF finale.\n- SALTA: Passa al prossimo gruppo.",
        }
        for topic in self.help_data.keys():
            self.help_topics_list.addItem(topic)
        self.help_topics_list.currentItemChanged.connect(self._on_help_topic_select)
        self.help_topics_list.setCurrentRow(0)

    def _on_help_topic_select(self, current, previous=None):
        if current:
            self.help_detail_text.setPlainText(self.help_data.get(current.text(), ""))

    # ======== BUSINESS LOGIC ========
    def _display_license_info(self):
        try:
            payload = license_validator.get_license_info()
            hw_id = license_validator.get_hardware_id()
            config = config_manager.load_config()
            last_access = config.get('last_access', 'N/A')
            if payload:
                self.license_status_label.setText("✓ SISTEMA ATTIVO")
                self.license_status_label.setStyleSheet(f"color: {COLORS['success']}; border: none;")
                self.license_fields['cliente'].setText(payload.get('Cliente', 'N/A').upper())
                self.license_fields['scadenza'].setText(payload.get('Scadenza Licenza', 'N/A'))
            else:
                self.license_status_label.setText("⚠ NON LICENZIATO")
                self.license_status_label.setStyleSheet(f"color: {COLORS['warning']}; border: none;")
                self.license_fields['cliente'].setText("UTENTE NON REGISTRATO")
                self.license_fields['scadenza'].setText("---")
            self.license_fields['hwid'].setText(hw_id)
            self.license_fields['last_access'].setText(last_access)
        except Exception:
            self.license_status_label.setText("✖ ERRORE CRITICO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['danger']}; border: none;")

    def _add_log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {"ERROR": COLORS['danger'], "WARNING": "#E67E22",
                     "SUCCESS": COLORS['success'], "PROGRESS": COLORS['accent'],
                     "HEADER": COLORS['accent']}
        prefix_map = {"ERROR": "[X] ", "WARNING": "[!] ", "SUCCESS": "[OK] ", "HEADER": "=== "}
        prefix = prefix_map.get(level, "")
        color = color_map.get(level, COLORS['text_primary'])
        self.log_area.append(f'<span style="color:{color}">[{timestamp}] {prefix}{message}</span>')
        if level in ["SUCCESS", "ERROR"] and self.notifier:
            if any(kw in message for kw in ["File completato", "ELABORAZIONE COMPLETATA", "Errore"]):
                self.notifier.notify(level, message, level)
        if level in ["SUCCESS", "ERROR", "WARNING"]:
            self.recent_log.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')

    def _add_recent_log(self, message, level="INFO"):
        pass  # Handled inline in _add_log_message

    def _process_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    self._add_log_message(item[0], item[1])
                elif isinstance(item, dict):
                    action = item.get('action')
                    if action == 'show_unknown_dialog':
                        self._pending_completion_data = item
                    elif action == 'update_progress':
                        self._target_progress = item.get('value', 0)
                        self.progress_label.setText(item.get('text', ''))
                        eta_seconds = item.get('eta_seconds')
                        if eta_seconds is not None:
                            if eta_seconds > 60:
                                m, s = divmod(int(eta_seconds), 60)
                                eta_text = f"Tempo stimato: {m}m {s}s"
                            else:
                                eta_text = f"Tempo stimato: {int(eta_seconds)}s"
                            self.eta_label.setText(eta_text)
                            self.eta_label.setStyleSheet(f"color: {COLORS['accent']};")
                        else:
                            self.eta_label.setText("")
                    elif action == 'increment_pages':
                        self.pages_processed_count += item.get('count', 1)
                        self.pages_count_label.setText(str(self.pages_processed_count))
                else:
                    self._add_log_message(str(item))
        except queue.Empty:
            pass

    def _smooth_progress_tick(self):
        if abs(self._current_progress - self._target_progress) > 0.05:
            step = (self._target_progress - self._current_progress) * 0.2
            self._current_progress += step
            self.progress_bar.setValue(int(self._current_progress * 10))
        elif self._current_progress != self._target_progress:
            self._current_progress = self._target_progress
            self.progress_bar.setValue(int(self._current_progress * 10))
            if self._current_progress >= 99.9 and self._pending_completion_data:
                self._finalize_processing()

    def _finalize_processing(self):
        if not self._pending_completion_data: return
        data = self._pending_completion_data
        self._pending_completion_data = None
        if data.get('action') == 'show_unknown_dialog' and data.get('files'):
            self._show_unknown_dialog(data['files'], data.get('odc', ''))
        elapsed = datetime.now() - self.processing_start_time if self.processing_start_time else None
        elapsed_str = str(elapsed).split('.')[0] if elapsed else "N/A"
        self._add_log_message("-" * 60, "INFO")
        self._add_log_message(f"ELABORAZIONE COMPLETATA IN {elapsed_str}", "HEADER")
        self._is_processing = False

    def _spinner_tick(self):
        if self._is_processing:
            self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
            self.spinner_label.setText(self._spinner_frames[self._spinner_idx])
        else:
            self.spinner_label.setText("")

    def _check_for_updates(self):
        if os.path.exists(SIGNAL_FILE):
            try:
                os.remove(SIGNAL_FILE)
                self.load_settings()
                self._add_log_message("Configurazione aggiornata dall'utility ROI", "SUCCESS")
            except OSError as e:
                logger.error(f"Gestione signal file: {e}")

    def update_last_access(self):
        try:
            config = config_manager.load_config()
            config['last_access'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            config_manager.save_config(config)
        except Exception as e:
            logger.error(f"Impossibile aggiornare l'ultimo accesso: {e}")

    def _on_drop(self, files):
        if files:
            self.pdf_files = files
            if len(self.pdf_files) == 1:
                self.pdf_path_label.setText(os.path.basename(self.pdf_files[0]))
            else:
                self.pdf_path_label.setText(f"{len(self.pdf_files)} file selezionati")
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    def _handle_cli_start(self, path):
        found_pdfs = []
        if os.path.isfile(path) and path.lower().endswith('.pdf'):
            found_pdfs.append(path)
        elif os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for name in files:
                    if name.lower().endswith('.pdf'):
                        found_pdfs.append(os.path.join(root_dir, name))
        if not found_pdfs:
            QMessageBox.critical(self, "Errore", "Nessun file PDF trovato.")
            return
        self.pdf_files = found_pdfs
        self.pdf_path_label.setText(f"{len(found_pdfs)} file trovati")
        odc, ok = QInputDialog.getText(self, "Input ODC", "Inserisci il codice ODC:")
        if ok and odc:
            self.odc_entry.setText(odc)
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    def _select_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona file PDF", "", "PDF Files (*.pdf)")
        if paths:
            self.pdf_files = list(paths)
            self.pdf_path_label.setText(
                f"{len(self.pdf_files)} file selezionati" if len(self.pdf_files) > 1
                else os.path.basename(self.pdf_files[0]))
            self._start_processing()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella")
        if not folder: return
        found = [os.path.join(r, f) for r, d, fs in os.walk(folder) for f in fs if f.lower().endswith('.pdf')]
        if found:
            self.pdf_files = found
            self.pdf_path_label.setText(f"{len(found)} file trovati")
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()
        else:
            QMessageBox.information(self, "Info", "Nessun file PDF trovato.")

    def _update_restore_button_state(self):
        self.restore_btn.setEnabled(os.path.exists(SESSION_FILE))

    def _check_for_restore(self):
        self._update_restore_button_state()
        if os.path.exists(SESSION_FILE):
            reply = QMessageBox.question(self, "Ripristino Sessione",
                "Trovata una sessione precedente non completata.\nVuoi ripristinare i file da revisionare?")
            if reply == QMessageBox.StandardButton.Yes:
                self._restore_session()

    def _clear_session(self):
        if os.path.exists(SESSION_FILE):
            try: os.remove(SESSION_FILE)
            except OSError as e: logger.error(f"Errore rimozione session file: {e}")
        self._update_restore_button_state()

    def _restore_session(self):
        if not os.path.exists(SESSION_FILE): return
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            if data:
                tasks, odc = [], "Unknown"
                if isinstance(data, list): tasks = data
                elif isinstance(data, dict): tasks = data.get('tasks', []); odc = data.get('odc', "Unknown")
                if tasks: self._show_unknown_dialog(tasks, odc)
                else: self._clear_session()
            else: self._clear_session()
        except Exception as e:
            logger.error(f"Errore ripristino sessione: {e}")
            QMessageBox.critical(self, "Errore", f"Impossibile ripristinare la sessione:\n{e}")
            self._clear_session()

    def _start_processing(self):
        odc_input = self.odc_entry.text().strip()
        if not odc_input:
            QMessageBox.critical(self, "Errore", "Inserire un codice ODC valido.")
            return
        if not self.pdf_files:
            QMessageBox.critical(self, "Errore", "Seleziona almeno un file PDF.")
            return
        self.log_area.clear()
        self._target_progress = 0
        self._current_progress = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText("Avvio in corso...")
        self.eta_label.setText("Calcolo stima...")
        self._add_log_message("AVVIO ELABORAZIONE", "HEADER")
        self._add_log_message(f"File da elaborare: {len(self.pdf_files)}", "INFO")
        self._add_log_message("-" * 60, "INFO")
        self.processing_start_time = datetime.now()
        self._is_processing = True
        thread = threading.Thread(target=self._processing_worker,
                                  args=(list(self.pdf_files), self.odc_entry.text(), self.config))
        thread.daemon = True
        thread.start()

    def _processing_worker(self, pdf_files, odc, config):
        try:
            unknown_files = []
            total_files = len(pdf_files)
            for i, pdf_path in enumerate(pdf_files):
                def progress_callback(message, level="INFO"):
                    self.log_queue.put((message, level))
                    if "Elaborazione pagina" in message:
                        try:
                            parts = message.split()
                            for p in parts:
                                if "/" in p:
                                    current, total = p.split("/")
                                    page_progress = int(current) / int(total) * 100
                                    file_progress = (i / total_files) * 100
                                    combined = file_progress + (page_progress / total_files)
                                    self.log_queue.put({
                                        'action': 'update_progress', 'value': combined,
                                        'text': f"File {i+1}/{total_files} - Pagina {current}/{total}",
                                        'eta_seconds': None
                                    })
                                    break
                        except: pass

                def advanced_progress_callback(data, level="INFO"):
                    if isinstance(data, dict) and data.get('type') == 'page_progress':
                        current = data.get('current', 0)
                        total = data.get('total', 1)
                        eta = data.get('eta_seconds', 0)
                        phase_pct = data.get('phase_pct', 0)
                        phase = data.get('phase', 'analysis')
                        file_internal_progress = phase_pct if phase_pct > 0 else (current / total) * 100
                        base_pct = (i / total_files) * 100
                        combined = base_pct + (file_internal_progress * (1.0 / total_files))
                        status_text = f"File {i+1}/{total_files}"
                        status_text += " - Salvataggio..." if phase == 'saving' else f" - Analisi {current}/{total}"
                        self.log_queue.put({'action': 'update_progress', 'value': combined,
                                            'text': status_text, 'eta_seconds': eta})
                    elif isinstance(data, dict): self.log_queue.put(data)
                    else: progress_callback(str(data), level)

                self.log_queue.put((f"=== FILE {i+1}/{total_files}: {os.path.basename(pdf_path)} ===", "HEADER"))
                success, message, generated, moved = pdf_processor.process_pdf(
                    pdf_path, odc, config, advanced_progress_callback)
                if not success:
                    self.log_queue.put((f"Errore: {message}", "ERROR"))
                else:
                    self.files_processed_count += 1
                    self.log_queue.put(("File completato con successo", "SUCCESS"))
                    if any(f['category'] == 'sconosciuto' for f in generated):
                        unknown_paths = [f['path'] for f in generated if f['category'] == 'sconosciuto']
                        siblings = [f['path'] for f in generated if f['category'] != 'sconosciuto']
                        for u_path in unknown_paths:
                            unknown_files.append({'unknown_path': u_path, 'source_path': moved, 'siblings': siblings})

            self.log_queue.put({'action': 'update_progress', 'value': 100, 'text': 'Completato!'})
            elapsed = datetime.now() - self.processing_start_time if self.processing_start_time else None
            elapsed_str = str(elapsed).split('.')[0] if elapsed else "N/A"
            self.log_queue.put(("-" * 60, "INFO"))
            self.log_queue.put((f"ELABORAZIONE COMPLETATA in {elapsed_str}", "HEADER"))
            self.log_queue.put((f"File elaborati: {total_files}", "SUCCESS"))
            if unknown_files:
                self.log_queue.put({'action': 'show_unknown_dialog', 'files': unknown_files, 'odc': odc})
            # Update UI from main thread
            QTimer.singleShot(0, lambda: self.files_count_label.setText(str(self.files_processed_count)))
            QTimer.singleShot(0, lambda: self.odc_entry.setText("5400"))
        finally:
            self._is_processing = False

    def _show_unknown_dialog(self, files, odc):
        if not files: return
        def on_close():
            self._add_log_message("Revisione file sconosciuti completata", "SUCCESS")
            QTimer.singleShot(100, self._update_restore_button_state)
        def on_dialog_closed():
            QTimer.singleShot(100, self._update_restore_button_state)
        dlg = UnknownFilesReviewDialog(self, files, on_finish=on_close, odc=odc, on_close_callback=on_dialog_closed)
        dlg.exec()

    def load_settings(self):
        self.config = config_manager.load_config()
        if hasattr(self, 'tesseract_path_entry'):
            self.tesseract_path_entry.blockSignals(True)
            self.tesseract_path_entry.setText(self.config.get("tesseract_path", ""))
            self.tesseract_path_entry.blockSignals(False)
        self._populate_rules_tree()
        rules_count = len(self.config.get("classification_rules", []))
        if hasattr(self, 'rules_count_label'):
            self.rules_count_label.setText(str(rules_count))

    def _auto_save_settings(self):
        try: config_manager.save_config(self.config)
        except Exception as e: logger.error(f"Auto-Save: {e}")

    def _populate_rules_tree(self):
        self.keywords_text.clear()
        self.roi_details_label.setText("")
        self.rules_tree.clear()
        for rule in self.config.get("classification_rules", []):
            color = rule.get("color", "#FFFFFF")
            suffix = rule.get("filename_suffix", rule["category_name"])
            item = QTreeWidgetItem([color, rule["category_name"], suffix])
            item.setBackground(0, QBrush(QColor(color)))
            h = color.lstrip('#')
            try:
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                brightness = (rgb[0]*299+rgb[1]*587+rgb[2]*114)/1000
                item.setForeground(0, QBrush(QColor("black" if brightness > 128 else "white")))
            except: pass
            self.rules_tree.addTopLevelItem(item)

    def _update_rule_details_panel(self):
        items = self.rules_tree.selectedItems()
        if not items:
            self.keywords_text.clear()
            self.roi_details_label.setText("")
            return
        category_name = items[0].text(1)
        rule = next((r for r in self.config.get("classification_rules", [])
                     if r["category_name"] == category_name), None)
        if rule:
            self.keywords_text.setPlainText(", ".join(rule.get("keywords", [])))
            self.roi_details_label.setText(f"{len(rule.get('rois', []))} aree ROI definite")

    def _on_tesseract_path_change(self):
        self.config["tesseract_path"] = self.tesseract_path_entry.text()
        self._auto_save_settings()

    def _browse_tesseract(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Tesseract", "", "Executable (*.exe)")
        if path: self.tesseract_path_entry.setText(path)

    def _auto_detect_tesseract(self):
        search_paths = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Tesseract-OCR", "tesseract.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe")
        ]
        for p in search_paths:
            if p and os.path.exists(p):
                self.tesseract_path_entry.setText(p)
                QMessageBox.information(self, "Trovato", f"Tesseract trovato:\n{p}")
                return
        QMessageBox.warning(self, "Non Trovato", "Tesseract non trovato automaticamente.\nIndicalo manualmente.")

    def _add_rule(self): self._show_rule_editor()
    def _modify_rule(self):
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da modificare.")
            return
        rule = next((r for r in self.config["classification_rules"]
                     if r["category_name"] == items[0].text(1)), None)
        if rule: self._show_rule_editor(rule)

    def _remove_rule(self):
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da rimuovere.")
            return
        cat = items[0].text(1)
        reply = QMessageBox.question(self, "Conferma", f"Rimuovere la regola '{cat}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.config["classification_rules"] = [r for r in self.config["classification_rules"] if r["category_name"] != cat]
            self._populate_rules_tree()
            self._auto_save_settings()
            self.rules_count_label.setText(str(len(self.config.get("classification_rules", []))))

    def _show_rule_editor(self, rule=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifica Regola" if rule else "Nuova Regola")
        dialog.setFixedSize(500, 400)
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        grid = QGridLayout()
        grid.addWidget(QLabel("Nome Categoria:"), 0, 0)
        cat_entry = QLineEdit(rule["category_name"] if rule else "")
        if rule: cat_entry.setReadOnly(True)
        grid.addWidget(cat_entry, 0, 1, 1, 2)

        grid.addWidget(QLabel("Suffisso File:"), 1, 0)
        suffix_entry = QLineEdit(rule.get("filename_suffix", "") if rule else "")
        grid.addWidget(suffix_entry, 1, 1, 1, 2)

        grid.addWidget(QLabel("Keywords:"), 2, 0)
        kw_entry = QLineEdit(", ".join(rule.get("keywords", [])) if rule else "")
        grid.addWidget(kw_entry, 2, 1, 1, 2)
        grid.addWidget(QLabel("(separate da virgola)"), 3, 1)

        grid.addWidget(QLabel("Colore:"), 4, 0)
        chosen_color = [rule.get("color", "#0D6EFD") if rule else "#0D6EFD"]
        color_swatch = QLabel("     ")
        color_swatch.setStyleSheet(f"background-color: {chosen_color[0]}; border: 1px solid black;")
        color_swatch.setFixedSize(60, 25)
        grid.addWidget(color_swatch, 4, 1)
        def choose_color():
            c = QColorDialog.getColor(QColor(chosen_color[0]), dialog, "Scegli Colore")
            if c.isValid():
                chosen_color[0] = c.name()
                color_swatch.setStyleSheet(f"background-color: {c.name()}; border: 1px solid black;")
        btn_color = QPushButton("Scegli")
        btn_color.clicked.connect(choose_color)
        grid.addWidget(btn_color, 4, 2)

        grid.addWidget(QLabel("Aree ROI:"), 5, 0)
        roi_count = len(rule.get("rois", [])) if rule else 0
        grid.addWidget(QLabel(f"{roi_count} aree definite"), 5, 1)
        layout.addLayout(grid)

        def on_save():
            category = cat_entry.text().strip()
            suffix = suffix_entry.text().strip() or category
            keywords = [k.strip() for k in kw_entry.text().split(',') if k.strip()]
            color = chosen_color[0]
            if not category or not keywords:
                QMessageBox.critical(dialog, "Errore", "Nome categoria e almeno una keyword sono obbligatori.")
                return
            new_data = {"category_name": category, "filename_suffix": suffix, "keywords": keywords, "color": color}
            if rule:
                new_data['rotate_roi'] = rule.get('rotate_roi', 0)
                new_data['rois'] = rule.get('rois', [])
                rule.update(new_data)
            else:
                if any(r["category_name"] == category for r in self.config.get("classification_rules", [])):
                    QMessageBox.critical(dialog, "Errore", "Categoria già esistente.")
                    return
                new_data["rois"] = []
                self.config.setdefault("classification_rules", []).append(new_data)
            self._populate_rules_tree()
            self._auto_save_settings()
            self.rules_count_label.setText(str(len(self.config.get("classification_rules", []))))
            dialog.accept()

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Salva"); btn_save.clicked.connect(on_save)
        btn_cancel = QPushButton("Annulla"); btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_save); btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dialog.exec()

    def _launch_roi_utility(self):
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, "--utility"])
            else:
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roi_utility.py')
                subprocess.Popen([sys.executable, script_path])
            self._add_log_message("Utility ROI avviata", "SUCCESS")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare l'utility ROI:\n{e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    # Check for ROI Utility launch flag (used in frozen builds)
    if "--utility" in sys.argv:
        try:
            import roi_utility
            roi_utility.run_utility()
        except Exception as e:
            logger.critical(f"Failed to launch ROI utility: {e}", exc_info=True)
        sys.exit(0)

    logger.info("=" * 68)
    logger.info("           INTELLEO PDF SPLITTER - AVVIO APPLICAZIONE")
    logger.info("=" * 68)
    logger.info(f"  Versione: {version.__version__}")
    logger.info(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("=" * 68)

    # License Update & Check
    logger.info("Verifica licenza in corso...")
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(GLOBAL_QSS)

    try:
        license_updater.run_update()
        logger.info("Aggiornamento licenza completato")
    except Exception as e:
        logger.critical(f"Verifica licenza fallita: {e}", exc_info=True)
        QMessageBox.critical(None, "Errore Licenza", f"Impossibile verificare la licenza:\n{e}")
        sys.exit(1)

    is_valid, msg = license_validator.verify_license()
    if not is_valid:
        logger.error(f"Licenza non valida: {msg}")
        hw_id = license_validator.get_hardware_id()
        err_msg = f"{msg}\n\nHardware ID:\n{hw_id}\n\n(Copiato negli appunti)"
        clipboard = qt_app.clipboard()
        clipboard.setText(hw_id)
        QMessageBox.critical(None, "Licenza Non Valida", err_msg)
        sys.exit(1)

    logger.info("Licenza valida")
    logger.info("Inizializzazione interfaccia grafica...")

    # Pulizia signal file
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)

    # Check CLI args
    cli_path = None
    if len(sys.argv) > 1:
        potential_path = sys.argv[1]
        if os.path.exists(potential_path):
            if os.path.isdir(potential_path) or potential_path.lower().endswith('.pdf'):
                cli_path = potential_path
                logger.info(f"Avvio con file: {potential_path}")

    logger.info("Applicazione pronta")

    window = MainApp(auto_file_path=cli_path)
    window.showMaximized()

    logger.info("Avvio event loop")
    sys.exit(qt_app.exec())
