"""
Swiss Precision Vector micro UI widgets for AGY Token Monitor developer HUD.
Includes CircularProgressRing (5-HR), GlowingPulseDot, MiniSparkline, GradientDivider, MinimalProgressBar, and ModelPillBadge.
"""

import math
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QLabel, QPushButton, QWidget


class CircularProgressRing(QWidget):
    """
    Vector-drawn antialiased circular progress ring gauge for 5-Hour Remaining Quota.
    Swiss precision HUD design:
    - 28px diameter ultra-clean circular dial
    - 2.5px hairline precision arc with rounded caps
    - Pure Bone (#F0F2F5) 9px Bold tabular numbers + 4px Cool Gray (#8A909E) '5H' label
    - Dynamic threshold colors:
      - > 40%: Electric Emerald (#00E599)
      - 20% ~ 40%: Amber Gold (#F5A623)
      - < 20%: Coral Red (#FF453A)
    """

    def __init__(
        self,
        size: int = 28,
        ring_width: float = 2.5,
        show_text: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.ring_size = size
        self.ring_width = ring_width
        self.show_text = show_text

        self.setFixedSize(size, size)

        self._target_percent: float = 100.0
        self._current_percent: float = 100.0
        self._bottom_label: str = "5H"
        self._accent_color: Optional[str] = None

        # Smooth value transition animation
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)

    def _on_anim_value(self, value: float) -> None:
        self._current_percent = float(value)
        self.update()

    def set_percent(self, percent: float, animate: bool = True, label: str = "5H", accent_color: Optional[str] = None) -> None:
        """Update target remaining percentage (0.0 - 100.0) with optional smooth animation."""
        clamped = max(0.0, min(100.0, float(percent)))
        self._target_percent = clamped
        self._bottom_label = label
        if accent_color is not None:
            self._accent_color = accent_color

        if not animate:
            self._anim.stop()
            self._current_percent = clamped
            self.update()
            return

        if abs(self._current_percent - clamped) < 0.1:
            self._current_percent = clamped
            self.update()
            return

        self._anim.stop()
        self._anim.setStartValue(self._current_percent)
        self._anim.setEndValue(clamped)
        self._anim.start()

    @property
    def percent(self) -> float:
        return self._target_percent

    def _get_status_color(self, val: float) -> QColor:
        """
        Return threshold-aware precision theme color for 5-Hour Remaining Quota:
        - > 40%: Electric Emerald (#00E599)
        - 20% ~ 40%: Amber Gold (#F5A623)
        - < 20%: Coral Red (#FF453A)
        """
        if val < 20.0:
            return QColor("#ff453a")  # Coral Red (<20%)
        if val <= 40.0:
            return QColor("#f5a623")  # Amber Gold (20~40%)
        if self._accent_color:
            return QColor(self._accent_color)
        return QColor("#00e599")      # Electric Emerald (>40%)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        padding = self.ring_width / 2.0 + 1.0
        rect = QRectF(padding, padding, w - 2 * padding, h - 2 * padding)

        # 1. Background subtle track (18/255 opacity hairline)
        track_pen = QPen(QColor(255, 255, 255, 18), self.ring_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        # 2. Dynamic precision progress arc
        val = self._current_percent
        if val > 0.01:
            color = self._get_status_color(val)
            progress_pen = QPen(color, self.ring_width)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)

            # In Qt coordinates: 90*16 is 12 o'clock, negative angles rotate clockwise
            start_angle = 90 * 16
            span_angle = -int((val / 100.0) * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 3. Stepped Center Typography
        if self.show_text:
            center_x = w / 2.0
            center_y = h / 2.0

            # Percentage number text (Pure Bone #F0F2F5)
            pct_font = QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold)
            pct_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            painter.setFont(pct_font)
            painter.setPen(QColor("#f0f2f5"))

            if val >= 99.9:
                pct_text = "100"
            elif val <= 0.1:
                pct_text = "0"
            elif val < 99.5:
                pct_text = f"{int(round(val))}"
            else:
                pct_text = "99"

            fm = QFontMetrics(pct_font)
            tw = fm.horizontalAdvance(pct_text)
            painter.drawText(QPointF(center_x - tw / 2.0, center_y + 1.5), pct_text)

            # Bottom micro label (Cool Gray #8A909E, 4pt DemiBold)
            sub_font = QFont("Segoe UI Variable Display", 4, QFont.Weight.DemiBold)
            sub_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            painter.setFont(sub_font)
            painter.setPen(QColor(138, 144, 158, 200))
            sub_fm = QFontMetrics(sub_font)
            sub_w = sub_fm.horizontalAdvance(self._bottom_label)
            painter.drawText(QPointF(center_x - sub_w / 2.0, center_y + 6.5), self._bottom_label)

        painter.end()


