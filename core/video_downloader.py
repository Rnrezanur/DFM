"""
DFM Media & Streaming Video Downloader.
Integrates yt-dlp to support 1000+ streaming sites (YouTube, Facebook, Twitter/X,
TikTok, Instagram, Vimeo, Reddit, Twitch, HLS m3u8, DASH mpd).
"""

import os
import sys
import logging
import threading
from typing import Dict, List, Optional, Callable

logger = logging.getLogger("DFM.VideoDownloader")

def _get_ydl():
    import yt_dlp
    return yt_dlp

class VideoInfo:
    def __init__(self, title: str, duration: int, thumbnail: str, formats: List[Dict]):
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.formats = formats  # [{"format_id": "...", "resolution": "1080p", "filesize": 12345, "ext": "mp4", "note": "..."}]

class VideoDownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        save_path: str,
        format_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        on_progress: Optional[Callable] = None,
        on_status_change: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        self.id = task_id
        self.url = url
        self.save_path = save_path
        self.format_id = format_id or "bestvideo+bestaudio/best"
        self.headers = headers or {}
        self.on_progress = on_progress
        self.on_status_change = on_status_change
        self.on_complete = on_complete
        self.on_error = on_error

        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.speed = 0.0
        self.eta = 0
        self.status = "pending"
        self.error_message = ""
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

    @classmethod
    def probe_media(cls, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[VideoInfo]:
        """Probe media link without downloading, returning available formats."""
        yt_dlp = _get_ydl()
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        if headers:
            ydl_opts["http_headers"] = headers
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                title = info.get("title", "video")
                duration = info.get("duration", 0)
                thumbnail = info.get("thumbnail", "")

                formats_list = []
                raw_formats = info.get("formats", [])

                # Collect distinct resolutions
                seen_res = set()

                # Add best quality option first
                formats_list.append({
                    "format_id": "bestvideo+bestaudio/best",
                    "resolution": "Best Available (Auto)",
                    "filesize": info.get("filesize") or info.get("filesize_approx") or 0,
                    "ext": "mp4",
                    "note": "Highest quality video & audio"
                })

                # Audio only option
                formats_list.append({
                    "format_id": "bestaudio/best",
                    "resolution": "Audio Only (MP3)",
                    "filesize": 0,
                    "ext": "mp3",
                    "note": "Convert to MP3 audio"
                })

                for f in reversed(raw_formats):
                    res = f.get("format_note") or (f"{f.get('height')}p" if f.get("height") else None)
                    ext = f.get("ext", "mp4")
                    vcodec = f.get("vcodec", "none")
                    if res and res not in seen_res and vcodec != "none":
                        seen_res.add(res)
                        sz = f.get("filesize") or f.get("filesize_approx") or 0
                        formats_list.append({
                            "format_id": f.get("format_id"),
                            "resolution": res,
                            "filesize": sz,
                            "ext": ext,
                            "note": f.get("format_note", "")
                        })

                return VideoInfo(title, duration, thumbnail, formats_list)
        except Exception as e:
            logger.error(f"Failed to probe media {url}: {e}")
            return None

    def start(self):
        self._stop_event.clear()
        self.status = "downloading"
        if self.on_status_change:
            self.on_status_change(self, "downloading")

        self._worker_thread = threading.Thread(target=self._run, daemon=True)
        self._worker_thread.start()

    def cancel(self):
        self._stop_event.set()
        self.status = "canceled"
        if self.on_status_change:
            self.on_status_change(self, "canceled")

    def pause(self):
        # yt-dlp doesn't have an in-process pause, but canceling keeps the .part file on disk so resuming later re-attaches
        self.cancel()
        self.status = "paused"
        if self.on_status_change:
            self.on_status_change(self, "paused")

    def resume(self):
        self.start()

    def _progress_hook(self, d):
        if self._stop_event.is_set():
            yt_dlp = _get_ydl()
            raise yt_dlp.utils.DownloadCancelled("Download canceled by user")

        if d.get("status") == "downloading":
            self.total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or self.total_bytes
            self.downloaded_bytes = d.get("downloaded_bytes", 0)
            self.speed = d.get("speed") or 0.0
            self.eta = d.get("eta") or 0
            if self.on_progress:
                self.on_progress(self)
        elif d.get("status") == "finished":
            self.status = "assembling"
            if self.on_status_change:
                self.on_status_change(self, "assembling")

    def _run(self):
        yt_dlp = _get_ydl()
        out_tmpl = self.save_path
        # If user picked audio-only, format extension
        is_audio_only = "bestaudio" in self.format_id

        ydl_opts = {
            "outtmpl": out_tmpl,
            "format": self.format_id,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 1024,
            "http_chunk_size": 10485760,
        }
        if self.headers:
            ydl_opts["http_headers"] = self.headers

        if is_audio_only:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            self.status = "completed"
            if self.on_status_change:
                self.on_status_change(self, "completed")
            if self.on_complete:
                self.on_complete(self)

        except yt_dlp.utils.DownloadCancelled:
            # Expected on cancel/pause
            pass
        except Exception as e:
            logger.error(f"Video download error: {e}")
            self.status = "error"
            self.error_message = str(e)
            if self.on_status_change:
                self.on_status_change(self, "error")
            if self.on_error:
                self.on_error(self, str(e))
