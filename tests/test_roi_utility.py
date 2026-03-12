"""
Unit tests for the ROI Drawing utility.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

# Activate testing mode before import
sys._testing = True  # type: ignore
from roi_utility import ROIDrawingApp  # noqa: E402


class TestRoiUtility(unittest.TestCase):
    """Test suite for ROIDrawingApp utility."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication for widget tests."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        """Create window and controller mocks."""
        with patch("roi_utility.RuleService"), patch("roi_utility.ConfigManager"):
            self.window = ROIDrawingApp()

    def tearDown(self) -> None:
        """Clean up window."""
        self.window.close()

    def test_initialization(self) -> None:
        """Test window title and initial UI state."""
        self.assertIn("Gestione Regole e ROI", self.window.windowTitle())
        self.assertFalse(self.window.delete_mode)

    def test_toggle_delete_mode(self) -> None:
        """Test switching between drawing and deletion modes."""
        self.window.toggle_delete_mode(True)
        self.assertTrue(self.window.delete_mode)
        
        self.window.toggle_delete_mode(False)
        self.assertFalse(self.window.delete_mode)

    def test_on_zoom_changed(self) -> None:
        """Test zoom level updates from the UI slider."""
        self.window.on_zoom_changed(150)
        # Check if the view scale was called or state updated
        # Here we just verify it doesn't crash
        pass

    def test_on_page_rendered(self) -> None:
        """Test handling of background image rendering."""
        pixmap = QPixmap(100, 100)
        self.window.on_page_rendered(pixmap)
        # Verify the scene was updated
        self.assertFalse(self.window.scene.itemsBoundingRect().isEmpty())

    def test_update_rules_list(self) -> None:
        """Test population of the rules list widget."""
        self.window.rules = [{"category_name": "Rule1"}]
        # Create a dummy list widget item since we are mocking
        self.window._update_rules_list()
        # Verify list widget has items
        self.assertEqual(self.window.list_rules.count(), 1)


if __name__ == "__main__":
    unittest.main()
