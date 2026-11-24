"""
Verification and automated test suite for AGY Token Monitor (Multi-CLI Architecture: AGY, Copilot, Claude Code).
Tests pricing, context limits, duration parsing, live countdown math,
Multi-CLI data models, selective display filtering, CLI quick switching,
Copilot & Claude Code text parsers, smart Multi-CLI alerts, custom vector widgets,
and PySide6 UI rendering.
"""

import sys
import time
import json
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    APP_NAME,
    APP_VERSION,
    get_model_pricing,
    get_model_context_limit,
    load_settings,
    save_settings,
    record_session_usage,
    get_today_usage,
    get_today_usage_detailed,
    reset_today_usage,
    load_multi_cli_state,
    save_multi_cli_state,
    load_dual_quota_state,
    save_dual_quota_state,
    MODEL_PRICING,
    MODEL_CONTEXT_LIMITS,
)
from src.monitor.multi_cli_parser import (
    ALL_CLIS,
    CLI_AGY,
    CLI_COPILOT,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_COMBINED,
    CLI_DISPLAY_NAMES,
    CLI_SHORT_NAMES,
    GROUP_GEMINI,
    GROUP_CLAUDE_GPT,
    QuotaWindow,
    ModelGroupQuota,
    AgyQuotaState,
    CopilotQuotaState,
    ClaudeCodeQuotaState,
    CodexUsageParser,
    MultiCliQuotaState,
    UsageParser,
    CopilotUsageParser,
    ClaudeCodeUsageParser,
    MultiCliParser,
    create_default_multi_cli_state,
    create_default_dual_quota_state,
    parse_duration_to_seconds,
    format_seconds_to_countdown,
)
from src.monitor.token_parser import TokenParser, SessionTokenStats, StepTokenInfo
from src.main import AlertManager
from PySide6.QtWidgets import QApplication
from src.ui.floating_capsule import FloatingCapsuleWidget, PulsingDot, ContextProgressWidget, UsageSyncDialog, BudgetDialog
from src.ui.widgets import (
    ChevronButton,
    CircularProgressRing,
    GeometricDot,
    GlowingPulseDot,
    MiniSparkline,
    GradientDivider,
    ModelPillBadge,
)


def test_pricing():
    print("Testing pricing resolution...")
    gemini_p = get_model_pricing("gemini-2.5-pro")
    assert gemini_p == (1.25, 5.00), f"Expected (1.25, 5.00), got {gemini_p}"

    claude_p = get_model_pricing("claude-3-7-sonnet")
    assert claude_p == (3.00, 15.00), f"Expected (3.00, 15.00), got {claude_p}"

    flash_p = get_model_pricing("gemini-2.5-flash-preview")
    assert flash_p == (0.075, 0.30), f"Expected (0.075, 0.30), got {flash_p}"
    print("Pricing resolution test passed!")


def test_context_limits():
    print("Testing context limit resolution...")
    assert get_model_context_limit("gemini-2.5-pro") == 2_000_000
    assert get_model_context_limit("gemini-2.5-flash") == 1_000_000
    assert get_model_context_limit("claude-3-7-sonnet") == 200_000
    assert get_model_context_limit("claude-3-5-haiku") == 200_000
    assert get_model_context_limit("gpt-4o") == 128_000
    assert get_model_context_limit("unknown-custom-model") == 1_000_000
    print("Context limit resolution test passed!")


