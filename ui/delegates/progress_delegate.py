"""
High-Performance Progress Bar & Status Pill Delegate.
Renders progress bars and status badges directly with QPainter,
completely eliminating QWidget memory overhead per row.
"""

from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QFont

class ModernProgressDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        # Progress value stored as integer 0..100 in Qt.ItemDataRole.UserRole
        pct = index.data(Qt.ItemDataRole.UserRole)
        if pct is None:
            pct = 0
        try:
            pct = int(pct)
        except (ValueError, TypeError):
            pct = 0

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = option.rect
        # Margins inside cell
        margin_x = 10
        margin_y = 7
        bar_rect = QRectF(
            rect.x() + margin_x,
            rect.y() + margin_y,
            rect.width() - (margin_x * 2),
            rect.height() - (margin_y * 2)
        )

        # Background track
        painter.setBrush(QBrush(QColor("#141724")))
        painter.setPen(QPen(QColor("#23283b"), 1))
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Filled track
        fill_width = (bar_rect.width() - 2) * (min(100, max(0, pct)) / 100.0)
        if fill_width > 0:
            fill_rect = QRectF(bar_rect.x() + 1, bar_rect.y() + 1, fill_width, bar_rect.height() - 2)
            gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            if pct >= 100:
                gradient.setColorAt(0, QColor("#059669")) # Emerald
                gradient.setColorAt(1, QColor("#10b981"))
            else:
                gradient.setColorAt(0, QColor("#2563eb")) # Royal Blue
                gradient.setColorAt(1, QColor("#38bdf8")) # Sky Cyan
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(fill_rect, 3, 3)

        # Percentage text
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff" if pct > 45 else "#94a3b8"))
        painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, f"{pct}%")

        painter.restore()


class ModernStatusPillDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        status_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        status_lower = status_text.lower()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = option.rect
        pill_height = 20
        pill_y = rect.y() + (rect.height() - pill_height) / 2.0

        # Colors based on state
        if "completed" in status_lower:
            bg_color = QColor("#064e3b")
            border_color = QColor("#059669")
            text_color = QColor("#34d399")
            icon_char = "✓"
        elif "downloading" in status_lower:
            bg_color = QColor("#1e3a8a")
            border_color = QColor("#2563eb")
            text_color = QColor("#60a5fa")
            icon_char = "⬇"
        elif "paused" in status_lower:
            bg_color = QColor("#451a03")
            border_color = QColor("#d97706")
            text_color = QColor("#fbbf24")
            icon_char = "⏸"
        elif "assembling" in status_lower:
            bg_color = QColor("#3b0764")
            border_color = QColor("#9333ea")
            text_color = QColor("#c084fc")
            icon_char = "⚡"
        else: # error / pending
            bg_color = QColor("#450a0a")
            border_color = QColor("#dc2626")
            text_color = QColor("#f87171")
            icon_char = "⚠"

        label = f"{icon_char} {status_text.capitalize()}"

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        # Calculate text width
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(label)
        pill_width = text_w + 16

        pill_rect = QRectF(rect.x() + 6, pill_y, pill_width, pill_height)

        # Draw Pill
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(pill_rect, 10, 10)

        # Draw Text
        painter.setPen(text_color)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.restore()
