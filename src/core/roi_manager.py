"""
Gestione logica e persistenza delle aree ROI (SRP).
"""

import logging
from typing import Any

import config_manager

logger = logging.getLogger("MAIN")


class RoiManager:
    """Gestisce la logica di business e la persistenza delle ROI."""

    def __init__(self) -> None:
        """Inizializza il gestore delle ROI caricando la configurazione."""
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Carica la configurazione aggiornata."""
        self.config = config_manager.load_config()

    def save_config(self) -> None:
        """Salva la configurazione corrente."""
        config_manager.save_config(self.config)

    def get_categories(self) -> list[str]:
        """Restituisce l'elenco delle categorie disponibili."""
        return [rule.get("category_name", "N/A") for rule in self.config.get("classification_rules", [])]

    def add_roi(self, category_name: str, roi_coords: list[int]) -> bool:
        """Aggiunge una ROI a una determinata categoria."""
        rules = self.config.get("classification_rules", [])
        for rule in rules:
            if rule.get("category_name") == category_name:
                rule.setdefault("rois", []).append(roi_coords)
                self.save_config()
                return True
        return False

    def remove_roi(self, rule_index: int, roi_index: int) -> bool:
        """Rimuove una ROI specifica in base agli indici."""
        try:
            rules = self.config.get("classification_rules", [])
            if 0 <= rule_index < len(rules):
                rois = rules[rule_index].get("rois", [])
                if 0 <= roi_index < len(rois):
                    rois.pop(roi_index)
                    self.save_config()
                    return True
            return False
        except Exception as e:
            logger.exception(f"Errore rimozione ROI: {e}")
            return False

    def get_rules(self) -> list[dict[str, Any]]:
        """Restituisce le regole di classificazione."""
        rules = self.config.get("classification_rules", [])
        return rules if isinstance(rules, list) else []
