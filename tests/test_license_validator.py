import unittest
import os
import sys
import json
import datetime
from unittest.mock import patch, MagicMock, mock_open
import license_validator

class TestLicenseValidator(unittest.TestCase):

    @patch("license_validator.get_hardware_id")
    def test_verify_license_invalid_key(self, mock_get_hw_id):
        mock_get_hw_id.return_value = "TEST-HW-ID"

        # Mock reading the license file
        # verify_license first checks os.path.exists for folder/files
        with patch("os.path.exists", side_effect=lambda x: False):
             # Returns False for everything
             is_valid, msg = license_validator.verify_license()
             self.assertFalse(is_valid)
             self.assertIn("Cartella 'Licenza' mancante", msg)

    @patch("license_validator.get_hardware_id")
    def test_verify_license_missing_files(self, mock_get_hw_id):
         # Mock dir exists but files don't
         def exists_side_effect(path):
             if "Licenza" in path and not path.endswith(".dat") and not path.endswith(".json"):
                 return True # Dir exists
             return False # Files don't

         with patch("os.path.exists", side_effect=exists_side_effect):
             is_valid, msg = license_validator.verify_license()
             self.assertFalse(is_valid)
             self.assertIn("File di licenza danneggiati", msg)

    def test_get_license_info_no_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("os.path.exists", return_value=False):
                info = license_validator.get_license_info()
                self.assertIsNone(info)

    # New tests for Coverage

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.check_output")
    def test_get_hardware_id_windows(self, mock_sub, mock_sys):
        mock_sub.return_value = b"SerialNumber\n  DISK-SERIAL-123  \n"
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "DISK-SERIAL-123")

    @patch("platform.system", return_value="Linux")
    @patch("subprocess.check_output")
    def test_get_hardware_id_linux_lsblk(self, mock_sub, mock_sys):
        mock_sub.return_value = b"LINUX-SERIAL-123"
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "LINUX-SERIAL-123")

    @patch("platform.system", return_value="Linux")
    @patch("subprocess.check_output", side_effect=Exception("No lsblk"))
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="MACHINE-ID-123")
    def test_get_hardware_id_linux_machineid(self, mock_open, mock_exists, mock_sub, mock_sys):
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "MACHINE-ID-123")

    @patch("platform.system", return_value="UnknownOS")
    def test_get_hardware_id_unknown(self, mock_sys):
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "UNKNOWN_ID")

    @patch("license_validator._get_license_paths")
    @patch("license_validator._calculate_sha256")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"config.dat": "valid_hash", "pyarmor.rkey": "valid_key_hash"}')
    @patch("license_validator.get_license_info")
    @patch("license_validator.get_hardware_id", return_value="HWID")
    def test_verify_license_success(self, mock_hw, mock_info, mock_open, mock_exists, mock_sha, mock_paths):
        mock_paths.return_value = {
            "dir": "Licenza",
            "config": "Licenza/config.dat",
            "rkey": "Licenza/pyarmor.rkey",
            "manifest": "Licenza/manifest.json"
        }
        mock_sha.side_effect = ["valid_hash", "valid_key_hash"] # For config and rkey

        mock_info.return_value = {
            "Hardware ID": "HWID",
            "Scadenza Licenza": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
            "Cliente": "TestUser"
        }

        is_valid, msg = license_validator.verify_license()
        self.assertTrue(is_valid)
        self.assertIn("Licenza Valida", msg)

    @patch("license_validator._get_license_paths")
    @patch("license_validator._calculate_sha256")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"config.dat": "valid_hash"}')
    def test_verify_license_bad_hash(self, mock_open, mock_exists, mock_sha, mock_paths):
        mock_paths.return_value = {"dir": "d", "config": "c", "manifest": "m"}
        mock_sha.return_value = "invalid_hash"

        is_valid, msg = license_validator.verify_license()
        self.assertFalse(is_valid)
        self.assertIn("Integrità licenza compromessa", msg)

    @patch("license_validator._get_license_paths")
    @patch("license_validator._calculate_sha256")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"config.dat": "valid_hash"}')
    @patch("license_validator.get_license_info")
    @patch("license_validator.get_hardware_id", return_value="WRONG_HWID")
    def test_verify_license_bad_hwid(self, mock_hw, mock_info, mock_open, mock_exists, mock_sha, mock_paths):
        mock_paths.return_value = {"dir": "d", "config": "c", "manifest": "m"}
        mock_sha.return_value = "valid_hash"

        mock_info.return_value = {
            "Hardware ID": "CORRECT_HWID",
            "Scadenza Licenza": "01/01/2099"
        }

        is_valid, msg = license_validator.verify_license()
        self.assertFalse(is_valid)
        self.assertIn("Hardware ID non valido", msg)

    @patch("license_validator._get_license_paths")
    @patch("license_validator._calculate_sha256")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"config.dat": "valid_hash"}')
    @patch("license_validator.get_license_info")
    @patch("license_validator.get_hardware_id", return_value="HWID")
    def test_verify_license_expired(self, mock_hw, mock_info, mock_open, mock_exists, mock_sha, mock_paths):
        mock_paths.return_value = {"dir": "d", "config": "c", "manifest": "m"}
        mock_sha.return_value = "valid_hash"

        mock_info.return_value = {
            "Hardware ID": "HWID",
            "Scadenza Licenza": "01/01/2000" # Expired
        }

        is_valid, msg = license_validator.verify_license()
        self.assertFalse(is_valid)
        self.assertIn("Licenza SCADUTA", msg)

if __name__ == "__main__":
    unittest.main()
