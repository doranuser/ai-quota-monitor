"""
Multi-CLI Quota Data Model and Parsers for Antigravity (AGY), GitHub Copilot, Claude Code CLI, and OpenAI Codex.
Zero-Emoji Pure Typographic & Geometric Swiss Precision Architecture.
"""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# CLI Source Identifiers
CLI_AGY = "agy"
CLI_COPILOT = "copilot"
CLI_CLAUDE_CODE = "claude"
CLI_CODEX = "codex"
CLI_COMBINED = "combined"

ALL_CLIS = [CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX]

CLI_DISPLAY_NAMES = {
    CLI_AGY: "ANTIGRAVITY (AGY)",
    CLI_COPILOT: "GITHUB COPILOT",
    CLI_CLAUDE_CODE: "CLAUDE CODE CLI",
    CLI_CODEX: "OPENAI CODEX",
    CLI_COMBINED: "MULTI-CLI COMBINED",
}

CLI_SHORT_NAMES = {
    CLI_AGY: "AGY",
    CLI_COPILOT: "COPILOT",
    CLI_CLAUDE_CODE: "CLAUDE",
    CLI_CODEX: "CODEX",
    CLI_COMBINED: "ALL",
}

CLI_THEME_COLORS = {
    CLI_AGY: "#00e599",         # Electric Emerald
    CLI_COPILOT: "#58a6ff",     # GitHub Electric Blue
    CLI_CLAUDE_CODE: "#e57b39", # Claude Warm Terracotta
    CLI_CODEX: "#10a37f",        # OpenAI Green
    CLI_COMBINED: "#a855f7",    # Vivid Violet
}

# Antigravity Model Groups
GROUP_GEMINI = "gemini"
GROUP_CLAUDE_GPT = "claude_gpt"

GROUP_DISPLAY_NAMES = {
    GROUP_GEMINI: "GEMINI MODELS",
    GROUP_CLAUDE_GPT: "CLAUDE AND GPT MODELS",
}

GROUP_SHORT_NAMES = {
    GROUP_GEMINI: "GEMINI",
    GROUP_CLAUDE_GPT: "CLAUDE/GPT",
}


def parse_duration_to_seconds(text: str) -> int:
    """
    Parse duration text into total seconds.
    Supports formats like '3h 10m', '111h 25m', '2d 5h 30m', '45m', '5h', '30s', '45m left', 'Resets in 3h 10m'.
    """
    if not text:
        return 0

    clean_text = text.lower().strip()

    if any(k in clean_text for k in ("optimal", "available", "充足", "full", "no limit", "infinite", "none")):
        return 0

    # Check for ISO 8601 timestamp (e.g. 2026-08-16T19:04:10Z or 2026-08-21T02:19:42Z)
    iso_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)', text)
    if iso_match:
        try:
            from datetime import datetime, timezone
            iso_str = iso_match.group(1).replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            now_dt = datetime.now(timezone.utc)
            diff = (dt - now_dt).total_seconds()
            return max(0, int(diff))
        except Exception:
            pass

    total_seconds = 0

    # Days
    days_match = re.search(r'(\d+)\s*(?:d|days?)\b', clean_text)
    if days_match:
        total_seconds += int(days_match.group(1)) * 86400

    # Hours
    hrs_match = re.search(r'(\d+)\s*(?:h|hrs?|hours?)\b', clean_text)
    if hrs_match:
        total_seconds += int(hrs_match.group(1)) * 3600

    # Minutes
    mins_match = re.search(r'(\d+)\s*(?:m|mins?|minutes?)\b', clean_text)
    if mins_match:
        total_seconds += int(mins_match.group(1)) * 60

    # Seconds
    secs_match = re.search(r'(\d+)\s*(?:s|secs?|seconds?)\b', clean_text)
    if secs_match:
        total_seconds += int(secs_match.group(1))

    return total_seconds


def format_seconds_to_countdown(seconds: int, is_full: bool = False, include_icon: bool = False) -> str:
    """
    Format remaining seconds into pure typographic countdown string (Zero Emoji).
    Ceiling rounds minutes so 3h 9m 59s presents cleanly as 3h 10m.
    """
    if is_full:
        return "OPTIMAL"

    if seconds <= 0:
        return "0m"

    if seconds >= 3600:
        total_mins = (seconds + 59) // 60
        hrs = total_mins // 60
        mins = total_mins % 60
        return f"{hrs}h {mins}m"
    elif seconds >= 60:
        if seconds < 300:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            total_mins = (seconds + 59) // 60
            return f"{total_mins}m"
    else:
        return f"{seconds}s"


