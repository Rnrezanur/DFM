"""
DFM Add New Download Dialog.
Probes URLs, supports video quality selection with thumbnail preview,
range/resume inspection, and category routing.
"""

import os
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QFileDialog, QGroupBox,
    QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

from core.database import db
from core.utils import (
    extract_filename_from_url_or_headers,
    get_category_for_filename,
    format_bytes,
    sanitize_filename
)
from core.video_downloader import VideoDownloadTask, VideoInfo

class ProbeThread(QThread):
    info_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # First check if it looks like a streaming video site
            video_info = None
            is_video_domain = any(dom in self.url.lower() for dom in [
                "youtube.com", "youtu.be", "facebook.com", "fb.watch", "tiktok.com",
                "x.com", "twitter.com", "vimeo.com", "twitch.tv", "dailymotion.com", "instagram.com"
            ])

            if is_video_domain:
                video_info = VideoDownloadTask.probe_media(self.url)

            if video_info:
                self.info_ready.emit({
                    "is_video": True,
                    "video_info": video_info,
                    "filename": sanitize_filename(f"{video_info.title}.mp4"),
                    "total_bytes": 0,
                    "supports_range": True
                })
                return

            # Otherwise probe as standard HTTP file
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Range": "bytes=0-0"
            }
            resp = requests.get(self.url, headers=headers, stream=True, timeout=10, allow_redirects=True)
            filename = extract_filename_from_url_or_headers(resp.url, dict(resp.headers))

            total_bytes = 0
            supports_range = False

            if resp.status_code == 206:
                supports_range = True
                content_range = resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    try:
                        total_bytes = int(content_range.split("/")[-1])
                    except ValueError:
                        total_bytes = 0
            else:
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    total_bytes = int(cl)

            resp.close()

            self.info_ready.emit({
                "is_video": False,
                "video_info": None,
                "filename": filename,
                "total_bytes": total_bytes,
                "supports_range": supports_range
            })

        except Exception as e:
            self.error_occurred.emit(str(e))


