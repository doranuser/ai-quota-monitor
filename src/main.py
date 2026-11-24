"""
Main application entry point for AGY Token Monitor.
Initializes QApplication, System Tray, Floating Capsule HUD, and Log Watcher.
Features Multi-CLI (AGY, Copilot, Claude Code, Codex) Quota Monitoring, custom icon and Windows desktop integration.
Pure Typographic & Geometric Design (Zero Emoji).
"""

import logging
import os
from pathlib import Path
import signal
import sys
from typing import Set

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set Windows App User Model ID so the taskbar displays custom icon rather than python.exe
if sys.platform == "win32":
    try:
        import ctypes
        from src.config import APP_USER_MODEL_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

from PySide6.QtCore import QLockFile, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from src.config import (
    APP_NAME,
    APP_VERSION,
    APP_ICON_ICO,
    APP_ICON_PNG,
    load_settings,
    save_settings,
    reset_today_usage,
    load_multi_cli_state,
)
from src.monitor.log_watcher import LogWatcher
from src.monitor.adaptive_poller import AdaptivePoller
from src.monitor.cli_runner import AGY_EXECUTABLE
from src.monitor.multi_cli_parser import (
    ALL_CLIS,
    CLI_AGY,
    CLI_COPILOT,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_DISPLAY_NAMES,
    CLI_SHORT_NAMES,
    GROUP_GEMINI,
    GROUP_CLAUDE_GPT,
)
from src.monitor.token_parser import SessionTokenStats, TokenParser
from src.ui.floating_capsule import FloatingCapsuleWidget
from src.ui.style import MENU_STYLESHEET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agy_monitor")


