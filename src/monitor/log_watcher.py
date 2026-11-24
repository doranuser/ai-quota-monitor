import datetime
from collections import deque
import datetime
import json
import logging
import os
from pathlib import Path
import random
import threading
import time
from typing import Deque, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from ..config import (
    DEFAULT_BRAIN_DIR,
    load_settings,
    load_multi_cli_state,
    save_multi_cli_state,
    load_dual_quota_state,
    record_session_usage,
    record_cli_session_usage,
    get_today_usage,
    get_today_usage_detailed,
    get_usage_history_summary,
    get_model_context_limit,
)
from .token_parser import SessionTokenStats, TokenParser
from .multi_cli_parser import (
    ALL_CLIS,
    CLI_AGY,
    CLI_CLAUDE_CODE,
    CLI_CODEX,
    CLI_COPILOT,
    CodexQuotaState,
    CodexUsageParser,
    MultiCliQuotaState,
    create_default_multi_cli_state,
)

logger = logging.getLogger(__name__)

# Try importing watchdog, handle fallback if missing
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object
    Observer = None


class TranscriptFileHandler(FileSystemEventHandler):
    """Watchdog event handler for transcript file changes."""

    def __init__(self, watcher: "LogWatcher"):
        super().__init__()
        self.watcher = watcher

    def on_modified(self, event):
        if not event.is_directory and "transcript" in event.src_path:
            self.watcher.trigger_check()

    def on_created(self, event):
        if not event.is_directory and "transcript" in event.src_path:
            self.watcher.trigger_check()


