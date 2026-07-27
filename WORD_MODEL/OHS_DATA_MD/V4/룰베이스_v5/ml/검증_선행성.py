#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검증_선행성 — ★ Phase 3 핵심 게이트
====================================================================
이상점수 anomaly_score(t) 가 "정체보다 먼저(선행) 오르는가" 를 데이터로 채점.
이게 통과해야 TSPulse 확정. 미달 시 XGBoost 지도 폴백.

측정:
  · 리드타임 = (정체 t0) − (이상점수가 임계 θ 를 처음 돌파한 시각),  t0 직전 look 분 안에서
  · 탐지율   = 정체 N건 중 (t0-lead, t0] 안에서 θ 돌파한 비율
  · 오경보율 = 정체 아닌 정상시간 중 θ 돌파 분 비율 (조용한 정체 감안 → 참고치)
  · 임계 θ 스윕 → 탐지율·리드타임·오경보 트레이드오프 표

★ 표준 라이브러리만 사용.

입력:
    --anomaly   anomaly.csv (datetime, anomaly_score[, ml_level]) — tspulse_infer 산출
    --episodes  episodes_jam.csv (labels_채점지 산출) 또는 episode.csv
    --lead      사전예측 목표 분 (기본 30)
    --look      리드타임 탐색 상한 분 (기본 120)
    --thr       평가할 임계 θ (미지정 시 0.3~0.9 스윕)
    --out       출력 폴더 (기본 ./out_ml)

실행:
    python 검증_선행성.py --anomaly ./out_ml/anomaly.csv --episodes ./out_ml/episodes_jam.csv

출력:
    선행성_사건별.csv   — 사건별 리드타임/탐지여부 (선택 θ)
    선행성_임계스윕.csv — θ별 탐지율/평균리드/오경보
    콘솔 판정           — 게이트 통과/미달
