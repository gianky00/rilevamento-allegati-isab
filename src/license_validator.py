"""
Intelleo PDF Splitter - License Validator
Gestisce la validazione della licenza software.
"""

import base64
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from contextlib import suppress
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# SincroJob V9.0 - Costanti di blindatura (Allineamento SyncroJob 2026)
LICENSE_SALT = b"SyncroJob_Grace_Salt_2026"


def derive_license_key(hw_id: str) -> bytes:
    """
    Deriva una chiave Fernet da 32 byte partendo dall'HWID dell'utente.
    Utilizza PBKDF2HMAC con 480.000 iterazioni per massima sicurezza.
    """
    # Normalizzazione HWID (Pilastro 1)
    # Rimuove spazi e punti finali, ma mantiene il case originale per consistenza
    clean_id = hw_id.strip().rstrip(".")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=LICENSE_SALT,
        iterations=480000,
        backend=default_backend(),
    )

    key_bytes = kdf.derive(clean_id.encode("utf-8"))
    return base64.urlsafe_b64encode(key_bytes)


def _calculate_sha256(filepath):
    """Calcola l'hash SHA256 di un file."""
    sha256_hash = hashlib.sha256()
    with Path(filepath).open("rb") as f:
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
        with suppress(Exception):
            cmd = "wmic diskdrive get serialnumber"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            parts = output.strip().split("\n")
            if len(parts) > 1:
                return parts[1].strip()

        # 2. Try PowerShell (Disk Serial)
        with suppress(Exception):
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

        # 3. Try PowerShell (System UUID)
        with suppress(Exception):
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

    elif system == "Linux":
        # Try lsblk
        with suppress(Exception):
            cmd = "lsblk --nodeps -o name,serial | grep -v 'NAME' | head -n 1 | awk '{print $2}'"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()

            if output:
                return output

        # Fallback to machine-id
        mid_path = Path("/etc/machine-id")
        if mid_path.exists():
            with suppress(Exception):
                return mid_path.read_text(encoding="utf-8").strip()

    # Fallback universale: UUID basato su MAC address
    with suppress(Exception):
        return str(uuid.getnode())

    return "ERROR_GETTING_ID"


def _get_license_paths():
    """Restituisce i percorsi dei file di licenza core."""
    # Use APPDATA for license storage to ensure write permissions
    if sys.platform == "win32":
        import os

        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home())
        license_dir = Path(appdata) / "Intelleo PDF Splitter" / "Licenza"
    else:
        # Linux/Mac fallback
        license_dir = Path.home() / ".intelleo-pdf-splitter" / "licenza"

    return {
        "dir": str(license_dir),
        "config": str(license_dir / "config.dat"),
        "manifest": str(license_dir / "manifest.json"),
        "token": str(license_dir / "validity.token"),
    }


def destroy_license():
    """Rimuove fisicamente tutti i file relativi alla licenza (Self-Destruct)."""
    paths = _get_license_paths()
    for key in ["config", "manifest", "token"]:
        with suppress(OSError):
            p = Path(paths[key])
            if p.exists():
                p.unlink()


def get_license_info():
    """
    Ottiene le informazioni della licenza decifrate utilizzando la chiave dinamica HWID.

    Returns:
        dict: Dati della licenza o None in caso di errore
    """
    paths = _get_license_paths()
    config_path = Path(paths["config"])

    if not config_path.exists():
        return None

    try:
        encrypted_data = config_path.read_bytes()

        # Derivazione dinamica della chiave (Pilastro 2)
        hw_id = get_hardware_id()
        dynamic_key = derive_license_key(hw_id)

        cipher = Fernet(dynamic_key)
        decrypted_data = cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode("utf-8"))
    except Exception:
        # Se la decifratura fallisce, la chiave HWID è cambiata o il file è corrotto
        return None


def verify_license():
    """
    Verifica la validità della licenza con blindatura SyncroJob V9.0.

    Controlli effettuati:
    1. Esistenza cartella e file licenza
    2. Integrità file tramite hash (manifest)
    3. Decifratura dati tramite HWID-Derived Key
    4. Validazione Hardware ID incrociata
    5. Verifica data di scadenza

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    paths = _get_license_paths()

    # Controllo cartella
    if not Path(paths["dir"]).exists():
        return False, "Cartella 'Licenza' mancante"

    # Controllo file
    if not Path(paths["config"]).exists() or not Path(paths["manifest"]).exists():
        return False, "File di licenza mancanti o danneggiati"

    # 1. Verifica integrità tramite manifest
    try:
        with Path(paths["manifest"]).open(encoding="utf-8") as f:
            manifest = json.load(f)

        # Verifica hash config.dat
        if _calculate_sha256(paths["config"]) != manifest.get("config.dat"):
            return False, "Integrità licenza compromessa (config.dat)"

    except Exception as e:
        return False, f"Errore lettura manifest: {e}"

    # 2. Decifra e valida i dati (Pilastro 2)
    try:
        payload = get_license_info()
        if not payload:
            return False, "Licenza non valida per questo Hardware (Decifratura fallita)"

        # Validazione Hardware ID (Pilastro 1)
        current_hw_id = get_hardware_id()
        license_hw_id = payload.get("Hardware ID", "")

        # Normalizzazione rigorosa
        norm_current = current_hw_id.strip().rstrip(".")
        norm_license = license_hw_id.strip().rstrip(".")

        if norm_current != norm_license:
            return False, (f"Hardware ID mismatch\nAtteso: {license_hw_id}\nRilevato: {current_hw_id}")

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
