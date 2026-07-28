#!/usr/bin/env python3
"""
AMHS Sentinel — 구간 그래프 (독립 SVG 렌더러)

발동이벤트_요약 / report_graphs 와 같은 규칙으로 그린다:
  · 주선   = unified_risk_score (등급 밴드 50/71/85 배경)
  · 보조선 = 최고점 reason 에서 뽑은 raw 지표들 (M16HUB_ra, STB저장율 …)

데모스를 import 하지 않는다. 외부 라이브러리도 쓰지 않는다(순수 SVG 문자열).
"""
from __future__ import annotations

import html
import re
from datetime import timedelta

from lp_client import load_config, parse_dt

# reason → 실제 CSV 컬럼 매핑 (report_graphs.parse_reason_metrics 와 동일 규칙)
_RA = {"M16HUB": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "M14": "M14.QUE.LOAD.AVGLOADTIME1MIN",
       "M14B": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "M16A": "M16A.QUE.LOAD.AVGLOADTIME1MIN",
       "M16B": "M16B.QUE.LOAD.AVGLOADTIME1MIN"}
_FAB = "M16HUB.STRATE.ALL.FABSTORAGERATIO"
_STB = "M16HUB.STRATE.STB.3F_STORAGE_UTIL"
_REV = "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT"

_PALETTE = ["#dc2626", "#ea580c", "#d97706", "#16a34a", "#0891b2", "#7c3aed", "#db2777"]
_SCORE_COLOR = "#3DDBE8"


def parse_reason_metrics(reason: str) -> list[dict]:
    """reason → [{col, raw, label, unit}]  (등장 순서, 중복 제거, M16_PKT/M16_WT 제외)."""
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
            add("M16HUB_stb_util", _STB, "M16HUB STB저장율", "%")
        if "OHT=" in inner or "OHT가동" in inner:
            add(f"{area}_rd_oht", f"{area}.QUE.OHT.OHTUTIL", f"{area} OHT가동률", "%")
        if "R-C" in inner:
            add("M16HUB_rev_count", _REV, "M16HUB 리프터 정체", "대")
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


def _esc(s):
    return html.escape(str(s), quote=True)


def window_rows(rows: list[dict], center, minutes: int = 60, cfg: dict | None = None):
    """center 를 가운데 둔 minutes 분 구간 행을 시간순으로 추린다."""
    cfg = cfg or load_config()
    tc = cfg.get("amos", {}).get("base_time_col", "datetime")
    half = timedelta(minutes=minutes / 2)
    lo, hi = center - half, center + half
    out = []
    for r in rows:
        t = parse_dt(r.get(tc))
        if t and lo <= t <= hi:
            out.append((t, r))
    out.sort(key=lambda x: x[0])
    return out


