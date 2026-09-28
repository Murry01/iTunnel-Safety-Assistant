# -*- coding: utf-8 -*-
"""
chatstore.py — SQLite-backed persistence for chat conversations.

Kept separate from accidents.db (the read-only domain dataset) so app state
and the case archive never share a file. Each function opens and closes its
own short-lived connection, same pattern as config.sqlite_conn_readonly().
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

CHATSTORE_PATH = os.getenv("CHATSTORE_PATH", "chats.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    case_ids TEXT,
    charts TEXT,
    ts TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(CHATSTORE_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(_SCHEMA)
    return con


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_conversation(title: str) -> str:
    conv_id = str(uuid.uuid4())
    now = _now()
    con = _conn()
    try:
        con.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now),
        )
        con.commit()
    finally:
        con.close()
    return conv_id


def list_conversations() -> list[dict]:
    con = _conn()
    try:
        rows = con.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    finally:
        con.close()
    return [
        {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]


def load_messages(conversation_id: str) -> list[dict]:
    con = _conn()
    try:
        rows = con.execute(
            "SELECT role, content, case_ids, charts FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "role": r[0],
            "content": r[1],
            "case_ids": json.loads(r[2]) if r[2] else [],
            "charts": json.loads(r[3]) if r[3] else [],
        }
        for r in rows
    ]


def append_message(
    conversation_id: str,
    role: str,
    content: str,
    case_ids: list[str] | None = None,
    charts: list[dict] | None = None,
) -> None:
    con = _conn()
    try:
        con.execute(
            "INSERT INTO messages (conversation_id, role, content, case_ids, charts, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                conversation_id,
                role,
                content,
                json.dumps(case_ids, ensure_ascii=False) if case_ids else None,
                json.dumps(charts, ensure_ascii=False) if charts else None,
                _now(),
            ),
        )
        con.commit()
    finally:
        con.close()


def set_title(conversation_id: str, title: str) -> None:
    con = _conn()
    try:
        con.execute(
            "UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id)
        )
        con.commit()
    finally:
        con.close()


def touch(conversation_id: str) -> None:
    con = _conn()
    try:
        con.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )
        con.commit()
    finally:
        con.close()


def delete_conversation(conversation_id: str) -> None:
    con = _conn()
    try:
        con.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        con.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        con.commit()
    finally:
        con.close()


def title_from_text(text: str, max_len: int = 50) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"
