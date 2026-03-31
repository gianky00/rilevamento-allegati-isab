"""
Intelleo PDF Splitter - Application Logger
Sistema di logging robusto che scrive su file per diagnostica.
DEVE essere importato PRIMA di qualsiasi altro modulo.

IMPORTANTE: Questo modulo scrive IMMEDIATAMENTE su file per garantire
la cattura di errori anche in caso di crash immediato.
"""

import logging
import os
import re
import sys
import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path

# Costante per il nome dell'applicazione
APP_NAME = "Intelleo PDF Splitter"


def save_bot_html(html_content: str, filename: str) -> str:
    """
    Salva il sorgente HTML di un bot dopo averlo sanificato (Pillar 4).
    Previene l'esecuzione di script durante il debug dei log.
    """
    try:
        from shared.security_utils import sanitize_html
        log_dir = Path(get_log_directory()) / "bot_html"
        log_dir.mkdir(parents=True, exist_ok=True)

        sanitized = sanitize_html(html_content)
        file_path = log_dir / filename

        file_path.write_text(sanitized, encoding="utf-8")
        return str(file_path)
    except Exception as e:
        _write_immediate(f"Errore salvataggio HTML bot: {e}")
        return ""

# Variabile globale per tracciare lo stato
_initialized = False
_log_path = None
_immediate_log_file = None


def _safe_print(message):
    """Print sicuro che non fallisce se stdout non è disponibile."""
    with suppress(Exception):
        if sys.stdout is not None:
            pass


def _write_immediate(message):
    """Scrive immediatamente su file senza buffering."""
    global _immediate_log_file
    if _immediate_log_file:
        with suppress(Exception):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _immediate_log_file.write(f"{timestamp} | {message}\n")
            _immediate_log_file.flush()
            os.fsync(_immediate_log_file.fileno())


def get_log_directory():
    """Ottiene la directory dei log in base al sistema operativo."""
    if sys.platform == "win32":
        # Windows: %APPDATA%\Intelleo PDF Splitter\Log
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home())
        log_dir = Path(appdata) / APP_NAME / "Log"
    else:
        # Linux/Mac: ~/.intelleo-pdf-splitter/log
        log_dir = Path.home() / ".intelleo-pdf-splitter" / "log"

    return str(log_dir)


def get_app_directory():
    """Ottiene la directory dell'applicazione."""
    if getattr(sys, "frozen", False):
        # Eseguibile compilato (Nuitka/PyInstaller)
        return str(Path(sys.executable).parent)
    # Script Python
    return str(Path(__file__).resolve().parent)


def setup_logging():
    """
    Configura il sistema di logging.
    Questa funzione DEVE essere chiamata PRIMA di qualsiasi altra operazione.

    Returns:
        str: Percorso del file di log
    """
    global _immediate_log_file, _log_path

    log_dir = get_log_directory()
    app_dir = get_app_directory()

    # Nome file log con formato Log_DD_MM_YYYY.log
    log_filename = f"Log_{datetime.now().strftime('%d_%m_%Y')}.log"

    # Lista di directory da provare in ordine
    dirs_to_try = [Path(log_dir), Path(app_dir), Path.home(), Path.cwd()]

    actual_log_path = None

    # Prova a creare il file di log in una delle directory
    for try_dir in dirs_to_try:
        try:
            try_dir.mkdir(parents=True, exist_ok=True)
            test_path = try_dir / log_filename
            # Prova ad aprire il file per verificare i permessi
            _immediate_log_file = test_path.open("a", encoding="utf-8", buffering=1)
            actual_log_path = str(test_path)
            _write_immediate(f"LOG FILE INIZIALIZZATO: {test_path}")
            _write_immediate(f"Frozen: {getattr(sys, 'frozen', False)}")
            _write_immediate(f"Executable: {sys.executable}")
            break
        except Exception:
            continue

    if actual_log_path is None:
        # Fallback estremo: scrivi nella temp
        with suppress(Exception):
            import tempfile

            temp_dir = Path(tempfile.gettempdir())
            test_path = temp_dir / log_filename
            _immediate_log_file = test_path.open("a", encoding="utf-8", buffering=1)
            actual_log_path = str(test_path)
            _write_immediate(f"LOG FILE (FALLBACK TEMP): {actual_log_path}")

    _log_path = actual_log_path

    # Configura il logger root
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Rimuovi handler esistenti
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Formatter comune
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler usando lo stesso path già aperto
    if actual_log_path:
        try:
            file_handler = logging.FileHandler(actual_log_path, encoding="utf-8", mode="a")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            _write_immediate("FileHandler logging configurato con successo")
        except Exception as e:
            _write_immediate(f"ERRORE FileHandler: {e}")
            file_handler = None
    else:
        file_handler = None

    # Se non siamo riusciti a creare un file handler, prova con NullHandler
    if file_handler is None:
        logger.addHandler(logging.NullHandler())
        actual_log_path = None

    # Console handler - solo se stdout e' disponibile
    with suppress(Exception):
        if sys.stdout is not None and hasattr(sys.stdout, "write"):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

    return actual_log_path


