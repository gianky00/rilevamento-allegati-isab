"""
Unit tests for core/pdf_processor.py.
"""

import unittest
from unittest.mock import patch

from core.pdf_processor import process_pdf


class TestPdfProcessor(unittest.TestCase):
    """Test suite for process_pdf orchestrator."""

    def setUp(self):
        """Setup common config and paths."""
        self.config = {
            "tesseract_path": "mock_tesseract.exe",
            "classification_rules": []
        }
        self.pdf_path = "test.pdf"
        self.odc = "ODC123"

    @patch("core.pdf_processor.Path.is_file")
    def test_process_pdf_invalid_tesseract(self, mock_is_file):
        """Test failure when Tesseract path is invalid."""
        mock_is_file.return_value = False
        success, msg, _gen, _moved = process_pdf(self.pdf_path, self.odc, self.config)
        self.assertFalse(success)
        self.assertIn("Percorso Tesseract non valido", msg)

    @patch("core.pdf_processor.OcrEngine")
    @patch("core.pdf_processor.AnalysisService")
    @patch("core.pdf_processor.PdfSplitter")
    @patch("core.pdf_processor.ArchiveService")
    @patch("core.pdf_processor.fitz.open")
    @patch("core.pdf_processor.Path.is_file")
    def test_process_pdf_success(self, mock_is_file, mock_fitz, mock_archive, mock_splitter, mock_analyzer, mock_ocr):
        """Test successful end-to-end processing flow."""
        mock_is_file.return_value = True # Tesseract exists

        # Mock Analyzer
        mock_analyzer_inst = mock_analyzer.return_value
        mock_analyzer_inst.analyze_pdf.return_value = {"Cat1": [0, 1]}
        mock_analyzer_inst.rules = []

        # Mock Splitter
        mock_splitter.split_and_save.return_value = [{"path": "out.pdf", "category": "Cat1"}]

        # Mock Archive
        mock_archive.archive_original.return_value = "ORIGINALI/test.pdf"

        success, msg, gen, moved = process_pdf(self.pdf_path, self.odc, self.config)

        self.assertTrue(success)
        self.assertEqual(msg, "Successo")
        self.assertEqual(len(gen), 1)
        self.assertEqual(moved, "ORIGINALI/test.pdf")

        mock_analyzer_inst.analyze_pdf.assert_called_once()
        mock_splitter.split_and_save.assert_called_once()
        mock_archive.archive_original.assert_called_once()

    def test_process_pdf_cancel(self):
        """Test immediate cancellation."""
        def cancel_true():
            """Return True to simulate immediate cancellation."""
            return True
        success, msg, _gen, _moved = process_pdf(self.pdf_path, self.odc, self.config, cancel_check=cancel_true)
        self.assertFalse(success)
        self.assertEqual(msg, "Annullato")

if __name__ == "__main__":
    unittest.main()
