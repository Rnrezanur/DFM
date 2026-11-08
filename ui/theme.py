"""
DFM Modern Ultra-Lightweight Fluent Dark Theme.
Designed for high aesthetic appeal, crisp contrast, minimal memory footprint,
and fast rendering across Windows and Ubuntu.
"""

MODERN_DARK_STYLESHEET = """
/* Global Reset */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Display", "Segoe UI", "Inter", Roboto, sans-serif;
    outline: none;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #0b0d13;
    color: #f1f5f9;
}

QWidget {
    background-color: transparent;
    color: #f1f5f9;
}

/* ToolBar Header */
QToolBar {
    background: #0f111a;
    border-bottom: 1px solid #1e2230;
    spacing: 8px;
    padding: 6px 12px;
}

QToolButton {
    background: #171a26;
    color: #e2e8f0;
    font-weight: 600;
    padding: 7px 14px;
    border-radius: 6px;
    border: 1px solid #23283a;
}

QToolButton:hover {
    background: #23283a;
    border-color: #3b82f6;
    color: #ffffff;
}

QToolButton:pressed {
    background: #1d2130;
}

/* Category Sidebar */
QTreeWidget {
    background-color: #0f111a;
    border: none;
    border-right: 1px solid #1a1e2b;
    color: #cbd5e1;
    padding: 10px 6px;
    show-decoration-selected: 1;
}

QTreeWidget::item {
    height: 34px;
    border-radius: 6px;
    padding-left: 8px;
    margin: 2px 4px;
}

QTreeWidget::item:hover {
    background-color: #171a26;
    color: #ffffff;
}

QTreeWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    font-weight: bold;
}

/* Downloads Table */
QTableWidget {
    background-color: #0b0d13;
    alternate-background-color: #0f1119;
    border: none;
    gridline-color: #151824;
    color: #f1f5f9;
    selection-background-color: #1a2236;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #141722;
}

QTableWidget::item:selected {
    background-color: #1a233a;
    color: #60a5fa;
}

QHeaderView::section {
    background-color: #0d0f17;
    color: #94a3b8;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #1e2230;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Status Bar */
QStatusBar {
    background-color: #0b0d13;
    color: #64748b;
    border-top: 1px solid #181c28;
    padding: 4px 10px;
    font-size: 12px;
}

/* Inputs & Search */
QLineEdit {
    background-color: #141724;
    border: 1px solid #23283b;
    border-radius: 6px;
    color: #f8fafc;
    padding: 7px 12px;
    selection-background-color: #3b82f6;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #171b2b;
}

/* Push Buttons */
QPushButton {
    background-color: #1c2030;
    color: #e2e8f0;
    border: 1px solid #282e44;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #262c42;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #161926;
}

QPushButton:disabled {
    background-color: #11131c;
    color: #475569;
    border-color: #1a1e2b;
}

/* Primary Accent Button */
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    border: none;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}

/* Group Boxes & Cards */
QGroupBox {
    background-color: #10131d;
    border: 1px solid #1c2132;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
    color: #94a3b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #60a5fa;
}

/* Progress Bar */
QProgressBar {
    background-color: #141724;
    border: 1px solid #1f2538;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    min-height: 14px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
    border-radius: 3px;
}

/* Context Menu */
QMenu {
    background-color: #121520;
    border: 1px solid #23283b;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
    color: #e2e8f0;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #1e2436;
    margin: 4px 6px;
}

/* ScrollBars */
QScrollBar:vertical {
    background-color: #0b0d13;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #23283b;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0b0d13;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #23283b;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #333a52;
    background-color: #141724;
}

QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}

/* ComboBox */
QComboBox {
    background-color: #141724;
    border: 1px solid #23283b;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #121520;
    border: 1px solid #23283b;
    selection-background-color: #2563eb;
    color: #f8fafc;
}
"""