@dataclass
class QuotaWindow:
    """Represents a generic time-window or quota limit."""
    name: str = "5-Hour Limit"
    percent: float = 100.0                # 0.0 ~ 100.0 (Remaining percentage)
    initial_reset_seconds: int = 0        # Total seconds remaining at sync
    last_synced_time: float = 0.0         # Timestamp when synced
    is_full: bool = True                  # True if 100% full with no active countdown
    total_units: Optional[float] = None   # e.g., 300 requests or 100 USD
    used_units: Optional[float] = None    # e.g., 45 requests or 8.8 USD
    remaining_units: Optional[float] = None  # e.g., 255 requests or 91.2 USD
    unit_label: str = ""                  # e.g., "req", "USD", "tokens"

    def get_remaining_seconds(self, current_time: Optional[float] = None) -> int:
        """Calculate live remaining seconds until reset based on elapsed time."""
        if self.is_full or self.initial_reset_seconds <= 0:
            return 0
        now = current_time if current_time is not None else time.time()
        elapsed = max(0.0, now - self.last_synced_time)
        remaining = int(self.initial_reset_seconds - elapsed)
        return max(0, remaining)

    def formatted_countdown(self, current_time: Optional[float] = None, include_icon: bool = False) -> str:
        """Format live countdown string in pure typography (e.g. '3h 10m' or 'OPTIMAL')."""
        if self.percent >= 99.99 and (self.is_full or self.initial_reset_seconds <= 0):
            return "OPTIMAL"
        rem_sec = self.get_remaining_seconds(current_time)
        return format_seconds_to_countdown(rem_sec, is_full=False, include_icon=include_icon)

    def formatted_percent(self) -> str:
        return f"{self.percent:.2f}%"

    def formatted_units_summary(self) -> str:
        """Format unit breakdown if present (e.g., '255/300 req' or '$91.20 / $100.00')."""
        if self.remaining_units is not None and self.total_units is not None:
            if self.unit_label.upper() == "USD" or "$" in self.unit_label:
                return f"${self.remaining_units:.2f} / ${self.total_units:.2f}"
            return f"{int(self.remaining_units)}/{int(self.total_units)} {self.unit_label}".strip()
        return f"{self.percent:.1f}%"

    def status_color(self) -> str:
        """
        Color threshold:
        - > 40%: Emerald Green (#10b981)
        - 20% ~ 40%: Amber Gold (#f59e0b)
        - < 20%: Crimson Red (#ef4444)
        """
        if self.percent < 20.0:
            return "#ef4444"
        if self.percent <= 40.0:
            return "#f59e0b"
        return "#10b981"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "percent": self.percent,
            "initial_reset_seconds": self.initial_reset_seconds,
            "last_synced_time": self.last_synced_time,
            "is_full": self.is_full,
            "total_units": self.total_units,
            "used_units": self.used_units,
            "remaining_units": self.remaining_units,
            "unit_label": self.unit_label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuotaWindow":
        return cls(
            name=data.get("name", "5-Hour Limit"),
            percent=float(data.get("percent", 100.0)),
            initial_reset_seconds=int(data.get("initial_reset_seconds", 0)),
            last_synced_time=float(data.get("last_synced_time", 0.0)),
            is_full=bool(data.get("is_full", True)),
            total_units=float(data["total_units"]) if data.get("total_units") is not None else None,
            used_units=float(data["used_units"]) if data.get("used_units") is not None else None,
            remaining_units=float(data["remaining_units"]) if data.get("remaining_units") is not None else None,
            unit_label=data.get("unit_label", ""),
        )


@dataclass
class ModelGroupQuota:
    """Represents dual-tier quotas for an Antigravity model group (Gemini or Claude/GPT)."""
    group_id: str = GROUP_GEMINI
    display_name: str = "GEMINI MODELS"
    short_name: str = "GEMINI"
    five_hour: QuotaWindow = field(default_factory=lambda: QuotaWindow(name="Five Hour Limit", percent=100.0, is_full=True))
    weekly: QuotaWindow = field(default_factory=lambda: QuotaWindow(name="Weekly Limit", percent=100.0, is_full=True))
    last_synced_time: float = 0.0

    def get_status_color(self) -> str:
        return self.five_hour.status_color()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "five_hour": self.five_hour.to_dict(),
            "weekly": self.weekly.to_dict(),
            "last_synced_time": self.last_synced_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelGroupQuota":
        gid = data.get("group_id", GROUP_GEMINI)
        return cls(
            group_id=gid,
            display_name=data.get("display_name", GROUP_DISPLAY_NAMES.get(gid, "GEMINI MODELS")),
            short_name=data.get("short_name", GROUP_SHORT_NAMES.get(gid, "GEMINI")),
            five_hour=QuotaWindow.from_dict(data.get("five_hour", {})),
            weekly=QuotaWindow.from_dict(data.get("weekly", {})),
            last_synced_time=float(data.get("last_synced_time", 0.0)),
        )


