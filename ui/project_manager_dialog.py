from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from database import Database

# ── Project tab columns ───────────────────────────────────────────────────────
PROJ_COL_ID   = 0  # hidden
PROJ_COL_NAME = 1
PROJ_COL_CODE = 2
PROJ_COL_TASK = 3
PROJ_COL_DESC = 4
PROJ_COL_BILL = 5
PROJ_COLUMNS = ["id", "Project Name", "Job No.", "Job Task No.", "Default Description", "Billability"]

# ── Ticket tab columns ────────────────────────────────────────────────────────
TKT_COL_ID   = 0  # hidden
TKT_COL_NO   = 1
TKT_COL_DESC = 2
TKT_COL_BILL = 3
TKT_COLUMNS = ["id", "Ticket No", "Default Description", "Billability"]

_BTN_BLUE   = "background:#1565c0; color:white; padding:6px 14px; border-radius:4px;"
_BTN_ORANGE = "background:#f57c00; color:white; padding:6px 14px; border-radius:4px;"
_BTN_RED    = "background:#c62828; color:white; padding:6px 14px; border-radius:4px;"
_BTN_GREY   = "background:#546e7a; color:white; padding:6px 14px; border-radius:4px;"


class ProjectManagerDialog(QDialog):
    """
    Tabbed dialog for managing the Projects master list and the Tickets master list.
    Entries saved here auto-populate dropdowns in the work-logging popup.
    """

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Projects & Tickets")
        self.setMinimumSize(780, 480)
        self._build_ui()
        self._load_projects()
        self._load_tickets()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_projects_tab(), "Projects")
        self.tabs.addTab(self._build_tickets_tab(), "Tickets")
        layout.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(_BTN_GREY)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _build_projects_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)

        hint = QLabel(
            "Projects added here appear in the Project Name dropdown. "
            "Selecting a project auto-fills Job No., Job Task No., description, and billability."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555; font-size:11px; padding-bottom:4px;")
        layout.addWidget(hint)

        self.proj_table = QTableWidget(0, len(PROJ_COLUMNS))
        self.proj_table.setHorizontalHeaderLabels(PROJ_COLUMNS)
        self.proj_table.hideColumn(PROJ_COL_ID)
        self.proj_table.horizontalHeader().setSectionResizeMode(PROJ_COL_NAME, QHeaderView.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(PROJ_COL_CODE, QHeaderView.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(PROJ_COL_TASK, QHeaderView.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(PROJ_COL_DESC, QHeaderView.Stretch)
        self.proj_table.horizontalHeader().setSectionResizeMode(PROJ_COL_BILL, QHeaderView.ResizeToContents)
        self.proj_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proj_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.proj_table.setAlternatingRowColors(True)
        layout.addWidget(self.proj_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Project")
        add_btn.setStyleSheet(_BTN_BLUE)
        add_btn.clicked.connect(self._add_project)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet(_BTN_ORANGE)
        edit_btn.clicked.connect(self._edit_project)

        del_btn = QPushButton("Delete Selected")
        del_btn.setStyleSheet(_BTN_RED)
        del_btn.clicked.connect(self._delete_project)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return widget

    def _build_tickets_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)

        hint = QLabel(
            "Tickets added here appear in the Ticket No. dropdown. "
            "Job Type is always 'Support'. Selecting a ticket auto-fills description and billability."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555; font-size:11px; padding-bottom:4px;")
        layout.addWidget(hint)

        self.tkt_table = QTableWidget(0, len(TKT_COLUMNS))
        self.tkt_table.setHorizontalHeaderLabels(TKT_COLUMNS)
        self.tkt_table.hideColumn(TKT_COL_ID)
        self.tkt_table.horizontalHeader().setSectionResizeMode(TKT_COL_NO, QHeaderView.ResizeToContents)
        self.tkt_table.horizontalHeader().setSectionResizeMode(TKT_COL_DESC, QHeaderView.Stretch)
        self.tkt_table.horizontalHeader().setSectionResizeMode(TKT_COL_BILL, QHeaderView.ResizeToContents)
        self.tkt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tkt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tkt_table.setAlternatingRowColors(True)
        layout.addWidget(self.tkt_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Ticket")
        add_btn.setStyleSheet(_BTN_BLUE)
        add_btn.clicked.connect(self._add_ticket)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.setStyleSheet(_BTN_ORANGE)
        edit_btn.clicked.connect(self._edit_ticket)

        del_btn = QPushButton("Delete Selected")
        del_btn.setStyleSheet(_BTN_RED)
        del_btn.clicked.connect(self._delete_ticket)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return widget

    # ── Project data ──────────────────────────────────────────────────────────

    def _load_projects(self):
        self.proj_table.setRowCount(0)
        for proj in self.db.get_all_projects():
            row = self.proj_table.rowCount()
            self.proj_table.insertRow(row)
            self.proj_table.setItem(row, PROJ_COL_ID,   QTableWidgetItem(str(proj["id"])))
            self.proj_table.setItem(row, PROJ_COL_NAME, QTableWidgetItem(proj["name"]))
            self.proj_table.setItem(row, PROJ_COL_CODE, QTableWidgetItem(proj["code"]))
            self.proj_table.setItem(row, PROJ_COL_TASK, QTableWidgetItem(proj.get("job_task_no", "")))
            self.proj_table.setItem(row, PROJ_COL_DESC, QTableWidgetItem(proj["default_description"]))
            self.proj_table.setItem(row, PROJ_COL_BILL, QTableWidgetItem(proj["billability"]))

    def _add_project(self):
        dlg = _ProjectEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            self.db.upsert_project(d["name"], d["code"], d["job_task_no"],
                                   d["default_description"], d["billability"])
            self._load_projects()

    def _edit_project(self):
        rows = self.proj_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a project to edit.")
            return
        row = rows[0].row()
        project = {
            "id":                  int(self.proj_table.item(row, PROJ_COL_ID).text()),
            "name":                self.proj_table.item(row, PROJ_COL_NAME).text(),
            "code":                self.proj_table.item(row, PROJ_COL_CODE).text(),
            "job_task_no":         self.proj_table.item(row, PROJ_COL_TASK).text(),
            "default_description": self.proj_table.item(row, PROJ_COL_DESC).text(),
            "billability":         self.proj_table.item(row, PROJ_COL_BILL).text(),
        }
        dlg = _ProjectEditDialog(project=project, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            self.db.update_project(project["id"], d["name"], d["code"], d["job_task_no"],
                                   d["default_description"], d["billability"])
            self._load_projects()

    def _delete_project(self):
        rows = self.proj_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a project to delete.")
            return
        row = rows[0].row()
        name = self.proj_table.item(row, PROJ_COL_NAME).text()
        project_id = int(self.proj_table.item(row, PROJ_COL_ID).text())
        ans = QMessageBox.question(
            self, "Delete Project",
            f'Delete project "{name}"?\n\nExisting timesheet entries will not be affected.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.db.delete_project(project_id)
            self._load_projects()

    # ── Ticket data ───────────────────────────────────────────────────────────

    def _load_tickets(self):
        self.tkt_table.setRowCount(0)
        for tkt in self.db.get_all_tickets():
            row = self.tkt_table.rowCount()
            self.tkt_table.insertRow(row)
            self.tkt_table.setItem(row, TKT_COL_ID,   QTableWidgetItem(str(tkt["id"])))
            self.tkt_table.setItem(row, TKT_COL_NO,   QTableWidgetItem(tkt["ticket_no"]))
            self.tkt_table.setItem(row, TKT_COL_DESC, QTableWidgetItem(tkt["description"]))
            self.tkt_table.setItem(row, TKT_COL_BILL, QTableWidgetItem(tkt["billability"]))

    def _add_ticket(self):
        dlg = _TicketEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            self.db.upsert_ticket(d["ticket_no"], d["description"], d["billability"])
            self._load_tickets()

    def _edit_ticket(self):
        rows = self.tkt_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a ticket to edit.")
            return
        row = rows[0].row()
        ticket = {
            "id":          int(self.tkt_table.item(row, TKT_COL_ID).text()),
            "ticket_no":   self.tkt_table.item(row, TKT_COL_NO).text(),
            "description": self.tkt_table.item(row, TKT_COL_DESC).text(),
            "billability": self.tkt_table.item(row, TKT_COL_BILL).text(),
        }
        dlg = _TicketEditDialog(ticket=ticket, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            self.db.update_ticket(ticket["id"], d["ticket_no"], d["description"], d["billability"])
            self._load_tickets()

    def _delete_ticket(self):
        rows = self.tkt_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a ticket to delete.")
            return
        row = rows[0].row()
        ticket_no = self.tkt_table.item(row, TKT_COL_NO).text()
        ticket_id = int(self.tkt_table.item(row, TKT_COL_ID).text())
        ans = QMessageBox.question(
            self, "Delete Ticket",
            f'Delete ticket "{ticket_no}"?\n\nExisting timesheet entries will not be affected.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.db.delete_ticket(ticket_id)
            self._load_tickets()


# ── Project add/edit form ─────────────────────────────────────────────────────

class _ProjectEditDialog(QDialog):
    def __init__(self, project: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Project" if project is None else "Edit Project")
        self.setMinimumWidth(440)
        self._build_ui()
        if project:
            self._prefill(project)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Goodview")
        form.addRow("Project Name *", self.name_edit)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. GV-01")
        form.addRow("Job No.", self.code_edit)

        self.task_edit = QLineEdit()
        self.task_edit.setPlaceholderText("e.g. TASK-001 (optional)")
        form.addRow("Job Task No.", self.task_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Default description (optional)")
        form.addRow("Default Description", self.desc_edit)

        self.bill_combo = QComboBox()
        self.bill_combo.addItems(["Billable", "Non-Billable"])
        form.addRow("Billability", self.bill_combo)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _prefill(self, project: dict):
        self.name_edit.setText(project["name"])
        self.code_edit.setText(project["code"])
        self.task_edit.setText(project.get("job_task_no", ""))
        self.desc_edit.setText(project["default_description"])
        idx = self.bill_combo.findText(project["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_save(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Required", "Project name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name":                self.name_edit.text().strip(),
            "code":                self.code_edit.text().strip(),
            "job_task_no":         self.task_edit.text().strip(),
            "default_description": self.desc_edit.text().strip(),
            "billability":         self.bill_combo.currentText(),
        }


# ── Ticket add/edit form ──────────────────────────────────────────────────────

class _TicketEditDialog(QDialog):
    def __init__(self, ticket: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Ticket" if ticket is None else "Edit Ticket")
        self.setMinimumWidth(420)
        self._build_ui()
        if ticket:
            self._prefill(ticket)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        job_type_lbl = QLabel("Support")
        job_type_lbl.setStyleSheet("font-weight:bold; color:#1565c0;")
        form.addRow("Job Type", job_type_lbl)

        self.ticket_no_edit = QLineEdit()
        self.ticket_no_edit.setPlaceholderText("e.g. INC-12345")
        form.addRow("Ticket No *", self.ticket_no_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Default description (optional)")
        form.addRow("Default Description", self.desc_edit)

        self.bill_combo = QComboBox()
        self.bill_combo.addItems(["Billable", "Non-Billable"])
        form.addRow("Billability", self.bill_combo)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _prefill(self, ticket: dict):
        self.ticket_no_edit.setText(ticket["ticket_no"])
        self.desc_edit.setText(ticket["description"])
        idx = self.bill_combo.findText(ticket["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_save(self):
        if not self.ticket_no_edit.text().strip():
            QMessageBox.warning(self, "Required", "Ticket number is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "ticket_no":   self.ticket_no_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "billability": self.bill_combo.currentText(),
        }
