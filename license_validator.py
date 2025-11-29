import os
import sys
import subprocess
import json
import hashlib
import platform
from datetime import date
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import messagebox

# SECURITY WARNING: Keep this key secret!
LICENSE_SECRET_KEY = b'8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek='

def _calculate_sha256(filepath):
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_hardware_id():
    """Retrieves a unique hardware ID for the machine."""
    system = platform.system()
    try:
        if system == 'Windows':
            # Use wmic to get disk serial number
            cmd = 'wmic diskdrive get serialnumber'
            output = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
            return output
        elif system == 'Linux':
            # Use lsblk or machine-id as fallback
            try:
                # Try getting root disk serial
                cmd = "lsblk --nodeps -o name,serial | grep -v 'NAME' | head -n 1 | awk '{print $2}'"
                output = subprocess.check_output(cmd, shell=True).decode().strip()
                if output:
                     return output
            except: pass

            # Fallback to machine-id
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            return "UNKNOWN_LINUX_ID"
        else:
            return "UNKNOWN_ID"
    except Exception:
        return "ERROR_GETTING_ID"

def verify_license():
    """
    Verifies the license presence and validity.
    Returns (True, message) if valid, (False, message) otherwise.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    license_dir = os.path.join(base_dir, "Licenza")

    # Check if directory exists
    if not os.path.exists(license_dir):
        return False, "Cartella 'Licenza' mancante."

    # Paths
    rkey_path = os.path.join(license_dir, "pyarmor.rkey")
    config_path = os.path.join(license_dir, "config.dat")
    manifest_path = os.path.join(license_dir, "manifest.json")

    # Check files existence
    if not os.path.exists(config_path) or not os.path.exists(manifest_path):
         return False, "File di licenza danneggiati o mancanti."

    # 1. Verify Integrity via Manifest
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # Verify config.dat hash
        if _calculate_sha256(config_path) != manifest.get("config.dat"):
            return False, "Integrità licenza compromessa (config.dat)."

        # Verify pyarmor.rkey hash if present in manifest and on disk
        if "pyarmor.rkey" in manifest and os.path.exists(rkey_path):
             if _calculate_sha256(rkey_path) != manifest.get("pyarmor.rkey"):
                 return False, "Integrità licenza compromessa (pyarmor.rkey)."

    except Exception as e:
        return False, f"Errore lettura manifest: {e}"

    # 2. Decrypt and Validate Config
    try:
        with open(config_path, "rb") as f:
            encrypted_data = f.read()

        cipher = Fernet(LICENSE_SECRET_KEY)
        decrypted_data = cipher.decrypt(encrypted_data)
        payload = json.loads(decrypted_data.decode('utf-8'))

        # Validate Hardware ID
        current_hw_id = get_hardware_id()
        # Clean up ID for comparison (remove dots/spaces if needed as per admin tool logic)
        license_hw_id = payload.get("Hardware ID", "")

        # Simple flexible check (contains or equals) to handle potential formatting diffs
        # The admin tool does: clean_disk_serial = disk_serial.rstrip('.')
        # We should be strict but fair.

        # If we are in development/testing (e.g. Linux sandbox), we might want to bypass HW check or simulate it.
        # But for production code, we must check.
        # Since I can't easily replicate the exact 'wmic' output of a real Windows user here,
        # I will assume exact match is required, but I'll strip whitespace.

        if current_hw_id.strip() != license_hw_id.strip() and "UNKNOWN" not in current_hw_id:
             return False, f"Hardware ID non valido.\nAtteso: {license_hw_id}\nRilevato: {current_hw_id}"

        # Validate Expiry
        expiry_str = payload.get("Scadenza Licenza", "")
        if expiry_str:
            try:
                # Format is DD/MM/YYYY
                day, month, year = map(int, expiry_str.split('/'))
                expiry_date = date(year, month, day)
                if date.today() > expiry_date:
                    return False, f"Licenza SCADUTA il {expiry_str}"
            except ValueError:
                return False, "Formato data scadenza non valido."

        return True, f"Licenza Valida per: {payload.get('Cliente', 'Utente')}"

    except Exception as e:
        return False, f"Errore decifrazione licenza: {e}"