def test_duration_parsing_and_countdown_math():
    print("Testing duration parsing and live countdown math (Zero-Emoji Pure Typography)...")
    # 1. parse_duration_to_seconds tests
    assert parse_duration_to_seconds("3h 10m") == 11400  # 3*3600 + 10*60
    assert parse_duration_to_seconds("111h 25m") == 401100  # 111*3600 + 25*60
    assert parse_duration_to_seconds("2d 5h") == 190800  # 2*86400 + 5*3600
    assert parse_duration_to_seconds("45m") == 2700
    assert parse_duration_to_seconds("2h 40m left") == 9600
    assert parse_duration_to_seconds("14d 6h") == 1231200
    assert parse_duration_to_seconds("OPTIMAL") == 0
    assert parse_duration_to_seconds("充足") == 0
    assert parse_duration_to_seconds("Full") == 0
    assert parse_duration_to_seconds("") == 0

    # 2. format_seconds_to_countdown tests
    assert format_seconds_to_countdown(11400) == "3h 10m"
    assert format_seconds_to_countdown(401100) == "111h 25m"
    assert format_seconds_to_countdown(2700) == "45m"
    assert format_seconds_to_countdown(0, is_full=True) == "OPTIMAL"
    assert format_seconds_to_countdown(0, is_full=False) == "0m"

    # 3. QuotaWindow live elapsed countdown tests
    base_time = 100000.0
    qw = QuotaWindow(
        name="5-Hour Limit",
        percent=78.5,
        initial_reset_seconds=9600,  # 2h 40m
        last_synced_time=base_time,
        is_full=False,
    )
    assert qw.get_remaining_seconds(current_time=base_time) == 9600
    assert qw.formatted_countdown(current_time=base_time) == "2h 40m"

    # After 10 mins (600s) -> 9000s (2h 30m)
    assert qw.get_remaining_seconds(current_time=base_time + 600) == 9000
    assert qw.formatted_countdown(current_time=base_time + 600) == "2h 30m"

    print("Duration parsing and countdown math tests passed!")


def test_multi_cli_parsers():
    print("Testing parsers for AGY, Copilot, and Claude Code CLI...")

    # 1. Copilot parser
    cop_text = """
    GITHUB COPILOT
    Premium Requests Remaining: 85.00% (255/300, Resets in 14d 6h)
    Rolling Rate Limit: 92.00% (Resets in 45m)
    """
    cop_state = CopilotUsageParser.parse(cop_text)
    assert abs(cop_state.premium_requests.percent - 85.0) < 0.01
    assert cop_state.premium_requests.remaining_units == 255.0
    assert cop_state.premium_requests.total_units == 300.0
    assert cop_state.premium_requests.initial_reset_seconds == 1231200
    assert abs(cop_state.rate_limit.percent - 92.0) < 0.01
    assert cop_state.rate_limit.initial_reset_seconds == 2700

    # 2. Claude Code parser
    claude_text = """
    CLAUDE CODE CLI
    5-Hour Window Remaining: 78.50% (Resets in 2h 40m)
    Monthly Budget Remaining: 91.20% ($91.20 / $100.00)
    """
    cc_state = ClaudeCodeUsageParser.parse(claude_text)
    assert abs(cc_state.five_hour.percent - 78.5) < 0.01
    assert cc_state.five_hour.initial_reset_seconds == 9600
    assert abs(cc_state.monthly_budget.percent - 91.2) < 0.01
    assert cc_state.monthly_budget.remaining_units == 91.20
    assert cc_state.monthly_budget.total_units == 100.0

    # 3. AGY parser
    agy_text = """
    GEMINI MODELS
    Five Hour Limit Remaining: 60.09% (Resets in 3h 10m)
    Weekly Limit Remaining: 93.25% (Resets in 111h 25m)

    CLAUDE AND GPT MODELS
    Five Hour Limit Remaining: 100.00%
    Weekly Limit Remaining: 100.00%
    """
    agy_state = UsageParser.parse(agy_text)
    assert abs(agy_state.gemini.five_hour.percent - 60.09) < 0.01
    assert abs(agy_state.gemini.weekly.percent - 93.25) < 0.01
    assert agy_state.claude_gpt.five_hour.percent == 100.0

    # 4. MultiCliParser unified parsing
    multi_text = f"{agy_text}\n\n{cop_text}\n\n{claude_text}"
    multi_state = MultiCliParser.parse(multi_text)
    assert abs(multi_state.agy.gemini.five_hour.percent - 60.09) < 0.01
    assert abs(multi_state.copilot.premium_requests.percent - 85.0) < 0.01
    assert abs(multi_state.claude.five_hour.percent - 78.5) < 0.01

    # 5. Codex local event parser: rate limits are reported as used %,
    # while the HUD consistently presents remaining %.
    codex_event = {
        "timestamp": "2026-09-19T05:00:00Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {
                "input_tokens": 1000,
                "output_tokens": 250,
                "cached_input_tokens": 100,
                "total_tokens": 1250,
            }},
            "rate_limits": {
                "primary": {"used_percent": 25.0, "window_minutes": 300, "resets_at": 1789814695},
                "secondary": {"used_percent": 75.0, "window_minutes": 10080, "resets_at": 1789894025},
                "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
                "plan_type": "plus",
            },
        },
    }
    codex_state = CodexUsageParser.parse(json.dumps(codex_event))
    assert abs(codex_state.five_hour.percent - 75.0) < 0.01
    assert abs(codex_state.weekly.percent - 25.0) < 0.01
    assert codex_state.plan_type == "plus"
    assert codex_state.total_tokens == 1250
    assert codex_state.auto_detected is True

    print("Multi-CLI parsers tests passed!")


