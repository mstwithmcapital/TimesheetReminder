import threading
import time
from datetime import date, datetime, timedelta

import schedule
from PyQt5.QtCore import QObject, pyqtSignal

from config import AppConfig
from state import AppState

WEEKLY_REMINDER_H = 16    # Friday 4 PM — not user-configurable yet
SATURDAY_REMINDER_H = 10  # first Saturday 10 AM — not user-configurable yet


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
    def __init__(self, bridge: SchedulerBridge, state: AppState, config: AppConfig) -> None:
        super().__init__(daemon=True, name="scheduler")
        self.bridge = bridge
        self.state = state
        self.config = config
        self._last_hourly_check: datetime | None = None

    def run(self) -> None:
        # Check every 60 seconds; individual methods guard their own timing.
        schedule.every(1).minutes.do(self._check_hourly)
        schedule.every(1).minutes.do(self._check_eod)
        schedule.every(1).minutes.do(self._check_weekly)
        schedule.every(1).minutes.do(self._check_saturday)

        while True:
            schedule.run_pending()
            time.sleep(30)

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_hourly(self) -> None:
        now = datetime.now()
        today = now.date()

        if not _is_workday(today):
            first_sat = _get_first_saturday(today.year, today.month)
            if today != first_sat:
                return

        # Use config for the active work window
        popup_start = now.replace(
            hour=self.config.work_start_hour,
            minute=self.config.work_start_minute,
            second=0, microsecond=0,
        )
        popup_end = now.replace(
            hour=self.config.work_end_hour,
            minute=self.config.work_end_minute,
            second=0, microsecond=0,
        )
        if not (popup_start <= now <= popup_end):
            return

        # Throttle: only fire once per configured interval
        interval_seconds = self.config.reminder_interval_hours * 3600 - 100  # 100 s buffer
        last = self.state.last_popup_time
        if last is not None:
            elapsed = (now - last.replace(tzinfo=None)).total_seconds()
            if elapsed < interval_seconds:
                return

        self.bridge.show_work_popup.emit()

    def _check_eod(self) -> None:
        now = datetime.now()
        today = now.date().isoformat()

        eod_start = now.replace(
            hour=self.config.eod_reminder_hour,
            minute=self.config.eod_reminder_minute,
            second=0, microsecond=0,
        )
        eod_end = eod_start + timedelta(minutes=10)
        if not (eod_start <= now <= eod_end):
            return

        if self.state.has_shown_eod_today(today):
            return

        self.bridge.show_eod_summary.emit()

    def _check_weekly(self) -> None:
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

    def _check_saturday(self) -> None:
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
