#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림_실시간 — 매분 원본(M16A_HUBROOM_PR)을 읽어 '지금' 밀림 판정 1줄 출력
====================================================================
실시간 운영 최종 실행파일. features_31 변환 불필요 — 원본에서 7컬럼 직접 읽음.
학습·모델·pandas 전부 불필요 (파이썬 표준 라이브러리만).

동작:
  · 원본 폴더에서 최신 데이터의 마지막 시각 기준, 직전 120분(권장 240분)으로 CUSUM 계산
  · 남측(4AFC3201)/북측(4AFC3301)/허브저장/브릿지타임 4감지기 판정
  · 콘솔 1줄 출력 + 매분 1행 CSV(realtime_cusum_YYYYMMDD.csv):
      측정시간|지속(분)|예측종류|밀림방향|최고등급|예측시각(10/30분후)|최고CUSUM|사유|판정|근거메시지
  · 구간표(밀림경보요약_실시간.csv)도 자동 갱신 — 경보시작~종료 한 줄
  · 판정/근거메시지는 실시간엔 공란 (월말 메신저 episode 대조로 채움)

사용 원본 컬럼(7개):
  M14.QUE.CNV.SOUTHCURRENTQCNT / NORTHCURRENTQCNT   남측/북측 큐
  M16HUB.STRATE.ALL.FABSTORAGERATIO                 허브저장
  M16HUB.QUE.TIME.AVGTOTALTIME1MIN                  브릿지타임
  M16HUB.STRATE.STK.STORAGERATIO / STB.3F_STORAGE_UTIL / QUE.ALL.TRANSPORT4MINOVERRATIO

실행:
  1회 판정 :  python 밀림_실시간.py --raw .\RAW
  운영 반복:  python 밀림_실시간.py --raw .\RAW --loop           (60초마다)
  시점 지정:  python 밀림_실시간.py --raw .\RAW --at "2026-06-24 11:36"   (검증용)

입력:
  --raw      원본 폴더(M16A_HUBROOM_PR_*.csv 자동, 최신 2개 파일 사용) 또는 파일 1개
  --outdir   결과 적재 폴더 (기본 .\밀림예측)
  --window   계산 창(분, 기본 240 = 기준선120 + 누적여유. 최소 120 권장)
