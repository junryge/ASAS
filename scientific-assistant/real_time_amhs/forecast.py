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
            "floor": floor, "drivers": [], "reason": ""}

    if not f.get("enabled", True):
        return {**base, "ok": False, "reason": "예보 꺼짐(config.forecast.enabled)"}

    pts, ref = _series(rows, "unified_risk_score", int(f["window_min"]))
    base["points"] = len(pts)
    if len(pts) < int(f["min_points"]):
        return {**base, "reason": f"표본 부족 — {len(pts)}분 (최소 {f['min_points']}분)"}

    cur = pts[-1][1]
    base["current"] = round(cur, 1)
    base["at"] = ref.strftime("%H:%M") if ref else None

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

    if slope < float(f["min_slope"]):
        return {**base, "reason": f"상승세 약함 — 분당 {slope:+.2f}점 (기준 {f['min_slope']})"}
    if base["sustain"] < 60:
        return {**base, "reason": f"최근 {f['sustain_min']}분 오르내림 — 상승 비율 {base['sustain']}%"}

    eta = (floor - cur) / slope
    if eta <= 0 or eta > float(f["horizon_min"]):
        return {**base, "reason": f"도달 예상 {eta:.0f}분 — 예보 범위({f['horizon_min']}분) 밖"}

    proj = cur + slope * float(f["horizon_min"])
    g = _grade_of(min(100.0, proj), cfg)

    # 신뢰도 — 오르막 지속 비율 + 기울기 여유 + 표본 수를 섞은 0~100.
    #   통계적 신뢰구간이 아니라 '얼마나 일관되게 오르고 있나' 지표다.
    conf = (0.5 * base["sustain"]
            + 30.0 * min(1.0, slope / (float(f["min_slope"]) * 3))
            + 20.0 * min(1.0, len(pts) / float(f["window_min"])))
    base["confidence"] = int(max(0, min(100, round(conf))))

    return {**base, "warn": True,
            "eta_min": int(round(eta)),
            "projected": round(min(100.0, proj), 1),
            "level": g.get("level", "경계"), "emoji": g.get("emoji", "🟠"),
            "drivers": _drivers(rows, cfg, int(f["window_min"])),
            "reason": f"분당 {slope:+.2f}점 · 최근 {f['sustain_min']}분 상승 {base['sustain']}%"}


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
    from store_csv import list_days, read_day
    cfg = cfg or load_config()
    floor = alarm_floor(cfg)

    if not days:
        days = [d["day"] for d in (list_days(cfg) or [])][-14:]
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
    from store_csv import read_day, list_days
    cfg = load_config()
    if len(sys.argv) > 1 and sys.argv[1] == "--leading":
        print(json.dumps(leading(sys.argv[2:] or None, cfg), ensure_ascii=False, indent=2))
    else:
        day = sys.argv[1] if len(sys.argv) > 1 else \
            (list_days(cfg) or [{"day": datetime.now().strftime("%Y%m%d")}])[-1]["day"]
        print(json.dumps(predict(read_day(day, cfg), cfg), ensure_ascii=False, indent=2))
