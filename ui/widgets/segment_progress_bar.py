"""
DFM Segmented Progress Visualizer Widget.
Custom-painted Qt widget showing IDM-style multi-connection chunk progress.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

class SegmentProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments_data = [] # List of {"index": 0, "progress": 0.5, "status": "downloading"}
        self.setMinimumHeight(32)
        self.overall_progress = 0.0

    def set_segments(self, segments, overall_progress=0.0):
        self.segments_data = segments
        self.overall_progress = overall_progress
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        width = self.width()
        height = self.height()

        # Background
        bg_rect = QRectF(0, 0, width, height)
        painter.fillRect(bg_rect, QColor("#1e1f22"))

        # Border
        painter.setPen(QPen(QColor("#35373c"), 1))
        painter.drawRect(0, 0, width - 1, height - 1)

        num_segs = len(self.segments_data)
        if num_segs == 0:
            # Draw overall progress if no segments
            fill_w = (width - 4) * min(1.0, max(0.0, self.overall_progress))
            painter.fillRect(QRectF(2, 2, fill_w, height - 4), QColor("#3b82f6"))
            painter.end()
            return

        gap = 2
        total_gaps = (num_segs - 1) * gap
        avail_width = (width - 4) - total_gaps
        seg_width = avail_width / num_segs

        for i, seg in enumerate(self.segments_data):
            x = 2 + i * (seg_width + gap)
            y = 2
            h = height - 4
            prog = min(1.0, max(0.0, seg.get("progress", 0.0)))
            status = seg.get("status", "pending")

            # Segment slot background
            painter.fillRect(QRectF(x, y, seg_width, h), QColor("#2b2d31"))

            # Fill color based on status
            if status == "completed":
                fill_color = QColor("#22c55e") # Green
            elif status == "error":
                fill_color = QColor("#ef4444") # Red
            elif status == "paused":
                fill_color = QColor("#eab308") # Yellow
            else:
                fill_color = QColor("#3b82f6") # Blue (Active)

            # Draw filled portion
            fill_w = seg_width * prog
            if fill_w > 0:
                painter.fillRect(QRectF(x, y, fill_w, h), fill_color)

            # Segment border
            painter.setPen(QPen(QColor("#404249"), 1))
            painter.drawRect(int(x), int(y), int(seg_width), int(h))

        painter.end()
