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


# ── 2026-09-21 변경내역서(고객이 준 "M16A·M16B 헛울림 수정 + PIO 1분값 가산")
#    에서 그대로 옮긴 값. ★지어낸 값이 아니다 — 우리가 잰 것은 점수뿐이고,
#    '무엇을 바꿨나' 는 고객 문서가 근거다. 문서에 옮겨 적을 때 출처를 밝힌다.
#    PIO 점수 = min(FAB 상한, 10분구간표 점수 + 1분구간표 점수)
#    배점은 다섯 구간 모두 1·3·5·8·10 순 (M16B 만 1·3·5 · 상한 5)
PIO_PTS = (1, 3, 5, 8, 10)
PIO_1MIN = {
    "M16HUB": {"b10": (13, 30, 54, 73, 140), "b1": (8, 14, 17, 26, 31), "cap": 10},
    "M14":    {"b10": (30, 42, 56, 66, 84),  "b1": (8, 12, 13, 15, 17), "cap": 10},
    "M14B":   {"b10": (12, 22, 36, 50, 90),  "b1": (6, 10, 12, 18, 20), "cap": 10},
    "M16A":   {"b10": (17, 38, 78, 108, 166), "b1": (12, 20, 23, 38, 45), "cap": 10},
    "M16B":   {"b10": (1, 1, 2, 3, 4),       "b1": (1, 2, 3),           "cap": 5},
}
# 새로 생기는 컬럼 (발동이벤트 146→151칸 · fab분리 PIO 3→4칸)
PIO_NEWCOL = ("{FAB}_PIO_WSUM1", "area_pio_wsum1")
# ★이 두 FAB 은 이번에 **임계를 하나도 안 바꿨다** (변경내역서: "M16HUB ·
#   M14 · M14B 임계는 하나도 안 바꿨습니다"). 임계를 바꾼 것은 M16A·M16B 다.
PIO_TH_UNTOUCHED = ("M16HUB", "M14", "M14B")


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
        if src and "변경전" in src and "변경후" in src:   # 다리 이름이 든 셀만
            out.append(src)
    return out


def legname(h: str) -> str:
    """컬럼 이름 → 짧은 다리 이름. 문서의 칸 제목이 되므로 짧아야 한다."""
    if "변경전" in h:
        return "변경 전"
    if "변경후" in h:
        return "변경 후"
    if "1분" in h or "cnt" in h.lower():
        return "+1분 cnt"
    return "그 외"


def parse(src: str) -> dict | None:
    """한 셀 → {fab, label, legs, rows:[(t, v1, v2[, v3])]}.

    모양 두 가지를 다 읽는다 — 받은 자료가 두 번에 걸쳐 모양이 달라졌다.
      ① datetime, 변경전, datetime, 변경후                  (2026-09-18 자료)
      ② datetime, 변경전, 변경후, 추가(1분cnt추가)          (2026-09-21 자료)
    ①은 시각 열이 둘이라 **어긋나면 비교 자체가 무의미하다** — 그 행은 버리고
    센다. ②는 시각 열이 하나뿐이라 어긋날 수가 없다.
    ★②를 ①의 규칙으로 읽으면 r[2] 가 숫자라 전부 버려지고 한 행도 안 남는다.
      (조용히 틀린 숫자가 나오는 게 아니라 아예 안 나온다 — 그래서 알아챈다.)
    """
    rows = list(csv.reader(io.StringIO(src)))
    if not rows or len(rows[0]) < 3:
        return None
    hdr = [h.strip() for h in rows[0]]
    m = re.search(r"변경전_(.+?)_area_score", hdr[1])
    fab = (m.group(1) if m else "?").upper()
    label = hdr[1].split("_변경전")[0]
    paired = len(hdr) >= 4 and hdr[2].lower().startswith("datetime")
    if paired:
        cols, legs = [1, 3], ["변경 전", "변경 후"]
    else:
        cols = list(range(1, len(hdr)))
        legs = [legname(hdr[i]) for i in cols]
    out, skew = [], 0
    for r in rows[1:]:
        if len(r) <= cols[-1] or not r[0].strip():
            continue
        try:
            t = datetime.strptime(r[0].strip(), "%Y-%m-%d %H:%M")
            if paired and datetime.strptime(r[2].strip(), "%Y-%m-%d %H:%M") != t:
                skew += 1
                continue
            vals = [float(r[i]) for i in cols]
        except ValueError:
            continue
        out.append(tuple([t] + vals))
    return ({"fab": fab, "label": label, "legs": legs, "rows": out, "skew": skew}
            if out else None)


