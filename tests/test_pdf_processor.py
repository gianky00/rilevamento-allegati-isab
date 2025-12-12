import unittest
from unittest.mock import patch, MagicMock, mock_open
import pdf_processor

class TestPdfProcessor(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tesseract_path": "fake_tesseract.exe",
            "classification_rules": [
                {
                    "category_name": "Invoice",
                    "keywords": ["invoice", "fattura"],
                    "rois": [[0, 0, 100, 100]],
                    "filename_suffix": "inv"
                }
            ]
        }

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_match(self, mock_isfile, mock_ocr, mock_fitz_open):
        # Mock PDF Document
        mock_doc = MagicMock()
        mock_fitz_open.return_value = mock_doc

        # Mock Page
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_doc.__getitem__.return_value = mock_page

        mock_page.rect.width = 500
        mock_page.rect.height = 500

        # Mock Pixmap for ROI
        mock_pix = MagicMock()
        mock_pix.width = 50
        mock_pix.height = 50
        mock_pix.samples = b'\x00' * (50 * 50)
        mock_page.get_pixmap.return_value = mock_pix

        # Mock OCR result to trigger match
        mock_ocr.return_value = "This is an invoice document."

        # Mock saving
        mock_new_pdf = MagicMock()
        mock_fitz_open.side_effect = [mock_doc, mock_new_pdf] # First call opens input, second opens new

        # Mock os actions
        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False), patch("builtins.print") as mock_print:
             # Add side_effect to fitz.open to handle multiple calls
             # 1. Main PDF
             # 2. New PDF for saving
             mock_fitz_open.side_effect = None
             mock_fitz_open.return_value = mock_doc

             def fitz_side_effect(*args, **kwargs):
                 if args:
                     return mock_doc
                 return mock_new_pdf

             mock_fitz_open.side_effect = fitz_side_effect

             success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "5400123", self.config)

             self.assertTrue(success)
             self.assertEqual(len(files), 1)
             self.assertIn("Invoice", files[0]['category'])

             # Verify saved filename
             saved_path = files[0]['path']
             self.assertTrue(saved_path.endswith("5400123_inv.pdf"))

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_no_match(self, mock_isfile, mock_ocr, mock_fitz_open):
        # Mock PDF Document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__iter__.return_value = iter([mock_page])

        mock_page.rect.width = 500
        mock_page.rect.height = 500

        mock_pix = MagicMock()
        mock_pix.width = 50
        mock_pix.height = 50
        mock_pix.samples = b'\x00' * (50 * 50)
        mock_page.get_pixmap.return_value = mock_pix

        # Mock OCR result to fail match
        mock_ocr.return_value = "random text"

        mock_new_pdf = MagicMock()

        def fitz_side_effect(*args, **kwargs):
             if args:
                 return mock_doc
             return mock_new_pdf
        mock_fitz_open.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
             success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ABC", self.config)

             self.assertTrue(success)
             self.assertEqual(len(files), 1)
             self.assertEqual(files[0]['category'], "sconosciuto")
             self.assertTrue(files[0]['path'].endswith("ABC_.pdf"))

    @patch("pdf_processor.fitz.open")
    def test_process_pdf_bad_tesseract_path(self, mock_fitz):
        config = {"tesseract_path": "invalid_path.exe"}
        with patch("os.path.isfile", return_value=False):
            success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ODC", config)
            self.assertFalse(success)
            self.assertIn("Tesseract non è configurato", msg)

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_roi_error_continue(self, mock_isfile, mock_ocr, mock_fitz_open):
        # Test error inside ROI loop should continue to next ROI/Rule
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_fitz_open.return_value = mock_doc

        # Mock get_pixmap raising exception
        mock_page.get_pixmap.side_effect = Exception("Render Fail")

        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
             if args:
                 return mock_doc
             return mock_new_pdf
        mock_fitz_open.side_effect = fitz_side_effect

        # Config with one rule
        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)

            # Should finish successfully (categorized as unknown because ROI failed)
            self.assertTrue(success)
            self.assertEqual(files[0]['category'], "sconosciuto")

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_move_retry_logic(self, mock_isfile, mock_ocr, mock_fitz_open):
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 0 # Empty doc for speed
        mock_doc.__iter__.return_value = iter([])
        mock_fitz_open.return_value = mock_doc

        # Mock shutil.move to fail twice then succeed
        with patch("os.makedirs"), patch("os.path.exists", return_value=False):
            with patch("shutil.move", side_effect=[PermissionError("Locked"), PermissionError("Locked"), None]) as mock_move:
                with patch("time.sleep") as mock_sleep:
                    success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)

                    self.assertTrue(success)
                    self.assertEqual(mock_move.call_count, 3)
                    self.assertEqual(mock_sleep.call_count, 2)

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_ocr_rotation_logic(self, mock_isfile, mock_ocr, mock_fitz_open):
        # Setup: Page with one ROI
        # OCR fails on first attempt (0 deg), succeeds on second (-90 deg)
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_fitz_open.return_value = mock_doc

        mock_page.get_pixmap.return_value = MagicMock(width=50, height=50, samples=b'\x00'*2500)

        # Side effect for OCR: first call fails match, second succeeds
        mock_ocr.side_effect = ["junk", "invoice text"]

        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
             if args: return mock_doc
             return mock_new_pdf
        mock_fitz_open.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)

            self.assertTrue(success)
            self.assertIn("Invoice", files[0]['category'])
            self.assertEqual(mock_ocr.call_count, 2)

    @patch("pdf_processor.fitz.open")
    @patch("pdf_processor.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_invalid_roi_coords(self, mock_isfile, mock_ocr, mock_fitz_open):
        # Config with invalid ROI
        bad_config = {
            "tesseract_path": "fake",
            "classification_rules": [{"category_name": "Bad", "rois": [[-1, 0, 10, 10]], "keywords": ["key"]}]
        }
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_fitz_open.return_value = mock_doc

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, msg, files, moved = pdf_processor.process_pdf("dummy.pdf", "ODC", bad_config)

            # Should ignore invalid ROI and end up as unknown
            self.assertTrue(success)
            self.assertEqual(files[0]['category'], "sconosciuto")
            mock_page.get_pixmap.assert_not_called()

if __name__ == "__main__":
    unittest.main()
