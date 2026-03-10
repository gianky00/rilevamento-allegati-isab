"""
Unit tests for core/rule_service.py.
"""

import unittest
from unittest.mock import patch
from core.rule_service import RuleService

class TestRuleService(unittest.TestCase):
    """Test suite for RuleService."""

    def setUp(self):
        """Setup initial configuration for testing."""
        self.config = {
            "classification_rules": [
                {"category_name": "Test1", "keywords": ["key1"], "rois": []},
                {"category_name": "Test2", "keywords": ["key2"], "rois": []}
            ]
        }
        self.service = RuleService(self.config)

    def test_get_rules(self):
        """Test retrieving all rules."""
        rules = self.service.get_rules()
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["category_name"], "Test1")

    def test_get_rules_empty(self):
        """Test behavior when no rules are present."""
        self.service.config = {}
        self.assertEqual(self.service.get_rules(), [])

    def test_add_rule_success(self):
        """Test adding a new unique rule."""
        new_rule = {"category_name": "NewRule", "keywords": ["new"]}
        success = self.service.add_rule(new_rule)
        self.assertTrue(success)
        self.assertEqual(len(self.service.get_rules()), 3)

    def test_add_rule_duplicate(self):
        """Test that duplicate category names are rejected."""
        duplicate_rule = {"category_name": "Test1", "keywords": ["other"]}
        success = self.service.add_rule(duplicate_rule)
        self.assertFalse(success)
        self.assertEqual(len(self.service.get_rules()), 2)

    def test_update_rule_success(self):
        """Test updating an existing rule."""
        new_data = {"category_name": "Test1", "keywords": ["updated"]}
        success = self.service.update_rule("Test1", new_data)
        self.assertTrue(success)
        rule = self.service.get_rule_by_category("Test1")
        self.assertEqual(rule["keywords"], ["updated"])

    def test_update_rule_persists_rois(self):
        """Test that updating a rule preserves ROIs if not provided in new data."""
        self.config["classification_rules"][0]["rois"] = [{"x": 10}]
        new_data = {"category_name": "Test1", "keywords": ["updated"]}
        
        self.service.update_rule("Test1", new_data)
        rule = self.service.get_rule_by_category("Test1")
        self.assertEqual(rule["rois"], [{"x": 10}])

    def test_update_rule_not_found(self):
        """Test updating a non-existent rule."""
        success = self.service.update_rule("NonExistent", {"category_name": "None"})
        self.assertFalse(success)

    def test_remove_rule_success(self):
        """Test removing a rule."""
        success = self.service.remove_rule("Test1")
        self.assertTrue(success)
        self.assertEqual(len(self.service.get_rules()), 1)

    def test_remove_rule_not_found(self):
        """Test removing a non-existent rule."""
        success = self.service.remove_rule("NonExistent")
        self.assertFalse(success)

    def test_get_rule_by_category(self):
        """Test finding a rule by its category name."""
        rule = self.service.get_rule_by_category("Test2")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["category_name"], "Test2")
        
        self.assertIsNone(self.service.get_rule_by_category("Unknown"))

    @patch("config_manager.save_config")
    def test_save(self, mock_save):
        """Test that save calls the config manager."""
        self.service.save()
        mock_save.assert_called_once_with(self.config)

if __name__ == "__main__":
    unittest.main()
