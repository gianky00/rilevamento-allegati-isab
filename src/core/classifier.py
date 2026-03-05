"""
Logica di Classificazione Documenti (SRP).
Gestisce il matching tra testo estratto e regole di classificazione.
Keywords pre-compilate nel costruttore per massime prestazioni.
"""

from typing import Any


class DocumentClassifier:
    """Gestisce la classificazione delle pagine basata su regole e keyword."""

    def __init__(self, rules: list[dict[str, Any]]) -> None:
        """Inizializza il classificatore pre-compilando le keywords in minuscolo."""
        self.rules = rules
        # Pre-compila: .lower() una sola volta, non per ogni pagina
        self._compiled_rules: list[tuple[str, list[str]]] = []
        for rule in rules:
            category = rule.get("category_name")
            if not isinstance(category, str):
                category = "sconosciuto"
            keywords = [k.lower() for k in rule.get("keywords", [])]
            self._compiled_rules.append((category, keywords))

    def classify_text(self, text: str) -> str | None:
        """
        Analizza un blocco di testo e restituisce il nome della categoria se c'è un match.
        Usa le keywords pre-compilate per evitare .lower() ripetuti.
        """
        text_lower = text.lower()
        for category, keywords in self._compiled_rules:
            if any(keyword in text_lower for keyword in keywords):
                return category
        return None

    def get_rule_for_category(self, category_name: str) -> dict[str, Any] | None:
        """Restituisce la configurazione della regola per una determinata categoria."""
        for rule in self.rules:
            if rule.get("category_name") == category_name:
                return rule
        return None
