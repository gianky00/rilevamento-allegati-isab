"""
Unit tests for core/ocr_engine.py.
"""

import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
from core.ocr_engine import OcrEngine

class TestOcrEngine(unittest.TestCase):
    """Test suite for OcrEngine."""

    def setUp(self):
        """Setup OcrEngine and a dummy image."""
        self.engine = OcrEngine(tesseract_path="/mock/tesseract")
        self.dummy_img = Image.new("RGB", (100, 100), color="white")

    def test_initialization(self):
        """Test engine initialization and tesseract path setup."""
        with patch("pytesseract.pytesseract.tesseract_cmd", ""):
            engine = OcrEngine(tesseract_path="/path/to/tess")
            import pytesseract
            self.assertEqual(pytesseract.pytesseract.tesseract_cmd, "/path/to/tess")

    def test_get_binary(self):
        """Test image binarization."""
        # Create a grey image
        img = Image.new("L", (10, 10), color=128)
        binary = OcrEngine.get_binary(img)
        self.assertEqual(binary.mode, "1")

    def test_get_contrast(self):
        """Test autocontrast application."""
        img = Image.new("L", (10, 10), color=100)
        # We just check it returns an image and doesn't crash
        result = OcrEngine.get_contrast(img)
        self.assertIsInstance(result, Image.Image)

    @patch("pytesseract.image_to_string")
    def test_scan_image_success(self, mock_ocr):
        """Test basic image scanning."""
        mock_ocr.return_value = "Detected Text"
        result = self.engine.scan_image(self.dummy_img)
        self.assertEqual(result, "detected text")
        mock_ocr.assert_called_once()

    @patch("pytesseract.image_to_string")
    def test_scan_image_failure(self, mock_ocr):
        """Test scan_image behavior on OCR error."""
        mock_ocr.side_effect = Exception("OCR Error")
        result = self.engine.scan_image(self.dummy_img)
        self.assertEqual(result, "")

    @patch("pytesseract.image_to_string")
    def test_robust_scan_match(self, mock_ocr):
        """Test robust scan finding a keyword in transformed steps."""
        # First call fails, second (rotated) succeeds
        mock_ocr.side_effect = ["nothing", "found target here", "etc"]
        
        found, keyword = self.engine.robust_scan(self.dummy_img, ["target", "other"])
        
        self.assertTrue(found)
        self.assertEqual(keyword, "target")
        # Should have called at least twice
        self.assertGreaterEqual(mock_ocr.call_count, 2)

    @patch("pytesseract.image_to_string")
    def test_robust_scan_no_match(self, mock_ocr):
        """Test robust scan when no keywords are found in any step."""
        mock_ocr.return_value = "no match here"
        
        found, keyword = self.engine.robust_scan(self.dummy_img, ["target"])
        
        self.assertFalse(found)
        self.assertEqual(keyword, "")

if __name__ == "__main__":
    unittest.main()
