import json
import os
from pathlib import Path

_CONFIG_FILE = Path(os.getenv("APPDATA", "")) / "TimesheetReminder" / "config.json"

_DEFAULTS: dict = {
    "reminder_interval_hours": 1.0,   # hours between work-popup reminders
    "work_start_hour": 11,            # 11:00 AM — earliest popup
    "work_start_minute": 0,
    "work_end_hour": 19,              # 7:30 PM — latest popup
    "work_end_minute": 30,
    "daily_target_hours": 8.5,        # green threshold in calendar / detail panel
    "eod_reminder_hour": 19,          # end-of-day dialog trigger (19:25 default)
    "eod_reminder_minute": 25,
}


class AppConfig:
    """
    Persistent user configuration stored at
    %APPDATA%\\TimesheetReminder\\config.json.

    All fields fall back to _DEFAULTS on first run or if the file is corrupt.
    """

    CONFIG_FILE = _CONFIG_FILE

    def __init__(self) -> None:
        self.reminder_interval_hours: float = _DEFAULTS["reminder_interval_hours"]
        self.work_start_hour: int = _DEFAULTS["work_start_hour"]
        self.work_start_minute: int = _DEFAULTS["work_start_minute"]
        self.work_end_hour: int = _DEFAULTS["work_end_hour"]
        self.work_end_minute: int = _DEFAULTS["work_end_minute"]
        self.daily_target_hours: float = _DEFAULTS["daily_target_hours"]
        self.eod_reminder_hour: int = _DEFAULTS["eod_reminder_hour"]
        self.eod_reminder_minute: int = _DEFAULTS["eod_reminder_minute"]

    # ── Persistence ───────────────────────────────────────────────────────────

    def load(self) -> None:
        if not self.CONFIG_FILE.exists():
            return
        try:
            data: dict = json.loads(self.CONFIG_FILE.read_text(encoding="utf-8"))
            self.reminder_interval_hours = float(
                data.get("reminder_interval_hours", _DEFAULTS["reminder_interval_hours"])
            )
            self.work_start_hour = int(data.get("work_start_hour", _DEFAULTS["work_start_hour"]))
            self.work_start_minute = int(data.get("work_start_minute", _DEFAULTS["work_start_minute"]))
            self.work_end_hour = int(data.get("work_end_hour", _DEFAULTS["work_end_hour"]))
            self.work_end_minute = int(data.get("work_end_minute", _DEFAULTS["work_end_minute"]))
            self.daily_target_hours = float(
                data.get("daily_target_hours", _DEFAULTS["daily_target_hours"])
            )
            self.eod_reminder_hour = int(data.get("eod_reminder_hour", _DEFAULTS["eod_reminder_hour"]))
            self.eod_reminder_minute = int(
                data.get("eod_reminder_minute", _DEFAULTS["eod_reminder_minute"])
            )
        except Exception:
            pass  # silently keep defaults if file is malformed

    def save(self) -> None:
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "reminder_interval_hours": self.reminder_interval_hours,
            "work_start_hour": self.work_start_hour,
            "work_start_minute": self.work_start_minute,
            "work_end_hour": self.work_end_hour,
            "work_end_minute": self.work_end_minute,
            "daily_target_hours": self.daily_target_hours,
            "eod_reminder_hour": self.eod_reminder_hour,
            "eod_reminder_minute": self.eod_reminder_minute,
        }
        tmp = self.CONFIG_FILE.parent / "_config_tmp.json"
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.CONFIG_FILE)
