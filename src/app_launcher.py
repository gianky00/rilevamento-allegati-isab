"""
Punto di ingresso principale per l'applicazione (SRP).
Gestisce l'inizializzazione del sistema, la licenza e il lancio della GUI o dell'Utility ROI.
"""

import logging
import sys
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
    """Configura e avvia l'applicazione principale con Splash Screen."""
    from gui.theme import GLOBAL_QSS
    from gui.widgets.splash_screen import SplashScreen
    from main import MainApp
    from shared.constants import SIGNAL_FILE

    logger.info("=" * 68)
    logger.info("           INTELLEO PDF SPLITTER - AVVIO SISTEMA")
    logger.info("=" * 68)

    # 1. Inizializzazione QApplication e Splash Screen
    qt_app = QApplication(sys.argv)

    # FORZATURA STILE E PALETTE: Previene i bug di Windows Dark Mode o temi ad alto contrasto
    qt_app.setStyle("Fusion")

    from PySide6.QtGui import QColor, QPalette

    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8F9FA"))
    light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.Button, QColor("#F8F9FA"))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#111827"))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.Link, QColor("#2563EB"))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563EB"))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    qt_app.setPalette(light_palette)

    qt_app.setStyleSheet(GLOBAL_QSS)

    splash = SplashScreen()
    splash.set_version(version.__version__)
    splash.show()

    # Piccola pausa per garantire il rendering iniziale dello splash
    QApplication.processEvents()
    splash.set_progress(10, "Inizializzazione moduli...")

    # 2. Verifica Licenza (DURANTE LO SPLASH SCREEN)
    splash.set_progress(30, "Verifica licenza online...")
    try:
        license_updater.run_update()
    except Exception as e:
        splash.hide()
        logger.critical(f"Verifica licenza fallita: {e}", exc_info=True)
        QMessageBox.critical(None, "Errore Licenza", f"Impossibile verificare la licenza:\n{e}")
        return  # Usa return invece di sys.exit(1) per facilitare i test e la pulizia

    splash.set_progress(60, "Convalida Hardware ID...")
    is_valid, msg = license_validator.verify_license()
    if not is_valid:
        splash.hide()
        logger.error(f"Licenza non valida: {msg}")
        hw_id = license_validator.get_hardware_id()
        err_msg = f"{msg}\n\nHardware ID:\n{hw_id}\n\n(Copiato negli appunti)"
        clipboard = qt_app.clipboard()
        clipboard.setText(hw_id)
        QMessageBox.critical(None, "Licenza Non Valida", err_msg)
        return  # Usa return invece di sys.exit(1)

    # 3. Preparazione Ambiente
    splash.set_progress(80, "Configurazione interfaccia...")
    signal_path = Path(SIGNAL_FILE)
    if signal_path.exists():
        signal_path.unlink()

    # Gestione CLI arguments
    cli_path = None
    if len(sys.argv) > 1:
        potential_path = Path(sys.argv[1])
        if potential_path.exists() and (potential_path.is_dir() or potential_path.name.lower().endswith(".pdf")):
            cli_path = str(potential_path)
            logger.info(f"Avvio con file: {potential_path}")

    # 4. Lancio MainApp
    window = MainApp(auto_file_path=cli_path)

    splash.set_progress(100, "Pronto!")
    QApplication.processEvents()

    from PySide6.QtCore import QTimer

    # Piccola pausa per mostrare il 100% e garantire che gli eventi grafici siano processati
    def finalize_startup():
        """Chiude lo splash screen e mostra la finestra principale massimizzata."""
        splash.close()
        # Una piccola pausa post-close previene i conflitti di pittura su alcuni driver
        QTimer.singleShot(100, window.showMaximized)

    QTimer.singleShot(400, finalize_startup)

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