def test_multi_cli_switching_and_filtering():
    print("Testing Multi-CLI switching, selective filtering, and persistence...")
    state = create_default_multi_cli_state()

    assert state.active_cli == CLI_AGY
    assert state.enabled_clis == [CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX]

    # Quick Switch cycling
    c1 = state.switch_next_cli()
    assert c1 == CLI_COPILOT
    assert state.get_active_short_name() == "COPILOT"
    assert state.get_active_theme_color() == "#58a6ff"

    c2 = state.switch_next_cli()
    assert c2 == CLI_CLAUDE_CODE
    assert state.get_active_short_name() == "CLAUDE"
    assert state.get_active_theme_color() == "#e57b39"

    c3 = state.switch_next_cli()
    assert c3 == CLI_CODEX
    c4 = state.switch_next_cli()
    assert c4 == CLI_AGY

    # Selective CLI Filtering
    # Disable Copilot
    state.set_cli_enabled(CLI_COPILOT, False)
    assert state.enabled_clis == [CLI_AGY, CLI_CLAUDE_CODE, CLI_CODEX]
    assert state.is_cli_enabled(CLI_COPILOT) is False
    assert state.is_cli_enabled(CLI_AGY) is True

    # Switching cycles only through enabled CLIs (AGY -> CLAUDE -> AGY)
    assert state.switch_next_cli() == CLI_CLAUDE_CODE
    assert state.switch_next_cli() == CLI_CODEX
    assert state.switch_next_cli() == CLI_AGY

    # Cannot disable all CLIs (at least one must stay)
    state.set_cli_enabled(CLI_CLAUDE_CODE, False)
    assert state.enabled_clis == [CLI_AGY, CLI_CODEX]
    state.set_cli_enabled(CLI_AGY, False)
    assert state.enabled_clis == [CLI_CODEX]
    state.set_cli_enabled(CLI_CODEX, False)
    assert state.enabled_clis == [CLI_CODEX]  # Guard keeps at least 1

    # Persistence
    state.set_active_cli(CLI_AGY)
    state.set_cli_enabled(CLI_COPILOT, True)
    state.set_cli_enabled(CLI_CLAUDE_CODE, True)
    save_multi_cli_state(state)
    loaded = load_multi_cli_state()
    assert loaded.active_cli == CLI_AGY
    assert CLI_COPILOT in loaded.enabled_clis
    assert CLI_CLAUDE_CODE in loaded.enabled_clis
    assert CLI_CODEX in loaded.enabled_clis

    print("Multi-CLI switching and filtering tests passed!")


