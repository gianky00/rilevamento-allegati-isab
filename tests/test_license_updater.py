"""
Unit tests for license_updater.py.
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from license_updater import check_grace_period, get_github_token, run_update
import license_validator


class TestLicenseUpdater(unittest.TestCase):
    """Test suite for license updater and grace period."""

    def setUp(self):
        """Setup temporary license directory."""
        self.test_dir = Path("temp_updater_test")
        self.test_dir.mkdir(exist_ok=True)
        self.token_path = self.test_dir / "validity.token"
        
        self.test_hwid = "TEST-HWID-UPDATE"
        self.dynamic_key = license_validator.derive_license_key(self.test_hwid)
        self.cipher = Fernet(self.dynamic_key)

    def tearDown(self):
        """Cleanup temporary files."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_get_github_token(self):
        """Test GitHub token reconstruction."""
        token = get_github_token()
        # Il token deve avere la struttura ghp_... e 40 caratteri
        self.assertEqual(len(token), 40)

    @patch("license_updater._get_token_path")
    @patch("license_validator.get_hardware_id")
    def test_grace_period_valid(self, mock_hwid, mock_path):
        """Test grace period verification with a fresh token."""
        mock_hwid.return_value = self.test_hwid
        mock_path.return_value = self.token_path

        # Create a valid token (current time)
        now_str = datetime.now(timezone.utc).isoformat()
        self.token_path.write_bytes(self.cipher.encrypt(now_str.encode()))

        self.assertTrue(check_grace_period())

    @patch("license_updater._get_token_path")
    @patch("license_validator.get_hardware_id")
    def test_grace_period_expired(self, mock_hwid, mock_path):
        """Test grace period expiration (> 3 days)."""
        mock_hwid.return_value = self.test_hwid
        mock_path.return_value = self.token_path

        old_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        self.token_path.write_bytes(self.cipher.encrypt(old_time.encode()))

        with self.assertRaises(Exception) as cm:
            check_grace_period()
        self.assertIn("SCADUTO", str(cm.exception))

    @patch("license_updater.requests.get")
    @patch("license_validator.get_hardware_id")
    @patch("license_validator._get_license_paths")
    def test_run_update_success(self, mock_paths, mock_hwid, mock_get):
        """Test full successful update from GitHub."""
        mock_hwid.return_value = self.test_hwid
        
        # Mappa dei percorsi per il test
        paths = {
            "sys_dir": self.test_dir,
            "sys_config": self.test_dir / "config.dat",
            "local_dir": self.test_dir / "local",
            "local_config": self.test_dir / "local" / "config.dat",
            "token": self.token_path
        }
        mock_paths.return_value = paths

        # Mock response per il manifest (200 OK)
        mock_resp_manifest = MagicMock()
        mock_resp_manifest.status_code = 200
        
        # Mock response per il config.dat
        mock_resp_config = MagicMock()
        mock_resp_config.status_code = 200
        mock_resp_config.content = b"encrypted_payload"
        
        # Setup side_effect per gestire chiamate multiple a requests.get
        def get_side_effect(url, headers=None, timeout=None):
            if "manifest.json" in url:
                return mock_resp_manifest
            if "config.dat" in url:
                return mock_resp_config
            return MagicMock(status_code=404)

        mock_get.side_effect = get_side_effect

        run_update()

        # Verifica file creati
        self.assertTrue(paths["sys_config"].exists())
        self.assertTrue(self.token_path.exists())

if __name__ == "__main__":
    unittest.main()
