"""
Vista grafica personalizzata per il disegno di ROI su PDF (SRP).
"""

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QPen
from PySide6.QtWidgets import QFrame, QGraphicsRectItem, QGraphicsScene, QGraphicsView

# Colori per il disegno (riflessi dal tema utility)
COLORS = {
    "accent": "#0D6EFD",
    "bg_tertiary": "#E9ECEF",
}


class ROIGraphicsView(QGraphicsView):
    """Vista grafica con supporto a zoom, pan e disegno rettangoli ROI."""

    def __init__(self, app: Any, parent: Any | None = None) -> None:
        """Inizializza la vista grafica configurando la scena e lo stile di base."""
        super().__init__(parent)
        self.app = app
        self.scene_ref = QGraphicsScene(self)
        self.setScene(self.scene_ref)
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_tertiary"])))
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # Stato disegno
        self._start_point: QPointF | None = None
        self._current_rect: QGraphicsRectItem | None = None
        self._panning: bool = False
        self._pan_start: QPointF | None = None

    def wheelEvent(self, event: Any) -> None:
        """Gestisce lo zoom con la rotellina del mouse quando Ctrl è premuto."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.app.zoom_in()
            else:
                self.app.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        """Gestisce l'inizio del disegno di una ROI, il pan o la cancellazione."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self.app.delete_mode:
                self.app.handle_delete_click(scene_pos)
            else:
                self._start_point = scene_pos
                if self._current_rect:
                    self.scene_ref.removeItem(self._current_rect)
                pen = QPen(QColor(COLORS["accent"]), 2, Qt.PenStyle.DashLine)
                self._current_rect = self.scene_ref.addRect(QRectF(scene_pos, scene_pos), pen)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Aggiorna la geometria del rettangolo durante il disegno o esegue il panning."""
        if self._panning and self._pan_start:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        # Aggiorna coordinate (comunicazione con l'app principale)
        if hasattr(self.app, "pdf_manager") and self.app.pdf_manager.doc:
            factor = 72 / (150 * self.app.zoom_level)
            pdf_x = int(scene_pos.x() * factor)
            pdf_y = int(scene_pos.y() * factor)
            if not self.app.delete_mode:
                self.app.status_bar.setText(f"[DISEGNO] Modalità attiva | Coordinate PDF: ({pdf_x}, {pdf_y})")

        if not self.app.delete_mode and self._current_rect and self._start_point:
            rect = QRectF(self._start_point, scene_pos).normalized()
            self._current_rect.setRect(rect)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Finalizza il disegno della ROI convertendo le coordinate in formato PDF."""
        if self._panning:
            self._panning = False
            self.setCursor(
                QCursor(Qt.CursorShape.CrossCursor if not self.app.delete_mode else Qt.CursorShape.ForbiddenCursor),
            )
            event.accept()
            return

        if not self.app.delete_mode and self._start_point:
            end_point = self.mapToScene(event.position().toPoint())
            dist = math.hypot(end_point.x() - self._start_point.x(), end_point.y() - self._start_point.y())
            if dist < 10:
                if self._current_rect:
                    self.scene_ref.removeItem(self._current_rect)
                    self._current_rect = None
                self._start_point = None
                return

            factor = 72 / (150 * self.app.zoom_level)
            x0 = min(self._start_point.x(), end_point.x())
            y0 = min(self._start_point.y(), end_point.y())
            x1 = max(self._start_point.x(), end_point.x())
            y1 = max(self._start_point.y(), end_point.y())
            roi_pdf_coords = [int(c * factor) for c in (x0, y0, x1, y1)]

            self.app.prompt_and_save_roi(roi_pdf_coords)

            if self._current_rect:
                self.scene_ref.removeItem(self._current_rect)
                self._current_rect = None
            self._start_point = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
