"""
Servizio di Gestione Regole di Classificazione (SRP).
Gestisce le operazioni CRUD sulle regole e la sincronizzazione con la configurazione.
"""

from typing import Any

import config_manager


class RuleService:
    """Gestisce la logica di business per le regole di classificazione."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Inizializza il servizio regole con l'oggetto configurazione fornito."""
        self.config = config

    def get_rules(self) -> list[dict[str, Any]]:
        """Restituisce la lista delle regole attuali."""
        rules = self.config.get("classification_rules", [])
        if not isinstance(rules, list):
            return []
        return rules

    def add_rule(self, rule_data: dict[str, Any]) -> bool:
        """Aggiunge una nuova regola alla configurazione."""
        rules = self.get_rules()
        # Verifica duplicati per nome categoria
        if any(r.get("category_name") == rule_data.get("category_name") for r in rules):
            return False

        rules.append(rule_data)
        self.config["classification_rules"] = rules
        return True

    def update_rule(self, category_name: str, new_data: dict[str, Any]) -> bool:
        """Aggiorna una regola esistente identificata dal nome categoria."""
        rules = self.get_rules()
        for i, rule in enumerate(rules):
            if rule.get("category_name") == category_name:
                # Mantieni dati non modificabili dal dialog base se necessario (es. rois se non passati)
                if "rois" not in new_data and "rois" in rule:
                    new_data["rois"] = rule["rois"]

                rules[i] = new_data
                self.config["classification_rules"] = rules
                return True
        return False

    def remove_rule(self, category_name: str) -> bool:
        """Rimuove una regola dalla configurazione."""
        rules = self.get_rules()
        initial_count = len(rules)
        self.config["classification_rules"] = [r for r in rules if r.get("category_name") != category_name]
        return len(self.config["classification_rules"]) < initial_count

    def save(self) -> None:
        """Sincronizza la configurazione su disco."""
        config_manager.save_config(self.config)

    def save_rules(self) -> None:
        """Alias per save() per coerenza con ROI utility."""
        self.save()

    def get_rule_by_category(self, category_name: str) -> dict[str, Any] | None:
        """Cerca una regola specifica per categoria."""
        for rule in self.get_rules():
            if rule.get("category_name") == category_name:
                return rule
        return None

    def add_roi_to_rule(self, category_name: str, coords: list[int]) -> bool:
        """Aggiunge un set di coordinate ROI a una regola esistente."""
        rule = self.get_rule_by_category(category_name)
        if not rule:
            return False

        if "rois" not in rule:
            rule["rois"] = []

        rule["rois"].append(coords)
        return True
