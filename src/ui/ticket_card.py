"""
Japanese Retro Ticket / Stationery style quota monitor cards for AGY Token Monitor.
Inspired by tactile paper-grid ticket aesthetics: warm cream paper (#F4F1E8),
crisp dark ink borders (#1C1B18), mascot illustrations, bold circular remaining gauge,
Today / Yesterday / 30-Day local token counters, mini bar sparkline, estimated API cost,
and weekly/monthly secondary quota bar.
"""

import datetime
import math
import platform
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import MASCOTS_DIR, PRICING_TABLE_DATE, get_usage_history_summary
from ..monitor.multi_cli_parser import (
    ALL_CLIS,
    CLI_AGY,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_COPILOT,
    GROUP_CLAUDE_GPT,
    GROUP_GEMINI,
    MultiCliQuotaState,
    QuotaWindow,
)
from ..monitor.token_parser import SessionTokenStats

# Warm retro paper palette
PAPER_BG = "#F4F1E8"
PAPER_BG_ALT = "#ECE7DA"
INK_DARK = "#1C1B18"
INK_MUTED = "#5C584F"
INK_LIGHT = "#787368"
BORDER_COLOR = "#26241F"
ALERT_RED = "#B63A2B"
FRESH_GREEN = "#256B3A"

# Per-CLI ticket persona & palette configuration
TICKET_CLI_PROFILES: Dict[str, Dict[str, str]] = {
    CLI_AGY: {
        "index": "01",
        "seat_name": "可愛龍席",
        "hero_title": "GEMINI",
        "accent": "#256B3A",       # Deep Forest Green
        "accent_soft": "#4A8B5E",
        "window_label": "5 小時視窗 / 剩餘",
        "secondary_label": "每週額度",
        "mascot_file": "gemini_dragon.png",
    },
    CLI_CLAUDE_CODE: {
        "index": "02",
        "seat_name": "暖橘貓席",
        "hero_title": "CLAUDE",
        "accent": "#B34B24",       # Retro Terracotta
        "accent_soft": "#D07550",
        "window_label": "5 小時視窗 / 剩餘",
        "secondary_label": "每週額度 (7 天)",
        "mascot_file": "claude_cat.png",
    },
    CLI_COPILOT: {
        "index": "03",
        "seat_name": "海藍章魚席",
        "hero_title": "COPILOT",
        "accent": "#1E5280",       # Retro Indigo Blue
        "accent_soft": "#4B7CA8",
        "window_label": "Premium 額度 / 剩餘",
        "secondary_label": "滾動速率限制",
        "mascot_file": "copilot_octo.png",
    },
    CLI_CODEX: {
        "index": "04",
        "seat_name": "翠綠柴犬席",
        "hero_title": "CODEX",
        "accent": "#146356",       # Retro Teal
        "accent_soft": "#3D8C7E",
        "window_label": "5 小時視窗 / 剩餘",
        "secondary_label": "7 天額度",
        "mascot_file": "codex_shiba.png",
    },
}


def format_reset_detail(window: QuotaWindow, current_time: Optional[float] = None) -> str:
    """Format reset countdown and local target timestamp, e.g. '2 小時 47 分鐘後重設 · 11月24日 15:48'."""
    now = current_time or time.time()
    rem = window.get_remaining_seconds(current_time=now)
    if rem <= 0:
        if window.percent >= 99.9:
            return "額度已滿 · 隨時可用"
        return "等待下一次配額重設"

    target_dt = datetime.datetime.fromtimestamp(now + rem)
    date_part = f"{target_dt.month}月{target_dt.day}日 {target_dt.hour:02d}:{target_dt.minute:02d}"

    days = rem // 86400
    hours = (rem % 86400) // 3600
    minutes = (rem % 3600) // 60

    if days > 0:
        dur_part = f"{days} 天 {hours} 小時後重設"
    elif hours > 0:
        dur_part = f"{hours} 小時 {minutes} 分鐘後重設"
    else:
        dur_part = f"{max(1, minutes)} 分鐘後重設"

    return f"{dur_part} · {date_part}"


def format_relative_ago(timestamp: float, current_time: Optional[float] = None) -> str:
    """Format elapsed time since last sync in Traditional Chinese."""
    if not timestamp or timestamp <= 0:
        return "尚未同步"
    now = current_time or time.time()
    diff = max(0, int(now - timestamp))
    if diff < 60:
        return "剛剛"
    mins = diff // 60
    if mins < 60:
        return f"{mins}分鐘前"
    hours = mins // 60
    if hours < 24:
        return f"{hours}小時前"
    days = hours // 24
    return f"{days}天前"


def _device_platform_label() -> str:
    sys_name = platform.system()
    if sys_name == "Windows":
        return "Windows"
    if sys_name == "Darwin":
        return "Mac"
    return sys_name or "本機"


