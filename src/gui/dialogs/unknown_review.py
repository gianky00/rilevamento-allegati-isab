"""
Intelleo PDF Splitter - Unknown Files Review Dialog
Gestisce la revisione manuale dei file che non hanno matchato nessuna regola.
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pymupdf as fitz
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
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
from gui.theme import COLORS
from gui.widgets.preview_view import PreviewGraphicsView

if TYPE_CHECKING:
    from unittest.mock import MagicMock
else:
    MagicMock = Any

logger = logging.getLogger("GUI")


class UnknownFilesReviewDialog(QDialog):
    """
    Finestra per la revisione dei file 'sconosciuti'.
    Permette all'utente di visualizzare i file e decidere se archiviarli o ignorarli.
    """

    finished_review = Signal()

    def __init__(
        self,
        parent: Optional[QWidget],
        tasks: List[Dict[str, Any]],
        odc: str = "N/A"
    ) -> None:
        super().__init__(parent)
        self.review_tasks = tasks
        self.odc = odc
        self.task_index = 0
        self._is_closing = False

        self.setWindowTitle(f"Revisione Allegati Sconosciuti - ODC: {odc}")
        self.resize(1200, 800)
        self.setup_ui()
        
        if self.review_tasks:
            self.load_task(0)

    def setup_ui(self) -> None:
        """Configura l'interfaccia grafica."""
        self.main_layout = QHBoxLayout(self)

        # Sinistra: Lista e Controlli
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_panel.setFixedWidth(350)

        self.lbl_info = QLabel("<b>File da revisionare</b>")
        self.left_layout.addWidget(self.lbl_info)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_task)
        for task in self.review_tasks:
            name = Path(task["unknown_path"]).name
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)
        self.left_layout.addWidget(self.list_widget)

        self.btn_layout = QHBoxLayout()
        self.btn_keep = QPushButton("Archivia come Altro")
        self.btn_keep.setStyleSheet(f"background-color: {COLORS['success']}; color: white; padding: 10px;")
        self.btn_keep.clicked.connect(self.on_keep)
        
        self.btn_ignore = QPushButton("Ignora")
        self.btn_ignore.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; padding: 10px;")
        self.btn_ignore.clicked.connect(self.on_ignore)

        self.btn_layout.addWidget(self.btn_keep)
        self.btn_layout.addWidget(self.btn_ignore)
        self.left_layout.addLayout(self.btn_layout)

        self.main_layout.addWidget(self.left_panel)

        # Destra: Anteprima
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # Gestione speciale per test senza GUI reale
        if getattr(sys, "_testing", False):
            from unittest.mock import MagicMock as MM
            self.preview: Any = MM()
            placeholder = QWidget()
            self.right_layout.addWidget(placeholder, 1)
        else:
            self.preview = PreviewGraphicsView()
            self.right_layout.addWidget(self.preview, 1)

        self.main_layout.addWidget(self.right_panel)

    def load_task(self, index: int) -> None:
        """Carica il task selezionato nell'anteprima."""
        if not (0 <= index < len(self.review_tasks)):
            return
        
        self.task_index = index
        task = self.review_tasks[index]
        path = task["unknown_path"]
        
        if not getattr(sys, "_testing", False):
            self.preview.load_pdf(path)
        
        self.list_widget.setCurrentRow(index)

    def on_keep(self) -> None:
        """Segna il file come da tenere (categoria 'Altro')."""
        # Logica di archiviazione (implementata via AppController)
        self.next_or_close()

    def on_ignore(self) -> None:
        """Segna il file come da ignorare."""
        self.next_or_close()

    def next_or_close(self) -> None:
        """Passa al file successivo o chiude se finiti."""
        if self.task_index + 1 < len(self.review_tasks):
            self.load_task(self.task_index + 1)
        else:
            self.finished_review.emit()
            self.accept()

    def closeEvent(self, event: Any) -> None:
        """Salva lo stato se l'utente chiude forzatamente."""
        if not self._is_closing:
            SessionManager.save_session(self.review_tasks, self.odc)
        super().closeEvent(event)
