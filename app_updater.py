"""
Intelleo PDF Splitter - App Updater
Gestisce il controllo e la notifica di aggiornamenti dell'applicazione.
"""
import requests
import version
import webbrowser
from tkinter import messagebox
from packaging import version as pkg_version
import tempfile
import subprocess
import sys
import os
import tkinter as tk
from tkinter import ttk


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
                        f"Vuoi scaricarla e installarla ora?"
                    )
                    
                    if messagebox.askyesno("🔄 Aggiornamento Disponibile", msg):
                        if download_url:
                            perform_auto_update(download_url)
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


def perform_auto_update(download_url):
    """
    Scarica e installa automaticamente l'aggiornamento.
    """
    try:
        # Crea finestra di progresso
        progress_win = tk.Toplevel()
        progress_win.title("Download Aggiornamento")
        progress_win.geometry("350x150")
        progress_win.resizable(False, False)

        # Centra finestra
        progress_win.update_idletasks()
        x = (progress_win.winfo_screenwidth() - progress_win.winfo_width()) // 2
        y = (progress_win.winfo_screenheight() - progress_win.winfo_height()) // 2
        progress_win.geometry(f"+{x}+{y}")

        lbl = ttk.Label(progress_win, text="Scaricamento aggiornamento in corso...", font=('Segoe UI', 10))
        lbl.pack(pady=20)

        pb = ttk.Progressbar(progress_win, mode='indeterminate', length=280)
        pb.pack(pady=10)
        pb.start(10)

        progress_win.update()

        # Scarica file in temp
        local_filename = download_url.split('/')[-1]
        if not local_filename.endswith('.exe'):
            local_filename = "update_setup.exe"

        temp_dir = tempfile.gettempdir()
        setup_path = os.path.join(temp_dir, local_filename)

        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        with open(setup_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress_win.update()

        progress_win.destroy()

        # Lancia installer in modo silenzioso e chiudi app
        # /SILENT -> mostra progresso ma non chiede input
        # /CLOSEAPPLICATIONS -> tenta di chiudere le app in uso (noi)
        subprocess.Popen([setup_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])

        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Errore Aggiornamento", f"Impossibile completare l'aggiornamento:\n{e}")


if __name__ == "__main__":
    check_for_updates(silent=False)
