from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QCompleter, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QRadioButton, QVBoxLayout, QWidget,
)

from database import Database
from state import AppState
from ui.icons import make_app_icon


class WorkPopupDialog(QDialog):
    """
    Work-logging dialog.
    add_mode=True  → manual add/edit from day panel (hours default 1.0)
    add_mode=False → triggered by scheduler (hours = time since last popup)

    Entry types:
      Project — Project Name, Job No, Job Task No, Description, Billability, Hours
      Ticket  — Job Type (static "Support"), Ticket No, Description, Billability, Hours
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
        self._entry_id = None  # set when editing an existing entry

        self.setWindowTitle("What are you working on?" if not add_mode else "Add Entry")
        self.setWindowIcon(make_app_icon())
        self.setMinimumWidth(480)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self._build_form()
        self._load_projects()

    def _build_form(self):
        layout = QVBoxLayout(self)

        if not self.add_mode:
            banner = QLabel("Time to log your work!")
            banner.setStyleSheet(
                "background:#1565c0; color:white; padding:8px;"
                " border-radius:4px; font-size:13px; font-weight:bold;"
            )
            banner.setAlignment(Qt.AlignCenter)
            layout.addWidget(banner)

        # ── Entry-type selector ───────────────────────────────────────────────
        type_group = QGroupBox("Entry Type")
        type_layout = QHBoxLayout(type_group)
        self.radio_project = QRadioButton("Project")
        self.radio_ticket = QRadioButton("Ticket")
        self.radio_project.setChecked(True)
        type_layout.addWidget(self.radio_project)
        type_layout.addWidget(self.radio_ticket)
        type_layout.addStretch()
        layout.addWidget(type_group)
        self.radio_project.toggled.connect(self._on_type_changed)

        # ── Project-specific fields ───────────────────────────────────────────
        self.project_widget = QWidget()
        proj_form = QFormLayout(self.project_widget)
        proj_form.setLabelAlignment(Qt.AlignRight)
        proj_form.setSpacing(8)
        proj_form.setContentsMargins(0, 0, 0, 0)

        self.project_combo = QComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.setInsertPolicy(QComboBox.NoInsert)
        self.project_combo.lineEdit().setPlaceholderText("Type or select project…")
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        proj_form.addRow("Project Name *", self.project_combo)

        self.job_no_edit = QLineEdit()
        self.job_no_edit.setPlaceholderText("e.g. JOB-001")
        proj_form.addRow("Job No", self.job_no_edit)

        self.job_task_combo = QComboBox()
        self.job_task_combo.setEditable(True)
        self.job_task_combo.setInsertPolicy(QComboBox.NoInsert)
        self.job_task_combo.lineEdit().setPlaceholderText("Select or type task no…")
        self.job_task_combo.activated.connect(self._on_task_no_activated)
        proj_form.addRow("Job Task No", self.job_task_combo)

        layout.addWidget(self.project_widget)

        # ── Ticket-specific fields ────────────────────────────────────────────
        self.ticket_widget = QWidget()
        ticket_form = QFormLayout(self.ticket_widget)
        ticket_form.setLabelAlignment(Qt.AlignRight)
        ticket_form.setSpacing(8)
        ticket_form.setContentsMargins(0, 0, 0, 0)

        job_type_lbl = QLabel("Support")
        job_type_lbl.setStyleSheet("font-weight:bold; color:#1565c0;")
        ticket_form.addRow("Job Type", job_type_lbl)

        self.ticket_no_edit = QLineEdit()
        self.ticket_no_edit.setPlaceholderText("e.g. INC-12345")
        ticket_form.addRow("Ticket No *", self.ticket_no_edit)

        self.ticket_widget.setVisible(False)
        layout.addWidget(self.ticket_widget)

        # ── Shared fields ─────────────────────────────────────────────────────
        shared_form = QFormLayout()
        shared_form.setLabelAlignment(Qt.AlignRight)
        shared_form.setSpacing(8)

        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText("Description of work done…")
        self.desc_edit.setMinimumHeight(70)
        self.desc_edit.setMaximumHeight(120)
        shared_form.addRow("Description *", self.desc_edit)

        self.bill_combo = QComboBox()
        self.bill_combo.addItems(["Billable", "Non-Billable"])
        shared_form.addRow("Billability", self.bill_combo)

        default_h = 1.0 if self.add_mode else self.state.hours_since_last_popup()
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.25, 24.0)
        self.hours_spin.setSingleStep(0.25)
        self.hours_spin.setDecimals(2)
        self.hours_spin.setValue(default_h)
        shared_form.addRow("Hours", self.hours_spin)

        layout.addLayout(shared_form)

        # ── Buttons ───────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_type_changed(self, project_selected: bool):
        self.project_widget.setVisible(project_selected)
        self.ticket_widget.setVisible(not project_selected)
        self.adjustSize()

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

        # Autocomplete for Job No from past project entries
        job_nos = self.db.get_distinct_codes("project")
        self._job_no_list = job_nos
        job_completer = QCompleter(job_nos, self)
        job_completer.setCaseSensitivity(Qt.CaseInsensitive)
        job_completer.setFilterMode(Qt.MatchContains)
        self.job_no_edit.setCompleter(job_completer)
        self.job_no_edit.textChanged.connect(self._on_job_no_changed)

        # Dropdown for Job Task No from past entries
        task_nos = self.db.get_distinct_task_nos()
        self._task_no_list = task_nos
        self.job_task_combo.clear()
        self.job_task_combo.addItem("")
        self.job_task_combo.addItems(task_nos)
        self.job_task_combo.addItem("+ New Task No.")
        self.job_task_combo.setCurrentIndex(0)
        task_completer = QCompleter(task_nos, self)
        task_completer.setCaseSensitivity(Qt.CaseInsensitive)
        task_completer.setFilterMode(Qt.MatchContains)
        self.job_task_combo.setCompleter(task_completer)

        # Autocomplete for Ticket No from past ticket entries
        ticket_nos = self.db.get_distinct_codes("ticket")
        self._ticket_no_list = ticket_nos
        ticket_completer = QCompleter(ticket_nos, self)
        ticket_completer.setCaseSensitivity(Qt.CaseInsensitive)
        ticket_completer.setFilterMode(Qt.MatchContains)
        self.ticket_no_edit.setCompleter(ticket_completer)
        self.ticket_no_edit.textChanged.connect(self._on_ticket_no_changed)

    def _on_project_changed(self, name: str):
        proj = self._project_map.get(name)
        if proj:
            if proj["code"]:
                self.job_no_edit.setText(proj["code"])
            if proj["default_description"]:
                self.desc_edit.setPlainText(proj["default_description"])
            idx = self.bill_combo.findText(proj["billability"])
            if idx >= 0:
                self.bill_combo.setCurrentIndex(idx)

    def _on_job_no_changed(self, code: str):
        """Auto-fill description/billability from most recent entry with this job no."""
        if code not in self._job_no_list:
            return
        entry = self.db.get_latest_entry_by_code(code, "project")
        if not entry:
            return
        if not self.desc_edit.toPlainText().strip():
            self.desc_edit.setPlainText(entry["description"])
        idx = self.bill_combo.findText(entry["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_ticket_no_changed(self, code: str):
        """Auto-fill description from most recent entry with this ticket no."""
        if code not in self._ticket_no_list:
            return
        entry = self.db.get_latest_entry_by_code(code, "ticket")
        if not entry:
            return
        if not self.desc_edit.toPlainText().strip():
            self.desc_edit.setPlainText(entry["description"])
        idx = self.bill_combo.findText(entry["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_task_no_activated(self, index: int):
        """When '+ New Task No.' is selected, clear so user can type a new value."""
        if self.job_task_combo.currentText() == "+ New Task No.":
            self.job_task_combo.setCurrentText("")
            self.job_task_combo.lineEdit().setFocus()

    # ── Save ──────────────────────────────────────────────────────────────────

    def _on_save(self):
        is_project = self.radio_project.isChecked()
        description = self.desc_edit.toPlainText().strip()

        if not description:
            QMessageBox.warning(self, "Required Field", "Description is required.")
            return

        if is_project:
            project_name = self.project_combo.currentText().strip()
            if not project_name:
                QMessageBox.warning(self, "Required Field", "Project name is required.")
                return
            project_code = self.job_no_edit.text().strip()
            raw_task = self.job_task_combo.currentText().strip()
            job_task_no = "" if raw_task == "+ New Task No." else raw_task
            entry_type = "project"
        else:
            ticket_no = self.ticket_no_edit.text().strip()
            if not ticket_no:
                QMessageBox.warning(self, "Required Field", "Ticket number is required.")
                return
            project_name = "Support"
            project_code = ticket_no
            job_task_no = ""
            entry_type = "ticket"

        billability = self.bill_combo.currentText()
        hours = self.hours_spin.value()

        if self._entry_id is not None:
            # ── Edit existing entry ───────────────────────────────────────────
            self.db.update_entry(
                self._entry_id,
                project_name=project_name,
                project_code=project_code,
                description=description,
                billability=billability,
                hours=hours,
                entry_type=entry_type,
                job_task_no=job_task_no,
            )
        else:
            # ── Check for duplicate project+code on same day ──────────────────
            existing = self.db.get_entry_by_project_date(
                self.target_date, project_name, project_code
            )
            if existing:
                label = (
                    f"'{project_name}'" + (f" ({project_code})" if project_code else "")
                )
                ans = QMessageBox.question(
                    self, "Entry Already Exists",
                    f"An entry for {label} already exists today with {existing['hours']}h logged.\n\n"
                    "Update the existing entry instead of creating a new one?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                )
                if ans == QMessageBox.Cancel:
                    return
                if ans == QMessageBox.Yes:
                    self.db.update_entry(
                        existing["id"],
                        description=description,
                        billability=billability,
                        hours=hours,
                        entry_type=entry_type,
                        job_task_no=job_task_no,
                    )
                    if not self.add_mode:
                        self.state.record_popup_saved()
                    self.accept()
                    return
                # No → fall through and create a second entry

            self.db.add_entry(
                self.target_date, project_name, project_code, description,
                billability, hours,
                entry_type=entry_type, job_task_no=job_task_no,
            )

        # Update project master list only for project-type entries
        if is_project:
            self.db.upsert_project(project_name, project_code, description, billability)

        if not self.add_mode and self._entry_id is None:
            self.state.record_popup_saved()

        self.accept()

    # ── Pre-fill for edit mode ────────────────────────────────────────────────

    def prefill(self, entry: dict):
        """Pre-fill form for editing an existing entry (call before exec_())."""
        self._entry_id = entry["id"]
        self.setWindowTitle("Edit Entry")

        entry_type = entry.get("entry_type", "project")
        if entry_type == "ticket":
            self.radio_ticket.setChecked(True)
            self.ticket_no_edit.setText(entry.get("project_code", ""))
        else:
            self.radio_project.setChecked(True)
            self.project_combo.blockSignals(True)
            self.project_combo.setCurrentText(entry.get("project_name", ""))
            self.project_combo.blockSignals(False)
            self.job_no_edit.setText(entry.get("project_code", ""))
            self.job_task_combo.setCurrentText(entry.get("job_task_no", ""))

        self.desc_edit.setPlainText(entry.get("description", ""))
        idx = self.bill_combo.findText(entry.get("billability", "Billable"))
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)
        self.hours_spin.setValue(entry.get("hours", 1.0))
