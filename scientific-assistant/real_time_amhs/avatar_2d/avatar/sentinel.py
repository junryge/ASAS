# -*- coding: utf-8 -*-
"""
sentinel.py — 버추얼 에이전트의 눈. real_time_amhs(관제 서버)를 읽는다.

왜 필요한가
    아바타가 "M16HUB 위험이에요!" 라고 말하려면 실제 점수를 봐야 한다.
    LLM 에게 "지금 상태 어때?" 를 그냥 물으면 **숫자를 지어낸다** — 그래서
    여기서 관제 서버의 숫자를 먼저 받아 근거(evidence)로 만들고, LLM 은
    그 근거 안에서만 말하게 한다 (llm.py 의 숫자 가드가 강제).

정직 규칙 — 이 파일 전체의 원칙
    · 관제 서버가 죽어 있으면 "죽어 있다" 고 말한다. 옛 캐시로 산 척 안 한다.
    · 데이터 시각이 오래됐으면(기본 10분) 근거에 '오래된 데이터' 라고 박는다.
    · 근거에 없는 것은 근거에 없다 — 지어낼 재료를 주지 않는다.

관제 서버 쪽 계약 (real_time_amhs)
    GET /api/fab/compare   ALL + FAB 5 를 한 시각으로 나란히 (fab_score.compare)
    GET /api/fab/columns   시스템별 감시 컬럼·임계·화면 조인
    응답의 rows[0] 는 ALL, 이후는 FAB 점수순. 등급 컷은 cuts{warn,danger,critical}.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config
from . import terms

# 폴링 캐시 — 브라우저가 3초마다 두드려도 관제 서버에는 이 주기로만 간다
CACHE_S = 5.0
STALE_MIN = 10          # 데이터 시각이 이보다 오래되면 '오래된 데이터'
# ★타임아웃 3초는 너무 빡빡했다. 관제 서버는 이 API 에서 하루 CSV 를 통째로
#   읽는데, 수집·LLM 분석과 겹치면 3초를 넘는 순간이 있다 — 그때마다
#   "끊김/복구" 가 번갈아 떠서 화면이 시끄러웠다 (실제 현장 증상).
TIMEOUT_S = 8.0
# 한 번 삐끗한 것은 끊김이 아니다 — 마지막 성공이 이 안이면 그 값으로 버틴다.
# 이걸 넘겨야 진짜 끊김이다. (버티는 동안엔 degraded 로 표시 — 산 척과 다르다:
# 최근 성공값이 실제로 있고, 몇 초 전 값인지도 같이 알린다)
GRACE_S = 60.0

_lock = threading.Lock()
_cache = {"at": 0.0, "compare": None, "err": "", "good_at": 0.0}
_cols_cache = {"at": 0.0, "columns": None, "err": ""}

# ── 알람 이력 (data/alarms.json) ──
# "언제 알람이 울렸었지?" 에 답하려면 서버가 기억해야 한다 — 브라우저는
# 닫히면 끝이다. watch() 가 등급 변화를 볼 때마다 여기 적는다.
HOLD_MIN = 60            # 정상 복귀 후 알람을 내리기까지의 관찰 시간(분)
                         # — 관제(real_time_amhs)의 '사건은 60분 뒤 닫힘' 과 같은 규칙
ALOG_MAX = 500
_alog_path = None        # init() 이 채운다
_alog = []               # [{t, fab, level, score, kind}]  kind: on|change|off
_last_levels = {}        # {fab: level} 직전 관측


def init(data_dir):
    """알람 이력 저장 위치. server.App.init 이 부른다."""
    global _alog_path, _alog
    import os
    _alog_path = os.path.join(str(data_dir), "alarms.json")
    try:
        with open(_alog_path, encoding="utf-8") as f:
            _alog = json.load(f) or []
    except Exception:
        _alog = []


def _alog_save():
    if not _alog_path:
        return
    try:
        with open(_alog_path, "w", encoding="utf-8") as f:
            json.dump(_alog[-ALOG_MAX:], f, ensure_ascii=False)
    except Exception:
        pass


def _record(alarms):
    """등급 변화만 적는다 — 폴링마다 적으면 이력이 아니라 소음이 된다."""
    global _last_levels
    now_lv = {a["fab"]: a["level"] for a in alarms}
    stamp = time.strftime("%Y-%m-%d %H:%M")
    changed = False
    with _lock:
        for fab, lv in now_lv.items():
            prev = _last_levels.get(fab, "정상")
            if prev == lv:
                continue
            kind = "on" if prev == "정상" else "change"
            sc = next((a.get("score") for a in alarms if a["fab"] == fab), None)
            _alog.append(_entry(stamp, fab, lv, sc, kind, prev))
            changed = True
        for fab, prev in list(_last_levels.items()):
            if fab not in now_lv and prev != "정상":
                _alog.append(_entry(stamp, fab, "정상", None, "off", prev))
                _close(fab, stamp, "")          # 열려 있던 건을 닫는다
                changed = True
        _last_levels = {**{f: "정상" for f in _last_levels}, **now_lv}
        if changed:
            del _alog[:-ALOG_MAX]
            _alog_save()


def _entry(stamp, fab, level, score, kind, prev):
    """기록 한 줄 — 사람이 표로 볼 것이므로 날짜·시간을 나눠 담는다.
    ★해제 여부(cleared)와 메모(note)를 처음부터 자리 잡아 둔다. 나중에
      붙이려면 옛 기록에 그 칸이 없어 화면이 들쭉날쭉해진다."""
    d, _, t = str(stamp).partition(" ")
    return {"id": "{}-{}-{}".format(fab, stamp.replace(" ", "_"), kind),
            "t": stamp, "date": d, "time": t, "fab": fab, "level": level,
            "score": score, "kind": kind, "prev": prev,
            "cleared": kind == "off", "cleared_at": stamp if kind == "off" else "",
            "note": ""}


def _close(fab, stamp, note):
    """그 FAB 의 아직 안 닫힌 발생 기록들을 해제 처리한다 (_lock 안에서 호출)."""
    for e in reversed(_alog):
        if e.get("fab") != fab or e.get("kind") == "off":
            continue
        if e.get("cleared"):
            break                       # 이미 닫힌 건부터는 옛 사건이다
        e["cleared"] = True
        e["cleared_at"] = stamp
        if note and not e.get("note"):
            e["note"] = note


def note(entry_id, text):
    """기록에 메모를 단다 (해제 사유·조치 내용). 단 건수를 돌려준다."""
    text = str(text or "").strip()[:500]
    n = 0
    with _lock:
        for e in _alog:
            if e.get("id") == entry_id:
                e["note"] = text
                n += 1
        if n:
            _alog_save()
    return n


def clear_note(fab, text, when=None):
    """사용자가 알람을 해제하면서 남긴 내용 — 그 FAB 의 열린 건을 닫고 메모."""
    stamp = when or time.strftime("%Y-%m-%d %H:%M")
    text = str(text or "").strip()[:500]
    with _lock:
        before = [e for e in _alog if e.get("fab") == fab and not e.get("cleared")]
        _close(fab, stamp, text)
        _alog.append(_entry(stamp, fab, "정상", None, "off", ""))
        _alog[-1]["note"] = text
        del _alog[:-ALOG_MAX]
        _alog_save()
    return len(before)


def history(n=20):
    with _lock:
        return list(_alog[-n:])


def history_text(n=8):
    """근거·채팅용 — 최근 알람 이력 몇 줄."""
    h = history(n)
    if not h:
        return "기록된 알람 없음 (감시 시작 이후 경계 이상이 없었다)"
    L = []
    for e in h:
        if e["kind"] == "off":
            L.append("{t} {f} 해제 ({p} → 정상)".format(
                t=e["t"], f=e["fab"], p=e.get("prev", "?")))
        else:
            L.append("{t} {f} {lv} 발생{s}".format(
                t=e["t"], f=e["fab"], lv=e["level"],
                s=" ({}점)".format(e["score"]) if e.get("score") is not None else ""))
    return "\n".join(L)


def base_url():
    s = getattr(config, "SENTINEL", {}) or {}
    return str(s.get("url") or "http://127.0.0.1:8989").rstrip("/")


def _get(path):
    """관제 서버 HTTP GET. 실패하면 (None, 이유) — 예외를 밖으로 안 던진다."""
    url = base_url() + path
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        # 관제 서버는 같은 망(대개 같은 PC)이다 — 프록시를 타면 오히려 막힌다
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=TIMEOUT_S) as r:
            return json.loads(r.read().decode("utf-8")), ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # ★서버는 떠 있는데 이 API 를 모른다 = server.py 가 옛 버전이다.
            #   "연결 안 됨" 이라고 하면 사용자가 네트워크만 뒤진다 (실제 그랬다).
            return None, ("관제 서버는 떠 있는데 {} 가 없습니다 (HTTP 404) — "
                          "real_time_amhs 의 server.py 가 옛 버전입니다. "
                          "새 server.py + fab_score.py 로 바꾸고 재시작하세요."
                          .format(path))
        return None, "HTTP {}".format(e.code)
    except Exception as e:  # noqa: BLE001 — 죽어 있음/타임아웃/파싱 전부 '못 읽음'
        return None, "{}: {}".format(type(e).__name__, e)


def compare(force=False):
    """/api/fab/compare — 캐시 5초 + 유예 60초.

    반환 {ok, data|None, err, cached, degraded, held_s}
      · 성공: 그 값 (good_at 갱신)
      · 실패 + 마지막 성공이 GRACE_S 안: **그 값으로 버틴다** (degraded=True,
        held_s=몇 초 전 값인지). 한 번 삐끗할 때마다 "끊김" 을 외치면
        화면이 끊김/복구로 도배된다 — 실제 현장 증상이었다.
      · 실패 + 유예도 지남: 그때가 진짜 끊김이다. ok=False.
        (성공한 적이 없으면 유예도 없다 — 산 척은 여전히 금지)
    """
    now = time.time()
    with _lock:
        if not force and _cache["compare"] is not None \
                and now - _cache["at"] < CACHE_S:
            return {"ok": True, "data": _cache["compare"], "err": "",
                    "cached": True, "degraded": False, "held_s": 0}
    data, err = _get("/api/fab/compare")
    with _lock:
        if data and data.get("ok"):
            _cache.update(at=now, compare=data, err="", good_at=now)
            return {"ok": True, "data": data, "err": "", "cached": False,
                    "degraded": False, "held_s": 0}
        _cache["err"] = err or str((data or {}).get("error") or "응답 이상")
        held = now - (_cache["good_at"] or 0)
        if _cache["compare"] is not None and held < GRACE_S:
            return {"ok": True, "data": _cache["compare"],
                    "err": _cache["err"], "cached": True,
                    "degraded": True, "held_s": int(held)}
        return {"ok": False, "data": None, "err": _cache["err"],
                "cached": False, "degraded": False, "held_s": 0}


def columns():
    """/api/fab/columns — 임계·컬럼 정의는 잘 안 바뀌므로 60초 캐시."""
    now = time.time()
    with _lock:
        if _cols_cache["columns"] is not None and now - _cols_cache["at"] < 60:
            return {"ok": True, "data": _cols_cache["columns"], "err": ""}
    data, err = _get("/api/fab/columns")
    with _lock:
        if data and data.get("ok"):
            _cols_cache.update(at=now, columns=data, err="")
            return {"ok": True, "data": data, "err": ""}
        return {"ok": False, "data": None, "err": err or "응답 이상"}


# ────────────────────────────── 시각 ──────────────────────────────
def _data_age_min(at_str):
    """'2026-07-28 08:20' → 지금으로부터 몇 분 전인가. 못 읽으면 None."""
    try:
        t = time.mktime(time.strptime(str(at_str), "%Y-%m-%d %H:%M"))
        return max(0, int((time.time() - t) / 60))
    except Exception:
        return None


def age_text(mins):
    """★"40780분 전" 은 사람이 못 읽는다 (실제 지적). 28일이면 28일이라고
    한다. 수집이 한 달 멈춘 것과 40분 늦은 것은 완전히 다른 사건인데,
    분으로만 적으면 둘 다 그냥 큰 숫자로 보인다.
    """
    if mins is None:
        return "시각 불명"
    m = int(mins)
    if m < 60:
        return "{}분 전".format(m)
    if m < 60 * 24:
        h, mm = divmod(m, 60)
        return "{}시간 {}분 전".format(h, mm) if mm else "{}시간 전".format(h)
    d, rem = divmod(m, 60 * 24)
    h = rem // 60
    return "{}일 {}시간 전".format(d, h) if h else "{}일 전".format(d)


# ────────────────────────────── 감시 (알람) ──────────────────────────────
LEVEL_ORDER = {"정상": 0, "경계": 1, "위험": 2, "초위험": 3}


def watch():
    """브라우저 알람 폴링용 — 지금 경계 이상인 시스템 목록.

    반환: {ok, alarms:[{fab, level, score}...] (등급 나쁜 순), at, stale, err}
    관제 서버가 죽어 있으면 ok=False — 화면은 '관제 연결 끊김' 을 보여야지
    '정상' 을 보여선 안 된다.
    """
    r = compare()
    if not r["ok"]:
        return {"ok": False, "alarms": [], "at": "", "stale": False,
                "err": r["err"]}
    d = r["data"]
    age = _data_age_min(d.get("at"))
    alarms = []
    for row in d.get("rows") or []:
        lv = str(row.get("level") or "정상")
        if LEVEL_ORDER.get(lv, 0) >= 1:
            alarms.append({"fab": row.get("fab"), "level": lv,
                           "score": row.get("score")})
    alarms.sort(key=lambda a: -LEVEL_ORDER.get(a["level"], 0))
    _record(alarms)              # 이력은 서버가 기억한다 — 브라우저는 닫히면 끝

    # ── 관찰 유지(HOLD) — 관제의 '사건은 60분 뒤 닫힘' 과 같은 규칙 ──
    # 데이터가 정상으로 돌아와도, 마지막 경계+ 로부터 HOLD_MIN 이 지나기
    # 전에는 hold 로 알려 준다. 화면은 경광등을 유지하되 "정상 복귀 —
    # 관찰 중" 으로 표시한다 (재발이 흔해서 바로 끄면 놓친다).
    hold = None
    if not alarms:
        last_bad = None
        for e in reversed(history(50)):
            if e["kind"] in ("on", "change"):
                last_bad = e
                break
            if e["kind"] == "off":
                # off 이후 HOLD_MIN 안이면 관찰 중
                try:
                    t = time.mktime(time.strptime(e["t"], "%Y-%m-%d %H:%M"))
                    mins = int((time.time() - t) / 60)
                except Exception:
                    break
                if mins < HOLD_MIN:
                    hold = {"fab": e["fab"], "prev": e.get("prev", "?"),
                            "since_min": mins,
                            "left_min": HOLD_MIN - mins}
                break
        del last_bad
    return {"ok": True, "alarms": alarms, "at": d.get("at") or "",
            "stale": age is not None and age > STALE_MIN,
            "age_min": age, "hold": hold, "hold_min": HOLD_MIN,
            "degraded": bool(r.get("degraded")),
            "held_s": int(r.get("held_s") or 0), "err": r.get("err") or ""}


# ────────────────────────────── 화면 그래프 ──────────────────────────────
MAX_READ = 8          # 한 FAB 에 조건이 너무 많으면 그래프가 아니라 표가 된다


def chart():
    """화면에 그릴 '지금 상태' — 표로 읽던 것을 눈으로 보게 한다.

    반환 {ok, at, age_min, stale, cuts, area_cap, fabs:[...], err}
      fabs[i] = {fab, score, level, delta, area, fired(한글), readings:[...]}
      readings[j] = {label, amos, unit, op, thr, value, over, has_value}

    ★비율(%)을 서버가 만들지 않는다. 임계 방향이 두 가지(≥ / ≤)라 한 숫자로
      뭉개면 거짓이 된다 — 값·임계·방향을 그대로 주고, 막대는 화면이 그린다.
    ★룰 코드는 한 글자도 안 내보낸다 (근거·대답과 같은 규칙).
    """
    r = compare()
    if not r["ok"]:
        return {"ok": False, "fabs": [], "at": "", "err": r["err"]}
    d = r["data"]
    cols = columns()
    rules = {}
    if cols["ok"]:
        for ru in (cols["data"].get("rules") or []):
            rules[ru.get("code")] = ru
    out = []
    for row in d.get("rows") or []:
        if row.get("is_all"):
            continue                     # 전체(ALL)는 FAB 막대와 축이 다르다
        reads = []
        for c in (row.get("readings") or [])[:MAX_READ]:
            # ★has_value 가 빠져 오면 값이 있어도 '값 없음(빗금)' 으로 그린다 —
            #   있는 데이터를 없다고 그리는 쪽이 더 나쁘다. 값으로 판단한다.
            has = (bool(c.get("has_value")) if "has_value" in c
                   else c.get("value") is not None)
            reads.append({
                "label": _no_code(c.get("label") or ""),
                "amos": c.get("amos") or "",
                "unit": c.get("unit") or "",
                "op": c.get("op") or ">=",
                "thr": c.get("thr"),
                "value": c.get("value") if has else None,
                "has_value": has,
                "over": bool(c.get("over")),
            })
        # 넘은 것을 먼저 — 그래프에서 눈이 먼저 가야 할 순서
        reads.sort(key=lambda c: (0 if c["over"] else
                                  1 if c["has_value"] else 2))
        fired = []
        for code in (row.get("fired") or []):
            meta = rules.get(code) or {}
            fired.append(_no_code(meta.get("label") or "") or
                         _KO.get(code, "룰"))
        out.append({"fab": row.get("fab"), "score": row.get("score"),
                    "level": row.get("level") or "정상",
                    "delta": row.get("delta"), "area": row.get("area"),
                    "fired": fired, "readings": reads})
    out.sort(key=lambda f: -(f["score"] or 0))
    age = _data_age_min(d.get("at"))
    return {"ok": True, "at": d.get("at") or "", "age_min": age,
            "age_text": age_text(age),          # "28일 3시간 전" — 분은 못 읽는다
            "stale": age is not None and age > STALE_MIN,
            "live": age is not None and age <= STALE_MIN,   # 실시간인가
            "cuts": d.get("cuts") or {"warn": 60, "danger": 71, "critical": 85},
            "area_cap": d.get("area_cap"), "delta_min": d.get("delta_min"),
            "blind": d.get("blind") or [], "fabs": out,
            "warn": d.get("warn") or "",          # "오늘 수집이 없어 …" 그대로
            "fallback_day": d.get("fallback_day"), "day": d.get("day") or "",
            "degraded": bool(r.get("degraded")), "err": r.get("err") or ""}


# ────────────────────────────── 과거 시각 조회 ──────────────────────────────
def parse_when(text, now=None):
    """질문 속의 날짜·시각 — 추측이 아니라 정해진 표현만 읽는다.

    반환 (day "YYYYMMDD", at "YYYY-MM-DD HH:MM"|None) 또는 None(과거 조회 아님).
      · 날짜: 2026-08-23 / 2026년 8월 23일 / 8월 23일 / 오늘·어제·그제
      · 시각: 8시 20분 / 08:20  (★'3시간' 의 '시' 는 시각이 아니다)
      · 시각만 있으면 오늘. '지금/현재/실시간' 이 있으면 과거 조회가 아니다.
    """
    t = str(text or "")
    if re.search(r"지금|현재|실시간", t):
        return None
    now = now or time.localtime()
    day = None
    m = re.search(r"(20\d{2})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})일?", t)
    if m:
        day = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif re.search(r"그제|그저께", t):
        lt = time.localtime(time.time() - 2 * 86400)
        day = (lt.tm_year, lt.tm_mon, lt.tm_mday)
    elif "어제" in t:
        lt = time.localtime(time.time() - 86400)
        day = (lt.tm_year, lt.tm_mon, lt.tm_mday)
    elif "오늘" in t:
        day = (now.tm_year, now.tm_mon, now.tm_mday)
    else:
        m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", t)
        if m:
            day = (now.tm_year, int(m.group(1)), int(m.group(2)))

    hh = mm = None
    m = re.search(r"(\d{1,2})\s*시(?!간)\s*(?:(\d{1,2})\s*분)?", t)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2) or 0)
        if re.search(r"오후|저녁|밤", t[:m.start()]) and hh < 12:
            hh += 12
    else:
        m = re.search(r"\b(\d{1,2}):(\d{2})\b", t)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))

    if day is None and hh is None:
        return None
    if day is None:
        day = (now.tm_year, now.tm_mon, now.tm_mday)   # 시각만 → 오늘
    if not (1 <= day[1] <= 12 and 1 <= day[2] <= 31):
        return None
    day_s = "{:04d}{:02d}{:02d}".format(*day)
    at_s = None
    if hh is not None and 0 <= hh <= 23 and 0 <= mm <= 59:
        at_s = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(*day, hh, mm)
    return (day_s, at_s)


def _fetch_at(day, at):
    """과거 한 시각의 비교 — 캐시 없이 그 자리에서 (자주 안 부른다)."""
    q = "/api/fab/compare?day=" + urllib.parse.quote(str(day))
    if at:
        q += "&at=" + urllib.parse.quote(str(at))
    data, err = _get(q)
    if data and data.get("ok"):
        return {"ok": True, "data": data, "err": ""}
    return {"ok": False, "data": None,
            "err": err or str((data or {}).get("error") or "응답 이상")}


def evidence_at(day, at=None):
    """과거 시각의 근거 — 요청한 시각과 실제 찾은 행의 시각을 둘 다 밝힌다."""
    r = _fetch_at(day, at)
    if not r["ok"]:
        return {"ok": False, "text": "", "numbers": set(), "err": r["err"]}
    req = at or "{}-{}-{} (그날 마지막 행)".format(day[:4], day[4:6], day[6:8])
    head = ["[과거 데이터 근거 — 사용자가 물은 시각: {}]".format(req),
            "실제 찾은 데이터 시각: {} — 대답에 이 시각을 반드시 말하라"
            .format(r["data"].get("at"))]
    return _evidence_from(r["data"], head)


# ────────────────────────────── 근거 (evidence) ──────────────────────────────
def evidence():
    """LLM 에게 줄 근거 텍스트 + 그 안의 숫자 집합.

    반환 {ok, text, numbers:set, err}
    ★numbers 는 llm.py 숫자 가드의 화이트리스트다 — 근거에 넣은 숫자만
      대답에 나올 수 있다. 여기 빠뜨리면 맞는 말도 막히므로, 화면에 보이는
      숫자는 전부 텍스트에 적는다.
    """
    r = compare()
    if not r["ok"]:
        return {"ok": False, "text": "", "numbers": set(),
                "err": r["err"]}
    d = r["data"]
    age = _data_age_min(d.get("at"))
    head = ["[관제 근거 — 실제 측정값. 이 블록에 있는 숫자만 말할 수 있다]",
            "지금 시각: {}".format(time.strftime("%Y-%m-%d %H:%M")),
            "데이터 시각: {} ({}) — 대답 첫머리에 이 시각을 말하라"
            .format(d.get("at"), age_text(age))]
    if age is not None and age > STALE_MIN:
        # ★분으로만 적으면 "40780분 전" 같은 말이 그대로 나간다 — 사람은
        #   그걸 못 읽고, 한 달 멈춘 수집을 '조금 늦은 값' 으로 넘긴다.
        head.append("⚠ 오래된 데이터다 — 반드시 '지금 값이 아니라 {} 값' "
                    "이라고 밝혀라. 분 단위로 바꿔 말하지 마라 "
                    "(‘{}분 전’ 은 사람이 못 읽는다).".format(age_text(age), age))
    if age is not None and age > 60 * 24:
        head.append("⚠⚠ 하루가 넘었다 — 이건 실시간이 아니다. 첫 문장에서 "
                    "'관제 수집이 멈춰 실시간 값이 아니다' 라고 먼저 말하고, "
                    "그다음에 수치를 말하라.")
    # ★관제가 '오늘 수집이 없어 옛 날짜를 보고 있다' 고 알려 주면 그대로
    #   전한다 — 이 사실을 안 말하면 옛 값을 현재로 읽는다 (실제로 그랬다).
    if d.get("warn"):
        head.append("⚠ 관제 알림: {} — 이 문장을 대답 첫머리에 그대로 전하라."
                    .format(d["warn"]))
    return _evidence_from(d, head)


# 룰 코드 → 한글 이름 (terms.py 한 곳에서 관리 — 근거·스킬·대답 세 자리에서
# 같은 표를 써야 한 군데만 새는 일이 없다).
# ★코드(RA·R-D…)를 근거에 **한 글자도 넣지 않는다.** 넣어 두면 LLM 이 그대로
#   베껴서 "R-D 룰이 켜짐" 이라고 말한다 (실제로 그랬다).
_KO = terms.KO
_CODE_RE = terms.CODE_RE
_no_code = terms.no_code


MAX_COND = 4          # 한 룰의 조건이 5개(저장·설비 포화)까지 있다 — 너무 길어진다


def _fired_lines(row, rules_by_code):
    """켜진 룰을 **실제 AMOS 컬럼·임계·실측값**으로 풀어 쓴다.

    ★'RA+RD' 같은 내부 코드만 던지면 관제는 무슨 일인지 모른다 (실제 지적).
      readings 에 룰별 컬럼·임계·그 1분 값이 이미 다 들어 있는데 안 쓰고
      있었다.

    ★정직하게 — 룰이 켜졌다고 그 1분 값이 임계를 넘은 것은 아니다.
      R-A′ 는 '최근 5분 중 3분', R-B 는 '31분 전 대비' 처럼 창(window)으로
      판정한다. 그래서 이 1분 값이 임계 미만이어도 룰은 켜질 수 있고,
      그때는 판정 방식을 같이 적어 준다 — 안 그러면 "값은 낮은데 왜
      켜졌냐" 가 된다.
    """
    fired = row.get("fired") or []
    if not fired:
        return []
    by_rule = {}
    for rd in (row.get("readings") or []):
        by_rule.setdefault(rd.get("rule"), []).append(rd)

    out = ["  켜진 룰 — 실제로 무엇이 걸렸나:"]
    for code in fired:
        meta = rules_by_code.get(code) or {}
        # 한글 이름만 쓴다 — 코드는 근거에 남기지 않는다
        name = _no_code(meta.get("label") or "") or _KO.get(code, "룰")
        pts = row.get("pts", {}).get(code)
        head = "   · {}{}".format(
            name,
            " ({}점)".format(int(pts)) if isinstance(pts, (int, float)) and pts else "")
        conds = by_rule.get(code) or []
        if not conds:
            # MAXCAPA 처럼 감시 컬럼이 CSV 에 없는 룰 — signals 텍스트가 유일한 근거
            extra = ""
            if code == "MAXCAPA" and row.get("maxcapa"):
                extra = " — 내려간 컬럼: " + ", ".join(row["maxcapa"])
            out.append(head + extra)
            if meta.get("when"):
                out.append("       판정: {}".format(_no_code(meta["when"])))
            continue
        # 임계를 넘은 조건을 먼저, 그 다음 값이 있는 것, 마지막이 값 없는 것
        conds.sort(key=lambda c: (0 if c.get("over") else
                                  1 if c.get("has_value") else 2))
        out.append(head + (" — 아래 조건 중 하나로 켜짐"
                           if len(conds) > 1 else ""))
        for c in conds[:MAX_COND]:
            thr = c.get("thr")
            op = {"<=": "≤", "diff10": "10분 +", ">=": "≥"}.get(
                c.get("op") or ">=", "≥")
            unit = c.get("unit") or ""
            thr_s = ("임계 {}{}{}".format(op, _g(thr), unit)
                     if thr is not None else "임계 미정의")
            if c.get("has_value"):
                val_s = "값 {}{}".format(_g(c.get("value")), unit)
                if c.get("over"):
                    val_s += " ← 넘음"
            else:
                val_s = "CSV 에 값 없음"
            amos = c.get("amos") or ""
            out.append("       {} · {} · {}{}".format(
                c.get("label") or "", thr_s, val_s,
                " [{}]".format(amos) if amos else ""))
        if len(conds) > MAX_COND:
            out.append("       (조건 {}개 더 있음)".format(len(conds) - MAX_COND))
        # 이 1분 값으로는 아무것도 안 넘었는데 룰이 켜졌다 — 왜인지 갈라 말한다
        if not any(c.get("over") for c in conds):
            blind = [c for c in conds if not c.get("has_value")]
            if blind:
                # R-D 처럼 조건 일부가 CSV 에 안 실려 오는 경우가 이쪽이다.
                # "조건 하나만 걸려도 켜짐" 이라고만 하면 왜 켜졌는지 여전히 모른다.
                out.append("       ※ 보이는 값은 임계 미만이다 — CSV 에 값이 "
                           "안 오는 조건 {}개 중 하나에서 걸렸을 가능성이 크다"
                           .format(len(blind)))
            elif meta.get("when"):
                out.append("       ※ 이 1분 값은 임계 미만인데 룰이 켜졌다 — "
                           "판정 방식: {}".format(_no_code(meta["when"])))
    return out


def _g(v):
    """숫자를 사람이 읽는 꼴로 (12.0 → 12)."""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def _evidence_from(d, head):
    """비교 응답(d) → 근거 텍스트. 현재/과거가 머리말만 다르고 몸은 같다."""
    cuts = d.get("cuts") or {}
    rules_by_code = {r.get("code"): r for r in (d.get("rules") or [])}
    L = list(head)
    L.append("등급 컷: 경계 {warn} · 위험 {danger} · 초위험 {critical}".format(
        warn=cuts.get("warn"), danger=cuts.get("danger"),
        critical=cuts.get("critical")))
    for row in d.get("rows") or []:
        if row.get("is_all"):
            fuse = row.get("fuse") or {}
            L.append("ALL(전체): {s}점 {lv} · 최고구역 {hot} · {stg}".format(
                s=row.get("score"), lv=row.get("level"),
                hot=row.get("hot_area") or "-",
                stg=row.get("stage_name") or "단계없음"))
            L.append("  융합: 영역합 {a} + 흐름 {f} + SLA {sl} + 소터 {so} "
                     "+ MAXCAPA {m} = raw {rw}".format(
                         a=fuse.get("areas"), f=fuse.get("flow"),
                         sl=fuse.get("sla"), so=fuse.get("sorter"),
                         m=fuse.get("maxcapa"), rw=fuse.get("raw")))
        else:
            fired = "+".join(row.get("fired") or []) or "없음"
            delta = row.get("delta")
            dtxt = ("{:+g}".format(delta) if isinstance(delta, (int, float))
                    else "이전값없음")
            L.append("{f}: 영역 {a}/{cap} · 위험도 {rk} {lv} · {m}분변화 {d}"
                     .format(f=row.get("fab"), a=row.get("area"),
                             cap=d.get("area_cap"), rk=row.get("risk"),
                             lv=row.get("level"),
                             m=d.get("delta_min"), d=dtxt))
            if row.get("mismatch"):
                L.append("  ⚠ {}".format(row["mismatch"]))
            # ★켜진 룰을 코드가 아니라 실제 컬럼·임계·실측값으로 풀어 쓴다
            L.extend(_fired_lines(row, rules_by_code))
            # 룰은 안 켜졌지만 임계를 넘긴 값이 있으면 그것도 알린다
            over_only = [rd for rd in (row.get("readings") or [])
                         if rd.get("over") and rd.get("rule") not in
                         (row.get("fired") or [])]
            for rd in over_only[:3]:
                L.append("  · (아직 룰 미발동) {lb} {v}{u} · 임계 {op}{t} [{a}]"
                         .format(lb=rd.get("label"), v=_g(rd.get("value")),
                                 u=rd.get("unit") or "",
                                 op={"<=": "≤", "diff10": "10분 +",
                                     ">=": "≥"}.get(rd.get("op") or ">=", "≥"),
                                 t=_g(rd.get("thr")),
                                 a=rd.get("amos") or "컬럼 미상"))
    if d.get("blind"):
        L.append("구조 주의: {} 는 단독으로는 전체 경보(경계 {}점)에 못 간다 "
                 "— FAB 위험도로 봐야 한다.".format(
                     ", ".join(d["blind"]), cuts.get("warn")))
    L.append("[최근 알람 이력]")
    L.append(history_text(8))
    text = "\n".join(L)
    return {"ok": True, "text": text, "numbers": _numbers(text), "err": ""}


def _numbers(text):
    """텍스트 속 숫자 집합 — 정규화해서 (12.0 == 12) 비교가 되게."""
    out = set()
    for m in re.findall(r"-?\d+(?:\.\d+)?", text or ""):
        try:
            out.add(round(float(m), 2))
        except ValueError:
            pass
    return out


def check_numbers(reply, allowed):
    """대답 속 숫자가 전부 근거에 있는가 → (통과여부, 위반숫자들).

    ★이 가드가 '헛소리 차단' 의 핵심이다. LLM 이 근거에 없는 점수를
      지어내면 여기서 걸린다. 다만 너무 빡빡하면 맞는 말도 막으므로:
      · 0~10 의 작은 정수(개수 세기·문장 나열)는 허용
      · 근거 숫자의 반올림(24.0 → 24)은 허용
    """
    bad = []
    for n in _numbers(reply):
        if n in allowed:
            continue
        if float(n).is_integer() and 0 <= n <= 10:
            continue
        if round(n) in allowed or round(n, 1) in allowed:
            continue
        # 반대 방향 반올림 — 근거 15.98 을 "16분" 이라고 말하는 건 거짓이 아니다
        if any(round(a) == n or round(a, 1) == n for a in allowed):
            continue
        bad.append(n)
    return (not bad), bad


# ────────────────────────────── 결정적 요약 (폴백) ──────────────────────────────
def plain_status(d=None, past=False):
    """LLM 없이/검증 실패 시 내보내는 상태 요약 — 숫자는 전부 근거 그대로.

    ★날짜·시각을 반드시 말한다 — '지금 몇 시고, 이 값은 언제 값인지'.
      점수만 던지면 어제 값을 지금 값으로 읽는다 (실제 요청 사항).
    """
    if d is None:
        r = compare()
        if not r["ok"]:
            return ("관제 서버에 연결이 안 돼요. ({}) real_time_amhs 서버가 떠 "
                    "있는지 확인해 주세요. 지금은 상태를 알 수 없어요 — "
                    "모르는 건 모른다고 말할게요.".format(r["err"]))
        d = r["data"]
    age = _data_age_min(d.get("at"))
    rows = d.get("rows") or []
    all_row = rows[0] if rows and rows[0].get("is_all") else None
    parts = []
    if all_row:
        parts.append("전체 {s}점 {lv}".format(
            s=all_row.get("score"), lv=all_row.get("level")))
    worst = [x for x in rows[1:] if LEVEL_ORDER.get(x.get("level"), 0) >= 1]
    if worst:
        parts.append("주의 구역: " + ", ".join(
            "{f} {lv}({rk}점)".format(f=x["fab"], lv=x["level"], rk=x["risk"])
            for x in worst))
    else:
        parts.append("경계 이상인 FAB 없음")
    # ★켜진 룰이 있으면 코드가 아니라 컬럼·값으로 붙인다 — 이 요약은 LLM 을
    #   안 거치고 그대로 화면에 나가므로, 여기서 'RA+RD' 를 쓰면 그대로 보인다.
    detail = []
    for x in rows[1:]:
        for rd in (x.get("readings") or []):
            if rd.get("over") and rd.get("rule") in (x.get("fired") or []):
                detail.append("{f} {lb} {v}{u}(임계 {op}{t})".format(
                    f=x["fab"], lb=rd.get("label"), v=_g(rd.get("value")),
                    u=rd.get("unit") or "",
                    op={"<=": "≤", "diff10": "10분 +", ">=": "≥"}.get(
                        rd.get("op") or ">=", "≥"),
                    t=_g(rd.get("thr"))))
    if detail:
        parts.append("임계 넘은 값: " + " · ".join(detail[:4]))
    # ★두 시각을 다 말한다 — 지금이 몇 시고, 이 값이 언제 값인지
    head = "지금 {} · 데이터 {} 기준".format(
        time.strftime("%H:%M"), d.get("at"))
    # 일부러 과거를 물었을 때 '오래된 값' 경고는 군더더기다
    if not past and age is not None and age > STALE_MIN:
        head += " (⚠ {} 값)".format(age_text(age))
    return head + " — " + " · ".join(parts) + "."


def plain_status_at(day, at=None):
    """과거 한 시각의 결정적 요약 — /상태 어제 08:20 같은 조회."""
    r = _fetch_at(day, at)
    if not r["ok"]:
        return "과거 데이터를 못 읽었어요 ({}).".format(r["err"])
    msg = plain_status(r["data"], past=True)
    return "과거 조회예요 (물은 시각: {}) — {}".format(
        at or "{}-{}-{} 마지막 행".format(day[:4], day[4:6], day[6:8]), msg)


# ────────────────────────────── 진단 (데이터 문제 찾기) ──────────────────────────────
def diagnose():
    """도메인 지식으로 데이터 문제를 찾는다 — '무엇을 해결해야 하나'.

    화면에 보이는 증상이 아니라 **데이터 자체의 문제**를 본다:
      · 점수 재현 불일치 (pts 합 ≠ 저장 점수 — 예측기 배점 변경 신호)
      · 임계 미정의 (룰은 도는데 기준이 없음)
      · 룰은 보는데 CSV 에 값이 안 오는 컬럼 (화면에서 근거를 못 봄)
      · 화면에 없는 점수 구성 항 (왜 그 점수인지 화면에서 못 짚음)
      · 오래된 데이터 (수집이 멈췄을 가능성)
    반환 {ok, problems:[{what, why, fix}...], err}
    """
    problems = []
    r = compare()
    if not r["ok"]:
        return {"ok": False, "problems": [], "err": r["err"]}
    d = r["data"]
    age = _data_age_min(d.get("at"))
    if age is not None and age > STALE_MIN:
        problems.append({
            "what": "데이터가 {} 것".format(age_text(age)),
            "why": "수집(주피터 CSV)이 멈췄거나 그 날짜 파일이 아직 없다",
            "fix": "관제 서버 로그에서 [수집] 줄과 주피터 로그인 오류를 확인"})
    for row in d.get("rows") or []:
        if row.get("mismatch"):
            problems.append({
                "what": "{} 점수 재현 불일치".format(row.get("fab")),
                "why": row["mismatch"],
                "fix": "예측기(hubroom_predictor.py) 배점이 바뀌었는지 확인 — "
                       "바뀌었으면 fab_score 의 RULES 를 맞춘다"})
    c = columns()
    if c["ok"]:
        for s, info in (c["data"].get("fabs") or {}).items():
            j = info.get("join") or {}
            undef = [m["key"] for m in (j.get("metrics") or [])
                     if m.get("used") and any(t is None for t in m.get("thr") or [])
                     and any(o not in ("sum", "score", "text", "ratio30")
                             for o in m.get("op") or [">="])]
            if undef:
                problems.append({
                    "what": "{} 임계 미정의: {}".format(s, ", ".join(undef)),
                    "why": "룰은 이 컬럼을 보는데 기준값이 없다 — 판정 불가",
                    "fix": "thresholds.json 확인 후 config.fab_score.thresholds 에 기입"})
            miss = [x["key"] for x in (j.get("only_rule") or [])]
            if miss:
                problems.append({
                    "what": "{} 화면에 없는 점수 구성 항: {}".format(
                        s, ", ".join(miss[:6])),
                    "why": "점수는 이 값으로 만들어지는데 추이 그래프 목록에 없다 "
                           "— '왜 이 점수인가' 를 화면에서 못 짚는다",
                    "fix": "config.ui.metric_groups 에 추가하면 바로 그려진다"})
            nocsv = j.get("no_csv") or []
            if nocsv:
                problems.append({
                    "what": "{} CSV 에 값이 안 오는 감시 컬럼 {}개".format(
                        s, len(nocsv)),
                    "why": "룰은 켜지는데 근거 값이 화면에 안 뜬다 (예: {})".format(
                        (nocsv[0].get("raw") or "")[:60]),
                    "fix": "예측 잡이 해당 컬럼을 CSV 에 실어 주도록 요청"})
    return {"ok": True, "problems": problems, "err": ""}


def diagnose_text():
    """진단 결과를 사람이 읽을 한 덩어리로. LLM 근거로도 그대로 쓴다."""
    d = diagnose()
    if not d["ok"]:
        return "관제 서버에 연결이 안 돼서 진단할 수 없어요. ({})".format(d["err"])
    if not d["problems"]:
        return "지금 데이터에서 짚이는 문제가 없어요. (재현 일치 · 임계 정의됨 · 데이터 최신)"
    L = ["짚이는 문제 {}건:".format(len(d["problems"]))]
    for i, p in enumerate(d["problems"], 1):
        L.append("{}. {} — {}. 조치: {}".format(i, p["what"], p["why"], p["fix"]))
    return "\n".join(L)
