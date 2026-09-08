#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 성능평가 — 발동이벤트로 Precision / Recall / F1 를 낸다
# ====================================================================
# 왜 필요한가
#   고객 보고에 "룰 개정 이력 / 제작 데이터 기간 / 평가 데이터 기간 / 성능" 이 필요하다.
#   그중 성능(P/R/F1)은 "실제로 정체가 났는가" 라는 정답이 있어야 계산된다.
#   발동이벤트에는 룰이 판정한 것만 있고 실제 결과가 없다.
#   그래서 여기서는 **대리 정답**을 쓴다 — 반드시 보고서에 기준을 같이 적을 것.
#
#     정답(실제 정체) : 어느 영역이든 반송시간(R-A)이 임계 이상인 상태가
#                       SUSTAIN 분 이상 연속되면 그 구간을 실제 정체로 본다
#     경보            : unified_risk_score >= CUT (기본 48 = 운영 ALL 경계)
#     적중            : 사건 시작 LEAD 분 전 ~ 사건 종료 사이에 경보가 있었으면 잡은 것
#
#   ※ 반송시간은 룰의 입력이기도 하다. 완전히 독립된 정답이 아니므로
#     "대리 정답 기준"임을 반드시 명시할 것. 진짜 성능을 내려면
#     운영자 인지 시각·MCS 알람 이력 같은 실제 장애 기록이 필요하다.
#
# 사용법
#   python 성능평가.py --event .\predict_tobe
#   python 성능평가.py --event .\predict_tobe --out 성능평가_결과.txt
#   python 성능평가.py --event .\predict_tobe --days 30
#   python 성능평가.py --event .\predict_tobe\20260826_발동이벤트.csv
#
# 운영 등급 컷 (2026-09 확인)
#   ALL 48/60/80 · M16HUB 40/55/75 · M14·M14B·M16A·M16B 36/52/72
#
# 옵션
#   --event     발동이벤트 CSV 또는 폴더 (필수)
#   --out       결과를 파일로도 저장 (작아서 그대로 전달 가능)
#   --days      최근 N일만
#   --since     YYYYMMDD 이후만
#   --cut       ALL 경보 기준 점수 (기본 48 = 운영 경계)
#   --sustain   실제 정체로 인정할 연속 분 (기본 5)
#   --lead      선행 인정 구간, 분 (기본 30)
#   --gap       이 분 이내로 끊긴 경보는 하나로 합침 (기본 10)
#   --mindur    이 분 미만 경보는 무시 (기본 5)
#   --fab-cut   FAB 경계를 한 값으로 통일 (기본: 운영값 M16HUB 40 · 그 외 36)
#   --denom     FAB 점수 분모 (기본 70)
import argparse
import csv
import glob
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta

csv.field_size_limit(10 ** 7)

EVENT_KEY = '발동이벤트'
AREAS = ['M16HUB', 'M14', 'M14B', 'M16A', 'M16B']
# R-A 임계 (반송시간, 분) — thresholds.json / 예측기가 있으면 그쪽 값으로 덮어쓴다
TH_RA_DEFAULT = {'M16HUB': 9.0, 'M14': 3.3, 'M14B': 5.0, 'M16A': 3.2, 'M16B': 3.5}

# ★ 운영 시스템에 실제로 설정된 등급 컷 (2026-09 확인)
#     ALL     48 / 60 / 80
#     M16HUB  40 / 55 / 75
#     그 외    36 / 52 / 72
#   FAB 마다 점수 분포가 달라 컷도 다르다. 경계 미만은 정상(무알람).
ALL_CUT_DEFAULT = 48
FAB_CUT_DEFAULT = {'M16HUB': 40, 'M14': 36, 'M14B': 36, 'M16A': 36, 'M16B': 36}
FAB_BANDS = {'M16HUB': (40, 55, 75), 'M14': (36, 52, 72), 'M14B': (36, 52, 72),
             'M16A': (36, 52, 72), 'M16B': (36, 52, 72)}
