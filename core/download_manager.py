"""
DFM Central Download Manager.
Coordinates active tasks, queue scheduling, concurrency limits, database syncing,
and global speed limits.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Callable, List

from core.database import db
from core.downloader import DownloadTask
from core.video_downloader import VideoDownloadTask
from core.utils import get_category_for_filename

logger = logging.getLogger("DFM.Manager")

class DownloadManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.active_tasks: Dict[str, object] = {} # id -> DownloadTask or VideoDownloadTask
        self.listeners: List[Callable] = []

    def register_listener(self, callback: Callable):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def unregister_listener(self, callback: Callable):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify(self, event_type: str, item_id: str, **kwargs):
        for listener in self.listeners:
            try:
                listener(event_type, item_id, **kwargs)
            except Exception as e:
                logger.error(f"Error in listener callback: {e}")

    def create_download(
        self,
        url: str,
        filename: str,
        save_dir: str,
        is_video: bool = False,
        video_format: Optional[str] = None,
        segments_count: int = 16,
        headers: Optional[Dict] = None,
        auto_start: bool = True
    ) -> str:
        task_id = str(uuid.uuid4())
        save_path = os.path.join(save_dir, filename)
        category = "Video" if is_video else get_category_for_filename(filename)

        headers_str = "{}"
        if headers:
            try:
                import json
                headers_str = json.dumps(headers) if isinstance(headers, dict) else str(headers)
            except Exception:
                headers_str = "{}"

        item_dict = {
            "id": task_id,
            "url": url,
            "filename": filename,
            "save_path": save_path,
            "total_bytes": 0,
            "downloaded_bytes": 0,
            "status": "pending",
            "speed": 0,
            "eta": 0,
            "category": category,
            "is_video": 1 if is_video else 0,
            "segments_count": segments_count,
            "segments_data": "[]",
            "headers": headers_str,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
            "error_message": ""
        }
        db.add_download(item_dict)
        self._notify("added", task_id, item=item_dict)

        if auto_start:
            self.start_download(task_id, video_format=video_format)

        return task_id

    def start_download(self, task_id: str, video_format: Optional[str] = None):
        item = db.get_download(task_id)
        if not item:
            return

        # Check concurrency
        max_concurrent = int(db.get_setting("max_concurrent_downloads", "3"))
        current_running = sum(1 for t in self.active_tasks.values() if t.status == "downloading")
        
        if current_running >= max_concurrent:
            logger.info(f"Concurrency limit reached ({max_concurrent}). Queuing {task_id}")
            db.update_download(task_id, status="queued")
            self._notify("status_changed", task_id, status="queued")
            return

        # Speed limit
        speed_limit_enabled = db.get_setting("speed_limit_enabled", "0") == "1"
        speed_limit_kbps = int(db.get_setting("speed_limit_kbps", "0"))
        limit_bytes = (speed_limit_kbps * 1024) if speed_limit_enabled and speed_limit_kbps > 0 else None

        hdrs = {}
        if item.get("headers"):
            try:
                import json
                hdrs = json.loads(item["headers"]) if isinstance(item["headers"], str) else item["headers"]
            except Exception:
                hdrs = {}

        if item["is_video"] == 1:
            task = VideoDownloadTask(
                task_id=task_id,
                url=item["url"],
                save_path=item["save_path"],
                format_id=video_format,
                headers=hdrs,
                on_progress=lambda t: self._on_task_progress(t),
                on_status_change=lambda t, s: self._on_task_status_change(t, s),
                on_complete=lambda t: self._on_task_complete(t),
                on_error=lambda t, err: self._on_task_error(t, err)
            )
        else:
            task = DownloadTask(
                task_id=task_id,
                url=item["url"],
                save_path=item["save_path"],
                segments_count=item["segments_count"] or 16,
                headers=hdrs,
                on_progress=lambda t: self._on_task_progress(t),
                on_status_change=lambda t, s: self._on_task_status_change(t, s),
                on_complete=lambda t: self._on_task_complete(t),
                on_error=lambda t, err: self._on_task_error(t, err)
            )
            task.speed_limit_bytes_per_sec = limit_bytes

        self.active_tasks[task_id] = task
        db.update_download(task_id, status="downloading")
        self._notify("status_changed", task_id, status="downloading")
        task.start()

    def pause_download(self, task_id: str):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].pause()
            del self.active_tasks[task_id]
        db.update_download(task_id, status="paused", speed=0)
        self._notify("status_changed", task_id, status="paused")
        self._check_queue()

    def resume_download(self, task_id: str):
        self.start_download(task_id)

    def stop_all(self):
        for task_id in list(self.active_tasks.keys()):
            self.pause_download(task_id)

    def delete_download(self, task_id: str, delete_file: bool = False):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]

        item = db.get_download(task_id)
        if item and delete_file and os.path.exists(item["save_path"]):
            try:
                os.remove(item["save_path"])
            except Exception as e:
                logger.error(f"Could not delete physical file: {e}")

        db.delete_download(task_id)
        self._notify("deleted", task_id)
        self._check_queue()

    def _check_queue(self):
        """Picks up queued or pending downloads if concurrency permits."""
        max_concurrent = int(db.get_setting("max_concurrent_downloads", "3"))
        current_running = sum(1 for t in self.active_tasks.values() if t.status == "downloading")
        
        if current_running < max_concurrent:
            all_downloads = db.get_all_downloads()
            for d in all_downloads:
                if d["status"] == "queued":
                    self.start_download(d["id"])
                    current_running += 1
                    if current_running >= max_concurrent:
                        break

    def _on_task_progress(self, task):
        db.update_download(
            task.id,
            total_bytes=task.total_bytes,
            downloaded_bytes=task.downloaded_bytes,
            speed=int(task.speed),
            eta=task.eta
        )
        self._notify("progress", task.id, speed=task.speed, eta=task.eta,
                     total_bytes=task.total_bytes, downloaded_bytes=task.downloaded_bytes)

    def _on_task_status_change(self, task, status):
        err = getattr(task, "error_message", "")
        if status == "error":
            db.update_download(task.id, status=status, error_message=err, speed=0)
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            self._notify("error", task.id, error_message=err)
            self._check_queue()
        else:
            db.update_download(task.id, status=status)
            self._notify("status_changed", task.id, status=status)

    def _on_task_complete(self, task):
        db.update_download(
            task.id,
            status="completed",
            speed=0,
            eta=0,
            downloaded_bytes=task.total_bytes,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        self._notify("completed", task.id)
        self._check_queue()

    def _on_task_error(self, task, error_msg):
        db.update_download(task.id, status="error", error_message=error_msg, speed=0)
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        self._notify("error", task.id, error_message=error_msg)
        self._check_queue()

manager = DownloadManager()
