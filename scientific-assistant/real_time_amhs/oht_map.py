#!/usr/bin/env python3
"""
real_time_amhs/oht_map.py — 주피터의 날짜별 OHT_MAP CSV (HID 정체 · PROBLEM_MAP 레포트)

무엇
    허브룸 예측 잡이 날짜마다 OHT_MAP_{day}.csv 를 떨군다 (그 분에 일이 있으면 한 줄).
        날짜,시간,FAB,ALARM_KR,ALARM_EN,HID_ZONE,HID_section,OHT_report,OHT_missing,
        OHT_JAM,ZONE_STOP,FILE_NAME,FILE_PATH
    실시간 · 과거 표의 '실제지표' 옆 두 칸이 이걸 쓴다.
        HID_JAM      ← HID_ZONE
        RET(레포트)  ← FILE_PATH 의 PROBLEM_MAP html — '링크' 를 누르면 내려받는다

어디서
    발동이벤트 CSV 와 **같은 주피터**다 — 주소 · 비밀번호는 config.source.jupyter 를 그대로 쓴다
    (로그인 세션도 jupyter_csv 것을 같이 쓴다). 파일 자리만 config.source.oht_map 으로
    바꿀 수 있고, 없으면 아래 DEFAULTS 다.

받는 법
    오늘    — 화면이 물을 때 **뒤에서** refresh_s(60초)마다 다시 받는다. 3초마다 묻는
              실시간 표를 주피터 왕복만큼 세워 두지 않는다.
    지난 날 — 그 날짜를 볼 때마다 **그 자리에서** 다시 받아, 내용이 달라졌으면 그 날짜 것을
              다시 등록한다 (고객: "과거 데이터는 데이터가 달라지면 재등록 — 해당 날짜에").
              recheck_s(10초) 안에 또 보면 건너뛴다.
    받은 원본은 data/oht_map/ 에 둔다 — 주피터에 못 닿을 때는 이 보관본으로 보인다.
    레포트 html — 그날 CSV 에 적힌 파일만 내준다 (화면이 준 경로로 주피터에서 아무 파일이나
              끌어오지 않게). 다시 만들어질 수 있어 보관하지 않고 누를 때마다 새로 받는다.

단독 실행
    python oht_map.py               # 오늘 받아서 몇 줄인지
    python oht_map.py 20261003      # 그 날
"""
from __future__ import annotations

import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import jupyter_csv
from lp_client import load_config

DEFAULTS = {
    "enabled": True,
    "path": "/files/pjt_shared_pool/job/m16a_hubroom_event_prediction/oht_map/OHT_MAP_{day}.csv",
    "file_root": "/project/",    # FILE_PATH 의 이 앞부분이 주피터 /files/ 아래다
    "refresh_s": 60,             # 오늘 파일을 다시 받는 간격
    "recheck_s": 10,             # 지난 날을 또 볼 때 이 안이면 다시 안 받는다
    "timeout_s": 15,             # 한 번 받는 데 기다리는 시간 (과거 탭은 기다리며 받는다)
    "retry_s": 300,              # 못 받았으면(없는 날 404 등) 이만큼은 다시 안 친다
}

# 화면으로 보내는 값 — FILE_PATH(서버 경로)는 안 보낸다
PUBLIC = ("d", "t", "f", "lv", "en", "z", "s", "rep", "miss", "jam", "stop", "file")

_LOCK = threading.Lock()
_DAY: dict = {}      # day → {"rows", "sig", "t", "checked", "err", "err_t", "busy"}
_NAME = re.compile(r"^[\w.\-]+\.html?$")


