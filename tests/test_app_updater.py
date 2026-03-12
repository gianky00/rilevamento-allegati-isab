"""
Unit tests for app_updater.py.
"""

import json
import unittest
from unittest.mock import patch

import app_updater


class TestAppUpdater(unittest.TestCase):
    """Test suite for app_updater module."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for widget tests."""
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Reset global variables before each test."""
        app_updater._pending_installer_path = None

    @patch("app_updater.get_metadata_from_network")
    @patch("app_updater.get_metadata_from_web")
    @patch("app_updater.QMessageBox.question")
    @patch("app_updater.version")
    def test_check_for_updates_network_preferred(self, mock_ver, mock_quest, mock_web, mock_net):
        """Test that network update is preferred when versions are equal."""
        mock_ver.__version__ = "1.0.0"

        # Entrambi hanno la 2.0.0
        mock_net.return_value = {"version": "2.0.0", "url": "\\\\path\\\\setup.exe", "source": "Rete Locale"}
        mock_web.return_value = {"version": "2.0.0", "url": "http://web/setup.exe", "source": "Web"}

        from PySide6.QtWidgets import QMessageBox
        mock_quest.return_value = QMessageBox.StandardButton.Yes

        with patch("app_updater.perform_auto_update") as mock_perform:
            app_updater.check_for_updates(silent=False)
            # Deve chiamare perform_auto_update con il percorso di RETE
            mock_perform.assert_called_once_with("\\\\path\\\\setup.exe")

    @patch("app_updater.get_metadata_from_network")
    @patch("app_updater.get_metadata_from_web")
    @patch("app_updater.QMessageBox.question")
    @patch("app_updater.version")
    def test_check_for_updates_web_newer(self, mock_ver, mock_quest, mock_web, mock_net):
        """Test that web update is chosen if it's newer than network."""
        mock_ver.__version__ = "1.0.0"

        mock_net.return_value = {"version": "2.0.0", "url": "\\\\path\\\\setup.exe", "source": "Rete Locale"}
        mock_web.return_value = {"version": "2.1.0", "url": "http://web/setup.exe", "source": "Web"}

        from PySide6.QtWidgets import QMessageBox
        mock_quest.return_value = QMessageBox.StandardButton.Yes

        with patch("app_updater.perform_auto_update") as mock_perform:
            app_updater.check_for_updates(silent=False)
            # Deve chiamare perform_auto_update con l'URL WEB perché 2.1.0 > 2.0.0
            mock_perform.assert_called_once_with("http://web/setup.exe")

    @patch("app_updater.Path.exists")
    @patch("app_updater.version")
    def test_get_metadata_from_network_success(self, mock_ver, mock_exists):
        """Test retrieving metadata from network share."""
        mock_ver.NETWORK_UPDATE_PATH = "\\\\server\\\\share"
        mock_exists.return_value = True

        mock_data = json.dumps({"version": "2.0.0", "url": "setup.exe"})
        with patch("app_updater.Path.read_text", return_value=mock_data):
            data = app_updater.get_metadata_from_network()
            self.assertEqual(data["version"], "2.0.0")
            self.assertIn("server", data["url"])

    @patch("app_updater.DownloadWorker.start")
    @patch("app_updater.UpdateProgressDialog.show")
    def test_perform_auto_update_starts_worker(self, mock_show, mock_worker_start):
        """Test that perform_auto_update initializes and starts the async worker."""
        with patch("app_updater.QApplication.topLevelWidgets", return_value=[]):
            app_updater.perform_auto_update("http://mock.com/setup.exe")
            mock_worker_start.assert_called_once()

    def test_get_local_setup_path(self):
        """Test local path generation for both UNC and URL."""
        path1 = app_updater.get_local_setup_path("\\\\server\\share\\setup.exe")
        path2 = app_updater.get_local_setup_path("http://web.com/update.exe")
        self.assertTrue(path1.endswith("setup.exe"))
        self.assertTrue(path2.endswith("update.exe"))

if __name__ == "__main__":
    unittest.main()
