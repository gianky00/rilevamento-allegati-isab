"""
Unit tests for app_logger.py.
"""
import contextlib
import logging
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import del modulo da testare
import app_logger


class TestAppLogger(unittest.TestCase):
    """Test suite per il modulo app_logger."""
    def setUp(self):
        """Setup prima di ogni test."""
        # Salva lo stato originale del logger
        self.original_handlers = logging.root.handlers.copy()
        self.original_level = logging.root.level
        # Reset delle variabili globali di app_logger
        app_logger._log_path = None
        app_logger._immediate_log_file = None
        app_logger._initialized = False

    def tearDown(self):
        """Cleanup dopo ogni test."""
        # Usa la nuova funzione di shutdown per pulire tutto
        app_logger.shutdown_logging()

        # Ripristina lo stato originale del logger
        logging.root.handlers = self.original_handlers
        logging.root.level = self.original_level

    def test_get_log_directory_windows(self):
        """Test che get_log_directory restituisce il percorso corretto su Windows."""
        with patch("sys.platform", "win32"), patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            log_dir = app_logger.get_log_directory()
            self.assertIn("Intelleo PDF Splitter", log_dir)
            self.assertIn("Log", log_dir)

    def test_get_log_directory_linux(self):
        """Test che get_log_directory restituisce il percorso corretto su Linux."""
        with patch("sys.platform", "linux"), patch("pathlib.Path.home", return_value=Path("/home/testuser")):
            log_dir = app_logger.get_log_directory()
            self.assertIn(".intelleo-pdf-splitter", log_dir)

    def test_get_app_directory_not_frozen(self):
        """Test get_app_directory quando non e' frozen."""
        # Assicurati che frozen sia False
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        app_dir = app_logger.get_app_directory()
        self.assertTrue(Path(app_dir).is_absolute())

    def test_get_app_directory_frozen(self):
        """Test get_app_directory quando e' frozen."""
        fake_path = str(Path("/path/to/app.exe"))
        expected_dir = str(Path("/path/to"))
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", fake_path):
            app_dir = app_logger.get_app_directory()
            self.assertEqual(app_dir, expected_dir)

    def test_setup_logging_creates_file(self):
        """Test che setup_logging crea un file di log."""
        # NOTA: Usiamo try-finally per garantire che shutdown_logging venga chiamato
        # PRIMA che tempfile provi a pulire la directory
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                log_path = app_logger.setup_logging()
                self.assertIsNotNone(log_path)
                self.assertTrue(Path(log_path).exists())
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_setup_logging_filename_format(self):
        """Test che il nome del file di log ha il formato Log_DD_MM_YYYY.log."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                log_path = app_logger.setup_logging()
                filename = Path(log_path).name
                self.assertTrue(filename.startswith("Log_"), f"Filename should start with 'Log_', got: {filename}")
                self.assertTrue(filename.endswith(".log"), f"Filename should end with '.log', got: {filename}")
                # Verifica formato DD_MM_YYYY
                parts = filename[4:-4].split("_")  # Rimuove "Log_" e ".log"
                self.assertEqual(len(parts), 3, f"Expected 3 parts in date, got: {parts}")
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_setup_exception_handler(self):
        """Test che setup_exception_handler configura sys.excepthook."""
        original_hook = sys.excepthook
        app_logger.setup_exception_handler()
        self.assertNotEqual(sys.excepthook, original_hook)
        # Ripristina
        sys.excepthook = original_hook

    def test_log_startup_info(self):
        """Test che log_startup_info non solleva eccezioni."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                app_logger.setup_logging()
                # Non deve sollevare eccezioni
                app_logger.log_startup_info()
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_initialize(self):
        """Test che initialize restituisce un percorso valido."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                log_path = app_logger.initialize()
                self.assertIsNotNone(log_path)
                self.assertEqual(app_logger.get_log_path(), log_path)
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_logging_writes_to_file(self):
        """Test che il logging scrive effettivamente sul file."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                log_path = app_logger.setup_logging()

                # Scrivi un messaggio di test
                logger = logging.getLogger("TEST")
                test_message = "Test message 12345"
                logger.info(test_message)

                # Forza il flush
                for handler in logging.root.handlers:
                    if hasattr(handler, "flush"):
                        handler.flush()

                # Verifica che il messaggio sia nel file
                with Path(log_path).open(encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn(test_message, content)
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_immediate_write(self):
        """Test che _write_immediate scrive immediatamente sul file."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                log_path = app_logger.setup_logging()

                test_message = "Immediate test 67890"
                app_logger._write_immediate(test_message)

                # Verifica che il messaggio sia nel file
                with Path(log_path).open(encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn(test_message, content)
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_safe_print_no_exception(self):
        """Test che _safe_print non solleva eccezioni anche se stdout è None."""
        original_stdout = sys.stdout
        try:
            sys.stdout = None
            # Non deve sollevare eccezioni
            app_logger._safe_print("Test message")
        finally:
            sys.stdout = original_stdout

    def test_exception_handler_logs_error(self):
        """Test che l'exception handler logghi l'errore correttamente."""


class TestAppLoggerExceptionHandler(unittest.TestCase):
    """Test suite specifica per l'exception handler di app_logger."""
    def setUp(self):
        """Setup prima di ogni test."""
        self.original_handlers = logging.root.handlers.copy()
        app_logger._log_path = None
        app_logger._immediate_log_file = None

    def tearDown(self):
        """Cleanup dopo ogni test."""
        app_logger.shutdown_logging()
        logging.root.handlers = self.original_handlers

    def test_exception_handler_keyboard_interrupt(self):
        """Test che KeyboardInterrupt non viene loggato."""
        app_logger.setup_exception_handler()

        # KeyboardInterrupt dovrebbe chiamare il hook originale
        with patch.object(sys, "__excepthook__") as mock_hook:
            with contextlib.suppress(Exception):
                sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
            mock_hook.assert_called_once()

    def test_exception_handler_logs_error(self):
        """Test che le eccezioni vengono loggate."""
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.object(app_logger, "get_log_directory", return_value=tmpdir):
                app_logger.setup_logging()
                app_logger.setup_exception_handler()

                # Simula un'eccezione
                try:
                    raise ValueError("Test exception")
                except ValueError:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    sys.excepthook(exc_type, exc_value, exc_tb)
        finally:
            app_logger.shutdown_logging()
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
