"""
Token and cost parser for AGY transcript JSONL files, integrated with Multi-CLI (AGY, Copilot, Claude Code) Quota state.
"""

from dataclasses import dataclass, field
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ..config import (
    get_model_pricing,
    get_model_context_limit,
    load_settings,
    get_today_usage,
    get_today_usage_detailed,
    load_multi_cli_state,
    load_dual_quota_state,
)
from .multi_cli_parser import (
    CLI_AGY,
    CLI_COPILOT,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_COMBINED,
    CLI_DISPLAY_NAMES,
    CLI_SHORT_NAMES,
    CLI_THEME_COLORS,
    GROUP_GEMINI,
    GROUP_CLAUDE_GPT,
    AgyQuotaState,
    CopilotQuotaState,
    ClaudeCodeQuotaState,
    CodexQuotaState,
    DualQuotaState,
    ModelGroupQuota,
    MultiCliQuotaState,
    QuotaWindow,
    create_default_multi_cli_state,
    create_default_dual_quota_state,
)

logger = logging.getLogger(__name__)


@dataclass
class StepTokenInfo:
    """Token metrics for a single step in the conversation."""
    step_index: int = 0
    timestamp: str = ""
    source: str = ""
    step_type: str = ""
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    content_snippet: str = ""


@dataclass
class SessionTokenStats:
    """Aggregated token statistics for a session with Multi-CLI Quota integration."""
    session_id: str = "N/A"
    session_dir: str = ""
    last_updated: float = 0.0
    total_steps: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    delta_tokens: int = 0
    delta_input: int = 0
    delta_output: int = 0
    estimated_cost: float = 0.0
    current_model: str = "Gemini 2.5/3.7"
    is_demo: bool = False
    error_message: str = ""
    history: List[StepTokenInfo] = field(default_factory=list)

    # Multi-CLI Quota State (AGY, Copilot, Claude Code)
    multi_cli: MultiCliQuotaState = field(default_factory=create_default_multi_cli_state)

    # Context window metrics
    context_limit: int = 1_000_000
    context_percent: float = 0.0
    remaining_context_tokens: int = 1_000_000
    remaining_context_percent: float = 100.0

    # Real-time generation & speed metrics
    tpm: int = 0
    is_generating: bool = False

    # Daily budget tracking
    daily_tokens: int = 0
    daily_cost: float = 0.0
    daily_budget_tokens: int = 5_000_000
    daily_budget_usd: float = 2.00
    daily_token_percent: float = 0.0
    daily_cost_percent: float = 0.0
    today_sessions_count: int = 1

    # Overall Daily Remaining Quota metrics
    remaining_daily_tokens: int = 5_000_000
    remaining_daily_usd: float = 2.00
    remaining_daily_percent: float = 100.0

    # Local Historical Usage (Today / Yesterday / Last 30 Days + per-CLI summaries)
    yesterday_tokens: int = 0
    yesterday_cost: float = 0.0
    last_30_days_tokens: int = 0
    last_30_days_cost: float = 0.0
    daily_token_series: List[int] = field(default_factory=list)
    cli_usage_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ----------------- Multi-CLI & Dual Quota Accessors -----------------
    @property
    def dual_quota(self) -> AgyQuotaState:
        """Backward compatibility access to AGY dual quota."""
        return self.multi_cli.agy

    @dual_quota.setter
    def dual_quota(self, value: AgyQuotaState) -> None:
        self.multi_cli.agy = value

    @property
    def active_cli(self) -> str:
        return self.multi_cli.active_cli

    @property
    def active_cli_name(self) -> str:
        return self.multi_cli.get_active_short_name()

    @property
    def active_cli_color(self) -> str:
        return self.multi_cli.get_active_theme_color()

    @property
    def active_group(self) -> ModelGroupQuota:
        """Return the active monitored model group quota for AGY."""
        return self.multi_cli.agy.get_active_group()

    @property
    def active_group_id(self) -> str:
        return self.multi_cli.agy.active_group

    @property
    def active_group_name(self) -> str:
        return self.active_group.short_name

    @property
    def active_five_hour_percent(self) -> float:
        if self.active_cli == CLI_COPILOT:
            return self.multi_cli.copilot.premium_requests.percent
        elif self.active_cli == CLI_CLAUDE_CODE:
            return self.multi_cli.claude.five_hour.percent
        elif self.active_cli == CLI_CODEX:
            return self.multi_cli.codex.five_hour.percent
        return self.active_group.five_hour.percent

    @property
    def active_weekly_percent(self) -> float:
        if self.active_cli == CLI_COPILOT:
            return self.multi_cli.copilot.rate_limit.percent
        elif self.active_cli == CLI_CLAUDE_CODE:
            return self.multi_cli.claude.monthly_budget.percent
        elif self.active_cli == CLI_CODEX:
            return self.multi_cli.codex.weekly.percent
        return self.active_group.weekly.percent

    def formatted_capsule_title(self) -> str:
        """
        Format prominent top capsule title based on active CLI.
        Examples:
        - AGY: 'GEMINI: 60.1%' or 'CLAUDE: 100.0%'
        - COPILOT: 'COPILOT: 85.0%'
        - CLAUDE: 'CLAUDE: 78.5%'
        - COMBINED: 'MULTI-CLI: 3'
        """
        if self.active_cli == CLI_COPILOT:
            pct = self.multi_cli.copilot.premium_requests.percent
            return f"COPILOT: {pct:.1f}%"
        elif self.active_cli == CLI_CLAUDE_CODE:
            pct = self.multi_cli.claude.five_hour.percent
            return f"CLAUDE: {pct:.1f}%"
        elif self.active_cli == CLI_CODEX:
            pct = self.multi_cli.codex.five_hour.percent
            return f"CODEX: {pct:.1f}%"
        elif self.active_cli == CLI_COMBINED:
            count = len(self.multi_cli.enabled_clis)
            return f"ALL: {count} CLIs"

        # Default AGY
        grp = self.active_group
        short = "GEMINI" if grp.group_id == GROUP_GEMINI else "CLAUDE"
        return f"{short}: {grp.five_hour.percent:.1f}%"

    def formatted_capsule_sub(self) -> str:
        """Format sub-label for active CLI in capsule header."""
        if self.active_cli == CLI_COPILOT:
            return "PREMIUM REQUESTS"
        elif self.active_cli == CLI_CLAUDE_CODE:
            return "5-HR ROLLING WINDOW"
        elif self.active_cli == CLI_CODEX:
            return "5-HR ROLLING WINDOW"
        elif self.active_cli == CLI_COMBINED:
            return "COMBINED HUD"
        return "5-HR ROLLING QUOTA"

    def formatted_capsule_countdown(self, current_time: Optional[float] = None) -> str:
        """
        Format active refresh countdown badge.
        Example: '3h 10m', '45m', '2h 40m', or 'OPTIMAL'
        """
        win = self.multi_cli.get_active_primary_window()
        return win.formatted_countdown(current_time=current_time)

    def active_status_color(self) -> str:
        """Status color for currently active CLI's primary quota window."""
        win = self.multi_cli.get_active_primary_window()
        return win.status_color()

    # ----------------- Existing Formatters (Backward Compatibility) -----------------
    def formatted_remaining_tokens(self) -> str:
        return f"{TokenParser.format_number(self.remaining_daily_tokens)} 剩餘"

    def formatted_remaining_tokens_raw(self) -> str:
        return TokenParser.format_number(self.remaining_daily_tokens)

    def formatted_remaining_percent(self) -> str:
        return f"{self.remaining_daily_percent:.1f}%"

    def formatted_remaining_cost(self) -> str:
        return f"${self.remaining_daily_usd:.2f} 剩餘"

    def formatted_remaining_cost_raw(self) -> str:
        return f"${self.remaining_daily_usd:.2f}"

    def formatted_deduction_delta(self) -> str:
        if self.delta_tokens == 0:
            return "0"
        return f"-{TokenParser.format_number(self.delta_tokens)}"

    def remaining_status_color(self) -> str:
        return self.active_status_color()

    def formatted_daily_remaining_summary(self) -> str:
        return f"剩餘 {TokenParser.format_number(self.remaining_daily_tokens)} / {TokenParser.format_number(self.daily_budget_tokens)} Tokens ({self.remaining_daily_percent:.1f}% 剩餘)"

    def formatted_daily_usd_summary(self) -> str:
        return f"剩餘 ${self.remaining_daily_usd:.2f} / ${self.daily_budget_usd:.2f} USD"

    def formatted_context_remaining_summary(self) -> str:
        return f"剩餘 {TokenParser.format_number(self.remaining_context_tokens)} / {TokenParser.format_number(self.context_limit)} ({self.remaining_context_percent:.1f}% 可用)"

    def formatted_global_sessions_summary(self) -> str:
        return f"對話總數: {self.today_sessions_count} Sessions  |  總消耗: {TokenParser.format_number(self.daily_tokens)} Tokens"

    def formatted_total_tokens(self) -> str:
        return TokenParser.format_number(self.total_tokens)

    def formatted_delta_tokens(self) -> str:
        if self.delta_tokens == 0:
            return "0"
        sign = "+" if self.delta_tokens > 0 else ""
        return f"{sign}{TokenParser.format_number(self.delta_tokens)}"

    def formatted_cost(self) -> str:
        if self.estimated_cost < 0.001:
            return f"${self.estimated_cost:.4f}"
        if self.estimated_cost < 1.0:
            return f"${self.estimated_cost:.3f}"
        return f"${self.estimated_cost:.2f}"

    def formatted_tpm(self) -> str:
        if self.tpm <= 0:
            return "0 tpm"
        return f"{TokenParser.format_number(self.tpm)} tpm"

    def formatted_context_percent(self) -> str:
        return f"{self.context_percent:.1f}%"

    def context_status_color(self) -> str:
        if self.context_percent >= 90.0:
            return "#ef4444"
        if self.context_percent >= 70.0:
            return "#f59e0b"
        return "#10b981"

    def formatted_daily_tokens(self) -> str:
        return f"{TokenParser.format_number(self.daily_tokens)} / {TokenParser.format_number(self.daily_budget_tokens)}"

    def formatted_daily_cost(self) -> str:
        return f"${self.daily_cost:.2f} / ${self.daily_budget_usd:.2f}"


