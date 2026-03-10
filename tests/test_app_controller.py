"""
Unit tests for core/app_controller.py.
"""

import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QCoreApplication
from core.app_controller import AppController

class TestAppController(unittest.TestCase):
    """Test suite for AppController."""

    @classmethod
    def setUpClass(cls):
        """Initialize QCoreApplication for Signal/Slot tests."""
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        """Setup controller and common mocks."""
        # Correcting patch path for RuleService to match how it's imported in app_controller.py
        with patch("config_manager.load_config", return_value={"global_docs": 10, "global_pages": 100}):
            with patch("core.app_controller.RuleService"):
                self.controller = AppController()

    def tearDown(self):
        """Cleanup controller."""
        self.controller._log_timer.stop()

    def test_load_settings(self):
        """Test settings loading and service initialization."""
        with patch("config_manager.load_config", return_value={"test": "val"}) as mock_load:
            with patch("core.app_controller.RuleService") as mock_rules:
                mock_signal = MagicMock()
                self.controller.rules_updated.connect(mock_signal)
                
                self.controller.load_settings()
                
                mock_load.assert_called()
                mock_rules.assert_called_with({"test": "val"})
                mock_signal.assert_called_once()

    @patch("license_validator.get_license_info")
    @patch("license_validator.get_hardware_id")
    @patch("config_manager.load_config")
    def test_check_license(self, mock_load, mock_hwid, mock_lic):
        """Test license check signal emission."""
        mock_load.return_value = {"last_access": "yesterday"}
        mock_lic.return_value = {"Cliente": "TestUser", "Scadenza Licenza": "2025-01-01"}
        mock_hwid.return_value = "HW-123"
        
        mock_signal = MagicMock()
        self.controller.license_status_updated.connect(mock_signal)
        
        self.controller.check_license()
        
        mock_signal.assert_called_once()
        info = mock_signal.call_args[0][0]
        self.assertEqual(info["cliente"], "TESTUSER")
        self.assertTrue(info["is_valid"])

    @patch("core.file_service.FileService.find_pdfs_in_path")
    def test_set_pdf_files(self, mock_find):
        """Test finding and setting PDF files."""
        mock_find.return_value = ["file1.pdf", "file2.pdf"]
        
        self.controller.set_pdf_files(["C:/temp"])
        self.assertEqual(len(self.controller.pdf_files), 2)
        self.assertIn("file1.pdf", self.controller.pdf_files)

    @patch("core.app_controller.PdfProcessingWorker")
    def test_start_processing(self, mock_worker):
        """Test starting the processing worker."""
        # Ensure we have files, otherwise it returns False
        self.controller.pdf_files = ["test.pdf"]
        
        res = self.controller.start_processing("ODC001")
        
        self.assertTrue(res)
        self.assertTrue(self.controller._is_processing)
        mock_worker.assert_called()
        mock_worker.return_value.start.assert_called_once()

    def test_process_log_queue(self):
        """Test log queue processing and signal emission."""
        mock_signal = MagicMock()
        self.controller.log_received.connect(mock_signal)
        
        # Add items to queue
        self.controller.log_queue.put(("Message 1", "INFO"))
        self.controller.log_queue.put({"action": "update_progress", "value": 50, "text": "Wait"})
        
        mock_progress = MagicMock()
        self.controller.progress_updated.connect(mock_progress)
        
        self.controller._process_log_queue()
        
        mock_signal.assert_any_call("Message 1", "INFO", False)
        mock_progress.assert_any_call(50.0, "Wait", None)

    @patch("core.app_controller.SessionManager.has_session")
    def test_check_for_restore(self, mock_has):
        """Test restore session check signal."""
        mock_has.return_value = True
        mock_signal = MagicMock()
        self.controller.session_status_changed.connect(mock_signal)
        
        self.controller.check_for_restore()
        mock_signal.assert_called_with(True)

if __name__ == "__main__":
    unittest.main()
