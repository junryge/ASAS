# -*- coding: utf-8 -*-
"""
Rule_hid.py — Logpresso 적재기 (HID_VHL_OHT 1분 줄 → AMHS_VHL_OHT)
=================================================================
Rule_LO.py 와 같은 방식
  - API key: api_key.txt (1줄)              ← Rule_LO 와 같은 파일 (없으면 hdi_api_key.txt)
  - 설정: config.json                        ← Rule_LO 와 같은 파일 (enabled · logpresso_base …)
  - 엔드포인트: http://HOST:PORT/logpresso/httpexport/query.csv
  - 인증: ?_apikey=XXX 쿼리 파라미터
  - 쿼리: json "{k = 'v', ...}" | import AMHS_VHL_OHT   (한 줄씩 — CSV 에 쓰고 바로 그 자리에서)

사용 (run_oht.py 가 부른다):
    import Rule_hid
    Rule_hid.start()
    Rule_hid.upload_rows(fab, header, rows)   # HID_VHL_OHT 가 CSV 에 1분 줄을 쓸 때마다
    Rule_hid.stop()

AMHS_VHL_OHT 한 줄 = HID_VHL_OHT CSV 한 줄 + FAB
    datetime      'YYYY-MM-DD HH:MM' (년-월-일 시:분, 초 없음)
    fab_name      M16HUB / M14 / M14B / M16A / M16B
    alarm_kr      정상 / 경계 / 위험 / 초위험
    alarm_en      NORMAL / WARNING / DANGER / CRITICAL
    hid_zone      병목 1위 HID 구역 (알람 아니면 0)
    hid_section   그 구역 Bay (알람 아니면 0)
    oht_report    보고 차량 수
    oht_missing   미보고 차량 수
    oht_jam       JAM 차량 수
    zone_stop     1위 구역 안 멈춘 차
    zone_vhl      1위 구역 안 차량
    vhl_max       1위 구역 정원
    zone_occ      점유율 %
    hid_zone_2    2위 구역
    hid_zone_3    3위 구역
  ★HT_STOP 은 숨김 — CSV 와 같이 안 넣는다.
  ★1분에 한 줄 (FAB 마다). HID_VHL_OHT 는 50초마다 판정하고, 1분이 끝나면 그 분 줄을 CSV 에 쓰고
    같은 줄을 여기로 넘긴다. 다시 켜도 이미 쓴 분은 안 넘긴다 (중복 없음).

config.json 에 넣을 수 있는 것 (전부 기본값이 있어 안 넣어도 된다 — enabled 만 true 면 동작)
    "enabled": true                          Rule_LO 와 같은 스위치 (false 면 Rule_hid 도 안 보냄)
    "logpresso_base": "http://…/logpresso"   Rule_LO 와 같은 곳
    "hid_enabled": false                     Rule_hid 만 끔
    "hid_table_name": "AMHS_VHL_OHT"         테이블 이름
    "hid_only_alarm": true                   경계 · 위험 · 초위험 줄만 보냄 (기본 false = 정상 포함 1분마다 다)
    "hid_api_key_file": "api_key_hid.txt"    이 테이블 권한이 있는 키를 따로 쓸 때 (없으면 api_key.txt)

시험 (Rule_hid.py 옆에서)
    python Rule_hid.py              설정 · 키 · 테이블 확인만 (데이터 안 넣음)
    python Rule_hid.py --write      AMHS_VHL_OHT 에 fab_name='DIAG_TEST' 한 줄 시험으로 넣기
"""
import json
import logging
import os
import queue
import sys
import threading
import time
import urllib.parse
from datetime import datetime as _dt

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# 로깅
# ============================================================
_HERE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("Rule_hid")
log.setLevel(logging.INFO)
if not log.handlers:
    _fmt = logging.Formatter("%(asctime)s [Rule_hid] %(message)s")
    for _h in (logging.StreamHandler(sys.stdout),
               logging.FileHandler(os.path.join(_HERE, "Rule_hid.log"), encoding="utf-8")):
        _h.setFormatter(_fmt)
        log.addHandler(_h)


# ============================================================
# 설정 로드 (config.json + api_key.txt) — Rule_LO 와 같은 규칙
# ============================================================
def _load_config():
    """config.json 로드. 없으면 안전한 기본값 (비활성)."""
    path = os.path.join(_HERE, "config.json")
    if not os.path.exists(path):
        log.warning(f"config.json 없음 ({path}) — 비활성. Rule_LO 의 config.json · api_key.txt 를 옆에 두세요")
        return {"enabled": False}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"config.json 파싱 실패: {e}")
        return {"enabled": False}