class AlertManager:
    """
    Manages notifications and threshold triggers for Multi-CLI Quotas (AGY, Copilot, Claude Code, Codex) and Context Limits.
    Pure typography, zero emoji.
    """

    def __init__(self):
        self.notified_gemini_thresholds: Set[int] = set()
        self.notified_claude_thresholds: Set[int] = set()
        self.notified_copilot_thresholds: Set[int] = set()
        self.notified_claude_code_thresholds: Set[int] = set()
        self.notified_codex_thresholds: Set[int] = set()
        self.notified_context_thresholds: Set[int] = set()
        self.current_session_id: str = ""

    def reset_session(self, new_session_id: str = "") -> None:
        """Reset session-specific alert flags."""
        self.notified_context_thresholds.clear()
        self.current_session_id = new_session_id

    def reset_daily(self) -> None:
        """Reset quota threshold alert flags."""
        self.notified_gemini_thresholds.clear()
        self.notified_claude_thresholds.clear()
        self.notified_copilot_thresholds.clear()
        self.notified_claude_code_thresholds.clear()
        self.notified_codex_thresholds.clear()

    def check_and_notify(self, stats: SessionTokenStats, tray_icon: QSystemTrayIcon) -> None:
        """Evaluate multi-CLI thresholds and trigger system tray messages when crossed."""
        settings = load_settings()
        if not settings.get("alerts_enabled", True):
            return

        if stats.session_id != self.current_session_id:
            self.reset_session(stats.session_id)

        raw_thresholds = settings.get("alert_thresholds", [20, 10, 0])
        thresholds = sorted([int(t) for t in raw_thresholds if t <= 50])
        if not thresholds:
            thresholds = [0, 10, 20]

        multi = stats.multi_cli

        # 1. Antigravity Gemini 5-Hour Quota
        if CLI_AGY in multi.enabled_clis:
            gemini_5h_pct = multi.agy.gemini.five_hour.percent
            for t in thresholds:
                if gemini_5h_pct <= float(t) and t not in self.notified_gemini_thresholds:
                    if t == 0 or gemini_5h_pct <= 0:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = "AGY Gemini 5小時額度已耗盡 (0% 剩餘)"
                        msg = f"Gemini 5小時額度已耗盡！\n• 刷新倒數: {multi.agy.gemini.five_hour.formatted_countdown()}\n建議切換至 Copilot 或 Claude Code！"
                    elif t <= 10:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = f"AGY Gemini 5小時額度嚴重不足 ({gemini_5h_pct:.1f}%)"
                        msg = f"Gemini 5小時可用配額低於 10%！\n• 刷新倒數: {multi.agy.gemini.five_hour.formatted_countdown()}\n建議切換至其他 CLI 備用！"
                    else:
                        icon_type = QSystemTrayIcon.MessageIcon.Warning
                        title = f"AGY Gemini 5小時額度即將見底 ({gemini_5h_pct:.1f}%)"
                        msg = f"Gemini 5小時可用配額低於 20%！\n• 刷新倒數: {multi.agy.gemini.five_hour.formatted_countdown()}"

                    tray_icon.showMessage(title, msg, icon_type, 6000)
                    for higher_t in thresholds:
                        if higher_t >= t:
                            self.notified_gemini_thresholds.add(higher_t)
                    break

        # 2. Antigravity Claude/GPT 5-Hour Quota
        if CLI_AGY in multi.enabled_clis:
            claude_gpt_5h_pct = multi.agy.claude_gpt.five_hour.percent
            for t in thresholds:
                if claude_gpt_5h_pct <= float(t) and t not in self.notified_claude_thresholds:
                    if t == 0 or claude_gpt_5h_pct <= 0:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = "AGY Claude/GPT 5小時額度已耗盡 (0% 剩餘)"
                        msg = f"Claude/GPT 5小時額度已耗盡！\n• 刷新倒數: {multi.agy.claude_gpt.five_hour.formatted_countdown()}\n建議切換至 Gemini 或其他 CLI！"
                    elif t <= 10:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = f"AGY Claude/GPT 5小時額度嚴重不足 ({claude_gpt_5h_pct:.1f}%)"
                        msg = f"Claude/GPT 5小時可用配額低於 10%！\n• 刷新倒數: {multi.agy.claude_gpt.five_hour.formatted_countdown()}\n建議切換至 Gemini 備用！"
                    else:
                        icon_type = QSystemTrayIcon.MessageIcon.Warning
                        title = f"AGY Claude/GPT 5小時額度即將見底 ({claude_gpt_5h_pct:.1f}%)"
                        msg = f"Claude/GPT 5小時可用配額低於 20%！\n• 刷新倒數: {multi.agy.claude_gpt.five_hour.formatted_countdown()}"

                    tray_icon.showMessage(title, msg, icon_type, 6000)
                    for higher_t in thresholds:
                        if higher_t >= t:
                            self.notified_claude_thresholds.add(higher_t)
                    break

        # 3. GitHub Copilot Premium Quota
        if CLI_COPILOT in multi.enabled_clis:
            cop_prem_pct = multi.copilot.premium_requests.percent
            for t in thresholds:
                if cop_prem_pct <= float(t) and t not in self.notified_copilot_thresholds:
                    if t == 0 or cop_prem_pct <= 0:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = "Copilot Premium 快速額度已耗盡 (0% 剩餘)"
                        msg = f"GitHub Copilot Premium 請求已達上限！\n• 刷新倒數: {multi.copilot.premium_requests.formatted_countdown()}\n建議切換至 AGY 或 Claude Code！"
                    else:
                        icon_type = QSystemTrayIcon.MessageIcon.Warning
                        title = f"Copilot Premium 額度低於 {t}% (剩餘 {cop_prem_pct:.1f}%)"
                        msg = f"Copilot 剩餘 {int(multi.copilot.premium_requests.remaining_units or 0)}/{int(multi.copilot.premium_requests.total_units or 300)} 請求\n• 刷新倒數: {multi.copilot.premium_requests.formatted_countdown()}"

                    tray_icon.showMessage(title, msg, icon_type, 6000)
                    for higher_t in thresholds:
                        if higher_t >= t:
                            self.notified_copilot_thresholds.add(higher_t)
                    break

        # 3. Claude Code CLI 5-Hour Window
        if CLI_CLAUDE_CODE in multi.enabled_clis:
            cc_5h_pct = multi.claude.five_hour.percent
            for t in thresholds:
                if cc_5h_pct <= float(t) and t not in self.notified_claude_code_thresholds:
                    if t == 0 or cc_5h_pct <= 0:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = "Claude Code 5小時窗口額度已耗盡"
                        msg = f"Claude Code 5小時窗口已耗盡！\n• 刷新倒數: {multi.claude.five_hour.formatted_countdown()}"
                    else:
                        icon_type = QSystemTrayIcon.MessageIcon.Warning
                        title = f"Claude Code 5小時額度低於 {t}% (剩餘 {cc_5h_pct:.1f}%)"
                        msg = f"Claude Code 窗口剩餘 {cc_5h_pct:.1f}%\n• 刷新倒數: {multi.claude.five_hour.formatted_countdown()}"

                    tray_icon.showMessage(title, msg, icon_type, 6000)
                    for higher_t in thresholds:
                        if higher_t >= t:
                            self.notified_claude_code_thresholds.add(higher_t)
                    break

        # 4. OpenAI Codex 5-Hour Window
        if CLI_CODEX in multi.enabled_clis:
            codex_5h_pct = multi.codex.five_hour.percent
            for t in thresholds:
                if codex_5h_pct <= float(t) and t not in self.notified_codex_thresholds:
                    if t == 0 or codex_5h_pct <= 0:
                        icon_type = QSystemTrayIcon.MessageIcon.Critical
                        title = "Codex 5小時窗口額度已耗盡"
                        msg = f"OpenAI Codex 5小時窗口已耗盡！\n• 刷新倒數: {multi.codex.five_hour.formatted_countdown()}"
                    else:
                        icon_type = QSystemTrayIcon.MessageIcon.Warning
                        title = f"Codex 5小時額度低於 {t}% (剩餘 {codex_5h_pct:.1f}%)"
                        msg = f"Codex 窗口剩餘 {codex_5h_pct:.1f}%\n• 刷新倒數: {multi.codex.five_hour.formatted_countdown()}"

                    tray_icon.showMessage(title, msg, icon_type, 6000)
                    for higher_t in thresholds:
                        if higher_t >= t:
                            self.notified_codex_thresholds.add(higher_t)
                    break

        # 4. Context Window Low Remaining Warning
        if stats.remaining_context_percent <= 10.0 and 90 not in self.notified_context_thresholds:
            tray_icon.showMessage(
                "當前模型 Context 容量即將耗盡",
                f"當前 Session 佔用已達 {stats.context_percent:.1f}%\n"
                f"• 剩餘空間: {TokenParser.format_number(stats.remaining_context_tokens)} / {TokenParser.format_number(stats.context_limit)} Tokens\n"
                f"• 模型: {stats.current_model}",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )
            self.notified_context_thresholds.add(90)


