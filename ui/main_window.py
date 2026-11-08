"""
DFM Main Application Window.
Rich dark-themed IDM alternative with real-time multi-threaded queue management,
category tree, segmented progress, system tray, and clipboard sniffer.
"""

import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QToolBar, QStatusBar, QLabel, QPushButton, QMenu, QMessageBox,
    QApplication, QSystemTrayIcon, QHeaderView, QAbstractItemView,
    QProgressBar, QStyledItemDelegate, QStyleOptionProgressBar, QStyle
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QIcon, QAction, QFont, QColor, QDesktopServices

from core.database import db
from core.download_manager import manager
from core.browser_bridge import BrowserBridgeServer
from core.clipboard_listener import ClipboardListener
from core.utils import format_bytes, format_speed, format_eta, get_category_for_filename, open_file_or_folder

from ui.dialogs.add_download_dialog import AddDownloadDialog
from ui.dialogs.download_progress_dialog import DownloadProgressDialog
from ui.dialogs.settings_dialog import SettingsDialog

class BridgeNotifier(QObject):
    browser_download_received = pyqtSignal(str, str, bool)
    clipboard_url_received = pyqtSignal(str, bool)
    manager_event = pyqtSignal(str, str, dict)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFM - Download Fast Manager")
        self.resize(1020, 640)
        self.setMinimumSize(800, 500)

        self.current_category_filter = "All Downloads"
        self.progress_dialogs = {} # task_id -> DownloadProgressDialog

        # Qt Event Bridge
        self.notifier = BridgeNotifier()
        self.notifier.browser_download_received.connect(self._handle_browser_download)
        self.notifier.clipboard_url_received.connect(self._handle_clipboard_url)
        self.notifier.manager_event.connect(self._handle_manager_event)

        # Register manager listener
        manager.register_listener(self._on_manager_callback)

        self._setup_ui()
        self._setup_tray()
        self._setup_clipboard()
        self._setup_bridge_server()
        self._load_downloads_table()

        # Polling timer for live table updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh_active_downloads)
        self.update_timer.start(500) # Every 500ms

    def _setup_ui(self):
        # Top Toolbar
        toolbar = QToolBar("Main Controls")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        toolbar.setStyleSheet("""
            QToolBar {
                background: #18191c;
                border-bottom: 1px solid #2b2d31;
                spacing: 6px;
                padding: 4px 8px;
            }
            QToolButton {
                color: #e3e5e8;
                font-weight: 500;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: #2b2d31;
            }
        """)
        self.addToolBar(toolbar)

        self.act_add = QAction("➕ Add URL", self)
        self.act_add.setToolTip("Add new download URL")
        self.act_add.triggered.connect(self.show_add_dialog)
        toolbar.addAction(self.act_add)

        toolbar.addSeparator()

        self.act_resume = QAction("▶ Resume", self)
        self.act_resume.setToolTip("Resume selected download")
        self.act_resume.triggered.connect(self._resume_selected)
        toolbar.addAction(self.act_resume)

        self.act_pause = QAction("⏸ Pause", self)
        self.act_pause.setToolTip("Pause selected download")
        self.act_pause.triggered.connect(self._pause_selected)
        toolbar.addAction(self.act_pause)

        self.act_stop_all = QAction("⏹ Stop All", self)
        self.act_stop_all.setToolTip("Pause all active downloads")
        self.act_stop_all.triggered.connect(manager.stop_all)
        toolbar.addAction(self.act_stop_all)

        toolbar.addSeparator()

        self.act_delete = QAction("🗑 Delete", self)
        self.act_delete.setToolTip("Delete selected download")
        self.act_delete.triggered.connect(self._delete_selected)
        toolbar.addAction(self.act_delete)

        self.act_open_folder = QAction("📁 Open Folder", self)
        self.act_open_folder.setToolTip("Open containing folder")
        self.act_open_folder.triggered.connect(self._open_selected_folder)
        toolbar.addAction(self.act_open_folder)

        toolbar.addSeparator()

        self.act_settings = QAction("⚙ Settings", self)
        self.act_settings.setToolTip("Configure DFM")
        self.act_settings.triggered.connect(self.show_settings_dialog)
        toolbar.addAction(self.act_settings)

        # Central Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(2)

        # Left Sidebar (Categories)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(200)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #18191c;
                border: none;
                border-right: 1px solid #2b2d31;
                color: #dcddde;
                font-size: 13px;
                padding-top: 8px;
            }
            QTreeWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #35373c;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self._populate_category_tree()
        self.tree.itemClicked.connect(self._on_category_clicked)
        main_splitter.addWidget(self.tree)

        # Right Panel (Downloads Table)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Size", "Progress", "Status", "Speed", "Time Left", "Added"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1f22;
                alternate-background-color: #232428;
                border: none;
                color: #e3e5e8;
                gridline-color: #2b2d31;
            }
            QHeaderView::section {
                background-color: #18191c;
                color: #949ba4;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #2b2d31;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #35373c;
                color: #ffffff;
            }
        """)

        # Configure columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 140)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

        right_layout.addWidget(self.table)
        main_splitter.addWidget(right_panel)
        self.setCentralWidget(main_splitter)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background: #18191c; color: #949ba4; border-top: 1px solid #2b2d31;")
        self.setStatusBar(self.status_bar)

        self.lbl_total_speed = QLabel("Total Speed: 0 B/s")
        self.lbl_active_count = QLabel("Active: 0")
        self.lbl_bridge_status = QLabel("● Web Integration Active (Port 9666)")
        self.lbl_bridge_status.setStyleSheet("color: #22c55e;")

        self.status_bar.addWidget(self.lbl_total_speed)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.lbl_active_count)
        self.status_bar.addPermanentWidget(self.lbl_bridge_status)

    def _populate_category_tree(self):
        self.tree.clear()
        
        # Main Categories
        cat_root = QTreeWidgetItem(self.tree, ["Downloads"])
        cat_root.setExpanded(True)

        self.item_all = QTreeWidgetItem(cat_root, ["All Downloads"])
        self.item_downloading = QTreeWidgetItem(cat_root, ["Downloading"])
        self.item_finished = QTreeWidgetItem(cat_root, ["Finished"])
        self.item_unfinished = QTreeWidgetItem(cat_root, ["Unfinished"])

        # File Types
        type_root = QTreeWidgetItem(self.tree, ["Categories"])
        type_root.setExpanded(True)

        self.item_compressed = QTreeWidgetItem(type_root, ["Compressed"])
        self.item_programs = QTreeWidgetItem(type_root, ["Programs"])
        self.item_video = QTreeWidgetItem(type_root, ["Video"])
        self.item_audio = QTreeWidgetItem(type_root, ["Audio"])
        self.item_documents = QTreeWidgetItem(type_root, ["Documents"])
        self.item_others = QTreeWidgetItem(type_root, ["Others"])

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
            on_browser_download=lambda u, fn, is_v: self.notifier.browser_download_received.emit(u, fn or "", is_v)
        )
        self.bridge_server.start()

    def _handle_browser_download(self, url: str, filename: str, is_video: bool):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.show_add_dialog(initial_url=url, is_media_hint=is_video)

    def _handle_clipboard_url(self, url: str, is_media: bool):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.show_add_dialog(initial_url=url, is_media_hint=is_media)

    def _on_manager_callback(self, event_type: str, item_id: str, **kwargs):
        self.notifier.manager_event.emit(event_type, item_id, kwargs)

    def _handle_manager_event(self, event_type: str, item_id: str, data: dict):
        if event_type == "completed":
            item = db.get_download(item_id)
            if item and self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "Download Completed",
                    f"{item['filename']} has finished downloading.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )
        self._load_downloads_table()

    def show_add_dialog(self, initial_url: str = "", is_media_hint: bool = False):
        dialog = AddDownloadDialog(self, initial_url=initial_url, is_media_hint=is_media_hint)
        if dialog.exec():
            task_id = manager.create_download(
                url=dialog.confirmed_url,
                filename=dialog.confirmed_filename,
                save_dir=dialog.confirmed_save_dir,
                is_video=dialog.is_video,
                video_format=dialog.confirmed_format_id,
                segments_count=dialog.confirmed_segments,
                auto_start=dialog.confirmed_auto_start
            )
            self._load_downloads_table()
            if dialog.confirmed_auto_start:
                self._open_progress_dialog(task_id)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _load_downloads_table(self):
        items = db.get_all_downloads()
        
        # Apply Category Filter
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

            if self.current_category_filter == "All Downloads":
                filtered_items.append(item)
            elif self.current_category_filter == "Downloading" and status == "downloading":
                filtered_items.append(item)
            elif self.current_category_filter == "Finished" and status == "completed":
                filtered_items.append(item)
            elif self.current_category_filter == "Unfinished" and status in ["paused", "pending", "queued", "error"]:
                filtered_items.append(item)
            elif item["category"].lower() == self.current_category_filter.lower():
                filtered_items.append(item)

        # Update category badges
        self.item_all.setText(0, f"All Downloads ({counts['All Downloads']})")
        self.item_downloading.setText(0, f"Downloading ({counts['Downloading']})")
        self.item_finished.setText(0, f"Finished ({counts['Finished']})")
        self.item_unfinished.setText(0, f"Unfinished ({counts['Unfinished']})")

        self.table.setRowCount(len(filtered_items))
        for row, item in enumerate(filtered_items):
            # 0: File Name
            fn_item = QTableWidgetItem(item["filename"])
            fn_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.table.setItem(row, 0, fn_item)

            # 1: Size
            sz_str = format_bytes(item["total_bytes"]) if item["total_bytes"] > 0 else "--"
            self.table.setItem(row, 1, QTableWidgetItem(sz_str))

            # 2: Progress Bar
            pct = 0
            if item["total_bytes"] > 0:
                pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100)
            p_bar = QProgressBar()
            p_bar.setRange(0, 100)
            p_bar.setValue(min(100, pct))
            p_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            p_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #3b82f6;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #2b2d31;
                    color: white;
                    font-size: 11px;
                }
                QProgressBar::chunk {
                    background-color: #3b82f6;
                }
            """)
            self.table.setCellWidget(row, 2, p_bar)

            # 3: Status
            status_item = QTableWidgetItem(item["status"].capitalize())
            if item["status"] == "completed":
                status_item.setForeground(QColor("#22c55e"))
            elif item["status"] == "downloading":
                status_item.setForeground(QColor("#3b82f6"))
            elif item["status"] == "error":
                status_item.setForeground(QColor("#ef4444"))
            self.table.setItem(row, 3, status_item)

            # 4: Speed
            speed_str = format_speed(item["speed"]) if item["status"] == "downloading" else ""
            self.table.setItem(row, 4, QTableWidgetItem(speed_str))

            # 5: Time Left
            eta_str = format_eta(item["eta"]) if item["status"] == "downloading" and item["eta"] > 0 else ""
            self.table.setItem(row, 5, QTableWidgetItem(eta_str))

            # 6: Added
            self.table.setItem(row, 6, QTableWidgetItem(item["added_at"]))

    def _refresh_active_downloads(self):
        """Live updates table cells for downloading rows without full re-render."""
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
                self.table.item(row, 1).setText(sz_str)

                # Update Progress
                pct = 0
                if item["total_bytes"] > 0:
                    pct = int((item["downloaded_bytes"] / item["total_bytes"]) * 100)
                p_bar = self.table.cellWidget(row, 2)
                if isinstance(p_bar, QProgressBar):
                    p_bar.setValue(min(100, pct))

                # Update Status
                self.table.item(row, 3).setText(item["status"].capitalize())
                # Update Speed
                self.table.item(row, 4).setText(format_speed(item["speed"]))
                # Update ETA
                self.table.item(row, 5).setText(format_eta(item["eta"]))

        self.lbl_total_speed.setText(f"Total Speed: {format_speed(total_speed)}")
        self.lbl_active_count.setText(f"Active: {active_count}")

    def _on_category_clicked(self, item, column):
        text = item.text(0).split(" (")[0]
        if text in ["Downloads", "Categories"]:
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
        act_details = menu.addAction("Download Status & Details...")
        act_details.triggered.connect(lambda: self._open_progress_dialog(ids[0]))

        menu.addSeparator()
        act_delete = menu.addAction("🗑 Delete")
        act_delete.triggered.connect(self._delete_selected)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_selected_file(self):
        ids = self._get_selected_task_ids()
        if not ids:
            return
        item = db.get_download(ids[0])
        if item and os.path.exists(item["save_path"]):
            open_file_or_folder(item["save_path"])

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
            open_file_or_folder(item["save_path"])
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
            self.tray_icon.showMessage(
                "DFM is still running",
                "DFM will continue downloading in the background. Right-click the tray icon to exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()
