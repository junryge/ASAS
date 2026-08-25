"""
real_time_amhs/forecast.py — 선행 감지 (임계 돌파 예보 + 선행 지표 분석)

왜 필요한가
    지금 구조는 점수가 임계(50)를 **넘은 뒤에야** 케이스가 생긴다. 넘고 나면
    이미 정체가 시작된 것이라, 관제 입장에서는 늘 뒤늦다. 여기서는 최근 추세로
    "이대로면 N분 뒤 임계 돌파" 를 미리 띄운다.

두 가지 기능
    ① predict(rows, cfg)      — 지금 데이터로 임계 돌파 시각 예보 (학습 불필요)
    ② leading(days, cfg)      — 과거 사건에서 '어느 지표가 몇 분 먼저 움직였나'

설계 원칙
    - **학습 없이도 당장 돈다.** ①은 최근 window_min 분 점수만 있으면 된다.
      데이터가 며칠 안 쌓여도 예보는 나온다.
    - **튀는 값에 안 흔들린다.** 최소자승 대신 Theil–Sen(모든 점쌍 기울기의
      중앙값)을 쓴다. 1분짜리 스파이크 하나로 경보가 나가면 아무도 안 믿는다.
    - **조건을 다 만족해야 경보.** 기울기가 충분히 크고(min_slope),
      최근 sustain_min 분이 대체로 오르막이고, 예상 도달이 horizon_min 안일 때만.
    - **왜 그런지 같이 준다.** 같은 창에서 함께 오르고 있는 지표(drivers)를
      붙여 준다 — '스코어가 오른다'만으로는 조치를 못 한다.
    - 표본이 모자라면 숫자를 지어내지 않고 부족하다고 말한다.

config.json (없으면 아래 기본값)
    "forecast": {
      "enabled": true,
      "window_min": 20,      // 추세를 볼 최근 구간(분)
      "horizon_min": 15,     // 이 시간 안에 넘을 것 같을 때만 경보
      "min_slope": 0.6,      // 분당 최소 상승(점) — 이보다 완만하면 무시
      "sustain_min": 5,      // 최근 이만큼은 대체로 오르막이어야 함
      "min_points": 8,       // 추세 계산 최소 표본(분)
      "quiet_below": 20      // 현재 점수가 이보다 낮으면 예보 안 함(잡음 구간)
    }
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

DEFAULTS = {
    "enabled": True,
    "window_min": 20,
    "horizon_min": 15,
    "min_slope": 0.6,
    "sustain_min": 5,
    "min_points": 8,
    "quiet_below": 20,
    # ④ 다지표 — 점수 기울기 하나만 보지 않고 선행 지표를 같이 본다 (아래 설명)
    "multi": {
        "enabled": True,
        "metrics": [],            # 비우면 leading() 이 뽑은 상위 지표를 자동 사용
        "top_k": 3,
        "min_rising": 2,          # 이만큼 오르고 있어야 '선행 신호 있음'
        "rise_pct": 25,           # 지표가 '오르고 있다' 로 볼 상승률(창 환산 %)
        "assist_slope": 0.25,     # 선행 신호가 있으면 점수 기울기를 여기까지 완화
        "assist_horizon_min": 30,  # 선행 신호가 있으면 이만큼 먼 미래까지 예보
        "require_for_warn": False,  # True 면 선행 신호 없는 경보는 억제(오보↓)
    },
}


def _cfg(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg or {}).get("forecast") or {})
    return c


def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _theil_sen(pts: list[tuple[float, float]]) -> float:
    """모든 점쌍 기울기의 중앙값 — 스파이크에 끌려가지 않는 추세선.

    최소자승은 튀는 값 하나에 기울기가 확 돌아간다. 관제 데이터는 순간
    스파이크가 흔해서 그대로 쓰면 헛경보가 난다.
    """
    n = len(pts)
    if n < 2:
        return 0.0
    slopes = []
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            if xj != xi:
                slopes.append((yj - yi) / (xj - xi))
    if not slopes:
        return 0.0
    slopes.sort()
    m = len(slopes)
    return slopes[m // 2] if m % 2 else (slopes[m // 2 - 1] + slopes[m // 2]) / 2.0


def _series(rows: list[dict], key: str, win_min: int, end: datetime | None = None):
    """(분오프셋, 값) 목록 — 최근 win_min 분. 오프셋은 창 끝 기준 음수."""
    from sentinel import _row_dt
    pts, last = [], None
    for r in rows or []:
        d = _row_dt(r)
        v = _num(r.get(key))
        if d is None or v is None:
            continue
        pts.append((d, v))
        if last is None or d > last:
            last = d
    if not pts:
        return [], None
    ref = end or last
    out = [((d - ref).total_seconds() / 60.0, v) for d, v in pts
           if 0 >= (d - ref).total_seconds() / 60.0 >= -win_min]
    out.sort(key=lambda x: x[0])
    return out, ref


def _grade_of(score: float, cfg: dict) -> dict:
    try:
        from sentinel import grade
        return grade(score, cfg)
    except Exception:
        return {"level": "정상", "emoji": "🟢"}


def _driver_metrics(cfg: dict) -> list[dict]:
    """추세를 같이 볼 지표 — 화면 '추이 그래프' 와 같은 목록을 쓴다."""
    ui = (cfg or {}).get("ui") or {}
    out = []
    for g in (ui.get("metric_groups") or []):
        for m in (g.get("metrics") or []):
            if isinstance(m, dict) and m.get("key") and m["key"] != "unified_risk_score":
                out.append(m)
    if not out:
        for m in (ui.get("strip_metrics") or []):
            if isinstance(m, dict) and m.get("key") and m["key"] != "unified_risk_score":
                out.append(m)
    # 중복 제거 (묶음이 겹칠 수 있음)
    seen, uniq = set(), []
    for m in out:
        if m["key"] not in seen:
            seen.add(m["key"])
            uniq.append(m)
    return uniq


def _mcfg(f: dict) -> dict:
    m = dict(DEFAULTS["multi"])
    m.update((f or {}).get("multi") or {})
    return m


def _decide(pts: list[tuple[float, float]], floor: float, f: dict,
            sig: dict | None = None) -> dict:
    """창 하나(분오프셋, 점수)로 경보 판정. **판정 규칙은 여기 한 곳뿐이다.**

    실시간 predict() 와 사후 채점 score() 가 같은 함수를 부른다. 두 곳에
    따로 쓰면 규칙이 조금씩 어긋나 '채점 결과'가 실제 화면과 달라진다 —
    그러면 채점을 믿고 임계를 조정할 수 없다.

    sig = 같은 시각의 **선행 지표 신호** {"n": 오르는 개수, "names": [...],
    "checked": 본 개수}. 점수는 결과이고 지표가 원인이라, 지표가 같이 오르면
    같은 상승도 더 믿을 수 있다.
      · 선행 신호가 있으면  → 기울기 기준을 assist_slope 로 낮추고
                              예보 범위를 assist_horizon_min 까지 늘린다 (조기 감지)
      · 선행 신호가 없으면  → 기본 기준 그대로. require_for_warn 이면 아예 억제
                              (점수만 잠깐 튀는 헛경보를 줄인다)
    """
    m = _mcfg(f)
    sig = sig or {"n": 0, "names": [], "checked": 0}
    use_multi = bool(m.get("enabled", True)) and sig.get("checked", 0) > 0
    has_lead = use_multi and int(sig.get("n", 0)) >= int(m["min_rising"])
    slope_min = float(m["assist_slope"]) if has_lead else float(f["min_slope"])
    horizon = (float(m["assist_horizon_min"]) if has_lead
               else float(f["horizon_min"]))

    base = {"warn": False, "eta_min": None, "current": None, "projected": None,
            "slope": 0.0, "confidence": 0, "sustain": 0, "points": len(pts),
            "lead_n": int(sig.get("n", 0)), "lead_names": list(sig.get("names", [])),
            "assisted": False, "horizon_used": horizon, "reason": ""}
    if len(pts) < int(f["min_points"]):
        return {**base, "reason": f"표본 부족 — {len(pts)}분 (최소 {f['min_points']}분)"}

    cur = pts[-1][1]
    base["current"] = round(cur, 1)
    if cur >= floor:
        return {**base, "reason": f"이미 임계 이상({cur:.0f}점) — 예보 대신 케이스로 처리"}
    if cur < float(f["quiet_below"]):
        return {**base, "reason": f"조용한 구간({cur:.0f}점) — 예보 생략"}

    slope = _theil_sen(pts)            # 점/분
    base["slope"] = round(slope, 2)

    # 최근 sustain_min 분이 대체로 오르막인가 (분당 변화의 과반이 상승)
    tail = [p for p in pts if p[0] >= -float(f["sustain_min"])]
    ups = sum(1 for a, b in zip(tail, tail[1:]) if b[1] > a[1])
    steps = max(1, len(tail) - 1)
    base["sustain"] = round(100.0 * ups / steps)

    if use_multi and m.get("require_for_warn") and not has_lead:
        return {**base, "reason": f"선행 지표가 같이 오르지 않음 "
                                  f"({sig.get('n', 0)}/{m['min_rising']}개) — 경보 보류"}
    if slope < slope_min:
        why = "선행 신호 반영 기준" if has_lead else "기준"
        return {**base, "reason": f"상승세 약함 — 분당 {slope:+.2f}점 ({why} {slope_min})"}
    if base["sustain"] < 60:
        return {**base, "reason": f"최근 {f['sustain_min']}분 오르내림 — 상승 비율 {base['sustain']}%"}

    eta = (floor - cur) / slope
    if eta <= 0 or eta > horizon:
        return {**base, "reason": f"도달 예상 {eta:.0f}분 — 예보 범위({horizon:.0f}분) 밖"}

    # 신뢰도 — 오르막 지속 비율 + 기울기 여유 + 표본 수를 섞은 0~100.
    #   통계적 신뢰구간이 아니라 '얼마나 일관되게 오르고 있나' 지표다.
    #   선행 지표가 같이 오르면 '점수만 튄 게 아니다' 라는 뜻이라 더 얹는다.
    conf = (0.45 * base["sustain"]
            + 25.0 * min(1.0, slope / (float(f["min_slope"]) * 3))
            + 15.0 * min(1.0, len(pts) / float(f["window_min"]))
            + (15.0 * min(1.0, sig.get("n", 0) / max(1, int(m["min_rising"])))
               if use_multi else 15.0 * min(1.0, slope / (float(f["min_slope"]) * 3))))
    lead_txt = (f" · 선행 지표 {sig['n']}개 동반({', '.join(sig['names'][:3])})"
                if has_lead else "")
    return {**base, "warn": True, "eta_min": int(round(eta)), "assisted": has_lead,
            "projected": round(min(100.0, cur + slope * horizon), 1),
            "confidence": int(max(0, min(100, round(conf)))),
            "reason": (f"분당 {slope:+.2f}점 · 최근 {f['sustain_min']}분 상승 "
                       f"{base['sustain']}%{lead_txt}")}


def predict(rows: list[dict], cfg: dict | None = None) -> dict:
    """지금 추세로 임계 돌파 시각을 예보한다.

    반환 (항상 같은 모양 — UI 가 분기 없이 읽게):
        {ok, warn, eta_min, at, current, projected, slope, level, emoji,
         confidence, sustain, points, floor, drivers[], reason}
        warn=True 일 때만 화면에 띄운다. reason 에 안 띄우는 이유가 들어간다.
    """
    from lp_client import load_config
    from sentinel import alarm_floor
    cfg = cfg or load_config()
    f = _cfg(cfg)
    floor = alarm_floor(cfg)
    base = {"ok": True, "warn": False, "eta_min": None, "at": None,
            "current": None, "projected": None, "slope": 0.0, "level": "정상",
            "emoji": "🟢", "confidence": 0, "sustain": 0, "points": 0,
            "floor": floor, "drivers": [], "reason": "",
            "lead_n": 0, "lead_names": [], "assisted": False,
            "lead_source": "", "lead_keys": []}

    if not f.get("enabled", True):
        return {**base, "ok": False, "reason": "예보 꺼짐(config.forecast.enabled)"}

    win = int(f["window_min"])
    pts, ref = _series(rows, "unified_risk_score", win)

    # 선행 지표가 같이 오르고 있나 — 점수는 결과, 지표가 원인이다
    m = _mcfg(f)
    sig, lm = {"n": 0, "names": [], "checked": 0}, {"source": "", "keys": []}
    if m.get("enabled", True):
        lm = lead_metrics(cfg, f)
        pk = {x["key"]: _series(rows, x["key"], win, ref)[0] for x in lm["metrics"]}
        sig = _signal_from(pk, {x["key"]: (x.get("label") or x["key"])
                                for x in lm["metrics"]}, win, m)

    d = _decide(pts, floor, f, sig)
    out = {**base, **d, "at": ref.strftime("%H:%M") if ref else None,
           "lead_source": lm.get("source", ""), "lead_keys": lm.get("keys", [])}
    if not out["warn"]:
        return out
    g = _grade_of(min(100.0, out["projected"] or 0), cfg)
    out["level"] = g.get("level", "경계")
    out["emoji"] = g.get("emoji", "🟠")
    out["drivers"] = _drivers(rows, cfg, int(f["window_min"]))
    return out


def _drivers(rows: list[dict], cfg: dict, win_min: int) -> list[dict]:
    """같은 창에서 함께 오르고 있는 지표 — 상승률 큰 순서.

    변화폭이 지표마다 단위가 달라(분/%/회) 그대로 못 비교한다. 창 안의
    변동폭(max-min) 대비 몇 %가 올랐는지로 정규화해서 비교한다.
    """
    out = []
    for m in _driver_metrics(cfg):
        pts, _ = _series(rows, m["key"], win_min)
        if len(pts) < 4:
            continue
        slope = _theil_sen(pts)
        vals = [v for _, v in pts]
        span = max(vals) - min(vals)
        if slope <= 0 or span <= 0:
            continue
        rel = 100.0 * (slope * win_min) / span      # 창 전체로 환산한 상승률
        out.append({"key": m["key"], "label": m.get("label") or m["key"],
                    "raw": m.get("raw") or m["key"], "unit": m.get("unit") or "",
                    "slope": round(slope, 3), "now": round(vals[-1], 2),
                    "rise_pct": int(max(0, min(100, round(rel))))})
    out.sort(key=lambda d: -d["rise_pct"])
    return out[:5]


# ─────────────────── ③ 예보 사후 채점 (적중·오보·놓침) ───────────────────
# 왜 필요한가
#   경보만 띄우고 그게 맞았는지 아무도 안 보면 min_slope·sustain_min 같은 값이
#   영원히 '감' 으로 남는다. 저장된 CSV 를 1분씩 되감아 그때 예보를 다시
#   돌려보고(판정 규칙은 _decide 하나로 공유), 실제로 임계를 넘었는지 대조한다.
#
# 세는 법
#   경보 묶음(episode) = 연달아 뜬 경보는 한 건으로 본다. 안 그러면 사건 하나에
#     경보 10건이 잡혀 적중률이 부풀려진다. 묶음의 **첫 경보 시각**이 기준이다.
#   적중  = 첫 경보 후 horizon_min 안에 점수가 임계를 넘었다
#   오보  = 넘지 않았다
#   놓침  = 임계를 넘었는데 직전 horizon_min 안에 경보가 없었다
#   선행분 = 돌파 시각 − 첫 경보 시각 (적중일 때만)
# ── 선행 지표 신호 ────────────────────────────────────────────────
# 어느 지표를 볼 것인가는 **과거가 정한다**. leading() 이 '점수보다 몇 분 먼저
# 움직였나' 를 이미 재고 있으므로, 그중 가장 먼저 움직인 상위 몇 개를 쓴다.
# 이력이 없으면(첫 가동) 추이 그래프의 지표 전체를 그냥 후보로 둔다 —
# 학습된 목록이 아님을 source 로 밝힌다.
_LEAD_PICK: dict = {"at": 0.0, "keys": None, "source": "", "detail": []}


def lead_metrics(cfg: dict, f: dict | None = None, ttl_s: float = 600.0) -> dict:
    """이번 판정에 쓸 선행 지표 목록 → {keys, metrics, source, detail}."""
    import time as _t
    from lp_client import load_config
    cfg = cfg or load_config()
    f = f or _cfg(cfg)
    m = _mcfg(f)
    allm = {x["key"]: x for x in _driver_metrics(cfg)}

    fixed = [k for k in (m.get("metrics") or []) if k in allm]
    if fixed:
        return {"keys": fixed, "metrics": [allm[k] for k in fixed],
                "source": "config 지정", "detail": []}

    now = _t.time()
    if _LEAD_PICK["keys"] is not None and now - _LEAD_PICK["at"] < ttl_s:
        keys = [k for k in _LEAD_PICK["keys"] if k in allm]
        return {"keys": keys, "metrics": [allm[k] for k in keys],
                "source": _LEAD_PICK["source"], "detail": _LEAD_PICK["detail"]}

    keys, source, detail = [], "", []
    try:
        d = leading(None, cfg)
        rows = [x for x in (d.get("metrics") or [])
                if x.get("samples") and x.get("median_lead") is not None]
        if rows and d.get("events", 0) >= 3:
            rows.sort(key=lambda x: (-(x["median_lead"] or 0), -x["hit_rate"]))
            keys = [x["key"] for x in rows[:int(m["top_k"])] if x["key"] in allm]
            source = f"선행 분석 학습 ({d.get('events')}건)"
            detail = [{"key": x["key"], "label": x["label"],
                       "median_lead": x["median_lead"], "hit_rate": x["hit_rate"]}
                      for x in rows[:int(m["top_k"])]]
    except Exception:
        pass
    if not keys:
        keys = list(allm)[:max(int(m["top_k"]), 3)]
        source = "이력 부족 — 추이 지표로 대체"
    _LEAD_PICK.update(at=now, keys=keys, source=source, detail=detail)
    return {"keys": keys, "metrics": [allm[k] for k in keys],
            "source": source, "detail": detail}


def _rise_pct(pts: list[tuple[float, float]], win_min: float) -> float:
    """창 안에서 얼마나 올랐나 — 변동폭 대비 %. 단위가 달라도 비교되게."""
    if len(pts) < 4:
        return 0.0
    slope = _theil_sen(pts)
    vals = [v for _, v in pts]
    span = max(vals) - min(vals)
    if slope <= 0 or span <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (slope * win_min) / span))


def _signal_from(pts_by_key: dict, labels: dict, win_min: float, m: dict) -> dict:
    n, names = 0, []
    for k, pts in pts_by_key.items():
        if _rise_pct(pts, win_min) >= float(m["rise_pct"]):
            n += 1
            names.append(labels.get(k, k))
    return {"n": n, "names": names, "checked": len(pts_by_key)}


# (날짜, 창길이, 지표목록) → 인덱스별 선행 신호. 격자 탐색이 min_slope 만
# 바꿔가며 수십 번 채점하는데, 선행 신호는 그 값과 무관하므로 한 번만 센다.
_SIG_CACHE: dict = {}


def _sig_series(day: str, rows: list[dict], seq: list, lm: dict,
                win_min: float, m: dict) -> list[dict]:
    from sentinel import _row_dt
    key = (day, round(win_min, 2), tuple(lm["keys"]), float(m["rise_pct"]), len(seq))
    hit = _SIG_CACHE.get(key)
    if hit is not None:
        return hit

    labels = {x["key"]: (x.get("label") or x["key"]) for x in lm["metrics"]}
    # 지표별 (시각, 값) 을 한 번만 만들고 창은 인덱스로 자른다
    series = {k: [] for k in lm["keys"]}
    for r in rows or []:
        d = _row_dt(r)
        if d is None:
            continue
        for k in lm["keys"]:
            v = _num(r.get(k))
            if v is not None:
                series[k].append((d, v))
    for k in series:
        series[k].sort(key=lambda x: x[0])

    out = []
    for i in range(len(seq)):
        ref = seq[i][0]
        pk = {}
        for k, arr in series.items():
            w = [((d - ref).total_seconds() / 60.0, v) for d, v in arr
                 if 0 >= (d - ref).total_seconds() / 60.0 >= -win_min]
            if w:
                pk[k] = w
        out.append(_signal_from(pk, labels, win_min, m))
    if len(_SIG_CACHE) > 64:                 # 메모리 상한 — 오래된 것부터 버린다
        for k in list(_SIG_CACHE)[:32]:
            _SIG_CACHE.pop(k, None)
    _SIG_CACHE[key] = out
    return out


def _seq_of(rows: list[dict]) -> list[tuple[datetime, float]]:
    from sentinel import _row_dt
    seq = []
    for r in rows or []:
        d, s = _row_dt(r), _num(r.get("unified_risk_score"))
        if d is not None and s is not None:
            seq.append((d, s))
    seq.sort(key=lambda x: x[0])
    return seq


def _window_pts(seq, i: int, win_min: float) -> list[tuple[float, float]]:
    """seq[i] 를 '지금' 으로 보는 창 — (분오프셋, 점수). 뒤에서 앞으로 훑는다."""
    ref = seq[i][0]
    out = []
    for j in range(i, -1, -1):
        off = (seq[j][0] - ref).total_seconds() / 60.0
        if off < -win_min:
            break
        out.append((off, seq[j][1]))
    out.reverse()
    return out


def score(day: str, cfg: dict | None = None, params: dict | None = None,
          rows: list[dict] | None = None) -> dict:
    """하루치를 되감아 예보 성적을 낸다.

    params 로 임계를 바꿔가며 부를 수 있다(튜닝용). 없으면 config 값 그대로.
    rows 를 주면 CSV 를 다시 안 읽는다 — 튜닝은 같은 날을 수십 번 채점하므로
    읽기를 반복하면 대부분의 시간을 파일 파싱에 쓰게 된다.
    """
    from lp_client import load_config
    from sentinel import alarm_floor
    from store_csv import read_day
    cfg = cfg or load_config()
    f = dict(_cfg(cfg))
    f.update(params or {})
    floor = alarm_floor(cfg)
    horizon = float(f["horizon_min"])

    src = rows if rows is not None else (read_day(day, cfg) or [])
    seq = _seq_of(src)
    if len(seq) < int(f["min_points"]) + 2:
        return {"ok": False, "day": day, "error": f"{day} 데이터 부족 ({len(seq)}분)"}

    # 선행 신호는 임계(min_slope 등)와 무관하다 → 격자 탐색이 같은 걸 수십 번
    # 다시 계산하지 않도록 (창 길이, 지표 목록) 단위로 캐시해 재사용한다.
    m = _mcfg(f)
    sigs, lead_src = None, ""
    if m.get("enabled", True):
        lm = lead_metrics(cfg, f)
        lead_src = lm.get("source", "")
        sigs = _sig_series(day, src, seq, lm, float(f["window_min"]), m)

    # 임계 돌파 시각 (아래→위)
    crossings = [seq[i][0] for i in range(1, len(seq))
                 if seq[i - 1][1] < floor <= seq[i][1]]

    warnings, cur_ep = [], None
    for i in range(len(seq)):
        d = _decide(_window_pts(seq, i, float(f["window_min"])), floor, f,
                    (sigs[i] if sigs else None))
        t = seq[i][0]
        if d["warn"]:
            if cur_ep is None:
                cur_ep = {"at": t, "last": t, "eta_min": d["eta_min"],
                          "slope": d["slope"], "confidence": d["confidence"],
                          "current": d["current"], "projected": d["projected"],
                          "assisted": d.get("assisted", False),
                          "lead_n": d.get("lead_n", 0),
                          "lead_names": d.get("lead_names", []), "n": 1}
            else:
                cur_ep["last"] = t
                cur_ep["n"] += 1
        elif cur_ep is not None and (t - cur_ep["last"]).total_seconds() / 60.0 > horizon:
            warnings.append(cur_ep)          # 조용해진 지 horizon 넘음 → 묶음 종료
            cur_ep = None
    if cur_ep is not None:
        warnings.append(cur_ep)

    # 판정
    warned_cross = set()
    for w in warnings:
        hit = next((c for c in crossings
                    if 0 < (c - w["at"]).total_seconds() / 60.0 <= horizon), None)
        w["verdict"] = "적중" if hit else "오보"
        w["lead_min"] = (round((hit - w["at"]).total_seconds() / 60.0)
                         if hit else None)
        w["cross_at"] = hit.strftime("%H:%M") if hit else None
        if hit:
            warned_cross.add(hit)
        w["at"] = w["at"].strftime("%H:%M")
        w["last"] = w["last"].strftime("%H:%M")

    missed = [c for c in crossings if c not in warned_cross]
    hits = [w for w in warnings if w["verdict"] == "적중"]
    false = [w for w in warnings if w["verdict"] == "오보"]
    leads = sorted(w["lead_min"] for w in hits if w["lead_min"] is not None)
    med = (None if not leads else
           leads[len(leads) // 2] if len(leads) % 2 else
           (leads[len(leads) // 2 - 1] + leads[len(leads) // 2]) / 2.0)

    n_h, n_f, n_m = len(hits), len(false), len(missed)
    prec = round(100.0 * n_h / (n_h + n_f)) if (n_h + n_f) else None
    rec = round(100.0 * n_h / (n_h + n_m)) if (n_h + n_m) else None
    f1 = (round(2 * prec * rec / (prec + rec)) if (prec and rec) else 0)
    return {"ok": True, "day": day, "floor": floor, "minutes": len(seq),
            "multi": bool(m.get("enabled", True)), "lead_source": lead_src,
            "assisted": sum(1 for w in warnings if w.get("assisted")),
            "params": {k: f[k] for k in ("window_min", "horizon_min", "min_slope",
                                         "sustain_min", "min_points", "quiet_below")},
            "warnings": warnings,
            "crossings": [{"at": c.strftime("%H:%M"), "warned": c in warned_cross}
                          for c in crossings],
            "hit": n_h, "false": n_f, "miss": n_m,
            "precision": prec, "recall": rec, "f1": f1, "median_lead": med}


def score_days(days: list[str] | None = None, cfg: dict | None = None,
               params: dict | None = None, limit: int = 14,
               cache: dict | None = None) -> dict:
    """여러 날 합산 성적. days 를 안 주면 저장된 최근 날짜를 쓴다.

    cache {day: rows} 를 주면 CSV 를 다시 안 읽는다 (tune 이 넘겨준다).
    """
    from lp_client import load_config
    from store_csv import recent_days
    cfg = cfg or load_config()
    if not days:
        days = recent_days(limit, cfg)      # ★최근 N일 (예전엔 가장 오래된 N일)
    per, hit, fa, miss, leads = [], 0, 0, 0, []
    for day in days:
        r = score(day, cfg, params, (cache or {}).get(day))
        if not r.get("ok"):
            continue
        per.append({k: r[k] for k in ("day", "hit", "false", "miss",
                                      "precision", "recall", "median_lead")})
        hit += r["hit"]
        fa += r["false"]
        miss += r["miss"]
        leads += [w["lead_min"] for w in r["warnings"]
                  if w["verdict"] == "적중" and w["lead_min"] is not None]
    leads.sort()
    med = (None if not leads else
           leads[len(leads) // 2] if len(leads) % 2 else
           (leads[len(leads) // 2 - 1] + leads[len(leads) // 2]) / 2.0)
    prec = round(100.0 * hit / (hit + fa)) if (hit + fa) else None
    rec = round(100.0 * hit / (hit + miss)) if (hit + miss) else None
    f1 = (round(2 * prec * rec / (prec + rec)) if (prec and rec) else 0)
    cur = dict(_cfg(cfg))
    cur.update(params or {})
    return {"ok": True, "days": [p["day"] for p in per], "per_day": per,
            "params": {k: cur[k] for k in ("window_min", "horizon_min", "min_slope",
                                           "sustain_min", "min_points", "quiet_below")},
            "hit": hit, "false": fa, "miss": miss,
            "precision": prec, "recall": rec, "f1": f1, "median_lead": med,
            "events": hit + miss,
            "note": ("" if hit + miss >= 5 else
                     f"돌파 사건 {hit + miss}건 — 표본이 적어 참고용입니다(5건 이상 권장)")}


def compare(days: list[str] | None = None, cfg: dict | None = None,
            limit: int = 14) -> dict:
    """다지표 선행 감지가 **정말 나은지** 같은 데이터로 맞대본다.

    바꿨는데 좋아졌는지 모르면 안 바꾼 것만 못하다. 기존(점수 기울기만) 과
    다지표를 같은 날짜·같은 임계로 각각 채점해 나란히 보여준다.
    판단은 사람이 한다 — 어느 쪽이 낫다고 자동으로 바꾸지 않는다.
    """
    from lp_client import load_config
    from store_csv import read_day, recent_days
    cfg = cfg or load_config()
    if not days:
        days = recent_days(limit, cfg)      # ★최근 N일 (예전엔 가장 오래된 N일)
    cache = {d: (read_day(d, cfg) or []) for d in days}

    m0 = _mcfg(_cfg(cfg))
    off = score_days(days, cfg, {"multi": {**m0, "enabled": False}}, limit, cache)
    on = score_days(days, cfg, {"multi": {**m0, "enabled": True,
                                          "require_for_warn": False}}, limit, cache)
    # 세 번째 안 — 선행 지표가 같이 오르지 않으면 아예 억제. 이걸 켤지 말지는
    # config 를 고쳐 하루 굴려보는 게 아니라 이 표를 보고 정하면 된다.
    strict = score_days(days, cfg, {"multi": {**m0, "enabled": True,
                                              "require_for_warn": True}}, limit, cache)
    lm = lead_metrics(cfg)

    def gain(a, b, higher=True):
        if a is None or b is None:
            return None
        return round(b - a) if higher else round(a - b)

    return {"ok": True, "days": on["days"], "events": on["events"],
            "lead_source": lm.get("source", ""), "lead_detail": lm.get("detail", []),
            "lead_keys": lm.get("keys", []),
            "off": {k: off[k] for k in ("hit", "false", "miss", "precision",
                                        "recall", "f1", "median_lead")},
            "on": {k: on[k] for k in ("hit", "false", "miss", "precision",
                                      "recall", "f1", "median_lead")},
            "strict": {k: strict[k] for k in ("hit", "false", "miss", "precision",
                                              "recall", "f1", "median_lead")},
            "current": {"enabled": bool(m0.get("enabled", True)),
                        "require_for_warn": bool(m0.get("require_for_warn", False))},
            "best": max((("off", off), ("on", on), ("strict", strict)),
                        key=lambda kv: (kv[1]["f1"] or 0,
                                        kv[1]["median_lead"] or 0))[0],
            "delta": {"hit": on["hit"] - off["hit"],
                      "false": on["false"] - off["false"],
                      "miss": on["miss"] - off["miss"],
                      "f1": gain(off["f1"], on["f1"]),
                      "median_lead": gain(off["median_lead"], on["median_lead"])},
            "note": on["note"]}


# 튜닝 격자 — 기울기·지속을 훑는다. 창 길이(window_min)는 기울기 계산을 통째로
# 다시 해야 해 느리므로 기본은 현재 값 고정. 필요하면 windows 로 넘긴다.
TUNE_SLOPES = (0.3, 0.4, 0.6, 0.8, 1.0, 1.4)
TUNE_SUSTAIN = (3, 5, 8)


def tune(days: list[str] | None = None, cfg: dict | None = None,
         slopes=None, sustains=None, windows=None, limit: int = 7) -> dict:
    """임계를 격자로 훑어 F1 이 가장 높은 조합을 찾는다.

    '적중률만' 보면 경보를 남발하는 쪽이 이긴다. 반대로 '오보 0' 만 보면
    아무것도 안 띄우는 쪽이 이긴다. 그래서 정밀도와 재현율의 조화평균(F1)로
    고르고, 표를 그대로 같이 돌려줘 사람이 다르게 판단할 여지를 남긴다.
    """
    from lp_client import load_config
    cfg = cfg or load_config()
    base = _cfg(cfg)
    slopes = list(slopes or TUNE_SLOPES)
    sustains = list(sustains or TUNE_SUSTAIN)
    windows = list(windows or [int(base["window_min"])])

    # 날짜별 CSV 는 한 번만 읽어 격자 전체가 나눠 쓴다
    from store_csv import read_day, recent_days
    if not days:
        days = recent_days(limit, cfg)      # ★최근 N일 (예전엔 가장 오래된 N일)
    cache = {d: (read_day(d, cfg) or []) for d in days}

    grid = []
    for w in windows:
        for s in slopes:
            for su in sustains:
                p = {"window_min": w, "min_slope": s, "sustain_min": su}
                r = score_days(days, cfg, p, limit, cache)
                grid.append({**p, "hit": r["hit"], "false": r["false"],
                             "miss": r["miss"], "precision": r["precision"],
                             "recall": r["recall"], "f1": r["f1"],
                             "median_lead": r["median_lead"],
                             "days": len(r["days"]), "events": r["events"]})
    grid.sort(key=lambda d: (-d["f1"], -(d["median_lead"] or 0), d["false"]))
    now = score_days(days, cfg, None, limit, cache)
    best = grid[0] if grid else None
    better = bool(best and now["f1"] is not None and best["f1"] > now["f1"])
    return {"ok": True, "current": {k: base[k] for k in
                                    ("window_min", "min_slope", "sustain_min")},
            "current_score": {k: now[k] for k in
                              ("hit", "false", "miss", "precision", "recall",
                               "f1", "median_lead", "events")},
            "grid": grid[:12], "best": best, "better": better,
            "days": now["days"], "note": now["note"]}


# ────────────────────── ② 선행 지표 분석 (과거 데이터) ──────────────────────
def leading(days: list[str] | None = None, cfg: dict | None = None,
            lookback_min: int = 60, baseline_min: int = 60) -> dict:
    """과거 사건에서 '어느 지표가 점수보다 몇 분 먼저 움직였나'.

    방법
        1. 저장된 날짜 CSV 에서 점수가 임계를 처음 넘는 순간(=돌파점)을 찾는다.
        2. 지표마다 '평소 수준' 을 **관측창보다 더 앞선 조용한 구간**
           (돌파 전 lookback+baseline ~ lookback 분)의 중앙값으로 잡는다.
           관측창 안에서 평소 수준을 구하면, 이미 오르고 있던 지표는 그 상승분이
           평소 수준에 섞여 들어가 선행 시간이 실제보다 짧게 나온다.
        3. 관측창에서 그 수준을 확실히 넘은 첫 시각을 찾아 돌파 시각과의 차이를 잰다.
        4. 관측창 첫 지점부터 이미 올라 있으면 '그보다 더 먼저' 이므로 값에
           censored 표시를 남긴다 (≥ lookback_min).

    중앙값을 쓰는 이유는 사건마다 양상이 달라 평균이 한두 건에 끌려가기 때문.
    사건 수가 적으면 samples 로 그대로 드러내고 판단은 사람에게 맡긴다.
    """
    from lp_client import load_config
    from sentinel import alarm_floor, _row_dt
    from store_csv import read_day, recent_days
    cfg = cfg or load_config()
    floor = alarm_floor(cfg)

    if not days:
        days = recent_days(14, cfg)         # ★최근 14일
    metrics = _driver_metrics(cfg)
    if not metrics:
        return {"ok": False, "error": "비교할 지표 목록이 없습니다(config.ui)"}

    per_metric: dict[str, list[float]] = {m["key"]: [] for m in metrics}
    censored: dict[str, int] = {m["key"]: 0 for m in metrics}
    events = 0
    used_days = []

    for day in days:
        rows = read_day(day, cfg) or []
        if not rows:
            continue
        seq = []
        for r in rows:
            d = _row_dt(r)
            s = _num(r.get("unified_risk_score"))
            if d is not None and s is not None:
                seq.append((d, s, r))
        if len(seq) < 10:
            continue
        seq.sort(key=lambda x: x[0])
        used_days.append(day)

        # 임계 돌파점 — 아래에 있다가 위로 올라온 순간
        crosses = [i for i in range(1, len(seq))
                   if seq[i - 1][1] < floor <= seq[i][1]]
        for i in crosses:
            t0 = seq[i][0]
            win = [(d, r) for d, s, r in seq
                   if timedelta(0) <= (t0 - d) <= timedelta(minutes=lookback_min)]
            # 평소 수준용 조용한 구간 — 관측창보다 더 앞
            quiet = [(d, r) for d, s, r in seq
                     if timedelta(minutes=lookback_min) < (t0 - d)
                     <= timedelta(minutes=lookback_min + baseline_min)]
            if len(win) < 8:
                continue
            events += 1
            for m in metrics:
                lead, cens = _lead_minutes(win, quiet, m["key"], t0, lookback_min)
                if lead is not None:
                    per_metric[m["key"]].append(lead)
                    censored[m["key"]] += 1 if cens else 0

    out = []
    for m in metrics:
        vals = sorted(per_metric[m["key"]])
        if not vals:
            out.append({"key": m["key"], "label": m.get("label") or m["key"],
                        "raw": m.get("raw") or m["key"], "samples": 0,
                        "median_lead": None, "hit_rate": 0, "censored": 0})
            continue
        mid = vals[len(vals) // 2] if len(vals) % 2 else \
            (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2.0
        out.append({"key": m["key"], "label": m.get("label") or m["key"],
                    "raw": m.get("raw") or m["key"],
                    "samples": len(vals), "median_lead": round(mid, 1),
                    "hit_rate": int(round(100.0 * len(vals) / max(1, events))),
                    # 관측창 시작부터 이미 올라 있던 횟수 — 실제 선행은 이보다 길다
                    "censored": censored[m["key"]]})
    out.sort(key=lambda d: (-(d["median_lead"] or 0), -d["hit_rate"]))

    enough = events >= 5
    return {"ok": True, "events": events, "days": used_days,
            "floor": floor, "lookback_min": lookback_min,
            "metrics": out, "enough": enough,
            "note": ("" if enough else
                     f"사건 {events}건 — 표본이 적어 참고용입니다(5건 이상 권장)")}


def _lead_minutes(win: list[tuple], quiet: list[tuple], key: str,
                  t0: datetime, lookback_min: int) -> tuple[float | None, bool]:
    """돌파(t0) 대비 이 지표가 몇 분 먼저 올라가기 시작했나 → (분, 절단여부).

    평소 수준은 quiet(관측창보다 앞선 조용한 구간)에서 잡는다. quiet 가 없으면
    관측창 앞쪽 1/3 로 물러서되, 그 경우 값이 짧게 나올 수 있음을 감안한다.
    """
    def vals_of(seg):
        out = []
        for d, r in seg:
            v = _num(r.get(key))
            if v is not None:
                out.append((d, v))
        out.sort(key=lambda x: x[0])
        return out

    pts = vals_of(win)
    if len(pts) < 6:
        return None, False
    qs = [v for _, v in vals_of(quiet)]
    wv = [v for _, v in pts]
    if len(qs) >= 5:
        base = sorted(qs)[len(qs) // 2]
        span = max(max(wv) - base, max(qs) - min(qs), 1e-9)
    else:
        head = wv[:max(2, len(wv) // 3)]
        base = sorted(head)[len(head) // 2]
        span = max(wv) - min(wv)
    if span <= 0:
        return None, False

    thr = base + span * 0.3          # 변동폭의 30% 넘게 오르면 '움직였다'
    for d, v in pts:
        if v >= thr:
            lead = (t0 - d).total_seconds() / 60.0
            if lead <= 0:
                return None, False
            # 관측창 첫 지점부터 이미 넘어 있으면 그보다 더 먼저 오른 것
            return lead, (d == pts[0][0] and lead >= lookback_min - 1)
    return None, False


if __name__ == "__main__":
    import json
    import sys
    from lp_client import load_config
    from store_csv import latest_day, read_day
    cfg = load_config()
    if len(sys.argv) > 1 and sys.argv[1] == "--leading":
        print(json.dumps(leading(sys.argv[2:] or None, cfg), ensure_ascii=False, indent=2))
    else:
        day = sys.argv[1] if len(sys.argv) > 1 else \
            (latest_day(cfg) or datetime.now().strftime("%Y%m%d"))
        print(json.dumps(predict(read_day(day, cfg), cfg), ensure_ascii=False, indent=2))
