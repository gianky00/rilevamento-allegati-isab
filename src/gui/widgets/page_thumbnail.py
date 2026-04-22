"""
Intelleo PDF Splitter — PageThumbnail
Widget per la visualizzazione di una singola pagina PDF come miniatura con stato di selezione.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QMouseEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PageThumbnail(QWidget):
    """Widget che rappresenta una singola pagina del PDF nella griglia di revisione."""

    clicked = Signal(int, bool)  # index, is_selected

    def __init__(self, index: int, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.index = index
        self.selected = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.img_label = QLabel()
        self.img_label.setPixmap(pixmap.scaled(150, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border: 2px solid transparent; border-radius: 4px;")

        self.info_label = QLabel(f"Pagina {index + 1}")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 10px; color: #666;")

        self.main_layout.addWidget(self.img_label)
        self.main_layout.addWidget(self.info_label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(170)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Gestisce il click per la selezione della miniatura."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_selection()
            self.clicked.emit(self.index, self.selected)
        super().mousePressEvent(event)

    def toggle_selection(self, state: bool | None = None) -> None:
        """Cambia lo stato visivo di selezione della miniatura."""
        if state is not None:
            self.selected = state
        else:
            self.selected = not self.selected

        if self.selected:
            self.img_label.setStyleSheet("border: 3px solid #0D6EFD; border-radius: 4px; background-color: rgba(13, 110, 253, 0.1);")
            self.info_label.setStyleSheet("font-size: 10px; color: #0D6EFD; font-weight: bold;")
        else:
            self.img_label.setStyleSheet("border: 2px solid transparent; border-radius: 4px;")
            self.info_label.setStyleSheet("font-size: 10px; color: #666;")
