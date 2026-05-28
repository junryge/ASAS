# -*- coding: utf-8 -*-
"""
Rule_LO.py — Logpresso 적재기 (hubroom_predictor v4.1 발동이벤트)
=================================================================
패턴: M14A_FAB_data_make.py 와 동일 방식
  - API key: api_key.txt (1줄)
  - 설정: config.json
  - 엔드포인트: http://HOST:PORT/logpresso/httpexport/query.csv
  - 인증: ?_apikey=XXX 쿼리 파라미터

사용 (hubroom_predictor.py 에서 import):
    import Rule_LO
    Rule_LO.start()
    Rule_LO.upload(EVENT_FIELDS, row_values)   # 매 이벤트
    Rule_LO.stop()

저장 방식:
  Logpresso 쿼리 `import csvtbl ... | savetbl test_table3` 형식.
  CSV 한 줄을 inputtxt 로 넣고 savetbl 로 적재.
"""
import json
import logging
import os
import queue
import sys
import threading
import time
import urllib.parse
import urllib3
from io import StringIO

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# 로깅
# ============================================================
log = logging.getLogger("Rule_LO")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [Rule_LO] %(message)s"))
    log.addHandler(h)


# ============================================================
# 설정 로드 (config.json + api_key.txt)
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_config():
    """config.json 로드. 없으면 안전한 기본값."""
    path = os.path.join(_HERE, "config.json")
    if not os.path.exists(path):
        log.warning(f"config.json 없음 ({path}) — 기본값 사용 (비활성)")
        return {"enabled": False}
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    except Exception as e:
        log.error(f"config.json 파싱 실패: {e}")
        return {"enabled": False}


def _load_api_key(key_file_name):
    """api_key.txt 로드 (1줄). M14A_FAB_data_make.py 동일 패턴."""
    for p in [os.path.join(_HERE, key_file_name),
              os.path.join(os.getcwd(), key_file_name)]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read().strip().splitlines()[0].strip()
    log.warning(f"{key_file_name} 없음 — 인증 실패 가능")
    return ""


CFG = _load_config()
API_KEY = _load_api_key(CFG.get("api_key_file", "api_key.txt")) if CFG.get("enabled") else ""

LOGPRESSO_BASE = CFG.get("logpresso_base", "http://localhost:8888/logpresso")
TABLE_NAME     = CFG.get("table_name", "test_table3")
FILE_LABEL     = CFG.get("file_label", "Rule_system")
ENABLED        = bool(CFG.get("enabled", False))
ASYNC_UPLOAD   = bool(CFG.get("async_upload", True))
QUEUE_MAX      = int(CFG.get("queue_max_size", 10000))
BATCH_SIZE     = int(CFG.get("batch_size", 50))
RETRY_ON_FAIL  = int(CFG.get("retry_on_fail", 3))
RETRY_BACKOFF  = float(CFG.get("retry_backoff", 1.0))
LOG_EVERY_N    = int(CFG.get("log_every_n", 60))
FAIL_SILENT    = bool(CFG.get("fail_silent", True))
HTTP_TIMEOUT   = int(CFG.get("http_timeout", 30))

INSERT_PATH    = CFG.get("_endpoints", {}).get("insert", "/httpexport/query.csv")
INSERT_URL     = LOGPRESSO_BASE.rstrip("/") + INSERT_PATH


# ============================================================
# 내부 상태
# ============================================================
_queue: "queue.Queue" = None
_worker_thread = None
_stop_flag = threading.Event()
_count = 0
_fail_count = 0


# ============================================================
# CSV 직렬화 (Logpresso inputtxt 용)
# ============================================================
def _csv_escape(v):
    """CSV 값 1개 escape. None → ''. 쉼표/따옴표/줄바꿈 처리."""
    if v is None:
        return ""
    s = str(v)
    if any(c in s for c in [',', '"', '\n', '\r']):
        s = '"' + s.replace('"', '""') + '"'
    return s


def _rows_to_csv(fields, rows):
    """헤더 + 데이터 행을 단일 CSV 문자열로."""
    buf = StringIO()
    buf.write(",".join(_csv_escape(f) for f in fields))
    buf.write("\n")
    for row in rows:
        buf.write(",".join(_csv_escape(v) for v in row))
        buf.write("\n")
    return buf.getvalue()


# ============================================================
# Logpresso 쿼리 (inputtxt + eval(file 하드코딩) + savetbl)
# ============================================================
def _build_query(csv_text):
    """Logpresso 쿼리 작성. inputtxt 로 csv 받아 file 컬럼 덮어쓰고 테이블에 저장."""
    # Logpresso 쿼리 안에서 큰 따옴표 escape (역슬래시)
    csv_esc = csv_text.replace("\\", "\\\\").replace('"', '\\"')
    q = (
        f'inputtxt "{csv_esc}" delim="," tab=t '
        f'| eval file="{FILE_LABEL}" '
        f'| savetbl {TABLE_NAME}'
    )
    return q


