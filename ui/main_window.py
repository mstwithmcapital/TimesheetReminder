import os
from datetime import date, datetime
from pathlib import Path

from PyQt5.QtCore import QDate, Qt, QTimer
from PyQt5.QtWidgets import (
    QAction, QApplication, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QMainWindow, QMenu, QPushButton,
    QSizePolicy, QSplitter, QSystemTrayIcon, QTimeEdit, QToolBar,
    QVBoxLayout, QWidget,
)

from config import AppConfig
from database import Database
from scheduler import SchedulerBridge, SchedulerThread
from state import AppState
from ui.calendar_widget import TimesheetCalendar
from ui.day_detail_panel import DayDetailPanel
from ui.icons import make_app_icon


class MainWindow(QMainWindow):
    def __init__(
        self,
        db: Database,
        state: AppState,
        bridge: SchedulerBridge,
        config: AppConfig,
        scheduler: SchedulerThread = None,
    ) -> None:
        super().__init__()
        self.db = db
        self.state = state
        self.bridge = bridge
        self.config = config
        self._scheduler = scheduler
        self._session_start = datetime.now()

        self.setWindowTitle("Timesheet Tracker")
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(780, 520)
        self.resize(980, 640)

        self._build_ui()
        self._setup_tray()
        self._connect_signals()

        # Load today by default
        self.calendar.setSelectedDate(QDate.currentDate())

        # Set splitter proportions after the event loop starts so the window
        # geometry is finalised and the splitter gets real pixel values.
        QTimer.singleShot(0, self._init_splitter_sizes)

    def _init_splitter_sizes(self):
        total = self.splitter.width()
        self.splitter.setSizes([int(total * 0.38), int(total * 0.62)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep splitter proportions on every resize
        total = self.splitter.width()
        if total > 0:
            sizes = self.splitter.sizes()
            current_total = sum(sizes)
            if current_total > 0:
                ratio = sizes[0] / current_total
                self.splitter.setSizes([int(total * ratio), total - int(total * ratio)])

    def _build_ui(self) -> None:
        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        log_action = QAction("Log Work Now", self)
        log_action.triggered.connect(self.open_work_popup)
        toolbar.addAction(log_action)

        toolbar.addSeparator()

        export_action = QAction("Export Week to Excel", self)
        export_action.triggered.connect(self._export_week)
        toolbar.addAction(export_action)

        weekly_action = QAction("View Weekly Summary", self)
        weekly_action.triggered.connect(lambda: self.open_weekly_summary("weekly"))
        toolbar.addAction(weekly_action)

        toolbar.addSeparator()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        projects_action = QAction("Manage Projects & Tickets", self)
        projects_action.triggered.connect(self._open_project_manager)
        toolbar.addAction(projects_action)

        toolbar.addSeparator()

        minimize_action = QAction("Minimize", self)
        minimize_action.triggered.connect(self.showMinimized)
        toolbar.addAction(minimize_action)

        # ── Central splitter ──────────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.calendar = TimesheetCalendar(self.db, self.config)
        self.calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.addWidget(self.calendar)

        self.day_panel = DayDetailPanel(self.db, self.state, self.config)
        self.day_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.addWidget(self.day_panel)

        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)

        self.setCentralWidget(self.splitter)

        data_dir = str(Path(os.getenv("APPDATA", "")) / "TimesheetReminder")
        self.statusBar().showMessage(f"Data saved to: {data_dir}")
        self.statusBar().setStyleSheet("color: #555; font-size: 11px;")

        self._uptime_label = QPushButton()
        self._uptime_label.setFlat(True)
        self._uptime_label.setCursor(Qt.PointingHandCursor)
        self._uptime_label.setToolTip("Click to set work start time")
        self._uptime_label.clicked.connect(self._set_work_start_time)
        self.statusBar().addPermanentWidget(self._uptime_label)
        self._update_uptime_label()

        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime_label)
        self._uptime_timer.start(60_000)

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(make_app_icon())
        self.tray.setToolTip("Timesheet Tracker")

        menu = QMenu()
        open_action = menu.addAction("Open")
        open_action.triggered.connect(self._show_window)
        log_action = menu.addAction("Log Work Now")
        log_action.triggered.connect(self.open_work_popup)
        menu.addSeparator()
        minimize_tray_action = menu.addAction("Minimize to Tray")
        minimize_tray_action.triggered.connect(self.hide)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _connect_signals(self) -> None:
        self.calendar.date_selected.connect(self._on_date_selected)
        self.day_panel.entry_changed.connect(self._on_entry_changed)

        self.bridge.show_work_popup.connect(self.open_work_popup)
        self.bridge.show_eod_summary.connect(self.open_eod_dialog)
        self.bridge.show_weekly_summary.connect(self.open_weekly_summary)
        self.bridge.refresh_entries.connect(self._on_refresh_entries)
        self.bridge.show_uptime_alert.connect(self._on_uptime_alert)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_date_selected(self, qdate: QDate) -> None:
        date_str = qdate.toString("yyyy-MM-dd")
        self.day_panel.load_date(date_str)

    def _on_entry_changed(self, date_str: str) -> None:
        d = date.fromisoformat(date_str)
        self.calendar.refresh_month(d.year, d.month)

    def _on_refresh_entries(self) -> None:
        """Called when scheduler auto-adds a standup entry."""
        today = date.today().isoformat()
        self.day_panel.load_date(today)
        self.calendar.refresh_month(date.today().year, date.today().month)

    def open_work_popup(self) -> None:
        from ui.work_popup import WorkPopupDialog
        if getattr(self, "_popup_open", False):
            return
        self._popup_open = True
        self.state.record_popup_shown()
        try:
            dlg = WorkPopupDialog(self.db, self.state, add_mode=False, parent=self)
            if dlg.exec_() == WorkPopupDialog.Accepted:
                today = date.today().isoformat()
                self.day_panel.load_date(today)
                self.calendar.refresh_month(date.today().year, date.today().month)
        finally:
            self._popup_open = False

    def open_eod_dialog(self) -> None:
        from ui.end_of_day_dialog import EndOfDayDialog
        today = date.today().isoformat()
        dlg = EndOfDayDialog(self.db, self.state, date_str=today, parent=self)
        dlg.exec_()

    def open_weekly_summary(self, mode: str = "weekly") -> None:
        from ui.weekly_summary_dialog import WeeklySummaryDialog
        dlg = WeeklySummaryDialog(self.db, self.state, mode=mode, parent=self)
        dlg.exec_()

    def _open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.config, parent=self)
        if dlg.exec_() == SettingsDialog.Accepted:
            self.day_panel.refresh_target()
            today = date.today()
            self.calendar.refresh_month(today.year, today.month)

    def _open_project_manager(self) -> None:
        from ui.project_manager_dialog import ProjectManagerDialog
        dlg = ProjectManagerDialog(self.db, parent=self)
        dlg.exec_()

    def _export_week(self) -> None:
        from ui.export import export_week_to_excel
        today = date.today()
        iso = today.isocalendar()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Week to Excel",
            f"timesheet_week_{iso.year}_W{iso.week:02d}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if path:
            export_week_to_excel(self.db, iso.year, iso.week, path)
            self.tray.showMessage(
                "Export Complete",
                f"Saved to {path}",
                QSystemTrayIcon.Information, 3000
            )

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _update_uptime_label(self) -> None:
        total_seconds = (datetime.now() - self._session_start).total_seconds()
        total_minutes = int(total_seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        target_minutes = 9 * 60
        elapsed_str = f"{hours}h {minutes:02d}m"
        base_style = "font-size: 11px; border: none; background: transparent; padding: 0 6px 0 0;"
        if total_minutes >= target_minutes:
            self._uptime_label.setText(f"Uptime: {elapsed_str}  — take a break!")
            self._uptime_label.setStyleSheet(base_style + "color: #c62828; font-weight: bold;")
        else:
            remaining = target_minutes - total_minutes
            rem_h, rem_m = divmod(remaining, 60)
            rem_str = f"{rem_h}h {rem_m:02d}m" if rem_h else f"{rem_m}m"
            self._uptime_label.setText(f"Uptime: {elapsed_str}  ({rem_str} to 9h)")
            self._uptime_label.setStyleSheet(base_style + "color: #555;")

    def _set_work_start_time(self) -> None:
        from PyQt5.QtCore import QTime
        dlg = QDialog(self)
        dlg.setWindowTitle("Set Work Start Time")
        dlg.setFixedWidth(280)
        layout = QFormLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 12)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("hh:mm AP")
        time_edit.setTime(QTime(self._session_start.hour, self._session_start.minute))
        layout.addRow("Work started at:", time_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            t = time_edit.time()
            now = datetime.now()
            new_start = now.replace(hour=t.hour(), minute=t.minute(), second=0, microsecond=0)
            if new_start > now:
                new_start = now
            self._session_start = new_start
            if self._scheduler:
                self._scheduler.set_session_start(new_start)
            self._update_uptime_label()

    def _on_uptime_alert(self) -> None:
        self.tray.showMessage(
            "9-Hour Uptime Reached",
            "Your PC has been running for 9 hours. Time to save your work and take a break!",
            QSystemTrayIcon.Information,
            10000,
        )

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Timesheet Tracker",
            "App is still running in the system tray.",
            QSystemTrayIcon.Information, 2000
        )
