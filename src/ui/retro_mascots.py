"""
Articulated retro-chibi vector mascot renderer for AGY Token Monitor.
Draws each CLI mascot with independently animated limbs, tail, ears/wings,
blinking eyes, mouth expressions, and special actions:
  - walk (alternating stepping legs, swinging arms, horizontal stroll)
  - yawn (open round mouth, sleepy eyes, floating Zzz)
  - breathe_fire (dragon fire breath) / sip_tea (cat steam) / blow_bubbles (octo) / wag_bark (shiba)
  - happy_hop, stretch, sweat_shake, panic_hop
"""

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen

INK = QColor("#241F1A")


def _draw_eyes_and_mouth(
    painter: QPainter,
    cx: float,
    cy: float,
    eye_dx: float,
    eye_y: float,
    mouth_y: float,
    is_blink: bool,
    action: str,
    action_p: float,
    quota_pct: float,
) -> None:
    """Draw expressive eyes and mouth shared across all four mascots."""
    eye_pen = QPen(INK, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(eye_pen)

    if action == "yawn" and action_p > 0.15:
        # Sleepy curved eyes + wide open yawning mouth
        for side in (-1.0, 1.0):
            ex = cx + side * eye_dx
            painter.drawArc(QRectF(ex - 2.6, eye_y - 1.5, 5.2, 3.5), 0, 180 * 16)
        mouth_r = 2.0 + 2.2 * math.sin(action_p * math.pi)
        painter.setBrush(QColor("#C85A53"))
        painter.drawEllipse(QPointF(cx, mouth_y + 1.2), mouth_r * 0.85, mouth_r)
        return

    if quota_pct < 20.0:
        # > < worried eyes + wavy mouth
        for side in (-1.0, 1.0):
            ex = cx + side * eye_dx
            painter.drawLine(QPointF(ex - 2.0 * side, eye_y - 1.5), QPointF(ex + 1.5 * side, eye_y))
            painter.drawLine(QPointF(ex + 1.5 * side, eye_y), QPointF(ex - 2.0 * side, eye_y + 1.5))
        painter.drawArc(QRectF(cx - 3.5, mouth_y, 7.0, 4.0), 20 * 16, 140 * 16)
        return

    if is_blink:
        for side in (-1.0, 1.0):
            ex = cx + side * eye_dx
            painter.drawLine(QPointF(ex - 2.2, eye_y), QPointF(ex + 2.2, eye_y))
    elif action == "happy_hop" and action_p > 0.1:
        # ^ ^ happy eyes
        for side in (-1.0, 1.0):
            ex = cx + side * eye_dx
            painter.drawArc(QRectF(ex - 2.5, eye_y - 2.0, 5.0, 4.0), 15 * 16, 150 * 16)
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(INK)
        for side in (-1.0, 1.0):
            ex = cx + side * eye_dx
            painter.drawEllipse(QPointF(ex, eye_y), 2.1, 2.3)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(ex - 0.6, eye_y - 0.7), 0.75, 0.75)
            painter.setBrush(INK)

    # Mouth
    painter.setPen(eye_pen)
    if action == "breathe_fire" and action_p > 0.12:
        mouth_r = 2.4 + 1.8 * math.sin(action_p * math.pi)
        painter.setBrush(QColor("#D94A2B"))
        painter.drawEllipse(QPointF(cx, mouth_y + 1.0), mouth_r, mouth_r * 0.85)
    elif action in ("happy_hop", "wag_bark") and action_p > 0.12:
        painter.setBrush(QColor("#E36D63"))
        painter.drawChord(QRectF(cx - 3.5, mouth_y - 1.0, 7.0, 5.5), 180 * 16, 180 * 16)
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(cx - 3.0, mouth_y - 1.5, 6.0, 3.8), 200 * 16, 140 * 16)


