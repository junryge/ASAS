#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_split40.py — 40개 분할 수집 + 자동 머지 (Python only, SQL*Plus 불필요)

사용법:
  pip install oracledb
  python3 collect_split40.py [출력디렉토리=./data]

환경변수 (옵션):
  ORA_USER, ORA_PASS, ORA_DSN — DB 접속 정보 덮어쓰기

동작:
  1) DB 접속
  2) 8영역 × 5개월 = 40개 쿼리 순차 실행
     (작은 영역부터: M16_PKT → M16_WT → M16 → M16B → M16A → M14 → M14B → M16HUB)
  3) 각각 IDC_{영역}_{YYYYMM}.csv 로 저장
  4) 자동 머지 호출 → ALL_MERGED.csv 생성
"""
import os
import sys
import csv
import time
from datetime import datetime
from pathlib import Path

import oracledb

# ==========================================================
# 설정
# ==========================================================
ORA_USER = os.getenv("ORA_USER", "STAREAD")
ORA_PASS = os.getenv("ORA_PASS", "Stareadadmin123!")
ORA_DSN  = os.getenv("ORA_DSN",  "10.40.41.103:1521/ICASTARPP")

OUTPUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data")

MONTHS = [
    ("202601", "2026-01-01 00:00:00", "2026-01-31 23:59:59"),
    ("202602", "2026-02-01 00:00:00", "2026-02-28 23:59:59"),
    ("202603", "2026-03-01 00:00:00", "2026-03-31 23:59:59"),
    ("202604", "2026-04-01 00:00:00", "2026-04-30 23:59:59"),
    ("202605", "2026-05-01 00:00:00", "2026-05-26 23:59:59"),
]

# 영역 → 컬럼 매핑 (265개 분포)
AREA_COLS = {
  "M16HUB": [
    "M16HUB.CNV.SENDFAB.TO_M14A_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0111.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0112.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0121.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL0122.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6012.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6021.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6022.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.2F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6031.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.2F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.3F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.3F_TO_6F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.6F_TO_2F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.6F_TO_3F_CURRENTQCNT",
    "M16HUB.LFT.6ABL6032.TOTAL_CURRENTQCNT",
    "M16HUB.LFT.SENDFAB.TO_M14B_CURRENTQCNT",
    "M16HUB.LFT.SENDFAB.TO_M16A_CURRENTQCNT",
    "M16HUB.LFT.SENDFAB.TO_M16E_CURRENTQCNT",
    "M16HUB.OHT.ALERT.OHTMCPALARMCNT",
    "M16HUB.QUE.ABN.AOTRANSDELAY",
    "M16HUB.QUE.ALL.3F_CMD",
    "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB",
    "M16HUB.QUE.ALL.3F_TO_M14A_3F_JOB",
    "M16HUB.QUE.ALL.3F_TO_M14B_7F_JOB",
    "M16HUB.QUE.ALL.3F_TO_M16A_2F_JOB",
    "M16HUB.QUE.ALL.3F_TO_M16A_6F_JOB",
    "M16HUB.QUE.ALL.CURRENTQCNT",
    "M16HUB.QUE.ALL.CURRENTQCOMPLETED",
    "M16HUB.QUE.ALL.CURRENTQCREATED",
    "M16HUB.QUE.ALL.CURRENT_M16A_3F_JOB",
    "M16HUB.QUE.ALL.CURRENT_M16A_3F_JOB_2",
    "M16HUB.QUE.ALL.FABTRANSJOBCNT",
    "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO",
    "M16HUB.QUE.ALL.TRANSPORT4MINOVERTIMEAVG",
    "M16HUB.QUE.CNV.3F_CNV_MAXCAPA",
    "M16HUB.QUE.CNV.3F_TO_M14A_CNV_AI_CMD",
    "M16HUB.QUE.LFT.3F_LFT_MAXCAPA",
    "M16HUB.QUE.LFT.3F_M14BLFT_MAXCAPA",
    "M16HUB.QUE.LFT.3F_TO_M14B_LFT_AI_CMD",
    "M16HUB.QUE.LFT.3F_TO_M16A_LFT_AI_CMD",
    "M16HUB.QUE.LOAD.AVGLOADTIME",
    "M16HUB.QUE.M14ATOM16.MESCURRENTQCNT",
    "M16HUB.QUE.M14BTOM16.MESCURRENTQCNT",
    "M16HUB.QUE.M14TOM16.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14A.MESCURRENTQCNT",
    "M16HUB.QUE.M16TOM14B.MESCURRENTQCNT",
    "M16HUB.QUE.MLUD.3F_TO_M16A_MLUD_AI_CMD",
    "M16HUB.QUE.OHT.CURRENTOHTQCNT",
    "M16HUB.QUE.OHT.OHTUTIL",
    "M16HUB.QUE.STB.3F_TO_M16A_3F_STB_CMD",
    "M16HUB.QUE.TIME.AVGTOTALTIME",
    "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
    "M16HUB.STRATE.ALL.FABSTORAGERATIO",
    "M16HUB.STRATE.STB.3F_STORAGE_UTIL",
    "M16HUB.STRATE.STK.STORAGERATIO"
  ],
  "M14": [
    "M14.CNV.SENDFAB.TO_M16HUB_CURRENTQCNT",
    "M14.OHT.STATECNT.ABNORMAL",
    "M14.OHT.STATECNT.CONGESTED",
    "M14.OHT.STATECNT.HTSTOP",
    "M14.OHT.STATECNT.OBSANDBZSTOP",
    "M14.QUE.ABN.AOTRANSDELAY",
    "M14.QUE.ALL.3F_TO_HUB_JOB",
    "M14.QUE.ALL.3F_TO_HUB_JOB_ALT",
    "M14.QUE.ALL.CURRENTQCNT",
    "M14.QUE.ALL.CURRENTQCOMPLETED",
    "M14.QUE.ALL.CURRENTQCREATED",
    "M14.QUE.ALL.TOTALCNVCURRENTQCNT",
    "M14.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M14.QUE.ALL.TRANSPORT4MINOVERRATIO",
    "M14.QUE.ALL.TRANSPORT4MINOVERTIMEAVG",
    "M14.QUE.CNV.3F_CNV_MAXCAPA",
    "M14.QUE.CNV.ALLTONORTHCNVCURRENTQCNT",
    "M14.QUE.CNV.ALLTOSOUTHCNVCURRENTQCNT",
    "M14.QUE.CNV.M14ATOM16ACURRNETQCNT",
    "M14.QUE.CNV.M14ATOM16CURRNETQCNT",
    "M14.QUE.CNV.M14ATONORTHCURRENTQCNT",
    "M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT",
    "M14.QUE.CNV.NORTHCNVTOALLCURRENTQCNT",
    "M14.QUE.CNV.NORTHCNVTOM14TIME",
    "M14.QUE.CNV.NORTHCNVTOM14TIME1MIN",
    "M14.QUE.CNV.NORTHCURRENTQCNT",
    "M14.QUE.CNV.NORTHM14TOCNVTIME",
    "M14.QUE.CNV.NORTHM14TOCNVTIME1MIN",
    "M14.QUE.CNV.SOUTHCNVTOALLCURRENTQCNT",
    "M14.QUE.CNV.SOUTHCNVTOM14TIME",
    "M14.QUE.CNV.SOUTHCNVTOM14TIME1MIN",
    "M14.QUE.CNV.SOUTHCURRENTQCNT",
    "M14.QUE.CNV.SOUTHM14TOCNVTIME",
    "M14.QUE.CNV.SOUTHM14TOCNVTIME1MIN",
    "M14.QUE.LOAD.AVGLOADTIME",
    "M14.QUE.LOAD.AVGLOADTIME1MIN",
    "M14.QUE.OHT.3F_TO_HUB_CMD",
    "M14.QUE.OHT.OHTUTIL",
    "M14.QUE.SFAB.SENDTOM16",
    "M14.SORTER.ABN.CUSORTERWAITCOUNTOVER",
    "M14.SORTER.ABN.SORTERWAITCOUNTOVER"
  ],
  "M14B": [
    "M14B.LFT.4ABLD111.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD111.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD111.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD112.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD112.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD112.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD121.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD121.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD121.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD122.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD122.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD122.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD131.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD131.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD131.TOTAL_CURRENTQCNT",
    "M14B.LFT.4ABLD132.4F_TO_7F_CURRENTQCNT",
    "M14B.LFT.4ABLD132.7F_TO_4F_CURRENTQCNT",
    "M14B.LFT.4ABLD132.TOTAL_CURRENTQCNT",
    "M14B.LFT.SENDFAB.TO_M14A_CURRENTQCNT",
    "M14B.LFT.SENDFAB.TO_M16HUB_CURRENTQCNT",
    "M14B.OHT.ALERT.OHTMCPALARMCNT",
    "M14B.QUE.ABN.AOTRANSDELAY",
    "M14B.QUE.ALL.7F_TO_HUB_JOB",
    "M14B.QUE.ALL.7F_TO_HUB_JOB_ALT",
    "M14B.QUE.ALL.CURRENTQCNT",
    "M14B.QUE.ALL.CURRENTQCOMPLETED",
    "M14B.QUE.ALL.CURRENTQCREATED",
    "M14B.QUE.LFT.ALLTOLFTCURRENTQCNT",
    "M14B.QUE.LFT.LFTTOALLCURRENTQCNT",
    "M14B.QUE.LFT.M14BTOM16ACURRNETQCNT",
    "M14B.QUE.LOAD.AVGLOADTIME",
    "M14B.QUE.LOAD.AVGLOADTIME1MIN",
    "M14B.QUE.LOAD.CURRENTLOADQCNT",
    "M14B.QUE.OHT.7F_TO_HUB_CMD",
    "M14B.QUE.OHT.CURRENTOHTQCNT",
    "M14B.QUE.OHT.OHTUTIL",
    "M14B.QUE.SENDFAB.VERTICALQUEUECOUNT",
    "M14B.QUE.TIME.AVGTOTALTIME",
    "M14B.QUE.TIME.AVGTOTALTIME1MIN",
    "M14B.SORTER.ABN.CUSORTERWAITCOUNTOVER",
    "M14B.SORTER.ABN.SORTERWAITCOUNTOVER",
    "M14B.SORTER.ABN.SORTERWAITCOUNTOVER_B01"
  ],
  "M16A": [
    "M16A.LFT.SENDFAB.TO_M16B_CURRENTQCNT",
    "M16A.LFT.SENDFAB.TO_M16E_CURRENTQCNT",
    "M16A.LFT.SENDFAB.TO_M16HUB_CURRENTQCNT",
    "M16A.QUE.ABN.AOTRANSDELAY",
    "M16A.QUE.ALL.2F_TO_6F_JOB",
    "M16A.QUE.ALL.2F_TO_HUB_JOB",
    "M16A.QUE.ALL.2F_TO_HUB_JOB_ALT",
    "M16A.QUE.ALL.6F_TO_2F_JOB",
    "M16A.QUE.ALL.6F_TO_HUB_JOB",
    "M16A.QUE.ALL.6F_TO_HUB_JOB_ALT",
    "M16A.QUE.ALL.CURRENTQCNT",
    "M16A.QUE.ALL.CURRENTQCOMPLETED",
    "M16A.QUE.ALL.CURRENTQCREATED",
    "M16A.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M16A.QUE.ALL.TRANSPORT4MINOVERRATIO",
    "M16A.QUE.ALL.TRANSPORT4MINOVERTIMEAVG",
    "M16A.QUE.CNV.ALLTONORTHCNVCURRENTQCNT",
    "M16A.QUE.CNV.ALLTOSOUTHCNVCURRENTQCNT",
    "M16A.QUE.CNV.M16ATOM14ACURRNETQCNT",
    "M16A.QUE.CNV.M16ATOM14BCURRNETQCNT",
    "M16A.QUE.CNV.M16TOM14ACURRNETQCNT",
    "M16A.QUE.CNV.M16TOM14BCURRNETQCNT",
    "M16A.QUE.CNV.NORTHCNVTOALLCURRENTQCNT",
    "M16A.QUE.CNV.SOUTHCNVTOALLCURRENTQCNT",
    "M16A.QUE.LFT.2F_LFT_MAXCAPA",
    "M16A.QUE.LFT.6F_LFT_MAXCAPA",
    "M16A.QUE.LFT.ALLTOLFTCURRENTQCNT",
    "M16A.QUE.LFT.LFTTOALLCURRENTQCNT",
    "M16A.QUE.LOAD.AVGFOUPLOADTIME",
    "M16A.QUE.LOAD.AVGLOADTIME1MIN",
    "M16A.QUE.LOAD.CURRENTLOADQCNT",
    "M16A.QUE.OHT.2F_TO_HUB_CMD",
    "M16A.QUE.OHT.6F_TO_HUB_CMD",
    "M16A.QUE.OHT.CURRENTOHTQCNT",
    "M16A.QUE.OHT.OHTUTIL",
    "M16A.SORTER.ABN.CUSORTERWAITCOUNTOVER",
    "M16A.SORTER.ABN.SORTERWAITCOUNTOVER"
  ],
  "M16B": [
    "M16B.LFT.SENDFAB.TO_M16A_CURRENTQCNT",
    "M16B.QUE.ABN.AOTRANSDELAY",
    "M16B.QUE.ALL.10F_TO_HUB_JOB",
    "M16B.QUE.ALL.CURRENTQCNT",
    "M16B.QUE.ALL.CURRENTQCOMPLETED",
    "M16B.QUE.ALL.CURRENTQCREATED",
    "M16B.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M16B.QUE.ALL.TRANSPORT4MINOVERRATIO",
    "M16B.QUE.ALL.TRANSPORT4MINOVERTIMEAVG",
    "M16B.QUE.LOAD.AVGFOUPLOADTIME",
    "M16B.QUE.LOAD.AVGLOADTIME1MIN",
    "M16B.QUE.LOAD.CURRENTLOADQCNT",
    "M16B.QUE.OHT.CURRENTOHTQCNT",
    "M16B.QUE.OHT.OHTUTIL",
    "M16B.SORTER.ABN.CUSORTERWAITCOUNTOVER",
    "M16B.SORTER.ABN.SORTERWAITCOUNTOVER"
  ],
  "M16": [
    "M16.CNV.SENDFAB.TO_M16WT_CURRENTQCNT",
    "M16.QUE.SFAB.COMPLETEQUEUETOTAL",
    "M16.QUE.SFAB.COMPLETETOM10",
    "M16.QUE.SFAB.COMPLETETOM14",
    "M16.QUE.SFAB.RECEIVEQUEUETOTAL",
    "M16.QUE.SFAB.RETURNQUEUETOTAL",
    "M16.QUE.SFAB.RETURNTOM10",
    "M16.QUE.SFAB.RETURNTOM14",
    "M16.QUE.SFAB.SENDQUEUETOTAL",
    "M16.QUE.SFAB.SENDTOM10",
    "M16.QUE.SFAB.SENDTOM14"
  ],
  "M16_PKT": [
    "M16_PKT.OHT.ALERT.OHTMCPALARMCNT",
    "M16_PKT.QUE.ABN.AOTRANSDELAY",
    "M16_PKT.QUE.OHT.OHTUTIL",
    "M16_PKT.QUE.TIME.AVGTOTALTIME1MIN"
  ],
  "M16_WT": [
    "M16_WT.OHT.ALERT.OHTMCPALARMCNT",
    "M16_WT.QUE.ABN.AOTRANSDELAY",
    "M16_WT.QUE.OHT.OHTUTIL",
    "M16_WT.QUE.TIME.AVGTOTALTIME1MIN"
  ]
}

# 실행 순서: 작은 영역부터
AREA_ORDER = ["M16_PKT","M16_WT","M16","M16B","M16A","M14","M14B","M16HUB"]


# ==========================================================
# 쿼리 빌드
# ==========================================================
def build_query(cols):
    """영역 컬럼 리스트로 PIVOT SELECT 생성."""
    select_parts = ",\n  ".join(
        f"MAX(CASE WHEN IDC_NM=\'{c}\' THEN IDC_VAL END) AS \"{c}\""
        for c in cols
    )
    in_list = ",\n    ".join(f"\'{c}\'" for c in cols)
    return f"""
