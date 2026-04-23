# TimesheetReminder — Project Context

## What it is
A Windows system-tray PyQt5 desktop app that reminds users to log work hours throughout the day. Built with Python + PyQt5, stores data in SQLite via `%APPDATA%\TimesheetReminder\timesheet.db`.

## Tech stack
- **Python 3.11+**, **PyQt5 ≥ 5.15.9**
- **SQLite** (via `sqlite3` stdlib) — thread-local connections, WAL mode
- **openpyxl** — Excel export
- **schedule** — background reminder scheduling

## Entry points
- `main.py` — bootstraps app, system tray icon, starts scheduler thread
- `ui/main_window.py` — central widget hosting calendar + day panel
- `scheduler.py` — background thread that fires work popups on interval
- `config.py` — `AppConfig` dataclass, JSON-persisted settings
- `state.py` — `AppState` — tracks last-popup timestamps

## Database schema (`database.py`)
Table **entries**: `id, date, project_name, project_code, description, billability, hours, is_auto_added, created_at, entry_type, job_task_no`
- `entry_type`: `"project"` | `"ticket"`
- `project_code` = Job No (for project) or Ticket No (for ticket)
- `job_task_no` = Job Task No (project entries only)
- Schema migrations are idempotent ALTER TABLE calls run on every start

Table **projects**: `id, name, code, default_description, billability` — master project list, auto-upserted on each project entry save

Key DB methods:
- `get_distinct_codes(entry_type)` — distinct `project_code` values, most-used first
- `get_distinct_task_nos()` — distinct `job_task_no` values, most-used first
- `get_latest_entry_by_code(code, entry_type)` — for auto-fill

## UI components (`ui/`)
| File | Purpose |
|------|---------|
| `main_window.py` | Splits into calendar (left) + day-detail panel (right) |
| `calendar_widget.py` | Monthly calendar, colours days by hours logged |
| `day_detail_panel.py` | Table of entries for selected date; inline bill/hours edit |
| `work_popup.py` | Work-logging dialog (popup + manual add/edit) |
| `project_manager_dialog.py` | CRUD for the projects master table |
| `settings_dialog.py` | Reminder interval, target hours, notification style |
| `end_of_day_dialog.py` | EOD summary / export prompt |
| `weekly_summary_dialog.py` | Weekly hours breakdown |
| `export.py` | Excel export logic |
| `icons.py` | Programmatic SVG icon generation |

## Work popup field layout (entry_type=project)
Project Name (QComboBox, editable) → Job No (QLineEdit + autocomplete) → Job Task No (QComboBox editable, "+ New Task No." option) → Description → Billability → Hours

Ticket entry: Job Type = "Support" (static) → Ticket No (QLineEdit + autocomplete)

## Key patterns
- Auto-fill: selecting a known Job No auto-fills description + billability from most recent entry with that code
- Duplicate guard: same project+code on same date → prompt to merge or create new row
- `is_auto_added=1` entries shown in grey and excluded from distinct-code lookups
- All non-editable table cells use `Qt.ItemIsEditable` flag removal; live edit uses cell widgets (QComboBox, QDoubleSpinBox)

## Features added (chronological)
1. Continuous-run reminder with configurable interval
2. Edit existing entries (prefill dialog)
3. Project/Ticket entry type split
4. Auto-populate Job No and Ticket No dropdowns from history
5. Job Task No field added to entries schema (migration)
6. Job Task No converted to editable QComboBox with "+ New Task No." option and history dropdown
