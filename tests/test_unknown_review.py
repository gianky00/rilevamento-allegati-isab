"""
Unit tests for gui/dialogs/unknown_review.py.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

# Activate testing mode before import
sys._testing = True
from gui.dialogs.unknown_review import UnknownFilesReviewDialog


class TestUnknownReview(unittest.TestCase):
    """Test suite for UnknownFilesReviewDialog logic."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Setup tasks and dialog instance."""
        self.tasks = [
            {"unknown_path": "mock1.pdf", "source_path": "original.pdf", "siblings": []}
        ]

        with patch("gui.dialogs.unknown_review.fitz.open") as mock_fitz, \
             patch("gui.dialogs.unknown_review.UnknownFilesReviewDialog.showMaximized"):

            self.mock_doc = MagicMock()
            self.mock_doc.page_count = 2
            mock_fitz.return_value = self.mock_doc

            self.dialog = UnknownFilesReviewDialog(None, self.tasks, odc="12345")

    def tearDown(self):
        """Cleanup dialog."""
        self.dialog.close()

    def test_initialization(self):
        """Test initialization logic."""
        self.assertEqual(len(self.dialog.review_tasks), 1)
        self.assertIn("File 1/1", self.dialog.lbl_file_info.text())

    @patch("gui.dialogs.unknown_review.fitz.open")
    def test_load_task_next(self, mock_fitz):
        """Test loading next task."""
        new_tasks = [
            {"unknown_path": "f1.pdf"},
            {"unknown_path": "f2.pdf"}
        ]
        self.dialog.review_tasks = new_tasks

        mock_doc2 = MagicMock()
        mock_doc2.page_count = 3
        mock_fitz.return_value = mock_doc2

        self.dialog.load_task(1)
        self.assertEqual(self.dialog.task_index, 1)
        self.assertEqual(len(self.dialog.available_pages), 3)

    @patch("gui.dialogs.unknown_review.SESSION_FILE", "test_session_review.json")
    def test_close_event_saves_session(self):
        """Test session persistence on close."""
        session_path = Path("test_session_review.json")
        if session_path.exists(): session_path.unlink()

        self.dialog.review_tasks = [{"unknown_path": "save_me.pdf"}]
        self.dialog.close()

        self.assertTrue(session_path.exists())
        session_path.unlink()

if __name__ == "__main__":
    unittest.main()
