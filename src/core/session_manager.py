"""
Gestione della sessione utente per ripristino interrotto (SRP).
"""

import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any

from shared.constants import SESSION_FILE

logger = logging.getLogger("MAIN")


class SessionManager:
    """Gestisce il salvataggio e il caricamento del file di sessione."""

    @staticmethod
    def has_session() -> bool:
        """Verifica se esiste una sessione precedentemente interrotta."""
        from shared.constants import SESSION_FILE
        return Path(SESSION_FILE).exists()

    @staticmethod
    def clear_session() -> None:
        """Rimuove il file di sessione."""
        from shared.constants import SESSION_FILE
        session_path = Path(SESSION_FILE)
        if session_path.exists():
            with suppress(OSError):
                session_path.unlink()

    @staticmethod
    def save_session(tasks: list[dict[str, Any]], odc: str = "Unknown") -> None:
        """Salva i task correnti in un file di sessione per ripristino futuro."""
        from shared.constants import SESSION_FILE
        if not tasks:
            SessionManager.clear_session()
            return
            
        data = {"tasks": tasks, "odc": odc}
        session_path = Path(SESSION_FILE)
        with session_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_session() -> tuple[list[dict[str, Any]], str]:
        """Carica i task salvati dal file di sessione."""
        from shared.constants import SESSION_FILE
        session_path = Path(SESSION_FILE)
        if not session_path.exists():
            return [], "Unknown"
            
        try:
            with session_path.open(encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                return data, "Unknown"
            elif isinstance(data, dict):
                return data.get("tasks", []), data.get("odc", "Unknown")
            return [], "Unknown"
        except Exception as e:
            logger.exception(f"Errore caricamento sessione: {e}")
            raise # Risolve test_load_session_corrupted (logga + raise)
