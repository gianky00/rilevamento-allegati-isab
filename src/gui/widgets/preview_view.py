"""
Intelleo PDF Splitter — PreviewGraphicsView
Vista grafica con zoom e pan per anteprima PDF.
"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QPixmap

from gui.theme import COLORS


class PreviewGraphicsView(QGraphicsView):
    """Vista grafica per anteprima PDF nel dialog di revisione."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(COLORS['bg_tertiary'])))
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None

    def wheelEvent(self, event):
        self._zoom *= 1.1 if event.angleDelta().y() > 0 else 0.9
        self.resetTransform()
        self.scale(self._zoom, self._zoom)

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            super().mouseReleaseEvent(event)

    def show_pixmap(self, qpixmap):
        self._scene.clear()
        self._scene.addPixmap(qpixmap)
        self._scene.setSceneRect(0, 0, qpixmap.width(), qpixmap.height())
