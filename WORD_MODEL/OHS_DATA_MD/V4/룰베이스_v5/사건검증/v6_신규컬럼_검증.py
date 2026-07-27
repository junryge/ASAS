#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6 발동이벤트 신규 컬럼 검증 — 지속성/재발생/예측유형

기존 발동이벤트.csv 의 매분 메트릭을 hubroom_predictor.py 의 새 로직으로
재시뮬하여 4개 신규 컬럼 값이 제대로 채워지는지 + fault_type 추론이
메신저 라벨과 얼마나 일치하는지 검증.
"""
import csv, glob, os, sys
from datetime import datetime, timedelta
from collections import Counter

V4 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA = os.path.join(V4, '룰베이스_v5', '데이터들', 'extracted')
AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']

TH = {'RA': {'M16HUB': 9.0, 'M14': 3.3, 'M14B': 5.0, 'M16A': 3.2, 'M16B': 3.5},
      'RB30': {'M16HUB': 100, 'M14': 80, 'M14B': 150, 'M16A': 84, 'M16B': 32},
      'RC': 4, 'FAB': 25.75, 'STB': 99.3,
      'SLA': {'M16HUB': 5.0, 'M14': 25.45, 'M16A': 14.05, 'M16B': 22.05}}
GAP = 60


def fnum(r, k):
    v = (r.get(k) or '').strip()
    try: return float(v)
    except: return None


def s3(r):
    ra = any(fnum(r, f'{a}_ra') is not None and fnum(r, f'{a}_ra') >= TH['RA'][a] for a in AREAS)
    rb = any(fnum(r, f'{a}_rb_diff30') is not None and fnum(r, f'{a}_rb_diff30') >= TH['RB30'][a] for a in AREAS)
    rev = fnum(r, 'M16HUB_rev_count'); tr = fnum(r, 'M16HUB_rc_trend')
    rc = (rev is not None and tr is not None and tr < 0 and rev >= TH['RC'])
    fab = fnum(r, 'M16HUB_rd_fab'); stb = fnum(r, 'M16HUB_stb_util')
    rd = (fab is not None and fab >= TH['FAB']) or (stb is not None and stb >= TH['STB'])
    sla = any(fnum(r, f'sla_{a}') is not None and fnum(r, f'sla_{a}') >= TH['SLA'][a] for a in TH['SLA'])
    flow = (fnum(r, 'flow_score') or 0) >= 15
    return ra and (rd or sla or rc) and (rb or flow)


def _top_type(types):
    """voting — '기타' 약화 (명확한 유형이 1번이라도 떠있으면 그걸 우선)."""
    if not types: return ''
    non_other = [(t, c) for t, c in types.most_common() if t not in ('기타', '')]
    if non_other:
        # '기타' 압도적(10배 이상)이 아니면 명확한 유형 선택
        other_c = types.get('기타', 0)
        top_c = non_other[0][1]
        if other_c >= top_c * 10:
            return '기타'
        return non_other[0][0]
    return '기타'


def predict_fault_type(r):
    """v6.3 — 데이터 직독: hot_area + 증상 키워드 (운영자 즉시 이해)."""
    scores = {a: fnum(r, f'{a}_score') or 0 for a in AREAS}
    hot_area = max(scores, key=scores.get)
    if scores[hot_area] < 10:
        return ''
    affected = sum(1 for s in scores.values() if s >= 30)

    # 광역 우선 — 3개 이상 영역 동시
    if affected >= 4:
        return '광역정체'

    if hot_area == 'M16HUB':
        rev = fnum(r, 'M16HUB_rev_count') or 0
        rc_trend = fnum(r, 'M16HUB_rc_trend') or 0
        fab = fnum(r, 'M16HUB_rd_fab') or 0
        stb = fnum(r, 'M16HUB_stb_util') or 0
        rb30 = fnum(r, 'M16HUB_rb_diff30') or 0
        ra = fnum(r, 'M16HUB_ra') or 0
        if rev >= 4 and rc_trend < 0:    return 'HUB-리프터역증가'
        if fab >= TH['FAB']:             return 'HUB-FAB정체'
        if stb >= TH['STB']:             return 'HUB-STB정체'
        if rb30 >= 100:                  return 'HUB-큐누적'
        if ra >= TH['RA']['M16HUB']:     return 'HUB-반송지연'
        return 'HUB-신호'
    if hot_area == 'M14':
        if (fnum(r, 'M14_cnv_skew') or 0) >= 1.5:        return 'M14-CNV쏠림'
        if (fnum(r, 'sorter_M14') or 0) >= 148:          return 'M14-Sorter대기'
        if (fnum(r, 'M14_rd_oht') or 0) >= 95:           return 'M14-OHT정체'
        if (fnum(r, 'sla_M14') or 0) >= TH['SLA']['M14']:return 'M14-SLA초과'
        if (fnum(r, 'M14_ra') or 0) >= TH['RA']['M14']:  return 'M14-반송지연'
        return 'M14-신호'
    if hot_area == 'M14B':
        if (fnum(r, 'sorter_M14B') or 0) >= 109:         return 'M14B-Sorter대기'
        if (fnum(r, 'M14B_rd_oht') or 0) >= 95:          return 'M14B-OHT정체'
        if (fnum(r, 'M14B_ra') or 0) >= TH['RA']['M14B']:return 'M14B-반송지연'
        return 'M14B-신호'
    if hot_area == 'M16A':
        if (fnum(r, 'sorter_M16A') or 0) >= 180:                return 'M16A-Sorter대기'
        if (fnum(r, 'sla_M16A') or 0) >= TH['SLA']['M16A']:     return 'M16A-SLA초과'
        if (fnum(r, 'M16A_rd_oht') or 0) >= 95:                 return 'M16A-OHT정체'
        if (fnum(r, 'M16A_ra') or 0) >= TH['RA']['M16A']:       return 'M16A-반송지연'
        return 'M16A-신호'
    if hot_area == 'M16B':
        if (fnum(r, 'sorter_M16B') or 0) >= 90:                 return 'M16B-Sorter대기'
        if (fnum(r, 'sla_M16B') or 0) >= TH['SLA']['M16B']:     return 'M16B-SLA초과'
        if (fnum(r, 'M16B_rd_oht') or 0) >= 95:                 return 'M16B-OHT정체'
        if (fnum(r, 'M16B_ra') or 0) >= TH['RA']['M16B']:       return 'M16B-반송지연'
        return 'M16B-신호'
    return ''


def main():
    # 매분 발동이벤트 로드 + 새 컬럼 시뮬
    annotated = []  # (datetime, incident_state, continuity_min, refire_count, fault_type, score)
    incident_log = []  # 사건 단위 (검증용)
    state = 'IDLE'
    current = None

    for fp in sorted(glob.glob(f'{DATA}/predict_tobe/*_발동이벤트.csv')):
        rows = []
        for r in csv.DictReader(open(fp, encoding='utf-8-sig')):
            try: r['_t'] = datetime.strptime(r['datetime'], '%Y-%m-%d %H:%M')
            except: continue
            rows.append(r)
        for r in rows:
            t = r['_t']
            sc = fnum(r, 'unified_risk_score') or 0
            ft = predict_fault_type(r)
            in_s3 = s3(r)
            if state == 'IDLE':
                if in_s3:
                    current = {'start': t, 'last_s3': t, 'refire': 0, 'max_score': sc, 'types': Counter()}
                    state = 'IN_INCIDENT'
            else:
                if in_s3:
                    gap = (t - current['last_s3']).total_seconds() / 60
                    if gap >= GAP:
                        current['refire'] += 1
                    current['last_s3'] = t
                    current['max_score'] = max(current['max_score'], sc)
                else:
                    gap = (t - current['last_s3']).total_seconds() / 60
                    if gap >= GAP:
                        # 사건 종료
                        if current['max_score'] >= 100:
                            incident_log.append(current)
                        current = None; state = 'IDLE'

            if state == 'IN_INCIDENT' and current:
                inc_state = 'IN_INCIDENT'
                cont = int((t - current['start']).total_seconds() / 60) + 1
                refire = current['refire']
                if ft: current['types'][ft] += 1
            else:
                inc_state = 'IDLE'; cont = 0; refire = 0
            annotated.append((t, inc_state, cont, refire, ft, sc))
    if current and current['max_score'] >= 100:
        incident_log.append(current)

    # 통계
    print("="*80)
    print("  v6 신규 컬럼 검증 — 지속성/재발생/예측유형")
    print("="*80)
    total = len(annotated)
    in_inc = sum(1 for x in annotated if x[1] == 'IN_INCIDENT')
    print(f"\n  전체 분 수: {total:,}분 (4-5월 매분)")
    print(f"  사건 진행 중 분: {in_inc:,}분 ({in_inc/total*100:.1f}%)")
    print(f"  사건 수 (점수 100+): {len(incident_log)}건")

    # 지속성 분포
    print(f"\n  [지속성 분포 — continuity_min]")
    dur_dist = Counter()
    for inc in incident_log:
        last = inc['last_s3']
        dur = int((last - inc['start']).total_seconds() / 60) + 1
        if dur <= 15: dur_dist['~15분'] += 1
        elif dur <= 60: dur_dist['16~60분'] += 1
        elif dur <= 180: dur_dist['61~180분 (지속)'] += 1
        elif dur <= 360: dur_dist['181~360분 (장기지속)'] += 1
        else: dur_dist['360분+ (초장기)'] += 1
    for k, v in sorted(dur_dist.items()):
        print(f"    {k:18s}: {v}건")

    # 재발생 분포
    print(f"\n  [재발생 분포 — refire_count]")
    rf_dist = Counter()
    for inc in incident_log:
        r = inc['refire']
        if r == 0: rf_dist['0회 (1회성)'] += 1
        elif r <= 2: rf_dist['1~2회 (낮음)'] += 1
        elif r <= 5: rf_dist['3~5회 (중간)'] += 1
        else: rf_dist['6회+ (잦은 재발생)'] += 1
    for k, v in sorted(rf_dist.items()):
        print(f"    {k:18s}: {v}건")

    # 예측유형 분포
    print(f"\n  [예측 장애 유형 분포 (사건별 최다 유형)]")
    type_dist = Counter()
    for inc in incident_log:
        if inc['types']:
            top = inc['types'].most_common(1)[0][0]
            type_dist[top] += 1
        else:
            type_dist['(추론없음)'] += 1
    for k, v in type_dist.most_common():
        print(f"    {k:12s}: {v}건")

    # 메신저 매칭 — 예측유형 정확도
    efp = sorted(glob.glob(f'{DATA}/episode_out/*_episode.csv'))[-1]
    eps = []
    for e in csv.DictReader(open(efp, encoding='utf-8-sig')):
        if e.get('is_orphan') == 'Y' or e.get('fault_type') == 'CAPA변경': continue
        try:
            eps.append({'start': datetime.strptime(e['start_time'], '%Y-%m-%d %H:%M:%S'),
                        'end': datetime.strptime(e['end_time'], '%Y-%m-%d %H:%M:%S'),
                        'type': e.get('fault_type', '')})
        except: pass

    PRE = timedelta(minutes=30); POST = timedelta(minutes=60)
    for inc in incident_log:
        inc['m'] = False; inc['matched_type'] = ''
    matches = []
    for ep in sorted(eps, key=lambda x: x['start']):
        best = None
        for inc in incident_log:
            if inc['m']: continue
            if inc['start'] - PRE <= ep['start'] <= inc['last_s3'] + POST:
                lead = (ep['start'] - inc['start']).total_seconds()/60
                if best is None or lead < best[1]: best = (inc, lead, ep)
        if best:
            best[0]['m'] = True
            best[0]['matched_type'] = best[2]['type']
            matches.append((best[0], best[2]))

    print(f"\n  [예측유형 정확도 — 메신저 매칭 {len(matches)}건]")
    correct = 0; partial = 0
    detail = Counter()
    for inc, ep in matches:
        pred = _top_type(inc['types'])
        actual = ep['type']
        detail[f'{actual} → {pred}'] += 1
        if pred == actual: correct += 1
        elif pred and actual:
            # 부분 매치
            if (pred == '정체/병목' and actual in ('CNV', '리프터')) or \
               (pred == '기타' and actual): partial += 1
    print(f"    정확 매칭: {correct}/{len(matches)} ({correct/max(1,len(matches))*100:.0f}%)")
    print(f"    부분 매칭: {partial}/{len(matches)}")
    print(f"\n  [예측→실제 분포 TOP 8]")
    for k, v in detail.most_common(8):
        print(f"    {k:30s}: {v}건")

    # 샘플 — 지속성 + 재발생 TOP 5
    print(f"\n  [지속성 + 재발생 TOP 5 사건]")
    top = sorted(incident_log, key=lambda x: -(((x['last_s3']-x['start']).total_seconds()/60) + x['refire']*30))[:5]
    for inc in top:
        dur = int((inc['last_s3']-inc['start']).total_seconds()/60)+1
        top_type = inc['types'].most_common(1)[0][0] if inc['types'] else '-'
        m = f"✅매칭({inc['matched_type']})" if inc['m'] else '❌미매칭'
        print(f"    {inc['start'].strftime('%m-%d %H:%M')} 지속{dur:>4}분 재발{inc['refire']}회 "
              f"점수{inc['max_score']:.0f} 예측[{top_type}] {m}")


if __name__ == '__main__':
    main()
