"""
DFM Multi-Threaded Segmented Download Engine.
Splits downloads into concurrent chunk streams with resume, pause, speed limit,
and per-segment live status tracking just like IDM.
"""

import os
import time
import json
import logging
import threading
import requests
from typing import List, Dict, Optional, Callable
from urllib.parse import urlparse

logger = logging.getLogger("DFM.Downloader")

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 DFM/2.0"
CHUNK_SIZE = 256 * 1024  # 256 KB high-throughput read buffer (IDM-grade)

class DownloadSegment:
    def __init__(self, index: int, start: int, end: int, downloaded: int = 0):
        self.index = index
        self.start = start
        self.end = end
        self.downloaded = downloaded
        self.status = "pending"  # pending, downloading, paused, completed, error
        self.error_msg = ""
        self.speed = 0.0

    @property
    def total_bytes(self) -> int:
        if self.end == -1:
            return 0
        return (self.end - self.start) + 1

    @property
    def progress(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(1.0, self.downloaded / self.total_bytes)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "start": self.start,
            "end": self.end,
            "downloaded": self.downloaded,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict):
        seg = cls(data["index"], data["start"], data["end"], data.get("downloaded", 0))
        seg.status = data.get("status", "pending")
        return seg


class DownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        segments_count: int = 16,
        headers: Optional[Dict] = None,
        on_progress: Optional[Callable] = None,
        on_status_change: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        self.id = task_id
        self.url = url
        self.save_path = save_path
        self.num_segments = max(1, min(segments_count, 32))
        self.headers = headers or {}
        if "User-Agent" not in self.headers and "user-agent" not in self.headers:
            self.headers["User-Agent"] = DEFAULT_USER_AGENT

        self.on_progress = on_progress
        self.on_status_change = on_status_change
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.status = "pending"  # pending, downloading, paused, completed, error
        self.supports_range = False
        self.error_message = ""
        self.segments: List[DownloadSegment] = []

        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_threads: List[threading.Thread] = []
        self._monitor_thread: Optional[threading.Thread] = None

        self.speed = 0.0
        self.eta = 0
        self._last_downloaded = 0
        self._last_speed_time = time.time()
        self.speed_limit_bytes_per_sec: Optional[int] = None

        # Lock for thread-safe dynamic segment splitting & progress aggregation
        self._lock = threading.Lock()

        # Dedicated high-speed connection pool
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=32,
            pool_maxsize=32,
            max_retries=3,
            pool_block=False
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_part_file_path(self, segment_index: int) -> str:
        return f"{self.save_path}.part{segment_index}"

    def get_meta_file_path(self) -> str:
        return f"{self.save_path}.dfm_meta"

    def probe(self) -> bool:
        """Send HEAD/GET range test request to inspect file size and range support."""
        try:
            head_headers = dict(self.headers)
            head_headers["Range"] = "bytes=0-0"
            resp = self.session.get(self.url, headers=head_headers, stream=True, timeout=12, allow_redirects=True)
            
            # Final URL after redirects
            self.url = resp.url
            status_code = resp.status_code

            if status_code == 206:
                self.supports_range = True
                content_range = resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    try:
                        self.total_bytes = int(content_range.split("/")[-1])
                    except ValueError:
                        self.total_bytes = 0
            else:
                self.supports_range = False
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    self.total_bytes = int(cl)

            # Close response connection
            resp.close()
            return True
        except Exception as e:
            logger.warning(f"Probe failed for {self.url}: {e}")
            self.error_message = str(e)
            return False

    def setup_segments(self):
        """Partition file into segments based on total_bytes."""
        meta_path = self.get_meta_file_path()
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                self.total_bytes = meta.get("total_bytes", self.total_bytes)
                self.supports_range = meta.get("supports_range", self.supports_range)
                self.segments = [DownloadSegment.from_dict(d) for d in meta.get("segments", [])]
                
                # Verify existing parts on disk
                for seg in self.segments:
                    part_file = self.get_part_file_path(seg.index)
                    if os.path.exists(part_file):
                        seg.downloaded = os.path.getsize(part_file)
                        if seg.total_bytes > 0 and seg.downloaded >= seg.total_bytes:
                            seg.status = "completed"
                return
            except Exception as e:
                logger.error(f"Error reading existing meta: {e}")

        self.segments = []
        if self.supports_range and self.total_bytes > (self.num_segments * 1024 * 128):
            chunk_size = self.total_bytes // self.num_segments
            for i in range(self.num_segments):
                start = i * chunk_size
                end = (start + chunk_size - 1) if i < self.num_segments - 1 else (self.total_bytes - 1)
                self.segments.append(DownloadSegment(i, start, end))
        else:
            # Single stream fallback
            self.segments.append(DownloadSegment(0, 0, self.total_bytes - 1 if self.total_bytes > 0 else -1))

        self.save_metadata()

    def save_metadata(self):
        meta_path = self.get_meta_file_path()
        try:
            data = {
                "url": self.url,
                "save_path": self.save_path,
                "total_bytes": self.total_bytes,
                "supports_range": self.supports_range,
                "segments": [seg.to_dict() for seg in self.segments]
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata {meta_path}: {e}")

    def start(self):
        """Start or resume the download threads."""
        self._stop_event.clear()
        self._pause_event.clear()

        # Ensure target folder exists
        os.makedirs(os.path.dirname(os.path.abspath(self.save_path)), exist_ok=True)

        if not self.segments:
            if not self.probe():
                self.set_status("error", f"Connection failed: {self.error_message}")
                return
            self.setup_segments()

        self.set_status("downloading")

        self._worker_threads = []
        for seg in self.segments:
            if seg.status != "completed":
                t = threading.Thread(target=self._download_segment_worker, args=(seg,), daemon=True)
                self._worker_threads.append(t)
                t.start()

        self._monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self._monitor_thread.start()

    def pause(self):
        """Pause all worker threads gracefully."""
        self._pause_event.set()
        self.set_status("paused")
        self.save_metadata()

    def resume(self):
        """Resume paused download."""
        if self.status in ["paused", "error"]:
            self.start()

    def cancel(self):
        """Stop download and clean up part files."""
        self._stop_event.set()
        self._pause_event.set()
        self.set_status("canceled")
        # Cleanup
        for seg in self.segments:
            part_path = self.get_part_file_path(seg.index)
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
        meta_path = self.get_meta_file_path()
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
            except Exception:
                pass

    def set_status(self, new_status: str, error_msg: str = ""):
        self.status = new_status
        if error_msg:
            self.error_message = error_msg
        if self.on_status_change:
            self.on_status_change(self, new_status)

    def _try_split_largest_segment(self, finished_worker_seg: DownloadSegment) -> Optional[DownloadSegment]:
        """
        IDM Dynamic Work-Stealing / Segment Splitting.
        When a worker finishes early, it dynamically splits the largest remaining chunk,
        keeping all connections 100% active until download completes.
        """
        with self._lock:
            if not self.supports_range or self._stop_event.is_set() or self._pause_event.is_set():
                return None

            if len(self.segments) >= 32:
                return None

            best_seg = None
            best_remaining = 0
            for s in self.segments:
                if s.status == "downloading" and s.end > 0:
                    current_pos = s.start + s.downloaded
                    rem = s.end - current_pos + 1
                    if rem > best_remaining:
                        best_remaining = rem
                        best_seg = s

            # Only split if remaining is at least 3 MB
            MIN_SPLIT_SIZE = 3 * 1024 * 1024
            if best_seg is None or best_remaining < MIN_SPLIT_SIZE:
                return None

            current_pos = best_seg.start + best_seg.downloaded
            split_point = current_pos + (best_remaining // 2)

            old_end = best_seg.end
            best_seg.end = split_point

            new_index = len(self.segments)
            new_seg = DownloadSegment(new_index, split_point + 1, old_end)
            new_seg.status = "pending"
            self.segments.append(new_seg)

            logger.info(
                f"IDM Dynamic Split: Segment {best_seg.index} split at byte {split_point}. "
                f"Created segment {new_index} for remaining {(old_end - split_point) / (1024 * 1024):.2f} MB"
            )
            return new_seg

    def _download_segment_worker(self, initial_seg: DownloadSegment):
        """Worker thread loop with dynamic work stealing."""
        current_seg = initial_seg
        while not self._stop_event.is_set() and not self._pause_event.is_set():
            self._download_single_segment(current_seg)
            if current_seg.status != "completed":
                break

            # Try to steal work from the largest remaining segment
            next_seg = self._try_split_largest_segment(current_seg)
            if next_seg is None:
                break
            current_seg = next_seg

    def _download_single_segment(self, seg: DownloadSegment):
        part_path = self.get_part_file_path(seg.index)
        
        # Verify existing bytes on disk
        if os.path.exists(part_path):
            seg.downloaded = os.path.getsize(part_path)
        else:
            seg.downloaded = 0

        # Check if already done
        if seg.total_bytes > 0 and seg.downloaded >= seg.total_bytes:
            seg.status = "completed"
            return

        seg.status = "downloading"
        req_headers = dict(self.headers)
        req_headers["Connection"] = "keep-alive"
        req_headers["Accept-Encoding"] = "identity"

        if self.supports_range:
            current_start = seg.start + seg.downloaded
            if seg.end > 0 and current_start > seg.end:
                seg.status = "completed"
                return
            req_headers["Range"] = f"bytes={current_start}-{seg.end}" if seg.end > 0 else f"bytes={current_start}-"
        else:
            # Single connection with no range support
            if seg.downloaded > 0:
                seg.downloaded = 0

        max_retries = 5
        retries = 0

        while retries < max_retries and not self._stop_event.is_set() and not self._pause_event.is_set():
            try:
                mode = "ab" if seg.downloaded > 0 and self.supports_range else "wb"
                with self.session.get(self.url, headers=req_headers, stream=True, timeout=15) as resp:
                    if resp.status_code not in (200, 206):
                        raise Exception(f"HTTP status {resp.status_code}")

                    with open(part_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                            if self._stop_event.is_set() or self._pause_event.is_set():
                                break
                            if chunk:
                                f.write(chunk)
                                chunk_len = len(chunk)
                                seg.downloaded += chunk_len

                                # Boundary check if dynamically split
                                if seg.end > 0:
                                    current_pos = seg.start + seg.downloaded
                                    if current_pos >= seg.end + 1:
                                        seg.status = "completed"
                                        return
                                
                                # Speed limiter delay if configured
                                if self.speed_limit_bytes_per_sec and self.speed_limit_bytes_per_sec > 0:
                                    per_thread_limit = self.speed_limit_bytes_per_sec / max(1, len(self.segments))
                                    expected_time = chunk_len / per_thread_limit
                                    time.sleep(min(expected_time * 0.8, 0.2))

                # Done reading stream or interrupted
                if self._pause_event.is_set():
                    seg.status = "paused"
                    return
                if self._stop_event.is_set():
                    seg.status = "canceled"
                    return

                # Check if segment completed
                if seg.total_bytes <= 0 or seg.downloaded >= seg.total_bytes:
                    seg.status = "completed"
                    return
                else:
                    # Stream ended prematurely, retry remaining
                    retries += 1
                    if self.supports_range:
                        current_start = seg.start + seg.downloaded
                        req_headers["Range"] = f"bytes={current_start}-{seg.end}" if seg.end > 0 else f"bytes={current_start}-"
                    time.sleep(1)

            except Exception as e:
                retries += 1
                logger.warning(f"Segment {seg.index} attempt {retries} failed: {e}")
                time.sleep(1.5)
                if self.supports_range:
                    current_start = seg.start + seg.downloaded
                    req_headers["Range"] = f"bytes={current_start}-{seg.end}" if seg.end > 0 else f"bytes={current_start}-"

        if seg.status != "completed":
            if self._pause_event.is_set():
                seg.status = "paused"
            elif self._stop_event.is_set():
                seg.status = "canceled"
            else:
                seg.status = "error"
                seg.error_msg = "Exceeded max retries"

    def _monitor_worker(self):
        """Calculates download speed, ETA, saves metadata, and merges parts upon completion."""
        self._last_speed_time = time.time()
        self._last_downloaded = sum(seg.downloaded for seg in self.segments)

        while not self._stop_event.is_set() and not self._pause_event.is_set():
            time.sleep(0.5)
            now = time.time()
            elapsed = now - self._last_speed_time

            total_down = sum(seg.downloaded for seg in self.segments)
            self.downloaded_bytes = total_down

            if elapsed >= 0.5:
                delta = total_down - self._last_downloaded
                self.speed = max(0.0, delta / elapsed)
                self._last_downloaded = total_down
                self._last_speed_time = now

                # Calculate ETA
                if self.total_bytes > 0 and self.speed > 0:
                    remaining = max(0, self.total_bytes - total_down)
                    self.eta = int(remaining / self.speed)
                else:
                    self.eta = 0

            # Notify progress callback
            if self.on_progress:
                self.on_progress(self)

            # Check if all completed
            all_done = all(seg.status == "completed" for seg in self.segments)
            any_error = any(seg.status == "error" for seg in self.segments)

            if all_done:
                self._finalize_download()
                return
            elif any_error and all(seg.status in ["completed", "error"] for seg in self.segments):
                self.set_status("error", "One or more download segments failed")
                return

    def _finalize_download(self):
        """Merges all .part files into final save_path."""
        self.set_status("assembling")
        logger.info(f"Merging {len(self.segments)} parts into {self.save_path}...")
        try:
            # If only 1 segment, simply rename
            if len(self.segments) == 1:
                part0 = self.get_part_file_path(0)
                if os.path.exists(self.save_path):
                    os.remove(self.save_path)
                os.replace(part0, self.save_path)
            else:
                # Merge multiple parts in strict byte offset order
                temp_merged = self.save_path + ".merging"
                sorted_segments = sorted(self.segments, key=lambda s: s.start)
                with open(temp_merged, "wb") as outfile:
                    for seg in sorted_segments:
                        part_file = self.get_part_file_path(seg.index)
                        if os.path.exists(part_file):
                            with open(part_file, "rb") as infile:
                                while True:
                                    buf = infile.read(8 * 1024 * 1024) # 8 MB fast streaming buffer
                                    if not buf:
                                        break
                                    outfile.write(buf)
                            # Remove segment part file
                            try:
                                os.remove(part_file)
                            except Exception:
                                pass
                if os.path.exists(self.save_path):
                    os.remove(self.save_path)
                os.replace(temp_merged, self.save_path)

            # Remove meta file
            meta_path = self.get_meta_file_path()
            if os.path.exists(meta_path):
                try:
                    os.remove(meta_path)
                except Exception:
                    pass

            self.set_status("completed")
            from core.utils import trim_memory, apply_mark_of_the_web
            apply_mark_of_the_web(self.save_path, self.url)
            trim_memory()
            if self.on_complete:
                self.on_complete(self)

        except Exception as e:
            logger.error(f"Error finalizing download: {e}")
            self.set_status("error", f"Assembly failed: {e}")
            if self.on_error:
                self.on_error(self, str(e))
