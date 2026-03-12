"""
Unit tests for gui/ui_factory.py.
"""

import unittest
from unittest.mock import patch

from PySide6.QtGui import QColor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QApplication, QLabel

from gui.theme import COLORS
from gui.ui_factory import AnimatedButton, UIFactory


class TestUIFactory(unittest.TestCase):
    """Test suite for UIFactory and AnimatedButton."""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication for widget tests."""
        cls.app = QApplication.instance() or QApplication([])

    def test_animated_button_init(self):
        """Test AnimatedButton initialization and styling."""
        btn = AnimatedButton("Test", is_primary=True)
        self.assertEqual(btn.text(), "Test")
        self.assertTrue(btn.is_primary)
        self.assertEqual(btn.background_color.name(), QColor(COLORS["accent"]).name())
        btn.deleteLater()

    def test_animated_button_color_property(self):
        """Test the background_color property of AnimatedButton."""
        btn = AnimatedButton("Test")
        target_color = QColor("#FF0000")
        btn.background_color = target_color
        self.assertEqual(btn.get_bg_color(), target_color)
        btn.deleteLater()

    @patch("gui.ui_factory.get_asset_path", return_value="mock_icon.svg")
    def test_create_svg_icon(self, mock_path):
        """Test SVG icon creation with a real widget but mocked path."""
        # Note: QSvgWidget might try to load the file, but it shouldn't crash if it fails
        icon = UIFactory.create_svg_icon("icon.svg", size=32)
        self.assertIsInstance(icon, QSvgWidget)
        self.assertEqual(icon.width(), 32)
        icon.deleteLater()

    def test_create_stat_card(self):
        """Test stat card creation."""
        card, label = UIFactory.create_stat_card("Title", "Value")
        self.assertIsInstance(label, QLabel)
        self.assertEqual(label.text(), "Value")
        card.deleteLater()

    def test_create_combined_stat_card(self):
        """Test combined stat card creation and sub-labels."""
        card, ds, dt, ps, pt = UIFactory.create_combined_stat_card("Group")
        self.assertEqual(ds.text(), "0")
        self.assertEqual(pt.text(), "0")
        card.deleteLater()

    def test_create_license_card(self):
        """Test license card creation."""
        card, status, grid = UIFactory.create_license_card("License")
        self.assertEqual(status.text(), "VERIFICA...")
        self.assertIsNotNone(grid)
        card.deleteLater()

    @patch("gui.ui_factory.get_asset_path", return_value="mock_icon.svg")
    def test_create_compact_info_row(self, mock_path):
        """Test info row creation using real widgets."""
        row, label = UIFactory.create_compact_info_row("Label", "icon.svg")
        # Find the label that contains our text
        found_label = None
        for lbl in row.findChildren(QLabel):
            if "Label:" in lbl.text():
                found_label = lbl
                break
        self.assertIsNotNone(found_label)
        row.deleteLater()

if __name__ == "__main__":
    unittest.main()
