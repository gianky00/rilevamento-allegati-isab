"""
Unit tests for license_updater.py.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from license_updater import GRACE_PERIOD_KEY, check_grace_period, get_github_token, run_update


class TestLicenseUpdater(unittest.TestCase):
    """Test suite for license updater and grace period."""

    def setUp(self):
        """Setup temporary license directory."""
        self.test_dir = Path("temp_updater_test")
        self.test_dir.mkdir(exist_ok=True)
        self.token_path = self.test_dir / "validity.token"

    def tearDown(self):
        """Cleanup temporary files."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_get_github_token(self):
        """Test GitHub token reconstruction."""
        token = get_github_token()
        self.assertTrue(token.startswith("ghp_"))
        self.assertEqual(len(token), 40)

    @patch("license_updater._get_validity_token_path")
    def test_grace_period_valid(self, mock_path):
        """Test grace period verification with a fresh token."""
        mock_path.return_value = str(self.token_path)

        # Create a valid token (current time)
        cipher = Fernet(GRACE_PERIOD_KEY)
        now_str = datetime.now(timezone.utc).isoformat()
        self.token_path.write_bytes(cipher.encrypt(now_str.encode()))

        self.assertTrue(check_grace_period())

    @patch("license_updater._get_validity_token_path")
    def test_grace_period_expired(self, mock_path):
        """Test grace period expiration (> 3 days)."""
        mock_path.return_value = str(self.token_path)

        cipher = Fernet(GRACE_PERIOD_KEY)
        old_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        self.token_path.write_bytes(cipher.encrypt(old_time.encode()))

        with self.assertRaises(Exception) as cm:
            check_grace_period()
        self.assertIn("SCADUTO", str(cm.exception))

    @patch("license_updater.requests.get")
    @patch("license_updater.license_validator.get_hardware_id")
    @patch("license_updater.get_license_dir")
    def test_run_update_success(self, mock_dir, mock_hwid, mock_get):
        """Test full successful update from GitHub."""
        mock_dir.return_value = str(self.test_dir)
        mock_hwid.return_value = "HW123"

        # Mock responses for 3 files
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_get.return_value = mock_response

        run_update()

        # Verify files created
        self.assertTrue((self.test_dir / "config.dat").exists())
        self.assertTrue((self.test_dir / "manifest.json").exists())
        self.assertTrue(self.token_path.exists())

if __name__ == "__main__":
    unittest.main()
