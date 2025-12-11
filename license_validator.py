import os
import sys
import subprocess
import json
import hashlib
import platform
import uuid
from datetime import date
from cryptography.fernet import Fernet

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
    """Retrieves a unique hardware ID for the machine with fallbacks."""
    system = platform.system()

    if system == 'Windows':
        # 1. Try WMIC (Legacy)
        try:
            cmd = 'wmic diskdrive get serialnumber'
            # Use shell=True and suppress stderr
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            parts = output.strip().split('\n')
            if len(parts) > 1:
                return parts[1].strip()
        except Exception:
            pass # WMIC failed, try next

        # 2. Try PowerShell (Disk Serial)
        try:
            cmd = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance -Class Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"]
            # Create startupinfo to hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL).decode().strip()
            if output:
                # If multiple disks, taking the first one (splitlines()[0]) is usually stable enough
                return output.splitlines()[0].strip()
        except Exception:
            pass

        # 3. Try PowerShell (System UUID) - Alternative stable ID
        try:
            cmd = ["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL).decode().strip()
            if output:
                return output
        except Exception:
            pass

    elif system == 'Linux':
        # Use lsblk or machine-id as fallback
        try:
            # Try getting root disk serial
            cmd = "lsblk --nodeps -o name,serial | grep -v 'NAME' | head -n 1 | awk '{print $2}'"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
            if output:
                 return output
        except: pass

        # Fallback to machine-id
        if os.path.exists('/etc/machine-id'):
            try:
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            except: pass

    # 4. Final Fallback: Python UUID (MAC Address based)
    # This works on all platforms and requires no external commands
    try:
        return str(uuid.getnode())
    except Exception:
        return "ERROR_GETTING_ID"

def _get_license_paths():
    """Returns the paths for license files."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    license_dir = os.path.join(base_dir, "Licenza")
    return {
        "dir": license_dir,
        "config": os.path.join(license_dir, "config.dat"),
        "rkey": os.path.join(license_dir, "pyarmor.rkey"),
        "manifest": os.path.join(license_dir, "manifest.json")
    }

def get_license_info():
    """
    Retrieves the decrypted license information without validation.
    Returns a dictionary with license details or None if error.
    """
    paths = _get_license_paths()
    config_path = paths["config"]

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, "rb") as f:
            encrypted_data = f.read()

        cipher = Fernet(LICENSE_SECRET_KEY)
        decrypted_data = cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception:
        return None

def verify_license():
    """
    Verifies the license presence and validity.
    Returns (True, message) if valid, (False, message) otherwise.
    """
    paths = _get_license_paths()

    # Check if directory exists
    if not os.path.exists(paths["dir"]):
        return False, "Cartella 'Licenza' mancante."

    # Check files existence
    if not os.path.exists(paths["config"]) or not os.path.exists(paths["manifest"]):
         return False, "File di licenza danneggiati o mancanti."

    # 1. Verify Integrity via Manifest
    try:
        with open(paths["manifest"], "r") as f:
            manifest = json.load(f)

        # Verify config.dat hash
        if _calculate_sha256(paths["config"]) != manifest.get("config.dat"):
            return False, "Integrità licenza compromessa (config.dat)."

        # Verify pyarmor.rkey hash if present in manifest and on disk
        if "pyarmor.rkey" in manifest and os.path.exists(paths["rkey"]):
             if _calculate_sha256(paths["rkey"]) != manifest.get("pyarmor.rkey"):
                 return False, "Integrità licenza compromessa (pyarmor.rkey)."

    except Exception as e:
        return False, f"Errore lettura manifest: {e}"

    # 2. Decrypt and Validate Config
    try:
        payload = get_license_info()
        if not payload:
             return False, "Impossibile leggere i dati della licenza."

        # Validate Hardware ID
        current_hw_id = get_hardware_id()
        license_hw_id = payload.get("Hardware ID", "")

        # Normalize IDs: strip whitespace and trailing dots (common in wmic output)
        norm_current = current_hw_id.strip().rstrip('.')
        norm_license = license_hw_id.strip().rstrip('.')

        # Check against normalized values
        if norm_current != norm_license and "UNKNOWN" not in current_hw_id:
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
