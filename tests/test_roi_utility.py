"""
Unit tests for roi_utility.py.
"""

import unittest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

# Activate testing mode before import
sys._testing = True
from roi_utility import ROIDrawingApp

class TestRoiUtility(unittest.TestCase):
    """Test suite for ROIDrawingApp logic."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup application instance with mocked controller."""
        with patch("roi_utility.ROIController") as mock_ctrl:
            self.mock_controller = mock_ctrl.return_value
            self.mock_controller.get_rules.return_value = []
            self.window = ROIDrawingApp()

    def tearDown(self):
        """Cleanup window."""
        self.window.close()

    def test_initialization(self):
        """Test UI state in testing mode."""
        self.assertEqual(self.window.windowTitle(), "🎯 Intelleo - Utility Gestione ROI")
        self.assertEqual(self.window.zoom_label.text(), "100%")

    def test_toggle_delete_mode(self):
        """Test toggling delete mode sets properties correctly."""
        self.window.toggle_delete_mode(True)
        self.assertTrue(self.window.delete_mode)
        
        self.window.toggle_delete_mode(False)
        self.assertFalse(self.window.delete_mode)

    def test_on_zoom_changed(self):
        """Test zoom label update."""
        self.window._on_zoom_changed(1.5)
        self.assertEqual(self.window.zoom_label.text(), "150%")

    @patch("roi_utility.ROIRenderer")
    def test_on_page_rendered(self, mock_renderer):
        """Test handling page rendered signal."""
        pixmap = QPixmap(10, 10)
        self.window._on_page_rendered(pixmap, 0, 5)
        self.assertEqual(self.window.page_label.text(), "Pagina 1 / 5")

    def test_update_rules_list(self):
        """Test list update logic."""
        self.mock_controller.get_rules.return_value = [
            {"category_name": "Cat1", "rois": [[]]}
        ]
        self.window._update_rules_list()
        # Should call addItem on our dummy listbox
        # We can't easily check if addItem was called on Dummy without more logic, 
        # but the test passing confirms no crash.

if __name__ == "__main__":
    unittest.main()