def _read_key(key_file_name, warn=True):
    """키 파일 첫 줄 (없으면 '')."""
    for p in [os.path.join(_HERE, key_file_name), os.path.join(os.getcwd(), key_file_name)]:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    lines = f.read().strip().splitlines()
                return lines[0].strip() if lines else ""
            except Exception:
                return ""
    if warn:
        log.warning(f"{key_file_name} 없음 — 인증 실패 가능")
    return ""


CFG = _load_config()
ENABLED        = bool(CFG.get("enabled", False)) and bool(CFG.get("hid_enabled", True))
LOGPRESSO_BASE = CFG.get("logpresso_base", "http://localhost:8888/logpresso")
INSERT_PATH    = CFG.get("_endpoints", {}).get("insert", "/httpexport/query.csv")
INSERT_URL     = LOGPRESSO_BASE.rstrip("/") + INSERT_PATH
HID_TABLE      = CFG.get("hid_table_name", "AMHS_VHL_OHT")
ONLY_ALARM     = bool(CFG.get("hid_only_alarm", False))
ASYNC_UPLOAD   = bool(CFG.get("hid_async_upload", False))   # ★기본 = CSV 쓰고 바로 그 자리에서 적재 (동기)
QUEUE_MAX      = int(CFG.get("queue_max_size", 10000))
RETRY_ON_FAIL  = int(CFG.get("hid_retry_on_fail", 2))
RETRY_BACKOFF  = float(CFG.get("retry_backoff", 1.0))
LOG_EVERY_N    = int(CFG.get("log_every_n", 60))
FAIL_SILENT    = bool(CFG.get("fail_silent", True))
HTTP_TIMEOUT   = int(CFG.get("hid_http_timeout", 10))     # 바로 보내므로 짧게 — 판정 루프(50초)를 오래 잡지 않게

API_KEY_FILE   = CFG.get("api_key_file", "api_key.txt")
HID_KEY_FILE   = CFG.get("hid_api_key_file", "api_key_hid.txt")
API_KEY        = _read_key(API_KEY_FILE, warn=False) if ENABLED else ""
if ENABLED and not API_KEY:                          # api_key.txt 가 없으면 판정용 hdi_api_key.txt (같은 10.40.42.167)
    API_KEY = _read_key("hdi_api_key.txt", warn=False)
    if API_KEY:
        API_KEY_FILE = "hdi_api_key.txt"
    else:
        log.warning(f"{API_KEY_FILE} · hdi_api_key.txt 둘 다 없음 — 인증 실패 가능")
_HID_OWN_KEY   = _read_key(HID_KEY_FILE, warn=False) if ENABLED else ""
HID_API_KEY    = _HID_OWN_KEY or API_KEY

# CSV 칸 → AMHS_VHL_OHT 칸 (FAB 이름이 붙은 칸은 {FAB}_ 를 떼고 맞춘다)
COLS = [("날짜", None), ("시간", None),
        ("ALARM_KR", "alarm_kr"), ("ALARM_EN", "alarm_en"),
        ("HID_ZONE", "hid_zone"), ("HID_section", "hid_section"),
        ("OHT_report", "oht_report"), ("OHT_missing", "oht_missing"), ("OHT_JAM", "oht_jam"),
        ("ZONE_STOP", "zone_stop"), ("ZONE_VHL", "zone_vhl"), ("VHL_MAX", "vhl_max"),
        ("ZONE_OCC", "zone_occ"), ("HID_ZONE_2", "hid_zone_2"), ("HID_ZONE_3", "hid_zone_3")]
# 0 도 그대로 넣는다 (1분마다 빠짐없이 — 정상 분도 숫자 그대로)
_KEEP_ZERO = {"hid_zone", "hid_section", "oht_report", "oht_missing", "oht_jam", "zone_stop", "zone_vhl",
              "vhl_max", "zone_occ", "hid_zone_2", "hid_zone_3"}
ALARMS = ("경계", "위험", "초위험")


# ============================================================
# 내부 상태
# ============================================================
_queue = None
_worker_thread = None
_stop_flag = threading.Event()
_count = 0
_fail_count = 0