def test_smart_alert_manager():
    print("Testing smart alert manager for Multi-CLI thresholds...")
    settings = load_settings()
    settings["alerts_enabled"] = True
    settings["alert_thresholds"] = [20, 10, 0]
    save_settings(settings)

    alert_mgr = AlertManager()
    alert_mgr.reset_session("session-alert-test")
    alert_mgr.reset_daily()

    class MockTrayIcon:
        def __init__(self):
            self.messages = []

        def showMessage(self, title, msg, icon, duration):
            self.messages.append((title, msg, icon))

    tray = MockTrayIcon()

    multi_state = create_default_multi_cli_state()
    stats = SessionTokenStats(
        session_id="session-alert-test",
        multi_cli=multi_state,
    )

    # 1. Normal safe state: no alert
    alert_mgr.check_and_notify(stats, tray)
    assert len(tray.messages) == 0

    # 2. Copilot drops below 20% (e.g. 15.0%) -> Warning
    stats.multi_cli.copilot.premium_requests.percent = 15.0
    alert_mgr.check_and_notify(stats, tray)
    assert len(tray.messages) == 1
    assert "Copilot" in tray.messages[0][0]

    # 3. Claude Code drops below 10% (e.g. 8.0%) -> Warning
    stats.multi_cli.claude.five_hour.percent = 8.0
    alert_mgr.check_and_notify(stats, tray)
    assert len(tray.messages) == 2
    assert "Claude Code" in tray.messages[1][0]

    print("Smart Multi-CLI alert manager tests passed!")


def test_vector_widgets():
    print("Testing custom vector widgets with Multi-CLI colors...")
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    # 1. CircularProgressRing with Copilot blue & Claude terracotta
    ring = CircularProgressRing(size=28, ring_width=2.5, show_text=True)
    ring.set_percent(85.0, animate=False, label="REQ", accent_color="#58a6ff")
    assert abs(ring.percent - 85.0) < 0.01
    assert ring._bottom_label == "REQ"
    assert ring._get_status_color(85.0).name() == "#58a6ff"

    ring.set_percent(78.5, animate=False, label="5H", accent_color="#e57b39")
    assert ring._get_status_color(78.5).name() == "#e57b39"

    # 2. GlowingPulseDot with copilot and claude states
    dot = GlowingPulseDot(size=6)
    dot.set_state(is_generating=True, status="copilot")
    assert dot._get_base_color().name() == "#58a6ff"

    dot.set_state(is_generating=True, status="claude")
    assert dot._get_base_color().name() == "#e57b39"

    # 3. MiniSparkline & ChevronButton
    spark = MiniSparkline(width=100, height=20, line_color="#58a6ff")
    spark.add_point(15000)
    assert spark.data_points[0] == 15000.0

    chevron = ChevronButton()
    chevron.set_expanded(True)
    assert chevron.is_expanded() is True

    print("Custom vector widgets tests passed!")


