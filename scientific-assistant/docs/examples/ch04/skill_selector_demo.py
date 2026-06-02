"""
Chapter 4 — 스킬 자동 선택 알고리즘 시뮬레이터.

scientific-assistant/demos_v1/skills.py 의 _score_query() 와 동일한 로직을
독립 실행 가능한 형태로 추려놓은 학습용 데모.

사용:
    python skill_selector_demo.py "OHT가 자꾸 N7 베이에서 멈춰요"
    python skill_selector_demo.py "RDKit 으로 벤젠 SMILES 알려줘" --top 5
"""
import argparse
import re
import sys


# 본 가이드 학습용 축약 키워드 dict.
# 실제 운영 SKILL_KEYWORDS 는 100개 이상의 스킬을 포함한다.
SKILL_KEYWORDS = {
    "semicon-fab": [
        "반도체", "팹", "fab", "웨이퍼", "wafer", "FOUP",
        "OHT", "AGV", "CNV", "컨베이어", "AMHS", "베이", "bay",
        "MES", "EAP", "SECS", "GEM", "EES", "FDC",
        "수율", "yield", "결함", "defect", "챔버", "chamber",
        "OEE", "PM", "RM",
    ],
    "rdkit": [
        "RDKit", "SMILES", "분자", "molecule", "화합물", "compound",
        "SDF", "molecular",
    ],
    "biopython": [
        "생물", "서열", "DNA", "RNA", "단백질", "FASTA",
        "GenBank", "BLAST", "alignment", "서열분석",
    ],
    "exploratory-data-analysis": [
        "EDA", "탐색", "데이터분석", "분포", "이상치", "결측",
    ],
    "matplotlib": [
        "시각화", "그래프", "차트", "matplotlib", "plot",
    ],
    "agent-debugger": [
        "디버깅", "버그", "bug", "에러", "error", "traceback", "exception",
    ],
    "systematic-debugging": [
        "왜 안 되", "루트코즈", "원인 분석", "재현", "이상해",
    ],
    "agent-python-pro": [
        "파이썬", "python", "함수", "클래스", "리팩터링", "구현",
    ],
}


def score_query(query_lower):
    """skills.py 의 _score_query() 와 같은 알고리즘."""
    scores = {}
    for skill_id, keywords in SKILL_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # 짧은 ASCII 단어는 단어경계까지 본다 (오탐 방지)
            if len(kw_lower) <= 4 and kw_lower.isascii() and kw_lower.isalpha():
                pattern = r"(?<![a-zA-Z])" + re.escape(kw_lower) + r"(?![a-zA-Z])"
                if re.search(pattern, query_lower):
                    score += len(kw_lower) * 2
            elif kw_lower in query_lower:
                score += len(kw_lower)
        if score > 0:
            scores[skill_id] = score
    return scores


def boost_by_keywords(query_lower, scores):
    """skills.py 의 context_aware_skill_select() 가 적용하는 트리거 부스트."""
    boosted = {}

    def bump(sid, n, reason):
        scores[sid] = scores.get(sid, 0) + n
        boosted.setdefault(sid, []).append(f"+{n} ({reason})")

    if any(k in query_lower for k in ["에러", "error", "버그", "bug",
                                      "traceback", "exception"]):
        bump("agent-debugger", 5, "디버깅 트리거")
    if any(k in query_lower for k in ["분석", "데이터", "csv",
                                      "그래프", "시각화", "차트", "통계"]):
        bump("exploratory-data-analysis", 3, "데이터 트리거")
        bump("matplotlib", 3, "시각화 트리거")
    if any(k in query_lower for k in ["왜 안", "원인", "이상해", "루트코즈"]):
        bump("systematic-debugging", 9, "체계적 디버깅 트리거")
    if any(k in query_lower for k in ["코드", "함수", "클래스", "구현",
                                      "코딩", "만들어"]):
        bump("agent-python-pro", 3, "코드 트리거")
    return boosted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="사용자 질문")
    ap.add_argument("--top", type=int, default=3, help="상위 N개 (기본 3)")
    ap.add_argument("--verbose", action="store_true",
                    help="매칭된 키워드까지 자세히 출력")
    args = ap.parse_args()

    q_lower = args.query.lower()
    print(f"\n질문: {args.query}\n")

    scores = score_query(q_lower)
    boost_log = boost_by_keywords(q_lower, scores)

    if not scores:
        print("⚠️  매칭된 스킬이 없습니다. 키워드를 확장해 보세요.")
        sys.exit(0)

    sorted_skills = sorted(scores.items(), key=lambda kv: -kv[1])

    print(f"=== 상위 {args.top}개 스킬 ===")
    for sid, sc in sorted_skills[:args.top]:
        print(f"  [{sc:>4}]  {sid}")
        if sid in boost_log:
            for line in boost_log[sid]:
                print(f"          {line}")

    if args.verbose:
        print("\n--- 매칭 상세 ---")
        for sid, sc in sorted_skills:
            kws = [kw for kw in SKILL_KEYWORDS[sid] if kw.lower() in q_lower]
            print(f"  {sid:<30} score={sc:<3} keywords={kws}")


if __name__ == "__main__":
    main()
