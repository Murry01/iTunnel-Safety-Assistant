"""Build the 40-question candidate benchmark from the frozen SQLite source."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "accidents.db"
OUTPUT = ROOT / "eval" / "benchmark_candidate_40.json"


def item(id, category, question_ko, question_en, tools, scoring, source_sql=None,
         rq_targets=None, reference_note="", reference_scope="exact"):
    return {
        "id": id,
        "status": "candidate_review",
        "rq_targets": rq_targets or ["RQ1", "RQ4"],
        "category": category,
        "question_ko": question_ko,
        "question_en": question_en,
        "expected_tools": tools,
        "scoring": scoring,
        "reference_scope": reference_scope,
        "reference_note": reference_note,
        "source_sql": source_sql,
    }


QUESTIONS = [
    item("BSQL-01", "statistics", "전체 사고 건수와 총 사망자 수는 각각 얼마인가요?",
         "What are the total numbers of accidents and fatalities?", ["get_statistics"], "exact_numeric",
         "SELECT COUNT(*) AS accidents, SUM(fatalities) AS fatalities FROM accidents"),
    item("BSQL-02", "statistics", "터널 종류별 사고 건수와 사망자 수를 비교해 주세요.",
         "Compare accident and fatality counts by tunnel type.", ["get_statistics"], "exact_grouped_values",
         "SELECT tunnel_type, COUNT(*) AS accidents, SUM(fatalities) AS fatalities FROM accidents GROUP BY tunnel_type ORDER BY fatalities DESC, accidents DESC, tunnel_type"),
    item("BSQL-03", "statistics", "철도터널에서 가장 많이 발생한 사고종류 5개와 건수를 알려주세요.",
         "List the five most frequent accident types in railway tunnels and their counts.", ["get_statistics"], "ordered_top_k",
         "SELECT accident_type, COUNT(*) AS cases FROM accidents WHERE tunnel_type='철도터널' GROUP BY accident_type ORDER BY cases DESC, accident_type LIMIT 5"),
    item("BSQL-04", "statistics", "사고가 10건 이상 발생한 작업프로세스와 건수를 내림차순으로 알려주세요.",
         "List work processes with at least 10 accidents, in descending order.", ["get_statistics"], "ordered_complete_set",
         "SELECT work_process, COUNT(*) AS cases FROM accidents GROUP BY work_process HAVING COUNT(*)>=10 ORDER BY cases DESC, work_process"),
    item("BSQL-05", "statistics", "해체작업 중 발생한 사고를 사고종류별로 집계해 주세요.",
         "Aggregate dismantling-work accidents by accident type.", ["get_statistics"], "exact_grouped_values",
         "SELECT accident_type, COUNT(*) AS cases FROM accidents WHERE work_process='해체작업' GROUP BY accident_type ORDER BY cases DESC, accident_type"),
    item("BSQL-06", "statistics", "설계오류와 시공오류 각각의 사고 건수와 사망자 수는 얼마인가요?",
         "How many accidents and fatalities are associated with design errors and construction errors?", ["get_statistics"], "exact_grouped_values",
         "SELECT cause_l1, COUNT(*) AS cases, SUM(fatalities) AS fatalities FROM accidents GROUP BY cause_l1 ORDER BY cases DESC"),
    item("BSQL-07", "statistics", "사망사고에서 사고객체 대분류별 사고 건수와 사망자 수를 알려주세요.",
         "For fatal accidents, report cases and fatalities by top-level accident object.", ["get_statistics"], "exact_grouped_values",
         "SELECT object_l1, COUNT(*) AS cases, SUM(fatalities) AS fatalities FROM accidents WHERE fatalities>0 GROUP BY object_l1 ORDER BY cases DESC, object_l1"),
    item("BSQL-08", "statistics", "도로터널 사고에서 가장 빈번한 사고객체 소분류 5개와 건수를 알려주세요.",
         "List the five most frequent lower-level accident objects in road-tunnel accidents.", ["get_statistics"], "ordered_top_k",
         "SELECT object_l2, COUNT(*) AS cases FROM accidents WHERE tunnel_type='도로터널' GROUP BY object_l2 ORDER BY cases DESC, object_l2 LIMIT 5"),

    item("BGRAPH-01", "graph_cause_chain", "'작업순서 미준수'가 속한 모든 원인 경로와 각 경로의 사고 건수를 알려주세요.",
         "List every cause path containing 'failure to follow work sequence' and the case count for each path.", ["query_graph"], "exact_paths_and_counts",
         "SELECT cause_l1, cause_l2, cause_l3, COUNT(*) AS cases FROM accidents WHERE cause_l3='작업순서 미준수' GROUP BY cause_l1,cause_l2,cause_l3 ORDER BY cause_l2",
         ["RQ1", "RQ3", "RQ4"], "The repeated L3 name must remain separated by its two L2 parents."),
    item("BGRAPH-02", "graph_cause_chain", "'기계장비관리 미흡' 원인과 연결된 작업프로세스와 사고 건수를 모두 알려주세요.",
         "List all work processes connected to inadequate equipment management and their case counts.", ["query_graph"], "exact_graph_grouping",
         "SELECT work_process, COUNT(*) AS cases FROM accidents WHERE cause_l2='기계장비관리 미흡' GROUP BY work_process ORDER BY cases DESC, work_process", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-03", "graph_cause_chain", "모든 사망사고의 사례번호와 전체 원인 경로(대분류-중분류-소분류)를 보여주세요.",
         "Show each fatal case ID with its full L1-L2-L3 cause path.", ["query_graph"], "exact_case_path_set",
         "SELECT case_id, fatalities, cause_l1, cause_l2, cause_l3 FROM accidents WHERE fatalities>0 ORDER BY case_id", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-04", "graph_cause_chain", "'작업자 통제 미흡'과 연결된 사고종류와 각 건수를 알려주세요.",
         "Which accident types are connected to inadequate worker control, and how many cases of each?", ["query_graph"], "exact_graph_grouping",
         "SELECT accident_type, COUNT(*) AS cases FROM accidents WHERE cause_l3='작업자 통제 미흡' GROUP BY accident_type ORDER BY cases DESC, accident_type", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-05", "graph_taxonomy", "사고객체 대분류 '가시설' 아래의 모든 소분류와 연결된 사고 건수를 알려주세요.",
         "List every lower-level object under temporary facilities and its linked accident count.", ["query_graph"], "complete_taxonomy_and_counts",
         "SELECT object_l2, COUNT(*) AS cases FROM accidents WHERE object_l1='가시설' GROUP BY object_l2 ORDER BY cases DESC, object_l2", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-06", "graph_cause_chain", "'설계오류' 아래의 모든 중분류-소분류 원인 경로와 사고 건수를 보여주세요.",
         "Show every L2-L3 cause path under design error and its case count.", ["query_graph"], "complete_taxonomy_and_counts",
         "SELECT cause_l1, cause_l2, cause_l3, COUNT(*) AS cases FROM accidents WHERE cause_l1='설계오류' GROUP BY cause_l1,cause_l2,cause_l3 ORDER BY cause_l2,cause_l3", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-07", "graph_cause_chain", "'안전환경 미제공' 원인과 연결된 터널 종류별 사고 건수를 알려주세요.",
         "Report accident counts by tunnel type connected to failure to provide a safe environment.", ["query_graph"], "exact_graph_grouping",
         "SELECT tunnel_type, COUNT(*) AS cases FROM accidents WHERE cause_l2='안전환경 미제공' GROUP BY tunnel_type ORDER BY cases DESC, tunnel_type", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-08", "graph_cause_chain", "감전 사고의 사례번호, 작업프로세스, 전체 원인 경로를 알려주세요.",
         "For electric-shock accidents, give the case ID, work process, and full cause path.", ["query_graph"], "exact_case_path_set",
         "SELECT case_id, work_process, cause_l1, cause_l2, cause_l3 FROM accidents WHERE accident_type='감전' ORDER BY case_id", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-09", "graph_cause_chain", "'건설기계-굴착기' 객체 경로와 '시공오류-안전수칙 미준수-작업자 부주의' 원인 경로가 동시에 연결된 사례번호를 알려주세요.",
         "List cases linked to both the Construction equipment-Excavator object path and the specified construction-error cause path.", ["query_graph"], "exact_case_set",
         "SELECT case_id FROM accidents WHERE object_l1='건설기계' AND object_l2='굴착기' AND cause_l1='시공오류' AND cause_l2='안전수칙 미준수' AND cause_l3='작업자 부주의' ORDER BY case_id", ["RQ1", "RQ3", "RQ4"]),
    item("BGRAPH-10", "graph_taxonomy", "둘 이상의 중분류 원인 아래에 나타나는 동일한 소분류 원인 이름이 있나요? 해당 이름과 상위 중분류를 알려주세요.",
         "Does any L3 cause name occur under more than one L2 parent? Give the name and its parents.", ["query_graph"], "exact_path_identity",
         "SELECT cause_l3, GROUP_CONCAT(DISTINCT cause_l2) AS parents, COUNT(DISTINCT cause_l2) AS parent_count FROM accidents GROUP BY cause_l3 HAVING COUNT(DISTINCT cause_l2)>1 ORDER BY cause_l3", ["RQ1", "RQ3", "RQ4"]),

    item("BRET-01", "narrative_retrieval", "굴착작업 중 토사나 암반과 관련해 발생한 사고 사례와 재발방지대책을 알려주세요.",
         "Find accidents involving soil or rock during excavation and report their prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE work_process='굴착작업' AND object_l1='토사 및 암반' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),
    item("BRET-02", "narrative_retrieval", "고소작업차에서 떨어진 사고 사례와 재발방지대책을 알려주세요.",
         "Find fall cases involving aerial work platforms and report prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE object_l2='고소작업차(고소작업대 등)' AND accident_type='떨어짐' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),
    item("BRET-03", "narrative_retrieval", "절단작업 중 절단·베임 사고 사례와 시행된 예방대책을 알려주세요.",
         "Find cutting or laceration cases during cutting work and report the prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE work_process='절단작업' AND accident_type='절단, 베임' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),
    item("BRET-04", "narrative_retrieval", "정비작업 중 기계에 끼인 사고 사례와 사고 후 조치 및 예방대책을 알려주세요.",
         "Find caught-in accidents during maintenance and report post-accident actions and prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE work_process='정비작업' AND accident_type='끼임' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),
    item("BRET-05", "narrative_retrieval", "터널공사 화재 사고 사례별 사고경위, 사고 후 조치, 재발방지대책을 알려주세요.",
         "For tunnel-construction fire cases, report the narrative, response, and prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE accident_type='화재' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "The structured set contains all cases classified as fire.", "structured_complete"),
    item("BRET-06", "narrative_retrieval", "감전 사고 사례에서 무슨 일이 있었고 어떤 조치와 예방대책이 시행되었나요?",
         "What happened in the electric-shock case, and what response and prevention measures were taken?", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE accident_type='감전' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "The structured set contains all cases classified as electric shock.", "structured_complete"),
    item("BRET-07", "narrative_retrieval", "자재 운반작업 중 발생한 사고 사례와 재발방지대책을 알려주세요.",
         "Find accidents during material transport and report prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id, accident_type FROM accidents WHERE work_process='운반작업' AND object_l2='자재' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are structured seeds; semantic relevance still requires review.", "seed_nonexhaustive"),
    item("BRET-08", "narrative_retrieval", "작업자가 이동 중 넘어졌던 사례와 공통적인 재발방지대책을 알려주세요.",
         "Find cases where workers fell on the same level while moving and summarize common prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE work_process='이동' AND accident_type='넘어짐' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "The structured set is broad; relevance and synthesis require human assessment.", "seed_nonexhaustive"),
    item("BRET-09", "narrative_retrieval", "비계에서 떨어진 사고 사례와 사고 원인 및 예방대책을 알려주세요.",
         "Find fall cases involving scaffolding and report their causes and prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE object_l2='비계' AND accident_type='떨어짐' ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),
    item("BRET-10", "narrative_retrieval", "타설작업 중 거푸집이나 콘크리트와 관련된 사고 사례와 예방대책을 알려주세요.",
         "Find concreting-work accidents involving formwork or concrete and report prevention measures.", ["search_cases"], "human_relevance_and_grounding",
         "SELECT case_id FROM accidents WHERE work_process='타설작업' AND object_l2 IN ('거푸집','콘크리트') ORDER BY case_id", ["RQ1", "RQ2", "RQ4"], "Reference IDs are seeds; assess additional retrieved cases for semantic relevance.", "seed_nonexhaustive"),

    item("BCOMP-01", "multi_source", "철도터널에서 가장 흔한 사고종류와 건수를 확인하고, 해당 사고의 실제 사례와 예방대책을 제시해 주세요.",
         "Identify the most common accident type in railway tunnels, then cite real cases and prevention measures.", ["get_statistics", "search_cases"], "numeric_plus_grounded_cases",
         "SELECT accident_type, COUNT(*) AS cases FROM accidents WHERE tunnel_type='철도터널' GROUP BY accident_type ORDER BY cases DESC, accident_type LIMIT 1", ["RQ1", "RQ2", "RQ4"], "The count is exact; case relevance and prevention grounding require human review."),
    item("BCOMP-02", "multi_source", "사망사고를 원인 중분류별로 순위화하고, 가장 많은 원인의 실제 사례와 예방대책을 제시해 주세요.",
         "Rank fatal accidents by L2 cause, then cite cases and prevention measures for the leading cause.", ["query_graph", "search_cases"], "graph_ranking_plus_grounded_cases",
         "SELECT cause_l2, COUNT(*) AS fatal_cases, SUM(fatalities) AS deaths FROM accidents WHERE fatalities>0 GROUP BY cause_l2 ORDER BY deaths DESC, fatal_cases DESC, cause_l2", ["RQ1", "RQ2", "RQ3", "RQ4"]),
    item("BCOMP-03", "multi_source", "떨어짐 사고와 가장 많이 연결된 사고객체 소분류 5개를 찾고, 상위 객체의 실제 사례와 예방대책을 알려주세요.",
         "Find the five lower-level objects most associated with falls, then cite cases and prevention measures for the leading object.", ["query_graph", "search_cases"], "graph_top_k_plus_grounded_cases",
         "SELECT object_l2, COUNT(*) AS cases FROM accidents WHERE accident_type='떨어짐' GROUP BY object_l2 ORDER BY cases DESC, object_l2 LIMIT 5", ["RQ1", "RQ2", "RQ3", "RQ4"]),
    item("BCOMP-04", "multi_source", "화재 사고의 전체 원인 경로를 찾고, 각 사례의 사고 후 조치와 재발방지대책을 설명해 주세요.",
         "Find the full cause paths for fire accidents and explain each case's response and prevention measures.", ["query_graph", "search_cases"], "exact_paths_plus_grounded_cases",
         "SELECT case_id, cause_l1, cause_l2, cause_l3 FROM accidents WHERE accident_type='화재' ORDER BY case_id", ["RQ1", "RQ2", "RQ3", "RQ4"]),
    item("BCOMP-05", "multi_source", "'안전환경 미제공'과 연결된 터널 종류와 사례를 찾고, 사례별 예방대책을 설명해 주세요.",
         "Find tunnel types and cases connected to failure to provide a safe environment, then explain case-specific prevention measures.", ["query_graph", "search_cases"], "exact_graph_set_plus_grounded_cases",
         "SELECT case_id, tunnel_type, accident_type FROM accidents WHERE cause_l2='안전환경 미제공' ORDER BY case_id", ["RQ1", "RQ2", "RQ3", "RQ4"]),
    item("BCOMP-06", "multi_source", "설계오류의 모든 원인 경로를 제시하고, 각 경로에서 실제 사례 한 건과 예방대책을 알려주세요.",
         "List all design-error cause paths and provide one real case and prevention measure for each path.", ["query_graph", "search_cases"], "complete_paths_plus_grounded_cases",
         "SELECT case_id, cause_l2, cause_l3 FROM accidents WHERE cause_l1='설계오류' ORDER BY case_id", ["RQ1", "RQ2", "RQ3", "RQ4"]),
    item("BCOMP-07", "multi_source", "설계오류와 시공오류의 사망사고 비율을 비교하고, 각 범주의 사망사고 사례와 예방대책을 제시해 주세요.",
         "Compare fatal-accident rates for design and construction errors, then cite fatal cases and prevention measures from each category.", ["get_statistics", "search_cases"], "rate_plus_grounded_cases",
         "SELECT cause_l1, COUNT(*) AS cases, SUM(CASE WHEN fatalities>0 THEN 1 ELSE 0 END) AS fatal_cases, ROUND(100.0*SUM(CASE WHEN fatalities>0 THEN 1 ELSE 0 END)/COUNT(*),2) AS fatal_case_percent FROM accidents GROUP BY cause_l1 ORDER BY cause_l1", ["RQ1", "RQ2", "RQ4"]),
    item("BCOMP-08", "multi_source", "도로터널과 철도터널에서 각각 가장 흔한 작업프로세스를 비교하고, 각 프로세스의 실제 사고 사례와 예방대책을 알려주세요.",
         "Compare the most common work process in road and railway tunnels, then cite cases and prevention measures for each.", ["get_statistics", "search_cases"], "grouped_top_one_plus_grounded_cases",
         "WITH ranked AS (SELECT tunnel_type, work_process, COUNT(*) AS cases, ROW_NUMBER() OVER (PARTITION BY tunnel_type ORDER BY COUNT(*) DESC, work_process) AS rn FROM accidents WHERE tunnel_type IN ('도로터널','철도터널') GROUP BY tunnel_type,work_process) SELECT tunnel_type,work_process,cases FROM ranked WHERE rn=1 ORDER BY tunnel_type", ["RQ1", "RQ2", "RQ4"]),

    item("BTERM-01", "terminology", "터널공사에서 '막장'은 무엇을 의미하나요?",
         "What does '막장' mean in tunnel construction?", ["explain_term"], "exact_glossary",
         "SELECT ko,en,aliases,category FROM glossary WHERE ko='막장'"),
    item("BTERM-02", "terminology", "터널공사에서 '부석'은 무엇이며 영어로 어떻게 표현하나요?",
         "What is '부석' and how is it expressed in English?", ["explain_term"], "exact_glossary",
         "SELECT ko,en,aliases,category FROM glossary WHERE ko='부석'"),
    item("BTERM-03", "terminology", "'동바리'의 영어 명칭과 터널공사에서의 의미를 알려주세요.",
         "Give the English term and construction meaning of '동바리'.", ["explain_term"], "exact_glossary",
         "SELECT ko,en,aliases,category FROM glossary WHERE ko='동바리'"),
    item("BTERM-04", "terminology", "'강지보재'는 영어로 무엇이며 어떤 종류의 터널 지보재인가요?",
         "What is the English term for '강지보재', and what type of tunnel support is it?", ["explain_term"], "exact_glossary",
         "SELECT ko,en,aliases,category FROM glossary WHERE ko='강지보재'"),
]


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        for question in QUESTIONS:
            question["reference_rows"] = [dict(row) for row in con.execute(question["source_sql"])]
    finally:
        con.close()
    payload = {
        "status": "candidate_review_not_frozen",
        "description": "Forty new Korean-primary candidate questions for the final proof-of-concept evaluation. English text is reviewer guidance only.",
        "source_database": "accidents.db",
        "question_count": len(QUESTIONS),
        "questions": QUESTIONS,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(QUESTIONS)} questions")


if __name__ == "__main__":
    main()
