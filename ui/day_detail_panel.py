from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from config import AppConfig
from database import Database
from state import AppState

COL_ID = 0       # hidden
COL_PROJECT = 1
COL_CODE = 2
COL_DESC = 3
COL_BILL = 4
COL_HOURS = 5
COLUMNS = ["id", "Project Name", "Code", "Description", "Billability", "Hours"]


class DayDetailPanel(QWidget):
    entry_changed = pyqtSignal(str)   # date string → tells calendar to repaint

    def __init__(self, db: Database, state: AppState, config: AppConfig, parent=None):
        super().__init__(parent)
        self.db = db
        self.state = state
        self.config = config
        self._current_date: str | None = None
        self._updating = False   # guard against recursive itemChanged

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Date header
        self.date_label = QLabel("Select a date")
        self.date_label.setStyleSheet("font-size:16px; font-weight:bold; color:#1565c0;")
        layout.addWidget(self.date_label)

        # Total bar
        target = self.config.daily_target_hours
        self.total_label = QLabel(f"Total: 0.0h / {target}h")
        self.total_label.setStyleSheet("font-size:13px; padding:4px;")
        layout.addWidget(self.total_label)

        # Table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.hideColumn(COL_ID)
        self.table.horizontalHeader().setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_PROJECT, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Entry")
        self.add_btn.setStyleSheet("background:#1565c0; color:white; padding:6px 12px; border-radius:4px;")
        self.add_btn.clicked.connect(self._add_entry)
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setStyleSheet("background:#f57c00; color:white; padding:6px 12px; border-radius:4px;")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet("background:#c62828; color:white; padding:6px 12px; border-radius:4px;")
        self.del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_date(self, date_str: str):
        self._current_date = date_str
        from datetime import date as dt_date
        d = dt_date.fromisoformat(date_str)
        self.date_label.setText(d.strftime("%A, %d %B %Y"))
        self._refresh_table()

    def _refresh_table(self):
        if not self._current_date:
            return
        self._updating = True
        entries = self.db.get_entries_for_date(self._current_date)
        self.table.setRowCount(0)
        for entry in entries:
            self._append_row(entry)
        self._update_total()
        self._updating = False

    def _append_row(self, entry: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Hidden ID
        id_item = QTableWidgetItem(str(entry["id"]))
        self.table.setItem(row, COL_ID, id_item)

        # Project
        proj_item = QTableWidgetItem(entry["project_name"])
        proj_item.setFlags(proj_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_PROJECT, proj_item)

        # Code
        code_item = QTableWidgetItem(entry["project_code"])
        code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_CODE, code_item)

        # Description
        desc_item = QTableWidgetItem(entry["description"])
        desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_DESC, desc_item)

        # Billability (combo)
        bill_combo = QComboBox()
        bill_combo.addItems(["Billable", "Non-Billable"])
        bill_combo.setCurrentText(entry["billability"])
        bill_combo.currentTextChanged.connect(
            lambda val, r=row: self._on_bill_changed(r, val)
        )
        self.table.setCellWidget(row, COL_BILL, bill_combo)

        # Hours (spin)
        spin = QDoubleSpinBox()
        spin.setRange(0.25, 24.0)
        spin.setSingleStep(0.25)
        spin.setDecimals(2)
        spin.setValue(entry["hours"])
        spin.valueChanged.connect(
            lambda val, r=row: self._on_hours_changed(r, val)
        )
        self.table.setCellWidget(row, COL_HOURS, spin)

        # Auto-added entries shown in italic/grey
        if entry.get("is_auto_added"):
            for col in [COL_PROJECT, COL_CODE, COL_DESC]:
                item = self.table.item(row, col)
                if item:
                    item.setForeground(QColor("#757575"))

    def _on_bill_changed(self, row: int, value: str):
        if self._updating:
            return
        entry_id = int(self.table.item(row, COL_ID).text())
        self.db.update_entry(entry_id, billability=value)

    def _on_hours_changed(self, row: int, value: float):
        if self._updating:
            return
        entry_id = int(self.table.item(row, COL_ID).text())
        self.db.update_entry(entry_id, hours=value)
        self._update_total()
        if self._current_date:
            self.entry_changed.emit(self._current_date)

    def _on_item_changed(self, item: QTableWidgetItem):
        # Only Hours column is editable via QTableWidgetItem (others use widgets)
        pass

    def _update_total(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, COL_HOURS)
            if spin:
                total += spin.value()
        target = self.config.daily_target_hours
        color = "#2e7d32" if total >= target else "#c62828"
        self.total_label.setText(f"Total: {total:.2f}h / {target}h")
        self.total_label.setStyleSheet(f"font-size:13px; font-weight:bold; color:{color}; padding:4px;")

    def refresh_target(self):
        """Called after settings change to update the target label immediately."""
        self._update_total()

    def _add_entry(self):
        if not self._current_date:
            return
        from ui.work_popup import WorkPopupDialog
        dlg = WorkPopupDialog(self.db, self.state, add_mode=True,
                               prefill_date=self._current_date, parent=self)
        if dlg.exec_() == WorkPopupDialog.Accepted:
            self._refresh_table()
            self.entry_changed.emit(self._current_date)

    def _edit_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        entry_id = int(self.table.item(row, COL_ID).text())
        # Rebuild entry dict from current row widgets
        spin = self.table.cellWidget(row, COL_HOURS)
        bill = self.table.cellWidget(row, COL_BILL)
        entry = {
            "id": entry_id,
            "project_name": self.table.item(row, COL_PROJECT).text(),
            "project_code": self.table.item(row, COL_CODE).text(),
            "description": self.table.item(row, COL_DESC).text(),
            "billability": bill.currentText() if bill else "Billable",
            "hours": spin.value() if spin else 1.0,
        }
        from ui.work_popup import WorkPopupDialog
        dlg = WorkPopupDialog(self.db, self.state, add_mode=True,
                               prefill_date=self._current_date, parent=self)
        dlg.prefill(entry)
        if dlg.exec_() == WorkPopupDialog.Accepted:
            self._refresh_table()
            self.entry_changed.emit(self._current_date)

    def _delete_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        ans = QMessageBox.question(self, "Delete Entry",
                                   f"Delete {len(rows)} entry/entries?",
                                   QMessageBox.Yes | QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        for idx in sorted(rows, reverse=True):
            entry_id = int(self.table.item(idx.row(), COL_ID).text())
            self.db.delete_entry(entry_id)
        self._refresh_table()
        if self._current_date:
            self.entry_changed.emit(self._current_date)
