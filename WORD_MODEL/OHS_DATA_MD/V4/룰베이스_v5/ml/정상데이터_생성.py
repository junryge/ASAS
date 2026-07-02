#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정상데이터_생성 — TSPulse R1 학습용 '정상 데이터' 만들기 (Phase 1의 핵심)
====================================================================
TSPulse R1 = '정상만' 학습하는 이상탐지.
→ raw 에서 사람이 개입한 '작업일정 구간' 을 데이터 제거(remove) → 남는 것 = 정상.

★ 이 스크립트 = TSPulse R1 데이터 준비 전용. (TabPFN/분류 아님)
★ 표준 라이브러리만 사용 → 회사 PC 어디서든 실행.

제거 대상:
  (1) 작업일정 구간  — H/T STOP·가벽철거·Maxcapa변경·Error대응·정체대응 등 (아래 SCHEDULE)
                       사람 개입으로 지표가 인위적 = 정상 아님 → 제거
  (2) (옵션) 메신저 정체 episode — 실제 정체 구간도 정상 아님 → 제거

입력:
    --raw     raw CSV (265컬럼) 또는 features.csv. CRT_TM/datetime 자동 인식. 폴더도 가능
    --episode (옵션) 메신저 episode.csv — 정체 구간도 제거하려면
    --buffer  작업 구간 전후 여유(분) 기본 15 (작업 여진 제거)
    --point   종료시각 '-'(미상) 작업의 기본 지속(분) 기본 30
    --guard   정체 episode 전후 여유(분) 기본 60
    --out     출력 폴더 기본 ./out_ml

실행:
    python 정상데이터_생성.py --raw ./raw --episode ..._episode.csv --out ./out_ml
    (시연) python 정상데이터_생성.py --raw 5_25.CSV

출력:
    정상데이터.csv   — 정상 분만 남긴 raw (원본 컬럼 그대로) → TSPulse 학습 입력
    제거구간.csv     — 제거된 작업/정체 구간 목록 (사유·원문)
    정상마스크.csv   — datetime, is_normal(1/0), 제외사유
    콘솔 리포트      — 총분 / 작업제거 / 정체제거 / 정상 kept (일자별)
