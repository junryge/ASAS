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


def parse(text):
    """CSV 원문 → (rows, error). 전 행을 읽는다 (MAX_ROWS 는 폭주 방지)."""
    text = str(text or "").lstrip("﻿")
    try:
        rows = []
        for i, r in enumerate(csv.DictReader(io.StringIO(text))):
            if i >= MAX_ROWS:
                break
            rows.append(r)
    except Exception as e:  # noqa: BLE001
        return [], "CSV 파싱 실패: {}".format(e)
    if not rows:
        return [], "행이 없습니다 (헤더뿐이거나 빈 파일)"
    return rows, ""


def analyze(name, text, cuts=(60, 71, 85)):
    """CSV 원문 → {ok, summary, numbers, rows, error}.

    summary 는 사람이 읽는 한 덩어리 텍스트 (LLM 근거로도 그대로 쓴다).
    모르는 형식이면 아는 만큼만 말하고, 모른다고 적는다 — 지어내지 않는다.
    ★rows 를 같이 돌려준다 — 이어지는 질문은 요약이 아니라 **원본 전체**를
      다시 계산해서 답해야 한다 (query 참조).
    """
    rows, err = parse(text)
    if err:
        return {"ok": False, "summary": "", "numbers": set(), "rows": [],
                "error": err}

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
    L.append("※ 위 수치는 {}행 **전부**를 계산한 값입니다. "
             "아래는 구조를 보여 주는 표본일 뿐입니다.".format(len(rows)))
    L.append("표본 {}행 ({}):".format(min(SAMPLE_ROWS, len(rows)),
                                     " | ".join(keep)))
    for r in rows[:SAMPLE_ROWS]:
        L.append("  " + " | ".join(str(r.get(c) or "")[:60] for c in keep))

    summary = "\n".join(L)
    return {"ok": True, "summary": summary, "rows": rows,
            "numbers": _numbers(summary), "error": ""}


def _numbers(text):
    out = set()
    for m in re.findall(r"-?\d+(?:\.\d+)?", text or ""):
        try:
            out.add(round(float(m), 2))
        except ValueError:
            pass
    return out


# ══════════════ 이어지는 질문에 답하기 ══════════════
# ★요약은 정해진 항목만 담는다. "14시에 뭐였어?", "M14B 최대는?" 처럼
#   요약에 없는 것을 물으면 답할 근거가 없어서 "확인이 안 된다" 가 나왔다.
#   그래서 **질문을 보고 원본 전체를 다시 계산**한다. 첨부가 붙어 있는 동안
#   매 질문마다 도는 자리라, 계산은 한 번 훑기(O(행))로만 한다.

_T_RANGE = re.compile(
    r"(\d{1,2})\s*(?:시|:00)?\s*(?:~|-|부터|에서)\s*(\d{1,2})\s*시")
_T_POINT = re.compile(r"(\d{1,2})\s*시\s*(\d{1,2})?\s*분?|(\d{1,2}):(\d{2})")
_ASK_MAX = re.compile(r"최대|최고|제일 (?:높|큰)|피크")
_ASK_MIN = re.compile(r"최소|최저|제일 (?:낮|작)")
_ASK_AVG = re.compile(r"평균")
_ASK_CNT = re.compile(r"몇 ?분|몇 ?번|횟수|건수|얼마나")


