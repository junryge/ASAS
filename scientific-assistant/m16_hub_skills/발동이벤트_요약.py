#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트_요약.py — M16 HUBROOM 발동이벤트.csv(분당 1행, 하루 1440행)를
'위험 구간 묶음'(수~수십 행)으로 압축한다.

목적: 발동이벤트 원본은 1440행 × 100여 열이라 LLM 컨텍스트(128K)를 넘김.
      이 스크립트가 샌드박스에서 미리 요약 → 데모스 LLM 은 작은 요약표만 보고
      하루 보고서를 작성. (데모스 스크립트 실행 기능으로 자동 호출)

입력: 발동이벤트.csv (16열 축약본도, 131열 원본도 모두 OK — 헤더 이름으로 읽음)
출력: <outdir>/발동이벤트_요약.csv  (경계 이상 위험 구간을 시간순으로 묶은 표)

규칙:
- '경계' 이상(점수 >=60) 인 분(minute)만 위험으로 보고, 30분 이내로 가까운
  위험 분들은 한 구간으로 병합(짧은 진동 흡수). 이게 하루 보고서의 시간대 표가 됨.
- 구간마다: 시간대 / 지속 / 최고위험레벨 / 최고점수 / 진원지 / 대표 전파경로 / 발동룰 / 특이신호
- stdlib 만 사용 (pandas 불필요).
"""
import sys
import os
import csv
import re
import argparse
from collections import Counter
from datetime import datetime

LEVEL_ORDER = {"정상": 0, "관심": 1, "주의": 2, "경계": 3, "위험": 4, "초위험": 5}
RISK_LEVEL_MIN = 3          # '경계' 이상(60점↑)을 활동 구간으로 (정상/관심/주의 폐지)


def _norm_key(k):
    return (k or "").lstrip("﻿").strip()


def _level_from(level_str, score):
    """★ 점수(unified_risk_score) 기준으로 등급 산출.
    회사 기준(1~100 척도): 60점 미만은 알람 없음, 경계 60~70 / 위험 71~84 / 초위험 85~100.
    무조건 점수로 판정한다(정상/관심/주의 폐지)."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "정상"
    if s >= 85: return "초위험"
    if s >= 71: return "위험"
    if s >= 60: return "경계"
    return "정상"


