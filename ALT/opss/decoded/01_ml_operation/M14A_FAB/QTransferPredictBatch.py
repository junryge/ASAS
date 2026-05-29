# -*- coding: utf-8 -*-
"""
QTransferPredictBatch.py
자바 QTransferPredictBatch.java 마이그레이션.

역할 (데이터수집·예측은 이미 분리됨 → 본 배치는 통계 + 알람판정 + 통합적재):
  _run() 이 적재 테이블(test_table5)에 적재하는 행은 3종류:
    1) 실측+통계 row (N개) : qTransferGroupData 쿼리 → IDC 컬럼별 IQR/SD 계산 (_get_pivot_data)
    2) 예측 row (1개)      : TOTALCNT 행에 LSTM(예측값)/LSTM_JUDGE(10% 차이) 부여
    3) 알람 row (0~11개)   : _alarm_valid(ALARM1~5) + _build_transport_alarm(ALARM6~11)
  추가: 예측 STATE 를 한글 변환하여 대시보드 테이블 적재 (_insert_prediction_state)

자바 매핑:
  _run                  : QTransferPredictBatch.java:54-226
  _insert_prediction_state : :369-443
  _get_pivot_data       : :450-535
  _alarm_valid          : :537-1157  (ALARM1~5)
  _build_transport_alarm: :1255-1369 (ALARM6~11)
  _build_alarm_base     : :1374-1396
  통계(IQR/SD/평균)      : :1159-1237 → numpy 로 대체

실행: Prediction_ml.py 마스터가 M14A_FAB 사이트의 예측 3종 다음에 --once 로 호출.
  python QTransferPredictBatch.py --once

단계적 구현 상태:
  [완료] 골격, 헬퍼, 통계, ALARM1/2, ALARM6~11, 적재
  [대기] ALARM3/4 (Oracle/Logpresso 대체 — Phase0 후), ALARM5 (pandas 집계)
        → queries 본문이 config 에 채워지면 활성화.
"""
import os
import sys
import json
import time
import csv as _csv
import urllib.parse
import urllib3
import requests
import statistics
from io import StringIO
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── 설정/키 로드 ───────────────────────────────
def load_config():
    with open(os.path.join(SCRIPT_DIR, "qtransfer_alarm_config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_api_key():
    for p in [os.path.join(SCRIPT_DIR, "api_key.txt"),
              os.path.join(os.getcwd(), "api_key.txt")]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                line = f.read().strip().splitlines()
                if line:
                    return line[0].strip()
    return os.environ.get("LOGPRESSO_API_KEY", "")


CFG = load_config()
API_KEY = load_api_key()
HOST = CFG["logpresso"]["host"]
PORT = CFG["logpresso"]["port"]
INSERT_TABLE = CFG["logpresso"]["insert_table"]      # test_table5 (구 test_currentjob_predict)
PREDICT_TABLE = CFG["logpresso"]["predict_table"]    # test_table6 (구 ATLAS_TS_PREDICT, 예측 스크립트가 저장)
DASHBOARD_TABLE = CFG["logpresso"].get("dashboard_table", "test_table7")  # 구 qtransfer_dashboard
BASE = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv"

THRESHOLDS = CFG["thresholds"]
MESSAGES = CFG["messages"]
QUERIES = CFG["queries"]
ORACLE_CFG = CFG.get("oracle", {"enabled": False})

# 자바 _run desiredOrder (L56-77) — 컬럼 강제 정렬 순서
DESIRED_ORDER = [
    "TIME", "IDCCOL", "IDCVAL",
    "IQR_Q1", "IQR_Q2", "IQR_LOWER", "IQR_UPPER", "IQR_JUDGE",
    "AVERAGE", "STANDARDDEVIATION", "SD_LOWER", "SD_UPPER", "SD_JUDGE",
    "LSTM", "LSTM_JUDGE",
    "ALARM_CD", "ALARM_CMT", "ALARM_DESC", "ALARM_MSG_CTN", "ALARM_YN",
]


# ─── Logpresso 헬퍼 (afagg 패턴 복제) ───────────
def query(q, timeout=180):
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


def save_rows(table, rows):
    """여러 row 를 한 건씩 import (afagg save_to_logpresso 패턴)"""
    ok = 0
    for row in rows:
        if _save_one(table, row):
            ok += 1
    print(f"  ✅ {table}: {ok}/{len(rows)} 건 적재")
    return ok


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


# ─── 임계치/메시지 (자바 _findValueByCode / getMessage) ──
def find_value(code, default):
    """자바 _findValueByCode (L1736) — config thresholds 에서. 없으면 default."""
    try:
        v = THRESHOLDS.get(code)
        return float(v) if v is not None else float(default)
    except (ValueError, TypeError):
        return float(default)


def get_message(code, *args):
    """자바 XmlUtil.getMessage — {0}{1}.. 자리표시자 치환 (MessageFormat)."""
    tmpl = MESSAGES.get(code, code)
    out = tmpl
    for i, a in enumerate(args):
        out = out.replace("{" + str(i) + "}", str(a))
    return out


def collect_idc_value(rows, idc_col):
    """자바 _collectIdcValue (L1754) — rows 중 IDCCOL==idc_col 의 IDCVAL."""
    for row in rows:
        if row.get("IDCCOL") == idc_col:
            return str(row.get("IDCVAL", ""))
    return ""


# ─── 통계 (자바 _calculate* L1159-1237 → 표준 라이브러리) ─
def _vals(rows, col):
    out = []
    for r in rows:
        v = r.get(col)
        if v in (None, ""):
            continue
        try:
            out.append(float(v))
        except (ValueError, TypeError):
            pass
    return out


def calc_average(rows, col):
    a = _vals(rows, col)
    return statistics.fmean(a) if a else 0.0


def calc_std(rows, col):
    a = _vals(rows, col)
    return statistics.pstdev(a) if len(a) >= 1 else 0.0  # 자바 모집단 표준편차


def _quantile(sorted_vals, p):
    """자바 _getQuantile (L1215) — floor(index) 방식 (linear, 정렬 입력)."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo = int(idx)  # floor
    frac = idx - lo
    if lo + 1 < n:
        return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])
    return sorted_vals[lo]


def calc_iqr(rows, col):
    a = sorted(_vals(rows, col))
    if not a:
        return 0.0, 0.0, 0.0, 0.0  # q1, q3, lower, upper
    q1 = _quantile(a, 0.25)
    q3 = _quantile(a, 0.75)
    iqr = q3 - q1
    return q1, q3, q1 - 1.5 * iqr, q3 + 1.5 * iqr  # 자바 L1203/1212 계수 1.5


# ─── 알람 공통 (자바 _buildAlarmBase L1374) ─────
def _alarm_base():
    return {
        "IDCVAL": "0", "AVERAGE": "0",
        "SD_LOWER": "0", "SD_UPPER": "0", "SD_JUDGE": "F", "STANDARDDEVIATION": "0",
        "IQR_Q1": "0", "IQR_Q2": "0", "IQR_LOWER": "0", "IQR_UPPER": "0", "IQR_JUDGE": "0",
        "ALARM_CD": "", "ALARM_YN": "Y",
    }


class QTransferPredictBatch:
    def __init__(self):
        self.event_dt = None  # 자바 eventDataTime

    def execute(self):
        self._run()

    # 자바 _run (L54-226)
    def _run(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] QTransferPredictBatch 시작")
        self.event_dt = datetime.now().replace(second=0, microsecond=0)

        # 1) ALARM6~11 (예측값 무관, 자바는 _run 초반에 호출 L86)
        monitoring = self._build_transport_alarm()

        # 2) 예측값 조회 (예측 스크립트가 PREDICT_TABLE 에 저장한 최신값)
        prediction_map = self._fetch_prediction()
        prediction = None
        if prediction_map and prediction_map.get("LSTM") not in (None, ""):
            try:
                prediction = float(prediction_map["LSTM"])
            except (ValueError, TypeError):
                prediction = None

        if prediction is not None:
            # 3) 대시보드 상태 적재 (자바 _insertPredictionState L115)
            self._insert_prediction_state(prediction_map)
            # 4) 실측통계 + 알람 (자바 _getPivotData L118)
            monitoring.extend(self._get_pivot_data(prediction))

        # 5) 컬럼 정렬 + LSTM_JUDGE + 반올림 (자바 L130-212)
        reordered = self._reorder_and_finalize(monitoring, prediction, prediction_map)

        # 6) 적재
        if reordered:
            save_rows(INSERT_TABLE, reordered)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 완료 ({len(reordered)}행)")

    # ── 예측값 조회 ──
    def _fetch_prediction(self):
        """예측 스크립트가 PREDICT_TABLE(test_table2)에 저장한 최신 LSTM/STATE/STATE_PER 조회.
           default 모델(10m, V8.3.1_Q_TRANSFER_PREDICTOR_10m.py) 기준."""
        q = (f'table from=dateadd(now(),"min",-5) to=now() {PREDICT_TABLE} '
             f'| sort -TIME | limit 1')
        rows = query(q)
        return rows[0] if rows else {}

    # 자바 _insertPredictionState (L369-443)
    def _insert_prediction_state(self, prediction_map):
        state = prediction_map.get("STATE")
        if state is None:
            print("  ⏭  STATE 없음 — 대시보드 적재 스킵")
            return
        state_per = prediction_map.get("STATE_PER")
        try:
            occurrence = float(state_per) if state_per is not None else 0.0
        except (ValueError, TypeError):
            occurrence = 0.0

        kor = {"NORMAL": "정상", "CAUTION": "주의", "CRITICAL": "심각"}.get(state, state)
        event_str = self.event_dt.strftime("%Y%m%d%H%M")
        data = {
            "OPER_ACT_CTN": kor, "VAL": occurrence, "TYP": "STATE",
            "JOB_STAT": "", "JOB_TYP": "", "DUE_GBN_CD": event_str,
            "ADMIN_USER_ID": "", "DEPT_NM": "", "JOB_SYS_ID": "",
            "EVENT_DT": event_str,
        }
        _save_one(DASHBOARD_TABLE, data)

    # 자바 _getPivotData (L450-535)
    def _get_pivot_data(self, prediction):
        result = []
        rows = query(QUERIES.get("qTransferGroupData", ""))
        if not rows:
            print("  ⏭  qTransferGroupData 비어있음 — 통계/ALARM1~5 스킵")
            return result

        latest = rows[0]
        for idc_col, idc_val in latest.items():
            if idc_col.upper() in ("CURRTIME", "TIME", "UID"):
                continue
            try:
                cur = float(idc_val)
            except (ValueError, TypeError):
                continue

            avg = calc_average(rows, idc_col)
            q1, q3, iqr_lo, iqr_hi = calc_iqr(rows, idc_col)
            iqr_judge = "T" if (cur < iqr_lo or cur > iqr_hi) else "F"
            std = calc_std(rows, idc_col)
            sd_lo, sd_hi = avg - 3 * std, avg + 3 * std
            sd_judge = "T" if (cur < sd_lo or cur > sd_hi) else "F"

            result.append({
                "TIME": latest.get("TIME"),
                "IDCCOL": idc_col, "IDCVAL": idc_val, "AVERAGE": avg,
                "IQR_Q1": q1, "IQR_Q2": q3, "IQR_LOWER": iqr_lo, "IQR_UPPER": iqr_hi,
                "IQR_JUDGE": iqr_judge,
                "STANDARDDEVIATION": std, "SD_LOWER": sd_lo, "SD_UPPER": sd_hi,
                "SD_JUDGE": sd_judge,
            })

        # ALARM1~5
        result.extend(self._alarm_valid(result, prediction))
        return result

    # 자바 _alarmValid (L537-1157) — ALARM1~5
    def _alarm_valid(self, origin, prediction):
        alarms = []
        req_limit = find_value("QTRANSFER_LIMIT", 1700)
        increase_rate = find_value("QTRANSFER_INCREASE_RATE", 10)
        vhl_limit = find_value("VHL_RATE_LIMIT", 95)
        cnv_down_limit = find_value("QTRANSFER_CNV_PORT_DOWN_RATE", 10)
        current_total = collect_idc_value(origin, "TOTALCNT")

        if prediction is None or prediction <= req_limit:
            return alarms  # 자바 L579: 임계 미만이면 알람 없음

        # ── ALARM1: VHL 가동률 & MES 큐 증가 ──
        try:
            vhl_rows = query(QUERIES.get("vhlRunRate", ""))
            oht_rate = ""
            for r in vhl_rows:
                if r.get("CARRIERTYPE") == "FOUP":
                    oht_rate = str(r.get("VHLOPERRATE", ""))
                    break
            vhl_flag = oht_rate not in ("",) and float(oht_rate.split(",")[0]) >= vhl_limit

            mes_q = QUERIES.get("mesOHTQCntAlarmValid", "")
            v24 = query(mes_q.replace("duration=1m", "duration=24h"))
            v10 = query(mes_q.replace("duration=1m", "duration=24h").replace("duration=24h", "duration=10m"))
            done = query(QUERIES.get("completedTsJobCountPerMin", ""))
            done_val = done[0].get("MINPER_CNT", "") if done else ""
            v24v = float(v24[0]["MESSAGE_COUNT"]) if v24 else 0.0
            v10v = float(v10[0]["MESSAGE_COUNT"]) if v10 else 0.0
            pct = ((v10v - v24v) / v24v * 100) if v24v else 0.0
            mes_flag = pct > increase_rate

            if vhl_flag and mes_flag:
                a = _alarm_base()
                a["IDCCOL"] = "QTRANSFER_ALARM1"
                a["ALARM_DESC"] = get_message("QTRANSFER_REQ_TITLE")
                a["ALARM_CMT"] = get_message("QTRANSFER_REQ_SUB_TITLE")
                a["ALARM_MSG_CTN"] = get_message("QTRANSFER_REQ_CONTENT",
                                                 int(prediction), int(req_limit), oht_rate,
                                                 int(v10v), int(v24v), current_total, done_val)
                alarms.append(a)
        except Exception as e:
            print(f"  ⚠ ALARM1 스킵: {e}")

        # ── ALARM2: CNV 반송 증가 & 포트 정상 ──
        try:
            tc = QUERIES.get("transferCountPerMin", "")
            t10 = query(tc)
            t24 = query(tc.replace("duration=10m", "duration=24h"))
            cnv_down = query(QUERIES.get("bridgeDetailCnvPortDownRate", ""))
            m14a16_10 = collect_idc_value(t10, "M14AM16SUM")
            m14a16_24 = collect_idc_value(t24, "M14AM16SUM")
            m14_16_10 = collect_idc_value(t10, "M14AM16")
            m14_16_24 = collect_idc_value(t24, "M14AM16")
            m16_14_10 = collect_idc_value(t10, "M16M14A")
            m16_14_24 = collect_idc_value(t24, "M16M14A")
            v10i = int(m14a16_10.split(",")[0]) if m14a16_10 else 0
            v24i = int(m14a16_24.split(",")[0]) if m14a16_24 else 0
            pct2 = ((v10i - v24i) / v24i * 100) if v24i else 0.0
            cnv_cnt_flag = pct2 > increase_rate
            cnv_rate = float(cnv_down[0]["PORT_DOWN_RATE"]) if cnv_down else 100.0
            cnv_down_flag = cnv_rate < cnv_down_limit

            if cnv_cnt_flag and cnv_down_flag:
                storage = self._oracle_storage_util()
                a = _alarm_base()
                a["IDCCOL"] = "QTRANSFER_ALARM2"
                a["ALARM_DESC"] = get_message("QTRANSFER_CNV_TITLE")
                a["ALARM_CMT"] = get_message("QTRANSFER_CNV_SUB_TITLE")
                a["ALARM_MSG_CTN"] = get_message("QTRANSFER_CNV_CONTENT",
                                                 int(prediction), int(req_limit),
                                                 m14_16_10, m14_16_24, m16_14_10, m16_14_24,
                                                 current_total, storage, "")
                alarms.append(a)
        except Exception as e:
            print(f"  ⚠ ALARM2 스킵: {e}")

        # ── ALARM3: M14↔M10A LFT 반송 10%↑ & LFT 다운율 < 25% (자바 L658-1040) ──
        try:
            m10_down_limit = find_value("QTRANSFER_M14TOM10_PORT_DOWN_RATE", 25)
            m10_10 = collect_idc_value(t10, "M14AM10ASUM")
            m10_24 = collect_idc_value(t24, "M14AM10ASUM")
            m14_10a_10 = collect_idc_value(t10, "M14AM10A")
            m14_10a_24 = collect_idc_value(t24, "M14AM10A")
            m10_14_10 = collect_idc_value(t10, "M10AM14A")
            m10_14_24 = collect_idc_value(t24, "M10AM14A")
            v10m = int(m10_10.split(",")[0]) if m10_10 else 0
            v24m = int(m10_24.split(",")[0]) if m10_24 else 0
            pct3 = ((v10m - v24m) / v24m * 100) if v24m else 0.0
            m14_to_m10_flag = pct3 > increase_rate
            # LFT 다운율 (dbquery Oracle)
            lft_down = self._oracle_query("SELECT_M14TOM10LFT_DOWN_RATE", "PORT_DOWN_RATE")
            lft_down_val = float(lft_down) if lft_down else 100.0
            m10_down_flag = lft_down_val < m10_down_limit

            if m14_to_m10_flag and m10_down_flag:
                storage = self._oracle_storage_util()
                inservice = round(100.0 - lft_down_val, 2)
                a = _alarm_base()
                a["IDCCOL"] = "QTRANSFER_ALARM3"
                a["ALARM_CMT"] = "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."
                a["ALARM_DESC"] = "M10A ↔ M14A FAB간 반송 큐 개수 다량 증가"
                a["ALARM_MSG_CTN"] = get_message("QTRANSFER_M14TOM10_LFT",
                                                 "10", int(prediction), int(req_limit),
                                                 m10_14_10, m10_14_24, m14_10a_10, m14_10a_24,
                                                 lft_down, current_total, storage, "", inservice)
                alarms.append(a)
        except Exception as e:
            print(f"  ⚠ ALARM3 스킵: {e}")

        # ── ALARM4: M14↔M14B LFT 반송 10%↑ & LFT 다운율 < 10% (자바 L1042-1106) ──
        try:
            m14b_down_limit = find_value("QTRANSFER_M14LFT_PORT_DOWN_RATE", 10)
            m14b_10 = collect_idc_value(t10, "M14AM14BSUM")
            m14b_24 = collect_idc_value(t24, "M14AM14BSUM")
            m14a_14b_10 = collect_idc_value(t10, "M14AM14B")
            m14a_14b_24 = collect_idc_value(t24, "M14AM14B")
            m14b_14a_10 = collect_idc_value(t10, "M14BM14A")
            m14b_14a_24 = collect_idc_value(t24, "M14BM14A")
            v10b = int(m14b_10.split(",")[0]) if m14b_10 else 0
            v24b = int(m14b_24.split(",")[0]) if m14b_24 else 0
            pct4 = ((v10b - v24b) / v24b * 100) if v24b else 0.0
            m14b_cnt_flag = pct4 > increase_rate
            lft_down2 = self._oracle_query("SELECT_M14LFT_DOWN_RATE", "PORT_DOWN_RATE")
            lft_down2_val = float(lft_down2) if lft_down2 else 100.0
            m14b_down_flag = lft_down2_val < m14b_down_limit

            if m14b_cnt_flag and m14b_down_flag:
                storage = self._oracle_storage_util()
                inservice2 = round(100.0 - lft_down2_val, 2)
                a = _alarm_base()
                a["IDCCOL"] = "QTRANSFER_ALARM4"
                a["ALARM_CMT"] = "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."
                a["ALARM_DESC"] = "M14A ↔ M14B FAB간 반송 큐 개수 다량 증가"
                a["ALARM_MSG_CTN"] = get_message("QTRANSFER_M14ATOM14B_LFT",
                                                 "10", int(prediction), int(req_limit),
                                                 m14b_14a_10, m14b_14a_24, m14a_14b_10, m14a_14b_24,
                                                 lft_down2, current_total, storage, "", inservice2)
                alarms.append(a)
        except Exception as e:
            print(f"  ⚠ ALARM4 스킵: {e}")

        # ── ALARM5 : JOB STATE ERROR/ALT 50%↑ & 동일장비 50%↑ (자바 L757-940) ──
        try:
            alarm5 = self._build_alarm5(prediction, req_limit, current_total)
            if alarm5:
                alarms.append(alarm5)
        except Exception as e:
            print(f"  ⚠ ALARM5 스킵: {e}")

        return alarms

    # 자바 ALARM5 (L757-940) — ALT JOB 집계
    def _build_alarm5(self, prediction, req_limit, current_total):
        from collections import defaultdict

        alt_job_limit = find_value("QTRANSFER_ALT_JOB_LIMIT", 50)
        alt_job_machine_rate = find_value("QTRANSFER_ALT_JOB_MACHINE_RATE", 50)

        today = self.event_dt.strftime("%Y%m%d")
        yesterday = (self.event_dt - timedelta(days=1)).strftime("%Y%m%d")

        # 1) qtransferAltJobCnt → INCREASE_RATE > 50 ?
        q6 = QUERIES.get("qtransferAltJobCnt", "").replace("START_DT", yesterday).replace("END_DT", today)
        alt_cnt = query(q6)
        if not alt_cnt:
            return None
        try:
            increase_rate = float(alt_cnt[0].get("INCREASE_RATE", 0))
        except (ValueError, TypeError):
            return None

        if increase_rate <= alt_job_limit:
            return None  # 자바: altJobLimitFlag=false → 알람 없음

        # 2) altJobMachineRate → RATE_DT >= 50% 인 장비/상태
        state_rate_msg = ""
        machine_rate_msg = ""
        state_mapping_machine = ""
        msg_idx = 2

        q7 = QUERIES.get("altJobMachineRate", "").replace("START_DT", yesterday).replace("END_DT", today)
        mrate = query(q7)
        if mrate:
            def fnum(v):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return 0.0

            filtered = [m for m in mrate if fnum(m.get("RATE_DT")) >= alt_job_machine_rate]
            if filtered:
                f_machines = {m.get("MACHINENAME") for m in filtered}
                f_states = {m.get("STATE") for m in filtered}

                # 장비별/상태별 CNT 합 (자바 groupingBy + summingInt)
                machine_cnt = defaultdict(int)
                state_cnt = defaultdict(int)
                for m in mrate:
                    try:
                        c = int(float(m.get("CNT", 0)))
                    except (ValueError, TypeError):
                        c = 0
                    if m.get("MACHINENAME") in f_machines:
                        machine_cnt[m.get("MACHINENAME")] += c
                    if m.get("STATE") in f_states:
                        state_cnt[m.get("STATE")] += c

                # STATE[MACHINE] 매핑
                state_machine = defaultdict(list)
                for m in mrate:
                    s, mc = m.get("STATE"), m.get("MACHINENAME")
                    if s in f_states and mc in f_machines and mc not in state_machine[s]:
                        state_machine[s].append(mc)
                state_mapping_machine = ",".join(f"{s}[{','.join(ms)}]" for s, ms in state_machine.items())

                machine_list = ",".join(f'"{m}"' for m in machine_cnt)  # "M1","M2"
                state_list = ",".join(f'"{s}"' for s in state_cnt)

                # 3) 24h 평균 — 장비별
                q72 = (QUERIES.get("altJobMachineRate24h", "")
                       .replace("START_DT", yesterday).replace("END_DT", today)
                       .replace("MACHINELIST", machine_list))
                m24 = query(q72)
                m24map = {r.get("MACHINENAME"): r.get("DAY_CNT") for r in m24}

                # 24h 평균 — 상태별
                q73 = (QUERIES.get("qtransferAltJobCnt24h", "")
                       .replace("START_DT", yesterday).replace("END_DT", today)
                       .replace("STATELIST", state_list))
                s24 = query(q73)
                s24map = {r.get("STATE"): r.get("AVG_VAL") for r in s24}

                # 메시지 동적 생성 (자바 L915-935)
                for st, cnt in state_cnt.items():
                    state_rate_msg += f"{msg_idx}. 1시간 {st} 상태 반송큐 수: {cnt}개 (전일 평균 {s24map.get(st, '')}개)\\n \n        "
                    msg_idx += 1
                for mc, cnt in machine_cnt.items():
                    machine_rate_msg += f"{msg_idx}. 1시간 {mc} 장비 반송큐 수: {cnt}개 (전일 평균 {m24map.get(mc, '')}개)\\n \n        "
                    msg_idx += 1

        # altJobLimitFlag=true 면 무조건 알람 발생 (자바 altJobMachineStateFlag=true)
        a = _alarm_base()
        a["IDCCOL"] = "QTRANSFER_ALARM5"
        # 자바: ALARM5 는 별도 title/subtitle 없이 ALT_JOB content 만 (인라인). 메시지 코드 사용.
        a["ALARM_DESC"] = ""
        a["ALARM_CMT"] = "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."
        a["ALARM_MSG_CTN"] = get_message(
            "QTRANSFER_ALT_JOB",
            "10",                       # 0: predictOutput
            int(prediction),            # 1
            int(req_limit),             # 2
            state_rate_msg,             # 3
            machine_rate_msg,           # 4
            current_total,              # 5
            "",                         # 6: JOB STATE별
            "",                         # 7: VHL 가동률
            state_mapping_machine,      # 8: STATE[MACHINE]
            "",                         # 9: 장비
        )
        return a

    def _oracle_query(self, query_id, col):
        """ALARM2/3/4 의 Oracle 값 1개 조회. dbquery 로 Logpresso httpexport 경유 (oracledb 불필요).
           query_id: oracle.queries 의 키. col: 가져올 컬럼명."""
        if not ORACLE_CFG.get("enabled"):
            return ""
        sql = ORACLE_CFG.get("queries", {}).get(query_id, "")
        if not sql:
            return ""
        rows = query(sql)  # 'dbquery mcs_m14a SELECT ...' 형태
        if rows and col in rows[0]:
            return str(rows[0].get(col, ""))
        return ""

    def _oracle_storage_util(self):
        """ALARM2/3/4 의 M16A STORAGE_UTIL (CURR_VAL). dbquery Oracle."""
        return self._oracle_query("SELECT_M16A_STORAGE_UTIL", "CURR_VAL")

    # 자바 _buildTransportAlarm (L1255-1369) — ALARM6~11
    def _build_transport_alarm(self):
        result = []
        idc_rows = query(QUERIES.get("SELECT_AWS_IDC_HISTORY", ""))
        if not idc_rows:
            return result
        idc = idc_rows[0]

        def add(idc_col, title_c, sub_c, content_c, cur, *bound):
            a = _alarm_base()
            a["IDCCOL"] = idc_col
            a["ALARM_DESC"] = get_message(title_c, cur)
            a["ALARM_CMT"] = get_message(sub_c, *bound) if bound else get_message(sub_c, cur)
            a["ALARM_MSG_CTN"] = get_message(content_c, cur, *bound)
            result.append(a)

        def fval(key):
            try:
                return float(idc.get(key))
            except (ValueError, TypeError):
                return None

        # ALARM6: Normal STB Storage 부하 >= 95
        v = fval("M14.STRATE.NONN2.STORAGERATIO")
        b = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_6", 95)
        if v is not None and v >= b:
            add("QTRANSFER_ALARM6", "NORMAL_STB_STORAGE_LOAD_TITLE",
                "NORMAL_STB_STORAGE_LOAD_SUB_TITLE", "NORMAL_STB_STORAGE_LOAD_CONTENT", v, b)

        # ALARM7: Sorter Wait Count >= 100
        v = fval("M14.SORTER.ABN.SORTERWAITCOUNTOVER")
        b = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_7", 100)
        if v is not None and v >= b:
            add("QTRANSFER_ALARM7", "SORTER_WAIT_COUNT_OVER_TITLE",
                "SORTER_WAIT_COUNT_OVER_SUB_TITLE", "SORTER_WAIT_COUNT_OVER_CONTENT", v, b)

        # ALARM8: Cu Sorter Wait Count >= 100
        v = fval("M14.SORTER.ABN.CUSORTERWAITCOUNTOVER")
        b = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_8", 100)
        if v is not None and v >= b:
            add("QTRANSFER_ALARM8", "CU_SORTER_WAIT_COUNT_OVER_TITLE",
                "CU_SORTER_WAIT_COUNT_OVER_SUB_TITLE", "CU_SORTER_WAIT_COUNT_OVER_CONTENT", v, b)

        # ALARM9: Q-COMPLETED >= 2700
        v = fval("M14.QUE.ALL.CURRENTQCOUNT")
        b = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_9", 2700)
        if v is not None and v >= b:
            add("QTRANSFER_ALARM9", "Q_COMPLETED_UNDER_AVERAGE_TITLE",
                "Q_COMPLETED_UNDER_AVERAGE_SUB_TITLE", "Q_COMPLETED_UNDER_AVERAGE_CONTENT", v, b)

        # ALARM10: Total Que >= 1700 & Manual Out >= 200
        v1 = fval("M14.QUE.ALL.CURRENTQCNT")
        v2 = fval("M14.QUE.STK.MANUALOUTCOUNT")
        b1 = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_10_1", 1700)
        b2 = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_10_2", 200)
        if v1 is not None and v2 is not None and v1 >= b1 and v2 >= b2:
            a = _alarm_base()
            a["IDCCOL"] = "QTRANSFER_ALARM10"
            a["ALARM_DESC"] = get_message("TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_TITLE", v1)
            a["ALARM_CMT"] = get_message("TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_SUB_TITLE", v1, v2)
            a["ALARM_MSG_CTN"] = get_message("TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_CONTENT", v1, b1, v2, b2)
            result.append(a)

        # ALARM11: 층간 대기 QUE >= 500 & STB 부하 >= 97
        v1 = fval("M14.QUE.SENDFAB.VERTICALQUEUECOUNT")
        v2 = fval("M14.STRATE.STB.NONN2STORAGERATIO")
        b1 = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_11_1", 500)
        b2 = find_value("Q_TRANSFER_BOUNDARY_DEFAULT_11_2", 97)
        if v1 is not None and v2 is not None and v1 >= b1 and v2 >= b2:
            a = _alarm_base()
            a["IDCCOL"] = "QTRANSFER_ALARM11"
            a["ALARM_DESC"] = get_message("WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_TITLE", v1)
            a["ALARM_CMT"] = get_message("WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_SUB_TITLE", v1, v2)
            a["ALARM_MSG_CTN"] = get_message("WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_CONTENT", v1, b1, v2, b2)
            result.append(a)

        return result

    # 자바 _run L130-212 (정렬 + LSTM_JUDGE + 반올림 + TIME)
    def _reorder_and_finalize(self, rows, prediction, prediction_map):
        event_str = self.event_dt.strftime("%Y%m%d%H%M")
        reordered = []
        for entry in rows:
            r = {k: entry.get(k) for k in DESIRED_ORDER}
            idc = r.get("IDCCOL")
            if idc is None:
                continue

            # TOTALCNT 행에 LSTM/LSTM_JUDGE (자바 L156-190)
            if idc == "TOTALCNT" and prediction is not None:
                idcval = r.get("IDCVAL")
                try:
                    iv = float(idcval)
                    pct = abs((iv - prediction) / iv) * 100 if iv else 0.0
                    r["LSTM_JUDGE"] = "Y" if pct >= 10 else "N"
                except (ValueError, TypeError):
                    r["LSTM_JUDGE"] = "N"
                # 예측 메타 병합 (LSTM/STATE/STATE_PER/TIME)
                for k, v in (prediction_map or {}).items():
                    if k in DESIRED_ORDER or k in ("LSTM", "STATE", "STATE_PER"):
                        r[k] = v
            else:
                r.setdefault("LSTM", "")
                r["LSTM_JUDGE"] = "N"

            # 소수점 2자리 반올림 (자바 L194-204)
            for k, v in list(r.items()):
                if isinstance(v, float):
                    r[k] = round(v * 100.0) / 100.0
            r["TIME"] = event_str
            reordered.append(r)
        return reordered


# ─── 메인 ──────────────────────────────────────
if __name__ == "__main__":
    once = "--once" in sys.argv
    batch = QTransferPredictBatch()

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
