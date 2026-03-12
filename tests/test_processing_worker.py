"""
Unit tests for the background processing worker.
"""

import unittest
from queue import Queue
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

from core.processing_worker import ProcessingWorker


class TestProcessingWorker(unittest.TestCase):
    """Test suite for ProcessingWorker class."""

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize QApplication for signals."""
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        """Setup worker and common mocks."""
        self.log_queue: Queue = Queue()
        self.config = {"tesseract_path": "tess", "pdf_output_path": "out"}
        self.worker = ProcessingWorker(["file1.pdf", "file2.pdf"], "ODC1", self.config, self.log_queue)

    @patch("core.pdf_processor.process_pdf")
    def test_run_success(self, mock_process) -> None:
        """Test successful execution loop."""
        mock_process.return_value = (True, "OK", [], [])
        
        self.worker.run()
        
        # Verify signals and logs
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())

        self.assertTrue(any("FILE 1/2" in str(entry) for entry in logs))
        self.assertTrue(any("ELABORAZIONE COMPLETATA" in str(entry) for entry in logs))

    @patch("core.pdf_processor.process_pdf")
    def test_cancellation(self, mock_process) -> None:
        """Test worker stop mechanism."""
        mock_process.return_value = (True, "OK", [], [])
        self.worker.stop()
        
        self.worker.run()
        
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())
        self.assertTrue(any("annullata" in str(entry) for entry in logs))

    @patch("core.pdf_processor.process_pdf")
    def test_process_failure_handling(self, mock_process) -> None:
        """Test how the worker handles a single file failure."""
        mock_process.return_value = (False, "Error msg", [], [])
        
        self.worker.run()
        
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())
        self.assertTrue(any("ERRORE" in str(entry) for entry in logs))


if __name__ == "__main__":
    unittest.main()
