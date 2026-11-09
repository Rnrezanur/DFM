"""
DFM Browser Integration Server.
Local REST API for browser extensions, userscripts, and command-line triggers.
"""

import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Optional

logger = logging.getLogger("DFM.BrowserBridge")

class BridgeRequestHandler(BaseHTTPRequestHandler):
    on_browser_download: Optional[Callable] = None

    def log_message(self, format, *args):
        # Silence default stderr logging
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status" or self.path == "/":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = json.dumps({"status": "running", "app": "DFM", "version": "2.0"}).encode("utf-8")
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ("/download", "/add"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body) if body else {}

                url = data.get("url")
                filename = data.get("filename")
                is_video = bool(data.get("is_video", False))
                cookies = data.get("cookies", "")
                referer = data.get("referer", "")
                user_agent = data.get("userAgent", "")

                headers = dict(data.get("headers", {}) or {})
                if referer:
                    headers["Referer"] = referer
                if user_agent:
                    headers["User-Agent"] = user_agent
                if cookies:
                    headers["Cookie"] = cookies

                if url and BridgeRequestHandler.on_browser_download:
                    BridgeRequestHandler.on_browser_download(url, filename, is_video, headers)

                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "accepted"}')
            except Exception as e:
                logger.error(f"Error handling browser download request: {e}")
                self.send_response(500)
                self._send_cors_headers()
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


class BrowserBridgeServer:
    def __init__(self, port: int = 9666, on_browser_download: Optional[Callable] = None):
        self.port = port
        self.on_browser_download = on_browser_download
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        BridgeRequestHandler.on_browser_download = self.on_browser_download
        try:
            self._httpd = HTTPServer(("127.0.0.1", self.port), BridgeRequestHandler)
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
            logger.info(f"Browser bridge listening on http://127.0.0.1:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start browser bridge on port {self.port}: {e}")

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
