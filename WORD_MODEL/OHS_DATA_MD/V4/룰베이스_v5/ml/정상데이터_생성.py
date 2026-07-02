#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정상데이터_생성 — 원본 raw 에서 '작업일정(문제시간)' 을 빼고 정상 raw 추출
====================================================================
TSPulse R1 = '정상만' 학습.  그래서:
   원본 61개 raw (M16A_HUBROOM_PR_YYYYMMDD.CSV, 4/1~5/31)
     ─ 작업일정.csv 의 문제시간(H/T STOP·가벽철거·Maxcapa·Error·정체대응)을 빼고
     → 남은 '정상 raw' 만 추출 → 이것이 학습 데이터.

★ 원본 형식 그대로 유지: 265컬럼, 파일명 그대로. 문제구간 '행' 만 제거.
★ 표준 라이브러리만 사용 → 회사 PC 어디서든.
★ 작업일정은 외부 파일(ml/작업일정.csv)에서 읽음 → 편집·추가 자유.

입력:
    --raw       원본 raw 폴더 (M16A_HUBROOM_PR_*.CSV 61개) 또는 단일 파일
    --schedule  작업일정.csv (기본: 이 스크립트 옆 작업일정.csv)
    --buffer    작업 구간 전후 여유(분) 기본 15 (작업 여진 제거)
    --point     완료 '-'(미상) 작업의 기본 지속(분) 기본 30
    --episode   (옵션) 메신저 episode.csv — 정체 구간도 추가로 빼려면
    --guard     정체 episode 전후 여유(분) 기본 60
    --out       정상 raw 출력 폴더 (기본 ./raw_정상)

실행:
    python 정상데이터_생성.py --raw ./raw --out ./raw_정상
    → ./raw_정상/M16A_HUBROOM_PR_YYYYMMDD.CSV (정상 행만) 61개 + _제거로그

출력:
    raw_정상/<원본파일명>.CSV  — 문제시간 제거된 정상 raw (일별)
    raw_정상/_제거구간.csv     — 어떤 작업/정체 구간을 뺐는지 목록
    raw_정상/_요약.csv         — 일자별 총분/제거/정상 통계
    콘솔 리포트
