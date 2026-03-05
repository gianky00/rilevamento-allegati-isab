"""
Logica di Classificazione Documenti (SRP).
Gestisce il matching tra testo estratto e regole di classificazione.
"""
from typing import Any, Dict, List, Optional, Tuple

class DocumentClassifier:
    """Gestisce la classificazione delle pagine basata su regole e keyword."""

    def __init__(self, rules: List[Dict[str, Any]]) -> None:
        self.rules = rules

    def classify_text(self, text: str) -> Optional[str]:
        """
        Analizza un blocco di testo e restituisce il nome della categoria se c'è un match.
        """
        text_lower = text.lower()
        for rule in self.rules:
            keywords = [k.lower() for k in rule.get("keywords", [])]
            category_name = rule.get("category_name")
            if not isinstance(category_name, str):
                category_name = "sconosciuto"
            
            if any(keyword in text_lower for keyword in keywords):
                return category_name
        return None

    def get_rule_for_category(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Restituisce la configurazione della regola per una determinata categoria."""
        for rule in self.rules:
            if rule.get("category_name") == category_name:
                return rule
        return None