class AddDownloadDialog(QDialog):
    def __init__(self, parent=None, initial_url: str = "", is_media_hint: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Enter New Download - DFM")
        self.setMinimumWidth(560)
        self.resize(580, 420)

        self.probe_thread = None
        self.is_video = is_media_hint
        self.selected_format_id = None
        self.detected_total_bytes = 0
        self.confirmed_auto_start = True

        self._setup_ui()
        if initial_url:
            self.url_edit.setText(initial_url)
            self._start_probe()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header info
        header_lbl = QLabel("Paste URL or streaming video link to download with high-speed multi-threading:")
        header_lbl.setStyleSheet("color: #949ba4; font-size: 13px;")
        layout.addWidget(header_lbl)

        # URL Input Row
        url_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/file.zip or https://youtube.com/watch?v=...")
        self.url_edit.textChanged.connect(self._on_url_changed)
        url_layout.addWidget(self.url_edit)

        self.probe_btn = QPushButton("Probe")
        self.probe_btn.clicked.connect(self._start_probe)
        url_layout.addWidget(self.probe_btn)
        layout.addLayout(url_layout)

        # Status / Details Box
        self.details_group = QGroupBox("Download Details")
        details_layout = QVBoxLayout(self.details_group)

        # File Name
        fn_layout = QHBoxLayout()
        fn_lbl = QLabel("File Name:")
        fn_lbl.setFixedWidth(80)
        self.filename_edit = QLineEdit()
        fn_layout.addWidget(fn_lbl)
        fn_layout.addWidget(self.filename_edit)
        details_layout.addLayout(fn_layout)

        # Save Directory
        dir_layout = QHBoxLayout()
        dir_lbl = QLabel("Save To:")
        dir_lbl.setFixedWidth(80)
        self.dir_edit = QLineEdit()
        default_dir = db.get_setting("default_download_dir", os.path.join(os.path.expanduser("~"), "Downloads", "DFM"))
        self.dir_edit.setText(default_dir)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(dir_lbl)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(self.browse_btn)
        details_layout.addLayout(dir_layout)

        # Video Quality selector (Hidden by default, shown when video detected)
        self.video_format_layout = QHBoxLayout()
        self.video_format_lbl = QLabel("Quality:")
        self.video_format_lbl.setFixedWidth(80)
        self.format_combo = QComboBox()
        self.video_format_layout.addWidget(self.video_format_lbl)
        self.video_format_layout.addWidget(self.format_combo)
        details_layout.addLayout(self.video_format_layout)
        self.video_format_lbl.hide()
        self.format_combo.hide()

        # Metadata info row (Size, Resume Capability, Segments)
        meta_layout = QHBoxLayout()
        self.size_info_lbl = QLabel("Size: Checking...")
        self.resume_info_lbl = QLabel("Resume: Checking...")
        self.resume_info_lbl.setStyleSheet("color: #22c55e;")
        
        seg_lbl = QLabel("Segments:")
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 32)
        default_segs = int(db.get_setting("default_segments", "8"))
        self.segments_spin.setValue(default_segs)

        meta_layout.addWidget(self.size_info_lbl)
        meta_layout.addWidget(self.resume_info_lbl)
        meta_layout.addStretch()
        meta_layout.addWidget(seg_lbl)
        meta_layout.addWidget(self.segments_spin)
        details_layout.addLayout(meta_layout)

        # Probe loader bar
        self.loader_bar = QProgressBar()
        self.loader_bar.setRange(0, 0) # Indeterminate
        self.loader_bar.setFixedHeight(4)
        self.loader_bar.setTextVisible(False)
        self.loader_bar.hide()
        details_layout.addWidget(self.loader_bar)

        layout.addWidget(self.details_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.download_later_btn = QPushButton("Download Later")
        self.download_later_btn.clicked.connect(lambda: self._submit(auto_start=False))
        btn_layout.addWidget(self.download_later_btn)

        self.start_btn = QPushButton("Download Now")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.start_btn.clicked.connect(lambda: self._submit(auto_start=True))
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

    def _on_url_changed(self, text):
        if text.startswith("http://") or text.startswith("https://"):
            # Auto-fill tentative filename
            fn = extract_filename_from_url_or_headers(text)
            if fn:
                self.filename_edit.setText(fn)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.dir_edit.text())
        if folder:
            self.dir_edit.setText(folder)

    def _start_probe(self):
        url = self.url_edit.text().strip()
        if not url:
            return

        self.loader_bar.show()
        self.size_info_lbl.setText("Size: Probing...")
        self.resume_info_lbl.setText("Resume: Checking...")

        if self.probe_thread and self.probe_thread.isRunning():
            self.probe_thread.terminate()

        self.probe_thread = ProbeThread(url)
        self.probe_thread.info_ready.connect(self._on_probe_ready)
        self.probe_thread.error_occurred.connect(self._on_probe_error)
        self.probe_thread.start()

    def _on_probe_ready(self, data: dict):
        self.loader_bar.hide()
        self.filename_edit.setText(data["filename"])
        self.detected_total_bytes = data["total_bytes"]
        self.is_video = data["is_video"]

        if data["is_video"] and data["video_info"]:
            vinfo: VideoInfo = data["video_info"]
            self.video_format_lbl.show()
            self.format_combo.show()
            self.format_combo.clear()
            for f in vinfo.formats:
                sz_str = format_bytes(f["filesize"]) if f["filesize"] > 0 else ""
                label = f"{f['resolution']} ({f['ext']}) {sz_str}".strip()
                self.format_combo.addItem(label, f["format_id"])
            self.size_info_lbl.setText(f"Media: {vinfo.title[:35]}...")
            self.resume_info_lbl.setText("Streaming: Supported")
        else:
            self.video_format_lbl.hide()
            self.format_combo.hide()
            sz_text = format_bytes(data["total_bytes"]) if data["total_bytes"] > 0 else "Unknown Size"
            self.size_info_lbl.setText(f"Size: {sz_text}")
            if data["supports_range"]:
                self.resume_info_lbl.setText("Resume: Supported (Multi-Segment)")
                self.resume_info_lbl.setStyleSheet("color: #22c55e;")
            else:
                self.resume_info_lbl.setText("Resume: Single-Stream Only")
                self.resume_info_lbl.setStyleSheet("color: #eab308;")

    def _on_probe_error(self, err: str):
        self.loader_bar.hide()
        self.size_info_lbl.setText("Size: Unknown")
        self.resume_info_lbl.setText("Resume: Untested")
        self.resume_info_lbl.setStyleSheet("color: #ef4444;")

    def _submit(self, auto_start: bool):
        url = self.url_edit.text().strip()
        filename = self.filename_edit.text().strip()
        save_dir = self.dir_edit.text().strip()

        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid download URL.")
            return

        if not filename:
            filename = extract_filename_from_url_or_headers(url)

        if not save_dir:
            save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "DFM")

        self.confirmed_url = url
        self.confirmed_filename = filename
        self.confirmed_save_dir = save_dir
        self.confirmed_auto_start = auto_start
        self.confirmed_segments = self.segments_spin.value()
        self.confirmed_format_id = self.format_combo.currentData() if self.is_video else None

        self.accept()
