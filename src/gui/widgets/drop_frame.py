"""
Intelleo PDF Splitter — DropFrame
Frame che accetta il drag & drop nativo Qt di file PDF.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.theme import COLORS, FONTS


class DropFrame(QFrame):
    """Frame che accetta il drag & drop di file PDF."""

    def __init__(self, on_drop_callback, parent=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback
        self.setAcceptDrops(True)
        self._set_default_style()
        lbl = QLabel("Trascina file o cartelle qui per avviare l'elaborazione automatica", self)
        lbl.setFont(FONTS["small"])
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(lbl)

    def _set_default_style(self):
        self.setStyleSheet(f"""QFrame {{ background-color: {COLORS["bg_tertiary"]};
            border: 2px dashed {COLORS["border"]}; border-radius: 8px; }}""")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""QFrame {{ background-color: {COLORS["accent"]}20;
                border: 2px dashed {COLORS["accent"]}; border-radius: 8px; }}""")

    def dragLeaveEvent(self, event):
        self._set_default_style()

    def dropEvent(self, event: QDropEvent):
        self._set_default_style()
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                if os.path.isdir(path):
                    for root_dir, _, fnames in os.walk(path):
                        for name in fnames:
                            if name.lower().endswith(".pdf"):
                                files.append(os.path.join(root_dir, name))
                elif path.lower().endswith(".pdf"):
                    files.append(path)
        if files:
            self.on_drop_callback(files)
        event.acceptProposedAction()
