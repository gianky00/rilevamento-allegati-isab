"""
Unit tests for gui/tabs/dashboard_tab.py.
"""

import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QWidget
from gui.tabs.dashboard_tab import DashboardTab

class TestDashboardTab(unittest.TestCase):
    """Test suite for DashboardTab UI components."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup tab with a mocked MainApp."""
        self.mock_main = MagicMock()
        self.mock_main.notifier = None
        self.parent = QWidget()
        self.tab = DashboardTab(self.parent, self.mock_main)

    def tearDown(self):
        """Cleanup widgets."""
        self.tab.deleteLater()
        self.parent.deleteLater()

    def test_ui_initialization(self):
        """Test if dashboard widgets are created and linked to main_app."""
        # Check if tab correctly assigned its internal widgets to main_app attributes
        self.assertIsNotNone(self.mock_main.files_count_sess_label)
        self.assertIsNotNone(self.mock_main.rules_count_label)
        self.assertIsNotNone(self.mock_main.odc_entry)
        self.assertIsNotNone(self.mock_main.progress_bar)
        self.assertIsNotNone(self.mock_main.log_area)
        
        # Check if clock label was created on the tab itself
        self.assertTrue(hasattr(self.tab, "clock_label"))

if __name__ == "__main__":
    unittest.main()
