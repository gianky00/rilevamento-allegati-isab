import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import pymupdf as fitz

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

    def _setup_mocks(self, mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr):
        # Documento principale
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__len__.return_value = 1
        
        # Pagina
        mock_page = MagicMock()
        mock_page.rect = fitz.Rect(0, 0, 1000, 1000)
        mock_page.get_text.return_value = ""
        
        # Pixmap
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 100
        mock_pix.samples = b"\x00" * (100 * 100)
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_doc.load_page.return_value = mock_page
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__.return_value = mock_doc

        # Nuovo documento (per salvataggio)
        mock_new_pdf = MagicMock()
        mock_new_pdf.__enter__.return_value = mock_new_pdf
        
        def fitz_side_effect(*args, **kwargs):
            return mock_doc if args else mock_new_pdf

        mock_fitz_proc.side_effect = fitz_side_effect
        mock_fitz_anal.side_effect = fitz_side_effect
        mock_fitz_split.side_effect = fitz_side_effect
        
        return mock_doc, mock_page, mock_new_pdf

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_process_pdf_match(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        self._setup_mocks(mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr)
        mock_ocr.return_value = "invoice text"
        mock_isfile.return_value = True

        with patch("pathlib.Path.mkdir"), patch("shutil.move"), patch("pathlib.Path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "5400123", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["category"], "Invoice")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_process_pdf_no_match(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        self._setup_mocks(mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr)
        mock_ocr.return_value = "random text"
        mock_isfile.return_value = True

        with patch("pathlib.Path.mkdir"), patch("shutil.move"), patch("pathlib.Path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ABC", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "sconosciuto")

    @patch("core.pdf_processor.fitz.open")
    def test_process_pdf_bad_tesseract_path(self, mock_fitz):
        config = {"tesseract_path": "invalid_path.exe"}
        with patch("pathlib.Path.is_file", return_value=False):
            success, msg, _files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", config)
            self.assertFalse(success)
            self.assertIn("Percorso Tesseract non valido", msg)

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_process_pdf_roi_error_continue(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        _doc, mock_page, _new = self._setup_mocks(mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr)
        mock_page.get_pixmap.side_effect = Exception("Render Fail")
        mock_isfile.return_value = True

        with patch("pathlib.Path.mkdir"), patch("shutil.move"), patch("pathlib.Path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "sconosciuto")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_move_retry_logic(self, mock_isfile, mock_ocr, mock_fitz_open):
        mock_doc = MagicMock()
        mock_doc.page_count = 0
        mock_doc.__len__.return_value = 0
        mock_fitz_open.return_value = mock_doc
        mock_isfile.return_value = True

        from core.archive_service import ArchiveService
        
        with patch("shutil.move", side_effect=[PermissionError("Locked"), PermissionError("Locked"), None]) as mock_move:
            with patch("pathlib.Path.mkdir"), \
                 patch("time.sleep"), \
                 patch("pathlib.Path.exists", return_value=True), \
                 patch("pathlib.Path.resolve", return_value=Path("C:/test/dummy.pdf")):
                
                res = ArchiveService.archive_original("dummy.pdf")
                self.assertIsNotNone(res)
                self.assertEqual(mock_move.call_count, 3)

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_ocr_rotation_logic(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        self._setup_mocks(mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr)
        mock_ocr.side_effect = ["junk", "invoice text"]
        mock_isfile.return_value = True

        with patch("pathlib.Path.mkdir"), patch("shutil.move"), patch("pathlib.Path.exists", return_value=False):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", self.config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "Invoice")

    @patch("core.pdf_processor.fitz.open")
    @patch("core.analysis_service.fitz.open")
    @patch("core.pdf_splitter.fitz.open")
    @patch("core.ocr_engine.pytesseract.image_to_string")
    @patch("pathlib.Path.is_file")
    def test_invalid_roi_coords(self, mock_isfile, mock_ocr, mock_fitz_split, mock_fitz_anal, mock_fitz_proc):
        bad_config = {
            "tesseract_path": "fake",
            "classification_rules": [{"category_name": "Bad", "rois": [[-1, 0, 10, 10]], "keywords": ["key"]}],
        }
        _doc, mock_page, _new = self._setup_mocks(mock_fitz_proc, mock_fitz_anal, mock_fitz_split, mock_ocr)
        mock_isfile.return_value = True
        
        # Pixmap vuoto
        mock_pix = MagicMock()
        mock_pix.width = 0
        mock_pix.height = 0
        mock_page.get_pixmap.return_value = mock_pix

        with patch("pathlib.Path.mkdir"), patch("core.archive_service.ArchiveService.archive_original"):
            success, msg, files, _moved = pdf_processor.process_pdf("dummy.pdf", "ODC", bad_config)
            self.assertTrue(success, msg)
            self.assertEqual(files[0]["category"], "sconosciuto")


if __name__ == "__main__":
    unittest.main()
