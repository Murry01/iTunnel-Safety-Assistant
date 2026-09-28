# -*- coding: utf-8 -*-
"""config.py — environment, model names, and lazily created clients."""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── models ──────────────────────────────────────────────────────
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o")
TRANSLATE_MODEL = os.getenv("TRANSLATE_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

# ── stores ──────────────────────────────────────────────────────
SQLITE_PATH = os.getenv("SQLITE_PATH", "accidents.db")
LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./lancedb")
LANCE_TABLE = "accidents"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

MAX_TOOL_ROUNDS = 6

_openai = None
_lance_tbl = None
_neo4j = None


def openai_client():
    global _openai
    if _openai is None:
        from openai import OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set (see .env)")
        _openai = OpenAI()
    return _openai


def lance_table():
    global _lance_tbl
    if _lance_tbl is None:
        import lancedb
        db = lancedb.connect(LANCEDB_DIR)
        _lance_tbl = db.open_table(LANCE_TABLE)
    return _lance_tbl


def neo4j_driver():
    global _neo4j
    if _neo4j is None:
        from neo4j import GraphDatabase
        _neo4j = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _neo4j.verify_connectivity()
    return _neo4j


def sqlite_conn_readonly():
    """Read-only connection so LLM-generated SQL can never modify data."""
    import sqlite3
    return sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)
