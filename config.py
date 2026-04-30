import json
import os
from pathlib import Path

_CONFIG_FILE = Path(os.getenv("APPDATA", "")) / "TimesheetReminder" / "config.json"

_DEFAULT_DAILY_TASKS = [
    {
        "project_name": "Internal Meeting",
        "job_no": "Intech",
        "job_task_no": "1501",
        "description": "Daily standup / internal meeting",
        "billability": "Non-Billable",
        "hours": 0.5,
    }
]

_DEFAULTS: dict = {
    "reminder_interval_hours": 1.0,   # hours between work-popup reminders
    "work_start_hour": 11,            # 11:00 AM — earliest popup
    "work_start_minute": 0,
    "work_end_hour": 19,              # 7:30 PM — latest popup
    "work_end_minute": 30,
    "daily_target_hours": 8.5,        # green threshold in calendar / detail panel
    "eod_reminder_hour": 19,          # end-of-day dialog trigger (19:25 default)
    "eod_reminder_minute": 25,
    "pre_eod_warning_minutes": 60,    # start frequent reminders this many minutes before work_end
    "pre_eod_interval_minutes": 10,   # reminder interval during pre-EOD window
    "daily_tasks": _DEFAULT_DAILY_TASKS,
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
        self.pre_eod_warning_minutes: int = _DEFAULTS["pre_eod_warning_minutes"]
        self.pre_eod_interval_minutes: int = _DEFAULTS["pre_eod_interval_minutes"]
        self.daily_tasks: list[dict] = [dict(t) for t in _DEFAULT_DAILY_TASKS]

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
            self.pre_eod_warning_minutes = int(
                data.get("pre_eod_warning_minutes", _DEFAULTS["pre_eod_warning_minutes"])
            )
            self.pre_eod_interval_minutes = int(
                data.get("pre_eod_interval_minutes", _DEFAULTS["pre_eod_interval_minutes"])
            )

            # New list format
            if "daily_tasks" in data and isinstance(data["daily_tasks"], list):
                self.daily_tasks = data["daily_tasks"]
            elif "daily_task_project_name" in data:
                # Migrate old single-task fields to list format
                self.daily_tasks = [{
                    "project_name": str(data.get("daily_task_project_name", _DEFAULT_DAILY_TASKS[0]["project_name"])),
                    "job_no":       str(data.get("daily_task_job_no",       _DEFAULT_DAILY_TASKS[0]["job_no"])),
                    "job_task_no":  str(data.get("daily_task_job_task_no",  _DEFAULT_DAILY_TASKS[0]["job_task_no"])),
                    "description":  str(data.get("daily_task_description",  _DEFAULT_DAILY_TASKS[0]["description"])),
                    "billability":  str(data.get("daily_task_billability",  _DEFAULT_DAILY_TASKS[0]["billability"])),
                    "hours":       float(data.get("daily_task_hours",       _DEFAULT_DAILY_TASKS[0]["hours"])),
                }]
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
            "pre_eod_warning_minutes": self.pre_eod_warning_minutes,
            "pre_eod_interval_minutes": self.pre_eod_interval_minutes,
            "daily_tasks": self.daily_tasks,
        }
        tmp = self.CONFIG_FILE.parent / "_config_tmp.json"
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.CONFIG_FILE)
