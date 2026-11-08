"""
DFM Modern High-End Fluent Themes (Dark & Light).
Pixel-perfect typography, modern card surfaces, refined contrast,
and robust geometry that prevents clipping or vertical stretching.
"""

MODERN_DARK_STYLESHEET = """
/* Reset & Base Typography */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "Inter", Roboto, sans-serif;
    outline: none;
    font-size: 13px;
}

QMainWindow, QDialog, QStackedWidget {
    background-color: #0b0e14;
    color: #f1f5f9;
}

QWidget {
    background-color: transparent;
    color: #f1f5f9;
}

/* Header & Top Bar */
#topHeader {
    background-color: #0e121a;
    border-bottom: 1px solid #1c2230;
    min-height: 52px;
    max-height: 52px;
}

#brandTitle {
    font-size: 16px;
    font-weight: 800;
    color: #3b82f6;
    letter-spacing: 0.5px;
}

#badgePill {
    background-color: #1e293b;
    color: #60a5fa;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 7px;
    border-radius: 4px;
    border: 1px solid #2563eb44;
}

/* Header Buttons */
QPushButton {
    background-color: #151a26;
    color: #cbd5e1;
    border: 1px solid #232a3d;
    border-radius: 6px;
    padding: 6px 11px;
    font-weight: 600;
    font-size: 12px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #21293d;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #10141f;
}

QPushButton:disabled {
    background-color: #0f121a;
    color: #475569;
    border-color: #191e2b;
}

/* Primary Vibrant Button */
QPushButton#primaryAction {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    border: 1px solid #60a5fa;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 14px;
}

QPushButton#primaryAction:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}

/* Search Bar */
#searchBar {
    background-color: #131722;
    border: 1px solid #22293d;
    border-radius: 6px;
    color: #f8fafc;
    padding: 6px 12px;
    font-size: 12px;
}

#searchBar:focus {
    border: 1px solid #3b82f6;
    background-color: #171d2b;
}

/* Category Sidebar */
QTreeWidget {
    background-color: #090c12;
    border: none;
    border-right: 1px solid #161b26;
    color: #cbd5e1;
    padding: 10px 4px;
    show-decoration-selected: 0;
    outline: none;
}

QTreeWidget::item {
    height: 34px;
    border-radius: 6px;
    padding-left: 8px;
    margin: 1px 6px;
    font-weight: 500;
}

QTreeWidget::item:hover {
    background-color: #141824;
    color: #ffffff;
}

QTreeWidget::item:selected {
    background: #172033;
    color: #60a5fa;
    font-weight: 700;
}

/* Downloads Table */
QTableWidget {
    background-color: #0b0e14;
    alternate-background-color: #0e121a;
    border: none;
    gridline-color: transparent;
    color: #f1f5f9;
    selection-background-color: #1a233a;
    selection-color: #60a5fa;
}

QTableWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #141824;
}

QTableWidget::item:selected {
    background-color: #162033;
    color: #93c5fd;
}

QHeaderView::section {
    background-color: #090c12;
    color: #64748b;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #1a202f;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.8px;
}

/* Status Bar */
QStatusBar {
    background-color: #080a0f;
    color: #64748b;
    border-top: 1px solid #161a26;
    padding: 0px 12px;
    font-size: 12px;
    min-height: 28px;
    max-height: 28px;
}

QStatusBar::item {
    border: none;
    margin: 0;
    padding: 0;
}

/* Context Menu */
QMenu {
    background-color: #121620;
    border: 1px solid #232a3d;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 12px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #1c2232;
    margin: 4px 6px;
}

/* ScrollBars */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #232a3d;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #232a3d;
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Group Boxes in Dialogs */
QGroupBox {
    background-color: #0f131c;
    border: 1px solid #1d2333;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
    color: #94a3b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #60a5fa;
}

/* Input Fields */
QLineEdit {
    background-color: #131722;
    border: 1px solid #22293d;
    border-radius: 6px;
    color: #f8fafc;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #171d2b;
}

/* ComboBox */
QComboBox {
    background-color: #131722;
    border: 1px solid #22293d;
    border-radius: 6px;
    padding: 7px 12px;
    color: #f8fafc;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #121620;
    border: 1px solid #232a3d;
    selection-background-color: #2563eb;
    color: #f8fafc;
}
"""

MODERN_LIGHT_STYLESHEET = """
/* Reset & Base Typography */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "Inter", Roboto, sans-serif;
    outline: none;
    font-size: 13px;
}

QMainWindow, QDialog, QStackedWidget {
    background-color: #f8fafc;
    color: #0f172a;
}

QWidget {
    background-color: transparent;
    color: #0f172a;
}

/* Header & Top Bar */
#topHeader {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    min-height: 52px;
    max-height: 52px;
}

#brandTitle {
    font-size: 16px;
    font-weight: 800;
    color: #2563eb;
    letter-spacing: 0.5px;
}

#badgePill {
    background-color: #eff6ff;
    color: #1d4ed8;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 7px;
    border-radius: 4px;
    border: 1px solid #bfdbfe;
}

/* Header Buttons */
QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 11px;
    font-weight: 600;
    font-size: 12px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #3b82f6;
    color: #0f172a;
}

QPushButton:pressed {
    background-color: #e2e8f0;
}

QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Primary Vibrant Button */
QPushButton#primaryAction {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    border: 1px solid #2563eb;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 14px;
}

QPushButton#primaryAction:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}

/* Search Bar */
#searchBar {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    padding: 6px 12px;
    font-size: 12px;
}

#searchBar:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}

/* Category Sidebar */
QTreeWidget {
    background-color: #f8fafc;
    border: none;
    border-right: 1px solid #e2e8f0;
    color: #334155;
    padding: 10px 4px;
    show-decoration-selected: 0;
    outline: none;
}

QTreeWidget::item {
    height: 34px;
    border-radius: 6px;
    padding-left: 8px;
    margin: 1px 6px;
    font-weight: 500;
    color: #334155;
}

QTreeWidget::item:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QTreeWidget::item:selected {
    background: #dbeafe;
    color: #1d4ed8;
    font-weight: 700;
}

/* Downloads Table */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    border: none;
    gridline-color: transparent;
    color: #0f172a;
    selection-background-color: #e0e7ff;
    selection-color: #1e40af;
}

QTableWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #f1f5f9;
}

QTableWidget::item:selected {
    background-color: #e0e7ff;
    color: #1e40af;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.8px;
}

/* Status Bar */
QStatusBar {
    background-color: #ffffff;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding: 0px 12px;
    font-size: 12px;
    min-height: 28px;
    max-height: 28px;
}

QStatusBar::item {
    border: none;
    margin: 0;
    padding: 0;
}

/* Context Menu */
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
    color: #1e293b;
    font-size: 12px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 6px;
}

/* ScrollBars */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Group Boxes in Dialogs */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
    color: #475569;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #2563eb;
}

/* Input Fields */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}

/* ComboBox */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 12px;
    color: #0f172a;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #2563eb;
    color: #0f172a;
}
"""

def get_theme_stylesheet(theme_name: str) -> str:
    """Returns the QSS stylesheet for the given theme name ('dark' or 'light')."""
    if theme_name and "light" in theme_name.lower():
        return MODERN_LIGHT_STYLESHEET
    return MODERN_DARK_STYLESHEET
