# -*- coding: utf-8 -*-
"""
Rule_LO.py — Logpresso 업로더 (hubroom_predictor v4.1 발동이벤트 적재)
=====================================================================
hubroom_predictor.py 에서 import 해서 사용:

    import Rule_LO
    Rule_LO.start()                                  # 초기화 (1회)
    Rule_LO.upload(EVENT_FIELDS, row_values)         # 매 이벤트마다 호출
    Rule_LO.stop()                                   # 종료 시 (선택)

설정 변경은 Rule_LO_config.py 에서.

동작:
  1) PREFER_CLIENT=True 면 Logpresso Python 클라이언트 시도
  2) 실패하면 HTTP REST API 폴백
  3) ASYNC_UPLOAD=True 면 백그라운드 큐로 비동기 처리 (predictor 지연 방지)
  4) FAIL_SILENT=True 면 적재 실패해도 예외 안 던짐
"""
import logging
import queue
import threading
import time

import Rule_LO_config as CONFIG

log = logging.getLogger("Rule_LO")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [Rule_LO] %(message)s"))
    log.addHandler(h)


# ============================================================
# 클라이언트 인스턴스 (lazy init)
# ============================================================
_client = None
_client_ok = False
_http_ok = False
_queue: "queue.Queue" = None
_worker_thread = None
_stop_flag = threading.Event()
_count = 0   # 적재 성공 카운터
_fail_count = 0


# ============================================================
# 1. Logpresso Python 클라이언트 시도
# ============================================================
def _try_client_init():
    """Logpresso 공식 Python 클라이언트 시도. 패키지 없으면 False."""
    global _client, _client_ok
    if not CONFIG.PREFER_CLIENT:
        return False
    try:
        from logpresso import Client
    except ImportError:
        log.info("logpresso 패키지 없음 → HTTP 폴백")
        return False
    try:
        _client = Client(
            host=CONFIG.LOGPRESSO_HOST,
            port=CONFIG.LOGPRESSO_PORT,
            login=CONFIG.LOGPRESSO_LOGIN,
            password=CONFIG.LOGPRESSO_PASSWORD,
            use_tls=CONFIG.LOGPRESSO_USE_SSL,
        )
        _client.connect()
        _client_ok = True
        log.info(f"Logpresso 클라이언트 연결 OK → {CONFIG.LOGPRESSO_HOST}:{CONFIG.LOGPRESSO_PORT}")
        return True
    except Exception as e:
        log.warning(f"Logpresso 클라이언트 연결 실패: {e} → HTTP 폴백")
        return False


# ============================================================
# 2. HTTP REST API 시도
# ============================================================
def _try_http_init():
    """requests 모듈 import 확인."""
    global _http_ok
    try:
        import requests   # noqa
        _http_ok = True
        log.info(f"HTTP API 사용 → {CONFIG.LOGPRESSO_HTTP_URL}")
        return True
    except ImportError:
        log.error("requests 모듈 없음 — HTTP 폴백 불가. pip install requests")
        return False


# ============================================================
# 3. 적재 (단일 행 → Logpresso row dict)
# ============================================================
def _build_row(fields, values):
    """field_names + values 를 dict 로 변환. 'file' 은 하드코딩."""
    row = dict(zip(fields, values))
    row['file'] = CONFIG.FILE_LABEL   # 무조건 하드코딩
    return row


def _send_via_client(rows):
    """Logpresso 클라이언트로 직접 전송."""
    _client.insert(CONFIG.LOGPRESSO_TABLE, rows)


def _send_via_http(rows):
    """HTTP POST 로 전송."""
    import requests
    from requests.auth import HTTPBasicAuth
    payload = {"table": CONFIG.LOGPRESSO_TABLE, "rows": rows}
    auth = HTTPBasicAuth(CONFIG.LOGPRESSO_LOGIN, CONFIG.LOGPRESSO_PASSWORD)
    r = requests.post(
        CONFIG.LOGPRESSO_HTTP_URL,
        json=payload,
        auth=auth,
        timeout=CONFIG.LOGPRESSO_HTTP_TIMEOUT,
    )
    r.raise_for_status()


def _send_one(rows):
    """전송 단일 시도 (재시도 포함). 성공 True / 실패 False."""
    last_err = None
    for attempt in range(CONFIG.RETRY_ON_FAIL):
        try:
            if _client_ok:
                _send_via_client(rows)
                return True
            elif _http_ok:
                _send_via_http(rows)
                return True
            else:
                return False
        except Exception as e:
            last_err = e
            time.sleep(CONFIG.RETRY_BACKOFF * (2 ** attempt))
    log.warning(f"Logpresso 적재 실패 (재시도 {CONFIG.RETRY_ON_FAIL}회): {last_err}")
    return False


# ============================================================
# 4. 비동기 워커
# ============================================================
def _worker():
    """큐에서 꺼내 배치로 전송 (1초 단위)."""
    global _count, _fail_count
    BATCH = 50
    while not _stop_flag.is_set():
        rows = []
        try:
            # 첫 행 대기 (1초)
            rows.append(_queue.get(timeout=1.0))
        except queue.Empty:
            continue
        # 추가 행 비대기 수집
        while len(rows) < BATCH:
            try:
                rows.append(_queue.get_nowait())
            except queue.Empty:
                break
        ok = _send_one(rows)
        if ok:
            _count += len(rows)
            if CONFIG.LOG_EVERY_N and _count % CONFIG.LOG_EVERY_N == 0:
                log.info(f"적재 누적 {_count}행")
        else:
            _fail_count += len(rows)


# ============================================================
# 외부 API
# ============================================================
def start():
    """초기화 (1회). predictor 시작 시 호출."""
    global _queue, _worker_thread
    if not CONFIG.ENABLED:
        log.info("Rule_LO 비활성 (CONFIG.ENABLED=False)")
        return
    # 연결 시도
    if not _try_client_init():
        if not _try_http_init():
            log.error("Logpresso 적재 불가 — 클라이언트도 HTTP도 사용 불가")
            return
    # 비동기 워커
    if CONFIG.ASYNC_UPLOAD:
        _queue = queue.Queue(maxsize=CONFIG.QUEUE_MAX_SIZE)
        _worker_thread = threading.Thread(target=_worker, daemon=True, name="Rule_LO-worker")
        _worker_thread.start()
        log.info("비동기 워커 시작")


def upload(fields, values):
    """단일 이벤트 행 적재. predictor 의 append_event_row 후 호출."""
    if not CONFIG.ENABLED:
        return
    try:
        row = _build_row(fields, values)
        if CONFIG.ASYNC_UPLOAD and _queue is not None:
            try:
                _queue.put_nowait(row)
            except queue.Full:
                # 큐 가득참 — 가장 오래된 것 폐기 후 추가
                try:
                    _queue.get_nowait()
                    _queue.put_nowait(row)
                except queue.Empty:
                    pass
        else:
            _send_one([row])
    except Exception as e:
        if not CONFIG.FAIL_SILENT:
            raise
        log.debug(f"upload 예외 무시: {e}")


def stop():
    """종료 (남은 큐 flush). predictor 종료 시 호출."""
    if not CONFIG.ENABLED:
        return
    _stop_flag.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5.0)
    if _client:
        try:
            _client.close()
        except Exception:
            pass
    log.info(f"종료 — 적재 성공 {_count}, 실패 {_fail_count}")


def stats():
    """간단 통계."""
    return {
        "enabled": CONFIG.ENABLED,
        "client_ok": _client_ok,
        "http_ok": _http_ok,
        "uploaded": _count,
        "failed": _fail_count,
        "queued": _queue.qsize() if _queue else 0,
    }
