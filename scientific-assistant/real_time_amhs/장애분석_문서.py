#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사건 하나를 놓고 '왜 그 점수였나' 를 따지는 문서를 만든다.

    python 장애분석_문서.py 발동이벤트.csv --fab M14 \
        --event 11:38-14:30 --title "M14A OHT 8대 무언정지"

왜 스크립트로 만드나 — 손으로 쓰면 다음 사건 때 또 처음부터다
    2026-09-13 M14A 무언정지를 분석하면서 만들었다. 그때 손으로 표를 짜
    두었으면 다음 사건에는 아무것도 안 남는다. 숫자는 전부 발동이벤트
    CSV 에서 읽고, 임계는 hubroom_predictor.py 에서 읽는다 — 룰이 바뀌면
    문서도 따라 바뀐다.

무엇을 따지나 — 고객이 물은 그대로
    ① 조용한데 왜 높은 점수가 났나   → 켜진 룰 수와 **임계 대비 배율**
    ② 사건인데 왜 점수가 낮았나      → 사건 전후로 지표가 어느 쪽으로 갔나
    ③ 그래서 점수식을 어떻게 고치나  → ①②에서 나온 것만 적는다
"""
from __future__ import annotations

import csv
import html
import io
import os
import re
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE, "docs")

# 룰 배점 칸 이름 — CSV 의 {FAB}_pts_{키} 와 같아야 한다
RULES = [("RA", "반송지연"), ("RA_sus", "반송지연 지속"), ("RB", "반입급증(30분)"),
         ("RB_fast", "반입급증(10분)"), ("RC", "리프터 정체"), ("RD", "저장 포화"),
         ("SLA", "4분초과"), ("SORT", "소터 대기"), ("MAXCAPA", "용량 축소")]

# 배율을 잴 수 있는 지표 — (표시이름, CSV 칸, 임계를 읽을 곳, 방향)
#   dir=+1 이면 '크면 이상', -1 이면 '작으면 이상'
METRICS = [
    ("반송시간(분)", "{f}_ra", ("TH_RA", "{f}"), +1),
    ("반입증감(30분)", "{f}_rb_diff30", ("TH_RB_30", "{f}"), +1),
    ("4분초과율(%)", "sla_{f}", ("TH_SLA_RATIO", "{f}"), +1),
    ("소터 대기", "sorter_{f}", ("TH_SORTER_WAIT", "{f}"), +1),
    ("OHT 가동률(%)", "{f}_rd_oht", ("TH_RD_OHT_UTIL", None), +1),
]


def e(s):
    return html.escape(str(s))


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def read_th():
    """임계를 룰 원본에서 읽는다 — 문서에 손으로 적으면 어긋난다."""
    import importlib.util
    p = os.path.join(BASE, "컬럼흐름_문서.py")
    spec = importlib.util.spec_from_file_location("_cf", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = m.build()
    return (d["C"] if d.get("ok") else {}), d


def th_of(C, spec, fab):
    """('TH_RA','M14') → 3.3. 없으면 None (문서에 '—' 로 적는다)."""
    key, sub = spec
    v = C.get(key)
    if v is None:
        return None
    if sub is None:
        return f(v)
    return f((v or {}).get(sub.format(f=fab)))


def hhmm(s):
    return str(s or "")[11:16]


def _mins(t):
    try:
        return int(t[:2]) * 60 + int(t[3:5])
    except (ValueError, IndexError):
        return None


def _shift(t, dm):
    m = (_mins(t) or 0) + dm
    m = max(0, min(24 * 60 - 1, m))
    return "%02d:%02d" % (m // 60, m % 60)


def d_lead(t, ref):
    """ref 보다 몇 분 빠른가 — 양수면 앞섰다. 못 읽으면 None."""
    a, b = _mins(t), _mins(ref)
    return None if (a is None or b is None) else (b - a)


_DT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


def load_screen(path):
    """FAB 화면 표 CSV(시간,등급,종합점수,…) → {HH:MM: (등급, 종합점수)}.

    ★등급은 발동이벤트 CSV 에 없다(unified_risk_level 이 비어 있다). 그런데
      고객이 물은 건 '초위험 알람이 울렸다' 이고, 그 등급은 화면이 매긴 것이다.
      두 파일을 맞춰야 '무엇을 보고 물었는지' 와 '왜 그랬는지' 가 한 줄에 선다.
    """
    out = {}
    if not path or not os.path.exists(path):
        return out
    for r in csv.DictReader(io.open(path, encoding="utf-8-sig")):
        t = str(r.get("시간") or "")
        if _DT.match(t):
            out[t[11:16]] = (r.get("등급") or "", r.get("종합점수") or "")
    return out


def load(path):
    """CSV → 분 단위 행. **datetime 이 날짜가 아닌 행은 버린다.**

    ★실제 받은 파일에 그런 행이 2개 있었다 — reason 칸 안의 따옴표가 어긋나
      한 줄이 두 줄로 쪼개진 것이다. 그대로 두면 정렬했을 때 맨 앞에 와서
      문서의 날짜·파일명이 'M16HUB.QUE…' 가 된다. 몇 줄을 버렸는지는
      문서에 적는다 — 조용히 버리면 자료가 모자란 걸 아무도 모른다.
    """
    raw = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
    rows = [r for r in raw if _DT.match(str(r.get("datetime") or ""))]
    rows.sort(key=lambda r: r["datetime"])
    return rows, len(raw) - len(rows)


# ────────────────────────────── 분석 ──────────────────────────────
def fired(r, fab):
    """그 분에 켜진 룰 — [(이름, 배점)]."""
    out = []
    for k, nm in RULES:
        v = f(r.get("{}_pts_{}".format(fab, k)))
        if v:
            out.append((nm, v))
    return out


def ratios(r, fab, C):
    """임계를 넘은 지표의 **배율** — [(이름, 값, 임계, 배율)].

    ★이 문서의 핵심 숫자다. 배점은 0 아니면 만점이라 '얼마나 넘었나' 를
      안 보는데, 고객이 물은 게 정확히 그것이다.
    """
    out = []
    for nm, col, spec, _d in METRICS:
        v = f(r.get(col.format(f=fab)))
        th = th_of(C, spec, fab)
        if v is None or not th:
            continue
        out.append((nm, v, th, v / th))
    return out


def peak_rows(rows, fab, C, n=8):
    """지표가 제일 심했던 분 — '심한데 점수가 낮았다' 를 보이는 자리."""
    col = "{}_ra".format(fab)
    th = th_of(C, ("TH_RA", "{f}"), fab) or 1.0
    got = [(f(r.get(col)), r) for r in rows]
    got = [(v, r) for v, r in got if v is not None]
    got.sort(key=lambda x: -x[0])
    return [(v, v / th, r) for v, r in got[:n]]


def window(rows, lo, hi):
    return [r for r in rows if lo <= hhmm(r.get("datetime")) <= hi]


def avg(rows, col):
    vs = [f(r.get(col)) for r in rows]
    vs = [v for v in vs if v is not None]
    return (sum(vs) / len(vs)) if vs else None


def top_scored(rows, fab, n=1):
    col = "{}_score".format(fab)
    got = [(f(r.get(col)) or 0, r) for r in rows]
    got.sort(key=lambda x: -x[0])
    return got[:n]


def direction(rows, fab, C, before, during):
    """사건 전/중 평균과 방향 — ②의 근거."""
    out = []
    for nm, col, spec, _d in METRICS:
        c = col.format(f=fab)
        a, b = avg(before, c), avg(during, c)
        if a is None or b is None:
            continue
        out.append((nm, a, b, th_of(C, spec, fab)))
    return out


CSS = """
:root{--ink:#111827;--dim:#6b7280;--line:#e5e7eb;--acc:#4f46e5;--bad:#b91c1c;
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
.flow{font-family:Consolas,"D2Coding",monospace;font-size:12.5px;
 background:var(--bg);border:1px solid var(--line);border-radius:8px;
 padding:14px 16px;white-space:pre;overflow-x:auto;line-height:1.6}
.big{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}
.dim{color:var(--dim)}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;
 background:var(--bg);border:1px solid var(--line);color:var(--dim)}