class GlowingPulseDot(QWidget):
    """
    Swiss Precision breathing pulse indicator.
    - 6px pure dot with restrained breathing micro-halo.
    - AI generating: 0.5s breathing oscillation.
    - Idle: constant sharp 6px dot with 1px subtle ambient rim.
    - Precision colors: Electric Emerald (#00E599), Deep Iris (#7B61FF), Amber Gold (#F5A623), Coral Red (#FF453A).
    """

    def __init__(self, size: int = 6, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.dot_size = size
        total_dim = size + 8
        self.setFixedSize(total_dim, total_dim)

        self.is_generating: bool = False
        self.status: str = "safe"  # "safe", "warning", "danger", "claude", "codex", "idle"

        # Smooth breathing animation timer (35ms tick -> ~0.5s cycle)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(35)
        self.anim_timer.timeout.connect(self._on_tick)
        self.phase: float = 0.0

    def set_state(self, is_generating: bool, status: str = "safe") -> None:
        """Update generation pulse state and status theme."""
        self.status = status
        if is_generating != self.is_generating:
            self.is_generating = is_generating
            if is_generating:
                if not self.anim_timer.isActive():
                    self.anim_timer.start()
            else:
                self.anim_timer.stop()
                self.phase = 0.0
        self.update()

    def set_percent_status(self, percent: float, is_generating: bool = False, group_name: str = "GEMINI") -> None:
        """Convenience method to set state based on quota percent and group."""
        if percent < 20.0:
            st = "danger"
        elif percent <= 40.0:
            st = "warning"
        elif "claude" in group_name.lower() or "gpt" in group_name.lower():
            st = "claude"
        else:
            st = "safe"
        self.set_state(is_generating=is_generating, status=st)

    def _on_tick(self) -> None:
        # 0.5s cycle: 2 * pi in ~14.3 ticks (35ms * 14.3 ≈ 500ms)
        self.phase = (self.phase + 0.44) % (2 * math.pi)
        self.update()

    def _get_base_color(self) -> QColor:
        if self.status in ("danger", "critical"):
            return QColor(255, 69, 58)    # Coral Red (#FF453A)
        elif self.status in ("warning", "demo"):
            return QColor(245, 166, 35)   # Amber Gold (#F5A623)
        elif self.status == "claude":
            return QColor(229, 123, 57)   # Claude Terracotta (#E57B39)
        elif self.status == "copilot":
            return QColor(88, 166, 255)   # GitHub Electric Blue (#58A6FF)
        elif self.status == "codex":
            return QColor(16, 163, 127)   # OpenAI Green (#10A37F)
        elif self.status == "iris":
            return QColor(123, 97, 255)   # Deep Iris (#7B61FF)
        elif self.status == "idle":
            return QColor(138, 144, 158)  # Cool Gray (#8A909E)
        return QColor(0, 229, 153)        # Electric Emerald (#00E599)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        core_r = self.dot_size / 2.0
        base_c = self._get_base_color()

        r_val, g_val, b_val = base_c.red(), base_c.green(), base_c.blue()

        if self.is_generating:
            # Clean, restrained breathing halo (0.5s cycle)
            wave = 0.5 + 0.5 * math.sin(self.phase)
            glow_radius = core_r + 1.2 + 1.8 * wave
            peak_alpha = int(140 * (0.30 + 0.70 * wave))

            glow_grad = QRadialGradient(cx, cy, glow_radius)
            glow_grad.setColorAt(0.0, QColor(r_val, g_val, b_val, peak_alpha))
            glow_grad.setColorAt(0.65, QColor(r_val, g_val, b_val, int(peak_alpha * 0.35)))
            glow_grad.setColorAt(1.0, QColor(r_val, g_val, b_val, 0))

            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - glow_radius, cy - glow_radius, glow_radius * 2, glow_radius * 2))
        else:
            # Ambient micro halo (1px subtle rim)
            glow_radius = core_r + 1.0
            ambient_grad = QRadialGradient(cx, cy, glow_radius)
            ambient_grad.setColorAt(0.0, QColor(r_val, g_val, b_val, 50))
            ambient_grad.setColorAt(0.8, QColor(r_val, g_val, b_val, 15))
            ambient_grad.setColorAt(1.0, QColor(r_val, g_val, b_val, 0))

            painter.setBrush(QBrush(ambient_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - glow_radius, cy - glow_radius, glow_radius * 2, glow_radius * 2))

        # Sharp solid core 6px dot
        painter.setBrush(QBrush(base_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - core_r, cy - core_r, self.dot_size, self.dot_size))

        # Precision highlight specular
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.drawEllipse(QRectF(cx - core_r * 0.4, cy - core_r * 0.4, core_r * 0.65, core_r * 0.65))

        painter.end()


