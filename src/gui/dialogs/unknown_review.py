import logging
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.session_manager import SessionManager
from gui.widgets.page_thumbnail import PageThumbnail

logger = logging.getLogger("GUI")


class UnknownFilesReviewDialog(QDialog):
    """
    Finestra per lo smistamento manuale avanzato di file e pagine 'sconosciuti'.
    Permette all'utente di selezionare singole pagine e assegnarle a categorie specifiche.
    """

    finished_review = Signal()

    def __init__(
        self,
        parent: QWidget | None,
        tasks: list[dict[str, Any]],
        odc: str = "N/A",
        rules: list[dict[str, Any]] | None = None,
        on_finish: Any | None = None,
        on_close_callback: Any | None = None
    ) -> None:
        """Inizializza il dialogo con la lista dei task e le regole di classificazione."""
        super().__init__(parent)
        self.review_tasks = tasks
        self.odc = odc
        self.rules = rules or []
        self.task_index = 0
        self._is_closing = False
        self._on_finish_callback = on_finish
        self._on_close_callback = on_close_callback

        # Stato smistamento per il file corrente {page_index: category_name}
        self.current_page_assignments: dict[int, str] = {}
        self.selected_pages: set[int] = set()

        self.setWindowTitle(f"Smistamento Manuale - ODC: {odc}")
        self.resize(1400, 900)
        self.setup_ui()

        if self.review_tasks:
            self.load_task(0)

        if self.review_tasks:
            self.load_task(0)

    def setup_ui(self) -> None:
        """Configura l'interfaccia con Anteprima a destra (piena altezza) e Controlli a sinistra."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Splitter Principale (Orizzontale)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- PANNELLO SINISTRO (Gestione e Miniature) ---
        self.left_container = QFrame()
        self.left_container.setStyleSheet("background-color: #F8F9FA; border-right: 1px solid #DDD;")
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Lista File (compatta in alto)
        self.lbl_files = QLabel("<b>📁 File in Revisione</b>")
        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(80)  # Altezza fissa ridotta per massimizzare miniature
        self.list_widget.currentRowChanged.connect(self.load_task)
        for task in self.review_tasks:
            name = Path(task["unknown_path"]).name
            self.list_widget.addItem(QListWidgetItem(name))

        self.left_layout.addWidget(self.lbl_files)
        self.left_layout.addWidget(self.list_widget)

        # 2. Area Miniature (parte centrale estesa)
        self.lbl_pages = QLabel("<b>📄 Pagine Documento (Miniature)</b>")
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: white;")
        self.thumb_container = QWidget()
        self.thumb_grid = QGridLayout(self.thumb_container)
        self.thumb_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll_area.setWidget(self.thumb_container)

        self.left_layout.addSpacing(10)
        self.left_layout.addWidget(self.lbl_pages)
        self.left_layout.addWidget(self.scroll_area, 1)

        # 3. Pannello Azioni Compatto (in basso a sinistra)
        self.actions_panel = QFrame()
        self.actions_panel.setStyleSheet("background-color: #F1F3F5; border-radius: 8px; padding: 5px;")
        self.actions_vlayout = QVBoxLayout(self.actions_panel)

        self.sel_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Tutte")
        self.btn_select_all.setFixedWidth(50)
        self.btn_select_all.setStyleSheet("padding: 2px;")
        self.btn_select_all.clicked.connect(self.select_all_pages)

        self.category_combo = QComboBox()
        self.category_combo.addItem("--- Categoria ---", "")
        for rule in self.rules:
            self.category_combo.addItem(rule.get("category_name", "N/A"), rule.get("category_name"))
        self.category_combo.addItem("ALTRO", "Altro")

        self.sel_layout.addWidget(self.btn_select_all)
        self.sel_layout.addWidget(self.category_combo, 1)
        self.actions_vlayout.addLayout(self.sel_layout)

        self.btn_apply = QPushButton("Applica Smistamento")
        self.btn_apply.setStyleSheet("background-color: #0D6EFD; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply.clicked.connect(self.apply_category_to_selection)
        self.actions_vlayout.addWidget(self.btn_apply)

        self.bottom_btns = QHBoxLayout()
        self.btn_finish_task = QPushButton("CONCLUDI")
        self.btn_finish_task.setStyleSheet("background-color: #198754; color: white; font-weight: bold; padding: 5px;")
        self.btn_finish_task.clicked.connect(self.finish_and_split)

        self.btn_ignore = QPushButton("Ignora")
        self.btn_ignore.setStyleSheet("padding: 5px;")
        self.btn_ignore.clicked.connect(self.on_ignore)

        self.bottom_btns.addWidget(self.btn_finish_task, 2)
        self.bottom_btns.addWidget(self.btn_ignore, 1)
        self.actions_vlayout.addLayout(self.bottom_btns)

        self.left_layout.addSpacing(10)
        self.left_layout.addWidget(self.actions_panel)

        self.splitter.addWidget(self.left_container)

        # --- PANNELLO DESTRO (Anteprima Dettaglio) ---
        if getattr(sys, "_testing", False):
            self.preview = QFrame()
        else:
            from gui.widgets.preview_view import PreviewGraphicsView
            self.preview = PreviewGraphicsView()

        self.splitter.addWidget(self.preview)

        # Inizialmente 40% sinistra / 60% destra (Anteprima grande)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 6)

        self.main_layout.addWidget(self.splitter)

    def load_task(self, index: int) -> None:
        """Carica un task di revisione specifico e genera le miniature delle pagine."""
        if not (0 <= index < len(self.review_tasks)):
            return

        self.task_index = index
        path = self.review_tasks[index]["unknown_path"]

        # Reset stato selezione
        self.selected_pages.clear()
        self.current_page_assignments.clear()
        self.category_combo.setCurrentIndex(0)

        # Aggiorna evidenziazione lista
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentRow(index)
        self.list_widget.blockSignals(False)

        # Carica anteprima grande (prima pagina per default)
        if hasattr(self.preview, "load_pdf"):
            self.preview.load_pdf(path)

        # Genera miniature
        self.update_thumbnails(path)

    def update_thumbnails(self, pdf_path: str) -> None:
        """Svuota e rigenera la griglia delle miniature (2 colonne) per il PDF corrente."""
        # Pulisci griglia
        while self.thumb_grid.count():
            item = self.thumb_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        try:
            import fitz
            doc = fitz.open(pdf_path)
            cols = 1  # Dispositizione verticale (una sotto l'altra) per massimizzare la leggibilità

            for i in range(len(doc)):
                page = doc.load_page(i)
                # Miniatura a bassa risoluzione per velocità
                pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))

                # Conversione in QPixmap
                from PySide6.QtGui import QImage
                fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
                qpix = QPixmap.fromImage(qimg.copy())

                thumb = PageThumbnail(i, qpix)
                thumb.clicked.connect(self.on_thumbnail_clicked)

                self.thumb_grid.addWidget(thumb, i // cols, i % cols)

            doc.close()
        except Exception as e:
            logger.error(f"Errore generazione miniature: {e}")

    def on_thumbnail_clicked(self, index: int, is_selected: bool) -> None:
        """Gestisce la selezione di una miniatura e aggiorna l'anteprima grande."""
        if is_selected:
            self.selected_pages.add(index)
            self.show_page_preview(index)
        else:
            self.selected_pages.discard(index)

    def show_page_preview(self, page_index: int) -> None:
        """Carica una pagina specifica nell'anteprima grande."""
        try:
            import fitz
            path = self.review_tasks[self.task_index]["unknown_path"]
            doc = fitz.open(path)
            page = doc.load_page(page_index)
            # Anteprima ad alta qualità
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

            from PySide6.QtGui import QImage
            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)

            if hasattr(self.preview, "show_pixmap"):
                self.preview.show_pixmap(QPixmap.fromImage(qimg.copy()))
            doc.close()
        except Exception as e:
            logger.error(f"Errore anteprima pagina {page_index}: {e}")

    def select_all_pages(self) -> None:
        """Seleziona tutte le miniature presenti nella griglia."""
        for i in range(self.thumb_grid.count()):
            widget = self.thumb_grid.itemAt(i).widget()
            if isinstance(widget, PageThumbnail):
                widget.toggle_selection(True)
                self.selected_pages.add(widget.index)

    def apply_category_to_selection(self) -> None:
        """Assegna la categoria selezionata alle pagine marcate."""
        category = self.category_combo.currentData()
        if not category:
            return

        if not self.selected_pages:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Info", "Seleziona almeno una pagina cliccando sulle miniature.")
            return

        for p in self.selected_pages:
            self.current_page_assignments[p] = category

        # Feedback visivo
        for i in range(self.thumb_grid.count()):
            widget = self.thumb_grid.itemAt(i).widget()
            if isinstance(widget, PageThumbnail) and widget.index in self.selected_pages:
                widget.info_label.setText(f"PAG {widget.index + 1} -> {category[:10]}")
                widget.info_label.setStyleSheet("font-size: 10px; color: #198754; font-weight: bold;")
                widget.toggle_selection(False)

        self.selected_pages.clear()

    def finish_and_split(self) -> None:
        """Esegue lo split fisico del file in base allo smistamento e passa al prossimo."""
        if not self.current_page_assignments:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Attenzione", "Nessuna pagina è stata smistata. Assegna le categorie prima di concludere.")
            return

        try:
            import pymupdf as fitz

            from core.pdf_splitter import PdfSplitter

            task = self.review_tasks[self.task_index]
            pdf_path = task["unknown_path"]
            doc = fitz.open(pdf_path)

            # Trasforma dict {page: cat} in {cat: [pages]}
            page_groups: dict[str, list[int]] = {}
            for page, cat in self.current_page_assignments.items():
                if cat not in page_groups:
                    page_groups[cat] = []
                page_groups[cat].append(page)

            output_dir = str(Path(pdf_path).parent)
            PdfSplitter.split_and_save(doc, page_groups, self.rules, output_dir, self.odc)
            doc.close()

            logger.info(f"Smistamento manuale completato per {pdf_path}")
            self.next_or_close()

        except Exception as e:
            logger.error(f"Errore durante lo split manuale: {e}")

    def on_ignore(self) -> None:
        """Azione per ignorare il file corrente."""
        self.next_or_close()

    def next_or_close(self) -> None:
        """Passa al task successivo o chiude il dialogo se terminati."""
        if self.task_index + 1 < len(self.review_tasks):
            self.load_task(self.task_index + 1)
        else:
            if self._on_finish_callback:
                self._on_finish_callback()
            self.finished_review.emit()
            self.accept()

    def closeEvent(self, event: Any) -> None:
        """Gestisce l'evento di chiusura salvando la sessione corrente."""
        self._is_closing = True
        SessionManager.save_session(self.review_tasks, self.odc)
        if self._on_close_callback:
            self._on_close_callback()
        super().closeEvent(event)
