import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jarvis.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memories "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)"
    )
    return conn


def remember(content):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO memories (content, created_at) VALUES (?, ?)",
            (content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_memories():
    with _connect() as conn:
        rows = conn.execute("SELECT content FROM memories ORDER BY id").fetchall()
    return [row[0] for row in rows]
