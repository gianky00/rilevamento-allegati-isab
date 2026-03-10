"""
Intelleo PDF Splitter - Utility ROI (PySide6)
Gestisce la definizione delle aree ROI per l'OCR.
"""

import contextlib
import sys
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.roi_controller import ROIController
from gui.dialogs.roi_selector_dialog import RoiSelectorDialog
from gui.theme import COLORS, FONTS
from gui.ui_factory import AnimatedButton
from gui.widgets.pdf_graphics_view import ROIGraphicsView
from gui.widgets.roi_renderer import ROIRenderer

SIGNAL_FILE = ".update_signal"


class ROIDrawingApp(QMainWindow):
    """Applicazione per la gestione delle aree ROI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inizializza l'applicazione, il controller e configura la GUI."""
        super().__init__(parent)
        self.setWindowTitle("🎯 Intelleo - Utility Gestione ROI")
        self.resize(1300, 900)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_primary']}; }}")

        # Controller
        self.controller = ROIController()
        self._connect_signals()

        # Widget UI
        self.nav_widget: QWidget
        self.prev_page_button: AnimatedButton
        self.next_page_button: AnimatedButton
        self.page_label: QLabel
        self.zoom_label: QLabel
        self.delete_mode_btn: QCheckBox
        self.mode_indicator: QLabel
        self.canvas: ROIGraphicsView
        self.rules_listbox: QListWidget
        self.status_bar: QLabel

        # Variabili di stato UI
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self.delete_mode = False
        self.roi_item_map: dict[Any, dict[str, int]] = {}
        self._filter_category: str | None = None

        if not getattr(sys, "_testing", False):
            self._setup_ui()
            self._setup_shortcuts()
        else:
            # Minimal UI mocks for logic testing
            class Dummy:
                def __init__(self, val=""): self._v = val
                def __getattr__(self, name): return lambda *args, **kwargs: Dummy()
                def text(self): return self._v
                def setText(self, t): self._v = t
                def setVisible(self, b): pass
                def setEnabled(self, b): pass
                def clear(self): pass
                def addItem(self, i): pass
                def count(self): return 0

            self.zoom_label = Dummy("100%")
            self.mode_indicator = Dummy()
            self.status_bar = Dummy()
            self.nav_widget = Dummy()
            self.page_label = Dummy()
            self.prev_page_button = Dummy()
            self.next_page_button = Dummy()
            self.canvas = Dummy()
            self.canvas.scene_ref = Dummy()
            self.rules_listbox = Dummy()

    def _setup_ui(self) -> None:
        """Crea l'interfaccia utente."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Header ---
        header = QLabel("Utility Gestione ROI")
        header.setFont(FONTS["heading"])
        header.setStyleSheet(f"color: {COLORS['accent']};")
        main_layout.addWidget(header)

        # --- Toolbar ---
        toolbar_group = QGroupBox(" Strumenti ")
        toolbar_group.setFont(FONTS["subheading"])
        toolbar_layout = QHBoxLayout(toolbar_group)
        toolbar_layout.setSpacing(8)

        # Apri PDF
        btn_open = AnimatedButton("Apri PDF di Esempio", is_primary=True)
        btn_open.setFont(FONTS["body"])
        btn_open.clicked.connect(self.open_pdf)
        toolbar_layout.addWidget(btn_open)

        self._add_separator(toolbar_layout)

        # Navigazione pagine
        self.nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_page_button = AnimatedButton("<< Pagina Precedente")
        self.prev_page_button.setFont(QFont("Segoe UI", 10))
        self.prev_page_button.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.prev_page_button)

        self.page_label = QLabel("Nessun PDF caricato")
        self.page_label.setFont(FONTS["body_bold"])
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(180)
        nav_layout.addWidget(self.page_label)

        self.next_page_button = AnimatedButton("Pagina Successiva >>")
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

        btn_zoom_out = AnimatedButton("-")
        btn_zoom_out.setFixedWidth(35)
        btn_zoom_out.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(btn_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(self.zoom_label)

        btn_zoom_in = AnimatedButton("+")
        btn_zoom_in.setFixedWidth(35)
        btn_zoom_in.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(btn_zoom_in)

        btn_zoom_reset = AnimatedButton("Reset")
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
        canvas_group.setFont(FONTS["subheading"])
        canvas_layout = QVBoxLayout(canvas_group)
        canvas_layout.setContentsMargins(10, 15, 10, 10)

        self.canvas = ROIGraphicsView(self)
        canvas_layout.addWidget(self.canvas)
        splitter.addWidget(canvas_group)

        # Sidebar
        sidebar_group = QGroupBox(" Regole Attive ")
        sidebar_group.setFont(FONTS["subheading"])
        sidebar_group.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar_group)

        self.rules_listbox = QListWidget()
        self.rules_listbox.setFont(FONTS["body"])
        self.rules_listbox.itemDoubleClicked.connect(self._on_rule_double_clicked)
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

        btn_refresh = AnimatedButton("Aggiorna Lista")
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
            "Attiva 'Cancellazione' per rimuovere ROI esistenti",
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
        """Visualizza un messaggio di stato e mostra dialoghi di errore se necessario."""
        self.status_bar.setText(f"[{level}] {message}")
        if level == "ERROR":
            QMessageBox.critical(self, "Errore", message)

    def _on_zoom_changed(self, level: float) -> None:
        """Aggiorna l'etichetta dello zoom nella UI."""
        self.zoom_label.setText(f"{int(level * 100)}%")

    def _on_page_rendered(self, pixmap: QPixmap, current: int, total: int) -> None:
        """Visualizza il pixmap della pagina PDF e aggiorna i controlli di navigazione."""
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
            item_text = f"  {name} ({roi_count} ROI)"

            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(item_text)

            # Evidenzia se filtrata
            if self._filter_category == name:
                item.setBackground(QColor(COLORS["accent"]))
                item.setForeground(QColor("white"))
                item.setText(f"👁 {name} ({roi_count} ROI) [FILTRO ATTIVO]")

            self.rules_listbox.addItem(item)

    def _on_rule_double_clicked(self, item: Any) -> None:
        """Gestisce il doppio click su una regola per attivare/disattivare il filtro."""
        text = item.text()
        # Estrai il nome della categoria (gestendo il prefisso 👁 e il suffisso [FILTRO...])
        clean_name = text.replace("👁 ", "").split(" (")[0].strip()

        if self._filter_category == clean_name:
            # Rimuove filtro
            self._filter_category = None
            self.status_bar.setText("[INFO] Filtro rimosso. Visualizzazione di tutte le ROI.")
        else:
            # Applica filtro
            self._filter_category = clean_name
            self.status_bar.setText(f"[INFO] Filtro attivato: visualizzazione esclusiva per '{clean_name}'")

        self._update_rules_list()
        self.draw_existing_rois()

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
        """Aumenta il livello di zoom della visualizzazione PDF."""
        self.controller.zoom_in()

    def zoom_out(self) -> None:
        """Diminuisce il livello di zoom della visualizzazione PDF."""
        self.controller.zoom_out()

    def zoom_reset(self) -> None:
        """Ripristina lo zoom al valore predefinito (100%)."""
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
        """Disegna le ROI esistenti delegando al renderer, rispettando eventuali filtri."""
        scene = self.canvas.scene_ref

        # Pulizia item ROI precedenti
        for item in list(self.roi_item_map.keys()):
            with contextlib.suppress(Exception):
                scene.removeItem(item)
        self.roi_item_map.clear()

        renderer = ROIRenderer(scene, self.controller.zoom_level)

        for rule_index, rule in enumerate(self.controller.get_rules()):
            category_name = rule.get("category_name", "N/A")

            # Applica filtro se attivo
            if self._filter_category and self._filter_category != category_name:
                continue

            color_hex = rule.get("color", "#FF0000")

            for roi_index, roi in enumerate(rule.get("rois", [])):
                items = renderer.draw_roi(rule_index, roi_index, category_name, color_hex, roi)

                # Registra item per interazione (cancellazione)
                roi_info = {"rule_index": rule_index, "roi_index": roi_index}
                for item in items:
                    self.roi_item_map[item] = roi_info

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

    def prompt_and_save_roi(self, roi_coords: list[int]) -> None:
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
        """Naviga alla pagina precedente del PDF caricato."""
        self.controller.prev_page()

    def next_page(self) -> None:
        """Naviga alla pagina successiva del PDF caricato."""
        self.controller.next_page()

    def update_nav_controls(self) -> None:
        """Vuoto: gestito da _on_page_rendered."""


def run_utility() -> None:
    """Entry point programmatico per l'utility."""

    app = QApplication(sys.argv)

    # FORZATURA STILE E PALETTE: Previene i bug di Windows Dark Mode o temi ad alto contrasto
    app.setStyle("Fusion")

    from PySide6.QtGui import QColor, QPalette

    from gui.theme import GLOBAL_QSS

    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8F9FA"))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Button, QColor("#F8F9FA"))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.Link, QColor("#2563EB"))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563EB"))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(light_palette)
    app.setStyleSheet(GLOBAL_QSS)

    window = ROIDrawingApp()
    window.show()
    sys.exit(app.exec())


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    run_utility()
