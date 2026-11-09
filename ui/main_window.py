"""
DFM Main Application Window.
Modernized IDM-Style Architecture with Iconic Vertical Action Toolbar,
Hierarchical Categories Tree, Native File Type Badges, and High-Performance Table.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QStatusBar, QLabel, QPushButton, QToolButton, QMenu, QMessageBox,
    QApplication, QSystemTrayIcon, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject
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
from ui.theme import get_theme_stylesheet
from ui.icons import (
    icon_add_url, icon_resume, icon_stop, icon_stop_all, icon_delete,
    icon_delete_completed, icon_options, icon_scheduler, icon_start_queue,
    icon_stop_queue, icon_theme_toggle, get_native_file_icon,
    icon_category_folder, icon_category_compressed, icon_category_documents,
    icon_category_music, icon_category_programs, icon_category_video,
    icon_category_unfinished, icon_category_finished, icon_category_queues
)

class BridgeNotifier(QObject):
    browser_download_received = pyqtSignal(str, str, bool, dict)
    clipboard_url_received = pyqtSignal(str, bool)
    manager_event = pyqtSignal(str, str, dict)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFM — Download Fast Manager (Lightweight Pro)")
        self.resize(1100, 680)
        self.setMinimumSize(920, 560)

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

        # ---------------- 1. Top Action Toolbar (IDM-Style Vertical Buttons) ----------------
        top_header = QFrame()
        top_header.setObjectName("topHeader")
        top_header.setFixedHeight(72)

        top_layout = QHBoxLayout(top_header)
        top_layout.setContentsMargins(10, 4, 12, 4)
        top_layout.setSpacing(4)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        def make_tool_btn(text: str, icon: QIcon, tooltip: str, callback) -> QToolButton:
            btn = QToolButton()
            btn.setText(text)
            btn.setIcon(icon)
            btn.setIconSize(QSize(28, 28))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            return btn

        # Toolbar Actions
        self.btn_add = make_tool_btn("Add URL", icon_add_url(), "Add new download URL", self.show_add_dialog)
        self.btn_resume = make_tool_btn("Resume", icon_resume(), "Resume selected download", self._resume_selected)
        self.btn_stop = make_tool_btn("Stop", icon_stop(), "Pause selected download", self._pause_selected)
        self.btn_stop_all = make_tool_btn("Stop All", icon_stop_all(), "Stop all active downloads", manager.stop_all)
        self.btn_delete = make_tool_btn("Delete", icon_delete(), "Delete selected download", self._delete_selected)
        self.btn_delete_completed = make_tool_btn("Delete C...", icon_delete_completed(), "Clear all completed downloads from list", self._delete_completed)
        self.btn_options = make_tool_btn("Options", icon_options(), "Preferences & settings", self.show_settings_dialog)
        self.btn_scheduler = make_tool_btn("Scheduler", icon_scheduler(), "Download queue scheduler", self.show_settings_dialog)
        self.btn_start_queue = make_tool_btn("Start Qu...", icon_start_queue(), "Start main download queue", self._start_queue)
        self.btn_stop_queue = make_tool_btn("Stop Qu...", icon_stop_queue(), "Stop main download queue", self._stop_queue)

        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_resume)
        top_layout.addWidget(self.btn_stop)
        top_layout.addWidget(self.btn_stop_all)
        top_layout.addWidget(self.btn_delete)
        top_layout.addWidget(self.btn_delete_completed)
        top_layout.addWidget(self.btn_options)
        top_layout.addWidget(self.btn_scheduler)
        top_layout.addWidget(self.btn_start_queue)
        top_layout.addWidget(self.btn_stop_queue)

        # Vertical Divider
        sep = QFrame()
        sep.setObjectName("toolSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        top_layout.addWidget(sep)

        # Theme Toggle Button
        self.btn_theme_toggle = make_tool_btn("Theme", icon_theme_toggle(self.is_dark), "Toggle Modern Dark / Light theme", self._toggle_theme)
        top_layout.addWidget(self.btn_theme_toggle)

        top_layout.addStretch()

        # Search Box
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchBar")
        self.search_edit.setPlaceholderText("🔍 Quick search...")
        self.search_edit.setFixedWidth(180)
        self.search_edit.setFixedHeight(30)
        self.search_edit.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_edit)

        root_layout.addWidget(top_header)

        # ---------------- 2. Main Splitter (Categories Tree + Downloads Table) ----------------
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)

        # Left Sidebar Container
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebarContainer")
        self.sidebar_widget.setMinimumWidth(180)
        self.sidebar_widget.setMaximumWidth(320)
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Categories Title Bar
        cat_header = QFrame()
        cat_header.setObjectName("categoriesHeader")
        cat_header_layout = QHBoxLayout(cat_header)
        cat_header_layout.setContentsMargins(10, 0, 8, 0)
        
        cat_title = QLabel("Categories")
        cat_title.setObjectName("categoriesTitle")
        cat_header_layout.addWidget(cat_title)
        cat_header_layout.addStretch()

        self.cat_close_btn = QPushButton("✕")
        self.cat_close_btn.setFixedSize(16, 16)
        self.cat_close_btn.setStyleSheet("border: none; color: #888888; font-size: 11px; font-weight: bold; padding: 0;")
        self.cat_close_btn.setToolTip("Hide Categories Pane")
        self.cat_close_btn.clicked.connect(self._toggle_sidebar)
        cat_header_layout.addWidget(self.cat_close_btn)
        sidebar_layout.addWidget(cat_header)

        # Categories Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self._populate_category_tree()
        self.tree.itemClicked.connect(self._on_category_clicked)
        sidebar_layout.addWidget(self.tree)

        self.main_splitter.addWidget(self.sidebar_widget)

        # Right Content: Full-Featured IDM Downloads Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Q", "Size", "Status", "Time left", "Transfer rate", "Last Try Date"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)
        self.table.setIconSize(QSize(18, 18))

        # Column Layout
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 32)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 95)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(3, 130)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(4, 95)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(5, 115)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(6, 140)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)
        self.main_splitter.addWidget(self.table)

        self.main_splitter.setSizes([220, 880])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        root_layout.addWidget(self.main_splitter)

        # ---------------- 3. Bottom Status Bar ----------------
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.lbl_total_speed = QLabel("⬇ Total Speed: 0 B/s")
        self.lbl_total_speed.setStyleSheet("color: #38bdf8; font-weight: 700; padding: 0 10px;")
        
        self.lbl_active_count = QLabel("⚡ Active: 0")
        self.lbl_active_count.setStyleSheet("color: #94a3b8; padding: 0 10px;")

        self.lbl_total_files = QLabel("📁 Total: 0 files")
        self.lbl_total_files.setStyleSheet("color: #94a3b8; padding: 0 10px;")

        self.lbl_ram_usage = QLabel("🍃 RAM: ...")
        self.lbl_ram_usage.setStyleSheet("""
            background: #064e3b;
            color: #34d399;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            margin-left: 8px;
        """)

        self.lbl_bridge_status = QLabel("● Web Integration Active (Port 9666)")
        self.lbl_bridge_status.setStyleSheet("color: #10b981; font-weight: 600; padding-right: 12px;")

        self.status_bar.addWidget(self.lbl_total_speed)
        self.status_bar.addWidget(self.lbl_active_count)
        self.status_bar.addWidget(self.lbl_total_files)
        self.status_bar.addWidget(self.lbl_ram_usage)
        self.status_bar.addPermanentWidget(self.lbl_bridge_status)

        self.setCentralWidget(central_widget)

    def _toggle_sidebar(self):
        if self.sidebar_widget.isVisible():
            self.sidebar_widget.hide()
        else:
            self.sidebar_widget.show()

    def _populate_category_tree(self):
        self.tree.clear()

        # 1. All Downloads (Parent with sub-categories)
        self.item_all = QTreeWidgetItem(self.tree, ["All Downloads"])
        self.item_all.setIcon(0, icon_category_folder("#eab308"))
        self.item_all.setData(0, Qt.ItemDataRole.UserRole, "All Downloads")

        self.item_compressed = QTreeWidgetItem(self.item_all, ["Compressed"])
        self.item_compressed.setIcon(0, icon_category_compressed())
        self.item_compressed.setData(0, Qt.ItemDataRole.UserRole, "Compressed")

        self.item_documents = QTreeWidgetItem(self.item_all, ["Documents"])
        self.item_documents.setIcon(0, icon_category_documents())
        self.item_documents.setData(0, Qt.ItemDataRole.UserRole, "Documents")

        self.item_music = QTreeWidgetItem(self.item_all, ["Music"])
        self.item_music.setIcon(0, icon_category_music())
        self.item_music.setData(0, Qt.ItemDataRole.UserRole, "Music")

        self.item_programs = QTreeWidgetItem(self.item_all, ["Programs"])
        self.item_programs.setIcon(0, icon_category_programs())
        self.item_programs.setData(0, Qt.ItemDataRole.UserRole, "Programs")

        self.item_video = QTreeWidgetItem(self.item_all, ["Video"])
        self.item_video.setIcon(0, icon_category_video())
        self.item_video.setData(0, Qt.ItemDataRole.UserRole, "Video")

        # 2. Unfinished (Downloading + Paused)
        self.item_unfinished = QTreeWidgetItem(self.tree, ["Unfinished"])
        self.item_unfinished.setIcon(0, icon_category_unfinished())
        self.item_unfinished.setData(0, Qt.ItemDataRole.UserRole, "Unfinished")

        # 3. Finished (Completed)
        self.item_finished = QTreeWidgetItem(self.tree, ["Finished"])
        self.item_finished.setIcon(0, icon_category_finished())
        self.item_finished.setData(0, Qt.ItemDataRole.UserRole, "Finished")

        # 4. Grabber projects (Media/Web capture)
        self.item_grabber = QTreeWidgetItem(self.tree, ["Grabber projects"])
        self.item_grabber.setIcon(0, icon_category_folder("#38bdf8"))
        self.item_grabber.setData(0, Qt.ItemDataRole.UserRole, "Grabber projects")

        # 5. Queues
        self.item_queues = QTreeWidgetItem(self.tree, ["Queues"])
        self.item_queues.setIcon(0, icon_category_queues())
        self.item_queues.setData(0, Qt.ItemDataRole.UserRole, "Queues")

        self.tree.expandAll()
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

    def _periodic_ram_trim(self):
        trim_memory()
        mb = get_process_memory_mb()
        self.lbl_ram_usage.setText(f"🍃 RAM: {mb:.1f} MB")

    def _manual_ram_trim(self):
        trim_memory()
        mb = get_process_memory_mb()
        self.lbl_ram_usage.setText(f"🍃 RAM: {mb:.1f} MB")
        self.statusBar().showMessage(f"Memory Trimmed: Working Set reduced to {mb:.1f} MB", 3000)

    def _on_category_clicked(self, item, column):
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        if cat_id:
            self.current_category_filter = cat_id
            self._load_downloads_table()

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

        # Update theme toggle button icon
        self.btn_theme_toggle.setIcon(icon_theme_toggle(is_dark))

        # Apply application-level style
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(theme_name))

        self.table.viewport().update()

    def _on_search_changed(self, text):
        self.search_filter = text.strip().lower()
        self._load_downloads_table()

    def _load_downloads_table(self):
        items = db.get_all_downloads()
        filtered_items = []
        counts = {
            "All Downloads": len(items),
            "Compressed": 0, "Documents": 0, "Music": 0, "Programs": 0, "Video": 0,
            "Unfinished": 0, "Finished": 0, "Grabber projects": 0, "Queues": 0
        }

        for item in items:
            cat = item.get("category", "Others")
            st = item["status"]

            if cat in counts:
                counts[cat] += 1
            if st == "completed":
                counts["Finished"] += 1
            else:
                counts["Unfinished"] += 1
            if item.get("is_video"):
                counts["Grabber projects"] += 1
            if st in ("queued", "pending"):
                counts["Queues"] += 1

            # Match filter
            cat_match = False
            if self.current_category_filter == "All Downloads":
                cat_match = True
            elif self.current_category_filter == "Finished" and st == "completed":
                cat_match = True
            elif self.current_category_filter == "Unfinished" and st != "completed":
                cat_match = True
            elif self.current_category_filter == "Grabber projects" and item.get("is_video"):
                cat_match = True
            elif self.current_category_filter == "Queues" and st in ("queued", "pending"):
                cat_match = True
            elif self.current_category_filter.lower() in cat.lower():
                cat_match = True

            search_match = True
            if self.search_filter:
                search_match = (
                    self.search_filter in item["filename"].lower() or
                    self.search_filter in item["url"].lower()
                )

            if cat_match and search_match:
                filtered_items.append(item)

        # Update category item labels with live counts
        self.item_all.setText(0, f"All Downloads ({counts['All Downloads']})")
        self.item_compressed.setText(0, f"Compressed ({counts['Compressed']})")
        self.item_documents.setText(0, f"Documents ({counts['Documents']})")
        self.item_music.setText(0, f"Music ({counts['Music']})")
        self.item_programs.setText(0, f"Programs ({counts['Programs']})")
        self.item_video.setText(0, f"Video ({counts['Video']})")
        self.item_unfinished.setText(0, f"Unfinished ({counts['Unfinished']})")
        self.item_finished.setText(0, f"Finished ({counts['Finished']})")
        self.item_grabber.setText(0, f"Grabber projects ({counts['Grabber projects']})")
        self.item_queues.setText(0, f"Queues ({counts['Queues']})")

        self.lbl_total_files.setText(f"📁 Total: {len(items)} files")

        # Table rows population
        self.table.setRowCount(len(filtered_items))
        for row, item in enumerate(filtered_items):
            # 0: File Name with true native operating system icon
            fn_item = QTableWidgetItem(f" {item['filename']}")
            fn_item.setIcon(get_native_file_icon(item["filename"]))
            fn_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.table.setItem(row, 0, fn_item)

            # 1: Q (Queue indicator)
            st = item["status"]
            q_val = "✓" if st == "completed" else "▶" if st == "downloading" else "⏸" if st == "paused" else ""
            q_item = QTableWidgetItem(q_val)
            q_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, q_item)

            # 2: Size
            sz_str = format_bytes(item["total_bytes"]) if item["total_bytes"] > 0 else "--"
            sz_item = QTableWidgetItem(sz_str)
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, sz_item)

            # 3: Status
            if st == "completed":
                st_text = "Complete"
            elif st == "downloading":
                pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100) if item["total_bytes"] > 0 else 0
                st_text = f"Downloading ({pct}%)"
            elif st == "paused":
                st_text = "Paused"
            elif st == "error":
                st_text = "Error"
            elif st == "queued":
                st_text = "Queued"
            else:
                st_text = st.capitalize()

            status_item = QTableWidgetItem(st_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if st == "completed":
                status_item.setForeground(QColor("#22c55e" if self.is_dark else "#16a34a"))
            elif st == "downloading":
                status_item.setForeground(QColor("#38bdf8" if self.is_dark else "#0284c7"))
            elif st == "paused":
                status_item.setForeground(QColor("#f59e0b" if self.is_dark else "#d97706"))
            elif st == "error":
                status_item.setForeground(QColor("#ef4444" if self.is_dark else "#dc2626"))
            self.table.setItem(row, 3, status_item)

            # 4: Time left
            eta_str = format_eta(item["eta"]) if st == "downloading" and item["eta"] > 0 else ""
            eta_item = QTableWidgetItem(eta_str)
            eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, eta_item)

            # 5: Transfer rate
            spd_str = format_speed(item["speed"]) if st == "downloading" and item["speed"] > 0 else ""
            spd_item = QTableWidgetItem(spd_str)
            spd_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, spd_item)

            # 6: Added Date
            date_item = QTableWidgetItem(item["added_at"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, date_item)

    def _refresh_active_downloads(self):
        """High-performance live cell update without re-allocating rows."""
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

                # Update Size
                sz_str = format_bytes(item["total_bytes"]) if item["total_bytes"] > 0 else "--"
                self.table.item(row, 2).setText(sz_str)

                # Update Status
                pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100) if item["total_bytes"] > 0 else 0
                st_item = self.table.item(row, 3)
                st_item.setText(f"Downloading ({pct}%)")
                st_item.setForeground(QColor("#38bdf8" if self.is_dark else "#0284c7"))

                # Update Time left
                eta_str = format_eta(item["eta"]) if item["eta"] > 0 else "--"
                self.table.item(row, 4).setText(eta_str)

                # Update Transfer rate
                spd_str = format_speed(item["speed"])
                self.table.item(row, 5).setText(spd_str)

        self.lbl_total_speed.setText(f"⬇ Total Speed: {format_speed(total_speed)}")
        self.lbl_active_count.setText(f"⚡ Active: {active_count}")

    def _get_selected_task_ids(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        ids = []
        for row in selected_rows:
            item = self.table.item(row, 0)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    ids.append(task_id)
        return ids

    def _resume_selected(self):
        for task_id in self._get_selected_task_ids():
            manager.resume_download(task_id)

    def _pause_selected(self):
        for task_id in self._get_selected_task_ids():
            manager.pause_download(task_id)

    def _start_queue(self):
        items = db.get_all_downloads()
        for item in items:
            if item["status"] in ("pending", "queued", "paused"):
                manager.start_download(item["id"])

    def _stop_queue(self):
        manager.stop_all()

    def _delete_selected(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return

        msg = f"Delete {len(ids)} selected download(s)?\n\nAlso delete the file(s) from your disk?"
        reply = QMessageBox.question(
            self,
            "Delete Confirmation",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        delete_disk_file = (reply == QMessageBox.StandardButton.Yes)
        for task_id in ids:
            manager.delete_download(task_id, delete_file=delete_disk_file)

        self._load_downloads_table()
        trim_memory()

    def _delete_completed(self):
        items = db.get_all_downloads()
        completed = [item for item in items if item["status"] == "completed"]
        if not completed:
            QMessageBox.information(self, "No Completed Downloads", "There are no completed downloads to remove.")
            return

        reply = QMessageBox.question(
            self,
            "Clear Completed Downloads",
            f"Remove all {len(completed)} completed download(s) from the list?\n\n(Physical files on disk will NOT be deleted).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            for item in completed:
                manager.delete_download(item["id"], delete_file=False)
            self._load_downloads_table()

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
