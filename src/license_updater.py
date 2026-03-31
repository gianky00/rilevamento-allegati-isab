"""
Intelleo PDF Splitter - License Updater (Standard SyncroJob 2026)
Tutorial Implementation: GitHub Cloud Validation + Grace Period.
"""

from contextlib import suppress
from datetime import datetime, timedelta, timezone

import requests
from cryptography.fernet import Fernet

import license_validator

# CONFIGURAZIONE (TUTORIAL)
GRACE_PERIOD_DAYS = 3


class LicenseRevokedError(Exception):
    """Eccezione sollevata quando la licenza è assente sul server (404)."""


def get_github_token():
    """Ricostruisce il token GitHub offuscato (Tutorial Implementation)."""
    chars = (103, 104, 112, 95, 99, 57, 68, 103, 54, 116, 79, 67, 75, 104, 57, 89, 106, 112, 97, 70, 117, 66, 54, 73, 52, 79, 66, 121, 107, 103, 120, 114, 113, 98, 49, 85, 106, 106, 65, 105)
    return "".join(chr(c) for c in chars)


def _get_token_path():
    """Percorso file di validità (Trusted Time Pillar)."""
    paths = license_validator._get_license_paths()
    return paths["token"]


def update_grace_timestamp():
    """Salva l'ultimo timestamp online riuscito cifrato con chiave HWID."""
    with suppress(Exception):
        hw_id = license_validator.get_hardware_id()
        dynamic_key = license_validator.derive_license_key(hw_id)
        token_path = _get_token_path()
        token_path.parent.mkdir(parents=True, exist_ok=True)

        current_time = datetime.now(timezone.utc).isoformat()
        cipher = Fernet(dynamic_key)
        encrypted_time = cipher.encrypt(current_time.encode("utf-8"))
        token_path.write_bytes(encrypted_time)


def check_grace_period():
    """Verifica il periodo di tolleranza offline (3 giorni)."""
    token_path = _get_token_path()
    if not token_path.exists():
        raise Exception("Nessuna validazione online precedente (Offline block).")

    try:
        hw_id = license_validator.get_hardware_id()
        dynamic_key = license_validator.derive_license_key(hw_id)

        cipher = Fernet(dynamic_key)
        decrypted_data = cipher.decrypt(token_path.read_bytes()).decode("utf-8")
        last_online = datetime.fromisoformat(decrypted_data)
        now = datetime.now(timezone.utc)

        # Anti-Clock Tampering
        if now < last_online - timedelta(minutes=5):
            raise Exception("Incoerenza orologio di sistema rilevata.")

        if (now - last_online).days >= GRACE_PERIOD_DAYS:
            raise Exception("Periodo di grazia offline SCADUTO.")

        return True
    except Exception as e:
        if "SCADUTO" in str(e) or "Incoerenza" in str(e):
            raise
        raise Exception(f"Errore verifica periodo di grazia: {e}") from e


def run_update():
    """
    Workflow di Sincronizzazione Cloud (GitHub):
    1. Calcola HWID Normalizzato.
    2. Costruisce URL Cloud.
    3. Scarica Manifest e Config se presenti.
    4. Cancella locale se 404.
    """
    hw_id = license_validator.get_hardware_id()
    paths = license_validator._get_license_paths()
    paths["sys_dir"].mkdir(parents=True, exist_ok=True)

    # Tutorial URL Structure
    base_url = f"https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{hw_id}"
    token = get_github_token()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}

    try:
        # 1. Verifica esistenza cartella/manifest su GitHub
        resp = requests.get(f"{base_url}/manifest.json", headers=headers, timeout=10)

        if resp.status_code == 404:
            # REVOCA ESPLICITA: Standard SyncroJob impone la distruzione locale
            license_validator.destroy_license()
            raise LicenseRevokedError("LICENZA REVOCATA DAL SERVER.")

        if resp.status_code != 200:
            # Errore server o rete -> Fallback su Grace Period
            check_grace_period()
            return

        # 2. Download payload cifrato
        r_config = requests.get(f"{base_url}/config.dat", headers=headers, timeout=10)
        if r_config.status_code == 200:
            paths["sys_config"].write_bytes(r_config.content)
            # Sincronizza immediatamente con la cartella locale del progetto
            license_validator.sync_license_files()
            update_grace_timestamp()

    except Exception as e:
        if isinstance(e, LicenseRevokedError):
            raise
        # Fallback period per problemi di rete
        with suppress(Exception):
            check_grace_period()
