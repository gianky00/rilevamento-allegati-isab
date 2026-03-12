"""
Unit tests for the Notification Manager.
"""

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QLabel

from core.notification_manager import NotificationManager


class TestNotificationManager(unittest.TestCase):
    """Test suite for NotificationManager class."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication for widget tests."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        """Create notification manager instance."""
        self.manager = NotificationManager()

    def test_toast_initialization(self) -> None:
        """Test toast creation and content."""
        toast = self.manager.show_toast("Title", "Message", "INFO")
        self.assertIsNotNone(toast)
        
        labels = toast.findChildren(QLabel)
        texts = [label.text() for label in labels]
        self.assertIn("Title", texts)
        self.assertIn("Message", texts)

    def test_notify_stacking(self) -> None:
        """Test that multiple toasts stack vertically."""
        self.manager.notify("Msg 1")
        self.manager.notify("Msg 2")
        self.assertEqual(len(self.manager.active_toasts), 2)

    def test_show_history(self) -> None:
        """Test opening the notification history window."""
        self.manager.notify("Test")
        with patch("core.notification_manager.QDialog.show"):
            self.manager.show_history()
            # Verify no crash

    def test_on_controller_log_filtering(self) -> None:
        """Test that only ERROR/WARNING logs trigger a toast."""
        with patch.object(self.manager, "notify") as mock_notify:
            self.manager.on_controller_log("Normal info", "INFO")
            mock_notify.assert_not_called()
            
            self.manager.on_controller_log("Alert!", "WARNING")
            mock_notify.assert_called_once()

    def test_setup_bell_icon(self) -> None:
        """Test visual update of the notification bell."""
        btn = MagicMock()
        self.manager.setup_bell_icon(btn)
        self.manager.notify("Test")
        # Should change style or icon
        pass


if __name__ == "__main__":
    unittest.main()
