"""
SQLite Database Layer for Case Persistence.
Implements ARCHITECTURE.md §4 and DATA_SCHEMA.md §1.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import DB_PATH
from backend.models import CaseObject


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initializes the SQLite schema.
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_name TEXT,
                status TEXT NOT NULL,
                structured_data TEXT NOT NULL
            )
        """)
        conn.commit()


def save_case(case: CaseObject) -> None:
    """
    Inserts or updates a case object in SQLite.
    """
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    case.updated_at = now_iso

    user_name = case.basic_info.name if case.basic_info and case.basic_info.name else None
    data_json = case.model_dump_json()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO cases (case_id, created_at, updated_at, user_name, status, structured_data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                user_name = excluded.user_name,
                status = excluded.status,
                structured_data = excluded.structured_data
        """, (case.case_id, case.created_at, case.updated_at, user_name, case.status, data_json))
        conn.commit()


def get_case(case_id: str) -> Optional[CaseObject]:
    """
    Retrieves a case by case_id.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT structured_data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = json.loads(row["structured_data"])
        return CaseObject(**data)


def delete_case(case_id: str) -> bool:
    """
    Deletes a case from SQLite (privacy / delete my data).
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
        conn.commit()
        return cursor.rowcount > 0


def list_cases() -> List[Dict[str, Any]]:
    """
    Returns high-level metadata for all stored cases.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT case_id, created_at, updated_at, user_name, status FROM cases ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
