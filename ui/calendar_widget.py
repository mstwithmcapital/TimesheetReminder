from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QCalendarWidget

from database import Database

GREEN_BG = QColor("#c8e6c9")
GREEN_FG = QColor("#1b5e20")
RED_BG = QColor("#ffcdd2")
RED_FG = QColor("#b71c1c")


class TimesheetCalendar(QCalendarWidget):
    date_selected = pyqtSignal(QDate)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._day_totals: dict[int, float] = {}
        self._displayed_year = QDate.currentDate().year()
        self._displayed_month = QDate.currentDate().month()

        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setMinimumSize(380, 280)

        self.selectionChanged.connect(self._on_selection_changed)
        self.currentPageChanged.connect(self._on_page_changed)

        self.refresh_month(self._displayed_year, self._displayed_month)

    def refresh_month(self, year: int, month: int):
        self._displayed_year = year
        self._displayed_month = month
        totals = self.db.get_daily_totals_for_month(year, month)
        # Map day-of-month (int) -> hours
        self._day_totals = {
            int(k.split("-")[2]): v for k, v in totals.items()
        }
        self.update()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        # Only color cells belonging to the currently displayed month
        if date.month() != self._displayed_month or date.year() != self._displayed_year:
            super().paintCell(painter, rect, date)
            return

        total = self._day_totals.get(date.day(), 0.0)

        if total >= 8.5:
            bg, fg = GREEN_BG, GREEN_FG
        elif total > 0:
            bg, fg = RED_BG, RED_FG
        else:
            super().paintCell(painter, rect, date)
            return

        painter.save()
        painter.fillRect(rect, bg)

        # Highlight today with a border
        if date == QDate.currentDate():
            painter.setPen(Qt.darkBlue)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        painter.setPen(fg)
        painter.drawText(rect, Qt.AlignCenter, str(date.day()))
        painter.restore()

    def _on_selection_changed(self):
        self.date_selected.emit(self.selectedDate())

    def _on_page_changed(self, year: int, month: int):
        self.refresh_month(year, month)
