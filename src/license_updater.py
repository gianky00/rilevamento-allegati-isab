"""
Intelleo PDF Splitter - License Updater
Gestisce l'aggiornamento e la validazione della licenza.
"""

import sys
import json
import hashlib
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from cryptography.fernet import Fernet

import license_validator


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
    """Salva il timestamp corrente cifrato per il periodo di grazia (HWID-Locked)."""
    with suppress(Exception):
        hw_id = license_validator.get_hardware_id()
        dynamic_key = license_validator.derive_license_key(hw_id)

        token_path = Path(_get_validity_token_path())
        current_time = datetime.now(timezone.utc).isoformat()

        cipher = Fernet(dynamic_key)
        encrypted_time = cipher.encrypt(current_time.encode("utf-8"))

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_bytes(encrypted_time)


def check_grace_period():
    """
    Verifica se l'applicazione può funzionare offline (Pillar 3).
    """
    token_path = Path(_get_validity_token_path())

    if not token_path.exists():
        msg = "Nessuna validazione online precedente.\nConnessione internet richiesta per il primo avvio."
        raise Exception(msg)

    try:
        hw_id = license_validator.get_hardware_id()
        dynamic_key = license_validator.derive_license_key(hw_id)

        encrypted_data = token_path.read_bytes()

        cipher = Fernet(dynamic_key)
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
    Controlla e scarica aggiornamenti licenza da GitHub (Cloud-Driven JIT Enforcement).
    """

    hw_id = license_validator.get_hardware_id()
    norm_hw_id = hw_id.strip().rstrip(".")
    license_dir = Path(get_license_dir())

    if not license_dir.exists():
        with suppress(OSError):
            license_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verifica REVOCA JIT (Pillar 3)
    # Una licenza è considerata REVOCATA se il file manifest non è più raggiungibile (404)
    base_url = f"https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{norm_hw_id}"
    token = get_github_token()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}

    try:
        manifest_url = f"{base_url}/manifest.json"
        resp = requests.get(manifest_url, headers=headers, timeout=10)

        if resp.status_code == 404:
            # Pilastro 3: Se ricevi 404, identifica la licenza come REVOCATA
            license_validator.destroy_license()
            msg = "LICENZA REVOCATA DAL SERVER.\nContattare l'amministratore per il ripristino."
            raise LicenseRevokedError(msg)

        if resp.status_code != 200:
            check_grace_period()
            return

        remote_manifest = resp.json() if isinstance(resp.content, dict) else json.loads(resp.content)
    except (requests.RequestException, json.JSONDecodeError) as e:
        if isinstance(e, LicenseRevokedError):
            raise
        check_grace_period()
        return

    # 2. Ottimizzazione Traffico
    local_manifest_path = license_dir / "manifest.json"
    if local_manifest_path.exists():
        with suppress(Exception):
            local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
            if local_manifest.get("config.dat") == remote_manifest.get("config.dat"):
                update_grace_timestamp()
                return

    # 3. Download in RAM e Validazione JIT (Pillar 3)
    files_to_download = ["config.dat"]
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

        # 4. Validazione in RAM prima di sovrascrivere (Pillar 3)
        config_data = downloaded_content.get("config.dat")
        if not config_data:
            raise Exception("Dati configurazione mancanti nel download")

        # Derivazione chiave dinamica
        dynamic_key = license_validator.derive_license_key(hw_id)
        
        # Ponte di Migrazione (SyncroJob V9.0 Bridge)
        # Tenta prima la decifratura HWID-Locked, poi fall-back su Master Key Legacy per migrazione
        try:
            cipher = Fernet(dynamic_key)
            decrypted_data = cipher.decrypt(config_data)
            payload = json.loads(decrypted_data.decode("utf-8"))
            logging.info("Validazione RAM: Licenza HWID-Locked rilevata e valida.")
        except Exception as e:
            # Fallback temporaneo per migrazione licenze legacy (Pilastro 5 Alignment)
            legacy_key = b"8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek="
            logging.warning(f"Decifratura dinamica fallita ({e}). Tentativo ponte legacy...")
            try:
                legacy_cipher = Fernet(legacy_key)
                decrypted_data = legacy_cipher.decrypt(config_data)
                payload = json.loads(decrypted_data.decode("utf-8"))
                
                # AUTO-MIGRAZIONE: Rincifra il payload con la nuova chiave dinamica
                logging.info("Auto-Migrazione: Rincifratura licenza legacy verso HWID-Locked...")
                new_encrypted = cipher.encrypt(json.dumps(payload).encode("utf-8"))
                downloaded_content["config.dat"] = new_encrypted
                
                # Aggiorna il manifest locale perché l'hash di config.dat è cambiato
                # Calcoliamo l'hash SHA256 dei nuovi dati cifrati in RAM
                new_hash = hashlib.sha256(new_encrypted).hexdigest()
                remote_manifest["config.dat"] = new_hash
                downloaded_content["manifest.json"] = json.dumps(remote_manifest, indent=4).encode("utf-8")
                logging.info(f"Manifest aggiornato con nuovo hash: {new_hash}")
                
            except Exception as legacy_err:
                logging.error(f"Decifratura fallita TOTALMENTE: {legacy_err}")
                raise Exception(f"Decifratura fallita (Nuova e Legacy): {legacy_err}") from legacy_err

        license_hw_id = payload.get("Hardware ID", "").strip().rstrip(".")
        if license_hw_id != norm_hw_id:
            logging.error(f"Hardware ID mismatch nel download: {license_hw_id} vs {norm_hw_id}")
            raise Exception(f"Hardware ID mismatch: {license_hw_id} vs {norm_hw_id}")

        # 5. Scrittura solo dopo validazione RAM superata
        logging.info(f"Scrittura file di licenza in: {license_dir}")
        for fname, content in downloaded_content.items():
            (license_dir / fname).write_bytes(content)

        update_grace_timestamp()
        logging.info("Aggiornamento licenza completato con successo.")

    except Exception as e:
        logging.exception(f"Errore critico durante run_update: {e}")
        if isinstance(e, LicenseRevokedError):
            raise
        with suppress(Exception):
            check_grace_period()


if __name__ == "__main__":
    with suppress(Exception):
        run_update()
