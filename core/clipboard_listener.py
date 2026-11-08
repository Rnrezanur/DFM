"""
DFM Clipboard Monitor.
Watches Windows clipboard for downloadable files or streaming media links,
prompting the user with an IDM-style download dialog.
"""

import re
import time
import logging
import threading
from urllib.parse import urlparse
from typing import Callable, Optional

logger = logging.getLogger("DFM.Clipboard")

DOWNLOAD_EXTENSIONS = (
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg",
    ".exe", ".msi", ".apk", ".deb", ".rpm", ".bin",
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".mp3", ".wav", ".flac",
    ".pdf", ".epub", ".docx", ".xlsx", ".pptx"
)

MEDIA_DOMAINS = (
    "youtube.com", "youtu.be", "facebook.com", "fb.watch", "twitter.com",
    "x.com", "tiktok.com", "instagram.com", "vimeo.com", "reddit.com",
    "twitch.tv", "dailymotion.com", "soundcloud.com"
)

class ClipboardListener:
    def __init__(self, on_url_detected: Callable[[str, bool], None]):
        self.on_url_detected = on_url_detected
        self.enabled = True
        self._last_clipboard = ""
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _is_downloadable_url(self, text: str) -> tuple[bool, bool]:
        """Returns (is_valid, is_media)."""
        text = text.strip()
        if not text.startswith("http://") and not text.startswith("https://"):
            return False, False
        if "\n" in text or " " in text:
            return False, False

        try:
            parsed = urlparse(text)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower()

            # Check media domains
            for domain in MEDIA_DOMAINS:
                if domain in netloc:
                    return True, True

            # Check file extensions in path
            for ext in DOWNLOAD_EXTENSIONS:
                if path.endswith(ext) or f"{ext}?" in text.lower():
                    return True, False

            return False, False
        except Exception:
            return False, False

    def check_text(self, text: str):
        if not self.enabled:
            return
        text = text.strip()
        if not text or text == self._last_clipboard:
            return
        self._last_clipboard = text

        is_valid, is_media = self._is_downloadable_url(text)
        if is_valid:
            logger.info(f"Clipboard detected download URL: {text} (media={is_media})")
            self.on_url_detected(text, is_media)

    def _run(self):
        # We can also monitor via win32 or polling with QClipboard in Qt thread.
        # This polling thread handles pure python background checking if needed.
        pass
