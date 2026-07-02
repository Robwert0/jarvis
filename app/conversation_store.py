import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jarvis.db"

TITLE_MAX = 60


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conversations "
        "(id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT, "
        "role TEXT, content TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)"
    )
    return conn


def new_session():
    sid = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (sid, "", now, now),
        )
        conn.commit()
    return sid


def exists(session_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (session_id,)
        ).fetchone()
    return row is not None


def append(session_id, role, content):
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        if role == "user":
            conn.execute(
                "UPDATE conversations SET title = ? "
                "WHERE id = ? AND (title IS NULL OR title = '')",
                (content[:TITLE_MAX], session_id),
            )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        conn.commit()


def get(session_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id",
            (session_id,),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def list_conversations():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    return [{"id": i, "title": t, "updated_at": u} for i, t, u in rows]


def delete_conversation(session_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (session_id,)
        )
        conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (session_id,)
        )
        conn.commit()
        return cur.rowcount > 0
