"""
DFM (Download Fast Manager) - Main Application Entrypoint
A fast, multi-threaded, modern IDM alternative for Windows.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import qdarktheme

# Add current folder to sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.main_window import MainWindow

def setup_logging():
    log_dir = os.path.join(os.path.expanduser("~"), ".dfm")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "dfm.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    setup_logging()
    logger = logging.getLogger("DFM.Main")
    logger.info("Starting DFM...")

    # Enable High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DFM")
    app.setOrganizationName("DFM")

    # Apply modern dark theme
    try:
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    except Exception as e:
        logger.warning(f"Failed to load dark stylesheet: {e}")

    # Set Application Icon
    icon_path = os.path.join(BASE_DIR, "assets", "dfm_icon.png")
    if os.path.exists(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    # Launch main window
    window = MainWindow()
    window.show()

    # If launched with a URL argument (e.g. from browser or command line: dfm.exe "https://...")
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        window.show_add_dialog(initial_url=sys.argv[1])

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
