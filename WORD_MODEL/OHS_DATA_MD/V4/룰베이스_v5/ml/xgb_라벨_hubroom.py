#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xgb_라벨_hubroom — hubroom_predictor 출력(발동이벤트)을 XGBoost 라벨(labels.csv)로 변환
====================================================================================
메신저 episode(56건·파편)로 라벨하던 걸, hubroom_predictor 의 매분 점수로 바꿈.
→ 4/1~5/31 매분이 촘촘히 라벨링돼서 데이터 파편화 해결.

[라벨 정의]
  y_pre30(t) = 1  : 앞으로 30분 안(t+1 ~ t+30)에 hubroom 위험(점수>=THR) 발생  → 정체 전조
             = 0  : 그 외
  is_normal(t)= 1 : 현재도, 과거·미래 ±GUARD 분도 경보(>=50) 없음 → 확실한 정상
             = 0 : 경보 근처 (학습 negative 에서 제외해 라벨 잡음 줄임)

★ 누수 차단: 피처는 t 까지, 라벨은 t 이후 30분 → 시간 방향 올바름.
★ hubroom 출력의 rule 점수는 라벨 만들 때만 쓰고, XGBoost 피처로는 안 씀
   (원신호 features.csv 로 예측해야 '룰 흉내'가 아니라 30분 선행 예측이 됨).

입력:
    --events   hubroom predict_tobe 폴더 (여러 날 *_발동이벤트.csv) 또는 단일 csv
    --thr      위험 판정 점수 (기본 71 = 회사표준 '위험'. 85=초위험만, 50=경계+)
    --pre      선행 창(분) 기본 30
    --guard    정상 가드(분) 기본 60
    --out      labels.csv 경로 (기본 ./out_ml/labels.csv)

실행:
    python xgb_라벨_hubroom.py --events ./predict_tobe --out ./out_ml/labels.csv
    # 그다음: python xgb_비정상_train.py --features ./out_ml/features.csv --labels ./out_ml/labels.csv
"""
import argparse
import csv
import glob
import os
import sys
from datetime import datetime, timedelta


def load_events(path):
    """발동이벤트 CSV(들)에서 (datetime, unified_risk_score) 시계열 로드."""
    files = []
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '*발동이벤트*.csv')))
        if not files:
            files = sorted(glob.glob(os.path.join(path, '*.csv')))
    else:
        files = [path]
    if not files:
        print(f"⚠️ 이벤트 파일 없음: {path}"); sys.exit(2)
    rows = {}
    for fp in files:
        with open(fp, encoding='utf-8-sig', newline='') as f:
            r = csv.DictReader(f)
            if 'unified_risk_score' not in (r.fieldnames or []):
                continue
            dtcol = 'datetime' if 'datetime' in r.fieldnames else None
            for x in r:
                dt = (x.get('datetime') or x.get('date', '') + ' ' + x.get('time', '')).strip()
                try:
                    t = datetime.strptime(dt[:16], '%Y-%m-%d %H:%M')
                except Exception:
                    continue
                try:
                    sc = float(x.get('unified_risk_score') or 0)
                except Exception:
                    sc = 0.0
                rows[t] = max(sc, rows.get(t, 0.0))   # 같은 분 중복이면 최대
    if not rows:
        print("⚠️ unified_risk_score 열이 있는 발동이벤트 파일을 못 찾음"); sys.exit(2)
    seq = sorted(rows.items())
    print(f"[이벤트] {len(files)}개 파일 → {len(seq)}분 로드 "
          f"({seq[0][0]:%Y-%m-%d} ~ {seq[-1][0]:%Y-%m-%d})")
    return seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', required=True, help='predict_tobe 폴더 또는 발동이벤트 csv')
    ap.add_argument('--thr', type=float, default=71, help='위험 점수 임계(기본 71)')
    ap.add_argument('--pre', type=int, default=30, help='선행 창(분)')
    ap.add_argument('--guard', type=int, default=60, help='정상 가드(분)')
    ap.add_argument('--alarm', type=float, default=50, help='경보(경계+) 기준점수')
    ap.add_argument('--out', default='./out_ml/labels.csv')
    a = ap.parse_args()

    seq = load_events(a.events)
    score = {t: s for t, s in seq}
    times = [t for t, _ in seq]

    # 인접 분 조회를 빠르게: 분 단위 정수 인덱스
    def z(t):
        return score.get(t, None)

    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    npos = nnorm = nrow = 0
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime', 'y_pre30', 'is_normal'])
        for t in times:
            # y_pre30: 미래 pre분 내 위험 도달?
            y = 0
            for k in range(1, a.pre + 1):
                s = z(t + timedelta(minutes=k))
                if s is not None and s >= a.thr:
                    y = 1; break
            # is_normal: 현재 ± guard 분 전부 경보 미만
            isn = 1
            cur = z(t)
            if cur is None or cur >= a.alarm:
                isn = 0
            else:
                for k in range(-a.guard, a.guard + 1):
                    s = z(t + timedelta(minutes=k))
                    if s is not None and s >= a.alarm:
                        isn = 0; break
            w.writerow([t.strftime('%Y-%m-%d %H:%M'), y, isn])
            nrow += 1; npos += y; nnorm += isn

    print(f"[완료] {nrow}분 → {a.out}")
    print(f"       정체전조 y_pre30=1 : {npos}분 ({npos/nrow*100:.1f}%)  [임계 {a.thr:.0f} / 선행 {a.pre}분]")
    print(f"       확실한 정상 is_normal=1 : {nnorm}분 ({nnorm/nrow*100:.1f}%)")
    print("다음: python xgb_비정상_train.py --features ./out_ml/features.csv --labels " + a.out)


if __name__ == '__main__':
    main()
