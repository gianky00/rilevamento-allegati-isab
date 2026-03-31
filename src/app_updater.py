"""
Intelleo PDF Splitter - App Updater (PySide6)
Gestisce l'controllo e la notifica di aggiornamenti dell'applicazione.
Confronta le versioni tra Rete Locale e Web, scegliendo la più recente o privilegiando la LAN.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import requests
from packaging import version as pkg_version
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout, QWidget

import version

# Variabile globale per memorizzare il percorso dell'installer se l'utente sceglie di installare alla chiusura
_pending_installer_path = None


def get_local_setup_path(url_or_path: str) -> str:
    """Determina il percorso locale dove salvare o cercare il setup scaricato."""
    local_filename = url_or_path.replace("\\", "/").split("/")[-1]
    if not local_filename.lower().endswith(".exe"):
        local_filename = "update_setup.exe"
    return os.path.join(tempfile.gettempdir(), local_filename)


class DownloadWorker(QThread):
    """Worker per il download/copia dell'aggiornamento."""
    progress = Signal(int, int, float)  # downloaded, total, speed
    finished = Signal(str)              # path del file scaricato
    error = Signal(str)
    retrying = Signal(int)              # numero del tentativo di riconnessione

    def __init__(self, source_path: str):
        """Inizializza il worker con la sorgente (URL o Path)."""
        super().__init__()
        self.source = source_path
        self._is_cancelled = False

    def stop(self) -> None:
        """Richiede l'interruzione del download."""
        self._is_cancelled = True

    def run(self) -> None:
        """Esegue il download via HTTP o copia via FileSystem."""
        target_path = Path(get_local_setup_path(self.source))

        # Caso 1: Percorso di RETE Locale (UNC o Path locale)
        source_path = Path(self.source)
        if source_path.exists() and not self.source.lower().startswith("http"):
            try:
                total_size = source_path.stat().st_size
                chunk_size = 1024 * 1024  # 1MB
                downloaded = 0
                start_time = time.time()

                with source_path.open("rb") as fsrc, target_path.open("wb") as fdst:
                    while not self._is_cancelled:
                        buf = fsrc.read(chunk_size)
                        if not buf:
                            break
                        fdst.write(buf)
                        downloaded += len(buf)
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        self.progress.emit(downloaded, total_size, speed)

                if not self._is_cancelled:
                    self.finished.emit(str(target_path))
                return
            except Exception as e:
                self.error.emit(f"Errore copia rete: {e}")
                return

        # Caso 2: URL WEB (Netlify)
        downloaded = target_path.stat().st_size if target_path.exists() else 0
        total_size = 0
        retries = 0
        start_time = time.time()

        while not self._is_cancelled:
            try:
                headers = {'Range': f'bytes={downloaded}-'} if downloaded > 0 else {}
                session = requests.Session()
                response = session.get(self.source, headers=headers, stream=True, timeout=(10, 30))

                if downloaded > 0 and response.status_code != 206:
                    downloaded = 0
                    with target_path.open("wb") as f:
                        pass

                if response.status_code not in (200, 206):
                    if response.status_code == 416 and total_size > 0 and downloaded >= total_size:
                        self.finished.emit(str(target_path))
                        return
                    raise Exception(f"Server error: {response.status_code}")

                if downloaded == 0:
                    total_size = int(response.headers.get("content-length", 0))
                elif 'Content-Range' in response.headers:
                    total_size = int(response.headers['Content-Range'].split('/')[-1])

                mode = "ab" if downloaded > 0 else "wb"
                with target_path.open(mode) as f:
                    content_iterator = response.iter_content(chunk_size=131072)
                    while True:
                        if self._is_cancelled:
                            return
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
                    self.finished.emit(str(target_path))
                    return
                raise requests.exceptions.ConnectionError("Stream interrotto")

            except Exception:
                if self._is_cancelled:
                    return
                retries += 1
                self.retrying.emit(retries)
                time.sleep(min(retries * 2, 10))


