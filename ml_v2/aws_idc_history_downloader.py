# -*- coding: utf-8 -*-
"""
AWS_IDC_DATA_HIS — 과거 기간 다운로더 (aws_idc_realtime_collector.py 개조판)
==========================================================================
원본(aws_idc_realtime_collector.py)은 실시간용으로 쿼리가
    WHERE CRT_TM BETWEEN SYSDATE - :window_min/1440 AND SYSDATE
로 고정되어 있어 과거 구간을 뽑을 수 없다.
이 버전은 **날짜 범위**를 받아 하루(또는 한 시간)씩 끊어 파일로 저장한다.

바뀐 점 (그 외 컬럼 정의·PIVOT 쿼리 방식·로깅은 원본과 동일)
  · SYSDATE 윈도우  →  :d0 ~ :d1 날짜 바인드
  · 무한 루프(매분)  →  기간 루프 후 종료
  · 단일 파일 덮어쓰기 → 날짜별 파일 (M16A_HUBROOM_PR_20260701.CSV ...)
  · 컬럼 목록을 기존 CSV 헤더에서 읽는 옵션 추가(--columns-from)
    → 학습 데이터(265컬럼)와 구성을 100% 일치시킬 때 사용
  · 비밀번호 하드코딩 제거 → 환경변수 ORA_PASS 필수

사용
    export ORA_USER=STAREAD  ORA_PASS='****'  ORA_DSN=10.40.41.103:1521/ICASTARPP

    # 7월 전체, 일별 파일 (기존 4~5월과 동일 형식)
    python aws_idc_history_downloader.py --from 2026-07-01 --to 2026-07-31 \
        --columns-from RAW/M16A_HUBROOM_PR_20260401.CSV --out RAW

    # 시간별 파일 (M16A_HUBROOM_PR_2026070101.csv)
    python aws_idc_history_downloader.py --from 2026-07-01 --to 2026-07-31 \
        --columns-from RAW/M16A_HUBROOM_PR_20260401.CSV --out RAW \
        --split hour --ext .csv

    # --columns-from 없이 돌리면 이 파일에 내장된 59개 IDC 컬럼만 저장
"""

import argparse
import os
import sys
import time
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path

try:
    import oracledb
except ImportError:                     # 안내만 하고, 컬럼/SQL 로직은 검증 가능하게
    oracledb = None

# ==========================================================
# 설정
# ==========================================================
ORACLE_USER     = os.getenv("ORA_USER", "STAREAD")
ORACLE_PASSWORD = os.getenv("ORA_PASS")          # 하드코딩 제거 — 환경변수 필수
ORACLE_DSN      = os.getenv("ORA_DSN",  "10.40.41.103:1521/ICASTARPP")

OUTPUT_DIR      = Path("RAW")                    # --out 으로 덮어씀
LOG_FILE        = Path("history_download.log")

# ==========================================================
# 로깅
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("idc_history")

