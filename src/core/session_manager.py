"""
Gestione della sessione utente per ripristino interrotto (SRP).
"""
import json
import logging
import os
from typing import Any, Dict, List, Tuple

from shared.constants import SESSION_FILE

logger = logging.getLogger("MAIN")

class SessionManager:
    """Gestisce il salvataggio e il caricamento del file di sessione."""

    @staticmethod
    def has_session() -> bool:
        """Verifica se esiste una sessione precedentemente interrotta."""
        return os.path.exists(SESSION_FILE)

    @staticmethod
    def clear_session() -> None:
        """Rimuove il file di sessione."""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except OSError as e:
                logger.error(f"Errore rimozione session file: {e}")

    @staticmethod
    def load_session() -> Tuple[List[Dict[str, Any]], str]:
        """Carica i task salvati dal file di sessione."""
        if not os.path.exists(SESSION_FILE):
            return [], "Unknown"
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if data:
                tasks: List[Dict[str, Any]] = []
                odc = "Unknown"
                if isinstance(data, list):
                    tasks = data
                elif isinstance(data, dict):
                    tasks = data.get("tasks", [])
                    odc = data.get("odc", "Unknown")
                return tasks, odc
            return [], "Unknown"
        except Exception as e:
            logger.error(f"Errore ripristino sessione: {e}")
            raise
