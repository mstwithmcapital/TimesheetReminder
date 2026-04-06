from datetime import date, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from database import Database
from state import AppState


def _monday_of_current_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


class WeeklySummaryDialog(QDialog):
    def __init__(self, db: Database, state: AppState,
                 mode: str = "weekly", parent=None):
        super().__init__(parent)
        self.db = db
        self.state = state
        self.mode = mode  # "weekly" | "saturday"

        iso = date.today().isocalendar()
        self.iso_year = iso.year
        self.iso_week = iso.week

        self.setWindowTitle("Weekly Summary — Timesheet Review")
        self.setMinimumWidth(600)
        self.setMinimumHeight(420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        monday = _monday_of_current_week()
        sunday = monday + timedelta(days=6)
        header = QLabel(
            f"Week of {monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"
        )
        header.setStyleSheet(
            "background:#1565c0; color:white; padding:10px; font-size:14px; font-weight:bold;"
        )
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        remind_text = (
            "Reminder: Submit your weekly timesheet!"
            if self.mode == "weekly"
            else "Reminder: Submit your first-Saturday timesheet!"
        )
        remind_label = QLabel(remind_text)
        remind_label.setStyleSheet(
            "font-size:12px; padding:6px; background:#fff3e0; color:#e65100; border-radius:4px;"
        )
        layout.addWidget(remind_label)

        # Summary by project table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Project Name", "Code", "Billability", "Total Hours"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.grand_total_label = QLabel()
        self.grand_total_label.setStyleSheet(
            "font-size:13px; font-weight:bold; padding:4px;"
        )
        layout.addWidget(self.grand_total_label)

        # Buttons
        btn_row = QHBoxLayout()

        export_btn = QPushButton("Export to Excel")
        export_btn.setStyleSheet("background:#2e7d32; color:white; padding:6px 14px; border-radius:4px;")
        export_btn.clicked.connect(self._export)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()

        submit_btn = QPushButton("Mark Submitted")
        submit_btn.setStyleSheet("background:#1565c0; color:white; padding:6px 14px; border-radius:4px;")
        submit_btn.clicked.connect(self._mark_submitted)
        btn_row.addWidget(submit_btn)

        close_btn = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn.rejected.connect(self.reject)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _load_data(self):
        monday = _monday_of_current_week()
        sunday = monday + timedelta(days=6)
        groups = self.db.get_entries_grouped_by_project(
            monday.isoformat(), sunday.isoformat()
        )

        self.table.setRowCount(0)
        grand_total = 0.0
        for g in groups:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(g["project_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(g["project_code"]))
            self.table.setItem(row, 2, QTableWidgetItem(g["billability"]))
            hours_item = QTableWidgetItem(f'{g["total_hours"]:.2f}')
            hours_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, hours_item)
            grand_total += g["total_hours"]

        self.grand_total_label.setText(f"Grand Total: {grand_total:.2f}h")
        color = "#2e7d32" if grand_total >= 42.5 else "#c62828"  # 5 days × 8.5h
        self.grand_total_label.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{color}; padding:4px;"
        )

    def _mark_submitted(self):
        if self.mode == "weekly":
            self.state.mark_weekly_submitted()
        else:
            self.state.mark_saturday_submitted()
        self.accept()

    def _export(self):
        from ui.export import export_week_to_excel
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel File",
            f"timesheet_week_{self.iso_year}_W{self.iso_week:02d}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if path:
            export_week_to_excel(self.db, self.iso_year, self.iso_week, path)
