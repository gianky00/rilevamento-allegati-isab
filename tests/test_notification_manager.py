"""
Unit tests for core/notification_manager.py.
"""

import unittest
import time
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from core.notification_manager import NotificationManager, ToastNotification, COLORS

class TestNotificationManager(unittest.TestCase):
    """Test suite for NotificationManager and ToastNotification."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for widget tests."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup a parent widget and manager for each test."""
        self.parent = QWidget()
        self.manager = NotificationManager(self.parent)

    def tearDown(self):
        """Cleanup widgets."""
        self.parent.deleteLater()
        for n in self.manager.notifications:
            with patch("PySide6.QtWidgets.QWidget.close"):
                n["window"].deleteLater()

    def test_toast_initialization(self):
        """Test if ToastNotification initializes with correct properties."""
        toast = ToastNotification("Title", "Message", "#FF0000", "#FFFFFF")
        self.assertEqual(toast.windowOpacity(), 0.0)
        from PySide6.QtWidgets import QLabel
        labels = toast.findChildren(QLabel)
        texts = [l.text() for l in labels]
        self.assertIn("Title", texts)
        self.assertIn("Message", texts)
        toast.deleteLater()

    def test_notify_stacking(self):
        """Test that multiple notifications increment unread count and stack."""
        with patch("PySide6.QtWidgets.QApplication.primaryScreen") as mock_screen:
            mock_geo = MagicMock()
            mock_geo.width.return_value = 1920
            mock_geo.height.return_value = 1080
            mock_screen.return_value.availableGeometry.return_value = mock_geo
            
            self.manager.notify("T1", "M1", "INFO")
            self.assertEqual(self.manager.unread_count, 1)
            self.assertEqual(len(self.manager.notifications), 1)
            
            self.manager.notify("T2", "M2", "SUCCESS")
            self.assertEqual(self.manager.unread_count, 2)
            self.assertEqual(len(self.manager.notifications), 2)
            
            self.assertEqual(len(self.manager.history), 2)
            self.assertEqual(self.manager.history[0]["title"], "T1")

    def test_on_controller_log_filtering(self):
        """Test that only important logs trigger notifications."""
        self.manager.notify = MagicMock()
        
        self.manager._on_controller_log("Minor info", "INFO")
        self.manager.notify.assert_not_called()
        
        self.manager._on_controller_log("File completato: test.pdf", "SUCCESS")
        self.manager.notify.assert_called_with("SUCCESS", "File completato: test.pdf", "SUCCESS")

    def test_setup_bell_icon(self):
        """Test bell icon setup and update."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        self.manager.setup_bell_icon(layout)
        self.assertIsNotNone(self.manager.bell_container)
        self.assertEqual(self.manager.bell_count_label.text(), "0")
        
        with patch("PySide6.QtWidgets.QApplication.primaryScreen"):
            self.manager.notify("Test", "Msg")
            self.assertEqual(self.manager.bell_count_label.text(), "1")

    def test_show_history(self):
        """Test showing history popup."""
        # Setup bell icon first to have bell_count_label
        container = QWidget()
        layout = QVBoxLayout(container)
        self.manager.setup_bell_icon(layout)
        
        # Add history
        self.manager.history = [{"title": "SUCCESS", "msg": "Done", "time": time.time(), "level": "SUCCESS"}]
        self.manager.unread_count = 5
        
        with patch("PySide6.QtWidgets.QFrame.show"):
            self.manager.show_history()
            self.assertEqual(self.manager.unread_count, 0)
            self.assertEqual(self.manager.bell_count_label.text(), "0")
            self.assertIsNotNone(self.manager._history_list)
            self.assertEqual(self.manager._history_list.count(), 1)

if __name__ == "__main__":
    unittest.main()
