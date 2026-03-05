"""
Intelleo PDF Splitter - Utility ROI (PySide6)
Gestisce la definizione delle aree ROI per l'OCR.
"""

import contextlib
import math
import os

import pymupdf as fitz
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QImage, QKeySequence, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import config_manager

SIGNAL_FILE = ".update_signal"

# ============================================================================
# COSTANTI STILE - TEMA CHIARO PROFESSIONALE
# ============================================================================
COLORS = {
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F8F9FA",
    "bg_tertiary": "#E9ECEF",
    "accent": "#0D6EFD",
    "accent_hover": "#0B5ED7",
    "success": "#198754",
    "warning": "#FFC107",
    "danger": "#DC3545",
    "text_primary": "#212529",
    "text_secondary": "#6C757D",
    "text_muted": "#ADB5BD",
    "border": "#DEE2E6",
}


class ROIGraphicsView(QGraphicsView):
    """Vista grafica personalizzata con disegno ROI, zoom, e pan."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.scene_ref = QGraphicsScene(self)
        self.setScene(self.scene_ref)
        self.setRenderHints(self.renderHints())
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_tertiary"])))
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # Stato disegno
        self._start_point = None
        self._current_rect = None
        self._panning = False
        self._pan_start = None

    def wheelEvent(self, event):
        """Zoom con rotella (Ctrl) o scroll verticale."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.app.zoom_in()
            else:
                self.app.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Gestisce click per disegno ROI, cancellazione, o pan."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Pan mode
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())

            if self.app.delete_mode:
                self.app.handle_delete_click(scene_pos)
            else:
                # Inizio disegno ROI
                self._start_point = scene_pos
                if self._current_rect:
                    self.scene_ref.removeItem(self._current_rect)
                    self._current_rect = None

                pen = QPen(QColor(COLORS["accent"]), 2, Qt.PenStyle.DashLine)
                self._current_rect = self.scene_ref.addRect(QRectF(scene_pos, scene_pos), pen)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Gestisce trascinamento per disegno ROI o pan."""
        if self._panning and self._pan_start:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        # Aggiorna coordinate nella status bar
        if self.app.pdf_doc:
            factor = 72 / (150 * self.app.zoom_level)
            pdf_x = int(scene_pos.x() * factor)
            pdf_y = int(scene_pos.y() * factor)
            if not self.app.delete_mode:
                self.app.status_bar.setText(f"[DISEGNO] Modalità attiva | Coordinate PDF: ({pdf_x}, {pdf_y})")

        if not self.app.delete_mode and self._current_rect and self._start_point:
            rect = QRectF(self._start_point, scene_pos).normalized()
            self._current_rect.setRect(rect)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Gestisce rilascio mouse per completare la ROI."""
        if self._panning:
            self._panning = False
            self._pan_start = None
            cursor = Qt.CursorShape.ForbiddenCursor if self.app.delete_mode else Qt.CursorShape.CrossCursor
            self.setCursor(QCursor(cursor))
            event.accept()
            return

        if not self.app.delete_mode and self._start_point:
            end_point = self.mapToScene(event.position().toPoint())

            dist = math.hypot(end_point.x() - self._start_point.x(), end_point.y() - self._start_point.y())
            if dist < 10:
                if self._current_rect:
                    self.scene_ref.removeItem(self._current_rect)
                    self._current_rect = None
                self._start_point = None
                return

            # Converti coordinate
            factor = 72 / (150 * self.app.zoom_level)
            x0 = min(self._start_point.x(), end_point.x())
            y0 = min(self._start_point.y(), end_point.y())
            x1 = max(self._start_point.x(), end_point.x())
            y1 = max(self._start_point.y(), end_point.y())
            roi_pdf_coords = [int(c * factor) for c in [x0, y0, x1, y1]]

            self.app.prompt_and_save_roi(roi_pdf_coords)

            if self._current_rect:
                self.scene_ref.removeItem(self._current_rect)
                self._current_rect = None
            self._start_point = None

            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ROIDrawingApp(QMainWindow):
    """Applicazione per la gestione delle aree ROI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Intelleo - Utility Gestione ROI")
        self.resize(1300, 900)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_primary']}; }}")

        # Variabili di stato
        self.pdf_doc = None
        self._pixmap_item = None
        self.current_page_index = 0
        self.config = config_manager.load_config()
        self.delete_mode = False
        self.roi_item_map = {}
        self.zoom_level = 1.0

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        """Crea l'interfaccia utente."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Header ---
        header = QLabel("Utility Gestione ROI")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['accent']};")
        main_layout.addWidget(header)

        # --- Toolbar ---
        toolbar_group = QGroupBox(" Strumenti ")
        toolbar_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        toolbar_layout = QHBoxLayout(toolbar_group)
        toolbar_layout.setSpacing(8)

        # Apri PDF
        btn_open = QPushButton("Apri PDF di Esempio")
        btn_open.setFont(QFont("Segoe UI", 10))
        btn_open.clicked.connect(self.open_pdf)
        toolbar_layout.addWidget(btn_open)

        self._add_separator(toolbar_layout)

        # Navigazione pagine
        self.nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_page_button = QPushButton("<< Pagina Precedente")
        self.prev_page_button.setFont(QFont("Segoe UI", 10))
        self.prev_page_button.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.prev_page_button)

        self.page_label = QLabel("Nessun PDF caricato")
        self.page_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(180)
        nav_layout.addWidget(self.page_label)

        self.next_page_button = QPushButton("Pagina Successiva >>")
        self.next_page_button.setFont(QFont("Segoe UI", 10))
        self.next_page_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_page_button)

        self.nav_widget.setVisible(False)
        toolbar_layout.addWidget(self.nav_widget)

        self._add_separator(toolbar_layout)

        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        toolbar_layout.addWidget(zoom_label)

        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedWidth(35)
        btn_zoom_out.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(btn_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(self.zoom_label)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedWidth(35)
        btn_zoom_in.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(btn_zoom_in)

        btn_zoom_reset = QPushButton("Reset")
        btn_zoom_reset.clicked.connect(self.zoom_reset)
        toolbar_layout.addWidget(btn_zoom_reset)

        self._add_separator(toolbar_layout)

        # Modalità cancellazione
        self.delete_mode_btn = QCheckBox("Modalità Cancellazione ROI")
        self.delete_mode_btn.setFont(QFont("Segoe UI", 10))
        self.delete_mode_btn.toggled.connect(self.toggle_delete_mode)
        toolbar_layout.addWidget(self.delete_mode_btn)

        toolbar_layout.addStretch()

        # Indicatore modalità
        self.mode_indicator = QLabel("[DISEGNO] Modalità attiva")
        self.mode_indicator.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mode_indicator.setStyleSheet(f"color: {COLORS['success']};")
        toolbar_layout.addWidget(self.mode_indicator)

        main_layout.addWidget(toolbar_group)

        # --- Content: Canvas + Sidebar ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Canvas (QGraphicsView)
        canvas_group = QGroupBox(" Area di Lavoro ")
        canvas_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        canvas_layout = QVBoxLayout(canvas_group)
        canvas_layout.setContentsMargins(10, 15, 10, 10)

        self.canvas = ROIGraphicsView(self)
        canvas_layout.addWidget(self.canvas)
        splitter.addWidget(canvas_group)

        # Sidebar
        sidebar_group = QGroupBox(" Regole Attive ")
        sidebar_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sidebar_group.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar_group)

        self.rules_listbox = QListWidget()
        self.rules_listbox.setFont(QFont("Segoe UI", 10))
        self.rules_listbox.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS["accent"]};
                color: white;
            }}
        """)
        sidebar_layout.addWidget(self.rules_listbox)
        self._update_rules_list()

        btn_refresh = QPushButton("Aggiorna Lista")
        btn_refresh.setFont(QFont("Segoe UI", 10))
        btn_refresh.clicked.connect(self._update_rules_list)
        sidebar_layout.addWidget(btn_refresh)

        splitter.addWidget(sidebar_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        main_layout.addWidget(splitter, 1)

        # --- Status Bar ---
        self.status_bar = QLabel("[INFO] Carica un PDF per iniziare a definire le aree ROI")
        self.status_bar.setFont(QFont("Segoe UI", 9))
        self.status_bar.setStyleSheet(f"color: {COLORS['text_secondary']};")
        main_layout.addWidget(self.status_bar)

        # --- Help ---
        help_label = QLabel(
            "[AIUTO] Disegna un rettangolo sul PDF per definire una nuova ROI | "
            "Frecce <- -> per navigare | Ctrl+Rotella per zoom | "
            "Attiva 'Cancellazione' per rimuovere ROI esistenti"
        )
        help_label.setFont(QFont("Segoe UI", 9))
        help_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        main_layout.addWidget(help_label)

    def _add_separator(self, layout):
        """Aggiunge un separatore verticale al layout."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setFixedWidth(20)
        layout.addWidget(sep)

    def _setup_shortcuts(self):
        """Configura scorciatoie tastiera."""
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, self.zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, self.zoom_out)
        QShortcut(QKeySequence(Qt.Key.Key_0), self, self.zoom_reset)

    def _update_rules_list(self):
        """Aggiorna la lista delle regole nella sidebar."""
        self.config = config_manager.load_config()
        self.rules_listbox.clear()

        for rule in self.config.get("classification_rules", []):
            name = rule.get("category_name", "N/A")
            roi_count = len(rule.get("rois", []))
            self.rules_listbox.addItem(f"  {name} ({roi_count} ROI)")

    def toggle_delete_mode(self, checked):
        """Attiva/disattiva la modalità cancellazione."""
        self.delete_mode = checked
        if checked:
            self.canvas.setCursor(QCursor(Qt.CursorShape.ForbiddenCursor))
            self.mode_indicator.setText("[CANCELLA] Modalità attiva")
            self.mode_indicator.setStyleSheet(f"color: {COLORS['danger']};")
            self.status_bar.setText("[!] Modalità Cancellazione: Clicca su una ROI per eliminarla")
        else:
            self.canvas.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            self.mode_indicator.setText("[DISEGNO] Modalità attiva")
            self.mode_indicator.setStyleSheet(f"color: {COLORS['success']};")
            self.status_bar.setText("[OK] Modalità Disegno: Trascina per creare una nuova ROI")

    def zoom_in(self):
        """Aumenta lo zoom."""
        self.zoom_level = min(4.0, self.zoom_level * 1.2)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def zoom_out(self):
        """Diminuisce lo zoom."""
        self.zoom_level = max(0.25, self.zoom_level / 1.2)
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def zoom_reset(self):
        """Resetta lo zoom."""
        self.zoom_level = 1.0
        self.zoom_label.setText("100%")
        if self.pdf_doc:
            self.render_page(self.current_page_index)

    def open_pdf(self):
        """Apre un file PDF."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleziona un PDF di esempio", "", "PDF Files (*.pdf)")

        if not filepath:
            return

        try:
            self.pdf_doc = fitz.open(filepath)

            if self.pdf_doc.page_count > 0:
                self.current_page_index = 0
                self.nav_widget.setVisible(True)
                self.zoom_level = 1.0
                self.zoom_label.setText("100%")
                self.render_page(self.current_page_index)
                self.status_bar.setText(
                    f"[OK] PDF caricato: {os.path.basename(filepath)} ({self.pdf_doc.page_count} pagine)"
                )
            else:
                QMessageBox.warning(self, "Attenzione", "Il PDF selezionato non contiene pagine.")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il PDF:\n{e}")

    def render_page(self, page_index):
        """Renderizza una pagina del PDF."""
        if not self.pdf_doc or not (0 <= page_index < self.pdf_doc.page_count):
            return

        self.current_page_index = page_index
        page = self.pdf_doc[page_index]

        # Calcola DPI in base allo zoom
        dpi = int(150 * self.zoom_level)
        pix = page.get_pixmap(dpi=dpi)

        # Converti PyMuPDF pixmap → QPixmap (senza passare da PIL/ImageTk)
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimage)

        # Aggiorna scena
        scene = self.canvas.scene_ref
        scene.clear()
        self.roi_item_map.clear()

        self._pixmap_item = scene.addPixmap(qpixmap)
        scene.setSceneRect(QRectF(0, 0, pix.width, pix.height))

        self.draw_existing_rois()
        self.update_nav_controls()

    def draw_existing_rois(self):
        """Disegna le ROI esistenti sulla scena."""
        self.config = config_manager.load_config()
        scene = self.canvas.scene_ref

        # Rimuovi solo le ROI, non il pixmap
        for item_id in list(self.roi_item_map.keys()):
            with contextlib.suppress(Exception):
                scene.removeItem(item_id)
        self.roi_item_map.clear()

        factor = (150 * self.zoom_level) / 72

        for rule_index, rule in enumerate(self.config.get("classification_rules", [])):
            category_name = rule.get("category_name", "N/A")
            color_hex = rule.get("color", "#FF0000")
            color = QColor(color_hex)

            for roi_index, roi in enumerate(rule.get("rois", [])):
                if not all(isinstance(c, int) for c in roi) or len(roi) != 4:
                    continue

                x0, y0, x1, y1 = [c * factor for c in roi]

                # Rettangolo ROI
                pen = QPen(color, 3, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(color.red(), color.green(), color.blue(), 40))
                rect_item = scene.addRect(QRectF(x0, y0, x1 - x0, y1 - y0), pen, brush)

                # Etichetta categoria con sfondo
                text_width = len(category_name) * 8 + 10
                text_bg = scene.addRect(QRectF(x0, y0, text_width, 18), QPen(Qt.PenStyle.NoPen), QBrush(color))

                # Calcola contrasto testo
                h = color_hex.lstrip("#")
                try:
                    rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
                    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                    text_color = QColor("white") if brightness < 128 else QColor("black")
                except Exception:
                    text_color = QColor("white")

                text_item = QGraphicsSimpleTextItem(category_name)
                text_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                text_item.setBrush(QBrush(text_color))
                text_item.setPos(x0 + 5, y0 + 1)
                scene.addItem(text_item)

                # Mappa per cancellazione
                roi_info = {"rule_index": rule_index, "roi_index": roi_index}
                self.roi_item_map[rect_item] = roi_info
                self.roi_item_map[text_item] = roi_info
                self.roi_item_map[text_bg] = roi_info

    def handle_delete_click(self, scene_pos):
        """Gestisce il click in modalità cancellazione."""
        scene = self.canvas.scene_ref
        items = scene.items(scene_pos)

        if not items:
            return

        for item in items:
            if item in self.roi_item_map:
                roi_info = self.roi_item_map[item]
                rule_index = roi_info["rule_index"]
                roi_index = roi_info["roi_index"]

                if rule_index < len(self.config["classification_rules"]) and roi_index < len(
                    self.config["classification_rules"][rule_index].get("rois", [])
                ):
                    rule = self.config["classification_rules"][rule_index]
                    category_name = rule.get("category_name", "N/A")

                    reply = QMessageBox.question(
                        self,
                        "Conferma Cancellazione",
                        f"Eliminare questa ROI per la categoria '{category_name}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        del rule["rois"][roi_index]
                        self.save_and_refresh()
                        self.status_bar.setText(f"[OK] ROI eliminata da '{category_name}'")
                        return

    def prompt_and_save_roi(self, roi_coords):
        """Mostra il dialog per salvare la ROI."""
        categories = [rule["category_name"] for rule in self.config.get("classification_rules", [])]

        if not categories:
            QMessageBox.warning(
                self,
                "Nessuna Categoria",
                "Non ci sono categorie definite.\nCrea prima una categoria nell'applicazione principale.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Salva Nuova ROI")
        dialog.setFixedSize(550, 250)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Associa ROI alla categoria:")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        category_combo = QComboBox()
        category_combo.setFont(QFont("Segoe UI", 10))
        category_combo.addItems(categories)
        category_combo.setCurrentIndex(0)
        layout.addWidget(category_combo)

        # Info coordinate
        coords_text = f"Coordinate: ({roi_coords[0]}, {roi_coords[1]}) -> ({roi_coords[2]}, {roi_coords[3]})"
        coords_label = QLabel(coords_text)
        coords_label.setFont(QFont("Segoe UI", 9))
        coords_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        coords_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(coords_label)

        # Pulsanti
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_save = QPushButton("Salva ROI")
        btn_save.setFont(QFont("Segoe UI", 10))
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Annulla")
        btn_cancel.setFont(QFont("Segoe UI", 10))
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        def save():
            selected = category_combo.currentText()
            if not selected:
                return
            for rule in self.config["classification_rules"]:
                if rule["category_name"] == selected:
                    rule.setdefault("rois", []).append(roi_coords)
                    break
            self.save_and_refresh()
            self.status_bar.setText(f"[OK] ROI aggiunta a '{selected}'")
            dialog.accept()

        btn_save.clicked.connect(save)
        dialog.exec()

    def save_and_refresh(self):
        """Salva la configurazione e aggiorna la vista."""
        try:
            config_manager.save_config(self.config)

            # Crea il file segnale per l'app principale
            with open(SIGNAL_FILE, "w") as f:
                f.write("update")

            self.render_page(self.current_page_index)
            self._update_rules_list()

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare la configurazione:\n{e}")

    def prev_page(self):
        """Va alla pagina precedente."""
        if self.current_page_index > 0:
            self.render_page(self.current_page_index - 1)

    def next_page(self):
        """Va alla pagina successiva."""
        if self.pdf_doc and self.current_page_index < self.pdf_doc.page_count - 1:
            self.render_page(self.current_page_index + 1)

    def update_nav_controls(self):
        """Aggiorna i controlli di navigazione."""
        if not self.pdf_doc:
            return

        total_pages = self.pdf_doc.page_count
        self.page_label.setText(f"Pagina {self.current_page_index + 1} / {total_pages}")

        self.prev_page_button.setEnabled(self.current_page_index > 0)
        self.next_page_button.setEnabled(self.current_page_index < total_pages - 1)


def run_utility():
    """Entry point programmatico per l'utility."""
    print("+====================================================================+")
    print("|            INTELLEO - UTILITY GESTIONE ROI                         |")
    print("+====================================================================+")
    print("|  Usa questa utility per definire le aree di ricerca OCR.           |")
    print("|  Le modifiche verranno sincronizzate con l'app principale.         |")
    print("+====================================================================+")
    print()

    app = QApplication.instance()
    standalone = app is None
    if standalone:
        app = QApplication([])

    window = ROIDrawingApp()
    window.showMaximized()

    if standalone:
        app.exec()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    run_utility()