"""
import argparse
import csv
import glob
import os
import re
from datetime import datetime, timedelta

YEAR = 2026

# ============================================================
# ★ 2026 4~5월 주요 작업 일정 (운영자 확인본. 시각 기재)
#   형식:  MM/DD,작업내용,시작,완료(-=미상/HH:MM(익일)),비고
#   ※ TSPulse 정상데이터엔 유형 무관 전부 '제거'. (유형 세분류는 TabPFN 때)
# ============================================================
SCHEDULE_TEXT = """
04/01,M16 ZT#6 호기 6F 가벽 철거 (오전 H/T STOP),09:50,11:03,작업 완료 보고
04/01,M16 ZT#6 호기 6F 가벽 철거 (오후 H/T STOP),13:30,14:56,Rail Cut → H/T STOP 변경
04/02,M16A ZT 4,5 호기 6F CONV Port 차단,08:45,-,작업 영향 확인용 차단
04/02,M16A ZT 6 호기 6F 가벽 철거 (오전),09:00,11:48,작업 완료 보고
04/02,M16A ZT 6 호기 6F 가벽 철거 (오후),13:30,-,오전 작업 연장 및 완료 (오후 작업 없음)
04/03,4ABLD122 호기 Error 대응 (AI Close/Open),11:30,12:14,11:30 Close 11:41 Open 11:42 재Close 12:14 Open
04/04,Bridge STB 공간부족 Maxcapa 50% 변경,01:08,01:46,M14A/B M16A 변경 및 원복 반복 (야간 작업)
04/05,Maxcapa 조정 (3→1→원복),04:03,07:09,M14A/B M16A 다수 변경 및 원복 (야간/새벽 작업)
04/06,M16A ZT#6 호기 3F CONV 안착 (오전),09:37,10:50,H/T 작업 완료
04/06,M16A ZT#6 호기 3F CONV 안착 (오후),14:14,16:10,H/T 작업 완료
04/07,M16A ZT#6 호기 3F CONV 설치 마무리 (오전),09:20,09:56,H/T 작업 완료
04/07,4ABLD111/112/121/122/131 호기 Error 대응,10:01,14:03,각 호기별 AI Close/Open 반복 조치
04/08,M16A ZT#6 호기 6F 작업 (오전),09:00,11:15,H/T-Stop 작업 완료
04/08,M16A ZT#6 호기 6F 작업 (오후),14:05,15:59,H/T-Stop 작업 완료
04/09,4AFC3201 ERROR 대응 (Port 차단/Open),01:02,01:21,M16→M14 A_IN 80~90 차단 후 복구
04/09,M16A ZT 4,5 호기 6F Conv Port Down,09:51,10:27,작업 완료 후 Open
04/09,4ABLD112 호기 Error 대응,09:26,11:10,AI Close/Open 반복
04/10,TCM813 통신 Cable 교체 작업,10:00,11:00,4AFC3201(남측) Zone81318
04/12,4ABLD132 호기 Error 대응,08:20,08:44,AI Close/Open
04/12,4ABLD111 호기 Error 대응 (야간),22:04,22:26,7F AI Close 4F Foup Manual 제거 (HT-Stop)
04/13,4ABLD122 호기 Error 대응 (새벽),01:12,01:45,Close 후 처리 완료 Open
04/13,M16A ZT 6 호기 3F 작업 (오전),09:11,11:25,Handy Stop 작업 완료
04/13,M16A ZT 6 호기 6F Rail Cut (오후),14:20,16:47,Conv 6 개 Down 작업 후 Open
04/16,Bridge OHT 몰림 Maxcapa 조정,10:48,11:19,M14A/B M16A Maxcapa 1 변경 및 원복
04/19,HUB 반송 지연 모니터링,09:04,09:43,M14 7 층/LFT 문제 확인 (작업 아님)
04/21,6FIOB101 장비 Teaching 작업,09:00,11:43,Manual Input port 사용 (Hand Stop)
04/21,PM 관련 MLUD 물량 감축 조정,14:10,14:52,M14A/B 수량 단계적 감축 (50→10)
04/22,Hub Room Conveyor Port 설치 작업,07:05,14:25,OHT HT Stop 중단/재개 및 Conveyor 작업
04/22,M16↔M14 Bridge OHT Open,14:34,-,작업 종료 후 정상화
04/22,PM 관련 물량 원복 조정,17:41,18:16,M14A/B 수량 단계적 원복 (10→50)
04/22,4ABLD131/6ABL6032 Error 대응,19:10,01:23(익일),AI Close/Open 및 야간 조치
04/23,6ABL6011 Error 대응,15:36,16:42,AI Close/Error Clear/Open 반복
04/24,4ABLD111 Error 대응 (새벽),03:27,03:40,AI Close/Open
04/24,6ABL6011 Error 대응 및 Maxcapa 조정,05:14,06:41,Error 조치 및 Maxcapa 1 변경/원복
04/25,M16 Bridge MLUD 출고 지연 대응,11:54,13:12,Queue 기준정보 수정 (50→10)
04/25,4ABLD112 호기 Error 대응 (야간),20:42,21:40,AI Close/Open
04/27,M14 A,B Maxcapa 조정 (새벽),05:22,06:27,1 로 변경 후 원복
04/27,4ABLD132 호기 반송 Delay/Error 대응,08:19,08:48,Manual/HT STOP 대응 및 Error 조치
04/27,M16A ZT#6 호기 3F CONV Sensor 조정,14:00,15:28,H/T STOP 작업 완료
04/30,4ABLD131 호기 Error 대응,09:26,09:49,AI Close/Open
05/06,4ABLD131 호기 Error 대응,09:26,09:49,AI Close/Open
05/06,4ABLD131 호기 Error 재발생 대응,11:49,12:05,AI Close/Open
05/07,4ABLD132 호기 AI75 임시 조치,07:31,07:36,Close 후 Open
05/07,Hubroom 정체로 4ABLD122 7F AI 조치,07:40,07:42,Close 후 Open
05/07,M16A ZT#6 호기 3F CONV Sensor 조정,09:20,10:26,H/T STOP 작업 완료
05/07,SFA 7F AI Full 호기 Close 대응,09:12,-,Port Close 조치
05/07,BRIDGE M16 ZT 3 호기 Down 대응,10:36,10:37,OHT 정체 발생 후 즉시 조치 완료
05/08,M14A/B M16A Maxcapa 1 변경,11:38,11:43,정체 해소를 위한 용량 제한
05/08,M16 HUB VHL 몰림 현상 대응,11:40,11:55,6ABL0121/0122 3F AI Port Open/Disable
05/08,M16A 6F MaxCapa 원복,11:55,-,Storage 증가에 따른 원복
05/08,M16 Bridge Hub OHT 정체 심화 대응,12:07,13:06,M16B→M16A Delay Foup Trans Count 상향 (11→25)
05/08,M16HUB Queue High Alarm 발생,13:06,17:20,Queue 1700~2000 개 초과 지속 (오후 내내 모니터링)
05/09,4AFC3201 Error 대응 (A_IN80~90 차단),17:39,17:48,조치 후 Open (86~90 먼저 80~85 뒤따름)
05/09,4AFC3201 Error 재발생 대응,17:59,18:14,재차단 후 Open
05/10,HUB Error 여부 확인 및 Maxcapa 조정,02:32,04:52,OHT Error 없음 확인 Maxcapa 50% 변경
05/10,M16A Maxcapa 원복 요청 및 조치,10:29,12:31,반송량 증가 우려로 지연 후 원복 완료
05/10,4AFC3301 Error 대응 (A_IN80~89 차단),22:34,22:38,차단 후 즉시 Open
05/11,M16A ZT Maxcapa 50% 변경,23:59,00:02(익일),야간 조치
05/11,Bridge OHT BV0165 호기 Err 처리,07:44,07:49,발생 및 처리 완료
05/11,4ABLD111 호기 Error 대응,10:03,10:27,AI Close/Open
05/11,4AFC3201 고소작업 Port 임시 차단,15:57,16:29,Zone70902 error 대응 Maxcapa 조정 (1→8 원복)
05/11,M16 Maxcapa 3 변경 및 원복,16:26,16:55,일시적 상향 후 원복
05/11,M14→M16 반송 정체 (6PDMP863) 대응,23:11,23:13,MCS Queue 확인 및 Car Status 모니터링
05/12,M16A ZT#6 호기 3F 소방 배관 설치,09:34,09:59,H/T STOP 작업 완료
05/12,4ABLD111 호기 Error 대응,10:41,11:01,AI Close/Open
05/12,M16A ZT#6 호기 3F Conv 확인 작업,14:30,15:11,H/T STOP 작업 (Conv Error 로 16:00 까지 연장)
05/13,M16 2F EUV VLF 점검 (1 호기),09:00,17:52,가이드롤러/스토퍼/베어링 교체 작업 완료
05/13,M16E LINE OHT 정체 대응,00:09,06:02,SFA Lifter 7F AI Port 전체 Close/Open 순차 조치
05/13,Bridge OHT Alarm Deadlock 처리,05:39,05:58,Delay 해소 및 Port Open
05/13,MLUD 정체로 인한 Capa 조정,07:07,07:28,6FIO103/105/107 Maxcapa 8→4 변경 후 원복
05/14,M16 2F EUV VLF 점검 (2,3 호기),09:07,15:21,2,3 호기 동시 Down 작업 완료
05/14,M14A/B Maxcapa 1 변경 및 원복,10:02,10:16,Hubroom 정체로 변경 즉시 원복
05/14,M16 Hubroom Rail Cut 대응,10:04,10:08,St.2298→2940 St.2375→2376 Cut 후 Open
05/14,4ABLD131 ERROR 대응,11:57,12:21,AI Close/Open
05/16,4ABLD121 Error 대응 (새벽),03:49,04:09,AI Close/Open
05/16,4ABLD121 Error 대응 (아침),07:45,08:00,AI Close/Open
05/18,ZT#6 호기 6F CONV OHT Teaching (오전),10:02,10:20,Capa 조정 (50% Down) 후 작업 취소 및 원복
05/18,ZT#6 호기 6F CONV OHT Teaching (오후),15:07,15:47,Capa 1 변경 후 작업 완료 후 원복
05/19,ZT#6 호기 BCL 설치 작업 (오전),09:00,09:52,Maxcapa 1~2 조정하며 5/10 개 설치 완료
05/19,ZT#6 호기 BCL 설치 작업 (오후),14:01,15:46,3 차 작업까지 완료 Upper 구간 BCL 설치 종료
05/21,3F Bridge ZT 6 호기 Teaching (오전),08:57,11:21,작업 종료
05/21,M16A 6ABL0121 Error 대응,13:31,13:40,AI Banned T 변경
05/21,3F Bridge ZT 6 호기 Teaching (오후),14:27,15:30,4 개소 티칭 완료 BCL/E84 설정 작업 진행
05/21,ZT5-1 호기 LOW FORK DISABLE 조치,14:44,17:14,잔류 FOUP 정리 3F IN CAPA 2 변경 2F 차단
05/21,M14A/B Maxcapa 1 변경 (야간),17:10,21:32,Hub 정체 및 Bridge 순환을 위한 조정
05/22,M16>M14>M10A/C 반송 지연 분석,16:34,16:45,STK FULL 아님 Manual 반송 영역 확인
05/24,M16A 6ABL0111 ERROR 대응,12:18,12:50,AI Banned T 변경 후 처리 완료
05/25,6AFS6201/6202 IN 증가 확인,16:13,16:25,STK 이상 없음 Queue 많음 확인
05/25,M16A ZT Maxcapa 50% 변경,17:04,17:05,조치 완료
05/25,M14A/B Maxcapa 50% 변경 및 원복,17:06,17:41,변경 후 원복 완료
05/25,M16 Maxcapa 1 변경,18:02,18:13,조치 완료
05/25,Deadlock 및 Storage Full 대응,18:34,21:15,층간반송 차단 Capa 조정 (70→10) Port 개방 조절
05/25,M16HUB Queue High Alarm 발생,19:59,20:39,Queue 2000 개 초과 지속
05/25,M14A/B Maxcapa 원복,22:06,22:14,정상화 조치
05/26,M16A Storage 층간 이동 수량 변경,07:58,-,임시 변경
05/26,작업 일정 재수립 및 취소 공지,08:41,08:50,연휴 물류 악화로 인한 일정 조정
05/26,M16A ZT5-1 호기 Motor 교체 작업 인폼,17:03,-,5/27 작업 예정 공지
05/26,HUB 쪽 OHT 몰림 현상 분산 요청,21:09,21:12,6AFS6201/6202 분산 요청
05/27,ZT5-1 호기 Lower Fork Motor 교체,08:16,13:47,3F/6F AI Close → 부분 Open → 전체 Open
05/27,SFA Lifter Maxcapa 1 전체 변경,13:44,13:59,조치 완료
05/27,M14A Maxcapa 1 변경 및 원복,13:50,14:25,변경 후 원복 완료
05/27,M16 6F Maxcapa 3 변경,13:47,15:30,작업 완료 후 원복
05/28,4AFC3201 Port 증축 작업 일정 재공지,11:25,11:31,5/29 작업으로 일정 확정
05/29,M16A ZT 3-2 호기 6ABL6032 Error 대응,08:16,10:18,Close → Clear/Open → 재발생 조치 → 전 Port Open
""".strip()

TIME_RE = re.compile(r'(\d{1,2}):(\d{2})')


def parse_schedule(point_min):
    """SCHEDULE_TEXT → [(start_dt, end_dt, content, note)] (2026년)."""
    events = []
    for ln in SCHEDULE_TEXT.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(',')
        if len(parts) < 4:
            continue
        mmdd, content, s_raw, e_raw = parts[0], parts[1], parts[2], parts[3]
        note = ','.join(parts[4:]) if len(parts) > 4 else ''
        try:
            mm, dd = mmdd.split('/')
            base = datetime(YEAR, int(mm), int(dd))
        except ValueError:
            continue
        sm = TIME_RE.search(s_raw)
        if not sm:                                  # 시작 미상 → 스킵
            continue
        start = base.replace(hour=int(sm.group(1)), minute=int(sm.group(2)))
        nextday = '익일' in e_raw
        em = TIME_RE.search(e_raw)
        if em:
            end = base.replace(hour=int(em.group(1)), minute=int(em.group(2)))
            if nextday or end < start:              # 자정 넘김
                end += timedelta(days=1)
        else:                                       # 종료 '-' 미상 → 기본 지속
            end = start + timedelta(minutes=point_min)
        events.append((start, end, content, note))
    return events


def load_episode_jams(fp, guard):
    """episode.csv → 정체 구간 [(t0-guard, t0+guard, content)]. 정체류만."""
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
        s = (r.get('start_time') or '').strip()
        try:
            t0 = datetime.strptime(s[:16], '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        out.append((t0 - timedelta(minutes=guard), t0 + timedelta(minutes=guard),
                    f"정체:{r.get('fault_type','')}"))
    return out


def load_raw_times(raw_path):
    """raw/features CSV(들) → [(datetime, raw_line_fields, header)]. 시간컬럼 자동인식."""
    files = []
    if os.path.isdir(raw_path):
        for ext in ('*.csv', '*.CSV'):
            files += glob.glob(os.path.join(raw_path, ext))
    else:
        files = [raw_path]
    rows = []
    header = None
    for fp in sorted(files):
        for enc in ('utf-8-sig', 'utf-8', 'cp949'):
            try:
                f = open(fp, encoding=enc)
                rd = csv.reader(f)
                hdr = next(rd)
                break
            except (UnicodeDecodeError, StopIteration):
                continue
        else:
            print(f"⚠️ 읽기 실패: {fp}"); continue
        tcol = 0
        for i, c in enumerate(hdr):
            if c.strip().upper() in ('CRT_TM', 'DATETIME'):
                tcol = i; break
        if header is None:
            header = hdr
        for rec in rd:
            if not rec or len(rec) <= tcol:
                continue
            ts = rec[tcol].strip()
            try:
                t = datetime.strptime(ts[:16], '%Y-%m-%d %H:%M')
            except ValueError:
                continue
            rows.append((t, rec))
        f.close()
    rows.sort(key=lambda x: x[0])
    return rows, header


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--episode', default=None)
    ap.add_argument('--buffer', type=int, default=15)
    ap.add_argument('--point', type=int, default=30)
    ap.add_argument('--guard', type=int, default=60)
    ap.add_argument('--out', default='./out_ml')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    print("=" * 64)
    print("정상데이터 생성 — TSPulse R1 학습용 (작업일정 구간 제거)")
    print("=" * 64)

    work = parse_schedule(a.point)
    print(f"[작업일정] {len(work)}건 파싱 (2026)")
    jams = load_episode_jams(a.episode, a.guard) if a.episode else []
    if a.episode:
        print(f"[정체] episode {len(jams)}건 (±{a.guard}분 제거)")

    rows, header = load_raw_times(a.raw)
    if not rows:
        print("⚠️ raw 없음 — 경로 확인"); return
    t_lo, t_hi = rows[0][0], rows[-1][0]
    print(f"[raw] {len(rows)}분 ({t_lo}~{t_hi}) / 컬럼 {len(header)}")

    # 제거 구간 = 작업(±buffer) + 정체(±guard)
    def expand(evs, buf):
        return [(s - timedelta(minutes=buf), e + timedelta(minutes=buf), c) for s, e, c, *_ in
                [(x[0], x[1], x[2]) for x in evs]]
    excl = [(s - timedelta(minutes=a.buffer), e + timedelta(minutes=a.buffer), 'work', c, n)
            for (s, e, c, n) in work]
    excl += [(s, e, 'jam', c, '') for (s, e, c) in jams]

    # 각 분 판정
    def reason_at(t):
        for s, e, kind, c, n in excl:
            if s <= t <= e:
                return kind, c
        return None, ''

    kept, removed_work, removed_jam = [], 0, 0
    mask_rows = []
    for t, rec in rows:
        kind, c = reason_at(t)
        if kind is None:
            kept.append(rec)
            mask_rows.append((t, 1, ''))
        else:
            if kind == 'work':
                removed_work += 1
            else:
                removed_jam += 1
            mask_rows.append((t, 0, f'{kind}:{c}'))

    # ── 저장: 정상데이터 (원본 컬럼 그대로) ──
    with open(os.path.join(a.out, '정상데이터.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(header)
        for rec in kept:
            w.writerow(rec)
    # ── 저장: 정상마스크 ──
    with open(os.path.join(a.out, '정상마스크.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['datetime', 'is_normal', '제외사유'])
        for t, n, r in mask_rows:
            w.writerow([t.strftime('%Y-%m-%d %H:%M'), n, r])
    # ── 저장: 제거구간 목록 ──
    with open(os.path.join(a.out, '제거구간.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['시작', '종료', '종류', '내용', '비고'])
        for s, e, kind, c, n in sorted(excl):
            if e < t_lo or s > t_hi:            # raw 범위 밖 구간은 생략
                continue
            w.writerow([s.strftime('%Y-%m-%d %H:%M'), e.strftime('%Y-%m-%d %H:%M'), kind, c, n])

    # ── 리포트 ──
    n = len(rows)
    nk = len(kept)
    print("\n" + "-" * 64)
    print(f"총 {n}분")
    print(f"  ├ 작업일정 제거 : {removed_work}분 ({removed_work/n*100:.1f}%)")
    print(f"  ├ 정체 제거     : {removed_jam}분 ({removed_jam/n*100:.1f}%)")
    print(f"  └ ★정상 kept    : {nk}분 ({nk/n*100:.1f}%)  ← TSPulse 학습 입력")
    # 일자별
    from collections import defaultdict
    per = defaultdict(lambda: [0, 0])
    for t, isn, r in mask_rows:
        per[t.date()][0] += 1
        per[t.date()][1] += isn
    if len(per) <= 3:
        print("\n[일자별]")
        for d in sorted(per):
            tot, nn = per[d]
            print(f"  {d}  정상 {nn}/{tot}분 ({nn/tot*100:.0f}%)  제거 {tot-nn}분")
    print(f"\n🎉 → {a.out}/정상데이터.csv (+ 정상마스크·제거구간)")
    print("다음: features_31.py 를 정상데이터.csv 에 돌려 → tspulse_train.py")


if __name__ == '__main__':
    main()