def _hhmm(t):
    """'2026-08-23 08:20' · '08:20' → (8, 20). 못 읽으면 None."""
    m = re.search(r"(\d{1,2}):(\d{2})", str(t or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _stats(vals):
    sv = sorted(vals)
    return sv[0], sv[len(sv) // 2], sv[-1], sum(sv) / len(sv)


def query(rows, question, cuts=(60, 71, 85)):
    """질문에 맞춰 **전 행**을 다시 계산한다 → {lines, numbers} 또는 None.

    답할 거리가 없으면 None — 근거를 억지로 부풀리지 않는다.
    """
    if not rows:
        return None
    q = str(question or "")
    cols = list(rows[0].keys())
    tcol = _pick(cols, TIME_COLS)
    scol = _pick(cols, SCORE_COLS)
    warn = cuts[0]
    L, hit = [], False

    # ── 어느 컬럼을 볼 것인가 — 질문에 나온 컬럼/FAB 이 있으면 그것 ──
    want = []
    ql = q.lower()
    for c in cols:
        cl = str(c).lower().strip()
        if len(cl) >= 4 and cl in ql:
            want.append(c)
    for f in FABS:
        if re.search(r"\b" + f + r"\b", q, re.I):
            c = _pick(cols, ("{}_score".format(f).lower(),))
            if c and c not in want:
                want.append(c)
    # ★잡담에까지 통계를 붙이면 안 된다 — 데이터를 물었을 때만 기본 점수 컬럼.
    asks_data = bool(_ASK_MAX.search(q) or _ASK_MIN.search(q) or
                     _ASK_AVG.search(q) or _ASK_CNT.search(q) or
                     _T_RANGE.search(q) or _T_POINT.search(q) or
                     re.search(r"점수|등급|추이|경계|위험|초위험|분포|구간", q))
    if not want and scol and asks_data:
        want = [scol]
    want = want[:3]

    # ── 시각 하나를 물었나 ("14시 20분에", "08:20") ──
    pt = None
    mr = _T_RANGE.search(q)
    if not mr:
        mp = _T_POINT.search(q)
        if mp:
            if mp.group(3) is not None:
                pt = (int(mp.group(3)), int(mp.group(4)))
            else:
                pt = (int(mp.group(1)), int(mp.group(2) or 0))
    if pt and tcol:
        best, bestd = None, None
        for r in rows:
            hm = _hhmm(r.get(tcol))
            if not hm:
                continue
            d = abs((hm[0] * 60 + hm[1]) - (pt[0] * 60 + pt[1]))
            if bestd is None or d < bestd:
                best, bestd = r, d
        if best is not None:
            hit = True
            L.append("{:02d}:{:02d} 에 가장 가까운 행 ({}):".format(
                pt[0], pt[1], str(best.get(tcol) or "").strip()))
            for c in want:
                v = _num(best.get(c))
                L.append("   · {} = {}".format(
                    c, "{:g}".format(v) if v is not None else "값 없음"))
            if bestd:
                L.append("   (정확히 그 시각의 행은 없어 {}분 차이 나는 행을 봤다)"
                         .format(bestd))

    # ── 시간대를 물었나 ("14시~18시") ──
    lo = hi = None
    if mr and tcol:
        lo, hi = int(mr.group(1)), int(mr.group(2))

    # ── 컬럼별 통계 — 전 행 기준 (구간을 물었으면 그 구간만) ──
    for c in want:
        seq = []
        for r in rows:
            v = _num(r.get(c))
            if v is None:
                continue
            if lo is not None:
                hm = _hhmm(r.get(tcol))
                if not hm or not (lo <= hm[0] <= hi):
                    continue
            seq.append((str(r.get(tcol) or "").strip(), v))
        if not seq:
            if lo is not None:
                hit = True
                L.append("{} — {}시~{}시 구간에 값이 없습니다".format(c, lo, hi))
            continue
        vals = [v for _t, v in seq]
        mn, md, mx, avg = _stats(vals)
        t_max = max(seq, key=lambda x: x[1])
        t_min = min(seq, key=lambda x: x[1])
        where = " ({}시~{}시)".format(lo, hi) if lo is not None else " (전 구간)"
        hit = True
        L.append("{}{} — {}행 계산: 최소 {:g}({}) · 중앙 {:g} · 평균 {:.1f} · "
                 "최대 {:g}({})".format(c, where, len(seq), mn, t_min[0], md,
                                       avg, mx, t_max[0]))
        if _ASK_CNT.search(q):
            n = sum(1 for v in vals if v >= warn)
            L.append("   · 경계({}) 이상: {}행 / {}행".format(warn, n, len(seq)))

    if not hit:
        return None
    head = ["[첨부 원본 재계산 — 질문에 맞춰 전 행을 다시 셌다]"]
    txt = "\n".join(head + L)
    return {"lines": txt, "numbers": _numbers(txt)}
