#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
밀림_실시간_V9 — CUSUM 룰 + V9 큐전망 합본 (매분 1행)
====================================================================
한 파일에 둘 다 기입:
  · CUSUM 4감지기 룰 (남측600/북측600/저장300/브릿지40 · 게이트: 초위험 24h, 그외 주간)
  · V9 큐 전망 (10분후 HUB총큐 예측 — 참고용, 6월 홀드아웃 R² 낮음)

출력(매분 1행): realtime_cusum_v9_YYYYMMDD.csv
  측정시간 | 예측시각(10분후) | 현재큐 | V9_MAX변화 | V9_10분후큐 |
  남큐CUSUM | 북큐CUSUM | 저장CUSUM | 브릿지CUSUM | 밀림방향 | 예측결과 | 사유

전제: HUBROOM_V9.PY + xgboost_수치형_V9.pkl 같은 폴더. pip: pandas numpy xgboost

실행:
  하루 재계산(배치):  python 밀림_실시간_V9.py --raw .\RAW            (최신 파일 기준)
  운영 반복:          python 밀림_실시간_V9.py --raw .\RAW --loop     (60초마다 오늘파일 갱신)
  기간 전체:          python 밀림_실시간_V9.py --raw .\OUT_6 --alldays (6월 30일치 일별 생성)