# ────────────────────────────── 세기 ──────────────────────────────
def stats(rows, cuts=None, pair=(1, 2)) -> dict:
    """두 다리를 견준다. pair 는 열 번호 (1=첫 다리). 기본은 전 → 후.

    ★자료에 다리가 셋이 되면서(전 · 후 · +1분 cnt) '어느 둘' 인지를 밝혀야
      한다. 기본값을 (1,2) 로 둬서 예전 부르던 자리는 그대로 돈다.
    """
    c = cuts or CUTS
    i, j = pair
    ch = [(r[0], r[i], r[j]) for r in rows if r[i] != r[j]]
    dif = [a - b for _, b, a in ch]
    cnt = {k: [0, 0] for k in LEVELS}
    for r in rows:
        cnt[level(r[i], c)][0] += 1
        cnt[level(r[j], c)][1] += 1
    moved = {}
    for r in rows:
        lb, la = level(r[i], c), level(r[j], c)
        if lb != la:
            moved[(lb, la)] = moved.get((lb, la), 0) + 1
    days = {}
    for r in rows:
        b, a = r[i], r[j]
        d = days.setdefault(r[0].date(), {"n": 0, "ch": 0, "wb": 0, "wa": 0,
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
        "hi_b": max((r[i] for r in rows), default=0.0),
        "hi_a": max((r[j] for r in rows), default=0.0),
        "changed": ch,
    }


def promote(rows, cuts, pair=(1, 2)) -> dict:
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
    i, j = pair

    def one(k):
        w = sum(1 for r in rows if cuts[0] <= r[k] < cuts[1])
        d = sum(1 for r in rows if r[k] >= cuts[1])
        return {"warn": w, "danger": d, "any": w + d,
                "share": (100.0 * w / (w + d)) if (w + d) else 0.0}
    up = [(r[0], r[i], r[j]) for r in rows if cuts[0] <= r[i] < cuts[1] <= r[j]]
    # ★내려간 쪽도 같이 센다 — 위험이던 분이 내려가면 그건 잃은 것이다.
    lost = [(r[0], r[i], r[j]) for r in rows if r[j] < cuts[1] <= r[i]]
    near = [r[j] for r in rows if cuts[0] <= r[j] < cuts[1]]
    return {"before": one(i), "after": one(j), "up": up, "lost": lost,
            "near5": sum(1 for a in near if cuts[1] - a <= 5),
            "near10": sum(1 for a in near if cuts[1] - a <= 10)}



# ────────────────────────────── 그림 ──────────────────────────────
CIRC = "①②③④⑤⑥"
# 다리별 선 색. ★면(위험 이상)은 **모든 칸에서 같은 빨강**으로 칠한다 —
#   칸끼리 '빨간 면이 얼마나 늘었나' 를 눈으로 견주는 것이 이 그림의 일이다.
#   (다리가 둘일 때만 옛 색을 그대로 둔다. 붙어 있는 문서가 그 색이다.)
LEG_LINE = ("#9ca3af", "#6b7280", "#4f46e5", "#047857")
HOT = "#b91c1c"


def chart(rows, cuts, day, events=(), legs=None) -> str:
    """하루치 — 다리마다 칸을 따로 내고, 맨 아래에 **차이** 칸을 붙인다.

    ★고객: "그래프 변경전후 보이지도 않는데 어디가 올랐는지도 모르겠어.
            따로따로 비교해서 그려야지, 한 그래프에 전부 다 그리면 어떻게 알아."
      맞다. 곡선들은 대부분 겹쳐 있어서 한 칸에 포개면 뒤 선이 앞 선을 덮는다.
      칸을 나눠 **같은 자(0~100)·같은 시간축**으로 세로로 쌓는다 —
      위아래를 눈으로 훑으면 어디가 달라졌는지가 바로 보인다.
        다리 둘: ① 변경 전 ② 변경 후 ③ 차이(후 − 전)
        다리 셋: ① 변경 전 ② 변경 후 ③ +1분 cnt ④ 차이(+1분 cnt − 변경 후)
    ★칸마다 등급 컷을 같이 그리고, 컷을 넘은 구간은 면을 칠한다 —
      '점수가 얼마다' 가 아니라 '화면이 무슨 색이었나' 가 우리가 보는 것이다.
    ★차이 칸은 0 선을 가운데 두고 **오른 쪽 위 · 내린 쪽 아래**로 그린다.
      1분 cnt 가 들어오면서 한가한 분의 점수가 내려갔다 — 내려간 것도 잰 값이다.
    """
    d = [r for r in rows if r[0].strftime("%Y-%m-%d") == day]
    if not d:
        return ""
    legs = list(legs or ["변경 전", "변경 후"])
    n = len(legs)
    two = (n == 2)
    W = 920
    PH = 112
    DH = 56 if two else 76                # 차이 칸 — 셋이면 아래로도 그린다
    L, R, T, GAP = 40, 12, 14, 26
    H = T + (PH + GAP) * n + DH + 22
    iw = W - L - R
    top = 100.0
    x = lambda i: L + iw * i / max(1, len(d) - 1)
    idx = {r[0].strftime("%H:%M"): i for i, r in enumerate(d)}

    a = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'aria-label="{esc(day)} {esc(" · ".join(legs))} 따로 보기">'
         '<style>.gx{stroke:#e5e7eb;stroke-width:1}'
         '.cut{stroke-dasharray:4 3;stroke-width:1}'
         '.lb{font:9.5px Consolas,monospace;fill:#9ca3af}'
         '.ct{font:9px "Malgun Gothic",sans-serif}'
         '.pn{font:11px "Malgun Gothic",sans-serif;font-weight:700;fill:#374151}'
         '.ev{fill:#111827;opacity:.05}'
         '.evt{font:9px "Malgun Gothic",sans-serif;fill:#6b7280}</style>']

    def panel(y0, key, name, col, fill):
        """점수 칸 하나 — 곡선 + 컷 + 위험 이상 면 칠하기."""
        y = lambda v: y0 + PH * (1 - min(v, top) / top)
        a.append(f'<text class=pn x="{L}" y="{y0-4:.0f}">{name}</text>')
        for e in events:                                  # 사건 띠
            i0, i1 = idx.get(e["from"]), idx.get(e["to"])
            if i0 is None or i1 is None:
                continue
            a.append(f'<rect class=ev x="{x(i0):.1f}" y="{y0}" '
                     f'width="{max(1, x(i1)-x(i0)):.1f}" height="{PH}"/>')
            if key == 1:
                a.append(f'<text class=evt x="{x(i0)+3:.1f}" y="{y0+10}">'
                         f'{esc(e["what"])}</text>')
        for v in (0, 50, 100):                            # 가로 눈금
            a.append(f'<line class=gx x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}"/>'
                     f'<text class=lb x="2" y="{y(v)+3:.1f}">{v}</text>')
        for v, nm, cc in ((cuts[0], "경계", "#b45309"), (cuts[1], "위험", "#b91c1c"),
                          (cuts[2], "초위험", "#7f1d1d")):
            a.append(f'<line class=cut x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}" '
                     f'stroke="{cc}"/>'
                     f'<text class=ct x="{W-R-2}" y="{y(v)-2:.1f}" text-anchor="end" '
                     f'fill="{cc}">{nm} {v}</text>')
        # ★위험 이상인 분은 바닥에서 위험선까지 면을 칠한다 — 눈에 제일 먼저 든다
        hot = [i for i, r in enumerate(d) if r[key] >= cuts[1]]
        if hot:
            a.append('<g fill="%s" opacity=".9">' % fill)
            for i in hot:
                a.append(f'<rect x="{x(i)-0.9:.1f}" y="{y(d[i][key]):.1f}" width="2.2" '
                         f'height="{max(1, y(cuts[1])-y(d[i][key])):.1f}"/>')
            a.append('</g>')
        pts = " ".join(f"{x(i):.1f},{y(r[key]):.1f}" for i, r in enumerate(d))
        a.append(f'<polyline fill="none" stroke="{col}" stroke-width="1.2" '
                 f'stroke-linejoin="round" points="{pts}"/>')
        for hh in range(0, 24, 3):
            i = idx.get(f"{hh:02d}:00")
            if i is not None:
                a.append(f'<line class=gx x1="{x(i):.1f}" y1="{y0}" '
                         f'x2="{x(i):.1f}" y2="{y0+PH}"/>')

    for k in range(n):
        key = k + 1
        nk = sum(1 for r in d if r[key] >= cuts[1])
        # 다리가 둘일 때는 예전 색 그대로 (붙어 있는 문서가 그 색이다)
        if two:
            col, fill = ("#6b7280", "#9ca3af") if k == 0 else ("#4f46e5", HOT)
        else:
            col, fill = LEG_LINE[min(k, len(LEG_LINE) - 1)], HOT
        panel(T + (PH + GAP) * k, key,
              f"{CIRC[k]} {legs[k]} — 위험 이상 {nk}분", col, fill)

    # ── 마지막 칸 — 차이 ──────────────────────────────────────────
    dy0 = T + (PH + GAP) * n
    i0, i1 = n - 1, n                      # 바로 앞 다리 → 마지막 다리
    dif = [r[i1] - r[i0] for r in d]
    nup = sum(1 for v in dif if v > 0)
    ndn = sum(1 for v in dif if v < 0)
    ncr = sum(1 for r in d if r[i0] < cuts[1] <= r[i1])
    nlo = sum(1 for r in d if r[i1] < cuts[1] <= r[i0])
    dname = ("③ 차이(후 − 전)" if two
             else f"{CIRC[n]} 차이({legs[-1]} − {legs[-2]})")
    head = (f"{dname} — 오른 분 {nup}" if two
            else f"{dname} — 오른 분 {nup} · 내린 분 {ndn}")
    a.append(f'<text class=pn x="{L}" y="{dy0-4:.0f}">{esc(head)}</text>')
    if two:
        mx = max(dif) if any(dif) else 1
        zero = dy0 + DH
        a.append(f'<line class=gx x1="{L}" y1="{zero:.0f}" x2="{W-R}" y2="{zero:.0f}"/>'
                 f'<text class=lb x="2" y="{zero+3:.0f}">0</text>'
                 f'<text class=lb x="2" y="{dy0+8:.0f}">+{mx:.0f}</text>')
        a.append('<g fill="#f59e0b">')
        for i, v in enumerate(dif):
            if v:
                h = max(2.0, DH * v / mx)
                a.append(f'<rect x="{x(i)-0.7:.1f}" y="{zero-h:.1f}" width="1.8" '
                         f'height="{h:.1f}"/>')
        a.append('</g>')
        for i, r in enumerate(d):
            if r[i0] < cuts[1] <= r[i1]:
                a.append(f'<rect x="{x(i)-1.1:.1f}" y="{dy0}" width="2.6" '
                         f'height="{DH}" fill="{HOT}"/>')
    else:
        mx = max((abs(v) for v in dif), default=1) or 1
        half = DH / 2.0
        zero = dy0 + half
        a.append(f'<line class=gx x1="{L}" y1="{zero:.1f}" x2="{W-R}" y2="{zero:.1f}"/>'
                 f'<text class=lb x="2" y="{zero+3:.1f}">0</text>'
                 f'<text class=lb x="2" y="{dy0+8:.0f}">+{mx:.0f}</text>'
                 f'<text class=lb x="2" y="{dy0+DH:.0f}">−{mx:.0f}</text>')
        a.append('<g fill="#f59e0b">')                       # 오른 쪽 — 위로
        for i, v in enumerate(dif):
            if v > 0:
                h = max(1.5, half * v / mx)
                a.append(f'<rect x="{x(i)-0.7:.1f}" y="{zero-h:.1f}" width="1.8" '
                         f'height="{h:.1f}"/>')
        a.append('</g><g fill="#0ea5e9" opacity=".75">')     # 내린 쪽 — 아래로
        for i, v in enumerate(dif):
            if v < 0:
                h = max(1.5, half * (-v) / mx)
                a.append(f'<rect x="{x(i)-0.7:.1f}" y="{zero:.1f}" width="1.8" '
                         f'height="{h:.1f}"/>')
        a.append('</g>')
        for i, r in enumerate(d):                            # 등급을 넘나든 자리
            if r[i0] < cuts[1] <= r[i1]:
                a.append(f'<rect x="{x(i)-1.1:.1f}" y="{dy0}" width="2.6" '
                         f'height="{half:.1f}" fill="{HOT}"/>')
            elif r[i1] < cuts[1] <= r[i0]:
                a.append(f'<rect x="{x(i)-1.1:.1f}" y="{zero:.1f}" width="2.6" '
                         f'height="{half:.1f}" fill="#1d4ed8"/>')
    for hh in range(0, 24, 3):
        i = idx.get(f"{hh:02d}:00")
        if i is not None:
            a.append(f'<text class=lb x="{x(i):.1f}" y="{H-6}" text-anchor="middle">'
                     f'{hh:02d}</text>')
    a.append('</svg>')
    if two:
        a.append(f'<p class=dim style="margin:2px 0 16px">'
                 f'①②는 같은 자(0~100)·같은 시간축입니다 — 위아래를 훑어 견주십시오. '
                 f'면을 칠한 곳이 <b style="color:#b91c1c">위험 이상</b>이고, '
                 f'③의 주황 막대가 <b style="color:#f59e0b">올라간 자리</b>, '
                 f'붉은 막대가 <b style="color:#b91c1c">위험을 넘긴 자리({ncr}분)</b>입니다.')
    else:
        a.append(f'<p class=dim style="margin:2px 0 16px">'
                 f'①②③은 같은 자(0~100)·같은 시간축입니다 — 위아래를 훑어 견주십시오. '
                 f'칠한 <b style="color:#b91c1c">빨간 면이 위험 이상</b>이고, '
                 f'세 칸 모두 같은 빨강이라 면이 넓어진 만큼 위험이 늘어난 것입니다. '
                 f'{CIRC[n]}는 주황이 <b style="color:#f59e0b">올라간 자리</b>, '
                 f'하늘색이 <b style="color:#0284c7">내려간 자리</b>, '
                 f'붉은 막대가 <b style="color:#b91c1c">위험을 넘긴 자리({ncr}분)</b>, '
                 f'파란 막대가 <b style="color:#1d4ed8">위험에서 내려온 자리({nlo}분)</b>입니다.')
    a.append('</p>')
    return "".join(a)


