from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QTimeEdit, QVBoxLayout,
)

from config import AppConfig


class SettingsDialog(QDialog):
    """
    User-facing dialog for editing AppConfig values.

    Changes are written to disk immediately when the user clicks Save.
    The scheduler picks up the new values on its next tick (within 60 s).
    """

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(380)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Work reminders ────────────────────────────────────────────────────
        reminder_group = QGroupBox("Work Reminders")
        form = QFormLayout(reminder_group)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.25, 8.0)
        self.interval_spin.setSingleStep(0.25)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSuffix("  hours")
        self.interval_spin.setToolTip(
            "How often the 'What are you working on?' popup appears during work hours."
        )
        self.interval_spin.setValue(self.config.reminder_interval_hours)
        form.addRow("Reminder interval:", self.interval_spin)

        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("hh:mm AP")
        self.start_time.setTime(QTime(self.config.work_start_hour, self.config.work_start_minute))
        self.start_time.setToolTip("First reminder will not fire before this time.")
        form.addRow("Work start time:", self.start_time)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("hh:mm AP")
        self.end_time.setTime(QTime(self.config.work_end_hour, self.config.work_end_minute))
        self.end_time.setToolTip("Reminders stop after this time.")
        form.addRow("Work end time:", self.end_time)

        layout.addWidget(reminder_group)

        # ── Daily target ──────────────────────────────────────────────────────
        target_group = QGroupBox("Daily Target")
        form2 = QFormLayout(target_group)
        form2.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.5, 24.0)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.setDecimals(1)
        self.target_spin.setSuffix("  hours")
        self.target_spin.setToolTip(
            "Days meeting or exceeding this total are shown in green on the calendar."
        )
        self.target_spin.setValue(self.config.daily_target_hours)
        form2.addRow("Daily target:", self.target_spin)

        self.eod_time = QTimeEdit()
        self.eod_time.setDisplayFormat("hh:mm AP")
        self.eod_time.setTime(QTime(self.config.eod_reminder_hour, self.config.eod_reminder_minute))
        self.eod_time.setToolTip("Time at which the end-of-day summary dialog appears.")
        form2.addRow("End-of-day reminder:", self.eod_time)

        layout.addWidget(target_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self) -> None:
        self.config.reminder_interval_hours = self.interval_spin.value()

        t = self.start_time.time()
        self.config.work_start_hour = t.hour()
        self.config.work_start_minute = t.minute()

        t = self.end_time.time()
        self.config.work_end_hour = t.hour()
        self.config.work_end_minute = t.minute()

        self.config.daily_target_hours = self.target_spin.value()

        t = self.eod_time.time()
        self.config.eod_reminder_hour = t.hour()
        self.config.eod_reminder_minute = t.minute()

        self.config.save()
        self.accept()