def test_ui_widget():
    print("Testing PySide6 UI Multi-CLI HUD, Dynamic Drawer Cards, and Quick Switcher in offscreen mode...")
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    widget = FloatingCapsuleWidget()
    assert widget is not None
    widget.set_ui_theme("obsidian")

    multi_state = create_default_multi_cli_state()
    stats = SessionTokenStats(
        session_id="multi-unit-test-session",
        total_tokens=45000,
        multi_cli=multi_state,
        tpm=12000,
        is_generating=False,
    )
    widget.update_stats(stats)

    # 1. Verify Header HUD for AGY
    assert "GEMINI: 60.1%" in widget.group_quota_label.text()
    assert widget.countdown_badge.text() == "3h 10m"
    assert widget.group_switch_btn.text() == "AGY"

    # 2. Verify Drawer Cards are enabled/configured
    assert not widget.agy_card.isHidden()
    assert not widget.copilot_card.isHidden()
    assert not widget.claude_code_card.isHidden()
    assert not widget.codex_card.isHidden()
    assert "85.00%" in widget.copilot_prem_val.text()
    assert "78.50%" in widget.claude_code_5h_val.text()

    # 3. Test Quick Switcher Button -> COPILOT
    widget.switch_next_cli()
    assert widget.multi_cli.active_cli == CLI_COPILOT
    assert "COPILOT: 85.0%" in widget.group_quota_label.text()
    assert widget.group_quota_sub.text() == "PREMIUM REQUESTS"
    assert widget.countdown_badge.text() in ("342h 0m", "14d 6h")
    assert widget.group_switch_btn.text() == "COPILOT"

    # 4. Test Quick Switcher Button -> CLAUDE
    widget.switch_next_cli()
    assert widget.multi_cli.active_cli == CLI_CLAUDE_CODE
    assert "CLAUDE: 78.5%" in widget.group_quota_label.text()
    assert widget.group_quota_sub.text() == "5-HR ROLLING WINDOW"
    assert widget.countdown_badge.text() == "2h 40m"
    assert widget.group_switch_btn.text() == "CLAUDE"

    # 5. Test Codex quick switch and local-usage card
    widget.switch_next_cli()
    assert widget.multi_cli.active_cli == CLI_CODEX
    assert "CODEX: 100.0%" in widget.group_quota_label.text()
    assert widget.group_quota_sub.text() == "5-HR ROLLING WINDOW"
    assert widget.codex_card.isHidden() is False

    # 6. Test Selective CLI Filtering (Disable Copilot)
    widget.toggle_cli_enabled(CLI_COPILOT)
    assert widget.multi_cli.is_cli_enabled(CLI_COPILOT) is False
    assert widget.copilot_card.isHidden() is True
    assert widget.agy_card.isHidden() is False
    assert widget.claude_code_card.isHidden() is False

    # 7. Test Drawer Expansion
    assert widget.is_drawer_expanded is False
    widget.toggle_drawer()
    assert widget.is_drawer_expanded is True
    assert widget.expand_btn.is_expanded() is True
    assert not widget.drawer_frame.isHidden()
    widget.toggle_drawer()
    assert widget.is_drawer_expanded is False

    # 8. Test Compact Mode Toggle
    widget.toggle_compact_mode()
    assert widget.is_compact is True
    widget.toggle_compact_mode()
    assert widget.is_compact is False

    # 9. Test UsageSyncDialog Multi-Tab Initialization
    sync_dlg = UsageSyncDialog(current_multi_state=multi_state, default_target=CLI_COPILOT)
    assert sync_dlg is not None
    assert sync_dlg.target_cli == CLI_COPILOT
    assert "GITHUB COPILOT" in sync_dlg.text_edit.toPlainText()

    print("UI Multi-CLI tests passed!")