# Backward compatibility alias
PulsingDot = GlowingPulseDot


class MiniSparkline(QWidget):
    """
    Swiss precision vector sparkline showing TPM rate history.
    - 1.2px hairline curve
    - 5% ultra-subtle transparent vertical area gradient
    - Precise endpoint dot
    """

    def __init__(
        self,
        width: int = 120,
        height: int = 20,
        max_points: int = 24,
        line_color: str = "#00e599",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.max_points = max_points
        self.line_color = QColor(line_color)
        self.data_points: List[float] = []

    def add_point(self, value: float) -> None:
        self.data_points.append(float(value))
        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)
        self.update()

    def set_data(self, points: List[float]) -> None:
        self.data_points = [float(p) for p in points[-self.max_points:]]
        self.update()

    def clear(self) -> None:
        self.data_points.clear()
        self.update()

    def set_line_color(self, color_str: str) -> None:
        self.line_color = QColor(color_str)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        padding = 1.5

        if len(self.data_points) < 2:
            base_pen = QPen(QColor(255, 255, 255, 14), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(base_pen)
            painter.drawLine(QPointF(padding, h / 2.0), QPointF(w - padding, h / 2.0))
            painter.end()
            return

        min_val = min(self.data_points)
        max_val = max(self.data_points)
        val_range = max_val - min_val
        if val_range <= 0.001:
            val_range = max(1.0, max_val * 0.1)

        step_x = (w - 2 * padding) / float(len(self.data_points) - 1)
        chart_h = h - 2 * padding

        coords = []
        for i, val in enumerate(self.data_points):
            x = padding + i * step_x
            norm_y = (val - min_val) / val_range
            y = (h - padding) - (norm_y * chart_h)
            coords.append(QPointF(x, y))

        # Area gradient (5% top to 0% bottom)
        fill_path = QPainterPath()
        fill_path.moveTo(coords[0].x(), h - padding)
        for pt in coords:
            fill_path.lineTo(pt)
        fill_path.lineTo(coords[-1].x(), h - padding)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, padding, 0, h - padding)
        r, g, b = self.line_color.red(), self.line_color.green(), self.line_color.blue()
        grad.setColorAt(0.0, QColor(r, g, b, 14))  # ~5.5% opacity
        grad.setColorAt(1.0, QColor(r, g, b, 0))
        painter.fillPath(fill_path, QBrush(grad))

        # Precision 1.2px hairline line
        line_path = QPainterPath()
        line_path.moveTo(coords[0])
        for pt in coords[1:]:
            line_path.lineTo(pt)

        line_pen = QPen(self.line_color, 1.2)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(line_pen)
        painter.drawPath(line_path)

        # Endpoint micro dot
        last_pt = coords[-1]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(r, g, b, 60)))
        painter.drawEllipse(last_pt, 2.8, 2.8)
        painter.setBrush(QBrush(self.line_color))
        painter.drawEllipse(last_pt, 1.6, 1.6)

        painter.end()


