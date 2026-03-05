import unittest
from unittest.mock import MagicMock, patch

from core import pdf_processor


class TestPdfProcessor(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tesseract_path": "fake_tesseract.exe",
            "classification_rules": [
                {
                    "category_name": "Invoice",
                    "keywords": ["invoice", "fattura"],
                    "rois": [[0, 0, 100, 100]],
                    "filename_suffix": "inv",
                }
            ],
        }

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_match(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_page.get_text.return_value = ""
        
        mock_pix = MagicMock(width=50, height=50, samples=b"\x00" * 2500)
        mock_page.get_pixmap.return_value = mock_pix
        mock_ocr.return_value = "invoice"

        mock_new_pdf = MagicMock()
        
        # Patch all fitz.open to return our mocks
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, _msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "5400123", self.config)
            self.assertTrue(success, _msg)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["category"], "Invoice")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_no_match(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_page.get_text.return_value = ""
        mock_page.get_pixmap.return_value = MagicMock(width=50, height=50, samples=b"\x00" * 2500)
        mock_ocr.return_value = "random"

        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, _msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ABC", self.config)
            self.assertTrue(success)
            self.assertEqual(files[0]["category"], "sconosciuto")

    @patch("core.pdf_processor.fitz.open")
    def test_process_pdf_bad_tesseract_path(self, mock_fitz):
        config = {"tesseract_path": "invalid_path.exe"}
        with patch("os.path.isfile", return_value=False):
            success, msg, _files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", config)
            self.assertFalse(success)
            self.assertIn("Percorso Tesseract non valido", msg)

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_process_pdf_roi_error_continue(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.side_effect = Exception("Render Fail")
        
        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "sconosciuto")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_move_retry_logic(self, mock_isfile, mock_ocr, mock_fitz_open):
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 0
        mock_fitz_open.return_value = mock_doc

        from core.archive_service import ArchiveService
        with patch("shutil.move", side_effect=[PermissionError("Locked"), PermissionError("Locked"), None]) as mock_move:
            with patch("os.makedirs"):
                with patch("time.sleep"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.path.dirname", return_value="C:/test"):
                            with patch("os.path.basename", side_effect=["dummy.pdf", "test", "dummy.pdf", "dummy.pdf", "dummy.pdf"]):
                                res = ArchiveService.archive_original("dummy.pdf")
                                self.assertIsNotNone(res)
                                self.assertEqual(mock_move.call_count, 3)

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_ocr_rotation_logic(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.rect.width = 500
        mock_page.rect.height = 500
        mock_page.get_text.return_value = ""
        mock_page.get_pixmap.return_value = MagicMock(width=50, height=50, samples=b"\x00" * 2500)
        mock_ocr.side_effect = ["junk", "invoice text"]

        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("shutil.move"), patch("os.path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "Invoice")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("os.path.isfile", return_value=True)
    def test_invalid_roi_coords(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        bad_config = {
            "tesseract_path": "fake",
            "classification_rules": [{"category_name": "Bad", "rois": [[-1, 0, 10, 10]], "keywords": ["key"]}],
        }
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = MagicMock(width=0, height=0)

        mock_new_pdf = MagicMock()
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect

        with patch("os.makedirs"), patch("core.archive_service.ArchiveService.archive_original"):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", bad_config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "sconosciuto")


if __name__ == "__main__":
    unittest.main()
