#!/usr/bin/env python3
"""
관제 목록 → OHT 월드모델 잇기.

무엇을 하나
    관제 목록에서 행을 더블클릭하면 그 1분의 구간 그래프가 뜬다. 거기서
    FAB 을 누르면 **그 1분 동안 OHT 가 실제로 어떻게 움직였는지**를 월드모델
    (월드모델/월드모델파생, 별도 프로세스 · 기본 10005 포트)에서 재생한다.

        10:35 행 더블클릭 → M16HUB 누름
        → 20260831103500 ~ 20260831103600 · oht_data_m16br 로 조회 · 재생

왜 별도 프로세스인가
    월드모델은 FastAPI + pandas + requests 로 돌고, 관제는 Flask + 표준
    라이브러리다. 한 프로세스에 합치면 관제가 pandas 를 끌고 오게 되고,
    월드모델 재생 상태(전역 엔진 하나)가 관제 수집 루프와 얽힌다.
    여기서는 **주소만 만들어 준다** — 실제 조회는 월드모델이 한다.

★M16 은 A · BR · E 세 레이아웃이 있다
    OHT_MAP/MAP/M16A/ 아래에 A.layout.zip · BR.layout.zip · E.layout.zip 이
    같이 있다. 우리가 쓰는 것은 **A(=M16A) 와 BR(=M16BR, 허브룸)** 둘이다.
    E 를 잘못 고르면 맵이 통째로 다른 구역이 뜬다 — 그래서 여기에 못 박는다.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

# 관제 FAB → (로그프레소 테이블, 월드모델 FAB, 월드모델 prefix)
#   테이블 이름은 현장에서 받은 그대로다 (대소문자까지).
#   FAB/prefix 는 OHT_MAP/cache 에 있는 레이아웃 이름과 1:1 이다:
#       M14A_A · M14B_A · M16A_A · M16A_BR · M16A_E · M16B_B
MAP = {
    "M14":    {"table": "oht_data_m14a",  "fab": "M14A", "prefix": "A"},
    "M14B":   {"table": "oht_data_m14b",  "fab": "M14B", "prefix": "A"},
    "M16A":   {"table": "oht_data_m16A",  "fab": "M16A", "prefix": "A"},
    "M16B":   {"table": "oht_data_m16B",  "fab": "M16B", "prefix": "B"},
    # ★허브룸. 레이아웃은 M16A 폴더 아래의 BR 이다 (M16BR).
    "M16HUB": {"table": "oht_data_m16br", "fab": "M16A", "prefix": "BR"},
}

DEFAULTS = {
    "enabled": True,
    "base": "",          # 비우면 화면이 보고 있는 host 의 10005 를 쓴다
    "port": 10005,
    "minutes": 1,        # 한 번에 볼 구간 — 기본 1분
    "timeout_s": 2.0,    # 살아 있나 두들겨 보는 시간
}

FMT = "%Y%m%d%H%M%S"


def cfg_of(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg or {}).get("world_model") or {})
    return c


def fabs() -> list[str]:
    """버튼으로 낼 FAB 순서 — 관제 표의 컬럼 순서와 같게."""
    return ["M14", "M14B", "M16A", "M16B", "M16HUB"]


def window(at: str | datetime, minutes: int = 1) -> tuple[str, str]:
    """그 행의 시각 → (from_dt, to_dt) 14자리.

    ★초를 버리고 그 분의 00초부터 잡는다. 10:35:47 행을 눌렀는데 조회가
      10:35:47~10:36:47 로 나가면, 사람이 화면에서 본 '10:35 한 칸' 과
      구간이 어긋난다.
    """
    t = at if isinstance(at, datetime) else _parse(at)
    if t is None:
        raise ValueError(f"시각을 못 읽었다: {at!r}")
    t = t.replace(second=0, microsecond=0)
    return t.strftime(FMT), (t + timedelta(minutes=max(1, int(minutes)))).strftime(FMT)


def _parse(s: str) -> datetime | None:
    s = str(s or "").strip()
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
              "%Y-%m-%dT%H:%M", FMT):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def target(fab: str) -> dict | None:
    """관제 FAB → 월드모델이 알아야 할 것 전부 (모르는 이름이면 None)."""
    return MAP.get(str(fab or "").strip().upper())


def base_url(cfg: dict, host_hint: str = "") -> str:
    """월드모델 주소.

    ★설정에 없으면 **화면이 보고 있는 host** 의 10005 를 쓴다. 관제와
      월드모델은 같은 기계에서 도는 것이 보통인데, 여기에 localhost 를
      박아 두면 다른 PC 에서 관제를 열었을 때 그 사람의 PC 를 찾아간다.
    """
    c = cfg_of(cfg)
    b = str(c.get("base") or "").strip().rstrip("/")
    if b:
        return b
    h = (host_hint or "127.0.0.1").split(":")[0].strip() or "127.0.0.1"
    return f"http://{h}:{int(c.get('port') or 10005)}"


def link(fab: str, at: str, cfg: dict, host_hint: str = "",
         label: str = "") -> dict | None:
    """버튼 하나가 열 주소 — 월드모델이 이것만 보고 스스로 조회한다.

    ★label 을 같이 실어 보낸다. 이 화면은 **증거 자료**로 쓰인다 —
      "그때 OHT 가 이랬다" 를 남기려면 어느 케이스의 그림인지가 같이
      찍혀 있어야 한다. 시각만 있고 점수·등급이 없으면, 며칠 뒤에
      그 그림만 봐서는 무슨 건이었는지 알 수 없다.
    """
    t = target(fab)
    if not t:
        return None
    c = cfg_of(cfg)
    f_dt, t_dt = window(at, c["minutes"])
    from urllib.parse import urlencode
    q = {"from": f_dt, "to": t_dt, "table": t["table"],
         "fab": t["fab"], "prefix": t["prefix"], "auto": "1"}
    if label:
        q["case"] = str(label)[:120]
    return {"fab": fab, "table": t["table"], "wm_fab": t["fab"],
            "prefix": t["prefix"], "from": f_dt, "to": t_dt,
            "label": label,
            "url": f"{base_url(cfg, host_hint)}/?{urlencode(q)}"}


def links(at: str, cfg: dict, host_hint: str = "",
          label: str = "") -> list[dict]:
    return [x for x in (link(f, at, cfg, host_hint, label) for f in fabs()) if x]


def alive(cfg: dict, host_hint: str = "") -> dict:
    """월드모델이 떠 있나 — 화면이 '안 떠 있다' 를 말해 줄 수 있게.

    ★죽어 있는데 버튼만 열어 두면 새 창이 뜨고 빈 화면이 나온다. 무엇을
      해야 하는지(그 폴더에서 python main.py)까지 같이 알려 준다.
    """
    c = cfg_of(cfg)
    url = base_url(cfg, host_hint) + "/api/status"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        # 같은 기계 안의 주소다 — 사내 프록시를 타면 안 된다
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=float(c["timeout_s"])) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
        return {"ok": True, "base": base_url(cfg, host_hint), "status": body}
    except Exception as e:                                  # noqa: BLE001
        return {"ok": False, "base": base_url(cfg, host_hint),
                "error": f"{type(e).__name__}: {e}",
                "how": "월드모델/월드모델파생 폴더에서 python main.py 를 띄우세요"}
