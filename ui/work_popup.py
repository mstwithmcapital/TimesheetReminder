from datetime import date

from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QComboBox,
    QCompleter, QFormLayout, QLabel, QLineEdit, QMessageBox,
    QVBoxLayout, QWidget,
)

from database import Database
from state import AppState


class WorkPopupDialog(QDialog):
    """
    'What are you working on?' dialog.
    add_mode=True  → manual add from day panel (hours default 1.0, no auto-hours)
    add_mode=False → triggered by scheduler (hours = time since last popup)
    """

    def __init__(self, db: Database, state: AppState,
                 add_mode: bool = False,
                 prefill_date: str = None,
                 parent=None):
        super().__init__(parent)
        self.db = db
        self.state = state
        self.add_mode = add_mode
        self.target_date = prefill_date or date.today().isoformat()
        self._entry_id = None  # set if editing existing

        self.setWindowTitle("What are you working on?" if not add_mode else "Add Entry")
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self._build_form()
        self._load_projects()

    def _build_form(self):
        layout = QVBoxLayout(self)

        if not self.add_mode:
            banner = QLabel("Time to log your work!")
            banner.setStyleSheet(
                "background:#1565c0; color:white; padding:8px; border-radius:4px; font-size:13px; font-weight:bold;"
            )
            banner.setAlignment(Qt.AlignCenter)
            layout.addWidget(banner)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        # Project Name
        self.project_combo = QComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.setInsertPolicy(QComboBox.NoInsert)
        self.project_combo.lineEdit().setPlaceholderText("Type or select project...")
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        form.addRow("Project Name *", self.project_combo)

        # Project Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. PRJ-001")
        form.addRow("Project Code", self.code_edit)

        # Short Description
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Brief description of work done...")
        form.addRow("Description *", self.desc_edit)

        # Billability
        self.bill_combo = QComboBox()
        self.bill_combo.addItems(["Billable", "Non-Billable"])
        form.addRow("Billability", self.bill_combo)

        # Hours
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.25, 24.0)
        self.hours_spin.setSingleStep(0.25)
        self.hours_spin.setDecimals(2)
        default_h = 1.0 if self.add_mode else self.state.hours_since_last_popup()
        self.hours_spin.setValue(default_h)
        form.addRow("Hours", self.hours_spin)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_projects(self):
        projects = self.db.get_all_projects()
        names = [p["name"] for p in projects]
        self._project_map = {p["name"]: p for p in projects}

        self.project_combo.clear()
        self.project_combo.addItems(names)
        self.project_combo.setCurrentText("")

        completer = QCompleter(names, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.project_combo.setCompleter(completer)

    def _on_project_changed(self, name: str):
        proj = self._project_map.get(name)
        if proj:
            self.code_edit.setText(proj["code"])
            if proj["default_description"]:
                self.desc_edit.setText(proj["default_description"])
            idx = self.bill_combo.findText(proj["billability"])
            if idx >= 0:
                self.bill_combo.setCurrentIndex(idx)

    def _on_save(self):
        project_name = self.project_combo.currentText().strip()
        description = self.desc_edit.text().strip()

        if not project_name:
            QMessageBox.warning(self, "Required Field", "Project name is required.")
            return
        if not description:
            QMessageBox.warning(self, "Required Field", "Description is required.")
            return

        code = self.code_edit.text().strip()
        billability = self.bill_combo.currentText()
        hours = self.hours_spin.value()

        self.db.add_entry(
            self.target_date, project_name, code, description, billability, hours
        )
        self.db.upsert_project(project_name, code, description, billability)

        if not self.add_mode:
            self.state.record_popup_shown()

        self.accept()

    def prefill(self, entry: dict):
        """Pre-fill form for editing an existing entry (called before exec_())."""
        self._entry_id = entry["id"]
        self.project_combo.setCurrentText(entry["project_name"])
        self.code_edit.setText(entry["project_code"])
        self.desc_edit.setText(entry["description"])
        idx = self.bill_combo.findText(entry["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)
        self.hours_spin.setValue(entry["hours"])
