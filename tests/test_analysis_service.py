"""
Unit tests for core/analysis_service.py.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import pymupdf as fitz
from core.analysis_service import AnalysisService, _analyze_single_page_standalone

class TestAnalysisService(unittest.TestCase):
    """Test suite for AnalysisService."""

    @classmethod
    def setUpClass(cls):
        """Create a multi-page test PDF."""
        cls.test_pdf = Path("test_analysis.pdf")
        doc = fitz.open()
        # Page 0: with text "TargetText"
        p1 = doc.new_page()
        p1.insert_text((50, 50), "TargetText")
        # Page 1: empty
        doc.new_page()
        doc.save(str(cls.test_pdf))
        doc.close()

    @classmethod
    def tearDownClass(cls):
        """Cleanup test PDF."""
        if cls.test_pdf.exists():
            cls.test_pdf.unlink()

    def setUp(self):
        """Setup service and mocks."""
        self.rules = [
            {"category_name": "Category1", "keywords": ["TargetText"], "rois": [[0, 0, 200, 200]]}
        ]
        self.mock_ocr = MagicMock()
        self.service = AnalysisService(self.rules, self.mock_ocr)

    def test_analyze_single_page_standalone_fast_path(self):
        """Test detection via native text (Stage 1)."""
        with fitz.open(self.test_pdf) as doc:
            page = doc[0]
            category = _analyze_single_page_standalone(page, self.rules, self.mock_ocr)
            self.assertEqual(category, "Category1")
            self.mock_ocr.scan_image.assert_not_called()

    def test_analyze_single_page_standalone_ocr_path(self):
        """Test detection via OCR (Stage 2)."""
        rules = [{"category_name": "OCR_Cat", "keywords": ["OCR_KW"], "rois": [[0, 0, 100, 100]]}]
        self.mock_ocr.scan_image.return_value = "ocr_kw found"
        
        with fitz.open(self.test_pdf) as doc:
            page = doc[1] 
            category = _analyze_single_page_standalone(page, rules, self.mock_ocr)
            self.assertEqual(category, "OCR_Cat")
            self.mock_ocr.scan_image.assert_called()

    def test_analyze_pdf_sequential(self):
        """Test full PDF analysis in sequential mode."""
        # Force sequential by patching os.cpu_count or total_pages
        with patch("os.cpu_count", return_value=1):
            self.mock_ocr.scan_image.return_value = "" 
            results = self.service.analyze_pdf(str(self.test_pdf))
            self.assertIn("Category1", results)
            self.assertEqual(results["Category1"], [0])

    def test_analyze_pdf_parallel(self):
        """Test parallel analysis path by mocking only the task method."""
        with patch("os.cpu_count", return_value=4):
            # Ensure parallel path is taken by having total_pages > 1 and cpu_count > 1
            with patch.object(self.service, "_analyze_page_task") as mock_task:
                mock_task.side_effect = lambda path, p: (p, "Category1" if p==0 else "sconosciuto")
                
                results = self.service.analyze_pdf(str(self.test_pdf))
                
                self.assertEqual(mock_task.call_count, 2)
                self.assertEqual(results["Category1"], [0])
                self.assertEqual(results["sconosciuto"], [1])

    def test_analyze_pdf_cancel(self):
        """Test cancellation during analysis."""
        def cancel_true(): return True
        with self.assertRaises(InterruptedError):
            self.service.analyze_pdf(str(self.test_pdf), cancel_check=cancel_true)

    def test_wrapper_method(self):
        """Test the _analyze_single_page wrapper."""
        with fitz.open(self.test_pdf) as doc:
            page = doc[0]
            with patch("core.analysis_service._analyze_single_page_standalone") as mock_std:
                mock_std.return_value = "mock_cat"
                res = self.service._analyze_single_page(page)
                self.assertEqual(res, "mock_cat")

if __name__ == "__main__":
    unittest.main()
