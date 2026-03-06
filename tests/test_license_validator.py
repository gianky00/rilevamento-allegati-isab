import datetime
import subprocess
import unittest
from unittest.mock import MagicMock, patch

import license_validator


class TestLicenseValidator(unittest.TestCase):
    @patch("license_validator.get_hardware_id")
    def test_verify_license_invalid_key(self, mock_get_hw_id):
        mock_get_hw_id.return_value = "TEST-HW-ID"
        with patch("pathlib.Path.exists", return_value=False):
            is_valid, msg = license_validator.verify_license()
            self.assertFalse(is_valid)
            self.assertIn("Cartella 'Licenza' mancante", msg)

    @patch("license_validator.get_hardware_id")
    def test_verify_license_missing_files(self, mock_get_hw_id):
        mock_get_hw_id.return_value = "ACE4_2E00_951D_4DDA"

        def exists_side_effect(self):
            # Simula che la cartella esiste ma i file no
            return "Licenza" in str(self) and not str(self).endswith(".dat") and not str(self).endswith(".json")

        with patch("pathlib.Path.exists", side_effect=exists_side_effect, autospec=True):
            is_valid, msg = license_validator.verify_license()
            self.assertFalse(is_valid)
            self.assertIn("File di licenza mancanti o danneggiati", msg)

    def test_get_license_info_no_file(self):
        with patch("pathlib.Path.exists", return_value=False):
            info = license_validator.get_license_info()
            self.assertIsNone(info)

    # --- Tests for Hardware ID Fallbacks ---

    @patch("platform.system", return_value="Windows")
    @patch("license_validator.subprocess.check_output")
    def test_get_hardware_id_windows_wmic(self, mock_sub, mock_sys):
        mock_sub.return_value = b"SerialNumber\n  DISK-SERIAL-123  \n"
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "DISK-SERIAL-123")

    @patch("platform.system", return_value="Windows")
    @patch("license_validator.subprocess.check_output")
    def test_get_hardware_id_windows_powershell(self, mock_sub, mock_sys):
        # Patch STARTUPINFO and STARTF_USESHOWWINDOW on the imported module
        with (
            patch("license_validator.subprocess.STARTUPINFO", create=True) as mock_startup,
            patch("license_validator.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
        ):
            mock_si = MagicMock()
            # Ensure dwFlags is an int so |= works
            mock_si.dwFlags = 0
            mock_startup.return_value = mock_si

            def side_effect(*args, **kwargs):
                cmd = args[0]
                if isinstance(cmd, str):
                    raise subprocess.CalledProcessError(1, cmd)
                return b"POWERSHELL-SERIAL-123\n"

            mock_sub.side_effect = side_effect

            hw_id = license_validator.get_hardware_id()
            self.assertEqual(hw_id, "POWERSHELL-SERIAL-123")

    @patch("platform.system", return_value="Windows")
    @patch("license_validator.subprocess.check_output")
    @patch("uuid.getnode", return_value=123456789)
    def test_get_hardware_id_windows_uuid_fallback(self, mock_uuid, mock_sub, mock_sys):
        with (
            patch("license_validator.subprocess.STARTUPINFO", create=True),
            patch("license_validator.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
        ):
            mock_sub.side_effect = subprocess.CalledProcessError(1, "cmd")
            hw_id = license_validator.get_hardware_id()
            self.assertEqual(hw_id, "123456789")

    # --- Other Tests ---

    @patch("platform.system", return_value="Linux")
    @patch("license_validator.subprocess.check_output")
    def test_get_hardware_id_linux_lsblk(self, mock_sub, mock_sys):
        mock_sub.return_value = b"LINUX-SERIAL-123"
        hw_id = license_validator.get_hardware_id()
        self.assertEqual(hw_id, "LINUX-SERIAL-123")

    @patch("license_validator._get_license_paths")
    @patch("license_validator._calculate_sha256")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open")
    @patch("license_validator.get_license_info")
    @patch("license_validator.get_hardware_id", return_value="HWID")
    def test_verify_license_success(self, mock_hw, mock_info, mock_open, mock_exists, mock_sha, mock_paths):
        mock_paths.return_value = {
            "dir": "Licenza",
            "config": "Licenza/config.dat",
            "rkey": "Licenza/pyarmor.rkey",
            "manifest": "Licenza/manifest.json",
        }
        mock_sha.side_effect = ["valid_hash", "valid_key_hash"]
        mock_info.return_value = {
            "Hardware ID": "HWID",
            "Scadenza Licenza": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
            "Cliente": "TestUser",
        }

        # Mock open for manifest
        mock_f = MagicMock()
        mock_f.__enter__.return_value = mock_f
        mock_f.read.return_value = '{"config.dat": "valid_hash", "pyarmor.rkey": "valid_key_hash"}'
        mock_open.return_value = mock_f

        is_valid, msg = license_validator.verify_license()
        self.assertTrue(is_valid)
        self.assertIn("Licenza valida per: TestUser", msg)


if __name__ == "__main__":
    unittest.main()
