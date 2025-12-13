import requests
import version
import webbrowser
import tkinter as tk
from tkinter import messagebox
from packaging import version as pkg_version

def check_for_updates(silent=True):
    """
    Checks if a newer version of the application is available.
    Expects a JSON at UPDATE_URL with format: {"version": "1.0.1", "url": "..."}
    """
    url = version.UPDATE_URL
    if not url or "example.com" in url:
        if not silent:
            print("Update URL not configured.")
        return

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            remote_ver_str = data.get("version")
            download_url = data.get("url")

            if remote_ver_str:
                current_ver = pkg_version.parse(version.__version__)
                remote_ver = pkg_version.parse(remote_ver_str)

                if remote_ver > current_ver:
                    msg = f"È disponibile una nuova versione ({remote_ver_str}).\nVersione attuale: {version.__version__}\n\nVuoi scaricarla ora?"
                    if messagebox.askyesno("Aggiornamento Disponibile", msg):
                        if download_url:
                            webbrowser.open(download_url)
                        else:
                            messagebox.showinfo("Info", "Visita il sito per scaricare l'aggiornamento.")
                else:
                    if not silent:
                        messagebox.showinfo("Aggiornamento", "L'applicazione è aggiornata.")
        else:
            if not silent:
                print(f"Errore controllo aggiornamenti: {response.status_code}")

    except Exception as e:
        if not silent:
            print(f"Eccezione controllo aggiornamenti: {e}")

if __name__ == "__main__":
    # Test
    check_for_updates(silent=False)
