"""
Intelleo PDF Splitter - App Updater
Gestisce il controllo e la notifica di aggiornamenti dell'applicazione.
"""
import requests
import version
import webbrowser
from tkinter import messagebox
from packaging import version as pkg_version


def check_for_updates(silent=True):
    """
    Controlla se è disponibile una nuova versione dell'applicazione.
    
    Interroga un endpoint JSON con formato:
    {
        "version": "2.0.0",
        "url": "https://example.com/download"
    }
    
    Args:
        silent (bool): Se True, non mostra notifiche se non ci sono aggiornamenti
    """
    url = version.UPDATE_URL
    
    if not url or "example.com" in url:
        if not silent:
            print("[INFO] URL aggiornamenti non configurato")
        return

    try:
        print("[SISTEMA] Controllo aggiornamenti in corso...")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            remote_ver_str = data.get("version")
            download_url = data.get("url")

            if remote_ver_str:
                current_ver = pkg_version.parse(version.__version__)
                remote_ver = pkg_version.parse(remote_ver_str)

                if remote_ver > current_ver:
                    msg = (
                        f"È disponibile una nuova versione!\n\n"
                        f"Versione corrente: {version.__version__}\n"
                        f"Nuova versione: {remote_ver_str}\n\n"
                        f"Vuoi scaricarla ora?"
                    )
                    
                    if messagebox.askyesno("🔄 Aggiornamento Disponibile", msg):
                        if download_url:
                            webbrowser.open(download_url)
                        else:
                            messagebox.showinfo(
                                "ℹ️ Info", 
                                "Visita il sito per scaricare l'aggiornamento."
                            )
                else:
                    print("[SISTEMA] ✓ Applicazione aggiornata")
                    if not silent:
                        messagebox.showinfo(
                            "✅ Aggiornamento",
                            f"L'applicazione è già aggiornata.\n"
                            f"Versione: {version.__version__}"
                        )
        else:
            if not silent:
                print(f"[AVVISO] Errore controllo aggiornamenti: HTTP {response.status_code}")

    except requests.Timeout:
        if not silent:
            print("[AVVISO] Timeout controllo aggiornamenti")
    except requests.RequestException as e:
        if not silent:
            print(f"[AVVISO] Errore connessione: {e}")
    except Exception as e:
        if not silent:
            print(f"[ERRORE] Controllo aggiornamenti: {e}")


if __name__ == "__main__":
    check_for_updates(silent=False)
