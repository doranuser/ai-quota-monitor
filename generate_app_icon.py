"""
Generates high-resolution Swiss Precision Dark Titanium HUD icons (app.ico and icon.png).
Packs multi-size PNG frames into a native multi-resolution Windows ICO (256, 128, 64, 48, 32, 16).
"""

import io
from pathlib import Path
import struct
import sys

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "src" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def draw_hud_icon(size: int) -> QImage:
    """Draw a vector-quality Swiss Precision HUD icon at specified dimension."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    s = float(size)
    pad = s * 0.04
    radius = s * 0.22

    # 1. Outer Titanium Dark Plate with subtle gradient
    bg_path = QPainterPath()
    bg_rect = QRectF(pad, pad, s - 2 * pad, s - 2 * pad)
    bg_path.addRoundedRect(bg_rect, radius, radius)

    grad = QLinearGradient(0, pad, 0, s - pad)
    grad.setColorAt(0.0, QColor(22, 25, 32))   # Dark Titanium Top
    grad.setColorAt(1.0, QColor(10, 11, 14))   # Obsidian Bottom
    painter.fillPath(bg_path, QBrush(grad))

    # Hairline rim stroke
    rim_pen = QPen(QColor(255, 255, 255, 40), max(1.0, s * 0.02))
    painter.setPen(rim_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(bg_path)

    # 2. Outer Subtle Multi-Arc HUD Meter (Emerald, Iris, Blue)
    center_x = s / 2.0
    center_y = s / 2.0
    ring_radius = s * 0.36
    ring_rect = QRectF(center_x - ring_radius, center_y - ring_radius, ring_radius * 2, ring_radius * 2)

    # Track
    track_pen = QPen(QColor(255, 255, 255, 18), max(1.5, s * 0.045))
    track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(track_pen)
    painter.drawArc(ring_rect, 0, 360 * 16)

    # Arc 1: Electric Emerald (#00e599 - AGY)
    emerald_pen = QPen(QColor(0, 229, 153), max(1.5, s * 0.045))
    emerald_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(emerald_pen)
    painter.drawArc(ring_rect, 45 * 16, 120 * 16)

    # Arc 2: Deep Iris (#7b61ff - Claude)
    iris_pen = QPen(QColor(123, 97, 255), max(1.5, s * 0.045))
    iris_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(iris_pen)
    painter.drawArc(ring_rect, 195 * 16, 90 * 16)

    # Arc 3: Copilot Blue (#58a6ff - Copilot)
    blue_pen = QPen(QColor(88, 166, 255), max(1.5, s * 0.045))
    blue_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(blue_pen)
    painter.drawArc(ring_rect, 305 * 16, 75 * 16)

    # 3. Geometric Center Quad Matrix Dots
    dot_radius = max(1.2, s * 0.028)
    offset = s * 0.13

    # Top-Left: Emerald (AGY)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(0, 229, 153)))
    painter.drawEllipse(QPointF(center_x - offset, center_y - offset), dot_radius, dot_radius)

    # Top-Right: Iris (Claude)
    painter.setBrush(QBrush(QColor(123, 97, 255)))
    painter.drawEllipse(QPointF(center_x + offset, center_y - offset), dot_radius, dot_radius)

    # Bottom-Left: Copilot Blue
    painter.setBrush(QBrush(QColor(88, 166, 255)))
    painter.drawEllipse(QPointF(center_x - offset, center_y + offset), dot_radius, dot_radius)

    # Bottom-Right: Warm Amber
    painter.setBrush(QBrush(QColor(245, 166, 35)))
    painter.drawEllipse(QPointF(center_x + offset, center_y + offset), dot_radius, dot_radius)

    # 4. Center High-Precision Typography "AGY"
    if size >= 32:
        font_size = int(s * 0.22)
        font = QFont("Segoe UI Variable Display", font_size, QFont.Weight.Black)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)
        painter.setPen(QColor(240, 242, 245))  # Pure Bone #F0F2F5

        fm = QFontMetrics(font)
        text = "AGY"
        tw = fm.horizontalAdvance(text)
        th = fm.capHeight()
        painter.drawText(QPointF(center_x - tw / 2.0, center_y + th / 2.0 - s * 0.01), text)
    else:
        # Center micro core dot
        painter.setBrush(QBrush(QColor(240, 242, 245)))
        painter.drawEllipse(QPointF(center_x, center_y), dot_radius * 1.4, dot_radius * 1.4)

    painter.end()
    return img


def qimage_to_png_bytes(img: QImage) -> bytes:
    """Convert QImage to in-memory PNG bytes."""
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def create_multi_res_ico(png_data_list: list, output_path: Path) -> None:
    """
    Pack multiple PNG byte streams into a standard Windows .ico file.
    Structure:
    - ICONDIR (6 bytes): 0 (uint16), 1 (uint16), count (uint16)
    - Array of ICONDIRENTRY (16 bytes each)
    - Raw image bytes
    """
    count = len(png_data_list)
    header = struct.pack("<HHH", 0, 1, count)

    entries = []
    offset = 6 + count * 16

    for sz, data in png_data_list:
        w = 0 if sz >= 256 else sz
        h = 0 if sz >= 256 else sz
        size_bytes = len(data)
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, size_bytes, offset)
        entries.append(entry)
        offset += size_bytes

    with open(output_path, "wb") as f:
        f.write(header)
        for entry in entries:
            f.write(entry)
        for _, data in png_data_list:
            f.write(data)


def main():
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    # 1. Generate 256x256 PNG
    img_256 = draw_hud_icon(256)
    png_path = ASSETS_DIR / "icon.png"
    img_256.save(str(png_path), "PNG")
    print(f"Generated PNG: {png_path}")

    # 2. Multi-size ICO: 256, 128, 64, 48, 32, 16
    sizes = [256, 128, 64, 48, 32, 16]
    png_list = []
    for sz in sizes:
        im = draw_hud_icon(sz)
        raw_png = qimage_to_png_bytes(im)
        png_list.append((sz, raw_png))

    ico_path = ASSETS_DIR / "app.ico"
    create_multi_res_ico(png_list, ico_path)
    print(f"Generated multi-resolution ICO (256/128/64/48/32/16): {ico_path}")


if __name__ == "__main__":
    main()
