# -*- coding: utf-8 -*-
"""
Graph_LO.py — 발동이벤트 ≥주의 시 자동 그래프 생성기
=====================================================
패턴: Rule_LO.py 와 동일 구조 (start / trigger / stop)

동작:
  매분 발동이벤트 행이 추가되면 trigger() 호출 →
    · unified_risk_level ∈ {주의, 경계, 위험, 발동} 이면 발동
    · predict/M16A_HUBROOM_PR.csv 를 gre/M16A_HUBROOM_PR_HH_MM.CSV 로 복사
    · reason 컬럼을 파싱해서 발동한 원본 컬럼만 추출
    · gre/M16A_HUBROOM_PR_HH_MM.svg 그래프 생성 (90분 윈도우 시계열)

사용 (hubroom_predictor.py 에서 import):
    import Graph_LO
    Graph_LO.start()
    Graph_LO.trigger(EVENT_FIELDS, row)   # 매분
    Graph_LO.stop()

설정 (config.json 또는 코드 기본값):
  · graph_enabled  : 활성 여부 (기본 True)
  · graph_dir      : 출력 폴더 (기본 ./gre)
  · graph_raw_path : raw 파일 경로 (기본 ./predict/M16A_HUBROOM_PR.csv)
  · graph_levels   : trigger 등급 (기본 ['주의','경계','위험','초위험'])

설치 의존성: 표준 라이브러리만 (csv / re / shutil / xml). matplotlib 불필요.
"""
import csv
import json
import logging
import os
import re
import shutil
from datetime import datetime
from xml.sax.saxutils import escape

log = logging.getLogger("Graph_LO")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [Graph_LO] %(message)s"))
    log.addHandler(h)

_HERE = os.path.dirname(os.path.abspath(__file__))


