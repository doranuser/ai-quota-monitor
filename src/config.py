"""
Configuration, pricing table, and multi-CLI quota persistence for AGY Token Monitor.
Supports Antigravity (AGY), GitHub Copilot, Claude Code CLI, and OpenAI Codex.
"""

import datetime
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Settings are read by the UI timer and written by interactive/background sync
# paths. Keep readers away from partially-written JSON inside this process.
_STATE_FILE_LOCK = threading.RLock()

APP_NAME = "AGY Token Monitor"
APP_VERSION = "2.3.0"
APP_USER_MODEL_ID = "Google.DeepMind.AGYTokenMonitor.HUD.2_1"
PRICING_TABLE_DATE = "2026-11-23"

# Directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "src" / "assets"
MASCOTS_DIR = ASSETS_DIR / "mascots"
APP_ICON_ICO = ASSETS_DIR / "app.ico"
APP_ICON_PNG = ASSETS_DIR / "icon.png"

# Default base path for Antigravity conversation sessions
DEFAULT_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"

# Path to persist window position, quotas, and user settings
STATE_FILE_PATH = Path.home() / ".agy_token_monitor_state.json"

# Pricing rates per 1,000,000 tokens (USD)
# (Input Price, Output Price)
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # Gemini models
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-3.7": (1.25, 5.00),
    # Claude models
    "claude-3-7-sonnet": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    # OpenAI models
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o1": (15.00, 60.00),
    "o3-mini": (1.10, 4.40),
    # Shortcuts and defaults
    "flash": (0.075, 0.30),
    "flash_lite": (0.05, 0.20),
    "pro": (1.25, 5.00),
    "default": (1.00, 4.00),
}

# Maximum Context Window limits (in tokens)
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # Gemini models (1M to 2M tokens)
    "gemini-2.5-pro": 2_000_000,
    "gemini-2.5-flash": 1_000_000,
    "gemini-2.0-flash": 1_000_000,
    "gemini-1.5-pro": 2_000_000,
    "gemini-1.5-flash": 1_000_000,
    "gemini-3.7": 1_000_000,
    # Claude models (200k tokens)
    "claude-3-7-sonnet": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-3-opus": 200_000,
    # OpenAI models
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "o1": 200_000,
    "o3-mini": 200_000,
    # Generic aliases
    "flash": 1_000_000,
    "flash_lite": 1_000_000,
    "pro": 2_000_000,
    "sonnet": 200_000,
    "haiku": 200_000,
    "opus": 200_000,
    "default": 1_000_000,
}


def get_model_pricing(model_name: str) -> Tuple[float, float]:
    """
    Get (input_price_per_1m, output_price_per_1m) for a given model name.
    Matches normalized sub-strings if exact match is not found.
    """
    if not model_name:
        return MODEL_PRICING["default"]

    norm_name = model_name.lower().strip()

    # Exact match
    if norm_name in MODEL_PRICING:
        return MODEL_PRICING[norm_name]

    # Partial / substring match
    for key, price in MODEL_PRICING.items():
        if key in norm_name:
            return price

    if "flash" in norm_name:
        return MODEL_PRICING["flash"]
    if "pro" in norm_name:
        return MODEL_PRICING["pro"]
    if "sonnet" in norm_name:
        return MODEL_PRICING["claude-3-7-sonnet"]
    if "haiku" in norm_name:
        return MODEL_PRICING["claude-3-5-haiku"]
    if "opus" in norm_name:
        return MODEL_PRICING["claude-3-opus"]

    return MODEL_PRICING["default"]


