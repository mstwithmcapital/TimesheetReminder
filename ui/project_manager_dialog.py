from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from database import Database

COL_ID = 0        # hidden
COL_NAME = 1
COL_CODE = 2
COL_DESC = 3
COL_BILL = 4
COLUMNS = ["id", "Project Name", "Code", "Default Description", "Billability"]


class ProjectManagerDialog(QDialog):
    """
    Full CRUD dialog for the project master list.
    Projects added here are available for auto-fill in every entry dialog.
    """

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Projects")
        self.setMinimumSize(700, 420)
        self._build_ui()
        self._load_projects()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Project Master List")
        header.setStyleSheet(
            "font-size:15px; font-weight:bold; color:#1565c0; padding:4px 0;"
        )
        layout.addWidget(header)

        hint = QLabel(
            "Projects added here will appear in the drop-down when logging work. "
            "Selecting a project auto-fills its code, description, and billability."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#555; font-size:11px; padding-bottom:4px;")
        layout.addWidget(hint)

        # Table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.hideColumn(COL_ID)
        self.table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_CODE, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_BILL, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Project")
        self.add_btn.setStyleSheet(
            "background:#1565c0; color:white; padding:6px 14px; border-radius:4px;"
        )
        self.add_btn.clicked.connect(self._add_project)

        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setStyleSheet(
            "background:#f57c00; color:white; padding:6px 14px; border-radius:4px;"
        )
        self.edit_btn.clicked.connect(self._edit_project)

        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet(
            "background:#c62828; color:white; padding:6px 14px; border-radius:4px;"
        )
        self.del_btn.clicked.connect(self._delete_project)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "background:#546e7a; color:white; padding:6px 14px; border-radius:4px;"
        )
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ── Data loading ─────────────────────────────────────────────────────────

    def _load_projects(self):
        self.table.setRowCount(0)
        for proj in self.db.get_all_projects():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, COL_ID, QTableWidgetItem(str(proj["id"])))
            self.table.setItem(row, COL_NAME, QTableWidgetItem(proj["name"]))
            self.table.setItem(row, COL_CODE, QTableWidgetItem(proj["code"]))
            self.table.setItem(row, COL_DESC, QTableWidgetItem(proj["default_description"]))
            self.table.setItem(row, COL_BILL, QTableWidgetItem(proj["billability"]))

    # ── Actions ──────────────────────────────────────────────────────────────

    def _add_project(self):
        dlg = _ProjectEditDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            self.db.upsert_project(
                data["name"], data["code"],
                data["default_description"], data["billability"],
            )
            self._load_projects()

    def _edit_project(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a project to edit.")
            return
        row = rows[0].row()
        project = {
            "id": int(self.table.item(row, COL_ID).text()),
            "name": self.table.item(row, COL_NAME).text(),
            "code": self.table.item(row, COL_CODE).text(),
            "default_description": self.table.item(row, COL_DESC).text(),
            "billability": self.table.item(row, COL_BILL).text(),
        }
        dlg = _ProjectEditDialog(project=project, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            self.db.update_project(
                project["id"], data["name"], data["code"],
                data["default_description"], data["billability"],
            )
            self._load_projects()

    def _delete_project(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "No Selection", "Select a project to delete.")
            return
        row = rows[0].row()
        name = self.table.item(row, COL_NAME).text()
        project_id = int(self.table.item(row, COL_ID).text())
        ans = QMessageBox.question(
            self, "Delete Project",
            f'Delete project "{name}"?\n\nExisting timesheet entries using this project will not be affected.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.db.delete_project(project_id)
            self._load_projects()


# ── Inner dialog for add / edit ──────────────────────────────────────────────

class _ProjectEditDialog(QDialog):
    """Compact form for adding or editing a single project."""

    def __init__(self, project: dict = None, parent=None):
        super().__init__(parent)
        self._project = project
        self.setWindowTitle("Add Project" if project is None else "Edit Project")
        self.setMinimumWidth(420)
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
        form.addRow("Project Code", self.code_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Default description for this project (optional)")
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
        self.desc_edit.setText(project["default_description"])
        idx = self.bill_combo.findText(project["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Project name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "code": self.code_edit.text().strip(),
            "default_description": self.desc_edit.text().strip(),
            "billability": self.bill_combo.currentText(),
        }