def _post_query(q):
    """Logpresso 쿼리 실행. M14A_FAB 패턴 그대로 (GET + URL 인코딩)."""
    qs = " ".join(q.split())
    url = f"{INSERT_URL}?_apikey={API_KEY}&_q={urllib.parse.quote(qs, safe='')}"
    r = requests.get(url, verify=False, timeout=HTTP_TIMEOUT)
    if r.status_code != 200 or r.text.strip().startswith("<"):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r


# ============================================================
# 전송 (재시도 포함)
# ============================================================
def _send_batch(fields, rows):
    """배치 행을 Logpresso 로 전송. 성공 True / 실패 False."""
    csv_text = _rows_to_csv(fields, rows)
    q = _build_query(csv_text)
    last_err = None
    for attempt in range(RETRY_ON_FAIL):
        try:
            _post_query(q)
            return True
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    log.warning(f"적재 실패 (재시도 {RETRY_ON_FAIL}회): {type(last_err).__name__}: {last_err}")
    return False


# ============================================================
# 비동기 워커
# ============================================================
def _worker():
    """큐에서 배치로 꺼내 전송. 종료 신호 받으면 남은 큐 flush 후 종료."""
    global _count, _fail_count
    while not _stop_flag.is_set() or (_queue and not _queue.empty()):
        batch = []
        try:
            batch.append(_queue.get(timeout=1.0))
        except queue.Empty:
            continue
        while len(batch) < BATCH_SIZE:
            try:
                batch.append(_queue.get_nowait())
            except queue.Empty:
                break
        # 첫 행의 fields 기준으로 그룹 처리 (모두 같은 EVENT_FIELDS 가정)
        fields = batch[0]["fields"]
        rows = [item["row"] for item in batch]
        ok = _send_batch(fields, rows)
        if ok:
            _count += len(rows)
            if LOG_EVERY_N and _count % LOG_EVERY_N == 0:
                log.info(f"적재 누적 {_count}행")
        else:
            _fail_count += len(rows)


# ============================================================
# 외부 API
# ============================================================
def start():
    """predictor 시작 시 호출 (1회)."""
    global _queue, _worker_thread
    if not ENABLED:
        log.info("Rule_LO 비활성 (config.json: enabled=false)")
        return
    if not API_KEY:
        log.warning("API key 없음 — 적재 시도하나 실패 예상")
    log.info(f"적재 활성 — {LOGPRESSO_BASE} / 테이블={TABLE_NAME} / file={FILE_LABEL}")
    if ASYNC_UPLOAD:
        _queue = queue.Queue(maxsize=QUEUE_MAX)
        _stop_flag.clear()
        _worker_thread = threading.Thread(target=_worker, daemon=True, name="Rule_LO-worker")
        _worker_thread.start()
        log.info(f"비동기 워커 시작 (batch={BATCH_SIZE}, queue_max={QUEUE_MAX})")


def upload(fields, row):
    """단일 이벤트 적재. fields/row 는 hubroom_predictor 의 EVENT_FIELDS / event_to_row 결과."""
    if not ENABLED:
        return
    try:
        # row 의 'file' 위치를 FILE_LABEL 로 덮어쓰기 (Logpresso 쿼리에서도 한번 더 덮어씀)
        if 'file' in fields:
            idx = fields.index('file')
            row = list(row)
            row[idx] = FILE_LABEL
        if ASYNC_UPLOAD and _queue is not None:
            item = {"fields": fields, "row": row}
            try:
                _queue.put_nowait(item)
            except queue.Full:
                try:
                    _queue.get_nowait()
                    _queue.put_nowait(item)
                except queue.Empty:
                    pass
        else:
            _send_batch(fields, [row])
    except Exception as e:
        if not FAIL_SILENT:
            raise
        log.debug(f"upload 예외 무시: {e}")


def stop():
    """predictor 종료 시 호출. 남은 큐 flush 후 종료."""
    if not ENABLED:
        return
    _stop_flag.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=10.0)
    log.info(f"종료 — 적재 성공 {_count}, 실패 {_fail_count}")


def stats():
    return {
        "enabled": ENABLED,
        "uploaded": _count,
        "failed": _fail_count,
        "queued": _queue.qsize() if _queue else 0,
        "url": INSERT_URL,
        "table": TABLE_NAME,
        "file_label": FILE_LABEL,
    }
