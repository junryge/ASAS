# -*- coding: utf-8 -*-
"""등급 카운터 — 최근 N분 동안 경계·위험·초위험이 **몇 번** 떴나.

왜 필요한가
    점수는 1분마다 오르내린다. 62점 한 번은 스쳐 지나간 것일 수 있지만,
    10분에 네 번이면 그건 계속되고 있는 것이다. 지금 화면은 '그 1분이
    몇 점인가' 만 말하고 '얼마나 계속되는가' 는 말하지 않는다.
    현장 규칙(고객 지정):
        10분에 경계 3~4회   → 모니터링    (경계중)
        10분에 위험 1~2회   → 확인 필요    (위험중)
        10분에 초위험 1회    → 확인 필요    (초위험중)

시스템(ALL·FAB 다섯)마다 따로다
    FAB 마다 점수 분포가 달라 등급 컷이 다르고(grade.by_sys), 그러면 등급이
    뜨는 빈도도 다르다. 컷이 시스템별인데 세는 기준만 공통이면 어느 FAB 은
    하루 종일 '위험중' 이고 어느 FAB 은 영영 안 뜬다. 그래서 컷과 **같은 모양**
    으로 grade.alarm_by_sys 에 시스템별 설정을 둔다 — 적용/미적용도 각각.
    기본(공통)은 grade.alarm 이고, 시스템 칸이 있으면 그것이 이긴다.

무엇을 안 하나
    ★점수를 만들지도, 등급 컷을 바꾸지도 않는다. 이미 매겨진 등급을
      **세기만** 한다. fab_score·sentinel 의 계산은 한 줄도 안 건드린다.
    ★창은 **시각**으로 센다(행 개수가 아니라). 수집이 몇 분 빠진 날
      행으로 세면 10분 창이 20분이 된다.

상위 등급은 하위도 켠 것으로 센다
    위험인 1분은 '경계값도 넘은' 1분이다. 그래서 경계 카운트는 '경계 이상',
    위험 카운트는 '위험 이상' 을 센다. 안 그러면 점수가 위험에 눌러앉은
    동안 경계 카운트가 0이 되어, 제일 나쁜 구간에서 알람이 꺼진다.
"""
from __future__ import annotations

from datetime import timedelta

# 등급 → 높이. 이 이름은 sentinel.grade() 가 돌려주는 level 글자 그대로다.
RANK = {"경계": 1, "위험": 2, "초위험": 3}
# 카운트가 차면 붙는 이름표
LABEL = {1: "경계중", 2: "위험중", 3: "초위험중"}

DEFAULTS = {
    "enabled": True,     # 정책 탭의 적용 / 미적용
    "window_min": 10,    # 몇 분을 되돌아보나
    "warn": 3,           # 경계 이상 N회 → 경계중   (0 = 이 단계 안 씀)
    "danger": 1,         # 위험 이상 N회 → 위험중
    "critical": 1,       # 초위험 N회   → 초위험중
}
KEYS = ("warn", "danger", "critical")
LIMITS = {"window_min": (1, 180), "warn": (0, 999),
          "danger": (0, 999), "critical": (0, 999)}


def sys_of(cfg: dict | None = None, sys: str | None = None) -> str:
    """이 설정이 어느 시스템 것인가.

    ★sys 를 안 받아도 알아낸다 — lp_client.sys_cfg() 가 만든 뷰에는 `_sys` 가
      박혀 있다. 덕분에 부르는 쪽(server.py 의 여러 자리)이 시스템을 따로
      들고 다니지 않아도 되고, 함수 서명이 안 바뀐다 (배포는 파일 단위다).
    """
    s = str(sys or (cfg or {}).get("_sys") or "ALL").strip().upper()
    return s or "ALL"


def _merge(out: dict, a: dict) -> dict:
    """설정 한 벌을 out 위에 덮는다 (범위 밖·이상한 값은 버린다)."""
    for k in out:
        if k == "enabled":
            if k in a:
                out[k] = bool(a[k])
            continue
        try:
            n = int(a[k])
        except (KeyError, TypeError, ValueError):
            continue
        lo, hi = LIMITS[k]
        out[k] = max(lo, min(hi, n))
    return out


