"""
Intelleo PDF Splitter — Tema Unificato (PySide6)
Single Source of Truth per colori, font e stylesheet globale.
"""

from PySide6.QtGui import QFont

# ============================================================================
# PALETTE COLORI — Tema Chiaro Professionale
# ============================================================================
COLORS = {
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F8F9FA",
    "bg_tertiary": "#E9ECEF",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text_primary": "#111827",
    "text_secondary": "#4B5563",
    "text_muted": "#9CA3AF",
    "border": "#E5E7EB",
    "card_shadow": "#9CA3AF",
}

# ============================================================================
# FONT PRESETS
# ============================================================================
FONTS = {
    "heading": QFont("Segoe UI", 14, QFont.Weight.Bold),
    "subheading": QFont("Segoe UI", 11, QFont.Weight.Bold),
    "body": QFont("Segoe UI", 11),
    "body_bold": QFont("Segoe UI", 11, QFont.Weight.Bold),
    "small": QFont("Segoe UI", 11),
    "small_bold": QFont("Segoe UI", 11, QFont.Weight.Bold),
    "mono": QFont("Consolas", 11),
    "mono_bold": QFont("Consolas", 11, QFont.Weight.Bold),
}

# ============================================================================
# GLOBAL QSS STYLESHEET
# ============================================================================
GLOBAL_QSS = f"""
* {{
    color: {COLORS["text_primary"]};
}}
QMainWindow, QDialog {{
    background-color: {COLORS["bg_primary"]};
}}
QTabWidget::pane {{
    background-color: {COLORS["bg_primary"]};
    border: none;
}}
QTabBar::tab {{
    font: bold 10pt "Segoe UI"; padding: 10px 20px;
    background-color: {COLORS["bg_secondary"]}; color: {COLORS["text_primary"]};
    border: none; margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS["accent"]};
    color: white;
}}
QPushButton {{
    font: 10pt "Segoe UI"; padding: 8px 15px;
    border: none; border-radius: 4px;
    background-color: {COLORS["bg_secondary"]}; color: {COLORS["text_primary"]};
}}
QPushButton:hover {{
    background-color: {COLORS["accent"]};
    color: white;
}}
QLineEdit, QComboBox, QTextEdit {{
    font: 10pt "Segoe UI"; padding: 8px;
    border: 1px solid {COLORS["border"]}; border-radius: 4px;
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
}}
QLabel {{
    color: {COLORS["text_primary"]};
}}
QGroupBox {{
    font: bold 11pt "Segoe UI"; border: 1px solid {COLORS["border"]};
    border-radius: 8px; margin-top: 10px; padding-top: 20px;
    color: {COLORS["text_primary"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px; padding: 0 5px;
    color: {COLORS["text_primary"]};
}}
QTreeWidget {{
    font: 10pt "Segoe UI"; background-color: {COLORS["bg_primary"]};
    border: none; alternate-background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
}}
QTreeWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: white;
}}
QTreeWidget QHeaderView::section {{
    font: bold 10pt "Segoe UI"; background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: none; padding: 5px;
}}
QProgressBar {{
    border: 1px solid {COLORS["border"]}; border-radius: 4px; text-align: center;
    background-color: {COLORS["bg_tertiary"]}; height: 20px;
    color: {COLORS["text_primary"]};
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {COLORS["success"]};
    border-radius: 3px;
}}
QListWidget {{
    font: 10pt "Segoe UI"; background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]}; border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: white;
}}
"""
