from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from database import Database
from state import AppState

DAILY_TARGET = 8.5


class EndOfDayDialog(QDialog):
    def __init__(self, db: Database, state: AppState,
                 date_str: str = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.state = state
        self.date_str = date_str or date.today().isoformat()

        self.setWindowTitle("End of Day Summary")
        self.setMinimumWidth(560)
        self.setMinimumHeight(380)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self._build_ui()
        self._load_data()

        # Mark as shown so it doesn't fire again today
        self.state.mark_eod_shown_today(self.date_str)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        d = date.fromisoformat(self.date_str)
        header = QLabel(f"End of Day — {d.strftime('%A, %d %B %Y')}")
        header.setStyleSheet(
            "background:#1565c0; color:white; padding:10px; font-size:14px; font-weight:bold;"
        )
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("font-size:12px; padding:6px;")
        layout.addWidget(self.warning_label)

        # Summary table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Project", "Code", "Description", "Billability", "Hours"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-size:13px; font-weight:bold; padding:4px;")
        layout.addWidget(self.total_label)

        # Buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Entry")
        add_btn.setStyleSheet("background:#1565c0; color:white; padding:6px 14px; border-radius:4px;")
        add_btn.clicked.connect(self._add_entry)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        close_btn = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn.rejected.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_data(self):
        entries = self.db.get_entries_for_date(self.date_str)
        self.table.setRowCount(0)
        total = 0.0
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry["project_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(entry["project_code"]))
            self.table.setItem(row, 2, QTableWidgetItem(entry["description"]))
            self.table.setItem(row, 3, QTableWidgetItem(entry["billability"]))
            self.table.setItem(row, 4, QTableWidgetItem(f'{entry["hours"]:.2f}'))
            total += entry["hours"]

        if total >= DAILY_TARGET:
            color = "#2e7d32"
            self.total_label.setStyleSheet("font-size:13px; font-weight:bold; color:#2e7d32; padding:4px;")
            self.warning_label.setText("")
        else:
            shortfall = DAILY_TARGET - total
            color = "#c62828"
            self.total_label.setStyleSheet("font-size:13px; font-weight:bold; color:#c62828; padding:4px;")
            self.warning_label.setText(
                f"You've logged {total:.2f}h today — {shortfall:.2f}h short of the {DAILY_TARGET}h target. "
                "Add more entries or adjust hours."
            )
            self.warning_label.setStyleSheet(
                "font-size:12px; padding:8px; background:#ffebee; color:#c62828; border-radius:4px;"
            )

        self.total_label.setText(f"Total: {total:.2f}h / {DAILY_TARGET}h")

    def _add_entry(self):
        from ui.work_popup import WorkPopupDialog
        dlg = WorkPopupDialog(self.db, self.state, add_mode=True,
                               prefill_date=self.date_str, parent=self)
        if dlg.exec_() == WorkPopupDialog.Accepted:
            self._load_data()
