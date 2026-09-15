# -*- coding: utf-8 -*-
"""더블클릭 구간 그래프 — 시안 (현행 graphs.render 를 대체할 후보).

현행에서 실제로 재 본 문제 넷:

  · 세로 1054px 인데 모달은 92vh(~900px) — **늘 스크롤**. 지표가 늘면 더 길어진다.
  · 패널마다 **자기 min~max 로 정규화**해서, 임계의 0.47배(정상)인 지표가
    2.5배(심각)인 지표와 똑같이 꽉 차 보인다. 심각도가 통째로 왜곡된다.
  · 지표 패널에 **임계선이 없다** — 넘었는지를 눈으로 못 본다.
  · 면적을 전부 빨강/주황으로 채워서 정상 지표도 위험해 보인다.

그래서 바꾼 것:

  · **임계를 넘은 것만 색.** 안 넘은 것은 회색으로 죽인다. 색은 '넘었다' 는
    뜻으로만 쓴다 (관제 화면에서 색은 곧 지시다).
  · **배수 큰 순으로 정렬.** 왼쪽 위가 항상 제일 심한 것 — 눈을 굴릴 필요가 없다.
  · **칸마다 임계선**(가로 실선)과 **배수 배지**. 실제 값과 단위는 그대로 남긴다.
    "2.5배" 만으로는 조치를 못 정한다 — 22.5분인지 4분인지를 알아야 한다.
  · 한 화면(약 560px)에 들어가게 격자로 깐다.

★색·테마는 graphs.py 것을 그대로 쓴다. 두 벌로 갈라지면 한쪽만 고치게 된다.
"""
from __future__ import annotations

import graphs as G

_e, _f, _fmt, _text_w = G._e, G._f, G._fmt, G._text_w


def thresholds() -> dict:
    """{csv컬럼: (임계, 부등호, 이름, 단위)} — 룰 원본에서 읽는다.

    ★한 컬럼에 임계가 둘인 경우가 있다 (반송시간 9.0 / 지속 6.3). 룰 정의
      순서가 앞선 쪽(본 임계)을 쓴다 — 낮은 쪽을 쓰면 늘 '넘음' 으로 뜬다.
    """
    try:
        import fab_score as F
    except Exception:
        return {}
    order = {r["code"]: i for i, r in enumerate(F.RULES)}
    best: dict = {}
    for src in (F.WATCH, {"_ALL": F.WATCH_ALL}):
        for _fab, rules in (src or {}).items():
            for code, specs in (rules or {}).items():
                for sp in specs or []:
                    c = sp.get("csv")
                    if not c or sp.get("thr") is None or sp.get("record_only"):
                        continue
                    k = order.get(code, 99)
                    if c not in best or k < best[c][0]:
                        best[c] = (k, sp["thr"], sp.get("op", ">="),
                                   sp.get("label"), sp.get("unit"))
    return {c: v[1:] for c, v in best.items()}


def _ratio(v, thr, op):
    """임계 대비 배수. 작을수록 나쁜 지표(<=)는 뒤집어 잰다."""
    if v is None or not thr:
        return None
    try:
        v, thr = float(v), float(thr)
    except (TypeError, ValueError):
        return None
    if thr == 0:
        return None
    return (thr / v) if (op in ("<=", "<") and v) else (v / thr)


# ── 크기 ──────────────────────────────────────────────────────────────
# ★한 화면(모달 max-height 92vh ≈ 900px)에 들어가야 한다. 현행 1054px 은
#   지표가 여섯일 때 값이고 여덟이면 1310px 이라 늘 스크롤이었다.
HEAD_H = 30          # 제목 줄
LBL_H = 18           # 섹션 라벨 줄 — 제목과 겹치지 않게 자리를 따로 준다
SCORE_H = 170        # 스코어 패널
AXIS_H = 16          # 시간축 글자 줄
CELL_H = 124
COLS = 3
PAD = 16
GAP = 10


def _badge(o, x, y, ratio, color, dim):
    """배수 배지 — 넘은 것만 색. '몇 배' 는 한 칸에서 제일 먼저 읽혀야 한다."""
    if ratio is None:
        return
    over = ratio >= 1.0
    txt = ("▲%.1f배" % ratio) if over else ("%.1f배" % ratio)
    w = _text_w(txt, 10.5) + 12
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="17" rx="8.5" '
             f'fill="{color}" opacity="{0.16 if over else 0.10}"/>')
    o.append(f'<text x="{x + w / 2:.1f}" y="{y + 12.3:.1f}" font-size="10.5" '
             f'font-weight="700" text-anchor="middle" '
             f'fill="{color if over else dim}">{_e(txt)}</text>')
    return w