def window(rows, day: str, t0: str, t1: str):
    """그 구간의 행을 **통째로** 돌려준다 — 다리가 몇이든 담긴다."""
    return [r for r in rows if r[0].strftime("%Y-%m-%d") == day
            and t0 <= r[0].strftime("%H:%M") <= t1]


def legs_of(s: dict) -> list:
    return list(s.get("legs") or ["변경 전", "변경 후"])


def pair_of(s: dict) -> tuple:
    """★언제나 **바로 앞 다리 → 마지막 다리**. 다리가 셋이면 (2,3) 이다.

    다리가 늘었는데 (1,2) 로 계속 세면 '이번에 뭐가 달라졌나' 가 아니라
    '지난번에 뭐가 달라졌나' 를 적게 된다 — 조용히 틀린 문서가 나온다.
    """
    n = len(legs_of(s))
    return (n - 1, n)


def leg_stat(rows, cuts, k) -> dict:
    """다리 하나의 등급 분포. 표에 다리마다 한 줄씩 놓으려고 쓴다."""
    cnt = {lv: 0 for lv in LEVELS}
    for r in rows:
        cnt[level(r[k], cuts)] += 1
    w, d = cnt["경계"], cnt["위험"] + cnt["초위험"]
    return {"cnt": cnt, "warn": w, "danger": d, "any": w + d,
            "share": (100.0 * w / (w + d)) if (w + d) else 0.0,
            "hi": max((r[k] for r in rows), default=0.0),
            "zero": sum(1 for r in rows if r[k] == 0),
            "avg": (sum(r[k] for r in rows) / len(rows)) if rows else 0.0}


