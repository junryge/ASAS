#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 구간 그래프 (독립 SVG 렌더러)

발동이벤트_요약 / report_graphs 와 같은 형식으로 그린다:

  ┌ 스코어 패널 ─ unified_risk_score, 등급 밴드(60/71/85), 사건 표시
  ├ 지표 패널 1 ─ M16HUB 반송시간 (분)
  │               M16HUB.QUE.TIME.AVGTOTALTIME1MIN   ← 실제 raw 컬럼
  │               범위 3.82~19.32분
  ├ 지표 패널 2 ─ …
  └ X축 (시각)

지표는 최고점 reason 에서 뽑는다. 각 패널은 자기 축을 가진다.
데모스를 import 하지 않고 외부 라이브러리도 쓰지 않는다(순수 SVG).
"""
from __future__ import annotations

import html
import re
from datetime import timedelta

from lp_client import load_config, parse_dt

_RA = {"M16HUB": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "M14": "M14.QUE.LOAD.AVGLOADTIME1MIN",
       "M14B": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "M16A": "M16A.QUE.LOAD.AVGLOADTIME1MIN",
       "M16B": "M16B.QUE.LOAD.AVGLOADTIME1MIN"}
_FAB = "M16HUB.STRATE.ALL.FABSTORAGERATIO"
_STB = "M16HUB.STRATE.STB.3F_STORAGE_UTIL"
_REV = "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT"

# ── 다크 테마 (dashboard.html CSS 변수와 동일) ──
_BG = "#0D1119"      # --panel
_BG2 = "#0F1622"     # 스코어 패널 정상 구간
_LINE = "#1C2431"    # --line
_GRID = "#2E3A4C"    # 눈금선
_TX = "#E6EDF6"      # --tx
_TX2 = "#8FA0B6"     # --tx2
_TX3 = "#5E6E85"     # --tx3

# 지표 패널 색 — 반송시간(빨강) → 저장율(주황/호박) → 리프터(자홍) → 4분초과율(청록/파랑)
# 어두운 배경에서 읽히도록 밝기를 올린 값
_PALETTE = ["#FF6B5E", "#FFA53D", "#F2C94C", "#FF6FB5", "#3DDBE8", "#5FB8FF", "#7C9CFF"]
# 지표 종류별 고정 색 (같은 지표는 항상 같은 색)
_COLOR_BY_KIND = {
    "ra": "#FF6B5E",        # 반송시간
    "rd_fab": "#FFA53D",    # FAB저장율
    "stb_util": "#F2C94C",  # STB저장율
    "rev_count": "#FF6FB5",  # 리프터 정체
    "sla": "#3DDBE8",       # 4분초과율
    "sorter": "#5FB8FF",    # 분류기 대기
    "rd_oht": "#7C9CFF",    # OHT가동률
}
_SCORE_COLOR = "#3DDBE8"   # --cy
_SEL_COLOR = "#E6EDF6"     # 더블클릭한 시각 표시색 (밝게)
_EVT_COLOR = "#FF9F2E"     # --major
_CRIT_COLOR = "#FF4D5E"    # --crit
# 등급 밴드 — 다크 배경 위에 등급색을 옅게 깐 톤. 경계선은 시스템별
# 설정(grade.by_sys)을 따르므로 그릴 때 cfg 로 계산한다.
_BAND_COLORS = (_BG2, "#2B2612", "#33210F", "#331419")


def _bands_of(cfg) -> list:
    from sentinel import grade_cuts
    w, d, c = grade_cuts(cfg or {})
    edges = (0, w, d, c, 100)
    return [(edges[i], edges[i + 1], _BAND_COLORS[i]) for i in range(4)]


def _kind_color(col: str, idx: int) -> str:
    """컬럼명으로 지표 종류를 알아 고정 색을 준다 (사진과 같은 색 배치)."""
    for key, c in _COLOR_BY_KIND.items():
        if col.endswith("_" + key) or col.startswith(key + "_") or col.endswith(key):
            return c
    return _PALETTE[idx % len(_PALETTE)]


def parse_reason_metrics(reason: str) -> list[dict]:
    """reason → [{col, raw, label, unit}] (등장 순서, 중복 제거, M16_PKT/M16_WT 제외)."""
    out, seen = [], set()
    body = (reason or "").split("발동:", 1)[-1]
    body = re.split(r"흐름:|운영자조치:", body)[0]

    def add(col, raw, label, unit):
        if col and col not in seen and not any(x in col for x in ("M16_PKT", "M16_WT")):
            seen.add(col)
            out.append({"col": col, "raw": raw, "label": label, "unit": unit})

    for m in re.finditer(r"(M16HUB|M14B|M16A|M16B|M14)\s*\[(.*?)\]", body):
        area, inner = m.group(1), m.group(2)
        if "AVGTOTALTIME1MIN" in inner or "AVGLOADTIME1MIN" in inner or "R-A" in inner:
            add(f"{area}_ra", _RA.get(area, f"{area}.QUE.TIME.AVGTOTALTIME1MIN"),
                f"{area} 반송시간", "분")
        if "FAB저장" in inner:
            add("M16HUB_rd_fab", _FAB, "M16HUB FAB저장율", "%")
        if re.search(r"\bSTB", inner):
            # R-D 판정에서 빠진 값이다 (2026-08) — 기록용임을 이름에 남긴다
            add("M16HUB_stb_util", _STB, "M16HUB STB저장율 (기록용)", "%")
        if "OHT=" in inner or "OHT가동" in inner:
            add(f"{area}_rd_oht", f"{area}.QUE.OHT.OHTUTIL", f"{area} OHT가동률", "%")
        if "R-C" in inner:
            add("M16HUB_rev_count", _REV, "M16HUB 리프터 정체", "회")
        if "SLA(" in inner or "4분초과" in inner:
            add(f"sla_{area}", f"{area}.QUE.ALL.TRANSPORT4MINOVERRATIO", f"{area} 4분초과율", "%")
        if "SORT(" in inner or "소터" in inner:
            add(f"sorter_{area}", f"{area}.SORTER.ABN.SORTERWAITCOUNTOVER", f"{area} 분류기 대기", "건")
    return out


def _f(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _e(s):
    return html.escape(str(s), quote=True)


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def window_rows(rows, center, minutes=60, cfg=None):
    cfg = cfg or load_config()
    tc = cfg.get("amos", {}).get("base_time_col", "datetime")
    half = timedelta(minutes=minutes / 2)
    lo, hi = center - half, center + half
    out = [(parse_dt(r.get(tc)), r) for r in rows]
    out = [(t, r) for t, r in out if t and lo <= t <= hi]
    out.sort(key=lambda x: x[0])
    return out


def _incidents(pts, floor=60):
    """점수가 임계 이상인 연속 구간마다 최고점 1개."""
    out, run = [], []
    for t, r in pts:
        sc = _f(r.get("unified_risk_score")) or 0
        if sc >= floor:
            run.append((t, r, sc))
        elif run:
            out.append(max(run, key=lambda x: x[2]))
            run = []
    if run:
        out.append(max(run, key=lambda x: x[2]))
    return out


def render(rows, center, minutes=60, width=1000, cfg=None) -> str:
    cfg = cfg or load_config()
    pts = window_rows(rows, center, minutes, cfg)
    if not pts:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="110">'
                '<rect width="100%%" height="100%%" fill="%s"/>'
                '<text x="%d" y="60" fill="%s" font-size="14" text-anchor="middle">'
                '해당 구간에 데이터가 없습니다</text></svg>'
                % (width, _BG, width // 2, _TX2))

    from sentinel import grade_cuts
    floor = grade_cuts(cfg)[0]
    t0, t1 = pts[0][0], pts[-1][0]
    span = max(1.0, (t1 - t0).total_seconds())
    incs = _incidents(pts, floor)
    peak_t, peak_r, peak_sc = max(
        ((t, r, _f(r.get("unified_risk_score")) or 0) for t, r in pts), key=lambda x: x[2])
    pts_sc = [(t, r, _f(r.get("unified_risk_score")) or 0) for t, r in pts]
    metrics = parse_reason_metrics(peak_r.get("reason") or "")
    area = (peak_r.get("hot_area") or "").strip()

    L, R = 62, 22
    pw = width - L - R
    SCORE_H, MET_H, GAP = 150, 88, 12
    head = 50                       # 제목 + 최고점 라벨 + 사건 라벨 3줄 공간
    sec_head = 30 if metrics else 0
    top_score = head
    y_met0 = top_score + SCORE_H + 18 + sec_head
    height = y_met0 + (MET_H + GAP) * len(metrics) + 34

    def X(t):
        return L + pw * ((t - t0).total_seconds() / span)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" '
         f'font-family="-apple-system,Segoe UI,Malgun Gothic,sans-serif">',
         f'<rect width="100%" height="100%" fill="{_BG}"/>']

    # ── 제목 ──
    o.append(f'<text x="{L-46}" y="21" font-size="14" font-weight="700" fill="{_TX}">'
             f'📅 {t0:%Y-%m-%d} M16 BR 구간 ({len(incs)}건) · {t0:%H:%M}~{t1:%H:%M}</text>')

    # ── 스코어 패널 ──
    def SY(v):
        return top_score + SCORE_H * (1 - max(0.0, min(100.0, v)) / 100.0)

    bands = _bands_of(cfg)
    for lo_, hi_, col in bands:
        y2, y1 = SY(lo_), SY(hi_)
        o.append(f'<rect x="{L}" y="{y1:.1f}" width="{pw}" height="{y2-y1:.1f}" fill="{col}"/>')
    for v in [b[0] for b in bands[1:]] + [100]:
        y = SY(v)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="{_GRID}" '
                 f'stroke-width="0.8" stroke-dasharray="3 3"/>')
        o.append(f'<text x="{L-7}" y="{y+4:.1f}" font-size="10" fill="{_TX2}" '
                 f'text-anchor="end">{v}</text>')

    sv = [(t, _f(r.get("unified_risk_score")) or 0) for t, r in pts]
    d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{SY(v):.1f}" for k, (t, v) in enumerate(sv))
    o.append(f'<path d="{d}" fill="none" stroke="{_SCORE_COLOR}" stroke-width="1.6"/>')

    # 사건 표시
    for i, (it, ir, isc) in enumerate(incs, 1):
        x = X(it)
        o.append(f'<line x1="{x:.1f}" y1="{top_score}" x2="{x:.1f}" y2="{top_score+SCORE_H}" '
                 f'stroke="{_EVT_COLOR}" stroke-width="1" stroke-dasharray="4 3" opacity="0.85"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{SY(isc):.1f}" r="3.4" fill="{_EVT_COLOR}"/>')
        o.append(f'<text x="{x:.1f}" y="{SY(isc)-7:.1f}" font-size="9.5" fill="{_EVT_COLOR}" '
                 f'font-weight="700" text-anchor="middle">{isc:.0f}점</text>')
        o.append(f'<text x="{x:.1f}" y="{top_score-5:.1f}" font-size="9" fill="{_EVT_COLOR}" '
                 f'text-anchor="middle">사건{i} {isc:.0f}점 @{it:%H:%M}</text>')

    # 최고점 라벨은 사건 라벨보다 한 줄 위 (겹침 방지)
    o.append(f'<text x="{X(peak_t):.1f}" y="{top_score-19:.1f}" font-size="10.5" '
             f'fill="{_CRIT_COLOR}" font-weight="700" text-anchor="middle">'
             f'▲ 최고 {peak_sc:.0f}점 · {peak_t:%H:%M}{" · " + _e(area) if area else ""}</text>')

    # ── 더블클릭한 시각 표시 (선택 시각 + 그 시각 스코어) ──
    sel_t, sel_r, sel_sc = min(pts_sc, key=lambda x: abs((x[0] - center).total_seconds()))
    sx = X(sel_t)
    o.append(f'<line x1="{sx:.1f}" y1="{top_score}" x2="{sx:.1f}" y2="{top_score+SCORE_H}" '
             f'stroke="{_SEL_COLOR}" stroke-width="1.4" opacity="0.8"/>')
    o.append(f'<circle cx="{sx:.1f}" cy="{SY(sel_sc):.1f}" r="4.6" fill="{_BG}" '
             f'stroke="{_SEL_COLOR}" stroke-width="2.2"/>')
    _lb = f'선택 {sel_t:%H:%M} · {sel_sc:.0f}점'
    _lw = len(_lb) * 6.2 + 12
    _lx = max(L + 2, min(L + pw - _lw - 2, sx - _lw / 2))
    _ly = SY(sel_sc) + (16 if sel_sc > 60 else -30)
    o.append(f'<rect x="{_lx:.1f}" y="{_ly:.1f}" width="{_lw:.1f}" height="19" rx="4" '
             f'fill="{_SEL_COLOR}"/>')
    o.append(f'<text x="{_lx+_lw/2:.1f}" y="{_ly+13.5:.1f}" font-size="10.5" fill="{_BG}" '
             f'font-weight="700" text-anchor="middle">{_e(_lb)}</text>')

    # 스코어 = 실제 컬럼명 명시
    o.append(f'<text x="{L}" y="{top_score+SCORE_H+14:.1f}" font-size="10.5" '
             f'fill="{_SCORE_COLOR}" font-weight="700">스코어</text>')
    o.append(f'<text x="{L+44}" y="{top_score+SCORE_H+14:.1f}" font-size="9.5" fill="{_TX2}" '
             f'font-family="ui-monospace,Menlo,Consolas,monospace">unified_risk_score</text>')

    # ── 지표 섹션 ──
    if metrics:
        o.append(f'<text x="{L-46}" y="{top_score+SCORE_H+40:.1f}" font-size="11" '
                 f'fill="{_TX}" font-weight="700">'
                 f'최고점({peak_t:%H:%M} · {peak_sc:.0f}점{" · " + _e(area) if area else ""}) '
                 f'발동 지표 — 실제 raw 컬럼 {minutes}분 추이</text>')

    for i, md in enumerate(metrics):
        y = y_met0 + (MET_H + GAP) * i
        col = _kind_color(md["col"], i)
        vals = [(t, _f(r.get(md["col"]))) for t, r in pts]
        vals = [(t, v) for t, v in vals if v is not None]

        o.append(f'<rect x="{L-46}" y="{y}" width="4" height="{MET_H}" fill="{col}" rx="2"/>')
        o.append(f'<text x="{L-38}" y="{y+12}" font-size="11.5" font-weight="700" fill="{col}">'
                 f'{_e(md["label"])} ({_e(md["unit"])})</text>')
        o.append(f'<text x="{L-38}" y="{y+26}" font-size="9" fill="{_TX2}" '
                 f'font-family="ui-monospace,Menlo,Consolas,monospace">{_e(md["raw"])}</text>')

        if len(vals) < 2:
            o.append(f'<text x="{L-38}" y="{y+44}" font-size="9.5" fill="{_TX3}">데이터 없음</text>')
            continue

        vmin = min(v for _, v in vals)
        vmax = max(v for _, v in vals)
        rng = (vmax - vmin) or 1.0
        o.append(f'<text x="{L-38}" y="{y+39}" font-size="9" fill="{_TX3}">'
                 f'범위 {_fmt(vmin)}~{_fmt(vmax)}{_e(md["unit"])}</text>')

        pt, pb = y + 6, y + MET_H - 10

        def MY(v):
            return pb - (pb - pt) * ((v - vmin) / rng)

        o.append(f'<line x1="{L}" y1="{pb:.1f}" x2="{L+pw}" y2="{pb:.1f}" stroke="{_LINE}"/>')
        area_d = (f"M{X(vals[0][0]):.1f},{pb:.1f} "
                  + " ".join(f"L{X(t):.1f},{MY(v):.1f}" for t, v in vals)
                  + f" L{X(vals[-1][0]):.1f},{pb:.1f} Z")
        o.append(f'<path d="{area_d}" fill="{col}" opacity="0.20"/>')
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{MY(v):.1f}"
                     for k, (t, v) in enumerate(vals))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.4"/>')

        # 사건 시각의 실제 값 표시
        vmap = dict(vals)
        for it, _ir, _isc in incs:
            x = X(it)
            o.append(f'<line x1="{x:.1f}" y1="{pt:.1f}" x2="{x:.1f}" y2="{pb:.1f}" '
                     f'stroke="{_EVT_COLOR}" stroke-width="0.9" stroke-dasharray="4 3" opacity="0.8"/>')
            v = vmap.get(it)
            if v is None:
                continue
            o.append(f'<circle cx="{x:.1f}" cy="{MY(v):.1f}" r="2.8" fill="{_EVT_COLOR}"/>')
            o.append(f'<text x="{x+4:.1f}" y="{MY(v)-5:.1f}" font-size="9" fill="{_EVT_COLOR}" '
                     f'font-weight="700">{_fmt(v)}{_e(md["unit"])}</text>')

        # 선택 시각 — 지표 패널에도 세로선 + 그 시각 실제 값
        o.append(f'<line x1="{sx:.1f}" y1="{pt:.1f}" x2="{sx:.1f}" y2="{pb:.1f}" '
                 f'stroke="{_SEL_COLOR}" stroke-width="1.2" opacity="0.55"/>')
        sv_ = vmap.get(sel_t)
        if sv_ is not None:
            o.append(f'<circle cx="{sx:.1f}" cy="{MY(sv_):.1f}" r="3.4" fill="{_BG}" '
                     f'stroke="{_SEL_COLOR}" stroke-width="1.8"/>')
            _t = f'{_fmt(sv_)}{md["unit"]}'
            _tw = len(_t) * 6.0
            _tx = max(L + _tw / 2, min(L + pw - _tw / 2, sx))
            o.append(f'<text x="{_tx:.1f}" y="{pt+9:.1f}" font-size="9" fill="{_SEL_COLOR}" '
                     f'font-weight="700" text-anchor="middle">{_e(_t)}</text>')

    # ── X 축 ──
    ybase = height - 20
    step = max(1, int(minutes // 8))
    tick = t0
    while tick <= t1:
        x = X(tick)
        o.append(f'<text x="{x:.1f}" y="{ybase}" font-size="9.5" fill="{_TX2}" '
                 f'text-anchor="middle">{tick:%H:%M}</text>')
        tick += timedelta(minutes=step)

    o.append("</svg>")
    return "".join(o)
