import os
import sqlite3
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.getenv("APPDATA", "")) / "TimesheetReminder" / "timesheet.db"

_local = threading.local()


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(_local, "conn") or _local.conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _local.conn = conn
        return _local.conn

    def initialize(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                code                TEXT NOT NULL DEFAULT '',
                default_description TEXT NOT NULL DEFAULT '',
                billability         TEXT NOT NULL DEFAULT 'Billable'
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no   TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                billability TEXT NOT NULL DEFAULT 'Billable'
            );

            CREATE TABLE IF NOT EXISTS entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                date          TEXT NOT NULL,
                project_name  TEXT NOT NULL,
                project_code  TEXT NOT NULL DEFAULT '',
                description   TEXT NOT NULL DEFAULT '',
                billability   TEXT NOT NULL DEFAULT 'Billable',
                hours         REAL NOT NULL DEFAULT 1.0,
                is_auto_added INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
        """)
        c.commit()

        # Schema migrations — idempotent, safe to run on every start
        for col, defn in [
            ("entry_type", "TEXT NOT NULL DEFAULT 'project'"),
            ("job_task_no", "TEXT NOT NULL DEFAULT ''"),
        ]:
            try:
                c.execute(f"ALTER TABLE entries ADD COLUMN {col} {defn}")
                c.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

        # projects table migrations
        try:
            c.execute("ALTER TABLE projects ADD COLUMN job_task_no TEXT NOT NULL DEFAULT ''")
            c.commit()
        except sqlite3.OperationalError:
            pass

    # ── Projects ──────────────────────────────────────────────────────────────

    def upsert_project(self, name: str, code: str, job_task_no: str,
                       default_description: str, billability: str):
        self._conn().execute(
            """INSERT INTO projects (name, code, job_task_no, default_description, billability)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   code=excluded.code,
                   job_task_no=excluded.job_task_no,
                   default_description=excluded.default_description,
                   billability=excluded.billability""",
            (name, code, job_task_no, default_description, billability),
        )
        self._conn().commit()

    def get_all_projects(self) -> list[dict]:
        rows = self._conn().execute(
            "SELECT id, name, code, job_task_no, default_description, billability FROM projects ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_project_by_name(self, name: str) -> dict | None:
        row = self._conn().execute(
            "SELECT id, name, code, job_task_no, default_description, billability FROM projects WHERE name=?",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def get_project_by_code(self, code: str) -> dict | None:
        """Return first matching project for a given job no / code."""
        row = self._conn().execute(
            "SELECT id, name, code, job_task_no, default_description, billability FROM projects WHERE code=?",
            (code,),
        ).fetchone()
        return dict(row) if row else None

    def update_project(self, project_id: int, name: str, code: str, job_task_no: str,
                       default_description: str, billability: str):
        self._conn().execute(
            """UPDATE projects SET name=?, code=?, job_task_no=?, default_description=?, billability=?
               WHERE id=?""",
            (name, code, job_task_no, default_description, billability, project_id),
        )
        self._conn().commit()

    def delete_project(self, project_id: int):
        self._conn().execute("DELETE FROM projects WHERE id=?", (project_id,))
        self._conn().commit()

    # ── Tickets ───────────────────────────────────────────────────────────────

    def upsert_ticket(self, ticket_no: str, description: str, billability: str):
        self._conn().execute(
            """INSERT INTO tickets (ticket_no, description, billability)
               VALUES (?, ?, ?)
               ON CONFLICT(ticket_no) DO UPDATE SET
                   description=excluded.description,
                   billability=excluded.billability""",
            (ticket_no, description, billability),
        )
        self._conn().commit()

    def get_all_tickets(self) -> list[dict]:
        rows = self._conn().execute(
            "SELECT id, ticket_no, description, billability FROM tickets ORDER BY ticket_no"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_ticket_by_no(self, ticket_no: str) -> dict | None:
        row = self._conn().execute(
            "SELECT id, ticket_no, description, billability FROM tickets WHERE ticket_no=?",
            (ticket_no,),
        ).fetchone()
        return dict(row) if row else None

    def update_ticket(self, ticket_id: int, ticket_no: str, description: str, billability: str):
        self._conn().execute(
            "UPDATE tickets SET ticket_no=?, description=?, billability=? WHERE id=?",
            (ticket_no, description, billability, ticket_id),
        )
        self._conn().commit()

    def delete_ticket(self, ticket_id: int):
        self._conn().execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        self._conn().commit()

    # ── Entries ───────────────────────────────────────────────────────────────

    def add_entry(self, date_str: str, project_name: str, project_code: str,
                  description: str, billability: str, hours: float,
                  is_auto_added: bool = False,
                  entry_type: str = "project", job_task_no: str = "") -> int:
        cur = self._conn().execute(
            """INSERT INTO entries
               (date, project_name, project_code, description, billability, hours,
                is_auto_added, created_at, entry_type, job_task_no)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date_str, project_name, project_code, description, billability,
             hours, 1 if is_auto_added else 0,
             datetime.now().isoformat(timespec="seconds"),
             entry_type, job_task_no),
        )
        self._conn().commit()
        return cur.lastrowid

    def update_entry(self, entry_id: int, **fields):
        if not fields:
            return
        allowed = {"project_name", "project_code", "description", "billability",
                   "hours", "entry_type", "job_task_no"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self._conn().execute(
            f"UPDATE entries SET {set_clause} WHERE id=?",
            (*fields.values(), entry_id),
        )
        self._conn().commit()

    def delete_entry(self, entry_id: int):
        self._conn().execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self._conn().commit()

    def get_entries_for_date(self, date_str: str) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM entries WHERE date=? ORDER BY created_at",
            (date_str,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_entries_for_week(self, iso_year: int, iso_week: int) -> list[dict]:
        monday = _monday_of_iso_week(iso_year, iso_week)
        sunday = monday + timedelta(days=6)
        rows = self._conn().execute(
            "SELECT * FROM entries WHERE date BETWEEN ? AND ? ORDER BY date, created_at",
            (monday.isoformat(), sunday.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_daily_totals_for_month(self, year: int, month: int) -> dict[str, float]:
        start = date(year, month, 1).isoformat()
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        rows = self._conn().execute(
            "SELECT date, SUM(hours) as total FROM entries WHERE date BETWEEN ? AND ? GROUP BY date",
            (start, end.isoformat()),
        ).fetchall()
        return {r["date"]: r["total"] for r in rows}

    def get_daily_total(self, date_str: str) -> float:
        row = self._conn().execute(
            "SELECT COALESCE(SUM(hours), 0.0) as total FROM entries WHERE date=?",
            (date_str,),
        ).fetchone()
        return float(row["total"]) if row else 0.0

    def get_entry_by_id(self, entry_id: int) -> dict | None:
        row = self._conn().execute(
            "SELECT * FROM entries WHERE id=?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_distinct_codes(self, entry_type: str) -> list[str]:
        """Return distinct non-empty project_codes for the given entry_type, most-used first."""
        rows = self._conn().execute(
            """SELECT project_code, COUNT(*) as cnt
               FROM entries
               WHERE entry_type=? AND project_code != '' AND is_auto_added=0
               GROUP BY project_code
               ORDER BY cnt DESC, project_code ASC""",
            (entry_type,),
        ).fetchall()
        return [r["project_code"] for r in rows]

    def get_distinct_task_nos(self) -> list[str]:
        """Return distinct non-empty job_task_no values, most-used first."""
        rows = self._conn().execute(
            """SELECT job_task_no, COUNT(*) as cnt
               FROM entries
               WHERE job_task_no != '' AND is_auto_added=0
               GROUP BY job_task_no
               ORDER BY cnt DESC, job_task_no ASC"""
        ).fetchall()
        return [r["job_task_no"] for r in rows]

    def get_latest_entry_by_code(self, project_code: str, entry_type: str) -> dict | None:
        """Return the most recently created entry for a given code and type."""
        row = self._conn().execute(
            """SELECT * FROM entries
               WHERE project_code=? AND entry_type=? AND is_auto_added=0
               ORDER BY created_at DESC LIMIT 1""",
            (project_code, entry_type),
        ).fetchone()
        return dict(row) if row else None

    def get_entry_by_project_date(self, date_str: str, project_name: str,
                                   project_code: str) -> dict | None:
        row = self._conn().execute(
            """SELECT * FROM entries
               WHERE date=? AND project_name=? AND project_code=?
               AND is_auto_added=0 LIMIT 1""",
            (date_str, project_name, project_code),
        ).fetchone()
        return dict(row) if row else None

    def has_auto_entry_today(self, date_str: str) -> bool:
        row = self._conn().execute(
            "SELECT 1 FROM entries WHERE date=? AND is_auto_added=1 LIMIT 1",
            (date_str,),
        ).fetchone()
        return row is not None

    def get_entries_grouped_by_project(self, date_from: str, date_to: str) -> list[dict]:
        rows = self._conn().execute(
            """SELECT project_name, project_code, billability,
                      SUM(hours) as total_hours,
                      COUNT(*) as entry_count
               FROM entries
               WHERE date BETWEEN ? AND ?
               GROUP BY project_name, project_code, billability
               ORDER BY total_hours DESC""",
            (date_from, date_to),
        ).fetchall()
        return [dict(r) for r in rows]


def _monday_of_iso_week(iso_year: int, iso_week: int) -> date:
    jan4 = date(iso_year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    return week1_monday + timedelta(weeks=iso_week - 1)
