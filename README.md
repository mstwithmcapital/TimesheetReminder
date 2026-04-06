# Timesheet Reminder

A desktop timesheet tracking app for Windows. Logs work entries throughout the day via hourly popups, displays a calendar overview, and exports weekly timesheets to Excel.

## Features

- **Hourly popups** — Prompts for what you worked on between 11 AM and 7:30 PM on workdays and the first Saturday of the month. Auto-calculates elapsed time (clamped to 0.25–4.0 hours), editable before saving.
- **Project autocomplete** — Remembers project codes, descriptions, and billability for fast re-entry.
- **Daily target** — 8.5 hours. Calendar cells colour green when met, red when not.
- **Fixed daily entry** — "Internal Meeting" (0.5h, Non-Billable) is added automatically each day on first launch.
- **End-of-day summary** — Fires once between 7:25–7:35 PM, shows the day's entries, and warns if below target.
- **Friday/Saturday reminders** — Every 30 minutes after 4 PM on Fridays, and from 10 AM on the first Saturday of the month, until you mark the timesheet as submitted.
- **Excel export** — Export the current week to `.xlsx` from the toolbar or the weekly summary dialog.

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | PyQt5 |
| Database | SQLite (built-in `sqlite3`) |
| Excel export | openpyxl |
| Scheduling | schedule |

## Project Structure

```
main.py                  # QApplication entry point, daily auto-entry
database.py              # Database class, all SQLite operations
state.py                 # AppState: popup timing, submission flags
scheduler.py             # SchedulerThread + SchedulerBridge (signals)
ui/
  main_window.py         # QMainWindow, QSplitter layout, system tray
  calendar_widget.py     # TimesheetCalendar with green/red cell painting
  day_detail_panel.py    # Editable entry table for the selected day
  work_popup.py          # Hourly "What are you working on?" dialog
  end_of_day_dialog.py   # 7:30 PM EOD summary dialog
  weekly_summary_dialog.py  # Friday/Saturday reminder + Mark Submitted
  export.py              # export_week_to_excel()
```

## Data Storage

App data is stored in `%APPDATA%\TimesheetReminder\`:

- `timesheet.db` — SQLite database with all entries
- `state.json` — Runtime state (last popup time, submission flags)

## Setup

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the app:
   ```
   python main.py
   ```

## Requirements

- Windows
- Python 3.8+
