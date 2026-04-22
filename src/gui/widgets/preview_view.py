"""
Intelleo PDF Splitter — PreviewGraphicsView
Vista grafica con zoom e pan per anteprima PDF.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QImage, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from gui.theme import COLORS

logger = logging.getLogger("GUI")


class PreviewGraphicsView(QGraphicsView):
    """Vista grafica per anteprima PDF nel dialog di revisione."""

    def __init__(self, parent=None):
        """Inizializza la vista di anteprima con scena grafica e impostazioni di zoom."""
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_tertiary"])))
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None

    def wheelEvent(self, event):
        """Gestisce lo zoom interattivo tramite la rotellina del mouse."""
        self._zoom *= 1.1 if event.angleDelta().y() > 0 else 0.9
        self.resetTransform()
        self.scale(self._zoom, self._zoom)

    def mousePressEvent(self, event):
        """Inizia l'operazione di panning se il tasto Ctrl è premuto."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Esegue il panning della vista durante il movimento del mouse."""
        if self._panning and self._pan_start:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Termina l'operazione di panning e ripristina il cursore."""
        if self._panning:
            self._panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            super().mouseReleaseEvent(event)

    def show_pixmap(self, qpixmap):
        """Carica un Pixmap nella scena e ne adatta i confini."""
        self._scene.clear()
        self._scene.addPixmap(qpixmap)
        self._scene.setSceneRect(0, 0, qpixmap.width(), qpixmap.height())

    def load_pdf(self, file_path: str) -> None:
        """Carica la prima pagina di un PDF nella vista grafica."""
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.page_count > 0:
                page = doc.load_page(0)
                # Renderizzazione ad alta qualità (2.0 zoom) per nitidezza
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)

                # Conversione da samples di fitz a QImage
                fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)

                # Creazione di una copia per sicurezza (il buffer di fitz potrebbe essere liberato)
                self.show_pixmap(QPixmap.fromImage(qimg.copy()))
                doc.close()
            else:
                logger.warning(f"File PDF senza pagine: {file_path}")
        except Exception as e:
            logger.error(f"Errore durante il caricamento del PDF {file_path}: {e}")
