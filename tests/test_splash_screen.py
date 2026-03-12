"""
Unit tests for splash_screen.py.
"""

import unittest

from PySide6.QtWidgets import QApplication

from gui.widgets.splash_screen import SplashScreen


class TestSplashScreen(unittest.TestCase):
    """Test suite for the SplashScreen widget."""

    @classmethod
    def setUpClass(cls):
        """Create the QApplication instance once for all tests."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Create a new SplashScreen for each test."""
        self.splash = SplashScreen()

    def tearDown(self):
        """Cleanup after each test."""
        self.splash.close()

    def test_initialization(self):
        """Test if the splash screen initializes with correct defaults."""
        self.assertEqual(self.splash.progress_bar.value(), 0)
        self.assertEqual(self.splash.status_label.text(), "Inizializzazione sistema...")
        self.assertIn("INTELLEO PDF SPLITTER", self.splash.title_label.text())

    def test_set_progress(self):
        """Test updating progress and status message."""
        self.splash.set_progress(50, "Test Message")
        self.assertEqual(self.splash.progress_bar.value(), 50)
        self.assertEqual(self.splash.status_label.text(), "Test Message")

    def test_set_version(self):
        """Test updating the version label."""
        self.splash.set_version("2.5.0")
        self.assertIn("2.5.0", self.splash.version_label.text())

if __name__ == "__main__":
    unittest.main()