def render(rows: list[dict], center, minutes: int = 60,
           width: int = 1000, height: int = 420, cfg: dict | None = None) -> str:
    """1시간 구간 그래프 SVG. 데이터가 없으면 안내 문구 SVG."""
    cfg = cfg or load_config()
    pts = window_rows(rows, center, minutes, cfg)
    if not pts:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="120">'
                f'<rect width="100%" height="100%" fill="#0D1119"/>'
                f'<text x="{width//2}" y="64" fill="#8FA0B6" font-size="14" '
                f'text-anchor="middle">해당 구간에 데이터가 없습니다</text></svg>')

    L, R, T, B = 58, 150, 28, 46
    pw, ph = width - L - R, height - T - B
    t0, t1 = pts[0][0], pts[-1][0]
    span = max(1.0, (t1 - t0).total_seconds())

    def x_of(t):
        return L + pw * ((t - t0).total_seconds() / span)

    def y_of(v):                       # 점수축 0~100
        return T + ph * (1 - max(0.0, min(100.0, v)) / 100.0)

    # 최고점 행에서 지표 정의를 뽑는다 (발동이벤트_요약 규칙과 동일)
    peak_t, peak_r = max(pts, key=lambda p: _f(p[1].get("unified_risk_score")) or 0)
    metrics = parse_reason_metrics(peak_r.get("reason") or "")

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Malgun Gothic,sans-serif">',
         f'<rect width="100%" height="100%" fill="#0D1119"/>']

    # 등급 밴드
    for lo_, hi_, col in ((50, 71, "#F2D338"), (71, 85, "#FF9F2E"), (85, 100, "#FF4D5E")):
        y2, y1 = y_of(lo_), y_of(hi_)
        o.append(f'<rect x="{L}" y="{y1:.1f}" width="{pw}" height="{y2-y1:.1f}" '
                 f'fill="{col}" opacity="0.06"/>')
        o.append(f'<line x1="{L}" y1="{y2:.1f}" x2="{L+pw}" y2="{y2:.1f}" '
                 f'stroke="{col}" stroke-width="1" stroke-dasharray="3 3" opacity="0.45"/>')
        o.append(f'<text x="{L-8}" y="{y2+4:.1f}" fill="{col}" font-size="10" '
                 f'text-anchor="end">{lo_}</text>')

    # 축
    o.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" stroke="#26303f"/>')
    o.append(f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" stroke="#26303f"/>')
    o.append(f'<text x="{L-8}" y="{T+ph+4}" fill="#5E6E85" font-size="10" text-anchor="end">0</text>')
    o.append(f'<text x="{L-8}" y="{T+4}" fill="#5E6E85" font-size="10" text-anchor="end">100</text>')

    # X 눈금 (10분 간격)
    step = max(1, int(minutes // 6))
    tick = t0
    while tick <= t1:
        x = x_of(tick)
        o.append(f'<line x1="{x:.1f}" y1="{T+ph}" x2="{x:.1f}" y2="{T+ph+4}" stroke="#26303f"/>')
        o.append(f'<text x="{x:.1f}" y="{T+ph+18}" fill="#5E6E85" font-size="10" '
                 f'text-anchor="middle">{tick:%H:%M}</text>')
        tick += timedelta(minutes=step)

    # 보조 지표선 (각자 자기 범위로 정규화 → 0~100 축에 겹쳐 그림)
    legend = []
    for i, md in enumerate(metrics[:6]):
        vals = [(t, _f(r.get(md["col"]))) for t, r in pts]
        vals = [(t, v) for t, v in vals if v is not None]
        if len(vals) < 2:
            continue
        vmin = min(v for _, v in vals)
        vmax = max(v for _, v in vals)
        rng = (vmax - vmin) or 1.0
        col = _PALETTE[i % len(_PALETTE)]
        d = " ".join(f"{'M' if k == 0 else 'L'}{x_of(t):.1f},{T + ph * (1 - (v - vmin) / rng * 0.92) - 6:.1f}"
                     for k, (t, v) in enumerate(vals))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" '
                 f'opacity="0.9" stroke-linejoin="round"/>')
        legend.append((col, md["label"], f"{vmin:g}~{vmax:g}{md['unit']}", md["raw"]))

    # 점수 주선
    sv = [(t, _f(r.get("unified_risk_score")) or 0) for t, r in pts]
    d = " ".join(f"{'M' if k == 0 else 'L'}{x_of(t):.1f},{y_of(v):.1f}"
                 for k, (t, v) in enumerate(sv))
    o.append(f'<path d="{d}" fill="none" stroke="{_SCORE_COLOR}" stroke-width="2.6" '
             f'stroke-linejoin="round"/>')

    # 최고점 표시
    px, py = x_of(peak_t), y_of(_f(peak_r.get("unified_risk_score")) or 0)
    o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{_SCORE_COLOR}"/>')
    o.append(f'<text x="{px:.1f}" y="{py-10:.1f}" fill="{_SCORE_COLOR}" font-size="11" '
             f'font-weight="700" text-anchor="middle">'
             f'{_f(peak_r.get("unified_risk_score")):.0f}점 {peak_t:%H:%M}</text>')

    # 선택 시각 세로선
    cx = x_of(min(max(center, t0), t1))
    o.append(f'<line x1="{cx:.1f}" y1="{T}" x2="{cx:.1f}" y2="{T+ph}" '
             f'stroke="#E6EDF6" stroke-width="1" stroke-dasharray="4 3" opacity="0.5"/>')

    # 범례
    ly = T + 6
    o.append(f'<text x="{L+pw+14}" y="{ly}" fill="{_SCORE_COLOR}" font-size="11" '
             f'font-weight="700">■ 위험 점수</text>')
    for col, label, rng, raw in legend:
        ly += 20
        o.append(f'<text x="{L+pw+14}" y="{ly}" fill="{col}" font-size="10.5">'
                 f'■ {_esc(label)}</text>')
        ly += 12
        o.append(f'<text x="{L+pw+24}" y="{ly}" fill="#5E6E85" font-size="9.5">{_esc(rng)}</text>')
    if not legend:
        o.append(f'<text x="{L+pw+14}" y="{ly+20}" fill="#5E6E85" font-size="10">'
                 f'(reason 지표 없음)</text>')

    o.append(f'<text x="{L}" y="{T-10}" fill="#8FA0B6" font-size="11.5">'
             f'{t0:%Y-%m-%d %H:%M} ~ {t1:%H:%M} · {len(pts)}분 · 보조선은 각 지표 범위로 정규화</text>')
    o.append("</svg>")
    return "".join(o)
