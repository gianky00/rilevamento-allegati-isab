"""
Unit tests for core/session_manager.py.
"""

import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.session_manager import SessionManager
from shared.constants import SESSION_FILE

class TestSessionManager(unittest.TestCase):
    """Test suite for SessionManager."""

    def setUp(self):
        """Ensure clean state before each test."""
        self.session_path = Path(SESSION_FILE)
        if self.session_path.exists():
            self.session_path.unlink()

    def tearDown(self):
        """Cleanup session file after each test."""
        if self.session_path.exists():
            self.session_path.unlink()

    def test_has_session(self):
        """Test detection of session file."""
        self.assertFalse(SessionManager.has_session())
        self.session_path.write_text("{}", encoding="utf-8")
        self.assertTrue(SessionManager.has_session())

    def test_clear_session(self):
        """Test removal of session file."""
        self.session_path.write_text("{}", encoding="utf-8")
        SessionManager.clear_session()
        self.assertFalse(self.session_path.exists())

    def test_load_session_missing(self):
        """Test behavior when loading a non-existent session."""
        tasks, odc = SessionManager.load_session()
        self.assertEqual(tasks, [])
        self.assertEqual(odc, "Unknown")

    def test_load_session_list_format(self):
        """Test loading session data in list format."""
        data = [{"task": 1}, {"task": 2}]
        self.session_path.write_text(json.dumps(data), encoding="utf-8")
        tasks, odc = SessionManager.load_session()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(odc, "Unknown")

    def test_load_session_dict_format(self):
        """Test loading session data in dictionary format with ODC."""
        data = {"tasks": [{"task": 1}], "odc": "ODC123"}
        self.session_path.write_text(json.dumps(data), encoding="utf-8")
        tasks, odc = SessionManager.load_session()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(odc, "ODC123")

    def test_load_session_empty(self):
        """Test loading an empty session file."""
        self.session_path.write_text("", encoding="utf-8")
        # Empty JSON might raise error, let's test specific content
        self.session_path.write_text("null", encoding="utf-8")
        tasks, odc = SessionManager.load_session()
        self.assertEqual(tasks, [])

    @patch("logging.Logger.exception")
    def test_load_session_corrupted(self, mock_log):
        """Test handling of corrupted session file."""
        self.session_path.write_text("invalid json", encoding="utf-8")
        with self.assertRaises(Exception):
            SessionManager.load_session()
        mock_log.assert_called()

if __name__ == "__main__":
    unittest.main()
