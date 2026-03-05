import logging
logger = logging.getLogger("MAIN")

# Ora importa il resto
try:
    logger.info("Importazione moduli PySide6...")
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QBrush, QColor, QFont, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QColorDialog,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSplitter,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    logger.info("Importazione moduli applicazione...")
    import os
    import queue
    import subprocess
    import sys
    import threading

    import app_updater
    import config_manager
    import license_updater
    import license_validator
    from core import pdf_processor
    import version

    logger.info("Importazione PyMuPDF...")
    import json
    from datetime import datetime
    from typing import Any, Dict, List, Optional

    from core import notification_manager
    from gui.dialogs.unknown_review import UnknownFilesReviewDialog
    from gui.dialogs.rule_editor import RuleEditorDialog
    from gui.tabs.dashboard_tab import DashboardTab
    from gui.tabs.processing_tab import ProcessingTab
    from gui.tabs.config_tab import ConfigTab
    from gui.tabs.help_tab import HelpTab
    
    # Moduli estratti
    from gui.theme import COLORS, FONTS, GLOBAL_QSS
    from gui.widgets.drop_frame import DropFrame
    from gui.ui_factory import UIFactory
    from shared.constants import APP_DATA_DIR, SESSION_FILE, SIGNAL_FILE
    
    # Core Managers (SRP)
    from core.session_manager import SessionManager
    from core.processing_worker import PdfProcessingWorker
    from core.rule_service import RuleService
    from core.tesseract_manager import TesseractManager
    from core.app_controller import AppController

    logger.info("Tutti i moduli importati con successo")
except Exception as e:
    logger.critical(f"Errore durante l'importazione dei moduli: {e}", exc_info=True)