def setup_exception_handler():
    """
    Configura un handler globale per le eccezioni non gestite.
    """

    def exception_handler(exc_type, exc_value, exc_traceback):
        """Handler globale per eccezioni non gestite."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Non loggare Ctrl+C
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Scrivi immediatamente su file aperto
        _write_immediate(f"!!! CRASH !!! {exc_type.__name__}: {exc_value}")

        logger = logging.getLogger("CRASH")
        logger.critical("Eccezione non gestita!", exc_info=(exc_type, exc_value, exc_traceback))

        # Scrivi anche su file dedicato per crash
        crash_dirs = [Path(get_log_directory()), Path(get_app_directory()), Path.home()]
        for crash_dir in crash_dirs:
            try:
                crash_dir.mkdir(parents=True, exist_ok=True)
                crash_file = crash_dir / f"Crash_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.log"
                with crash_file.open("w", encoding="utf-8") as f:
                    f.write(f"CRASH REPORT - {APP_NAME}\n")
                    f.write(f"{'=' * 60}\n")
                    f.write(f"Data/Ora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Python: {sys.version}\n")
                    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                    f.write(f"Executable: {sys.executable}\n")
                    f.write(f"Working Dir: {Path.cwd()}\n")
                    f.write(f"{'=' * 60}\n\n")
                    f.write("TRACEBACK:\n")
                    traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                _write_immediate(f"Crash file scritto: {crash_file}")
                break
            except Exception:
                continue

    sys.excepthook = exception_handler


def log_startup_info():
    """Logga informazioni di avvio per diagnostica."""
    logger = logging.getLogger("STARTUP")
    logger.info("=" * 60)
    logger.info(f"{APP_NAME} - AVVIO APPLICAZIONE")
    logger.info("=" * 60)
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"Working Directory: {Path.cwd()}")
    logger.info(f"App Directory: {get_app_directory()}")
    logger.info(f"Log Directory: {get_log_directory()}")

    # Log delle variabili d'ambiente rilevanti
    logger.debug(f"APPDATA: {os.environ.get('APPDATA', 'N/A')}")
    logger.debug(f"PATH (first 200 chars): {os.environ.get('PATH', 'N/A')[:200]}...")

    logger.info("-" * 60)


def initialize():
    """
    Inizializza il sistema di logging.
    Chiamare all'inizio di main.py PRIMA di qualsiasi altro import.

    Returns:
        str: Percorso del file di log (o None se non disponibile)
    """
    global _log_path
    _log_path = setup_logging()
    setup_exception_handler()
    log_startup_info()

    # Log il percorso del file di log
    logger = logging.getLogger("STARTUP")
    if _log_path:
        logger.info(f"Log file: {_log_path}")
    else:
        logger.warning("Impossibile creare file di log")

    return _log_path


def get_log_path():
    """Restituisce il percorso del file di log corrente."""
    return _log_path


def shutdown_logging():
    """
    Chiude tutti gli handler di logging e il file di log immediato.
    Da usare principalmente per cleanup durante i test o alla chiusura dell'app.
    """
    global _immediate_log_file, _log_path, _initialized

    # 1. Chiudi e rimuovi gli handler del logging standard
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        with suppress(Exception):
            handler.close()
            logger.removeHandler(handler)

    # 2. Chiudi il file di log immediato
    if _immediate_log_file:
        with suppress(Exception):
            _immediate_log_file.flush()
            os.fsync(_immediate_log_file.fileno())
            _immediate_log_file.close()
        _immediate_log_file = None

    # 3. Reset variabili globali
    _log_path = None
    _initialized = False


# Test standalone
if __name__ == "__main__":
    log_path = initialize()
    logger = logging.getLogger("TEST")
    logger.info("Test del sistema di logging")
    logger.debug("Messaggio di debug")
    logger.warning("Messaggio di warning")
    logger.error("Messaggio di errore")
