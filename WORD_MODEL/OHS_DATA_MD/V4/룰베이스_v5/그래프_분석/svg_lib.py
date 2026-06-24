#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 SVG 빌더 — 발동이벤트 24h / 위험사건 그래프에서 공유.

표준 라이브러리만 사용 (matplotlib 불필요).
"""
import os
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

# ─────────────────────────────────────────────────────────────
# 발동이벤트 raw 컬럼 매핑 (reason 의 원본 컬럼 → 발동이벤트 컬럼)
# ─────────────────────────────────────────────────────────────
# reason 안의 컬럼명은 raw 데이터 컬럼명. 발동이벤트.csv 에는 축약형으로 들어있다.
COL_MAP_RAW_TO_EVT = {
    # 반송시간
    'M16HUB.QUE.TIME.AVGTOTALTIME1MIN':  'M16HUB_ra',
    'M14.QUE.LOAD.AVGLOADTIME1MIN':      'M14_ra',
    'M14B.QUE.TIME.AVGTOTALTIME1MIN':    'M14B_ra',
    'M16A.QUE.LOAD.AVGLOADTIME1MIN':     'M16A_ra',
    'M16B.QUE.LOAD.AVGLOADTIME1MIN':     'M16B_ra',
    # 저장
    'M16HUB.STRATE.ALL.FABSTORAGERATIO': 'M16HUB_rd_fab',
    'M16HUB.STRATE.STB.3F_STORAGE_UTIL': 'M16HUB_stb_util',
    # OHT
    'M14.QUE.OHT.OHTUTIL':                'M14_rd_oht',
    'M14B.QUE.OHT.OHTUTIL':               'M14B_rd_oht',
    'M16A.QUE.OHT.OHTUTIL':               'M16A_rd_oht',
    'M16B.QUE.OHT.OHTUTIL':               'M16B_rd_oht',
    # SLA
    'M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO': 'sla_M16HUB',
    'M14.QUE.ALL.TRANSPORT4MINOVERRATIO':    'sla_M14',
    'M14B.QUE.ALL.TRANSPORT4MINOVERRATIO':   'sla_M14B',
    'M16A.QUE.ALL.TRANSPORT4MINOVERRATIO':   'sla_M16A',
    'M16B.QUE.ALL.TRANSPORT4MINOVERRATIO':   'sla_M16B',
    # Sorter
    'M14.SORTER.ABN.SORTERWAITCOUNTOVER':  'sorter_M14',
    'M14B.SORTER.ABN.SORTERWAITCOUNTOVER': 'sorter_M14B',
    'M16A.SORTER.ABN.SORTERWAITCOUNTOVER': 'sorter_M16A',
    'M16B.SORTER.ABN.SORTERWAITCOUNTOVER': 'sorter_M16B',
    'M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER':'sorter_M16HUB',
    # R-C 리프터 역증가
    '리프터역증가': 'M16HUB_rev_count',
}


def short_label(col):
    """발동이벤트 축약형 컬럼 → 사람 읽는 라벨."""
    if col.endswith('_ra'):
        a = col.replace('_ra',''); return f"{a} 반송시간 (분)"
    if col == 'M16HUB_rd_fab': return "M16HUB FAB 저장율 (%)"
    if col == 'M16HUB_stb_util': return "M16HUB STB 저장율 (%)"
    if col == 'M16HUB_rev_count': return "M16HUB 리프터 역증가 (대)"
    if col.endswith('_rd_oht'):
        a = col.replace('_rd_oht',''); return f"{a} OHT 가동률 (%)"
    if col.startswith('sla_'):
        a = col.replace('sla_',''); return f"{a} 4분초과 (%)"
    if col.startswith('sorter_'):
        a = col.replace('sorter_',''); return f"{a} Sorter 대기 (LOT)"
    return col


# ─────────────────────────────────────────────────────────────
# 등급 배경 색
# ─────────────────────────────────────────────────────────────
LEVEL_BANDS = [
    (0,   100, '#F0FDF4', '정상'),
    (100, 120, '#DBEAFE', '관심'),
    (120, 130, '#FEF9C3', '주의'),
    (130, 160, '#FED7AA', '경계'),
    (160, 220, '#FECACA', '위험'),
    (220, 500, '#FCA5A5', '발동'),
]

COLORS = ['#2563EB','#DC2626','#059669','#D97706','#7C3AED','#0891B2','#DB2777','#65A30D','#EA580C','#0D9488']


# ─────────────────────────────────────────────────────────────
# 24시간 점수 추이 그래프
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# 24시간 통합 그래프 — 상단 점수 추이 + 하단 최고점 reason 컬럼 시계열
# ─────────────────────────────────────────────────────────────
def make_24h_combined_svg(day, score_data, peak, raw_series, friendly_map=None):
    """
    score_data = [{'t', 'score', 'level', 'hot'}, ...]  매분
    peak       = {'t', 'score', 'level', 'hot', 'reason'}
    raw_series = {col: [(t, val), ...]}  최고점 reason 의 컬럼들 24h 시계열
                 ★ key 는 **raw 풀네임 권장** (M16HUB.QUE.TIME.AVGTOTALTIME1MIN).
                    축약 컬럼 (M16HUB_ra) 도 호환 — friendly_map 으로 라벨 결정.
    friendly_map = {col: "한글 라벨 (단위)"} — 좌측 큰 라벨용 (없으면 short_label())
    """
    friendly_map = friendly_map or {}
    from collections import Counter
    levels = Counter(d['level'] for d in score_data)
    t0 = datetime.strptime(f'{day} 00:00', '%Y-%m-%d %H:%M')
    t1 = datetime.strptime(f'{day} 23:59', '%Y-%m-%d %H:%M')
    total_sec = (t1 - t0).total_seconds()

    W = 1400
    H_SCORE = 360
    H_PER = 110
    PAD_L, PAD_R, PAD_T, PAD_B = 220, 100, 140, 80
    n_sub = len(raw_series)
    H = PAD_T + H_SCORE + 30 + H_PER * n_sub + PAD_B
    plot_w = W - PAD_L - PAD_R
    def tx(t): return PAD_L + (t - t0).total_seconds() / total_sec * plot_w

    y_s_top = PAD_T
    y_s_bot = PAD_T + H_SCORE
    Y_MAX = 250
    def ty_score(v): return y_s_bot - (min(v, Y_MAX) / Y_MAX) * H_SCORE

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Malgun Gothic, AppleGothic, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        f'<text x="{W//2}" y="32" text-anchor="middle" font-size="22" font-weight="700" fill="#111827">'
        f'{day} 발동이벤트 24시간 분석</text>',
        f'<text x="{W//2}" y="54" text-anchor="middle" font-size="13" fill="#6B7280">'
        f'최고 {peak["score"]}점 [{peak["level"]}] @ {peak["t"].strftime("%H:%M")} (hot={peak["hot"]}) · '
        f'정상 {levels.get("정상",0)} · 관심 {levels.get("관심",0)} · 주의 {levels.get("주의",0)} · '
        f'경계 {levels.get("경계",0)} · 위험 {levels.get("위험",0)} · 발동 {levels.get("발동",0)}</text>',
        f'<text x="{PAD_L}" y="92" font-size="11" fill="#374151" font-weight="600">등급 :</text>',
    ]
    xx = PAD_L + 42
    for v0, v1, color, name in LEVEL_BANDS[:-1]:
        svg.append(f'<rect x="{xx}" y="82" width="14" height="12" fill="{color}" stroke="#D1D5DB"/>')
        svg.append(f'<text x="{xx+18}" y="92" font-size="11" fill="#374151">{name} ({v0}~{v1})</text>')
        xx += 100

    # ── ① 상단: 점수 추이 ──
    svg.append(f'<text x="{PAD_L-8}" y="{y_s_top - 10}" font-size="13" font-weight="700" fill="#111827">'
               f'① unified_risk_score 추이 (점수 0~{Y_MAX}+)</text>')
    # 등급 배경 밴드
    for v0, v1, color, name in LEVEL_BANDS:
        if v0 >= Y_MAX: continue
        y_a = ty_score(min(v1, Y_MAX)); y_b = ty_score(v0)
        svg.append(f'<rect x="{PAD_L}" y="{y_a:.1f}" width="{plot_w}" height="{y_b-y_a:.1f}" '
                   f'fill="{color}" opacity="0.45"/>')
    for v in [0, 100, 120, 130, 160, 220]:
        if v > Y_MAX: continue
        y = ty_score(v)
        if v > 0:
            svg.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+plot_w}" y2="{y:.1f}" '
                       f'stroke="#9CA3AF" stroke-width="0.7" stroke-dasharray="3,3"/>')
        svg.append(f'<text x="{PAD_L-6}" y="{y:.1f}" text-anchor="end" font-size="10" fill="#6B7280" '
                   f'dominant-baseline="middle">{v}</text>')
    # 점수 선
    path = " ".join(f"{'M' if i==0 else 'L'}{tx(d['t']):.1f},{ty_score(d['score']):.1f}"
                    for i, d in enumerate(score_data))
    svg.append(f'<path d="{path}" stroke="#1F2937" stroke-width="1.4" fill="none" stroke-linejoin="round"/>')
    # 최고점 마커
    mx, my = tx(peak['t']), ty_score(peak['score'])
    svg.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="6" fill="#DC2626" stroke="#fff" stroke-width="2"/>')
    svg.append(f'<text x="{mx:.1f}" y="{my-13:.1f}" text-anchor="middle" font-size="12" '
               f'fill="#DC2626" font-weight="700">{peak["score"]}점 @ {peak["t"].strftime("%H:%M")}</text>')
    # 우측 등급 라벨
    for v0, v1, color, name in LEVEL_BANDS:
        if v0 >= Y_MAX: continue
        y_mid = (ty_score(v0) + ty_score(v1)) / 2
        svg.append(f'<text x="{PAD_L + plot_w + 5}" y="{y_mid:.1f}" font-size="11" '
                   f'fill="#374151" dominant-baseline="middle">{name}</text>')
    # x축 (점수 그래프 아래)
    def draw_xticks(y_x):
        for h in range(0, 25, 3):
            tt = datetime.strptime(f'{day} {h:02d}:00', '%Y-%m-%d %H:%M') if h < 24 else t1
            x = tx(tt)
            svg.append(f'<line x1="{x:.1f}" y1="{y_x}" x2="{x:.1f}" y2="{y_x+4}" stroke="#6B7280"/>')
            svg.append(f'<text x="{x:.1f}" y="{y_x+16}" text-anchor="middle" font-size="10" fill="#6B7280">{h:02d}</text>')
    draw_xticks(y_s_bot)

    # ── ② 하단: reason 컬럼들 24h ──
    y_sec = y_s_bot + 60
    svg.append(f'<text x="{PAD_L-8}" y="{y_sec - 20}" font-size="13" font-weight="700" fill="#111827">'
               f'② 최고점({peak["t"].strftime("%H:%M")}) reason 발동 컬럼 — 24시간 추이</text>')

    # 라벨 결정 — friendly_map 우선, 없으면 COL_MAP_RAW_TO_EVT 역추론, 그것도 없으면 col 그대로
    raw_to_orig_legacy = {v: k for k, v in COL_MAP_RAW_TO_EVT.items() if v != 'M16HUB_rev_count'}
    raw_to_orig_legacy['M16HUB_rev_count'] = 'M16HUB.LFT (리프터 역증가 개수)'

    def _resolve(col):
        # 한글 친화 라벨
        nice = friendly_map.get(col) or short_label(col)
        # 풀네임 (monospace 표시용) — col 자체가 raw 풀네임이면 그대로, 아니면 역매핑
        if '.' in col:
            mono = col
        else:
            mono = raw_to_orig_legacy.get(col, col)
        return nice, mono

    for k, (col, pts) in enumerate(raw_series.items()):
        nice, mono = _resolve(col)
        color = COLORS[k % len(COLORS)]
        y_top = y_sec + k * H_PER
        y_bot = y_top + H_PER - 25
        plot_h = y_bot - y_top
        svg.append(f'<rect x="{PAD_L}" y="{y_top}" width="{plot_w}" height="{plot_h}" '
                   f'fill="#FAFAFA" stroke="#E5E7EB" stroke-width="1"/>')
        svg.append(f'<text x="{PAD_L-12}" y="{y_top+plot_h/2-7}" text-anchor="end" font-size="12" '
                   f'fill="#1F2937" font-weight="700" dominant-baseline="middle">{escape(nice)}</text>')
        svg.append(f'<text x="{PAD_L-12}" y="{y_top+plot_h/2+9}" text-anchor="end" font-size="9" '
                   f'fill="#9CA3AF" font-family="Consolas,monospace" dominant-baseline="middle">{escape(mono)}</text>')

        if not pts:
            svg.append(f'<text x="{PAD_L+plot_w/2}" y="{y_top+plot_h/2}" text-anchor="middle" font-size="11" fill="#9CA3AF">(데이터 없음)</text>')
            continue
        vmin = min(v for _, v in pts); vmax = max(v for _, v in pts)
        rng = max(vmax-vmin, 1e-9)
        vmin_d, vmax_d = vmin - rng*0.05, vmax + rng*0.08
        def ty(v): return y_bot - (v-vmin_d)/(vmax_d-vmin_d)*plot_h
        for frac in (0.25, 0.5, 0.75):
            y = y_top + plot_h*frac
            svg.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+plot_w}" y2="{y:.1f}" stroke="#F3F4F6"/>')
        svg.append(f'<text x="{PAD_L-6}" y="{y_top+3}" text-anchor="end" font-size="9" fill="#6B7280" dominant-baseline="hanging">{vmax:.1f}</text>')
        svg.append(f'<text x="{PAD_L-6}" y="{y_bot-3}" text-anchor="end" font-size="9" fill="#6B7280">{vmin:.1f}</text>')
        path = " ".join(f"{'M' if i==0 else 'L'}{tx(t):.1f},{ty(v):.1f}" for i,(t,v) in enumerate(pts))
        svg.append(f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none" stroke-linejoin="round"/>')
        # 최고점 빨간 점선
        x_p = tx(peak['t'])
        svg.append(f'<line x1="{x_p:.1f}" y1="{y_top}" x2="{x_p:.1f}" y2="{y_bot}" '
                   f'stroke="#DC2626" stroke-width="1" stroke-dasharray="3,2" opacity="0.6"/>')
        # 우측 아래 원본 컬럼명
        svg.append(f'<text x="{PAD_L+plot_w}" y="{y_bot+12}" text-anchor="end" font-size="10" '
                   f'fill="#6B7280" font-family="Consolas, monospace">{escape(mono)}</text>')

    # 시간축 (마지막)
    y_last_x = y_sec + n_sub * H_PER - 22
    draw_xticks(y_last_x)
    svg.append(f'<text x="{W//2}" y="{H - 12}" text-anchor="middle" font-size="11" fill="#6B7280">'
               f'시각 (시간) · 빨간 점선 = 최고점({peak["t"].strftime("%H:%M")})</text>')
    svg.append('</svg>')
    return '\n'.join(svg)


# ─────────────────────────────────────────────────────────────
# 24시간 점수만 — 단순 그래프 (기존 호환)
# ─────────────────────────────────────────────────────────────
def make_24h_score_svg(day, data, peak):
    """data = [{'t':..., 'score':..., 'level':..., 'hot':...}, ...] (매분 1행)."""
    from collections import Counter
    levels = Counter(d['level'] for d in data)
    t0 = datetime.strptime(f'{day} 00:00', '%Y-%m-%d %H:%M')
    t1 = datetime.strptime(f'{day} 23:59', '%Y-%m-%d %H:%M')
    total_sec = (t1 - t0).total_seconds()

    W = 1400; H = 600
    PAD_L, PAD_R, PAD_T, PAD_B = 90, 100, 130, 90
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    y_top, y_bot = PAD_T, PAD_T + plot_h
    Y_MAX = 250
    def ty(v): return y_bot - (min(v, Y_MAX) / Y_MAX) * plot_h
    def tx(t): return PAD_L + (t - t0).total_seconds() / total_sec * plot_w

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Malgun Gothic, AppleGothic, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        f'<text x="{W//2}" y="32" text-anchor="middle" font-size="20" font-weight="700" fill="#111827">'
        f'{day} 발동이벤트 24시간 추이 (unified_risk_score)</text>',
        f'<text x="{W//2}" y="54" text-anchor="middle" font-size="13" fill="#6B7280">'
        f'최고 {peak["score"]}점 [{peak["level"]}] @ {peak["t"].strftime("%H:%M")} (hot={peak["hot"]})  ·  '
        f'정상 {levels.get("정상",0)} · 관심 {levels.get("관심",0)} · 주의 {levels.get("주의",0)} · '
        f'경계 {levels.get("경계",0)} · 위험 {levels.get("위험",0)} · 발동 {levels.get("발동",0)}</text>',
    ]
    # 범례
    svg.append(f'<text x="{PAD_L}" y="92" font-size="11" fill="#374151" font-weight="600">등급:</text>')
    xx = PAD_L + 42
    for v0, v1, color, name in LEVEL_BANDS[:-1]:
        svg.append(f'<rect x="{xx}" y="82" width="14" height="12" fill="{color}" stroke="#D1D5DB"/>')
        svg.append(f'<text x="{xx+18}" y="92" font-size="11" fill="#374151">{name} ({v0}~{v1})</text>')
        xx += 100

    # 배경 밴드 + 우측 라벨
    for v0, v1, color, name in LEVEL_BANDS:
        if v0 >= Y_MAX: continue
        y_a = ty(min(v1, Y_MAX)); y_b = ty(v0)
        svg.append(f'<rect x="{PAD_L}" y="{y_a:.1f}" width="{plot_w}" height="{y_b-y_a:.1f}" '
                   f'fill="{color}" opacity="0.5"/>')
        svg.append(f'<text x="{PAD_L+plot_w+5}" y="{(y_a+y_b)/2:.1f}" font-size="11" '
                   f'fill="#374151" font-weight="600" dominant-baseline="middle">{name}</text>')

    # 격자
    for v in [0, 100, 120, 130, 160, 220]:
        if v > Y_MAX: continue
        y = ty(v)
        if v > 0:
            svg.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+plot_w}" y2="{y:.1f}" '
                       f'stroke="#9CA3AF" stroke-width="0.7" stroke-dasharray="3,3"/>')
        svg.append(f'<text x="{PAD_L-6}" y="{y:.1f}" text-anchor="end" font-size="10" fill="#6B7280" '
                   f'dominant-baseline="middle">{v}</text>')

    # 점수 선
    path = " ".join(f"{'M' if i==0 else 'L'}{tx(d['t']):.1f},{ty(d['score']):.1f}"
                    for i, d in enumerate(data))
    svg.append(f'<path d="{path}" stroke="#1F2937" stroke-width="1.3" fill="none" stroke-linejoin="round"/>')

    # 최고점 마커
    mx, my = tx(peak['t']), ty(peak['score'])
    svg.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="6" fill="#DC2626" stroke="#fff" stroke-width="2"/>')
    svg.append(f'<text x="{mx:.1f}" y="{my-13:.1f}" text-anchor="middle" font-size="12" '
               f'fill="#DC2626" font-weight="700">{peak["score"]}점 @ {peak["t"].strftime("%H:%M")}</text>')

    # x축 3시간 단위
    for h in range(0, 25, 3):
        tt = datetime.strptime(f'{day} {h:02d}:00', '%Y-%m-%d %H:%M') if h < 24 else t1
        x = tx(tt)
        svg.append(f'<line x1="{x:.1f}" y1="{y_bot}" x2="{x:.1f}" y2="{y_bot+5}" stroke="#6B7280"/>')
        svg.append(f'<text x="{x:.1f}" y="{y_bot+20}" text-anchor="middle" font-size="11" '
                   f'fill="#374151" font-weight="500">{h:02d}:00</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


# ─────────────────────────────────────────────────────────────
# 위험사건 ±60분 그래프
# ─────────────────────────────────────────────────────────────
def make_incident_svg(incident, series, evt_score_series=None, friendly_map=None):
    """incident = {'predict':..., 'start':..., 'end':..., 'level':..., 'score':..., 'hot':..., 'day':...}
       series = {col: [(t, val), ...]} (key 는 raw 풀네임 권장; 축약형도 호환)
       evt_score_series = [(t, score), ...] (상단에 그릴 점수 추이, 선택)
       friendly_map = {col: "한글 라벨"} — 좌측 큰 라벨"""
    friendly_map = friendly_map or {}
    t0 = incident['t0']
    t1 = incident['t1']
    total_sec = (t1 - t0).total_seconds() or 1

    W = 1300
    H_SCORE = 240 if evt_score_series else 0
    H_PER = 115
    PAD_L, PAD_R, PAD_T, PAD_B = 230, 60, 110, 90
    n = len(series)
    H_GAP = 35 if evt_score_series else 0
    H = PAD_T + H_SCORE + H_GAP + H_PER * n + PAD_B
    plot_w = W - PAD_L - PAD_R
    def tx(t): return PAD_L + (t - t0).total_seconds() / total_sec * plot_w

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Malgun Gothic, AppleGothic, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        f'<text x="{W//2}" y="32" text-anchor="middle" font-size="20" font-weight="700" fill="#111827">'
        f'[{incident["level"]} {incident["score"]}점] {incident["day"]} '
        f'{incident["start"].strftime("%H:%M")}~{incident["end"].strftime("%H:%M")} '
        f'(hot={incident["hot"]})</text>',
        f'<text x="{W//2}" y="54" text-anchor="middle" font-size="13" fill="#6B7280">'
        f'예측 {incident["predict"].strftime("%H:%M")} · 확정 {incident["start"].strftime("%H:%M")} · '
        f'종료 {incident["end"].strftime("%H:%M")} · 사건 ±60분 표시</text>',
        f'<rect x="{PAD_L}" y="68" width="14" height="14" fill="#FEE2E2" stroke="#FCA5A5"/>',
        f'<text x="{PAD_L+20}" y="80" font-size="12" fill="#374151">사건 진행 구간</text>',
        f'<line x1="{PAD_L+150}" y1="75" x2="{PAD_L+175}" y2="75" stroke="#10B981" stroke-width="2" stroke-dasharray="4,2"/>',
        f'<text x="{PAD_L+183}" y="80" font-size="12" fill="#374151">예측 시작</text>',
    ]

    # 상단: 점수 추이 (선택)
    if evt_score_series:
        y_s_top = PAD_T
        y_s_bot = PAD_T + H_SCORE
        Y_MAX = 250
        def ty_score(v): return y_s_bot - (min(v, Y_MAX) / Y_MAX) * H_SCORE
        svg.append(f'<text x="{PAD_L-8}" y="{y_s_top - 6}" font-size="12" font-weight="700" '
                   f'fill="#111827">unified_risk_score 추이</text>')
        # 등급 밴드
        for v0, v1, color, _ in LEVEL_BANDS:
            if v0 >= Y_MAX: continue
            y_a = ty_score(min(v1, Y_MAX)); y_b = ty_score(v0)
            svg.append(f'<rect x="{PAD_L}" y="{y_a:.1f}" width="{plot_w}" height="{y_b-y_a:.1f}" '
                       f'fill="{color}" opacity="0.4"/>')
        # 점수 선
        path = " ".join(f"{'M' if i==0 else 'L'}{tx(t):.1f},{ty_score(s):.1f}"
                        for i, (t, s) in enumerate(evt_score_series))
        svg.append(f'<path d="{path}" stroke="#1F2937" stroke-width="1.4" fill="none" stroke-linejoin="round"/>')
        # 사건 구간 빨간 음영
        if t0 <= incident['start'] <= t1 and t0 <= incident['end'] <= t1:
            x_a, x_b = tx(incident['start']), tx(incident['end'])
            svg.append(f'<rect x="{x_a:.1f}" y="{y_s_top}" width="{x_b-x_a:.1f}" height="{H_SCORE}" '
                       f'fill="#FEE2E2" opacity="0.35"/>')
        # 예측 초록 점선
        if t0 <= incident['predict'] <= t1:
            x = tx(incident['predict'])
            svg.append(f'<line x1="{x:.1f}" y1="{y_s_top}" x2="{x:.1f}" y2="{y_s_bot}" '
                       f'stroke="#10B981" stroke-width="1.5" stroke-dasharray="4,2" opacity="0.8"/>')
        # y 라벨
        for v in [0, 100, 160, 220]:
            if v > Y_MAX: continue
            y = ty_score(v)
            svg.append(f'<text x="{PAD_L-6}" y="{y:.1f}" text-anchor="end" font-size="9" fill="#6B7280" '
                       f'dominant-baseline="middle">{v}</text>')

    # 하단: raw 시계열
    y_sec = PAD_T + H_SCORE + H_GAP
    for k, (col, pts) in enumerate(series.items()):
        color = COLORS[k % len(COLORS)]
        y_top = y_sec + k * H_PER
        y_bot = y_top + H_PER - 25
        plot_h = y_bot - y_top

        # 사건 구간 음영
        if t0 <= incident['start'] <= t1 and t0 <= incident['end'] <= t1:
            x_a, x_b = tx(incident['start']), tx(incident['end'])
            svg.append(f'<rect x="{x_a:.1f}" y="{y_top}" width="{x_b-x_a:.1f}" height="{plot_h}" '
                       f'fill="#FEE2E2" opacity="0.5"/>')
        svg.append(f'<rect x="{PAD_L}" y="{y_top}" width="{plot_w}" height="{plot_h}" '
                   f'fill="none" stroke="#E5E7EB" stroke-width="1"/>')
        nice = friendly_map.get(col) or short_label(col)
        mono = col if '.' in col else col
        svg.append(f'<text x="{PAD_L-12}" y="{y_top + plot_h/2 - 7}" text-anchor="end" font-size="12" '
                   f'fill="#1F2937" font-weight="700" dominant-baseline="middle">{escape(nice)}</text>')
        svg.append(f'<text x="{PAD_L-12}" y="{y_top + plot_h/2 + 8}" text-anchor="end" font-size="9" '
                   f'fill="#9CA3AF" font-family="Consolas,monospace" dominant-baseline="middle">{escape(mono)}</text>')

        if not pts:
            svg.append(f'<text x="{PAD_L+plot_w/2}" y="{y_top+plot_h/2}" text-anchor="middle" font-size="11" fill="#9CA3AF">(데이터 없음)</text>')
            continue
        vmin = min(v for _,v in pts); vmax = max(v for _,v in pts)
        rng = max(vmax-vmin, 1e-9)
        vmin_d, vmax_d = vmin - rng*0.05, vmax + rng*0.08
        def ty(v): return y_bot - (v-vmin_d)/(vmax_d-vmin_d)*plot_h
        svg.append(f'<text x="{PAD_L-6}" y="{y_top+3}" text-anchor="end" font-size="9" fill="#6B7280" dominant-baseline="hanging">{vmax:.1f}</text>')
        svg.append(f'<text x="{PAD_L-6}" y="{y_bot-3}" text-anchor="end" font-size="9" fill="#6B7280">{vmin:.1f}</text>')
        path = " ".join(f"{'M' if i==0 else 'L'}{tx(t):.1f},{ty(v):.1f}" for i,(t,v) in enumerate(pts))
        svg.append(f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none" stroke-linejoin="round"/>')

        # 예측 초록 점선
        if t0 <= incident['predict'] <= t1:
            x = tx(incident['predict'])
            svg.append(f'<line x1="{x:.1f}" y1="{y_top}" x2="{x:.1f}" y2="{y_bot}" '
                       f'stroke="#10B981" stroke-width="1.5" stroke-dasharray="4,2" opacity="0.8"/>')

    # x축
    y_x = H - PAD_B + 5
    t = t0.replace(minute=0, second=0)
    if t < t0: t += timedelta(hours=1)
    while t <= t1:
        x = tx(t)
        svg.append(f'<line x1="{x:.1f}" y1="{y_x}" x2="{x:.1f}" y2="{y_x+4}" stroke="#6B7280"/>')
        svg.append(f'<text x="{x:.1f}" y="{y_x+18}" text-anchor="middle" font-size="11" '
                   f'fill="#374151">{t.strftime("%H:%M")}</text>')
        t += timedelta(hours=1)

    svg.append('</svg>')
    return '\n'.join(svg)
