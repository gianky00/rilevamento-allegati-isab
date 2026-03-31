"""
Unit tests for license_validator.py.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from license_validator import derive_license_key, get_hardware_id, get_license_info, verify_license


class TestLicenseValidator(unittest.TestCase):
    """Test suite for license validation logic."""

    def setUp(self):
        """Setup temporary license files."""
        self.test_dir = Path("temp_license_test")
        self.test_dir.mkdir(exist_ok=True)

        self.paths = {
            "sys_dir": self.test_dir,
            "local_dir": self.test_dir,
            "sys_config": self.test_dir / "config.dat",
            "local_config": self.test_dir / "config_local.dat",
            "token": self.test_dir / "validity.token"
        }

        # Per i test, usiamo un HWID fisso e deriviamo la chiave
        self.test_hwid = "TEST-HWID-123"
        self.dynamic_key = derive_license_key(self.test_hwid)
        self.cipher = Fernet(self.dynamic_key)

    def tearDown(self):
        """Cleanup temporary files."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.check_output")
    def test_get_hardware_id_windows(self, mock_sub, mock_sys):
        """Test hardware ID retrieval on Windows with normalization."""
        # Il comando powershell restituisce il seriale con spazi/punti
        mock_sub.return_value = b"SerialNumber\n  XYZ.123  \n"
        hwid = get_hardware_id()
        # Normalizzazione: rimuove '.' e trimma/maiuscolo
        self.assertEqual(hwid, "XYZ123")

    @patch("license_validator._get_license_paths")
    @patch("license_validator.get_hardware_id")
    def test_get_license_info_valid(self, mock_hwid, mock_paths):
        """Test decrypting license info with dynamic key."""
        mock_hwid.return_value = self.test_hwid
        mock_paths.return_value = self.paths

        data = {"Cliente": "Test", "Hardware ID": self.test_hwid}
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.paths["sys_config"].write_bytes(encrypted)

        info = get_license_info()
        self.assertIsNotNone(info)
        self.assertEqual(info["Cliente"], "Test")

    @patch("license_validator._get_license_paths")
    @patch("license_validator.get_hardware_id")
    def test_verify_license_full_flow(self, mock_hwid, mock_paths):
        """Test the full license verification process."""
        mock_hwid.return_value = self.test_hwid
        mock_paths.return_value = self.paths

        # 1. Create encrypted config
        data = {
            "Cliente": "ACME",
            "Hardware ID": self.test_hwid,
            "Scadenza Licenza": "01/01/2099"
        }
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.paths["sys_config"].write_bytes(encrypted)

        valid, msg = verify_license()
        self.assertTrue(valid)
        self.assertIn("ACME", msg)

    @patch("license_validator._get_license_paths")
    @patch("license_validator.get_hardware_id")
    def test_verify_license_expired(self, mock_hwid, mock_paths):
        """Test verification of an expired license."""
        mock_hwid.return_value = self.test_hwid
        mock_paths.return_value = self.paths

        data = {
            "Cliente": "Test",
            "Hardware ID": self.test_hwid,
            "Scadenza Licenza": "01/01/2020"
        }
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.paths["sys_config"].write_bytes(encrypted)

        valid, msg = verify_license()
        self.assertFalse(valid)
        self.assertIn("SCADUTA", msg)

if __name__ == "__main__":
    unittest.main()
