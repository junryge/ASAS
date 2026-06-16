#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발동이벤트 점수분석 — 점수가 '어느 컬럼/룰에서' 나왔는지 분해

사용법:
  python 발동이벤트_점수분석.py <발동이벤트.csv>
  python 발동이벤트_점수분석.py <발동이벤트.csv> 06:55        # 특정 시각
  python 발동이벤트_점수분석.py <발동이벤트.csv> --top 5       # 점수 높은 5개 분

인자 없이 시각만 안 주면 → 그 파일에서 점수(unified_risk_score) 최고점 1개 분석.
"""
import csv
import sys

# 윈도우 cp949 콘솔에서도 한글/유니코드(— 등) 깨지지 않게 stdout UTF-8 강제
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

AREAS5 = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']
RULES = ['RA', 'RA_sus', 'RB', 'RB_fast', 'RC', 'RD', 'SLA', 'SORT', 'MAXCAPA']
RULE_KR = {
    'RA': '반송지연', 'RA_sus': '반송지연지속', 'RB': '큐누적', 'RB_fast': '큐급증',
    'RC': '리프터역증가', 'RD': 'FAB/STB/OHT정체', 'SLA': 'SLA초과',
    'SORT': 'Sorter대기', 'MAXCAPA': 'MAXCAPA변경',
}


def fnum(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return 0


def analyze_row(r):
    print("=" * 70)
    print(f"  {r.get('datetime','')} | 점수 {r.get('unified_risk_score','')} "
          f"[{r.get('unified_risk_level','')}] | hot={r.get('hot_area','')} "
          f"| 예측유형 {r.get('predicted_fault_type','')}")
    print("=" * 70)

    # ── 점수 구성 (5대 컴포넌트) ──
    layer1 = fnum(r, 'layer1_total')
    flow = fnum(r, 'flow_score')
    sla = fnum(r, 'sla_score_total')
    sorter = fnum(r, 'sorter_score_total')
    mc = fnum(r, 'mc_score_total')
    total = layer1 + flow + sla + sorter + mc
    print(f"\n  [점수 구성]  합계 = {total:.0f}")
    print(f"    영역점수합(layer1) : {layer1:>4.0f}")
    print(f"    흐름정체(flow)     : {flow:>4.0f}")
    print(f"    SLA초과            : {sla:>4.0f}")
    print(f"    Sorter             : {sorter:>4.0f}")
    print(f"    MAXCAPA            : {mc:>4.0f}")

    # ── 영역별 × 룰별 점수 기여 (pts 컬럼) ──
    print(f"\n  [어느 영역 / 어느 룰이 점수를 만들었나]")
    print(f"  {'영역':<8}", end='')
    for rule in RULES:
        print(f"{rule:>8}", end='')
    print(f"{'합':>6}")
    print("  " + "-" * 86)
    for area in AREAS5:
        vals = [fnum(r, f'{area}_pts_{rule}') for rule in RULES]
        s = sum(vals)
        if s == 0:
            continue
        print(f"  {area:<8}", end='')
        for v in vals:
            print(f"{(int(v) if v else '·'):>8}", end='')
        print(f"{s:>6.0f}")

    # ── 발동 룰 상세 (점수 0 초과만, 한글 설명 + 실측값) ──
    print(f"\n  [발동한 룰 상세 — 실측값]")
    raw = {
        'ra': {a: fnum(r, f'{a}_ra') for a in AREAS5},
        'rb': {a: fnum(r, f'{a}_rb_diff30') for a in AREAS5},
        'sla': {a: fnum(r, f'sla_{a}') for a in AREAS5},
        'sorter': {a: fnum(r, f'sorter_{a}') for a in ('M14','M14B','M16A','M16B','M16HUB')},
    }
    for area in AREAS5:
        parts = []
        for rule in RULES:
            pts = fnum(r, f'{area}_pts_{rule}')
            if pts <= 0:
                continue
            tag = f"{RULE_KR[rule]}({int(pts)}점"
            if rule in ('RA', 'RA_sus'):
                tag += f", 반송={raw['ra'][area]:.1f}분"
            elif rule in ('RB', 'RB_fast'):
                tag += f", 큐+{int(raw['rb'][area])}/30분"
            elif rule == 'RD' and area == 'M16HUB':
                tag += f", FAB={fnum(r,'M16HUB_rd_fab'):.0f}%/STB={fnum(r,'M16HUB_stb_util'):.0f}%"
            elif rule == 'RC' and area == 'M16HUB':
                tag += f", 역증가={int(fnum(r,'M16HUB_rev_count'))}개"
            elif rule == 'SLA':
                tag += f", {raw['sla'][area]:.1f}%4분초과"
            elif rule == 'SORT':
                tag += f", {int(raw['sorter'].get(area,0))}LOT대기"
            tag += ")"
            parts.append(tag)
        if parts:
            print(f"    {area}: " + ", ".join(parts))

    # 흐름 정체
    fs = r.get('flow_signals', '')
    if fs:
        print(f"    흐름: {fs}")
    print()


def main():
    if len(sys.argv) < 2:
        print("사용법: python 발동이벤트_점수분석.py <발동이벤트.csv> [HH:MM | --top N]")
        return
    path = sys.argv[1]
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    # S3(확정) 만 — 점수 의미 있는 행
    rows = [r for r in rows if (r.get('time') or '')]

    target_time = None
    top_n = 1
    if len(sys.argv) >= 3:
        a = sys.argv[2]
        if a == '--top' and len(sys.argv) >= 4:
            top_n = int(sys.argv[3])
        else:
            target_time = a  # HH:MM

    if target_time:
        hits = [r for r in rows if (r.get('time') == target_time
                                    or r.get('datetime', '').endswith(target_time))]
        if not hits:
            print(f"{target_time} 행 없음")
            return
        for r in hits:
            analyze_row(r)
    else:
        rows_sorted = sorted(rows, key=lambda r: fnum(r, 'unified_risk_score'), reverse=True)
        print(f"\n>>> 점수 최고점 {top_n}개 분석\n")
        for r in rows_sorted[:top_n]:
            analyze_row(r)


if __name__ == '__main__':
    main()
