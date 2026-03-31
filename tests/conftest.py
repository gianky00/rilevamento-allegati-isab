"""
Configurazione dei test per Pytest.
Inizializza l'ambiente Qt per i test della GUI.
"""
import os
import sys

import pytest

# Add the src directory to sys.path so tests can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# CRITICAL: Initialize QApplication BEFORE any tests or modules are imported.
# PySide6 will throw memory access violations or segmentation faults if QFont or QIcon
# are instatiated at the module level (e.g. in theme.py) before QApplication exists.
from PySide6.QtWidgets import QApplication

_app = QApplication.instance()
if not _app:
    _app = QApplication(sys.argv)


@pytest.fixture(scope="session", autouse=True)
def qapp_global():
    """Restituisce l'istanza QApplication globale creata al root level."""
    yield _app
