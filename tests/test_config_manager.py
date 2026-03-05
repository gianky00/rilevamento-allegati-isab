import builtins
import contextlib
import os
import unittest
from unittest.mock import patch

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

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_load_config_defaults(self):
        # Ensure file does not exist
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)

        config = config_manager.load_config()
        self.assertEqual(config, {})

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_save_and_load_config(self):
        test_data = {"key": "value", "classification_rules": []}

        config_manager.save_config(test_data)
        self.assertTrue(os.path.exists(self.test_config_file))

        loaded = config_manager.load_config()
        self.assertEqual(loaded, test_data)

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config(self):
        # Create a corrupted file
        with open(self.test_config_file, "w") as f:
            f.write("{ invalid json")

        # Should not raise, should rename and load default
        config = config_manager.load_config()
        self.assertEqual(config, {})

        # Check if backup was created
        self.assertTrue(os.path.exists(self.test_config_file + ".bak"))

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_corrupted_config_rename_fail(self):
        with open(self.test_config_file, "w") as f:
            f.write("{ invalid")

        # Mock os.rename to raise OSError
        with patch("os.rename", side_effect=OSError("Mock fail")), patch("builtins.print") as mock_print:
            config = config_manager.load_config()
            self.assertEqual(config, {})
            # Check if error printed
            mock_print.assert_called()

    @patch("config_manager.CONFIG_FILE", "test_config_temp.json")
    def test_atomic_save_failure(self):
        # Test that temp file is cleaned up if rename fails
        test_data = {"key": "value"}

        with patch("os.replace", side_effect=OSError("Rename Fail")):
            with self.assertRaises(OSError):
                config_manager.save_config(test_data)

            # Temp file should be removed by exception handler
            self.assertFalse(os.path.exists(self.test_config_file + ".tmp"))


if __name__ == "__main__":
    unittest.main()
