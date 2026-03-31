"""
Integration tests for the main application window.
"""

import sys
import typing
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

# NON impostiamo sys._testing = True qui per permettere il caricamento dei tab reali
# o gestiremo i mock internamente nel setUp.
import main


class TestMainApp(unittest.TestCase):
    """Test suite for MainApp class."""

    app: QApplication

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication for widget tests."""
        cls.app = typing.cast("QApplication", QApplication.instance() or QApplication([]))

    def setUp(self) -> None:
        """Create window and controller mocks."""
        # Patch dell'AppController per evitare effetti collaterali
        with patch("main.AppController") as mock_ctrl:
            self.mock_controller = mock_ctrl.return_value
            self.mock_controller.global_docs = 0
            self.mock_controller.global_pages = 0
            # Mock config.get per restituire stringhe (evita TypeError in setText)
            self.mock_controller.config = MagicMock()
            self.mock_controller.config.get.return_value = ""

            # Creiamo l'istanza. Se sys._testing è False (default), caricherà i tab.
            # Per sicurezza, forziamo False se fosse stato impostato altrove.
            if hasattr(sys, "_testing"):
                delattr(sys, "_testing")

            self.window = main.MainApp()

            # Mock degli attributi UI se non creati dai tab (fallback di sicurezza per i test)
            if not hasattr(self.window, "dashboard_start_btn"):
                self.window.dashboard_start_btn = MagicMock()
            if not hasattr(self.window, "files_count_sess_label"):
                self.window.files_count_sess_label = MagicMock()
            if not hasattr(self.window, "files_count_tot_label"):
                self.window.files_count_tot_label = MagicMock()
            if not hasattr(self.window, "pages_count_sess_label"):
                self.window.pages_count_sess_label = MagicMock()
            if not hasattr(self.window, "pages_count_tot_label"):
                self.window.pages_count_tot_label = MagicMock()

    def tearDown(self) -> None:
        """Clean up window."""
        self.window.close()

    def test_initialization(self) -> None:
        """Test window title and initial state."""
        self.assertIn("Intelleo", self.window.windowTitle())
        self.assertIsNotNone(self.window.tabs)

    def test_add_log_message(self) -> None:
        """Test adding log messages."""
        # Se dashboard_tab non esiste (es. in test isolati), verifichiamo log_area
        self.window.add_log_message("Test message", "INFO")
        log_text = ""
        if hasattr(self.window, "dashboard_tab") and hasattr(self.window.dashboard_tab, "console"):
            log_text = self.window.dashboard_tab.console.toPlainText()
        elif hasattr(self.window, "log_area"):
            log_text = self.window.log_area.toPlainText()

        self.assertIn("Test message", log_text)

    def test_on_processing_state_changed(self) -> None:
        """Test UI updates when processing starts/stops."""
        self.window.on_processing_state_changed(True)
        self.assertFalse(self.window.dashboard_start_btn.isEnabled())

        self.window.on_processing_state_changed(False)
        self.assertTrue(self.window.dashboard_start_btn.isEnabled())

    def test_on_stats_updated(self) -> None:
        """Test statistics labels update with 4 arguments."""
        # Firma: on_stats_updated(self, s_docs, s_pages, g_docs, g_pages)
        self.window.on_stats_updated(10, 50, 100, 500)

        # Se sono widget reali (non mock) usiamo .text(), altrimenti mock assertions
        for attr, expected in (
            ("files_count_sess_label", "10"),
            ("files_count_tot_label", "100"),
            ("pages_count_sess_label", "50"),
            ("pages_count_tot_label", "500")
        ):
            widget = getattr(self.window, attr)
            if hasattr(widget, "text"):
                self.assertEqual(widget.text(), expected)
            else:
                widget.setText.assert_called_with(expected)

    def test_tab_change_animation(self) -> None:
        """Test that changing tabs triggers UI animation."""
        with patch("gui.animations.UIAnimations.slide_fade_transition") as mock_anim:
            # Abbiamo rimosso _testing, quindi i tab dovrebbero esistere
            if self.window.tabs.count() > 1:
                self.window.tabs.setCurrentIndex(1)
                mock_anim.assert_called()


if __name__ == "__main__":
    unittest.main()
