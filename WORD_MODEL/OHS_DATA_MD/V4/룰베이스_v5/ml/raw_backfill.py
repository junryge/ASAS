#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# raw_backfill — 과거 구간 원본(M16A_HUBROOM_PR) 일별 수집
# ====================================================================
# 실시간 수집기(aws_idc_realtime_collector)는 SYSDATE-90분만 가져온다.
# 이 스크립트는 임의 기간을 날짜별 CSV 로 뽑아, hubroom_predictor 로
# 발동이벤트/사건단위를 다시 만들 수 있게 한다.
#
# 컬럼 정의·SQL 형식은 수집기 모듈에서 그대로 가져와 쓰므로 형식이 100% 동일하다.
# (수집기 파일이 같은 폴더 또는 --collector 경로에 있어야 한다)
#
# 사용법:
#   python raw_backfill.py --from 2026-07-01 --to 2026-07-31 -o .\RAW_7
#     → RAW_7\M16A_HUBROOM_PR_20260701.CSV ... _20260731.CSV (31개)
#
#   이어서:
#   python hubroom_predictor.py .\RAW_7\M16A_HUBROOM_PR_20260701.CSV -o .\out_7
#   (또는 --run-predictor 로 한 번에)
#
# 옵션:
#   --chunk-hours 6   하루가 무거우면 시간 단위로 쪼개서 조회 (기본 24=하루 한 번)
#   --skip-existing   이미 있는 날짜 파일은 건너뜀 (중단 후 이어받기)
#   --run-predictor   수집 직후 hubroom_predictor 를 날짜순으로 자동 실행
import argparse
import csv
import importlib.util
import os
import sys
import time
from datetime import datetime, timedelta


def load_collector(path):
    """수집기 모듈 로드 — IDC_COLUMNS / CSV_HEADER / 접속정보를 재사용."""
    cands = [path] if os.path.isabs(path) else [
        os.path.join(os.getcwd(), path),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), path),
    ]
    fp = next((p for p in cands if os.path.exists(p)), None)
    if not fp:
        raise SystemExit(f'❌ 수집기 파일 없음: {path}\n'
                         f'   aws_idc_realtime_collector.py 를 같은 폴더에 두거나 --collector 로 지정하세요')
    spec = importlib.util.spec_from_file_location('_collector', fp)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['_collector'] = mod
    spec.loader.exec_module(mod)
    print(f'  [수집기] {fp} · 컬럼 {len(mod.IDC_COLUMNS)}개')
    return mod


def build_sql(cols):
    """수집기와 동일한 PIVOT 쿼리 — 시간 조건만 SYSDATE → 명시 구간으로."""
    pivot = ",\n  ".join(f"MAX(CASE WHEN IDC_NM='{n}' THEN IDC_VAL END) AS \"{n}\"" for n in cols)
    in_list = ",\n    ".join(f"'{n}'" for n in cols)
    return f"""
SELECT
  TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI:SS') AS CRT_TM,
  {pivot}
FROM AWS_IDC_DATA_HIS
WHERE CRT_TM >= TO_DATE(:dt_from, 'YYYY-MM-DD HH24:MI:SS')
  AND CRT_TM <  TO_DATE(:dt_to,   'YYYY-MM-DD HH24:MI:SS')
  AND IDC_NM IN (
    {in_list}
  )
GROUP BY CRT_TM
ORDER BY CRT_TM
""".strip()


def fetch_range(conn, sql, f, t):
    with conn.cursor() as cur:
        cur.execute(sql, dt_from=f.strftime('%Y-%m-%d %H:%M:%S'),
                         dt_to=t.strftime('%Y-%m-%d %H:%M:%S'))
        return cur.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='d_from', required=True, help='시작일 YYYY-MM-DD')
    ap.add_argument('--to', dest='d_to', required=True, help='종료일 YYYY-MM-DD (포함)')
    ap.add_argument('-o', '--out', default='./RAW_BACKFILL', help='출력 폴더')
    ap.add_argument('--collector', default='aws_idc_realtime_collector.py')
    ap.add_argument('--chunk-hours', dest='chunk_hours', type=int, default=24,
                    help='하루를 몇 시간 단위로 쪼개 조회할지 (기본 24 = 한 번에)')
    ap.add_argument('--skip-existing', action='store_true', help='이미 있는 날짜 파일 건너뜀')
    ap.add_argument('--run-predictor', action='store_true',
                    help='수집 후 hubroom_predictor 를 날짜순 자동 실행')
    ap.add_argument('--predictor', default='hubroom_predictor.py')
    ap.add_argument('--predictor-out', dest='pred_out', default='./out_backfill')
    a = ap.parse_args()

    d0 = datetime.strptime(a.d_from, '%Y-%m-%d')
    d1 = datetime.strptime(a.d_to, '%Y-%m-%d')
    if d1 < d0:
        raise SystemExit('❌ --to 가 --from 보다 빠릅니다')
    os.makedirs(a.out, exist_ok=True)

    col = load_collector(a.collector)
    sql = build_sql(col.IDC_COLUMNS)
    header = col.CSV_HEADER

    import oracledb
    print(f'  [DB] {col.ORACLE_DSN} 접속…')
    conn = oracledb.connect(user=col.ORACLE_USER, password=col.ORACLE_PASSWORD,
                            dsn=col.ORACLE_DSN)
    print(f'  [DB] 접속 OK (v{conn.version})')

    made, skipped, empty = [], 0, []
    try:
        day = d0
        while day <= d1:
            ymd = day.strftime('%Y%m%d')
            out_fp = os.path.join(a.out, f'M16A_HUBROOM_PR_{ymd}.CSV')
            if a.skip_existing and os.path.exists(out_fp):
                skipped += 1; print(f'  · {ymd} 건너뜀(이미 있음)'); day += timedelta(days=1); continue

            t0 = time.time()
            rows = []
            span = timedelta(hours=max(1, a.chunk_hours))
            cur_t, end_t = day, day + timedelta(days=1)
            while cur_t < end_t:
                nxt = min(cur_t + span, end_t)
                rows.extend(fetch_range(conn, sql, cur_t, nxt))
                cur_t = nxt

            with open(out_fp, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                w.writerow(header)
                for r in rows:
                    w.writerow(['' if v is None else v for v in r])
            print(f'  ✅ {ymd} — {len(rows):>5}행 · {time.time()-t0:.1f}s → {os.path.basename(out_fp)}')
            made.append(out_fp)
            if not rows:
                empty.append(ymd)
            day += timedelta(days=1)
    finally:
        conn.close()

    n_day = (d1 - d0).days + 1
    print(f'\n🎉 수집 완료 — {len(made)}개 생성 / {skipped}개 건너뜀 (요청 {n_day}일)')
    if empty:
        print(f'  ⚠️ 데이터 0행인 날짜: {", ".join(empty)}  (그날 수집이 없었거나 보존기간 밖)')

    if a.run_predictor:
        print(f'\n[예측기] {a.predictor} 실행 → {a.pred_out}')
        os.makedirs(a.pred_out, exist_ok=True)
        for fp in made:
            r = os.system(f'"{sys.executable}" "{a.predictor}" "{fp}" -o "{a.pred_out}"')
            print(f'  {"✅" if r == 0 else "❌"} {os.path.basename(fp)}')
        print('🎉 발동이벤트 / 사건단위 생성 완료')


if __name__ == '__main__':
    main()
