import os
import requests
import license_validator
import sys

def get_github_token():
    """
    Reconstructs the obfuscated GitHub token.
    """
    p1 = "ghp_Y3HKJIcBbI"
    p2 = "LsRP039ymKyF"
    p3 = "YdxrEK0U2R2kFZ"
    return p1 + p2 + p3

def run_update():
    """
    Checks for license updates on GitHub matching the Hardware ID.
    Downloads config.dat, pyarmor.rkey, and manifest (as manifest.json).
    """
    try:
        print("Controllo aggiornamenti licenza in corso...")

        # 1. Get Hardware ID
        hw_id = license_validator.get_hardware_id()

        # 2. Setup Paths
        # Use license_validator logic to find Licenza dir
        paths = license_validator._get_license_paths()
        license_dir = paths["dir"]

        if not os.path.exists(license_dir):
            try:
                os.makedirs(license_dir)
            except OSError as e:
                print(f"Errore creazione cartella Licenza: {e}")
                return

        # 3. GitHub Configuration
        # Construct URL using the HWID.
        # Note: HWID should match the folder name in the repo exactly.
        base_url = f"https://raw.githubusercontent.com/gianky00/intelleo-licenses/main/licenses/{hw_id}"
        token = get_github_token()
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw"
        }

        # Map remote filename -> local filename
        files_map = {
            "config.dat": "config.dat",
            "pyarmor.rkey": "pyarmor.rkey",
            "manifest": "manifest.json"
        }

        downloaded_files = {}

        # 4. Download Loop
        for remote_name, local_name in files_map.items():
            url = f"{base_url}/{remote_name}"
            try:
                # Use a timeout to avoid hanging
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    downloaded_files[local_name] = response.content
                else:
                    print(f"File {remote_name} non trovato o errore (Status: {response.status_code})")
                    # Implicitly: if files are not found, we assume no update is available or HWID not matched.
                    # We abort the update to avoid partial states or overwriting with nothing.
                    return
            except requests.RequestException as e:
                print(f"Errore di connessione per {remote_name}: {e}")
                return # Stop update on network error

        # 5. Save Files
        print("Scaricamento completato. Aggiornamento file locali...")
        for local_name, content in downloaded_files.items():
            full_path = os.path.join(license_dir, local_name)
            try:
                with open(full_path, "wb") as f:
                    f.write(content)
                print(f"Aggiornato: {local_name}")
            except OSError as e:
                print(f"Errore scrittura {local_name}: {e}")

    except Exception as e:
        print(f"Errore imprevisto durante l'aggiornamento licenza: {e}")

if __name__ == "__main__":
    run_update()
