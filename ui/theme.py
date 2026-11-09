"""
DFM Professional Desktop Themes (IDM Modern Dark & IDM Modern Light).
Faithfully captures the beloved layout, high readability, and clean workflow of IDM
with modern crisp typography, sleek dark slate surfaces, and pixel-perfect controls.
"""

MODERN_DARK_STYLESHEET = """
/* Reset & Base Typography */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "Inter", Roboto, sans-serif;
    outline: none;
    font-size: 12px;
}

QMainWindow, QDialog {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QWidget {
    background-color: transparent;
    color: #e0e0e0;
}

/* ---------------- TOP ACTION TOOLBAR ---------------- */
#topHeader {
    background-color: #252526;
    border-bottom: 1px solid #333333;
    min-height: 72px;
    max-height: 72px;
}

/* Iconic Vertical Tool Buttons (Icon Top, Text Bottom) */
QToolButton {
    background-color: transparent;
    color: #cccccc;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 500;
    min-width: 54px;
    max-width: 68px;
    min-height: 60px;
    max-height: 60px;
}

QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #ffffff;
}

QToolButton:pressed {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QToolButton:disabled {
    color: #666666;
    background-color: transparent;
    border-color: transparent;
}

/* Toolbar Divider */
#toolSeparator {
    width: 1px;
    background-color: #383838;
    margin: 8px 4px;
}

/* Search Box */
#searchBar {
    background-color: #181818;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #ffffff;
    padding: 5px 10px;
    font-size: 12px;
}

#searchBar:focus {
    border-color: #0078d4;
    background-color: #1a1a1a;
}

/* ---------------- CATEGORIES SIDEBAR (LEFT) ---------------- */
#sidebarContainer {
    background-color: #202020;
    border-right: 1px solid #2d2d2d;
}

#categoriesHeader {
    background-color: #252526;
    border-bottom: 1px solid #303030;
    min-height: 26px;
    max-height: 26px;
    padding: 0 8px;
}

#categoriesTitle {
    font-size: 11px;
    font-weight: 700;
    color: #999999;
    letter-spacing: 0.5px;
}

QTreeWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    border: none;
    padding: 4px 0;
    font-size: 12px;
}

QTreeWidget::item {
    height: 25px;
    padding-left: 4px;
    border-radius: 3px;
    margin: 1px 4px;
}

QTreeWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #ffffff;
}

QTreeWidget::item:selected {
    background-color: #04395e;
    color: #ffffff;
    font-weight: 600;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    border-image: none;
    image: none;
}

/* ---------------- DOWNLOADS TABLE (RIGHT) ---------------- */
QTableWidget {
    background-color: #181818;
    color: #e0e0e0;
    border: none;
    gridline-color: #2b2b2b;
    selection-background-color: #094771;
    selection-color: #ffffff;
    font-size: 12px;
}

QTableWidget::item {
    height: 28px;
    padding: 3px 8px;
    border-bottom: 1px solid #242424;
}

QTableWidget::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QTableWidget::item:hover:!selected {
    background-color: rgba(255, 255, 255, 0.04);
}

/* Alternating Row Coloring */
QTableWidget {
    alternate-background-color: #1f1f1f;
}

/* Table Header */
QHeaderView::section {
    background-color: #252526;
    color: #b0b0b0;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
    height: 26px;
}

QHeaderView::section:hover {
    background-color: #2d2d2d;
    color: #ffffff;
}

/* ---------------- STATUS BAR ---------------- */
QStatusBar {
    background-color: #252526;
    color: #999999;
    border-top: 1px solid #2d2d2d;
    min-height: 24px;
    font-size: 11px;
}

/* ---------------- SPLITTER ---------------- */
QSplitter::handle {
    background-color: #2d2d2d;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #0078d4;
}

/* ---------------- CONTEXT MENU ---------------- */
QMenu {
    background-color: #252526;
    color: #e0e0e0;
    border: 1px solid #383838;
    border-radius: 4px;
    padding: 4px 0;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
}

QMenu::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #383838;
    margin: 4px 0;
}

/* ---------------- DIALOGS & BUTTONS ---------------- */
QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383838;
    border-color: #555555;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #222222;
}

QPushButton#primaryButton {
    background-color: #0078d4;
    color: #ffffff;
    border: 1px solid #1084d8;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #1084d8;
}

QProgressBar {
    background-color: #252526;
    border: 1px solid #383838;
    border-radius: 2px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 2px;
}

QScrollBar:vertical {
    background: #181818;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #383838;
    min-height: 20px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #4f4f4f;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #181818;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #383838;
    min-width: 20px;
    border-radius: 5px;
    margin: 2px;
}
"""

