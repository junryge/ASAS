#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사건 그래프 생성기 — 주의/경계/위험/발동 사건만, reason(relation) 컬럼만 그래프화

처리:
  1. 사건단위.csv 에서 max_risk_level ∈ {주의, 경계, 위험, 발동} 사건만 추림
  2. 각 사건의 relation 컬럼 파싱 → 발동된 룰이 본 원본 컬럼 추출
  3. M16A_HUBROOM_PR.csv 에서 그 컬럼들 + 사건 시각 ±60분 추출
  4. CSV 복사 + PNG 생성 (컬럼당 1줄 subplot, 사건 start/end 빨간 점선)

사용:
  python 사건_그래프생성.py <사건단위.csv> <M16A_HUBROOM_PR.csv> -o <출력폴더>
"""
import csv
import os
import re
import sys
from datetime import datetime, timedelta

# matplotlib 한글 깨짐 방지
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    # 한글 폰트
    for f in ('Malgun Gothic', 'NanumGothic', 'AppleGothic', 'DejaVu Sans'):
        try:
            plt.rcParams['font.family'] = f
            break
        except Exception:
            pass
    plt.rcParams['axes.unicode_minus'] = False
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠️ matplotlib 없음 — CSV 복사만 수행 (PNG 생략)")

# ── 대상 등급 ──
TARGET_LEVELS = {'주의', '경계', '위험', '발동'}

# ── relation 파싱 정규식 ──
# 예: "[M16HUB R-A'] M16HUB.QUE.TIME.AVGTOTALTIME1MIN=12.24분 (기준 9.45분)"
# 예: "[M16HUB R-C'] 리프터 역증가 10개 (기준 4)"
# 예: "[M16A R-B] M16A.QUE.ALL.6F_TO_HUB_JOB +124/30분 (기준 +84)"
RELATION_TOKEN = re.compile(r'\[([^\]]+)\]\s*([^|]+?)(?=\s*\||$)')
COLUMN_NAME = re.compile(r'([A-Z][A-Z0-9_]+(?:\.[A-Z0-9_]+)+)')


def parse_relation_columns(relation):
    """relation 텍스트에서 원본 컬럼명 추출."""
    cols = []
    for area_rule, body in RELATION_TOKEN.findall(relation or ''):
        for col in COLUMN_NAME.findall(body):
            if col not in cols:
                cols.append(col)
        # 리프터 역증가는 컬럼명 없이 한글 → 룰별 매핑
        if '리프터' in body and '역증가' in body:
            # M16HUB 리프터 10대 합계 (대표 컬럼들)
            for lid in ('M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT',
                        'M16HUB.LFT.6ABL6021.TOTAL_CURRENTQCNT',
                        'M16HUB.LFT.6ABL0111.TOTAL_CURRENTQCNT'):
                if lid not in cols:
                    cols.append(lid)
            break  # 대표만 추가
    return cols


def parse_dt(s):
    """'2026-05-25 16:57' 또는 '16:57' 형태 처리."""
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M')
    except Exception:
        return None


def load_incidents(path):
    """사건단위.csv → 주의 이상 사건 리스트."""
    incidents = []
    # 파일명 첫 8자리에서 날짜 추출
    base = os.path.basename(path)
    m = re.match(r'(\d{8})', base)
    day = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else None
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        level = (r.get('max_risk_level') or '').strip()
        if level not in TARGET_LEVELS:
            continue
        # 시각 파싱 (HH:MM → 날짜 합침)
        d = r.get('date') or day
        if not d:
            continue
        predict = parse_dt(f"{d} {r.get('predict_time','')}")
        start = parse_dt(f"{d} {r.get('start_time','')}")
        end = parse_dt(f"{d} {r.get('end_time','')}")
        if start and end and end < start:
            end += timedelta(days=1)
        if start and predict and start < predict:
            start += timedelta(days=1)
            if end:
                end += timedelta(days=1)
        incidents.append({
            'predict': predict, 'start': start, 'end': end,
            'level': level, 'score': r.get('max_risk_score', ''),
            'hot_area': r.get('hot_area', ''),
            'relation': r.get('relation', ''),
            'date': d,
        })
    return incidents


def load_raw(path):
    """M16A_HUBROOM_PR.csv → (header, rows) — datetime 컬럼 1번째."""
    f = open(path, encoding='utf-8-sig')
    rdr = csv.reader(f)
    hdr = next(rdr)
    rows = []
    for row in rdr:
        if not row:
            continue
        t = parse_dt(row[0]) or parse_dt(row[0][:16])
        if t:
            rows.append((t, row))
    return hdr, rows


def slice_window(hdr, rows, t0, t1):
    """t0~t1 구간 행만 반환 (있는 만큼)."""
    return [(t, r) for t, r in rows if t0 <= t <= t1]


def extract_columns(hdr, rows_window, cols_wanted):
    """원하는 컬럼만 추출 → {col: [(t, val), ...]}."""
    # 인덱스 매핑
    idx = {c: i for i, c in enumerate(hdr)}
    result = {}
    for col in cols_wanted:
        if col not in idx:
            continue
        i = idx[col]
        series = []
        for t, r in rows_window:
            if i >= len(r) or r[i] == '':
                continue
            try:
                series.append((t, float(r[i])))
            except ValueError:
                pass
        if series:
            result[col] = series
    return result


def short_label(col):
    """긴 컬럼명 → 그래프 라벨 (영역.지표)."""
    parts = col.split('.')
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[-1]}"
    return col


def write_csv(out_path, hdr, rows_window, cols_wanted):
    """필요 컬럼만 추린 CSV 저장."""
    idx = {c: i for i, c in enumerate(hdr)}
    keep_idx = [0] + [idx[c] for c in cols_wanted if c in idx]
    keep_hdr = [hdr[i] for i in keep_idx]
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(keep_hdr)
        for t, r in rows_window:
            w.writerow([r[i] if i < len(r) else '' for i in keep_idx])


def make_graph(png_path, series, inc):
    """컬럼별 1줄 subplot. 사건 start/end 빨간 점선."""
    if not HAS_MPL or not series:
        return False
    n = len(series)
    fig, axes = plt.subplots(n, 1, figsize=(12, 1.8 * n + 0.5), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (col, pts) in zip(axes, series.items()):
        ts = [t for t, _ in pts]
        vs = [v for _, v in pts]
        ax.plot(ts, vs, '-', color='#2563EB', linewidth=1.3)
        ax.set_ylabel(short_label(col), fontsize=9)
        ax.grid(True, alpha=0.3)
        # 사건 시작/종료 표시
        if inc.get('start'):
            ax.axvline(inc['start'], color='red', linestyle='--', linewidth=1, alpha=0.7)
        if inc.get('end'):
            ax.axvline(inc['end'], color='red', linestyle='--', linewidth=1, alpha=0.7)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    axes[-1].set_xlabel('시각', fontsize=9)
    fig.suptitle(
        f"[{inc['level']} {inc['score']}점] {inc['date']} {inc['start'].strftime('%H:%M') if inc['start'] else '?'} ~ "
        f"{inc['end'].strftime('%H:%M') if inc['end'] else '?'} | hot={inc['hot_area']}",
        fontsize=11, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(png_path, dpi=110)
    plt.close(fig)
    return True


def make_filename(inc):
    """예: 20260525_1657_위험_M16HUB"""
    t = inc['start'] or inc['predict']
    d = t.strftime('%Y%m%d') if t else inc['date'].replace('-', '')
    hm = t.strftime('%H%M') if t else '0000'
    return f"{d}_{hm}_{inc['level']}_{inc['hot_area'] or 'NA'}"


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    incident_csv = sys.argv[1]
    raw_csv = sys.argv[2]
    out_dir = './out_그래프'
    for i, a in enumerate(sys.argv):
        if a == '-o' and i + 1 < len(sys.argv):
            out_dir = sys.argv[i + 1]
    os.makedirs(out_dir, exist_ok=True)

    print(f"📂 사건단위: {incident_csv}")
    print(f"📂 RAW:     {raw_csv}")
    print(f"📂 출력:    {out_dir}\n")

    incidents = load_incidents(incident_csv)
    print(f"✅ 대상 사건 (주의/경계/위험/발동): {len(incidents)}건\n")
    if not incidents:
        print("(처리할 사건 없음)"); return

    hdr, rows = load_raw(raw_csv)
    print(f"✅ RAW 로드: {len(hdr)} 컬럼, {len(rows)} 행")
    if rows:
        print(f"   기간: {rows[0][0]} ~ {rows[-1][0]}\n")

    for inc in incidents:
        anchor = inc['start'] or inc['predict']
        if not anchor:
            print(f"⏭️  시각 없음 — 스킵"); continue
        t0 = anchor - timedelta(minutes=60)
        t1 = (inc['end'] or anchor) + timedelta(minutes=60)

        window = slice_window(hdr, rows, t0, t1)
        if not window:
            print(f"⏭️  {anchor.strftime('%H:%M')} {inc['level']} — RAW 데이터 없음 (수집기 90분 윈도우 밖일 수 있음)")
            continue

        cols = parse_relation_columns(inc['relation'])
        if not cols:
            print(f"⏭️  {anchor.strftime('%H:%M')} {inc['level']} — relation 컬럼 추출 실패"); continue

        series = extract_columns(hdr, window, cols)
        base = make_filename(inc)
        csv_path = os.path.join(out_dir, base + '.csv')
        png_path = os.path.join(out_dir, base + '.png')

        write_csv(csv_path, hdr, window, list(series.keys()))
        ok = make_graph(png_path, series, inc)
        print(f"✅ {base}")
        print(f"   컬럼 {len(series)}개, {len(window)}분 → CSV{' + PNG' if ok else ''}")

    print(f"\n🎉 완료 — {out_dir}/")


if __name__ == '__main__':
    main()