def get_model_context_limit(model_name: str) -> int:
    """
    Get maximum Context Window token limit for a model name.
    """
    if not model_name:
        return MODEL_CONTEXT_LIMITS["default"]

    norm_name = model_name.lower().strip()

    # Exact match
    if norm_name in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[norm_name]

    # Substring match
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in norm_name:
            return limit

    if "flash" in norm_name:
        return MODEL_CONTEXT_LIMITS["flash"]
    if "pro" in norm_name:
        return MODEL_CONTEXT_LIMITS["pro"]
    if "sonnet" in norm_name:
        return MODEL_CONTEXT_LIMITS["sonnet"]
    if "haiku" in norm_name:
        return MODEL_CONTEXT_LIMITS["haiku"]
    if "opus" in norm_name:
        return MODEL_CONTEXT_LIMITS["opus"]
    if "gpt-4" in norm_name:
        return MODEL_CONTEXT_LIMITS["gpt-4o"]

    return MODEL_CONTEXT_LIMITS["default"]


DEFAULT_SETTINGS: Dict[str, Any] = {
    "window_x": None,
    "window_y": None,
    "opacity": 0.94,
    "always_on_top": True,
    "is_compact": False,
    "custom_brain_dir": "",
    "refresh_interval_ms": 1000,
    "daily_budget_tokens": 5_000_000,
    "daily_budget_usd": 2.00,
    "alerts_enabled": True,
    "alert_thresholds": [20, 10, 0],
    "active_cli": "agy",
    "enabled_clis": ["agy", "copilot", "claude", "codex"],
    "active_group": "gemini",
    "ui_theme": "obsidian",
    "ticket_show_all": False,
    "multi_cli": {
        "active_cli": "agy",
        "enabled_clis": ["agy", "copilot", "claude", "codex"],
        "agy": {
            "cli_id": "agy",
            "display_name": "ANTIGRAVITY (AGY)",
            "short_name": "AGY",
            "gemini": {
                "group_id": "gemini",
                "display_name": "GEMINI MODELS",
                "short_name": "GEMINI",
                "five_hour": {
                    "name": "Five Hour Limit",
                    "percent": 100.0,
                    "initial_reset_seconds": 0,
                    "last_synced_time": 0.0,
                    "is_full": True,
                },
                "weekly": {
                    "name": "Weekly Limit",
                    "percent": 100.0,
                    "initial_reset_seconds": 0,
                    "last_synced_time": 0.0,
                    "is_full": True,
                },
                "last_synced_time": 0.0,
            },
            "claude_gpt": {
                "group_id": "claude_gpt",
                "display_name": "CLAUDE AND GPT MODELS",
                "short_name": "CLAUDE/GPT",
                "five_hour": {
                    "name": "Five Hour Limit",
                    "percent": 100.0,
                    "initial_reset_seconds": 0,
                    "last_synced_time": 0.0,
                    "is_full": True,
                },
                "weekly": {
                    "name": "Weekly Limit",
                    "percent": 100.0,
                    "initial_reset_seconds": 0,
                    "last_synced_time": 0.0,
                    "is_full": True,
                },
                "last_synced_time": 0.0,
            },
            "active_group": "gemini",
            "last_updated": 0.0,
            "raw_usage_text": "",
        },
        "copilot": {
            "cli_id": "copilot",
            "display_name": "GITHUB COPILOT",
            "short_name": "COPILOT",
            "premium_requests": {
                "name": "Premium Requests",
                "percent": 85.0,
                "initial_reset_seconds": 1231200,
                "last_synced_time": 0.0,
                "is_full": False,
                "total_units": 300.0,
                "used_units": 45.0,
                "remaining_units": 255.0,
                "unit_label": "req",
            },
            "rate_limit": {
                "name": "Rolling Rate Limit",
                "percent": 92.0,
                "initial_reset_seconds": 2700,
                "last_synced_time": 0.0,
                "is_full": False,
                "unit_label": "speed",
            },
            "plan_name": "Copilot Pro / Business",
            "last_synced_time": 0.0,
            "raw_text": "",
        },
        "claude": {
            "cli_id": "claude",
            "display_name": "CLAUDE CODE CLI",
            "short_name": "CLAUDE",
            "five_hour": {
                "name": "5-Hour Window",
                "percent": 78.5,
                "initial_reset_seconds": 9600,
                "last_synced_time": 0.0,
                "is_full": False,
            },
            "monthly_budget": {
                "name": "Monthly Budget",
                "percent": 91.2,
                "initial_reset_seconds": 0,
                "last_synced_time": 0.0,
                "is_full": False,
                "total_units": 100.0,
                "used_units": 8.80,
                "remaining_units": 91.20,
                "unit_label": "USD",
            },
            "auto_detected": False,
            "last_synced_time": 0.0,
            "raw_text": "",
        },
        "last_updated": 0.0,
        "raw_sync_text": "",
    },
    "dual_quota": {
        "gemini": {
            "group_id": "gemini",
            "display_name": "GEMINI MODELS",
            "short_name": "GEMINI",
            "five_hour": {
                "name": "Five Hour Limit",
                "percent": 60.09,
                "initial_reset_seconds": 11400,
                "last_synced_time": 0.0,
                "is_full": False,
            },
            "weekly": {
                "name": "Weekly Limit",
                "percent": 93.25,
                "initial_reset_seconds": 401100,
                "last_synced_time": 0.0,
                "is_full": False,
            },
            "last_synced_time": 0.0,
        },
        "claude_gpt": {
            "group_id": "claude_gpt",
            "display_name": "CLAUDE AND GPT MODELS",
            "short_name": "CLAUDE/GPT",
            "five_hour": {
                "name": "Five Hour Limit",
                "percent": 100.0,
                "initial_reset_seconds": 0,
                "last_synced_time": 0.0,
                "is_full": True,
            },
            "weekly": {
                "name": "Weekly Limit",
                "percent": 100.0,
                "initial_reset_seconds": 0,
                "last_synced_time": 0.0,
                "is_full": True,
            },
            "last_synced_time": 0.0,
        },
        "active_group": "gemini",
        "last_updated": 0.0,
        "raw_usage_text": "",
    },
    "daily_usage_ledger": {},
    "cli_daily_ledger": {},
}


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file or return defaults."""
    settings = dict(DEFAULT_SETTINGS)
    try:
        with _STATE_FILE_LOCK:
            if not STATE_FILE_PATH.exists():
                return settings
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings.update(data)
                    # Migrate legacy threshold settings [80, 90, 95] to remaining quota thresholds [20, 10, 0]
                    thresholds = settings.get("alert_thresholds")
                    if thresholds and isinstance(thresholds, list):
                        if any(t > 50 for t in thresholds):
                            settings["alert_thresholds"] = [20, 10, 0]
                    # Ensure active_cli & enabled_clis
                    if "active_cli" not in settings:
                        settings["active_cli"] = "agy"
                    if "enabled_clis" not in settings or not settings["enabled_clis"]:
                        settings["enabled_clis"] = ["agy", "copilot", "claude", "codex"]
    except Exception as exc:
        logger.warning("Unable to load settings from %s: %s", STATE_FILE_PATH, exc)
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings atomically so polling never observes partial JSON."""
    temp_path = STATE_FILE_PATH.with_name(
        f"{STATE_FILE_PATH.name}.{os.getpid()}.tmp"
    )
    try:
        with _STATE_FILE_LOCK:
            current = load_settings()
            current.update(settings)
            STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, STATE_FILE_PATH)
    except Exception as exc:
        logger.warning("Unable to save settings to %s: %s", STATE_FILE_PATH, exc)
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def load_multi_cli_state():
    """
    Load persisted MultiCliQuotaState from settings or initialize default state.
    """
    from .monitor.multi_cli_parser import MultiCliQuotaState, create_default_multi_cli_state

    settings = load_settings()
    now = time.time()

    multi_dict = settings.get("multi_cli")
    if isinstance(multi_dict, dict) and "agy" in multi_dict:
        try:
            state = MultiCliQuotaState.from_dict(multi_dict)
            state.active_cli = settings.get("active_cli", state.active_cli)
            state.enabled_clis = settings.get("enabled_clis", state.enabled_clis)
            if "codex" not in multi_dict and "codex" not in state.enabled_clis:
                state.enabled_clis.append("codex")

            # Fix 0.0 timestamps to current time
            if state.agy.gemini.five_hour.last_synced_time <= 0:
                state.agy.gemini.five_hour.last_synced_time = now
            if state.agy.gemini.weekly.last_synced_time <= 0:
                state.agy.gemini.weekly.last_synced_time = now
            if state.agy.claude_gpt.five_hour.last_synced_time <= 0:
                state.agy.claude_gpt.five_hour.last_synced_time = now
            if state.agy.claude_gpt.weekly.last_synced_time <= 0:
                state.agy.claude_gpt.weekly.last_synced_time = now
            if state.copilot.premium_requests.last_synced_time <= 0:
                state.copilot.premium_requests.last_synced_time = now
            if state.copilot.rate_limit.last_synced_time <= 0:
                state.copilot.rate_limit.last_synced_time = now
            if state.claude.five_hour.last_synced_time <= 0:
                state.claude.five_hour.last_synced_time = now
            if state.claude.monthly_budget.last_synced_time <= 0:
                state.claude.monthly_budget.last_synced_time = now
            if state.codex.five_hour.last_synced_time <= 0:
                state.codex.five_hour.last_synced_time = now
            if state.codex.weekly.last_synced_time <= 0:
                state.codex.weekly.last_synced_time = now
            return state
        except Exception as exc:
            logger.warning("Unable to load multi-CLI settings: %s", exc)

    # Legacy dual_quota migration
    legacy_quota = settings.get("dual_quota")
    state = create_default_multi_cli_state()
    if isinstance(legacy_quota, dict) and "gemini" in legacy_quota:
        try:
            from .monitor.multi_cli_parser import AgyQuotaState
            state.agy = AgyQuotaState.from_dict(legacy_quota)
        except Exception as exc:
            logger.warning("Unable to migrate legacy quota settings: %s", exc)

    state.active_cli = settings.get("active_cli", "agy")
    state.enabled_clis = settings.get("enabled_clis", ["agy", "copilot", "claude", "codex"])
    return state