SELECT
  TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI') AS CRT_TM,
  {select_parts}
FROM AWS_IDC_DATA_HIS
WHERE CRT_TM BETWEEN TO_DATE(:start_dt, 'YYYY-MM-DD HH24:MI:SS')
                 AND TO_DATE(:end_dt, 'YYYY-MM-DD HH24:MI:SS')
  AND IDC_NM IN (
    {in_list}
  )
GROUP BY TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI')
ORDER BY TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI')
""".strip()


def collect_one(conn, area, cols, ym, start, end, out_path):
    """한 (영역, 월) 쿼리 실행 + CSV 저장. 반환: (행수, 소요초)"""
    sql = build_query(cols)
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(sql, start_dt=start, end_dt=end)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(col_names)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    return len(rows), time.time() - t0


# ==========================================================
# 머지 (merge_split40.py 동일 로직 내장)
# ==========================================================
def merge_all(in_dir, out_path):
    from collections import OrderedDict
    monthly = {}
    for ym, _, _ in MONTHS:
        merged = OrderedDict()
        all_cols = ["CRT_TM"]
        for area in AREA_ORDER:
            fn = in_dir / f"IDC_{area}_{ym}.csv"
            if not fn.exists():
                print(f"    ⚠ 누락: {fn.name}")
                continue
            with open(fn, "r", encoding="utf-8-sig") as f:
                rdr = csv.reader(f)
                hdr = next(rdr)
                crt_i = hdr.index("CRT_TM")
                area_cols = [c for i, c in enumerate(hdr) if i != crt_i]
                all_cols.extend(area_cols)
                for row in rdr:
                    t = row[crt_i]
                    if t not in merged:
                        merged[t] = {"CRT_TM": t}
                    for i, c in enumerate(hdr):
                        if i != crt_i:
                            merged[t][c] = row[i]
        monthly[ym] = (all_cols, merged)
        print(f"    {ym}: {len(merged):,}행, {len(all_cols)-1}컬럼")

    # 통합 컬럼 (중복 제거, 순서 보존)
    final_cols = ["CRT_TM"]
    seen = {"CRT_TM"}
    for ym in [m[0] for m in MONTHS]:
        if ym in monthly:
            for c in monthly[ym][0]:
                if c not in seen:
                    final_cols.append(c)
                    seen.add(c)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(final_cols)
        total = 0
        for ym in [m[0] for m in MONTHS]:
            if ym not in monthly: continue
            _, merged = monthly[ym]
            for t in sorted(merged.keys()):
                row_dict = merged[t]
                w.writerow([row_dict.get(c, "") for c in final_cols])
                total += 1
    return total, len(final_cols)


# ==========================================================
# 메인
# ==========================================================
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUTPUT_DIR / "collect_split40.log"

    print(f"="*70)
    print(f"  collect_split40.py — 40분할 수집 + 자동 머지")
    print(f"="*70)
    print(f"  DB     : {ORA_USER}@{ORA_DSN}")
    print(f"  출력   : {OUTPUT_DIR.resolve()}")
    print(f"  쿼리   : {len(AREA_ORDER)} 영역 × {len(MONTHS)} 개월 = {len(AREA_ORDER)*len(MONTHS)}개")
    print(f"="*70)

    t_start = time.time()
    conn = oracledb.connect(user=ORA_USER, password=ORA_PASS, dsn=ORA_DSN)
    print(f"\n[연결 성공]\n")

    done, fail = 0, 0
    for ym, start, end in MONTHS:
        print(f"--- {ym} ({start[:10]} ~ {end[:10]}) ---")
        for area in AREA_ORDER:
            cols = AREA_COLS[area]
            out = OUTPUT_DIR / f"IDC_{area}_{ym}.csv"
            try:
                n, dt = collect_one(conn, area, cols, ym, start, end, out)
                print(f"  ✅ {area:<8s} ({len(cols):3d}컬럼): {n:6,d}행, {dt:5.1f}s → {out.name}")
                done += 1
            except Exception as e:
                print(f"  ❌ {area:<8s}: {type(e).__name__}: {e}")
                fail += 1

    conn.close()
    elapsed = time.time() - t_start
    print(f"\n="*70)
    print(f"  수집 완료: {done}/{done+fail}, 총 {elapsed/60:.1f}분")
    print(f"="*70)

    if fail > 0:
        print(f"\n⚠ {fail}개 실패 — 머지 건너뜀")
        return

    # 머지
    print(f"\n[머지 시작]")
    merged_path = OUTPUT_DIR / "ALL_MERGED.csv"
    n_rows, n_cols = merge_all(OUTPUT_DIR, merged_path)
    print(f"\n  ✅ 머지 완료: {merged_path.name}  ({n_rows:,}행, {n_cols}컬럼)")
    print(f"\n총 소요시간: {(time.time()-t_start)/60:.1f}분")


if __name__ == "__main__":
    main()