def cfg_of(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    c = dict(DEFAULTS)
    c.update((cfg.get("source") or {}).get("oht_map") or {})
    return c


# ────────────────────────────── 주피터에서 받기 ──────────────────────────────
def _login_page(raw: bytes) -> bool:
    """세션이 끊기면 파일 대신 로그인 폼이 온다 (주피터는 302 → /login 이 보통)."""
    return bool(re.search(rb"<input[^>]+name=['\"]password['\"]", raw[:20000], re.I))


def _get(path: str, cfg: dict, om: dict, want_csv: bool) -> tuple[bytes | None, str]:
    """주피터 /files/… 한 개 → (원문, 오류). 로그인은 발동이벤트와 같은 세션을 쓴다.

    ★막히면(403 · 로그인 폼) 한 번만 새로 로그인해서 다시 받는다 — jupyter_csv 와 같은 규칙.
    ★발동이벤트의 이어받기(Range) 캐시는 안 건드린다. jupyter_csv.download 를 그대로 부르면
      그 캐시에 이 파일을 덮어써서, 다음 발동이벤트 수집이 통째로 다시 받게 된다.
    """
    jc = jupyter_csv.cfg_of(cfg)
    if not str(jc.get("base_url") or "").strip():
        return None, "config.source.jupyter.base_url 이 비어 있습니다"
    try:
        url = jupyter_csv.file_url("", dict(jc, path=path))
    except ValueError as e:
        return None, str(e)
    wait = float(om.get("timeout_s") or 15)
    for fresh in (False, True):
        s, err = jupyter_csv.login(jc, fresh=fresh)
        if err:
            return None, err
        try:
            r = s.opener.open(urllib.request.Request(url), timeout=wait)
            raw, final = r.read(), (r.geturl() or "")
        except urllib.error.HTTPError as e:
            if e.code in (302, 403) and not fresh:
                continue                                   # 쿠키가 만료됐을 수 있다 — 한 번만
            if e.code == 404:
                return None, "HTTP 404 — 주피터에 아직 없는 파일입니다"
            return None, f"HTTP {e.code}"
        except Exception as e:                             # noqa: BLE001
            return None, f"{type(e).__name__}: {e}"
        if "/login" in final or _login_page(raw):
            if not fresh:
                continue
            return None, "주피터 로그인이 안 됩니다 — 발동이벤트와 같은 비밀번호인지 확인하세요"
        if want_csv and raw[:400].lstrip().lower().startswith((b"<!doctype html", b"<html")):
            return None, "CSV 가 아니라 HTML 이 왔습니다"
        return raw, ""
    return None, "주피터 로그인이 안 됩니다"


def jupyter_path(file_path: str, om: dict | None = None) -> str:
    """CSV 의 FILE_PATH(/project/…/x.html) → 주피터 내려받기 경로(/files/…/x.html)."""
    om = om or DEFAULTS
    p = str(file_path or "").strip().replace("\\", "/")
    root = "/" + str(om.get("file_root") or "/project/").strip("/") + "/"
    p = p[len(root):] if p.startswith(root) else p.lstrip("/")
    if not p or ".." in p.split("/"):
        raise ValueError(f"레포트 경로가 이상합니다: {file_path!r}")
    return "/files/" + p


# ────────────────────────────── CSV 읽기 ──────────────────────────────
def parse(raw: bytes) -> list[dict]:
    """OHT_MAP 원문 → 줄 목록 (짧은 이름으로). 날짜 · 시간을 못 읽는 줄은 버린다."""
    out = []
    for r in jupyter_csv.parse_csv(raw, {"encoding": "utf-8-sig"}):
        R = {str(k or "").strip().lower(): str(v or "").strip() for k, v in r.items()}
        d = re.sub(r"\D", "", R.get("날짜", ""))[:8]
        m = re.match(r"^(\d{1,2}):(\d{2})", R.get("시간", ""))
        if len(d) != 8 or not m:
            continue
        out.append({
            "d": d, "t": f"{int(m.group(1)):02d}:{m.group(2)}",
            "f": R.get("fab", "").upper(),
            "lv": R.get("alarm_kr", ""), "en": R.get("alarm_en", ""),
            "z": R.get("hid_zone", ""), "s": R.get("hid_section", ""),
            "rep": R.get("oht_report", ""), "miss": R.get("oht_missing", ""),
            "jam": R.get("oht_jam", ""), "stop": R.get("zone_stop", ""),
            "file": R.get("file_name", ""), "path": R.get("file_path", ""),
        })
    return out


# ────────────────────────────── 날짜별 보관 ──────────────────────────────
def _dir(cfg: dict) -> str:
    from store_csv import data_dir
    d = os.path.join(data_dir(cfg), "oht_map")
    os.makedirs(d, exist_ok=True)
    return d


def _disk(day: str, cfg: dict) -> str:
    return os.path.join(_dir(cfg), f"OHT_MAP_{day}.csv")


def _put(day: str, raw: bytes, t: float, checked: float = 0.0) -> None:
    """그 날 줄을 (다시) 등록한다. checked — 주피터에서 확인한 시각 (보관본이면 0)."""
    import hashlib
    rows = parse(raw)
    with _LOCK:
        e = _DAY.setdefault(day, {})
        e.update(rows=rows, sig=hashlib.sha1(raw).hexdigest()[:12], t=t,
                 checked=checked, err="", err_t=0.0)


def _from_disk(day: str, cfg: dict) -> None:
    p = _disk(day, cfg)
    if not os.path.isfile(p):
        return
    try:
        with open(p, "rb") as f:
            raw = f.read()
        _put(day, raw, os.path.getmtime(p))
    except OSError as e:
        print(f"[OHT_MAP] ⚠️ {p} 읽기 실패: {e}")


def refresh(day: str, cfg: dict | None = None) -> dict:
    """그 날 파일을 지금 받아 **다시 등록**한다 (실패하면 있던 줄은 그대로 둔다).

    돌려주는 changed — 전에 등록한 것과 내용이 달랐나 (처음이면 True).
    """
    cfg = cfg or load_config()
    om = cfg_of(cfg)
    raw, err = _get(str(om.get("path") or "").replace("{day}", day), cfg, om, want_csv=True)
    now = time.time()
    if err:
        with _LOCK:
            e = _DAY.setdefault(day, {})
            e.update(err=err, err_t=now)
        print(f"[OHT_MAP] {day} 못 받음 — {err}")
        return {"ok": False, "day": day, "error": err}
    import hashlib
    with _LOCK:
        old = str((_DAY.get(day) or {}).get("sig") or "")
    changed = old != hashlib.sha1(raw).hexdigest()[:12]
    p = _disk(day, cfg)
    if changed or not os.path.isfile(p):
        try:                                        # 반쯤 쓴 파일을 남기지 않는다
            with open(p + ".part", "wb") as f:
                f.write(raw)
            os.replace(p + ".part", p)
        except OSError as e:
            print(f"[OHT_MAP] ⚠️ 저장 실패 (화면에는 씁니다): {e}")
        if old and changed:
            print(f"[OHT_MAP] {day} 주피터 파일이 바뀌어 다시 등록했습니다")
    _put(day, raw, now, checked=now)
    with _LOCK:
        n = len(_DAY[day]["rows"])
    return {"ok": True, "day": day, "rows": n, "changed": changed}


def _bg(day: str, cfg: dict) -> None:
    try:
        refresh(day, cfg)
    finally:
        with _LOCK:
            _DAY.setdefault(day, {})["busy"] = False


def ensure(day: str, cfg: dict | None = None, wait: bool | None = None) -> None:
    """그 날 줄을 쓸 수 있게 해 둔다 — 주피터 파일이 달라졌으면 다시 등록한다.

    wait — None 이면 오늘은 뒤에서, 지난 날은 그 자리에서 받는다.
    """
    cfg = cfg or load_config()
    om = cfg_of(cfg)
    if not om.get("enabled", True) or not re.fullmatch(r"\d{8}", day or ""):
        return
    today = datetime.now().strftime("%Y%m%d")
    with _LOCK:
        known = day in _DAY
    if not known:
        _from_disk(day, cfg)                        # 보관본 먼저 — 주피터에 못 닿아도 보이게
    now = time.time()
    with _LOCK:
        e = dict(_DAY.get(day) or {})
    if e.get("busy"):
        return
    if e.get("err_t") and now - e["err_t"] < float(om.get("retry_s") or 300):
        return
    gap = float(om.get("refresh_s") or 60) if day == today else float(om.get("recheck_s") or 0)
    if e.get("checked") and now - e["checked"] < gap:
        return
    if wait is None:
        wait = day != today
    if wait:
        refresh(day, cfg)
        return
    with _LOCK:
        if _DAY.setdefault(day, {}).get("busy"):
            return
        _DAY[day]["busy"] = True
    threading.Thread(target=_bg, args=(day, cfg), daemon=True,
                     name=f"oht_map-{day}").start()


def sig(day: str) -> str:
    """그 날 받은 원문의 지문 — 바뀌면 화면 응답(캐시)을 다시 만든다."""
    with _LOCK:
        return str((_DAY.get(day) or {}).get("sig") or "")


def by_time(day: str, sys_: str = "ALL") -> dict:
    """'HH:MM' → 그 분의 줄 목록. FAB 화면이면 그 FAB 것만 (ALL 은 전부)."""
    sys_ = str(sys_ or "ALL").strip().upper()
    with _LOCK:
        rows = list((_DAY.get(day) or {}).get("rows") or [])
    out: dict = {}
    for r in rows:
        if sys_ != "ALL" and r["f"] and r["f"] != sys_:
            continue
        out.setdefault(r["t"], []).append({k: r[k] for k in PUBLIC})
    return out


# ────────────────────────────── 레포트 ──────────────────────────────
def report(day: str, name: str, cfg: dict | None = None) -> tuple[bytes | None, str]:
    """RET(레포트) — 그 날 CSV 에 적힌 PROBLEM_MAP html 을 받아 준다 (원문, 오류)."""
    cfg = cfg or load_config()
    om = cfg_of(cfg)
    name = str(name or "").strip()
    day = re.sub(r"\D", "", str(day or ""))[:8]
    if len(day) != 8 or not _NAME.match(name):
        return None, "레포트 이름이 이상합니다"

    def find():
        with _LOCK:
            rows = (_DAY.get(day) or {}).get("rows") or []
        return next((r for r in rows if r["file"] == name), None)

    ensure(day, cfg, wait=True)
    hit = find()
    if hit is None:                     # 방금 생긴 줄일 수 있다 — 한 번 더 받아 본다
        refresh(day, cfg)
        hit = find()
    if hit is None or not hit.get("path"):
        return None, f"{day} OHT_MAP 에 없는 레포트입니다: {name}"
    try:
        path = jupyter_path(hit["path"], om)
    except ValueError as e:
        return None, str(e)
    # ★보관하지 않고 누를 때마다 새로 받는다 — 레포트가 다시 만들어지면 그게 나가야 한다
    return _get(path, cfg, om, want_csv=False)


if __name__ == "__main__":
    d = (sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d"))[:8]
    r = refresh(d)
    print(r)
    for t, hs in sorted(by_time(d).items())[-5:]:
        print(t, hs)
