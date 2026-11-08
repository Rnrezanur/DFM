"""
Generates DFM application icons (.ico and .png).
"""

from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPolygonF, QFont
from PyQt6.QtCore import QPointF, Qt, QRectF
import os

def create_icon():
    size = 256
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Rounded background
    rect = QRectF(12, 12, size - 24, size - 24)
    painter.setBrush(QBrush(QColor("#2563eb"))) # Vibrant Blue
    painter.setPen(QPen(QColor("#60a5fa"), 6))
    painter.drawRoundedRect(rect, 48, 48)

    # Inner lightning / download arrow
    # Downward arrow combined with speed bolt
    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.setPen(Qt.PenStyle.NoPen)

    # Arrow head
    arrow_head = QPolygonF([
        QPointF(128, 195),
        QPointF(65, 125),
        QPointF(100, 125),
        QPointF(100, 55),
        QPointF(156, 55),
        QPointF(156, 125),
        QPointF(191, 125)
    ])
    painter.drawPolygon(arrow_head)

    # Bottom speed bar
    bar_rect = QRectF(65, 208, 126, 14)
    painter.setBrush(QBrush(QColor("#38bdf8"))) # Cyan accent
    painter.drawRoundedRect(bar_rect, 7, 7)

    painter.end()

    os.makedirs("d:/DFM/assets", exist_ok=True)
    png_path = "d:/DFM/assets/dfm_icon.png"
    ico_path = "d:/DFM/assets/dfm_icon.ico"

    img.save(png_path, "PNG")
    img.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation).save(ico_path, "ICO")
    print(f"Icons generated at {png_path} and {ico_path}")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    create_icon()