class LogWatcher(QObject):
    """
    Monitors Antigravity conversation transcripts and Claude Code CLI logs,
    scans today's sessions across the workspace, and emits real-time Multi-CLI quota statistics.
    """
    stats_updated = Signal(object)      # Emits SessionTokenStats
    session_changed = Signal(str, str)  # Emits (session_id, path)
    status_changed = Signal(str)        # Emits status message

    def __init__(self, brain_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.brain_dir = brain_dir or DEFAULT_BRAIN_DIR
        self.agy_statusline_payload = Path.home() / ".gemini" / "antigravity-cli" / "last_statusline_payload.json"
        self._agy_payload_mtime: float = 0.0
        self.claude_dir = Path.home() / ".claude"
        self.claude_statusline_payload = self.claude_dir / "cache" / "last_statusline_payload.json"
        self._claude_payload_mtime: float = 0.0
        self.t3_caches_dir = Path.home() / ".t3" / "caches"
        self._t3_cache_mtimes: dict = {}
        self.codex_sessions_dir = Path.home() / ".codex" / "sessions"
        self._codex_last_scan_at: float = 0.0
        self._codex_file_signature: Optional[Tuple[str, int, int]] = None
        self._codex_cached_state: Optional[CodexQuotaState] = None
        self._history_last_scan_at: float = 0.0
        self._history_thread_running: bool = False
        self._synced_file_mtimes: dict = {}
        self.current_session_dir: Optional[Path] = None
        self.current_transcript_path: Optional[Path] = None
        self.last_mtime: float = 0.0
        self.last_file_size: int = 0
        self.cached_stats: Optional[SessionTokenStats] = None

        # Tracking token generation & TPM sliding window (last 60s)
        self.token_events: Deque[Tuple[float, int]] = deque()
        self.last_seen_tokens: int = 0
        self.last_activity_time: float = 0.0

        # Watchdog observer
        self.observer = None
        self.watch_handle = None

        # Polling timer for periodic synchronization & TPM decay
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.check_updates)

        # Debounce timer for filesystem events
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(150)
        self.debounce_timer.timeout.connect(self.check_updates)

    def start(self, interval_ms: int = 1000) -> None:
        """Start monitoring sessions and transcripts."""
        self.discover_latest_session()
        self.check_updates()

        # Start timer polling
        self.poll_timer.start(interval_ms)

        # Start watchdog if available
        self._start_watchdog()

    def stop(self) -> None:
        """Stop watcher and cleanup resources."""
        self.poll_timer.stop()
        self.debounce_timer.stop()
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=1.0)
            except Exception as e:
                logger.warning(f"Error stopping watchdog observer: {e}")
            self.observer = None

    def trigger_check(self) -> None:
        """Debounced check triggered by filesystem event."""
        self.debounce_timer.start()

    def _start_watchdog(self) -> None:
        """Initialize and start watchdog observer on brain directory."""
        if not WATCHDOG_AVAILABLE or not self.brain_dir.exists():
            return

        try:
            if self.observer:
                self.observer.stop()
                self.observer = None

            self.observer = Observer()
            handler = TranscriptFileHandler(self)
            self.observer.schedule(handler, str(self.brain_dir), recursive=True)
            self.observer.daemon = True
            self.observer.start()
            logger.info(f"Watchdog active on: {self.brain_dir}")
        except Exception as e:
            logger.warning(f"Failed to start watchdog: {e}")

    def scan_all_today_sessions(self) -> List[Tuple[float, Path, Path]]:
        """
        Scan all session folders in brain directory.
        Identifies sessions updated today and synchronizes their totals into the daily ledger.
        Returns sorted list of (mtime, session_dir, transcript_file) with the newest first.
        """
        settings = load_settings()
        custom_dir = settings.get("custom_brain_dir")
        if custom_dir and os.path.isdir(custom_dir):
            self.brain_dir = Path(custom_dir)

        if not self.brain_dir.exists() or not self.brain_dir.is_dir():
            return []

        candidates: List[Tuple[float, Path, Path]] = []
        today_date = datetime.date.today()

        try:
            for session_folder in self.brain_dir.iterdir():
                if not session_folder.is_dir():
                    continue

                transcript_file = None
                t1 = session_folder / ".system_generated" / "logs" / "transcript.jsonl"
                t2 = session_folder / "transcript.jsonl"
                t3 = session_folder / ".system_generated" / "logs" / "transcript_full.jsonl"

                for t in (t1, t2, t3):
                    if t.exists() and t.is_file():
                        transcript_file = t
                        break

                if not transcript_file:
                    continue

                try:
                    stat_info = transcript_file.stat()
                    mtime = stat_info.st_mtime
                    candidates.append((mtime, session_folder, transcript_file))

                    # Only sync today's sessions inline; older 30-day sessions are backfilled in background
                    mod_date = datetime.date.fromtimestamp(mtime)
                    cache_key = f"agy:{transcript_file}"
                    if mod_date == today_date and self.current_session_dir != session_folder:
                        if self._synced_file_mtimes.get(cache_key) != mtime:
                            try:
                                with open(transcript_file, "r", encoding="utf-8", errors="ignore") as f:
                                    lines = f.readlines()
                                s_stats = TokenParser.parse_transcript_lines(
                                    lines,
                                    session_id=session_folder.name,
                                    session_dir=str(session_folder),
                                )
                                record_session_usage(
                                    session_folder.name,
                                    s_stats.total_tokens,
                                    s_stats.estimated_cost,
                                    date_str=mod_date.isoformat(),
                                    cli_id=CLI_AGY,
                                )
                                self._synced_file_mtimes[cache_key] = mtime
                            except Exception:
                                pass
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Error scanning brain directory: {e}")

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates

    def sync_local_agy_statusline(self, multi_cli: MultiCliQuotaState) -> None:
        """
        Read Antigravity CLI's local statusline payload JSON when newer than last_updated.
        Provides instant (<1ms) floating-point quota updates without spawning 'agy -p /usage'.
        """
        try:
            if not self.agy_statusline_payload.exists():
                return
            mtime = self.agy_statusline_payload.stat().st_mtime
            if mtime <= self._agy_payload_mtime or mtime <= multi_cli.agy.last_updated:
                return

            data = json.loads(self.agy_statusline_payload.read_text(encoding="utf-8", errors="ignore"))
            quota = data.get("quota")
            if not isinstance(quota, dict):
                return

            now = time.time()
            mapping = [
                ("gemini-5h", multi_cli.agy.gemini.five_hour),
                ("gemini-weekly", multi_cli.agy.gemini.weekly),
                ("3p-5h", multi_cli.agy.claude_gpt.five_hour),
                ("3p-weekly", multi_cli.agy.claude_gpt.weekly),
            ]
            updated = False
            for key, win in mapping:
                entry = quota.get(key)
                if not isinstance(entry, dict):
                    continue
                frac = entry.get("remaining_fraction")
                if frac is None:
                    continue
                pct = max(0.0, min(100.0, float(frac) * 100.0))
                reset_s = int(entry.get("reset_in_seconds") or 0)
                # Adjust reset_in_seconds by file age so countdown stays accurate
                age_s = max(0, int(now - mtime))
                adj_reset_s = max(0, reset_s - age_s) if reset_s > 0 else 0
                win.percent = round(pct, 2)
                win.initial_reset_seconds = adj_reset_s
                win.last_synced_time = now
                win.is_full = pct >= 99.9
                updated = True

            if updated:
                multi_cli.agy.gemini.last_synced_time = now
                multi_cli.agy.claude_gpt.last_synced_time = now
                multi_cli.agy.last_updated = now
                self._agy_payload_mtime = mtime
                save_multi_cli_state(multi_cli)
        except Exception as exc:
            logger.debug("AGY statusline payload sync skipped: %s", exc)

    def sync_local_claude_code_logs(self, multi_cli: MultiCliQuotaState) -> None:
        """
        Sync Claude Code CLI quota from ~/.claude/cache/last_statusline_payload.json
        (rate_limits.five_hour / seven_day) and detect local session activity.
        """
        now = time.time()

        # 1. Read statusline payload dumped by ~/.claude/statusline-wrapper.sh
        try:
            if self.claude_statusline_payload.exists():
                mtime = self.claude_statusline_payload.stat().st_mtime
                if mtime > self._claude_payload_mtime and mtime > multi_cli.claude.last_synced_time:
                    data = json.loads(
                        self.claude_statusline_payload.read_text(encoding="utf-8", errors="ignore")
                    )
                    rate_limits = data.get("rate_limits")
                    if isinstance(rate_limits, dict):
                        updated = False
                        fh = rate_limits.get("five_hour")
                        if isinstance(fh, dict) and fh.get("used_percentage") is not None:
                            used_pct = float(fh["used_percentage"])
                            rem_pct = max(0.0, min(100.0, 100.0 - used_pct))
                            resets_at = fh.get("resets_at")
                            reset_s = max(0, int(float(resets_at) - now)) if resets_at else 0
                            multi_cli.claude.five_hour.percent = round(rem_pct, 2)
                            multi_cli.claude.five_hour.initial_reset_seconds = reset_s
                            multi_cli.claude.five_hour.last_synced_time = now
                            multi_cli.claude.five_hour.is_full = rem_pct >= 99.9
                            updated = True

                        sd = rate_limits.get("seven_day")
                        if isinstance(sd, dict) and sd.get("used_percentage") is not None:
                            used_7d = float(sd["used_percentage"])
                            rem_7d = max(0.0, min(100.0, 100.0 - used_7d))
                            resets_7d = sd.get("resets_at")
                            reset_7d_s = max(0, int(float(resets_7d) - now)) if resets_7d else 0
                            multi_cli.claude.monthly_budget.percent = round(rem_7d, 2)
                            multi_cli.claude.monthly_budget.initial_reset_seconds = reset_7d_s
                            multi_cli.claude.monthly_budget.last_synced_time = now
                            multi_cli.claude.monthly_budget.is_full = rem_7d >= 99.9
                            updated = True

                        if updated:
                            multi_cli.claude.auto_detected = True
                            multi_cli.claude.last_synced_time = now
                            self._claude_payload_mtime = mtime
                            save_multi_cli_state(multi_cli)
                            return
        except Exception as exc:
            logger.debug("Claude statusline payload sync skipped: %s", exc)

        # 2. Fallback: detect today's session activity in ~/.claude/projects/
        projects_dir = self.claude_dir / "projects"
        if not projects_dir.exists() or not projects_dir.is_dir():
            return

        today_date = datetime.date.today()
        found_claude_activity = False

        try:
            for proj in projects_dir.iterdir():
                if not proj.is_dir():
                    continue
                for log_file in proj.glob("*.jsonl"):
                    try:
                        mtime = log_file.stat().st_mtime
                        if datetime.date.fromtimestamp(mtime) == today_date:
                            found_claude_activity = True
                            break
                    except Exception:
                        pass
                if found_claude_activity:
                    break

            if found_claude_activity:
                multi_cli.claude.auto_detected = True
        except Exception:
            pass

    def sync_local_codex_usage(self, multi_cli: MultiCliQuotaState) -> None:
        """Read Codex's local session rate-limit snapshots when available."""
        try:
            now = time.monotonic()
            if self._codex_cached_state is not None and now - self._codex_last_scan_at < 2.0:
                multi_cli.codex = self._codex_cached_state
                return

            self._codex_last_scan_at = now
            newest = None
            if self.codex_sessions_dir.exists():
                files = list(self.codex_sessions_dir.rglob("*.jsonl"))
                if files:
                    newest = max(files, key=lambda path: path.stat().st_mtime_ns)

            signature = None
            if newest is not None:
                stat = newest.stat()
                signature = (str(newest), stat.st_mtime_ns, stat.st_size)

            if signature == self._codex_file_signature and self._codex_cached_state is not None:
                state = self._codex_cached_state
            else:
                state = CodexUsageParser.parse_session_logs(
                    self.codex_sessions_dir,
                    existing_state=multi_cli.codex,
                )
                self._codex_file_signature = signature
                self._codex_cached_state = state

            multi_cli.codex = state
        except Exception as exc:
            logger.debug("Codex usage scan skipped: %s", exc)

    @staticmethod
    def _parse_iso_timestamp(iso_str: Optional[str]) -> Optional[float]:
        """Parse an ISO-8601 UTC timestamp string into Unix epoch seconds."""
        if not iso_str or not isinstance(iso_str, str):
            return None
        try:
            dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return None

    def sync_local_t3_caches(self, multi_cli: MultiCliQuotaState) -> None:
        """
        Read T3 Code's ~/.t3/caches/{claudeAgent,antigravity,codex}.json usageLimits
        so quota stays fresh even when running Claude/AGY/Codex inside T3 Code.
        """
        if not self.t3_caches_dir.exists() or not self.t3_caches_dir.is_dir():
            return

        now = time.time()
        any_updated = False

        def _apply_window(win, used_pct: float, resets_at: Optional[str], sync_ts: float) -> None:
            rem_pct = max(0.0, min(100.0, 100.0 - float(used_pct)))
            reset_ts = self._parse_iso_timestamp(resets_at)
            reset_s = max(0, int(reset_ts - now)) if reset_ts is not None else 0
            win.percent = round(rem_pct, 2)
            win.initial_reset_seconds = reset_s
            win.last_synced_time = sync_ts
            win.is_full = rem_pct >= 99.9

        # 1. Claude Code via T3 Code (claudeAgent.json)
        cc_file = self.t3_caches_dir / "claudeAgent.json"
        if cc_file.exists():
            try:
                mtime = cc_file.stat().st_mtime
                if mtime > self._t3_cache_mtimes.get("claudeAgent.json", 0.0):
                    self._t3_cache_mtimes["claudeAgent.json"] = mtime
                    data = json.loads(cc_file.read_text(encoding="utf-8", errors="ignore"))
                    ul = data.get("usageLimits") if isinstance(data, dict) else None
                    if isinstance(ul, dict) and isinstance(ul.get("windows"), list):
                        checked_ts = self._parse_iso_timestamp(ul.get("checkedAt")) or mtime
                        if checked_ts > multi_cli.claude.last_synced_time:
                            for w in ul["windows"]:
                                if not isinstance(w, dict) or w.get("usedPercent") is None:
                                    continue
                                wid = w.get("id")
                                if wid == "five_hour":
                                    _apply_window(multi_cli.claude.five_hour, w["usedPercent"], w.get("resetsAt"), checked_ts)
                                elif wid == "seven_day":
                                    _apply_window(multi_cli.claude.monthly_budget, w["usedPercent"], w.get("resetsAt"), checked_ts)
                            multi_cli.claude.auto_detected = True
                            multi_cli.claude.last_synced_time = checked_ts
                            any_updated = True
            except Exception as exc:
                logger.debug("T3 claudeAgent.json sync skipped: %s", exc)

        # 2. Antigravity via T3 Code (antigravity.json)
        agy_file = self.t3_caches_dir / "antigravity.json"
        if agy_file.exists():
            try:
                mtime = agy_file.stat().st_mtime
                if mtime > self._t3_cache_mtimes.get("antigravity.json", 0.0):
                    self._t3_cache_mtimes["antigravity.json"] = mtime
                    data = json.loads(agy_file.read_text(encoding="utf-8", errors="ignore"))
                    ul = data.get("usageLimits") if isinstance(data, dict) else None
                    if isinstance(ul, dict) and isinstance(ul.get("windows"), list):
                        checked_ts = self._parse_iso_timestamp(ul.get("checkedAt")) or mtime
                        if checked_ts > multi_cli.agy.last_updated:
                            win_map = {
                                "gemini-5h": multi_cli.agy.gemini.five_hour,
                                "gemini-weekly": multi_cli.agy.gemini.weekly,
                                "3p-5h": multi_cli.agy.claude_gpt.five_hour,
                                "3p-weekly": multi_cli.agy.claude_gpt.weekly,
                            }
                            for w in ul["windows"]:
                                if not isinstance(w, dict) or w.get("usedPercent") is None:
                                    continue
                                target = win_map.get(w.get("id"))
                                if target is not None:
                                    _apply_window(target, w["usedPercent"], w.get("resetsAt"), checked_ts)
                            multi_cli.agy.gemini.last_synced_time = checked_ts
                            multi_cli.agy.claude_gpt.last_synced_time = checked_ts
                            multi_cli.agy.last_updated = checked_ts
                            any_updated = True
            except Exception as exc:
                logger.debug("T3 antigravity.json sync skipped: %s", exc)

        # 3. Codex via T3 Code (codex.json)
        codex_file = self.t3_caches_dir / "codex.json"
        if codex_file.exists():
            try:
                mtime = codex_file.stat().st_mtime
                if mtime > self._t3_cache_mtimes.get("codex.json", 0.0):
                    self._t3_cache_mtimes["codex.json"] = mtime
                    data = json.loads(codex_file.read_text(encoding="utf-8", errors="ignore"))
                    ul = data.get("usageLimits") if isinstance(data, dict) else None
                    if isinstance(ul, dict) and isinstance(ul.get("windows"), list):
                        checked_ts = self._parse_iso_timestamp(ul.get("checkedAt")) or mtime
                        if checked_ts > multi_cli.codex.last_synced_time:
                            for w in ul["windows"]:
                                if not isinstance(w, dict) or w.get("usedPercent") is None:
                                    continue
                                wid = w.get("id")
                                if wid == "primary":
                                    _apply_window(multi_cli.codex.five_hour, w["usedPercent"], w.get("resetsAt"), checked_ts)
                                elif wid == "secondary":
                                    _apply_window(multi_cli.codex.weekly, w["usedPercent"], w.get("resetsAt"), checked_ts)
                            multi_cli.codex.auto_detected = True
                            multi_cli.codex.last_synced_time = checked_ts
                            any_updated = True
            except Exception as exc:
                logger.debug("T3 codex.json sync skipped: %s", exc)

        if any_updated:
            save_multi_cli_state(multi_cli)

    def discover_latest_session(self) -> Optional[Path]:
        """
        Find the most recent conversation session in brain directory.
        Looks for directories containing transcript files.
        """
        candidates = self.scan_all_today_sessions()
        if not candidates:
            return None

        _, latest_session_dir, latest_transcript = candidates[0]

        if self.current_transcript_path != latest_transcript:
            self.current_session_dir = latest_session_dir
            self.current_transcript_path = latest_transcript
            self.last_mtime = 0
            self.last_file_size = 0
            self.last_seen_tokens = 0
            self.session_changed.emit(latest_session_dir.name, str(latest_transcript))

        return latest_session_dir

    def check_updates(self) -> None:
        """Scan file for new tokens or update simulated demo stats."""
        self.discover_latest_session()
        now = time.time()

        multi_cli = load_multi_cli_state()
        self.sync_local_agy_statusline(multi_cli)
        self.sync_local_claude_code_logs(multi_cli)
        self.sync_local_codex_usage(multi_cli)
        self.sync_local_t3_caches(multi_cli)

        if not self.current_transcript_path or not self.current_transcript_path.exists():
            if not self.cached_stats or not self.cached_stats.is_demo:
                self.cached_stats = self._generate_demo_stats(multi_cli)
                self.stats_updated.emit(self.cached_stats)
                self.status_changed.emit("Demo Mode (No active logs detected)")
            else:
                self.cached_stats.multi_cli = multi_cli
                self.stats_updated.emit(self.cached_stats)
            return

        try:
            stat_info = self.current_transcript_path.stat()
            current_mtime = stat_info.st_mtime
            current_size = stat_info.st_size

            file_changed = not (current_mtime == self.last_mtime and current_size == self.last_file_size)

            if file_changed:
                self.last_mtime = current_mtime
                self.last_file_size = current_size

                with open(self.current_transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                session_id = self.current_session_dir.name if self.current_session_dir else "active"
                stats = TokenParser.parse_transcript_lines(
                    lines,
                    session_id=session_id,
                    session_dir=str(self.current_session_dir),
                    multi_cli=multi_cli,
                )
                stats.last_updated = now
                stats.is_demo = False

                if stats.total_tokens > self.last_seen_tokens:
                    delta = stats.total_tokens - self.last_seen_tokens
                    if self.last_seen_tokens > 0:
                        self.token_events.append((now, delta))
                        self.last_activity_time = now
                    self.last_seen_tokens = stats.total_tokens

                day_tokens, day_cost, session_cnt = record_session_usage(
                    session_id=stats.session_id,
                    tokens=stats.total_tokens,
                    cost=stats.estimated_cost
                )
                stats.daily_tokens = day_tokens
                stats.daily_cost = day_cost
                stats.today_sessions_count = max(1, session_cnt)
                stats.daily_token_percent = min(100.0, (day_tokens / max(1, stats.daily_budget_tokens)) * 100.0)
                stats.daily_cost_percent = min(100.0, (day_cost / max(0.001, stats.daily_budget_usd)) * 100.0)

                stats.remaining_daily_tokens = max(0, stats.daily_budget_tokens - day_tokens)
                stats.remaining_daily_usd = max(0.0, round(stats.daily_budget_usd - day_cost, 4))
                stats.remaining_daily_percent = max(0.0, min(100.0, (stats.remaining_daily_tokens / max(1, stats.daily_budget_tokens)) * 100.0))

                self.cached_stats = stats

            elif self.cached_stats:
                stats = self.cached_stats
                stats.multi_cli = multi_cli

            else:
                return

            cutoff = now - 60.0
            while self.token_events and self.token_events[0][0] < cutoff:
                self.token_events.popleft()

            stats.tpm = TokenParser.compute_tpm(list(self.token_events), window_seconds=60.0, current_time=now)
            stats.is_generating = (now - self.last_activity_time) < 3.5

            self._sync_other_cli_histories(multi_cli)
            self._attach_historical_usage(stats)

            self.stats_updated.emit(stats)
            if not stats.is_demo:
                self.status_changed.emit(f"Tracking: {stats.session_id[:8]}... ({stats.total_steps} turns)")

        except PermissionError:
            pass
        except Exception as e:
            logger.error(f"Error reading transcript: {e}")
            self.status_changed.emit(f"Read error: {str(e)[:30]}")

    def _sync_other_cli_histories(self, multi_cli: MultiCliQuotaState) -> None:
        """
        Launch a throttled background thread to scan 30-day local logs (AGY, Claude Code, Codex)
        so the UI thread is never blocked during startup or polling.
        """
        now_mono = time.monotonic()
        if self._history_thread_running or (now_mono - self._history_last_scan_at < 30.0):
            return
        self._history_last_scan_at = now_mono
        self._history_thread_running = True

        def _worker() -> None:
            try:
                self._scan_30day_histories_worker(multi_cli)
            finally:
                self._history_thread_running = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _scan_30day_histories_worker(self, multi_cli: MultiCliQuotaState) -> None:
        """Background worker that backfills 30-day AGY, Claude Code, and Codex usage."""
        today_date = datetime.date.today()

        # 0. AGY older sessions (1~29 days ago)
        if self.brain_dir.exists() and self.brain_dir.is_dir():
            try:
                for session_folder in self.brain_dir.iterdir():
                    if not session_folder.is_dir():
                        continue
                    for rel in (
                        Path(".system_generated") / "logs" / "transcript.jsonl",
                        Path("transcript.jsonl"),
                    ):
                        tf = session_folder / rel
                        if not tf.exists():
                            continue
                        try:
                            mtime = tf.stat().st_mtime
                            mod_date = datetime.date.fromtimestamp(mtime)
                            days_ago = (today_date - mod_date).days
                            if not (1 <= days_ago < 30):
                                break
                            cache_key = f"agy:{tf}"
                            if self._synced_file_mtimes.get(cache_key) == mtime:
                                break
                            with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                                lines = f.readlines()
                            s_stats = TokenParser.parse_transcript_lines(
                                lines,
                                session_id=session_folder.name,
                                session_dir=str(session_folder),
                            )
                            record_session_usage(
                                session_folder.name,
                                s_stats.total_tokens,
                                s_stats.estimated_cost,
                                date_str=mod_date.isoformat(),
                                cli_id=CLI_AGY,
                            )
                            self._synced_file_mtimes[cache_key] = mtime
                        except Exception:
                            pass
                        break
            except Exception:
                pass

        # 1. Claude Code local logs (~/.claude/projects/*/*.jsonl)
        projects_dir = self.claude_dir / "projects"
        if projects_dir.exists() and projects_dir.is_dir():
            try:
                for proj in projects_dir.iterdir():
                    if not proj.is_dir():
                        continue
                    for log_file in proj.glob("*.jsonl"):
                        try:
                            mtime = log_file.stat().st_mtime
                            mod_date = datetime.date.fromtimestamp(mtime)
                            if not (0 <= (today_date - mod_date).days < 30):
                                continue
                            cache_key = f"claude:{log_file}"
                            if self._synced_file_mtimes.get(cache_key) == mtime:
                                continue
                            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                                lines = f.readlines()
                            c_stats = TokenParser.parse_transcript_lines(
                                lines,
                                session_id=log_file.stem,
                                session_dir=str(proj),
                                multi_cli=multi_cli,
                            )
                            if c_stats.total_tokens > 0:
                                record_cli_session_usage(
                                    CLI_CLAUDE_CODE,
                                    log_file.stem,
                                    c_stats.total_tokens,
                                    c_stats.estimated_cost,
                                    date_str=mod_date.isoformat(),
                                )
                            self._synced_file_mtimes[cache_key] = mtime
                        except Exception:
                            pass
            except Exception:
                pass

        # 2. Codex local logs (~/.codex/sessions/**/*.jsonl)
        if self.codex_sessions_dir.exists() and self.codex_sessions_dir.is_dir():
            try:
                for log_file in self.codex_sessions_dir.rglob("*.jsonl"):
                    try:
                        mtime = log_file.stat().st_mtime
                        mod_date = datetime.date.fromtimestamp(mtime)
                        if not (0 <= (today_date - mod_date).days < 30):
                            continue
                        cache_key = f"codex:{log_file}"
                        if self._synced_file_mtimes.get(cache_key) == mtime:
                            continue
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        x_stats = TokenParser.parse_transcript_lines(
                            lines,
                            session_id=log_file.stem,
                            session_dir=str(log_file.parent),
                            multi_cli=multi_cli,
                        )
                        if x_stats.total_tokens > 0:
                            record_cli_session_usage(
                                CLI_CODEX,
                                log_file.stem,
                                x_stats.total_tokens,
                                x_stats.estimated_cost,
                                date_str=mod_date.isoformat(),
                            )
                        self._synced_file_mtimes[cache_key] = mtime
                    except Exception:
                        pass
            except Exception:
                pass

    def _attach_historical_usage(self, stats: SessionTokenStats) -> None:
        """Populate Today / Yesterday / 30-Day local summaries onto SessionTokenStats."""
        settings = load_settings()
        agy_summary = get_usage_history_summary(cli_id=CLI_AGY, settings=settings)
        stats.yesterday_tokens = agy_summary["yesterday_tokens"]
        stats.yesterday_cost = agy_summary["yesterday_cost"]
        stats.last_30_days_tokens = agy_summary["last_30_days_tokens"]
        stats.last_30_days_cost = agy_summary["last_30_days_cost"]
        stats.daily_token_series = agy_summary["daily_series"]
        stats.cli_usage_summaries = {
            cli_id: get_usage_history_summary(cli_id=cli_id, settings=settings)
            for cli_id in ALL_CLIS
        }

    def _generate_demo_stats(self, multi_cli: Optional[MultiCliQuotaState] = None) -> SessionTokenStats:
        """Generate demo data with Multi-CLI quota focus when no active transcript is found."""
        now = time.time()
        context_limit = 2_000_000
        total_tokens = 125400
        budget_tokens = 5_000_000
        budget_usd = 2.00
        cost = 0.0342
        remaining_tokens = budget_tokens - total_tokens
        remaining_usd = budget_usd - cost
        rem_pct = (remaining_tokens / budget_tokens) * 100.0
        rem_ctx = context_limit - total_tokens
        rem_ctx_pct = (rem_ctx / context_limit) * 100.0

        stats = SessionTokenStats(
            session_id="demo-session-preview",
            session_dir="C:/Users/User/.gemini/antigravity-cli/brain/demo",
            last_updated=now,
            total_steps=18,
            total_input_tokens=94200,
            total_output_tokens=31200,
            total_tokens=total_tokens,
            delta_tokens=1240,
            delta_input=340,
            delta_output=900,
            estimated_cost=cost,
            current_model="Gemini 2.5 Pro",
            is_demo=True,
            multi_cli=multi_cli or load_multi_cli_state(),
            context_limit=context_limit,
            context_percent=(total_tokens / context_limit) * 100.0,
            remaining_context_tokens=rem_ctx,
            remaining_context_percent=rem_ctx_pct,
            tpm=24200,
            is_generating=True,
            daily_tokens=total_tokens,
            daily_cost=cost,
            daily_budget_tokens=budget_tokens,
            daily_budget_usd=budget_usd,
            daily_token_percent=(total_tokens / budget_tokens) * 100.0,
            daily_cost_percent=(cost / budget_usd) * 100.0,
            today_sessions_count=1,
            remaining_daily_tokens=remaining_tokens,
            remaining_daily_usd=remaining_usd,
            remaining_daily_percent=rem_pct,
        )
        self._attach_historical_usage(stats)
        return stats
