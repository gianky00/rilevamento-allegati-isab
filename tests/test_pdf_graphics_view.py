"""
Unit tests for gui/widgets/pdf_graphics_view.py.
"""

import typing
import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from gui.widgets.pdf_graphics_view import ROIGraphicsView


class TestPdfGraphicsView(unittest.TestCase):
    """Test suite for ROIGraphicsView interaction logic."""

    app: QApplication

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication."""
        cls.app = typing.cast("QApplication", QApplication.instance() or QApplication([]))

    def setUp(self):
        """Setup view with a mocked app."""
        self.mock_app = MagicMock()
        self.mock_app.delete_mode = False
        self.mock_app.zoom_level = 1.0
        self.view = ROIGraphicsView(self.mock_app)

    def tearDown(self):
        """Cleanup view."""
        self.view.deleteLater()

    def test_mouse_press_drawing_start(self):
        """Test starting a ROI drawing with real event."""
        pos = QPointF(10, 10)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos, pos, pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(event)
        self.assertIsNotNone(self.view._start_point)

    def test_mouse_release_minimal(self):
        """Test release without drawing doesn't crash."""
        pos = QPointF(10, 10)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            pos, pos, pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mouseReleaseEvent(event)
        self.assertIsNone(self.view._start_point)

if __name__ == "__main__":
    unittest.main()
