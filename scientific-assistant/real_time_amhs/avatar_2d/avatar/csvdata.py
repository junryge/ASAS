# -*- coding: utf-8 -*-
"""
csvdata.py — 첨부된 CSV(발동이벤트 등)를 서버가 직접 분석한다.

왜 서버가 분석하나
    발동이벤트 CSV 는 하루 1440행 × 143컬럼, 수 MB 다. 프롬프트에 넣을 수
    없고, 잘라 넣으면 LLM 이 못 본 구간의 숫자를 지어낸다 (실제로
    "파일을 확인할 수 없다" 가 나왔다 — 400KB 제한에 걸려 첨부 자체가
    안 됐던 것). 그래서:
      ① 파일은 data/uploads/ 에 통째로 저장하고
      ② 요약은 **여기서 계산**해서 (기간·점수 통계·등급 구간·FAB별 최고점)
      ③ LLM 에는 계산된 요약 + 표본 몇 줄만 준다. 요약의 숫자는 숫자
        가드 화이트리스트에 들어간다 — 분석도 근거 우선이다.

컬럼 규칙 (real_time_amhs 와 같은 이름을 쓴다 — 새로 짓지 않는다)
    시각    datetime > time > 일시
    전체점수 unified_risk_score > area_score > score
    FAB점수  {FAB}_score (M14/M14B/M16A/M16B/M16HUB), area_score
"""
import csv
import io
import re

MAX_ROWS = 100_000          # 폭주 방지 — 하루 1440행이 정상이다
SAMPLE_ROWS = 6             # LLM 에게 보여줄 표본 행 수
FABS = ("M14", "M14B", "M16A", "M16B", "M16HUB")
TIME_COLS = ("datetime", "time", "일시", "date")
SCORE_COLS = ("unified_risk_score", "area_score", "score")


def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _pick(cols, cands):
    low = {c.lower().strip(): c for c in cols}
    for c in cands:
        if c in low:
            return low[c]
    return None


def analyze(name, text, cuts=(60, 71, 85)):
    """CSV 원문 → {ok, summary, numbers, error}.

    summary 는 사람이 읽는 한 덩어리 텍스트 (LLM 근거로도 그대로 쓴다).
    모르는 형식이면 아는 만큼만 말하고, 모른다고 적는다 — 지어내지 않는다.
    """
    text = str(text or "").lstrip("﻿")
    try:
        rows = []
        for i, r in enumerate(csv.DictReader(io.StringIO(text))):
            if i >= MAX_ROWS:
                break
            rows.append(r)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "summary": "", "numbers": set(),
                "error": "CSV 파싱 실패: {}".format(e)}
    if not rows:
        return {"ok": False, "summary": "", "numbers": set(),
                "error": "행이 없습니다 (헤더뿐이거나 빈 파일)"}

    cols = list(rows[0].keys())
    tcol = _pick(cols, TIME_COLS)
    scol = _pick(cols, SCORE_COLS)
    warn, danger, crit = cuts

    L = ["[첨부 데이터 분석 — {}]".format(name),
         "행 {}개 · 컬럼 {}개".format(len(rows), len(cols))]

    if tcol:
        times = [str(r.get(tcol) or "").strip() for r in rows]
        times = [t for t in times if t]
        if times:
            L.append("기간: {} ~ {}".format(times[0], times[-1]))

    if scol is None:
        L.append("점수 컬럼(unified_risk_score/area_score/score)이 없습니다 — "
                 "등급 분석은 못 합니다. 컬럼: "
                 + ", ".join(cols[:12]) + ("…" if len(cols) > 12 else ""))
    else:
        seq = [( str(r.get(tcol) or "").strip() if tcol else str(i),
                 _num(r.get(scol)) ) for i, r in enumerate(rows)]
        vals = [v for _t, v in seq if v is not None]
        if not vals:
            L.append("{} 컬럼에 숫자가 없습니다".format(scol))
        else:
            sv = sorted(vals)
            med = sv[len(sv) // 2]
            L.append("{}: 최소 {:g} · 중앙 {:g} · 최대 {:g}".format(
                scol, sv[0], med, sv[-1]))
            n_w = sum(1 for v in vals if warn <= v < danger)
            n_d = sum(1 for v in vals if danger <= v < crit)
            n_c = sum(1 for v in vals if v >= crit)
            L.append("등급 분포(컷 {}/{}/{}): 경계 {}분 · 위험 {}분 · "
                     "초위험 {}분 · 정상 {}분".format(
                         warn, danger, crit, n_w, n_d, n_c,
                         len(vals) - n_w - n_d - n_c))
            peak_t, peak_v = max(
                ((t, v) for t, v in seq if v is not None),
                key=lambda x: x[1])
            L.append("최고점: {:g}점 ({})".format(peak_v, peak_t))
            # 경계(warn) 이상 연속 구간 — "언제부터 언제까지 올라갔나"
            spans, cur = [], None
            for t, v in seq:
                if v is not None and v >= warn:
                    if cur is None:
                        cur = [t, t, v]
                    else:
                        cur[1] = t
                        cur[2] = max(cur[2], v)
                elif cur is not None:
                    spans.append(cur)
                    cur = None
            if cur is not None:
                spans.append(cur)
            if spans:
                spans.sort(key=lambda s: -s[2])
                L.append("경계({}) 이상 구간 {}곳 (최고점 순 상위 {}):".format(
                    warn, len(spans), min(3, len(spans))))
                for s, e, mx in spans[:3]:
                    L.append("  · {} ~ {} (최고 {:g}점)".format(s, e, mx))
            else:
                L.append("경계({}) 이상으로 올라간 구간이 없습니다".format(warn))

    # FAB 별 자기 점수 컬럼이 있으면 최고점만
    fab_bits = []
    for f in FABS:
        c = _pick(cols, ("{}_score".format(f).lower(),))
        if not c:
            continue
        best_v, best_t = None, ""
        for r in rows:
            v = _num(r.get(c))
            if v is not None and (best_v is None or v > best_v):
                best_v, best_t = v, (str(r.get(tcol) or "").strip() if tcol else "")
        if best_v is not None:
            fab_bits.append("{} 최고 {:g}점({})".format(f, best_v, best_t))
    if fab_bits:
        L.append("FAB별 자기점수 최고: " + " · ".join(fab_bits))

    # 표본 몇 줄 — 구조를 보여 준다 (숫자를 더 말할 근거가 되기도 한다)
    keep = [c for c in ([tcol, scol] + ["hot_area", "stage_name", "reason"])
            if c and c in cols][:5] or cols[:5]
    L.append("표본 {}행 ({}):".format(min(SAMPLE_ROWS, len(rows)),
                                     " | ".join(keep)))
    for r in rows[:SAMPLE_ROWS]:
        L.append("  " + " | ".join(str(r.get(c) or "")[:60] for c in keep))

    summary = "\n".join(L)
    return {"ok": True, "summary": summary,
            "numbers": _numbers(summary), "error": ""}


def _numbers(text):
    out = set()
    for m in re.findall(r"-?\d+(?:\.\d+)?", text or ""):
        try:
            out.add(round(float(m), 2))
        except ValueError:
            pass
    return out
