# -*- coding: utf-8 -*-
"""
common.py — shared loader for the construction_rag ingestion scripts.
Reads Tunnel_data_master.csv (utf-8-sig) and renames columns to English identifiers.
"""
import sys
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env in the current folder, if present
except ImportError:
    pass  # dotenv not installed — environment variables still work

sys.stdout.reconfigure(encoding="utf-8")

MASTER_CSV = "Tunnel_data_master.csv"

# Korean source column -> English identifier (used across all stores)
COLUMN_MAP = {
    "case_id": "case_id",
    "터널분류": "tunnel_type",
    "사고종류": "accident_type",
    "사고객체-대분류": "object_l1",
    "사고객체-소분류": "object_l2",
    "작업프로세스": "work_process",
    "사고원인-대분류": "cause_l1",
    "사고원인-중분류": "cause_l2",
    "사고원인-소분류": "cause_l3",
    "구체적사고원인": "specific_cause",
    "사망자": "fatalities",
    "피해내용": "damage",
    "향후조치계획": "future_plan",
    "사고경위": "narrative",
    "사고발생후 조치사항": "post_actions",
    "재발방지대책": "prevention",
}

# English identifier -> Korean label (for composing readable documents)
KO_LABEL = {v: k for k, v in COLUMN_MAP.items()}

NARRATIVE_COLS = [
    "narrative", "specific_cause", "damage",
    "prevention", "future_plan", "post_actions",
]


def load_master(path: str = MASTER_CSV) -> pd.DataFrame:
    """Load the master CSV with English column names and basic validation."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(
            f"[error] {path} not found. Place Tunnel_data_master.csv "
            f"in the same folder or pass the path as the first argument."
        )
    df = pd.read_csv(p, encoding="utf-8-sig")
    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise SystemExit(f"[error] source is missing columns: {missing}")
    df = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    df["fatalities"] = df["fatalities"].fillna(0).astype(int)
    for col in NARRATIVE_COLS:
        df[col] = df[col].fillna("")
    if not df["case_id"].is_unique:
        raise SystemExit("[error] case_id values are not unique")
    print(f"[load] {len(df)} rows from {path}")
    return df


def compose_document(row: pd.Series) -> str:
    """One embeddable document per accident, with Korean section labels."""
    parts = []
    for col in NARRATIVE_COLS:
        text = str(row[col]).strip()
        if text:
            parts.append(f"{KO_LABEL[col]}: {text}")
    return "\n\n".join(parts)
