"""
Integration tests for the main application window.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Activate testing mode before import
sys._testing = True  # type: ignore
import main  # noqa: E402


class TestMainApp(unittest.TestCase):
    """Test suite for MainApp class."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication for widget tests."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        """Create window and controller mocks."""
        with patch("main.AppController") as mock_ctrl:
            self.mock_controller = mock_ctrl.return_value
            self.mock_controller.global_docs = 0
            self.mock_controller.global_pages = 0
            self.window = main.MainApp()

    def tearDown(self) -> None:
        """Clean up window."""
        self.window.close()

    def test_initialization(self) -> None:
        """Test window title and initial state."""
        self.assertIn("Intelleo PDF Splitter", self.window.windowTitle())
        self.assertIsNotNone(self.window.tabs)

    def test_add_log_message(self) -> None:
        """Test adding log messages."""
        self.window.add_log_message("Test message", "INFO")
        console = self.window.dashboard_tab.console
        self.assertIn("Test message", console.toPlainText())

    def test_on_processing_state_changed(self) -> None:
        """Test UI updates when processing starts/stops."""
        self.window.on_processing_state_changed(True)
        self.assertFalse(self.window.dashboard_tab.btn_start.isEnabled())
        
        self.window.on_processing_state_changed(False)
        self.assertTrue(self.window.dashboard_tab.btn_start.isEnabled())

    def test_on_stats_updated(self) -> None:
        """Test statistics labels update."""
        self.window.on_stats_updated(10, 50)
        self.assertEqual(self.window.dashboard_tab.lbl_total_docs.text(), "10")
        self.assertEqual(self.window.dashboard_tab.lbl_total_pages.text(), "50")

    def test_tab_change_animation(self) -> None:
        """Test that changing tabs triggers UI animation."""
        with patch("gui.animations.UIAnimations.slide_fade_transition") as mock_anim:
            self.window.tabs.setCurrentIndex(1)
            mock_anim.assert_called()


if __name__ == "__main__":
    unittest.main()
