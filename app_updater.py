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


def check_for_updates(silent=True, on_confirm=None):
    """
    Controlla se è disponibile una nuova versione dell'applicazione.
    
    Interroga un endpoint JSON con formato:
    {
        "version": "2.0.0",
        "url": "https://example.com/download"
    }
    
    Args:
        silent (bool): Se True, non mostra notifiche se non ci sono aggiornamenti
        on_confirm (callable): Funzione da chiamare se l'utente conferma l'aggiornamento (es. salvataggio)
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
                        f"L'applicazione verrà chiusa e riavviata automaticamente.\n"
                        f"Vuoi procedere con l'aggiornamento?"
                    )
                    
                    if messagebox.askyesno("🔄 Aggiornamento Disponibile", msg):
                        if on_confirm:
                            try:
                                on_confirm()
                                print("[AGGIORNAMENTO] Salvataggio automatico completato.")
                            except Exception as e:
                                print(f"[ERRORE] Callback salvataggio: {e}")

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
    Scarica e installa automaticamente l'aggiornamento con barra di avanzamento reale.
    """
    try:
        # Crea finestra di progresso
        progress_win = tk.Toplevel()
        progress_win.title("Download Aggiornamento")
        progress_win.geometry("400x180")
        progress_win.resizable(False, False)
        progress_win.attributes("-topmost", True)  # Sempre in primo piano

        # Centra finestra
        progress_win.update_idletasks()
        x = (progress_win.winfo_screenwidth() - progress_win.winfo_width()) // 2
        y = (progress_win.winfo_screenheight() - progress_win.winfo_height()) // 2
        progress_win.geometry(f"+{x}+{y}")

        lbl = ttk.Label(progress_win, text="Inizializzazione download...", font=('Segoe UI', 10))
        lbl.pack(pady=(20, 10))

        # Barra determinata
        pb = ttk.Progressbar(progress_win, mode='determinate', length=320)
        pb.pack(pady=5)

        # Label per dettagli (es. 45% - 10MB / 20MB)
        details_lbl = ttk.Label(progress_win, text="", font=('Segoe UI', 9), foreground="#666666")
        details_lbl.pack(pady=5)

        progress_win.update()

        # Scarica file in temp
        local_filename = download_url.split('/')[-1]
        if not local_filename.endswith('.exe'):
            local_filename = "update_setup.exe"

        temp_dir = tempfile.gettempdir()
        setup_path = os.path.join(temp_dir, local_filename)

        # Richiesta con stream
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # Ottieni dimensione totale
        total_size = int(response.headers.get('content-length', 0))
        pb['maximum'] = total_size if total_size > 0 else 100

        downloaded = 0
        chunk_size = 8192

        with open(setup_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Aggiorna UI
                    pb['value'] = downloaded

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        lbl.config(text=f"Scaricamento in corso: {int(percent)}%")
                        details_lbl.config(text=f"{mb_down:.1f} MB / {mb_total:.1f} MB")
                    else:
                        # Fallback se content-length manca
                        mb_down = downloaded / (1024 * 1024)
                        lbl.config(text="Scaricamento in corso...")
                        details_lbl.config(text=f"{mb_down:.1f} MB scaricati")

                    progress_win.update()

        progress_win.destroy()

        # Lancia installer in modo silenzioso e chiudi app
        # /SILENT -> mostra progresso ma non chiede input
        # /CLOSEAPPLICATIONS -> tenta di chiudere le app in uso (noi)
        # /FORCESTART -> flag custom per riavviare l'app alla fine (gestito dallo script Inno Setup)
        subprocess.Popen([setup_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])

        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Errore Aggiornamento", f"Impossibile completare l'aggiornamento:\n{e}")


if __name__ == "__main__":
    check_for_updates(silent=False)