def save_multi_cli_state(state) -> None:
    """
    Persist MultiCliQuotaState to settings JSON file.
    """
    try:
        settings = load_settings()
        settings["multi_cli"] = state.to_dict()
        settings["active_cli"] = state.active_cli
        settings["enabled_clis"] = list(state.enabled_clis)
        settings["dual_quota"] = state.agy.to_dict()
        settings["active_group"] = state.agy.active_group
        save_settings(settings)
    except Exception as exc:
        logger.warning("Unable to save multi-CLI state: %s", exc)


def load_dual_quota_state():
    """
    Load persisted DualQuotaState (AGY state) for backward compatibility.
    """
    m_state = load_multi_cli_state()
    return m_state.agy


def save_dual_quota_state(state) -> None:
    """
    Persist DualQuotaState (AGY state) for backward compatibility.
    """
    try:
        m_state = load_multi_cli_state()
        m_state.agy = state
        save_multi_cli_state(m_state)
    except Exception as exc:
        logger.warning("Unable to save legacy dual quota state: %s", exc)


def get_today_date_str() -> str:
    """Return today's date formatted as YYYY-MM-DD."""
    return datetime.date.today().isoformat()


def get_today_usage(settings: Optional[Dict[str, Any]] = None, date_str: Optional[str] = None) -> Tuple[int, float]:
    """
    Get cumulative (total_tokens, total_cost) for today from settings ledger.
    """
    tok, cost, _ = get_today_usage_detailed(settings, date_str)
    return tok, cost