def _draw_zzz(painter: QPainter, x: float, y: float, p: float) -> None:
    """Floating sleepy Zzz bubbles during yawn."""
    if p <= 0.15:
        return
    alpha = int(230 * math.sin(p * math.pi))
    c = QColor("#5C584F")
    c.setAlpha(max(0, min(255, alpha)))
    painter.setPen(c)
    f = QFont("Consolas", 8, QFont.Weight.Bold)
    painter.setFont(f)
    drift = (1.0 - p) * 10.0
    painter.drawText(QPointF(x, y - drift), "z")
    f2 = QFont("Consolas", 10, QFont.Weight.Bold)
    painter.setFont(f2)
    painter.drawText(QPointF(x + 6.0, y - 6.0 - drift * 1.2), "Z")


def draw_dragon(
    painter: QPainter,
    cx: float,
    cy: float,
    phase: float,
    action: str,
    action_p: float,
    quota_pct: float,
    is_blink: bool,
    walk_dir: float,
) -> None:
    """Articulated Cute Green Dragon (可愛龍) with wings, tail, legs, arms, and fire breath."""
    outline = QPen(INK, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    body_green = QColor("#6BC46D")
    belly_cream = QColor("#F5E2A8")
    horn_gold = QColor("#F2B84B")
    wing_orange = QColor("#E78B48")

    # Compute limb kinematics
    if action == "walk":
        stride = math.sin(action_p * math.pi * 6.0)
        leg_l = stride * 4.5
        leg_r = -stride * 4.5
        arm_l = -stride * 25.0
        arm_r = stride * 25.0
        tail_ang = math.sin(action_p * math.pi * 6.0) * 18.0
        wing_flap = math.sin(action_p * math.pi * 6.0) * 12.0
    elif action == "happy_hop":
        leg_l = -2.0
        leg_r = -2.0
        arm_l = -55.0 + math.sin(action_p * math.pi * 4.0) * 18.0
        arm_r = -55.0 - math.sin(action_p * math.pi * 4.0) * 18.0
        tail_ang = math.sin(action_p * math.pi * 4.0) * 22.0
        wing_flap = math.sin(action_p * math.pi * 6.0) * 25.0
    else:
        leg_l = 0.0
        leg_r = 0.0
        arm_l = math.sin(phase) * 8.0 - 10.0
        arm_r = -math.sin(phase) * 8.0 + 10.0
        tail_ang = math.sin(phase * 1.2) * 12.0
        wing_flap = math.sin(phase * 1.8) * 10.0

    # 1. Swinging Tail (behind body)
    painter.save()
    painter.translate(cx + 10.0 * walk_dir, cy + 12.0)
    painter.rotate(tail_ang)
    tail_path = QPainterPath()
    tail_path.moveTo(0, 0)
    tail_path.quadTo(12.0 * walk_dir, -2.0, 15.0 * walk_dir, -9.0)
    tail_path.quadTo(10.0 * walk_dir, 4.0, 0, 5.0)
    tail_path.closeSubpath()
    painter.setPen(outline)
    painter.setBrush(body_green)
    painter.drawPath(tail_path)
    painter.restore()

    # 2. Flapping Little Wings
    for side in (-1.0, 1.0):
        painter.save()
        painter.translate(cx + side * 11.0, cy + 2.0)
        painter.rotate(side * (15.0 + wing_flap))
        wing = QPainterPath()
        wing.moveTo(0, 0)
        wing.lineTo(side * 9.0, -7.0)
        wing.lineTo(side * 7.0, 3.0)
        wing.closeSubpath()
        painter.setPen(outline)
        painter.setBrush(wing_orange)
        painter.drawPath(wing)
        painter.restore()

    # 3. Walking Legs
    painter.setPen(outline)
    painter.setBrush(body_green)
    painter.drawRoundedRect(QRectF(cx - 9.5, cy + 13.0 + leg_l * 0.4, 6.5, 7.5), 3.0, 3.0)
    painter.drawRoundedRect(QRectF(cx + 3.0, cy + 13.0 + leg_r * 0.4, 6.5, 7.5), 3.0, 3.0)

    # 4. Chibi Body + Belly Stripes
    painter.drawRoundedRect(QRectF(cx - 12.0, cy - 2.0, 24.0, 18.0), 10.0, 9.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(belly_cream)
    painter.drawRoundedRect(QRectF(cx - 7.5, cy + 1.5, 15.0, 13.0), 6.0, 6.0)
    painter.setPen(QPen(QColor("#C8A85A"), 1.0))
    painter.drawLine(QPointF(cx - 5.5, cy + 6.0), QPointF(cx + 5.5, cy + 6.0))
    painter.drawLine(QPointF(cx - 5.5, cy + 10.0), QPointF(cx + 5.5, cy + 10.0))

    # 5. Articulated Arms
    painter.setPen(outline)
    painter.setBrush(body_green)
    for side, ang in ((-1.0, arm_l), (1.0, arm_r)):
        painter.save()
        painter.translate(cx + side * 11.0, cy + 3.0)
        painter.rotate(ang)
        painter.drawRoundedRect(QRectF(side * 1.0 - (5.0 if side < 0 else 0.0), -2.5, 6.0, 9.0), 3.0, 3.0)
        painter.restore()

    # 6. Head + Horns + Cheek Spikes
    painter.setPen(outline)
    painter.setBrush(horn_gold)
    for side in (-1.0, 1.0):
        horn = QPainterPath()
        horn.moveTo(cx + side * 6.0, cy - 15.0)
        horn.lineTo(cx + side * 9.5, cy - 22.0)
        horn.lineTo(cx + side * 11.0, cy - 13.5)
        horn.closeSubpath()
        painter.drawPath(horn)

    painter.setBrush(body_green)
    painter.drawRoundedRect(QRectF(cx - 14.0, cy - 17.5, 28.0, 20.0), 9.5, 9.5)

    # Rosy cheeks
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(242, 130, 120, 140))
    painter.drawEllipse(QPointF(cx - 9.0, cy - 4.5), 2.5, 1.6)
    painter.drawEllipse(QPointF(cx + 9.0, cy - 4.5), 2.5, 1.6)

    _draw_eyes_and_mouth(painter, cx, cy, 6.0, cy - 8.5, cy - 4.2, is_blink, action, action_p, quota_pct)

    # 7. Special Action Overlays: Fire Breath or Yawn Zzz
    if action == "breathe_fire" and action_p > 0.1:
        f_env = math.sin(action_p * math.pi)
        fx = cx + 10.0
        fy = cy - 3.5
        flicker = math.sin(action_p * math.pi * 10.0) * 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(235, 82, 38, int(230 * f_env)))
        painter.drawEllipse(QPointF(fx + 5.0 * f_env, fy + flicker * 0.4), 7.5 * f_env, 4.8 * f_env)
        painter.setBrush(QColor(249, 178, 51, int(240 * f_env)))
        painter.drawEllipse(QPointF(fx + 3.0 * f_env, fy - flicker * 0.3), 4.8 * f_env, 3.0 * f_env)
        painter.setBrush(QColor(255, 240, 140, int(240 * f_env)))
        painter.drawEllipse(QPointF(fx + 10.5 * f_env, fy - 2.0 + flicker), 2.0 * f_env, 2.0 * f_env)
    elif action == "yawn":
        _draw_zzz(painter, cx + 13.0, cy - 14.0, action_p)