@dataclass
class AgyQuotaState:
    """Antigravity (AGY) Quota State containing Gemini and Claude/GPT model groups."""
    cli_id: str = CLI_AGY
    display_name: str = "ANTIGRAVITY (AGY)"
    short_name: str = "AGY"
    gemini: ModelGroupQuota = field(default_factory=lambda: ModelGroupQuota(
        group_id=GROUP_GEMINI,
        display_name="GEMINI MODELS",
        short_name="GEMINI",
        five_hour=QuotaWindow(name="Five Hour Limit", percent=60.09, initial_reset_seconds=11400, last_synced_time=time.time(), is_full=False),
        weekly=QuotaWindow(name="Weekly Limit", percent=93.25, initial_reset_seconds=401100, last_synced_time=time.time(), is_full=False),
        last_synced_time=time.time(),
    ))
    claude_gpt: ModelGroupQuota = field(default_factory=lambda: ModelGroupQuota(
        group_id=GROUP_CLAUDE_GPT,
        display_name="CLAUDE AND GPT MODELS",
        short_name="CLAUDE/GPT",
        five_hour=QuotaWindow(name="Five Hour Limit", percent=100.0, initial_reset_seconds=0, last_synced_time=time.time(), is_full=True),
        weekly=QuotaWindow(name="Weekly Limit", percent=100.0, initial_reset_seconds=0, last_synced_time=time.time(), is_full=True),
        last_synced_time=time.time(),
    ))
    active_group: str = GROUP_GEMINI
    last_updated: float = field(default_factory=time.time)
    raw_usage_text: str = ""

    def get_active_group(self) -> ModelGroupQuota:
        if self.active_group == GROUP_CLAUDE_GPT:
            return self.claude_gpt
        return self.gemini

    def set_active_group(self, group_id: str) -> None:
        if group_id in (GROUP_GEMINI, GROUP_CLAUDE_GPT):
            self.active_group = group_id

    def toggle_active_group(self) -> str:
        if self.active_group == GROUP_GEMINI:
            self.active_group = GROUP_CLAUDE_GPT
        else:
            self.active_group = GROUP_GEMINI
        return self.active_group

    def get_primary_window(self) -> QuotaWindow:
        return self.get_active_group().five_hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cli_id": self.cli_id,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "gemini": self.gemini.to_dict(),
            "claude_gpt": self.claude_gpt.to_dict(),
            "active_group": self.active_group,
            "last_updated": self.last_updated,
            "raw_usage_text": self.raw_usage_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgyQuotaState":
        now = time.time()
        gemini_data = data.get("gemini")
        claude_data = data.get("claude_gpt")

        state = cls()
        if isinstance(gemini_data, dict):
            state.gemini = ModelGroupQuota.from_dict(gemini_data)
        if isinstance(claude_data, dict):
            state.claude_gpt = ModelGroupQuota.from_dict(claude_data)

        state.active_group = data.get("active_group", GROUP_GEMINI)
        state.last_updated = float(data.get("last_updated", now))
        state.raw_usage_text = data.get("raw_usage_text", "")
        return state


# DualQuotaState alias for 100% backward compatibility
DualQuotaState = AgyQuotaState


@dataclass
class CopilotQuotaState:
    """GitHub Copilot Quota State (Premium Requests & Rate Limits)."""
    cli_id: str = CLI_COPILOT
    display_name: str = "GITHUB COPILOT"
    short_name: str = "COPILOT"
    premium_requests: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="Premium Requests",
        percent=85.0,
        initial_reset_seconds=1231200,  # ~14d 6h
        last_synced_time=time.time(),
        is_full=False,
        total_units=300.0,
        used_units=45.0,
        remaining_units=255.0,
        unit_label="req",
    ))
    rate_limit: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="Rolling Rate Limit",
        percent=92.0,
        initial_reset_seconds=2700,     # 45m
        last_synced_time=time.time(),
        is_full=False,
        unit_label="speed",
    ))
    plan_name: str = "Copilot Pro / Business"
    last_synced_time: float = field(default_factory=time.time)
    raw_text: str = ""

    def get_primary_window(self) -> QuotaWindow:
        """Returns the primary quota window (premium requests)."""
        return self.premium_requests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cli_id": self.cli_id,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "premium_requests": self.premium_requests.to_dict(),
            "rate_limit": self.rate_limit.to_dict(),
            "plan_name": self.plan_name,
            "last_synced_time": self.last_synced_time,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CopilotQuotaState":
        now = time.time()
        state = cls()
        if "premium_requests" in data and isinstance(data["premium_requests"], dict):
            state.premium_requests = QuotaWindow.from_dict(data["premium_requests"])
        if "rate_limit" in data and isinstance(data["rate_limit"], dict):
            state.rate_limit = QuotaWindow.from_dict(data["rate_limit"])
        state.plan_name = data.get("plan_name", "Copilot Pro / Business")
        state.last_synced_time = float(data.get("last_synced_time", now))
        state.raw_text = data.get("raw_text", "")
        return state


@dataclass
class ClaudeCodeQuotaState:
    """Claude Code CLI Quota State (5-Hour Session Window & Monthly Budget)."""
    cli_id: str = CLI_CLAUDE_CODE
    display_name: str = "CLAUDE CODE CLI"
    short_name: str = "CLAUDE"
    five_hour: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="5-Hour Window",
        percent=78.5,
        initial_reset_seconds=9600,     # 2h 40m
        last_synced_time=time.time(),
        is_full=False,
    ))
    monthly_budget: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="Monthly Budget",
        percent=91.2,
        initial_reset_seconds=0,
        last_synced_time=time.time(),
        is_full=False,
        total_units=100.0,
        used_units=8.80,
        remaining_units=91.20,
        unit_label="USD",
    ))
    auto_detected: bool = False
    last_synced_time: float = field(default_factory=time.time)
    raw_text: str = ""

    def get_primary_window(self) -> QuotaWindow:
        """Returns the primary rolling 5-hour quota window."""
        return self.five_hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cli_id": self.cli_id,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "five_hour": self.five_hour.to_dict(),
            "monthly_budget": self.monthly_budget.to_dict(),
            "auto_detected": self.auto_detected,
            "last_synced_time": self.last_synced_time,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClaudeCodeQuotaState":
        now = time.time()
        state = cls()
        if "five_hour" in data and isinstance(data["five_hour"], dict):
            state.five_hour = QuotaWindow.from_dict(data["five_hour"])
        if "monthly_budget" in data and isinstance(data["monthly_budget"], dict):
            state.monthly_budget = QuotaWindow.from_dict(data["monthly_budget"])
        state.auto_detected = bool(data.get("auto_detected", False))
        state.last_synced_time = float(data.get("last_synced_time", now))
        state.raw_text = data.get("raw_text", "")
        return state


