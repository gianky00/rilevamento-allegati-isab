import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import license_updater


class TestLicenseUpdater(unittest.TestCase):
    def setUp(self):
        # Setup mocks for commonly used functions
        self.mock_hw_id = patch("license_validator.get_hardware_id", return_value="TEST_HWID").start()
        self.mock_get_dir = patch("license_updater.get_license_dir", return_value="/mock/Licenza").start()
        self.mock_exists = patch("pathlib.Path.exists").start()
        self.mock_mkdir = patch("pathlib.Path.mkdir").start()
        self.mock_unlink = patch("pathlib.Path.unlink").start()
        self.mock_read_bytes = patch("pathlib.Path.read_bytes").start()
        self.mock_write_bytes = patch("pathlib.Path.write_bytes").start()

    def tearDown(self):
        patch.stopall()

    @patch("requests.get")
    @patch("license_updater.update_grace_timestamp")
    def test_run_update_online_success(self, mock_update_grace, mock_get):
        """Test successful download of ALL files (Online)."""
        self.mock_exists.return_value = True

        # Setup responses: All 200 OK
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"DATA"
        mock_get.return_value = mock_response

        license_updater.run_update()

        # Check files written (3 files)
        self.assertEqual(self.mock_write_bytes.call_count, 3)
        mock_update_grace.assert_called_once()

    @patch("requests.get")
    @patch("license_updater.update_grace_timestamp")
    def test_run_update_online_incomplete(self, mock_update_grace, mock_get):
        """Test that NO files are written if one is missing (404)."""
        self.mock_exists.return_value = True

        # Setup responses: First 200, Second 404
        r_ok = MagicMock()
        r_ok.status_code = 200
        r_ok.content = b"DATA"

        r_missing = MagicMock()
        r_missing.status_code = 404

        # Cycle through responses
        mock_get.side_effect = [r_ok, r_missing, r_ok]

        license_updater.run_update()

        # Check NO files written
        self.assertEqual(self.mock_write_bytes.call_count, 0)
        # Grace timestamp should still be updated (we are online)
        mock_update_grace.assert_called_once()

    @patch("requests.get")
    @patch("license_updater.check_grace_period")
    def test_run_update_offline(self, mock_check_grace, mock_get):
        """Test fallback to grace period on network error."""
        self.mock_exists.return_value = True

        # Raise ConnectionError
        import requests

        mock_get.side_effect = requests.ConnectionError("Fail")

        license_updater.run_update()

        # Check grace period checked
        mock_check_grace.assert_called_once()

    def test_check_grace_period_valid(self):
        """Test grace period with valid token."""
        from cryptography.fernet import Fernet

        key = license_updater.GRACE_PERIOD_KEY

        valid_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(valid_time.encode())

        self.mock_exists.return_value = True
        self.mock_read_bytes.return_value = encrypted
        
        result = license_updater.check_grace_period()
        self.assertTrue(result)

    def test_check_grace_period_expired(self):
        """Test grace period expired (>3 days)."""
        from cryptography.fernet import Fernet

        key = license_updater.GRACE_PERIOD_KEY

        expired_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(expired_time.encode())

        self.mock_exists.return_value = True
        self.mock_read_bytes.return_value = encrypted
        
        with self.assertRaises(Exception) as cm:
            license_updater.check_grace_period()
        self.assertIn("SCADUTO", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