def draw_cat(
    painter: QPainter,
    cx: float,
    cy: float,
    phase: float,
    action: str,
    action_p: float,
    quota_pct: float,
    is_blink: bool,
    walk_dir: float,
) -> None:
    """Articulated Warm Terracotta Cat (暖橘貓) with twitching ears, tail, paws, and steaming teacup."""
    outline = QPen(INK, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    fur = QColor("#E48448")
    belly = QColor("#FBE8CC")
    ear_inner = QColor("#F0A899")

    if action == "walk":
        stride = math.sin(action_p * math.pi * 6.0)
        leg_l, leg_r = stride * 4.0, -stride * 4.0
        arm_l, arm_r = -stride * 22.0, stride * 22.0
        tail_ang = math.sin(action_p * math.pi * 6.0) * 20.0
    elif action == "happy_hop":
        leg_l, leg_r = -2.0, -2.0
        arm_l = -50.0 + math.sin(action_p * math.pi * 4.0) * 16.0
        arm_r = -50.0 - math.sin(action_p * math.pi * 4.0) * 16.0
        tail_ang = math.sin(action_p * math.pi * 4.0) * 24.0
    else:
        leg_l, leg_r = 0.0, 0.0
        arm_l = math.sin(phase) * 7.0 - 8.0
        arm_r = -math.sin(phase) * 7.0 + 8.0
        tail_ang = math.sin(phase * 1.4) * 14.0

    # Curled waving tail
    painter.save()
    painter.translate(cx + 11.0 * walk_dir, cy + 12.0)
    painter.rotate(tail_ang)
    painter.setPen(QPen(INK, 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(0, -12, 13 * walk_dir, 14), 0, 150 * 16)
    painter.setPen(QPen(fur, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(0, -12, 13 * walk_dir, 14), 0, 150 * 16)
    painter.restore()

    # Legs
    painter.setPen(outline)
    painter.setBrush(fur)
    painter.drawRoundedRect(QRectF(cx - 9.0, cy + 13.0 + leg_l * 0.4, 6.0, 7.0), 3.0, 3.0)
    painter.drawRoundedRect(QRectF(cx + 3.0, cy + 13.0 + leg_r * 0.4, 6.0, 7.0), 3.0, 3.0)

    # Body
    painter.drawRoundedRect(QRectF(cx - 11.5, cy - 2.0, 23.0, 17.5), 9.5, 9.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(belly)
    painter.drawEllipse(QPointF(cx, cy + 7.5), 7.0, 6.0)

    # Paws
    painter.setPen(outline)
    painter.setBrush(fur)
    for side, ang in ((-1.0, arm_l), (1.0, arm_r)):
        painter.save()
        painter.translate(cx + side * 10.5, cy + 3.5)
        painter.rotate(ang)
        painter.drawRoundedRect(QRectF(side * 1.0 - (5.0 if side < 0 else 0.0), -2.0, 5.5, 8.5), 2.8, 2.8)
        painter.restore()

    # Cat Ears (subtle twitch)
    ear_twitch = math.sin(phase * 3.0) * 1.2 if action != "yawn" else 0.0
    for side in (-1.0, 1.0):
        ear = QPainterPath()
        ear.moveTo(cx + side * 5.0, cy - 15.0)
        ear.lineTo(cx + side * 12.0, cy - 23.0 + (ear_twitch if side > 0 else 0.0))
        ear.lineTo(cx + side * 13.5, cy - 11.5)
        ear.closeSubpath()
        painter.setPen(outline)
        painter.setBrush(fur)
        painter.drawPath(ear)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ear_inner)
        painter.drawEllipse(QPointF(cx + side * 10.0, cy - 16.5), 1.8, 2.4)

    # Head + Whiskers
    painter.setPen(outline)
    painter.setBrush(fur)
    painter.drawRoundedRect(QRectF(cx - 14.0, cy - 17.5, 28.0, 19.5), 9.5, 9.5)

    painter.setPen(QPen(INK, 1.0))
    for side in (-1.0, 1.0):
        painter.drawLine(QPointF(cx + side * 11.0, cy - 6.0), QPointF(cx + side * 17.0, cy - 7.5))
        painter.drawLine(QPointF(cx + side * 11.0, cy - 4.0), QPointF(cx + side * 17.0, cy - 3.5))

    _draw_eyes_and_mouth(painter, cx, cy, 5.8, cy - 8.2, cy - 4.2, is_blink, action, action_p, quota_pct)

    # Teacup + Steam during sip_tea
    if action == "sip_tea" and action_p > 0.1:
        env = math.sin(action_p * math.pi)
        painter.setPen(outline)
        painter.setBrush(QColor("#5C9EAD"))
        painter.drawRoundedRect(QRectF(cx - 5.0, cy + 2.0, 10.0, 7.5), 2.5, 2.5)
        steam_pen = QPen(QColor(255, 255, 255, int(210 * env)), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(steam_pen)
        s_off = math.sin(action_p * math.pi * 4.0) * 1.5
        painter.drawLine(QPointF(cx - 2.0, cy), QPointF(cx - 2.0 + s_off, cy - 6.0 * env))
        painter.drawLine(QPointF(cx + 2.0, cy), QPointF(cx + 2.0 - s_off, cy - 7.0 * env))
    elif action == "yawn":
        _draw_zzz(painter, cx + 13.0, cy - 14.0, action_p)


def draw_octopus(
    painter: QPainter,
    cx: float,
    cy: float,
    phase: float,
    action: str,
    action_p: float,
    quota_pct: float,
    is_blink: bool,
    walk_dir: float,
) -> None:
    """Articulated Slate-Blue Octopus (海藍章魚) with 6 waving tentacles and aviator goggles."""
    outline = QPen(INK, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    skin = QColor("#5B82A6")
    goggle_brass = QColor("#D99B38")
    goggle_glass = QColor("#B7E4F9")

    # 6 Independently Waving Tentacles
    tent_speed = 6.0 if action == "walk" else 2.0
    tent_amp = 4.5 if action in ("walk", "happy_hop") else 2.2
    for i, tx in enumerate((-11.0, -6.5, -2.0, 2.5, 7.0, 11.5)):
        wave = math.sin(phase * tent_speed + i * 1.1) * tent_amp
        lift = -3.0 if (action == "walk" and (i % 2 == 0) == (math.sin(action_p * math.pi * 6.0) > 0)) else 0.0
        painter.setPen(QPen(INK, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(cx + tx, cy + 8.0), QPointF(cx + tx + wave * 0.6, cy + 17.5 + lift))
        painter.setPen(QPen(skin, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(cx + tx, cy + 8.0), QPointF(cx + tx + wave * 0.6, cy + 17.5 + lift))

    # Round Octopus Head
    painter.setPen(outline)
    painter.setBrush(skin)
    painter.drawEllipse(QPointF(cx, cy - 3.0), 15.0, 13.5)

    # Aviator Goggles on forehead
    painter.setBrush(goggle_brass)
    painter.drawRoundedRect(QRectF(cx - 12.0, cy - 15.5, 10.5, 7.0), 3.0, 3.0)
    painter.drawRoundedRect(QRectF(cx + 1.5, cy - 15.5, 10.5, 7.0), 3.0, 3.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(goggle_glass)
    painter.drawRoundedRect(QRectF(cx - 10.2, cy - 14.0, 7.0, 4.0), 1.8, 1.8)
    painter.drawRoundedRect(QRectF(cx + 3.2, cy - 14.0, 7.0, 4.0), 1.8, 1.8)

    _draw_eyes_and_mouth(painter, cx, cy, 5.5, cy - 3.5, cy + 1.0, is_blink, action, action_p, quota_pct)

    if action == "blow_bubbles" and action_p > 0.1:
        env = math.sin(action_p * math.pi)
        painter.setPen(QPen(QColor("#3B82F6"), 1.2))
        painter.setBrush(QColor(186, 230, 253, int(190 * env)))
        painter.drawEllipse(QPointF(cx + 12.0, cy - 2.0 - (1.0 - action_p) * 10.0), 3.0, 3.0)
        painter.drawEllipse(QPointF(cx + 16.5, cy - 8.0 - (1.0 - action_p) * 14.0), 2.0, 2.0)
    elif action == "yawn":
        _draw_zzz(painter, cx + 13.0, cy - 12.0, action_p)


def draw_shiba(
    painter: QPainter,
    cx: float,
    cy: float,
    phase: float,
    action: str,
    action_p: float,
    quota_pct: float,
    is_blink: bool,
    walk_dir: float,
) -> None:
    """Articulated Teal-Cream Shiba Inu (翠綠柴犬) with wagging tail, scarf, and stepping paws."""
    outline = QPen(INK, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    coat = QColor("#67A99A")
    cream = QColor("#F5ECD7")
    scarf = QColor("#256B3A")

    if action == "walk":
        stride = math.sin(action_p * math.pi * 6.0)
        leg_l, leg_r = stride * 4.2, -stride * 4.2
        arm_l, arm_r = -stride * 22.0, stride * 22.0
        tail_wag = math.sin(action_p * math.pi * 8.0) * 24.0
    elif action in ("happy_hop", "wag_bark"):
        leg_l, leg_r = -2.0, -2.0
        arm_l, arm_r = -45.0, -45.0
        tail_wag = math.sin(action_p * math.pi * 10.0) * 30.0
    else:
        leg_l, leg_r = 0.0, 0.0
        arm_l = math.sin(phase) * 7.0 - 8.0
        arm_r = -math.sin(phase) * 7.0 + 8.0
        tail_wag = math.sin(phase * 2.4) * 14.0

    # Wagging Curled Shiba Tail
    painter.save()
    painter.translate(cx + 10.0 * walk_dir, cy + 10.0)
    painter.rotate(tail_wag)
    painter.setPen(outline)
    painter.setBrush(coat)
    painter.drawEllipse(QPointF(5.5 * walk_dir, -4.0), 5.5, 5.5)
    painter.restore()

    # Legs
    painter.setPen(outline)
    painter.setBrush(cream)
    painter.drawRoundedRect(QRectF(cx - 9.0, cy + 13.0 + leg_l * 0.4, 6.0, 7.0), 3.0, 3.0)
    painter.drawRoundedRect(QRectF(cx + 3.0, cy + 13.0 + leg_r * 0.4, 6.0, 7.0), 3.0, 3.0)

    # Body
    painter.setBrush(coat)
    painter.drawRoundedRect(QRectF(cx - 11.0, cy - 1.5, 22.0, 17.0), 9.0, 8.5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(cream)
    painter.drawEllipse(QPointF(cx, cy + 7.5), 6.5, 5.5)

    # Paws
    painter.setPen(outline)
    painter.setBrush(cream)
    for side, ang in ((-1.0, arm_l), (1.0, arm_r)):
        painter.save()
        painter.translate(cx + side * 10.0, cy + 3.5)
        painter.rotate(ang)
        painter.drawRoundedRect(QRectF(side * 1.0 - (4.5 if side < 0 else 0.0), -2.0, 5.0, 8.0), 2.5, 2.5)
        painter.restore()

    # Green Scarf
    painter.setPen(outline)
    painter.setBrush(scarf)
    painter.drawRoundedRect(QRectF(cx - 10.5, cy - 1.5, 21.0, 4.5), 2.0, 2.0)

    # Pointed Shiba Ears
    for side in (-1.0, 1.0):
        ear = QPainterPath()
        ear.moveTo(cx + side * 5.0, cy - 15.0)
        ear.lineTo(cx + side * 11.5, cy - 23.0)
        ear.lineTo(cx + side * 13.0, cy - 11.5)
        ear.closeSubpath()
        painter.setPen(outline)
        painter.setBrush(coat)
        painter.drawPath(ear)

    # Head + Cream Cheek Mask
    painter.setBrush(coat)
    painter.drawRoundedRect(QRectF(cx - 13.5, cy - 17.5, 27.0, 18.5), 9.0, 9.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(cream)
    painter.drawRoundedRect(QRectF(cx - 10.0, cy - 8.5, 20.0, 8.5), 4.5, 4.5)

    _draw_eyes_and_mouth(painter, cx, cy, 5.5, cy - 9.0, cy - 4.5, is_blink, action, action_p, quota_pct)

    # Cute nose
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(INK)
    painter.drawEllipse(QPointF(cx, cy - 6.0), 1.6, 1.2)

    if action == "yawn":
        _draw_zzz(painter, cx + 13.0, cy - 14.0, action_p)


def draw_mascot_frame(
    painter: QPainter,
    mascot_key: str,
    w: float,
    h: float,
    phase: float,
    action: str,
    action_p: float,
    quota_pct: float,
    is_generating: bool,
    jump_boost: float,
    is_blink: bool,
) -> None:
    """Render an articulated mascot frame with natural body motion, limbs, and effects."""
    cx = w / 2.0
    cy = h / 2.0 + 3.0

    dx = 0.0
    bob_y = 0.0
    tilt_deg = 0.0
    walk_dir = 1.0

    if action == "walk":
        # Smooth stroll left-right-center
        stroll = math.sin(action_p * math.pi * 2.0)
        dx = stroll * 8.0
        walk_dir = 1.0 if math.cos(action_p * math.pi * 2.0) >= 0 else -1.0
        bob_y = -abs(math.sin(action_p * math.pi * 6.0)) * 2.5
        tilt_deg = stroll * 3.0
    elif action == "happy_hop":
        bob_y = -abs(math.sin(action_p * math.pi * 2.0)) * 7.5
        tilt_deg = math.sin(action_p * math.pi * 2.0) * 6.0
    elif action == "stretch":
        bob_y = -math.sin(action_p * math.pi) * 3.0
    elif action == "sweat_shake":
        dx = math.sin(action_p * math.pi * 8.0) * 2.2
        tilt_deg = math.sin(action_p * math.pi * 6.0) * 3.5
    elif action == "panic_hop":
        bob_y = -abs(math.sin(action_p * math.pi * 3.0)) * 5.5
        dx = math.sin(action_p * math.pi * 10.0) * 2.0
    elif is_generating:
        bob_y = -abs(math.sin(phase * 1.6)) * 3.5
        tilt_deg = math.sin(phase * 1.6) * 3.5
    elif quota_pct < 20.0:
        dx = math.sin(phase * 6.0) * 1.2
        tilt_deg = math.sin(phase * 5.0) * 2.5
    else:
        bob_y = math.sin(phase) * 1.6
        tilt_deg = math.sin(phase * 0.5) * 1.4

    if jump_boost > 0.0:
        arc = math.sin(jump_boost * math.pi)
        bob_y -= arc * 6.0
        tilt_deg += arc * 5.0

    # Ground shadow
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(28, 27, 24, 32))
    shadow_w = max(8.0, 14.0 + bob_y * 0.5)
    painter.drawEllipse(QPointF(cx + dx, cy + 21.0), shadow_w, 3.0)

    # Sparkles or sweat drop
    if quota_pct < 40.0:
        drop_color = QColor("#B63A2B" if quota_pct < 20.0 else "#D97706")
        drop_y = 10.0 + (1.0 - (phase % math.pi) / math.pi) * 5.0
        painter.setBrush(drop_color)
        painter.drawEllipse(QPointF(w - 9.0, drop_y), 2.0, 3.0)
    else:
        sparkle_color = QColor("#D49B27" if quota_pct >= 80.0 else "#B89B5E")
        for sx, sy, offset in ((9.0, 13.0, 0.0), (w - 9.0, 12.0, 2.1), (w - 8.0, h - 13.0, 4.2)):
            alpha = int(105 + 140 * (0.5 + 0.5 * math.sin(phase * 1.6 + offset)))
            size = 1.8 + 1.4 * (0.5 + 0.5 * math.sin(phase * 1.6 + offset))
            c = QColor(sparkle_color)
            c.setAlpha(alpha)
            painter.setPen(QPen(c, 1.3))
            painter.drawLine(QPointF(sx - size, sy), QPointF(sx + size, sy))
            painter.drawLine(QPointF(sx, sy - size), QPointF(sx, sy + size))

    painter.save()
    painter.translate(cx + dx, cy + bob_y)
    painter.rotate(tilt_deg)

    if "dragon" in mascot_key:
        draw_dragon(painter, 0.0, 0.0, phase, action, action_p, quota_pct, is_blink, walk_dir)
    elif "cat" in mascot_key:
        draw_cat(painter, 0.0, 0.0, phase, action, action_p, quota_pct, is_blink, walk_dir)
    elif "octo" in mascot_key:
        draw_octopus(painter, 0.0, 0.0, phase, action, action_p, quota_pct, is_blink, walk_dir)
    else:
        draw_shiba(painter, 0.0, 0.0, phase, action, action_p, quota_pct, is_blink, walk_dir)

    painter.restore()
