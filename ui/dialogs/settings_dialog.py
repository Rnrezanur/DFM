"""
DFM Settings Dialog.
Configuration for segments, speed limits, clipboard sniffing, paths, and integration.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QFileDialog, QGroupBox, QMessageBox
)
from core.database import db

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DFM Configuration & Options")
        self.setMinimumWidth(500)
        self.resize(520, 420)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # File Storage Group
        storage_group = QGroupBox("Save Locations")
        storage_layout = QVBoxLayout(storage_group)
        
        dir_lbl = QLabel("Default Download Folder:")
        storage_layout.addWidget(dir_lbl)

        dir_h_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_h_layout.addWidget(self.dir_edit)
        dir_h_layout.addWidget(self.browse_btn)
        storage_layout.addLayout(dir_h_layout)

        layout.addWidget(storage_group)

        # Connection Engine Group
        engine_group = QGroupBox("Multi-Threaded Download Engine")
        engine_layout = QVBoxLayout(engine_group)

        # Default segments
        seg_layout = QHBoxLayout()
        seg_lbl = QLabel("Default Segment Count per File:")
        self.segments_spin = QSpinBox()
        self.segments_spin.setRange(1, 32)
        seg_layout.addWidget(seg_lbl)
        seg_layout.addStretch()
        seg_layout.addWidget(self.segments_spin)
        engine_layout.addLayout(seg_layout)

        # Max concurrent downloads
        conc_layout = QHBoxLayout()
        conc_lbl = QLabel("Maximum Concurrent Active Downloads:")
        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 15)
        conc_layout.addWidget(conc_lbl)
        conc_layout.addStretch()
        conc_layout.addWidget(self.conc_spin)
        engine_layout.addLayout(conc_layout)

        # Speed Limiter
        speed_layout = QHBoxLayout()
        self.speed_limit_chk = QCheckBox("Enable Speed Limiter:")
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(50, 100000)
        self.speed_limit_spin.setSuffix(" KB/s")
        speed_layout.addWidget(self.speed_limit_chk)
        speed_layout.addStretch()
        speed_layout.addWidget(self.speed_limit_spin)
        engine_layout.addLayout(speed_layout)

        layout.addWidget(engine_group)

        # Automation & Integration Group
        auto_group = QGroupBox("Automation & Integration")
        auto_layout = QVBoxLayout(auto_group)

        self.clipboard_chk = QCheckBox("Monitor Clipboard for Download Links & Media")
        self.auto_start_chk = QCheckBox("Automatically start downloads when added")
        self.tray_chk = QCheckBox("Minimize to System Tray on window close")

        port_layout = QHBoxLayout()
        port_lbl = QLabel("Browser Integration Bridge Port:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        port_layout.addWidget(port_lbl)
        port_layout.addStretch()
        port_layout.addWidget(self.port_spin)

        auto_layout.addWidget(self.clipboard_chk)
        auto_layout.addWidget(self.auto_start_chk)
        auto_layout.addWidget(self.tray_chk)
        auto_layout.addLayout(port_layout)

        layout.addWidget(auto_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
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
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.dir_edit.text())
        if folder:
            self.dir_edit.setText(folder)

    def _load_settings(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads", "DFM")
        self.dir_edit.setText(db.get_setting("default_download_dir", default_dir))
        self.segments_spin.setValue(int(db.get_setting("default_segments", "8")))
        self.conc_spin.setValue(int(db.get_setting("max_concurrent_downloads", "3")))
        self.speed_limit_chk.setChecked(db.get_setting("speed_limit_enabled", "0") == "1")
        self.speed_limit_spin.setValue(int(db.get_setting("speed_limit_kbps", "1024")))
        self.clipboard_chk.setChecked(db.get_setting("clipboard_monitor", "1") == "1")
        self.auto_start_chk.setChecked(db.get_setting("auto_start_downloads", "1") == "1")
        self.tray_chk.setChecked(db.get_setting("close_to_tray", "1") == "1")
        self.port_spin.setValue(int(db.get_setting("browser_bridge_port", "9666")))

    def _save_settings(self):
        db.set_setting("default_download_dir", self.dir_edit.text().strip())
        db.set_setting("default_segments", str(self.segments_spin.value()))
        db.set_setting("max_concurrent_downloads", str(self.conc_spin.value()))
        db.set_setting("speed_limit_enabled", "1" if self.speed_limit_chk.isChecked() else "0")
        db.set_setting("speed_limit_kbps", str(self.speed_limit_spin.value()))
        db.set_setting("clipboard_monitor", "1" if self.clipboard_chk.isChecked() else "0")
        db.set_setting("auto_start_downloads", "1" if self.auto_start_chk.isChecked() else "0")
        db.set_setting("close_to_tray", "1" if self.tray_chk.isChecked() else "0")
        db.set_setting("browser_bridge_port", str(self.port_spin.value()))

        self.accept()
