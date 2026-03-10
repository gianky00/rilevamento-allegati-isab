"""
Unit tests for main.py.
"""

import unittest
import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

# Activate testing mode before import
sys._testing = True
import main

class TestMainApp(unittest.TestCase):
    """Test suite for MainApp GUI orchestration."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup MainApp instance with mocked components."""
        # We need to mock things THAT MainApp USES/INSTANTIATES
        with patch("main.AppController"), \
             patch("main.DashboardTab"), \
             patch("main.ConfigTab"), \
             patch("main.HelpTab"), \
             patch("main.UIAnimations"):
            
            # Since RuleService is NOT in main module but in controller, 
            # and MainApp uses it via controller, we don't patch it in main.
            self.window = main.MainApp()

    def tearDown(self):
        """Cleanup window."""
        self.window.close()

    def test_initialization(self):
        """Test if MainApp initializes with core components."""
        self.assertTrue(self.window.windowTitle().startswith("Intelleo PDF Splitter"))
        self.assertIsNotNone(self.window.notebook)
        self.assertEqual(self.window.notebook.count(), 3)

    def test_on_stats_updated(self):
        """Test UI update on stats signal."""
        # Setup labels manually as tabs are mocked
        self.window.files_count_sess_label = MagicMock()
        self.window.files_count_tot_label = MagicMock()
        self.window.pages_count_sess_label = MagicMock()
        self.window.pages_count_tot_label = MagicMock()
        
        self.window._on_stats_updated(5, 10, 50, 100)
        
        self.window.files_count_sess_label.setText.assert_called_with("5")
        self.window.files_count_tot_label.setText.assert_called_with("50")

    def test_add_log_message(self):
        """Test adding log messages to UI area."""
        self.window.log_area = MagicMock()
        self.window.recent_log = MagicMock()
        
        self.window._add_log_message("Test message", "SUCCESS")
        
        call_args = self.window.log_area.append.call_args[0][0]
        self.assertIn("Test message", call_args)
        self.assertIn("[OK]", call_args)

    @patch("main.UIAnimations.slide_fade_transition")
    def test_tab_change_animation(self, mock_anim):
        """Test if tab change triggers transition animation."""
        self.window._on_tab_changed(1)
        mock_anim.assert_called()

    def test_on_processing_state_changed(self):
        """Test UI updates when processing state changes."""
        self.window.dashboard_start_btn = MagicMock()
        self.window.odc_entry = MagicMock()
        
        self.window._on_processing_state_changed(True)
        self.assertTrue(self.window._is_processing)
        self.window.dashboard_start_btn.setEnabled.assert_called_with(False)
        
        self.window._on_processing_state_changed(False)
        self.assertFalse(self.window._is_processing)
        self.window.dashboard_start_btn.setEnabled.assert_called_with(True)

if __name__ == "__main__":
    unittest.main()
