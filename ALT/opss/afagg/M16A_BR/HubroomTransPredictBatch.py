# -*- coding: utf-8 -*-
"""
HubroomTransPredictBatch.py
자바 HubroomTransPredictBatch.java 의 _validWarnYN 로직 마이그레이션.

역할 (자바에서 데이터수집·예측은 이미 분리됨 → 본 배치는 WARN_YN 판정만):
  - Numerical 예측 스크립트(V8_Numerical_Real_time_*.py)가 test_hubroom_predict 에
    이미 JUDGEVAL 과 함께 저장한 최신 예측을 조회
  - 직전 예측의 JUDGEVAL 과 비교하여 WARN_YN 판정
      · 직전 JUDGEVAL=1 && 현재 JUDGEVAL=1  → WARN_YN="Y" (연속 2회 위험)
      · 그 외                              → WARN_YN="N"
  - test_hubroom_predict 에 WARN_YN 반영하여 갱신 적재

자바 매핑: _validWarnYN (HubroomTransPredictBatch.java:114-177)

실행: Prediction_ml.py 마스터가 M16A_BR 사이트의 예측 6종 다음에 --once 로 호출.
  python HubroomTransPredictBatch.py --once

주의: errorVhlVal / VHL_OFF_PLUS_DATA 는 CSV 생성(data_make) 단계 로직이라
      본 배치와 무관 (M16BR_hubroom_data_make.py 담당).
"""
import os
import sys
import json
import time
import urllib.parse
import urllib3
import requests
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── 설정 로드 ─────────────────────────────────
def load_config():
    path = os.path.join(SCRIPT_DIR, "hubroom_alarm_config.json")
    with open(path, encoding="utf-8") as f:
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
INSERT_TABLE = CFG["logpresso"]["insert_table"]
BASE = f"http://{HOST}:{PORT}/logpresso/httpexport/query.csv"
FLOWS = CFG["flows"]
PREV_QUERY_TMPL = CFG["prev_judgeval_query"]


# ─── Logpresso 조회 (afagg query() 패턴 복제) ──
def query(q, timeout=60):
    """Logpresso httpexport 쿼리 → list[dict]"""
    qs = " ".join(q.split())
    url = f"{BASE}?_apikey={API_KEY}&_q={urllib.parse.quote(qs, safe='')}"
    try:
        r = requests.get(url, verify=False, timeout=timeout)
        if r.status_code != 200 or r.text.strip().startswith("<"):
            print(f"  ❌ 쿼리 HTTP {r.status_code}")
            return []
        import csv as _csv
        from io import StringIO
        reader = _csv.DictReader(StringIO(r.text))
        return list(reader)
    except Exception as e:
        print(f"  ❌ 쿼리 예외 {type(e).__name__}: {e}")
        return []


# ─── Logpresso 저장 (afagg save_to_logpresso() 패턴 복제) ──
def save_to_logpresso(table, row):
    if not API_KEY:
        print("❌ API_KEY 없음")
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
        if r.status_code == 200 and not r.text.strip().startswith("<"):
            print(f"  ✅ Logpresso 저장 ({table})")
            return True
        print(f"  ❌ HTTP {r.status_code} | {r.text[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return False


# ─── WARN_YN 판정 (자바 _validWarnYN L143-169 이식) ──
def _valid_warn_yn(cur_judgeval, prev_judgeval):
    """
    자바 _validWarnYN 의 JUDGEVAL 분기 1:1 이식.
      prev < 2 인 경우만 처리 (0,1 만 유효):
        prev=0                 → WARN_YN="N"
        prev=1 && cur=0        → WARN_YN="N"
        prev=1 && cur=1        → WARN_YN="Y"  (연속 2회 위험)
      그 외                    → WARN_YN="N"
    """
    if prev_judgeval is None:
        return "N"  # 최초 등록 — 직전 없음
    try:
        prev = int(prev_judgeval)
    except (ValueError, TypeError):
        return "N"

    if prev >= 2:
        return "N"
    if prev == 1 and str(cur_judgeval) == "1":
        return "Y"
    return "N"


class HubroomTransPredictBatch:
    def execute(self):
        self._run()

    def _run(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] HubroomTransPredictBatch 시작 ({len(FLOWS)}개 FLOW)")

        event_dt = datetime.now().replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:00")

        for flow in FLOWS:
            try:
                self._process_flow(flow, event_dt)
            except Exception as e:
                print(f"  ❌ [{flow}] 예외 {type(e).__name__}: {e}")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] HubroomTransPredictBatch 완료")

    def _process_flow(self, flow, event_dt):
        # 1) 현재(최신) 예측 조회 — 예측 스크립트가 직전에 저장한 최신 row
        cur_q = (f'table from=dateadd(now(),"min",-30) to=now() {INSERT_TABLE} '
                 f'| search FLOW == "{flow}" | sort -EVENT_DT | limit 1')
        cur_rows = query(cur_q)
        if not cur_rows:
            print(f"  ⏭  [{flow}] 현재 예측 없음 — 스킵")
            return
        cur = cur_rows[0]
        cur_judgeval = cur.get("JUDGEVAL")

        # 2) 직전 예측 JUDGEVAL 조회 (현재 row 직전 것 = limit 1 offset 1 효과 → 2개 받아 두번째)
        prev_q = (f'table from=dateadd(now(),"min",-30) to=now() {INSERT_TABLE} '
                  f'| search FLOW == "{flow}" | sort -EVENT_DT | limit 2')
        prev_rows = query(prev_q)
        prev_judgeval = None
        if len(prev_rows) >= 2:
            prev_judgeval = prev_rows[1].get("JUDGEVAL")

        # 3) WARN_YN 판정 (자바 _validWarnYN)
        warn_yn = _valid_warn_yn(cur_judgeval, prev_judgeval)

        # 4) 갱신 row 적재 (현재 예측 + WARN_YN/FLOW/EVENT_DT)
        out = dict(cur)
        out["FLOW"] = flow
        out["WARN_YN"] = warn_yn
        out["EVENT_DT"] = event_dt
        # 내부 메타 컬럼 제거 (_time, _id 등 Logpresso 자동 컬럼)
        for meta in ("_time", "_id"):
            out.pop(meta, None)

        print(f"  [{flow}] cur_judge={cur_judgeval} prev_judge={prev_judgeval} → WARN_YN={warn_yn}")
        save_to_logpresso(INSERT_TABLE, out)


# ─── 메인 ──────────────────────────────────────
if __name__ == "__main__":
    once = "--once" in sys.argv
    batch = HubroomTransPredictBatch()

    if once:
        batch.execute()
        sys.exit(0)

    # 단독 실행 시(디버그용) 매분 정각 — 운영은 Prediction_ml.py 가 호출
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
