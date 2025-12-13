"""
Intelleo PDF Splitter - Application Logger
Sistema di logging robusto che scrive su file per diagnostica.
DEVE essere importato PRIMA di qualsiasi altro modulo.
"""
import os
import sys
import logging
import traceback
from datetime import datetime

# Directory per i log
def get_log_directory():
    """Ottiene la directory dei log in base al sistema operativo."""
    if sys.platform == 'win32':
        # Windows: %APPDATA%\Intelleo PDF Splitter\Log
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_dir = os.path.join(appdata, 'Intelleo PDF Splitter', 'Log')
    else:
        # Linux/Mac: ~/.intelleo-pdf-splitter/log
        log_dir = os.path.join(os.path.expanduser('~'), '.intelleo-pdf-splitter', 'log')
    
    return log_dir

def setup_logging():
    """
    Configura il sistema di logging.
    Questa funzione DEVE essere chiamata PRIMA di qualsiasi altra operazione.
    """
    log_dir = get_log_directory()
    
    # Crea la directory se non esiste
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        # Se non riusciamo a creare la directory, proviamo nella directory corrente
        log_dir = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(sys.executable)
    
    # Nome file log con data
    log_filename = f"intelleo_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # Configura il logger root
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Rimuovi handler esistenti
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler con rotazione giornaliera
    try:
        file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback: prova a scrivere accanto all'eseguibile
        try:
            fallback_path = os.path.join(
                os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__),
                'error.log'
            )
            file_handler = logging.FileHandler(fallback_path, encoding='utf-8', mode='a')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except:
            pass
    
    # Console handler (solo se non frozen o se console disponibile)
    if not getattr(sys, 'frozen', False) or sys.stdout is not None:
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        except:
            pass
    
    return log_path

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
        
        logger = logging.getLogger('CRASH')
        logger.critical(
            "Eccezione non gestita!",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Scrivi anche su file dedicato per crash
        try:
            log_dir = get_log_directory()
            crash_file = os.path.join(log_dir, f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            with open(crash_file, 'w', encoding='utf-8') as f:
                f.write(f"CRASH REPORT - Intelleo PDF Splitter\n")
                f.write(f"{'='*60}\n")
                f.write(f"Data/Ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                f.write(f"Executable: {sys.executable}\n")
                f.write(f"{'='*60}\n\n")
                f.write("TRACEBACK:\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        except:
            pass
    
    sys.excepthook = exception_handler

def log_startup_info():
    """Logga informazioni di avvio per diagnostica."""
    logger = logging.getLogger('STARTUP')
    logger.info("="*60)
    logger.info("INTELLEO PDF SPLITTER - AVVIO APPLICAZIONE")
    logger.info("="*60)
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info(f"Log Directory: {get_log_directory()}")
    
    # Log delle variabili d'ambiente rilevanti
    logger.debug(f"PATH: {os.environ.get('PATH', 'N/A')[:200]}...")
    logger.debug(f"APPDATA: {os.environ.get('APPDATA', 'N/A')}")
    
    logger.info("-"*60)

# Inizializzazione automatica quando il modulo viene importato
_log_path = None

def initialize():
    """Inizializza il sistema di logging. Chiamare all'inizio di main.py."""
    global _log_path
    _log_path = setup_logging()
    setup_exception_handler()
    log_startup_info()
    return _log_path

def get_log_path():
    """Restituisce il percorso del file di log corrente."""
    return _log_path