def _cell(o, x, y, w, h, m, pts, P, X0):
    """지표 한 칸 — 배지 · 이름 · 값/임계 · 스파크라인 + 임계선."""
    col, thr, op = m["col"], m.get("thr"), m.get("op", ">=")
    unit = m.get("unit") or ""
    cols = m.get("sumcols") or [col]
    def _v(r):
        got = [_f(r.get(c)) for c in cols]
        got = [g for g in got if g is not None]
        return sum(got) if got else None
    vals = [(t, _v(r)) for t, r in pts]
    vals = [(t, v) for t, v in vals if v is not None]
    if not vals:
        return
    # ★배지(배수)는 구간 최악값으로 재는데 값만 마지막 것을 적으면 서로
    #   어긋난다 ("7.7배 / 20개"). 같은 값을 보여 준다 — 최악값과 그 시각.
    ratio = m.get("ratio")
    cur = m.get("worst", vals[-1][1])
    at = next((t for t, v in vals if v == cur), None)
    over = ratio is not None and ratio >= 1.0
    # ★색은 '넘었다' 는 뜻으로만. 안 넘은 칸은 회색으로 죽인다 —
    #   지금 화면이 전부 빨간 이유가 이걸 안 해서다.
    color = (P["crit"] if (ratio or 0) >= 2 else P["evt"]) if over else P["tx3"]
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
             f'fill="{P["bg2"]}" stroke="{P["line"]}"/>')
    if over:
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" '
                 f'rx="1.5" fill="{color}"/>')
    bw = _badge(o, x + 12, y + 11, ratio, color, P["tx3"]) or 0
    o.append(f'<text x="{x + 12 + bw + 8:.1f}" y="{y + 23.5:.1f}" font-size="11.5" '
             f'font-weight="700" fill="{P["tx"] if over else P["tx2"]}">'
             f'{_e(m["label"])}</text>')
    # ★실제 AMOS 컬럼명 — 현장에서 이걸 보고 원 지표를 찾아간다. 이름표만
    #   있으면 "그게 어느 컬럼이냐" 를 다시 물어야 한다. 칸이 좁으면 앞을
    #   자르고 뒤(컬럼 이름)를 남긴다 — 뒤쪽이 무엇을 재는지를 말한다.
    raw = str(m.get("raw") or "")
    if raw:
        avail = w - 24
        shown = raw
        while shown and _text_w(shown, 9) > avail:
            shown = shown[1:]
        if shown != raw:
            shown = "…" + shown[1:]
        o.append(f'<text x="{x + 12:.1f}" y="{y + 37:.1f}" font-size="9" '
                 f'fill="{P["tx3"]}" font-family="Consolas,monospace">'
                 f'{_e(shown)}<title>{_e(raw)}</title></text>')
    o.append(f'<text x="{x + 12:.1f}" y="{y + 56:.1f}" font-size="14" '
             f'font-weight="800" fill="{color if over else P["tx2"]}" '
             f'font-family="Consolas,monospace">{_e(_fmt(cur))}{_e(unit)}</text>')
    if at is not None:
        o.append(f'<text x="{x + 12 + _text_w(_fmt(cur) + unit, 14) + 7:.1f}" '
                 f'y="{y + 56:.1f}" font-size="9.5" fill="{P["tx3"]}" '
                 f'font-family="Consolas,monospace">최고 @{at:%H:%M}</text>')
    if thr:
        o.append(f'<text x="{x + w - 12:.1f}" y="{y + 56:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{P["tx3"]}" '
                 f'font-family="Consolas,monospace">임계 {_e(_fmt(thr))}{_e(unit)}</text>')

    # 스파크라인 — 0 과 임계×2 사이로 **모든 칸이 같은 자로** 잰다.
    # ★여기가 현행과 갈리는 자리다. 칸마다 자기 min~max 로 재면 정상인 값도
    #   꽉 차 보인다. 임계를 기준으로 재야 칸끼리 비교가 된다.
    pt, pb = y + 66, y + h - 12
    lo, hi = 0.0, (float(thr) * 2 if thr else max(v for _t, v in vals) or 1.0)
    hi = max(hi, max(v for _t, v in vals) * 1.05, 1e-9)
    Y = lambda v: pb - (pb - pt) * ((min(max(v, lo), hi) - lo) / (hi - lo))
    n = len(vals)
    X = lambda i: x + 12 + (w - 24) * (i / max(1, n - 1))
    if m.get("bar"):
        bwd = max(1.4, min(7.0, (w - 24) / max(1, n) - 0.8))
        for i, (_t, v) in enumerate(vals):
            if v <= 0:
                continue
            hh = max(1.0, pb - Y(v))
            o.append(f'<rect x="{X(i) - bwd / 2:.1f}" y="{pb - hh:.1f}" '
                     f'width="{bwd:.1f}" height="{hh:.1f}" rx="1.2" fill="{color}" '
                     f'opacity="{0.95 if over else 0.5}"/>')
    else:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}"
                     for i, (_t, v) in enumerate(vals))
        # 면적은 10% 워시 — 현행 20% 는 칸을 덩어리로 만들어 선이 안 보인다
        o.append(f'<path d="{d} L{X(n - 1):.1f},{pb:.1f} L{X(0):.1f},{pb:.1f} Z" '
                 f'fill="{color}" opacity="{0.10 if over else 0.06}"/>')
        o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round" '
                 f'opacity="{1 if over else 0.65}"/>')
        o.append(f'<circle cx="{X(n - 1):.1f}" cy="{Y(vals[-1][1]):.1f}" r="4" '
                 f'fill="{color}" stroke="{P["bg2"]}" stroke-width="2"/>')
    if thr and lo <= float(thr) <= hi:
        ty = Y(float(thr))
        o.append(f'<line x1="{x + 12:.1f}" y1="{ty:.1f}" x2="{x + w - 12:.1f}" '
                 f'y2="{ty:.1f}" stroke="{P["crit"]}" stroke-width="1" opacity=".55"/>')
    o.append(f'<line x1="{x + 12:.1f}" y1="{pb:.1f}" x2="{x + w - 12:.1f}" '
             f'y2="{pb:.1f}" stroke="{P["line"]}" stroke-width="1"/>')