# ============================================================
# Logpresso 쿼리 (json "{...}" | import AMHS_VHL_OHT) — Rule_LO 와 같은 꼴
# ============================================================
def _to_maru_literal(row_dict):
    """dict → {k = 'v', k2 = 'v2'}. 빈 값은 뺀다, 0 은 넣는다 (_KEEP_ZERO)."""
    parts = []
    for k, v in row_dict.items():
        if k.startswith("_") or v is None or v == "":
            continue
        if k not in _KEEP_ZERO and k not in ("datetime", "fab_name", "alarm_kr", "alarm_en") and str(v) in ("0", "0.0"):
            continue
        s = str(v)[:200].replace("'", "\\'")
        parts.append(f"{k} = '{s}'")
    return "{" + ", ".join(parts) + "}"


def _build_query(row_dict):
    literal = _to_maru_literal(row_dict).replace('"', '\\"')
    return f'json "{literal}" | import {HID_TABLE}'


def _post_query(q, key):
    """GET httpexport (POST 는 서버가 405) — Rule_LO 와 같음."""
    qs = " ".join(q.split())
    url = f"{INSERT_URL}?_apikey={key}&_q={urllib.parse.quote(qs, safe='')}"
    r = requests.get(url, verify=False, timeout=HTTP_TIMEOUT)
    if r.status_code != 200 or r.text.strip().startswith("<"):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r


def _send_one(row_dict):
    """한 줄 보내기 — 성공 True. 동기 모드면 줄마다 로그를 남긴다."""
    ok = _send_raw(row_dict)
    if not ASYNC_UPLOAD:
        global _count, _fail_count
        if ok:
            _count += 1
            log.info(f"적재 OK → {HID_TABLE}  {row_dict.get('fab_name')} {row_dict.get('datetime')} "
                     f"{row_dict.get('alarm_kr')}")
        else:
            _fail_count += 1
    return ok


def _send_raw(row_dict):
    q = _build_query(row_dict)
    last_err = None
    for attempt in range(max(1, RETRY_ON_FAIL)):
        try:
            _post_query(q, HID_API_KEY)
            return True
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    log.warning(f"적재 실패 (재시도 {RETRY_ON_FAIL}회): {type(last_err).__name__}: {last_err}")
    return False


def _worker():
    """큐에서 1건씩 꺼내 전송. 종료 신호 받으면 남은 큐 flush 후 종료 (Rule_LO 와 같음)."""
    global _count, _fail_count
    while not _stop_flag.is_set() or (_queue and not _queue.empty()):
        try:
            row_dict = _queue.get(timeout=1.0)
        except queue.Empty:
            continue
        if _send_one(row_dict):
            _count += 1
            if LOG_EVERY_N and _count % LOG_EVERY_N == 0:
                log.info(f"적재 누적 {_count}행 → {HID_TABLE}")
        else:
            if not row_dict.get("_requeued") and _queue is not None and not _stop_flag.is_set():
                row_dict["_requeued"] = True        # 한 번만 다시 넣는다 (유실 방지 · 무한 재시도 방지)
                try:
                    _queue.put_nowait(row_dict)
                    log.info("실패 행 재큐잉 (다음 사이클 재시도)")
                except queue.Full:
                    _fail_count += 1
            else:
                _fail_count += 1


def _enqueue(row_dict):
    if ASYNC_UPLOAD and _queue is not None:
        try:
            _queue.put_nowait(row_dict)
        except queue.Full:
            try:
                _queue.get_nowait()
                _queue.put_nowait(row_dict)
            except queue.Empty:
                pass
    else:
        _send_one(row_dict)


# ============================================================
# CSV 한 줄 → AMHS_VHL_OHT 한 줄
# ============================================================
def to_row(fab, header, row):
    """HID_VHL_OHT CSV 줄(헤더 · 값) → {datetime, fab_name, alarm_kr, …}"""
    pre = f"{fab}_"
    d = {}
    for h, v in zip(header, row):
        h = h[len(pre):] if h.startswith(pre) else h          # M16HUB_OHT_report → OHT_report
        d[h] = v
    out = {"datetime": f"{d.get('날짜', '')} {d.get('시간', '')}".strip()[:16], "fab_name": fab}
    for src, dst in COLS:
        if dst:
            out[dst] = d.get(src, "")
    return out


# ============================================================
# 외부 API
# ============================================================
_started = False