"""
import argparse
import csv
import glob
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

YEAR = 2026
TIME_RE = re.compile(r'(\d{1,2}):(\d{2})')


# ============================================================
# 1. 작업일정.csv 로드 → 제외 구간 [(start, end, 내용, 비고)]
# ============================================================
def load_schedule(path, point_min, buffer_min):
    if not os.path.exists(path):
        raise SystemExit(f"⚠️ 작업일정 파일 없음: {path}\n   (ml/작업일정.csv 확인)")
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rows = list(csv.DictReader(open(path, encoding=enc)))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"⚠️ 작업일정 읽기 실패: {path}")
    ivs = []
    for r in rows:
        mmdd = (r.get('날짜') or '').strip()
        s_raw = (r.get('시작') or '').strip()
        e_raw = (r.get('완료') or '').strip()
        content = (r.get('작업내용') or '').strip()
        note = (r.get('비고') or '').strip()
        try:
            mm, dd = mmdd.split('/')
            base = datetime(YEAR, int(mm), int(dd))
        except (ValueError, AttributeError):
            continue
        sm = TIME_RE.search(s_raw)
        if not sm:
            continue
        start = base.replace(hour=int(sm.group(1)), minute=int(sm.group(2)))
        em = TIME_RE.search(e_raw)
        if em:
            end = base.replace(hour=int(em.group(1)), minute=int(em.group(2)))
            if '익일' in e_raw or end < start:       # 자정 넘김
                end += timedelta(days=1)
        else:                                         # 완료 '-' 미상
            end = start + timedelta(minutes=point_min)
        ivs.append((start - timedelta(minutes=buffer_min),
                    end + timedelta(minutes=buffer_min), content, note))
    ivs.sort()
    return ivs


def load_episode_jams(fp, guard):
    JAM = {'정체/병목', '리프터', 'CNV', 'MLUD', '브릿지'}
    out = []
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            rows = list(csv.DictReader(open(fp, encoding=enc)))
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"⚠️ episode 읽기 실패: {fp}"); return out
    for r in rows:
        if (r.get('is_orphan') or '').strip().upper() == 'Y':
            continue
        if (r.get('fault_type') or '').strip() not in JAM:
            continue
        try:
            t0 = datetime.strptime((r.get('start_time') or '').strip()[:16], '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        out.append((t0 - timedelta(minutes=guard), t0 + timedelta(minutes=guard),
                    f"정체:{r.get('fault_type','')}", ''))
    return out


# ============================================================
# 2. raw 파일별로 정상 행만 추출
# ============================================================
def excluded_reason(t, ivs):
    for s, e, c, n in ivs:
        if s <= t <= e:
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--raw', required=True)
    ap.add_argument('--schedule', default=os.path.join(here, '작업일정.csv'))
    ap.add_argument('--buffer', type=int, default=15)
    ap.add_argument('--point', type=int, default=30)
    ap.add_argument('--episode', default=None)
    ap.add_argument('--guard', type=int, default=60)
    ap.add_argument('--out', default='./raw_정상')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    print("=" * 64)
    print("정상 raw 추출 — 원본 raw − 작업일정(문제시간) = 정상만")
    print("=" * 64)

    ivs = load_schedule(a.schedule, a.point, a.buffer)
    print(f"[작업일정] {a.schedule} → {len(ivs)}건 (버퍼 ±{a.buffer}분)")
    if a.episode:
        j = load_episode_jams(a.episode, a.guard)
        ivs += j
        print(f"[정체] episode {len(j)}건 추가 (±{a.guard}분)")

    files = []
    if os.path.isdir(a.raw):
        for ext in ('*.csv', '*.CSV'):
            files += glob.glob(os.path.join(a.raw, ext))
    else:
        files = [a.raw]
    files = sorted(files)
    if not files:
        raise SystemExit(f"⚠️ raw 파일 없음: {a.raw}")
    print(f"[raw] {len(files)}개 파일 처리\n")

    tot_min = tot_keep = tot_rm = 0
    per_day = {}                       # date → (total, keep)
    removed_windows = set()            # (start,end,content) 실제 적중한 구간
    for fp in files:
        base = os.path.basename(fp)
        for enc in ('utf-8-sig', 'utf-8', 'cp949'):
            try:
                f = open(fp, encoding=enc)
                rd = csv.reader(f)
                header = next(rd)
                break
            except (UnicodeDecodeError, StopIteration):
                continue
        else:
            print(f"  ⚠️ 읽기 실패: {base}"); continue
        tcol = 0
        for i, c in enumerate(header):
            if c.strip().upper() in ('CRT_TM', 'DATETIME'):
                tcol = i; break
        keep_rows = []
        n_tot = n_keep = 0
        day = None
        for rec in rd:
            if not rec or len(rec) <= tcol:
                continue
            try:
                t = datetime.strptime(rec[tcol].strip()[:16], '%Y-%m-%d %H:%M')
            except ValueError:
                continue
            n_tot += 1
            day = t.date()
            reason = excluded_reason(t, ivs)
            if reason is None:
                keep_rows.append(rec)
                n_keep += 1
            else:
                for s, e, c, nnn in ivs:
                    if s <= t <= e:
                        removed_windows.add((s, e, c))
                        break
        f.close()
        # 정상 raw 파일 저장 (원본 형식)
        with open(os.path.join(a.out, base), 'w', newline='', encoding='utf-8-sig') as g:
            w = csv.writer(g); w.writerow(header); w.writerows(keep_rows)
        tot_min += n_tot; tot_keep += n_keep; tot_rm += (n_tot - n_keep)
        if day:
            per_day[day] = (n_tot, n_keep)
        pct = n_keep / n_tot * 100 if n_tot else 0
        print(f"  {base}  총 {n_tot:4d}분 → 정상 {n_keep:4d}분 ({pct:3.0f}%)  제거 {n_tot-n_keep}분")

    # ── 제거구간 목록 ──
    with open(os.path.join(a.out, '_제거구간.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['시작', '종료', '내용'])
        for s, e, c in sorted(removed_windows):
            w.writerow([s.strftime('%Y-%m-%d %H:%M'), e.strftime('%Y-%m-%d %H:%M'), c])
    # ── 일자별 요약 ──
    with open(os.path.join(a.out, '_요약.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['날짜', '총분', '정상분', '제거분', '정상%'])
        for d in sorted(per_day):
            tt, kk = per_day[d]
            w.writerow([d, tt, kk, tt - kk, f'{kk/tt*100:.0f}' if tt else '0'])

    print("\n" + "-" * 64)
    kp = tot_keep / tot_min * 100 if tot_min else 0
    print(f"총 {tot_min}분 → ★정상 {tot_keep}분 ({kp:.1f}%) / 제거 {tot_rm}분")
    print(f"적중한 작업/정체 구간 {len(removed_windows)}개")
    print(f"\n🎉 정상 raw → {a.out}/  (일별 {len(files)}개 + _제거구간·_요약)")
    print(f"다음: python features_31.py --raw {a.out} --out ./out_ml  → tspulse_train.py")


if __name__ == '__main__':
    main()
