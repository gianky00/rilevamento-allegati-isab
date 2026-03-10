"""
Unit tests for gui/tabs/config_tab.py.
"""

import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QWidget
from gui.tabs.config_tab import ConfigTab

class TestConfigTab(unittest.TestCase):
    """Test suite for ConfigTab UI components."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup tab with a mocked MainApp."""
        self.mock_main = MagicMock()
        self.parent = QWidget()
        self.tab = ConfigTab(self.parent, self.mock_main)

    def tearDown(self):
        """Cleanup widgets."""
        self.tab.deleteLater()
        self.parent.deleteLater()

    def test_ui_initialization(self):
        """Test if config widgets are created and linked to main_app attributes."""
        self.assertIsNotNone(self.mock_main.tesseract_path_entry)
        self.assertIsNotNone(self.mock_main.rules_tree)
        self.assertIsNotNone(self.mock_main.keywords_text)
        self.assertIsNotNone(self.mock_main.roi_details_label)
        
        # Check specific widget types/properties
        self.assertEqual(self.mock_main.rules_tree.columnCount(), 3)
        self.assertTrue(self.mock_main.keywords_text.isReadOnly())

if __name__ == "__main__":
    unittest.main()