def get_today_usage_detailed(
    settings: Optional[Dict[str, Any]] = None,
    date_str: Optional[str] = None
) -> Tuple[int, float, int]:
    """
    Get cumulative (total_tokens, total_cost, session_count) for today from settings ledger.
    """
    if settings is None:
        settings = load_settings()

    target_date = date_str or get_today_date_str()
    ledger = settings.get("daily_usage_ledger", {})
    day_entry = ledger.get(target_date, {})

    sessions = day_entry.get("sessions", {})
    tokens = int(day_entry.get("tokens", 0))
    cost = float(day_entry.get("cost", 0.0))
    count = len(sessions) if isinstance(sessions, dict) else int(day_entry.get("sessions_count", 0))
    if count == 0 and tokens > 0:
        count = 1
    return tokens, cost, count


def record_session_usage(
    session_id: str,
    tokens: int,
    cost: float,
    date_str: Optional[str] = None,
    cli_id: str = "agy",
) -> Tuple[int, float, int]:
    """
    Record or update a session's usage for the day in the persistent ledger.
    Returns the updated (today_total_tokens, today_total_cost, today_sessions_count).
    """
    if not session_id:
        return 0, 0.0, 0

    settings = load_settings()
    target_date = date_str or get_today_date_str()

    ledger = settings.setdefault("daily_usage_ledger", {})
    day_entry = ledger.setdefault(target_date, {"sessions": {}, "tokens": 0, "cost": 0.0})
    sessions = day_entry.setdefault("sessions", {})

    # Record latest cumulative totals for this specific session
    sessions[session_id] = {
        "tokens": int(tokens),
        "cost": float(cost),
    }

    # Recalculate today's totals across all active sessions
    day_tokens = sum(int(s.get("tokens", 0)) for s in sessions.values())
    day_cost = sum(float(s.get("cost", 0.0)) for s in sessions.values())
    session_count = len(sessions)

    day_entry["tokens"] = day_tokens
    day_entry["cost"] = round(day_cost, 6)
    day_entry["sessions_count"] = session_count

    # Also mirror into per-CLI ledger so each CLI ticket card has its own 30-day history
    cli_ledgers = settings.setdefault("cli_daily_ledger", {})
    cli_bucket = cli_ledgers.setdefault(cli_id, {})
    cli_day = cli_bucket.setdefault(target_date, {"sessions": {}, "tokens": 0, "cost": 0.0})
    cli_sessions = cli_day.setdefault("sessions", {})
    cli_sessions[session_id] = {"tokens": int(tokens), "cost": float(cost)}
    cli_day["tokens"] = sum(int(s.get("tokens", 0)) for s in cli_sessions.values())
    cli_day["cost"] = round(sum(float(s.get("cost", 0.0)) for s in cli_sessions.values()), 6)
    cli_day["sessions_count"] = len(cli_sessions)

    # Prune ledger entries older than 30 days
    all_dates = sorted(ledger.keys())
    if len(all_dates) > 30:
        for old_date in all_dates[:-30]:
            ledger.pop(old_date, None)

    cli_dates = sorted(cli_bucket.keys())
    if len(cli_dates) > 30:
        for old_date in cli_dates[:-30]:
            cli_bucket.pop(old_date, None)

    save_settings(settings)
    return day_tokens, day_cost, session_count


