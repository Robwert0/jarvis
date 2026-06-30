import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "macros.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS macros (name TEXT PRIMARY KEY, apps TEXT NOT NULL)"
    )
    return conn


def get_macro(name):
    with _connect() as conn:
        row = conn.execute(
            "SELECT apps FROM macros WHERE name = ?", (name,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def list_macros():
    with _connect() as conn:
        rows = conn.execute("SELECT name, apps FROM macros").fetchall()
    return {name: json.loads(apps) for name, apps in rows}


def upsert_macro(name, apps):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO macros (name, apps) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET apps = excluded.apps",
            (name, json.dumps(apps)),
        )
        conn.commit()
