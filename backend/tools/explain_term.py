# -*- coding: utf-8 -*-
"""tools/explain_term.py — Module D: KO<->EN terminology (glossary table)."""
from .. import bilingual

SCHEMA = {
    "type": "function",
    "function": {
        "name": "explain_term",
        "description": (
            "Look up a tunnel-construction domain term in the KO<->EN glossary. "
            "Works in both directions: Korean term (막장) or English term/alias "
            "(tunnel face, waler). Use when the user asks what a term means, or "
            "when you need the correct translation of a technical term."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "the term to look up"},
            },
            "required": ["term"],
        },
    },
}


def run(term: str) -> list[dict]:
    t = term.strip().lower()
    hits = []
    for e in bilingual.load_glossary():
        haystack = [e["ko"], e["en"].lower()] + [a.lower() for a in e["aliases"]]
        if any(t == h or t in h for h in haystack):
            hits.append(e)
    if not hits:
        return [{"result": f"'{term}' not found in glossary"}]
    return hits[:5]