def record_cli_session_usage(
    cli_id: str,
    session_id: str,
    tokens: int,
    cost: float,
    date_str: Optional[str] = None,
) -> Tuple[int, float, int]:
    """
    Record or update a session's usage for a specific CLI (agy, copilot, claude, codex).
    For 'agy', delegates to record_session_usage so legacy daily_usage_ledger stays in sync.
    """
    if cli_id == "agy":
        return record_session_usage(session_id, tokens, cost, date_str=date_str, cli_id="agy")
    if not session_id or not cli_id:
        return 0, 0.0, 0

    settings = load_settings()
    target_date = date_str or get_today_date_str()
    cli_ledgers = settings.setdefault("cli_daily_ledger", {})
    cli_bucket = cli_ledgers.setdefault(cli_id, {})
    cli_day = cli_bucket.setdefault(target_date, {"sessions": {}, "tokens": 0, "cost": 0.0})
    cli_sessions = cli_day.setdefault("sessions", {})

    cli_sessions[session_id] = {
        "tokens": int(tokens),
        "cost": float(cost),
    }
    day_tokens = sum(int(s.get("tokens", 0)) for s in cli_sessions.values())
    day_cost = sum(float(s.get("cost", 0.0)) for s in cli_sessions.values())
    session_count = len(cli_sessions)

    cli_day["tokens"] = day_tokens
    cli_day["cost"] = round(day_cost, 6)
    cli_day["sessions_count"] = session_count

    cli_dates = sorted(cli_bucket.keys())
    if len(cli_dates) > 30:
        for old_date in cli_dates[:-30]:
            cli_bucket.pop(old_date, None)

    save_settings(settings)
    return day_tokens, day_cost, session_count


