import builtins
import contextlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import config_manager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_config_file = "test_config_temp.json"

    def tearDown(self):
        p = Path(self.test_config_file)
        if p.exists():
            with contextlib.suppress(BaseException):
                p.unlink()
        
        pbak = p.with_suffix(p.suffix + ".bak")
        if pbak.exists():
            with contextlib.suppress(BaseException):
                pbak.unlink()
                
        ptmp = p.with_suffix(p.suffix + ".tmp")
        if ptmp.exists():
            with contextlib.suppress(Exception):
                ptmp.unlink()

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_load_config_defaults(self, mock_base):
        # Ensure file does not exist
        with patch("pathlib.Path.exists", return_value=False):
            config = config_manager.load_config()
            self.assertEqual(config, {})

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_save_and_load_config(self, mock_base):
        test_data = {"key": "value", "classification_rules": [{"name": "test"}]}

        config_manager.save_config(test_data)
        self.assertTrue(Path(self.test_config_file).exists())

        loaded = config_manager.load_config()
        self.assertEqual(loaded["key"], test_data["key"])

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config(self, mock_base):
        # Mock rename and open to trigger failure via OSError
        with patch("pathlib.Path.rename") as mock_rename, \
             patch("pathlib.Path.unlink"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.open", side_effect=OSError("Simulated IO Error")):
            
            config = config_manager.load_config()
            self.assertEqual(config, {})
            self.assertTrue(mock_rename.called)

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config_rename_fail(self, mock_base):
        Path(self.test_config_file).write_text("{ invalid", encoding="utf-8")

        # Mock Path.exists to raise OSError
        with patch("pathlib.Path.rename", side_effect=OSError("Mock fail")):
            with patch("pathlib.Path.exists", side_effect=lambda self: self.name == "test_config_temp.json", autospec=True):
                config = config_manager.load_config()
                self.assertEqual(config, {})

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_atomic_save_failure(self):
        # Test that temp file is cleaned up if rename fails
        test_data = {"key": "value"}

        with patch("pathlib.Path.replace", side_effect=OSError("Rename Fail")):
            with self.assertRaises(OSError):
                config_manager.save_config(test_data)

            # Temp file should be removed by exception handler
            self.assertFalse(Path(self.test_config_file + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
