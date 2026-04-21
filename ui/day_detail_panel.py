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

COL_ID       = 0   # hidden — entry id
COL_TYPE     = 1   # hidden — entry_type ('project'/'ticket')
COL_PROJECT  = 2   # "Project / Job Type"
COL_CODE     = 3   # "Job No / Ticket No"
COL_TASK     = 4   # "Task No"
COL_DESC     = 5   # "Description"
COL_BILL     = 6   # "Billability"
COL_HOURS    = 7   # "Hours"

COLUMNS = ["id", "type", "Project / Job Type", "Job No / Ticket No",
           "Task No", "Description", "Billability", "Hours"]


class DayDetailPanel(QWidget):
    entry_changed = pyqtSignal(str)   # date string → tells calendar to repaint

    def __init__(self, db: Database, state: AppState, config: AppConfig, parent=None):
        super().__init__(parent)
        self.db = db
        self.state = state
        self.config = config
        self._current_date: str | None = None
        self._updating = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.date_label = QLabel("Select a date")
        self.date_label.setStyleSheet("font-size:16px; font-weight:bold; color:#1565c0;")
        layout.addWidget(self.date_label)

        target = self.config.daily_target_hours
        self.total_label = QLabel(f"Total: 0.0h / {target}h")
        self.total_label.setStyleSheet("font-size:13px; padding:4px;")
        layout.addWidget(self.total_label)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.hideColumn(COL_ID)
        self.table.hideColumn(COL_TYPE)
        self.table.horizontalHeader().setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_PROJECT, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_CODE, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_TASK, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Entry")
        self.add_btn.setStyleSheet(
            "background:#1565c0; color:white; padding:6px 12px; border-radius:4px;"
        )
        self.add_btn.clicked.connect(self._add_entry)
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setStyleSheet(
            "background:#f57c00; color:white; padding:6px 12px; border-radius:4px;"
        )
        self.edit_btn.clicked.connect(self._edit_selected)
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet(
            "background:#c62828; color:white; padding:6px 12px; border-radius:4px;"
        )
        self.del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ── Data loading ──────────────────────────────────────────────────────────

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

        # Hidden: id
        id_item = QTableWidgetItem(str(entry["id"]))
        self.table.setItem(row, COL_ID, id_item)

        # Hidden: entry_type
        type_item = QTableWidgetItem(entry.get("entry_type", "project"))
        self.table.setItem(row, COL_TYPE, type_item)

        # Project / Job Type
        proj_item = QTableWidgetItem(entry["project_name"])
        proj_item.setFlags(proj_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_PROJECT, proj_item)

        # Job No / Ticket No
        code_item = QTableWidgetItem(entry["project_code"])
        code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_CODE, code_item)

        # Task No (empty for tickets)
        task_item = QTableWidgetItem(entry.get("job_task_no", ""))
        task_item.setFlags(task_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_TASK, task_item)

        # Description
        desc_item = QTableWidgetItem(entry["description"])
        desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, COL_DESC, desc_item)

        # Billability combo
        bill_combo = QComboBox()
        bill_combo.addItems(["Billable", "Non-Billable"])
        bill_combo.setCurrentText(entry["billability"])
        bill_combo.currentTextChanged.connect(
            lambda val, r=row: self._on_bill_changed(r, val)
        )
        self.table.setCellWidget(row, COL_BILL, bill_combo)

        # Hours spin
        spin = QDoubleSpinBox()
        spin.setRange(0.25, 24.0)
        spin.setSingleStep(0.25)
        spin.setDecimals(2)
        spin.setValue(entry["hours"])
        spin.valueChanged.connect(
            lambda val, r=row: self._on_hours_changed(r, val)
        )
        self.table.setCellWidget(row, COL_HOURS, spin)

        # Auto-added entries shown in grey
        if entry.get("is_auto_added"):
            for col in [COL_PROJECT, COL_CODE, COL_TASK, COL_DESC]:
                item = self.table.item(row, col)
                if item:
                    item.setForeground(QColor("#757575"))

    # ── Inline edit handlers ──────────────────────────────────────────────────

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
        pass  # non-editable items; handled via cell widgets

    def _update_total(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, COL_HOURS)
            if spin:
                total += spin.value()
        target = self.config.daily_target_hours
        color = "#2e7d32" if total >= target else "#c62828"
        self.total_label.setText(f"Total: {total:.2f}h / {target}h")
        self.total_label.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{color}; padding:4px;"
        )

    def refresh_target(self):
        self._update_total()

    # ── Button actions ────────────────────────────────────────────────────────

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

        # Fetch fresh entry from DB so we have all fields including new columns
        entry = self.db.get_entry_by_id(entry_id)
        if not entry:
            return

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
        ans = QMessageBox.question(
            self, "Delete Entry",
            f"Delete {len(rows)} entry/entries?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        for idx in sorted(rows, reverse=True):
            entry_id = int(self.table.item(idx.row(), COL_ID).text())
            self.db.delete_entry(entry_id)
        self._refresh_table()
        if self._current_date:
            self.entry_changed.emit(self._current_date)
