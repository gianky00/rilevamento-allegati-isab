"""
Unit tests for app_launcher.py.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Setup initial mocks for module import
with patch("app_logger.initialize", return_value="/mock/log.txt"):
    with patch("PySide6.QtWidgets.QApplication", MagicMock()):
        import app_launcher

class TestAppLauncher(unittest.TestCase):
    """Test suite for app_launcher module."""

    @patch("app_launcher.QApplication")
    @patch("gui.widgets.splash_screen.SplashScreen")
    @patch("main.MainApp")
    @patch("license_updater.run_update")
    @patch("license_validator.verify_license")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    def test_run_app_success(self, mock_unlink, mock_exists, mock_verify, mock_update, mock_main, mock_splash, mock_qapp):
        """Test successful application launch flow."""
        mock_exists.return_value = True
        mock_verify.return_value = (True, "OK")
        
        # Mock QApplication instance and clipboard
        mock_instance = mock_qapp.return_value
        mock_qapp.instance.return_value = mock_instance
        
        with patch("PySide6.QtCore.QTimer.singleShot", lambda ms, cb: cb()):
            with patch("sys.exit") as mock_exit:
                app_launcher.run_app()
                
                # Verify calls using the patched module attributes
                self.assertTrue(mock_qapp.called)
                mock_splash.assert_called()
                mock_update.assert_called_once()
                mock_verify.assert_called_once()
                mock_main.assert_called_once()

    @patch("app_launcher.QApplication")
    @patch("gui.widgets.splash_screen.SplashScreen")
    @patch("PySide6.QtWidgets.QMessageBox.critical")
    @patch("license_updater.run_update")
    def test_run_app_license_update_fail(self, mock_update, mock_msg, mock_splash, mock_qapp):
        """Test application behavior when license update fails."""
        mock_update.side_effect = Exception("Update Error")
        
        app_launcher.run_app()
        mock_msg.assert_called()
        mock_splash.return_value.hide.assert_called()

    @patch("app_launcher.QApplication")
    @patch("gui.widgets.splash_screen.SplashScreen")
    @patch("PySide6.QtWidgets.QMessageBox.critical")
    @patch("license_updater.run_update")
    @patch("license_validator.verify_license")
    @patch("license_validator.get_hardware_id", return_value="MOCK-HWID")
    def test_run_app_license_invalid(self, mock_hw, mock_verify, mock_update, mock_msg, mock_splash, mock_qapp):
        """Test application behavior when license validation fails."""
        mock_verify.return_value = (False, "Invalid Key")
        
        # Setup clipboard mock on the app instance
        mock_clipboard = MagicMock()
        mock_instance = mock_qapp.return_value
        mock_instance.clipboard.return_value = mock_clipboard
        
        app_launcher.run_app()
        mock_msg.assert_called()
        mock_splash.return_value.hide.assert_called()
        mock_clipboard.setText.assert_called_with("MOCK-HWID")

    @patch("app_launcher.run_app")
    def test_main_block_app(self, mock_run):
        """Test the main entry point block."""
        with patch("sys.argv", ["app.py"]):
            app_launcher.run_app()
            mock_run.assert_called()

    @patch("roi_utility.run_utility")
    def test_main_block_utility(self, mock_roi):
        """Test launching ROI utility via CLI flag."""
        with patch("sys.argv", ["app.py", "--utility"]):
            import roi_utility
            if "--utility" in sys.argv:
                roi_utility.run_utility()
            mock_roi.assert_called_once()

if __name__ == "__main__":
    unittest.main()
