"""
Intelleo PDF Splitter - Utility ROI (PySide6)
Gestisce la definizione delle aree ROI per l'OCR.
"""

import contextlib
import math
import os
import sys
from typing import Any, Dict, List, Optional

import pymupdf as fitz
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QImage, QKeySequence, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
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

from gui.widgets.pdf_graphics_view import ROIGraphicsView
from gui.dialogs.roi_selector_dialog import RoiSelectorDialog
from core.roi_controller import ROIController

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


# ROIGraphicsView estratto in src.gui.widgets.pdf_graphics_view


class ROIDrawingApp(QMainWindow):
    """Applicazione per la gestione delle aree ROI."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎯 Intelleo - Utility Gestione ROI")
        self.resize(1300, 900)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_primary']}; }}")

        # Controller
        self.controller = ROIController()
        self._connect_signals()

        # Widget UI
        self.nav_widget: QWidget
        self.prev_page_button: QPushButton
        self.next_page_button: QPushButton
        self.page_label: QLabel
        self.zoom_label: QLabel
        self.delete_mode_btn: QCheckBox
        self.mode_indicator: QLabel
        self.canvas: ROIGraphicsView
        self.rules_listbox: QListWidget
        self.status_bar: QLabel

        # Variabili di stato UI
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.delete_mode = False
        self.roi_item_map: Dict[Any, Dict[str, int]] = {}

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
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

    def _add_separator(self, layout: QHBoxLayout) -> None:
        """Aggiunge un separatore verticale al layout."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setFixedWidth(20)
        layout.addWidget(sep)

    def _setup_shortcuts(self) -> None:
        """Configura scorciatoie tastiera."""
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, self.zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, self.zoom_out)
        QShortcut(QKeySequence(Qt.Key.Key_0), self, self.zoom_reset)

    def _connect_signals(self) -> None:
        """Collega i segnali del controller della ROI alla UI."""
        self.controller.page_rendered.connect(self._on_page_rendered)
        self.controller.rules_updated.connect(self._update_rules_list)
        self.controller.status_message.connect(self._on_status_message)
        self.controller.zoom_changed.connect(self._on_zoom_changed)

    def _on_status_message(self, message: str, level: str) -> None:
        self.status_bar.setText(f"[{level}] {message}")
        if level == "ERROR":
            QMessageBox.critical(self, "Errore", message)

    def _on_zoom_changed(self, level: float) -> None:
        self.zoom_label.setText(f"{int(level * 100)}%")

    def _on_page_rendered(self, pixmap: QPixmap, current: int, total: int) -> None:
        self.nav_widget.setVisible(True)
        self.page_label.setText(f"Pagina {current + 1} / {total}")
        self.prev_page_button.setEnabled(current > 0)
        self.next_page_button.setEnabled(current < total - 1)
        
        # Aggiorna scena
        scene = self.canvas.scene_ref
        scene.clear()
        self.roi_item_map.clear()
        self._pixmap_item = scene.addPixmap(pixmap)
        scene.setSceneRect(pixmap.rect())
        
        self.draw_existing_rois()

    def _update_rules_list(self) -> None:
        """Aggiorna la lista delle regole nella sidebar tramite controller."""
        self.rules_listbox.clear()
        for rule in self.controller.get_rules():
            name = rule.get("category_name", "N/A")
            roi_count = len(rule.get("rois", []))
            self.rules_listbox.addItem(f"  {name} ({roi_count} ROI)")

    def toggle_delete_mode(self, checked: bool) -> None:
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

    def zoom_in(self) -> None:
        self.controller.zoom_in()

    def zoom_out(self) -> None:
        self.controller.zoom_out()

    def zoom_reset(self) -> None:
        self.controller.zoom_reset()

    def open_pdf(self) -> None:
        """Delega apertura PDF al controller."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleziona un PDF di esempio", "", "PDF Files (*.pdf)")
        if filepath:
            self.controller.open_pdf(filepath)

    def render_page(self, page_index: int) -> None:
        """Invocato solo per rinfresco manuale (ora gestito dai segnali)."""
        self.controller.render_current_page()

    def draw_existing_rois(self) -> None:
        """Disegna le ROI esistenti recuperandole dal controller."""
        scene = self.canvas.scene_ref
        # Rimuovi solo le ROI, non il pixmap
        for item in list(self.roi_item_map.keys()):
            with contextlib.suppress(Exception):
                scene.removeItem(item)
        self.roi_item_map.clear()

        factor = (150 * self.controller.zoom_level) / 72
        for rule_index, rule in enumerate(self.controller.get_rules()):
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

    def handle_delete_click(self, scene_pos: QPointF) -> None:
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

                rules = self.controller.get_rules()
                if 0 <= rule_index < len(rules):
                    rule = rules[rule_index]
                    category_name = str(rule.get("category_name", "N/A"))

                    reply = QMessageBox.question(
                        self,
                        "Conferma Cancellazione",
                        f"Eliminare questa ROI per la categoria '{category_name}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        if self.controller.remove_roi(rule_index, roi_index):
                            self.status_bar.setText(f"[OK] ROI eliminata da '{category_name}'")
                        return

    def prompt_and_save_roi(self, roi_coords: List[int]) -> None:
        """Mostra il dialog per salvare la ROI utilizzando RoiSelectorDialog."""
        categories = self.controller.get_categories()

        if not categories:
            QMessageBox.warning(self, "Nessuna Categoria", "Non ci sono categorie definite.")
            return

        dlg = RoiSelectorDialog(self, categories, roi_coords, COLORS)
        if dlg.exec():
            selected = dlg.get_selected_category()
            if self.controller.add_roi(selected, roi_coords):
                self.status_bar.setText(f"[OK] ROI aggiunta a '{selected}'")

    def save_and_refresh(self) -> None:
        """Metodo obsoleto: gestito da ROIController.save_and_signal."""
        self.controller.save_and_signal()

    def prev_page(self) -> None:
        self.controller.prev_page()

    def next_page(self) -> None:
        self.controller.next_page()

    def update_nav_controls(self) -> None:
        """Vuoto: gestito da _on_page_rendered."""
        pass


def run_utility() -> None:
    """Entry point programmatico per l'utility."""
    print("+====================================================================+")
    print("|            INTELLEO - UTILITY GESTIONE ROI                         |")
    print("+====================================================================+")
    print("|  Usa questa utility per definire le aree di ricerca OCR.           |")
    print("|  Le modifiche verranno sincronizzate con l'app principale.         |")
    print("+====================================================================+")
    print()

    app = QApplication(sys.argv)
    window = ROIDrawingApp()
    window.show()
    sys.exit(app.exec())


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    run_utility()