def _parse_dt(row):
    """datetime 컬럼(YYYY-MM-DD HH:MM) 우선, 없으면 date+time 조합."""
    dt = (row.get("datetime") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(dt, fmt)
        except ValueError:
            pass
    d = (row.get("date") or "").strip()
    t = (row.get("time") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{d} {t}", fmt)
        except ValueError:
            pass
    return None


# propagation_chain 예: "M16(23:05,RB+RB_fast) → M16HUB(23:07,RC+RD)"
_RULE_RE = re.compile(r"\(([^)]*?)\)")
_RULE_TOKEN_RE = re.compile(r"R[A-D](?:_sus)?|RB_fast|SLA|SORT|MAXCAPA\*?\d*|RC|RD|RA")


def _rules_in_chain(chain):
    rules = []
    for inside in _RULE_RE.findall(chain or ""):
        # inside 예: "23:07,RC+RD"  → 룰 토큰만
        parts = inside.split(",", 1)
        if len(parts) == 2:
            for tok in re.split(r"[+\s]+", parts[1]):
                tok = tok.strip()
                if tok:
                    rules.append(tok)
    return rules


# 룰 코드 → 한글 (처음 보는 사람도 알아먹게). 순서 보존 중복 제거.
_RULE_KR = {
    "RA_sus": "반송지연지속", "RA": "반송지연",
    "RB_fast": "큐급증", "RB": "큐누적",
    "RC": "리프터 막힘", "RD": "저장공간 포화",
    "SLA": "4분초과", "SORT": "분류기대기", "MAXCAPA": "운영자용량변경",
}
_EXCLUDE_AREA = {"M16_PKT"}   # 영향 없음 — 분석에서 제외

# 등급 → 이모지 (보고서에 색으로 보이게)
_GRADE_EMOJI = {"정상": "", "경계": "🟠", "위험": "🔴", "초위험": "⛔"}


def _grade_label(level):
    e = _GRADE_EMOJI.get(level, "")
    return (e + " " + level).strip()


def _kr_rules(rule_list):
    seen, out = set(), []
    for r in rule_list:
        base = r.split("*")[0].strip()          # MAXCAPA*1 → MAXCAPA
        kr = _RULE_KR.get(base, base)
        if kr not in seen:
            seen.add(kr)
            out.append(kr)
    return out


def _clean_chain(chain):
    """전파경로를 영역 흐름만 남긴다(룰 괄호 제거) + M16_PKT 제외.
    예: 'M16(..,RB) → M16HUB(..,RC+RD) → M16_PKT(..)' → 'M16 → M16HUB'"""
    areas = []
    for seg in re.split(r"\s*→\s*", chain or ""):
        a = re.split(r"[(\s]", seg.strip(), 1)[0].strip()
        if a and a not in _EXCLUDE_AREA:
            areas.append(a)
    return " → ".join(areas) if areas else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="발동이벤트.csv 경로")
    ap.add_argument("-o", "--outdir", default=".", help="출력 폴더")
    args = ap.parse_args()

    # 입력 읽기 (utf-8-sig 로 BOM 흡수)
    with open(args.input, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [_norm_key(k) for k in (reader.fieldnames or [])]
        rows = []
        for r in reader:
            rows.append({_norm_key(k): v for k, v in r.items()})

    # 분 단위 정보 추출 + 시간순 정렬
    minutes = []
    for r in rows:
        dt = _parse_dt(r)
        if dt is None:
            continue
        try:
            score = float(r.get("unified_risk_score") or 0)
        except ValueError:
            score = 0.0
        level = _level_from(r.get("unified_risk_level"), score)
        minutes.append({
            "dt": dt,
            "time": (r.get("time") or dt.strftime("%H:%M")).strip(),
            "score": score,
            "level": level,
            "lvl_n": LEVEL_ORDER.get(level, 0),
            "hot_area": (r.get("hot_area") or "").strip(),
            "chain": (r.get("propagation_chain") or "").strip(),
            "flow": (r.get("flow_signals") or "").strip(),
            "maxcapa": (r.get("maxcapa_signals") or "").strip(),
            "affected": (r.get("affected_areas") or "").strip(),
            "stage": str(r.get("stage") or "").strip(),
            "reason": (r.get("reason") or "").strip(),
            # AMOS 이상감지 신규 4컬럼 (없는 배포본이면 빈 문자열)
            "amos_bott": ", ".join(x for x in (
                (r.get("BOTTLENECK_downward_anomaly_cols") or "").strip(),
                (r.get("BOTTLENECK_upward_anomaly_cols") or "").strip()) if x),
            "amos_queue": ", ".join(x for x in (
                (r.get("QUEUE_downward_anomaly_cols") or "").strip(),
                (r.get("QUEUE_upward_anomaly_cols") or "").strip()) if x),
        })
    minutes.sort(key=lambda m: m["dt"])

    from collections import defaultdict

    # ───────────────────────────────────────────────────────────
    # 일일 보고서용 자료 추출 (스킬이 이걸로 보고서를 쓴다)
    #   ① 하루 통계  ② 24시간 시간대별 프로파일(정상 시간 포함)
    #   ※ '정체' 판정 = unified_risk_score >= 60 (60 미만은 알람 없음)
    # ───────────────────────────────────────────────────────────
    n_total = len(minutes)
    grade_ct = Counter(m["level"] for m in minutes)
    risk_mins = [m for m in minutes if m["score"] >= 60]
    peak_all = max(minutes, key=lambda x: (x["lvl_n"], x["score"])) if minutes else None
    busy = Counter(m["dt"].strftime("%H") + "시" for m in risk_mins).most_common(5)
    busy_str = ", ".join(f"{h}({c}분)" for h, c in busy) or "-"
    # 보고서 제목용 날짜 (데이터에서 가장 흔한 날짜)
    day_str = Counter(m["dt"].strftime("%Y-%m-%d") for m in minutes).most_common(1)[0][0] if minutes else "-"
    # 제목에 그대로 박을 한국어 날짜 (모델이 변환 안 하게 미리 만들어 줌)
    try:
        _d = datetime.strptime(day_str, "%Y-%m-%d")
        report_date_kr = f"{_d.year}년 {_d.month}월 {_d.day}일"
    except Exception:
        report_date_kr = day_str

    stats_rows = [{
        "보고일자": report_date_kr,
        "날짜": day_str,
        "총분": n_total,
        "정상분": grade_ct.get("정상", 0),
        "정체분(60+)": len(risk_mins),
        "경계": grade_ct.get("경계", 0),
        "위험": grade_ct.get("위험", 0),
        "초위험": grade_ct.get("초위험", 0),
        "최고점수": int(peak_all["score"]) if peak_all else 0,
        "최고시각": peak_all["time"] if peak_all else "-",
        "최고진원지": peak_all["hot_area"] if peak_all else "-",
        "정체집중시간대": busy_str,
    }]

    # 시간대별 정체 분석표 (★ 정체 있는 시간만 — 정상 시간은 제외)
    hour_buckets = defaultdict(list)
    for m in minutes:
        hour_buckets[m["dt"].strftime("%H")].append(m)
    profile_rows = []
    for hh in sorted(hour_buckets):
        hm = hour_buckets[hh]
        risk = [x for x in hm if x["score"] >= 60]
        if not risk:                      # 정체 없는(정상) 시간은 분석표에서 제외
            continue
        peak = max(hm, key=lambda x: (x["lvl_n"], x["score"]))
        # 진원지: M16_PKT 제외(영향 없음)
        hot = Counter(x["hot_area"] for x in risk
                      if x["hot_area"] and x["hot_area"] not in _EXCLUDE_AREA).most_common(1)
        rule_ct = Counter()
        for x in risk:
            for rr in _rules_in_chain(x["chain"]):
                rule_ct[rr] += 1
        kr = _kr_rules([r for r, _ in rule_ct.most_common(8)])
        profile_rows.append({
            "시간": f"{hh}시",
            "최고점수": int(peak["score"]),
            "최고등급": _GRADE_EMOJI.get(peak["level"]) or peak["level"],
            "정체분": len(risk),
            "진원지": hot[0][0] if hot else "-",
            "발동룰": ", ".join(kr[:6]) or "-",
        })

    # 출력 2개 (이름 앞 1_,2_ 로 정렬 순서 고정 — 데모스가 통계 먼저 읽게)
    os.makedirs(args.outdir, exist_ok=True)

    def _wcsv(fname, cols, rows):
        p = os.path.join(args.outdir, fname)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return p

    p1 = _wcsv("발동이벤트_1_일일통계.csv",
               ["보고일자", "날짜", "총분", "정상분", "정체분(60+)", "경계", "위험", "초위험",
                "최고점수", "최고시각", "최고진원지", "정체집중시간대"], stats_rows)
    p2 = _wcsv("발동이벤트_2_시간프로파일.csv",
               ["시간", "최고점수", "최고등급", "정체분", "진원지", "발동룰"],
               profile_rows)

    # ───────────────────────────────────────────────────────────
    # ③ 사건목록 — 발동이벤트에서 사건 자동 추출
    #    ★ 점수 기준: 점수 60 이상(경계+) 구간을 사건으로. (전엔 stage=3 기준이라 점수 낮은
    #      시각이 사건 시작으로 잡혀 가짜 장기사건 발생 → 점수 기준으로 교정. predictor와 동일.)
    #    '사건단위 분석' 요청 시 스킬이 이 표로 이벤트 보고서를 쓴다.
    # ───────────────────────────────────────────────────────────
    GAP_MIN, MIN_SCORE = 60, 50
    incs, cur = [], None
    for m in minutes:
        alarm = (m["score"] >= MIN_SCORE)        # ★ stage 대신 점수
        if cur is None:
            if alarm:
                cur = {"s": m, "e": m, "last": m["dt"], "peak": m}
        elif alarm:
            cur["e"] = m; cur["last"] = m["dt"]
            if m["score"] > cur["peak"]["score"]:
                cur["peak"] = m
        elif (m["dt"] - cur["last"]).total_seconds() / 60.0 >= GAP_MIN:
            incs.append(cur); cur = None
    if cur:
        incs.append(cur)
    incs = [c for c in incs if c["peak"]["score"] >= MIN_SCORE]
    inc_rows = []
    for i, c in enumerate(incs, 1):
        pk = c["peak"]
        dur = int((c["e"]["dt"] - c["s"]["dt"]).total_seconds() / 60) + 1
        inc_rows.append({
            "번호": i,
            "시각": pk["time"],                                # ★ 최고점(진짜 몰림) 시각
            "구간": f'{c["s"]["time"]}~{c["e"]["time"]}',      # 시작~종료(점수 50+ 구간)
            "지속분": dur,
            "최고등급": _grade_label(pk["level"]),
            "최고점수": int(pk["score"]),
            "시작영역": pk["hot_area"],
        })
    p3 = _wcsv("발동이벤트_3_사건목록.csv",
               ["번호", "시각", "구간", "지속분", "최고등급", "최고점수", "시작영역"],
               inc_rows)
    print(f"  ③ 사건목록: {len(inc_rows)}건 (점수 {MIN_SCORE}+·간격{GAP_MIN}분) → {p3}")

    # ───────────────────────────────────────────────────────────
    # ④ AMOS 이상감지 — 신규 4컬럼(BOTTLENECK/QUEUE *_anomaly_cols)을 사건 구간별 집계
    #    구간 = BOTTLENECK 의 HID 토큰(HID_32_FROM_SUM_A → HID32)
    #    항목 = 최고점 reason 의 그래프 지표(raw 컬럼) + QUEUE 이상 컬럼 (<br> 구분)
    #    심각도 = 경계→경계/주의(확인필요) / 위험→위험/경고(모니터링 필요) / 초위험→초위험/심각(조치필요)
    # ───────────────────────────────────────────────────────────
    _SEV = {"경계": "경계/주의(확인필요)", "위험": "위험/경고(모니터링 필요)", "초위험": "초위험/심각(조치필요)"}
    _RA_RAW = {"M16HUB": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "M14": "M14.QUE.LOAD.AVGLOADTIME1MIN",
               "M14B": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "M16A": "M16A.QUE.LOAD.AVGLOADTIME1MIN",
               "M16B": "M16B.QUE.LOAD.AVGLOADTIME1MIN"}

    def _reason_metrics(reason):
        """최고점 reason → 그래프와 동일한 raw 지표 목록 (report_graphs.parse_reason_metrics 미러)."""
        out, seen = [], set()
        body = (reason or "").split("발동:", 1)[-1]
        body = re.split(r"흐름:|운영자조치:", body)[0]
        def _add(label, raw):
            # ★ raw 컬럼명만 표기 (한글 라벨 없이 — 고객 요청)
            if raw not in seen:
                seen.add(raw)
                out.append(raw)
        for m in re.finditer(r"(M16HUB|M14B|M16A|M16B|M14)\s*\[(.*?)\]", body):
            area, inner = m.group(1), m.group(2)
            if "AVGTOTALTIME1MIN" in inner or "AVGLOADTIME1MIN" in inner:
                _add(f"{area} 반송시간", _RA_RAW.get(area, f"{area}.QUE.TIME.AVGTOTALTIME1MIN"))
            if "FAB저장" in inner:
                _add("M16HUB FAB저장율", "M16HUB.STRATE.ALL.FABSTORAGERATIO")
            if re.search(r"\bSTB", inner):
                _add("M16HUB STB저장율", "M16HUB.STRATE.STB.3F_STORAGE_UTIL")
            if "OHT=" in inner or "OHT가동" in inner:
                _add(f"{area} OHT가동률", f"{area}.QUE.OHT.OHTUTIL")
            if "R-C" in inner:
                _add("M16HUB 리프터 정체", "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT")
            if "SLA(" in inner or "4분초과" in inner:
                _add(f"{area} 4분초과율", f"{area}.QUE.ALL.TRANSPORT4MINOVERRATIO")
            if "SORT(" in inner or "소터" in inner:
                _add(f"{area} 소터대기", f"{area}.SORTER.ABN.SORTERWAITCOUNTOVER")
        return out

    def _hid_zones(text_list):
        seen, z = set(), []
        for token in text_list:
            for tok in token.split(","):
                tok = tok.strip()
                if not tok:
                    continue
                m = re.match(r"HID_?(\d+)", tok)
                name = f"HID{m.group(1)}" if m else tok
                if name not in seen:
                    seen.add(name)
                    z.append(name)
        return z

    amos_rows = []
    for i, c in enumerate(incs, 1):
        w0, w1 = c["s"]["dt"], c["e"]["dt"]
        bott, queue = [], []
        for m in minutes:
            if w0 <= m["dt"] <= w1:
                if m.get("amos_bott"):
                    bott.append(m["amos_bott"])
                if m.get("amos_queue"):
                    queue.append(m["amos_queue"])
        zones = _hid_zones(bott)
        items, iseen = [], set()
        for it in _reason_metrics(c["peak"].get("reason", "")):
            if it not in iseen:
                iseen.add(it)
                items.append(it)
        for qcsv in queue:
            for q in qcsv.split(","):
                q = q.strip()
                base = re.sub(r"_[A-Z]$", "", q)
                if base and base not in iseen:
                    iseen.add(base)
                    items.append(base)
        pk = c["peak"]
        # ★ 구간이 길면 4개마다 <br> 줄바꿈 (표 셀에서 보기 좋게 — 고객 요청)
        zone_str = "<br>".join(
            ", ".join(zones[i2:i2 + 4]) for i2 in range(0, len(zones), 4)
        ) if zones else "-"
        amos_rows.append({
            "번호": i,
            "이상감지 시간": pk["time"],
            "이상감지 구간": zone_str,
            "심각도": _SEV.get(pk["level"], "경계/주의(확인필요)"),
            "이상감지 항목": "<br>".join(items) if items else "-",
        })
    p4 = _wcsv("발동이벤트_4_AMOS이상감지.csv",
               ["번호", "이상감지 시간", "이상감지 구간", "심각도", "이상감지 항목"],
               amos_rows)
    print(f"  ④ AMOS이상감지: {len(amos_rows)}건 → {p4}")

    # 콘솔 요약
    print(f"[발동이벤트 일일자료] 총 {n_total}분 중 정체(60점↑) {len(risk_mins)}분 "
          f"| 정상 {grade_ct.get('정상', 0)}분")
    if peak_all:
        print(f"하루 최고: {peak_all['time']} {peak_all['level']} "
              f"{int(peak_all['score'])}점 (진원지 {peak_all['hot_area']})")
    print(f"정체집중: {busy_str}")
    print(f"출력: {p1} / {p2}")


if __name__ == "__main__":
    main()