def policy(cfg: dict | None = None, sys: str | None = None) -> dict:
    """그 **시스템**의 설정 한 벌 (기본 ← grade.alarm ← grade.alarm_by_sys[시스템]).

    ★등급 컷(grade_cuts/by_sys)과 같은 차례다. 두 정책이 다른 길로 풀리면
      '컷은 M14 것인데 카운터는 공통' 같은 어긋남이 난다.
    """
    g = ((cfg or {}).get("grade") or {})
    out = _merge(dict(DEFAULTS), g.get("alarm") or {})
    row = (g.get("alarm_by_sys") or {}).get(sys_of(cfg, sys))
    if isinstance(row, dict):
        out = _merge(out, row)
    return out


def is_custom(cfg: dict | None = None, sys: str | None = None) -> bool:
    """이 시스템이 공통값이 아니라 자기 값을 들고 있나 (화면의 '개별 설정')."""
    g = ((cfg or {}).get("grade") or {})
    return isinstance((g.get("alarm_by_sys") or {}).get(sys_of(cfg, sys)), dict)


def table(cfg: dict | None = None, systems=()) -> list[dict]:
    """시스템 목록 → 화면이 그대로 그리는 표 (등급 컷의 systems 응답과 같은 모양)."""
    return [dict(policy(cfg, s), sys=s, custom=is_custom(cfg, s)) for s in systems]


def sig(cfg: dict | None = None, sys: str | None = None) -> str:
    """이 설정의 지문 — 캐시 키·렌더 서명에 넣는다.

    ★안 넣으면 '정책을 바꿨는데 화면이 그대로' 가 난다. 등급 컷에서 이미
      똑같이 당했다 (server.py `_sig` 주석).
    ★시스템 이름도 넣는다. 안 넣으면 M14 화면과 ALL 화면이 설정값만 같으면
      같은 지문이 되어, 캐시가 남의 화면 응답을 내줄 수 있다.
    """
    p = policy(cfg, sys)
    return sys_of(cfg, sys) + ":" + "|".join(
        f"{k}={p[k]}" for k in ("enabled", "window_min", *KEYS))


def label_of(c1: int, c2: int, c3: int, pol: dict) -> str:
    """세 카운트 → 이름표. 높은 등급이 이긴다. 기준이 0이면 그 단계는 안 쓴다."""
    if pol["critical"] and c3 >= pol["critical"]:
        return LABEL[3]
    if pol["danger"] and c2 >= pol["danger"]:
        return LABEL[2]
    if pol["warn"] and c1 >= pol["warn"]:
        return LABEL[1]
    return ""


def scan(seq, cfg: dict | None = None, sys: str | None = None) -> list[dict]:
    """[(시각, 등급)] **오름차순** → 행마다 {warn, danger, critical, label, ...}.

    창은 (t − N분, t] — 지금 분을 포함한 지난 N분이다.
    돌려주는 것은 들어온 순서 그대로라, 부른 쪽이 zip 으로 붙이면 된다.
    """
    pol = policy(cfg, sys)
    out = []
    if not pol["enabled"]:
        return [dict(warn=0, danger=0, critical=0, label="", window_min=pol["window_min"],
                     enabled=False) for _ in seq]
    win = timedelta(minutes=pol["window_min"])
    buf: list = []          # 창 안 (시각, 높이) — 오름차순
    head = 0                # 창 밖으로 나간 자리 (pop(0) 대신 색인으로 — O(n))
    for t, lv in seq:
        r = RANK.get(str(lv or "").strip(), 0)
        buf.append((t, r))
        while head < len(buf) and buf[head][0] <= t - win:
            head += 1
        c1 = c2 = c3 = 0
        for _t, rr in buf[head:]:
            if rr >= 1:
                c1 += 1
            if rr >= 2:
                c2 += 1
            if rr >= 3:
                c3 += 1
        out.append(dict(warn=c1, danger=c2, critical=c3,
                        label=label_of(c1, c2, c3, pol),
                        window_min=pol["window_min"], enabled=True))
        # 다 쓴 앞부분은 실제로 버린다 (하루 1440행이면 창 밖이 대부분이다)
        if head > 256:
            del buf[:head]
            head = 0
    return out


def why(row: dict, pol: dict | None = None) -> str:
    """이름표가 왜 붙었나 — 화면 말풍선에 그대로 쓴다."""
    if not row or not row.get("label"):
        return ""
    p = pol or DEFAULTS
    n = row["window_min"]
    if row["label"] == LABEL[3]:
        return f"최근 {n}분에 초위험 {row['critical']}회 (기준 {p['critical']}회)"
    if row["label"] == LABEL[2]:
        return f"최근 {n}분에 위험 이상 {row['danger']}회 (기준 {p['danger']}회)"
    return f"최근 {n}분에 경계 이상 {row['warn']}회 (기준 {p['warn']}회)"
