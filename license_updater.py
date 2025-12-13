"""
Intelleo PDF Splitter - License Updater
Gestisce l'aggiornamento e la validazione della licenza.
"""
import os
import requests
import json
import sys
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
import license_validator

# Chiave per cifratura token grace period
GRACE_PERIOD_KEY = b'8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek='


def get_github_token():
    """Ricostruisce il token GitHub offuscato."""
    chars = [
        103, 104, 112, 95, 50, 98, 75, 119, 107, 75, 87, 118, 115, 70, 99, 99,
        52, 82, 66, 79, 79, 71, 65, 110, 111, 118, 80, 114, 67, 70, 53, 75, 72,
        99, 48, 49, 112, 71, 103, 107
    ]
    return "".join(chr(c) for c in chars)


def get_license_dir():
    """Restituisce il percorso della cartella Licenza."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "Licenza")


def _get_validity_token_path():
    """Restituisce il percorso del token di validità."""
    return os.path.join(get_license_dir(), "validity.token")


def update_grace_timestamp():
    """Salva il timestamp corrente cifrato per il periodo di grazia."""
    try:
        token_path = _get_validity_token_path()
        current_time = datetime.now(timezone.utc).isoformat()
        
        cipher = Fernet(GRACE_PERIOD_KEY)
        encrypted_time = cipher.encrypt(current_time.encode('utf-8'))
        
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        
        with open(token_path, "wb") as f:
            f.write(encrypted_time)
    except Exception as e:
        print(f"[AVVISO] Errore aggiornamento timestamp: {e}")


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
    token_path = _get_validity_token_path()
    
    if not os.path.exists(token_path):
        raise Exception(
            "Nessuna validazione online precedente.\n"
            "Connessione internet richiesta per il primo avvio."
        )
        
    try:
        with open(token_path, "rb") as f:
            encrypted_data = f.read()
            
        cipher = Fernet(GRACE_PERIOD_KEY)
        decrypted_data = cipher.decrypt(encrypted_data).decode('utf-8')
        last_online = datetime.fromisoformat(decrypted_data)
        now = datetime.now(timezone.utc)
        
        # Controllo rollback orologio
        if now < last_online - timedelta(minutes=5):
            raise Exception("Rilevata incoerenza orologio di sistema.")
            
        # Controllo 3 giorni
        days_offline = (now - last_online).days
        if days_offline >= 3:
            raise Exception(
                "Periodo di grazia offline (3 giorni) SCADUTO.\n"
                "Connettiti a internet per rinnovare la licenza."
            )
            
        remaining_days = 3 - days_offline
        print(f"[LICENZA] Modalità offline: {remaining_days} giorni rimanenti")
        return True
        
    except Exception as e:
        if any(x in str(e) for x in ["SCADUTO", "incoerenza", "Nessuna validazione"]):
            raise e
        raise Exception(f"Errore verifica periodo di grazia: {e}")


def run_update():
    """
    Controlla e scarica aggiornamenti licenza da GitHub.
    
    - Usa l'API GitHub per scaricare i file di licenza
    - Se tutti i file sono disponibili (200 OK), li scarica
    - Se qualche file manca (404), mantiene i file locali
    - In caso di errore di rete, verifica il periodo di grazia
    """
    print("[LICENZA] ══════════════════════════════════════════════")
    print("[LICENZA] Controllo aggiornamenti licenza...")
    
    hw_id = license_validator.get_hardware_id().strip().rstrip('.')
    license_dir = get_license_dir()
    
    print(f"[LICENZA] Hardware ID: {hw_id[:20]}...")
    
    if not os.path.exists(license_dir):
        try:
            os.makedirs(license_dir)
            print("[LICENZA] Cartella licenza creata")
        except OSError as e:
            print(f"[ERRORE] Creazione cartella licenza: {e}")
            return

    base_url = f"https://api.github.com/repos/gianky00/intelleo-licenses/contents/licenses/{hw_id}"
    token = get_github_token()
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    
    files_map = {
        "config.dat": "config.dat",
        "pyarmor.rkey": "pyarmor.rkey",
        "manifest.json": "manifest.json" 
    }
    
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
                print(f"[LICENZA] ✓ {remote_name} scaricato")
            elif response.status_code == 404:
                print(f"[LICENZA] ⚠ {remote_name} non trovato")
                incomplete_update = True
            elif response.status_code == 401:
                print("[ERRORE] Token autenticazione non valido")
                incomplete_update = True
                break
            else:
                print(f"[AVVISO] {remote_name}: HTTP {response.status_code}")
                incomplete_update = True
                
        except requests.RequestException as e:
            print(f"[AVVISO] Connessione fallita: {e}")
            network_error_occurred = True
            break
            
    if network_error_occurred:
        print("[LICENZA] Modalità offline - verifica periodo di grazia...")
        check_grace_period()
    else:
        if incomplete_update:
            print("[LICENZA] Aggiornamento parziale, file locali mantenuti")
            update_grace_timestamp()
        else:
            try:
                for local_name, content in downloaded_content.items():
                    full_path = os.path.join(license_dir, local_name)
                    with open(full_path, "wb") as f:
                        f.write(content)
                print("[LICENZA] ✓ Aggiornamento completato")
                update_grace_timestamp()
            except OSError as e:
                print(f"[ERRORE] Scrittura file licenza: {e}")

    print("[LICENZA] ══════════════════════════════════════════════")


if __name__ == "__main__":
    try:
        run_update()
    except Exception as e:
        print(f"[ERRORE] Aggiornamento: {e}")
