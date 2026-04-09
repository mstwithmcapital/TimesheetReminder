import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


class AppState:
    STATE_FILE = Path(os.getenv("APPDATA", "")) / "TimesheetReminder" / "state.json"

    def __init__(self):
        self.last_popup_time: datetime | None = None        # when user last SAVED a popup entry
        self.last_popup_shown_time: datetime | None = None  # when popup last appeared (for throttle)
        self.first_launch_date: str | None = None
        self.weekly_submitted_for: str | None = None
        self.saturday_submitted_for: str | None = None
        self.eod_shown_for: str | None = None  # 'YYYY-MM-DD' — guard against repeat EOD dialog

    def load(self):
        if not self.STATE_FILE.exists():
            return
        try:
            data = json.loads(self.STATE_FILE.read_text(encoding="utf-8"))
            raw = data.get("last_popup_time")
            self.last_popup_time = datetime.fromisoformat(raw) if raw else None
            raw2 = data.get("last_popup_shown_time")
            self.last_popup_shown_time = datetime.fromisoformat(raw2) if raw2 else None
            self.first_launch_date = data.get("first_launch_date")
            self.weekly_submitted_for = data.get("weekly_submitted_for")
            self.saturday_submitted_for = data.get("saturday_submitted_for")
            self.eod_shown_for = data.get("eod_shown_for")
        except Exception:
            pass

    def save(self):
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_popup_time": self.last_popup_time.isoformat() if self.last_popup_time else None,
            "last_popup_shown_time": self.last_popup_shown_time.isoformat() if self.last_popup_shown_time else None,
            "first_launch_date": self.first_launch_date,
            "weekly_submitted_for": self.weekly_submitted_for,
            "saturday_submitted_for": self.saturday_submitted_for,
            "eod_shown_for": self.eod_shown_for,
        }
        tmp = self.STATE_FILE.parent / "_state_tmp.json"
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.STATE_FILE)

    # ── Popup timing ──────────────────────────────────────────────────────────

    def hours_since_last_popup(self) -> float:
        if self.last_popup_time is None:
            return 1.0
        delta = (datetime.now() - self.last_popup_time.replace(tzinfo=None)).total_seconds()
        hours = delta / 3600.0
        # Round to nearest 0.25, clamp to [0.25, 4.0]
        rounded = round(round(hours / 0.25) * 0.25, 2)
        return max(0.25, min(rounded, 4.0))

    def record_popup_shown(self):
        """Call when a popup is displayed — updates throttle timer."""
        self.last_popup_shown_time = datetime.now()
        self.save()

    def record_popup_saved(self):
        """Call when user saves an entry in the popup — updates hours-since-last calculation."""
        self.last_popup_time = datetime.now()
        self.save()

    # ── First launch guard ────────────────────────────────────────────────────

    def has_launched_today(self, date_str: str) -> bool:
        return self.first_launch_date == date_str

    def mark_first_launch_today(self, date_str: str):
        self.first_launch_date = date_str

    # ── EOD dialog guard ──────────────────────────────────────────────────────

    def has_shown_eod_today(self, date_str: str) -> bool:
        return self.eod_shown_for == date_str

    def mark_eod_shown_today(self, date_str: str):
        self.eod_shown_for = date_str
        self.save()

    # ── Submission flags ──────────────────────────────────────────────────────

    def mark_weekly_submitted(self):
        self.weekly_submitted_for = _current_iso_week()
        self.save()

    def mark_saturday_submitted(self):
        self.saturday_submitted_for = _current_iso_month()
        self.save()

    def is_weekly_submitted_this_week(self) -> bool:
        return self.weekly_submitted_for == _current_iso_week()

    def is_saturday_submitted_this_month(self) -> bool:
        return self.saturday_submitted_for == _current_iso_month()


def _current_iso_week() -> str:
    iso = datetime.now().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _current_iso_month() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"
