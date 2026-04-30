from PyQt5.QtCore import QTime, Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTimeEdit, QVBoxLayout,
)

from config import AppConfig

_BTN_BLUE   = "background:#1565c0; color:white; padding:5px 12px; border-radius:4px;"
_BTN_ORANGE = "background:#f57c00; color:white; padding:5px 12px; border-radius:4px;"
_BTN_RED    = "background:#c62828; color:white; padding:5px 12px; border-radius:4px;"

# Column indices for the daily tasks table
_COL_PROJECT = 0
_COL_JOB_NO  = 1
_COL_TASK_NO = 2
_COL_DESC    = 3
_COL_BILL    = 4
_COL_HOURS   = 5


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
        self.setMinimumWidth(680)
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

        # ── Pre-EOD frequent reminders ─────────────────────────────────────────
        pre_eod_group = QGroupBox("Pre-End-of-Day Reminders")
        form3 = QFormLayout(pre_eod_group)
        form3.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.pre_eod_warning_spin = QSpinBox()
        self.pre_eod_warning_spin.setRange(5, 180)
        self.pre_eod_warning_spin.setSingleStep(5)
        self.pre_eod_warning_spin.setSuffix("  min before end")
        self.pre_eod_warning_spin.setToolTip(
            "How many minutes before work end time to switch to faster reminders."
        )
        self.pre_eod_warning_spin.setValue(self.config.pre_eod_warning_minutes)
        form3.addRow("Start frequent reminders:", self.pre_eod_warning_spin)

        self.pre_eod_interval_spin = QSpinBox()
        self.pre_eod_interval_spin.setRange(1, 60)
        self.pre_eod_interval_spin.setSingleStep(1)
        self.pre_eod_interval_spin.setSuffix("  min interval")
        self.pre_eod_interval_spin.setToolTip(
            "How often (in minutes) to show reminders during the pre-EOD window."
        )
        self.pre_eod_interval_spin.setValue(self.config.pre_eod_interval_minutes)
        form3.addRow("Reminder frequency:", self.pre_eod_interval_spin)

        layout.addWidget(pre_eod_group)

        # ── Default daily tasks ───────────────────────────────────────────────
        daily_group = QGroupBox("Default Daily Tasks (auto-added each workday)")
        daily_layout = QVBoxLayout(daily_group)
        daily_layout.setSpacing(6)

        hint = QLabel("These entries are automatically added at the start of each workday.")
        hint.setStyleSheet("color:#555; font-size:11px;")
        daily_layout.addWidget(hint)

        self.tasks_table = QTableWidget(0, 6)
        self.tasks_table.setHorizontalHeaderLabels(
            ["Project Name", "Job No.", "Job Task No.", "Description", "Billability", "Hours"]
        )
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_PROJECT, QHeaderView.ResizeToContents)
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_JOB_NO,  QHeaderView.ResizeToContents)
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_TASK_NO, QHeaderView.ResizeToContents)
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_DESC,    QHeaderView.Stretch)
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_BILL,    QHeaderView.ResizeToContents)
        self.tasks_table.horizontalHeader().setSectionResizeMode(_COL_HOURS,   QHeaderView.ResizeToContents)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setMinimumHeight(120)
        daily_layout.addWidget(self.tasks_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Task")
        add_btn.setStyleSheet(_BTN_BLUE)
        add_btn.clicked.connect(self._add_task)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet(_BTN_ORANGE)
        edit_btn.clicked.connect(self._edit_task)

        del_btn = QPushButton("Delete Selected")
        del_btn.setStyleSheet(_BTN_RED)
        del_btn.clicked.connect(self._delete_task)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        daily_layout.addLayout(btn_row)

        layout.addWidget(daily_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_tasks_table()

    # ── Daily tasks table ─────────────────────────────────────────────────────

    def _load_tasks_table(self):
        self.tasks_table.setRowCount(0)
        for task in self.config.daily_tasks:
            self._append_task_row(task)

    def _append_task_row(self, task: dict):
        row = self.tasks_table.rowCount()
        self.tasks_table.insertRow(row)
        self.tasks_table.setItem(row, _COL_PROJECT, QTableWidgetItem(task.get("project_name", "")))
        self.tasks_table.setItem(row, _COL_JOB_NO,  QTableWidgetItem(task.get("job_no", "")))
        self.tasks_table.setItem(row, _COL_TASK_NO, QTableWidgetItem(task.get("job_task_no", "")))
        self.tasks_table.setItem(row, _COL_DESC,    QTableWidgetItem(task.get("description", "")))
        self.tasks_table.setItem(row, _COL_BILL,    QTableWidgetItem(task.get("billability", "Non-Billable")))
        self.tasks_table.setItem(row, _COL_HOURS,   QTableWidgetItem(str(task.get("hours", 0.5))))

    def _row_to_task(self, row: int) -> dict:
        return {
            "project_name": self.tasks_table.item(row, _COL_PROJECT).text(),
            "job_no":       self.tasks_table.item(row, _COL_JOB_NO).text(),
            "job_task_no":  self.tasks_table.item(row, _COL_TASK_NO).text(),
            "description":  self.tasks_table.item(row, _COL_DESC).text(),
            "billability":  self.tasks_table.item(row, _COL_BILL).text(),
            "hours":        float(self.tasks_table.item(row, _COL_HOURS).text()),
        }

    def _add_task(self):
        dlg = _DailyTaskEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._append_task_row(dlg.get_data())

    def _edit_task(self):
        rows = self.tasks_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a task to edit.")
            return
        row = rows[0].row()
        dlg = _DailyTaskEditDialog(task=self._row_to_task(row), parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            self.tasks_table.item(row, _COL_PROJECT).setText(data["project_name"])
            self.tasks_table.item(row, _COL_JOB_NO).setText(data["job_no"])
            self.tasks_table.item(row, _COL_TASK_NO).setText(data["job_task_no"])
            self.tasks_table.item(row, _COL_DESC).setText(data["description"])
            self.tasks_table.item(row, _COL_BILL).setText(data["billability"])
            self.tasks_table.item(row, _COL_HOURS).setText(str(data["hours"]))

    def _delete_task(self):
        rows = self.tasks_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a task to delete.")
            return
        row = rows[0].row()
        name = self.tasks_table.item(row, _COL_PROJECT).text()
        ans = QMessageBox.question(
            self, "Delete Task",
            f'Remove "{name}" from the daily auto-add list?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.tasks_table.removeRow(row)

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

        self.config.pre_eod_warning_minutes = self.pre_eod_warning_spin.value()
        self.config.pre_eod_interval_minutes = self.pre_eod_interval_spin.value()

        self.config.daily_tasks = [
            self._row_to_task(r) for r in range(self.tasks_table.rowCount())
        ]

        self.config.save()
        self.accept()


# ── Daily task add/edit dialog ────────────────────────────────────────────────

class _DailyTaskEditDialog(QDialog):
    def __init__(self, task: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Daily Task" if task is None else "Edit Daily Task")
        self.setMinimumWidth(420)
        self._build_ui()
        if task:
            self._prefill(task)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText("e.g. Internal Meeting")
        self.project_edit.setMaxLength(100)
        form.addRow("Project Name *", self.project_edit)

        self.job_no_edit = QLineEdit()
        self.job_no_edit.setPlaceholderText("e.g. Intech")
        self.job_no_edit.setMaxLength(50)
        form.addRow("Job No.", self.job_no_edit)

        self.task_no_edit = QLineEdit()
        self.task_no_edit.setPlaceholderText("e.g. 1501")
        self.task_no_edit.setMaxLength(50)
        form.addRow("Job Task No.", self.task_no_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("e.g. Daily standup / internal meeting")
        self.desc_edit.setMaxLength(200)
        form.addRow("Description", self.desc_edit)

        self.bill_combo = QComboBox()
        self.bill_combo.addItems(["Billable", "Non-Billable"])
        form.addRow("Billability", self.bill_combo)

        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.25, 8.0)
        self.hours_spin.setSingleStep(0.25)
        self.hours_spin.setDecimals(2)
        self.hours_spin.setSuffix("  hours")
        self.hours_spin.setValue(0.5)
        form.addRow("Hours", self.hours_spin)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _prefill(self, task: dict):
        self.project_edit.setText(task.get("project_name", ""))
        self.job_no_edit.setText(task.get("job_no", ""))
        self.task_no_edit.setText(task.get("job_task_no", ""))
        self.desc_edit.setText(task.get("description", ""))
        idx = self.bill_combo.findText(task.get("billability", "Non-Billable"))
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)
        self.hours_spin.setValue(float(task.get("hours", 0.5)))

    def _on_save(self):
        if not self.project_edit.text().strip():
            QMessageBox.warning(self, "Required", "Project name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "project_name": self.project_edit.text().strip(),
            "job_no":       self.job_no_edit.text().strip(),
            "job_task_no":  self.task_no_edit.text().strip(),
            "description":  self.desc_edit.text().strip(),
            "billability":  self.bill_combo.currentText(),
            "hours":        self.hours_spin.value(),
        }