def blocks(rows, k, cuts, gap=5):
    """위험 이상이 **이어진 덩어리**. gap 분 이내로 끊긴 것은 한 사건으로 본다.

    ★운전원에게 의미 있는 것은 '위험이 몇 분' 이 아니라 '언제부터 몇 분' 이다.
      1분짜리 단발이 스무 번 뜨는 것과 20분이 이어지는 것은 다른 일이다.
      그래서 덩어리로 묶어 **첫 경보 시각**을 견준다.
    """
    out, cur = [], None
    for r in rows:
        if r[k] < cuts[1]:
            continue
        if cur and 0 < (r[0] - cur["end"]).total_seconds() <= gap * 60:
            cur["end"], cur["n"] = r[0], cur["n"] + 1
            cur["hi"] = max(cur["hi"], r[k])
        else:
            if cur:
                out.append(cur)
            cur = {"beg": r[0], "end": r[0], "n": 1, "hi": r[k]}
    if cur:
        out.append(cur)
    return out


def match_blocks(bb, aa, slack=30):
    """변경 후 덩어리 ↔ 새 덩어리를 겹치는 것끼리 짝짓는다.

    돌려주는 것: [(전 덩어리 or None, 후 덩어리 or None)] — 짝이 없으면
    한쪽이 None 이다(사라진 것 · 새로 생긴 것).
    """
    from datetime import timedelta
    sl = timedelta(minutes=slack)
    # ★앞에서부터 집어가면 2분짜리가 먼 덩어리를 채가고, 정작 그 자리에 있던
    #   덩어리가 '사라짐' 으로 찍힌다 (M14 9/12 17:59 이 18:22 를 채갔다).
    #   그래서 **시작 시각이 가장 가까운 짝부터** 붙인다.
    cand = []
    for i, b in enumerate(bb):
        for j, x in enumerate(aa):
            if x["beg"] > b["end"] + sl or x["end"] < b["beg"] - sl:
                continue
            cand.append((abs((x["beg"] - b["beg"]).total_seconds()), i, j))
    cand.sort()
    ub, ua, pairs = set(), set(), []
    for _, i, j in cand:
        if i in ub or j in ua:
            continue
        ub.add(i)
        ua.add(j)
        pairs.append((bb[i], aa[j]))
    pairs += [(b, None) for i, b in enumerate(bb) if i not in ub]
    pairs += [(None, x) for j, x in enumerate(aa) if j not in ua]
    pairs.sort(key=lambda p: (p[0] or p[1])["beg"])
    return pairs


def scale_table(rows, ev=None, cuts=None, pair=None):
    """배점을 N 배로 키웠다면 경계 이상이 몇 분이 되나 — '얼마나 모자란가' 를 본다."""
    c = cuts or CUTS
    out = []
    i, j = pair or (1, 2)
    for mul in (1, 1.5, 2, 3, 4, 5):
        n = sum(1 for r in rows if r[i] + (r[j] - r[i]) * mul >= c[0])
        e = sum(1 for r in (ev or []) if r[i] + (r[j] - r[i]) * mul >= c[0])
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
        f'{fabname(s["fab"])} {min(r[0] for r in s["rows"]):%Y-%m-%d}~{max(r[0] for r in s["rows"]):%m-%d}'
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
             promote(s["rows"], cuts_of(s["fab"]), pair_of(s))) for s in sets]
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
        st = stats(s["rows"], c, pair_of(s))
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
        st, rows = stats(s["rows"], c, pair_of(s)), s["rows"]
        pr = promote(rows, c, pair_of(s))
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
                bi, ai = pair_of(s)
                cb = sum(1 for r in w if r[bi] >= c[1])
                ca = sum(1 for r in w if r[ai] >= c[1])
                a.append(f'<tr><td>{esc(e["what"])}<br><span class=dim>{esc(e["day"])}</span></td>'
                         f'<td class=n>{esc(e["from"])}~{esc(e["to"])}</td>'
                         f'<td class=n>{len(w)}</td>'
                         f'<td class=n>{sum(1 for r in w if r[bi]!=r[ai])}</td>'
                         f'<td class=n>{max(r[bi] for r in w):.0f} → '
                         f'<b>{max(r[ai] for r in w):.0f}</b></td>'
                         f'<td class=n>{cb} → <b class="{"okc" if ca>cb else "bad"}">{ca}</b></td></tr>')
            a.append('</table>')
            for e in evs:
                w = window(rows, e["day"], e["from"], e["to"])
                if not w:
                    continue
                hi = max(r[pair_of(s)[1]] for r in w)
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
        for mul, n, e in scale_table(rows, ev, c, pair_of(s)):
            a.append(f'<tr{" class=hi" if mul==1 else ""}><td class=n>×{mul}</td>'
                     f'<td class=n>{n:,}</td>'
                     + (f'<td class=n>{e}</td>' if ev else '') + '</tr>')
        a.append('</table>')

    # ★'그래서 이렇게 하자' 는 뺐다 — 이 문서는 **잰 값만** 적는다
    #   (고객: "제안 빼라. 현재 데이터를 보고 이야기하는 거야").

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



SEC_CSS = ('<style>.bar{display:inline-block;height:9px;background:#4f46e5;'
           'border-radius:5px;vertical-align:middle}'
           '.bar.b2{background:#c7d2fe}'
           '.arw{font-weight:700}.arw.u{color:#b91c1c}.arw.d{color:#0284c7}</style>')


def _leg_table(rows, c, legs) -> str:
    """다리마다 한 줄 — 등급이 어떻게 갈렸나. 이 표가 이 절의 본문이다."""
    a = ['<table><tr><th>다리</th>'
         + "".join(f'<th class=n>{k}</th>' for k in LEVELS)
         + '<th class=n>위험 이상</th><th class=n>경계 쏠림</th>'
           '<th class=n>최고점</th><th class=n>0점</th></tr>']
    for k, nm in enumerate(legs):
        q = leg_stat(rows, c, k + 1)
        hi = ' class=hi' if k == len(legs) - 1 else ''
        a.append(f'<tr{hi}><td><b>{esc(nm)}</b></td>'
                 + "".join(f'<td class=n>{q["cnt"][lv]}</td>' for lv in LEVELS)
                 + f'<td class=n><b>{q["danger"]}</b></td>'
                   f'<td class=n>{q["share"]:.0f}%</td>'
                   f'<td class=n>{q["hi"]:.0f}</td>'
                   f'<td class=n>{q["zero"]:,}</td></tr>')
    return "".join(a) + '</table>'


