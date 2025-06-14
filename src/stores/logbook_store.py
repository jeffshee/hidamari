import sqlite3
import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .paths_config import LOGBOOK_DB_PATH


def __connect():
    conn = sqlite3.connect(LOGBOOK_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def __initialize_logbook_db():
    if not os.path.exists(LOGBOOK_DB_PATH):
        with __connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS logbook (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hostile_count INTEGER NOT NULL,
                    hostile_list TEXT,
                    scan_target TEXT,
                    engine TEXT,
                    db_version TEXT,
                    db_date TEXT,
                    duration REAL,
                    notes TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_logbook_timestamp
                ON logbook(timestamp)
                """
            )
            conn.commit()


def __eradicate_logbook_db():
    if os.path.exists(LOGBOOK_DB_PATH):
        os.remove(LOGBOOK_DB_PATH)


def clear_all_log_entries():
    with __connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logbook")
        conn.commit()


def add_logbook_entry(
    hostile_count: int,
    hostile_list: Optional[list] = None,
    scan_target: Optional[str] = None,
    engine: Optional[str] = None,
    db_version: Optional[str] = None,
    db_date: Optional[str] = None,
    duration: Optional[float] = None,
    notes: Optional[str] = None,
):
    timestamp = datetime.now().isoformat()
    hostile_list_json = json.dumps(hostile_list) if hostile_list is not None else None

    with __connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logbook (
                timestamp, hostile_count, hostile_list, scan_target,
                engine, db_version, db_date, duration, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                hostile_count,
                hostile_list_json,
                scan_target,
                engine,
                db_version,
                db_date,
                duration,
                notes,
            ),
        )
        conn.commit()


def get_logbook_entries(limit: int = 10) -> List[Dict]:
    with __connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, hostile_count, hostile_list, scan_target,
                   engine, db_version, db_date, duration, notes
            FROM logbook
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

    entries = []
    for row in rows:
        entries.append(
            {
                "id": row["id"],
                "timestamp": datetime.fromisoformat(row["timestamp"]).strftime("%c"),
                "hostile_count": row["hostile_count"],
                "hostile_list": (
                    json.loads(row["hostile_list"]) if row["hostile_list"] else None
                ),
                "scan_target": row["scan_target"],
                "engine": row["engine"],
                "db_version": row["db_version"],
                "db_date": row["db_date"],
                "duration": (
                    str(timedelta(seconds=row["duration"])) if row["duration"] else None
                ),
                "notes": row["notes"],
            }
        )
    return entries


def delete_logbook_entry(entry_id: int):
    with __connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logbook WHERE id = ?", (entry_id,))
        conn.commit()


# Automatically initialize DB when imported
__initialize_logbook_db()
