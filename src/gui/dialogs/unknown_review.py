"""
Intelleo PDF Splitter - Unknown Files Review Dialog
Gestisce la revisione manuale dei file che non hanno matchato nessuna regola.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Import richiesto dai test per il mocking (legacy compatibility)
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.session_manager import SessionManager

logger = logging.getLogger("GUI")


class UnknownFilesReviewDialog(QDialog):
    """
    Finestra per la revisione dei file 'sconosciuti'.
    Permette all'utente di visualizzare i file non classificati e decidere se archiviarli o scartarli.
    """

    finished_review = Signal()

    def __init__(
        self,
        parent: QWidget | None,
        tasks: list[dict[str, Any]],
        odc: str = "N/A",
        on_finish: Any | None = None,
        on_close_callback: Any | None = None
    ) -> None:
        """Inizializza il dialogo con la lista dei task (file) da revisionare."""
        super().__init__(parent)
        self.review_tasks = tasks
        self.odc = odc
        self.task_index = 0
        self._is_closing = False
        self._on_finish_callback = on_finish
        self._on_close_callback = on_close_callback

        self.setWindowTitle(f"Revisione Allegati Sconosciuti - ODC: {odc}")
        self.resize(1200, 800)
        self.setup_ui()

        if self.review_tasks:
            self.load_task(0)

    def setup_ui(self) -> None:
        """Configura l'interfaccia grafica del dialogo di revisione."""
        self.main_layout = QHBoxLayout(self)

        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_panel.setFixedWidth(350)

        self.lbl_info = QLabel("<b>File da revisionare</b>")
        self.left_layout.addWidget(self.lbl_info)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_task)
        for task in self.review_tasks:
            name = Path(task["unknown_path"]).name
            self.list_widget.addItem(QListWidgetItem(name))
        self.left_layout.addWidget(self.list_widget)

        self.btn_layout = QHBoxLayout()
        self.btn_keep = QPushButton("Archivia come Altro")
        self.btn_keep.clicked.connect(self.on_keep)
        self.btn_ignore = QPushButton("Ignora")
        self.btn_ignore.clicked.connect(self.on_ignore)
        self.btn_layout.addWidget(self.btn_keep)
        self.btn_layout.addWidget(self.btn_ignore)
        self.left_layout.addLayout(self.btn_layout)
        self.main_layout.addWidget(self.left_panel)

        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)

        if getattr(sys, "_testing", False):
            self.preview = QWidget()
        else:
            from gui.widgets.preview_view import PreviewGraphicsView
            self.preview = PreviewGraphicsView()

        self.right_layout.addWidget(self.preview, 1)
        self.main_layout.addWidget(self.right_panel)

    def load_task(self, index: int) -> None:
        """Carica un task di revisione specifico visualizzandone l'anteprima PDF."""
        if not (0 <= index < len(self.review_tasks)):
            return
        self.task_index = index
        path = self.review_tasks[index]["unknown_path"]
        if not getattr(sys, "_testing", False) and hasattr(self.preview, "load_pdf"):
            self.preview.load_pdf(path)
        self.list_widget.setCurrentRow(index)

    def on_keep(self) -> None:
        """Azione per confermare l'archiviazione del file corrente."""
        self.next_or_close()

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
