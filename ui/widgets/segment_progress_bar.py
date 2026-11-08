"""
DFM Cybernetic Multi-Segment Chunk Visualizer.
Sleek, futuristic real-time display of multi-connection chunk progress.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

class SegmentProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments_data = [] # List of {"index": 0, "progress": 0.5, "status": "downloading"}
        self.setMinimumHeight(42)
        self.overall_progress = 0.0

    def set_segments(self, segments, overall_progress=0.0):
        self.segments_data = segments
        self.overall_progress = overall_progress
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = self.width()
        height = self.height()

        # Outer rounded card background
        bg_rect = QRectF(0, 0, width, height)
        painter.setBrush(QBrush(QColor("#0d0f17")))
        painter.setPen(QPen(QColor("#1e2333"), 1.5))
        painter.drawRoundedRect(bg_rect, 6, 6)

        num_segs = len(self.segments_data)
        if num_segs == 0:
            # Single stream smooth gradient fallback
            fill_w = (width - 8) * min(1.0, max(0.0, self.overall_progress))
            if fill_w > 0:
                fill_rect = QRectF(4, 4, fill_w, height - 8)
                grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
                grad.setColorAt(0, QColor("#2563eb"))
                grad.setColorAt(1, QColor("#38bdf8"))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(fill_rect, 4, 4)
            painter.end()
            return

        gap = 3
        total_gaps = (num_segs - 1) * gap
        avail_width = (width - 8) - total_gaps
        seg_width = avail_width / num_segs

        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)

        for i, seg in enumerate(self.segments_data):
            x = 4 + i * (seg_width + gap)
            y = 4
            h = height - 8
            prog = min(1.0, max(0.0, seg.get("progress", 0.0)))
            status = seg.get("status", "pending")

            seg_rect = QRectF(x, y, seg_width, h)

            # Segment slot background
            painter.setBrush(QBrush(QColor("#151824")))
            painter.setPen(QPen(QColor("#22273a"), 1))
            painter.drawRoundedRect(seg_rect, 3, 3)

            # Fill based on status
            fill_w = seg_width * prog
            if fill_w > 0:
                fill_rect = QRectF(x, y, fill_w, h)
                grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())

                if status == "completed":
                    grad.setColorAt(0, QColor("#059669"))
                    grad.setColorAt(1, QColor("#10b981"))
                elif status == "error":
                    grad.setColorAt(0, QColor("#b91c1c"))
                    grad.setColorAt(1, QColor("#ef4444"))
                elif status == "paused":
                    grad.setColorAt(0, QColor("#d97706"))
                    grad.setColorAt(1, QColor("#f59e0b"))
                else:
                    grad.setColorAt(0, QColor("#2563eb"))
                    grad.setColorAt(1, QColor("#38bdf8"))

                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(fill_rect, 3, 3)

            # Label (Thread number: 1..N) if width allows
            if seg_width > 18:
                painter.setPen(QColor("#64748b" if prog < 0.5 else "#ffffff"))
                painter.drawText(seg_rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))

        painter.end()