MODERN_LIGHT_STYLESHEET = """
/* Reset & Base Typography */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "Inter", Roboto, sans-serif;
    outline: none;
    font-size: 12px;
}

QMainWindow, QDialog {
    background-color: #f3f3f3;
    color: #212529;
}

QWidget {
    background-color: transparent;
    color: #212529;
}

/* ---------------- TOP ACTION TOOLBAR ---------------- */
#topHeader {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    min-height: 72px;
    max-height: 72px;
}

/* Iconic Vertical Tool Buttons */
QToolButton {
    background-color: transparent;
    color: #333333;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 500;
    min-width: 54px;
    max-width: 68px;
    min-height: 60px;
    max-height: 60px;
}

QToolButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(0, 0, 0, 0.1);
    color: #000000;
}

QToolButton:pressed {
    background-color: rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(0, 0, 0, 0.15);
}

QToolButton:disabled {
    color: #aaaaaa;
    background-color: transparent;
    border-color: transparent;
}

/* Toolbar Divider */
#toolSeparator {
    width: 1px;
    background-color: #e5e5e5;
    margin: 8px 4px;
}

/* Search Box */
#searchBar {
    background-color: #f8f9fa;
    border: 1px solid #ced4da;
    border-radius: 4px;
    color: #212529;
    padding: 5px 10px;
    font-size: 12px;
}

#searchBar:focus {
    border-color: #0078d4;
    background-color: #ffffff;
}

/* ---------------- CATEGORIES SIDEBAR (LEFT) ---------------- */
#sidebarContainer {
    background-color: #fafafa;
    border-right: 1px solid #e0e0e0;
}

#categoriesHeader {
    background-color: #f1f3f5;
    border-bottom: 1px solid #e0e0e0;
    min-height: 26px;
    max-height: 26px;
    padding: 0 8px;
}

#categoriesTitle {
    font-size: 11px;
    font-weight: 700;
    color: #666666;
    letter-spacing: 0.5px;
}

QTreeWidget {
    background-color: #fafafa;
    color: #333333;
    border: none;
    padding: 4px 0;
    font-size: 12px;
}

QTreeWidget::item {
    height: 25px;
    padding-left: 4px;
    border-radius: 3px;
    margin: 1px 4px;
}

QTreeWidget::item:hover {
    background-color: rgba(0, 0, 0, 0.04);
    color: #000000;
}

QTreeWidget::item:selected {
    background-color: #cce8ff;
    color: #004578;
    font-weight: 600;
}

/* ---------------- DOWNLOADS TABLE (RIGHT) ---------------- */
QTableWidget {
    background-color: #ffffff;
    color: #212529;
    border: none;
    gridline-color: #f0f0f0;
    selection-background-color: #cce8ff;
    selection-color: #004578;
    font-size: 12px;
}

QTableWidget::item {
    height: 28px;
    padding: 3px 8px;
    border-bottom: 1px solid #f0f0f0;
}

QTableWidget::item:selected {
    background-color: #cce8ff;
    color: #004578;
}

QTableWidget::item:hover:!selected {
    background-color: rgba(0, 0, 0, 0.03);
}

/* Alternating Row Coloring */
QTableWidget {
    alternate-background-color: #f8f9fa;
}

/* Table Header */
QHeaderView::section {
    background-color: #f1f3f5;
    color: #495057;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #e0e0e0;
    border-bottom: 1px solid #e0e0e0;
    height: 26px;
}

QHeaderView::section:hover {
    background-color: #e9ecef;
    color: #212529;
}

/* ---------------- STATUS BAR ---------------- */
QStatusBar {
    background-color: #f8f9fa;
    color: #666666;
    border-top: 1px solid #e0e0e0;
    min-height: 24px;
    font-size: 11px;
}

/* ---------------- SPLITTER ---------------- */
QSplitter::handle {
    background-color: #e0e0e0;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #0078d4;
}

/* ---------------- CONTEXT MENU ---------------- */
QMenu {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 4px 0;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
}

QMenu::item:selected {
    background-color: #cce8ff;
    color: #004578;
}

QMenu::separator {
    height: 1px;
    background-color: #e9ecef;
    margin: 4px 0;
}

/* ---------------- DIALOGS & BUTTONS ---------------- */
QPushButton {
    background-color: #f8f9fa;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #e9ecef;
    border-color: #adb5bd;
}

QPushButton:pressed {
    background-color: #dee2e6;
}

QPushButton#primaryButton {
    background-color: #0078d4;
    color: #ffffff;
    border: 1px solid #005a9e;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #1084d8;
}

QProgressBar {
    background-color: #f1f3f5;
    border: 1px solid #ced4da;
    border-radius: 2px;
    text-align: center;
    color: #212529;
    font-size: 11px;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 2px;
}

QScrollBar:vertical {
    background: #f8f9fa;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #ced4da;
    min-height: 20px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #adb5bd;
}

QScrollBar:horizontal {
    background: #f8f9fa;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #ced4da;
    min-width: 20px;
    border-radius: 5px;
    margin: 2px;
}
"""

def get_theme_stylesheet(theme_name: str) -> str:
    if "light" in theme_name.lower():
        return MODERN_LIGHT_STYLESHEET
    return MODERN_DARK_STYLESHEET