def start():
    """시작 때 1회 (HID_VHL_OHT.py · run_oht.py 가 부른다 — 두 번 불러도 한 번만)."""
    global _queue, _worker_thread, _started
    if _started:
        return
    _started = True
    if not ENABLED:
        why = "config.json 없음 · enabled=false" if not CFG.get("enabled") else "hid_enabled=false"
        log.info(f"Rule_hid 비활성 ({why}) — CSV · 문제맵만 만들고 로그프레소에는 안 넣음")
        return
    if not API_KEY and not _HID_OWN_KEY:
        log.warning("API key 없음 — 적재 시도하나 실패 예상")
    log.info(f"적재 활성 — {LOGPRESSO_BASE} / 테이블={HID_TABLE} / "
             f"{'경계 이상만' if ONLY_ALARM else '1분마다 (정상 포함)'} / FAB · 15칸 / "
             f"{'비동기 큐' if ASYNC_UPLOAD else 'CSV 쓰고 바로 적재'}")
    log.info(f"키 — {HID_KEY_FILE}" if _HID_OWN_KEY else f"키 — {API_KEY_FILE} 공용 ({HID_KEY_FILE} 없음)")
    if ASYNC_UPLOAD:
        _queue = queue.Queue(maxsize=QUEUE_MAX)
        _stop_flag.clear()
        _worker_thread = threading.Thread(target=_worker, daemon=True, name="Rule_hid-worker")
        _worker_thread.start()
        log.info(f"비동기 워커 시작 (queue_max={QUEUE_MAX}, 단일행씩 전송)")


def upload_rows(fab, header, rows):
    """HID_VHL_OHT 가 CSV 에 새로 쓴 1분 줄들 → AMHS_VHL_OHT (HID_VHL_OHT.SAVE_HOOKS 에 단다)."""
    if not ENABLED:
        return
    try:
        for row in rows:
            r = to_row(fab, header, row)
            if ONLY_ALARM and r.get("alarm_kr") not in ALARMS:
                continue
            _enqueue(r)
    except Exception as e:
        if not FAIL_SILENT:
            raise
        log.debug(f"upload 예외 무시: {e}")


def stop():
    """종료 때. 남은 큐 flush 후 종료."""
    global _started
    if not ENABLED or not _started:
        return
    _started = False
    _stop_flag.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=10.0)
    log.info(f"종료 — 적재 성공 {_count}, 실패 {_fail_count}")


def stats():
    return {"enabled": ENABLED, "uploaded": _count, "failed": _fail_count,
            "queued": _queue.qsize() if _queue else 0, "url": INSERT_URL, "table": HID_TABLE,
            "only_alarm": ONLY_ALARM}


# ============================================================
# 시험 — python Rule_hid.py [--write]
# ============================================================
def _diag(write=False):
    print("=" * 70)
    print("로그프레소 :", INSERT_URL)
    print("enabled    :", CFG.get("enabled"), "/ hid_enabled:", CFG.get("hid_enabled", True))
    print("테이블     :", HID_TABLE, "/", "경계 이상만" if ONLY_ALARM else "1분마다 (정상 포함)")
    print("키 파일    :", HID_KEY_FILE if _HID_OWN_KEY else API_KEY_FILE,
          "(있음)" if HID_API_KEY else "(없음/비어있음)")
    print("=" * 70)
    if not ENABLED:
        print("비활성 — config.json 의 enabled 를 확인하세요")
        return
    try:
        _post_query(f"table limit=1 {HID_TABLE}", HID_API_KEY)
        print(f"읽기 OK — {HID_TABLE} 테이블 조회됨")
    except Exception as e:
        print(f"읽기 실패 — {e}\n  (키 권한 · 테이블이 아직 없음 · 주소 중 하나)")
    if write:
        row = {"datetime": _dt.now().strftime("%Y-%m-%d %H:%M"), "fab_name": "DIAG_TEST", "alarm_kr": "정상",
               "alarm_en": "NORMAL", "hid_zone": 0, "oht_report": 0}
        try:
            _post_query(_build_query(row), HID_API_KEY)
            print(f"쓰기 OK — {HID_TABLE} 에 fab_name='DIAG_TEST' 한 줄 넣음")
        except Exception as e:
            print(f"쓰기 실패 — {e}")


if __name__ == "__main__":
    _diag("--write" in sys.argv)