class UpdateProgressDialog(QDialog):
    """Dialogo che mostra l'avanzamento dello scaricamento dell'aggiornamento."""

    def __init__(self, source: str, parent: QWidget | None = None):
        """Inizializza il dialogo e il worker di download."""
        super().__init__(parent)
        self.setWindowTitle("Aggiornamento Intelligente")
        self.setFixedSize(450, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setup_ui()
        self.worker = DownloadWorker(source)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.retrying.connect(self.on_retrying)

    def setup_ui(self) -> None:
        """Configura gli elementi grafici del dialogo."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        self.lbl_status = QLabel("Avvio scaricamento...")
        self.lbl_status.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.lbl_status)
        self.pb = QProgressBar()
        self.pb.setFixedHeight(24)
        self.pb.setStyleSheet("QProgressBar { border: 1px solid #CCC; border-radius: 6px; text-align: center; background: #F0F0F0; } QProgressBar::chunk { background: #0D6EFD; border-radius: 5px; }")
        layout.addWidget(self.pb)
        self.lbl_details = QLabel("Preparazione...")
        self.lbl_details.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.lbl_details)
        self.lbl_retry = QLabel("")
        self.lbl_retry.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_retry.setStyleSheet("color: #DC3545;")
        layout.addWidget(self.lbl_retry)

    def start(self) -> None:
        """Mostra il dialogo e avvia il thread di download."""
        self.show()
        self.worker.start()

    @Slot(int, int, float)
    def update_progress(self, downloaded: int, total: int, speed: float) -> None:
        """Aggiorna la barra di progresso e le etichette informative."""
        self.lbl_retry.setText("")
        if total > 0:
            self.pb.setMaximum(total)
            self.pb.setValue(downloaded)
            percent = (downloaded / total) * 100
            mb_down = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            speed_mb = speed / (1024 * 1024)
            self.lbl_status.setText(f"Avanzamento: {int(percent)}% completato")
            self.lbl_details.setText(f"{mb_down:.1f} MB di {mb_total:.1f} MB ({speed_mb:.2f} MB/s)")
        else:
            self.pb.setMaximum(0)

    @Slot(int)
    def on_retrying(self, count: int) -> None:
        """Gestisce la visualizzazione dei tentativi di riconnessione."""
        self.lbl_retry.setText(f"⚠️ Tentativo di ripresa #{count}...")

    @Slot(str)
    def on_finished(self, path: str) -> None:
        """Chiude il dialogo e chiede conferma per l'installazione."""
        self.close()
        show_install_prompt(path, self.parent())

    @Slot(str)
    def on_error(self, err: str) -> None:
        """Chiude il dialogo e mostra l'errore avvenuto durante il download."""
        self.close()
        parent = self.parent()
        parent_widget = parent if isinstance(parent, QWidget) else None
        QMessageBox.critical(parent_widget, "Errore", f"Aggiornamento fallito: {err}")


def show_install_prompt(path: str, parent: Any = None) -> None:
    """Chiede all'utente se installare subito l'aggiornamento o alla chiusura."""
    global _pending_installer_path
    msg = QMessageBox(parent if isinstance(parent, QWidget) else None)
    msg.setWindowTitle("🔄 Aggiornamento Pronto")
    msg.setText("L'aggiornamento è stato scaricato correttamente.\n\nCosa desideri fare?")
    msg.setIcon(QMessageBox.Icon.Question)
    btn_now = msg.addButton("Installa Ora", QMessageBox.ButtonRole.AcceptRole)
    btn_later = msg.addButton("Alla Chiusura", QMessageBox.ButtonRole.ActionRole)
    msg.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)
    msg.exec()
    if msg.clickedButton() == btn_now:
        _run_installer_and_exit(path)
    elif msg.clickedButton() == btn_later:
        _pending_installer_path = path
        QMessageBox.information(parent if isinstance(parent, QWidget) else None, "Info", "L'aggiornamento verrà eseguito alla chiusura dell'applicazione.")


def _run_installer_and_exit(path: str) -> None:
    """Avvia l'installer in modalità silenziosa e chiude l'app corrente."""
    if Path(path).exists():
        subprocess.Popen([path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])
        sys.exit(0)


def run_pending_installer() -> None:
    """Esegue l'installer memorizzato alla chiusura dell'app."""
    global _pending_installer_path
    if _pending_installer_path and Path(_pending_installer_path).exists():
        subprocess.Popen([_pending_installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/FORCESTART"])


def get_metadata_from_network() -> dict[str, Any] | None:
    """Recupera metadati dalla rete locale."""
    net_json = Path(version.NETWORK_UPDATE_PATH) / "version.json"
    if net_json.exists():
        with suppress(Exception):
            data = json.loads(net_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["url"] = str(Path(version.NETWORK_UPDATE_PATH) / data["url"])
                data["source"] = "Rete Locale"
                return data
    return None


def get_metadata_from_web() -> dict[str, Any] | None:
    """Recupera metadati dal web (Netlify)."""
    with suppress(Exception):
        resp = requests.get(version.UPDATE_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                data["source"] = "Web (Netlify)"
                return data
    return None


def check_for_updates(silent: bool = True, on_confirm: Any = None) -> None:
    """Controlla aggiornamenti confrontando Rete e Web, privilegiando la più recente o la LAN."""
    net_data = get_metadata_from_network()
    web_data = get_metadata_from_web()

    best_update = None

    if net_data and web_data:
        v_net = pkg_version.parse(net_data["version"])
        v_web = pkg_version.parse(web_data["version"])

        if v_net >= v_web:
            best_update = net_data
        else:
            best_update = web_data
    elif net_data:
        best_update = net_data
    elif web_data:
        best_update = web_data

    if not best_update:
        if not silent:
            QMessageBox.information(None, "Info", "Nessuna sorgente di aggiornamento raggiungibile.")
        return

    remote_v_str = best_update.get("version")
    download_source = best_update.get("url")
    source_name = best_update.get("source")

    if remote_v_str and pkg_version.parse(remote_v_str) > pkg_version.parse(version.__version__):
        msg = f"Disponibile versione {remote_v_str} ({source_name}).\n\nVuoi scaricare l'aggiornamento?"
        reply = QMessageBox.question(None, "🔄 Aggiornamento", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if on_confirm:
                on_confirm()
            if download_source:
                perform_auto_update(str(download_source))
    elif not silent:
        QMessageBox.information(None, "✅ OK", f"L'app è aggiornata (v{version.__version__})")


def perform_auto_update(source: str) -> None:
    """Inizia la procedura di aggiornamento automatico."""
    parent = next((w for w in QApplication.topLevelWidgets() if w.isWindow() and not w.parent()), None)
    dialog = UpdateProgressDialog(source, parent if isinstance(parent, QWidget) else None)
    dialog.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_for_updates(silent=False)
    sys.exit(app.exec())
