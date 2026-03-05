"""
Punto di ingresso principale per l'applicazione (SRP).
Gestisce l'inizializzazione del sistema, la licenza e il lancio della GUI o dell'Utility ROI.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Gestione crash precoci prima dell'inizializzazione del logger
try:
    from PySide6.QtWidgets import QApplication, QMessageBox

    # Importazioni locali
    import app_logger
    import license_updater
    import license_validator
    import version
except Exception as e:
    with Path("crash_startup.txt").open("w") as f:
        f.write(f"CRITICAL ERROR DURING EARLY IMPORT: {e}\n")
        import traceback

        f.write(traceback.format_exc())
    sys.exit(1)

# Inizializza log prima di caricare MainApp (che dipende dal logger)
LOG_PATH = app_logger.initialize()
logger = logging.getLogger("LAUNCHER")


def run_app() -> None:
    """Configura e avvia l'applicazione principale."""
    from gui.theme import GLOBAL_QSS
    from main import MainApp
    from shared.constants import SIGNAL_FILE

    logger.info("=" * 68)
    logger.info("           INTELLEO PDF SPLITTER - AVVIO SISTEMA")
    logger.info("=" * 68)
    logger.info(f"  Versione: {version.__version__}")
    logger.info(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("=" * 68)

    # Inizializza QApplication
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(GLOBAL_QSS)

    # Verifica Licenza
    logger.info("Verifica licenza in corso...")
    try:
        license_updater.run_update()
    except Exception as e:
        logger.critical(f"Verifica licenza fallita: {e}", exc_info=True)
        QMessageBox.critical(None, "Errore Licenza", f"Impossibile verificare la licenza:\n{e}")
        sys.exit(1)

    is_valid, msg = license_validator.verify_license()
    if not is_valid:
        logger.error(f"Licenza non valida: {msg}")
        hw_id = license_validator.get_hardware_id()
        err_msg = f"{msg}\n\nHardware ID:\n{hw_id}\n\n(Copiato negli appunti)"
        clipboard = qt_app.clipboard()
        clipboard.setText(hw_id)
        QMessageBox.critical(None, "Licenza Non Valida", err_msg)
        sys.exit(1)

    # Pulizia signal file
    signal_path = Path(SIGNAL_FILE)
    if signal_path.exists():
        signal_path.unlink()

    # Gestione CLI arguments
    cli_path = None
    if len(sys.argv) > 1:
        potential_path = Path(sys.argv[1])
        if potential_path.exists() and (
            potential_path.is_dir() or potential_path.name.lower().endswith(".pdf")
        ):
            cli_path = str(potential_path)
            logger.info(f"Avvio con file: {potential_path}")

    window = MainApp(auto_file_path=cli_path)
    window.showMaximized()

    logger.info("Avvio event loop")
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    # Check for ROI Utility launch flag
    if "--utility" in sys.argv:
        try:
            import roi_utility

            roi_utility.run_utility()
        except Exception as e:
            logger.critical(f"Failed to launch ROI utility: {e}", exc_info=True)
        sys.exit(0)

    run_app()
