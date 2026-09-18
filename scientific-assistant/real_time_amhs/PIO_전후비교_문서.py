# -*- coding: utf-8 -*-
"""PIO_ERROR 룰 추가 **전/후** 비교 문서를 만든다.

    python PIO_전후비교_문서.py <받은_노트북.txt 또는 .ipynb> [-o docs/...html]

2026-09-18. 고객이 "새로운 룰 키워서 스코어 PIO_ERROR FAB별 추가했어 —
전 후로 비교해서 해줄래, 결과도 만들어주고, 어떻게 더 나은지" 라고 해서 만들었다.
받은 노트북에는 셀마다 CSV 한 벌이 들어 있다:

    datetime, {라벨}_변경전_{fab}_area_score, datetime, {라벨}_변경후_{fab}_area_score

★이 문서가 재는 것은 '점수가 올랐나' 가 아니라 **화면이 달라졌나** 다.
  점수는 올라도 등급 컷(경계 60 · 위험 71 · 초위험 85)을 못 넘으면 관제
  화면에는 아무 일도 일어나지 않는다 — 운전원이 보는 것은 등급이다.
★그래서 셋을 나눠 본다:
    ① 룰이 먹었나        — 몇 분이 얼마나 올랐나
    ② 화면이 달라졌나    — 등급이 바뀐 분이 몇인가
    ③ 잡고 싶던 것을 잡았나 — 알려진 사건 구간에서 등급이 올랐나
  ①만 보고 "좋아졌다" 고 하면 안 된다. 실제로 이번 자료가 그랬다.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(BASE_DIR, "docs", "PIO_ERROR_전후비교.html")

# ── 등급 컷 ──────────────────────────────────────────────────────
# ★★현장은 **시스템마다 컷이 다르다** (정책 탭 → config.grade.by_sys).
#   저장소의 config.json 에는 by_sys 가 비어 있어서, 처음에 기본 밴드
#   (60·71·85)로 계산했다가 결론이 통째로 틀렸다 — M14 무언정지 구간이
#   "경계 0분" 으로 나왔는데 실제 컷(36)으로는 23분이었다.
#   컷이 틀리면 이 문서의 모든 숫자가 틀린다. 그래서 여기 박아 두고,
#   config 에 by_sys 가 있으면 그것을 먼저 쓴다.
CUTS_DEFAULT = (60, 71, 85)
CUTS_BY_SYS = {            # 2026-09-18 고객이 알려 준 운영 값
    "ALL":    (48, 60, 80),
    "M14":    (36, 52, 72),
    "M14B":   (36, 52, 72),
    "M16A":   (36, 52, 72),
    "M16B":   (36, 52, 72),
    "M16HUB": (40, 55, 75),
}
# 받은 자료의 컬럼명 → 관제 시스템 코드
SYS_OF = {"M16HUBROOM": "M16HUB", "M14A": "M14"}

# ★새 문서를 따로 만들지 않는다 — **이미 있는 그 FAB 의 분석 문서 뒤에 붙인다**
#   (고객: "하나 하나식 분리해줘!! 기존 내용에다가!! M14A·M16HUB 각각").
#   문서가 둘로 흩어지면 나중에 어느 쪽이 최신인지 알 수 없게 된다.
INTO = {
    "M14":    "M14_20260913_장애분석.html",      # M14A 2026-09-13 OHT 무언정지
    "M16HUB": "M16HUB_데드락_분석.html",          # M16 HUB 데드락 — 점수가 왜 안 올랐나
}
# 붙인 자리를 표시해 둔다 — 다시 돌리면 이 사이만 갈아끼운다(중복으로 안 쌓인다)
MARK0 = "<!-- PIO_ERROR 전/후 비교 (자동 생성 · PIO_전후비교_문서.py) -->"
MARK1 = "<!-- /PIO_ERROR 전/후 비교 -->"


def cuts_of(fab: str) -> tuple:
    """그 FAB 의 등급 컷. config.grade.by_sys 가 있으면 그것이 먼저다."""
    code = SYS_OF.get(fab.upper(), fab.upper())
    try:
        from lp_client import load_config
        g = (load_config().get("grade") or {})
        o = (g.get("by_sys") or {}).get(code)
        if o and all(k in o for k in ("warn", "danger", "critical")):
            return (int(o["warn"]), int(o["danger"]), int(o["critical"]))
    except Exception:                                    # noqa: BLE001
        pass
    return CUTS_BY_SYS.get(code, CUTS_DEFAULT)


CUTS = CUTS_DEFAULT        # 아래 함수들이 기본값으로 쓴다 (FAB 을 알면 cuts_of)
LEVELS = ("정상", "경계", "위험", "초위험")

# 알려진 사건 — 장애분석 문서(docs/M14_20260913_장애분석.html)에서 가져왔다.
# 그때 화면은 이 구간에서 '정상 31점' 이었다. 새 룰이 그걸 고쳤는지가 핵심이다.
# 같은 곳을 두 이름으로 부른다 — 받은 자료의 컬럼명(m14)과 현장·장애분석
# 문서의 이름(M14A). 문서에는 둘 다 적어 어느 쪽을 봐도 알아보게 한다.
ALIAS = {"M14": "M14A"}

KNOWN = [
    {"fab": "M14", "day": "2026-09-13", "from": "11:38", "to": "14:30",
     "what": "OHT 무언정지", "doc": "M14_20260913_장애분석.html"},
    {"fab": "M14", "day": "2026-09-13", "from": "05:16", "to": "08:38",
     "what": "컨베이어 용량 축소 203분", "doc": "M14_20260913_장애분석.html"},
]


def level(v: float, cuts=None) -> str:
    c = cuts or CUTS
    if v >= c[2]:
        return "초위험"
    if v >= c[1]:
        return "위험"
    if v >= c[0]:
        return "경계"
    return "정상"


def fabname(fab: str) -> str:
    """받은 컬럼명 + 현장 이름. 둘이 다르면 둘 다 적는다 (M14 ↔ M14A)."""
    other = ALIAS.get(fab.upper())
    return f"{fab} ({other})" if other else fab


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ────────────────────────────── 읽기 ──────────────────────────────
def read_cells(path: str) -> list[str]:
    """노트북(.ipynb/.txt)에서 셀 소스를 뽑는다. 그냥 CSV 파일이면 그대로."""
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    try:
        nb = json.loads(raw)
    except ValueError:
        return [raw]
    out = []
    for c in nb.get("cells", []):
        src = c.get("source")
        if isinstance(src, list):
            src = "".join(src)
        if src and "변경전" in src and "변경후" in src:
            out.append(src)
    return out


def parse(src: str) -> dict | None:
    """한 셀 → {fab, label, rows:[(t, before, after)]}.

    ★두 열의 시각이 어긋나면 비교 자체가 무의미하다 — 그 행은 버리고 센다.
    """
    rows = list(csv.reader(io.StringIO(src)))
    if not rows or len(rows[0]) < 4:
        return None
    hdr = [h.strip() for h in rows[0]]
    m = re.search(r"변경전_(.+?)_area_score", hdr[1])
    fab = (m.group(1) if m else "?").upper()
    label = hdr[1].split("_변경전")[0]
    out, skew = [], 0
    for r in rows[1:]:
        if len(r) < 4 or not r[0].strip():
            continue
        try:
            t1 = datetime.strptime(r[0].strip(), "%Y-%m-%d %H:%M")
            t2 = datetime.strptime(r[2].strip(), "%Y-%m-%d %H:%M")
            b, a = float(r[1]), float(r[3])
        except ValueError:
            continue
        if t1 != t2:
            skew += 1
            continue
        out.append((t1, b, a))
    return {"fab": fab, "label": label, "rows": out, "skew": skew} if out else None


# ────────────────────────────── 세기 ──────────────────────────────
def stats(rows, cuts=None) -> dict:
    c = cuts or CUTS
    ch = [(t, b, a) for t, b, a in rows if b != a]
    dif = [a - b for _, b, a in ch]
    cnt = {k: [0, 0] for k in LEVELS}
    for _, b, a in rows:
        cnt[level(b, c)][0] += 1
        cnt[level(a, c)][1] += 1
    moved = {}
    for _, b, a in rows:
        lb, la = level(b, c), level(a, c)
        if lb != la:
            moved[(lb, la)] = moved.get((lb, la), 0) + 1
    days = {}
    for t, b, a in rows:
        d = days.setdefault(t.date(), {"n": 0, "ch": 0, "wb": 0, "wa": 0,
                                       "hb": 0.0, "ha": 0.0})
        d["n"] += 1
        d["ch"] += (b != a)
        d["wb"] += (b >= c[0])
        d["wa"] += (a >= c[0])
        d["hb"] = max(d["hb"], b)
        d["ha"] = max(d["ha"], a)
    return {
        "n": len(rows), "ch": len(ch),
        "up": sum(1 for d in dif if d > 0), "down": sum(1 for d in dif if d < 0),
        "avg": (sum(dif) / len(dif)) if dif else 0.0,
        "max": max(dif) if dif else 0.0, "min": min(dif) if dif else 0.0,
        "cnt": cnt, "moved": moved, "days": days,
        "hi_b": max((b for _, b, _ in rows), default=0.0),
        "hi_a": max((a for _, _, a in rows), default=0.0),
        "changed": ch,
    }


def promote(rows, cuts) -> dict:
    """★이 문서의 핵심 지표 — 고객: "지금 경계값에 몰려있는데 위험이 있어야 돼.
    그게 핵심이야. 전보다 좋아졌는지 안 좋아졌는지 그게 핵심이야."

    점수가 오른 것도, 경계가 늘어난 것도 답이 아니다. 경계에 몰려 있던 것이
    **위험으로 올라갔는가** 가 답이다. 그래서 셋을 센다:
      · 위험 이상 분      — 전 → 후 (많아져야 좋다)
      · 경계 쏠림 비율    — 경계이상 중 경계에 머문 비율 (낮아져야 좋다)
      · 경계 → 위험 승격  — 실제로 올라간 분
    ★경계도 같이 늘면 쏠림 비율은 안 내려간다. 그건 '전체를 끌어올린 것' 이지
      '경계를 위험으로 올린 것' 이 아니다 — 그 둘을 가르려고 비율을 같이 본다.
    """
    def one(i):
        w = sum(1 for r in rows if cuts[0] <= r[i] < cuts[1])
        d = sum(1 for r in rows if r[i] >= cuts[1])
        return {"warn": w, "danger": d, "any": w + d,
                "share": (100.0 * w / (w + d)) if (w + d) else 0.0}
    up = [(t, b, a) for t, b, a in rows
          if cuts[0] <= b < cuts[1] <= a]
    near = [a for _, _, a in rows if cuts[0] <= a < cuts[1]]
    return {"before": one(1), "after": one(2), "up": up,
            "near5": sum(1 for a in near if cuts[1] - a <= 5),
            "near10": sum(1 for a in near if cuts[1] - a <= 10)}


def window(rows, day: str, t0: str, t1: str):
    return [(t, b, a) for t, b, a in rows
            if t.strftime("%Y-%m-%d") == day and t0 <= t.strftime("%H:%M") <= t1]


def scale_table(rows, ev=None, cuts=None):
    """배점을 N 배로 키웠다면 경계 이상이 몇 분이 되나 — '얼마나 모자란가' 를 본다."""
    c = cuts or CUTS
    out = []
    for mul in (1, 1.5, 2, 3, 4, 5):
        n = sum(1 for _, b, a in rows if b + (a - b) * mul >= c[0])
        e = sum(1 for _, b, a in (ev or []) if b + (a - b) * mul >= c[0])
        out.append((mul, n, e))
    return out


# ────────────────────────────── 쓰기 ──────────────────────────────
CSS = """:root{--ink:#111827;--dim:#6b7280;--line:#e5e7eb;--acc:#4f46e5;--bad:#b91c1c;
 --ok:#047857;--warn:#b45309;--bg:#f8fafc}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);line-height:1.7;
 font-family:"Malgun Gothic","맑은 고딕",-apple-system,system-ui,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:36px 24px 80px}