def create_tray_icon_pixmap() -> QIcon:
    """Return high-resolution icon if available, or generate procedural vector-like tray icon."""
    if APP_ICON_ICO.exists():
        return QIcon(str(APP_ICON_ICO))
    elif APP_ICON_PNG.exists():
        return QIcon(str(APP_ICON_PNG))

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark round background
    painter.setBrush(QColor(18, 21, 28))
    painter.setPen(QColor(138, 180, 248))
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    # Inner bright accent dot
    painter.setBrush(QColor(16, 185, 129))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(12, 12, 12, 12)

    # Text "AGY"
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 16, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, 10, 0, 0), Qt.AlignmentFlag.AlignCenter, "AGY")

    painter.end()
    return QIcon(pixmap)


def main():
    """Application main entry point."""
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)

    # Prevent an older/background copy from racing on the shared state file.
    instance_lock = QLockFile(str(Path.home() / ".agy_token_monitor.lock"))
    if not instance_lock.tryLock(100):
        QMessageBox.information(
            None,
            APP_NAME,
            "AGY Token Monitor 已在背景執行。請從系統匣開啟現有視窗。",
        )
        return

    # Apply global app icon
    app_icon = create_tray_icon_pixmap()
    app.setWindowIcon(app_icon)

    # Create Alert Manager
    alert_mgr = AlertManager()

    # Create Floating Widget
    capsule = FloatingCapsuleWidget()

    # Create System Tray
    tray_icon = QSystemTrayIcon(app_icon, app)
    tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION} - 多 CLI 配額監控")

    tray_menu = QMenu()
    tray_menu.setStyleSheet(MENU_STYLESHEET)

    toggle_action = tray_menu.addAction("顯示 / 隱藏懸浮窗")
    toggle_action.triggered.connect(
        lambda: capsule.hide() if capsule.isVisible() else (capsule.show(), capsule.raise_())
    )

    sync_action = tray_menu.addAction("立即同步配額 (背景處理)")
    sync_action.triggered.connect(capsule.trigger_sync_now)

    manual_sync_action = tray_menu.addAction("備援：手動修正配額...")
    manual_sync_action.triggered.connect(lambda: capsule.show_usage_sync_dialog(force_dialog=True))

    # Submenu: Switch Active CLI
    switch_cli_menu = tray_menu.addMenu("切換主顯示 CLI")
    switch_cli_actions = {}
    for cli_id in ALL_CLIS:
        act = switch_cli_menu.addAction(CLI_DISPLAY_NAMES.get(cli_id, cli_id.upper()))
        act.setCheckable(True)
        act.setChecked(capsule.multi_cli.active_cli == cli_id)
        act.triggered.connect(lambda _, c=cli_id: capsule.set_active_cli(c))
        switch_cli_actions[cli_id] = act

    # Submenu: Selective CLI Display Filters
    filter_cli_menu = tray_menu.addMenu("監控 CLI 項目 (自訂顯示)")
    filter_cli_actions = {}
    for cli_id in ALL_CLIS:
        act = filter_cli_menu.addAction(CLI_DISPLAY_NAMES.get(cli_id, cli_id.upper()))
        act.setCheckable(True)
        act.setChecked(capsule.multi_cli.is_cli_enabled(cli_id))
        act.triggered.connect(lambda _, c=cli_id: capsule.toggle_cli_enabled(c))
        filter_cli_actions[cli_id] = act

    mode_action = tray_menu.addAction("切換完整 / 極簡模式")
    mode_action.triggered.connect(capsule.toggle_compact_mode)

    # Submenu: UI Theme Switcher (Obsidian HUD vs Retro Ticket)
    theme_menu = tray_menu.addMenu("介面風格 (Theme)")
    theme_hud_act = theme_menu.addAction("深鈦極簡 HUD (Obsidian)")
    theme_hud_act.setCheckable(True)
    theme_hud_act.setChecked(capsule.ui_theme == "obsidian")
    theme_ticket_act = theme_menu.addAction("復古票券卡片 (Retro Ticket)")
    theme_ticket_act.setCheckable(True)
    theme_ticket_act.setChecked(capsule.ui_theme == "ticket")

    def _on_tray_theme(theme_name: str):
        capsule.set_ui_theme(theme_name)
        theme_hud_act.setChecked(theme_name == "obsidian")
        theme_ticket_act.setChecked(theme_name == "ticket")

    theme_hud_act.triggered.connect(lambda: _on_tray_theme("obsidian"))
    theme_ticket_act.triggered.connect(lambda: _on_tray_theme("ticket"))

    alert_action = tray_menu.addAction("額度即將耗盡警報")
    alert_action.setCheckable(True)
    settings = load_settings()
    alert_action.setChecked(settings.get("alerts_enabled", True))

    def on_toggle_alert(checked: bool):
        capsule.toggle_alerts(checked)

    alert_action.toggled.connect(on_toggle_alert)

    tray_menu.addSeparator()

    shortcut_action = tray_menu.addAction("建立桌面捷徑 (Desktop Shortcut)")
    def on_create_shortcut():
        import subprocess
        ps_script = PROJECT_ROOT / "create_desktop_shortcut.ps1"
        if ps_script.exists():
            cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)], capture_output=True, creationflags=cflags)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(capsule, "桌面捷徑", "已在桌面成功建立「AGY Quota Monitor」專屬圖示捷徑！")
    shortcut_action.triggered.connect(on_create_shortcut)

    budget_action = tray_menu.addAction("修改每日總配額/預算...")
    budget_action.triggered.connect(capsule.show_budget_dialog)

    reset_daily_action = tray_menu.addAction("重設今日統計")
    reset_daily_action.triggered.connect(capsule.confirm_reset_daily)

    rescan_action = tray_menu.addAction("立即重新整理所有日誌")

    tray_menu.addSeparator()

    about_action = tray_menu.addAction(f"關於 {APP_NAME}")
    about_action.triggered.connect(capsule.show_details_dialog)

    tray_menu.addSeparator()

    exit_action = tray_menu.addAction("結束程式")
    exit_action.triggered.connect(app.quit)

    def _sync_tray_menu_checks() -> None:
        for cid, act in switch_cli_actions.items():
            act.setChecked(capsule.multi_cli.active_cli == cid)
        for cid, act in filter_cli_actions.items():
            act.setChecked(capsule.multi_cli.is_cli_enabled(cid))
        theme_hud_act.setChecked(capsule.ui_theme == "obsidian")
        theme_ticket_act.setChecked(capsule.ui_theme == "ticket")
        alert_action.setChecked(capsule.alerts_enabled)

    tray_menu.aboutToShow.connect(_sync_tray_menu_checks)
    tray_icon.setContextMenu(tray_menu)

    def on_tray_activated(reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if capsule.isVisible():
                capsule.hide()
            else:
                capsule.show()
                capsule.raise_()
                capsule.activateWindow()

    tray_icon.activated.connect(on_tray_activated)
    tray_icon.show()

    # Setup Log Watcher
    custom_brain = settings.get("custom_brain_dir")
    brain_dir = Path(custom_brain) if custom_brain else None

    watcher = LogWatcher(brain_dir=brain_dir)
    rescan_action.triggered.connect(watcher.check_updates)
    capsule.request_rescan.connect(watcher.check_updates)
    capsule.request_exit.connect(app.quit)
    capsule.request_hide_to_tray.connect(capsule.hide)
    capsule.request_reset_daily.connect(alert_mgr.reset_daily)
    watcher.session_changed.connect(lambda sid, path: alert_mgr.reset_session(sid))

    def on_stats_updated(stats: SessionTokenStats):
        capsule.update_stats(stats)
        alert_mgr.check_and_notify(stats, tray_icon)

        multi = stats.multi_cli
        g_5h = multi.agy.gemini.five_hour
        cop_prem = multi.copilot.premium_requests
        cc_5h = multi.claude.five_hour
        codex_5h = multi.codex.five_hour

        tray_tip = (
            f"{APP_NAME} v{APP_VERSION} - 多 CLI 配額監控\n"
            f"• AGY (Gemini): 5h {g_5h.percent:.1f}% ({g_5h.formatted_countdown()})\n"
            f"• COPILOT: {cop_prem.percent:.1f}% ({cop_prem.formatted_countdown()})\n"
            f"• CLAUDE: 5h {cc_5h.percent:.1f}% ({cc_5h.formatted_countdown()})\n"
            f"• CODEX: 5h {codex_5h.percent:.1f}% ({codex_5h.formatted_countdown()})\n"
            f"• 當前主視窗: {multi.get_active_display_name()}"
        )
        tray_icon.setToolTip(tray_tip)

    watcher.stats_updated.connect(on_stats_updated)

    # Show capsule immediately so startup feels instant, then start watcher/poller
    capsule.show()
    QTimer.singleShot(30, lambda: watcher.start(interval_ms=settings.get("refresh_interval_ms", 1000)))

    # ── Adaptive Poller ──────────────────────────────────────────────────────
    poller = AdaptivePoller()

    def on_usage_updated(raw_text: str) -> None:
        """Parse the raw /usage text and push the new quota state into the UI."""
        try:
            from src.monitor.quota_parser import UsageParser
            from src.config import save_multi_cli_state
            capsule.multi_cli.agy = UsageParser.parse(raw_text, capsule.multi_cli.agy)
            capsule.dual_quota = capsule.multi_cli.agy
            save_multi_cli_state(capsule.multi_cli)
            if hasattr(capsule, "refresh_ui"):
                capsule.refresh_ui()
            elif capsule.current_stats:
                capsule.current_stats.multi_cli = capsule.multi_cli
                capsule.current_stats.dual_quota = capsule.multi_cli.agy
                capsule.update_stats(capsule.current_stats)
            else:
                capsule._update_drawer_ui()
            if hasattr(capsule, "on_sync_finished"):
                capsule.on_sync_finished(True)
            logger.info("Adaptive poller synced /usage successfully.")
        except Exception as exc:
            logger.error("Failed to parse auto-synced /usage output: %s", exc)
            if hasattr(capsule, "on_sync_finished"):
                capsule.on_sync_finished(False)

    def on_sync_status(status: str) -> None:
        """Push the sync status string to the drawer status bar."""
        if hasattr(capsule, "set_sync_status"):
            capsule.set_sync_status(status)

    def on_sync_failed(count: int) -> None:
        if hasattr(capsule, "on_sync_finished"):
            capsule.on_sync_finished(False)
        if count >= AdaptivePoller.MAX_FAILURES:
            tray_icon.showMessage(
                APP_NAME,
                f"AUTO-SYNC FAILED {count} times. Switching to manual mode.\nUse SYNC /usage in the widget.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )

    def on_stats_for_poller(stats: SessionTokenStats) -> None:
        """Feed current quota health to the poller so it can adjust interval."""
        try:
            multi = stats.multi_cli
            pcts = [
                multi.agy.gemini.five_hour.percent,
                multi.agy.claude_gpt.five_hour.percent,
                multi.copilot.premium_requests.percent,
                multi.claude.five_hour.percent,
                multi.codex.five_hour.percent,
            ]
            min_pct = min(pcts)
            poller.update_state(min_pct, is_active=stats.is_generating)
        except Exception:
            pass

    poller.usage_updated.connect(on_usage_updated)
    poller.sync_status.connect(on_sync_status)
    poller.sync_failed.connect(on_sync_failed)
    if hasattr(poller, "sync_completed") and hasattr(capsule, "on_sync_finished"):
        poller.sync_completed.connect(capsule.on_sync_finished)
    watcher.stats_updated.connect(on_stats_for_poller)
    capsule.request_rescan.connect(poller.force_sync)

    # Wire SYNC NOW button (if capsule exposes force_sync signal)
    if hasattr(capsule, "request_force_sync"):
        capsule.request_force_sync.connect(poller.force_sync)

    poller.start()

    # Emit initial auto-sync availability status
    if AGY_EXECUTABLE:
        if hasattr(capsule, "set_sync_status"):
            capsule.set_sync_status("AUTO-SYNC ON  |  Starting first sync...")
        logger.info("Auto-sync enabled. agy found at: %s", AGY_EXECUTABLE)
    else:
        if hasattr(capsule, "set_sync_status"):
            capsule.set_sync_status("AUTO-SYNC UNAVAILABLE  |  [ FALLBACK SYNC AVAILABLE ]")
        logger.warning("agy not found in PATH. Auto-sync disabled.")
    # ─────────────────────────────────────────────────────────────────────────

    # Graceful shutdown cleanup
    def cleanup():
        logger.info("Stopping watcher and poller, exiting...")
        poller.stop()
        poller.wait(3000)
        watcher.stop()

    app.aboutToQuit.connect(cleanup)

    # Allow Python to catch SIGINT / Ctrl+C
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)
    signal.signal(signal.SIGINT, lambda *args: app.quit())

    logger.info(f"{APP_NAME} v{APP_VERSION} started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