@dataclass
class CodexQuotaState:
    """OpenAI Codex usage state read from local Codex session events."""
    cli_id: str = CLI_CODEX
    display_name: str = "OPENAI CODEX"
    short_name: str = "CODEX"
    five_hour: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="5-Hour Window",
        percent=100.0,
        initial_reset_seconds=0,
        last_synced_time=time.time(),
        is_full=True,
    ))
    weekly: QuotaWindow = field(default_factory=lambda: QuotaWindow(
        name="7-Day Window",
        percent=100.0,
        initial_reset_seconds=0,
        last_synced_time=time.time(),
        is_full=True,
    ))
    plan_type: str = "unknown"
    credits_balance: Optional[str] = None
    has_credits: Optional[bool] = None
    unlimited: bool = False
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    auto_detected: bool = False
    last_synced_time: float = field(default_factory=time.time)
    raw_text: str = ""

    def get_primary_window(self) -> QuotaWindow:
        return self.five_hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cli_id": self.cli_id,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "five_hour": self.five_hour.to_dict(),
            "weekly": self.weekly.to_dict(),
            "plan_type": self.plan_type,
            "credits_balance": self.credits_balance,
            "has_credits": self.has_credits,
            "unlimited": self.unlimited,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "auto_detected": self.auto_detected,
            "last_synced_time": self.last_synced_time,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodexQuotaState":
        now = time.time()
        state = cls()
        if isinstance(data.get("five_hour"), dict):
            state.five_hour = QuotaWindow.from_dict(data["five_hour"])
        if isinstance(data.get("weekly"), dict):
            state.weekly = QuotaWindow.from_dict(data["weekly"])
        state.plan_type = str(data.get("plan_type", "unknown"))
        state.credits_balance = data.get("credits_balance")
        state.has_credits = data.get("has_credits")
        state.unlimited = bool(data.get("unlimited", False))
        state.total_tokens = int(data.get("total_tokens", 0) or 0)
        state.input_tokens = int(data.get("input_tokens", 0) or 0)
        state.output_tokens = int(data.get("output_tokens", 0) or 0)
        state.cached_input_tokens = int(data.get("cached_input_tokens", 0) or 0)
        state.auto_detected = bool(data.get("auto_detected", False))
        state.last_synced_time = float(data.get("last_synced_time", now))
        state.raw_text = str(data.get("raw_text", ""))
        return state


