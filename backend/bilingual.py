# -*- coding: utf-8 -*-
"""
bilingual.py — language detection and glossary-aware EN→KO query translation.

Flow: EN query → inject matching glossary terms → 4o-mini translation →
Korean retrieval query. Korean queries pass through untouched.
"""
import json
import re

from . import config

_HANGUL = re.compile(r"[가-힣]")
_glossary_cache = None


def detect_language(text: str) -> str:
    """'ko' if the query contains a meaningful share of Hangul, else 'en'."""
    letters = [c for c in text if c.isalpha() or _HANGUL.match(c)]
    if not letters:
        return "en"
    hangul = sum(1 for c in letters if _HANGUL.match(c))
    return "ko" if hangul / len(letters) > 0.15 else "en"


def load_glossary() -> list[dict]:
    """All glossary rows as dicts with parsed alias lists (cached)."""
    global _glossary_cache
    if _glossary_cache is None:
        con = config.sqlite_conn_readonly()
        try:
            rows = con.execute(
                "SELECT ko, en, aliases, category FROM glossary"
            ).fetchall()
        finally:
            con.close()
        _glossary_cache = [
            {
                "ko": ko,
                "en": en,
                "aliases": json.loads(aliases) if aliases else [],
                "category": category,
            }
            for ko, en, aliases, category in rows
        ]
    return _glossary_cache


def matching_terms(query_en: str) -> list[dict]:
    """Glossary entries whose EN name or any alias appears in the query."""
    q = query_en.lower()
    hits = []
    for entry in load_glossary():
        candidates = [entry["en"].lower()] + [a.lower() for a in entry["aliases"]]
        if any(c in q for c in candidates):
            hits.append(entry)
    return hits


def to_korean_query(query_en: str) -> str:
    """Translate an English question into a Korean retrieval query,
    forcing correct domain terminology via glossary injection."""
    hints = matching_terms(query_en)
    hint_block = ""
    if hints:
        lines = "\n".join(f"- {h['en']} -> {h['ko']}" for h in hints)
        hint_block = (
            "\nUse EXACTLY these Korean domain terms for the following words:\n"
            f"{lines}\n"
        )
    resp = config.openai_client().chat.completions.create(
        model=config.TRANSLATE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You translate English questions about tunnel construction "
                    "accidents into natural Korean search queries. Output ONLY "
                    "the Korean translation, nothing else." + hint_block
                ),
            },
            {"role": "user", "content": query_en},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()
