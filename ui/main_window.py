"""
DFM Main Application Window.
Professional Fluent Dark UI with fixed-height alignment, zero-clipping headers,
responsive stacked empty-state, and high-DPI modern aesthetics.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QStatusBar, QLabel, QPushButton, QMenu, QMessageBox,
    QApplication, QSystemTrayIcon, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont, QColor

from core.database import db
from core.download_manager import manager
from core.browser_bridge import BrowserBridgeServer
from core.clipboard_listener import ClipboardListener
from core.utils import (
    format_bytes, format_speed, format_eta,
    open_file_or_folder, trim_memory, get_process_memory_mb,
    is_dangerous_executable, check_double_extension_spoof
)

from ui.dialogs.add_download_dialog import AddDownloadDialog
from ui.dialogs.download_progress_dialog import DownloadProgressDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.delegates.progress_delegate import ModernProgressDelegate, ModernStatusPillDelegate
from ui.theme import get_theme_stylesheet

class BridgeNotifier(QObject):
    browser_download_received = pyqtSignal(str, str, bool, dict)
    clipboard_url_received = pyqtSignal(str, bool)
    manager_event = pyqtSignal(str, str, dict)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFM — Download Fast Manager (Lightweight Pro)")
        self.resize(1080, 680)
        self.setMinimumSize(900, 560)

        self.current_category_filter = "All Downloads"
        self.search_filter = ""
        self.progress_dialogs = {}

        # Theme Configuration
        self.current_theme = db.get_setting("theme", "dark")
        self.is_dark = "light" not in self.current_theme.lower()

        # Event Bridge
        self.notifier = BridgeNotifier()
        self.notifier.browser_download_received.connect(self._handle_browser_download)
        self.notifier.clipboard_url_received.connect(self._handle_clipboard_url)
        self.notifier.manager_event.connect(self._handle_manager_event)

        manager.register_listener(self._on_manager_callback)

        self._setup_ui()
        self._setup_tray()
        self._setup_clipboard()
        self._setup_bridge_server()
        self._load_downloads_table()

        # Update timer (500ms)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh_active_downloads)
        self.update_timer.start(500)

        # RAM Trimming Timer (every 25s)
        self.ram_timer = QTimer(self)
        self.ram_timer.timeout.connect(self._periodic_ram_trim)
        self.ram_timer.start(25000)
        self._periodic_ram_trim()

    def _setup_ui(self):
        central_widget = QWidget()
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------- 1. Top Header Bar (Strict 54px Height) ----------------
        top_header = QFrame()
        top_header.setObjectName("topHeader")
        top_header.setFixedHeight(54)

        top_layout = QHBoxLayout(top_header)
        top_layout.setContentsMargins(14, 0, 14, 0)
        top_layout.setSpacing(6)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Brand Logo & Title
        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 0, 8, 0)
        brand_layout.setSpacing(8)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand_lbl = QLabel("⚡ DFM")
        brand_lbl.setObjectName("brandTitle")

        badge_lbl = QLabel("PRO")
        badge_lbl.setObjectName("badgePill")
        badge_lbl.setFixedHeight(20)

        brand_layout.addWidget(brand_lbl)
        brand_layout.addWidget(badge_lbl)
        top_layout.addWidget(brand_container)

        # Action Buttons
        self.btn_add = QPushButton("＋ Add Download")
        self.btn_add.setObjectName("primaryAction")
        self.btn_add.setFixedHeight(32)
        self.btn_add.clicked.connect(self.show_add_dialog)
        top_layout.addWidget(self.btn_add)

        self.btn_resume = QPushButton("▶ Resume")
        self.btn_resume.setFixedHeight(32)
        self.btn_resume.clicked.connect(self._resume_selected)
        top_layout.addWidget(self.btn_resume)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setFixedHeight(32)
        self.btn_pause.clicked.connect(self._pause_selected)
        top_layout.addWidget(self.btn_pause)

        self.btn_stop_all = QPushButton("⏹ Stop All")
        self.btn_stop_all.setFixedHeight(32)
        self.btn_stop_all.clicked.connect(manager.stop_all)
        top_layout.addWidget(self.btn_stop_all)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setFixedHeight(32)
        self.btn_delete.clicked.connect(self._delete_selected)
        top_layout.addWidget(self.btn_delete)

        self.btn_folder = QPushButton("📁 Folder")
        self.btn_folder.setFixedHeight(32)
        self.btn_folder.clicked.connect(self._open_selected_folder)
        top_layout.addWidget(self.btn_folder)

        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_settings.setFixedHeight(32)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        top_layout.addWidget(self.btn_settings)

        self.btn_theme_toggle = QPushButton("☀️ Light" if self.is_dark else "🌙 Dark")
        self.btn_theme_toggle.setFixedHeight(32)
        self.btn_theme_toggle.setToolTip("Switch between Fluent Light and Dark Themes")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        top_layout.addWidget(self.btn_theme_toggle)

        top_layout.addStretch()

        # Search Box
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchBar")
        self.search_edit.setPlaceholderText("🔍 Search...")
        self.search_edit.setFixedWidth(160)
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_edit)

        root_layout.addWidget(top_header)

        # ---------------- 2. Main Splitter (Sidebar + Table) ----------------
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(1)

        # Left Sidebar Container
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self._populate_category_tree()
        self.tree.itemClicked.connect(self._on_category_clicked)
        sidebar_layout.addWidget(self.tree)

        # Mini System Info Card at bottom of sidebar
        self.sys_card = QFrame()
        self.sys_card.setStyleSheet(
            "background-color: #0c0f16; border-top: 1px solid #161b26; padding: 10px;" if self.is_dark
            else "background-color: #f1f5f9; border-top: 1px solid #e2e8f0; padding: 10px;"
        )
        card_layout = QVBoxLayout(self.sys_card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(10, 8, 10, 8)

        card_title = QLabel("● Engine Active")
        card_title.setStyleSheet("color: #10b981; font-weight: 700; font-size: 11px;")
        card_sub = QLabel("Port 9666 • Multi-Thread")
        card_sub.setStyleSheet("color: #64748b; font-size: 11px;")

        card_layout.addWidget(card_title)
        card_layout.addWidget(card_sub)
        sidebar_layout.addWidget(self.sys_card)

        main_splitter.addWidget(sidebar_widget)

        # Right Content Area (Stacked: Empty State or Downloads Table)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(
            "background-color: #0b0e14; border: none;" if self.is_dark
            else "background-color: #f8fafc; border: none;"
        )

        # Page 0: Empty State View
        self.empty_widget = QWidget()
        self.empty_widget.setObjectName("emptyWidget")
        self.empty_widget.setStyleSheet(
            "background-color: #0b0e14;" if self.is_dark
            else "background-color: #f8fafc;"
        )
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)

        self.icon_lbl = QLabel("⚡")
        self.icon_lbl.setStyleSheet("""
            font-size: 42px;
            color: #3b82f6;
            background: #172033;
            border-radius: 36px;
            padding: 12px;
            min-width: 72px;
            max-width: 72px;
            min-height: 72px;
            max-height: 72px;
        """)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_title = QLabel("No Downloads Yet")
        self.empty_title.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #f8fafc;" if self.is_dark
            else "font-size: 18px; font-weight: 800; color: #0f172a;"
        )

        self.empty_desc = QLabel("Add a URL or copy any downloadable link from your browser to get started.")
        self.empty_desc.setStyleSheet("color: #64748b; font-size: 13px; max-width: 440px;")
        self.empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_desc.setWordWrap(True)

        empty_btn = QPushButton("＋ Add Your First Download")
        empty_btn.setObjectName("primaryAction")
        empty_btn.setFixedHeight(36)
        empty_btn.clicked.connect(self.show_add_dialog)

        empty_layout.addWidget(self.icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_desc, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty_widget)

        # Page 1: Downloads Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "FILE NAME", "SIZE", "PROGRESS", "STATUS", "SPEED", "TIME LEFT", "ADDED"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setVisible(False)

        # Custom high-performance delegates with active theme awareness
        self.progress_delegate = ModernProgressDelegate(self.table, is_dark=self.is_dark)
        self.status_delegate = ModernStatusPillDelegate(self.table, is_dark=self.is_dark)
        self.status_delegate = ModernStatusPillDelegate(self.table)
        self.table.setItemDelegateForColumn(2, self.progress_delegate)
        self.table.setItemDelegateForColumn(3, self.status_delegate)

        # Column Layout sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 85)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 160)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 130)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(4, 105)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(5, 95)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(6, 140)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)
        self.stack.addWidget(self.table)

        main_splitter.addWidget(self.stack)
        main_splitter.setSizes([220, 860])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        root_layout.addWidget(main_splitter)

        # ---------------- 3. Bottom Status Bar ----------------
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.lbl_total_speed = QLabel("⬇ 0 B/s")
        self.lbl_total_speed.setStyleSheet("color: #38bdf8; font-weight: 700; padding: 0 10px;")
        self.lbl_active_count = QLabel("⚡ Active: 0")
        self.lbl_active_count.setStyleSheet("color: #94a3b8; padding: 0 10px;")
        self.lbl_ram_usage = QLabel("🍃 RAM: ...")
        self.lbl_ram_usage.setStyleSheet("""
            background: #064e3b;
            color: #34d399;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 10px;
            margin-left: 8px;
        """)

        self.lbl_bridge_status = QLabel("● Web Integration Active")
        self.lbl_bridge_status.setStyleSheet("color: #10b981; font-weight: 600; padding-right: 12px;")

        self.status_bar.addWidget(self.lbl_total_speed)
        self.status_bar.addWidget(self.lbl_active_count)
        self.status_bar.addWidget(self.lbl_ram_usage)
        self.status_bar.addPermanentWidget(self.lbl_bridge_status)

        self.setCentralWidget(central_widget)

    def _populate_category_tree(self):
        self.tree.clear()
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)

        def make_section(title):
            hdr = QTreeWidgetItem(self.tree, [title.upper()])
            hdr.setFlags(Qt.ItemFlag.NoItemFlags)
            f = hdr.font(0)
            f.setBold(True)
            f.setPointSize(9)
            hdr.setFont(0, f)
            hdr.setForeground(0, QColor("#64748b"))
            return hdr

        make_section("Downloads")
        self.item_all = QTreeWidgetItem(self.tree, ["  ⚡ All Downloads"])
        self.item_downloading = QTreeWidgetItem(self.tree, ["  ⏳ Downloading"])
        self.item_finished = QTreeWidgetItem(self.tree, ["  ✓ Completed"])
        self.item_unfinished = QTreeWidgetItem(self.tree, ["  ⏸ Paused"])

        make_section("Categories")
        self.item_compressed = QTreeWidgetItem(self.tree, ["  📦 Compressed"])
        self.item_programs = QTreeWidgetItem(self.tree, ["  💻 Programs"])
        self.item_video = QTreeWidgetItem(self.tree, ["  🎬 Video & Audio"])
        self.item_documents = QTreeWidgetItem(self.tree, ["  📄 Documents"])
        self.item_others = QTreeWidgetItem(self.tree, ["  📁 Others"])

        self.tree.setCurrentItem(self.item_all)

    def _setup_tray(self):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_dir, "assets", "dfm_icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(base_dir), "assets", "dfm_icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.windowIcon()
        self.setWindowIcon(icon)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()
        act_show = tray_menu.addAction("Show DFM")
        act_show.triggered.connect(self.showNormal)
        act_add = tray_menu.addAction("Add Download")
        act_add.triggered.connect(self.show_add_dialog)
        tray_menu.addSeparator()
        act_trim = tray_menu.addAction("Clean RAM Cache")
        act_trim.triggered.connect(self._manual_ram_trim)
        tray_menu.addSeparator()
        act_exit = tray_menu.addAction("Exit DFM")
        act_exit.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _setup_clipboard(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard_listener = ClipboardListener(
            on_url_detected=lambda u, m: self.notifier.clipboard_url_received.emit(u, m)
        )
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)

    def _on_clipboard_changed(self):
        if db.get_setting("clipboard_monitor", "1") != "1":
            return
        text = self.clipboard.text()
        self.clipboard_listener.check_text(text)

    def _setup_bridge_server(self):
        port = int(db.get_setting("browser_bridge_port", "9666"))
        self.bridge_server = BrowserBridgeServer(
            port=port,
            on_browser_download=lambda u, fn, is_v, hdrs: self.notifier.browser_download_received.emit(u, fn or "", is_v, hdrs or {})
        )
        self.bridge_server.start()

    def _handle_browser_download(self, url: str, filename: str, is_video: bool, headers: dict = None):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.show_add_dialog(initial_url=url, is_media_hint=is_video, headers=headers)

    def _handle_clipboard_url(self, url: str, is_media: bool):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.show_add_dialog(initial_url=url, is_media_hint=is_media)

    def _on_manager_callback(self, event_type: str, item_id: str, **kwargs):
        self.notifier.manager_event.emit(event_type, item_id, kwargs)

    def _handle_manager_event(self, event_type: str, item_id: str, data: dict):
        if event_type == "completed":
            trim_memory()
            item = db.get_download(item_id)
            if item and self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "Download Completed",
                    f"{item['filename']} has finished downloading.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3500
                )
        self._load_downloads_table()

    def show_add_dialog(self, initial_url: str = "", is_media_hint: bool = False, headers: dict = None):
        dialog = AddDownloadDialog(self, initial_url=initial_url, is_media_hint=is_media_hint, headers=headers)
        if dialog.exec():
            task_id = manager.create_download(
                url=dialog.confirmed_url,
                filename=dialog.confirmed_filename,
                save_dir=dialog.confirmed_save_dir,
                is_video=dialog.is_video,
                video_format=dialog.confirmed_format_id,
                segments_count=dialog.confirmed_segments,
                headers=getattr(dialog, "confirmed_headers", None),
                auto_start=dialog.confirmed_auto_start
            )
            self._load_downloads_table()
            if dialog.confirmed_auto_start:
                self._open_progress_dialog(task_id)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            theme = db.get_setting("theme", "dark")
            if theme != self.current_theme:
                self._apply_theme(theme)

    def _toggle_theme(self):
        new_theme = "light" if self.is_dark else "dark"
        self._apply_theme(new_theme)

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        is_dark = "light" not in theme_name.lower()
        self.is_dark = is_dark
        db.set_setting("theme", "dark" if is_dark else "light")

        # Update delegates
        self.progress_delegate.set_dark_mode(is_dark)
        self.status_delegate.set_dark_mode(is_dark)

        # Update button text
        self.btn_theme_toggle.setText("☀️ Light" if is_dark else "🌙 Dark")

        # Apply application-level style
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(theme_name))

        # Dynamic surfaces for empty state and sidebar card
        if is_dark:
            self.empty_widget.setStyleSheet("background-color: #0b0e14;")
            self.stack.setStyleSheet("background-color: #0b0e14; border: none;")
            self.empty_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #f8fafc;")
            self.empty_desc.setStyleSheet("color: #64748b; font-size: 13px; max-width: 440px;")
            self.sys_card.setStyleSheet("background-color: #0c0f16; border-top: 1px solid #161b26; padding: 10px;")
            self.lbl_ram_usage.setStyleSheet("""
                background: #064e3b;
                color: #34d399;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 10px;
                border-radius: 10px;
                margin-left: 8px;
            """)
        else:
            self.empty_widget.setStyleSheet("background-color: #f8fafc;")
            self.stack.setStyleSheet("background-color: #f8fafc; border: none;")
            self.empty_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0f172a;")
            self.empty_desc.setStyleSheet("color: #64748b; font-size: 13px; max-width: 440px;")
            self.sys_card.setStyleSheet("background-color: #f1f5f9; border-top: 1px solid #e2e8f0; padding: 10px;")
            self.lbl_ram_usage.setStyleSheet("""
                background: #d1fae5;
                color: #065f46;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 10px;
                border-radius: 10px;
                margin-left: 8px;
            """)

        self.table.viewport().update()

    def _on_search_changed(self, text):
        self.search_filter = text.strip().lower()
        self._load_downloads_table()

    def _load_downloads_table(self):
        items = db.get_all_downloads()
        filtered_items = []
        counts = {"All Downloads": len(items), "Downloading": 0, "Finished": 0, "Unfinished": 0}

        for item in items:
            status = item["status"]
            if status == "downloading":
                counts["Downloading"] += 1
            elif status == "completed":
                counts["Finished"] += 1
            else:
                counts["Unfinished"] += 1

            # Category filter
            cat_match = False
            if self.current_category_filter == "All Downloads":
                cat_match = True
            elif self.current_category_filter == "Downloading" and status == "downloading":
                cat_match = True
            elif self.current_category_filter == "Completed" and status == "completed":
                cat_match = True
            elif self.current_category_filter == "Paused" and status in ["paused", "pending", "queued", "error"]:
                cat_match = True
            elif item["category"].lower() in self.current_category_filter.lower():
                cat_match = True

            # Search filter
            search_match = True
            if self.search_filter:
                search_match = (
                    self.search_filter in item["filename"].lower() or
                    self.search_filter in item["url"].lower()
                )

            if cat_match and search_match:
                filtered_items.append(item)

        # Update category badges
        self.item_all.setText(0, f"  ⚡ All Downloads ({counts['All Downloads']})")
        self.item_downloading.setText(0, f"  ⏳ Downloading ({counts['Downloading']})")
        self.item_finished.setText(0, f"  ✓ Completed ({counts['Finished']})")
        self.item_unfinished.setText(0, f"  ⏸ Paused ({counts['Unfinished']})")

        # Switch between Empty State and Table
        if len(filtered_items) == 0:
            self.stack.setCurrentIndex(0)
            return
        else:
            self.stack.setCurrentIndex(1)

        self.table.setRowCount(len(filtered_items))
        for row, item in enumerate(filtered_items):
            # 0: File Name
            fn_item = QTableWidgetItem(f"  {item['filename']}")
            fn_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.table.setItem(row, 0, fn_item)

            # 1: Size
            sz_str = format_bytes(item["total_bytes"]) if item["total_bytes"] > 0 else "--"
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, sz_item)

            # 2: Progress (Painted by ModernProgressDelegate)
            pct = 0
            if item["total_bytes"] > 0:
                pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100)
            prog_item = QTableWidgetItem()
            prog_item.setData(Qt.ItemDataRole.UserRole, min(100, pct))
            self.table.setItem(row, 2, prog_item)

            # 3: Status (Painted by ModernStatusPillDelegate)
            status_item = QTableWidgetItem(item["status"])
            self.table.setItem(row, 3, status_item)

            # 4: Speed
            speed_str = format_speed(item["speed"]) if item["status"] == "downloading" else ""
            speed_item = QTableWidgetItem(speed_str)
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, speed_item)

            # 5: Time Left
            eta_str = format_eta(item["eta"]) if item["status"] == "downloading" and item["eta"] > 0 else ""
            eta_item = QTableWidgetItem(eta_str)
            eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, eta_item)

            # 6: Added
            date_item = QTableWidgetItem(item["added_at"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, date_item)

    def _refresh_active_downloads(self):
        """High performance live cell update without re-allocating rows."""
        total_speed = 0
        active_count = 0

        for row in range(self.table.rowCount()):
            fn_item = self.table.item(row, 0)
            if not fn_item:
                continue
            task_id = fn_item.data(Qt.ItemDataRole.UserRole)
            item = db.get_download(task_id)
            if not item:
                continue

            if item["status"] == "downloading":
                total_speed += item["speed"]
                active_count += 1

                sz_str = format_bytes(item["total_bytes"]) if item["total_bytes"] > 0 else "--"
                self.table.item(row, 1).setText(sz_str)

                # Progress percentage update
                pct = 0
                if item["total_bytes"] > 0:
                    pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100)
                self.table.item(row, 2).setData(Qt.ItemDataRole.UserRole, min(100, pct))

                # Status, speed, ETA
                self.table.item(row, 3).setText(item["status"])
                self.table.item(row, 4).setText(format_speed(item["speed"]))
                self.table.item(row, 5).setText(format_eta(item["eta"]))

        self.lbl_total_speed.setText(f"⬇ {format_speed(total_speed)}")
        self.lbl_active_count.setText(f"⚡ Active: {active_count}")

    def _periodic_ram_trim(self):
        """Called every 25 seconds to minimize RAM usage and update the status monitor."""
        trim_memory()
        mem_mb = get_process_memory_mb()
        if mem_mb > 0:
            self.lbl_ram_usage.setText(f"🍃 RAM: {mem_mb} MB")

    def _manual_ram_trim(self):
        trim_memory()
        mem_mb = get_process_memory_mb()
        self.lbl_ram_usage.setText(f"🍃 RAM: {mem_mb} MB")
        if self.tray_icon.isSystemTrayAvailable():
            self.tray_icon.showMessage("RAM Cleaned", f"Process memory trimmed to {mem_mb} MB.", QSystemTrayIcon.MessageIcon.Information, 2000)

    def _on_category_clicked(self, item, column):
        raw = item.text(0).strip()
        clean = raw.replace("⚡ ", "").replace("⏳ ", "").replace("✓ ", "").replace("⏸ ", "")
        clean = clean.replace("📦 ", "").replace("💻 ", "").replace("🎬 ", "").replace("🎵 ", "").replace("📄 ", "").replace("📁 ", "")
        text = clean.split(" (")[0].strip()
        if text.upper() in ["DOWNLOADS", "CATEGORIES"]:
            return
        self.current_category_filter = text
        self._load_downloads_table()

    def _get_selected_task_ids(self):
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        ids = []
        for row in selected_rows:
            fn_item = self.table.item(row, 0)
            if fn_item:
                ids.append(fn_item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _resume_selected(self):
        for task_id in self._get_selected_task_ids():
            manager.resume_download(task_id)
        self._load_downloads_table()

    def _pause_selected(self):
        for task_id in self._get_selected_task_ids():
            manager.pause_download(task_id)
        self._load_downloads_table()

    def _delete_selected(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return

        reply = QMessageBox.question(
            self,
            "Delete Downloads",
            f"Are you sure you want to remove {len(ids)} selected download(s)?\nAlso delete downloaded files from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        delete_disk_file = (reply == QMessageBox.StandardButton.Yes)
        for task_id in ids:
            manager.delete_download(task_id, delete_file=delete_disk_file)

        self._load_downloads_table()
        trim_memory()

    def _open_selected_folder(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return
        item = db.get_download(ids[0])
        if item:
            folder = os.path.dirname(item["save_path"])
            if os.path.exists(folder):
                open_file_or_folder(folder)

    def _show_context_menu(self, pos):
        ids = self._get_selected_task_ids()
        if not ids:
            return

        menu = QMenu(self)
        act_resume = menu.addAction("▶ Resume")
        act_resume.triggered.connect(self._resume_selected)
        act_pause = menu.addAction("⏸ Pause")
        act_pause.triggered.connect(self._pause_selected)
        menu.addSeparator()

        act_open_file = menu.addAction("Open File")
        act_open_file.triggered.connect(self._open_selected_file)
        act_open_folder = menu.addAction("Open Folder")
        act_open_folder.triggered.connect(self._open_selected_folder)
        menu.addSeparator()

        act_copy_url = menu.addAction("Copy Download Link")
        act_copy_url.triggered.connect(self._copy_selected_url)
        act_details = menu.addAction("Download Details...")
        act_details.triggered.connect(lambda: self._open_progress_dialog(ids[0]))

        menu.addSeparator()
        act_delete = menu.addAction("🗑 Delete")
        act_delete.triggered.connect(self._delete_selected)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _safe_open_file(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return
        filename = os.path.basename(file_path)

        if check_double_extension_spoof(filename):
            reply = QMessageBox.critical(
                self,
                "⚠️ High-Risk File Detected",
                f"The file '{filename}' appears to have a deceptive double extension and is actually an executable!\n\n"
                f"Malicious software often uses this technique to disguise viruses as documents.\n\n"
                f"Are you completely sure you want to run it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        elif is_dangerous_executable(file_path):
            reply = QMessageBox.warning(
                self,
                "Security Notice — Executable File",
                f"'{filename}' is an executable application downloaded from the internet.\n\n"
                f"Running unverified programs can make changes to your PC. Do you wish to launch it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        open_file_or_folder(file_path)

    def _open_selected_file(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return
        item = db.get_download(ids[0])
        if item and os.path.exists(item["save_path"]):
            self._safe_open_file(item["save_path"])

    def _copy_selected_url(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return
        item = db.get_download(ids[0])
        if item:
            QApplication.clipboard().setText(item["url"])

    def _on_table_double_clicked(self, row, column):
        fn_item = self.table.item(row, 0)
        if not fn_item:
            return
        task_id = fn_item.data(Qt.ItemDataRole.UserRole)
        item = db.get_download(task_id)
        if not item:
            return

        if item["status"] == "completed" and os.path.exists(item["save_path"]):
            self._safe_open_file(item["save_path"])
        else:
            self._open_progress_dialog(task_id)

    def _open_progress_dialog(self, task_id: str):
        if task_id in self.progress_dialogs and self.progress_dialogs[task_id].isVisible():
            self.progress_dialogs[task_id].activateWindow()
            return
        dialog = DownloadProgressDialog(task_id, self)
        self.progress_dialogs[task_id] = dialog
        dialog.show()

    def closeEvent(self, event):
        close_to_tray = db.get_setting("close_to_tray", "1") == "1"
        if close_to_tray and self.tray_icon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            trim_memory()
            self.tray_icon.showMessage(
                "DFM Running in Background",
                "DFM is active in system tray using minimal RAM. Double-click tray icon to reopen.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()
