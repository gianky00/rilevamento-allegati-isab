"""
Intelleo PDF Splitter - App Updater (PySide6)
Gestisce il controllo e la notifica di aggiornamenti dell'applicazione in modo asincrono e resiliente.
"""

import contextlib
import os
import subprocess
import sys
import tempfile
import time

import requests
from packaging import version as pkg_version
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout

import version

# Variabile globale per memorizzare il percorso dell'installer se l'utente sceglie di installare alla chiusura
_pending_installer_path = None


def get_local_setup_path(url: str) -> str:
    """
    Determina il percorso locale dove salvare o cercare il setup scaricato.
    
    Args:
        url (str): L'URL di download del setup.
        
    Returns:
        str: Il percorso assoluto del file nel sistema temporaneo.
    """
    local_filename = url.split("/")[-1]
    if not local_filename.endswith(".exe"):
        local_filename = "update_setup.exe"
    return os.path.join(tempfile.gettempdir(), local_filename)


class DownloadWorker(QThread):
    """Worker per il download dell'aggiornamento con supporto per la ripresa (resume) infinita."""
    progress = Signal(int, int, float)  # downloaded, total, speed
    finished = Signal(str)              # path del file scaricato
    error = Signal(str)
    retrying = Signal(int)              # numero del tentativo di riconnessione

    def __init__(self, url):
        """Inizializza il worker con l'URL di download."""
        super().__init__()
        self.url = url
        self._is_cancelled = False
        self.max_retries = 999

    def stop(self):
        """Richiede l'interruzione del download."""
        self._is_cancelled = True

    def run(self):
        """Esegue il download con logica di resume che riprova finché non completa."""
        setup_path = get_local_setup_path(self.url)
        
        downloaded = 0
        total_size = 0
        retries = 0
        start_time = time.time()

        # Rimuovi file vecchio solo se è molto vecchio (più di 24 ore)
        if os.path.exists(setup_path):
            if time.time() - os.path.getmtime(setup_path) > 86400:
                with contextlib.suppress(Exception):
                    os.remove(setup_path)

        while not self._is_cancelled:
            try:
                downloaded = os.path.getsize(setup_path) if os.path.exists(setup_path) else 0
                headers = {'Range': f'bytes={downloaded}-'} if downloaded > 0 else {}
                
                session = requests.Session()
                response = session.get(self.url, headers=headers, stream=True, timeout=(10, 30))
                
                if downloaded > 0 and response.status_code != 206:
                    downloaded = 0
                    with open(setup_path, "wb") as f: pass
                
                if response.status_code not in [200, 206]:
                    if response.status_code == 416:
                        if total_size > 0 and downloaded >= total_size:
                            self.finished.emit(setup_path)
                            return
                    raise Exception(f"Server error: {response.status_code}")

                if downloaded == 0:
                    total_size = int(response.headers.get("content-length", 0))
                elif 'Content-Range' in response.headers:
                    total_size = int(response.headers['Content-Range'].split('/')[-1])
                
                mode = "ab" if downloaded > 0 else "wb"
                with open(setup_path, mode) as f:
                    content_iterator = response.iter_content(chunk_size=131072)
                    while True:
                        if self._is_cancelled: return
                        try:
                            chunk = next(content_iterator)
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                self.progress.emit(downloaded, total_size, speed)
                                retries = 0 
                        except StopIteration:
                            break
                
                if total_size > 0 and downloaded >= total_size:
                    self.finished.emit(setup_path)
                    return
                else:
                    raise requests.exceptions.ConnectionError("Stream interrotto")

            except Exception as e:
                if self._is_cancelled: return
                retries += 1
                self.retrying.emit(retries)
                time.sleep(min(retries * 2, 10))


