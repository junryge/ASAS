# -*- coding: utf-8 -*-
"""
QTransferDashBoardItemBatch.py
자바 QTransferDashBoardItemBatch.java (216줄) 마이그레이션.

역할: QTransfer 대시보드 행 생성·적재 (test_table6 = qtransfer_dashboard 대응)
  1) _build_requestor()          → TYP="REQUESTOR"  (MES 반송지시 Req 비율, requestorCount)
  2) _build_mcs_error_log_count()→ TYP="WARNINGLOG" (MCS ERROR LOG, mcsErrorLogCnt)
  3) _build_trans_que_predict_error() → TYP="ERROR" (예측 오차 ERROR_RATE/ERROR_VALUE, quePredictError)

자바 매핑:
  _run                          : QTransferDashBoardItemBatch.java:51-90
  insertLogpressoData           : :92-105  (table="qtransfer_dashboard" → DASHBOARD_TABLE)
  _buildRequestor               : :107-130
  _buildMcsErrorLogCount        : :132-144
  _buildTransQuePredictError    : :146-159
  _buildMap(type, queryData)    : :161-173 (1행에서 (k,v) 마다 1 OPER_ACT_CTN row 생성)
  _buildMap(content, val, type) : :175-199 (key/val 컬럼 지정)
  _getMapData                   : :201-215 (OPER_ACT_CTN/VAL/TYP/EVENT_DT/DUE_GBN_CD)

ERROR 행 예 (운영):
  OPER_ACT_CTN=ERROR_RATE,  TYP=ERROR, VAL=95.98
  OPER_ACT_CTN=ERROR_VALUE, TYP=ERROR, VAL=53.03

실행: Prediction_ml.py 마스터가 QTransferPredictBatch 다음에 --once 로 호출.
"""
import os
import sys
import json
import time
import urllib.parse
import urllib3
import requests
from io import StringIO
import csv as _csv
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(SCRIPT_DIR, "qtransfer_alarm_config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_api_key():
    for p in [os.path.join(SCRIPT_DIR, "api_key.txt"),
              os.path.join(os.getcwd(), "api_key.txt")]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
                if lines:
                    return lines[0].strip()
    return os.environ.get("LOGPRESSO_API_KEY", "")


CFG = load_config()
API_KEY = load_api_key()
HOST = CFG["logpresso"]["host"]
PORT = CFG["logpresso"]["port"]
DASHBOARD_TABLE = CFG["logpresso"].get("dashboard_table", "test_table6")
BASE = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv"

DASHBOARD_QUERIES = CFG.get("dashboard_queries", {})
REQUESTOR_LIST = CFG.get("dashboard_variables", {}).get(
    "QTRANSFER_REQUESTOR_LIST", '"RTD/RTS","EIS","ETC","OFS","MCS"'
)


# ─── Logpresso 헬퍼 (afagg 패턴) ────────────────
def query(q, timeout=120):
    if not q or not q.strip():
        return []
    qs = " ".join(q.split())
    url = f"{BASE}?_apikey={API_KEY}&_q={urllib.parse.quote(qs, safe='')}"
    try:
        r = requests.get(url, verify=False, timeout=timeout)
        if r.status_code != 200 or r.text.strip().startswith("<"):
            print(f"  ❌ 쿼리 HTTP {r.status_code}")
            return []
        return list(_csv.DictReader(StringIO(r.text)))
    except Exception as e:
        print(f"  ❌ 쿼리 예외 {type(e).__name__}: {e}")
        return []


def _save_one(table, row):
    if not API_KEY:
        print("  ❌ API_KEY 없음")
        return False
    parts = []
    for k, v in row.items():
        if v is None:
            parts.append(f"{k} = null")
        else:
            s = str(v).replace("'", "\\'")
            parts.append(f"{k} = '{s}'")
    literal = "{" + ", ".join(parts) + "}"
    escaped = literal.replace('"', '\\"')
    q = f'json "{escaped}" | import {table}'
    url = f"{BASE}?_apikey={API_KEY}&_q={urllib.parse.quote(q, safe='')}"
    try:
        r = requests.get(url, verify=False, timeout=30)
        return r.status_code == 200 and not r.text.strip().startswith("<")
    except Exception as e:
        print(f"  ❌ save 예외 {type(e).__name__}: {e}")
        return False


# ─── 자바 _getMapData (L201-215) — row 베이스 ─
def _get_map_data(operator_action_content, value, type_):
    return {
        "OPER_ACT_CTN": operator_action_content,
        "VAL": value,
        "TYP": type_,
        "JOB_STAT": "",
        "JOB_TYP": "",
        "DUE_GBN_CD": "",
        "ADMIN_USER_ID": "",
        "DEPT_NM": "",
        "JOB_SYS_ID": "",
    }


# 자바 _buildMap(String type, List queryData) (L161-173)
# 1 row 의 (k,v) 들을 펼쳐서 각자 OPER_ACT_CTN row 로
def _build_map_unpivot(type_, query_data):
    result = []
    for row in query_data:
        for k, v in row.items():
            result.append(_get_map_data(k, v, type_))
    return result


# 자바 _buildMap(content, value, type, data) (L175-199)
def _build_map_keyval(content_field, value_field, type_, query_data):
    result = []
    for row in query_data:
        c = row.get(content_field)
        v = row.get(value_field)
        if c is None or v is None:
            return []  # 자바 동일: null 발견 시 빈 리스트
        result.append(_get_map_data(str(c), str(v), type_))
    return result


class QTransferDashBoardItemBatch:
    def __init__(self):
        self.event_dt = None

    def execute(self):
        self._run()

    # 자바 _run (L51-90)
    def _run(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] QTransferDashBoardItemBatch 시작 (table={DASHBOARD_TABLE})")
        self.event_dt = datetime.now().replace(second=0, microsecond=0)

        final_list = []
        final_list.extend(self._build_requestor())             # 1) REQUESTOR
        final_list.extend(self._build_mcs_error_log_count())   # 2) WARNINGLOG
        final_list.extend(self._build_trans_que_predict_error())  # 3) ERROR

        if not final_list:
            print("  ⚠ 빌드된 대시보드 데이터 없음 (자바 동일 동작 — 종료)")
            return

        event_str = self.event_dt.strftime("%Y%m%d%H%M")
        ok = 0
        for row in final_list:
            row["EVENT_DT"] = event_str
            row["DUE_GBN_CD"] = event_str
            if _save_one(DASHBOARD_TABLE, row):
                ok += 1

        print(f"  ✅ {DASHBOARD_TABLE}: {ok}/{len(final_list)} 건 적재")

    # 자바 _buildRequestor (L107-130)
    def _build_requestor(self):
        sql = DASHBOARD_QUERIES.get("requestorCount", "")
        if not sql:
            return []
        sql = sql.replace("SEARCHSYSTEM", REQUESTOR_LIST)
        try:
            data = query(sql)
        except Exception as e:
            print(f"  ⚠ requestorCount 예외: {e}")
            return []
        return _build_map_keyval("REQUESTOR", "REQUESTOR_CNT", "REQUESTOR", data)

    # 자바 _buildMcsErrorLogCount (L132-144)
    def _build_mcs_error_log_count(self):
        sql = DASHBOARD_QUERIES.get("mcsErrorLogCnt", "")
        if not sql:
            return []
        try:
            data = query(sql)
        except Exception as e:
            print(f"  ⚠ mcsErrorLogCnt 예외: {e}")
            return []
        return _build_map_keyval("LEVEL", "CNT", "WARNINGLOG", data)

    # 자바 _buildTransQuePredictError (L146-159) — ERROR_RATE/ERROR_VALUE
    def _build_trans_que_predict_error(self):
        sql = DASHBOARD_QUERIES.get("quePredictError", "")
        if not sql:
            return []
        # 자바 quePredictError 본문은 test_currentjob_predict 를 직접 참조.
        # config 의 insert_table 이 다르면 (test_table5 등) 치환.
        insert_table = CFG["logpresso"].get("insert_table", "test_currentjob_predict")
        sql = sql.replace("test_currentjob_predict", insert_table)
        try:
            data = query(sql)
        except Exception as e:
            print(f"  ⚠ quePredictError 예외: {e}")
            return []
        # 자바 _buildMap(type, data): 1 row 의 (k,v) 들이 각자 OPER_ACT_CTN row
        # → 결과: {OPER_ACT_CTN=ERROR_VALUE, VAL=...}, {OPER_ACT_CTN=ERROR_RATE, VAL=...}
        return _build_map_unpivot("ERROR", data)


# ─── 메인 ──────────────────────────────────────
if __name__ == "__main__":
    once = "--once" in sys.argv
    batch = QTransferDashBoardItemBatch()

    if once:
        batch.execute()
        sys.exit(0)

    INTERVAL = 60
    while True:
        try:
            t0 = time.time()
            batch.execute()
            time.sleep(max(1, INTERVAL - (time.time() - t0)))
        except KeyboardInterrupt:
            print("\n중단")
            break
        except Exception as e:
            print(f"❌ 루프 예외: {e}")
            time.sleep(60)