class TokenParser:
    """Parses transcript JSONL files and calculates token usage, costs, and remaining quotas."""

    @staticmethod
    def format_number(val: int) -> str:
        """Format integer count to readable string."""
        abs_val = abs(val)
        if abs_val >= 1_000_000:
            return f"{val / 1_000_000:.2f}M"
        if abs_val >= 1_000:
            return f"{val / 1_000:.1f}k"
        return str(val)

    @staticmethod
    def estimate_tokens_from_text(text: str) -> int:
        """
        Robust heuristic estimator for token counts from mixed language text.
        """
        if not text:
            return 0

        cjk_count = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]', text))
        non_cjk_len = len(text) - cjk_count

        cjk_tokens = int(cjk_count * 1.25)
        non_cjk_tokens = int(non_cjk_len / 3.7)

        return max(1, cjk_tokens + non_cjk_tokens)

    @classmethod
    def extract_model_from_entry(cls, entry: Dict[str, Any]) -> Optional[str]:
        """Attempt to extract model identifier from entry metadata or tool calls."""
        if not isinstance(entry, dict):
            return None

        for field_name in ("model", "model_name", "model_id", "selected_model"):
            if field_name in entry and isinstance(entry[field_name], str) and entry[field_name].strip():
                return entry[field_name].strip()

        # Check tool calls if model was specified (e.g., invoke_subagent)
        tool_calls = entry.get("tool_calls", [])
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict):
                    args = tc.get("arguments") or tc.get("args") or tc.get("parameters") or {}
                    if isinstance(args, dict):
                        if "Model" in args and isinstance(args["Model"], str):
                            return args["Model"]
                        subagents = args.get("Subagents", [])
                        if isinstance(subagents, list) and len(subagents) > 0:
                            first_sub = subagents[0]
                            if isinstance(first_sub, dict) and "Model" in first_sub:
                                return str(first_sub["Model"])

        return None

    @classmethod
    def extract_token_counts(cls, entry: Dict[str, Any]) -> Tuple[int, int]:
        """
        Extract (input_tokens, output_tokens) from JSONL entry.
        """
        input_tokens = 0
        output_tokens = 0

        usage = entry.get("usage") or entry.get("token_usage") or entry.get("tokens")
        if isinstance(usage, dict):
            input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
            if input_tokens > 0 or output_tokens > 0:
                return input_tokens, output_tokens

        content = entry.get("content") or entry.get("text") or ""
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_parts.append(str(item.get("text", "")))
            content = " ".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)

        estimated = cls.estimate_tokens_from_text(content)
        entry_type = entry.get("type", "")
        source = entry.get("source", "")

        if source == "USER" or "USER" in entry_type:
            input_tokens = estimated
        else:
            output_tokens = estimated

        return input_tokens, output_tokens

    @classmethod
    def parse_transcript_lines(
        cls,
        lines: List[str],
        session_id: str = "N/A",
        session_dir: str = "",
        multi_cli: Optional[MultiCliQuotaState] = None,
        dual_quota: Optional[DualQuotaState] = None,
    ) -> SessionTokenStats:
        """
        Parse all JSONL lines for a session transcript and compute aggregate usage statistics.
        """
        m_state = multi_cli or load_multi_cli_state()
        if dual_quota is not None:
            m_state.agy = dual_quota

        stats = SessionTokenStats(
            session_id=session_id,
            session_dir=session_dir,
            last_updated=time.time(),
            multi_cli=m_state,
        )

        settings = load_settings()
        stats.daily_budget_tokens = int(settings.get("daily_budget_tokens", 5_000_000))
        stats.daily_budget_usd = float(settings.get("daily_budget_usd", 2.00))

        # Pull existing daily usage from persistent ledger
        day_tokens, day_cost, session_cnt = get_today_usage_detailed(settings)
        stats.daily_tokens = day_tokens
        stats.daily_cost = day_cost
        stats.today_sessions_count = max(1, session_cnt)

        total_inp = 0
        total_out = 0
        detected_model = "Gemini 2.5 Pro"
        step_history: List[StepTokenInfo] = []

        last_inp_delta = 0
        last_out_delta = 0

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except Exception:
                continue

            if not isinstance(entry, dict):
                continue

            model_found = cls.extract_model_from_entry(entry)
            if model_found:
                detected_model = model_found

            inp, out = cls.extract_token_counts(entry)
            total_inp += inp
            total_out += out

            last_inp_delta = inp
            last_out_delta = out

            in_rate, out_rate = get_model_pricing(detected_model)
            step_cost = (inp * in_rate + out * out_rate) / 1_000_000.0

            content_text = str(entry.get("content", ""))[:120]
            step_info = StepTokenInfo(
                step_index=entry.get("step_index", line_num),
                timestamp=str(entry.get("timestamp", "")),
                source=str(entry.get("source", "")),
                step_type=str(entry.get("type", "")),
                model_name=detected_model,
                input_tokens=inp,
                output_tokens=out,
                total_tokens=inp + out,
                cost=step_cost,
                content_snippet=content_text,
            )
            step_history.append(step_info)

        stats.total_steps = len(step_history)
        stats.total_input_tokens = total_inp
        stats.total_output_tokens = total_out
        stats.total_tokens = total_inp + total_out
        stats.delta_tokens = last_inp_delta + last_out_delta
        stats.delta_input = last_inp_delta
        stats.delta_output = last_out_delta
        stats.current_model = detected_model
        stats.history = step_history

        # Calculate estimated cost
        in_price, out_price = get_model_pricing(detected_model)
        stats.estimated_cost = (total_inp * in_price + total_out * out_price) / 1_000_000.0

        # Context window calculations
        context_limit = get_model_context_limit(detected_model)
        stats.context_limit = context_limit
        stats.context_percent = min(100.0, (stats.total_tokens / max(1, context_limit)) * 100.0)
        stats.remaining_context_tokens = max(0, context_limit - stats.total_tokens)
        stats.remaining_context_percent = max(0.0, min(100.0, (stats.remaining_context_tokens / max(1, context_limit)) * 100.0))

        # Overall Daily Remaining Quota calculations
        stats.remaining_daily_tokens = max(0, stats.daily_budget_tokens - stats.daily_tokens)
        stats.remaining_daily_usd = max(0.0, round(stats.daily_budget_usd - stats.daily_cost, 4))
        stats.remaining_daily_percent = max(0.0, min(100.0, (stats.remaining_daily_tokens / max(1, stats.daily_budget_tokens)) * 100.0))

        return stats

    @classmethod
    def compute_tpm(cls, token_events: List[Tuple[float, int]], window_seconds: float = 60.0, current_time: Optional[float] = None) -> int:
        """
        Calculate sliding window Tokens Per Minute (TPM).
        """
        now = current_time or time.time()
        cutoff = now - window_seconds

        recent_tokens = sum(count for ts, count in token_events if ts >= cutoff)
        if not token_events:
            return 0

        valid_events = [ts for ts, _ in token_events if ts >= cutoff]
        if not valid_events:
            return 0

        earliest_ts = min(valid_events)
        duration = max(1.0, now - earliest_ts)
        effective_window = min(window_seconds, duration)

        if effective_window < 1.0:
            effective_window = 1.0

        tpm = int((recent_tokens / effective_window) * 60.0)
        return max(0, tpm)
