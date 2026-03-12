"""
Unit tests for the Unknown Files Review Dialog.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Pre-import optimization
import gui.dialogs.unknown_review

class TestUnknownReview(unittest.TestCase):
    """Test suite for UnknownFilesReviewDialog."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tasks = [{"unknown_path": "test.pdf"}]
        # Set testing flag to avoid complex widget init
        sys._testing = True
        
        # Mock SessionManager to avoid file writes
        with patch("gui.dialogs.unknown_review.SessionManager"):
            from gui.dialogs.unknown_review import UnknownFilesReviewDialog
            self.dialog = UnknownFilesReviewDialog(None, self.tasks, odc="ODC123")

    def tearDown(self):
        self.dialog.close()

    def test_initialization(self):
        """Test basic init and title."""
        self.assertIn("ODC123", self.dialog.windowTitle())
        self.assertEqual(len(self.dialog.review_tasks), 1)

    def test_load_task_next(self):
        """Test task iteration."""
        self.dialog.review_tasks = [{"unknown_path": "f1.pdf"}, {"unknown_path": "f2.pdf"}]
        self.dialog.load_task(0)
        self.assertEqual(self.dialog.task_index, 0)
        
        self.dialog.next_or_close()
        self.assertEqual(self.dialog.task_index, 1)

    def test_close_event_saves_session(self):
        """Test that closing saves session."""
        with patch("gui.dialogs.unknown_review.SessionManager.save_session") as mock_save:
            self.dialog.close()
            mock_save.assert_called_once()

if __name__ == "__main__":
    unittest.main()
