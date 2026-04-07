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

    # ── Projects ──────────────────────────────────────────────────────────────

    def upsert_project(self, name: str, code: str,
                       default_description: str, billability: str):
        self._conn().execute(
            """INSERT INTO projects (name, code, default_description, billability)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   code=excluded.code,
                   default_description=excluded.default_description,
                   billability=excluded.billability""",
            (name, code, default_description, billability),
        )
        self._conn().commit()

    def get_all_projects(self) -> list[dict]:
        rows = self._conn().execute(
            "SELECT id, name, code, default_description, billability FROM projects ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_project_by_name(self, name: str) -> dict | None:
        row = self._conn().execute(
            "SELECT id, name, code, default_description, billability FROM projects WHERE name=?",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def update_project(self, project_id: int, name: str, code: str,
                       default_description: str, billability: str):
        self._conn().execute(
            """UPDATE projects SET name=?, code=?, default_description=?, billability=?
               WHERE id=?""",
            (name, code, default_description, billability, project_id),
        )
        self._conn().commit()

    def delete_project(self, project_id: int):
        self._conn().execute("DELETE FROM projects WHERE id=?", (project_id,))
        self._conn().commit()

    # ── Entries ───────────────────────────────────────────────────────────────

    def add_entry(self, date_str: str, project_name: str, project_code: str,
                  description: str, billability: str, hours: float,
                  is_auto_added: bool = False) -> int:
        cur = self._conn().execute(
            """INSERT INTO entries
               (date, project_name, project_code, description, billability, hours, is_auto_added, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (date_str, project_name, project_code, description, billability,
             hours, 1 if is_auto_added else 0,
             datetime.now().isoformat(timespec="seconds")),
        )
        self._conn().commit()
        return cur.lastrowid

    def update_entry(self, entry_id: int, **fields):
        if not fields:
            return
        allowed = {"project_name", "project_code", "description", "billability", "hours"}
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
        # Last day of month
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        rows = self._conn().execute(
            "SELECT date, SUM(hours) as total FROM entries WHERE date BETWEEN ? AND ? GROUP BY date",
            (start, end.isoformat()),
        ).fetchall()
        return {r["date"]: r["total"] for r in rows}

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
    # ISO week Monday: Jan 4 is always in week 1
    jan4 = date(iso_year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    return week1_monday + timedelta(weeks=iso_week - 1)