class TicketDonutGauge(QWidget):
    """Right-hand solid accent block with bold white circular remaining ring and percentage."""

    def __init__(self, accent_color: str = "#256B3A", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._percent: float = 100.0
        self._accent = QColor(accent_color)
        self.setFixedWidth(134)
        self.setMinimumHeight(134)

    def set_data(self, percent: float, accent_color: Optional[str] = None) -> None:
        self._percent = max(0.0, min(100.0, float(percent)))
        if accent_color:
            self._accent = QColor(accent_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect()
        # Solid accent background block
        painter.fillRect(rect, self._accent)

        # Left vertical separator line
        painter.setPen(QPen(QColor(BORDER_COLOR), 1.5))
        painter.drawLine(0, 0, 0, rect.height())

        # Donut ring geometry
        side = min(rect.width(), rect.height()) - 28
        side = max(72, min(98, side))
        cx = rect.width() / 2.0
        cy = rect.height() / 2.0
        ring_rect = QRectF(cx - side / 2.0, cy - side / 2.0, side, side)
        stroke_w = 8.5

        # Subtle semi-transparent track
        track_pen = QPen(QColor(255, 255, 255, 72), stroke_w)
        track_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(ring_rect)

        # Bold white progress arc starting at 12 o'clock clockwise
        if self._percent > 0.1:
            arc_pen = QPen(QColor("#FFFFFF"), stroke_w)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            start_angle = 90 * 16
            span_angle = -int((self._percent / 100.0) * 360 * 16)
            painter.drawArc(ring_rect, start_angle, span_angle)

        # Center percentage text
        pct_text = f"{int(round(self._percent))}%"
        pct_font = QFont("Microsoft JhengHei UI", 17, QFont.Weight.Black)
        painter.setFont(pct_font)
        painter.setPen(QColor("#FFFFFF"))
        fm = QFontMetrics(pct_font)
        tw = fm.horizontalAdvance(pct_text)
        painter.drawText(QPointF(cx - tw / 2.0, cy + 4.0), pct_text)

        # Sub-label "剩餘"
        sub_text = "剩餘"
        sub_font = QFont("Microsoft JhengHei UI", 8, QFont.Weight.Bold)
        painter.setFont(sub_font)
        painter.setPen(QColor(255, 255, 255, 230))
        sfm = QFontMetrics(sub_font)
        stw = sfm.horizontalAdvance(sub_text)
        painter.drawText(QPointF(cx - stw / 2.0, cy + 20.0), sub_text)

        painter.end()


class TicketBarSparkline(QWidget):
    """30-day mini vertical bar chart with dotted baseline matching the reference ticket card."""

    def __init__(self, accent_color: str = "#256B3A", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._series: List[int] = [0] * 30
        self._accent = QColor(accent_color)
        self.setMinimumSize(104, 42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, series: List[int], accent_color: Optional[str] = None) -> None:
        if series:
            self._series = [max(0, int(v)) for v in series[-30:]]
        else:
            self._series = [0] * 30
        if accent_color:
            self._accent = QColor(accent_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = float(self.width())
        h = float(self.height())
        pad_x = 6.0
        pad_top = 6.0
        pad_bottom = 6.0
        base_y = h - pad_bottom

        # Dotted baseline
        base_pen = QPen(QColor(INK_DARK), 1.0, Qt.PenStyle.DotLine)
        painter.setPen(base_pen)
        painter.drawLine(QPointF(pad_x, base_y), QPointF(w - pad_x, base_y))

        n = len(self._series)
        if n == 0:
            painter.end()
            return

        max_val = max(self._series)
        if max_val <= 0:
            painter.end()
            return

        chart_w = max(10.0, w - 2 * pad_x)
        chart_h = max(6.0, base_y - pad_top)
        slot_w = chart_w / float(n)
        bar_w = max(1.5, min(3.5, slot_w * 0.65))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._accent))

        for i, val in enumerate(self._series):
            if val <= 0:
                continue
            bh = max(2.0, (val / float(max_val)) * chart_h)
            x = pad_x + i * slot_w + (slot_w - bar_w) / 2.0
            y = base_y - bh
            painter.drawRect(QRectF(x, y, bar_w, bh))

        painter.end()


class TicketLinearBar(QWidget):
    """Crisp bordered retro horizontal progress bar for the footer weekly/monthly quota."""

    def __init__(self, accent_color: str = "#256B3A", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._percent: float = 100.0
        self._accent = QColor(accent_color)
        self.setFixedSize(96, 8)

    def set_data(self, percent: float, accent_color: Optional[str] = None) -> None:
        self._percent = max(0.0, min(100.0, float(percent)))
        if accent_color:
            self._accent = QColor(accent_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setPen(QPen(QColor(INK_DARK), 1.0))
        painter.setBrush(QColor("#DDD8CA"))
        painter.drawRect(rect)

        fill_w = max(0.0, (self.width() - 2.0) * (self._percent / 100.0))
        if fill_w > 0.5:
            fill_color = self._accent
            if self._percent < 20.0:
                fill_color = QColor(ALERT_RED)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawRect(QRectF(1.0, 1.0, fill_w, self.height() - 2.0))

        painter.end()


class RetroLaptopIcon(QWidget):
    """Tiny crisp vector laptop icon for the local-device scope row."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(16, 13)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor(INK_DARK), 1.3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Screen
        painter.drawRect(QRectF(2.5, 1.5, 11.0, 7.5))
        # Base
        painter.drawLine(QPointF(1.0, 10.5), QPointF(15.0, 10.5))
        painter.end()


class MascotWidget(QWidget):
    """
    Animated retro mascot widget preserving the original cute PNG illustration
    while adding natural waddling walk, yawn (Zzz), fire breath / steam / bubbles,
    quota-tier moods, and click interaction.
    """

    def __init__(self, mascot_path: Path, accent_color: str, fallback_code: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(78, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("點擊吉祥物互動！保留原版可愛造型，會散步、打哈欠、噴火並依剩餘額度 % 反應")
        self._mascot_path = mascot_path
        self._mascot_key = mascot_path.stem.lower()
        self._accent = accent_color
        self._fallback_code = fallback_code
        self._pixmap: Optional[QPixmap] = None
        self._pose_pixmaps: Dict[str, QPixmap] = {}
        self._poses_loaded: bool = False
        self._phase: float = random.uniform(0.0, 2.0 * math.pi)
        self._jump_boost: float = 0.0
        self._is_generating: bool = False
        self._quota_percent: float = 100.0

        # Random action & micro-interaction state
        self._action_name: str = "none"
        self._action_progress: float = 0.0
        self._next_action_at: float = time.monotonic() + random.uniform(1.8, 4.2)
        self._is_hovered: bool = False
        self._bubble_text: str = ""
        self._bubble_progress: float = 0.0

        self._load_pixmap(mascot_path)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps buttery smooth animation
        self._anim_timer.timeout.connect(self._on_tick)

    def _load_pixmap(self, path: Path) -> None:
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._pixmap = pm.scaled(
                    56,
                    56,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

    def _ensure_pose_pixmaps_loaded(self) -> None:
        """Lazy-load multi-pose sprite frames only when the mascot actually becomes visible."""
        if self._poses_loaded:
            return
        self._poses_loaded = True
        path = self._mascot_path
        stem = path.stem
        for pose in ("walk1", "walk2", "walk3", "yawn", "sig1", "sig2", "fire"):
            pose_path = path.with_name(f"{stem}_{pose}{path.suffix}")
            if pose_path.exists():
                ppm = QPixmap(str(pose_path))
                if not ppm.isNull():
                    max_dim = 64 if pose in ("sig2", "fire") else 56
                    self._pose_pixmaps[pose] = ppm.scaled(
                        max_dim,
                        max_dim,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

    def set_activity(self, is_generating: bool = False, quota_percent: float = 100.0) -> None:
        self._is_generating = bool(is_generating)
        self._quota_percent = max(0.0, min(100.0, float(quota_percent)))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._ensure_pose_pixmaps_loaded()
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if self._anim_timer.isActive():
            self._anim_timer.stop()

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._jump_boost = 1.0
            if "dragon" in self._mascot_key:
                self._action_name = random.choice(["happy_hop", "breathe_fire"])
                self._bubble_text = "FIRE!" if self._action_name == "breathe_fire" else "ROAR ♪"
            elif "cat" in self._mascot_key:
                self._action_name = random.choice(["happy_hop", "sip_tea"])
                self._bubble_text = "TEA ♪" if self._action_name == "sip_tea" else "MEOW~"
            elif "octo" in self._mascot_key:
                self._action_name = random.choice(["happy_hop", "blow_bubbles"])
                self._bubble_text = "POP!" if self._action_name == "blow_bubbles" else "BLUB~"
            else:
                self._action_name = random.choice(["happy_hop", "wag_bark"])
                self._bubble_text = "WAN!"
            self._action_progress = 1.0
            self._bubble_progress = 1.0
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def _signature_action(self) -> str:
        if "dragon" in self._mascot_key:
            return "breathe_fire"
        if "cat" in self._mascot_key:
            return "sip_tea"
        if "octo" in self._mascot_key:
            return "blow_bubbles"
        return "wag_bark"

    def _pick_random_action(self) -> str:
        pct = self._quota_percent
        sig = self._signature_action()
        if pct >= 80.0:
            return random.choice(["walk", "happy_hop", sig, "yawn", "stretch"])
        if pct >= 40.0:
            return random.choice(["walk", sig, "yawn", "stretch"])
        if pct >= 20.0:
            return random.choice(["walk", "sweat_shake", "yawn"])
        return random.choice(["panic_hop", "sweat_shake"])

    def _on_tick(self) -> None:
        now_mono = time.monotonic()

        if self._is_generating:
            speed = 0.12
        elif self._quota_percent < 20.0:
            speed = 0.10
        elif self._quota_percent < 40.0:
            speed = 0.075
        else:
            speed = 0.05

        self._phase = (self._phase + speed) % (2.0 * math.pi)

        if self._jump_boost > 0.0:
            self._jump_boost = max(0.0, self._jump_boost - 0.04)

        if self._bubble_progress > 0.0:
            self._bubble_progress = max(0.0, self._bubble_progress - 0.018)

        if self._action_progress > 0.0:
            step = 0.010 if self._action_name in ("walk", "yawn", "breathe_fire") else 0.014
            self._action_progress = max(0.0, self._action_progress - step)
            if self._action_progress == 0.0:
                self._action_name = "none"
                self._next_action_at = now_mono + random.uniform(2.6, 5.6)
        elif now_mono >= self._next_action_at:
            self._action_name = self._pick_random_action()
            self._action_progress = 1.0

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0 + 1.0

        pct = self._quota_percent
        p = self._action_progress
        act = self._action_name

        dx = 0.0
        bob_y = 0.0
        tilt_deg = 0.0
        scale_x = 1.0
        scale_y = 1.0
        facing = 1.0

        # Base breathing rhythm by quota tier
        if self._is_generating:
            bob_y = -abs(math.sin(self._phase * 1.6)) * 4.0
            tilt_deg = math.sin(self._phase * 1.6) * 3.8
            scale_y = 1.0 + 0.04 * math.cos(self._phase * 3.2)
        elif pct >= 80.0:
            bob_y = math.sin(self._phase) * 2.0
            tilt_deg = math.sin(self._phase * 0.5) * 1.8
            scale_y = 1.0 + 0.02 * math.sin(self._phase)
        elif pct >= 40.0:
            bob_y = math.sin(self._phase) * 1.6
            tilt_deg = math.sin(self._phase * 0.5) * 1.3
            scale_y = 1.0 + 0.015 * math.sin(self._phase)
        elif pct >= 20.0:
            bob_y = math.sin(self._phase * 1.4) * 1.2
            tilt_deg = math.sin(self._phase * 2.5) * 2.0
            dx = math.sin(self._phase * 3.0) * 0.8
        else:
            bob_y = math.sin(self._phase * 2.0) * 1.0
            tilt_deg = math.sin(self._phase * 5.0) * 3.0
            dx = math.sin(self._phase * 6.0) * 1.5

        # Overlay natural action motion on top of the original cute sprite
        if p > 0.0:
            env = math.sin(p * math.pi)
            if act == "walk":
                stroll = math.sin(p * math.pi * 2.0)
                dx = stroll * 9.0
                facing = -1.0 if math.cos(p * math.pi * 2.0) < 0 else 1.0
                bob_y = -abs(math.sin(p * math.pi * 6.0)) * 3.5
                tilt_deg = math.sin(p * math.pi * 6.0) * 6.5
                scale_y = 1.0 - abs(math.sin(p * math.pi * 6.0)) * 0.04
            elif act == "happy_hop":
                bob_y -= abs(math.sin(p * math.pi * 2.0)) * 7.5
                tilt_deg += math.sin(p * math.pi * 2.0) * 6.5
            elif act == "yawn":
                # Cozy sleepy stretch + slow head tilt
                scale_y += env * 0.07
                scale_x -= env * 0.04
                tilt_deg += env * -5.0
                bob_y -= env * 1.5
            elif act == "breathe_fire":
                # Recoil slightly backward while puffing fire forward
                dx -= env * 3.0
                tilt_deg -= env * 5.0
                scale_x += env * 0.05
                scale_y -= env * 0.03
            elif act == "stretch":
                scale_y += env * 0.09
                scale_x -= env * 0.05
                bob_y -= env * 2.0
            elif act == "sweat_shake":
                dx += math.sin(p * math.pi * 8.0) * 2.4 * env
                tilt_deg += math.sin(p * math.pi * 6.0) * 4.0 * env
            elif act == "panic_hop":
                bob_y -= abs(math.sin(p * math.pi * 3.0)) * 6.0
                dx += math.sin(p * math.pi * 10.0) * 2.2
            elif act == "wag_bark":
                bob_y -= abs(math.sin(p * math.pi * 3.0)) * 4.5
                tilt_deg += math.sin(p * math.pi * 6.0) * 6.0

        if self._jump_boost > 0.0:
            arc = math.sin(self._jump_boost * math.pi)
            bob_y -= arc * 6.0
            tilt_deg += arc * 5.0

        # Ground shadow beneath feet
        ground_y = h - 7.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(28, 27, 24, 30))
        shadow_rx = max(10.0, 16.0 + bob_y * 0.5)
        painter.drawEllipse(QPointF(cx + dx, ground_y), shadow_rx, 2.8)

        # Tiny walking dust puffs behind feet
        if p > 0.08 and act == "walk":
            dust_alpha = int(110 * abs(math.sin(p * math.pi * 6.0)))
            painter.setBrush(QColor(180, 170, 150, dust_alpha))
            painter.drawEllipse(QPointF(cx + dx - facing * 13.0, ground_y - 1.5), 2.8, 2.0)
            painter.drawEllipse(QPointF(cx + dx - facing * 17.0, ground_y - 3.0), 1.8, 1.5)

        # Tier-specific ambient sparkles or sweat drop
        if pct < 40.0:
            drop_color = QColor(ALERT_RED if pct < 20.0 else "#D97706")
            drop_y = 11.0 + (1.0 - (self._phase % math.pi) / math.pi) * 5.0
            painter.setBrush(drop_color)
            painter.drawEllipse(QPointF(w - 10.0, drop_y), 2.1, 3.1)
        else:
            sparkle_color = QColor("#D49B27" if pct >= 80.0 else "#B89B5E")
            for sx, sy, offset in ((9.0, 14.0, 0.0), (w - 10.0, 13.0, 2.1), (w - 9.0, h - 14.0, 4.2)):
                alpha = int(105 + 140 * (0.5 + 0.5 * math.sin(self._phase * 1.6 + offset)))
                size = 1.8 + 1.5 * (0.5 + 0.5 * math.sin(self._phase * 1.6 + offset))
                c = QColor(sparkle_color)
                c.setAlpha(alpha)
                painter.setPen(QPen(c, 1.3))
                painter.drawLine(QPointF(sx - size, sy), QPointF(sx + size, sy))
                painter.drawLine(QPointF(sx, sy - size), QPointF(sx, sy + size))

        # Draw pose sprite frame (or original cute mascot PNG) with natural transform
        active_pm = self._pixmap
        if p > 0.08:
            if act == "walk" and ("walk1" in self._pose_pixmaps or "walk2" in self._pose_pixmaps):
                if "walk3" in self._pose_pixmaps and "walk2" in self._pose_pixmaps and "walk1" in self._pose_pixmaps:
                    cycle = ("walk1", "walk2", "walk3", "walk2")
                    w_key = cycle[int((1.0 - p) * 12.0) % 4]
                else:
                    w_key = "walk1" if int((1.0 - p) * 8.0) % 2 == 0 else "walk2"
                active_pm = self._pose_pixmaps.get(w_key, self._pixmap)
            elif act == "yawn" and "yawn" in self._pose_pixmaps:
                active_pm = self._pose_pixmaps["yawn"]
            elif act in ("breathe_fire", "sip_tea", "blow_bubbles", "wag_bark"):
                # 2-stage signature animation: windup (sig1) -> peak (sig2 / fire)
                if p > 0.65 and "sig1" in self._pose_pixmaps:
                    active_pm = self._pose_pixmaps["sig1"]
                elif "sig2" in self._pose_pixmaps:
                    active_pm = self._pose_pixmaps["sig2"]
                elif act == "breathe_fire" and "fire" in self._pose_pixmaps:
                    active_pm = self._pose_pixmaps["fire"]

        # Draw pose sprite frame anchored at feet baseline so height changes never cause floating
        hover_scale = 1.06 if self._is_hovered else 1.0
        painter.save()
        painter.translate(cx + dx, ground_y + bob_y)
        painter.rotate(tilt_deg)
        painter.scale(scale_x * facing * hover_scale, scale_y * hover_scale)

        if active_pm is not None:
            pw = float(active_pm.width())
            ph = float(active_pm.height())
            painter.drawPixmap(QPointF(-pw / 2.0, -ph), active_pm)
        else:
            badge_rect = QRectF(-24.0, -48.0, 48.0, 48.0)
            painter.setPen(QPen(QColor(INK_DARK), 1.5))
            painter.setBrush(QColor(PAPER_BG_ALT))
            painter.drawRoundedRect(badge_rect, 8.0, 8.0)
            painter.setPen(QColor(self._accent))
            f = QFont("Consolas", 14, QFont.Weight.Black)
            painter.setFont(f)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._fallback_code)

        painter.restore()

        # Floating click reaction micro-bubble
        if self._bubble_progress > 0.0 and self._bubble_text:
            bp = self._bubble_progress
            b_alpha = int(245 * min(1.0, bp * 2.0))
            b_color = QColor(self._accent)
            b_color.setAlpha(b_alpha)
            painter.setPen(b_color)
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Black))
            painter.drawText(QPointF(cx + dx - 12.0, 11.0 - (1.0 - bp) * 8.0), self._bubble_text)

        # Action-specific cute overlays (Zzz yawn, plus fallback effects only if sprite frames absent)
        if p > 0.1:
            env = math.sin(p * math.pi)
            if act == "breathe_fire" and "sig2" not in self._pose_pixmaps and "fire" not in self._pose_pixmaps:
                fx = cx + dx + 13.0
                fy = cy + bob_y - 2.0
                flicker = math.sin(p * math.pi * 10.0) * 1.8
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(235, 82, 38, int(230 * env)))
                painter.drawEllipse(QPointF(fx + 6.0 * env, fy + flicker * 0.4), 8.0 * env, 5.0 * env)
                painter.setBrush(QColor(249, 178, 51, int(240 * env)))
                painter.drawEllipse(QPointF(fx + 4.0 * env, fy - flicker * 0.3), 5.0 * env, 3.2 * env)
                painter.setBrush(QColor(255, 240, 140, int(240 * env)))
                painter.drawEllipse(QPointF(fx + 12.0 * env, fy - 2.0 + flicker), 2.0 * env, 2.0 * env)
            elif act == "yawn":
                c = QColor(INK_MUTED)
                c.setAlpha(int(230 * env))
                painter.setPen(c)
                drift = (1.0 - p) * 10.0
                painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
                painter.drawText(QPointF(cx + dx + 16.0, cy - 12.0 - drift), "z")
                painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
                painter.drawText(QPointF(cx + dx + 22.0, cy - 18.0 - drift * 1.2), "Z")
            elif act == "sip_tea":
                steam_pen = QPen(QColor(255, 255, 255, int(215 * env)), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(steam_pen)
                s_off = math.sin(p * math.pi * 4.0) * 1.8
                painter.drawLine(QPointF(cx + dx - 3.0, cy + 4.0), QPointF(cx + dx - 3.0 + s_off, cy - 5.0 * env))
                painter.drawLine(QPointF(cx + dx + 2.0, cy + 4.0), QPointF(cx + dx + 2.0 - s_off, cy - 6.0 * env))
            elif act == "blow_bubbles":
                painter.setPen(QPen(QColor("#3B82F6"), 1.2))
                painter.setBrush(QColor(186, 230, 253, int(195 * env)))
                painter.drawEllipse(QPointF(cx + dx + 16.0, cy - 4.0 - (1.0 - p) * 10.0), 3.0, 3.0)
                painter.drawEllipse(QPointF(cx + dx + 21.0, cy - 10.0 - (1.0 - p) * 14.0), 2.0, 2.0)
            elif act == "wag_bark":
                c = QColor(self._accent)
                c.setAlpha(int(230 * env))
                painter.setPen(c)
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(QPointF(cx + dx + 16.0, cy - 14.0 - (1.0 - p) * 6.0), "♪")

        painter.end()


class RetroTicketCard(QFrame):
    """
    Complete Japanese Retro Ticket Monitor Card for a single CLI.
    Faithfully reproduces the 6-band paper-grid structure:
      1. Header bar: [01] Seat Name · CLI  |  Freshness / Stale Alert
      2. Main Hero: 5-hr window label, big title, mascot, reset countdown + time, status note  |  Right donut gauge
      3. Device Scope: [laptop] 此 Windows 本機用量，不含其他裝置  |  資料：X分鐘前
      4. Metrics 4-grid: 今天 | 昨天 | 近 30 天 | 30-day mini bar sparkline
      5. Cost bar: 估算 API 等值成本 今天 ≈ US$X.XX · 近 30 天 ≈ US$Y.YY  |  價格表 YYYY-MM-DD
      6. Footer bar: 每週額度 + reset time  |  XX% 剩餘 + bordered bar
    """

    card_clicked = Signal(str)

    def __init__(self, cli_id: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cli_id = cli_id
        self.profile = TICKET_CLI_PROFILES.get(cli_id, TICKET_CLI_PROFILES[CLI_AGY])
        self.setObjectName(f"RetroTicketCard_{cli_id}")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QFrame#RetroTicketCard_{cli_id} {{"
            f"  background-color: {PAPER_BG};"
            f"  border: 1.5px solid {BORDER_COLOR};"
            f"  border-radius: 2px;"
            f"}}"
            f"QFrame#RetroTicketCard_{cli_id} QWidget {{"
            f"  background-color: transparent;"
            f"}}"
        )
        self._build_ui()

    def _make_hline(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER_COLOR}; border: none;")
        return line

    def _make_vline(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet(f"background-color: {BORDER_COLOR}; border: none;")
        return line

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ==================== 1. HEADER BAR ====================
        header_w = QWidget(self)
        header_w.setCursor(Qt.CursorShape.PointingHandCursor)
        header_w.mousePressEvent = lambda e: self.card_clicked.emit(self.cli_id)
        header_lay = QHBoxLayout(header_w)
        header_lay.setContentsMargins(10, 7, 10, 7)
        header_lay.setSpacing(8)

        self.index_badge = QLabel(self.profile["index"], header_w)
        self.index_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index_badge.setFixedSize(28, 20)
        self.index_badge.setStyleSheet(
            f"background-color: {INK_DARK}; color: {PAPER_BG}; "
            f"font-family: 'Consolas', 'Segoe UI', monospace; font-size: 11px; font-weight: 800; "
            f"border-radius: 1px;"
        )

        self.header_title = QLabel(
            f"{self.profile['seat_name']}  ·  {self.profile['hero_title']}", header_w
        )
        self.header_title.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 11.5px; font-weight: 800; letter-spacing: 0.4px;"
        )

        self.status_badge = QLabel("● 資料已同步", header_w)
        self.status_badge.setStyleSheet(
            f"color: {FRESH_GREEN}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10.5px; font-weight: 700;"
        )

        header_lay.addWidget(self.index_badge)
        header_lay.addWidget(self.header_title)
        header_lay.addStretch()
        header_lay.addWidget(self.status_badge)
        root.addWidget(header_w)
        root.addWidget(self._make_hline())

        # ==================== 2. HERO ROW (LEFT INFO + RIGHT DONUT) ====================
        hero_w = QWidget(self)
        hero_lay = QHBoxLayout(hero_w)
        hero_lay.setContentsMargins(0, 0, 0, 0)
        hero_lay.setSpacing(0)

        # Left column
        hero_left = QWidget(hero_w)
        hl_lay = QVBoxLayout(hero_left)
        hl_lay.setContentsMargins(12, 10, 10, 10)
        hl_lay.setSpacing(3)

        top_sub_row = QHBoxLayout()
        top_sub_row.setContentsMargins(0, 0, 0, 0)
        top_sub_row.setSpacing(6)

        title_stack = QVBoxLayout()
        title_stack.setContentsMargins(0, 0, 0, 0)
        title_stack.setSpacing(1)

        self.window_tag = QLabel(self.profile["window_label"], hero_left)
        self.window_tag.setStyleSheet(
            f"color: {ALERT_RED}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10.5px; font-weight: 800;"
        )

        self.hero_title_lbl = QLabel(self.profile["hero_title"], hero_left)
        self.hero_title_lbl.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Arial Black', 'Segoe UI Black', 'Segoe UI', sans-serif; "
            f"font-size: 24px; font-weight: 900; letter-spacing: 0.5px;"
        )

        title_stack.addWidget(self.window_tag)
        title_stack.addWidget(self.hero_title_lbl)

        mascot_path = MASCOTS_DIR / self.profile["mascot_file"]
        self.mascot = MascotWidget(
            mascot_path=mascot_path,
            accent_color=self.profile["accent"],
            fallback_code=self.profile["index"],
            parent=hero_left,
        )

        top_sub_row.addLayout(title_stack, 1)
        top_sub_row.addWidget(self.mascot, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hl_lay.addLayout(top_sub_row)

        self.reset_detail_lbl = QLabel("額度已滿 · 隨時可用", hero_left)
        self.reset_detail_lbl.setStyleSheet(
            f"color: {INK_MUTED}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10.5px; font-weight: 600;"
        )

        self.sync_note_lbl = QLabel("即時監控中，自動同步最新額度狀態。", hero_left)
        self.sync_note_lbl.setWordWrap(True)
        self.sync_note_lbl.setStyleSheet(
            f"color: {INK_LIGHT}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 500;"
        )

        self.last_update_lbl = QLabel("最後更新：剛剛", hero_left)
        self.last_update_lbl.setStyleSheet(
            f"color: {INK_LIGHT}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 500;"
        )

        hl_lay.addWidget(self.reset_detail_lbl)
        hl_lay.addWidget(self.sync_note_lbl)
        hl_lay.addWidget(self.last_update_lbl)

        # Right column: Donut Gauge
        self.donut_gauge = TicketDonutGauge(accent_color=self.profile["accent"], parent=hero_w)

        hero_lay.addWidget(hero_left, 1)
        hero_lay.addWidget(self.donut_gauge, 0)
        root.addWidget(hero_w)
        root.addWidget(self._make_hline())

        # ==================== 3. LOCAL DEVICE SCOPE BAR ====================
        scope_w = QWidget(self)
        scope_lay = QHBoxLayout(scope_w)
        scope_lay.setContentsMargins(10, 6, 10, 6)
        scope_lay.setSpacing(6)

        self.laptop_icon = RetroLaptopIcon(scope_w)
        self.scope_text_lbl = QLabel(f"此 {_device_platform_label()} 本機用量，不含其他裝置", scope_w)
        self.scope_text_lbl.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10.5px; font-weight: 700;"
        )

        self.scope_ago_lbl = QLabel("資料：剛剛", scope_w)
        self.scope_ago_lbl.setStyleSheet(
            f"color: {INK_LIGHT}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 600;"
        )

        scope_lay.addWidget(self.laptop_icon)
        scope_lay.addWidget(self.scope_text_lbl)
        scope_lay.addStretch()
        scope_lay.addWidget(self.scope_ago_lbl)
        root.addWidget(scope_w)
        root.addWidget(self._make_hline())

        # ==================== 4. METRICS 4-GRID (TODAY / YESTERDAY / 30D / SPARKLINE) ====================
        grid_w = QWidget(self)
        grid_lay = QHBoxLayout(grid_w)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setSpacing(0)

        self.today_val_lbl = self._add_metric_cell(grid_lay, "今天", "0")
        grid_lay.addWidget(self._make_vline())
        self.yesterday_val_lbl = self._add_metric_cell(grid_lay, "昨天", "0")
        grid_lay.addWidget(self._make_vline())
        self.days30_val_lbl = self._add_metric_cell(grid_lay, "近 30 天", "0")
        grid_lay.addWidget(self._make_vline())

        spark_container = QWidget(grid_w)
        spark_lay = QVBoxLayout(spark_container)
        spark_lay.setContentsMargins(4, 4, 4, 4)
        spark_lay.setSpacing(0)
        self.bar_sparkline = TicketBarSparkline(accent_color=self.profile["accent"], parent=spark_container)
        spark_lay.addWidget(self.bar_sparkline)
        grid_lay.addWidget(spark_container, 1)

        root.addWidget(grid_w)
        root.addWidget(self._make_hline())

        # ==================== 5. ESTIMATED API COST BAR ====================
        cost_w = QWidget(self)
        cost_lay = QHBoxLayout(cost_w)
        cost_lay.setContentsMargins(10, 7, 10, 7)
        cost_lay.setSpacing(6)

        cost_left = QVBoxLayout()
        cost_left.setContentsMargins(0, 0, 0, 0)
        cost_left.setSpacing(2)

        cost_title = QLabel("估算 API 等值成本", cost_w)
        cost_title.setStyleSheet(
            f"color: {INK_MUTED}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 600;"
        )

        self.cost_summary_lbl = QLabel("今天 ≈ US$0.00 · 近 30 天 ≈ US$0.00", cost_w)
        self.cost_summary_lbl.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Consolas', 'Microsoft JhengHei UI', sans-serif; "
            f"font-size: 11.5px; font-weight: 800;"
        )

        cost_left.addWidget(cost_title)
        cost_left.addWidget(self.cost_summary_lbl)

        self.pricing_date_lbl = QLabel(f"價格表 {PRICING_TABLE_DATE}", cost_w)
        self.pricing_date_lbl.setStyleSheet(
            f"color: {INK_LIGHT}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 9.5px; font-weight: 600;"
        )

        cost_lay.addLayout(cost_left, 1)
        cost_lay.addWidget(self.pricing_date_lbl, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        root.addWidget(cost_w)
        root.addWidget(self._make_hline())

        # ==================== 6. FOOTER SECONDARY QUOTA BAR ====================
        footer_w = QWidget(self)
        footer_lay = QHBoxLayout(footer_w)
        footer_lay.setContentsMargins(10, 7, 10, 8)
        footer_lay.setSpacing(8)

        footer_left = QVBoxLayout()
        footer_left.setContentsMargins(0, 0, 0, 0)
        footer_left.setSpacing(2)

        self.secondary_title_lbl = QLabel(self.profile["secondary_label"], footer_w)
        self.secondary_title_lbl.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 11px; font-weight: 800;"
        )

        self.secondary_reset_lbl = QLabel("額度已滿 · 隨時可用", footer_w)
        self.secondary_reset_lbl.setStyleSheet(
            f"color: {INK_LIGHT}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 600;"
        )

        footer_left.addWidget(self.secondary_title_lbl)
        footer_left.addWidget(self.secondary_reset_lbl)

        footer_right = QVBoxLayout()
        footer_right.setContentsMargins(0, 0, 0, 0)
        footer_right.setSpacing(4)
        footer_right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.secondary_pct_lbl = QLabel("100% 剩餘", footer_w)
        self.secondary_pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.secondary_pct_lbl.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 11px; font-weight: 800;"
        )

        self.secondary_bar = TicketLinearBar(accent_color=self.profile["accent"], parent=footer_w)

        footer_right.addWidget(self.secondary_pct_lbl)
        footer_right.addWidget(self.secondary_bar, 0, Qt.AlignmentFlag.AlignRight)

        footer_lay.addLayout(footer_left, 1)
        footer_lay.addLayout(footer_right, 0)
        root.addWidget(footer_w)

    def _add_metric_cell(self, parent_layout: QHBoxLayout, label_text: str, value_text: str) -> QLabel:
        cell = QWidget(self)
        lay = QVBoxLayout(cell)
        lay.setContentsMargins(8, 7, 8, 8)
        lay.setSpacing(3)

        title = QLabel(label_text, cell)
        title.setStyleSheet(
            f"color: {INK_MUTED}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
            f"font-size: 10px; font-weight: 600;"
        )

        val = QLabel(value_text, cell)
        val.setStyleSheet(
            f"color: {INK_DARK}; font-family: 'Consolas', 'Segoe UI', monospace; "
            f"font-size: 12px; font-weight: 900;"
        )

        lay.addWidget(title)
        lay.addWidget(val)
        parent_layout.addWidget(cell, 1)
        return val

    def update_card(
        self,
        multi_cli: MultiCliQuotaState,
        usage_summary: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
        is_generating: bool = False,
    ) -> None:
        """Refresh all ticket fields from MultiCliQuotaState and 30-day local usage summary."""
        now = current_time or time.time()
        accent = self.profile["accent"]

        # Resolve primary & secondary windows per CLI
        if self.cli_id == CLI_AGY:
            grp = multi_cli.agy.get_active_group()
            primary_win = grp.five_hour
            secondary_win = grp.weekly
            hero_name = "GEMINI" if grp.group_id == GROUP_GEMINI else "CLAUDE/GPT"
            seat = "可愛龍席" if grp.group_id == GROUP_GEMINI else "星紫智席"
            accent = "#256B3A" if grp.group_id == GROUP_GEMINI else "#4B3B8C"
            last_sync = max(primary_win.last_synced_time, multi_cli.agy.last_updated)
        elif self.cli_id == CLI_COPILOT:
            primary_win = multi_cli.copilot.premium_requests
            secondary_win = multi_cli.copilot.rate_limit
            hero_name = "COPILOT"
            seat = self.profile["seat_name"]
            last_sync = max(primary_win.last_synced_time, multi_cli.copilot.last_synced_time)
        elif self.cli_id == CLI_CLAUDE_CODE:
            primary_win = multi_cli.claude.five_hour
            secondary_win = multi_cli.claude.monthly_budget
            hero_name = "CLAUDE"
            seat = self.profile["seat_name"]
            last_sync = max(primary_win.last_synced_time, multi_cli.claude.last_synced_time)
        else:
            primary_win = multi_cli.codex.five_hour
            secondary_win = multi_cli.codex.weekly
            hero_name = "CODEX"
            seat = self.profile["seat_name"]
            last_sync = max(primary_win.last_synced_time, multi_cli.codex.last_synced_time)

        # Header title & active highlight
        is_active = multi_cli.active_cli == self.cli_id
        self.header_title.setText(f"{seat}  ·  {hero_name}")
        if is_active:
            self.index_badge.setStyleSheet(
                f"background-color: {accent}; color: #FFFFFF; "
                f"font-family: 'Consolas', 'Segoe UI', monospace; font-size: 11px; font-weight: 800; "
                f"border-radius: 1px;"
            )
        else:
            self.index_badge.setStyleSheet(
                f"background-color: {INK_DARK}; color: {PAPER_BG}; "
                f"font-family: 'Consolas', 'Segoe UI', monospace; font-size: 11px; font-weight: 800; "
                f"border-radius: 1px;"
            )

        # Freshness / Stale status (> 180s considered stale like reference screenshot)
        is_stale = (last_sync <= 0) or ((now - last_sync) > 180.0)
        ago_str = format_relative_ago(last_sync, now)
        if is_stale:
            self.status_badge.setText("◷ 資料已過期")
            self.status_badge.setStyleSheet(
                f"color: {ALERT_RED}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
                f"font-size: 10.5px; font-weight: 800;"
            )
            self.sync_note_lbl.setText("目前顯示最後一次可用數值，等待新的更新結果。")
        else:
            self.status_badge.setText("● 資料已同步")
            self.status_badge.setStyleSheet(
                f"color: {FRESH_GREEN}; font-family: 'Microsoft JhengHei UI', 'Segoe UI', sans-serif; "
                f"font-size: 10.5px; font-weight: 800;"
            )
            self.sync_note_lbl.setText("即時監控中，自動同步最新額度狀態。")

        # Hero content
        self.hero_title_lbl.setText(hero_name)
        self.reset_detail_lbl.setText(format_reset_detail(primary_win, now))
        self.last_update_lbl.setText(f"最後更新：{ago_str}")
        self.scope_ago_lbl.setText(f"資料：{ago_str}")

        # Donut Gauge & Animated Mascot
        self.donut_gauge.set_data(primary_win.percent, accent_color=accent)
        self.mascot.set_activity(
            is_generating=is_generating and is_active,
            quota_percent=primary_win.percent,
        )

        # Historical local usage & cost
        summary = usage_summary or {}
        today_tok = int(summary.get("today_tokens", 0))
        yest_tok = int(summary.get("yesterday_tokens", 0))
        d30_tok = int(summary.get("last_30_days_tokens", 0))
        today_cost = float(summary.get("today_cost", 0.0))
        d30_cost = float(summary.get("last_30_days_cost", 0.0))
        series = summary.get("daily_series") or [0] * 30

        self.today_val_lbl.setText(f"{today_tok:,}")
        self.yesterday_val_lbl.setText(f"{yest_tok:,}")
        self.days30_val_lbl.setText(f"{d30_tok:,}")
        self.bar_sparkline.set_data(series, accent_color=accent)
        self.cost_summary_lbl.setText(
            f"今天 ≈ US${today_cost:.2f}  ·  近 30 天 ≈ US${d30_cost:.2f}"
        )

        # Secondary weekly / monthly / rate-limit footer
        self.secondary_reset_lbl.setText(format_reset_detail(secondary_win, now))
        self.secondary_pct_lbl.setText(f"{int(round(secondary_win.percent))}% 剩餘")
        self.secondary_bar.set_data(secondary_win.percent, accent_color=accent)


class TicketDashboardPanel(QWidget):
    """
    Container for Retro Ticket mode inside the floating drawer.
    Provides a compact paper-tab selector ([01 GEMINI] [02 CLAUDE] [03 COPILOT] [04 CODEX] [ALL])
    and displays either the active CLI ticket card or all enabled ticket cards in a clean scroll area.
    """

    cli_selected = Signal(str)
    show_all_toggled = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.show_all: bool = False
        self.cards: Dict[str, RetroTicketCard] = {}
        self.tab_buttons: Dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Compact Ticket Index Tabs
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.setSpacing(4)

        for cli_id in ALL_CLIS:
            prof = TICKET_CLI_PROFILES[cli_id]
            btn = QPushButton(f"{prof['index']} {prof['hero_title']}", self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, c=cli_id: self._on_tab_clicked(c))
            self.tab_buttons[cli_id] = btn
            tab_bar.addWidget(btn)

        self.btn_all = QPushButton("ALL", self)
        self.btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_all.setFixedHeight(22)
        self.btn_all.setFixedWidth(36)
        self.btn_all.clicked.connect(self._on_all_clicked)
        tab_bar.addWidget(self.btn_all)
        lay.addLayout(tab_bar)

        # Scrollable Ticket Stack (handles ALL mode cleanly without overflowing screen)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #8A8375; border-radius: 3px; min-height: 24px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        self.cards_host = QWidget(self.scroll_area)
        self.cards_host.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)

        for cli_id in ALL_CLIS:
            card = RetroTicketCard(cli_id, parent=self.cards_host)
            card.card_clicked.connect(self._on_card_clicked)
            self.cards[cli_id] = card
            self.cards_layout.addWidget(card)

        self.scroll_area.setWidget(self.cards_host)
        lay.addWidget(self.scroll_area)

    def _on_tab_clicked(self, cli_id: str) -> None:
        self.show_all = False
        self.show_all_toggled.emit(False)
        self.cli_selected.emit(cli_id)

    def _on_card_clicked(self, cli_id: str) -> None:
        self.cli_selected.emit(cli_id)

    def _on_all_clicked(self) -> None:
        self.show_all = not self.show_all
        self.show_all_toggled.emit(self.show_all)

    def set_show_all(self, show_all: bool) -> None:
        self.show_all = bool(show_all)

    def _style_tabs(self, active_cli: str, enabled_clis: List[str]) -> None:
        for cli_id, btn in self.tab_buttons.items():
            btn.setVisible(cli_id in enabled_clis)
            prof = TICKET_CLI_PROFILES[cli_id]
            selected = (not self.show_all) and (cli_id == active_cli)
            if selected:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {prof['accent']}; color: #FFFFFF; "
                    f"border: 1.5px solid {INK_DARK}; border-radius: 2px; padding: 1px 6px; "
                    f"font-family: 'Consolas', 'Microsoft JhengHei UI', sans-serif; "
                    f"font-size: 9.5px; font-weight: 800; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {PAPER_BG}; color: {INK_DARK}; "
                    f"border: 1px solid {BORDER_COLOR}; border-radius: 2px; padding: 1px 6px; "
                    f"font-family: 'Consolas', 'Microsoft JhengHei UI', sans-serif; "
                    f"font-size: 9.5px; font-weight: 700; }}"
                    f"QPushButton:hover {{ background-color: {PAPER_BG_ALT}; }}"
                )

        if self.show_all:
            self.btn_all.setStyleSheet(
                f"QPushButton {{ background-color: {INK_DARK}; color: {PAPER_BG}; "
                f"border: 1.5px solid {INK_DARK}; border-radius: 2px; "
                f"font-size: 9.5px; font-weight: 800; }}"
            )
        else:
            self.btn_all.setStyleSheet(
                f"QPushButton {{ background-color: {PAPER_BG}; color: {INK_DARK}; "
                f"border: 1px solid {BORDER_COLOR}; border-radius: 2px; "
                f"font-size: 9.5px; font-weight: 700; }}"
                f"QPushButton:hover {{ background-color: {PAPER_BG_ALT}; }}"
            )

    def update_panel(
        self,
        multi_cli: MultiCliQuotaState,
        stats: Optional[SessionTokenStats] = None,
        current_time: Optional[float] = None,
    ) -> None:
        """Update tab states, card visibility, and refresh card metrics."""
        now = current_time or time.time()
        enabled = multi_cli.enabled_clis or list(ALL_CLIS)
        active = multi_cli.active_cli if multi_cli.active_cli in enabled else enabled[0]

        self._style_tabs(active, enabled)

        summaries = (stats.cli_usage_summaries if stats and stats.cli_usage_summaries else {})

        visible_count = 0
        for cli_id, card in self.cards.items():
            should_show = (cli_id in enabled) if self.show_all else (cli_id == active)
            card.setVisible(should_show)
            if should_show:
                visible_count += 1
                summary = summaries.get(cli_id)
                if summary is None:
                    summary = get_usage_history_summary(cli_id=cli_id)
                is_gen = bool(stats and stats.is_generating)
                card.update_card(multi_cli, usage_summary=summary, current_time=now, is_generating=is_gen)

        # Size scroll area gracefully: single card fits completely without scrollbar, ALL scrolls cleanly
        if self.show_all and visible_count > 1:
            self.scroll_area.setMinimumHeight(420)
            self.scroll_area.setMaximumHeight(560)
        else:
            active_card = self.cards.get(active)
            card_h = active_card.sizeHint().height() if active_card else 348
            target_h = max(348, card_h + 4)
            self.scroll_area.setMinimumHeight(target_h)
            self.scroll_area.setMaximumHeight(target_h + 8)
