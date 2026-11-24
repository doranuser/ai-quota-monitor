"""
Swiss Precision Dark Titanium floating HUD for AGY Token Monitor (Refined Apple Dynamic Island / Teenage Engineering style).
Supports Multi-CLI Quota Monitoring (Antigravity AGY, GitHub Copilot, Claude Code CLI, OpenAI Codex) and Selective CLI Display.
Features Obsidian Titanium material, 1px hairline borders, micro-vector gauges, live countdowns, and flyout drawer.
Pure Typographic & Geometric Design (Zero Emoji).
"""

import logging
import math
from pathlib import Path
import time
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QCursor,
    QFont,
    QIcon,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    APP_ICON_ICO,
    APP_ICON_PNG,
    load_settings,
    save_settings,
    reset_today_usage,
    load_multi_cli_state,
    save_multi_cli_state,
)
from ..monitor.multi_cli_parser import (
    ALL_CLIS,
    CLI_AGY,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_COMBINED,
    CLI_COPILOT,
    CLI_DISPLAY_NAMES,
    CLI_SHORT_NAMES,
    CLI_THEME_COLORS,
    GROUP_CLAUDE_GPT,
    GROUP_DISPLAY_NAMES,
    GROUP_GEMINI,
    GROUP_SHORT_NAMES,
    AgyQuotaState,
    ClaudeCodeQuotaState,
    CodexQuotaState,
    CopilotQuotaState,
    DualQuotaState,
    ModelGroupQuota,
    MultiCliParser,
    MultiCliQuotaState,
    QuotaWindow,
    UsageParser,
    create_default_multi_cli_state,
    create_default_dual_quota_state,
)
from ..monitor.token_parser import SessionTokenStats, TokenParser
from .style import DIALOG_STYLESHEET, MAIN_STYLESHEET, MENU_STYLESHEET
from .ticket_card import TicketDashboardPanel
from .widgets import (
    ChevronButton,
    CircularProgressRing,
    ContextProgressWidget,
    GeometricDot,
    GlowingPulseDot,
    GradientDivider,
    MinimalProgressBar,
    MiniSparkline,
    ModelPillBadge,
    PulsingDot,
)

logger = logging.getLogger(__name__)


class UsageSyncDialog(QDialog):
    """
    Swiss Precision Dark modal dialog for synchronizing Multi-CLI quota text (AGY, Copilot, Claude Code, Codex).
    Pure typography, zero emoji.
    """

    SAMPLE_TEXTS = {
        CLI_AGY: (
            "GEMINI MODELS\n"
            "Five Hour Limit Remaining: 60.09% (Resets in 3h 10m)\n"
            "Weekly Limit Remaining: 93.25% (Resets in 111h 25m)\n\n"
            "CLAUDE AND GPT MODELS\n"
            "Five Hour Limit Remaining: 100.00%\n"
            "Weekly Limit Remaining: 100.00%"
        ),
        CLI_COPILOT: (
            "GITHUB COPILOT\n"
            "Premium Requests Remaining: 85.00% (255/300, Resets in 14d 6h)\n"
            "Rolling Rate Limit: 92.00% (Resets in 45m)"
        ),
        CLI_CLAUDE_CODE: (
            "CLAUDE CODE CLI\n"
            "5-Hour Window Remaining: 78.50% (Resets in 2h 40m)\n"
            "Monthly Budget Remaining: 91.20% ($91.20 / $100.00)"
        ),
        CLI_CODEX: (
            "OPENAI CODEX\n"
            "5-Hour Window Remaining: 99.00% (Resets in 4h 12m)\n"
            "7-Day Window Remaining: 75.00% (Resets in 5d 8h)\n"
            "Plan: plus\n"
            "Total Tokens: 125,400"
        ),
    }

    def __init__(self, current_multi_state: Optional[MultiCliQuotaState] = None, default_target: str = CLI_AGY, parent=None):
        super().__init__(parent)
        self.setWindowTitle("同步 CLI 配額與使用量 (Multi-CLI Sync)")
        self.setFixedWidth(470)
        self.setStyleSheet(DIALOG_STYLESHEET)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        if APP_ICON_ICO.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_ICO)))

        self.multi_state = current_multi_state or load_multi_cli_state()
        self.target_cli = default_target
        self.synced_multi_state: Optional[MultiCliQuotaState] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("<b>同步 CLI 配額與使用量</b>", self)
        title_lbl.setStyleSheet("font-size: 14px; color: #00e599; font-weight: 700; letter-spacing: 0.3px;")
        layout.addWidget(title_lbl)

        # CLI Target Selector Buttons
        sel_layout = QHBoxLayout()
        sel_layout.setSpacing(6)
        self.tab_btns = {}

        for cli_id in ALL_CLIS:
            btn = QPushButton(CLI_SHORT_NAMES.get(cli_id, cli_id.upper()), self)
            btn.setProperty("class", "CliTabBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cli_id: self._select_tab(c))
            self.tab_btns[cli_id] = btn
            sel_layout.addWidget(btn)

        layout.addLayout(sel_layout)

        self.desc_lbl = QLabel("", self)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: #8a909e; font-size: 11px;")
        layout.addWidget(self.desc_lbl)

        # Text input area
        self.text_edit = QTextEdit(self)
        self.text_edit.setMinimumHeight(140)
        layout.addWidget(self.text_edit)

        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)

        btn_sample = QPushButton("載入範例", self)
        btn_sample.clicked.connect(self._load_sample)
        btn_sample.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_clear = QPushButton("清空", self)
        btn_clear.clicked.connect(self.text_edit.clear)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)

        preset_layout.addWidget(btn_sample)
        preset_layout.addWidget(btn_clear)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        cancel_btn = QPushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)

        sync_btn = QPushButton("立即解析同步", self)
        sync_btn.setObjectName("PrimaryBtn")
        sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_btn.clicked.connect(self._parse_and_accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(sync_btn)
        layout.addLayout(btn_layout)

        self._select_tab(self.target_cli)

    def _select_tab(self, cli_id: str) -> None:
        self.target_cli = cli_id
        for cid, btn in self.tab_btns.items():
            is_active = (cid == cli_id)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if cli_id == CLI_AGY:
            self.desc_lbl.setText("備援模式：自動同步不可用時，才需要貼上 Antigravity <b>/usage</b> 輸出文字。")
            prev_text = self.multi_state.agy.raw_usage_text or self.SAMPLE_TEXTS[CLI_AGY]
        elif cli_id == CLI_COPILOT:
            self.desc_lbl.setText("備援模式：目前 Copilot 沒有內建自動配額來源時，可貼上 Fast Requests / Rate Limits 狀態。")
            prev_text = self.multi_state.copilot.raw_text or self.SAMPLE_TEXTS[CLI_COPILOT]
        elif cli_id == CLI_CLAUDE_CODE:
            self.desc_lbl.setText("備援模式：目前 Claude Code 沒有內建配額來源時，可貼上 5 小時窗口與月度預算狀態。")
            prev_text = self.multi_state.claude.raw_text or self.SAMPLE_TEXTS[CLI_CLAUDE_CODE]
        else:
            self.desc_lbl.setText("Codex 會自動讀取本機 ~/.codex/sessions/*.jsonl；若需要，也可貼上 5 小時與 7 天窗口狀態。")
            raw_codex = self.multi_state.codex.raw_text
            prev_text = raw_codex if raw_codex and not raw_codex.startswith("AUTO:") else self.SAMPLE_TEXTS[CLI_CODEX]

        self.text_edit.setPlainText(prev_text)

    def _load_sample(self) -> None:
        sample = self.SAMPLE_TEXTS.get(self.target_cli, "")
        self.text_edit.setPlainText(sample)

    def _parse_and_accept(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "輸入為空", "請先貼上配額文字。")
            return

        try:
            self.synced_multi_state = MultiCliParser.parse(text, self.multi_state, target_cli=self.target_cli)
            save_multi_cli_state(self.synced_multi_state)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "解析失敗", f"無法解析文字: {e}")