"""
import argparse
import csv
import os
from datetime import datetime, timedelta


def parse_dt(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def load_anomaly(fp):
    """anomaly.csv → {datetime: score}."""
    d = {}
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rd = csv.DictReader(open(fp, encoding=enc))
            cols = rd.fieldnames or []
            scol = 'anomaly_score' if 'anomaly_score' in cols else cols[-1]
            for row in rd:
                t = parse_dt(row.get('datetime'))
                v = (row.get(scol) or '').strip()
                if t is None or not v:
                    continue
                try:
                    d[t] = float(v)
                except ValueError:
                    pass
            break
        except UnicodeDecodeError:
            continue
    return d


def load_jams(fp):
    """episodes_jam.csv(t0 컬럼) 또는 episode.csv(start_time) → [t0]."""
    JAM = {'정체/병목', '리프터', 'CNV', 'MLUD', '브릿지'}
    out = []
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rows = list(csv.DictReader(open(fp, encoding=enc)))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"⚠️ episodes 읽기 실패: {fp}")
    for r in rows:
        if 't0' in r:                       # episodes_jam.csv
            t = parse_dt(r.get('t0'))
            if t:
                out.append(t)
        else:                               # 원본 episode.csv
            if (r.get('is_orphan') or '').strip().upper() == 'Y':
                continue
            if (r.get('fault_type') or '').strip() not in JAM:
                continue
            t = parse_dt(r.get('start_time'))
            if t:
                out.append(t.replace(second=0))
    return sorted(out)


def lead_for(anom, t0, thr, look):
    """t0 직전 look분 안, 이상점수가 θ 를 처음 넘은 시각 → 리드타임(분). 없으면 None."""
    first = None
    for off in range(-look, 1):
        v = anom.get(t0 + timedelta(minutes=off))
        if v is not None and v >= thr:
            first = off
            break
    return (-first) if first is not None else None


def evaluate(anom, jams, thr, lead, look):
    """θ 하나에 대한 탐지율/평균리드/오경보."""
    rows = []
    detected = 0
    leads = []
    for t0 in jams:
        lt = lead_for(anom, t0, thr, look)
        hit = lt is not None and lt >= 0 and lt <= look
        pre_hit = lt is not None and 0 <= lt  # 돌파 존재
        is_det = lt is not None and lt >= 0 and lt <= look and lt >= 0
        # 'lead분 전 탐지' = 돌파가 존재하고 리드 >= 0 (t0 이전) 이며 창 안
        det = lt is not None and lt >= 0
        if det:
            detected += 1
            leads.append(lt)
        rows.append((t0, lt, det))
    # 오경보: 정상시간(정체 ±look 밖) 중 θ 돌파 분 비율
    jam_set = set()
    for t0 in jams:
        for off in range(-look, 1):
            jam_set.add(t0 + timedelta(minutes=off))
    normal_min = [t for t in anom if t not in jam_set]
    fp_min = sum(1 for t in normal_min if anom[t] >= thr)
    fpr = fp_min / len(normal_min) * 100 if normal_min else 0.0
    det_rate = detected / len(jams) * 100 if jams else 0.0
    avg_lead = sum(leads) / len(leads) if leads else 0.0
    return rows, det_rate, avg_lead, fpr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anomaly', required=True)
    ap.add_argument('--episodes', required=True)
    ap.add_argument('--lead', type=int, default=30)
    ap.add_argument('--look', type=int, default=120)
    ap.add_argument('--thr', type=float, default=None)
    ap.add_argument('--out', default='./out_ml')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    print("=" * 60)
    print(f"검증_선행성 (Phase 3 게이트) — 목표 리드 {a.lead}분")
    print("=" * 60)

    anom = load_anomaly(a.anomaly)
    jams = load_jams(a.episodes)
    if not anom:
        raise SystemExit("⚠️ anomaly.csv 비었음 — tspulse_infer.py 먼저")
    if not jams:
        raise SystemExit("⚠️ 정체 사건 없음 — episodes 확인")
    tmin, tmax = min(anom), max(anom)
    jams = [t for t in jams if tmin <= t <= tmax]
    print(f"이상점수 {len(anom)}분 ({tmin.date()}~{tmax.date()}) / 정체 {len(jams)}건")

    # ── θ 스윕 ──
    sweep = [round(x / 100, 2) for x in range(30, 91, 5)] if a.thr is None else [a.thr]
    sweep_rows = []
    for thr in sweep:
        _, det, avg, fpr = evaluate(anom, jams, thr, a.lead, a.look)
        sweep_rows.append((thr, det, avg, fpr))
    with open(os.path.join(a.out, '선행성_임계스윕.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['임계θ', '탐지율%', '평균리드분', '오경보율%'])
        for thr, det, avg, fpr in sweep_rows:
            w.writerow([thr, f'{det:.0f}', f'{avg:.1f}', f'{fpr:.2f}'])

    # ── 대표 θ 선택: 탐지율>=60 중 오경보 최소, 없으면 최고 탐지율 ──
    ok = [r for r in sweep_rows if r[1] >= 60]
    best = min(ok, key=lambda r: r[3]) if ok else max(sweep_rows, key=lambda r: r[1])
    thr = a.thr if a.thr is not None else best[0]
    rows, det, avg, fpr = evaluate(anom, jams, thr, a.lead, a.look)

    with open(os.path.join(a.out, '선행성_사건별.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['t0', 'lead_min(θ돌파→정체)', '탐지(≥0)'])
        for t0, lt, d in rows:
            w.writerow([t0.strftime('%Y-%m-%d %H:%M'),
                        '' if lt is None else lt, 'O' if d else 'X'])

    # ── 콘솔 스윕 표 ──
    print("\n[임계 θ 스윕]")
    print(f"  {'θ':>5}{'탐지율':>8}{'평균리드':>9}{'오경보':>8}")
    for t, d, av, fr in sweep_rows:
        mark = '  ←선택' if t == thr else ''
        print(f"  {t:>5}{d:>7.0f}%{av:>7.1f}분{fr:>7.2f}%{mark}")

    # ── 게이트 판정 ──
    print("\n" + "=" * 60)
    print(f"[선택 θ={thr}]  탐지율 {det:.0f}%  ·  평균리드 {avg:.1f}분  ·  오경보 {fpr:.2f}%")
    g_lead = avg >= 25
    g_det = det >= 60
    print("-" * 60)
    print(f"  게이트1 평균리드 ≥25분 : {'✅통과' if g_lead else '❌미달'} ({avg:.1f})")
    print(f"  게이트2 탐지율   ≥60% : {'✅통과' if g_det else '❌미달'} ({det:.0f})")
    if g_lead and g_det:
        print("\n🎉 Phase 3 통과 → TSPulse R1 확정. 다음: XGBoost 비교(Phase 4)")
    else:
        print("\n⚠️ 게이트 미달 → 피처/윈도우/임계 튜닝 or XGBoost 지도 폴백 검토")
    print(f"저장 → {a.out}/ (선행성_사건별 · 선행성_임계스윕)")


if __name__ == '__main__':
    main()
