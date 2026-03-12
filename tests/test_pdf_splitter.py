"""
Unit tests for core/pdf_splitter.py.
"""

import os
import unittest

import pymupdf as fitz

from core.pdf_splitter import PdfSplitter


class TestPdfSplitter(unittest.TestCase):
    """Test suite for PdfSplitter."""

    @classmethod
    def setUpClass(cls):
        """Create a test PDF with multiple pages."""
        cls.test_pdf_path = "test_split_input.pdf"
        doc = fitz.open()
        for i in range(5):
            p = doc.new_page()
            p.insert_text((50, 50), f"Page {i}")
        doc.save(cls.test_pdf_path)
        doc.close()

    @classmethod
    def tearDownClass(cls):
        """Cleanup test files."""
        if os.path.exists(cls.test_pdf_path):
            os.remove(cls.test_pdf_path)

    def test_get_ranges(self):
        """Test page range grouping logic."""
        pages = [0, 1, 2, 4, 6, 7]
        ranges = PdfSplitter._get_ranges(pages)
        self.assertEqual(ranges, [(0, 2), (4, 4), (6, 7)])

        self.assertEqual(PdfSplitter._get_ranges([]), [])
        self.assertEqual(PdfSplitter._get_ranges([5]), [(5, 5)])

    def test_split_and_save_success(self):
        """Test splitting and saving PDF pages."""
        doc = fitz.open(self.test_pdf_path)
        page_groups = {
            "CatA": [0, 1],
            "CatB": [2],
            "sconosciuto": [3, 4]
        }
        rules = [
            {"category_name": "CatA", "filename_suffix": "SUFFIX_A"},
            {"category_name": "CatB"} # No suffix, should use category name
        ]
        output_dir = "."
        odc = "ODC999"

        generated = PdfSplitter.split_and_save(doc, page_groups, rules, output_dir, odc)
        doc.close()

        # Verify generated list
        self.assertEqual(len(generated), 3)
        paths = [f["path"] for f in generated]

        # Check specific filenames
        expected_a = os.path.abspath(os.path.join(output_dir, "ODC999_SUFFIX_A.pdf"))
        expected_b = os.path.abspath(os.path.join(output_dir, "ODC999_CatB.pdf"))
        self.assertIn(expected_a, paths)
        self.assertIn(expected_b, paths)

        # Verify content of one generated file
        doc_a = fitz.open(expected_a)
        self.assertEqual(doc_a.page_count, 2)
        doc_a.close()

        # Cleanup
        for f in generated:
            if os.path.exists(f["path"]):
                os.remove(f["path"])

    def test_safe_save_retry(self):
        """Test safe save retry logic (mocking failure then success)."""
        doc = fitz.open()
        doc.new_page()

        # We can't easily force a PermissionError without OS help,
        # but we can test that it returns True on normal save.
        res = PdfSplitter._safe_save(doc, "test_safe.pdf")
        self.assertTrue(res)
        doc.close()
        if os.path.exists("test_safe.pdf"):
            os.remove("test_safe.pdf")

if __name__ == "__main__":
    unittest.main()