"""
import argparse, csv, glob, os, statistics, sys, time
from datetime import datetime, timedelta

# ── 파라미터 (밀림_방향_CUSUM.py 와 동일 — 6월 실검증 값) ──
CUSUM_BASE_WIN = 120
CUSUM_K = 0.5
TH_CUSUM_Q = 600.0      # 남측/북측 큐
TH_CUSUM_FAB = 300.0    # 허브 저장
TH_CUSUM_BR = 40.0      # 브릿지타임
TH_RD_STK = 10.0        # STK 저장률 하드경보

SRC = {'M14.QUE.CNV.SOUTHCURRENTQCNT': '남큐',
       'M14.QUE.CNV.NORTHCURRENTQCNT': '북큐',
       'M16HUB.STRATE.ALL.FABSTORAGERATIO': '저장',
       'M16HUB.QUE.TIME.AVGTOTALTIME1MIN': '브릿지',
       'M16HUB.STRATE.STK.STORAGERATIO': 'STK',
       'M16HUB.STRATE.STB.3F_STORAGE_UTIL': 'STB',
       'M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO': 'SLA'}
DIR_LABEL = {'남측': '남측(4AFC3201)', '북측': '북측(4AFC3301)',
             '허브': '허브(몰림/저장)', '브릿지': '브릿지(BridgeTime상승)'}
GRADE_ORD = {'': 0, '경계': 1, '위험': 2, '초위험': 3}
COLS = ['측정시간', '지속(분)', '예측종류', '밀림방향', '최고등급',
        '예측시각(10분후)', '예측시각(30분후)', '최고CUSUM', '사건적중', '사유', '판정', '근거메시지']


def read_window(raw_path, upto=None, window=240):
    """원본에서 (upto 기준) 마지막 window분 로드 → times, {지표: 값리스트}."""
    if os.path.isdir(raw_path):
        files = sorted(glob.glob(os.path.join(raw_path, '*.csv'))
                       + glob.glob(os.path.join(raw_path, '*.CSV')),
                       key=os.path.getmtime)[-2:]          # 최신 2개(자정 넘김 대비)
    else:
        files = [raw_path]
    if not files:
        return [], {}
    grid = {}
    for fp in files:
        with open(fp, encoding='utf-8-sig', errors='replace') as f:
            for row in csv.DictReader(f):
                ts = (row.get('CRT_TM') or '').strip()[:16]
                try:
                    t = datetime.strptime(ts, '%Y-%m-%d %H:%M')
                except ValueError:
                    continue
                if upto and t > upto:
                    continue
                d = grid.setdefault(t, {})
                for src, short in SRC.items():
                    v = (row.get(src) or '').strip()
                    if v != '':
                        try:
                            d[short] = float(v)
                        except ValueError:
                            pass
    times = sorted(grid)[-window:]
    series = {}
    for short in SRC.values():
        vals, last = [], None
        for t in times:
            v = grid[t].get(short)
            if v is not None:
                last = v
            vals.append(last if last is not None else 0.0)
        series[short] = vals
    return times, series


def cusum_last(x):
    """창 내 CUSUM — 마지막 분의 누적값. (기준선: 직전 120분 중앙값+K×표준편차, 과거만)"""
    n = len(x)
    base = [None] * n
    sd = [0.0] * n
    for i in range(n):
        w = x[max(0, i - CUSUM_BASE_WIN):i]
        if len(w) >= 15:
            base[i] = statistics.median(w)
            m = sum(w) / len(w)
            sd[i] = (sum((v - m) ** 2 for v in w) / (len(w) - 1)) ** 0.5
    first = next((b for b in base if b is not None), x[0] if x else 0.0)
    C = 0.0
    for i in range(n):
        b = base[i] if base[i] is not None else first
        C = max(0.0, C + (x[i] - b - CUSUM_K * sd[i]))
    return C


def grade(cu, thr):
    if cu < thr:
        return '', 0.0
    r = cu / thr
    return ('초위험' if r >= 2.5 else '위험' if r >= 1.5 else '경계'), r


def gated(g, hour):
    """초위험=밤낮 항상 / 위험·경계=주간(08~19)만 (6월 검증 게이트)."""
    if g == '초위험':
        return g
    if g in ('위험', '경계') and 8 <= hour <= 19:
        return g
    return ''


def judge(times, S):
    """마지막 분 판정 → 결과 dict."""
    t = times[-1]
    cu = {'남측': cusum_last(S['남큐']), '북측': cusum_last(S['북큐']),
          '허브': cusum_last(S['저장']), '브릿지': cusum_last(S['브릿지'])}
    TH = {'남측': TH_CUSUM_Q, '북측': TH_CUSUM_Q, '허브': TH_CUSUM_FAB, '브릿지': TH_CUSUM_BR}
    stk = S['STK'][-1]
    hard = f"STK{stk:.0f}%≥{TH_RD_STK:.0f}" if stk >= TH_RD_STK else ''
    gg = {}
    cand = []
    for d in cu:
        g, r = grade(cu[d], TH[d])
        if d == '허브' and hard and GRADE_ORD['위험'] > GRADE_ORD[g]:
            g, r = '위험', max(r, 1.5)                     # 저장 하드경보 승격
        gg[d] = gated(g, t.hour)
        if gg[d]:
            nm = {'남측': '남측큐', '북측': '북측큐', '허브': '허브저장', '브릿지': '브릿지타임'}[d]
            cand.append((gg[d], r, d, f"{nm} 지속상승 CUSUM {cu[d]:.0f}({r:.1f}배)"
                                       + (f" +{hard}" if d == '허브' and hard else '')))
    best = max(cand, key=lambda x: (GRADE_ORD[x[0]], x[1])) if cand else None
    return {
        '_등급': best[0] if best else '',
        '_cu': cu[best[2]] if best else 0.0,
        'datetime': t.strftime('%Y-%m-%d %H:%M'),
        '예측시각(10분후)': (t + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M') if best else '',
        '예측시각(30분후)': (t + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M') if best else '',
        '남큐CUSUM': f"{cu['남측']:.0f}", '남측_예측결과': '예측' if gg['남측'] else '미예측',
        '북큐CUSUM': f"{cu['북측']:.0f}", '북측_예측결과': '예측' if gg['북측'] else '미예측',
        '저장CUSUM': f"{cu['허브']:.0f}", '허브_예측결과': '예측' if gg['허브'] else '미예측',
        '브릿지CUSUM': f"{cu['브릿지']:.0f}", '브릿지_예측결과': '예측' if gg['브릿지'] else '미예측',
        'RD_STK': f'{stk:.0f}', '저장하드경보': hard,
        '밀림방향': DIR_LABEL[best[2]] if best else '',
        '예측결과': '예측' if best else '미예측',
        '사유': best[3] if best else '',
    }


def append_row(outdir, rec, seg):
    """매분 1행 (사용자 형식): 측정시간 | 지속 | 종류 | 방향 | 등급 | 예측시각 | 최고CUSUM | 사유.
       미예측 분은 측정시간만 채움. 판정/근거메시지는 월말 메신저 대조로 채움(실시간 공란)."""
    os.makedirs(outdir, exist_ok=True)
    day = rec['datetime'][:10].replace('-', '')
    fp = os.path.join(outdir, f'realtime_cusum_{day}.csv')
    if os.path.exists(fp):
        with open(fp, encoding='utf-8-sig') as f:
            lines = f.readlines()
        if lines and lines[-1].startswith(rec['datetime']):
            return fp, False
    pred = rec['예측결과'] == '예측'
    row = {'측정시간': rec['datetime'],
           '지속(분)': (seg['지속(분)'] if seg else '1') if pred else '',
           '예측종류': (seg['예측종류'] if seg else kind_of(rec['밀림방향'], rec['사유'])) if pred else '',
           '밀림방향': rec['밀림방향'] if pred else '',
           '최고등급': (seg['최고등급'] if seg else rec['_등급']) if pred else '',
           '예측시각(10분후)': rec['예측시각(10분후)'],
           '예측시각(30분후)': rec['예측시각(30분후)'],
           '최고CUSUM': (seg['최고CUSUM'] if seg else f"{rec['_cu']:.0f}") if pred else '',
           '사건적중': '', '사유': rec['사유'] if pred else '', '판정': '', '근거메시지': ''}
    new = not os.path.exists(fp)
    with open(fp, 'a', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        if new:
            w.writeheader()
        w.writerow(row)
    return fp, True


SCOLS = ['경보시작', '경보종료', '지속(분)', '예측종류', '밀림방향', '최고등급',
         '예측시각(10분후)', '예측시각(30분후)', '최고CUSUM', '사건적중', '사유', '판정', '근거메시지']


def kind_of(direction, why):
    if '남측' in direction:
        return '컨베이어밀림(남측)'
    if '북측' in direction:
        return '컨베이어밀림(북측)'
    if '브릿지' in direction:
        return '브릿지 정체(BridgeTime)'
    if 'STK' in why or '저장Full' in why:
        return '허브 저장Full'
    return '허브 몰림/저장'


def update_summary(outdir, rec, gap=10):
    """매분 결과 → 사람이 보는 구간 요약(경보시작~종료 한 줄). 진행중 구간은 계속 갱신.
       판정/근거메시지는 실시간엔 공란 — 월말 메신저(episode)로 채움."""
    if rec['예측결과'] != '예측':
        return None
    fp = os.path.join(outdir, '밀림경보요약_실시간.csv')
    rows = []
    if os.path.exists(fp):
        with open(fp, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
    now = datetime.strptime(rec['datetime'], '%Y-%m-%d %H:%M')
    cu = rec['_cu']; g = rec['_등급']
    merged = False
    if rows:
        last = rows[-1]
        st = datetime.strptime(last['경보시작'], '%Y-%m-%d %H:%M')
        en = datetime.strptime(last['경보시작'][:11] + last['경보종료'], '%Y-%m-%d %H:%M')
        if en < st:
            en += timedelta(days=1)
        if last['밀림방향'] == rec['밀림방향'] and (now - en).total_seconds() <= gap * 60:
            last['경보종료'] = now.strftime('%H:%M')
            last['지속(분)'] = str(int((now - st).total_seconds() // 60) + 1)
            if cu > float(last['최고CUSUM'] or 0):
                last['최고CUSUM'] = f'{cu:.0f}'; last['사유'] = rec['사유']
            if GRADE_ORD.get(g, 0) > GRADE_ORD.get(last['최고등급'], 0):
                last['최고등급'] = g
            merged = True
    if not merged:
        rows.append({'경보시작': rec['datetime'], '경보종료': now.strftime('%H:%M'),
                     '지속(분)': '1', '예측종류': kind_of(rec['밀림방향'], rec['사유']),
                     '밀림방향': rec['밀림방향'], '최고등급': g,
                     '예측시각(10분후)': rec['예측시각(10분후)'],
                     '예측시각(30분후)': rec['예측시각(30분후)'],
                     '최고CUSUM': f'{cu:.0f}', '사건적중': '', '사유': rec['사유'],
                     '판정': '', '근거메시지': ''})
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=SCOLS, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
    return rows[-1]


def once(a, upto=None):
    times, S = read_window(a.raw, upto=upto, window=a.window)
    if len(times) < 30:
        print(f"  ⚠️ 데이터 부족 ({len(times)}분 — 최소 30분, 권장 120분↑)")
        return
    rec = judge(times, S)
    seg = update_summary(a.outdir, rec)
    fp, wrote = append_row(a.outdir, rec, seg)
    if rec['예측결과'] == '예측':
        info = f" | 구간 {seg['경보시작'][11:]}~{seg['경보종료']} ({seg['지속(분)']}분, {seg['예측종류']})" if seg else ''
        print(f"[{rec['datetime']}] 🔴 예측 ▶ {rec['밀림방향']} | {rec['사유']}"
              + f" | 예측시각 {rec['예측시각(10분후)'][11:]}~{rec['예측시각(30분후)'][11:]}" + info)
    else:
        print(f"[{rec['datetime']}] ⚪ 미예측" + ('' if wrote else ' (중복생략)'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True, help='원본 폴더 또는 파일 (M16A_HUBROOM_PR)')
    ap.add_argument('--outdir', default='./밀림예측')
    ap.add_argument('--window', type=int, default=240, help='계산 창(분, 기본 240·최소 120 권장)')
    ap.add_argument('--at', default=None, help='검증용: 이 시각 기준 판정 (예 "2026-06-24 11:36")')
    ap.add_argument('--loop', action='store_true', help='60초마다 반복 (운영)')
    ap.add_argument('--interval', type=int, default=60)
    a = ap.parse_args()

    print("=" * 60)
    print("밀림 실시간 감지 — CUSUM 4감지기 (남측/북측/허브/브릿지)")
    print(f"임계 Q{TH_CUSUM_Q:.0f}/저장{TH_CUSUM_FAB:.0f}/BR{TH_CUSUM_BR:.0f} · 창 {a.window}분 · 게이트(초위험 24h/그외 주간)")
    print("=" * 60)
    upto = datetime.strptime(a.at, '%Y-%m-%d %H:%M') if a.at else None

    if a.loop:
        print(f"[운영] {a.interval}초 간격 반복 (Ctrl+C 종료)")
        while True:
            try:
                once(a, upto)
                time.sleep(a.interval)
            except KeyboardInterrupt:
                print("\n종료."); break
            except Exception as e:
                print(f"  ⚠️ 오류(계속): {e}")
                time.sleep(a.interval)
    else:
        once(a, upto)


if __name__ == '__main__':
    main()
