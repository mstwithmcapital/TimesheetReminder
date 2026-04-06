import threading
import time
from datetime import date, datetime, timedelta

import schedule
from PyQt5.QtCore import QObject, pyqtSignal

from state import AppState

POPUP_START_H = 11
POPUP_END_H = 19
POPUP_END_M = 30
EOD_H = 19
EOD_M = 25   # trigger window start (fires once between 19:25–19:35)
EOD_WINDOW = 10  # minutes
WEEKLY_REMINDER_H = 16
SATURDAY_REMINDER_H = 10


def _is_workday(d: date) -> bool:
    return d.weekday() < 5  # Mon–Fri


def _get_first_saturday(year: int, month: int) -> date:
    d = date(year, month, 1)
    days = (5 - d.weekday()) % 7
    return d + timedelta(days=days)


class SchedulerBridge(QObject):
    """Lives in the Qt main thread. All signals are thread-safe."""
    show_work_popup = pyqtSignal()
    show_eod_summary = pyqtSignal()
    show_weekly_summary = pyqtSignal(str)   # "weekly" | "saturday"


class SchedulerThread(threading.Thread):
    def __init__(self, bridge: SchedulerBridge, state: AppState):
        super().__init__(daemon=True, name="scheduler")
        self.bridge = bridge
        self.state = state
        self._last_hourly_check: datetime | None = None

    def run(self):
        # Check every 60 seconds; individual jobs guard their own timing
        schedule.every(1).minutes.do(self._check_hourly)
        schedule.every(1).minutes.do(self._check_eod)
        schedule.every(1).minutes.do(self._check_weekly)
        schedule.every(1).minutes.do(self._check_saturday)

        while True:
            schedule.run_pending()
            time.sleep(30)

    def _check_hourly(self):
        now = datetime.now()
        today = now.date()

        if not _is_workday(today):
            # Also allow first Saturday
            first_sat = _get_first_saturday(today.year, today.month)
            if today != first_sat:
                return

        popup_start = now.replace(hour=POPUP_START_H, minute=0, second=0, microsecond=0)
        popup_end = now.replace(hour=POPUP_END_H, minute=POPUP_END_M, second=0, microsecond=0)
        if not (popup_start <= now <= popup_end):
            return

        # Throttle: only fire once per hour
        last = self.state.last_popup_time
        if last is not None:
            elapsed = (now - last.replace(tzinfo=None)).total_seconds()
            if elapsed < 3500:  # ~1 hour with small buffer
                return

        self.bridge.show_work_popup.emit()

    def _check_eod(self):
        now = datetime.now()
        today = now.date().isoformat()

        # Only fire in the 19:25–19:35 window, once per day
        eod_start = now.replace(hour=EOD_H, minute=EOD_M, second=0, microsecond=0)
        eod_end = eod_start + timedelta(minutes=EOD_WINDOW)
        if not (eod_start <= now <= eod_end):
            return

        if self.state.has_shown_eod_today(today):
            return

        self.bridge.show_eod_summary.emit()

    def _check_weekly(self):
        now = datetime.now()
        if now.weekday() != 4:  # Friday only
            return
        if now.hour < WEEKLY_REMINDER_H:
            return
        if self.state.is_weekly_submitted_this_week():
            return
        # Throttle to every 30 min
        if self._last_hourly_check is not None:
            if (now - self._last_hourly_check).total_seconds() < 1800:
                return
        self._last_hourly_check = now
        self.bridge.show_weekly_summary.emit("weekly")

    def _check_saturday(self):
        now = datetime.now()
        today = now.date()
        first_sat = _get_first_saturday(today.year, today.month)
        if today != first_sat:
            return
        if now.hour < SATURDAY_REMINDER_H:
            return
        if self.state.is_saturday_submitted_this_month():
            return
        self.bridge.show_weekly_summary.emit("saturday")