@dataclass
class MultiCliQuotaState:
    """Unified Multi-CLI Quota State managing AGY, Copilot, Claude Code, and Codex."""
    agy: AgyQuotaState = field(default_factory=lambda: AgyQuotaState())
    copilot: CopilotQuotaState = field(default_factory=lambda: CopilotQuotaState())
    claude: ClaudeCodeQuotaState = field(default_factory=lambda: ClaudeCodeQuotaState())
    codex: CodexQuotaState = field(default_factory=lambda: CodexQuotaState())
    active_cli: str = CLI_AGY
    enabled_clis: List[str] = field(default_factory=lambda: [CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX])
    last_updated: float = field(default_factory=time.time)
    raw_sync_text: str = ""

    def get_active_cli_state(self) -> Any:
        """Get quota state dataclass for currently active CLI."""
        if self.active_cli == CLI_COPILOT:
            return self.copilot
        elif self.active_cli == CLI_CLAUDE_CODE:
            return self.claude
        elif self.active_cli == CLI_CODEX:
            return self.codex
        return self.agy

    def get_active_primary_window(self) -> QuotaWindow:
        """Get the primary quota window for the currently active CLI."""
        state = self.get_active_cli_state()
        if hasattr(state, "get_primary_window"):
            return state.get_primary_window()
        return self.agy.get_primary_window()

    def get_active_display_name(self) -> str:
        return CLI_DISPLAY_NAMES.get(self.active_cli, "ANTIGRAVITY (AGY)")

    def get_active_short_name(self) -> str:
        return CLI_SHORT_NAMES.get(self.active_cli, "AGY")

    def get_active_theme_color(self) -> str:
        return CLI_THEME_COLORS.get(self.active_cli, "#00e599")

    def is_cli_enabled(self, cli_id: str) -> bool:
        return cli_id in self.enabled_clis

    def set_cli_enabled(self, cli_id: str, enabled: bool) -> None:
        """Enable or disable a CLI source. Guarantees at least one CLI remains enabled."""
        if enabled:
            if cli_id not in self.enabled_clis:
                self.enabled_clis.append(cli_id)
        else:
            if cli_id in self.enabled_clis:
                if len(self.enabled_clis) > 1:
                    self.enabled_clis.remove(cli_id)
                    if self.active_cli == cli_id:
                        self.active_cli = self.enabled_clis[0]

    def toggle_cli_enabled(self, cli_id: str) -> bool:
        """Toggle enabled status for a CLI."""
        is_en = self.is_cli_enabled(cli_id)
        self.set_cli_enabled(cli_id, not is_en)
        return self.is_cli_enabled(cli_id)

    def switch_next_cli(self) -> str:
        """Cycle through enabled CLIs."""
        if not self.enabled_clis:
            self.enabled_clis = [CLI_AGY]

        try:
            cur_idx = self.enabled_clis.index(self.active_cli)
            next_idx = (cur_idx + 1) % len(self.enabled_clis)
            self.active_cli = self.enabled_clis[next_idx]
        except ValueError:
            self.active_cli = self.enabled_clis[0]

        return self.active_cli

    def set_active_cli(self, cli_id: str) -> None:
        """Explicitly switch active CLI if valid."""
        if cli_id in ALL_CLIS or cli_id == CLI_COMBINED:
            self.active_cli = cli_id
            if cli_id not in self.enabled_clis and cli_id != CLI_COMBINED:
                self.enabled_clis.append(cli_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agy": self.agy.to_dict(),
            "copilot": self.copilot.to_dict(),
            "claude": self.claude.to_dict(),
            "codex": self.codex.to_dict(),
            "active_cli": self.active_cli,
            "enabled_clis": list(self.enabled_clis),
            "last_updated": self.last_updated,
            "raw_sync_text": self.raw_sync_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiCliQuotaState":
        now = time.time()
        state = cls()
        if "agy" in data and isinstance(data["agy"], dict):
            state.agy = AgyQuotaState.from_dict(data["agy"])
        elif "gemini" in data:  # Legacy flat DualQuotaState migration
            state.agy = AgyQuotaState.from_dict(data)

        if "copilot" in data and isinstance(data["copilot"], dict):
            state.copilot = CopilotQuotaState.from_dict(data["copilot"])

        if "claude" in data and isinstance(data["claude"], dict):
            state.claude = ClaudeCodeQuotaState.from_dict(data["claude"])

        if "codex" in data and isinstance(data["codex"], dict):
            state.codex = CodexQuotaState.from_dict(data["codex"])

        state.active_cli = data.get("active_cli", CLI_AGY)
        en = data.get("enabled_clis")
        if isinstance(en, list) and len(en) > 0:
            state.enabled_clis = [c for c in en if c in ALL_CLIS]
            if not state.enabled_clis:
                state.enabled_clis = [CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX]
        else:
            state.enabled_clis = [CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX]

        state.last_updated = float(data.get("last_updated", now))
        state.raw_sync_text = data.get("raw_sync_text", "")
        return state


def create_default_multi_cli_state() -> MultiCliQuotaState:
    """Create default initial state for Multi-CLI token and quota monitor."""
    now = time.time()
    return MultiCliQuotaState(
        agy=AgyQuotaState(
            gemini=ModelGroupQuota(
                group_id=GROUP_GEMINI,
                display_name="GEMINI MODELS",
                short_name="GEMINI",
                five_hour=QuotaWindow(name="Five Hour Limit", percent=60.09, initial_reset_seconds=11400, last_synced_time=now, is_full=False),
                weekly=QuotaWindow(name="Weekly Limit", percent=93.25, initial_reset_seconds=401100, last_synced_time=now, is_full=False),
                last_synced_time=now,
            ),
            claude_gpt=ModelGroupQuota(
                group_id=GROUP_CLAUDE_GPT,
                display_name="CLAUDE AND GPT MODELS",
                short_name="CLAUDE/GPT",
                five_hour=QuotaWindow(name="Five Hour Limit", percent=100.0, initial_reset_seconds=0, last_synced_time=now, is_full=True),
                weekly=QuotaWindow(name="Weekly Limit", percent=100.0, initial_reset_seconds=0, last_synced_time=now, is_full=True),
                last_synced_time=now,
            ),
            active_group=GROUP_GEMINI,
            last_updated=now,
        ),
        copilot=CopilotQuotaState(
            premium_requests=QuotaWindow(
                name="Premium Requests",
                percent=85.0,
                initial_reset_seconds=1231200,
                last_synced_time=now,
                is_full=False,
                total_units=300.0,
                used_units=45.0,
                remaining_units=255.0,
                unit_label="req",
            ),
            rate_limit=QuotaWindow(
                name="Rolling Rate Limit",
                percent=92.0,
                initial_reset_seconds=2700,
                last_synced_time=now,
                is_full=False,
                unit_label="speed",
            ),
            plan_name="Copilot Pro / Business",
            last_synced_time=now,
        ),
        claude=ClaudeCodeQuotaState(
            five_hour=QuotaWindow(
                name="5-Hour Window",
                percent=78.5,
                initial_reset_seconds=9600,
                last_synced_time=now,
                is_full=False,
            ),
            monthly_budget=QuotaWindow(
                name="Monthly Budget",
                percent=91.2,
                initial_reset_seconds=0,
                last_synced_time=now,
                is_full=False,
                total_units=100.0,
                used_units=8.80,
                remaining_units=91.20,
                unit_label="USD",
            ),
            auto_detected=False,
            last_synced_time=now,
        ),
        codex=CodexQuotaState(
            five_hour=QuotaWindow(
                name="5-Hour Window",
                percent=100.0,
                initial_reset_seconds=0,
                last_synced_time=now,
                is_full=True,
            ),
            weekly=QuotaWindow(
                name="7-Day Window",
                percent=100.0,
                initial_reset_seconds=0,
                last_synced_time=now,
                is_full=True,
            ),
            last_synced_time=now,
        ),
        active_cli=CLI_AGY,
        enabled_clis=[CLI_AGY, CLI_COPILOT, CLI_CLAUDE_CODE, CLI_CODEX],
        last_updated=now,
    )


def create_default_dual_quota_state() -> DualQuotaState:
    """Create default DualQuotaState (AGY state) for backward compatibility."""
    m_state = create_default_multi_cli_state()
    return m_state.agy


# =========================================================================
# PARSERS FOR EACH CLI
# =========================================================================

class CopilotUsageParser:
    """Parser for GitHub Copilot CLI quota status text."""

    @classmethod
    def parse(cls, text: str, existing_state: Optional[CopilotQuotaState] = None) -> CopilotQuotaState:
        now = time.time()
        state = existing_state or CopilotQuotaState()
        state.raw_text = text
        state.last_synced_time = now

        if not text or not text.strip():
            return state

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            line_lower = line.lower()

            # 1. Premium requests line
            if any(k in line_lower for k in ("premium", "fast request", "requests", "monthly quota", "copilot pro")):
                pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                units_match = re.search(r'(\d+)\s*(?:/|of)\s*(\d+)', line)

                if units_match:
                    rem = float(units_match.group(1))
                    tot = float(units_match.group(2))
                    state.premium_requests.remaining_units = rem
                    state.premium_requests.total_units = tot
                    state.premium_requests.used_units = max(0.0, tot - rem)
                    if not pct_match and tot > 0:
                        state.premium_requests.percent = round((rem / tot) * 100.0, 2)

                if pct_match:
                    state.premium_requests.percent = max(0.0, min(100.0, float(pct_match.group(1))))

                sec = parse_duration_to_seconds(line)
                state.premium_requests.initial_reset_seconds = sec
                state.premium_requests.last_synced_time = now
                state.premium_requests.is_full = (state.premium_requests.percent >= 99.99 and sec == 0)

            # 2. Rate limit line
            elif any(k in line_lower for k in ("rate limit", "hourly", "rolling", "speed", "hourly limit")):
                pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if pct_match:
                    state.rate_limit.percent = max(0.0, min(100.0, float(pct_match.group(1))))

                sec = parse_duration_to_seconds(line)
                state.rate_limit.initial_reset_seconds = sec
                state.rate_limit.last_synced_time = now
                state.rate_limit.is_full = (state.rate_limit.percent >= 99.99 and sec == 0)

        return state


class ClaudeCodeUsageParser:
    """Parser for Claude Code CLI cost and session limit text."""

    @classmethod
    def parse(cls, text: str, existing_state: Optional[ClaudeCodeQuotaState] = None) -> ClaudeCodeQuotaState:
        now = time.time()
        state = existing_state or ClaudeCodeQuotaState()
        state.raw_text = text
        state.last_synced_time = now

        if not text or not text.strip():
            return state

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            line_lower = line.lower()

            # 1. 5-Hour or Session rolling limit
            if any(k in line_lower for k in ("5-hour", "5 hour", "5h", "session window", "rolling window", "session limit")):
                pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                if pct_match:
                    state.five_hour.percent = max(0.0, min(100.0, float(pct_match.group(1))))

                sec = parse_duration_to_seconds(line)
                state.five_hour.initial_reset_seconds = sec
                state.five_hour.last_synced_time = now
                state.five_hour.is_full = (state.five_hour.percent >= 99.99 and sec == 0)

            # 2. Monthly Budget or Spend
            elif any(k in line_lower for k in ("budget", "monthly", "cost", "spend", "usd", "token budget", "limit")):
                usd_matches = re.findall(r'\$\s*(\d+(?:\.\d+)?)', line)
                pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)

                if len(usd_matches) >= 2:
                    val1 = float(usd_matches[0])
                    val2 = float(usd_matches[1])
                    if "used" in line_lower or "spent" in line_lower:
                        used = val1
                        tot = val2
                        rem = max(0.0, tot - used)
                    else:
                        rem = val1
                        tot = val2
                        used = max(0.0, tot - rem)

                    state.monthly_budget.remaining_units = rem
                    state.monthly_budget.total_units = tot
                    state.monthly_budget.used_units = used
                    if not pct_match and tot > 0:
                        state.monthly_budget.percent = round((rem / tot) * 100.0, 2)

                if pct_match:
                    state.monthly_budget.percent = max(0.0, min(100.0, float(pct_match.group(1))))

                sec = parse_duration_to_seconds(line)
                state.monthly_budget.initial_reset_seconds = sec
                state.monthly_budget.last_synced_time = now
                state.monthly_budget.is_full = (state.monthly_budget.percent >= 99.99 and sec == 0)

        return state


