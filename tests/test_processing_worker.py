"""
Unit tests for core/processing_worker.py.
"""

import unittest
from unittest.mock import MagicMock, patch
from queue import Queue
from pathlib import Path
from core.processing_worker import PdfProcessingWorker

class TestProcessingWorker(unittest.TestCase):
    """Test suite for PdfProcessingWorker."""

    def setUp(self):
        """Setup worker with mocks."""
        self.log_queue = Queue()
        self.pdf_files = ["test1.pdf", "test2.pdf"]
        self.on_complete = MagicMock()
        self.worker = PdfProcessingWorker(
            self.log_queue, self.pdf_files, "ODC123", {}, self.on_complete
        )

    @patch("core.pdf_processor.process_pdf")
    @patch("pymupdf.open")
    def test_run_success(self, mock_fitz, mock_process):
        """Test successful run of the worker."""
        # Mock process_pdf to return success
        mock_process.return_value = (True, "Success", [{"category": "A", "path": "p1.pdf"}], "moved.pdf")
        
        # Mock fitz for page count
        mock_doc = MagicMock()
        mock_doc.page_count = 5
        mock_fitz.return_value.__enter__.return_value = mock_doc
        
        self.worker._run()
        
        # Verify stats
        self.assertEqual(self.worker.files_processed_count, 2)
        self.assertEqual(self.worker.pages_processed_count, 10)
        self.on_complete.assert_called_with(2, 10, [])
        
        # Check if logs were produced
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())
        
        self.assertTrue(any("FILE 1/2" in str(l) for l in logs))
        self.assertTrue(any("ELABORAZIONE COMPLETATA" in str(l) for l in logs))

    @patch("core.pdf_processor.process_pdf")
    def test_run_cancel(self, mock_process):
        """Test worker cancellation."""
        self.worker.cancel()
        self.worker._run()
        
        # Should not call process_pdf if cancelled at start
        mock_process.assert_not_called()
        self.on_complete.assert_called_once()
        
        logs = []
        while not self.log_queue.empty():
            logs.append(self.log_queue.get())
        self.assertTrue(any("annullata" in str(l) for l in logs))

    @patch("core.pdf_processor.process_pdf")
    def test_unknown_files_detection(self, mock_process):
        """Test that unknown files are correctly identified and reported."""
        # First file has unknown page
        mock_process.side_effect = [
            (True, "OK", [{"category": "sconosciuto", "path": "u1.pdf"}], "source.pdf"),
            (True, "OK", [{"category": "A", "path": "p1.pdf"}], "source2.pdf")
        ]
        
        # We need to mock fitz to avoid actual file opening
        with patch("pymupdf.open", MagicMock()):
            self.worker._run()
            
            # Check callback args for unknown files
            args = self.on_complete.call_args[0]
            unknown_files = args[2]
            self.assertEqual(len(unknown_files), 1)
            self.assertEqual(unknown_files[0]["unknown_path"], "u1.pdf")

if __name__ == "__main__":
    unittest.main()