def get_usage_history_summary(
    cli_id: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    reference_date: Optional[datetime.date] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Compute local usage summary for today, yesterday, and rolling 30-day window.
    Returns dict with:
      today_tokens, today_cost, yesterday_tokens, yesterday_cost,
      last_30_days_tokens, last_30_days_cost, daily_series (list of length `days`).
    """
    if settings is None:
        settings = load_settings()

    ref_date = reference_date or datetime.date.today()
    today_key = ref_date.isoformat()
    yesterday_key = (ref_date - datetime.timedelta(days=1)).isoformat()

    # Select ledger source: per-CLI bucket if requested (falling back to daily_usage_ledger for agy)
    if cli_id:
        cli_ledgers = settings.get("cli_daily_ledger", {})
        bucket = cli_ledgers.get(cli_id) if isinstance(cli_ledgers, dict) else None
        if not isinstance(bucket, dict) or (cli_id == "agy" and not bucket):
            bucket = settings.get("daily_usage_ledger", {}) if cli_id == "agy" else {}
    else:
        bucket = settings.get("daily_usage_ledger", {})

    if not isinstance(bucket, dict):
        bucket = {}

    today_entry = bucket.get(today_key, {})
    yesterday_entry = bucket.get(yesterday_key, {})

    today_tokens = int(today_entry.get("tokens", 0)) if isinstance(today_entry, dict) else 0
    today_cost = float(today_entry.get("cost", 0.0)) if isinstance(today_entry, dict) else 0.0
    yesterday_tokens = int(yesterday_entry.get("tokens", 0)) if isinstance(yesterday_entry, dict) else 0
    yesterday_cost = float(yesterday_entry.get("cost", 0.0)) if isinstance(yesterday_entry, dict) else 0.0

    last_n_tokens = 0
    last_n_cost = 0.0
    daily_series: List[int] = []

    for offset in range(days - 1, -1, -1):
        d_key = (ref_date - datetime.timedelta(days=offset)).isoformat()
        entry = bucket.get(d_key, {})
        tok = int(entry.get("tokens", 0)) if isinstance(entry, dict) else 0
        cost = float(entry.get("cost", 0.0)) if isinstance(entry, dict) else 0.0
        daily_series.append(tok)
        last_n_tokens += tok
        last_n_cost += cost

    return {
        "today_tokens": today_tokens,
        "today_cost": round(today_cost, 4),
        "yesterday_tokens": yesterday_tokens,
        "yesterday_cost": round(yesterday_cost, 4),
        "last_30_days_tokens": last_n_tokens,
        "last_30_days_cost": round(last_n_cost, 4),
        "daily_series": daily_series,
    }


def reset_today_usage(date_str: Optional[str] = None) -> None:
    """Reset today's usage ledger in settings."""
    settings = load_settings()
    target_date = date_str or get_today_date_str()
    ledger = settings.setdefault("daily_usage_ledger", {})
    if target_date in ledger:
        ledger[target_date] = {"sessions": {}, "tokens": 0, "cost": 0.0, "sessions_count": 0}
    cli_ledgers = settings.setdefault("cli_daily_ledger", {})
    if isinstance(cli_ledgers, dict):
        for bucket in cli_ledgers.values():
            if isinstance(bucket, dict) and target_date in bucket:
                bucket[target_date] = {"sessions": {}, "tokens": 0, "cost": 0.0, "sessions_count": 0}
    save_settings(settings)
