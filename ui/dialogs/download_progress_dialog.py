"""
DFM Active Download Status Dialog.
The iconic IDM-style dialog featuring multi-segment visual progress,
live transfer speed, ETA, and connection control.
"""

import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QGroupBox, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from core.database import db
from core.download_manager import manager
from core.utils import format_bytes, format_speed, format_eta, open_file_or_folder
from ui.widgets.segment_progress_bar import SegmentProgressBar

class DownloadProgressDialog(QDialog):
    def __init__(self, task_id: str, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle("Download Status - DFM")
        self.setMinimumWidth(540)
        self.resize(580, 360)

        self._setup_ui()

        # Update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_status)
        self.timer.start(300) # Every 300 ms

        self._refresh_status()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header info box
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #1e1f22; border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)

        self.fn_lbl = QLabel("File: ...")
        self.fn_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        self.url_lbl = QLabel("URL: ...")
        self.url_lbl.setStyleSheet("color: #949ba4; font-size: 11px;")
        self.url_lbl.setWordWrap(True)

        info_layout.addWidget(self.fn_lbl)
        info_layout.addWidget(self.url_lbl)
        layout.addWidget(info_frame)

        # Metrics Grid
        metrics_group = QGroupBox("Transfer Metrics")
        metrics_layout = QVBoxLayout(metrics_group)

        row1 = QHBoxLayout()
        self.status_val = QLabel("Status: Downloading")
        self.size_val = QLabel("File Size: --")
        row1.addWidget(self.status_val)
        row1.addWidget(self.size_val)
        metrics_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.downloaded_val = QLabel("Downloaded: 0 B")
        self.speed_val = QLabel("Transfer Rate: 0 B/s")
        row2.addWidget(self.downloaded_val)
        row2.addWidget(self.speed_val)
        metrics_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.resume_val = QLabel("Resume: Supported")
        self.eta_val = QLabel("Time Left: --:--:--")
        row3.addWidget(self.resume_val)
        row3.addWidget(self.eta_val)
        metrics_layout.addLayout(row3)

        layout.addWidget(metrics_group)

        # Overall Progress Bar
        self.main_progress = QProgressBar()
        self.main_progress.setRange(0, 100)
        self.main_progress.setValue(0)
        self.main_progress.setFixedHeight(18)
        self.main_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3b82f6;
                border-radius: 3px;
                text-align: center;
                background-color: #2b2d31;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
            }
        """)
        layout.addWidget(self.main_progress)

        # Segment Visualizer Label & Widget
        seg_lbl = QLabel("Segmented Connections (Multi-Threaded):")
        seg_lbl.setStyleSheet("color: #949ba4; font-size: 11px; margin-top: 4px;")
        layout.addWidget(seg_lbl)

        self.seg_bar = SegmentProgressBar()
        layout.addWidget(self.seg_bar)

        # Checkbox
        self.open_when_done_chk = QCheckBox("Open file when download is finished")
        layout.addWidget(self.open_when_done_chk)

        # Buttons
        btn_layout = QHBoxLayout()
        self.pause_resume_btn = QPushButton("Pause")
        self.pause_resume_btn.clicked.connect(self._toggle_pause_resume)
        btn_layout.addWidget(self.pause_resume_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.cancel_btn)

        btn_layout.addStretch()

        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setEnabled(False)
        self.open_file_btn.clicked.connect(self._open_file)
        btn_layout.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self._open_folder)
        btn_layout.addWidget(self.open_folder_btn)

        self.hide_btn = QPushButton("Hide")
        self.hide_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.hide_btn)

        layout.addLayout(btn_layout)

    def _refresh_status(self):
        item = db.get_download(self.task_id)
        if not item:
            self.timer.stop()
            self.close()
            return

        self.fn_lbl.setText(f"File: {item['filename']}")
        self.url_lbl.setText(f"URL: {item['url']}")

        status = item["status"]
        self.status_val.setText(f"Status: {status.capitalize()}")
        self.size_val.setText(f"File Size: {format_bytes(item['total_bytes'])}")
        self.downloaded_val.setText(f"Downloaded: {format_bytes(item['downloaded_bytes'])}")
        self.speed_val.setText(f"Transfer Rate: {format_speed(item['speed'])}")
        self.eta_val.setText(f"Time Left: {format_eta(item['eta'])}")

        pct = 0
        if item["total_bytes"] > 0:
            pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100)
            self.main_progress.setValue(min(100, pct))
        else:
            self.main_progress.setValue(0)

        # Query active task if in memory
        task = manager.active_tasks.get(self.task_id)
        if task and hasattr(task, "segments") and task.segments:
            seg_list = []
            for seg in task.segments:
                seg_list.append({
                    "index": seg.index,
                    "progress": seg.progress,
                    "status": seg.status
                })
            self.seg_bar.set_segments(seg_list, overall_progress=pct / 100.0)
        else:
            self.seg_bar.set_segments([], overall_progress=pct / 100.0)

        if status == "completed":
            self.pause_resume_btn.setEnabled(False)
            self.open_file_btn.setEnabled(True)
            self.timer.stop()
            if self.open_when_done_chk.isChecked():
                self._open_file()
        elif status == "paused":
            self.pause_resume_btn.setText("Resume")
            self.pause_resume_btn.setEnabled(True)
        else:
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setEnabled(True)

    def _toggle_pause_resume(self):
        item = db.get_download(self.task_id)
        if not item:
            return
        if item["status"] == "downloading":
            manager.pause_download(self.task_id)
        else:
            manager.resume_download(self.task_id)
            if not self.timer.isActive():
                self.timer.start(300)

    def _cancel(self):
        manager.delete_download(self.task_id, delete_file=False)
        self.close()

    def _open_file(self):
        item = db.get_download(self.task_id)
        if item and os.path.exists(item["save_path"]):
            open_file_or_folder(item["save_path"])

    def _open_folder(self):
        item = db.get_download(self.task_id)
        if item:
            folder = os.path.dirname(item["save_path"])
            if os.path.exists(folder):
                open_file_or_folder(folder)