def _steps_table(rows, c, legs) -> str:
    """다리와 다리 **사이**에 무슨 일이 있었나 — 한 줄에 한 걸음.

    ★다리가 셋이 되면서 ①② 칸이 '마지막 걸음' 만 재게 됐다. 지난 걸음
      (변경 전 → 변경 후)을 여기 남겨 둬야 문서 한 장으로 다 읽힌다.
    """
    a = ['<table><tr><th>걸음</th><th class=n>달라진 분</th><th class=n>오른 분</th>'
         '<th class=n>내린 분</th><th class=n>등급 바뀐 분</th>'
         '<th class=n>위험 이상</th><th class=n>경계 → 위험</th>'
         '<th class=n>위험에서 내려옴</th></tr>']
    for k in range(1, len(legs)):
        pr = promote(rows, c, (k, k + 1))
        st = stats(rows, c, (k, k + 1))
        hi = ' class=hi' if k == len(legs) - 1 else ''
        a.append(f'<tr{hi}><td><b>{esc(legs[k-1])} → {esc(legs[k])}</b></td>'
                 f'<td class=n>{st["ch"]:,}</td><td class=n>{st["up"]:,}</td>'
                 f'<td class=n>{st["down"]:,}</td>'
                 f'<td class=n>{sum(st["moved"].values()):,}</td>'
                 f'<td class=n>{pr["before"]["danger"]} → '
                 f'<b>{pr["after"]["danger"]}</b></td>'
                 f'<td class=n>{len(pr["up"])}</td>'
                 f'<td class=n>{len(pr["lost"])}</td></tr>')
    return "".join(a) + '</table>'


def _what_changed(fab: str) -> str:
    """무엇이 바뀌었나 — **고객이 준 변경내역서에서 옮긴 값**이다.

    ★우리가 잰 것은 점수뿐이다. '무엇을 바꿨나' 는 잴 수 없고, 2026-09-21
      변경내역서가 근거다. 그래서 출처를 문서에 같이 적는다 — 나중에 숫자가
      안 맞을 때 어디를 봐야 하는지가 남아야 한다.
    """
    code = SYS_OF.get(fab.upper(), fab.upper())
    p = PIO_1MIN.get(code)
    if not p:
        return ""
    a = ['<h3>무엇이 바뀌었나 <span class=dim>— 2026-09-21 변경내역서'
         '(고객 제공)에서 옮김</span></h3>']
    a.append('<p>PIO 점수를 <b>10분 누적만</b> 보던 것에서 '
             '<b>그 분(1분) 값을 같이</b> 보도록 바꿨습니다. '
             '두 구간표가 각각 점수를 내고, 그 <b>합</b>을 상한으로 자릅니다.</p>')
    a.append('<pre><code>PIO 점수  = min(상한 %d, 10분구간표 점수 + 1분구간표 점수)\n'
             '가중       직접(나가는 실패) ×2.0 · 간접(들어오는 실패) ×1.0\n'
             'area_score = min(100, round((기본룰 합계 + PIO 점수) × 100 ÷ 70))'
             '</code></pre>' % p["cap"])
    b10, b1 = p["b10"], p["b1"]
    pts = PIO_PTS[:len(b1)]
    a.append(f'<table><tr><th>{esc(code)} 구간표</th>'
             + "".join(f'<th class=n>{k+1}구간</th>' for k in range(len(b10)))
             + '</tr>')
    a.append('<tr><td>10분 누적 <span class=dim>(기존)</span></td>'
             + "".join(f'<td class=n>{v}</td>' for v in b10) + '</tr>')
    a.append('<tr class=hi><td><b>1분</b> <span class=dim>(신규)</span></td>'
             + "".join(f'<td class=n>{v}</td>' for v in b1)
             + '<td class=n></td>' * (len(b10) - len(b1)) + '</tr>')
    a.append('<tr><td>배점</td>'
             + "".join(f'<td class=n>{v}</td>' for v in pts)
             + '<td class=n></td>' * (len(b10) - len(pts)) + '</tr></table>')
    a.append(f'<p>새로 생기는 칸 — 발동이벤트 CSV 에 '
             f'<code>{esc(code)}_PIO_WSUM1</code>(146칸 → <b>151칸</b>), '
             f'fab분리 CSV 에 <code>area_pio_wsum1</code>(PIO 3칸 → <b>4칸</b>). '
             f'이름이 같은 <code>area_pio_score</code> 는 그대로 0~{p["cap"]} 인데 '
             f'<b>계산식이 바뀝니다</b>.</p>')
    if code in PIO_TH_UNTOUCHED:
        a.append(f'<div class="note"><b>{esc(code)} 임계는 이번에 하나도 안 바꿨습니다.</b> '
                 f'변경내역서가 임계를 손댄 것은 M16A·M16B 입니다 — '
                 f'그러니 아래 숫자가 움직인 것은 1분값이 들어온 몫입니다.</div>')
    return "".join(a)


