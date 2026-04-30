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

    Auto-fill priority: master table → most recent history entry.
    Billability defaults to "Billable" for all entries.
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
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowStaysOnTopHint
            | Qt.WindowMinimizeButtonHint
        )

        self._build_form()
        self._load_masters()

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

        self.ticket_no_combo = QComboBox()
        self.ticket_no_combo.setEditable(True)
        self.ticket_no_combo.setInsertPolicy(QComboBox.NoInsert)
        self.ticket_no_combo.lineEdit().setPlaceholderText("e.g. INC-12345")
        self.ticket_no_combo.currentTextChanged.connect(self._on_ticket_no_changed)
        ticket_form.addRow("Ticket No *", self.ticket_no_combo)

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
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        shared_form.addRow("Description *", self.desc_edit)

        self.desc_char_label = QLabel("0/200")
        self.desc_char_label.setStyleSheet("color:#888; font-size:11px;")
        self.desc_char_label.setAlignment(Qt.AlignRight)
        shared_form.addRow("", self.desc_char_label)

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

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_masters(self):
        """Populate all dropdowns from master tables + entry history."""
        # ── Project master ────────────────────────────────────────────────────
        projects = self.db.get_all_projects()
        self._project_map = {p["name"]: p for p in projects}          # name → project
        self._project_code_map = {p["code"]: p for p in projects if p["code"]}  # code → project

        names = [p["name"] for p in projects]
        self.project_combo.clear()
        self.project_combo.addItems(names)
        self.project_combo.setCurrentText("")

        name_completer = QCompleter(names, self)
        name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        name_completer.setFilterMode(Qt.MatchContains)
        self.project_combo.setCompleter(name_completer)

        # Job No — merge master codes + history codes (deduped, master first)
        master_codes = [p["code"] for p in projects if p["code"]]
        history_codes = self.db.get_distinct_codes("project")
        all_job_nos = master_codes + [c for c in history_codes if c not in master_codes]
        self._job_no_list = set(all_job_nos)
        job_completer = QCompleter(all_job_nos, self)
        job_completer.setCaseSensitivity(Qt.CaseInsensitive)
        job_completer.setFilterMode(Qt.MatchContains)
        self.job_no_edit.setCompleter(job_completer)
        self.job_no_edit.textChanged.connect(self._on_job_no_changed)

        # Job Task No — merge master task nos + history
        master_tasks = list({p["job_task_no"] for p in projects if p.get("job_task_no")})
        history_tasks = self.db.get_distinct_task_nos()
        all_tasks = master_tasks + [t for t in history_tasks if t not in master_tasks]
        self._task_no_list = set(all_tasks)
        self.job_task_combo.clear()
        self.job_task_combo.addItem("")
        self.job_task_combo.addItems(all_tasks)
        self.job_task_combo.addItem("+ New Task No.")
        self.job_task_combo.setCurrentIndex(0)
        task_completer = QCompleter(all_tasks, self)
        task_completer.setCaseSensitivity(Qt.CaseInsensitive)
        task_completer.setFilterMode(Qt.MatchContains)
        self.job_task_combo.setCompleter(task_completer)

        # ── Ticket master ─────────────────────────────────────────────────────
        tickets = self.db.get_all_tickets()
        self._ticket_master_map = {t["ticket_no"]: t for t in tickets}

        master_ticket_nos = [t["ticket_no"] for t in tickets]
        history_ticket_nos = self.db.get_distinct_codes("ticket")
        all_ticket_nos = master_ticket_nos + [n for n in history_ticket_nos if n not in master_ticket_nos]
        self._ticket_no_list = set(all_ticket_nos)
        self.ticket_no_combo.clear()
        self.ticket_no_combo.addItem("")
        self.ticket_no_combo.addItems(all_ticket_nos)
        self.ticket_no_combo.setCurrentIndex(0)
        ticket_completer = QCompleter(all_ticket_nos, self)
        ticket_completer.setCaseSensitivity(Qt.CaseInsensitive)
        ticket_completer.setFilterMode(Qt.MatchContains)
        self.ticket_no_combo.setCompleter(ticket_completer)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_type_changed(self, project_selected: bool):
        self.project_widget.setVisible(project_selected)
        self.ticket_widget.setVisible(not project_selected)
        self.adjustSize()

    def _on_project_changed(self, name: str):
        """Selecting a project name auto-fills all project fields from master."""
        proj = self._project_map.get(name)
        if not proj:
            return
        if proj["code"]:
            self.job_no_edit.blockSignals(True)
            self.job_no_edit.setText(proj["code"])
            self.job_no_edit.blockSignals(False)
        if proj.get("job_task_no"):
            self.job_task_combo.setCurrentText(proj["job_task_no"])
        if proj["default_description"]:
            self.desc_edit.setPlainText(proj["default_description"])
        idx = self.bill_combo.findText(proj["billability"])
        if idx >= 0:
            self.bill_combo.setCurrentIndex(idx)

    def _on_job_no_changed(self, code: str):
        """Selecting a known job no auto-fills fields — master table first, then history."""
        if not code:
            return
        # 1. Try project master by code
        proj = self._project_code_map.get(code)
        if proj:
            if proj.get("job_task_no") and not self.job_task_combo.currentText().strip():
                self.job_task_combo.setCurrentText(proj["job_task_no"])
            if proj["default_description"] and not self.desc_edit.toPlainText().strip():
                self.desc_edit.setPlainText(proj["default_description"])
            idx = self.bill_combo.findText(proj["billability"])
            if idx >= 0:
                self.bill_combo.setCurrentIndex(idx)
            return
        # 2. Fall back to most recent entry with this code
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
        """Selecting a known ticket no auto-fills fields — master table first, then history."""
        if not code:
            return
        # 1. Try ticket master
        tkt = self._ticket_master_map.get(code)
        if tkt:
            if tkt["description"] and not self.desc_edit.toPlainText().strip():
                self.desc_edit.setPlainText(tkt["description"])
            idx = self.bill_combo.findText(tkt["billability"])
            if idx >= 0:
                self.bill_combo.setCurrentIndex(idx)
            return
        # 2. Fall back to most recent entry with this ticket no
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

    def _on_desc_changed(self):
        text = self.desc_edit.toPlainText()
        if len(text) > 200:
            cursor = self.desc_edit.textCursor()
            pos = cursor.position()
            self.desc_edit.blockSignals(True)
            self.desc_edit.setPlainText(text[:200])
            self.desc_edit.blockSignals(False)
            cursor.setPosition(min(pos, 200))
            self.desc_edit.setTextCursor(cursor)
            text = text[:200]
        self.desc_char_label.setText(f"{len(text)}/200")

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
            ticket_no = self.ticket_no_combo.currentText().strip()
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

            self.db.add_entry(
                self.target_date, project_name, project_code, description,
                billability, hours,
                entry_type=entry_type, job_task_no=job_task_no,
            )

        # Update project master list only for project-type entries
        if is_project:
            self.db.upsert_project(project_name, project_code, job_task_no,
                                   description, billability)

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
            self.ticket_no_combo.setCurrentText(entry.get("project_code", ""))
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