# ==========================================================
# IDC 컬럼 (v3 — 60개)
# ==========================================================
IDC_COLUMNS = [
    # M16HUB 기존 32
    "M16HUB.QUE.ALL.CURRENTQCNT",
    "M16HUB.QUE.ALL.CURRENTQCOMPLETED",
    "M16HUB.QUE.OHT.CURRENTOHTQCNT",
    "M16HUB.QUE.OHT.OHTUTIL",
    "M16HUB.QUE.LOAD.AVGLOADTIME",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERTIMEAVG",
    "M16HUB.QUE.TIME.AVGTOTALTIME",
    "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
    "M16HUB.OHT.ALERT.OHTMCPALARMCNT",
    "M16HUB.QUE.M14TOM16.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14A.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14B.MESCURRENTQCNT",
    "M16HUB.QUE.ALL.FABTRANSJOBCNT",
    "M16HUB.QUE.M14ATOM16.MESCURRENTQCNT",
    "M16HUB.QUE.M14BTOM16.MESCURRENTQCNT",
    "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.TOTAL_CURRENTQCNT",
    "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT",
    "M16HUB.STRATE.STK.STORAGERATIO",
    "M16HUB.STRATE.ALL.FABSTORAGERATIO",
    # 32번째는 위에 다 들어감 - 31개. 원본 v3 헤더와 맞춤 (M16HUB 31개)
    # ★★★ M14 STATECNT (4)
    "M14.OHT.STATECNT.HTSTOP",
    "M14.OHT.STATECNT.CONGESTED",
    "M14.OHT.STATECNT.ABNORMAL",
    "M14.OHT.STATECNT.OBSANDBZSTOP",
    # ★★ M14B 트래픽/지연 (6)
    "M14B.QUE.OHT.OHTUTIL",
    "M14B.QUE.OHT.CURRENTOHTQCNT",
    "M14B.QUE.TIME.AVGTOTALTIME",
    "M14B.QUE.TIME.AVGTOTALTIME1MIN",
    "M14B.QUE.ABN.AOTRANSDELAY",
    "M14B.OHT.ALERT.OHTMCPALARMCNT",
    # ★★★ M14B 7F 리프터 4ABLDxxx (6)
    "M14B.LFT.4ABLD111.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD112.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD121.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD122.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD131.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD132.TOTAL_CURRENTQCNT",
    # ★★ M14B 7F→HUB (3)
    "M14B.QUE.ALL.7F_TO_HUB_JOB",
    "M14B.QUE.ALL.7F_TO_HUB_JOB_ALT",
    "M14B.QUE.OHT.7F_TO_HUB_CMD",
    # ★ M14B Send Fab (1)
    "M14B.LFT.SENDFAB.TO_M16HUB_CURRENTQCNT",
    # ★★ M16_PKT 브릿지 (4)
    "M16_PKT.QUE.OHT.OHTUTIL",
    "M16_PKT.QUE.TIME.AVGTOTALTIME1MIN",
    "M16_PKT.QUE.ABN.AOTRANSDELAY",
    "M16_PKT.OHT.ALERT.OHTMCPALARMCNT",
    # ★★ M16_WT 브릿지 (4)
    "M16_WT.QUE.OHT.OHTUTIL",
    "M16_WT.QUE.TIME.AVGTOTALTIME1MIN",
    "M16_WT.QUE.ABN.AOTRANSDELAY",
    "M16_WT.OHT.ALERT.OHTMCPALARMCNT",
]

CSV_HEADER = ["CRT_TM"] + IDC_COLUMNS

# ==========================================================
# SQL — 원본 PIVOT 방식 유지, 시간조건만 날짜 바인드로 교체
# ==========================================================
def build_sql(columns) -> str:
    pivot_cols = ",\n  ".join(
        f"MAX(CASE WHEN IDC_NM='{nm}' THEN IDC_VAL END) AS \"{nm}\""
        for nm in columns
    )
    in_list = ",\n    ".join(f"'{nm}'" for nm in columns)
    return f"""
SELECT
  TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI:SS') AS CRT_TM,
  {pivot_cols}
FROM AWS_IDC_DATA_HIS
WHERE CRT_TM >= :d0 AND CRT_TM < :d1
  AND IDC_NM IN (
    {in_list}
  )
GROUP BY CRT_TM
ORDER BY CRT_TM
""".strip()