class CodexUsageParser:
    """Parser for Codex local session rate-limit and token-count events."""

    @staticmethod
    def _timestamp(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                from datetime import datetime, timezone
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                return 0.0
        return 0.0

    @classmethod
    def _apply_window(cls, target: QuotaWindow, payload: Any, now: float) -> None:
        if not isinstance(payload, dict):
            return
        used = payload.get("used_percent")
        if used is None:
            return
        try:
            used_pct = max(0.0, min(100.0, float(used)))
        except (TypeError, ValueError):
            return

        reset_at = payload.get("resets_at")
        reset_seconds = 0
        if reset_at is not None:
            try:
                reset_seconds = max(0, int(float(reset_at) - now))
            except (TypeError, ValueError):
                pass

        target.percent = round(100.0 - used_pct, 2)
        target.initial_reset_seconds = reset_seconds
        target.last_synced_time = now
        target.is_full = target.percent >= 99.99 and reset_seconds == 0

    @classmethod
    def parse(cls, text: str, existing_state: Optional[CodexQuotaState] = None) -> CodexQuotaState:
        """Parse newline-delimited Codex events or human-readable fallback text."""
        now = time.time()
        state = existing_state or CodexQuotaState()
        state.raw_text = text or ""
        state.last_synced_time = now
        parsed_json = False

        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except (TypeError, ValueError):
                continue

            payload = event.get("payload") if isinstance(event, dict) else None
            if not isinstance(payload, dict):
                continue
            if isinstance(payload.get("payload"), dict):
                payload = payload["payload"]

            rate_limits = payload.get("rate_limits")
            if not isinstance(rate_limits, dict):
                continue

            parsed_json = True
            event_now = cls._timestamp(event.get("timestamp")) or now
            primary = rate_limits.get("primary")
            secondary = rate_limits.get("secondary")
            cls._apply_window(state.five_hour, primary, event_now)
            cls._apply_window(state.weekly, secondary, event_now)

            state.plan_type = str(rate_limits.get("plan_type") or state.plan_type or "unknown")
            credits = rate_limits.get("credits")
            if isinstance(credits, dict):
                state.credits_balance = credits.get("balance")
                state.has_credits = credits.get("has_credits")
                state.unlimited = bool(credits.get("unlimited", False))

            info = payload.get("info")
            token_usage = info.get("total_token_usage") if isinstance(info, dict) else None
            if isinstance(token_usage, dict):
                for attr, keys in {
                    "total_tokens": ("total_tokens",),
                    "input_tokens": ("input_tokens",),
                    "output_tokens": ("output_tokens",),
                    "cached_input_tokens": ("cached_input_tokens",),
                }.items():
                    value = next((token_usage.get(k) for k in keys if token_usage.get(k) is not None), None)
                    if value is not None:
                        try:
                            setattr(state, attr, int(value))
                        except (TypeError, ValueError):
                            pass

        if not parsed_json:
            cls._parse_text_fallback(text or "", state, now)

        state.auto_detected = parsed_json or state.auto_detected
        return state

    @classmethod
    def _parse_text_fallback(cls, text: str, state: CodexQuotaState, now: float) -> None:
        for line in text.splitlines():
            lower = line.lower()
            pct = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
            if not pct:
                continue
            try:
                remaining = max(0.0, min(100.0, float(pct.group(1))))
            except ValueError:
                continue
            target = state.weekly if any(k in lower for k in ("7-day", "7 day", "weekly", "week")) else state.five_hour
            target.percent = remaining
            target.initial_reset_seconds = parse_duration_to_seconds(line)
            target.last_synced_time = now
            target.is_full = target.percent >= 99.99 and target.initial_reset_seconds == 0

        plan = re.search(r'plan\s*[:=]\s*([\w-]+)', text, re.IGNORECASE)
        if plan:
            state.plan_type = plan.group(1)
        token_match = re.search(r'(?:total\s+tokens?|tokens?)\s*[:=]\s*([\d,]+)', text, re.IGNORECASE)
        if token_match:
            state.total_tokens = int(token_match.group(1).replace(",", ""))

    @classmethod
    def parse_session_logs(
        cls,
        sessions_dir: Optional[Path] = None,
        existing_state: Optional[CodexQuotaState] = None,
        max_files: int = 120,
    ) -> CodexQuotaState:
        """Read the newest Codex session tails without touching auth or database files."""
        root = sessions_dir or (Path.home() / ".codex" / "sessions")
        state = existing_state or CodexQuotaState()
        if not root.exists() or not root.is_dir():
            return state

        try:
            files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
        except OSError:
            return state

        for path in files:
            try:
                with path.open("rb") as handle:
                    handle.seek(max(0, path.stat().st_size - 512 * 1024))
                    raw = handle.read().decode("utf-8", errors="ignore")
                parsed = cls.parse(raw, state)
                if parsed.auto_detected:
                    # Codex writes the current rate-limit snapshot into the
                    # newest active session; older files may contain stale windows.
                    state.raw_text = "AUTO: ~/.codex/sessions"
                    break
            except (OSError, ValueError):
                continue

        return state


class UsageParser:
    """Official Antigravity (AGY) /usage parser."""

    @classmethod
    def parse(cls, text: str, existing_state: Optional[AgyQuotaState] = None) -> AgyQuotaState:
        now = time.time()
        state = existing_state or AgyQuotaState()
        state.raw_usage_text = text
        state.last_updated = now

        if not text or not text.strip():
            return state

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        current_group: Optional[str] = None
        parsed_gemini = False
        parsed_claude = False

        for line in lines:
            line_upper = line.upper()

            # Check if line specifies group
            line_group = None
            if any(k in line_upper for k in ("CLAUDE", "GPT", "ANTHROPIC", "OPENAI")):
                line_group = GROUP_CLAUDE_GPT
                current_group = GROUP_CLAUDE_GPT
                parsed_claude = True
            elif "GEMINI" in line_upper:
                line_group = GROUP_GEMINI
                current_group = GROUP_GEMINI
                parsed_gemini = True
            else:
                line_group = current_group

            target_group_quota = None
            if line_group == GROUP_GEMINI:
                target_group_quota = state.gemini
            elif line_group == GROUP_CLAUDE_GPT:
                target_group_quota = state.claude_gpt

            if target_group_quota is not None:
                cls._parse_line_into_group(line, target_group_quota, now)

        if not parsed_gemini and not parsed_claude:
            cls._parse_flat_text(text, state, now)

        return state

    @classmethod
    def _parse_line_into_group(cls, line: str, group_quota: ModelGroupQuota, now: float) -> None:
        line_lower = line.lower()
        if any(k in line_lower for k in ("five hour", "5-hour", "5 hour", "5h limit", "5h remaining", "5 hr")):
            pct, sec, is_full = cls._extract_percent_and_reset(line)
            if pct is not None:
                group_quota.five_hour.percent = pct
                group_quota.five_hour.initial_reset_seconds = sec
                group_quota.five_hour.last_synced_time = now
                group_quota.five_hour.is_full = is_full
                group_quota.last_synced_time = now

        elif any(k in line_lower for k in ("weekly", "week limit", "7-day", "7 day", "7d")):
            pct, sec, is_full = cls._extract_percent_and_reset(line)
            if pct is not None:
                group_quota.weekly.percent = pct
                group_quota.weekly.initial_reset_seconds = sec
                group_quota.weekly.last_synced_time = now
                group_quota.weekly.is_full = is_full
                group_quota.last_synced_time = now

    @classmethod
    def _extract_percent_and_reset(cls, text: str) -> Tuple[Optional[float], int, bool]:
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        if not pct_match:
            return None, 0, False

        pct = float(pct_match.group(1))
        pct = max(0.0, min(100.0, pct))

        if pct >= 99.99:
            reset_sec = parse_duration_to_seconds(text)
            is_full = (reset_sec == 0)
            return pct, reset_sec, is_full

        reset_sec = parse_duration_to_seconds(text)
        is_full = False
        return pct, reset_sec, is_full

    @classmethod
    def _parse_flat_text(cls, text: str, state: AgyQuotaState, now: float) -> None:
        gemini_pattern = re.compile(r'GEMINI.*?(?=CLAUDE|GPT|$)', re.DOTALL | re.IGNORECASE)
        claude_pattern = re.compile(r'(?:CLAUDE|GPT).*?(?=GEMINI|$)', re.DOTALL | re.IGNORECASE)

        gem_match = gemini_pattern.search(text)
        if gem_match:
            gem_text = gem_match.group(0)
            for line in gem_text.splitlines():
                cls._parse_line_into_group(line, state.gemini, now)

        claude_match = claude_pattern.search(text)
        if claude_match:
            claude_text = claude_match.group(0)
            for line in claude_text.splitlines():
                cls._parse_line_into_group(line, state.claude_gpt, now)


class MultiCliParser:
    """Unified Parser capable of detecting and parsing any or all CLI quota formats."""

    @classmethod
    def parse(
        cls,
        text: str,
        existing_state: Optional[MultiCliQuotaState] = None,
        target_cli: Optional[str] = None,
    ) -> MultiCliQuotaState:
        """
        Parse multi-CLI quota text and update MultiCliQuotaState.
        If target_cli is specified ('agy', 'copilot', 'claude', 'codex'), routes specifically to that parser.
        Otherwise, intelligently detects sections for AGY, Copilot, Claude Code, and Codex.
        """
        now = time.time()
        state = existing_state or create_default_multi_cli_state()
        state.raw_sync_text = text
        state.last_updated = now

        if not text or not text.strip():
            return state

        text_upper = text.upper()

        if target_cli == CLI_AGY:
            state.agy = UsageParser.parse(text, state.agy)
            return state
        elif target_cli == CLI_COPILOT:
            state.copilot = CopilotUsageParser.parse(text, state.copilot)
            return state
        elif target_cli == CLI_CLAUDE_CODE:
            state.claude = ClaudeCodeUsageParser.parse(text, state.claude)
            return state
        elif target_cli == CLI_CODEX:
            state.codex = CodexUsageParser.parse(text, state.codex)
            return state

        # Auto-detection mode:
        has_agy = any(k in text_upper for k in ("ANTIGRAVITY", "GEMINI", "/USAGE", "FIVE HOUR LIMIT", "WEEKLY LIMIT"))
        has_copilot = any(k in text_upper for k in ("COPILOT", "GITHUB", "PREMIUM REQUESTS", "FAST REQUESTS"))
        has_claude = any(k in text_upper for k in ("CLAUDE CODE", "ANTHROPIC CLAUDE", "SESSION WINDOW", "MONTHLY BUDGET"))
        has_codex = any(k in text_upper for k in ("OPENAI CODEX", "CODEX", "RATE_LIMITS", "RATE LIMITS", "WINDOW_MINUTES"))

        if has_copilot:
            copilot_chunk = cls._extract_section(text, r'(?:GITHUB\s+)?COPILOT', r'(?:ANTIGRAVITY|GEMINI|CLAUDE\s+CODE|$)')
            state.copilot = CopilotUsageParser.parse(copilot_chunk or text, state.copilot)

        if has_claude:
            claude_chunk = cls._extract_section(text, r'CLAUDE\s+CODE', r'(?:ANTIGRAVITY|GEMINI|COPILOT|$)')
            state.claude = ClaudeCodeUsageParser.parse(claude_chunk or text, state.claude)

        if has_codex:
            state.codex = CodexUsageParser.parse(text, state.codex)

        if has_agy or (not has_copilot and not has_claude):
            agy_chunk = cls._extract_section(text, r'(?:ANTIGRAVITY|GEMINI\s+MODELS)', r'(?:COPILOT|CLAUDE\s+CODE|$)')
            state.agy = UsageParser.parse(agy_chunk or text, state.agy)

        return state

    @staticmethod
    def _extract_section(text: str, start_pattern: str, end_pattern: str) -> Optional[str]:
        regex = re.compile(rf'{start_pattern}.*?(?={end_pattern})', re.DOTALL | re.IGNORECASE)
        match = regex.search(text)
        if match:
            return match.group(0).strip()
        return None
