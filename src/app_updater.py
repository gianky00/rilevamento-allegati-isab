"""
Intelleo PDF Splitter - App Updater (PySide6)
Gestisce il controllo e la notifica di aggiornamenti dell'applicazione.
"""
import requests
import version
import webbrowser
from packaging import version as pkg_version
import tempfile
import subprocess
import sys
import os
import time

from PySide6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


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

                    reply = QMessageBox.question(
                        None,
                        "🔄 Aggiornamento Disponibile",
                        msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        if on_confirm:
                            try:
                                on_confirm()
                                print("[AGGIORNAMENTO] Salvataggio automatico completato.")
                            except Exception as e:
                                print(f"[ERRORE] Callback salvataggio: {e}")

                        if download_url:
                            perform_auto_update(download_url)
                        else:
                            QMessageBox.information(
                                None,
                                "ℹ️ Info",
                                "Visita il sito per scaricare l'aggiornamento."
                            )
                else:
                    print("[SISTEMA] ✓ Applicazione aggiornata")
                    if not silent:
                        QMessageBox.information(
                            None,
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
        progress_win = QDialog()
        progress_win.setWindowTitle("Download Aggiornamento")
        progress_win.setFixedSize(400, 180)
        progress_win.setWindowFlags(
            progress_win.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # Rimuovi pulsante chiudi (non deve chiudere durante il download)
        progress_win.setWindowFlags(
            progress_win.windowFlags()
            & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(progress_win)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Label stato
        lbl = QLabel("Inizializzazione download...")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        # Barra di progresso
        pb = QProgressBar()
        pb.setMinimum(0)
        pb.setMaximum(100)
        pb.setValue(0)
        pb.setFixedHeight(22)
        pb.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                text-align: center;
                background-color: #E0E0E0;
            }
            QProgressBar::chunk {
                background-color: #198754;
                border-radius: 3px;
            }
        """)
        layout.addWidget(pb)

        # Label dettagli
        details_lbl = QLabel("")
        details_lbl.setFont(QFont("Segoe UI", 9))
        details_lbl.setStyleSheet("color: #666666;")
        details_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(details_lbl)

        # Centra la finestra sullo schermo
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - 400) // 2 + screen_geo.x()
            y = (screen_geo.height() - 180) // 2 + screen_geo.y()
            progress_win.move(x, y)

        progress_win.show()
        QApplication.processEvents()

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
        if total_size > 0:
            pb.setMaximum(total_size)

        downloaded = 0
        chunk_size = 8192
        start_time = time.time()

        with open(setup_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Aggiorna UI
                    pb.setValue(downloaded)

                    elapsed_time = time.time() - start_time
                    speed = downloaded / elapsed_time if elapsed_time > 0 else 0

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_down = downloaded / (1024 * 1024)

                        # Stima tempo rimanente
                        remaining_bytes = total_size - downloaded
                        remaining_time = remaining_bytes / speed if speed > 0 else 0

                        if remaining_time < 60:
                            eta_str = f"{int(remaining_time)}s"
                        else:
                            eta_str = f"{int(remaining_time // 60)}m {int(remaining_time % 60)}s"

                        lbl.setText(f"Scaricamento in corso... ({int(percent)}%) - ETA: {eta_str}")
                        details_lbl.setText(f"{mb_down:.1f} MB scaricati")
                    else:
                        mb_down = downloaded / (1024 * 1024)
                        lbl.setText("Scaricamento in corso...")
                        details_lbl.setText(f"{mb_down:.1f} MB scaricati")

                    QApplication.processEvents()

        progress_win.close()

        # Lancia installer in modo silenzioso e chiudi app
        subprocess.Popen([setup_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])

        sys.exit(0)

    except Exception as e:
        QMessageBox.critical(
            None,
            "Errore Aggiornamento",
            f"Impossibile completare l'aggiornamento:\n{e}"
        )


if __name__ == "__main__":
    check_for_updates(silent=False)
