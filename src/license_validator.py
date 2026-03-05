"""
Intelleo PDF Splitter - License Validator
Gestisce la validazione della licenza software.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import date

from cryptography.fernet import Fernet

# Chiave segreta per decifratura licenza
LICENSE_SECRET_KEY = b"8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek="


def _calculate_sha256(filepath):
    """Calcola l'hash SHA256 di un file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_hardware_id():
    """
    Ottiene un ID hardware univoco per la macchina.

    Strategia con fallback multipli:
    1. WMIC (Windows Legacy)
    2. PowerShell CIM (Windows Modern)
    3. PowerShell UUID (Windows Fallback)
    4. lsblk (Linux)
    5. machine-id (Linux Fallback)
    6. Python UUID (Universale)
    """
    system = platform.system()

    if system == "Windows":
        # 1. Try WMIC (Legacy)
        try:
            cmd = "wmic diskdrive get serialnumber"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            parts = output.strip().split("\n")
            if len(parts) > 1:
                return parts[1].strip()
        except Exception:
            pass

        # 2. Try PowerShell (Disk Serial)
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance -Class Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber",
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL).decode().strip()

            if output:
                return output.splitlines()[0].strip()
        except Exception:
            pass

        # 3. Try PowerShell (System UUID)
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID",
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL).decode().strip()

            if output:
                return output
        except Exception:
            pass

    elif system == "Linux":
        # Try lsblk
        try:
            cmd = "lsblk --nodeps -o name,serial | grep -v 'NAME' | head -n 1 | awk '{print $2}'"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()

            if output:
                return output
        except Exception:
            pass

        # Fallback to machine-id
        if os.path.exists("/etc/machine-id"):
            try:
                with open("/etc/machine-id") as f:
                    return f.read().strip()
            except Exception:
                pass

    # Fallback universale: UUID basato su MAC address
    try:
        return str(uuid.getnode())
    except Exception:
        return "ERROR_GETTING_ID"


def _get_license_paths():
    """Restituisce i percorsi dei file di licenza."""
    # Use APPDATA for license storage to ensure write permissions
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~")
        license_dir = os.path.join(appdata, "Intelleo PDF Splitter", "Licenza")
    else:
        # Linux/Mac fallback
        license_dir = os.path.join(os.path.expanduser("~"), ".intelleo-pdf-splitter", "licenza")

    return {
        "dir": license_dir,
        "config": os.path.join(license_dir, "config.dat"),
        "rkey": os.path.join(license_dir, "pyarmor.rkey"),
        "manifest": os.path.join(license_dir, "manifest.json"),
    }


def get_license_info():
    """
    Ottiene le informazioni della licenza decifrate.

    Returns:
        dict: Dati della licenza o None in caso di errore
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
        return json.loads(decrypted_data.decode("utf-8"))
    except Exception:
        return None


def verify_license():
    """
    Verifica la validità della licenza.

    Controlli effettuati:
    1. Esistenza cartella e file licenza
    2. Integrità file tramite hash (manifest)
    3. Decifratura dati licenza
    4. Validazione Hardware ID
    5. Verifica data di scadenza

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    paths = _get_license_paths()

    # Controllo cartella
    if not os.path.exists(paths["dir"]):
        return False, "Cartella 'Licenza' mancante"

    # Controllo file
    if not os.path.exists(paths["config"]) or not os.path.exists(paths["manifest"]):
        return False, "File di licenza mancanti o danneggiati"

    # 1. Verifica integrità tramite manifest
    try:
        with open(paths["manifest"]) as f:
            manifest = json.load(f)

        # Verifica hash config.dat
        if _calculate_sha256(paths["config"]) != manifest.get("config.dat"):
            return False, "Integrità licenza compromessa (config.dat)"

        # Verifica hash pyarmor.rkey se presente
        if "pyarmor.rkey" in manifest and os.path.exists(paths["rkey"]):
            if _calculate_sha256(paths["rkey"]) != manifest.get("pyarmor.rkey"):
                return False, "Integrità licenza compromessa (pyarmor.rkey)"

    except Exception as e:
        return False, f"Errore lettura manifest: {e}"

    # 2. Decifra e valida i dati
    try:
        payload = get_license_info()
        if not payload:
            return False, "Impossibile leggere i dati della licenza"

        # Validazione Hardware ID
        current_hw_id = get_hardware_id()
        license_hw_id = payload.get("Hardware ID", "")

        # Normalizzazione ID
        norm_current = current_hw_id.strip().rstrip(".")
        norm_license = license_hw_id.strip().rstrip(".")

        if norm_current != norm_license and "UNKNOWN" not in current_hw_id:
            return False, (f"Hardware ID non valido\nAtteso: {license_hw_id}\nRilevato: {current_hw_id}")

        # Validazione scadenza
        expiry_str = payload.get("Scadenza Licenza", "")
        if expiry_str:
            try:
                day, month, year = map(int, expiry_str.split("/"))
                expiry_date = date(year, month, day)

                if date.today() > expiry_date:
                    return False, f"Licenza SCADUTA il {expiry_str}"
            except ValueError:
                return False, "Formato data scadenza non valido"

        cliente = payload.get("Cliente", "Utente")
        return True, f"Licenza valida per: {cliente}"

    except Exception as e:
        return False, f"Errore validazione licenza: {e}"