class BudgetDialog(QDialog):
    """
    Swiss Precision Dark modal dialog for configuring daily token & USD budgets.
    Pure typography, zero emoji.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定每日預算")
        self.setFixedWidth(320)
        self.setStyleSheet(DIALOG_STYLESHEET)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        if APP_ICON_ICO.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_ICO)))

        settings = load_settings()
        current_tokens = settings.get("daily_budget_tokens", 5_000_000)
        current_usd = settings.get("daily_budget_usd", 2.00)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_lbl = QLabel("<b>每日使用預算設定</b>", self)
        title_lbl.setStyleSheet("font-size: 14px; color: #00e599; font-weight: 700; letter-spacing: 0.3px;")
        layout.addWidget(title_lbl)

        # Tokens budget
        tok_lbl = QLabel("每日 Token 上限 (預設 5,000,000):", self)
        self.tokens_edit = QLineEdit(str(current_tokens), self)
        self.tokens_edit.setPlaceholderText("例如: 5000000")
        layout.addWidget(tok_lbl)
        layout.addWidget(self.tokens_edit)

        # USD budget
        usd_lbl = QLabel("每日花費上限 (USD, 預設 2.00):", self)
        self.usd_edit = QLineEdit(f"{current_usd:.2f}", self)
        self.usd_edit.setPlaceholderText("例如: 2.00")
        layout.addWidget(usd_lbl)
        layout.addWidget(self.usd_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        cancel_btn = QPushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("儲存設定", self)
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save_and_accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save_and_accept(self) -> None:
        try:
            tok_val = int(self.tokens_edit.text().strip().replace(",", "").replace("_", ""))
            usd_val = float(self.usd_edit.text().strip().replace("$", ""))
            if tok_val <= 0 or usd_val <= 0:
                raise ValueError("Values must be positive")

            settings = load_settings()
            settings["daily_budget_tokens"] = tok_val
            settings["daily_budget_usd"] = usd_val
            save_settings(settings)
            self.accept()
        except Exception:
            QMessageBox.warning(self, "輸入錯誤", "請輸入有效的正整數 Tokens 與金額數字。")


class FloatingCapsuleWidget(QWidget):
    """
    Frameless Swiss Precision Dark Titanium HUD floating capsule widget.
    Multi-CLI Quota Monitoring (Antigravity AGY, GitHub Copilot, Claude Code CLI).
    Zero Emoji / Pure Typographic & Geometric Design.
    """
    request_rescan = Signal()
    request_exit = Signal()
    request_hide_to_tray = Signal()
    request_reset_daily = Signal()
    request_force_sync = Signal()   # Tells AdaptivePoller to sync immediately
    budget_changed = Signal()
    group_switched = Signal(str)
    cli_switched = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_position = QPoint()
        self.is_dragging = False
        self.mouse_pressed_pos = QPoint()
        self._press_in_capsule_bar = False
        self.current_stats: Optional[SessionTokenStats] = None

        # TPM rate history for sparkline
        self.tpm_history: List[float] = []
        self.peak_tpm: int = 0

        # Load persisted settings and Multi-CLI state
        self.settings = load_settings()
        self.multi_cli: MultiCliQuotaState = load_multi_cli_state()
        self.is_compact = bool(self.settings.get("is_compact", False))
        self.always_on_top = bool(self.settings.get("always_on_top", True))
        self.current_opacity = float(self.settings.get("opacity", 0.96))
        self.alerts_enabled = bool(self.settings.get("alerts_enabled", True))
        self.ui_theme = str(self.settings.get("ui_theme", "obsidian"))
        if self.ui_theme not in ("obsidian", "ticket"):
            self.ui_theme = "obsidian"
        self.ticket_show_all = bool(self.settings.get("ticket_show_all", False))
        self.is_drawer_expanded = False
        self._sync_request_id = 0
        self._sync_timeout_ms = 20_000

        # Setup window properties & icon
        self._init_window_flags()
        if APP_ICON_ICO.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_ICO)))
        elif APP_ICON_PNG.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PNG)))

        self.setStyleSheet(MAIN_STYLESHEET)

        # Setup UI
        self._init_ui()

        # Background live countdown timer (1 second interval)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._on_countdown_tick)
        self.countdown_timer.start()

        # Apply position & opacity
        self.setWindowOpacity(self.current_opacity)
        self._restore_position()

    @property
    def dual_quota(self) -> AgyQuotaState:
        """Backward compatibility dual_quota property."""
        return self.multi_cli.agy

    @dual_quota.setter
    def dual_quota(self, value: AgyQuotaState) -> None:
        self.multi_cli.agy = value

    def _init_window_flags(self) -> None:
        """Set frameless, transparent, and always-on-top window flags."""
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.NoDropShadowWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _init_ui(self) -> None:
        """Build Swiss precision HUD UI elements (Zero Emoji)."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(0)

        # =========================================================================
        # 1. ROOT CONTAINER (Obsidian Titanium HUD, 18px Radius)
        # =========================================================================
        self.root_frame = QFrame(self)
        self.root_frame.setObjectName("CapsuleRootContainer")

        shadow = QGraphicsDropShadowEffect(self.root_frame)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.root_frame.setGraphicsEffect(shadow)

        self.root_layout = QVBoxLayout(self.root_frame)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ----------------- A. MAIN CAPSULE BAR (HEADER, 36px Height) -----------------
        self.capsule_bar = QFrame(self.root_frame)
        self.capsule_bar.setObjectName("CapsuleBar")
        bar_layout = QHBoxLayout(self.capsule_bar)
        bar_layout.setContentsMargins(10, 0, 10, 0)
        bar_layout.setSpacing(7)

        # [1. STATUS DOT: 6px Precision Breathing Dot]
        self.pulsing_dot = GlowingPulseDot(size=6, parent=self.capsule_bar)
        self.pulsing_dot.setToolTip("即時狀態呼吸指示燈 | 拖曳移動視窗")
        bar_layout.addWidget(self.pulsing_dot)

        # [2. ACTIVE CLI & REMAINING VALUE]
        group_box = QVBoxLayout()
        group_box.setSpacing(0)
        group_box.setContentsMargins(0, 0, 0, 0)
        self.group_quota_label = QLabel("GEMINI: 60.1%", self.capsule_bar)
        self.group_quota_label.setObjectName("GroupQuotaLabel")
        self.group_quota_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_quota_label.setMinimumWidth(74)
        self.group_quota_label.mousePressEvent = lambda e: self._on_group_label_clicked()

        self.group_quota_sub = QLabel("5-HR ROLLING QUOTA", self.capsule_bar)
        self.group_quota_sub.setObjectName("GroupQuotaSub")
        self.group_quota_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_quota_sub.mousePressEvent = lambda e: self._on_group_label_clicked()

        group_box.addWidget(self.group_quota_label)
        group_box.addWidget(self.group_quota_sub)

        # Backward compatibility aliases
        self.remaining_tokens_label = self.group_quota_label
        self.remaining_tokens_sub = self.group_quota_sub
        self.total_tokens_label = self.group_quota_label
        self.total_tokens_sub = self.group_quota_sub

        bar_layout.addLayout(group_box)

        # Deduction Delta Chip
        self.deduction_badge = QLabel("0", self.capsule_bar)
        self.deduction_badge.setObjectName("DeductionBadge")
        self.deduction_badge.setToolTip("即時單輪 Token 扣減提示")
        self.deduction_badge.hide()
        self.delta_badge = self.deduction_badge
        bar_layout.addWidget(self.deduction_badge)

        # [3. VERTICAL HAIRLINE DIVIDER 1]
        self.div1 = GradientDivider(height=18, parent=self.capsule_bar)
        bar_layout.addWidget(self.div1)

        # [4. 28px CIRCULAR PROGRESS RING GAUGE]
        self.circular_ring = CircularProgressRing(size=28, ring_width=2.5, show_text=True, parent=self.capsule_bar)
        self.circular_ring.setToolTip("當前 CLI 剩餘配額精準環形儀表")
        bar_layout.addWidget(self.circular_ring)

        # Hidden text labels for backward compatibility
        self.remaining_pct_label = QLabel("60.1%", self.capsule_bar)
        self.remaining_pct_label.setObjectName("RemainingPctLabel")
        self.remaining_pct_label.hide()
        self.remaining_sub_label = QLabel("剩餘", self.capsule_bar)
        self.remaining_sub_label.setObjectName("RemainingSubLabel")
        self.remaining_sub_label.hide()
        self.context_pct_label = self.remaining_pct_label
        self.context_sub_label = self.remaining_sub_label
        self.context_progress = ContextProgressWidget(width=28, height=4, parent=self.capsule_bar)
        self.context_progress.hide()

        # [5. VERTICAL HAIRLINE DIVIDER 2]
        self.div2 = GradientDivider(height=18, parent=self.capsule_bar)
        bar_layout.addWidget(self.div2)

        # [6. COUNTDOWN BADGE & TPM SPEED BADGE]
        self.countdown_badge = QLabel("3h 10m", self.capsule_bar)
        self.countdown_badge.setObjectName("CountdownBadge")
        self.countdown_badge.setToolTip("配額刷新/滾動倒數計時")

        self.tpm_badge = QLabel("0 tpm", self.capsule_bar)
        self.tpm_badge.setObjectName("TpmBadge")
        self.tpm_badge.setProperty("generating", "false")
        self.tpm_badge.setToolTip("即時消耗速率 (Tokens Per Minute)")

        self.cost_badge = QLabel("$2.00 剩餘", self.capsule_bar)
        self.cost_badge.setObjectName("RemainingCostBadge")
        self.cost_badge.hide()

        bar_layout.addWidget(self.countdown_badge)
        bar_layout.addWidget(self.tpm_badge)

        # [7. MULTI-CLI QUICK SWITCHER BUTTON & CHEVRON]
        self.group_switch_btn = QPushButton("AGY", self.capsule_bar)
        self.group_switch_btn.setObjectName("CliSwitchBtn")
        self.group_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_switch_btn.setToolTip("快速切換監控 CLI (AGY ⇄ COPILOT ⇄ CLAUDE ⇄ CODEX)")
        self.group_switch_btn.setAccessibleName("切換監控 CLI")
        self.group_switch_btn.setAccessibleDescription("切換至下一個已啟用的 CLI 配額視圖")
        self.group_switch_btn.clicked.connect(self.switch_next_cli)
        bar_layout.addWidget(self.group_switch_btn)
        self.cli_switch_btn = self.group_switch_btn

        self.model_pill = ModelPillBadge("GEMINI 2.5", parent=self.capsule_bar)
        self.model_pill.hide()

        self.expand_btn = ChevronButton(parent=self.capsule_bar)
        self.expand_btn.setToolTip("展開 / 摺疊 Multi-CLI Dashboard 抽屜")
        self.expand_btn.setAccessibleName("展開或摺疊監控儀表板")
        self.expand_btn.setAccessibleDescription("顯示或隱藏各 CLI 配額卡片與同步操作")
        self.expand_btn.clicked.connect(self.toggle_drawer)
        bar_layout.addWidget(self.expand_btn)

        self.root_layout.addWidget(self.capsule_bar)

        # ----------------- B. MINI-DASHBOARD FLYOUT DRAWER -----------------
        self.drawer_frame = QFrame(self.root_frame)
        self.drawer_frame.setObjectName("DrawerWidget")
        self.drawer_frame.setMaximumHeight(0)
        self.drawer_frame.hide()

        self.drawer_layout = QVBoxLayout(self.drawer_frame)
        self.drawer_layout.setContentsMargins(10, 8, 10, 10)
        self.drawer_layout.setSpacing(8)

        # 1. ANTIGRAVITY (AGY) CARD
        self.agy_card = QFrame(self.drawer_frame)
        self.agy_card.setObjectName("GeminiCard")
        agy_layout = QVBoxLayout(self.agy_card)
        agy_layout.setContentsMargins(8, 6, 8, 6)
        agy_layout.setSpacing(5)

        agy_header_box = QHBoxLayout()
        agy_title = QLabel("ANTIGRAVITY (AGY)", self.agy_card)
        agy_title.setObjectName("GeminiCardHeader")
        self.agy_badge = QLabel("ACTIVE", self.agy_card)
        self.agy_badge.setProperty("class", "ActiveGroupBadge")
        self.agy_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.agy_badge.mousePressEvent = lambda e: self.set_active_cli(CLI_AGY)
        agy_header_box.addWidget(agy_title)
        agy_header_box.addStretch()
        agy_header_box.addWidget(self.agy_badge)
        agy_layout.addLayout(agy_header_box)

        # Gemini 5h Row
        gem_5h_row = QHBoxLayout()
        gem_5h_title = QLabel("Gemini 5-Hour:", self.agy_card)
        gem_5h_title.setProperty("class", "DrawerRowTitle")
        self.gemini_sub_badge = QLabel("ACTIVE", self.agy_card)
        self.gemini_sub_badge.setProperty("class", "ActiveGroupBadge")
        self.gemini_sub_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gemini_sub_badge.mousePressEvent = lambda e: self.set_active_agy_group(GROUP_GEMINI)
        self.gemini_5h_val = QLabel("60.09%", self.agy_card)
        self.gemini_5h_val.setProperty("class", "DrawerRowVal")
        self.gemini_5h_time = QLabel("3h 10m", self.agy_card)
        self.gemini_5h_time.setProperty("class", "DrawerRowTime")
        gem_5h_row.addWidget(gem_5h_title)
        gem_5h_row.addWidget(self.gemini_sub_badge)
        gem_5h_row.addStretch()
        gem_5h_row.addWidget(self.gemini_5h_val)
        gem_5h_row.addWidget(self.gemini_5h_time)
        agy_layout.addLayout(gem_5h_row)

        self.gemini_5h_bar = QProgressBar(self.agy_card)
        self.gemini_5h_bar.setProperty("class", "DrawerBar")
        self.gemini_5h_bar.setRange(0, 1000)
        self.gemini_5h_bar.setValue(601)
        self.gemini_5h_bar.setTextVisible(False)
        agy_layout.addWidget(self.gemini_5h_bar)

        # Claude/GPT 5h Row
        claude_5h_row = QHBoxLayout()
        claude_5h_title = QLabel("Claude/GPT 5-Hour:", self.agy_card)
        claude_5h_title.setProperty("class", "DrawerRowTitle")
        self.claude_sub_badge = QLabel("SWITCH", self.agy_card)
        self.claude_sub_badge.setProperty("class", "InactiveGroupBadge")
        self.claude_sub_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.claude_sub_badge.mousePressEvent = lambda e: self.set_active_agy_group(GROUP_CLAUDE_GPT)
        self.claude_5h_val = QLabel("100.00%", self.agy_card)
        self.claude_5h_val.setProperty("class", "DrawerRowVal")
        self.claude_5h_time = QLabel("OPTIMAL", self.agy_card)
        self.claude_5h_time.setProperty("class", "DrawerRowTimeFull")
        claude_5h_row.addWidget(claude_5h_title)
        claude_5h_row.addWidget(self.claude_sub_badge)
        claude_5h_row.addStretch()
        claude_5h_row.addWidget(self.claude_5h_val)
        claude_5h_row.addWidget(self.claude_5h_time)
        agy_layout.addLayout(claude_5h_row)

        self.claude_5h_bar = QProgressBar(self.agy_card)
        self.claude_5h_bar.setProperty("class", "DrawerBar")
        self.claude_5h_bar.setProperty("group", "claude_gpt")
        self.claude_5h_bar.setRange(0, 1000)
        self.claude_5h_bar.setValue(1000)
        self.claude_5h_bar.setTextVisible(False)
        agy_layout.addWidget(self.claude_5h_bar)

        # Gemini weekly row for compatibility
        self.gemini_weekly_val = QLabel("93.25%", self.agy_card)
        self.gemini_weekly_time = QLabel("111h 25m", self.agy_card)
        self.gemini_weekly_bar = QProgressBar(self.agy_card)
        self.gemini_weekly_bar.hide()
        self.gemini_badge = self.agy_badge
        self.gemini_card = self.agy_card
        self.claude_card = self.agy_card
        self.claude_badge = self.agy_badge
        self.claude_weekly_val = QLabel("100.00%", self.agy_card)
        self.claude_weekly_time = QLabel("OPTIMAL", self.agy_card)
        self.claude_weekly_bar = QProgressBar(self.agy_card)
        self.claude_weekly_bar.hide()

        self.drawer_layout.addWidget(self.agy_card)

        # 2. GITHUB COPILOT CARD
        self.copilot_card = QFrame(self.drawer_frame)
        self.copilot_card.setObjectName("CopilotCard")
        cop_layout = QVBoxLayout(self.copilot_card)
        cop_layout.setContentsMargins(8, 6, 8, 6)
        cop_layout.setSpacing(5)

        cop_header_box = QHBoxLayout()
        cop_title = QLabel("GITHUB COPILOT", self.copilot_card)
        cop_title.setObjectName("CopilotCardHeader")
        self.copilot_badge = QLabel("SWITCH", self.copilot_card)
        self.copilot_badge.setProperty("class", "InactiveGroupBadge")
        self.copilot_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copilot_badge.mousePressEvent = lambda e: self.set_active_cli(CLI_COPILOT)
        cop_header_box.addWidget(cop_title)
        cop_header_box.addStretch()
        cop_header_box.addWidget(self.copilot_badge)
        cop_layout.addLayout(cop_header_box)

        # Copilot Premium Requests Row
        cop_prem_row = QHBoxLayout()
        cop_prem_title = QLabel("Premium Quota:", self.copilot_card)
        cop_prem_title.setProperty("class", "DrawerRowTitle")
        self.copilot_prem_val = QLabel("85.00% (255/300)", self.copilot_card)
        self.copilot_prem_val.setProperty("class", "DrawerRowVal")
        self.copilot_prem_time = QLabel("14d 6h", self.copilot_card)
        self.copilot_prem_time.setProperty("class", "DrawerRowTime")
        cop_prem_row.addWidget(cop_prem_title)
        cop_prem_row.addStretch()
        cop_prem_row.addWidget(self.copilot_prem_val)
        cop_prem_row.addWidget(self.copilot_prem_time)
        cop_layout.addLayout(cop_prem_row)

        self.copilot_prem_bar = QProgressBar(self.copilot_card)
        self.copilot_prem_bar.setProperty("class", "DrawerBar")
        self.copilot_prem_bar.setProperty("group", "copilot")
        self.copilot_prem_bar.setRange(0, 1000)
        self.copilot_prem_bar.setValue(850)
        self.copilot_prem_bar.setTextVisible(False)
        cop_layout.addWidget(self.copilot_prem_bar)

        # Copilot Rate Limit Row
        cop_rate_row = QHBoxLayout()
        cop_rate_title = QLabel("Rolling Rate Limit:", self.copilot_card)
        cop_rate_title.setProperty("class", "DrawerRowTitle")
        self.copilot_rate_val = QLabel("92.00%", self.copilot_card)
        self.copilot_rate_val.setProperty("class", "DrawerRowVal")
        self.copilot_rate_time = QLabel("45m", self.copilot_card)
        self.copilot_rate_time.setProperty("class", "DrawerRowTime")
        cop_rate_row.addWidget(cop_rate_title)
        cop_rate_row.addStretch()
        cop_rate_row.addWidget(self.copilot_rate_val)
        cop_rate_row.addWidget(self.copilot_rate_time)
        cop_layout.addLayout(cop_rate_row)

        self.copilot_rate_bar = QProgressBar(self.copilot_card)
        self.copilot_rate_bar.setProperty("class", "DrawerBar")
        self.copilot_rate_bar.setProperty("group", "copilot")
        self.copilot_rate_bar.setRange(0, 1000)
        self.copilot_rate_bar.setValue(920)
        self.copilot_rate_bar.setTextVisible(False)
        cop_layout.addWidget(self.copilot_rate_bar)

        self.drawer_layout.addWidget(self.copilot_card)

        # 3. CLAUDE CODE CLI CARD
        self.claude_code_card = QFrame(self.drawer_frame)
        self.claude_code_card.setObjectName("ClaudeCodeCard")
        claude_code_layout = QVBoxLayout(self.claude_code_card)
        claude_code_layout.setContentsMargins(8, 6, 8, 6)
        claude_code_layout.setSpacing(5)

        cc_header_box = QHBoxLayout()
        cc_title = QLabel("CLAUDE CODE CLI", self.claude_code_card)
        cc_title.setObjectName("ClaudeCodeCardHeader")
        self.claude_code_badge = QLabel("SWITCH", self.claude_code_card)
        self.claude_code_badge.setProperty("class", "InactiveGroupBadge")
        self.claude_code_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.claude_code_badge.mousePressEvent = lambda e: self.set_active_cli(CLI_CLAUDE_CODE)
        cc_header_box.addWidget(cc_title)
        cc_header_box.addStretch()
        cc_header_box.addWidget(self.claude_code_badge)
        claude_code_layout.addLayout(cc_header_box)

        # 5-Hour Session Window Row
        cc_5h_row = QHBoxLayout()
        cc_5h_title = QLabel("5-Hour Window:", self.claude_code_card)
        cc_5h_title.setProperty("class", "DrawerRowTitle")
        self.claude_code_5h_val = QLabel("78.50%", self.claude_code_card)
        self.claude_code_5h_val.setProperty("class", "DrawerRowVal")
        self.claude_code_5h_time = QLabel("2h 40m", self.claude_code_card)
        self.claude_code_5h_time.setProperty("class", "DrawerRowTime")
        cc_5h_row.addWidget(cc_5h_title)
        cc_5h_row.addStretch()
        cc_5h_row.addWidget(self.claude_code_5h_val)
        cc_5h_row.addWidget(self.claude_code_5h_time)
        claude_code_layout.addLayout(cc_5h_row)

        self.claude_code_5h_bar = QProgressBar(self.claude_code_card)
        self.claude_code_bar = self.claude_code_5h_bar
        self.claude_code_5h_bar.setProperty("class", "DrawerBar")
        self.claude_code_5h_bar.setProperty("group", "claude")
        self.claude_code_5h_bar.setRange(0, 1000)
        self.claude_code_5h_bar.setValue(785)
        self.claude_code_5h_bar.setTextVisible(False)
        claude_code_layout.addWidget(self.claude_code_5h_bar)

        # Monthly Budget Row
        cc_mo_row = QHBoxLayout()
        cc_mo_title = QLabel("Monthly Budget:", self.claude_code_card)
        cc_mo_title.setProperty("class", "DrawerRowTitle")
        self.claude_code_mo_val = QLabel("91.20% ($91.20/$100)", self.claude_code_card)
        self.claude_code_mo_val.setProperty("class", "DrawerRowVal")
        self.claude_code_mo_time = QLabel("OPTIMAL", self.claude_code_card)
        self.claude_code_mo_time.setProperty("class", "DrawerRowTimeFull")
        cc_mo_row.addWidget(cc_mo_title)
        cc_mo_row.addStretch()
        cc_mo_row.addWidget(self.claude_code_mo_val)
        cc_mo_row.addWidget(self.claude_code_mo_time)
        claude_code_layout.addLayout(cc_mo_row)

        self.claude_code_mo_bar = QProgressBar(self.claude_code_card)
        self.claude_code_mo_bar.setProperty("class", "DrawerBar")
        self.claude_code_mo_bar.setProperty("group", "claude")
        self.claude_code_mo_bar.setRange(0, 1000)
        self.claude_code_mo_bar.setValue(912)
        self.claude_code_mo_bar.setTextVisible(False)
        claude_code_layout.addWidget(self.claude_code_mo_bar)

        self.drawer_layout.addWidget(self.claude_code_card)

        # 4. OPENAI CODEX CARD
        self.codex_card = QFrame(self.drawer_frame)
        self.codex_card.setObjectName("CodexCard")
        codex_layout = QVBoxLayout(self.codex_card)
        codex_layout.setContentsMargins(8, 6, 8, 6)
        codex_layout.setSpacing(5)

        codex_header_box = QHBoxLayout()
        codex_title = QLabel("OPENAI CODEX", self.codex_card)
        codex_title.setObjectName("CodexCardHeader")
        self.codex_badge = QLabel("SWITCH", self.codex_card)
        self.codex_badge.setProperty("class", "InactiveGroupBadge")
        self.codex_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.codex_badge.mousePressEvent = lambda e: self.set_active_cli(CLI_CODEX)
        codex_header_box.addWidget(codex_title)
        codex_header_box.addStretch()
        codex_header_box.addWidget(self.codex_badge)
        codex_layout.addLayout(codex_header_box)

        codex_5h_row = QHBoxLayout()
        codex_5h_title = QLabel("5-Hour Window:", self.codex_card)
        codex_5h_title.setProperty("class", "DrawerRowTitle")
        self.codex_5h_val = QLabel("100.00%", self.codex_card)
        self.codex_5h_val.setProperty("class", "DrawerRowVal")
        self.codex_5h_time = QLabel("OPTIMAL", self.codex_card)
        self.codex_5h_time.setProperty("class", "DrawerRowTime")
        codex_5h_row.addWidget(codex_5h_title)
        codex_5h_row.addStretch()
        codex_5h_row.addWidget(self.codex_5h_val)
        codex_5h_row.addWidget(self.codex_5h_time)
        codex_layout.addLayout(codex_5h_row)

        self.codex_5h_bar = QProgressBar(self.codex_card)
        self.codex_5h_bar.setProperty("class", "DrawerBar")
        self.codex_5h_bar.setProperty("group", "codex")
        self.codex_5h_bar.setRange(0, 1000)
        self.codex_5h_bar.setValue(1000)
        self.codex_5h_bar.setTextVisible(False)
        codex_layout.addWidget(self.codex_5h_bar)

        codex_weekly_row = QHBoxLayout()
        codex_weekly_title = QLabel("7-Day Window:", self.codex_card)
        codex_weekly_title.setProperty("class", "DrawerRowTitle")
        self.codex_weekly_val = QLabel("100.00%", self.codex_card)
        self.codex_weekly_val.setProperty("class", "DrawerRowVal")
        self.codex_weekly_time = QLabel("OPTIMAL", self.codex_card)
        self.codex_weekly_time.setProperty("class", "DrawerRowTime")
        codex_weekly_row.addWidget(codex_weekly_title)
        codex_weekly_row.addStretch()
        codex_weekly_row.addWidget(self.codex_weekly_val)
        codex_weekly_row.addWidget(self.codex_weekly_time)
        codex_layout.addLayout(codex_weekly_row)

        self.codex_weekly_bar = QProgressBar(self.codex_card)
        self.codex_weekly_bar.setProperty("class", "DrawerBar")
        self.codex_weekly_bar.setProperty("group", "codex")
        self.codex_weekly_bar.setRange(0, 1000)
        self.codex_weekly_bar.setValue(1000)
        self.codex_weekly_bar.setTextVisible(False)
        codex_layout.addWidget(self.codex_weekly_bar)

        self.codex_meta = QLabel("Plan: unknown  |  Local session scan: waiting", self.codex_card)
        self.codex_meta.setProperty("class", "DrawerRowTime")
        codex_layout.addWidget(self.codex_meta)
        self.drawer_layout.addWidget(self.codex_card)

        # 5. REAL-TIME ACTIVITY & TPM SPARKLINE CARD
        self.act_card = QFrame(self.drawer_frame)
        act_card = self.act_card
        act_card.setProperty("class", "FlyoutCard")
        act_layout = QVBoxLayout(act_card)
        act_layout.setContentsMargins(8, 6, 8, 6)
        act_layout.setSpacing(4)

        act_row1 = QHBoxLayout()
        act_title = QLabel("REAL-TIME ACTIVITY", act_card)
        act_title.setProperty("class", "DrawerTitle")
        self.drawer_sessions_val = QLabel("Sessions: 1  |  Total: 0", act_card)
        self.drawer_sessions_val.setProperty("class", "DrawerValue")
        act_row1.addWidget(act_title)
        act_row1.addStretch()
        act_row1.addWidget(self.drawer_sessions_val)

        self.sparkline = MiniSparkline(width=340, height=20, line_color="#00e599", parent=act_card)
        self.drawer_tpm_val = QLabel("Rate: 0 tpm  (Peak: 0 tpm)", act_card)
        self.drawer_tpm_val.setProperty("class", "DrawerValueSub")

        act_layout.addLayout(act_row1)
        act_layout.addWidget(self.sparkline)
        act_layout.addWidget(self.drawer_tpm_val)
        self.drawer_layout.addWidget(act_card)

        # 5B. RETRO TICKET CARD VIEW (Alternative Theme inside Drawer)
        self.ticket_panel = TicketDashboardPanel(self.drawer_frame)
        self.ticket_panel.set_show_all(self.ticket_show_all)
        self.ticket_panel.cli_selected.connect(self._on_ticket_cli_selected)
        self.ticket_panel.show_all_toggled.connect(self._on_ticket_show_all_toggled)
        self.ticket_panel.setMinimumWidth(452)
        self.ticket_panel.hide()
        self.drawer_layout.addWidget(self.ticket_panel)

        # Backward compatibility drawer elements
        self.drawer_budget_val = QLabel("剩餘 5.00M / 5.00M", self.drawer_frame)
        self.drawer_budget_val.hide()
        self.drawer_budget_bar = QProgressBar(self.drawer_frame)
        self.drawer_budget_bar.hide()
        self.drawer_budget_sub = QLabel("", self.drawer_frame)
        self.drawer_budget_sub.hide()
        self.drawer_usd_val = QLabel("剩餘 $2.00 / $2.00 USD", self.drawer_frame)
        self.drawer_usd_val.hide()
        self.drawer_usd_bar = QProgressBar(self.drawer_frame)
        self.drawer_usd_bar.hide()
        self.drawer_usd_sub = QLabel("", self.drawer_frame)
        self.drawer_usd_sub.hide()
        self.drawer_ctx_val = QLabel("剩餘 1.00M / 1.00M", self.drawer_frame)
        self.drawer_ctx_val.hide()
        self.drawer_ctx_bar = QProgressBar(self.drawer_frame)
        self.drawer_ctx_bar.hide()
        self.drawer_tokens_breakdown = QLabel("", self.drawer_frame)
        self.drawer_tokens_breakdown.hide()

        # 5. QUICK ACTION BUTTONS BAR
        self.drawer_action_bar_widget = QWidget(self.drawer_frame)
        action_bar = QHBoxLayout(self.drawer_action_bar_widget)
        action_bar.setContentsMargins(0, 0, 0, 0)
        action_bar.setSpacing(6)

        btn_sync = QPushButton("SYNC QUOTAS", self.drawer_action_bar_widget)
        btn_sync.setObjectName("SyncUsageActionBtn")
        btn_sync.setProperty("class", "DrawerActionBtnPrimary")
        btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sync.setToolTip("在背景靜默拉取最新配額 (不彈窗)")
        btn_sync.clicked.connect(self.trigger_sync_now)

        btn_switch = QPushButton("SWITCH CLI", self.drawer_action_bar_widget)
        btn_switch.setProperty("class", "DrawerActionBtn")
        btn_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_switch.clicked.connect(self.switch_next_cli)

        btn_top = QPushButton("PIN ON TOP", self.drawer_action_bar_widget)
        btn_top.setProperty("class", "DrawerActionBtn")
        btn_top.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_top.clicked.connect(lambda: self.set_always_on_top(not self.always_on_top))

        btn_compact = QPushButton("MINI HUD", self.drawer_action_bar_widget)
        btn_compact.setProperty("class", "DrawerActionBtn")
        btn_compact.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_compact.clicked.connect(self.toggle_compact_mode)

        self.btn_theme = QPushButton(
            "HUD VIEW" if self.ui_theme == "ticket" else "TICKET VIEW",
            self.drawer_action_bar_widget,
        )
        self.btn_theme.setObjectName("ThemeSwitchBtn")
        self.btn_theme.setProperty("class", "DrawerActionBtn")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setToolTip("切換「深鈦極簡 HUD」與「日系復古票券卡片」介面風格")
        self.btn_theme.clicked.connect(self.toggle_ui_theme)

        action_bar.addWidget(btn_sync)
        action_bar.addWidget(btn_switch)
        action_bar.addWidget(self.btn_theme)
        action_bar.addWidget(btn_top)
        action_bar.addWidget(btn_compact)
        self.drawer_layout.addWidget(self.drawer_action_bar_widget)

        # ── Auto-Sync Status Bar ─────────────────────────────────────────────
        self.drawer_sync_bar_widget = QWidget(self.drawer_frame)
        sync_bar_layout = QHBoxLayout(self.drawer_sync_bar_widget)
        sync_bar_layout.setContentsMargins(0, 2, 0, 0)
        sync_bar_layout.setSpacing(6)

        self.sync_status_label = QLabel(
            "AUTO-SYNC UNAVAILABLE  |  [ FALLBACK SYNC AVAILABLE ]",
            self.drawer_sync_bar_widget,
        )
        self.sync_status_label.setObjectName("SyncStatusBar")
        self.sync_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_sync_now = QPushButton("SYNC NOW", self.drawer_sync_bar_widget)
        self.btn_sync_now.setObjectName("SyncNowBtn")
        self.btn_sync_now.setProperty("class", "DrawerActionBtnPrimary")
        self.btn_sync_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_now.clicked.connect(self.trigger_sync_now)

        sync_bar_layout.addWidget(self.sync_status_label, 1)
        sync_bar_layout.addWidget(self.btn_sync_now)
        self.drawer_layout.addWidget(self.drawer_sync_bar_widget)
        # ─────────────────────────────────────────────────────────────────────

        self.root_layout.addWidget(self.drawer_frame)


        # Drawer height animation with seamless auto-resizing
        self.drawer_anim = QPropertyAnimation(self.drawer_frame, b"maximumHeight", self)
        self.drawer_anim.setDuration(220)
        self.drawer_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.drawer_anim.valueChanged.connect(self._on_drawer_anim_step)
        self.drawer_anim.finished.connect(self._on_drawer_anim_finished)

        # =========================================================================
        # 2. COMPACT FRAME (MINIMAL PILL MODE)
        # =========================================================================
        self.compact_frame = QFrame(self)
        self.compact_frame.setObjectName("CompactFrame")

        compact_shadow = QGraphicsDropShadowEffect(self.compact_frame)
        compact_shadow.setBlurRadius(12)
        compact_shadow.setYOffset(2)
        compact_shadow.setColor(QColor(0, 0, 0, 160))
        self.compact_frame.setGraphicsEffect(compact_shadow)

        compact_layout = QHBoxLayout(self.compact_frame)
        compact_layout.setContentsMargins(8, 2, 8, 2)
        compact_layout.setSpacing(6)

        self.compact_dot = GlowingPulseDot(size=6, parent=self.compact_frame)
        self.compact_group_label = QLabel("GEMINI: 60.1%", self.compact_frame)
        self.compact_group_label.setObjectName("CompactRemainingLabel")

        # Backward compatibility compact aliases
        self.compact_token_label = self.compact_group_label
        self.compact_remaining_label = self.compact_group_label

        self.compact_countdown_badge = QLabel("3h 10m", self.compact_frame)
        self.compact_countdown_badge.setObjectName("CompactCountdownBadge")

        self.compact_context_badge = QLabel("60.1%", self.compact_frame)
        self.compact_context_badge.setObjectName("CompactRemainingBadge")
        self.compact_remaining_badge = self.compact_context_badge

        self.compact_tpm_label = QLabel("0 tpm", self.compact_frame)
        self.compact_tpm_label.setObjectName("CompactTpmLabel")

        self.compact_cost_label = QLabel("$2.00", self.compact_frame)
        self.compact_cost_label.setObjectName("CompactCostLabel")
        self.compact_cost_label.hide()

        compact_layout.addWidget(self.compact_dot)
        compact_layout.addWidget(self.compact_group_label)
        compact_layout.addWidget(self.compact_countdown_badge)
        compact_layout.addWidget(self.compact_tpm_label)

        self.main_layout.addWidget(self.root_frame)
        self.main_layout.addWidget(self.compact_frame)

        # Apply initial mode
        if self.is_compact:
            self.root_frame.hide()
            self.compact_frame.show()
        else:
            self.root_frame.show()
            self.compact_frame.hide()

        self._update_card_visibility()
        self._update_drawer_ui()

    def _update_card_visibility(self) -> None:
        """Show or hide CLI cards in drawer based on enabled_clis and active UI theme."""
        en = self.multi_cli.enabled_clis
        is_ticket = (self.ui_theme == "ticket")
        self.agy_card.setVisible((not is_ticket) and (CLI_AGY in en))
        self.copilot_card.setVisible((not is_ticket) and (CLI_COPILOT in en))
        self.claude_code_card.setVisible((not is_ticket) and (CLI_CLAUDE_CODE in en))
        self.codex_card.setVisible((not is_ticket) and (CLI_CODEX in en))
        if hasattr(self, "act_card"):
            self.act_card.setVisible(not is_ticket)
        if hasattr(self, "drawer_action_bar_widget"):
            self.drawer_action_bar_widget.setVisible(not is_ticket)
        if hasattr(self, "drawer_sync_bar_widget"):
            self.drawer_sync_bar_widget.setVisible(not is_ticket)
        if hasattr(self, "ticket_panel"):
            self.ticket_panel.setVisible(is_ticket)
        if hasattr(self, "btn_theme"):
            self.btn_theme.setText("HUD VIEW" if is_ticket else "TICKET VIEW")

    def _on_drawer_anim_step(self, value) -> None:
        """Dynamically adjust parent widget geometry during drawer animation."""
        self.adjustSize()

    def _on_drawer_anim_finished(self) -> None:
        """Handle cleanup after drawer animation completes."""
        if not self.is_drawer_expanded:
            self.drawer_frame.hide()
            self.drawer_frame.setMaximumHeight(0)
            self.adjustSize()
            self.resize(self.sizeHint())
        else:
            self.drawer_frame.setMaximumHeight(16777215)
            self.adjustSize()

    def _on_countdown_tick(self) -> None:
        """Periodic 1-second tick to update live countdown strings for all active CLIs."""
        if not self.multi_cli:
            return

        now = time.time()
        win = self.multi_cli.get_active_primary_window()

        # Update Header Countdown Badge
        cd_str = win.formatted_countdown(current_time=now)
        self.countdown_badge.setText(cd_str)
        self.countdown_badge.setProperty("full", "true" if cd_str in ("OPTIMAL", "AVAILABLE", "充足") else "false")
        self.countdown_badge.style().unpolish(self.countdown_badge)
        self.countdown_badge.style().polish(self.countdown_badge)

        self.compact_countdown_badge.setText(cd_str)

        # If drawer is expanded, update card countdown labels
        if self.is_drawer_expanded:
            # AGY
            g_5h_cd = self.multi_cli.agy.gemini.five_hour.formatted_countdown(current_time=now)
            c_5h_cd = self.multi_cli.agy.claude_gpt.five_hour.formatted_countdown(current_time=now)
            self.gemini_5h_time.setText(g_5h_cd)
            self.claude_5h_time.setText(c_5h_cd)

            # Copilot
            cop_prem_cd = self.multi_cli.copilot.premium_requests.formatted_countdown(current_time=now)
            cop_rate_cd = self.multi_cli.copilot.rate_limit.formatted_countdown(current_time=now)
            self.copilot_prem_time.setText(cop_prem_cd)
            self.copilot_rate_time.setText(cop_rate_cd)

            # Claude Code
            cc_5h_cd = self.multi_cli.claude.five_hour.formatted_countdown(current_time=now)
            cc_mo_cd = self.multi_cli.claude.monthly_budget.formatted_countdown(current_time=now)
            self.claude_code_5h_time.setText(cc_5h_cd)
            self.claude_code_mo_time.setText(cc_mo_cd)

            self.codex_5h_time.setText(self.multi_cli.codex.five_hour.formatted_countdown(current_time=now))
            self.codex_weekly_time.setText(self.multi_cli.codex.weekly.formatted_countdown(current_time=now))

            if self.ui_theme == "ticket" and hasattr(self, "ticket_panel"):
                self.ticket_panel.update_panel(self.multi_cli, stats=self.current_stats, current_time=now)

    def trigger_sync_now(self) -> None:
        """Immediate visual and tactile feedback on Sync Now click."""
        self._sync_request_id += 1
        request_id = self._sync_request_id
        if hasattr(self, "btn_sync_now"):
            self.btn_sync_now.setText("SYNCING...")
            self.btn_sync_now.setEnabled(False)
        self.set_sync_status("AUTO-SYNC ON  |  SYNCING...")
        QTimer.singleShot(self._sync_timeout_ms, lambda rid=request_id: self._handle_sync_timeout(rid))
        self.request_force_sync.emit()

    def on_sync_finished(self, success: bool = True) -> None:
        """Invoked when background CLI poller returns with fresh quota data."""
        self._sync_request_id += 1
        if hasattr(self, "btn_sync_now"):
            self.btn_sync_now.setText("SYNCED" if success else "FAILED")
            QTimer.singleShot(1500, self._reset_sync_button)
        self.refresh_ui()

    def _handle_sync_timeout(self, request_id: int) -> None:
        """Recover the SYNC NOW button if no background completion signal arrives."""
        if request_id != self._sync_request_id:
            return
        self._sync_request_id += 1
        self.set_sync_status("AUTO-SYNC TIMEOUT  |  [ FALLBACK SYNC AVAILABLE ]")
        if hasattr(self, "btn_sync_now"):
            self.btn_sync_now.setText("FAILED")
            QTimer.singleShot(1500, self._reset_sync_button)
        self.refresh_ui()

    def _reset_sync_button(self) -> None:
        if hasattr(self, "btn_sync_now"):
            self.btn_sync_now.setText("SYNC NOW")
            self.btn_sync_now.setEnabled(True)

    def _on_group_label_clicked(self) -> None:
        """Clicking group label triggers instant group toggle in AGY or CLI cycling."""
        if self.multi_cli.active_cli == CLI_AGY:
            self.toggle_active_group()
        else:
            self.switch_next_cli()

    def refresh_ui(self, stats: Optional[SessionTokenStats] = None) -> None:
        """Force full immediate update and repaint across all HUD layers."""
        if stats is not None:
            self.current_stats = stats
        elif self.current_stats is None:
            self.current_stats = SessionTokenStats(
                session_id="ready",
                multi_cli=self.multi_cli,
                last_updated=time.time(),
            )
        else:
            self.current_stats.multi_cli = self.multi_cli
            self.current_stats.dual_quota = self.multi_cli.agy

        self.update_stats(self.current_stats)
        self._update_drawer_ui(self.current_stats)

        # Force repaint all visual layers
        self.root_frame.update()
        self.capsule_bar.update()
        self.circular_ring.update()
        self.pulsing_dot.update()
        self.drawer_frame.update()
        self.agy_card.update()
        self.copilot_card.update()
        self.claude_code_card.update()
        self.codex_card.update()
        self.gemini_5h_bar.update()
        self.claude_5h_bar.update()
        self.update()

    def update_stats(self, stats: SessionTokenStats) -> None:
        """Update HUD UI elements with fresh session stats and Multi-CLI state."""
        self.current_stats = stats
        if stats.multi_cli:
            # Polling owns quota values, while the widget owns the current view.
            # Preserve the user's selections when a delayed/stale poll result arrives.
            active_cli = self.multi_cli.active_cli if self.multi_cli else None
            active_group = self.multi_cli.agy.active_group if self.multi_cli else None
            enabled_clis = list(self.multi_cli.enabled_clis) if (self.multi_cli and self.multi_cli.enabled_clis) else None
            self.multi_cli = stats.multi_cli
            if enabled_clis is not None:
                self.multi_cli.enabled_clis = enabled_clis
            if active_cli in ALL_CLIS or active_cli == CLI_COMBINED:
                if active_cli == CLI_COMBINED or active_cli in self.multi_cli.enabled_clis:
                    self.multi_cli.active_cli = active_cli
                elif self.multi_cli.enabled_clis:
                    self.multi_cli.active_cli = self.multi_cli.enabled_clis[0]
            if active_group in (GROUP_GEMINI, GROUP_CLAUDE_GPT):
                self.multi_cli.agy.active_group = active_group
            stats.multi_cli = self.multi_cli

        now = time.time()
        win = self.multi_cli.get_active_primary_window()
        active_cli = self.multi_cli.active_cli
        theme_color = self.multi_cli.get_active_theme_color()

        # 1. Update Header Capsule Bar
        title_text = stats.formatted_capsule_title()
        self.group_quota_label.setText(title_text)
        self.compact_group_label.setText(title_text)

        g_5h = self.multi_cli.agy.gemini.five_hour
        c_5h = self.multi_cli.agy.claude_gpt.five_hour

        # Check AGY dual group alert & sub-label text
        if active_cli == CLI_AGY:
            cur_grp = self.multi_cli.agy.active_group
            if cur_grp == GROUP_GEMINI:
                alt_name = "CLAUDE"
                alt_pct = c_5h.percent
            else:
                alt_name = "GEMINI"
                alt_pct = g_5h.percent

            if alt_pct <= 0:
                sub_text = f"{alt_name}: 0% 耗盡  |  點擊秒切"
            elif alt_pct <= 20.0:
                sub_text = f"{alt_name}: {alt_pct:.0f}% 緊縮  |  點擊切換"
            else:
                sub_text = f"{alt_name}: {alt_pct:.0f}%  |  點擊切換"
            self.group_quota_sub.setText(sub_text)
            self.group_switch_btn.setText("AGY")
            self.group_switch_btn.setToolTip(f"當前: AGY ({self.multi_cli.agy.get_active_group().display_name})\n點擊快速切換至 {alt_name} ({alt_pct:.1f}%)")
        else:
            self.group_quota_sub.setText(stats.formatted_capsule_sub())
            self.group_switch_btn.setText(self.multi_cli.get_active_short_name())
            self.group_switch_btn.setToolTip(f"當前: {self.multi_cli.get_active_display_name()} (點擊切換下一個已啟用 CLI)")

        # Status Dot Alert Logic
        dot_status = "safe"
        if win.percent < 20.0:
            dot_status = "danger"
        elif active_cli == CLI_AGY and (c_5h.percent <= 0.0 or g_5h.percent <= 0.0):
            dot_status = "danger"  # Red alert if either Claude or Gemini is depleted!
        elif active_cli == CLI_AGY and (c_5h.percent < 20.0 or g_5h.percent < 20.0):
            dot_status = "warning"
        elif win.percent <= 40.0:
            dot_status = "warning"
        elif active_cli == CLI_COPILOT:
            dot_status = "copilot"
        elif active_cli == CLI_CLAUDE_CODE:
            dot_status = "claude"
        elif active_cli == CLI_CODEX:
            dot_status = "codex"
        elif self.multi_cli.agy.active_group == GROUP_CLAUDE_GPT:
            dot_status = "iris"

        self.pulsing_dot.set_state(is_generating=stats.is_generating, status=dot_status)
        self.compact_dot.set_state(is_generating=stats.is_generating, status=dot_status)

        # Circular Ring Gauge
        label_text = "5H" if active_cli != CLI_COPILOT else "REQ"
        self.circular_ring.set_percent(win.percent, animate=True, label=label_text, accent_color=theme_color)
        self.compact_context_badge.setText(f"{win.percent:.1f}%")

        # Countdown Badge
        cd_str = win.formatted_countdown(current_time=now)
        self.countdown_badge.setText(cd_str)
        self.countdown_badge.setProperty("full", "true" if cd_str in ("OPTIMAL", "AVAILABLE", "充足") else "false")
        self.countdown_badge.style().unpolish(self.countdown_badge)
        self.countdown_badge.style().polish(self.countdown_badge)
        self.compact_countdown_badge.setText(cd_str)

        # TPM Speed Badge
        tpm_text = stats.formatted_tpm()
        self.tpm_badge.setText(tpm_text)
        self.tpm_badge.setProperty("generating", "true" if stats.is_generating else "false")
        self.tpm_badge.style().unpolish(self.tpm_badge)
        self.tpm_badge.style().polish(self.tpm_badge)
        self.compact_tpm_label.setText(tpm_text)

        # Sparkline
        self.sparkline.set_line_color(theme_color)
        if stats.tpm > 0 or stats.is_generating:
            self.sparkline.add_point(float(stats.tpm))
            if stats.tpm > self.peak_tpm:
                self.peak_tpm = stats.tpm
        elif len(self.sparkline.data_points) == 0:
            self.sparkline.add_point(0.0)

        # 2. Update Drawer UI
        self._update_card_visibility()
        self._update_drawer_ui(stats, now)

    def _update_drawer_ui(self, stats: Optional[SessionTokenStats] = None, current_time: Optional[float] = None) -> None:
        """Update cards in the Mini-Dashboard drawer."""
        now = current_time or time.time()
        active_cli = self.multi_cli.active_cli

        # Badges on Cards
        self._update_badge(self.agy_badge, active_cli == CLI_AGY)
        self._update_badge(self.copilot_badge, active_cli == CLI_COPILOT)
        self._update_badge(self.claude_code_badge, active_cli == CLI_CLAUDE_CODE)
        self._update_badge(self.codex_badge, active_cli == CLI_CODEX)

        # 1. AGY Values & Bars
        g_5h = self.multi_cli.agy.gemini.five_hour
        c_5h = self.multi_cli.agy.claude_gpt.five_hour
        cur_agy_grp = self.multi_cli.agy.active_group

        if hasattr(self, "gemini_sub_badge"):
            self._update_badge(self.gemini_sub_badge, cur_agy_grp == GROUP_GEMINI and active_cli == CLI_AGY)
        if hasattr(self, "claude_sub_badge"):
            self._update_badge(self.claude_sub_badge, cur_agy_grp == GROUP_CLAUDE_GPT and active_cli == CLI_AGY)

        gem_display = f"{g_5h.percent:.2f}%" if g_5h.percent > 0 else "0.00% [EMPTY]"
        self.gemini_5h_val.setText(gem_display)
        self.gemini_5h_time.setText(g_5h.formatted_countdown(current_time=now))
        self.gemini_5h_bar.setValue(int(g_5h.percent * 10))
        self._style_bar(self.gemini_5h_bar, g_5h.percent)

        claude_display = f"{c_5h.percent:.2f}%" if c_5h.percent > 0 else "0.00% [EMPTY]"
        self.claude_5h_val.setText(claude_display)
        self.claude_5h_time.setText(c_5h.formatted_countdown(current_time=now))
        self.claude_5h_bar.setValue(int(c_5h.percent * 10))
        self._style_bar(self.claude_5h_bar, c_5h.percent)

        # 2. Copilot Values & Bars
        cop_prem = self.multi_cli.copilot.premium_requests
        cop_rate = self.multi_cli.copilot.rate_limit
        prem_summary = f"{cop_prem.percent:.2f}% ({int(cop_prem.remaining_units or 0)}/{int(cop_prem.total_units or 300)})"
        self.copilot_prem_val.setText(prem_summary)
        self.copilot_prem_time.setText(cop_prem.formatted_countdown(current_time=now))
        self.copilot_prem_bar.setValue(int(cop_prem.percent * 10))
        self._style_bar(self.copilot_prem_bar, cop_prem.percent)

        self.copilot_rate_val.setText(f"{cop_rate.percent:.2f}%")
        self.copilot_rate_time.setText(cop_rate.formatted_countdown(current_time=now))
        self.copilot_rate_bar.setValue(int(cop_rate.percent * 10))
        self._style_bar(self.copilot_rate_bar, cop_rate.percent)

        # 3. Claude Code Values & Bars
        cc_5h = self.multi_cli.claude.five_hour
        cc_mo = self.multi_cli.claude.monthly_budget
        self.claude_code_5h_val.setText(f"{cc_5h.percent:.2f}%")
        self.claude_code_5h_time.setText(cc_5h.formatted_countdown(current_time=now))
        self.claude_code_5h_bar.setValue(int(cc_5h.percent * 10))
        self._style_bar(self.claude_code_5h_bar, cc_5h.percent)

        mo_summary = f"{cc_mo.percent:.2f}% (${cc_mo.remaining_units or 0:.2f}/${cc_mo.total_units or 100:.2f})"
        self.claude_code_mo_val.setText(mo_summary)
        self.claude_code_mo_time.setText(cc_mo.formatted_countdown(current_time=now))
        self.claude_code_mo_bar.setValue(int(cc_mo.percent * 10))
        self._style_bar(self.claude_code_mo_bar, cc_mo.percent)

        # 4. OpenAI Codex Values & Bars
        codex_5h = self.multi_cli.codex.five_hour
        codex_weekly = self.multi_cli.codex.weekly
        self.codex_5h_val.setText(f"{codex_5h.percent:.2f}%")
        self.codex_5h_time.setText(codex_5h.formatted_countdown(current_time=now))
        self.codex_5h_bar.setValue(int(codex_5h.percent * 10))
        self._style_bar(self.codex_5h_bar, codex_5h.percent)

        self.codex_weekly_val.setText(f"{codex_weekly.percent:.2f}%")
        self.codex_weekly_time.setText(codex_weekly.formatted_countdown(current_time=now))
        self.codex_weekly_bar.setValue(int(codex_weekly.percent * 10))
        self._style_bar(self.codex_weekly_bar, codex_weekly.percent)
        plan = self.multi_cli.codex.plan_type or "unknown"
        detected = "detected" if self.multi_cli.codex.auto_detected else "waiting"
        token_summary = TokenParser.format_number(self.multi_cli.codex.total_tokens)
        self.codex_meta.setText(f"Plan: {plan}  |  Tokens: {token_summary}  |  Local scan: {detected}")

        # 5. Activity Card
        if stats:
            self.drawer_sessions_val.setText(f"Sessions: {stats.today_sessions_count}  |  Total: {TokenParser.format_number(stats.daily_tokens)}")
            self.drawer_tpm_val.setText(f"Rate: {stats.formatted_tpm()}  (Peak: {TokenParser.format_number(self.peak_tpm)} tpm)")
            self.drawer_budget_val.setText(f"剩餘 {TokenParser.format_number(stats.remaining_daily_tokens)} / {TokenParser.format_number(stats.daily_budget_tokens)} ({stats.remaining_daily_percent:.1f}%)")
            self.drawer_usd_val.setText(f"剩餘 ${stats.remaining_daily_usd:.2f} / ${stats.daily_budget_usd:.2f} USD")
            self.drawer_ctx_val.setText(f"剩餘 {TokenParser.format_number(stats.remaining_context_tokens)} / {TokenParser.format_number(stats.context_limit)}")

        # 6. Retro Ticket Dashboard Panel
        if hasattr(self, "ticket_panel"):
            self.ticket_panel.update_panel(self.multi_cli, stats=stats or self.current_stats, current_time=now)

    def _update_badge(self, badge: QLabel, is_active: bool) -> None:
        if is_active:
            badge.setText("ACTIVE")
            badge.setProperty("class", "ActiveGroupBadge")
        else:
            badge.setText("SWITCH")
            badge.setProperty("class", "InactiveGroupBadge")
        badge.style().unpolish(badge)
        badge.style().polish(badge)

    def _style_bar(self, bar: QProgressBar, pct: float) -> None:
        """Apply quota status property to progress bar for stylesheet chunk color."""
        if pct < 20.0:
            bar.setProperty("quota", "danger")
        elif pct <= 40.0:
            bar.setProperty("quota", "warning")
        else:
            bar.setProperty("quota", "safe")
        bar.style().unpolish(bar)
        bar.style().polish(bar)

    def switch_next_cli(self) -> None:
        """Cycle active CLI among enabled_clis."""
        next_cli = self.multi_cli.switch_next_cli()
        save_multi_cli_state(self.multi_cli)
        self.cli_switched.emit(next_cli)
        self.refresh_ui()

    def set_active_cli(self, cli_id: str) -> None:
        """Explicitly switch active CLI."""
        self.multi_cli.set_active_cli(cli_id)
        save_multi_cli_state(self.multi_cli)
        self.cli_switched.emit(cli_id)
        self.refresh_ui()

    def set_active_agy_group(self, group_id: str) -> None:
        """Explicitly select AGY model group (GEMINI or CLAUDE_GPT)."""
        self.multi_cli.active_cli = CLI_AGY
        self.multi_cli.agy.set_active_group(group_id)
        save_multi_cli_state(self.multi_cli)
        self.group_switched.emit(group_id)
        self.refresh_ui()

    def set_sync_status(self, status: str) -> None:
        """Update the Auto-Sync status bar label in the drawer (thread-safe via Qt signal)."""
        if hasattr(self, "sync_status_label"):
            self.sync_status_label.setText(status)

    def toggle_cli_enabled(self, cli_id: str) -> None:
        """Toggle enabled status of a CLI source."""
        self.multi_cli.toggle_cli_enabled(cli_id)
        save_multi_cli_state(self.multi_cli)
        self._update_card_visibility()
        self.refresh_ui()
        if self.is_drawer_expanded:
            self.drawer_frame.setMaximumHeight(16777215)
            self.adjustSize()
            self.resize(self.sizeHint())

    def toggle_active_group(self) -> None:
        """Switch active monitored group within Antigravity (Gemini ⇄ Claude/GPT)."""
        new_grp = self.multi_cli.agy.toggle_active_group()
        save_multi_cli_state(self.multi_cli)
        self.group_switched.emit(new_grp)
        self.refresh_ui()

    def set_ui_theme(self, theme: str) -> None:
        """Switch drawer visual theme between 'obsidian' (Dark Titanium HUD) and 'ticket' (Retro Ticket Card)."""
        norm = "ticket" if str(theme).lower() == "ticket" else "obsidian"
        self.ui_theme = norm
        self.settings["ui_theme"] = norm
        save_settings({"ui_theme": norm})
        self._update_card_visibility()
        self.refresh_ui()
        if self.is_drawer_expanded:
            self.drawer_frame.setMaximumHeight(16777215)
            self.adjustSize()
            self.resize(self.sizeHint())

    def toggle_ui_theme(self) -> None:
        """Toggle between Dark Titanium HUD and Retro Ticket Card theme."""
        self.set_ui_theme("obsidian" if self.ui_theme == "ticket" else "ticket")

    def _on_ticket_cli_selected(self, cli_id: str) -> None:
        """Handle clicking a CLI tab or card header in Retro Ticket mode."""
        self.set_active_cli(cli_id)

    def _on_ticket_show_all_toggled(self, show_all: bool) -> None:
        """Persist single-card vs all-cards toggle in Retro Ticket mode."""
        self.ticket_show_all = bool(show_all)
        self.settings["ticket_show_all"] = self.ticket_show_all
        save_settings({"ticket_show_all": self.ticket_show_all})
        self._update_drawer_ui(self.current_stats)
        if self.is_drawer_expanded:
            self.drawer_frame.setMaximumHeight(16777215)
            self.adjustSize()
            self.resize(self.sizeHint())

    def show_usage_sync_dialog(self, force_dialog: bool = False) -> None:
        """Open manual sync dialog when requested, otherwise trigger silent background sync."""
        if not force_dialog:
            self.trigger_sync_now()
            return

        dlg = UsageSyncDialog(current_multi_state=self.multi_cli, default_target=self.multi_cli.active_cli, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.synced_multi_state:
                self.multi_cli = dlg.synced_multi_state
                save_multi_cli_state(self.multi_cli)
                self.set_sync_status("AUTO-SYNC ON  |  LAST SYNC just now  |  FALLBACK SYNCED")
                self.refresh_ui()

    def show_budget_dialog(self) -> None:
        """Open daily budget modal dialog."""
        dlg = BudgetDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.settings = load_settings()
            self.budget_changed.emit()
            self.request_rescan.emit()

    def toggle_drawer(self) -> None:
        """Smoothly expand or collapse the Mini-Dashboard flyout drawer."""
        if self.is_compact:
            return

        self.drawer_anim.stop()
        if not self.is_drawer_expanded:
            self.is_drawer_expanded = True
            self.drawer_frame.show()
            self.expand_btn.set_expanded(True)

            # Respect the actual content height so the fourth CLI card and
            # sync controls are not clipped by a fixed 500px ceiling.
            content_h = self.drawer_frame.sizeHint().height()
            max_screen_h = content_h
            screen = QApplication.primaryScreen()
            if screen is not None:
                max_screen_h = max(360, screen.availableGeometry().height() - 120)
            target_h = min(max(320, content_h), max_screen_h)

            self.drawer_anim.setStartValue(self.drawer_frame.height())
            self.drawer_anim.setEndValue(target_h)
            self.drawer_anim.start()
        else:
            self.is_drawer_expanded = False
            self.expand_btn.set_expanded(False)

            self.drawer_anim.setStartValue(self.drawer_frame.height())
            self.drawer_anim.setEndValue(0)
            self.drawer_anim.start()

    def toggle_compact_mode(self) -> None:
        """Toggle between full HUD capsule and minimal compact pill mode."""
        self.is_compact = not self.is_compact
        self.settings["is_compact"] = self.is_compact
        save_settings({"is_compact": self.is_compact})

        if self.is_compact:
            if self.is_drawer_expanded:
                self.is_drawer_expanded = False
                self.expand_btn.set_expanded(False)
                self.drawer_frame.hide()
                self.drawer_frame.setMaximumHeight(0)
            self.root_frame.hide()
            self.compact_frame.show()
        else:
            self.compact_frame.hide()
            self.root_frame.show()

        self.adjustSize()
        self.resize(self.sizeHint())

    def set_always_on_top(self, enabled: bool) -> None:
        """Toggle always-on-top window flag."""
        self.always_on_top = enabled
        self.settings["always_on_top"] = enabled
        save_settings({"always_on_top": enabled})

        pos = self.pos()
        self._init_window_flags()
        self.show()
        self.move(pos)

    def set_opacity_level(self, opacity: float) -> None:
        """Adjust HUD window opacity."""
        self.current_opacity = max(0.3, min(1.0, float(opacity)))
        self.setWindowOpacity(self.current_opacity)
        self.settings["opacity"] = self.current_opacity
        save_settings({"opacity": self.current_opacity})

    def toggle_alerts(self, enabled: bool) -> None:
        """Toggle low quota notifications."""
        self.alerts_enabled = enabled
        self.settings["alerts_enabled"] = enabled
        save_settings({"alerts_enabled": enabled})

    def confirm_reset_daily(self) -> None:
        """Prompt user confirmation and reset today's usage ledger."""
        reply = QMessageBox.question(
            self,
            "重設今日統計",
            "確定要重設今日的所有 Token 消耗記錄與統計金額嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            reset_today_usage()
            self.request_reset_daily.emit()
            self.request_rescan.emit()

    def show_details_dialog(self) -> None:
        """Show About / Version details dialog."""
        from ..config import APP_NAME, APP_VERSION
        QMessageBox.information(
            self,
            f"關於 {APP_NAME}",
            f"<b>{APP_NAME} v{APP_VERSION}</b><br><br>"
            "瑞士極簡深鈦精度 HUD (Swiss Precision Dark Titanium HUD)。<br>"
            "• 支援 Antigravity (AGY)、GitHub Copilot、Claude Code CLI、OpenAI Codex 四大多 CLI 配額監控<br>"
            "• 支援即時自訂切換與勾選僅顯示特定 CLI<br>"
            "• 5 小時滾動限制、Premium 請求、每週限制與月度預算精確倒數<br>"
            "• 純粹文字排版與幾何微標籤 (Zero Emoji Pure Typography)",
        )

    # ----------------- Window Position & Dragging -----------------
    def _restore_position(self) -> None:
        """Restore saved window screen coordinates or center at top of screen."""
        x = self.settings.get("window_x")
        y = self.settings.get("window_y")
        if x is not None and y is not None:
            self.move(int(x), int(y))
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                self.move(geom.center().x() - 170, 24)

    def _save_position(self) -> None:
        """Save current window position to settings."""
        self.settings["window_x"] = self.x()
        self.settings["window_y"] = self.y()
        save_settings({"window_x": self.x(), "window_y": self.y()})

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.mouse_pressed_pos = event.globalPosition().toPoint()
            self.drag_position = self.mouse_pressed_pos - self.frameGeometry().topLeft()
            self._press_in_capsule_bar = (
                not self.is_compact
                and hasattr(self, "capsule_bar")
                and self.capsule_bar.isVisible()
                and self.capsule_bar.geometry().contains(self.root_frame.mapFrom(self, event.pos()))
            )
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            dist = (event.globalPosition().toPoint() - self.mouse_pressed_pos).manhattanLength()
            if dist > 4:
                self.is_dragging = True
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                self.is_dragging = False
                self._save_position()
            else:
                if self._press_in_capsule_bar and not self.is_compact:
                    child = self.childAt(event.pos())
                    if child in (
                        self,
                        self.root_frame,
                        self.capsule_bar,
                        self.pulsing_dot,
                        self.div1,
                        self.div2,
                        self.circular_ring,
                        self.countdown_badge,
                        self.tpm_badge,
                    ):
                        self.toggle_drawer()
            self._press_in_capsule_bar = False
            event.accept()

    def contextMenuEvent(self, event) -> None:
        """Right-click context menu with Multi-CLI filtering and switching."""
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLESHEET)

        sync_act = menu.addAction("立即同步配額 (背景處理)")
        sync_act.triggered.connect(self.trigger_sync_now)

        manual_sync_act = menu.addAction("備援：手動修正配額...")
        manual_sync_act.triggered.connect(lambda: self.show_usage_sync_dialog(force_dialog=True))

        # Submenu: Switch Active CLI
        switch_menu = menu.addMenu("切換主顯示 CLI")
        for cli_id in ALL_CLIS:
            act = switch_menu.addAction(CLI_DISPLAY_NAMES.get(cli_id, cli_id.upper()))
            act.setCheckable(True)
            act.setChecked(self.multi_cli.active_cli == cli_id)
            act.triggered.connect(lambda _, c=cli_id: self.set_active_cli(c))

        # Submenu: Selective CLI Display Filters (Checkboxes)
        filter_menu = menu.addMenu("監控 CLI 項目 (自訂顯示)")
        for cli_id in ALL_CLIS:
            act = filter_menu.addAction(CLI_DISPLAY_NAMES.get(cli_id, cli_id.upper()))
            act.setCheckable(True)
            act.setChecked(self.multi_cli.is_cli_enabled(cli_id))
            act.triggered.connect(lambda _, c=cli_id: self.toggle_cli_enabled(c))

        # AGY sub-group switch
        other_grp = "CLAUDE AND GPT" if self.multi_cli.agy.active_group == GROUP_GEMINI else "GEMINI"
        grp_act = menu.addAction(f"切換 AGY 內部群組至 {other_grp}")
        grp_act.triggered.connect(self.toggle_active_group)

        mode_act = menu.addAction("切換完整 / 極簡模式")
        mode_act.triggered.connect(self.toggle_compact_mode)

        theme_menu = menu.addMenu("介面風格 (Theme)")
        theme_group = QActionGroup(theme_menu)
        hud_act = QAction("深鈦極簡 HUD (Obsidian)", theme_menu)
        hud_act.setCheckable(True)
        hud_act.setChecked(self.ui_theme == "obsidian")
        hud_act.triggered.connect(lambda: self.set_ui_theme("obsidian"))
        ticket_act = QAction("復古票券卡片 (Retro Ticket)", theme_menu)
        ticket_act.setCheckable(True)
        ticket_act.setChecked(self.ui_theme == "ticket")
        ticket_act.triggered.connect(lambda: self.set_ui_theme("ticket"))
        theme_group.addAction(hud_act)
        theme_group.addAction(ticket_act)
        theme_menu.addAction(hud_act)
        theme_menu.addAction(ticket_act)

        drawer_act = menu.addAction("展開 / 摺疊 Mini-Dashboard 抽屜")
        drawer_act.triggered.connect(self.toggle_drawer)

        menu.addSeparator()

        top_act = menu.addAction("視窗置頂 (Always on Top)")
        top_act.setCheckable(True)
        top_act.setChecked(self.always_on_top)
        top_act.triggered.connect(lambda: self.set_always_on_top(not self.always_on_top))

        # Opacity submenu
        opacity_menu = menu.addMenu("視窗不透明度")
        opacity_group = QActionGroup(opacity_menu)
        for pct in (100, 96, 88, 75, 60):
            val = pct / 100.0
            act = QAction(f"{pct}%", opacity_menu)
            act.setCheckable(True)
            act.setChecked(abs(self.current_opacity - val) < 0.04)
            act.triggered.connect(lambda _, v=val: self.set_opacity_level(v))
            opacity_group.addAction(act)
            opacity_menu.addAction(act)

        menu.addSeparator()

        rescan_act = menu.addAction("立即重新整理日誌")
        rescan_act.triggered.connect(self.request_rescan.emit)

        about_act = menu.addAction("關於程式")
        about_act.triggered.connect(self.show_details_dialog)

        menu.addSeparator()

        hide_act = menu.addAction("隱藏至系統匣")
        hide_act.triggered.connect(self.request_hide_to_tray.emit)

        exit_act = menu.addAction("結束程式")
        exit_act.triggered.connect(self.request_exit.emit)

        menu.exec(event.globalPos())
