"""
Intelleo PDF Splitter — UnknownFilesReviewDialog
Dialog per la revisione manuale dei file sconosciuti (Splitter).
"""

import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from gui.theme import COLORS, FONTS
from gui.ui_factory import AnimatedButton
from gui.widgets.preview_view import PreviewGraphicsView
from shared.constants import SESSION_FILE

logger = logging.getLogger("MAIN")


class UnknownFilesReviewDialog(QDialog):
    """Dialog per la revisione manuale (Splitter) dei file sconosciuti."""

    def __init__(
        self,
        parent: Any,
        review_tasks: list[dict[str, Any]],
        on_finish: Any | None = None,
        odc: str | None = None,
        on_close_callback: Any | None = None,
    ) -> None:
        """Inizializza il dialog per la revisione manuale dei documenti non classificati."""
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint,
        )
        self.setWindowTitle("Revisione Manuale - Divisione Allegati")

        # Posticipa la massimizzazione al caricamento completato
        from PySide6 import QtCore

        QtCore.QTimer.singleShot(0, self.showMaximized)
        self.review_tasks = review_tasks
        self.on_finish = on_finish
        self.odc = odc
        self.on_close_callback = on_close_callback
        self.task_index = 0
        self.current_doc: Any | None = None
        self.current_doc_path: str | None = None
        self.available_pages: list[int] = []
        self.preview_page_index = 0

        self._create_widgets()
        self.load_task(0)

    def _create_widgets(self) -> None:
        """Configura layout e widget della finestra di revisione."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left.setFixedWidth(300)

        self.lbl_file_info = QLabel("Caricamento...")
        self.lbl_file_info.setFont(FONTS["subheading"])
        self.lbl_file_info.setWordWrap(True)
        left_layout.addWidget(self.lbl_file_info)

        lbl_pages = QLabel("Seleziona le pagine da unire:")
        lbl_pages.setFont(FONTS["body_bold"])
        left_layout.addWidget(lbl_pages)

        self.pages_listbox = QListWidget()
        self.pages_listbox.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pages_listbox.itemSelectionChanged.connect(self._on_page_select)
        left_layout.addWidget(self.pages_listbox, 1)

        action_group = QGroupBox(" Azione ")
        action_layout = QVBoxLayout(action_group)
        btn_rename = AnimatedButton("RINOMINA (Estrai Pagine)", is_primary=True)
        btn_rename.setFont(FONTS["body_bold"])
        btn_rename.clicked.connect(self.extract_and_rename)
        action_layout.addWidget(btn_rename)
        action_layout.addWidget(QLabel("Crea un nuovo file con le pagine selezionate."))
        left_layout.addWidget(action_group)

        self.btn_skip = AnimatedButton("Salta File >>")
        self.btn_skip.clicked.connect(self.skip_task)
        left_layout.addWidget(self.btn_skip)

        layout.addWidget(left)

        # Right panel - Preview
        self.preview = PreviewGraphicsView()
        layout.addWidget(self.preview, 1)

    def load_task(self, index: int) -> None:
        """Carica il documento PDF corrispondente all'indice della lista dei task."""
        # Rilascia sempre il documento precedente prima di caricare il nuovo o chiudere
        if self.current_doc:
            with suppress(Exception):
                self.current_doc.close()
            self.current_doc = None

        if index >= len(self.review_tasks):
            QMessageBox.information(self, "Completato", "Tutti i file sono stati revisionati con successo!")
            session_path = Path(SESSION_FILE)
            if session_path.exists():
                with suppress(Exception):
                    session_path.unlink()
            if self.on_finish:
                self.on_finish()
            self.accept()
            return

        self.task_index = index
        self.task = self.review_tasks[index]
        self.current_doc_path = self.task["unknown_path"]

        try:
            self.current_doc = fitz.open(self.current_doc_path)
            self.available_pages = list(range(self.current_doc.page_count))
            self.lbl_file_info.setText(
                f"File {index + 1}/{len(self.review_tasks)}\n{Path(self.current_doc_path).name}",
            )
            self._refresh_pages_list()
            if self.available_pages:
                self.pages_listbox.setCurrentRow(0)
                self._on_page_select()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file: {e}")
            self.skip_task()

    def _refresh_pages_list(self) -> None:
        """Aggiorna l'elenco grafico delle pagine disponibili per l'estrazione."""
        self.pages_listbox.clear()
        for real_idx in self.available_pages:
            self.pages_listbox.addItem(f"Pagina {real_idx + 1}")

    def _on_page_select(self) -> None:
        """Callback eseguita al cambio della selezione nella lista pagine per aggiornare l'anteprima."""
        items = self.pages_listbox.selectedItems()
        if not items:
            return
        last_row = self.pages_listbox.row(items[-1])
        if last_row < len(self.available_pages):
            self.preview_page_index = self.available_pages[last_row]
            self._render_preview()

    def _render_preview(self) -> None:
        """Renderizza graficamente la pagina PDF selezionata nell'area di anteprima."""
        if not self.current_doc:
            return
        try:
            page = self.current_doc[self.preview_page_index]
            pix = page.get_pixmap(dpi=150)
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            self.preview.show_pixmap(QPixmap.fromImage(qimage))
        except Exception as e:
            logger.exception(f"Render error: {e}")

    def extract_and_rename(self) -> None:
        """Estrae le pagine selezionate in un nuovo file PDF rinominato dall'utente."""
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
        odc_entry = QLineEdit(self.odc or "")
        odc_entry.setFocus()
        grid.addWidget(odc_entry, 0, 1)
        grid.addWidget(QLabel("Suffisso:"), 1, 0)
        suffix_entry = QLineEdit()
        grid.addWidget(suffix_entry, 1, 1)
        dlayout.addLayout(grid)

        result = {}

        def on_ok() -> None:
            """Valida l'input ODC/Suffisso e procede con la creazione del PDF."""
            result["odc"] = odc_entry.text().strip()
            result["suffix"] = suffix_entry.text().strip()
            if not result["odc"] or not result["suffix"]:
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

        if dialog.exec() != QDialog.DialogCode.Accepted or not result.get("odc"):
            return

        selected_indices = [self.pages_listbox.row(item) for item in selected]
        selected_real_indices = [self.available_pages[i] for i in selected_indices]
        new_filename = f"{result['odc']}_{result['suffix']}.pdf"

        if not self.current_doc_path:
            return

        src_path = Path(self.current_doc_path)
        output_path = src_path.parent / new_filename

        if output_path.exists():
            reply = QMessageBox.question(self, "Sovrascrivi", "File esistente. Sovrascrivere?")
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                output_path.unlink()
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile sovrascrivere:\n{e}")
                return

        try:
            new_doc = fitz.open()
            for idx in selected_real_indices:
                new_doc.insert_pdf(self.current_doc, from_page=idx, to_page=idx)
            new_doc.save(str(output_path))
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

    def finish_task(self) -> None:
        """Pulisce il file corrente e carica il prossimo task."""
        if self.current_doc:
            with suppress(Exception):
                self.current_doc.close()
            self.current_doc = None
        try:
            if self.current_doc_path:
                doc_path = Path(self.current_doc_path)
                if doc_path.exists():
                    doc_path.unlink()
        except Exception as e:
            logger.exception(f"Impossibile cancellare file temp {self.current_doc_path}: {e}")

        if 0 <= self.task_index < len(self.review_tasks):
            del self.review_tasks[self.task_index]
            session_path = Path(SESSION_FILE)
            if self.review_tasks:
                with suppress(Exception):
                    with session_path.open("w", encoding="utf-8") as f:
                        json.dump({"odc": self.odc, "tasks": self.review_tasks}, f, indent=4)
            elif session_path.exists():
                with suppress(Exception):
                    session_path.unlink()
            self.load_task(self.task_index)
        else:
            self.load_task(0)

    def skip_task(self) -> None:
        """Salta il file corrente senza elaborarlo."""
        self.load_task(self.task_index + 1)

    def closeEvent(self, event: Any) -> None:
        """Gestisce il salvataggio della sessione alla chiusura del dialog."""
        if self.current_doc:
            with suppress(Exception):
                self.current_doc.close()
            self.current_doc = None
        if self.review_tasks:
            try:
                session_path = Path(SESSION_FILE)
                session_path.parent.mkdir(parents=True, exist_ok=True)
                with session_path.open("w", encoding="utf-8") as f:
                    json.dump({"odc": self.odc, "tasks": self.review_tasks}, f, indent=4)
                logger.info(f"Sessione salvata: {len(self.review_tasks)} task rimasti.")
            except Exception as e:
                logger.exception(f"Errore salvataggio sessione: {e}")
        if self.on_close_callback:
            with suppress(Exception):
                self.on_close_callback()
        super().closeEvent(event)
