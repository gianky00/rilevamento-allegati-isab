"""
Intelleo PDF Splitter - License Updater
Gestisce l'aggiornamento e la validazione della licenza.
"""

import sys
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from cryptography.fernet import Fernet

import license_validator

# Chiave per cifratura token grace period
GRACE_PERIOD_KEY = b"8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek="


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
    Controlla e scarica aggiornamenti licenza da GitHub.

    - Usa l'API GitHub per scaricare i file di licenza
    - Se tutti i file sono disponibili (200 OK), li scarica
    - Se qualche file manca (404), mantiene i file locali
    - In caso di errore di rete, verifica il periodo di grazia
    """

    hw_id = license_validator.get_hardware_id().strip().rstrip(".")
    license_dir = Path(get_license_dir())

    if not license_dir.exists():
        with suppress(OSError):
            license_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{hw_id}"
    token = get_github_token()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}

    files_map = {"config.dat": "config.dat", "pyarmor.rkey": "pyarmor.rkey", "manifest.json": "manifest.json"}

    downloaded_content = {}
    incomplete_update = False
    network_error_occurred = False

    # Tentativo download
    for remote_name, local_name in files_map.items():
        url = f"{base_url}/{remote_name}"

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                downloaded_content[local_name] = response.content
            elif response.status_code in (404, 401):
                incomplete_update = True
                if response.status_code == 401:
                    break
            else:
                incomplete_update = True

        except requests.RequestException:
            network_error_occurred = True
            break

    if network_error_occurred:
        check_grace_period()
    elif incomplete_update:
        update_grace_timestamp()
    else:
        with suppress(OSError):
            for local_name, content in downloaded_content.items():
                full_path = license_dir / local_name
                full_path.write_bytes(content)
            update_grace_timestamp()


if __name__ == "__main__":
    with suppress(Exception):
        run_update()
