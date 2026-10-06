#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 점수0_진단 — 영역 점수가 0 으로 나올 때 원인을 가려낸다
# ====================================================================
#   ① 수집 CSV 에 그 영역의 컬럼이 있는가        없으면 → 수집기 문제
#   ② 값이 들어오는가 (전부 빈칸/NULL 아닌가)     비면 → 수집 쿼리·권한 문제
#   ③ 값이 임계를 안 넘는가                      그러면 → 0 이 정상 (정체가 없는 것)
#
# 사용법
#   python 점수0_진단.py                          (기본 ../predict/M16A_HUBROOM_PR.csv)
#   python 점수0_진단.py --input ./predict/M16A_HUBROOM_PR.csv
#   python 점수0_진단.py --event ./predict_tobe   (발동이벤트 최근 행도 같이 확인)
import argparse, csv, os, sys


def load_predictor():
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.getcwd(), here, os.path.dirname(here)):
        fp = os.path.join(d, 'hubroom_predictor.py')
        if os.path.exists(fp):
            import importlib.util
            spec = importlib.util.spec_from_file_location('hp', fp)
            m = importlib.util.module_from_spec(spec)
            sys.modules['hp'] = m
            spec.loader.exec_module(m)
            return m, fp
    raise SystemExit('❌ hubroom_predictor.py 를 찾을 수 없습니다')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=None, help='수집 CSV (기본: ../predict/M16A_HUBROOM_PR.csv)')
    ap.add_argument('--event', default=None, help='발동이벤트 폴더/파일 (선택)')
    a = ap.parse_args()

    H, hp_path = load_predictor()
    here = os.path.dirname(os.path.abspath(__file__))
    inp = a.input or os.path.join(os.path.dirname(here), 'predict', 'M16A_HUBROOM_PR.csv')
    print('=' * 66)
    print('영역 점수 0 진단')
    print('=' * 66)
    print(f'  예측기 : {hp_path}  (EVENT_FIELDS {len(H.EVENT_FIELDS)}컬럼)')
    print(f'  수집CSV: {os.path.abspath(inp)}')
    if not os.path.exists(inp):
        print('\n❌ 수집 CSV 가 없습니다 — 수집기가 안 돌고 있습니다.')
        print('   수집기(aws_idc_realtime_collector)를 먼저 살리세요.')
        sys.exit(2)

    with open(inp, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f)
        header = next(rd, [])
        rows = list(rd)
    print(f'  컬럼 {len(header)}개 · {len(rows)}행'
          + (f' · 마지막 {rows[-1][0] if rows else "-"}' if rows else ''))
    if len(header) < 100:
        print(f'\n  ⚠️ 컬럼이 {len(header)}개뿐입니다. 운영 수집기는 260개 이상이어야 합니다.')
        print('     → 잘못된(구버전) 수집기가 돌고 있을 가능성이 큽니다.')
    if not rows:
        print('\n❌ 데이터 행이 없습니다 — 수집기가 조회를 못 하고 있습니다.')
        sys.exit(2)

    last = dict(zip(header, rows[-1]))

    def val(col):
        v = (last.get(col) or '').strip()
        return v

    # 영역별 핵심 컬럼 = 그 영역 점수를 만드는 룰의 입력
    checks = []
    for area, col in H.RA_COL.items():
        checks.append((area, 'R-A 반송/적재시간', col, H.TH_RA.get(area), '>='))
    for area, col in H.RB_COL.items():
        checks.append((area, 'R-B 대기물량(30분증가)', col, H.TH_RB_30.get(area), '증가'))
    for area, col in H.RD_OHT_COL.items():
        if area != 'M16HUB':
            checks.append((area, 'R-D OHT가동률', col, H.TH_RD_OHT_UTIL, '>='))
    checks.append(('M16HUB', 'R-D FAB저장율', 'M16HUB.STRATE.ALL.FABSTORAGERATIO', H.TH_RD_FABSTORAGE, '>='))
    for area, col in H.SLA_COL.items():
        checks.append((area, 'SLA 4분초과율', col, H.TH_SLA_RATIO.get(area), '>='))

    print('\n' + '-' * 66)
    print(f"{'영역':<8}{'룰':<22}{'컬럼 있음':>9}{'현재값':>10}{'임계':>9}  판정")
    print('-' * 66)
    miss = empty = 0
    by_area = {}
    for area, rule, col, th, how in checks:
        has = col in header
        v = val(col) if has else ''
        if not has:
            verdict = '❌ 컬럼 없음'; miss += 1
        elif v == '':
            verdict = '⚠️ 값 없음(NULL)'; empty += 1
        else:
            try:
                fv = float(v)
                if how == '>=' and th is not None:
                    verdict = '🔥 임계 초과' if fv >= th else '정상(임계 미만)'
                else:
                    verdict = '값 있음'
            except ValueError:
                verdict = f'값 이상: {v[:12]}'
        by_area.setdefault(area, []).append(verdict)
        print(f"{area:<8}{rule:<22}{'O' if has else 'X':>9}{(v or '-'):>10}"
              f"{(str(th) if th is not None else '-'):>9}  {verdict}")

    print('-' * 66)
    print('\n[해석]')
    if miss:
        print(f'  ❌ 컬럼 없음 {miss}개 → 수집 CSV 에 그 지표가 아예 없습니다.')
        print('     수집기 버전이 다르거나 조회 컬럼이 빠졌습니다. 수집기를 원래 것으로 되돌리세요.')
    if empty:
        print(f'  ⚠️ 값 없음 {empty}개 → 컬럼은 있는데 NULL 입니다. 조회 권한/구간을 확인하세요.')
    if not miss and not empty:
        hot = [a for a, vs in by_area.items() if any('임계 초과' in x for x in vs)]
        if hot:
            print(f'  🔥 임계를 넘긴 영역이 있습니다: {", ".join(hot)} → 점수가 나와야 정상입니다.')
            print('     그런데도 0 이면 예측기 쪽 문제이니 이 출력을 그대로 알려 주세요.')
        else:
            print('  ✅ 모든 지표가 임계 아래입니다 — 지금은 정체가 없어서 점수 0 이 정상입니다.')
            print('     (룰베이스는 임계를 넘어야 점수를 줍니다. 평상시 0 은 이상이 아닙니다)')

    if a.event:
        ev = a.event
        if os.path.isdir(ev):
            import glob, re
            c = [f for f in glob.glob(os.path.join(ev, '*발동이벤트*.csv')) if '_M1' not in os.path.basename(f)]
            ev = max(c) if c else None
        if ev and os.path.exists(ev):
            with open(ev, encoding='utf-8-sig') as f:
                er = list(csv.DictReader(f))
            if er:
                x = er[-1]
                print(f'\n[발동이벤트 최근 행] {os.path.basename(ev)} · {len(x)}컬럼 · {len(er)}행')
                print(f"  {x.get('datetime')} · score={x.get('unified_risk_score')} "
                      f"level={x.get('unified_risk_level') or '-'} hot={x.get('hot_area')} "
                      f"stage={x.get('stage')}")
                print(f"  영역: " + ' · '.join(f"{k}={x.get(k+'_score')}"
                                              for k in ('M16HUB', 'M14', 'M14B', 'M16A', 'M16B')))
                print(f"  PIO: cnt={x.get('pio_10min_cnt', '(컬럼없음)')} score={x.get('pio_score', '(컬럼없음)')}")


if __name__ == '__main__':
    main()
