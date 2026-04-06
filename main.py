import ctypes
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from config import AppConfig
from database import Database
from scheduler import SchedulerBridge, SchedulerThread
from state import AppState
from ui.main_window import MainWindow


# ── Feature 1: run as a detached background process ───────────────────────────

def _ensure_background() -> None:
    """
    When the user launches the app from a terminal (VS Code, cmd, PowerShell),
    the process is a child of that terminal — closing it would kill the app.

    This function detects a live console window and re-launches the app via
    pythonw.exe with DETACHED_PROCESS | CREATE_NO_WINDOW flags so it survives
    independently of any terminal session.

    The --background flag prevents infinite re-launch loops.
    """
    if "--background" in sys.argv:
        return  # already running as the detached background instance

    try:
        # GetConsoleWindow() returns 0 when there is no attached console
        # (e.g. when launched by the Windows Startup VBS or a previous relaunch).
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd == 0:
            return  # no console — nothing to do
    except Exception:
        return  # not Windows or ctypes unavailable

    # pythonw.exe suppresses the console window entirely
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)  # fallback — at least stay alive

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000

    subprocess.Popen(
        [str(pythonw), str(Path(__file__).resolve()), "--background"],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
        cwd=str(Path(__file__).parent),
    )
    sys.exit(0)  # let the terminal process exit cleanly


# ── Windows auto-start registration ──────────────────────────────────────────

def _register_startup() -> None:
    """Register the app to auto-start with Windows (idempotent)."""
    startup_dir = (
        Path(os.getenv("APPDATA", ""))
        / "Microsoft/Windows/Start Menu/Programs/Startup"
    )
    vbs_path = startup_dir / "TimesheetTracker.vbs"
    if vbs_path.exists():
        return

    script_path = Path(__file__).resolve()
    python_exe = Path(sys.executable).parent / "pythonw.exe"
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run Chr(34) & "{python_exe}" & Chr(34) & " " & Chr(34) & "{script_path}" & Chr(34) & " --background", 0, False\n'
    )
    try:
        vbs_path.write_text(vbs_content, encoding="utf-8")
    except Exception as e:
        print(f"[TimesheetTracker] Could not register startup: {e}", file=sys.stderr)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    _ensure_background()   # re-launch silently if started from a terminal

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep alive when the window is hidden
    app.setApplicationName("Timesheet Tracker")

    _register_startup()

    # ── Feature 2: persistent local storage (SQLite + JSON state) ────────────
    # Data survives restarts automatically:
    #   database  → %APPDATA%\TimesheetReminder\timesheet.db  (SQLite)
    #   state     → %APPDATA%\TimesheetReminder\state.json
    #   config    → %APPDATA%\TimesheetReminder\config.json
    db = Database()
    db.initialize()

    state = AppState()
    state.load()

    # ── Feature 3: configurable reminder settings ─────────────────────────────
    config = AppConfig()
    config.load()

    # Auto-add "Internal Meeting" (0.5 h) on first launch of each day
    today = date.today().isoformat()
    if not state.has_launched_today(today):
        if not db.has_auto_entry_today(today):
            db.add_entry(
                today,
                "Internal Meeting",
                "",
                "Daily standup / internal meeting",
                "Non-Billable",
                0.5,
                is_auto_added=True,
            )
        state.mark_first_launch_today(today)
        state.save()

    bridge = SchedulerBridge()
    window = MainWindow(db, state, bridge, config)

    SchedulerThread(bridge, state, config).start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