def test_instant_sync_and_smart_group_switching():
    print("Testing instant sync feedback, UI refresh, and smart model group switching with alerts...")
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    widget = FloatingCapsuleWidget()
    assert widget is not None
    widget.set_ui_theme("obsidian")

    # 1. Test SYNC NOW button immediate feedback
    widget.trigger_sync_now()
    assert widget.btn_sync_now.text() == "SYNCING..."
    assert widget.btn_sync_now.isEnabled() is False
    assert "SYNCING..." in widget.sync_status_label.text()

    # 2. Test SYNC FINISHED state
    widget.on_sync_finished(success=True)
    assert widget.btn_sync_now.text() == "SYNCED"

    # Reset button test
    widget._reset_sync_button()
    assert widget.btn_sync_now.text() == "SYNC NOW"
    assert widget.btn_sync_now.isEnabled() is True

    # 3. Simulate parsing raw /usage output where Claude is 0% and Gemini is 91%
    raw_usage = (
        "Gemini Models\tWeekly Limit Remaining\t82%\t2026-08-21T02:19:42Z\n"
        "Gemini Models\tFive Hour Limit Remaining\t91%\t2026-08-16T19:04:10Z\n"
        "Claude and GPT models\tWeekly Limit Remaining\t66%\t2026-08-23T12:47:37Z\n"
        "Claude and GPT models\tFive Hour Limit Remaining\t0%\t2026-08-16T17:47:37Z"
    )
    widget.multi_cli.agy = UsageParser.parse(raw_usage, widget.multi_cli.agy)
    widget.multi_cli.active_cli = CLI_AGY
    widget.multi_cli.agy.active_group = GROUP_GEMINI
    save_multi_cli_state(widget.multi_cli)
    save_dual_quota_state(widget.multi_cli.agy)

    # Force instant UI refresh
    widget.refresh_ui()

    # Verify Gemini is active with 91.0% in header and drawer
    assert "GEMINI: 91.0%" in widget.group_quota_label.text()
    assert abs(widget.circular_ring.percent - 91.0) < 0.01
    assert "91.00%" in widget.gemini_5h_val.text()
    assert "0.00% [EMPTY]" in widget.claude_5h_val.text()

    # Verify Smart Alert logic: Claude is 0%, so status dot must be 'danger' (red alert)
    assert widget.pulsing_dot.status == "danger"
    assert "CLAUDE: 0% 耗盡" in widget.group_quota_sub.text()

    # 4. Test instant 1-click group switching between Gemini and Claude (0%)
    widget.toggle_active_group()
    assert widget.multi_cli.agy.active_group == GROUP_CLAUDE_GPT
    assert "CLAUDE: 0.0%" in widget.group_quota_label.text()
    assert abs(widget.circular_ring.percent - 0.0) < 0.01
    assert "GEMINI: 91%" in widget.group_quota_sub.text()

    # Switch back via explicit helper
    widget.set_active_agy_group(GROUP_GEMINI)
    assert widget.multi_cli.agy.active_group == GROUP_GEMINI
    assert "GEMINI: 91.0%" in widget.group_quota_label.text()

    # 5. Test UsageSyncDialog instant acceptance & refresh
    sync_dlg = UsageSyncDialog(current_multi_state=widget.multi_cli, default_target=CLI_AGY)
    sync_dlg.text_edit.setPlainText(
        "GEMINI MODELS\nFive Hour Limit Remaining: 95.50%\nWeekly Limit Remaining: 99.00%\n\n"
        "CLAUDE AND GPT MODELS\nFive Hour Limit Remaining: 50.00%\nWeekly Limit Remaining: 80.00%"
    )
    sync_dlg._parse_and_accept()
    assert sync_dlg.synced_multi_state is not None
    assert abs(sync_dlg.synced_multi_state.agy.gemini.five_hour.percent - 95.5) < 0.01

    widget.multi_cli = sync_dlg.synced_multi_state
    widget.refresh_ui()
    assert "GEMINI: 95.5%" in widget.group_quota_label.text()
    assert abs(widget.circular_ring.percent - 95.5) < 0.01

    print("Instant sync and smart group switching tests passed!")


def test_sync_button_timeout_recovery():
    print("Testing sync button timeout recovery...")
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    widget = FloatingCapsuleWidget()
    assert widget is not None
    widget.set_ui_theme("obsidian")

    widget.trigger_sync_now()
    request_id = widget._sync_request_id
    assert widget.btn_sync_now.text() == "SYNCING..."
    assert widget.btn_sync_now.isEnabled() is False

    widget._handle_sync_timeout(request_id)
    assert widget.btn_sync_now.text() == "FAILED"
    assert "TIMEOUT" in widget.sync_status_label.text()

    widget._reset_sync_button()
    assert widget.btn_sync_now.text() == "SYNC NOW"
    assert widget.btn_sync_now.isEnabled() is True

    print("Sync button timeout recovery test passed!")


def test_periodic_stats_preserves_active_cli():
    print("Testing that periodic stats cannot reset the selected CLI...")
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])

    widget = FloatingCapsuleWidget()
    widget.multi_cli = create_default_multi_cli_state()
    widget.multi_cli.set_active_cli(CLI_CODEX)
    widget.refresh_ui()

    stale_stats = SessionTokenStats(
        session_id="stale-periodic-update",
        multi_cli=create_default_multi_cli_state(),
    )
    assert stale_stats.multi_cli.active_cli == CLI_AGY

    widget.update_stats(stale_stats)

    assert widget.multi_cli.active_cli == CLI_CODEX
    assert stale_stats.multi_cli.active_cli == CLI_CODEX
    assert widget.group_switch_btn.text() == "CODEX"
    print("Periodic stats selection preservation test passed!")