# ==========================================================
# 수집 — 구간 조회 후 파일 저장
# ==========================================================
def read_columns_from_csv(path: str) -> list:
    """기존 CSV 헤더에서 컬럼 목록을 읽는다 (265컬럼 구성 일치용)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    cols = [c.strip() for c in header if c.strip() and c.strip() != "CRT_TM"]
    if not cols:
        sys.exit(f"컬럼을 못 읽었습니다: {path}")
    return cols


def fetch_range(conn, sql, t0, t1) -> list:
    """[t0, t1) 구간 행 목록."""
    with conn.cursor() as cur:
        cur.arraysize = 5000
        cur.execute(sql, d0=t0, d1=t1)
        return cur.fetchall()


def save_rows(path: Path, header: list, rows: list) -> int:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for r in rows:
            writer.writerow(["" if v is None else v for v in r])
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.5)
    return len(rows)


# ==========================================================
# 메인 — 기간 루프 후 종료 (원본은 매분 무한루프)
# ==========================================================
def main():
    ap = argparse.ArgumentParser(
        description="AWS_IDC_DATA_HIS 과거 기간 다운로더")
    ap.add_argument("--from", dest="d_from", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="d_to", required=True, help="YYYY-MM-DD (포함)")
    ap.add_argument("--out", default="RAW", help="저장 폴더 (기본 RAW)")
    ap.add_argument("--prefix", default="M16A_HUBROOM_PR_")
    ap.add_argument("--split", choices=["day", "hour"], default="day",
                    help="day=20260701 (기본) / hour=2026070101")
    ap.add_argument("--ext", default=".CSV", help=".CSV 또는 .csv")
    ap.add_argument("--columns-from", default=None,
                    help="기존 CSV 헤더에서 컬럼 목록 읽기 (265컬럼 일치용). "
                         "생략하면 내장 IDC_COLUMNS 사용")
    ap.add_argument("--overwrite", action="store_true", help="기존 파일 덮어씀")
    a = ap.parse_args()

    if oracledb is None:
        sys.exit("oracledb 모듈이 필요합니다:  pip install oracledb")
    if not ORACLE_PASSWORD:
        sys.exit("환경변수 ORA_PASS 가 필요합니다.\n"
                 "  예) export ORA_PASS='****'   (ORA_USER/ORA_DSN 은 기본값 사용 가능)")
    if not a.ext.startswith("."):
        a.ext = "." + a.ext

    columns = (read_columns_from_csv(a.columns_from) if a.columns_from
               else IDC_COLUMNS)
    header = ["CRT_TM"] + columns
    sql = build_sql(columns)

    d0 = datetime.strptime(a.d_from, "%Y-%m-%d")
    d1 = datetime.strptime(a.d_to, "%Y-%m-%d")
    if d1 < d0:
        sys.exit("--to 가 --from 보다 앞섭니다")
    end = d1 + timedelta(days=1)                 # --to 당일 포함
    step, dfmt, expect, unit = (
        (timedelta(hours=1), "%Y%m%d%H", 60, "시간") if a.split == "hour"
        else (timedelta(days=1), "%Y%m%d", 1440, "일"))

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("AWS_IDC_DATA_HIS 과거 다운로더 시작")
    log.info(f"  DSN     : {ORACLE_DSN}")
    log.info(f"  USER    : {ORACLE_USER}")
    log.info(f"  기간     : {a.d_from} ~ {a.d_to}  ({a.split} 단위)")
    log.info(f"  OUTPUT  : {out_dir}/{a.prefix}{d0:{dfmt}}{a.ext}")
    log.info(f"  COLUMNS : {len(columns)}개 IDC + CRT_TM"
             + (f"  (기준 {Path(a.columns_from).name})" if a.columns_from else " (내장)"))
    log.info("=" * 60)

    conn = None
    total, done, skipped, failed = 0, 0, 0, 0
    cur_t = d0
    try:
        conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD,
                                dsn=ORACLE_DSN)
        log.info("Oracle 연결 성공")

        while cur_t < end:
            name = f"{a.prefix}{cur_t:{dfmt}}{a.ext}"
            path = out_dir / name
            if path.exists() and not a.overwrite:
                log.info(f"  {name}  (이미 있음 — 건너뜀)")
                skipped += 1
                cur_t += step
                continue
            t_start = time.time()
            try:
                rows = fetch_range(conn, sql, cur_t, cur_t + step)
            except oracledb.DatabaseError as e:
                log.error(f"  {name}  DB 오류: {e}")
                failed += 1
                try:
                    conn.close()
                except Exception:
                    pass
                conn = oracledb.connect(user=ORACLE_USER,
                                        password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
                cur_t += step
                continue
            n = save_rows(path, header, rows)
            total += n
            done += 1
            warn = f"  ⚠ {expect}행 미달" if n < expect * 0.97 else ""
            log.info(f"  {name}  {n}행  ({time.time()-t_start:.1f}s){warn}")
            cur_t += step

    except KeyboardInterrupt:
        log.warning("사용자 중단 — 받은 파일은 보존됩니다 (재실행 시 이어받음)")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    log.info("=" * 60)
    log.info(f"완료: {done}{unit} 저장 · {skipped}{unit} 건너뜀 · "
             f"실패 {failed} · 총 {total}행")
    log.info(f"확인:  python data.py --data \"{a.out}/*{a.ext}\" --window 10 --pct 0.99")


if __name__ == "__main__":
    main()
