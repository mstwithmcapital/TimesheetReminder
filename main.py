import os
import sys
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from database import Database
from scheduler import SchedulerBridge, SchedulerThread
from state import AppState
from ui.main_window import MainWindow


def register_startup():
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
        f'WshShell.Run Chr(34) & "{python_exe}" & Chr(34) & " " & Chr(34) & "{script_path}" & Chr(34), 0, False\n'
    )
    try:
        vbs_path.write_text(vbs_content, encoding="utf-8")
    except Exception as e:
        print(f"[TimesheetTracker] Could not register startup: {e}", file=sys.stderr)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep running when window is hidden
    app.setApplicationName("Timesheet Tracker")

    register_startup()

    db = Database()
    db.initialize()

    state = AppState()
    state.load()

    # Auto-add "Internal Meeting" (0.5h) on first launch of each day
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
    window = MainWindow(db, state, bridge)

    SchedulerThread(bridge, state).start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
