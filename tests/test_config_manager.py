import builtins
import contextlib
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

import config_manager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_config_file = "test_config_temp.json"

    def tearDown(self):
        if os.path.exists(self.test_config_file):
            with contextlib.suppress(builtins.BaseException):
                os.remove(self.test_config_file)
        if os.path.exists(self.test_config_file + ".bak"):
            with contextlib.suppress(builtins.BaseException):
                os.remove(self.test_config_file + ".bak")
        if os.path.exists(self.test_config_file + ".tmp"):
            with contextlib.suppress(Exception):
                os.remove(self.test_config_file + ".tmp")

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_load_config_defaults(self, mock_base):
        # Ensure file does not exist
        with patch("os.path.exists", return_value=False):
            config = config_manager.load_config()
            self.assertEqual(config, {})

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_save_and_load_config(self, mock_base):
        test_data = {"key": "value", "classification_rules": [{"name": "test"}]}

        with patch("os.path.dirname", return_value="."):
            config_manager.save_config(test_data)
            self.assertTrue(os.path.exists(self.test_config_file))

            loaded = config_manager.load_config()
            self.assertEqual(loaded["key"], test_data["key"])

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config(self, mock_base):
        # Mock rename and open to trigger failure via OSError
        with patch("config_manager.os.rename") as mock_rename, \
             patch("config_manager.os.remove"), \
             patch("config_manager.os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=OSError("Simulated IO Error")):
            
            config = config_manager.load_config()
            self.assertEqual(config, {})
            self.assertTrue(mock_rename.called)

    @patch("config_manager.get_app_base_dir", return_value="/tmp/fake")
    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config_rename_fail(self, mock_base):
        with open(self.test_config_file, "w") as f:
            f.write("{ invalid")

        # Mock os.rename to raise OSError
        with patch("os.rename", side_effect=OSError("Mock fail")), patch("builtins.print"):
            with patch("os.path.exists", side_effect=lambda x: x == "test_config_temp.json"):
                config = config_manager.load_config()
                self.assertEqual(config, {})

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_atomic_save_failure(self):
        # Test that temp file is cleaned up if rename fails
        test_data = {"key": "value"}

        with patch("os.path.dirname", return_value="."):
            with patch("os.replace", side_effect=OSError("Rename Fail")):
                with self.assertRaises(OSError):
                    config_manager.save_config(test_data)

                # Temp file should be removed by exception handler
                self.assertFalse(os.path.exists(self.test_config_file + ".tmp"))


if __name__ == "__main__":
    unittest.main()