"""
import argparse, importlib.machinery, importlib.util, os, pickle, sys, time

# ── CUSUM 룰 (밀림_실시간.py 와 동일 — 6월 검증값) ──
CUSUM_BASE_WIN = 120
CUSUM_K = 0.5
TH = {'남측': 600.0, '북측': 600.0, '허브': 300.0, '브릿지': 40.0}
TH_RD_STK = 10.0
SRC = {'남측': 'M14.QUE.CNV.SOUTHCURRENTQCNT', '북측': 'M14.QUE.CNV.NORTHCURRENTQCNT',
       '허브': 'M16HUB.STRATE.ALL.FABSTORAGERATIO', '브릿지': 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN'}
DIR_LABEL = {'남측': '남측(4AFC3201)', '북측': '북측(4AFC3301)',
             '허브': '허브(몰림/저장)', '브릿지': '브릿지(BridgeTime상승)'}
GRADE_ORD = {'': 0, '경계': 1, '위험': 2, '초위험': 3}
COLS = ['측정시간', '예측시각(10분후)', '현재큐', 'V9_MAX변화', 'V9_10분후큐',
        '남큐CUSUM', '북큐CUSUM', '저장CUSUM', '브릿지CUSUM',
        '밀림방향', '예측결과', '사유']


def load_v9():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ('HUBROOM_V9.PY', 'HUBROOM_V9.py'):
        fp = os.path.join(here, name)
        if os.path.exists(fp):
            loader = importlib.machinery.SourceFileLoader('HUBROOM_V9', fp)
            spec = importlib.util.spec_from_loader('HUBROOM_V9', loader)
            mod = importlib.util.module_from_spec(spec)
            loader.exec_module(mod)
            return mod
    raise SystemExit('❌ HUBROOM_V9.PY 필요 (같은 폴더)')


def cusum_series(pd, np, s):
    x = pd.Series(s).astype(float)
    base = x.shift(1).rolling(CUSUM_BASE_WIN, min_periods=15).median().bfill()
    base = base.fillna(x.iloc[0] if len(x) else 0.0)
    sd = x.shift(1).rolling(CUSUM_BASE_WIN, min_periods=15).std().fillna(0.0).values
    base = base.values; xv = x.values
    C = np.zeros(len(xv)); prev = 0.0
    for i in range(len(xv)):
        prev = max(0.0, prev + (xv[i] - base[i] - CUSUM_K * sd[i])); C[i] = prev
    return C


def grade(cu, thr):
    if cu < thr:
        return '', 0.0
    r = cu / thr
    return ('초위험' if r >= 2.5 else '위험' if r >= 1.5 else '경계'), r


def gated(g, hour):
    if g == '초위험':
        return g
    if g in ('위험', '경계') and 8 <= hour <= 19:
        return g
    return ''


def process(df, v9, models, feat_names, pd, np):
    """df(시간정렬, 30분+ 문맥 포함) → 매분 결과 rows (문맥 제외한 대상 구간만 반환은 호출부에서)."""
    # V9 예측 (미래 라벨용으로 마지막행 HORIZON+1개 패딩 → 마지막 분까지 피처 생성)
    pad = pd.concat([df, pd.concat([df.iloc[[-1]]] * (v9.HORIZON + 1), ignore_index=True)],
                    ignore_index=True)
    pad.loc[len(df):, 'CRT_TM'] = [df['CRT_TM'].iloc[-1] + pd.Timedelta(minutes=k + 1)
                                   for k in range(v9.HORIZON + 1)]
    X, _, idx = v9.create_features_v9(pad, set(df.columns), stride=1)
    for c in feat_names:
        if c not in X.columns:
            X[c] = 0.0
    X = X[feat_names]
    vmax = models[1].predict(X)
    # idx→예측 매핑 (실데이터 범위만)
    v9_at = {}
    for k, i in enumerate(idx):
        if i < len(df):
            v9_at[i] = vmax[k]

    # CUSUM 4감지기
    def col(name):
        return (pd.to_numeric(df[name], errors='coerce').ffill().fillna(0.0).values
                if name in df.columns else np.zeros(len(df)))
    cu = {d: cusum_series(pd, np, col(c)) for d, c in SRC.items()}
    stk = col('M16HUB.STRATE.STK.STORAGERATIO')
    curq = col('M16HUB.QUE.ALL.CURRENTQCNT')
    hours = df['CRT_TM'].dt.hour.values

    rows = []
    for i in range(len(df)):
        t = df['CRT_TM'].iloc[i]
        cand = []
        for d in TH:
            g, r = grade(cu[d][i], TH[d])
            if d == '허브' and stk[i] >= TH_RD_STK and GRADE_ORD['위험'] > GRADE_ORD[g]:
                g, r = '위험', max(r, 1.5)
            gg = gated(g, hours[i])
            if gg:
                nm = {'남측': '남측큐', '북측': '북측큐', '허브': '허브저장', '브릿지': '브릿지타임'}[d]
                cand.append((gg, r, d, f"{nm} 지속상승 CUSUM {cu[d][i]:.0f}({r:.1f}배)"))
        best = max(cand, key=lambda x: (GRADE_ORD[x[0]], x[1])) if cand else None
        vm = v9_at.get(i)
        rows.append({
            '측정시간': t.strftime('%Y-%m-%d %H:%M'),
            '예측시각(10분후)': (t + pd.Timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M'),
            '현재큐': f'{curq[i]:.0f}',
            'V9_MAX변화': f'{vm:+.0f}' if vm is not None else '',
            'V9_10분후큐': f'{curq[i] + vm:.0f}' if vm is not None else '',
            '남큐CUSUM': f'{cu["남측"][i]:.0f}', '북큐CUSUM': f'{cu["북측"][i]:.0f}',
            '저장CUSUM': f'{cu["허브"][i]:.0f}', '브릿지CUSUM': f'{cu["브릿지"][i]:.0f}',
            '밀림방향': DIR_LABEL[best[2]] if best else '',
            '예측결과': '예측' if best else '미예측',
            '사유': best[3] if best else '',
        })
    return rows


def write_day(outdir, day, rows, csv):
    os.makedirs(outdir, exist_ok=True)
    fp = os.path.join(outdir, f'realtime_cusum_v9_{day}.csv')
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader(); w.writerows(rows)
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--model', default='xgboost_수치형_V9.pkl')
    ap.add_argument('--outdir', default='./밀림예측')
    ap.add_argument('--alldays', action='store_true', help='폴더 내 모든 날짜 일괄 생성')
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--interval', type=int, default=60)
    a = ap.parse_args()

    import csv
    import numpy as np
    import pandas as pd
    v9 = load_v9()
    with open(a.model, 'rb') as f:
        md = pickle.load(f)
    models, feat_names = md['models'], md['feature_names']
    print('=' * 60)
    print('밀림 실시간 V9합본 — CUSUM 4룰 + V9 큐전망 (매분 1행)')
    print('=' * 60)

    def run_once():
        df = v9.load_raw(a.raw)
        days = sorted(df['CRT_TM'].dt.strftime('%Y%m%d').unique())
        targets = days if a.alldays else days[-1:]
        for day in targets:
            # 해당 일 + 앞 문맥 240분
            mask = df['CRT_TM'].dt.strftime('%Y%m%d') == day
            start = df.index[mask][0]
            ctx = df.iloc[max(0, start - 240):df.index[mask][-1] + 1].reset_index(drop=True)
            rows = process(ctx, v9, models, feat_names, pd, np)
            rows = [r for r in rows if r['측정시간'][:10].replace('-', '') == day]
            fp = write_day(a.outdir, day, rows, csv)
            last = rows[-1]
            mark = f"🔴 {last['밀림방향']} | {last['사유']}" if last['예측결과'] == '예측' else '⚪ 미예측'
            print(f"[{last['측정시간']}] {mark} | 현재큐 {last['현재큐']} → V9 10분후 {last['V9_10분후큐']}"
                  f"  ({len(rows)}행 → {os.path.basename(fp)})")

    if a.loop:
        print(f'[운영] {a.interval}초 간격 (Ctrl+C 종료)')
        while True:
            try:
                run_once(); time.sleep(a.interval)
            except KeyboardInterrupt:
                print('\n종료.'); break
            except Exception as e:
                print(f'  ⚠️ 오류(계속): {e}'); time.sleep(a.interval)
    else:
        run_once()
        print('🎉 완료')


if __name__ == '__main__':
    main()
