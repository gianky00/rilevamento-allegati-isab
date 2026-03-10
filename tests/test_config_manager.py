"""
Unit tests for config_manager.py.
"""

import unittest
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import config_manager

class TestConfigManager(unittest.TestCase):
    """Test suite for config loading and saving."""

    def setUp(self):
        """Setup temporary config file path."""
        self.test_dir = Path("temp_config_test")
        self.test_dir.mkdir(exist_ok=True)
        self.config_file = self.test_dir / "config.json"
        
        # Patch the global constant in config_manager
        self.patcher = patch("config_manager.CONFIG_FILE", str(self.config_file))
        self.patcher.start()

    def tearDown(self):
        """Cleanup temporary files."""
        self.patcher.stop()
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_config_success(self):
        """Test saving configuration to file."""
        data = {"key": "value", "rules": [1, 2]}
        config_manager.save_config(data)
        
        self.assertTrue(self.config_file.exists())
        with open(self.config_file, encoding="utf-8") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["key"], "value")

    def test_load_config_existing(self):
        """Test loading existing configuration."""
        data = {"classification_rules": [{"name": "rule1"}]}
        self.config_file.write_text(json.dumps(data), encoding="utf-8")
        
        loaded = config_manager.load_config()
        self.assertEqual(len(loaded["classification_rules"]), 1)

    def test_load_config_corrupt_backup(self):
        """Test that corrupt config is backed up and skipped."""
        self.config_file.write_text("invalid json", encoding="utf-8")
        
        loaded = config_manager.load_config()
        self.assertEqual(loaded, {})
        
        # Check if backup was created
        backup = self.config_file.with_suffix(".json.bak")
        self.assertTrue(backup.exists())

    @patch("config_manager.get_app_base_dir")
    def test_load_config_fallback_to_local(self, mock_base):
        """Test fallback to local template when APPDATA is empty."""
        # Setup local template
        local_dir = self.test_dir / "app_base"
        local_dir.mkdir()
        local_config = local_dir / "config.json"
        local_data = {"classification_rules": [{"name": "template"}], "setting": "default"}
        local_config.write_text(json.dumps(local_data), encoding="utf-8")
        
        mock_base.return_value = str(local_dir)
        
        # APPDATA config doesn't exist yet
        loaded = config_manager.load_config()
        
        self.assertEqual(len(loaded["classification_rules"]), 1)
        self.assertEqual(loaded["setting"], "default")

if __name__ == "__main__":
    unittest.main()