class MainApp(QMainWindow):
    def __init__(self, auto_file_path: Optional[str] = None) -> None:
        super().__init__()
        logger.info("Inizializzazione MainApp...")
        self.setWindowTitle(f"Intelleo PDF Splitter v{version.__version__}")
        self.setStyleSheet(GLOBAL_QSS)
        self.setup_icon()

        self.config: Dict[str, Any] = {}
        self.pdf_files: List[str] = []
        self.log_queue: queue.Queue = queue.Queue()
        self.processing_start_time: Optional[datetime] = None
        self.files_processed_count: int = 0
        self.pages_processed_count: int = 0
        self._target_progress: float = 0.0
        self._current_progress: float = 0.0
        self._spinner_frames: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx: int = 0
        self._is_processing: bool = False
        self._pending_completion_data: Optional[Dict[str, Any]] = None

        # Widget UI (Inizializzati dalle Tab)
        self.dashboard: Any = None
        self.processing: Any = None
        self.config_panel: Any = None
        self.help_panel: Any = None
        self.license_status_label: QLabel
        self.license_fields: Dict[str, QLabel] = {}
        self.files_count_label: QLabel
        self.pages_count_label: QLabel
        self.rules_count_label: QLabel
        self.recent_log: QTextEdit
        self.log_area: QTextEdit
        self.odc_entry: QLineEdit
        self.pdf_path_label: QLabel
        self.progress_label: QLabel
        self.eta_label: QLabel
        self.progress_bar: QProgressBar
        self.spinner_label: QLabel
        self.rules_tree: QTreeWidget
        self.keywords_text: QTextEdit
        self.roi_details_label: QLabel
        self.tesseract_path_entry: QLineEdit
        self.restore_btn: QPushButton

        # Controller e Notifiche
        self.controller = AppController()
        self.notifier: Optional[Any] = None
        try:
            from core import notification_manager
            self.notifier = notification_manager.NotificationManager(self)
        except Exception as e:
            logger.error(f"Errore inizializzazione notifiche: {e}")

        self._connect_controller_signals()

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
        
        # —————— Tab Initialization ——————
        self.dashboard = DashboardTab(self.dashboard_tab, self)
        self.processing = ProcessingTab(self.processing_tab, self)
        self.config_panel = ConfigTab(self.config_tab, self)
        self.help_panel = HelpTab(self.help_tab, self)
        
        self.notebook.addTab(self.dashboard_tab, "Dashboard")
        self.notebook.addTab(self.processing_tab, "Elaborazione")
        self.notebook.addTab(self.config_tab, "Configurazione")
        self.notebook.addTab(self.help_tab, "Guida")
        
        # —————— Final Initialization ——————
        self.load_settings()
        self._display_license_info()
        self._populate_rules_tree()
        self.update_last_access()

        # Timers (Solo quelli UI-only)
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
        QTimer.singleShot(3000, lambda: app_updater.check_for_updates(silent=True, on_confirm=self._auto_save_settings))

        if auto_file_path and os.path.exists(auto_file_path):
            QTimer.singleShot(500, lambda: self._handle_cli_start(auto_file_path))
        logger.info("MainApp inizializzata con successo")

    def _connect_controller_signals(self) -> None:
        """Collega i segnali del controller agli slot della UI."""
        self.controller.log_received.connect(self._add_log_message)
        self.controller.progress_updated.connect(self._on_progress_update)
        self.controller.license_status_updated.connect(self._on_license_updated)
        self.controller.processing_state_changed.connect(self._on_processing_state_changed)
        self.controller.rules_updated.connect(self._on_rules_updated)
        self.controller.session_status_changed.connect(self._update_restore_button_state)
        self.controller.unknown_files_found.connect(self._show_unknown_dialog)

    def _on_rules_updated(self) -> None:
        rs = self.controller.rule_service
        if not rs:
            return
        self._populate_rules_tree()
        if hasattr(self, "rules_count_label"):
            self.rules_count_label.setText(str(len(rs.get_rules())))

    def _on_processing_state_changed(self, is_processing: bool) -> None:
        self._is_processing = is_processing
        # UI updates if needed
        if not is_processing:
            self._finalize_processing()

    def _on_license_updated(self, info: Dict[str, Any]) -> None:
        if info.get("is_valid"):
            self.license_status_label.setText("✓ SISTEMA ATTIVO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['success']}; border: none;")
        else:
            self.license_status_label.setText("⚠ NON LICENZIATO")
            self.license_status_label.setStyleSheet(f"color: {COLORS['warning']}; border: none;")
        
        self.license_fields["cliente"].setText(info.get("cliente", "---"))
        self.license_fields["scadenza"].setText(info.get("scadenza", "---"))
        self.license_fields["hwid"].setText(info.get("hwid", "---"))
        self.license_fields["last_access"].setText(info.get("last_access", "---"))

    def _on_progress_update(self, value: float, text: str, eta_seconds: Optional[int]) -> None:
        self._target_progress = value
        self.progress_label.setText(text)
        if eta_seconds is not None:
             m, s = divmod(int(eta_seconds), 60)
             self.eta_label.setText(f"Tempo stimato: {m}m {s}s" if m > 0 else f"Tempo stimato: {s}s")
             self.eta_label.setStyleSheet(f"color: {COLORS['accent']};")
        else:
             self.eta_label.setText("")

    def setup_icon(self) -> None:
        """Configura l'icona della finestra."""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            logger.warning(f"Impossibile caricare icona: {e}")

    # ======== DASHBOARD ========
    def _update_clock(self) -> None:
        """Aggiorna l'orologio della dashboard."""
        if hasattr(self, "dashboard"):
            self.dashboard.clock_label.setText(datetime.now().strftime("%d %b %Y | %H:%M:%S"))

    def _quick_select_pdf(self) -> None:
        """Passa all'elaborazione e apre il selettore file."""
        self.notebook.setCurrentWidget(self.processing_tab)
        QTimer.singleShot(100, self._select_pdf)

    # ======== COMMON UI HELPERS (STUBS) ========
    def _on_help_topic_select(self, current: QListWidget, previous: Optional[QListWidget]=None) -> None:
        """Stub mantenuto per compatibilità durante la transizione."""
        pass

    # ======== BUSINESS LOGIC ========
    def _display_license_info(self) -> None:
        """Delega il controllo licenza al controller."""
        self.controller.check_license()

    def _add_log_message(self, message: str, level: str = "INFO") -> None:
        """Aggiunge un messaggio al terminale e al log di elaborazione."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "ERROR": COLORS["danger"],
            "WARNING": "#E67E22",
            "SUCCESS": COLORS["success"],
            "PROGRESS": COLORS["accent"],
            "HEADER": COLORS["accent"],
        }
        prefix_map = {"ERROR": "[X] ", "WARNING": "[!] ", "SUCCESS": "[OK] ", "HEADER": "=== "}
        prefix = prefix_map.get(level, "")
        color = color_map.get(level, COLORS["text_primary"])
        self.log_area.append(f'<span style="color:{color}">[{timestamp}] {prefix}{message}</span>')
        if level in ["SUCCESS", "ERROR"] and self.notifier:
            if any(kw in message for kw in ["File completato", "ELABORAZIONE COMPLETATA", "Errore"]):
                self.notifier.notify(level, message, level)
        if level in ["SUCCESS", "ERROR", "WARNING"]:
            self.recent_log.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')

    def _add_recent_log(self, message: str, level: str = "INFO") -> None:
        """Metodo legacy rimosso (ora integrato in _add_log_message)."""
        pass

    def _process_log_queue(self) -> None:
        """Metodo rimosso: log gestiti da AppController segnali."""
        pass

    def _smooth_progress_tick(self) -> None:
        """Aggiorna la barra di progresso con un'animazione fluida."""
        if abs(self._current_progress - self._target_progress) > 0.05:
            step = (self._target_progress - self._current_progress) * 0.2
            self._current_progress += step
            self.progress_bar.setValue(int(self._current_progress * 10))
        elif self._current_progress != self._target_progress:
            self._current_progress = self._target_progress
            self.progress_bar.setValue(int(self._current_progress * 10))
            if self._current_progress >= 99.9 and self._pending_completion_data:
                self._finalize_processing()

    def _finalize_processing(self) -> None:
        """Completa le operazioni post-elaborazione."""
        if not self._pending_completion_data:
            return
        data = self._pending_completion_data
        self._pending_completion_data = None
        if data.get("action") == "show_unknown_dialog" and data.get("files"):
            self._show_unknown_dialog(data["files"], data.get("odc", ""))
        
        elapsed = datetime.now() - self.processing_start_time if self.processing_start_time else None
        elapsed_str = str(elapsed).split(".")[0] if elapsed else "N/A"
        self._add_log_message("-" * 60, "INFO")
        self._add_log_message(f"ELABORAZIONE COMPLETATA IN {elapsed_str}", "HEADER")
        self._is_processing = False

    def _spinner_tick(self) -> None:
        """Aggiorna lo spinner di caricamento."""
        if self._is_processing:
            self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
            self.spinner_label.setText(self._spinner_frames[self._spinner_idx])
        else:
            self.spinner_label.setText("")

    def _check_for_updates(self) -> None:
        """Controlla segnali esterni tramite il controller."""
        if self.controller.check_roi_signal():
            self._add_log_message("Configurazione sincronizzata", "SUCCESS")

    def update_last_access(self) -> None:
        """Aggiorna il timestamp dell'ultimo accesso nel file di configurazione."""
        try:
            config = config_manager.load_config()
            config["last_access"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            config_manager.save_config(config)
        except Exception as e:
            logger.error(f"Impossibile aggiornare l'ultimo accesso: {e}")

    def _on_drop(self, files: List[str]) -> None:
        """Gestisce il drag-and-drop di file sulla GUI."""
        if files:
            self.pdf_files = files
            if len(self.pdf_files) == 1:
                self.pdf_path_label.setText(os.path.basename(self.pdf_files[0]))
            else:
                self.pdf_path_label.setText(f"{len(self.pdf_files)} file selezionati")
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()

    def _handle_cli_start(self, path: str) -> None:
        """Inizializza l'elaborazione se un file viene passato come argomento CLI."""
        found_pdfs: List[str] = []
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            found_pdfs.append(path)
        elif os.path.isdir(path):
            for root_dir, _, files in os.walk(path):
                for name in files:
                    if name.lower().endswith(".pdf"):
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

    def _select_pdf(self) -> None:
        """Apre il selettore di file PDF."""
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona file PDF", "", "PDF Files (*.pdf)")
        if paths:
            self.pdf_files = list(paths)
            self.pdf_path_label.setText(
                f"{len(self.pdf_files)} file selezionati"
                if len(self.pdf_files) > 1
                else os.path.basename(self.pdf_files[0])
            )
            self._start_processing()

    def _select_folder(self) -> None:
        """Apre il selettore di cartelle per trovare file PDF."""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella")
        if not folder:
            return
        found = [os.path.join(r, f) for r, d, fs in os.walk(folder) for f in fs if f.lower().endswith(".pdf")]
        if found:
            self.pdf_files = found
            self.pdf_path_label.setText(f"{len(found)} file trovati")
            self.notebook.setCurrentWidget(self.processing_tab)
            self._start_processing()
        else:
            QMessageBox.information(self, "Info", "Nessun file PDF trovato.")

    def _update_restore_button_state(self) -> None:
        """Aggiorna lo stato del pulsante di ripristino sessione."""
        self.restore_btn.setEnabled(SessionManager.has_session())

    def _check_for_restore(self) -> None:
        """Verifica all'avvio se esiste una sessione da ripristinare."""
        self._update_restore_button_state()
        if SessionManager.has_session():
            reply = QMessageBox.question(
                self,
                "Ripristino Sessione",
                "Trovata una sessione precedente non completata.\nVuoi ripristinare i file da revisionare?",
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._restore_session()

    def _clear_session(self) -> None:
        """Delega cancellazione sessione."""
        self.controller.clear_session()

    def _restore_session(self) -> None:
        """Ripristina sessione tramite controller."""
        data = self.controller.restore_session()
        if data:
            self._show_unknown_dialog(data[0], data[1])
        else:
            self._add_log_message("Nessuna sessione da ripristinare", "WARNING")

    def _start_processing(self) -> None:
        """Avvia elaborazione tramite controller."""
        odc = self.odc_entry.text().strip()
        if not odc or not self.pdf_files:
            QMessageBox.warning(self, "Errore", "Verificare ODC e file selezionati.")
            return
            
        self.log_area.clear()
        self.processing_start_time = datetime.now()
        self.controller.start_processing(self.pdf_files, odc)

    def _show_unknown_dialog(self, files: List[Any], odc: str) -> None:
        """Visualizza il dialog di revisione per i file non classificati."""
        if not files:
            return

        def on_close() -> None:
            self._add_log_message("Revisione file sconosciuti completata", "SUCCESS")
            QTimer.singleShot(100, self._update_restore_button_state)

        def on_dialog_closed() -> None:
            QTimer.singleShot(100, self._update_restore_button_state)

        dlg = UnknownFilesReviewDialog(self, files, on_finish=on_close, odc=odc, on_close_callback=on_dialog_closed)
        dlg.exec()

    def load_settings(self) -> None:
        """Delega caricamento al controller."""
        self.controller.load_settings()
        if hasattr(self, "tesseract_path_entry"):
            self.tesseract_path_entry.setText(self.controller.config.get("tesseract_path", ""))
        self._populate_rules_tree()

    def _auto_save_settings(self) -> None:
        """Delega salvataggio al controller."""
        self.controller.save_settings()

    def _populate_rules_tree(self) -> None:
        """Popola l'albero delle regole nella UI."""
        rs = self.controller.rule_service
        if not hasattr(self, "rules_tree") or not rs: 
            return
        self.keywords_text.clear()
        self.roi_details_label.setText("")
        self.rules_tree.clear()
        
        for rule in rs.get_rules():
            # Assicura tipi corretti per la view
            color = str(rule.get("color", "#FFFFFF"))
            category = str(rule.get("category_name", "N/A"))
            suffix = str(rule.get("filename_suffix", category))
            
            item = QTreeWidgetItem([color, category, suffix])
            item.setBackground(0, QBrush(QColor(color)))
            
            # Contrasto testo
            h = color.lstrip("#")
            try:
                rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
                brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                item.setForeground(0, QBrush(QColor("black" if brightness > 128 else "white")))
            except Exception:
                pass
            self.rules_tree.addTopLevelItem(item)

    def _update_rule_details_panel(self) -> None:
        """Aggiorna il pannello laterale con i dettagli della regola selezionata."""
        if not self.controller.rule_service:
            return
        items = self.rules_tree.selectedItems()
        if not items:
            self.keywords_text.clear()
            self.roi_details_label.setText("")
            return
            
        category_name = items[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category_name)
        
        if rule:
            self.keywords_text.setPlainText(", ".join(rule.get("keywords", [])))
            self.roi_details_label.setText(f"{len(rule.get('rois', []))} aree ROI definite")

    def _on_tesseract_path_change(self) -> None:
        """Salva il nuovo percorso Tesseract se valido."""
        path = self.tesseract_path_entry.text()
        self.controller.config["tesseract_path"] = path
        self._auto_save_settings()
        
        from core.tesseract_manager import TesseractManager
        if path and not TesseractManager.is_valid(path):
             self._add_log_message("Percorso Tesseract indicato potrebbe non essere valido", "WARNING")

    def _browse_tesseract(self) -> None:
        """Apre il selettore file per l'eseguibile Tesseract."""
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Tesseract", "", "Executable (*.exe)")
        if path:
            self.tesseract_path_entry.setText(path)

    def _auto_detect_tesseract(self) -> None:
        """Utilizza TesseractManager per rilevare automaticamente l'eseguibile."""
        path = TesseractManager.auto_detect()
        if path:
            self.tesseract_path_entry.setText(path)
            QMessageBox.information(self, "Trovato", f"Tesseract trovato:\n{path}")
        else:
            QMessageBox.warning(self, "Non Trovato", "Tesseract non trovato automaticamente.\nIndicalo manualmente.")

    def _add_rule(self) -> None:
        """Apre l'editor per aggiungere una nuova regola."""
        self._show_rule_editor()

    def _modify_rule(self) -> None:
        """Apre l'editor per modificare la regola selezionata."""
        if not self.controller.rule_service:
            return
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da modificare.")
            return
            
        category_name = items[0].text(1)
        rule = self.controller.rule_service.get_rule_by_category(category_name)
        if rule:
            self._show_rule_editor(rule)

    def _remove_rule(self) -> None:
        """Rimuove la regola selezionata."""
        items = self.rules_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "Selezione", "Selezionare una regola da rimuovere.")
            return
            
        cat = items[0].text(1)
        reply = QMessageBox.question(self, "Conferma", f"Rimuovere la regola '{cat}'?")
        
        rs = self.controller.rule_service
        if reply == QMessageBox.StandardButton.Yes and rs:
            if rs.remove_rule(cat):
                self._populate_rules_tree()
                self._auto_save_settings()
                self.rules_count_label.setText(str(len(rs.get_rules())))

    def _show_rule_editor(self, rule: Optional[Dict[str, Any]] = None) -> None:
        """Apre l'editor delle regole delegando al controller se disponibile."""
        if not self.controller.rule_service:
            return
        dlg = RuleEditorDialog(self, self.controller.rule_service, rule)
        if dlg.exec():
            self.controller.rule_service.save()
            self._populate_rules_tree()
            self.rules_count_label.setText(str(len(self.controller.rule_service.get_rules())))

    def _launch_roi_utility(self) -> None:
        """Avvia l'utility esterna per la definizione delle ROI."""
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable, "--utility"])
            else:
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roi_utility.py")
                subprocess.Popen([sys.executable, script_path])
            self._add_log_message("Utility ROI avviata", "SUCCESS")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare l'utility ROI:\n{e}")

