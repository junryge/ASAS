#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드_판정 — XGBoost 예측 + 저장룰(반송시간 확인) 결합 최종 판정
====================================================================================
[구조] 캐스케이드 흐름(하이브리드)
  ① XGBoost   : 60분 흐름 → 30분/10분 정체확률 (점진 정체: 6/2·6/5형)
  ② 저장룰    : (RD_FAB≥25 OR RD_STB≥99) AND 반송시간 실제상승 → 저장경보 (저장Full: 6/16형)
                ★ 반송시간 확인으로 6/4형(저장 튀어도 반송 정상=소화됨) 오탐 차단
  ③ 최종판정  : 두 신호 결합(max) + 사유 표기 → LLM 진단/리포트 입력

hubroom_predictor.py 저장 룰 임계 그대로 사용:
  TH_RD_FABSTORAGE=25.0 / TH_RD_HUB_STB_UTIL=99.0

입력:
    --xgb       xgb_비정상_infer 산출 (june_prob.csv: y_pre10/30_prob)
    --features  features_31 산출 (RD_FAB·RD_STB·RA_M16HUB 반송시간 포함)
    --ra_up     반송시간 '상승' 판정 임계(분). 기본 6.0 (SLA 4분초과의 여유선)
    --out       기본 ./out_ml/hybrid_verdict.csv

실행:
    python 하이브리드_판정.py --xgb ./out_ml/june_prob.csv --features ./out_ml/june/features.csv

출력:
    hybrid_verdict.csv — datetime, 최종등급, 사유, xgb30_prob, xgb10_prob,
                         저장경보, rd_fab, rd_stb, ra_m16hub(반송시간)
"""
import argparse
import csv
import os
from datetime import datetime

TH_RD_FAB = 25.0      # FAB저장률 임계 (hubroom 동일)
TH_RD_STB = 99.0      # STB이용률 임계 (hubroom 동일)


def load_csv(fp):
    with open(fp, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def xgb_level30(p):
    return '위험' if p >= 0.50 else ''


def xgb_level10(p):
    return '초위험' if p >= 0.90 else '위험' if p >= 0.70 else '경계' if p >= 0.50 else ''


# 등급 강도 순위 (max 결합용)
RANK = {'': 0, '경계': 1, '위험': 2, '초위험': 3}
INV = {v: k for k, v in RANK.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xgb', required=True)
    ap.add_argument('--features', required=True)
    ap.add_argument('--sla_up', type=float, default=5.0,
                    help="4분초과율(SLA_M16HUB) '실제정체' 확인 임계(%). 6/4는 0이라 차단됨")
    ap.add_argument('--out', default='./out_ml/hybrid_verdict.csv')
    a = ap.parse_args()

    xgb = {r['datetime'].strip(): r for r in load_csv(a.xgb)}
    feat = {r['datetime'].strip(): r for r in load_csv(a.features)}

    # 반송시간 컬럼명 (features_31 short): RA_M16HUB / 저장: RD_FAB, RD_STB
    times = sorted(set(xgb) & set(feat), key=lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M'))
    if not times:
        print("⚠️ xgb 와 features 의 datetime 이 안 맞음 — 형식 확인"); return

    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    n_xgb = n_stor = n_final = n_stor_blocked = 0
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['datetime', '최종등급', '사유', 'xgb30_prob', 'xgb10_등급',
                    '저장경보', 'rd_fab', 'rd_stb', 'sla_4분초과율', 'ra_반송시간'])
        for t in times:
            xr, fr = xgb[t], feat[t]
            p30 = fnum(xr.get('y_pre30_prob')) or 0.0
            p10 = fnum(xr.get('y_pre10_prob')) or 0.0
            rd_fab = fnum(fr.get('RD_FAB'))
            rd_stb = fnum(fr.get('RD_STB'))
            ra = fnum(fr.get('RA_M16HUB'))
            sla = fnum(fr.get('SLA_M16HUB'))        # 4분초과율(%) = 실제 정체 지표

            # ① XGBoost 등급 (30분 우선, 10분 초위험이면 승격)
            g_xgb = xgb_level30(p30)
            g10 = xgb_level10(p10)
            if RANK[g10] > RANK[g_xgb]:
                g_xgb = g10
            reasons = []
            if g_xgb:
                reasons.append(f"XGBoost 30분{p30*100:.0f}%/10분{p10*100:.0f}%")

            # ② 저장룰 + 실제정체 확인 (6/4형 오탐 차단)
            #    확인 지표 = SLA(4분초과율). 6/4는 저장 튀어도 SLA=0(소화) → 차단.
            stor_raw = ((rd_fab is not None and rd_fab >= TH_RD_FAB)
                        or (rd_stb is not None and rd_stb >= TH_RD_STB))
            congested = (sla is not None and sla >= a.sla_up)
            stor_alarm = stor_raw and congested
            g_stor = ''
            if stor_raw and not congested:
                n_stor_blocked += 1                     # 저장 튀었지만 4분초과 없음 → 소화(6/4형)
            if stor_alarm:
                g_stor = '위험'
                why = []
                if rd_fab is not None and rd_fab >= TH_RD_FAB:
                    why.append(f"FAB저장{rd_fab:.0f}%≥{TH_RD_FAB:.0f}")
                if rd_stb is not None and rd_stb >= TH_RD_STB:
                    why.append(f"STB{rd_stb:.0f}%≥{TH_RD_STB:.0f}")
                reasons.append(f"저장경보({'+'.join(why)}, 4분초과{sla:.0f}%)")

            # ③ 최종 = max(XGBoost, 저장경보)
            final = INV[max(RANK[g_xgb], RANK[g_stor])]

            if g_xgb:
                n_xgb += 1
            if stor_alarm:
                n_stor += 1
            if final:
                n_final += 1

            w.writerow([t, final, ' | '.join(reasons),
                        f'{p30:.3f}', g10 or '',
                        '예' if stor_alarm else '',
                        '' if rd_fab is None else f'{rd_fab:.1f}',
                        '' if rd_stb is None else f'{rd_stb:.1f}',
                        '' if sla is None else f'{sla:.1f}',
                        '' if ra is None else f'{ra:.1f}'])

    print(f"[하이브리드] {len(times)}분 판정 → {a.out}")
    print(f"   XGBoost 경보 {n_xgb}분 · 저장경보 {n_stor}분 · 최종경보 {n_final}분")
    print(f"   저장 튀었지만 반송정상으로 차단(6/4형 오탐방지) {n_stor_blocked}분")
    print("   사유 컬럼에 '어느 신호가 왜' 울렸는지 표기 → LLM 진단 입력")


if __name__ == '__main__':
    main()