class GradientDivider(QWidget):
    """Refined 1px hairline vertical gradient divider line for HUD layouts."""

    def __init__(self, height: int = 18, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(1, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.5, QColor(255, 255, 255, 30))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.end()


class MinimalProgressBar(QWidget):
    """4px ultra-narrow Swiss rounded progress bar."""

    def __init__(self, height: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._percent: float = 100.0
        self._fill_color: QColor = QColor("#00e599")

    def set_percent(self, pct: float, color: Optional[str] = None) -> None:
        self._percent = max(0.0, min(100.0, float(pct)))
        if color:
            self._fill_color = QColor(color)
        else:
            if self._percent < 20.0:
                self._fill_color = QColor("#ff453a")
            elif self._percent <= 40.0:
                self._fill_color = QColor("#f5a623")
            else:
                self._fill_color = QColor("#00e599")
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.rect()
        radius = self.height() / 2.0

        # Background track
        painter.setBrush(QBrush(QColor(255, 255, 255, 15)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(r, radius, radius)

        # Fill chunk
        fill_w = (self._percent / 100.0) * float(self.width())
        if fill_w > 0:
            fill_rect = QRectF(0, 0, fill_w, float(self.height()))
            painter.setBrush(QBrush(self._fill_color))
            painter.drawRoundedRect(fill_rect, radius, radius)

        painter.end()


class ChevronButton(QPushButton):
    """
    Precision vector-drawn 1.2px hairline chevron toggle button.
    Eliminates text glyph glitches and renders a sharp, minimalist chevron (ˆ / ˇ).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ExpandChevronBtn")
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expanded: bool = False

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.update()

    def is_expanded(self) -> bool:
        return self._expanded

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Subtle background on hover
        if self.underMouse():
            painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 4, 4)

        # 1.2px vector hairline chevron
        color = QColor("#f0f2f5") if self.underMouse() else QColor("#8a909e")
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        s = 3.2

        path = QPainterPath()
        if self._expanded:
            # Chevron pointing up (ˆ)
            path.moveTo(cx - s, cy + 1.2)
            path.lineTo(cx, cy - 2.0)
            path.lineTo(cx + s, cy + 1.2)
        else:
            # Chevron pointing down (ˇ)
            path.moveTo(cx - s, cy - 1.2)
            path.lineTo(cx, cy + 2.0)
            path.lineTo(cx + s, cy - 1.2)

        painter.drawPath(path)
        painter.end()


class GeometricDot(QWidget):
    """
    Minimal 4px/6px solid geometric dot indicator for status/groups (Zero Emoji).
    """

    def __init__(self, size: int = 5, color: str = "#00e599", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.dot_size = size
        self.dot_color = QColor(color)
        self.setFixedSize(size + 4, size + 4)

    def set_color(self, color_str: str) -> None:
        self.dot_color = QColor(color_str)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = self.dot_size / 2.0
        painter.setBrush(QBrush(self.dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r, cy - r, self.dot_size, self.dot_size))
        painter.end()


class ModelPillBadge(QLabel):
    """Styled micro-pill badge showing model name or group in pure typography."""

    def __init__(self, model_name: str = "GEMINI 2.5", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ModelPillTag")
        self.update_model_name(model_name)

    def update_model_name(self, raw_name: str) -> None:
        norm = raw_name.lower().strip()
        if "gemini" in norm:
            if "flash" in norm:
                display = "GEMINI FLASH"
            elif "3.7" in norm or "3-7" in norm:
                display = "GEMINI 3.7"
            else:
                display = "GEMINI PRO"
        elif "claude" in norm:
            if "sonnet" in norm:
                display = "CLAUDE 3.7"
            elif "opus" in norm:
                display = "CLAUDE OPUS"
            else:
                display = "CLAUDE 3.5"
        elif "gpt" in norm or "o1" in norm or "o3" in norm:
            display = "OPENAI GPT"
        else:
            clean = raw_name.replace("models/", "").replace("-preview", "").upper()
            display = clean[:14]

        self.setText(display)


class ContextProgressWidget(QWidget):
    """Context bar kept for backward compatibility."""

    def __init__(self, width: int = 34, height: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._percent: float = 0.0

    def set_percent(self, pct: float) -> None:
        self._percent = max(0.0, min(100.0, pct))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(r, 2, 2)

        fill_w = int((self._percent / 100.0) * self.width())
        if fill_w > 0:
            fill_rect = QRectF(0, 0, fill_w, self.height())
            painter.setBrush(QBrush(QColor("#00e599")))
            painter.drawRoundedRect(fill_rect, 2, 2)
        painter.end()
