import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
import config_manager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_config_file = "test_config_temp.json"

    def tearDown(self):
        if os.path.exists(self.test_config_file):
            try:
                os.remove(self.test_config_file)
            except:
                pass
        if os.path.exists(self.test_config_file + ".bak"):
            try:
                os.remove(self.test_config_file + ".bak")
            except:
                pass

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
        with patch("os.rename", side_effect=OSError("Mock fail")):
            with patch("builtins.print") as mock_print:
                config = config_manager.load_config()
                self.assertEqual(config, {})
                # Check if error printed
                mock_print.assert_called()

    def test_get_config_path_frozen(self):
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, 'executable', '/frozen/path/app'):
                path = config_manager.get_config_path()
                self.assertEqual(path, os.path.join('/frozen/path', 'config.json'))

    def test_get_config_path_normal(self):
         with patch.object(sys, 'frozen', False, create=True):
             # When not frozen, it uses __file__
             # We can't easily mock __file__ directly on the module once imported without reload,
             # but we can rely on os.path.dirname logic being called.
             path = config_manager.get_config_path()
             self.assertTrue(path.endswith("config.json"))

if __name__ == "__main__":
    unittest.main()
