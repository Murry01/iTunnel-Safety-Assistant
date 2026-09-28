# -*- coding: utf-8 -*-
"""
build_sqlite.py — Module C (statistics) + Module D (glossary).

Builds accidents.db with two tables:
  accidents : all 16 columns, English identifiers
  glossary  : KO<->EN terminology, seeded with 25 starter terms

Usage (PowerShell, from the project root):
  python ingestion\build_sqlite.py
  python ingestion\build_sqlite.py Tunnel_data_master.csv accidents.db
"""
import sqlite3
import sys

from common import load_master

ACCIDENTS_DDL = """
CREATE TABLE accidents (
  case_id        TEXT PRIMARY KEY,   -- TA-0001 .. TA-0310
  tunnel_type    TEXT NOT NULL,      -- 터널분류
  accident_type  TEXT NOT NULL,      -- 사고종류
  object_l1      TEXT,               -- 사고객체-대분류
  object_l2      TEXT,               -- 사고객체-소분류
  work_process   TEXT,               -- 작업프로세스
  cause_l1       TEXT,               -- 사고원인-대분류
  cause_l2       TEXT,               -- 사고원인-중분류
  cause_l3       TEXT,               -- 사고원인-소분류
  specific_cause TEXT,               -- 구체적사고원인
  fatalities     INTEGER NOT NULL DEFAULT 0,  -- 사망자
  damage         TEXT,               -- 피해내용
  future_plan    TEXT,               -- 향후조치계획
  narrative      TEXT,               -- 사고경위
  post_actions   TEXT,               -- 사고발생후 조치사항
  prevention     TEXT                -- 재발방지대책
);
"""

GLOSSARY_DDL = """
CREATE TABLE glossary (
  ko       TEXT PRIMARY KEY,
  en       TEXT NOT NULL,
  aliases  TEXT,     -- JSON array as text, e.g. '["face","heading"]'
  category TEXT
);
"""

INDEXES = [
    "CREATE INDEX idx_tunnel_type   ON accidents (tunnel_type);",
    "CREATE INDEX idx_accident_type ON accidents (accident_type);",
    "CREATE INDEX idx_work_process  ON accidents (work_process);",
    "CREATE INDEX idx_cause_l3      ON accidents (cause_l3);",
    "CREATE INDEX idx_fatalities    ON accidents (fatalities);",
]

STARTER_GLOSSARY = [
    ("막장",     "tunnel face",        '["face","heading","tunnel heading"]',   "excavation"),
    ("띠장",     "wale",               '["waler","wale beam"]',                 "temporary works"),
    ("강지보재", "steel rib",          '["steel support","steel rib support"]', "support"),
    ("흙막이",   "earth retention",    '["retaining wall","earth retaining"]',  "temporary works"),
    ("가시설",   "temporary facility", '["temporary works","falsework"]',       "temporary works"),
    ("부석",     "loose rock",         '["scaling rock","loose stone"]',        "excavation"),
    ("숏크리트", "shotcrete",          '["sprayed concrete"]',                  "support"),
    ("라이닝",   "tunnel lining",      '["lining","concrete lining"]',          "structure"),
    ("갱구부",   "tunnel portal",      '["portal","tunnel entrance"]',          "structure"),
    ("발파",     "blasting",           '["blast","rock blasting"]',             "excavation"),
    ("천공",     "drilling",           '["boring","drill"]',                    "excavation"),
    ("동바리",   "shoring post",       '["support post","prop"]',               "temporary works"),
    ("거푸집",   "formwork",           '["form","concrete form"]',              "temporary works"),
    ("비계",     "scaffolding",        '["scaffold"]',                          "temporary works"),
    ("안전고리", "safety hook",        '["lanyard hook","harness hook"]',       "PPE"),
    ("생명줄",   "lifeline",           '["safety line","life line"]',           "PPE"),
    ("안전벨트", "safety harness",     '["safety belt","harness"]',             "PPE"),
    ("타설",     "concrete pouring",   '["pouring","placement"]',               "concreting"),
    ("버력",     "muck",               '["spoil","excavated rock"]',            "excavation"),
    ("광차",     "mine car",           '["muck car","tram car"]',               "equipment"),
    ("굴착기",   "excavator",          '["backhoe","digger"]',                  "equipment"),
    ("지보재",   "support member",     '["tunnel support","rib"]',              "support"),
    ("철근",     "rebar",              '["reinforcing bar","reinforcement"]',   "material"),
    ("협착",     "caught-in",          '["pinch","crush injury"]',              "accident"),
    ("추락",     "fall from height",   '["fall","falling"]',                    "accident"),
]


def main(src: str, dst: str) -> None:
    df = load_master(src)

    con = sqlite3.connect(dst)
    try:
        con.executescript(
            "DROP TABLE IF EXISTS accidents; DROP TABLE IF EXISTS glossary;"
        )
        con.executescript(ACCIDENTS_DDL + GLOSSARY_DDL)
        df.to_sql("accidents", con, if_exists="append", index=False)
        con.executemany(
            "INSERT INTO glossary (ko, en, aliases, category) VALUES (?, ?, ?, ?)",
            STARTER_GLOSSARY,
        )
        for ddl in INDEXES:
            con.execute(ddl)
        con.commit()

        n = con.execute("SELECT COUNT(*) FROM accidents").fetchone()[0]
        g = con.execute("SELECT COUNT(*) FROM glossary").fetchone()[0]
        fatal = con.execute("SELECT SUM(fatalities) FROM accidents").fetchone()[0]
        types = con.execute(
            "SELECT accident_type, COUNT(*) FROM accidents "
            "GROUP BY accident_type ORDER BY 2 DESC"
        ).fetchall()
        print(f"[done] {dst}")
        print(f"  accidents : {n} rows, {fatal} total fatalities")
        print(f"  glossary  : {g} starter terms")
        print(f"  accident types ({len(types)}): " + ", ".join(f"{t}({c})" for t, c in types))
    finally:
        con.close()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "Tunnel_data_master.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "accidents.db"
    main(src, dst)
