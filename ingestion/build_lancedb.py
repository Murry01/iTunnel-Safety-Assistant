# -*- coding: utf-8 -*-
"""
build_lancedb.py — Module A (hybrid semantic search).

Creates ./lancedb/accidents:
  - one row per accident
  - text  : composed document (6 narrative columns, Korean section labels)
  - vector: text-embedding-3-large (3072 dims, multilingual)
  - metadata columns for filtered search (English identifiers)
  - FTS index on text (created only if absent — no rebuild on rerun)

Requires: OPENAI_API_KEY environment variable.
  PowerShell:  $env:OPENAI_API_KEY = "sk-..."

Usage (from the project root):
  python ingestion\build_lancedb.py
  python ingestion\build_lancedb.py Tunnel_data_master.csv ./lancedb
"""
import os
import sys

import lancedb
from openai import OpenAI

from common import compose_document, load_master

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMS = 3072
TABLE_NAME = "accidents"
BATCH_SIZE = 64  # rows per embedding API call

METADATA_COLS = [
    "case_id", "tunnel_type", "accident_type",
    "object_l1", "object_l2", "work_process",
    "cause_l1", "cause_l2", "cause_l3", "fatalities",
]


def embed_batches(client: OpenAI, texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        vectors.extend(d.embedding for d in resp.data)
        print(f"  embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return vectors


def main(src: str, db_dir: str) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "[error] OPENAI_API_KEY is not set.\n"
            '  PowerShell:  $env:OPENAI_API_KEY = "sk-..."'
        )
    client = OpenAI()
    df = load_master(src)

    print("[compose] building documents...")
    texts = [compose_document(row) for _, row in df.iterrows()]
    lengths = [len(t) for t in texts]
    print(f"  doc length: min={min(lengths)}, max={max(lengths)}, mean={sum(lengths)//len(lengths)}")

    print(f"[embed] {EMBED_MODEL} ({EMBED_DIMS} dims)...")
    vectors = embed_batches(client, texts)

    records = []
    for (_, row), text, vec in zip(df.iterrows(), texts, vectors):
        rec = {"text": text, "vector": vec}
        for col in METADATA_COLS:
            rec[col] = row[col].item() if hasattr(row[col], "item") else row[col]
        records.append(rec)

    db = lancedb.connect(db_dir)
    existing = db.list_tables().tables  # table_names() is deprecated
    if TABLE_NAME in existing:
        db.drop_table(TABLE_NAME)
        print(f"[lancedb] dropped existing table '{TABLE_NAME}'")
    tbl = db.create_table(TABLE_NAME, data=records)
    print(f"[lancedb] created '{TABLE_NAME}' with {tbl.count_rows()} rows")

    # FTS index: create only if absent (replace=False; no rebuild on rerun)
    index_names = [idx.name for idx in tbl.list_indices()]
    if not any("text" in name for name in index_names):
        tbl.create_fts_index("text", replace=False)
        print("[lancedb] FTS index created on 'text'")
    else:
        print("[lancedb] FTS index already exists — skipped")

    # smoke test: hybrid search via the native API (as in HybridLanceRetriever)
    q = "안전고리 미체결 추락"
    qvec = client.embeddings.create(model=EMBED_MODEL, input=[q]).data[0].embedding
    hits = (
        tbl.search(query_type="hybrid")
        .vector(qvec)
        .text(q)
        .limit(3)
        .to_list()
    )
    print(f"[smoke test] '{q}' -> {[h['case_id'] for h in hits]}")
    print("[done]")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "Tunnel_data_master.csv"
    db_dir = sys.argv[2] if len(sys.argv) > 2 else "./lancedb"
    main(src, db_dir)