def _blocks_table(rows, c, legs) -> str:
    """④ 언제부터 울렸나 — 위험 덩어리를 짝지어 **첫 경보 시각**을 견준다.

    ★'위험 몇 분' 만으로는 좋아졌는지 알 수 없다. 사건 꼬리에서 10분 울리던
      것이 사건 머리에서 20분 울리게 됐다면 그것이 좋아진 것이다. 운전원이
      손쓸 수 있는 시간이 생기기 때문이다.
    """
    n = len(legs)
    bb, aa = blocks(rows, n - 1, c), blocks(rows, n, c)
    pr = match_blocks(bb, aa)
    if not pr:
        return ""
    a = [f'<h3>④ 언제부터 울렸나 <span class=dim>— 위험 이상이 이어진 덩어리 '
         f'(5분 이내로 끊긴 것은 한 건으로 묶음)</span></h3>']
    a.append(f'<p>{esc(legs[-2])} <b>{len(bb)}</b>건 / {esc(legs[-1])} '
             f'<b>{len(aa)}</b>건 · 총 <b>{sum(b["n"] for b in bb)}</b>분 → '
             f'<b>{sum(b["n"] for b in aa)}</b>분 · '
             f'최장 <b>{max((b["n"] for b in bb), default=0)}</b>분 → '
             f'<b>{max((b["n"] for b in aa), default=0)}</b>분</p>')
    a.append(f'<table><tr><th>날</th><th>{esc(legs[-2])}</th>'
             f'<th class=n>분</th><th class=n>최고</th>'
             f'<th>{esc(legs[-1])}</th><th class=n>분</th><th class=n>최고</th>'
             f'<th class=n>첫 경보</th></tr>')
    def cell(b):
        return ('<td class=dim>—</td><td class=n>—</td><td class=n>—</td>' if not b
                else f'<td class=n>{b["beg"]:%H:%M}~{b["end"]:%H:%M}</td>'
                     f'<td class=n>{b["n"]}</td><td class=n>{b["hi"]:.0f}</td>')
    def over(z, pool):
        """시간이 겹치는 덩어리가 저쪽에 있나 — 있으면 '없어진' 게 아니라 합쳐진 것."""
        return any(not (w["beg"] > z["end"] or w["end"] < z["beg"]) for w in pool)

    gone = 0
    for b, x in pr:
        day = (b or x)["beg"].strftime("%m-%d")
        if b and x:
            d = int((x["beg"] - b["beg"]).total_seconds() // 60)
            lead = (f'<span class="arw u">{-d}분 빨라짐</span>' if d < 0
                    else (f'<span class="arw d">{d}분 늦어짐</span>' if d > 0 else '같음'))
        elif x:
            # ★1:1 로만 짝지으면 '둘이 하나로 뭉친' 경우가 '사라짐' 으로 찍힌다.
            #   시간이 겹치는 덩어리가 저쪽에 있으면 뭉친 것이다 — 그렇게 쓴다.
            lead = ('<span class=dim>합쳐짐</span>' if over(x, bb)
                    else '<span class="arw u">새로 생김</span>')
        else:
            if over(b, aa):
                lead = '<span class=dim>합쳐짐</span>'
            else:
                lead = '<span class="arw d">사라짐</span>'
                gone += 1
        a.append(f'<tr><td class=n>{day}</td>{cell(b)}{cell(x)}'
                 f'<td class=n>{lead}</td></tr>')
    lost = [b for b, x in pr if x is None and not over(b, aa)]
    a.append('</table><p class=dim>붉은 글씨는 경보가 <b>더 빨리·더 많이</b> 울리게 '
             '된 자리, 파란 글씨는 <b>덜 울리게</b> 된 자리입니다. '
             "'합쳐짐' 은 없어진 것이 아니라 옆 덩어리에 뭉친 것입니다.</p>")
    if lost:
        one = [b for b in lost if b["n"] == 1]
        big = [b for b in lost if b["n"] > 1]
        wh = " · ".join(f'{b["beg"]:%m-%d %H:%M}~{b["end"]:%H:%M}({b["n"]}분)' for b in big)
        if not big:
            tail = "전부 1분짜리 단발입니다."
        elif not one:
            tail = f"{wh} 입니다."
        else:
            tail = f"1분짜리 단발 {len(one)}건, 나머지 {len(big)}건은 {wh} 입니다."
        a.append(f'<div class="note {"miss" if big else ""}">'
                 f'<b>아주 없어진 덩어리 {len(lost)}건</b> — {tail}</div>')
    return "".join(a)


def _quiet_table(rows, c, legs) -> str:
    """⑤ 헛울림 — 내려간 분이 **어디였나**.

    ★내려간 것만 세면 '신호를 깎았다' 인지 '잡음을 깎았다' 인지 모른다.
      그래서 내려간 분이 내려가기 전에 무슨 등급이었는지를 같이 센다 —
      전부 정상이던 분이면 깎인 것은 잡음이다.
    """
    i, j = len(legs) - 1, len(legs)
    dn = [r for r in rows if r[j] < r[i]]
    if not dn:
        return ""
    z = [r for r in rows if r[j] == 0]
    zhot = sum(1 for r in z if r[i] >= c[0])
    out = [r for r in rows if r[i] >= c[0] > r[j]]          # 경계 밖으로
    hh = {}
    for r in out:
        hh[r[0].hour] = hh.get(r[0].hour, 0) + 1
    qi, qj = leg_stat(rows, c, i), leg_stat(rows, c, j)
    a = ['<h3>⑤ 내려간 분은 어디였나 <span class=dim>— 깎인 것이 잡음인지 신호인지'
         '</span></h3>']
    a.append(f'<table><tr><th>센 것</th><th class=n>분</th><th>내용</th></tr>'
             f'<tr><td>점수가 내려간 분</td><td class=n>{len(dn):,}</td>'
             f'<td class=dim>{esc(legs[-1])} 가 {esc(legs[-2])}보다 낮은 분</td></tr>'
             f'<tr><td>0점이 된 분</td><td class=n>{len(z):,}</td>'
             f'<td class=dim>그중 {esc(legs[-2])}에 경계 이상이던 분 '
             f'<b class="{"bad" if zhot else "okc"}">{zhot}</b></td></tr>'
             f'<tr><td>경계 밖으로 나간 분</td><td class=n>{len(out):,}</td>'
             f'<td class=dim>경계 이상 전체는 {qi["any"]:,} → {qj["any"]:,}</td></tr>'
             f'<tr><td>평균 점수</td>'
             f'<td class=n>{qi["avg"]:.1f} → {qj["avg"]:.1f}</td>'
             f'<td class=dim>평균은 내려가고 위험은 '
             f'{qi["danger"]} → {qj["danger"]}분</td></tr></table>')
    if hh:
        mx = max(hh.values())
        a.append('<p>경계 밖으로 나간 분이 <b>몇 시</b>에 있었나</p>'
                 '<table><tr><th class=n>시</th><th class=n>분</th><th></th></tr>')
        for k in sorted(hh, key=lambda k: -hh[k])[:8]:
            w = int(300 * hh[k] / mx)
            a.append(f'<tr><td class=n>{k:02d}시</td><td class=n>{hh[k]}</td>'
                     f'<td><span class="bar b2" style="width:{w}px"></span></td></tr>')
        a.append('</table>')
    return "".join(a)


def fab_section(s: dict, title: str = "") -> str:
    """한 FAB 의 비교 — **기존 분석 문서 뒤에 붙일** 한 절.

    ★고객: "하나 하나식 분리해줘!! 기존 내용에다가!! M14A·M16HUB 각각".
      새 문서를 따로 만들면 나중에 어느 쪽이 최신인지 알 수 없다.
    ★다리가 둘이면(2026-09-18 자료) 예전 그대로 찍는다 — 이미 붙어 있는
      문서와 글자가 달라지면 무엇이 바뀐 절인지 읽는 사람이 헷갈린다.
      다리가 셋이면(2026-09-21 자료) 칸을 늘리고 ④⑤를 더 붙인다.
    """
    a = [SEC_CSS]
    rows = s["rows"]
    legs = list(s.get("legs") or ["변경 전", "변경 후"])
    n = len(legs)
    two = (n == 2)
    c = cuts_of(s["fab"])
    pair = pair_of(s)                      # ★언제나 바로 앞 다리 → 마지막 다리
    st, pr = stats(rows, c, pair), promote(rows, c, pair)
    if not title:
        title = (f'PIO_ERROR 룰 추가 — 전 / 후 ({fabname(s["fab"])})' if two
                 else f'PIO_ERROR 룰 — {" / ".join(legs)} ({fabname(s["fab"])})')
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
    extra = ""
    if not two:
        z = [r for r in rows if r[n] == 0]
        zhot = sum(1 for r in z if r[n - 1] >= c[0])
        extra = (f'<br>같은 자료에서 점수가 내려간 분은 {st["down"]:,}분이고, '
                 f'0점이 된 {len(z):,}분 가운데 {esc(legs[-2])}에 '
                 f'경계 이상이던 분은 <b>{zhot}분</b>입니다.')
    a.append(f'<div class="note {"good" if good else "miss"}">'
             f'<b>{word} — 위험 이상 {db} → {da}분{up_txt}</b><br>'
             f'등급 컷 {c[0]} / {c[1]} / {c[2]} 로 셌습니다. '
             f'운전원이 보는 것은 등급이라, 컷을 안 넘은 점수 변화는 '
             f'화면에 나타나지 않습니다.{extra}</div>')
    if not two:
        a.append(_what_changed(s["fab"]))
        a.append('<h3>등급 분포 <span class=dim>— 다리마다 (분)</span></h3>')
        a.append(_leg_table(rows, c, legs))
        a.append('<h3>걸음마다 무엇이 달라졌나</h3>')
        a.append(_steps_table(rows, c, legs))
    else:
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
    if pr["up"] or pr["lost"]:
        a.append(f'<p>경계 → 위험으로 올라간 분 <b>{len(pr["up"])}</b>'
                 + (f' · 위험에서 내려온 분 <b>{len(pr["lost"])}</b>'
                    if not two else '')
                 + f' · 위험({c[1]}) 문턱 5점 이내에 남은 분 <b>{pr["near5"]}</b> · '
                   f'10점 이내 <b>{pr["near10"]}</b></p>')

    # ── 그림 — 날마다 한 장. 표의 숫자가 '어디서' 생겼는지를 보여 준다 ──
    evs = [e for e in KNOWN if SYS_OF.get(e["fab"].upper(), e["fab"].upper())
           == SYS_OF.get(s["fab"].upper(), s["fab"].upper())]
    days = sorted({r[0].strftime("%Y-%m-%d") for r in rows})
    a.append(f'<h3>{"변경 전 / 후" if two else " / ".join(legs)}'
             f' — 하루치 점수</h3>')
    for day in days:
        ev = [e for e in evs if e["day"] == day]
        a.append(f'<p style="margin:14px 0 2px"><b>{esc(day)}</b>'
                 + (f' <span class=dim>· {esc(" · ".join(e["what"] for e in ev))}</span>'
                    if ev else '') + '</p>')
        a.append(chart(rows, c, day, ev, legs))
    if s.get("skew"):
        a.append(f'<div class="note miss"><b>주의:</b> 두 열의 시각이 어긋난 행이 '
                 f'{s["skew"]}개 있어 뺐습니다.</div>')

    ftr = "" if two else f' <span class=dim>— {esc(legs[-2])} → {esc(legs[-1])}</span>'
    if two:
        a.append(f'<h3>① 룰이 먹었나</h3><table>'
                 '<tr><th>점수가 오른 분</th><th class=n>올린 폭 평균</th>'
                 '<th class=n>최대</th><th class=n>내려간 분</th></tr>'
                 f'<tr><td class=n>{st["ch"]:,}분 / {st["n"]:,}분 '
                 f'({100*st["ch"]/st["n"]:.1f}%)</td>'
                 f'<td class=n>{st["avg"]:+.1f}점</td><td class=n>{st["max"]:+.0f}점</td>'
                 f'<td class=n>{st["down"]}</td></tr></table>')
    else:
        # ★'올린 폭 평균' 이라고 쓰면 안 된다 — 이번 다리는 내려간 분이 더 많아서
        #   평균이 음수다. 칸 이름과 숫자가 어긋나면 읽는 사람이 잘못 읽는다.
        a.append(f'<h3>① 룰이 먹었나{ftr}</h3><table>'
                 '<tr><th>점수가 달라진 분</th><th class=n>오른 분</th>'
                 '<th class=n>내린 분</th><th class=n>제일 많이 오른 폭</th>'
                 '<th class=n>제일 많이 내린 폭</th><th class=n>바뀐 폭 평균</th></tr>'
                 f'<tr><td class=n>{st["ch"]:,}분 / {st["n"]:,}분 '
                 f'({100*st["ch"]/st["n"]:.1f}%)</td>'
                 f'<td class=n>{st["up"]:,}</td><td class=n>{st["down"]:,}</td>'
                 f'<td class=n>{st["max"]:+.0f}점</td>'
                 f'<td class=n>{st["min"]:+.0f}점</td>'
                 f'<td class=n>{st["avg"]:+.1f}점</td></tr></table>')

    a.append(f'<h3>② 화면이 달라졌나{ftr} <span class=dim>— 등급 분포(분)</span></h3>'
             '<table><tr><th></th>' +
             "".join(f'<th class=n>{k}</th>' for k in LEVELS) +
             '<th class=n>최고점</th></tr>'
             f'<tr><td>{esc(legs[-2])}</td>{_lvrow(st["cnt"],0)}'
             f'<td class=n>{st["hi_b"]:.0f}</td></tr>'
             f'<tr><td>{esc(legs[-1])}</td>{_lvrow(st["cnt"],1)}'
             f'<td class=n>{st["hi_a"]:.0f}</td></tr></table>')
    if st["moved"]:
        a.append('<table><tr><th>등급이 바뀐 분</th><th class=n>분</th></tr>' +
                 "".join(f'<tr class=hi><td>{esc(lb)} → <b>{esc(la)}</b></td>'
                         f'<td class=n>{n2}</td></tr>'
                         for (lb, la), n2 in sorted(st["moved"].items(),
                                                    key=lambda kv: -kv[1])) +
                 '</table>')
    else:
        a.append('<div class="note miss"><b>등급이 바뀐 분: 0</b> — '
                 '점수는 올랐지만 컷을 넘은 곳이 한 분도 없습니다. '
                 '관제 화면은 전과 완전히 같습니다.</div>')

    # ③ 알려진 사건
    evs = [e for e in KNOWN if e["fab"] == s["fab"]]
    if evs:
        a.append('<h3>③ 잡고 싶던 것을 잡았나 <span class=dim>— 알려진 사건 구간</span></h3>')
        a.append('<table><tr><th>사건</th><th class=n>구간</th><th class=n>분</th>'
                 + ('<th class=n>오른 분</th>' if two else '')
                 + f'<th class=n>구간 최고 ({esc(" → ".join(legs))})</th>'
                   f'<th class=n><b>위험 이상</b> ({esc(" → ".join(legs))})</th></tr>')
        for e in evs:
            w = window(rows, e["day"], e["from"], e["to"])
            if not w:
                continue
            his = " → ".join(f'{max(r[k] for r in w):.0f}' if k < n
                             else f'<b>{max(r[k] for r in w):.0f}</b>'
                             for k in range(1, n + 1))
            cn = [sum(1 for r in w if r[k] >= c[1]) for k in range(1, n + 1)]
            kls = "okc" if cn[-1] > cn[-2] else ("bad" if cn[-1] < cn[-2] else "")
            cns = " → ".join(str(v) for v in cn[:-1]) + \
                  f' → <b class="{kls}">{cn[-1]}</b>'
            a.append(f'<tr><td>{esc(e["what"])}<br><span class=dim>{esc(e["day"])}</span></td>'
                     f'<td class=n>{esc(e["from"])}~{esc(e["to"])}</td>'
                     f'<td class=n>{len(w)}</td>'
                     + (f'<td class=n>{sum(1 for r in w if r[1]!=r[2])}</td>' if two else '')
                     + f'<td class=n>{his}</td><td class=n>{cns}</td></tr>')
        a.append('</table>')
        for e in evs:
            w = window(rows, e["day"], e["from"], e["to"])
            if not w:
                continue
            hi = max(r[n] for r in w)
            if hi < c[1]:
                a.append(f'<div class="note miss"><b>{esc(e["what"])}</b> — '
                         f'구간 최고가 {"변경 전후 모두 " if two else ""}'
                         f'<b>{hi:.0f}점</b>으로,'
                         f' 위험({c[1]})까지 {c[1]-hi:.0f}점 남았습니다.</div>')
            else:
                hit = [r for r in w if r[n] >= c[1]]
                was = sum(1 for r in w if r[n - 1] >= c[1])
                if not two and len(hit) > was:
                    # ★구간 **밖**에서 이미 울리고 있었는지도 본다 — 사건을
                    #   신고 시각보다 먼저 잡았다면 그게 제일 값진 결과다.
                    beg, k = hit[0][0], rows.index(hit[0])
                    while k > 0 and rows[k - 1][n] >= c[1] and \
                            (beg - rows[k - 1][0]).total_seconds() == 60:
                        k -= 1
                        beg = rows[k][0]
                    early = int((hit[0][0] - beg).total_seconds() // 60)
                    pre = (f' 이어진 덩어리로는 <b>{beg:%H:%M}</b>부터 — '
                           f'구간 시작보다 <b>{early}분 빠릅니다</b>.' if early else '')
                    a.append(f'<div class="note good"><b>{esc(e["what"])}</b> — '
                             f'이 구간에서 위험 이상이 {was} → <b>{len(hit)}분</b>이 '
                             f'됐습니다. 처음 위험이 뜬 시각은 '
                             f'<b>{hit[0][0]:%H:%M}</b>, 구간 최고 '
                             f'<b>{max(r[n] for r in w):.0f}점</b>입니다.{pre}</div>')

    if not two:
        a.append(_blocks_table(rows, c, legs))
        a.append(_quiet_table(rows, c, legs))

    # 날짜별
    a.append('<h3>날짜별</h3><table><tr><th>날짜</th><th class=n>분</th>'
             '<th class=n>달라진 분</th><th class=n>경계 이상 '
             f'({esc(legs[-2])} → {esc(legs[-1])})</th>'
             f'<th class=n>최고점 ({esc(legs[-2])} → {esc(legs[-1])})</th></tr>')
    for day in sorted(st["days"]):
        d = st["days"][day]
        a.append(f'<tr><td>{day}</td><td class=n>{d["n"]:,}</td>'
                 f'<td class=n>{d["ch"]:,}</td>'
                 f'<td class=n>{d["wb"]} → {d["wa"]}</td>'
                 f'<td class=n>{d["hb"]:.0f} → {d["ha"]:.0f}</td></tr>')
    a.append('</table>')

    # 오른 분이 어디까지 갔나
    up_rows = [r for r in st["changed"] if r[2] > r[1]]
    if up_rows:
        buck = {}
        for _, _, av in up_rows:
            buck.setdefault(int(av) // 10 * 10, 0)
            buck[int(av) // 10 * 10] += 1
        mx = max(buck.values())
        a.append(f'<h3>오른 분이 어디까지 갔나 <span class=dim>'
                 f'({esc(legs[-1])} 점수대)</span></h3>'
                 '<table><tr><th class=n>점수대</th><th class=n>분</th><th></th></tr>')
        for k in sorted(buck):
            w = int(300 * buck[k] / mx)
            over = ' <b class=okc>← 경계 위</b>' if k >= c[0] else ''
            a.append(f'<tr><td class=n>{k}~{k+9}</td><td class=n>{buck[k]:,}</td>'
                     f'<td><span class="bar" style="width:{w}px"></span>{over}</td></tr>')
        a.append('</table>')
        top = max(av for _, _, av in up_rows)
        if top < c[0]:
            a.append(f'<div class="note miss">제일 높이 올라간 분도 <b>{top:.0f}점</b> — '
                     f'경계({c[0]})까지 <b>{c[0]-top:.0f}점</b> 모자랍니다.</div>')

    # ★'배점을 N 배로 키웠다면' 표는 뺐다 (고객: "제안 빼라. 지금 PIO 들어가잖아.
    #   현재 데이터를 보고 이야기하는 거야"). 이 문서는 **지금 들어간 룰이
    #   무엇을 했는지**만 적는다 — 가정한 배점으로 센 숫자를 같이 놓으면
    #   읽는 사람이 그것도 잰 값으로 읽는다.
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
        st = stats(s["rows"], c, pair_of(s))
        pr = promote(s["rows"], c, pair_of(s))
        lg = legs_of(s)
        print(f'  {fabname(s["fab"]):<18} 컷 {c[0]}/{c[1]}/{c[2]}'
              f' · {lg[-2]} → {lg[-1]}'
              f' · 달라진 분 {st["ch"]:>5} (오름 {st["up"]} 내림 {st["down"]})'
              f' · 등급 바뀐 분 {sum(st["moved"].values()):>3}'
              f' · 위험이상 {pr["before"]["danger"]} → {pr["after"]["danger"]}'
              f' · 경계→위험 {len(pr["up"])} · 위험에서 내려옴 {len(pr["lost"])}')

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
