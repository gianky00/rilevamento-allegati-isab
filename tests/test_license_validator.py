"""
Unit tests for license_validator.py.
"""

import unittest
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import date
from cryptography.fernet import Fernet
from license_validator import (
    _calculate_sha256, 
    get_hardware_id, 
    get_license_info, 
    verify_license, 
    LICENSE_SECRET_KEY
)

class TestLicenseValidator(unittest.TestCase):
    """Test suite for license validation logic."""

    def setUp(self):
        """Setup temporary license files."""
        self.test_dir = Path("temp_license_test")
        self.test_dir.mkdir(exist_ok=True)
        
        self.paths = {
            "dir": str(self.test_dir),
            "config": str(self.test_dir / "config.dat"),
            "manifest": str(self.test_dir / "manifest.json"),
            "rkey": str(self.test_dir / "pyarmor.rkey")
        }
        
        # Helper to create a valid encrypted config
        self.cipher = Fernet(LICENSE_SECRET_KEY)

    def tearDown(self):
        """Cleanup temporary files."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_calculate_sha256(self):
        """Test SHA256 calculation."""
        test_file = self.test_dir / "hash_me.txt"
        test_file.write_text("hello world", encoding="utf-8")
        h = _calculate_sha256(test_file)
        # sha256 of "hello world"
        self.assertEqual(h, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.check_output")
    def test_get_hardware_id_windows(self, mock_sub, mock_sys):
        """Test hardware ID retrieval on Windows."""
        mock_sub.return_value = b"SerialNumber\nXYZ-123\n"
        hwid = get_hardware_id()
        self.assertEqual(hwid, "XYZ-123")

    @patch("license_validator._get_license_paths")
    def test_get_license_info_valid(self, mock_paths):
        """Test decrypting license info."""
        mock_paths.return_value = self.paths
        data = {"Cliente": "Test", "Hardware ID": "HW1"}
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        Path(self.paths["config"]).write_bytes(encrypted)
        
        info = get_license_info()
        self.assertEqual(info["Cliente"], "Test")

    @patch("license_validator._get_license_paths")
    @patch("license_validator.get_hardware_id")
    def test_verify_license_full_flow(self, mock_hwid, mock_paths):
        """Test the full license verification process."""
        mock_paths.return_value = self.paths
        mock_hwid.return_value = "HW123"
        
        # 1. Create encrypted config
        data = {"Cliente": "ACME", "Hardware ID": "HW123", "Scadenza Licenza": "01/01/2099"}
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        Path(self.paths["config"]).write_bytes(encrypted)
        
        # 2. Create manifest with correct hash
        config_hash = _calculate_sha256(self.paths["config"])
        manifest = {"config.dat": config_hash}
        Path(self.paths["manifest"]).write_text(json.dumps(manifest))
        
        valid, msg = verify_license()
        self.assertTrue(valid)
        self.assertIn("ACME", msg)

    @patch("license_validator._get_license_paths")
    def test_verify_license_expired(self, mock_paths):
        """Test verification of an expired license."""
        mock_paths.return_value = self.paths
        data = {"Cliente": "Test", "Hardware ID": "HW1", "Scadenza Licenza": "01/01/2020"}
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        Path(self.paths["config"]).write_bytes(encrypted)
        
        # Fake HWID to match
        with patch("license_validator.get_hardware_id", return_value="HW1"):
            # Update manifest
            config_hash = _calculate_sha256(self.paths["config"])
            Path(self.paths["manifest"]).write_text(json.dumps({"config.dat": config_hash}))
            
            valid, msg = verify_license()
            self.assertFalse(valid)
            self.assertIn("SCADUTA", msg)

if __name__ == "__main__":
    unittest.main()
