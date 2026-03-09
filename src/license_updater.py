"""
Intelleo PDF Splitter - License Updater
Gestisce l'aggiornamento e la validazione della licenza.
"""

import sys
import json
import hashlib
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from cryptography.fernet import Fernet

import license_validator

# Chiave per cifratura token grace period
GRACE_PERIOD_KEY = b"8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek="


class LicenseRevokedError(Exception):
    """Eccezione sollevata quando la licenza è stata revocata dal server."""
    pass


def get_github_token():
    """Ricostruisce il token GitHub offuscato."""
    chars = (
        103,
        104,
        112,
        95,
        99,
        57,
        68,
        103,
        54,
        116,
        79,
        67,
        75,
        104,
        57,
        89,
        106,
        112,
        97,
        70,
        117,
        66,
        54,
        73,
        52,
        79,
        66,
        121,
        107,
        103,
        120,
        114,
        113,
        98,
        49,
        85,
        106,
        106,
        65,
        105,
    )
    return "".join(chr(c) for c in chars)


def get_license_dir():
    """Restituisce il percorso della cartella Licenza."""
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

    return str(license_dir)


def _get_validity_token_path():
    """Restituisce il percorso del token di validità."""
    return str(Path(get_license_dir()) / "validity.token")


def update_grace_timestamp():
    """Salva il timestamp corrente cifrato per il periodo di grazia."""
    with suppress(Exception):
        token_path = Path(_get_validity_token_path())
        current_time = datetime.now(timezone.utc).isoformat()

        cipher = Fernet(GRACE_PERIOD_KEY)
        encrypted_time = cipher.encrypt(current_time.encode("utf-8"))

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_bytes(encrypted_time)


def check_grace_period():
    """
    Verifica se l'applicazione può funzionare offline.

    Condizioni:
    1. Il file 'validity.token' deve esistere e essere decifrabile
    2. L'ultimo controllo online deve essere < 3 giorni fa
    3. L'orologio di sistema non deve essere stato modificato

    Returns:
        True se consentito

    Raises:
        Exception se il periodo di grazia è scaduto
    """
    token_path = Path(_get_validity_token_path())

    if not token_path.exists():
        msg = "Nessuna validazione online precedente.\nConnessione internet richiesta per il primo avvio."
        raise Exception(msg)

    try:
        encrypted_data = token_path.read_bytes()

        cipher = Fernet(GRACE_PERIOD_KEY)
        decrypted_data = cipher.decrypt(encrypted_data).decode("utf-8")
        last_online = datetime.fromisoformat(decrypted_data)
        now = datetime.now(timezone.utc)

        # Controllo rollback orologio
        if now < last_online - timedelta(minutes=5):
            msg = "Rilevata incoerenza orologio di sistema."
            raise Exception(msg)

        # Controllo 3 giorni
        days_offline = (now - last_online).days
        if days_offline >= 3:
            msg = "Periodo di grazia offline (3 giorni) SCADUTO.\nConnettiti a internet per rinnovare la licenza."
            raise Exception(msg)

        return True

    except Exception as e:
        if any(x in str(e) for x in ("SCADUTO", "incoerenza", "Nessuna validazione")):
            raise
        msg = f"Errore verifica periodo di grazia: {e}"
        raise Exception(msg) from e


def run_update():
    """
    Controlla e scarica aggiornamenti licenza da GitHub con Zero-Corruption Policy.

    Workflow:
    1. Verifica esistenza HWID folder (404 = REVOCATA).
    2. Download manifest.json per check hash.
    3. Download config.dat e rkey solo se necessario.
    4. Validazione in memoria (HWID e decifratura) prima di scrivere.
    """

    hw_id = license_validator.get_hardware_id().strip().rstrip(".")
    license_dir = Path(get_license_dir())

    if not license_dir.exists():
        with suppress(OSError):
            license_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verifica REVOCA (Cartella HWID su GitHub)
    base_url = f"https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{hw_id}"
    token = get_github_token()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}

    try:
        # Check folder existence/status
        # Invece di iterare, scarichiamo prima il manifest per vedere se siamo autorizzati
        manifest_url = f"{base_url}/manifest.json"
        resp = requests.get(manifest_url, headers=headers, timeout=10)

        if resp.status_code == 404:
            # SEGNALE 404: La cartella non esiste più -> Licenza REVOCATA
            license_validator.destroy_license()
            msg = "LICENZA REVOCATA DAL SERVER.\nContattare l'amministratore per il ripristino."
            raise LicenseRevokedError(msg)

        if resp.status_code != 200:
            # Altri errori (es. 401, 403, 500) -> Usa Grace Period
            check_grace_period()
            return

        remote_manifest = resp.json() if isinstance(resp.content, dict) else json.loads(resp.content)
    except (requests.RequestException, json.JSONDecodeError) as e:
        if isinstance(e, LicenseRevokedError):
            raise
        check_grace_period()
        return

    # 2. Ottimizzazione Traffico: Check hash manifest locale vs remoto
    local_manifest_path = license_dir / "manifest.json"
    if local_manifest_path.exists():
        with suppress(Exception):
            local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
            if local_manifest.get("config.dat") == remote_manifest.get("config.dat"):
                # Licenza già aggiornata
                update_grace_timestamp()
                return

    # 3. Download in RAM (Pre-Validazione)
    files_to_download = ["config.dat", "pyarmor.rkey"]
    downloaded_content = {"manifest.json": json.dumps(remote_manifest).encode("utf-8")}

    try:
        for filename in files_to_download:
            if filename not in remote_manifest:
                continue
            url = f"{base_url}/{filename}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                downloaded_content[filename] = r.content
            else:
                raise Exception(f"Errore download {filename}: {r.status_code}")

        # 4. Validazione in Memoria (Zero-Corruption)
        config_data = downloaded_content.get("config.dat")
        if not config_data:
            raise Exception("Dati configurazione mancanti nel download")

        # Verifica decifratura e HWID
        cipher = Fernet(license_validator.LICENSE_SECRET_KEY)
        decrypted_data = cipher.decrypt(config_data)
        payload = json.loads(decrypted_data.decode("utf-8"))

        license_hw_id = payload.get("Hardware ID", "").strip().rstrip(".")
        if license_hw_id != hw_id:
            raise Exception(f"Hardware ID mismatch nel nuovo file: {license_hw_id} vs {hw_id}")

        # 5. Scrittura sicura su disco solo se tutto OK
        for fname, content in downloaded_content.items():
            (license_dir / fname).write_bytes(content)

        update_grace_timestamp()

    except Exception as e:
        if isinstance(e, LicenseRevokedError):
            raise
        # Se l'aggiornamento fallisce, manteniamo la licenza precedente e usiamo il grace period
        # se il timestamp è ancora valido
        with suppress(Exception):
            check_grace_period()


if __name__ == "__main__":
    with suppress(Exception):
        run_update()
