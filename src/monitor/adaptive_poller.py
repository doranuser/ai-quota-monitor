"""
Adaptive Polling Engine: Background QThread that auto-runs 'agy /usage'
at dynamically adjusted intervals based on current quota remaining %.
Never blocks the UI thread.
"""

import logging
import threading
import time
from typing import Optional

from PySide6.QtCore import QThread, Signal

from .cli_runner import AGY_EXECUTABLE, find_agy_executable, run_agy_usage

logger = logging.getLogger(__name__)


def compute_poll_interval(min_remaining_pct: float, is_active: bool) -> int:
    """
    Return the next polling interval in seconds based on quota health.

    Args:
        min_remaining_pct: The lowest remaining % across all monitored CLIs.
        is_active:         True when TPM > 0 (AI is actively generating).

    Interval table:
        > 40% + idle    → 1800s (30 min)
        > 40% + active  →  300s ( 5 min)
        20–40%          →  180s ( 3 min)
        5–20%           →   60s ( 1 min)
        < 5%            →   30s (30 sec)
    """
    if min_remaining_pct > 40.0:
        return 300 if is_active else 1800
    if min_remaining_pct > 20.0:
        return 180
    if min_remaining_pct > 5.0:
        return 60
    return 30


class AdaptivePoller(QThread):
    """
    Background thread that periodically calls 'agy /usage', parses the
    output, and emits signals to update the UI.

    Signals:
        usage_updated(str):    Emitted with raw /usage text on success.
        sync_status(str):      Human-readable status line for the UI bar.
        sync_failed(int):      Emitted with consecutive-failure count.
        sync_completed(bool):  Emitted with True/False when a sync operation finishes.
    """

    usage_updated = Signal(str)
    sync_status = Signal(str)
    sync_failed = Signal(int)
    sync_completed = Signal(bool)

    # After this many consecutive failures, downgrade to manual mode.
    MAX_FAILURES = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_flag = False
        self._force_now = True
        self._consecutive_failures = 0
        self._last_sync_ts: Optional[float] = None
        self._next_sync_ts: Optional[float] = None
        self._min_remaining_pct: float = 100.0
        self._is_active: bool = False
        self._wake_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API (called from the main thread)
    # ------------------------------------------------------------------

    def update_state(self, min_remaining_pct: float, is_active: bool) -> None:
        """Called by the main window whenever quota state changes."""
        self._min_remaining_pct = min_remaining_pct
        self._is_active = is_active

    def force_sync(self) -> None:
        """Trigger an immediate sync with zero sleep delay."""
        self._force_now = True
        self._wake_event.set()

    def stop(self) -> None:
        self._stop_flag = True
        self._wake_event.set()
        self.quit()

    # ------------------------------------------------------------------
    # Thread body
    # ------------------------------------------------------------------

    def run(self) -> None:
        exe = AGY_EXECUTABLE or find_agy_executable()
        if not exe:
            self.sync_status.emit("AUTO-SYNC UNAVAILABLE  |  [ FALLBACK SYNC AVAILABLE ]")
            return

        logger.info("AdaptivePoller started. agy path: %s", exe)
        self.sync_status.emit("AUTO-SYNC ON  |  Initializing...")

        while not self._stop_flag:
            # Check if this iteration was triggered by force_now or normal cycle
            is_forced = self._force_now
            self._force_now = False
            self._wake_event.clear()

            if not is_forced:
                interval = compute_poll_interval(self._min_remaining_pct, self._is_active)
                self._next_sync_ts = time.time() + interval

                # Sleep in small ticks to update live countdown and allow quick interrupt
                elapsed = 0
                while elapsed < interval and not self._stop_flag:
                    # Wait up to 1 second on wake event
                    if self._wake_event.wait(timeout=1.0):
                        self._wake_event.clear()
                        if self._stop_flag:
                            break
                        if self._force_now:
                            self._force_now = False
                            break

                    elapsed += 1
                    # Emit live countdown every 5 seconds
                    if elapsed % 5 == 0 and not self._stop_flag:
                        remaining_s = max(0, interval - elapsed)
                        self._emit_status(remaining_s)

            if self._stop_flag:
                break

            # --- Run agy /usage ---
            self._emit_status(0, syncing=True)
            raw = run_agy_usage(timeout=12)

            if raw:
                self._consecutive_failures = 0
                self._last_sync_ts = time.time()
                next_interval = compute_poll_interval(self._min_remaining_pct, self._is_active)
                self._next_sync_ts = self._last_sync_ts + next_interval
                self.usage_updated.emit(raw)
                self.sync_completed.emit(True)
                self._emit_status(next_interval)
            else:
                self._consecutive_failures += 1
                logger.warning("Sync failed (%d/%d)", self._consecutive_failures, self.MAX_FAILURES)
                self.sync_failed.emit(self._consecutive_failures)
                self.sync_completed.emit(False)
                if self._consecutive_failures >= self.MAX_FAILURES:
                    self.sync_status.emit(
                        f"AUTO-SYNC FAILED ({self.MAX_FAILURES}x)  |  [ FALLBACK SYNC AVAILABLE ]"
                    )
                    break  # Downgrade to manual mode

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_status(self, next_in_s: int, syncing: bool = False) -> None:
        """Build and emit the status bar string shown in the drawer."""
        last_str = self._format_last_sync()
        if syncing:
            status = f"AUTO-SYNC ON  |  {last_str}  |  SYNCING..."
        elif next_in_s > 0:
            next_str = self._format_duration(next_in_s)
            status = f"AUTO-SYNC ON  |  {last_str}  |  NEXT SYNC in {next_str}"
        else:
            status = f"AUTO-SYNC ON  |  {last_str}  |  SYNC NOW..."
        self.sync_status.emit(status)

    def _format_last_sync(self) -> str:
        if self._last_sync_ts is None:
            return "LAST SYNC never"
        ago = int(time.time() - self._last_sync_ts)
        if ago < 10:
            return "LAST SYNC just now"
        return f"LAST SYNC {self._format_duration(ago)} ago"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}m {s:02d}s" if s else f"{m}m"
        h, rem = divmod(seconds, 3600)
        m = rem // 60
        return f"{h}h {m}m" if m else f"{h}h"
