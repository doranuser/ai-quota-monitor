"""
CLI Runner: Auto-detects the 'agy' command and executes '/usage' safely
in a background thread without blocking the UI.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import sys

logger = logging.getLogger(__name__)

# Preferred native binary locations for agy on Windows (avoids npm.cmd wrapper popup)
_AGY_FALLBACK_PATHS = [
    Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe",
    Path.home() / "AppData" / "Local" / "Programs" / "agy" / "agy.exe",
    Path("C:/Program Files/agy/agy.exe"),
    Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.cmd",
    Path.home() / "AppData" / "Roaming" / "npm" / "agy.cmd",
    Path.home() / "AppData" / "Roaming" / "npm" / "agy.exe",
    Path.home() / "AppData" / "Local" / "Programs" / "agy" / "agy.cmd",
]


def find_agy_executable() -> Optional[str]:
    """Locate the agy executable, prioritizing native agy.exe over npm wrapper."""
    # Check native agy.exe first to completely bypass npm exec / cmd wrapper
    for path in _AGY_FALLBACK_PATHS:
        if path.suffix == ".exe" and path.exists():
            return str(path)

    # Fallback to which
    found = shutil.which("agy.exe") or shutil.which("agy") or shutil.which("agy.cmd")
    if found:
        return found

    for path in _AGY_FALLBACK_PATHS:
        if path.exists():
            return str(path)
    return None


AGY_EXECUTABLE: Optional[str] = find_agy_executable()


def run_agy_usage(timeout: int = 10) -> Optional[str]:
    """
    Execute 'agy -p /usage' completely invisibly in background with zero window popups.
    Uses CREATE_NO_WINDOW and STARTUPINFO(SW_HIDE) on Windows.
    """
    global AGY_EXECUTABLE
    if not AGY_EXECUTABLE or not Path(AGY_EXECUTABLE).exists():
        AGY_EXECUTABLE = find_agy_executable()
    if not AGY_EXECUTABLE:
        logger.warning("agy executable not found. Cannot auto-sync.")
        return None

    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    try:
        result = subprocess.run(
            [AGY_EXECUTABLE, "-p", "/usage"],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        logger.warning("agy /usage returned non-zero or empty: %s", result.stderr[:200])
        return None
    except subprocess.TimeoutExpired:
        logger.error("agy /usage timed out after %ss", timeout)
        return None
    except Exception as exc:
        logger.error("Failed to run agy /usage: %s", exc)
        return None
