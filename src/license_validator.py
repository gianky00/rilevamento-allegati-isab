"""
Intelleo PDF Splitter - License Validator (Standard SyncroJob 2026)
Tutorial Implementation: HWID via Primary Disk Serial + Normalizzazione Aggressiva.
"""

import base64
import json
import logging
import platform
import re
import shutil
import subprocess
from contextlib import suppress
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("Intelleo")

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
    # Rimuove anche i doppi apici che spesso PowerShell restituisce
    return re.sub(r"[^a-zA-Z0-9-_]", "", raw_id.replace('"', '')).strip().upper()


def get_all_hardware_ids() -> list[str]:
    """
    Recupera TUTTI i possibili Hardware ID validi per questa macchina:
    1. Seriali di tutti i dischi fisici interni.
    2. UUID della scheda madre (fallback).
    """
    ids = []
    if platform.system() == "Windows":
        with suppress(Exception):
            # Query per TUTTI i dischi fisici
            cmd = "Get-CimInstance -Class Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"
            output = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], stderr=subprocess.DEVNULL, shell=True).decode().strip()

            if output:
                for line in output.splitlines():
                    line = line.strip()
                    # Salta intestazioni o linee vuote
                    if not line or line.lower() in ("serialnumber", "index", "deviceid", "model"):
                        continue

                    clean_id = normalize_hwid(line)
                    if clean_id and clean_id != "UNKNOWN_HWID":
                        ids.append(clean_id)

    # Fallback UUID (sempre incluso come ultima risorsa)
    with suppress(Exception):
        import uuid
        ids.append(normalize_hwid(str(uuid.getnode())))

    # Rimuove duplicati mantenendo l'ordine
    return list(dict.fromkeys(ids))


def get_hardware_id() -> str:
    """
    Restituisce l'ID primario (preferibilmente il disco C:).
    Mantenuto per compatibilità con il resto del codice.
    """
    if platform.system() == "Windows":
        with suppress(Exception):
            # Tenta di prendere il seriale del disco che ospita la partizione C: (molto più affidabile)
            cmd = "(Get-Partition -DriveLetter C | Get-Disk).SerialNumber"
            output = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], stderr=subprocess.DEVNULL, shell=True).decode().strip()

            if output:
                # Se l'output contiene più righe (raro per un solo disco), prendiamo l'ultima che non sia l'intestazione
                for line in reversed(output.splitlines()):
                    line = line.strip()
                    if line and line.lower() not in ("serialnumber", "index"):
                        return normalize_hwid(line)

    # Fallback al primo dei dischi rilevati o UUID
    all_ids = get_all_hardware_ids()
    return all_ids[0] if all_ids else "UNKNOWN_HWID"



def derive_license_key(hw_id: str) -> bytes:
    """
    Derivazione della Chiave (Tutorial Protocol):
    Utilizza KDF PBKDF2 con Salt 2026 e 480.000 iterazioni.
    """
    clean_id = normalize_hwid(hw_id)
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
            shutil.copy2(paths["sys_config"], paths["local_config"])
        elif paths["local_config"].exists() and not paths["sys_config"].exists():
            paths["sys_dir"].mkdir(parents=True, exist_ok=True)
            shutil.copy2(paths["local_config"], paths["sys_config"])


def get_license_info() -> dict | None:
    """
    Tenta di decifrare il payload provando TUTTI gli HWID rilevati sulla macchina.
    Se uno funziona, abbiamo trovato il disco licenziato.
    """
    sync_license_files()
    paths = _get_license_paths()
    config_path = paths["sys_config"] if paths["sys_config"].exists() else paths["local_config"]

    if not config_path.exists():
        return None

    all_ids = get_all_hardware_ids()
    encrypted_bytes = config_path.read_bytes()

    for hw_id in all_ids:
        try:
            dynamic_key = derive_license_key(hw_id)
            cipher = Fernet(dynamic_key)
            decrypted_data = cipher.decrypt(encrypted_bytes)
            data = json.loads(decrypted_data.decode("utf-8"))
            if isinstance(data, dict):
                logger.debug(f"Licenza decifrata con successo usando HWID: {hw_id}")
                return data
        except Exception:
            continue

    return None


def verify_license() -> tuple[bool, str]:
    """Validazione finale (Tutorial Completion)."""
    payload = get_license_info()
    if not payload:
        return False, "Licenza mancante o non valida per questo PC."

    # Se get_license_info() ha restituito un payload, significa che uno degli HWID
    # della macchina ha decifrato con successo il file. La licenza è quindi valida.
    # Verifichiamo solo la scadenza.

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
    with suppress(Exception):
        shutil.rmtree(paths["sys_dir"], ignore_errors=True)
        shutil.rmtree(paths["local_dir"], ignore_errors=True)