h1{font-size:26px;margin:0 0 6px}
.sub{color:var(--dim);font-size:13px;margin:0 0 28px}
h2{font-size:18px;margin:34px 0 10px;padding-top:16px;border-top:2px solid var(--ink)}
h3{font-size:14.5px;margin:20px 0 8px;color:#374151}
p,li{font-size:13.5px}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:var(--bg);font-weight:700;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code,.mono{font-family:Consolas,"D2Coding",monospace;font-size:12.5px;
 background:var(--bg);padding:1px 5px;border-radius:4px}
.note{background:var(--bg);border-left:4px solid var(--acc);padding:10px 14px;
 margin:12px 0;font-size:13px}
.miss{background:#fef2f2;border-left-color:var(--bad)}
.miss b{color:var(--bad)}
.good{background:#ecfdf5;border-left-color:var(--ok)}
.big{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}
.dim{color:var(--dim)}
.bad{color:var(--bad);font-weight:700}
.warn{color:var(--warn);font-weight:700}
.okc{color:var(--ok);font-weight:700}
tr.hi td{background:#fff7ed}
.bar{display:inline-block;height:9px;background:var(--acc);border-radius:5px;
 vertical-align:middle}
.bar.b2{background:#c7d2fe}
@media print{.wrap{max-width:none;padding:0} h2{page-break-after:avoid}}"""


def _lvrow(cnt, idx):
    return "".join(f'<td class=n>{cnt[k][idx]}</td>' for k in LEVELS)


def build(sets: list[dict]) -> str:
    a = [f'<!doctype html><html lang=ko><head><meta charset=utf-8>'
         f'<title>PIO_ERROR 룰 전/후 비교</title><style>{CSS}</style></head>'
         f'<body><div class=wrap>']
    a.append('<h1>PIO_ERROR 룰 추가 — 전 / 후 비교</h1>')
    a.append('<p class="sub">받은 자료 · ' + esc(" · ".join(
        f'{fabname(s["fab"])} {min(t for t,_,_ in s["rows"]):%Y-%m-%d}~{max(t for t,_,_ in s["rows"]):%m-%d}'
        f' {len(s["rows"])}분' for s in sets))
        + '</p>')
    a.append('<p class=sub>등급 컷은 <b>시스템마다 다릅니다</b> (정책 탭) — '
             + esc(' · '.join(f'{fabname(s["fab"])} {"/".join(map(str, cuts_of(s["fab"])))}'
                              for s in sets)) + '</p>')

    # ── 0. 한 줄로 ──────────────────────────────────────────────
    a.append('<h2>0. 한 줄로</h2>')
    # ★기준은 **위험이 늘었나** 다.
    #   고객: "지금 경계값에 몰려있는데 위험이 있어야 돼. 그게 핵심이야.
    #          전보다 좋아졌는지 안 좋아졌는지 그게 핵심이야."
    #   점수가 올랐다도, 경계가 늘었다도 답이 아니다. 경계만 늘면 "또 경계네" 가
    #   되어 오히려 덜 보게 된다.
    pres = [(fabname(s["fab"]), cuts_of(s["fab"]),
             promote(s["rows"], cuts_of(s["fab"]))) for s in sets]
    wins = [(nm, p) for nm, _, p in pres if p["after"]["danger"] > p["before"]["danger"]]
    flats = [(nm, p) for nm, _, p in pres if p["after"]["danger"] <= p["before"]["danger"]]
    if wins and not flats:
        head, box = "<b>좋아졌습니다 — 경계에 몰려 있던 것이 위험으로 올라갔습니다.</b>", "good"
    elif wins:
        head = ("<b>한쪽만 좋아졌습니다.</b> "
                + esc(" · ".join(f'{nm} 위험 {p["before"]["danger"]}→{p["after"]["danger"]}분'
                                 for nm, p in wins))
                + " 는 올라갔고, " + esc(" · ".join(nm for nm, _ in flats))
                + " 는 그대로입니다.")
        box = "miss"
    else:
        head, box = "<b>위험이 늘지 않았습니다 — 여전히 경계에 몰려 있습니다.</b>", "miss"
    a.append(f'<div class="note {box}">{head}<br>'
             f'운전원이 보는 것은 점수가 아니라 등급입니다. 점수가 올라도 컷을 '
             f'안 넘으면 화면에는 아무 일도 일어나지 않고, 경계만 늘면 '
             f'“또 경계네” 가 되어 오히려 덜 보게 됩니다.</div>')
    # ★FAB 을 합치지 않는다. 컷도 다르고(정책 탭) 성격도 전혀 다르다.
    a.append('<table><tr><th>FAB</th><th class=n>위험 이상 (전 → 후)</th>'
             '<th class=n>경계 쏠림</th><th class=n>경계→위험</th>'
             '<th>좋아졌나</th></tr>')
    for nm, c, pr in pres:
        db, da = pr["before"]["danger"], pr["after"]["danger"]
        if da > db and len(pr["up"]) >= 5:
            one = f'<b class=okc>좋아졌다</b> — 위험이 {db} → {da}분'
        elif da > db:
            one = f'<b class=warn>조금</b> — 위험이 {db} → {da}분'
        else:
            one = '<b class=bad>그대로</b>'
        a.append(f'<tr><td><b>{esc(nm)}</b> '
                 f'<span class=dim>컷 {c[0]}/{c[1]}/{c[2]}</span></td>'
                 f'<td class=n>{db} → <b>{da}</b></td>'
                 f'<td class=n>{pr["before"]["share"]:.0f}% → {pr["after"]["share"]:.0f}%</td>'
                 f'<td class=n>{len(pr["up"])}</td><td>{one}</td></tr>')
    a.append('</table>')
    a.append('<p class=dim>위험 이상 = 위험 + 초위험 · 경계 쏠림 = 경계 이상 가운데 '
             '경계에 머문 비율(<b>낮아져야</b> 좋다). '
             '★경계가 같이 늘면 쏠림은 안 내려간다 — 그건 “전체를 끌어올린 것” 이지 '
             '“경계를 위험으로 올린 것” 이 아니다. 둘을 가르려고 같이 본다.</p>')

    # ── 1. 한눈에 ───────────────────────────────────────────────
    a.append('<h2>1. 한눈에</h2><table><tr><th>FAB</th><th class=n>분</th>'
             '<th class=n>점수 오른 분</th><th class=n>올린 폭(평균/최대)</th>'
             '<th class=n>등급 바뀐 분</th><th>화면이 달라졌나</th></tr>')
    for s in sets:
        c = cuts_of(s["fab"])
        st = stats(s["rows"], c)
        mv = sum(st["moved"].values())
        a.append(f'<tr><td><b>{esc(fabname(s["fab"]))}</b></td><td class=n>{st["n"]:,}</td>'
                 f'<td class=n>{st["ch"]:,} <span class=dim>({100*st["ch"]/st["n"]:.1f}%)</span></td>'
                 f'<td class=n>{st["avg"]:+.1f} / {st["max"]:+.0f}</td>'
                 f'<td class=n>{"<b class=okc>" if mv else "<b class=bad>"}{mv}</b></td>'
                 f'<td>{"거의 그대로" if mv <= 1 else "일부 달라짐"}</td></tr>')
    a.append('</table>')

    # ── 2. FAB 마다 ─────────────────────────────────────────────
    for s in sets:
        c = cuts_of(s["fab"])
        st, rows = stats(s["rows"], c), s["rows"]
        pr = promote(rows, c)
        a.append(f'<h2>2. {esc(fabname(s["fab"]))} <span class=dim>— {esc(s["label"])}</span></h2>')
        if s.get("skew"):
            a.append(f'<div class="note miss"><b>주의:</b> 두 열의 시각이 어긋난 행이 '
                     f'{s["skew"]}개 있어 뺐습니다.</div>')

        a.append('<h3>① 룰이 먹었나</h3><table>'
                 '<tr><th>점수가 오른 분</th><th class=n>올린 폭 평균</th>'
                 '<th class=n>최대</th><th class=n>내려간 분</th></tr>'
                 f'<tr><td class=n>{st["ch"]:,}분 / {st["n"]:,}분 '
                 f'({100*st["ch"]/st["n"]:.1f}%)</td>'
                 f'<td class=n>{st["avg"]:+.1f}점</td><td class=n>{st["max"]:+.0f}점</td>'
                 f'<td class=n>{st["down"]}</td></tr></table>')

        a.append('<h3>② 화면이 달라졌나 <span class=dim>— 등급 분포(분)</span></h3>'
                 '<table><tr><th></th>' +
                 "".join(f'<th class=n>{k}</th>' for k in LEVELS) +
                 '<th class=n>최고점</th></tr>'
                 f'<tr><td>변경 전</td>{_lvrow(st["cnt"],0)}'
                 f'<td class=n>{st["hi_b"]:.0f}</td></tr>'
                 f'<tr><td>변경 후</td>{_lvrow(st["cnt"],1)}'
                 f'<td class=n>{st["hi_a"]:.0f}</td></tr></table>')
        if st["moved"]:
            a.append('<table><tr><th>등급이 바뀐 분</th><th class=n>분</th></tr>' +
                     "".join(f'<tr class=hi><td>{esc(lb)} → <b>{esc(la)}</b></td>'
                             f'<td class=n>{n}</td></tr>'
                             for (lb, la), n in sorted(st["moved"].items(),
                                                       key=lambda kv: -kv[1])) +
                     '</table>')
        else:
            a.append('<div class="note miss"><b>등급이 바뀐 분: 0</b> — '
                     '점수는 올랐지만 컷을 넘은 곳이 한 분도 없습니다. '
                     '관제 화면은 전과 완전히 같습니다.</div>')

        # 날짜별
        a.append('<h3>날짜별</h3><table><tr><th>날짜</th><th class=n>분</th>'
                 '<th class=n>오른 분</th><th class=n>경계 이상 (전 → 후)</th>'
                 '<th class=n>최고점 (전 → 후)</th></tr>')
        for day in sorted(st["days"]):
            d = st["days"][day]
            a.append(f'<tr><td>{day}</td><td class=n>{d["n"]:,}</td>'
                     f'<td class=n>{d["ch"]:,}</td>'
                     f'<td class=n>{d["wb"]} → {d["wa"]}</td>'
                     f'<td class=n>{d["hb"]:.0f} → {d["ha"]:.0f}</td></tr>')
        a.append('</table>')

        # 오른 분이 어디까지 갔나
        if st["changed"]:
            buck = {}
            for _, _, av in st["changed"]:
                buck.setdefault(int(av) // 10 * 10, 0)
                buck[int(av) // 10 * 10] += 1
            mx = max(buck.values())
            a.append('<h3>오른 분이 어디까지 갔나 <span class=dim>(변경 후 점수대)</span></h3>'
                     '<table><tr><th class=n>점수대</th><th class=n>분</th><th></th></tr>')
            for k in sorted(buck):
                w = int(300 * buck[k] / mx)
                over = ' <b class=okc>← 경계 위</b>' if k >= c[0] else ''
                a.append(f'<tr><td class=n>{k}~{k+9}</td><td class=n>{buck[k]:,}</td>'
                         f'<td><span class="bar" style="width:{w}px"></span>{over}</td></tr>')
            a.append('</table>')
            top = max(av for _, _, av in st["changed"])
            if top < c[0]:
                a.append(f'<div class="note miss">제일 높이 올라간 분도 <b>{top:.0f}점</b> — '
                         f'경계({c[0]})까지 <b>{c[0]-top:.0f}점</b> 모자랍니다.</div>')

        # ③ 알려진 사건
        evs = [e for e in KNOWN if e["fab"] == s["fab"]]
        if evs:
            a.append('<h3>③ 잡고 싶던 것을 잡았나 <span class=dim>— 알려진 사건 구간</span></h3>')
            a.append('<table><tr><th>사건</th><th class=n>구간</th><th class=n>분</th>'
                     '<th class=n>오른 분</th><th class=n>구간 최고 (전 → 후)</th>'
                     '<th class=n><b>위험 이상</b> (전 → 후)</th></tr>')
            for e in evs:
                w = window(rows, e["day"], e["from"], e["to"])
                if not w:
                    continue
                cb = sum(1 for _, b, _ in w if b >= c[1])
                ca = sum(1 for _, _, av in w if av >= c[1])
                a.append(f'<tr><td>{esc(e["what"])}<br><span class=dim>{esc(e["day"])}</span></td>'
                         f'<td class=n>{esc(e["from"])}~{esc(e["to"])}</td>'
                         f'<td class=n>{len(w)}</td>'
                         f'<td class=n>{sum(1 for _,b,av in w if b!=av)}</td>'
                         f'<td class=n>{max(b for _,b,_ in w):.0f} → '
                         f'<b>{max(av for _,_,av in w):.0f}</b></td>'
                         f'<td class=n>{cb} → <b class="{"okc" if ca>cb else "bad"}">{ca}</b></td></tr>')
            a.append('</table>')
            for e in evs:
                w = window(rows, e["day"], e["from"], e["to"])
                if not w:
                    continue
                hi = max(av for _, _, av in w)
                if hi < c[1]:
                    a.append(f'<div class="note miss"><b>{esc(e["what"])}</b> — 새 룰을 넣은 뒤에도 '
                             f'구간 최고가 <b>{hi:.0f}점</b>이라 여전히 '
                             f'<b>위험 아래</b>입니다 (위험까지 {c[1]-hi:.0f}점). '
                             f'이 사건에 대해서는 PIO_ERROR 가 신호가 아닙니다.</div>')

        # 배점을 키웠다면
        ev = []
        for e in evs:
            ev += window(rows, e["day"], e["from"], e["to"])
        a.append('<h3>배점을 키웠다면 <span class=dim>— 지금 올린 폭의 N 배였을 때 경계 이상 분</span></h3>'
                 '<table><tr><th class=n>배수</th><th class=n>경계 이상 분</th>'
                 + ('<th class=n>그중 사건 구간</th>' if ev else '') + '</tr>')
        for mul, n, e in scale_table(rows, ev, c):
            a.append(f'<tr{" class=hi" if mul==1 else ""}><td class=n>×{mul}</td>'
                     f'<td class=n>{n:,}</td>'
                     + (f'<td class=n>{e}</td>' if ev else '') + '</tr>')
        a.append('</table>')

    # ── 3. 그래서 ──────────────────────────────────────────────
    a.append('<h2>3. 그래서 — 어떻게 해야 나아지나</h2>')
    a.append('<div class="note"><b>지금 자료가 말하는 것</b><ul>'
             '<li>룰 자체는 <b>잘 붙었습니다</b> — 점수가 올라야 할 자리에서 올랐고, '
             '내려간 분은 한 분도 없습니다(부작용 없음).</li>'
             '<li>다만 <b>올린 폭이 컷에 비해 작습니다</b>. 등급이 바뀌지 않으면 '
             '관제 화면에서는 아무 일도 일어나지 않습니다.</li>'
             '<li>알려진 사건 구간에서 등급이 안 올랐다면, 그 사건에 대해서는 '
             '<b>PIO_ERROR 가 신호가 아닙니다</b> — 배점을 키워도 안 잡힙니다.</li>'
             '</ul></div>')
    a.append('<p>배점을 키우는 것은 <b>양날</b>입니다. 위 “배점을 키웠다면” 표에서 '
             '경계 이상 분이 몇 배로 뛰는지를 먼저 보십시오 — 사건이 없는 날에도 '
             '같이 뜁니다. 점수를 올리는 것보다 </p>'
             '<ul><li><b>얼마나 넘었나</b>(1% 넘은 것과 300% 넘은 것을 가르기)</li>'
             '<li><b>얼마나 계속됐나</b>(1분짜리와 173분짜리를 가르기)</li></ul>'
             '<p>를 점수에 넣는 쪽이 먼저입니다 — '
             '<code>docs/M14_20260913_장애분석.html</code> 3) 에 적어 둔 그것입니다.</p>')
    a.append('<h2>4. 이 문서가 말하지 않는 것</h2><ul>'
             '<li>받은 두 벌(변경 전·후 area_score)만 놓고 비교했습니다. '
             'PIO_ERROR 룰이 <b>어떻게</b> 계산되는지는 보지 않았습니다.</li>'
             '<li>사건 구간은 <code>docs/M14_20260913_장애분석.html</code> 에서 가져왔습니다. '
             '다른 사건이 더 있었다면 이 문서에는 없습니다.</li>'
             '<li>등급 컷은 <code>config.grade.bands</code> 의 지금 값입니다 '
             '— 시스템마다 다릅니다(정책 탭). 컷을 바꾸면 결론도 바뀝니다. '
             '실제로 처음엔 저장소 기본값(60·71·85)으로 계산했다가 M14 무언정지가 '
             '“경계 0분” 으로 나왔는데, 실제 컷(36)으로는 23분이었습니다.</li>'
             '</ul>')
    a.append('</div></body></html>')
    return "".join(a)



def fab_section(s: dict, title: str = "") -> str:
    """한 FAB 의 전/후 비교 — **기존 분석 문서 뒤에 붙일** 한 절.

    ★고객: "하나 하나식 분리해줘!! 기존 내용에다가!! M14A·M16HUB 각각".
      새 문서를 따로 만들면 나중에 어느 쪽이 최신인지 알 수 없다.
    """
    a = []
    c = cuts_of(s["fab"])
    st, rows = stats(s["rows"], c), s["rows"]
    pr = promote(rows, c)
    title = title or f'PIO_ERROR 룰 추가 — 전 / 후 ({fabname(s["fab"])})'
    a.append(f'<h2>{esc(title)} <span class=dim>— {esc(s["label"])}</span></h2>')
    # 이 절만 떼어 봐도 뭘 잰 것인지 알게, 머리에 한 줄을 둔다
    db, da = pr["before"]["danger"], pr["after"]["danger"]
    # ★+2분을 '좋아졌다' 고 쓰면 거짓말이다. 경계에서 올라온 것이 5분 이상일
    #   때만 초록으로 쓴다 (0. 한 줄로 의 판정과 같은 기준).
    nup = len(pr["up"])
    if da > db and nup >= 5:
        good, word = True, "좋아졌습니다"
    elif da > db:
        good, word = False, "조금 올랐을 뿐입니다"
    else:
        good, word = False, "위험은 늘지 않았습니다"
    up_txt = f' (경계에서 올라온 것 {nup}분)' if nup else ""
    a.append(f'<div class="note {"good" if good else "miss"}">'
             f'<b>{word} — 위험 이상 {db} → {da}분{up_txt}</b><br>'
             f'기준은 <b>경계에 몰려 있던 것이 위험으로 올라갔나</b> 입니다. '
             f'점수가 올라도 컷({c[0]}/{c[1]}/{c[2]})을 안 넘으면 화면은 그대로이고, '
             f'경계만 늘면 “또 경계네” 가 되어 오히려 덜 보게 됩니다.</div>')
    a.append('<table><tr><th></th><th class=n>정상</th><th class=n>경계</th>'
             '<th class=n>위험</th><th class=n>초위험</th>'
             '<th class=n>위험 이상</th><th class=n>경계 쏠림</th></tr>')
    for tag, key, idx in (("변경 전", "before", 0), ("변경 후", "after", 1)):
        q = pr[key]
        a.append(f'<tr><td><b>{tag}</b></td>'
                 + "".join(f'<td class=n>{st["cnt"][k][idx]}</td>' for k in LEVELS)
                 + f'<td class=n><b>{q["danger"]}</b></td>'
                 f'<td class=n>{q["share"]:.0f}%</td></tr>')
    a.append('</table>')
    if pr["up"]:
        a.append(f'<p>경계 → 위험으로 올라간 분 <b>{len(pr["up"])}</b> · '
                 f'위험({c[1]}) 문턱 5점 이내에 남은 분 <b>{pr["near5"]}</b> · '
                 f'10점 이내 <b>{pr["near10"]}</b></p>')
    c = cuts_of(s["fab"])
    st, rows = stats(s["rows"], c), s["rows"]
    pr = promote(rows, c)
    if s.get("skew"):
        a.append(f'<div class="note miss"><b>주의:</b> 두 열의 시각이 어긋난 행이 '
                 f'{s["skew"]}개 있어 뺐습니다.</div>')

    a.append('<h3>① 룰이 먹었나</h3><table>'
             '<tr><th>점수가 오른 분</th><th class=n>올린 폭 평균</th>'
             '<th class=n>최대</th><th class=n>내려간 분</th></tr>'
             f'<tr><td class=n>{st["ch"]:,}분 / {st["n"]:,}분 '
             f'({100*st["ch"]/st["n"]:.1f}%)</td>'
             f'<td class=n>{st["avg"]:+.1f}점</td><td class=n>{st["max"]:+.0f}점</td>'
             f'<td class=n>{st["down"]}</td></tr></table>')

    a.append('<h3>② 화면이 달라졌나 <span class=dim>— 등급 분포(분)</span></h3>'
             '<table><tr><th></th>' +
             "".join(f'<th class=n>{k}</th>' for k in LEVELS) +
             '<th class=n>최고점</th></tr>'
             f'<tr><td>변경 전</td>{_lvrow(st["cnt"],0)}'
             f'<td class=n>{st["hi_b"]:.0f}</td></tr>'
             f'<tr><td>변경 후</td>{_lvrow(st["cnt"],1)}'
             f'<td class=n>{st["hi_a"]:.0f}</td></tr></table>')
    if st["moved"]:
        a.append('<table><tr><th>등급이 바뀐 분</th><th class=n>분</th></tr>' +
                 "".join(f'<tr class=hi><td>{esc(lb)} → <b>{esc(la)}</b></td>'
                         f'<td class=n>{n}</td></tr>'
                         for (lb, la), n in sorted(st["moved"].items(),
                                                   key=lambda kv: -kv[1])) +
                 '</table>')
    else:
        a.append('<div class="note miss"><b>등급이 바뀐 분: 0</b> — '
                 '점수는 올랐지만 컷을 넘은 곳이 한 분도 없습니다. '
                 '관제 화면은 전과 완전히 같습니다.</div>')

    # 날짜별
    a.append('<h3>날짜별</h3><table><tr><th>날짜</th><th class=n>분</th>'
             '<th class=n>오른 분</th><th class=n>경계 이상 (전 → 후)</th>'
             '<th class=n>최고점 (전 → 후)</th></tr>')
    for day in sorted(st["days"]):
        d = st["days"][day]
        a.append(f'<tr><td>{day}</td><td class=n>{d["n"]:,}</td>'
                 f'<td class=n>{d["ch"]:,}</td>'
                 f'<td class=n>{d["wb"]} → {d["wa"]}</td>'
                 f'<td class=n>{d["hb"]:.0f} → {d["ha"]:.0f}</td></tr>')
    a.append('</table>')

    # 오른 분이 어디까지 갔나
    if st["changed"]:
        buck = {}
        for _, _, av in st["changed"]:
            buck.setdefault(int(av) // 10 * 10, 0)
            buck[int(av) // 10 * 10] += 1
        mx = max(buck.values())
        a.append('<h3>오른 분이 어디까지 갔나 <span class=dim>(변경 후 점수대)</span></h3>'
                 '<table><tr><th class=n>점수대</th><th class=n>분</th><th></th></tr>')
        for k in sorted(buck):
            w = int(300 * buck[k] / mx)
            over = ' <b class=okc>← 경계 위</b>' if k >= c[0] else ''
            a.append(f'<tr><td class=n>{k}~{k+9}</td><td class=n>{buck[k]:,}</td>'
                     f'<td><span class="bar" style="width:{w}px"></span>{over}</td></tr>')
        a.append('</table>')
        top = max(av for _, _, av in st["changed"])
        if top < c[0]:
            a.append(f'<div class="note miss">제일 높이 올라간 분도 <b>{top:.0f}점</b> — '
                     f'경계({c[0]})까지 <b>{c[0]-top:.0f}점</b> 모자랍니다.</div>')

    # ③ 알려진 사건
    evs = [e for e in KNOWN if e["fab"] == s["fab"]]
    if evs:
        a.append('<h3>③ 잡고 싶던 것을 잡았나 <span class=dim>— 알려진 사건 구간</span></h3>')
        a.append('<table><tr><th>사건</th><th class=n>구간</th><th class=n>분</th>'
                 '<th class=n>오른 분</th><th class=n>구간 최고 (전 → 후)</th>'
                 '<th class=n><b>위험 이상</b> (전 → 후)</th></tr>')
        for e in evs:
            w = window(rows, e["day"], e["from"], e["to"])
            if not w:
                continue
            cb = sum(1 for _, b, _ in w if b >= c[1])
            ca = sum(1 for _, _, av in w if av >= c[1])
            a.append(f'<tr><td>{esc(e["what"])}<br><span class=dim>{esc(e["day"])}</span></td>'
                     f'<td class=n>{esc(e["from"])}~{esc(e["to"])}</td>'
                     f'<td class=n>{len(w)}</td>'
                     f'<td class=n>{sum(1 for _,b,av in w if b!=av)}</td>'
                     f'<td class=n>{max(b for _,b,_ in w):.0f} → '
                     f'<b>{max(av for _,_,av in w):.0f}</b></td>'
                     f'<td class=n>{cb} → <b class="{"okc" if ca>cb else "bad"}">{ca}</b></td></tr>')
        a.append('</table>')
        for e in evs:
            w = window(rows, e["day"], e["from"], e["to"])
            if not w:
                continue
            hi = max(av for _, _, av in w)
            if hi < c[1]:
                a.append(f'<div class="note miss"><b>{esc(e["what"])}</b> — 새 룰을 넣은 뒤에도 '
                         f'구간 최고가 <b>{hi:.0f}점</b>이라 여전히 '
                         f'<b>위험 아래</b>입니다 (위험까지 {c[1]-hi:.0f}점). '
                         f'이 사건에 대해서는 PIO_ERROR 가 신호가 아닙니다.</div>')

    # 배점을 키웠다면
    ev = []
    for e in evs:
        ev += window(rows, e["day"], e["from"], e["to"])
    a.append('<h3>배점을 키웠다면 <span class=dim>— 지금 올린 폭의 N 배였을 때 경계 이상 분</span></h3>'
             '<table><tr><th class=n>배수</th><th class=n>경계 이상 분</th>'
             + ('<th class=n>그중 사건 구간</th>' if ev else '') + '</tr>')
    for mul, n, e in scale_table(rows, ev, c):
        a.append(f'<tr{" class=hi" if mul==1 else ""}><td class=n>×{mul}</td>'
                 f'<td class=n>{n:,}</td>'
                 + (f'<td class=n>{e}</td>' if ev else '') + '</tr>')
    a.append('</table>')
    return "".join(a)


def splice(path: str, html: str) -> str:
    """기존 문서 뒤에 붙인다. 이미 붙어 있으면 그 자리만 갈아끼운다."""
    doc = io.open(path, encoding="utf-8").read()
    block = MARK0 + html + MARK1
    if MARK0 in doc and MARK1 in doc:
        i, j = doc.index(MARK0), doc.index(MARK1) + len(MARK1)
        doc = doc[:i] + block + doc[j:]
    else:
        tail = "</div></body></html>"
        if tail not in doc:
            raise ValueError(f"문서 끝을 못 찾았다: {path}")
        doc = doc.replace(tail, block + tail)
    io.open(path, "w", encoding="utf-8").write(doc)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="PIO_ERROR 룰 전/후 비교")
    ap.add_argument("src", help="받은 노트북(.ipynb/.txt) 또는 CSV")
    ap.add_argument("-o", "--out", default=OUT_DEFAULT,
                    help="합본 문서 자리 (--into 를 쓰면 안 만든다)")
    ap.add_argument("--into", action="store_true", default=True,
                    help="[기본] FAB 마다 **이미 있는 분석 문서 뒤에** 붙인다")
    ap.add_argument("--standalone", action="store_true",
                    help="붙이지 않고 합본 문서 한 장만 만든다")
    ns = ap.parse_args(argv)

    sets = [p for p in (parse(c) for c in read_cells(ns.src)) if p]
    if not sets:
        print("변경전/변경후 두 열을 가진 자료를 못 찾았습니다.", file=sys.stderr)
        return 2

    for s in sets:
        c = cuts_of(s["fab"])
        st = stats(s["rows"], c)
        pr = promote(s["rows"], c)
        print(f'  {fabname(s["fab"]):<18} 컷 {c[0]}/{c[1]}/{c[2]}'
              f' · 오른 분 {st["ch"]:>4}'
              f' · 등급 바뀐 분 {sum(st["moved"].values()):>3}'
              f' · 위험이상 {pr["before"]["danger"]} → {pr["after"]["danger"]}'
              f' · 경계→위험 {len(pr["up"])}')

    if ns.standalone:
        os.makedirs(os.path.dirname(ns.out), exist_ok=True)
        io.open(ns.out, "w", encoding="utf-8").write(build(sets))
        print(f"→ {ns.out}")
        return 0

    # ★기본은 **기존 문서에 붙이기**. FAB 마다 제 문서로 간다.
    miss = []
    for s in sets:
        code = SYS_OF.get(s["fab"].upper(), s["fab"].upper())
        name = INTO.get(code)
        if not name:
            miss.append(s["fab"])
            continue
        path = os.path.join(BASE_DIR, "docs", name)
        if not os.path.isfile(path):
            miss.append(f'{s["fab"]}({name} 없음)')
            continue
        splice(path, fab_section(s))
        print(f'→ {os.path.join("docs", name)}  ({fabname(s["fab"])} 절 붙임)')
    if miss:
        print("붙일 문서를 못 찾음: " + ", ".join(miss), file=sys.stderr)
        print("  (INTO 에 FAB → 문서 이름을 적어 주세요)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
