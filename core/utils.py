"""
DFM Utility Functions: Size formatting, filename sanitize, category detection, headers parsing.
"""

import os
import re
import urllib.parse
from datetime import timedelta

CATEGORIES = {
    "Compressed": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg", ".tgz", ".z"],
    "Programs": [".exe", ".msi", ".bat", ".cmd", ".apk", ".jar", ".app", ".deb", ".rpm", ".sh", ".bin"],
    "Video": [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v", ".ts", ".3gp", ".mpeg", ".mpg"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".alac", ".aiff"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".csv", ".epub", ".mobi"]
}

def get_category_for_filename(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"

def sanitize_filename(name: str) -> str:
    # Remove query string if any
    name = name.split("?")[0].split("#")[0]
    # Replace illegal Windows characters
    name = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return name if name else "download_file"

def extract_filename_from_url_or_headers(url: str, headers: dict = None) -> str:
    filename = None
    if headers:
        # Check Content-Disposition
        cd = headers.get("content-disposition") or headers.get("Content-Disposition")
        if cd:
            # Match filename*="utf-8''..." or filename="..."
            fn_star_match = re.search(r"filename\*\s*=\s*UTF-8''([^;\r\n]+)", cd, re.IGNORECASE)
            if fn_star_match:
                filename = urllib.parse.unquote(fn_star_match.group(1))
            else:
                fn_match = re.search(r'filename\s*=\s*(?:"([^"]+)"|([^;\r\n]+))', cd, re.IGNORECASE)
                if fn_match:
                    filename = fn_match.group(1) or fn_match.group(2)
    
    if not filename:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        basename = os.path.basename(path)
        if basename:
            filename = basename

    if not filename or filename == "/":
        filename = "download"

    return sanitize_filename(filename)

def format_bytes(num_bytes: int) -> str:
    if num_bytes is None or num_bytes < 0:
        return "Unknown"
    if num_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    n = float(num_bytes)
    for unit in units:
        if n < 1024.0 or unit == units[-1]:
            return f"{n:.2f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.2f} PB"

def format_speed(bps: float) -> str:
    if not bps or bps <= 0:
        return "0 B/s"
    return f"{format_bytes(int(bps))}/s"

def format_eta(seconds: int) -> str:
    if seconds is None or seconds <= 0:
        return "--:--:--"
    if seconds > 86400 * 30: # > 30 days
        return "> 30 days"
    return str(timedelta(seconds=int(seconds)))

def open_file_or_folder(path: str) -> bool:
    """Cross-platform opener for files and folders (Windows, Ubuntu/Linux, macOS)."""
    if not path or not os.path.exists(path):
        return False

    import platform
    import subprocess
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import QUrl

    # Standard Qt desktop service first
    try:
        if QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path))):
            return True
    except Exception:
        pass

    sys_name = platform.system()
    try:
        if sys_name == "Windows":
            os.startfile(path)
        elif sys_name == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            # Linux / Ubuntu (GNOME, KDE, XFCE, etc.)
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False