def test_historical_usage_ledger_and_ticket_theme():
    print("Testing 30-day local usage ledger and Retro Ticket Card theme...")
    import datetime
    from src.config import (
        get_usage_history_summary,
        record_cli_session_usage,
        record_session_usage,
    )

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    earlier = today - datetime.timedelta(days=10)

    record_session_usage("ticket-test-today", 25_813_887, 17.93, date_str=today.isoformat(), cli_id=CLI_AGY)
    record_session_usage("ticket-test-yest", 39_725_768, 26.84, date_str=yesterday.isoformat(), cli_id=CLI_AGY)
    record_cli_session_usage(CLI_CLAUDE_CODE, "cc-s1", 1_200_000, 4.50, date_str=earlier.isoformat())

    agy_sum = get_usage_history_summary(cli_id=CLI_AGY)
    assert agy_sum["today_tokens"] >= 25_813_887
    assert agy_sum["yesterday_tokens"] >= 39_725_768
    assert agy_sum["last_30_days_tokens"] >= 65_539_655
    assert len(agy_sum["daily_series"]) == 30

    cc_sum = get_usage_history_summary(cli_id=CLI_CLAUDE_CODE)
    assert cc_sum["last_30_days_tokens"] >= 1_200_000
    assert cc_sum["last_30_days_cost"] >= 4.50

    app = QApplication.instance() or QApplication(["--platform", "offscreen"])
    widget = FloatingCapsuleWidget()
    widget.set_ui_theme("ticket")
    assert widget.ui_theme == "ticket"
    assert widget.btn_theme.text() == "HUD VIEW"
    assert not widget.agy_card.isVisible()

    # Expand drawer and verify ticket cards render with real data
    widget.toggle_drawer()
    assert widget.is_drawer_expanded is True
    assert not widget.ticket_panel.isHidden()

    agy_card = widget.ticket_panel.cards[CLI_AGY]
    assert "GEMINI" in agy_card.hero_title_lbl.text()
    assert "," in agy_card.today_val_lbl.text()
    assert "US$" in agy_card.cost_summary_lbl.text()

    # Clicking 01 GEMINI tab/header must keep GEMINI selected (never flip to CLAUDE/GPT)
    widget.set_active_agy_group(GROUP_GEMINI)
    widget._on_ticket_cli_selected(CLI_AGY)
    assert widget.multi_cli.agy.active_group == GROUP_GEMINI
    assert "GEMINI" in agy_card.hero_title_lbl.text()

    # Switch back to obsidian HUD
    widget.set_ui_theme("obsidian")
    assert widget.ui_theme == "obsidian"
    assert widget.btn_theme.text() == "TICKET VIEW"
    assert widget.ticket_panel.isHidden()

    # Disabling Copilot must persist across opacity/position/theme saves and periodic stats updates
    widget.set_ui_theme("ticket")
    if widget.multi_cli.is_cli_enabled(CLI_COPILOT):
        widget.toggle_cli_enabled(CLI_COPILOT)
    assert not widget.multi_cli.is_cli_enabled(CLI_COPILOT)

    widget.set_opacity_level(0.88)
    widget._save_position()
    widget.set_ui_theme("obsidian")
    widget.set_ui_theme("ticket")

    stale_stats = SessionTokenStats(
        session_id="stale-with-copilot",
        multi_cli=create_default_multi_cli_state(),
    )
    assert CLI_COPILOT in stale_stats.multi_cli.enabled_clis
    widget.update_stats(stale_stats)

    assert not widget.multi_cli.is_cli_enabled(CLI_COPILOT)
    assert widget.copilot_card.isHidden()
    assert widget.ticket_panel.tab_buttons[CLI_COPILOT].isHidden()
    assert widget.ticket_panel.cards[CLI_COPILOT].isHidden()

    # In ticket mode, bottom action/sync bars are hidden so the card displays cleanly
    assert widget.drawer_action_bar_widget.isHidden()
    assert widget.drawer_sync_bar_widget.isHidden()
    widget.set_ui_theme("obsidian")
    assert not widget.drawer_action_bar_widget.isHidden()
    assert not widget.drawer_sync_bar_widget.isHidden()

    reloaded = FloatingCapsuleWidget()
    assert not reloaded.multi_cli.is_cli_enabled(CLI_COPILOT)

    # Verify Claude statusline payload sync updates 5h & 7d remaining %
    import tempfile, json, time as _t
    from src.monitor.log_watcher import LogWatcher
    with tempfile.TemporaryDirectory() as tmpdir:
        payload_path = Path(tmpdir) / "last_statusline_payload.json"
        now_ts = _t.time()
        payload_path.write_text(json.dumps({
            "rate_limits": {
                "five_hour": {"used_percentage": 22.5, "resets_at": now_ts + 3600},
                "seven_day": {"used_percentage": 14.0, "resets_at": now_ts + 86400},
            }
        }), encoding="utf-8")
        watcher = LogWatcher()
        watcher.claude_statusline_payload = payload_path
        m_state = create_default_multi_cli_state()
        m_state.claude.last_synced_time = 0.0
        watcher.sync_local_claude_code_logs(m_state)
        assert abs(m_state.claude.five_hour.percent - 77.5) < 0.01
        assert abs(m_state.claude.monthly_budget.percent - 86.0) < 0.01
        assert m_state.claude.auto_detected is True

    # Verify T3 Code ~/.t3/caches/*.json sync updates Claude, AGY, and Codex
    with tempfile.TemporaryDirectory() as t3dir:
        import datetime as _dt
        t3_path = Path(t3dir)
        checked_iso = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
        reset_iso = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        (t3_path / "claudeAgent.json").write_text(json.dumps({
            "usageLimits": {
                "checkedAt": checked_iso,
                "windows": [
                    {"id": "five_hour", "usedPercent": 6, "resetsAt": reset_iso},
                    {"id": "seven_day", "usedPercent": 2, "resetsAt": reset_iso},
                ],
            }
        }), encoding="utf-8")
        (t3_path / "codex.json").write_text(json.dumps({
            "usageLimits": {
                "checkedAt": checked_iso,
                "windows": [
                    {"id": "primary", "usedPercent": 13, "resetsAt": reset_iso},
                    {"id": "secondary", "usedPercent": 2, "resetsAt": reset_iso},
                ],
            }
        }), encoding="utf-8")
        watcher = LogWatcher()
        watcher.t3_caches_dir = t3_path
        m_t3 = create_default_multi_cli_state()
        m_t3.claude.last_synced_time = 0.0
        m_t3.codex.last_synced_time = 0.0
        watcher.sync_local_t3_caches(m_t3)
        assert abs(m_t3.claude.five_hour.percent - 94.0) < 0.01
        assert abs(m_t3.claude.monthly_budget.percent - 98.0) < 0.01
        assert abs(m_t3.codex.five_hour.percent - 87.0) < 0.01
        assert abs(m_t3.codex.weekly.percent - 98.0) < 0.01

    print("Historical usage ledger and Retro Ticket Card theme tests passed!")


if __name__ == "__main__":
    print(f"Running tests for {APP_NAME} v{APP_VERSION} (Multi-CLI Edition)...")
    backup_settings = load_settings()
    try:
        test_pricing()
        test_context_limits()
        test_duration_parsing_and_countdown_math()
        test_multi_cli_parsers()
        test_multi_cli_switching_and_filtering()
        test_smart_alert_manager()
        test_vector_widgets()
        test_ui_widget()
        test_instant_sync_and_smart_group_switching()
        test_sync_button_timeout_recovery()
        test_periodic_stats_preserves_active_cli()
        test_historical_usage_ledger_and_ticket_theme()
        print("========================================")
        print("ALL TESTS PASSED SUCCESSFULLY (100%)!")
        print("========================================")
    finally:
        save_settings(backup_settings)
        print("User live settings restored successfully.")