def render(rows, center, minutes=60, width=1000, cfg=None, fabs=None,
           theme="dark") -> str:
    """구간 그래프 — 스코어 크게 + 지표 격자."""
    from sentinel import load_config
    cfg = cfg or load_config()
    P = G._pal(theme)
    pts = G.window_rows(rows, center, minutes, cfg)
    if not pts:
        return (f'<div style="padding:28px;color:{P["tx2"]};font-size:13px">'
                f'이 구간에 자료가 없습니다</div>')

    # ── 지표 모으기 + 배수 재기 ───────────────────────────────────────
    TH = thresholds()
    sel = min(pts, key=lambda tr: abs((tr[0] - center).total_seconds()))
    mets = G.parse_reason_metrics(sel[1].get("reason") or "")
    seen, metrics = set(), []
    for m in mets:
        c = m["col"]
        if c in seen:
            continue
        seen.add(c)
        # ★PIO 주 경로는 raw 가 'PIO.DEPOSIT.{경로}' 라는 자리표다. 현장에서
        #   찾아갈 수 없는 이름이라, 실제 컬럼명으로 바꿔 적고 값도 그 컬럼들의
        #   합으로 잰다 (첫 경로만 그리면 나머지가 화면에서 사라진다).
        sub = [x["col"] for x in (m.get("cols") or [])] if m.get("pio_stack") else None
        if sub:
            m = dict(m, sumcols=sub, raw=" + ".join(sub))
            c = sub[0]
        cs = m.get("sumcols") or [c]
        vs = []
        for _t, r in pts:
            got = [_f(r.get(k)) for k in cs]
            got = [g for g in got if g is not None]
            if got:
                vs.append(sum(got))
        if not vs:
            continue
        thr, op, _lb, _un = TH.get(c, (None, ">=", None, None))
        m = dict(m, thr=thr, op=op)
        # ★배수는 **구간 최악값**으로 잰다. 마지막 값으로 재면 이미 지나간
        #   급증이 회색으로 죽어서, 방금 무슨 일이 있었는지가 안 보인다.
        worst = max(vs) if op in (">=", ">") else min(vs)
        m["ratio"] = _ratio(worst, thr, op)
        m["worst"] = worst
        metrics.append(m)
    # 넘은 것 먼저, 그 안에서 배수 큰 순 — 왼쪽 위가 늘 제일 심한 것
    metrics.sort(key=lambda m: (-(m["ratio"] or 0)))

    # ── 자리 잡기 ─────────────────────────────────────────────────────
    rowsn = (len(metrics) + COLS - 1) // COLS
    cw = (width - PAD * 2 - GAP * (COLS - 1)) / COLS
    y_slbl = HEAD_H + LBL_H            # '스코어' 라벨 baseline
    top_s = y_slbl + 6                 # 스코어 그림 위
    y_axis = top_s + SCORE_H + AXIS_H  # 시간축 글자 baseline
    y_mlbl = y_axis + 22               # '발동 지표' 라벨 baseline
    y_grid = y_mlbl + 10
    height = y_grid + rowsn * (CELL_H + GAP) - GAP + PAD

    o = [f'<svg viewBox="0 0 {width} {height:.0f}" width="100%" '
         f'style="display:block" role="img" xmlns="http://www.w3.org/2000/svg">',
         f'<style>.ghit:hover{{fill-opacity:.07}}'
         f'.mhit:hover{{fill-opacity:.10}}</style>',
         f'<rect width="{width}" height="{height:.0f}" rx="14" fill="{P["bg"]}"/>']

    # ── 제목 ─────────────────────────────────────────────────────────
    r0 = sel[1]
    sc = _f(r0.get("unified_risk_score"))
    bands = [(lo, hi, nm, c) for (lo, hi, c), nm
             in zip(G._bands_of(cfg, P), ("정상", "경계", "위험", "초위험"))]
    lvl, lvc = "정상", P["tx2"]
    for lo, hi, nm, c in bands:
        if sc is not None and lo <= sc <= hi:
            lvl, lvc = nm, c
    o.append(f'<text x="{PAD}" y="21" font-size="13.5" font-weight="700" '
             f'fill="{P["tx"]}">{_e(sel[0].strftime("%Y-%m-%d %H:%M"))}'
             f'<tspan fill="{P["tx3"]}" font-weight="400"> · </tspan>'
             f'<tspan fill="{P["tx2"]}">{_e(r0.get("hot_area") or "")}</tspan></text>')
    if sc is not None:
        # 점수는 이 화면의 머리글자다 — 배경에 묻히지 않게 알약을 깔고 얹는다
        # ★정상일 때 lvc 는 흐린 회색이라, 그대로 쓰면 제일 큰 글자가 제일
        #   안 읽힌다. 알약만 등급색으로 깔고 숫자는 본문색으로 쓴다.
        txt, sub = f"{sc:.0f}", f" {lvl}"
        bw2 = _text_w(txt, 20) + _text_w(sub, 12) + 24
        o.append(f'<rect x="{width - PAD - bw2:.1f}" y="3" width="{bw2:.1f}" '
                 f'height="25" rx="12.5" fill="{lvc}" opacity="0.18" '
                 f'stroke="{lvc}" stroke-opacity="0.45"/>')
        o.append(f'<text x="{width - PAD - 12:.1f}" y="21.5" font-size="20" '
                 f'font-weight="800" text-anchor="end" fill="{P["tx"]}" '
                 f'font-family="Consolas,monospace">{txt}'
                 f'<tspan font-size="12" font-weight="700" fill="{lvc}">'
                 f'{_e(sub)}</tspan></text>')

    # ── 스코어 패널 ───────────────────────────────────────────────────
    L, R = PAD + 30, width - PAD
    pw = R - L
    SY = lambda v: top_s + SCORE_H * (1 - max(0.0, min(100.0, v)) / 100.0)
    n = len(pts)
    X = lambda i: L + pw * (i / max(1, n - 1))
    o.append(f'<text x="{PAD}" y="{y_slbl:.1f}" font-size="10.5" '
             f'font-weight="700" fill="{P["tx2"]}">스코어</text>')
    for lo, hi, nm, c in bands:
        y1, y2 = SY(min(hi, 100)), SY(lo)
        o.append(f'<rect x="{L}" y="{y1:.1f}" width="{pw:.1f}" height="{y2 - y1:.1f}" '
                 f'fill="{c}" opacity="0.10"/>')
        if lo:                              # 0 은 안 적는다 (바닥선이 곧 0)
            o.append(f'<line x1="{L}" y1="{y2:.1f}" x2="{R}" y2="{y2:.1f}" '
                     f'stroke="{c}" stroke-width="1" opacity="0.30"/>')
            # 숫자를 밴드색으로 쓰면 어두운 배경에서 안 읽힌다 — 본문 흐린색
            o.append(f'<text x="{L - 5}" y="{y2 + 3.5:.1f}" font-size="9.5" '
                     f'text-anchor="end" fill="{P["tx3"]}" '
                     f'font-family="Consolas,monospace">{lo:g}</text>')
    o.append(f'<line x1="{L}" y1="{top_s + SCORE_H:.1f}" x2="{R}" '
             f'y2="{top_s + SCORE_H:.1f}" stroke="{P["line"]}"/>')
    sv = [(i, _f(r.get("unified_risk_score"))) for i, (_t, r) in enumerate(pts)]
    sv = [(i, v) for i, v in sv if v is not None]
    if sv:
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(i):.1f},{SY(v):.1f}"
                     for k, (i, v) in enumerate(sv))
        o.append(f'<path d="{d}" fill="none" stroke="{P["score"]}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
    # ★분마다 호버 — 현행에 있던 것이라 없애면 안 된다. 서버가 그린 SVG 라
    #   <title> 이 곧 툴팁이다(JS 없이 뜬다). 막대가 1px 라도 손이 닿게
    #   히트 영역을 칸 폭만큼 넓게 깐다.
    hw = max(3.0, pw / max(1, n))
    for i, (t, r) in enumerate(pts):
        v = _f(r.get("unified_risk_score"))
        lv2 = next((nm for lo, hi, nm, _c in bands
                    if v is not None and lo <= v <= hi), "")
        tip = f"{t:%H:%M}  {'' if v is None else f'{v:.0f}점'} {lv2}"
        ho = (r.get("hot_area") or "").strip()
        if ho:
            tip += f"\n주 영역 {ho}"
        ft = (r.get("predicted_fault_type") or "").strip()
        if ft:
            tip += f"\n예측 {ft}"
        o.append(f'<rect class="ghit" data-at="{_e(t.isoformat())}" '
                 f'x="{X(i) - hw / 2:.1f}" y="{top_s}" '
                 f'width="{hw:.1f}" height="{SCORE_H}" fill="{P["tx"]}" '
                 f'fill-opacity="0" style="cursor:pointer">'
                 f'<title>{_e(tip)}</title></rect>')

    si = pts.index(sel)
    o.append(f'<line x1="{X(si):.1f}" y1="{top_s}" x2="{X(si):.1f}" '
             f'y2="{top_s + SCORE_H:.1f}" stroke="{P["sel"]}" stroke-width="1.2"/>')
    if sc is not None:
        o.append(f'<circle cx="{X(si):.1f}" cy="{SY(sc):.1f}" r="5" fill="{P["sel"]}" '
                 f'stroke="{P["bg"]}" stroke-width="2"/>')
    o.append(f'<text x="{L}" y="{y_axis:.1f}" font-size="9.5" fill="{P["tx3"]}" '
             f'font-family="Consolas,monospace">{_e(pts[0][0].strftime("%H:%M"))}</text>')
    o.append(f'<text x="{X(si):.1f}" y="{y_axis:.1f}" font-size="9.5" '
             f'text-anchor="middle" fill="{P["sel"]}" font-weight="700" '
             f'font-family="Consolas,monospace">{_e(sel[0].strftime("%H:%M"))}</text>')
    o.append(f'<text x="{R}" y="{y_axis:.1f}" font-size="9.5" text-anchor="end" '
             f'fill="{P["tx3"]}" font-family="Consolas,monospace">'
             f'{_e(pts[-1][0].strftime("%H:%M"))}</text>')

    # ── 지표 격자 ─────────────────────────────────────────────────────
    nover = sum(1 for m in metrics if (m["ratio"] or 0) >= 1)
    o.append(f'<text x="{PAD}" y="{y_mlbl:.1f}" font-size="10.5" '
             f'font-weight="700" fill="{P["tx2"]}">발동 지표 '
             f'<tspan fill="{P["tx3"]}" font-weight="400">— 임계 넘은 것부터 · '
             f'{nover}/{len(metrics)}개 넘음</tspan></text>')
    for k, m in enumerate(metrics):
        cx = PAD + (k % COLS) * (cw + GAP)
        cy = y_grid + (k // COLS) * (CELL_H + GAP)
        _cell(o, cx, cy, cw, CELL_H, m, pts, P, X)
    o.append("</svg>")
    return "".join(o)