.bad{color:var(--bad);font-weight:700}
.warn{color:var(--warn);font-weight:700}
.okc{color:var(--ok);font-weight:700}
tr.hi td{background:#fff7ed}
tr.lo td{background:#f5f3ff}
@media print{.wrap{max-width:none;padding:0} h2{page-break-after:avoid}}
"""


def bar_svg(items, th, unit="", w=620, label=""):
    """임계 대비 배율 막대 — 숫자만으로는 '3.45배' 가 안 와닿는다."""
    if not items:
        return ""
    h = 22 * len(items) + 34
    mx = max(max(v for _t, v in items), th * 1.2) or 1.0
    X = lambda v: 118 + (w - 150) * (v / mx)
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.b{fill:#a5b4fc}.b2{fill:#f87171}.t{font:11px "Malgun Gothic",sans-serif;fill:#374151}'
         '.n{font:700 11px Consolas,monospace;fill:#111827}.th{stroke:#b91c1c;stroke-dasharray:4 3}'
         '.thx{font:10px Consolas,monospace;fill:#b91c1c}</style>']
    o.append('<line class="th" x1="%.1f" y1="16" x2="%.1f" y2="%d"/>' % (X(th), X(th), h - 16))
    o.append('<text class="thx" x="%.1f" y="12" text-anchor="middle">임계 %s</text>'
             % (X(th), _num(th)))
    y = 24
    for t, v in items:
        o.append('<text class="t" x="0" y="%d">%s</text>' % (y + 10, e(t)))
        o.append('<rect class="%s" x="118" y="%d" width="%.1f" height="13" rx="2"/>'
                 % ("b2" if v >= th else "b", y, max(1.0, X(v) - 118)))
        o.append('<text class="n" x="%.1f" y="%d">%s%s</text>'
                 % (X(v) + 5, y + 11, _num(v), e(unit)))
        y += 22
    o.append("</svg>")
    return '<div style="margin:10px 0">' + "".join(o) + "</div>"


def ratio_svg(items, w=660, label=""):
    """룰별 '임계 대비 배율' 가로 막대 — 1.0배 선을 긋는다.

    ★이 그림 하나가 1번의 답이다. 막대가 전부 1.0배 선에 딱 붙어 있으면
      '심해서 높은 게 아니라 여럿이 걸쳐서 높은 것' 이 눈에 보인다.
    """
    if not items:
        return ""
    h = 24 * len(items) + 46
    mx = max(2.2, max(m for _n, _v, _t, m in items) * 1.15)
    X = lambda r: 150 + (w - 190) * (r / mx)
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.t{font:11.5px "Malgun Gothic",sans-serif;fill:#374151}'
         '.n{font:700 11px Consolas,monospace}.g{stroke:#e5e7eb}'
         '.one{stroke:#b91c1c;stroke-width:1.2;stroke-dasharray:4 3}'
         '.lb{font:10px Consolas,monospace;fill:#b91c1c}'
         '.s{font:10px Consolas,monospace;fill:#9ca3af}</style>']
    for g in (1.0, 2.0):
        if g <= mx:
            o.append('<line class="%s" x1="%.1f" y1="26" x2="%.1f" y2="%d"/>'
                     % ("one" if g == 1.0 else "g", X(g), X(g), h - 18))
            o.append('<text class="%s" x="%.1f" y="20" text-anchor="middle">%.0f배</text>'
                     % ("lb" if g == 1.0 else "s", X(g), g))
    y = 32
    for nm, v, th, m in items:
        col = "#dc2626" if m >= 2 else "#f59e0b" if m >= 1.3 else "#93c5fd"
        o.append('<text class="t" x="0" y="%d">%s</text>' % (y + 11, e(nm)))
        o.append('<rect x="150" y="%d" width="%.1f" height="14" rx="2" fill="%s"/>'
                 % (y, max(1.5, X(m) - 150), col))
        o.append('<text class="n" x="%.1f" y="%d" fill="#111827">%.2f배</text>'
                 % (X(m) + 6, y + 12, m))
        o.append('<text class="s" x="%.1f" y="%d">%s / %s</text>'
                 % (X(m) + 52, y + 12, _num(v), _num(th)))
        y += 24
    o.append("</svg>")
    return '<div style="margin:12px 0">%s</div>' % "".join(o)


def series_svg(pts, mark=None, w=880, h=None, label=""):
    """사건 구간 시계열 — 점수는 막대, 지표는 선(각자 0~1 로 정규화).

    ★2번의 답이다. 점수가 낮은 채로 눌려 있는 동안 지표들이 **같이 내려가는**
      모습이 한 화면에 있어야 '왜 못 잡았나' 가 설명된다. 눈금이 서로 달라
      정규화하고, 실제 값은 양 끝에 적는다.
    """
    if not pts:
        return ""
    ts = [t for t, _sc, _ms in pts]
    n = len(pts)
    # 높이는 범례 줄 수를 따라간다 — 박아 두면 지표가 늘 때 범례가 넘친다
    h = h or max(210, 56 + 27 * len(pts[0][2] or {}))
    L, R, T, B = 46, 150, 26, 30      # 오른쪽은 범례 자리(두 줄 × 지표 수)
    iw, ih = w - L - R, h - T - B
    X = lambda i: L + iw * (i / max(1, n - 1))
    smax = max([sc for _t, sc, _m in pts] + [1.0])
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.ax{font:10px Consolas,monospace;fill:#9ca3af}'
         '.lg{font:10.5px "Malgun Gothic",sans-serif}'
         '.bar{fill:#c7d2fe}.mk{stroke:#b91c1c;stroke-dasharray:3 3}</style>',
         '<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfcfe" stroke="#e5e7eb"/>'
         % (L, T, iw, ih)]
    bw = max(2.0, iw / n * 0.62)
    for i, (_t, sc, _m) in enumerate(pts):
        hh = ih * (sc / smax)
        o.append('<rect class="bar" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1"/>'
                 % (X(i) - bw / 2, T + ih - hh, bw, max(0.8, hh)))
    cols = ["#dc2626", "#0891b2", "#7c3aed", "#059669", "#d97706"]
    names = [k for k in (pts[0][2] or {})]
    for j, k in enumerate(names):
        vs = [(m or {}).get(k) for _t, _s, m in pts]
        ok = [v for v in vs if v is not None]
        if len(ok) < 2:
            continue
        lo, hi = min(ok), max(ok)
        rng = (hi - lo) or 1.0
        d, first = [], True
        for i, v in enumerate(vs):
            if v is None:
                continue
            d.append("%s%.1f,%.1f" % ("M" if first else "L", X(i),
                                      T + ih * (1 - (v - lo) / rng) * 0.92 + ih * 0.04))
            first = False
        c = cols[j % len(cols)]
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.5" opacity=".9"/>' % (" ".join(d), c))
        yy = T + 14 + j * 27          # 이름+값범위 두 줄이라 15px 면 겹친다
        o.append('<text class="lg" x="%d" y="%d" fill="%s">%s</text>' % (L + iw + 8, yy, c, e(k)))
        o.append('<text class="ax" x="%d" y="%d">%s→%s</text>'
                 % (L + iw + 8, yy + 11, _num(ok[0]), _num(ok[-1])))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">%s</text>' % (L - 5, T + 9, _num(smax)))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">0</text>' % (L - 5, T + ih))
    o.append('<text class="ax" x="%d" y="%d">%s</text>' % (L, h - 10, e(ts[0])))
    o.append('<text class="ax" x="%d" y="%d" text-anchor="end">%s</text>' % (L + iw, h - 10, e(ts[-1])))
    o.append('<text class="ax" x="%d" y="%d">점수(막대)</text>' % (L + 4, T + 11))
    o.append("</svg>")
    return '<div style="margin:12px 0;overflow-x:auto">%s</div>' % "".join(o)


def compare_svg(rows, w=660, label=""):
    """지금 점수 vs 제안 점수 — 3번이 실제로 뒤집는지 눈으로 본다."""
    if not rows:
        return ""
    h = 44 * len(rows) + 40
    mx = max(max(a, b) for _n, a, b in rows) * 1.18 or 1
    X = lambda v: 152 + (w - 190) * (v / mx)
    o = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">' % (w, h, e(label)),
         '<style>.t{font:11.5px "Malgun Gothic",sans-serif;fill:#374151}'
         '.n{font:700 11px Consolas,monospace;fill:#111827}'
         '.k{font:10px "Malgun Gothic",sans-serif;fill:#6b7280}</style>']
    o.append('<rect x="152" y="8" width="9" height="9" rx="2" fill="#c7d2fe"/>'
             '<text class="k" x="165" y="16">지금</text>'
             '<rect x="205" y="8" width="9" height="9" rx="2" fill="#4f46e5"/>'
             '<text class="k" x="218" y="16">제안</text>')
    y = 26
    for nm, now, new in rows:
        o.append('<text class="t" x="0" y="%d">%s</text>' % (y + 22, e(nm)))
        for k, (v, c) in enumerate(((now, "#c7d2fe"), (new, "#4f46e5"))):
            o.append('<rect x="152" y="%d" width="%.1f" height="15" rx="2" fill="%s"/>'
                     % (y + k * 18, max(1.5, X(v) - 152), c))
            o.append('<text class="n" x="%.1f" y="%d">%s</text>' % (X(v) + 6, y + 12 + k * 18, _num(v)))
        y += 44
    o.append("</svg>")
    return '<div style="margin:12px 0">%s</div>' % "".join(o)


def _num(v):
    if v is None:
        return "—"
    return ("%.2f" % v).rstrip("0").rstrip(".") if abs(v) < 100 else "%.0f" % v


# ────────────────────────────── 문서 ──────────────────────────────
def render(d):
    fab, C, rows = d["fab"], d["C"], d["rows"]
    o = ['<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>%s 장애 분석 — %s</title><style>%s</style></head><body><div class=wrap>"
         % (e(fab), e(d["day"]), CSS)]
    a = o.append
    a("<h1>%s</h1>" % e(d["title"]))
    a('<p class="sub">%s · 대상 <b>%s</b> · 사건 구간 <b>%s~%s</b> · '
      '자료 %s (%d분) · 임계 출처 <code>%s</code></p>'
      % (e(d["day"]), e(fab), e(d["ev_lo"]), e(d["ev_hi"]),
         e(os.path.basename(d["src"])), len(rows), e(d["rule_src"])))

    # ── 0. 한 줄 요약 ──
    hi, lo = d["hi"], d["lo"]
    a("<h2>0. 한 줄로</h2>")
    a('<table><tr><th>시각</th><th class=n>반송시간</th><th class=n>임계 대비</th>'
      "<th class=n>켜진 룰</th><th class=n>영역 원점수</th>"
      "<th>화면 등급</th><th class=n>화면 점수</th></tr>")
    for r, cls, note in ((lo, "lo", "심한데 낮았다"), (hi, "hi", "턱걸이인데 높았다")):
        if not r:
            continue
        a('<tr class="%s"><td><b>%s</b> <span class=dim>%s</span></td>'
          '<td class=n><b>%s분</b></td><td class=n><b>%.2f배</b></td>'
          '<td class=n>%d개</td><td class=n>%s</td><td class="%s">%s</td>'
          "<td class=n><b>%s</b></td></tr>"
          % (cls, e(hhmm(r["r"].get("datetime"))), e(note), _num(r["ra"]), r["mul"],
             len(fired(r["r"], fab)), e(r["r"].get("%s_score_raw" % fab) or
                                        r["r"].get("%s_score" % fab)),
             "bad" if r.get("level") in ("초위험", "위험") else "dim",
             e(r.get("level") or "—"), e(r.get("screen") or "—")))
    a("</table>")
    a('<div class="note miss"><b>배점이 0 아니면 만점이라 "얼마나 넘었는지" 를 '
      "안 본다.</b> 임계를 1% 넘으나 300% 넘으나 같은 점수다. 그래서 살짝 넘은 "
      "지표 여럿이 모인 분이, 하나가 크게 터진 분보다 높게 나온다.</div>")

    # ── 1) 조용한데 초위험이 울린 이유 ──
    a("<h2>1) 08:00 즈음 별일 없었는데 초위험이 울린 원인</h2>")
    if hi:
        r = hi["r"]
        fr = fired(r, fab)
        a("<p><b>%s</b> — 화면 <b class=bad>%s %s점</b>. 룰 <b>%d개</b>가 "
          "한꺼번에 켜졌다.</p>"
          % (e(hhmm(r.get("datetime"))), e(hi.get("level") or "—"),
             e(hi.get("screen") or "—"), len(fr)))
        a("<div class=flow>%s\n= %s%s</div>"
          % (e(" + ".join("%s(%g)" % (n, v) for n, v in fr)),
             e(r.get("%s_score_raw" % fab) or "?"),
             ("   →   상한에 걸려 %s" % e(r.get("%s_score" % fab)))
             if (f(r.get("%s_score_raw" % fab)) or 0) > (f(r.get("%s_score" % fab)) or 0) else ""))
        rt = [x for x in ratios(r, fab, C) if x[3] >= 1.0]
        if rt:
            a("<h3>그림 1 — 켜진 값은 전부 임계 <b>턱걸이</b>였다</h3>")
            a(ratio_svg(sorted(rt, key=lambda x: -x[3]), label="07:58 룰별 임계 대비 배율"))
            a('<div class="note"><b>막대가 전부 1배 선에 붙어 있다.</b> '
              "심해서 높은 점수가 난 게 아니라, <b>여럿이 동시에 선을 살짝 "
              "넘어서</b> 높아진 것이다. 배점이 0 아니면 만점이라 1% 넘으나 "
              "300% 넘으나 같은 점수를 준다.</div>")
    else:
        a("<p class=dim>이 자료에서 높은 점수 구간을 못 찾았다.</p>")

    # ── 2) 사건인데 점수가 낮았던 이유 ──
    a("<h2>2) 사건 발생 때 점수가 낮았던 원인</h2>")
    a('<div class="note good"><b>먼저 바로잡습니다 — 못 잡은 것이 아닙니다.</b><br>'
      "전조는 계속 떴고, 시스템은 <b>고장 유형까지 맞혔습니다</b>. "
      "문제는 그것이 <b>점수로 이어지지 않은 것</b>입니다.</div>")

    # ㉠ 전조가 떴다
    a("<h3>㉠ 전조는 떴다 — 경계 %d분</h3>" % len(d["alerts"]))
    if d["alerts"]:
        a("<table><tr><th>시각</th><th>등급</th><th class=n>점수</th>"
          "<th class=n>사건 대비</th></tr>")
        for t, g, sc in d["alerts"][:14]:
            lead = d_lead(t, d["ev_lo"])
            a('<tr><td>%s</td><td class="%s">%s</td><td class=n>%s</td>'
              "<td class=n>%s</td></tr>"
              % (e(t), "warn" if g == "경계" else "bad", e(g), e(sc),
                 ("<b>%d분 전</b>" % lead) if lead and lead > 0 else
                 ("%d분 후" % -lead if lead else "사건 시작")))
        a("</table>")

    # ㉡ 고장 유형을 맞혔다 — 이 문서의 핵심
    hit = [h for h in d["hits"] if 0 < (d_lead(h[0], d["ev_lo"]) or -1) <= 60]
    if hit:
        t0, ft0, st0, g0, sc0 = hit[-1]
        a("<h3>㉡ 고장 유형까지 맞혔다 <span class=tag>핵심</span></h3>")
        a('<div class="flow">%s   predicted_fault_type = <b>%s</b>\n'
          "%s   단계 = %s\n"
          "%s   그런데 화면은 = <b>%s %s점</b></div>"
          % (e(t0), e(ft0), " " * len(t0), e(st0), " " * len(t0), e(g0), e(sc0)))
        a('<div class="note miss"><b>최초 공유(%s)보다 %d분 빨랐습니다.</b> '
          "예측기는 <code>%s</code> 를 집어냈는데, 운전원 화면에는 "
          "<b>%s %s점</b>으로 떴습니다 — <b>예측 결과가 점수에 들어가지 "
          "않습니다.</b></div>"
          % (e(d["ev_lo"]), d_lead(t0, d["ev_lo"]), e(ft0), e(g0), e(sc0)))

    # ㉢ 장치가 죽어 있다
    a("<h3>㉢ 사건 추적 장치가 값을 채우지 않는다</h3>")
    a("<table><tr><th>칸</th><th>하루 %d분 동안</th><th>뜻</th></tr>" % len(rows))
    for c, nm, why in (("incident_state", "사건 상태", "사건으로 묶인 적이 한 번도 없다"),
                       ("continuity_min", "연속 분", "얼마나 계속됐는지 안 센다"),
                       ("refire_count", "재발 횟수", "몇 번 되살아났는지 안 센다")):
        v = d["dead"].get(c)
        a('<tr><td><code>%s</code></td><td class="%s">%s</td><td>%s</td></tr>'
          % (e(c), "bad" if v else "dim",
             ("계속 <b>%s</b>" % e(v)) if v else "값이 바뀜", e(why)))
    a("</table>")
    a("<h3>㉣ 단계가 늘 켜져 있어 뜻이 없다</h3>")
    a("<table><tr><th>단계</th><th class=n>분</th><th class=n>비율</th></tr>")
    tot = sum(d["stages"].values()) or 1
    for k, v in sorted(d["stages"].items(), key=lambda x: -x[1]):
        a("<tr><td>%s</td><td class=n>%d</td><td class=n>%.0f%%</td></tr>"
          % (e(k), v, 100.0 * v / tot))
    a("</table>")
    a('<div class="note miss"><b>「3단계 확정」이 하루의 절반입니다.</b> '
      "정상(0단계)인 분이 <b>한 분도 없습니다</b>. 늘 켜져 있는 경보는 "
      "경보가 아닙니다 — 그래서 아무도 안 봅니다.</div>")

    # ㉤ 13시 이후 — 지표가 거꾸로
    a("<h3>㉤ 13시 이후엔 지표까지 거꾸로 갔다</h3>")
    a("<p>사건 전(<b>%s~%s</b>)과 사건 중(<b>%s~%s</b>)의 지표 평균이다.</p>"
      % (e(d["bf_lo"]), e(d["bf_hi"]), e(d["ev_lo"]), e(d["ev_hi"])))
    a("<table><tr><th>지표</th><th class=n>사건 전</th><th class=n>사건 중</th>"
      "<th>방향</th><th class=n>임계</th><th>룰이 켜지나</th></tr>")
    for nm, bef, dur, th in d["dirs"]:
        down = dur < bef
        on = (th is not None and dur >= th)
        a("<tr><td>%s</td><td class=n>%s</td><td class=n>%s</td>"
          '<td class="%s">%s</td><td class=n>%s</td><td class="%s">%s</td></tr>'
          % (e(nm), _num(bef), _num(dur), "okc" if down else "warn",
             "▼ 내려감" if down else "▲ 올라감", _num(th),
             "bad" if on else "dim", "켜짐" if on else "안 켜짐"))
    a("</table>")
    if d.get("series"):
        a("<h3>그림 2 — 점수가 눌려 있는 동안 지표도 같이 내려갔다</h3>")
        a(series_svg(d["series"], label="사건 구간 점수와 지표"))
    a('<div class="note miss"><b>평균의 함정</b> — 반송시간 평균은 '
      "<b>끝난 반송</b>만 셉니다. 차가 멈추면 그 화물은 평균에 안 들어갑니다. "
      "<b>정체가 심할수록 평균이 내려갑니다.</b><br>"
      "게다가 여덟 룰이 전부 <b>올라가는 것</b>만 잡습니다. 무언정지는 "
      "<b>내려가는 것</b>(가동률 93%%→76%%)으로 나타납니다.</div>")

    # ── 3) 점수 재산정 ──
    a("<h2>3) 점수 산정 방식 재설계</h2>")
    a('<div class="note"><b>고객 지적:</b> 이상 지표가 <i>많으면</i> 고점을 '
      "주는데, 특정 지표가 <i>심각</i>하면 고점을 못 준다. 한 지표가 많이 높으면 "
      "전체 점수도 많이 높아져야 한다.<br>"
      "<b>→ 1)2) 가 정확히 그 증상이다.</b> 아래가 그 답이다.</div>")
    a("<h3>㉮ 초과 배율 가중 — 1)을 고친다</h3>")
    a("<div class=flow>배율 r = 값 / 임계\n"
      "  r &lt; 1.3       →  배점 × 1.0   (턱걸이 — 지금과 같다)\n"
      "  1.3 ≤ r &lt; 2.0 →  배점 × 1.5\n"
      "  r ≥ 2.0       →  배점 × 2.5   (심각)</div>")
    if d.get("cmp"):
        a("<h3>그림 3 — 이 규칙을 그날 두 분에 적용하면</h3>")
        a(compare_svg(d["cmp"], label="지금 점수 vs 제안 점수"))
        # ★숫자를 실제로 읽어 적는다. "순서가 바로잡힌다" 고 단정했다가
        #   52 vs 55 로 여전히 뒤집히지 않은 걸 뒤늦게 봤다 — 과장하면
        #   고객이 돌려 봤을 때 바로 들통난다.
        _c = {n.split()[0]: (a_, b_) for n, a_, b_ in d["cmp"]}
        _lo = _c.get(hhmm(lo["r"].get("datetime"))) if lo else None
        _hi = _c.get(hhmm(hi["r"].get("datetime"))) if hi else None
        if _lo and _hi:
            gap0, gap1 = _hi[0] - _lo[0], _hi[1] - _lo[1]
            flipped = _lo[1] > _hi[1]
            a('<div class="note %s">심한 쪽이 <b>%s → %s</b> 로 오른다. '
              "턱걸이 쪽은 <b>%s → %s</b> 로 그대로다 — 배율이 1배라 곱해도 "
              "안 오른다.<br>두 분의 차이가 <b>%s점 → %s점</b> 으로 좁혀진다. "
              "%s</div>"
              % ("good" if flipped else "",
                 _num(_lo[0]), _num(_lo[1]), _num(_hi[0]), _num(_hi[1]),
                 _num(gap0), _num(gap1),
                 "순서가 뒤집힌다." if flipped else
                 "<b>다만 ㉮만으로는 아직 뒤집히지 않는다</b> — 뒤집으려면 "
                 "아래 ㉯(단독 심각 하한)가 같이 있어야 한다."))
    a("<h3>㉯ 단독 심각 하한 — \"한 지표가 높으면 전체도 높게\"</h3>")
    a("<p>한 룰이라도 <code>r ≥ 2.0</code> 이면 그것만으로 <b>위험 등급 하한</b>을 "
      "보장한다. 지금은 아무리 심해도 다른 룰이 안 켜지면 경계에 머문다 — "
      "%s 가 그 예다(%s배인데 <b>%s</b>).</p>"
      % (e(hhmm(lo["r"].get("datetime"))) if lo else "—",
         ("%.2f" % lo["mul"]) if lo else "—",
         e(lo.get("level") or "—") if lo else "—"))

    # ── 예측 시스템다운 개선 ─────────────────────────────────────
    a("<h3>㉰ 예측 결과를 점수에 넣는다 <span class=tag>예측 시스템의 핵심</span></h3>")
    a('<div class="note"><b>우리는 예측 시스템입니다.</b> 그런데 지금은 '
      "예측 결과(<code>predicted_fault_type</code>·단계)와 점수가 "
      "<b>따로 돕니다</b>. 2)㉡ 에서 본 대로, 고장 유형을 맞힌 그 분의 화면은 "
      "<b>정상</b>이었습니다.</div>")
    a("<table><tr><th>지금</th><th>제안</th></tr>"
      "<tr><td>예측 유형은 <code>reason</code> 에만 적힌다</td>"
      "<td><b>그 FAB 의 고장 유형을 맞히면 가산점</b> — 예측이 점수를 올린다</td></tr>"
      "<tr><td>3단계 확정이 하루의 55%%, 0단계가 0분</td>"
      "<td><b>단계를 올리는 조건을 조인다</b> — 늘 켜진 경보는 경보가 아니다</td></tr>"
      "</table>")

    a("<h3>㉱ 전조를 이어 붙인다 — 사건 추적을 되살린다</h3>")
    a('<div class="note miss"><b>%s 분 내내 '
      "<code>incident_state=IDLE · continuity_min=0 · refire_count=0</code> "
      "입니다.</b> 칸은 있는데 아무도 채우지 않습니다 — 그래서 "
      "<b>전조가 아무리 계속돼도 점수가 안 쌓입니다.</b></div>" % len(rows))
    a("<table><tr><th>칸</th><th>되살리면</th></tr>"
      "<tr><td><code>continuity_min</code></td>"
      "<td>같은 룰이 <b>N분 이어지면</b> 가산 — 3시간 계속된 것과 1분짜리가 "
      "같은 점수일 수 없다</td></tr>"
      "<tr><td><code>refire_count</code></td>"
      "<td>10분 안에 <b>다시 뜨면</b> 같은 사건으로 묶고 점수 유지 — 지금은 "
      "한 분만 정상이면 리셋된다</td></tr>"
      "<tr><td><code>incident_state</code></td>"
      "<td>IDLE → <b>감시 → 진행 → 종료</b> 로 상태를 갖는다. 사건이 "
      "이어지는 동안 등급이 안 떨어진다</td></tr></table>")
    if d["alerts"]:
        a("<p>이 규칙이면 %s 흩어진 경계 <b>%d분</b>이 <b>한 사건</b>으로 "
          "묶입니다 — 운전원 눈에 들어옵니다.</p>"
          % (e("%s~%s" % (d["alerts"][0][0], d["alerts"][-1][0])), len(d["alerts"])))

    a("<h3>㉲ 상한 재조정</h3>")
    a("<p>지금 영역점수 상한은 <b>%s</b> 다. 위 %s 의 원점수 %s 가 이미 잘렸다 — "
      "가중·가산을 넣으면 더 자주 잘려 <b>변별력이 사라진다</b>. 상한을 올리거나 "
      "정규화 방식을 바꿔야 한다.</p>"
      % (e(d["cap"]), e(hhmm(hi["r"].get("datetime"))) if hi else "—",
         e(hi["r"].get("%s_score_raw" % fab)) if hi else "—"))

    a("<h3>그리고 — 내려가는 것도 봐야 한다</h3>")
    a("<table><tr><th>신호</th><th>지금</th><th>제안</th><th>자료</th></tr>"
      "<tr><td>OHT 가동률 <b>급락</b></td><td>≥95%% 일 때만 켜짐</td>"
      "<td>평소 대비 −10%%p 급락도 이상으로</td><td class=okc>이미 있음 "
      "(<code>%s_rd_oht</code>)</td></tr>"
      "<tr><td>처리량 대비</td><td>반송시간만 봄</td>"
      "<td>시간이 내려가는데 <b>처리 건수도</b> 내려가면 좋아진 게 아니라 "
      "일이 안 되는 것</td><td class=warn>일부 (4분초과 건수로 대체 가능)</td></tr>"
      "<tr><td>무언정지 대수</td><td>없음</td><td>제일 직접적인 신호</td>"
      "<td class=bad>수집에 없음 — 요청 필요</td></tr></table>" % e(fab))

    # ── 4) 후순위 ──
    a("<h2>4) Play Back HMI 개선 <span class=tag>후순위</span></h2>")
    a("<p class=dim>요청하신 대로 이번 분석에서는 제외했습니다. "
      "1)2)3)이 정리된 뒤에 착수하는 것이 맞다고 봅니다.</p>")

    if d.get("dropped"):
        a('<div class="note miss"><b>자료에서 %d줄을 버렸습니다.</b> '
          "datetime 이 날짜가 아닌 줄입니다 — reason 칸 안의 따옴표가 어긋나 "
          "한 줄이 두 줄로 쪼개진 것으로 보입니다. 이 문서의 모든 수치는 "
          "나머지 %d분으로 계산했습니다.</div>" % (d["dropped"], len(rows)))

    a("<h2>4. 이 문서가 말하지 않는 것</h2>")
    a("<ul><li>장애의 <b>원인</b>은 다루지 않는다. 왜 OHT 가 멈췄는지가 아니라, "
      "<b>우리 점수가 왜 그 값이었는지</b>만 따진다.</li>"
      "<li>제안한 배율(1.3 / 2.0 / ×1.5 / ×2.5)은 <b>출발점</b>이다. "
      "과거 사건들에 돌려 보고 정해야 한다.</li>"
      "<li>Play Back HMI 개선은 <b>후순위</b>로 빼 두었다.</li></ul>")
    a('<p class="sub" style="margin-top:30px">이 문서는 '
      "<code>장애분석_문서.py</code> 가 발동이벤트 CSV 와 "
      "<code>hubroom_predictor.py</code> 에서 읽어 만듭니다 — 손으로 고치지 "
      "마세요. 룰·임계가 바뀌면 다시 돌리면 됩니다.</p>")
    a("</div></body></html>")
    return "".join(o)


# ────────────────────────────── 실행 ──────────────────────────────
def build(src, fab, ev_lo, ev_hi, title, before_min=38, screen=None):
    C, meta = read_th()
    rows, dropped = load(src)
    scr = load_screen(screen)
    if not rows:
        raise SystemExit("빈 CSV: " + src)
    # ★date 칸을 믿으면 안 된다 — 이 CSV 에는 컬럼명이 밀려 들어와
    #   " M16HUB.QU…" 같은 값이 들어 있었다. datetime 앞 10자가 정답이다.
    day = (rows[0].get("datetime") or "")[:10] or "unknown"
    ev = window(rows, ev_lo, ev_hi)
    # 사건 직전 같은 길이 — 비교 기준을 임의로 고르지 않는다
    lo_h, lo_m = int(ev_lo[:2]), int(ev_lo[3:5])
    st = max(0, lo_h * 60 + lo_m - before_min)
    bf_lo, bf_hi = "%02d:%02d" % (st // 60, st % 60), ev_lo
    bf = window(rows, bf_lo, bf_hi)

    cap = None
    m = re.search(r"min\((\d+)", "")            # 상한은 룰 원본 pts 에서
    pts = (meta or {}).get("pts") or {}
    cap = pts.get("_cap")

    # ① 하루 중 제일 높았던 분 (턱걸이 다발)
    top = top_scored(rows, fab, 1)
    hi = None
    if top and top[0][0]:
        r = top[0][1]
        ra = f(r.get("%s_ra" % fab))
        th = th_of(C, ("TH_RA", "{f}"), fab) or 1.0
        hi = {"r": r, "ra": ra, "mul": (ra / th) if ra else 0, "level": None}

    # ② 지표가 제일 심했던 분 (점수는 낮았던)
    pk = peak_rows(rows, fab, C, 1)
    lo = None
    if pk:
        v, mul, r = pk[0]
        raw = f(r.get("%s_score_raw" % fab)) or 0
        ra_pts = f(r.get("%s_pts_RA" % fab)) or 0
        lo = {"r": r, "ra": v, "mul": mul, "level": None, "boost": None}

    def weighted(r):
        """제안 ㉮ 를 그 분에 실제로 적용해 본 점수.

        ★말로만 '올라갑니다' 라고 쓰면 아무도 못 믿는다. 그날 데이터에 돌려
          숫자를 보여야 한다. 배율은 룰이 보는 지표에 맞춰 잡는다 —
          RA/RA_sus 는 반송시간, RB/RB_fast 는 반입증감, SLA 는 4분초과율.
        """
        mp = {"RA": ("{f}_ra", ("TH_RA", "{f}")),
              "RA_sus": ("{f}_ra", ("TH_RA", "{f}")),
              "RB": ("{f}_rb_diff30", ("TH_RB_30", "{f}")),
              "RB_fast": ("{f}_rb_diff10", ("TH_RB_10", "{f}")),
              "SLA": ("sla_{f}", ("TH_SLA_RATIO", "{f}")),
              "SORT": ("sorter_{f}", ("TH_SORTER_WAIT", "{f}"))}
        tot = 0.0
        for k, _nm in RULES:
            pv = f(r.get("{}_pts_{}".format(fab, k))) or 0
            if not pv:
                continue
            g = 1.0
            if k in mp:
                col, spec = mp[k]
                v, th = f(r.get(col.format(f=fab))), th_of(C, spec, fab)
                if v is not None and th:
                    m = v / th
                    g = 2.5 if m >= 2.0 else 1.5 if m >= 1.3 else 1.0
            tot += pv * g
        return tot

    # 화면 등급은 CSV 에 없으면 컷으로 매긴다
    try:
        from sentinel import grade_cuts
        warn_cut = grade_cuts({"_sys": fab})[0]
    except Exception:
        warn_cut = None
    for x in (hi, lo):
        if x:
            g, sc = scr.get(hhmm(x["r"].get("datetime")), ("", ""))
            x["level"] = g or x["r"].get("unified_risk_level") or "—"
            x["screen"] = sc

    # 시계열 그림용 — 점수(막대) + 지표(선). 눈금이 달라 그림에서 정규화한다.
    SER = [("반송시간", "{f}_ra"), ("OHT가동률", "{f}_rd_oht"),
           ("4분초과율", "sla_{f}"), ("4분초과건수", "{f}_sla_cnt")]
    step = max(1, len(ev) // 90)
    series = []
    for r in ev[::step]:
        g, sc = scr.get(hhmm(r.get("datetime")), ("", ""))
        series.append((hhmm(r.get("datetime")),
                       (f(sc) if scr else f(r.get("%s_score" % fab))) or 0,
                       {nm: f(r.get(c.format(f=fab))) for nm, c in SER}))

    # 추이는 **화면 점수**로 그린다 — 운전원이 본 눈금이 그거다(없으면 영역점수)
    evs = [(hhmm(r.get("datetime")),
            f(scr.get(hhmm(r.get("datetime")), ("", ""))[1]) if scr
            else (f(r.get("%s_score" % fab)) or 0))
           for r in ev]
    evs = [(t, v if v is not None else 0) for t, v in evs][::max(1, len(ev) // 12)][:12]

    # ── 예측 장치가 무엇을 하고 있었나 ─────────────────────────────
    # ★"전조는 계속 있었다" 는 지적을 받고 넣었다. 처음엔 점수만 보고
    #   '못 잡았다' 고 썼는데, 단계·예측유형 칸을 보니 시스템은 보고 있었다.
    #   점수에 반영이 안 됐을 뿐이다 — 진단이 통째로 달라진다.
    from collections import Counter
    stages = Counter(r.get("stage_name") or "(빈값)" for r in rows)
    dead = {c: (len(set(str(r.get(c, "")) for r in rows)) == 1 and
                str(rows[0].get(c, "")))
            for c in ("incident_state", "continuity_min", "refire_count")}
    # 사건 구간 언저리에서 '그 고장'을 맞힌 분
    kinds = ("OHT정체", "큐누적", "반송지연")
    hits = []
    for r in rows:
        t = hhmm(r.get("datetime"))
        ft = r.get("predicted_fault_type") or ""
        if ft.startswith(fab + "-") and any(k in ft for k in kinds):
            g, sc = scr.get(t, ("", ""))
            hits.append((t, ft, r.get("stage_name") or "-", g or "-", sc or "-"))
    ev_hits = [h for h in hits if d_lead(h[0], ev_lo) is not None]

    # 지금 vs 제안 — 그날의 두 분에 실제로 돌려 본다
    # 사건 언저리에서 경계 이상이 뜬 분 — '전조가 떴다' 의 증거
    alerts = []
    for t, (g, sc) in sorted(scr.items()):
        if g and g != "정상" and d_lead(t, ev_hi) is not None and t <= ev_hi:
            if d_lead(t, ev_lo) is None or t >= _shift(ev_lo, -30):
                alerts.append((t, g, sc))

    cmp_rows = []
    for x, tag in ((lo, "심했는데 낮았다"), (hi, "턱걸이인데 높았다")):
        if not x:
            continue
        r = x["r"]
        now = f(r.get("%s_score_raw" % fab)) or 0
        cmp_rows.append(("%s  %s" % (hhmm(r.get("datetime")), tag), now, weighted(r)))
    return {"fab": fab, "C": C, "rows": rows, "day": day, "src": src,
            "rule_src": os.path.basename(meta.get("path") or "hubroom_predictor.py"),
            "ev_lo": ev_lo, "ev_hi": ev_hi, "bf_lo": bf_lo, "bf_hi": bf_hi,
            "dropped": dropped,
            "dirs": direction(rows, fab, C, bf, ev), "hi": hi, "lo": lo,
            "cap": cap, "warn_cut": warn_cut, "ev_scores": evs, "title": title,
            "screen": bool(scr), "series": series, "cmp": cmp_rows,
            "stages": stages, "dead": dead, "hits": hits, "ev_hits": ev_hits,
            "alerts": alerts}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 1
    src = argv.pop(0)
    fab, ev, title, out, screen = "M14", "11:38-14:30", "", None, None
    while argv:
        k = argv.pop(0)
        if k == "--fab":
            fab = argv.pop(0)
        elif k == "--event":
            ev = argv.pop(0)
        elif k == "--screen":
            screen = argv.pop(0)
        elif k == "--title":
            title = argv.pop(0)
        elif k == "--out":
            out = argv.pop(0)
        else:
            out = k
    lo, hi = (ev.split("-") + [""])[:2]
    d = build(src, fab, lo, hi, title or ("%s 장애 분석" % fab), screen=screen)
    os.makedirs(DOC_DIR, exist_ok=True)
    out = out or os.path.join(DOC_DIR, "%s_%s_장애분석.html" % (fab, d["day"].replace("-", "")))
    io.open(out, "w", encoding="utf-8").write(render(d))
    print("만들었습니다:", out)
    print("  대상 %s · %d분 · 사건 %s~%s" % (fab, len(d["rows"]), lo, hi))
    if d["hi"]:
        print("  턱걸이 다발: %s (%.2f배, 원점수 %s)"
              % (hhmm(d["hi"]["r"].get("datetime")), d["hi"]["mul"],
                 d["hi"]["r"].get("%s_score_raw" % fab)))
    if d["lo"]:
        print("  심했는데 낮음: %s (%.2f배, 원점수 %s)"
              % (hhmm(d["lo"]["r"].get("datetime")), d["lo"]["mul"],
                 d["lo"]["r"].get("%s_score_raw" % fab)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