ALL_BANDS = (48, 60, 80)


# ────────────────────────────────────────────────── 입력
def load_thresholds():
    """thresholds.json 이 옆에 있으면 그 값을 쓴다 (운영과 어긋나지 않게)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.getcwd(), here, os.path.dirname(here)):
        fp = os.path.join(d, 'thresholds.json')
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            continue
        ra = cfg.get('TH_RA') or {}
        th = dict(TH_RA_DEFAULT)
        for a in AREAS:
            if a in ra:
                try:
                    th[a] = float(ra[a])
                except (TypeError, ValueError):
                    pass
        return th, fp
    return dict(TH_RA_DEFAULT), None


def is_event_csv(name):
    if not name.lower().endswith('.csv'):
        return False
    n = unicodedata.normalize('NFC', name)
    return EVENT_KEY in n and '_M1' not in n      # FAB 분리 파일은 제외


def pick_files(event, days=None, since=None):
    ev = (event or '').strip().strip('"').strip("'")
    hits = []
    if any(c in ev for c in '*?'):
        hits = [p for p in glob.glob(ev) if is_event_csv(os.path.basename(p))]
    elif os.path.isdir(ev):
        hits = [os.path.join(ev, f) for f in os.listdir(ev) if is_event_csv(f)]
    elif os.path.exists(ev):
        hits = [ev]
    else:
        print(f'  ❌ 없음: {os.path.abspath(ev)}')
        return []
    if days:
        since = max(since or '', (datetime.now() - timedelta(days=days - 1)).strftime('%Y%m%d'))
    out = []
    for p in sorted(hits):
        m = re.search(r'(\d{8})', os.path.basename(p))
        if since and m and m.group(1) < since:
            continue
        out.append(p)
    if not out:
        print(f'  ❌ 대상 없음: {os.path.abspath(ev)}')
    return out


def fl(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def read_event(fp):
    """(시각, 행) 목록. 같은 시각 중복은 첫 행만 남긴다."""
    rows = []
    with open(fp, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            d = (r.get('datetime') or '').strip()
            t = None
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    t = datetime.strptime(d, fmt)
                    break
                except ValueError:
                    pass
            if t:
                rows.append((t, r))
    rows.sort(key=lambda x: x[0])
    seen, out = set(), []
    for t, r in rows:
        if t not in seen:
            seen.add(t)
            out.append((t, r))
    return out, len(rows) - len(out)


# ────────────────────────────────────────────────── 구간 계산
def episodes(flags):
    """연속 True 구간 → [(시작, 끝)] (끝 포함)"""
    ep, s = [], None
    for i, f in enumerate(flags):
        if f and s is None:
            s = i
        elif not f and s is not None:
            ep.append((s, i - 1))
            s = None
    if s is not None:
        ep.append((s, len(flags) - 1))
    return ep


def merge(ep, gap):
    """gap 분 이내로 끊긴 구간은 하나로 합친다."""
    if not ep:
        return ep
    out = [list(ep[0])]
    for s, e in ep[1:]:
        if s - out[-1][1] - 1 <= gap:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def prf(real, alarm, gap, mindur, lead):
    """정답 구간 / 경보 구간 → Precision, Recall, F1"""
    n = len(real)
    R = merge(episodes(real), gap)
    A = merge(episodes(alarm), gap)
    A = [(s, e) for s, e in A if e - s + 1 >= mindur]
    # Recall 도 '정리된 경보' 기준으로 본다 — Precision 과 같은 잣대를 써야 값이 어긋나지 않는다
    kept = [False] * n
    for s, e in A:
        for i in range(s, e + 1):
            kept[i] = True
    tp_r = sum(1 for s, e in R if any(kept[max(0, s - lead):e + 1]))
    tp_a = sum(1 for s, e in A if any(real[s:min(n, e + 1 + lead)]))
    p = tp_a / len(A) if A else 0.0
    r = tp_r / len(R) if R else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return dict(nR=len(R), nA=len(A), tpR=tp_r, tpA=tp_a, p=p, r=r, f1=f1,
                minR=sum(real), minA=sum(kept))


def build(rows, th_ra, sustain):
    """→ (분 인덱스 길이, 정답 flags, 원본 dict, 시작시각)"""
    base = rows[0][0]
    idx = {int((t - base).total_seconds() // 60): r for t, r in rows}
    n = max(idx) + 1
    over = []
    for m in range(n):
        r = idx.get(m)
        hit = False
        if r is not None:
            for a, th in th_ra.items():
                v = fl(r.get(a + '_ra'))
                if v is not None and v >= th:
                    hit = True
                    break
        over.append(hit)
    real = [False] * n
    for s, e in episodes(over):
        if e - s + 1 >= sustain:
            for i in range(s, e + 1):
                real[i] = True
    return n, real, idx, base


# ────────────────────────────────────────────────── 출력
class Tee:
    def __init__(self, path=None):
        self.f = open(path, 'w', encoding='utf-8') if path else None
        self.lines = []

    def __call__(self, s=''):
        print(s)
        self.lines.append(s)
        if self.f:
            self.f.write(s + '\n')

    def close(self):
        if self.f:
            self.f.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', required=True, help='발동이벤트 CSV 또는 폴더')
    ap.add_argument('--out', default=None, help='결과를 파일로도 저장')
    ap.add_argument('--days', type=int, default=None)
    ap.add_argument('--since', default=None, metavar='YYYYMMDD')
    ap.add_argument('--cut', type=float, default=ALL_CUT_DEFAULT,
                    help=f'ALL 경보 기준 점수 (기본 {ALL_CUT_DEFAULT} = 운영 경계)')
    ap.add_argument('--sustain', type=int, default=5, help='실제 정체 연속 분 (기본 5)')
    ap.add_argument('--lead', type=int, default=30, help='선행 인정 분 (기본 30)')
    ap.add_argument('--gap', type=int, default=10, help='경보 병합 간격 분 (기본 10)')
    ap.add_argument('--mindur', type=int, default=5, help='최소 경보 지속 분 (기본 5)')
    ap.add_argument('--fab-cut', type=float, default=None, dest='fabcut',
                    help='FAB 경계를 한 값으로 통일 (기본: 영역별 운영값 40/36)')
    ap.add_argument('--denom', type=float, default=70)
    a = ap.parse_args()

    th_ra, th_path = load_thresholds()
    fabcut = dict(FAB_CUT_DEFAULT)
    if a.fabcut is not None:
        fabcut = {x: a.fabcut for x in AREAS}
    files = pick_files(a.event, a.days, a.since)
    if not files:
        sys.exit(2)

    o = Tee(a.out)
    o('=' * 72)
    o('룰베이스 성능평가 — Precision / Recall / F1')
    o('=' * 72)
    o(f'  대상 파일 {len(files)}개')
    o(f'  R-A 임계  ' + ' · '.join(f'{k} {v:g}' for k, v in th_ra.items())
      + (f'   (출처 {os.path.basename(th_path)})' if th_path else '   (코드 기본값)'))
    o(f'  경보 기준 unified >= {a.cut:g}   ·   정답 = 반송시간 임계초과 {a.sustain}분 지속')
    o(f'  적중 판정 사건 시작 {a.lead}분 전까지의 경보 인정')
    o(f'  경보 정리 {a.gap}분 이내 병합 · {a.mindur}분 미만 무시')

    # ── 파일별
    o('')
    o('─' * 72)
    o('[1] 일자별 성능')
    o('─' * 72)
    o(f"{'파일':<26}{'분':>6}{'사건':>5}{'경보':>5}{'Prec':>7}{'Recall':>8}{'F1':>7}")
    allreal, allalarm = [], []
    per_area_raw = {x: [] for x in AREAS}
    per_area_real = {x: [] for x in AREAS}
    per_area_alarm = {x: [] for x in AREAS}
    dup_total = 0
    for fp in files:
        rows, dup = read_event(fp)
        dup_total += dup
        if len(rows) < 30:
            o(f'{os.path.basename(fp)[:25]:<26}{len(rows):>6}   (행 부족 — 건너뜀)')
            continue
        n, real, idx, base = build(rows, th_ra, a.sustain)
        alarm = []
        for m in range(n):
            r = idx.get(m)
            v = fl(r.get('unified_risk_score')) if r else None
            alarm.append(v is not None and v >= a.cut)
        d = prf(real, alarm, a.gap, a.mindur, a.lead)
        o(f"{os.path.basename(fp)[:25]:<26}{len(rows):>6}{d['nR']:>5}{d['nA']:>5}"
          f"{d['p']:>7.2f}{d['r']:>8.2f}{d['f1']:>7.2f}")
        allreal.append(real)
        allalarm.append(alarm)
        # 영역별 자료 모으기
        for x in AREAS:
            ov = []
            for m in range(n):
                r = idx.get(m)
                v = fl(r.get(x + '_ra')) if r else None
                ov.append(v is not None and v >= th_ra[x])
            rr = [False] * n
            for s, e in episodes(ov):
                if e - s + 1 >= a.sustain:
                    for i in range(s, e + 1):
                        rr[i] = True
            aa = []
            for m in range(n):
                r = idx.get(m)
                sr = fl(r.get(x + '_score_raw')) if r else None
                sc = min(100, round(sr * 100 / a.denom)) if sr is not None else 0
                aa.append(sc >= fabcut[x])
                if sr is not None:
                    per_area_raw[x].append(sr)
            per_area_real[x].append(rr)
            per_area_alarm[x].append(aa)

    if not allreal:
        o('\n❌ 평가할 데이터가 없습니다.')
        o.close()
        sys.exit(2)

    # ── 전체 합산 (파일을 이어 붙이지 않고 각각 계산 후 합산 — 날짜 경계 오염 방지)
    def total(reals, alarms, cut_alarm=None):
        nR = nA = tpR = tpA = 0
        for i, real in enumerate(reals):
            al = alarms[i] if cut_alarm is None else cut_alarm[i]
            d = prf(real, al, a.gap, a.mindur, a.lead)
            nR += d['nR']; nA += d['nA']; tpR += d['tpR']; tpA += d['tpA']
        p = tpA / nA if nA else 0.0
        r = tpR / nR if nR else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        return nR, nA, p, r, f1

    nR, nA, P, R, F = total(allreal, allalarm)
    o('─' * 72)
    o(f"{'전체 합산':<26}{'':>6}{nR:>5}{nA:>5}{P:>7.2f}{R:>8.2f}{F:>7.2f}")
    o('')
    o(f'  ★ 보고용 :  Precision {P:.2f}  /  Recall {R:.2f}  /  F1 {F:.2f}')
    o(f'     실제 사건 {nR}건 · 유효 경보 {nA}건')
    if dup_total:
        o(f'  ※ 시각 중복 {dup_total}행은 제거하고 계산했습니다.')

    # ── 임계 트레이드오프
    o('')
    o('─' * 72)
    o('[2] 경보 기준을 바꾸면 — 트레이드오프')
    o('─' * 72)
    o(f"{'경보기준':<10}{'경보수':>7}{'Precision':>11}{'Recall':>9}{'F1':>7}")
    for cut in (36, 40, 44, 48, 52, 56, 60):
        alarms = []
        for i, fp in enumerate(files):
            rows, _ = read_event(fp)
            if len(rows) < 30:
                continue
            n, _, idx, _ = build(rows, th_ra, a.sustain)
            al = []
            for m in range(n):
                r = idx.get(m)
                v = fl(r.get('unified_risk_score')) if r else None
                al.append(v is not None and v >= cut)
            alarms.append(al)
        n2, a2, p2, r2, f2 = total(allreal, alarms)
        mark = '  ← 현재' if abs(cut - a.cut) < 0.5 else ''
        o(f'{cut:<10.0f}{a2:>7}{p2:>11.2f}{r2:>9.2f}{f2:>7.2f}{mark}')

    # ── FAB 별
    o('')
    o('─' * 72)
    o(f'[3] FAB별 성능 (분모 {a.denom:g} · 경계 '
      + ' · '.join(f'{k} {v:g}' for k, v in fabcut.items()) + ')')
    o('─' * 72)
    o(f"{'영역':<9}{'컷':>4}{'사건':>5}{'경보':>5}{'Precision':>11}{'Recall':>9}{'F1':>7}")
    dead = []
    for x in AREAS:
        n3, a3, p3, r3, f3 = total(per_area_real[x], per_area_alarm[x])
        o(f'{x:<9}{fabcut[x]:>4}{n3:>5}{a3:>5}{p3:>11.2f}{r3:>9.2f}{f3:>7.2f}')
        if a3 == 0:
            dead.append(x)
    if dead:
        o('')
        o(f'  ⚠️ 경보가 한 건도 안 뜬 영역: {", ".join(dead)}')
        o('     → 그 영역 경계가 너무 높거나, 그 기간에 정말 조용했던 것입니다. [4] 참고.')

    # ── FAB 경계 재산정
    o('')
    o('─' * 72)
    o('[4] FAB 경계 재산정 — score_raw 실제 분포')
    o('─' * 72)
    o(f"{'영역':<9}{'raw최대':>8}{'raw p99':>9}{'점수최대':>9}"
      + ''.join(f'{c}점↑'.rjust(8) for c in (40, 45, 50, 55, 60)))
    for x in AREAS:
        v = sorted(per_area_raw[x])
        if not v:
            o(f'{x:<9} (컬럼 없음)')
            continue
        p99 = v[min(len(v) - 1, int(len(v) * 0.99))]
        sc = [min(100, round(z * 100 / a.denom)) for z in v]
        cnt = ''.join(str(sum(1 for s in sc if s >= c)).rjust(8) for c in (40, 45, 50, 55, 60))
        o(f'{x:<9}{v[-1]:>8.0f}{p99:>9.0f}{max(sc):>9}{cnt}')
    o('')
    o('  · 각 열은 그 점수 이상으로 올라간 "분" 수입니다.')
    o('  · 전 영역이 고르게 발동하는 값을 경계로 잡으십시오.')
    o('  · 0 뿐인 열은 그 경계로는 절대 안 뜬다는 뜻입니다.')

    # ── 보고서용 각주
    o('')
    o('=' * 72)
    o('[보고서에 반드시 같이 적을 것 — 성능 산출 기준]')
    o('=' * 72)
    o(f'  · 정답(실제 정체) : 반송시간(R-A)이 영역 임계 이상인 상태가 {a.sustain}분 이상 지속')
    o(f'  · 경보           : unified_risk_score >= {a.cut:g}  (운영 ALL 경계)')
    o('  · FAB 경계       : ' + ' · '.join(f'{k} {v:g}' for k, v in fabcut.items()))
    o(f'  · 적중 판정       : 사건 시작 {a.lead}분 전 ~ 종료 사이에 경보 존재')
    o(f'  · 경보 정리       : {a.gap}분 이내 병합, {a.mindur}분 미만 제외')
    o('  · 한계           : 반송시간은 룰의 입력이기도 하므로 완전히 독립된 정답이 아님.')
    o('                     진짜 성능은 운영자 인지 시각·MCS 알람 이력 확보 후 재측정 필요.')
    if a.out:
        o('')
        o(f'  → 저장 완료: {os.path.abspath(a.out)}')
    o.close()


if __name__ == '__main__':
    main()
