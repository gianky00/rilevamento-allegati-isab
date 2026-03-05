# Prompt di Quality & Refactoring

> **Origine**: Prompt generici presi da un altro progetto, adattabili a qualsiasi progetto Python.
> **Adattamento**: Il `pyproject.toml` nella root del progetto contiene già la configurazione specifica.

## Ordine di Esecuzione

| #   | File                                                     | Scopo                                          |
| --- | -------------------------------------------------------- | ---------------------------------------------- |
| 1   | [1_QUALITY_STACK_INSTALL.md](1_QUALITY_STACK_INSTALL.md) | Installazione tool: ruff, mypy, bandit, ecc.   |
| 2   | [2_QUALITY_STACK_CONFIG.md](2_QUALITY_STACK_CONFIG.md)   | Configurazione unificata in `pyproject.toml`   |
| 3   | [3_REFACTORING_AUDIT.md](3_REFACTORING_AUDIT.md)         | Audit code smells e complessità                |
| 4   | [4_SECURITY_AUDIT.md](4_SECURITY_AUDIT.md)               | Audit sicurezza (bandit, secrets, dipendenze)  |
| 5   | [5_TESTING_STRATEGY.md](5_TESTING_STRATEGY.md)           | Strategia di test e coverage target            |
| 6   | [6_REFACTORING_EXECUTION.md](6_REFACTORING_EXECUTION.md) | Esecuzione refactoring (Strangler Fig pattern) |

## Note Progetto-Specifiche

- **Framework GUI**: PySide6 (migrato da Tkinter nella v2.1.0)
- **Stubs mancanti**: `pymupdf`, `pytesseract` → override mypy in `pyproject.toml`
- **Security-sensitive**: `license_validator.py`, `license_updater.py`, `config.dat`
- **Test PySide6**: Necessario `@pytest.fixture` per `QApplication` nei test GUI
- **Comandi Windows**: Usare PowerShell (`$env:PYTHONUTF8 = "1"`)