class UpdateProgressDialog(QDialog):
    """Dialogo di progresso per il download dell'aggiornamento."""
    def __init__(self, url, parent=None):
        """Inizializza il dialogo e connette i segnali al worker."""
        super().__init__(parent)
        self.setWindowTitle("Aggiornamento Resiliente")
        self.setFixedSize(450, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setup_ui()
        self.worker = DownloadWorker(url)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.retrying.connect(self.on_retrying)
        
    def setup_ui(self):
        """Configura l'interfaccia grafica del dialogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        self.lbl_status = QLabel("Avvio download...")
        self.lbl_status.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.lbl_status)
        self.pb = QProgressBar()
        self.pb.setFixedHeight(24)
        self.pb.setStyleSheet("QProgressBar { border: 1px solid #CCCCCC; border-radius: 6px; text-align: center; background-color: #F0F0F0; } QProgressBar::chunk { background-color: #0D6EFD; border-radius: 5px; }")
        layout.addWidget(self.pb)
        self.lbl_details = QLabel("Preparazione...")
        self.lbl_details.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.lbl_details)
        self.lbl_retry = QLabel("")
        self.lbl_retry.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_retry.setStyleSheet("color: #DC3545;")
        layout.addWidget(self.lbl_retry)

    def start(self):
        """Mostra il dialogo e avvia il thread del worker."""
        self.show()
        self.worker.start()

    @Slot(int, int, float)
    def update_progress(self, downloaded, total, speed):
        """Aggiorna la barra di progresso."""
        self.lbl_retry.setText("")
        if total > 0:
            self.pb.setMaximum(total)
            self.pb.setValue(downloaded)
            percent = (downloaded / total) * 100
            mb_down = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            speed_mb = speed / (1024 * 1024)
            self.lbl_status.setText(f"Scaricamento: {int(percent)}% completato")
            self.lbl_details.setText(f"{mb_down:.1f} MB di {mb_total:.1f} MB ({speed_mb:.2f} MB/s)")
        else:
            self.pb.setMaximum(0)
            self.lbl_status.setText("Scaricamento in corso...")

    @Slot(int)
    def on_retrying(self, retry_count):
        """Segnala all'utente la riconnessione."""
        self.lbl_retry.setText(f"⚠️ Connessione persa. Tentativo di ripresa #{retry_count}...")

    @Slot(str)
    def on_finished(self, setup_path):
        """Chiede all'utente quando installare l'aggiornamento."""
        self.close()
        show_install_prompt(setup_path, self.parent())

    @Slot(str)
    def on_error(self, err_msg):
        """Gestisce errori fatali."""
        self.close()
        QMessageBox.critical(self.parent() or None, "Errore", f"Download interrotto: {err_msg}")


def show_install_prompt(setup_path, parent=None):
    """Mostra la scelta tra installazione immediata o ritardata."""
    global _pending_installer_path
    msg_box = QMessageBox(parent or None)
    msg_box.setWindowTitle("🔄 Aggiornamento Pronto")
    msg_box.setText("L'aggiornamento è stato scaricato ed è pronto per l'installazione.\n\nCosa desideri fare?")
    msg_box.setIcon(QMessageBox.Icon.Question)
    btn_now = msg_box.addButton("Installa Ora", QMessageBox.ButtonRole.AcceptRole)
    btn_later = msg_box.addButton("Alla Chiusura", QMessageBox.ButtonRole.ActionRole)
    msg_box.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)
    msg_box.exec()
    if msg_box.clickedButton() == btn_now:
        _run_installer_and_exit(setup_path)
    elif msg_box.clickedButton() == btn_later:
        _pending_installer_path = setup_path
        QMessageBox.information(parent or None, "ℹ️ Info", "L'aggiornamento partirà automaticamente alla chiusura dell'app.")


def _run_installer_and_exit(setup_path):
    """Esegue l'installer e termina il processo."""
    if os.path.exists(setup_path):
        subprocess.Popen([setup_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])
        sys.exit(0)


def run_pending_installer():
    """Esegue l'installer memorizzato alla chiusura dell'app."""
    global _pending_installer_path
    if _pending_installer_path and os.path.exists(_pending_installer_path):
        subprocess.Popen([_pending_installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])


def check_for_updates(silent=True, on_confirm=None):
    """Controlla aggiornamenti, gestendo anche file parziali o già scaricati."""
    url = version.UPDATE_URL
    if not url or "example.com" in url: return

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            remote_ver_str = data.get("version")
            download_url = data.get("url")
            if not remote_ver_str or not download_url: return

            if pkg_version.parse(remote_ver_str) > pkg_version.parse(version.__version__):
                setup_path = get_local_setup_path(download_url)
                
                # Ottieni dimensione remota per confronto
                remote_size = 0
                with contextlib.suppress(Exception):
                    head_resp = requests.head(download_url, timeout=5)
                    remote_size = int(head_resp.headers.get("content-length", 0))

                is_complete = False
                local_size = os.path.getsize(setup_path) if os.path.exists(setup_path) else 0
                
                if remote_size > 0 and local_size >= remote_size:
                    is_complete = True

                if is_complete:
                    show_install_prompt(setup_path)
                else:
                    if local_size > 0 and remote_size > 0:
                        percent = (local_size / remote_size) * 100
                        msg = f"Rilevato download parziale ({int(percent)}%) della versione {remote_ver_str}.\n\nVuoi completare lo scaricamento ora?"
                    else:
                        msg = f"Nuova versione {remote_ver_str} disponibile!\n\nVuoi scaricarla ora?"
                    
                    reply = QMessageBox.question(None, "🔄 Aggiornamento", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        if on_confirm: on_confirm()
                        perform_auto_update(download_url)
            elif not silent:
                QMessageBox.information(None, "✅ OK", f"L'app è aggiornata (v{version.__version__})")
    except Exception as e:
        if not silent: QMessageBox.warning(None, "Errore", str(e))


def perform_auto_update(download_url):
    """Inizia il download asincrono."""
    parent = None
    for widget in QApplication.topLevelWidgets():
        if widget.isWindow() and not widget.parent():
            parent = widget
            break
    global _active_update_dialog
    _active_update_dialog = UpdateProgressDialog(download_url, parent)
    _active_update_dialog.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_for_updates(silent=False)
    sys.exit(app.exec())
