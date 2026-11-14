"""
DFM (Download Fast Manager) - SQLite Database Manager
Persists downloads, states, segments, settings, and categories.
"""

import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("DFM.Database")

DB_DIR = os.path.join(os.path.expanduser("~"), ".dfm")
DB_PATH = os.path.join(DB_DIR, "dfm.db")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Downloads table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                save_path TEXT NOT NULL,
                total_bytes INTEGER DEFAULT 0,
                downloaded_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',  -- pending, downloading, paused, completed, error
                speed INTEGER DEFAULT 0,        -- bytes per second
                eta INTEGER DEFAULT 0,          -- seconds
                category TEXT DEFAULT 'Others',
                is_video INTEGER DEFAULT 0,
                segments_count INTEGER DEFAULT 8,
                segments_data TEXT DEFAULT '[]', -- JSON serialization of segment offsets
                headers TEXT DEFAULT '{}',      -- Custom headers / cookies
                added_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT
            )
            """)

            # Settings table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """)
            conn.commit()
            self._init_default_settings()

    def _init_default_settings(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads", "DFM")
        defaults = {
            "default_download_dir": default_dir,
            "max_concurrent_downloads": "5",
            "default_segments": "16",
            "speed_limit_enabled": "0",
            "speed_limit_kbps": "0",
            "clipboard_monitor": "1",
            "browser_bridge_port": "9666",
            "auto_start_downloads": "1",
            "close_to_tray": "1",
            "theme": "dark"
        }
        for k, v in defaults.items():
            if self.get_setting(k) is None:
                self.set_setting(k, v)

    def get_setting(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value))
            )
            conn.commit()

    def get_all_settings(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def add_download(self, item_dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO downloads (
                id, url, filename, save_path, total_bytes, downloaded_bytes,
                status, speed, eta, category, is_video, segments_count,
                segments_data, headers, added_at, completed_at, error_message
            ) VALUES (
                :id, :url, :filename, :save_path, :total_bytes, :downloaded_bytes,
                :status, :speed, :eta, :category, :is_video, :segments_count,
                :segments_data, :headers, :added_at, :completed_at, :error_message
            )
            """, item_dict)
            conn.commit()

    def update_download(self, download_id, **kwargs):
        if not kwargs:
            return
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v)
        values.append(download_id)
        query = f"UPDATE downloads SET {', '.join(fields)} WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(values))
            conn.commit()

    def delete_download(self, download_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            conn.commit()

    def get_download(self, download_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_downloads(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM downloads ORDER BY added_at DESC")
            return [dict(row) for row in cursor.fetchall()]

db = Database()
