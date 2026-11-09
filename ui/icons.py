"""
DFM Modern Icon Suite.
Generates pixel-perfect, crisp modern vector icons for the IDM-style toolbar,
categories tree, and file-type badges.
"""

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QFileInfo
from PyQt6.QtWidgets import QFileIconProvider

_icon_provider = None

def get_file_icon_provider() -> QFileIconProvider:
    global _icon_provider
    if _icon_provider is None:
        _icon_provider = QFileIconProvider()
    return _icon_provider

def get_native_file_icon(filename: str) -> QIcon:
    """Returns the true operating system icon for this filename, or a styled fallback."""
    try:
        prov = get_file_icon_provider()
        ico = prov.icon(QFileInfo(filename))
        if not ico.isNull():
            return ico
    except Exception:
        pass
    return get_generic_file_icon(filename)

def get_generic_file_icon(filename: str) -> QIcon:
    """Fallback styled badge icon based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    pm = QPixmap(24, 24)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    color_map = {
        "exe": "#3b82f6", "msi": "#2563eb", "bat": "#0284c7",
        "zip": "#eab308", "rar": "#ca8a04", "7z": "#d97706", "tar": "#b45309", "gz": "#b45309",
        "pdf": "#ef4444", "doc": "#2563eb", "docx": "#2563eb", "txt": "#64748b",
        "mp4": "#a855f7", "mkv": "#9333ea", "avi": "#7e22ce", "mov": "#6b21a8",
        "mp3": "#ec4899", "wav": "#db2777", "flac": "#be185d",
        "iso": "#14b8a6", "img": "#0d9488",
        "png": "#10b981", "jpg": "#059669", "jpeg": "#059669"
    }
    bg_color = color_map.get(ext, "#64748b")

    # Draw rounded document badge
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(bg_color))
    p.drawRoundedRect(QRectF(3, 2, 18, 20), 3, 3)

    # Draw text label inside
    p.setPen(QColor("#ffffff"))
    font = p.font()
    font.setPixelSize(7)
    font.setBold(True)
    p.setFont(font)
    tag = ext[:3].upper() if ext else "FILE"
    p.drawText(QRectF(3, 8, 18, 12), Qt.AlignmentFlag.AlignCenter, tag)
    p.end()
    return QIcon(pm)

def make_toolbar_icon(draw_func) -> QIcon:
    """Helper to generate normal and disabled states for high-DPI toolbars."""
    pm = QPixmap(36, 36)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_func(p, is_disabled=False)
    p.end()

    pm_disabled = QPixmap(36, 36)
    pm_disabled.fill(Qt.GlobalColor.transparent)
    p_dis = QPainter(pm_disabled)
    p_dis.setRenderHint(QPainter.RenderHint.Antialiasing)
    p_dis.setOpacity(0.35)
    draw_func(p_dis, is_disabled=True)
    p_dis.end()

    ico = QIcon()
    ico.addPixmap(pm, QIcon.Mode.Normal)
    ico.addPixmap(pm_disabled, QIcon.Mode.Disabled)
    return ico

# ======================== TOOLBAR ACTION ICONS ========================

def icon_add_url() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#22c55e") # Neon green
        p.setPen(QPen(pen_col, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Outer soft ring
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 8, 8)
        # Plus
        p.drawLine(18, 11, 18, 25)
        p.drawLine(11, 18, 25, 18)
    return make_toolbar_icon(draw)

def icon_resume() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#38bdf8") # Sky blue
        p.setPen(QPen(pen_col, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 8, 8)
        # Down Arrow
        p.drawLine(18, 11, 18, 23)
        path = QPainterPath()
        path.moveTo(13, 19)
        path.lineTo(18, 24)
        path.lineTo(23, 19)
        p.drawPath(path)
    return make_toolbar_icon(draw)

def icon_stop() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#f59e0b") # Amber
        p.setPen(QPen(pen_col, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 8, 8)
        # Square stop block
        p.setBrush(pen_col)
        p.drawRoundedRect(QRectF(13, 13, 10, 10), 2, 2)
    return make_toolbar_icon(draw)

def icon_stop_all() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#ef4444") # Red
        p.setPen(QPen(pen_col, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(QRectF(4, 4, 28, 28), 8, 8)
        # Octagon or double stop bars
        p.setBrush(pen_col)
        p.drawRoundedRect(QRectF(11, 12, 5, 12), 1.5, 1.5)
        p.drawRoundedRect(QRectF(20, 12, 5, 12), 1.5, 1.5)
    return make_toolbar_icon(draw)

def icon_delete() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#f43f5e") # Rose
        p.setPen(QPen(pen_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Trash lid
        p.drawLine(10, 12, 26, 12)
        p.drawLine(15, 9, 21, 9)
        # Trash body
        p.drawLine(12, 12, 13, 26)
        p.drawLine(24, 12, 23, 26)
        p.drawLine(13, 26, 23, 26)
        # Slits
        p.drawLine(16, 15, 16, 23)
        p.drawLine(20, 15, 20, 23)
    return make_toolbar_icon(draw)

def icon_delete_completed() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#d946ef") # Fuchsia / Purple
        p.setPen(QPen(pen_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Trash body
        p.drawLine(9, 12, 23, 12)
        p.drawLine(13, 9, 19, 9)
        p.drawLine(11, 12, 12, 25)
        p.drawLine(21, 12, 20, 25)
        p.drawLine(12, 25, 20, 25)
        # Checkmark on right
        check_pen = QColor("#22c55e")
        p.setPen(QPen(check_pen, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(20, 20)
        path.lineTo(24, 24)
        path.lineTo(31, 16)
        p.drawPath(path)
    return make_toolbar_icon(draw)

def icon_options() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#06b6d4") # Cyan
        p.setPen(QPen(pen_col, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Gear circle
        p.drawEllipse(QRectF(11, 11, 14, 14))
        # Cog teeth
        p.drawLine(18, 6, 18, 9)
        p.drawLine(18, 27, 18, 30)
        p.drawLine(6, 18, 9, 18)
        p.drawLine(27, 18, 30, 18)
        p.drawLine(10, 10, 12, 12)
        p.drawLine(24, 24, 26, 26)
        p.drawLine(26, 10, 24, 12)
        p.drawLine(10, 26, 12, 24)
    return make_toolbar_icon(draw)

def icon_scheduler() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#8b5cf6") # Violet
        p.setPen(QPen(pen_col, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QRectF(6, 6, 24, 24))
        # Clock hands
        p.drawLine(18, 18, 18, 11)
        p.drawLine(18, 18, 23, 18)
    return make_toolbar_icon(draw)

def icon_start_queue() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#10b981") # Emerald
        p.setPen(QPen(pen_col, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Tray base
        p.drawLine(7, 24, 29, 24)
        p.drawLine(7, 20, 7, 24)
        p.drawLine(29, 20, 29, 24)
        # Arrow down into tray
        p.drawLine(18, 8, 18, 20)
        path = QPainterPath()
        path.moveTo(13, 16)
        path.lineTo(18, 21)
        path.lineTo(23, 16)
        p.drawPath(path)
    return make_toolbar_icon(draw)

def icon_stop_queue() -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        pen_col = QColor("#525252") if is_disabled else QColor("#f97316") # Orange
        p.setPen(QPen(pen_col, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Tray base
        p.drawLine(7, 24, 29, 24)
        p.drawLine(7, 20, 7, 24)
        p.drawLine(29, 20, 29, 24)
        # Pause bars above tray
        p.setBrush(pen_col)
        p.drawRoundedRect(QRectF(13, 9, 3, 10), 1, 1)
        p.drawRoundedRect(QRectF(20, 9, 3, 10), 1, 1)
    return make_toolbar_icon(draw)

def icon_theme_toggle(is_dark: bool) -> QIcon:
    def draw(p: QPainter, is_disabled: bool):
        if is_dark:
            # Sun icon to switch to light
            pen_col = QColor("#facc15") # Gold sun
            p.setPen(QPen(pen_col, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawEllipse(QRectF(11, 11, 14, 14))
            for i in range(8):
                p.save()
                p.translate(18, 18)
                p.rotate(i * 45)
                p.drawLine(0, -11, 0, -14)
                p.restore()
        else:
            # Crescent moon icon to switch to dark
            pen_col = QColor("#6366f1") # Indigo moon
            p.setPen(QPen(pen_col, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath()
            path.moveTo(24, 9)
            path.cubicTo(14, 9, 10, 18, 15, 27)
            path.cubicTo(9, 23, 9, 13, 24, 9)
            p.setBrush(pen_col)
            p.drawPath(path)
    return make_toolbar_icon(draw)

# ======================== CATEGORY ICONS ========================

def icon_category_folder(color="#eab308") -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    # Folder tab
    p.drawRoundedRect(QRectF(2, 4, 7, 4), 1.5, 1.5)
    # Folder body
    p.drawRoundedRect(QRectF(2, 6, 16, 11), 2, 2)
    p.end()
    return QIcon(pm)

def icon_category_compressed() -> QIcon:
    return icon_category_folder("#eab308") # Yellow

def icon_category_documents() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#3b82f6"), 1.6))
    p.drawRoundedRect(QRectF(4, 2, 12, 16), 2, 2)
    p.drawLine(7, 7, 13, 7)
    p.drawLine(7, 10, 13, 10)
    p.drawLine(7, 13, 11, 13)
    p.end()
    return QIcon(pm)

def icon_category_music() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#ec4899"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(7, 6, 15, 4)
    p.drawLine(7, 6, 7, 14)
    p.drawLine(15, 4, 15, 12)
    p.setBrush(QColor("#ec4899"))
    p.drawEllipse(QRectF(4, 12, 5, 4))
    p.drawEllipse(QRectF(12, 10, 5, 4))
    p.end()
    return QIcon(pm)

def icon_category_programs() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#06b6d4"), 1.8))
    p.drawRoundedRect(QRectF(3, 3, 14, 14), 2, 2)
    p.drawLine(3, 7, 17, 7)
    p.end()
    return QIcon(pm)

def icon_category_video() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#a855f7"), 1.8))
    p.drawRoundedRect(QRectF(3, 4, 14, 12), 2, 2)
    # Play triangle
    path = QPainterPath()
    path.moveTo(8, 7)
    path.lineTo(13, 10)
    path.lineTo(8, 13)
    path.closeSubpath()
    p.setBrush(QColor("#a855f7"))
    p.drawPath(path)
    p.end()
    return QIcon(pm)

def icon_category_unfinished() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#f59e0b"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    # Hourglass
    p.drawLine(5, 4, 15, 4)
    p.drawLine(5, 16, 15, 16)
    p.drawLine(5, 4, 15, 16)
    p.drawLine(15, 4, 5, 16)
    p.end()
    return QIcon(pm)

def icon_category_finished() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#22c55e"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    path = QPainterPath()
    path.moveTo(4, 10)
    path.lineTo(8, 15)
    path.lineTo(16, 5)
    p.drawPath(path)
    p.end()
    return QIcon(pm)

def icon_category_queues() -> QIcon:
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#6366f1"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(4, 5, 16, 5)
    p.drawLine(4, 10, 16, 10)
    p.drawLine(4, 15, 12, 15)
    p.end()
    return QIcon(pm)
