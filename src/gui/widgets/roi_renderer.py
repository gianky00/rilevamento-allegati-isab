"""
Responsabile del rendering grafico delle aree ROI (SRP).
Trasforma coordinate PDF in oggetti QGraphicsItem.
"""

from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSimpleTextItem


class ROIRenderer:
    """Gestisce il disegno delle ROI su una QGraphicsScene."""

    def __init__(self, scene: QGraphicsScene, zoom_level: float):
        """Inizializza il renderer con la scena di destinazione e il fattore di zoom corrente."""
        self.scene = scene
        self.zoom_level = zoom_level
        # Fattore di scala: (DPI_RENDER / DPI_PDF_BASE)
        self.scale_factor = (150 * zoom_level) / 72

    def draw_roi(
        self,
        rule_index: int,
        roi_index: int,
        category_name: str,
        color_hex: str,
        roi_coords: list[int],
    ) -> list[Any]:
        """Disegna una singola ROI e la sua etichetta. Restituisce gli item creati."""
        if len(roi_coords) != 4:
            return []

        color = QColor(color_hex)
        x0, y0, x1, y1 = [c * self.scale_factor for c in roi_coords]
        w, h = x1 - x0, y1 - y0

        # 1. Rettangolo principale
        pen = QPen(color, 3, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(color.red(), color.green(), color.blue(), 40))
        rect_item = self.scene.addRect(QRectF(x0, y0, w, h), pen, brush)

        # 2. Etichetta categoria
        text_width = len(category_name) * 8 + 10
        text_bg = self.scene.addRect(QRectF(x0, y0, text_width, 18), QPen(Qt.PenStyle.NoPen), QBrush(color))

        text_color = self._get_contrast_color(color_hex)
        text_item = QGraphicsSimpleTextItem(category_name)
        text_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_item.setBrush(QBrush(text_color))
        text_item.setPos(x0 + 5, y0 + 1)
        self.scene.addItem(text_item)

        return [rect_item, text_bg, text_item]

    def _get_contrast_color(self, hex_color: str) -> QColor:
        """Calcola se usare bianco o nero per il testo sopra il colore dato."""
        h = hex_color.lstrip("#")
        try:
            rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
            brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            return QColor("white") if brightness < 128 else QColor("black")
        except Exception:
            return QColor("white")
