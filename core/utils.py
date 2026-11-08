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

def trim_memory():
    """Forces Python and OS garbage collection to minimize RAM usage to the absolute minimum."""
    import gc
    gc.collect(2)

    import platform
    import ctypes
    sys_name = platform.system()
    try:
        if sys_name == "Windows":
            # SetProcessWorkingSetSize(-1, -1) empties the working set into paging file/free RAM
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
        elif sys_name == "Linux":
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
            except Exception:
                pass
    except Exception:
        pass

def get_process_memory_mb() -> float:
    """Returns the current process physical RAM footprint in MB."""
    import platform
    sys_name = platform.system()
    try:
        if sys_name == "Windows":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                    ('PrivateUsage', ctypes.c_size_t),
                ]

            func = getattr(ctypes.windll.kernel32, "K32GetProcessMemoryInfo", None) or getattr(ctypes.windll.psapi, "GetProcessMemoryInfo", None)
            if func:
                func.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
                func.restype = wintypes.BOOL
                pmc = PROCESS_MEMORY_COUNTERS_EX()
                pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                if func(handle, ctypes.byref(pmc), pmc.cb):
                    # PrivateUsage represents the actual unshared memory consumed by the application
                    return round(pmc.PrivateUsage / (1024 * 1024), 1)
        else:
            # Linux /proc/self/status
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        return round(int(parts[1]) / 1024.0, 1)
    except Exception:
        pass
    return 0.0

DANGEROUS_EXTENSIONS = (
    ".exe", ".msi", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".ps1", ".scr", ".com", ".pif", ".cpl", ".hta", ".iso"
)

def is_dangerous_executable(filename_or_path: str) -> bool:
    """Detects if a file is an executable or script that can execute code."""
    if not filename_or_path:
        return False
    lower = filename_or_path.lower()
    return any(lower.endswith(ext) for ext in DANGEROUS_EXTENSIONS)

def check_double_extension_spoof(filename: str) -> bool:
    """Detects spoofed extensions designed to deceive users (e.g. invoice.pdf.exe or song.mp3.exe)."""
    lower = filename.lower()
    media_exts = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt", ".rtf",
        ".zip", ".rar", ".7z", ".mp3", ".wav", ".flac", ".mp4", ".mkv", ".avi"
    ]
    if any(lower.endswith(ext) for ext in DANGEROUS_EXTENSIONS):
        base, _ = os.path.splitext(lower)
        if any(base.endswith(m_ext) for m_ext in media_exts):
            return True
    return False

def apply_mark_of_the_web(filepath: str, source_url: str = ""):
    """
    Attaches the Windows Mark-of-the-Web (Zone.Identifier NTFS stream).
    This ensures Windows Defender and SmartScreen inspect downloaded executables
    before execution, preventing drive-by zero-day malware attacks.
    """
    import platform
    if platform.system() != "Windows" or not os.path.exists(filepath):
        return
    try:
        zone_path = filepath + ":Zone.Identifier"
        with open(zone_path, "w", encoding="utf-8") as f:
            f.write(f"[ZoneTransfer]\nZoneId=3\nHostUrl={source_url}\n")
    except Exception:
        pass
