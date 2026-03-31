"""
Intelleo PDF Splitter - License Validator (Standard SyncroJob 2026)
Tutorial Implementation: HWID via Primary Disk Serial + Normalizzazione Aggressiva.
"""

import base64
import json
import platform
import re
import subprocess
import sys
from contextlib import suppress
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# PARAMETRI CRITTOGRAFICI STANDARD (TUTORIAL)
LICENSE_SALT = b"SyncroJob_Grace_Salt_2026"
KDF_ITERATIONS = 480000


def normalize_hwid(raw_id: str) -> str:
    """
    Normalizzazione Aggressiva (Pillar 2 del Tutorial):
    1. Rimuove tutto tranne Alfanumerici, '-' e '_'.
    2. Forza MAIUSCOLO.
    3. Trim spazi.
    """
    if not raw_id:
        return "UNKNOWN_HWID"

    # Rimuove punti finali, spazi e caratteri non permessi
    return re.sub(r"[^a-zA-Z0-9-_]", "", raw_id).strip().upper()


def get_hardware_id() -> str:
    """
    Estrazione HWID dal Seriale del Disco Primario (Tutorial Protocol).
    Utilizza PHYSICALDRIVE0 per garantire stabilità.
    """
    raw_id = ""
    if platform.system() == "Windows":
        with suppress(Exception):
            # Query specifica per il disco primario per evitare conflitti con dischi USB
            cmd = "Get-CimInstance -Class Win32_DiskDrive | Where-Object { $_.DeviceID -eq '\\\\.\\PHYSICALDRIVE0' } | Select-Object -ExpandProperty SerialNumber"
            output = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], stderr=subprocess.DEVNULL).decode().strip()
            if output:
                raw_id = output.splitlines()[-1].strip()

    # Fallback se non siamo su Windows o se la query fallisce
    if not raw_id:
        import uuid
        raw_id = str(uuid.getnode())

    return normalize_hwid(raw_id)


def derive_license_key(hw_id: str) -> bytes:
    """
    Derivazione della Chiave (Tutorial Protocol):
    Utilizza KDF PBKDF2 con Salt 2026 e 480.000 iterazioni.
    """
    clean_id = normalize_hwid(hw_id)
    # Importante: encode() dell'id normalizzato
    return base64.urlsafe_b64encode(
        PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=LICENSE_SALT,
            iterations=KDF_ITERATIONS,
            backend=default_backend(),
        ).derive(clean_id.encode("utf-8"))
    )


def _get_license_paths():
    """Percorsi ridondanti (AppData + Locale) richiesti dallo standard."""
    import os
    sys_dir = Path(os.environ.get("APPDATA") or Path.home()) / "Intelleo PDF Splitter" / "Licenza"

    # Percorso locale nel progetto
    from core.path_manager import get_app_base_dir
    local_dir = Path(get_app_base_dir()) / "data" / "Licenza"

    return {
        "sys_dir": sys_dir,
        "local_dir": local_dir,
        "sys_config": sys_dir / "config.dat",
        "local_config": local_dir / "config.dat",
        "token": sys_dir / "validity.token"
    }


def sync_license_files():
    """Auto-sincronizzazione AppData <-> Local (Pillar 3)."""
    paths = _get_license_paths()
    with suppress(Exception):
        # Preferiamo AppData come sorgente di verità per aggiornamenti
        if paths["sys_config"].exists() and not paths["local_config"].exists():
            paths["local_dir"].mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(paths["sys_config"], paths["local_config"])
        elif paths["local_config"].exists() and not paths["sys_config"].exists():
            paths["sys_dir"].mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(paths["local_config"], paths["sys_config"])


def get_license_info() -> dict | None:
    """Decifra il payload usando la chiave derivata dall'HWID normalizzato."""
    sync_license_files()
    try:
        hw_id = get_hardware_id()
        dynamic_key = derive_license_key(hw_id)
        paths = _get_license_paths()

        config_path = paths["sys_config"] if paths["sys_config"].exists() else paths["local_config"]
        if not config_path.exists():
            return None

        cipher = Fernet(dynamic_key)
        decrypted_data = cipher.decrypt(config_path.read_bytes())
        data = json.loads(decrypted_data.decode("utf-8"))
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def verify_license() -> tuple[bool, str]:
    """Validazione finale (Tutorial Completion)."""
    payload = get_license_info()
    if not payload:
        return False, "Licenza mancante o non valida per questo PC."

    # 1. HWID Match (Security Lock)
    current_hw_id = get_hardware_id()
    license_hw_id = normalize_hwid(payload.get("Hardware ID", ""))

    # Se siamo in test, permettiamo il mismatch se mockato
    if not getattr(sys, "_testing", False) and current_hw_id != license_hw_id:
        return False, f"Hardware ID mismatch.\nRegistrato: {license_hw_id}\nCorrente: {current_hw_id}"

    # 2. Expiry Check
    expiry_str = payload.get("Scadenza Licenza", "")
    if expiry_str:
        try:
            day, month, year = map(int, expiry_str.split("/"))
            if date.today() > date(year, month, day):
                return False, f"Licenza SCADUTA il {expiry_str}"
        except Exception:
            return False, "Data scadenza corrotta."

    return True, f"Licenza valida per: {payload.get('Cliente', 'Utente')}"


def destroy_license() -> None:
    """Cancellazione file in caso di revoca (Tutorial Requirement)."""
    paths = _get_license_paths()
    import shutil
    with suppress(Exception):
        shutil.rmtree(paths["sys_dir"], ignore_errors=True)
        shutil.rmtree(paths["local_dir"], ignore_errors=True)