# ────────────────────────────────────────────────────────────
# 설정 로드
# ────────────────────────────────────────────────────────────
def _load_config():
    path = os.path.join(_HERE, "config.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_CFG = _load_config()

ENABLED   = bool(_CFG.get("graph_enabled", True))
GRAPH_DIR = _CFG.get("graph_dir", os.path.join(_HERE, "gre"))
RAW_PATH  = _CFG.get("graph_raw_path", os.path.join(_HERE, "predict", "M16A_HUBROOM_PR.csv"))
LEVELS    = set(_CFG.get("graph_levels", ["경계", "위험", "초위험"]))

# 같은 분 중복 방지
_processed = set()
_count = 0


# ────────────────────────────────────────────────────────────
# reason 파싱 → 발동된 원본 컬럼 추출
# ────────────────────────────────────────────────────────────
_KEYWORDS = {
    'AVGTOTALTIME1MIN': 'QUE.TIME.AVGTOTALTIME1MIN',
    'AVGLOADTIME1MIN':  'QUE.LOAD.AVGLOADTIME1MIN',
    'STB':              'STRATE.STB.3F_STORAGE_UTIL',
    'FAB저장':          'STRATE.ALL.FABSTORAGERATIO',
    'OHT':              'QUE.OHT.OHTUTIL',
    '4분초과':          'QUE.ALL.TRANSPORT4MINOVERRATIO',
}
_AREAS = ('M16HUB', 'M14B', 'M14', 'M16A', 'M16B', 'M16_PKT', 'M16_WT', 'M16')


def _parse_reason_cols(reason):
    cols = []
    for m in re.finditer(r'(M16HUB|M14B|M14|M16A|M16B|M16_PKT|M16_WT|M16)\[([^\]]+)\]', reason or ''):
        area, body = m.group(1), m.group(2)
        for kw, suf in _KEYWORDS.items():
            if kw in body:
                col = f"{area}.{suf}"
                if col not in cols:
                    cols.append(col)
    return cols


# ────────────────────────────────────────────────────────────
# SVG 그래프 생성
# ────────────────────────────────────────────────────────────
_COLORS = ['#2563EB', '#DC2626', '#059669', '#D97706', '#7C3AED',
           '#0891B2', '#DB2777', '#65A30D', '#EA580C', '#0D9488']


def _short(col):
    p = col.split('.'); a = p[0]
    if 'AVGTOTALTIME' in col or 'AVGLOADTIME' in col: return f"{a} 반송시간 (분)"
    if 'STB' in col: return f"{a} STB 저장율 (%)"
    if 'FABSTORAGE' in col: return f"{a} FAB 저장율 (%)"
    if 'OHTUTIL' in col: return f"{a} OHT 가동률 (%)"
    if 'TRANSPORT4MIN' in col: return f"{a} 4분초과 (%)"
    return col


def _build_svg(csv_path, trigger_dt, score, level, hot, cols):
    """저장된 90분 CSV 를 읽어 SVG 생성."""
    hdr = None; rows = []
    with open(csv_path, encoding='utf-8-sig') as f:
        rdr = csv.reader(f); hdr = next(rdr)
        for row in rdr:
            if not row or not row[0]: continue
            try: t = datetime.strptime(row[0][:16], '%Y-%m-%d %H:%M')
            except: continue
            rows.append((t, row))
    if not rows:
        return None

    idx = {c: i for i, c in enumerate(hdr)}
    keep = [c for c in cols if c in idx]
    if not keep:
        return None
    series = {c: [] for c in keep}
    for t, row in rows:
        for c in keep:
            i = idx[c]
            if i < len(row) and row[i]:
                try: series[c].append((t, float(row[i])))
                except: pass

    t_start, t_end = rows[0][0], rows[-1][0]
    total_sec = max((t_end - t_start).total_seconds(), 1)

    W = 1300; H_PER = 110
    PAD_L, PAD_R, PAD_T, PAD_B = 220, 60, 110, 80
    n = len(keep)
    H = PAD_T + H_PER * n + PAD_B
    plot_w = W - PAD_L - PAD_R
    def tx(t): return PAD_L + (t - t_start).total_seconds() / total_sec * plot_w

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Malgun Gothic, AppleGothic, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        f'<text x="{W//2}" y="32" text-anchor="middle" font-size="20" font-weight="700" fill="#111827">'
        f'{os.path.basename(csv_path)} — 90분 윈도우 분석</text>',
        f'<text x="{W//2}" y="54" text-anchor="middle" font-size="13" fill="#6B7280">'
        f'트리거 {trigger_dt.strftime("%H:%M")}  ·  점수 {score} [{level}]  ·  hot={hot}  ·  '
        f'{len(rows)}분 ({t_start.strftime("%H:%M")} ~ {t_end.strftime("%H:%M")})</text>',
        f'<line x1="{PAD_L}" y1="78" x2="{PAD_L+25}" y2="78" stroke="#DC2626" stroke-width="2" stroke-dasharray="4,2"/>',
        f'<text x="{PAD_L+32}" y="82" font-size="12" fill="#374151">발동 시점 ({trigger_dt.strftime("%H:%M")})</text>',
    ]
    for k, col in enumerate(keep):
        color = _COLORS[k % len(_COLORS)]
        y_top = PAD_T + k * H_PER
        y_bot = y_top + H_PER - 25
        ph = y_bot - y_top
        pts = series.get(col, [])
        svg.append(f'<rect x="{PAD_L}" y="{y_top}" width="{plot_w}" height="{ph}" '
                   f'fill="#FAFAFA" stroke="#E5E7EB"/>')
        svg.append(f'<text x="{PAD_L-12}" y="{y_top+ph/2-7}" text-anchor="end" font-size="12" '
                   f'fill="#1F2937" font-weight="700" dominant-baseline="middle">{escape(_short(col))}</text>')
        svg.append(f'<text x="{PAD_L-12}" y="{y_top+ph/2+8}" text-anchor="end" font-size="9" '
                   f'fill="#9CA3AF" font-family="Consolas,monospace" dominant-baseline="middle">{escape(col)}</text>')
        if not pts:
            svg.append(f'<text x="{PAD_L+plot_w/2}" y="{y_top+ph/2}" text-anchor="middle" font-size="11" fill="#9CA3AF">(데이터 없음)</text>')
            continue
        vmin = min(v for _, v in pts); vmax = max(v for _, v in pts)
        rng = max(vmax - vmin, 1e-9)
        vmin_d = vmin - rng * 0.05; vmax_d = vmax + rng * 0.08
        def ty(v): return y_bot - (v - vmin_d) / (vmax_d - vmin_d) * ph
        svg.append(f'<text x="{PAD_L-6}" y="{y_top+3}" text-anchor="end" font-size="9" fill="#6B7280" dominant-baseline="hanging">{vmax:.1f}</text>')
        svg.append(f'<text x="{PAD_L-6}" y="{y_bot-3}" text-anchor="end" font-size="9" fill="#6B7280">{vmin:.1f}</text>')
        path = " ".join(f"{'M' if i==0 else 'L'}{tx(t):.1f},{ty(v):.1f}" for i, (t, v) in enumerate(pts))
        svg.append(f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none" stroke-linejoin="round"/>')
        x = tx(trigger_dt)
        if PAD_L <= x <= PAD_L + plot_w:
            svg.append(f'<line x1="{x:.1f}" y1="{y_top}" x2="{x:.1f}" y2="{y_bot}" '
                       f'stroke="#DC2626" stroke-width="1.2" stroke-dasharray="4,2" opacity="0.7"/>')
        svg.append(f'<text x="{PAD_L+plot_w}" y="{y_bot+12}" text-anchor="end" font-size="10" '
                   f'fill="#6B7280" font-family="Consolas, monospace">{escape(col)}</text>')

    # x축 (10분 단위)
    y_x = PAD_T + H_PER * n - 22
    from datetime import timedelta
    t = t_start.replace(second=0, microsecond=0)
    t = t.replace(minute=(t.minute // 10) * 10)
    if t < t_start: t += timedelta(minutes=10)
    while t <= t_end:
        x = tx(t)
        svg.append(f'<line x1="{x:.1f}" y1="{y_x}" x2="{x:.1f}" y2="{y_x+4}" stroke="#6B7280"/>')
        svg.append(f'<text x="{x:.1f}" y="{y_x+18}" text-anchor="middle" font-size="10" fill="#374151">{t.strftime("%H:%M")}</text>')
        t += timedelta(minutes=10)

    svg.append('</svg>')
    return '\n'.join(svg)


# ────────────────────────────────────────────────────────────
# 외부 API
# ────────────────────────────────────────────────────────────
def start():
    """predictor 시작 시 호출 (1회)."""
    if not ENABLED:
        log.info("Graph_LO 비활성 (config.json: graph_enabled=false)")
        return
    os.makedirs(GRAPH_DIR, exist_ok=True)
    log.info(f"활성 — 출력 폴더 {GRAPH_DIR} / raw {RAW_PATH} / 등급 {LEVELS}")


def trigger(fields, row):
    """매분 발동이벤트 한 행 받음. 등급 ≥주의 면 CSV 복사 + 그래프 생성.
       fields(list) + row(list of values) — hubroom_predictor 의 EVENT_FIELDS / event_to_row 결과."""
    if not ENABLED:
        return
    try:
        d = dict(zip(fields, row))
        level = (d.get('unified_risk_level') or '').strip()
        if level not in LEVELS:
            return

        dt_str = (d.get('datetime') or '').strip()
        try:
            tdt = datetime.strptime(dt_str[:16], '%Y-%m-%d %H:%M')
        except Exception:
            return
        key = tdt.strftime('%Y%m%d_%H%M')
        if key in _processed:
            return
        _processed.add(key)

        if not os.path.exists(RAW_PATH):
            log.warning(f"raw 파일 없음: {RAW_PATH}")
            return

        # CSV 복사
        hh, mm = tdt.strftime('%H'), tdt.strftime('%M')
        out_csv = os.path.join(GRAPH_DIR, f'M16A_HUBROOM_PR_{hh}_{mm}.CSV')
        shutil.copyfile(RAW_PATH, out_csv)

        # 그래프 생성
        cols = _parse_reason_cols(d.get('reason', ''))
        score = d.get('unified_risk_score', '?')
        hot = d.get('hot_area', '')
        svg = _build_svg(out_csv, tdt, score, level, hot, cols)
        if svg:
            out_svg = os.path.join(GRAPH_DIR, f'M16A_HUBROOM_PR_{hh}_{mm}.svg')
            with open(out_svg, 'w', encoding='utf-8') as f:
                f.write(svg)

        global _count
        _count += 1
        log.info(f"[{tdt.strftime('%H:%M')}] {level} {score}점 → {os.path.basename(out_csv)} + 그래프 (#{_count})")

    except Exception as e:
        log.warning(f"trigger 예외 무시: {e}")


def stop():
    """predictor 종료 시 호출."""
    if not ENABLED:
        return
    log.info(f"종료 — 누적 생성 {_count}건")


def stats():
    return {"enabled": ENABLED, "generated": _count,
            "dir": GRAPH_DIR, "raw": RAW_PATH, "levels": list(LEVELS)}
