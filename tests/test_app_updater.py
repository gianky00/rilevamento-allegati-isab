"""
Unit tests for app_updater.py.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open
import requests
from app_updater import check_for_updates, perform_auto_update

class TestAppUpdater(unittest.TestCase):
    """Test suite for app_updater module."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for widget tests."""
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    @patch("app_updater.requests.get")
    @patch("app_updater.QMessageBox.question")
    @patch("app_updater.version")
    def test_check_for_updates_available(self, mock_ver, mock_quest, mock_get):
        """Test update check when a new version is available."""
        mock_ver.__version__ = "1.0.0"
        mock_ver.UPDATE_URL = "http://mock.com/version.json"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2.0.0", "url": "http://mock.com/setup.exe"}
        mock_get.return_value = mock_response
        
        from PySide6.QtWidgets import QMessageBox
        mock_quest.return_value = QMessageBox.StandardButton.Yes
        
        with patch("app_updater.perform_auto_update") as mock_perform:
            check_for_updates(silent=False)
            mock_perform.assert_called_once()

    @patch("app_updater.requests.get")
    @patch("app_updater.version")
    def test_check_for_updates_already_updated(self, mock_ver, mock_get):
        """Test update check when already on latest version."""
        mock_ver.__version__ = "2.0.0"
        mock_ver.UPDATE_URL = "http://mock.com/version.json"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2.0.0"}
        mock_get.return_value = mock_response
        
        with patch("app_updater.QMessageBox.information") as mock_info:
            check_for_updates(silent=False)
            mock_info.assert_called()

    @patch("app_updater.requests.get")
    @patch("app_updater.QMessageBox.critical")
    def test_perform_auto_update_failure(self, mock_crit, mock_get):
        """Test auto update behavior on error, mocking UI components to avoid C++ conflicts."""
        mock_get.side_effect = Exception("Download failed")
        
        with patch("app_updater.QDialog"), \
             patch("app_updater.QVBoxLayout"), \
             patch("app_updater.QLabel"), \
             patch("app_updater.QProgressBar"):
            perform_auto_update("http://mock.com/fail.exe")
            mock_crit.assert_called()

    @patch("app_updater.requests.get")
    @patch("app_updater.subprocess.Popen")
    def test_perform_auto_update_success(self, mock_popen, mock_get):
        """Test successful auto update flow with full UI mocking."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_response
        
        # Mocking all UI components used inside perform_auto_update
        with patch("app_updater.QDialog"), \
             patch("app_updater.QVBoxLayout"), \
             patch("app_updater.QLabel"), \
             patch("app_updater.QProgressBar"), \
             patch("app_updater.QApplication"):
            
            mock_file = MagicMock()
            with patch("builtins.open", return_value=mock_file):
                mock_file.__enter__.return_value = mock_file
                with patch("app_updater.sys.exit") as mock_exit:
                    perform_auto_update("http://mock.com/setup.exe")
                    
                    self.assertTrue(mock_file.write.called)
                    mock_popen.assert_called()
                    mock_exit.assert_called_with(0)

if __name__ == "__main__":
    unittest.main()
