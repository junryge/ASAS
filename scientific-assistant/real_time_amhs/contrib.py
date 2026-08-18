"""
real_time_amhs/contrib.py — 스코어 기여도 분해 ('왜 이 점수인가')

왜 필요한가
    화면에 "88점 초위험" 이라고만 뜨면 관제는 다음 질문에서 막힌다 —
    "그래서 뭘 손봐야 하나?" reason 한글 요약이 어떤 룰이 떴는지는 알려주지만,
    **어느 지표가 이 점수를 얼마나 밀어올렸는지**는 아무도 말해주지 않는다.

정직하게 말해두는 한계
    unified_risk_score 는 이 시스템 밖(hubroom_predictor)에서 계산돼 들어온다.
    우리는 점수식을 갖고 있지 않다. 그래서 여기 나오는 %는 **점수식을 푼 게
    아니라 추정치**다. 화면에도 반드시 '추정' 이라고 쓴다.

어떻게 추정하나
    1. 그날의 **조용한 구간**(점수 < 임계)을 평소 수준으로 삼는다.
       평균이 아니라 중앙값·MAD 를 쓴다 — 스파이크 몇 개에 평소가 끌려가면
       모든 지표가 다 이상해 보인다.
    2. 지표마다 그 시각 값이 평소에서 몇 MAD 벗어났는지(robust z)를 잰다.
    3. **실제로 룰을 발동시킨 지표에 가중치를 준다.** 통계적으로 튀었어도
       룰이 안 봤으면 점수를 올린 게 아니다. reason 이 지목한 지표
       (sentinel.reason_metrics) 에 boost 배를 준다.
    4. 양의 기여만 모아 100%로 정규화한다.

    z 가 작은 것(|z| < min_z)은 '평소 범위' 로 보고 뺀다. 다 빼면 기여도를
    지어내지 않고 '평소와 다른 지표 없음' 이라고 말한다.
"""
from __future__ import annotations

DEFAULTS = {
    "min_z": 1.0,        # 이보다 덜 벗어났으면 '평소 범위'
    "fired_boost": 2.0,  # reason 이 지목한 지표 가중
    "top": 8,            # 최대 표시 개수
    "z_cap": 8.0,        # z 상한 — 눈금이 작은 지표가 화면을 다 먹는 것 방지
}


def _cfg(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg or {}).get("contrib") or {})
    return c


def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _mad(xs: list[float], med: float) -> float:
    """중앙절대편차 × 1.4826 → 정규분포에서 표준편차와 같은 눈금."""
    if not xs:
        return 0.0
    return 1.4826 * _median([abs(x - med) for x in xs])


def _scale(vals: list[float], med: float) -> float | None:
    """z 를 재는 눈금. MAD 가 0 이어도 터지지 않게 대안을 순서대로 쓴다.

    ★리프터 정체처럼 평소 값이 대부분 0 인 지표는 MAD 가 정확히 0 이 된다.
      그대로 나누면 z 가 수십억이 되어 그 지표 하나가 100%를 먹는다
      (실제로 그렇게 나왔다). 분포 폭 → 값의 10% → 전체 범위 순으로 물러난다.
    """
    sd = _mad(vals, med)
    if sd > 1e-9:
        return sd
    xs = sorted(vals)
    n = len(xs) - 1
    for cand in ((xs[int(0.9 * n)] - xs[int(0.1 * n)]) / 2.56,
                 abs(med) * 0.10,
                 (xs[-1] - xs[0]) / 4.0):
        if cand > 1e-9:
            return cand
    return None            # 하루 종일 완전히 같은 값 — 눈금을 만들 수 없다


def _metrics(cfg: dict) -> list[dict]:
    """비교할 지표 — 화면 '추이 그래프' 목록과 같은 것을 쓴다."""
    ui = (cfg or {}).get("ui") or {}
    out = []
    for g in (ui.get("metric_groups") or []):
        for m in (g.get("metrics") or []):
            if isinstance(m, dict) and m.get("key") and m["key"] != "unified_risk_score":
                out.append(m)
    if not out:
        out = [m for m in (ui.get("strip_metrics") or [])
               if isinstance(m, dict) and m.get("key")
               and m["key"] != "unified_risk_score"]
    seen, uniq = set(), []
    for m in out:
        if m["key"] not in seen:
            seen.add(m["key"])
            uniq.append(m)
    return uniq


def explain(rows: list[dict], at, cfg: dict | None = None) -> dict:
    """그 1분의 점수를 지표별 추정 기여도로 쪼갠다.

    rows  : 그날(또는 앞뒤 포함) 분단위 행
    at    : datetime — 설명할 시각
    반환  : {ok, at, score, level, emoji, floor, baseline_n, items[], note, error}
            items = [{key,label,raw,unit,value,base,z,dir,fired,pct}]
    """
    from lp_client import load_config
    from sentinel import _row_dt, _score, alarm_floor, grade, reason_metrics
    cfg = cfg or load_config()
    c = _cfg(cfg)
    floor = alarm_floor(cfg)

    seq = []
    for r in rows or []:
        d = _row_dt(r)
        if d is not None:
            seq.append((d, r))
    if not seq:
        return {"ok": False, "error": "데이터 없음"}
    seq.sort(key=lambda x: x[0])

    # 그 시각 행 — 정확히 없으면 가장 가까운 분
    row = min(seq, key=lambda x: abs((x[0] - at).total_seconds()))
    if abs((row[0] - at).total_seconds()) > 300:
        return {"ok": False, "error": f"{at:%H:%M} 근처에 데이터가 없습니다"}
    dt, r0 = row
    sc = _score(r0)
    g = grade(sc, cfg)

    # 평소 수준 = 그날 조용한 구간(점수 < 임계). 너무 적으면 전체를 쓴다.
    quiet = [r for d, r in seq if _score(r) < floor]
    base_rows = quiet if len(quiet) >= 20 else [r for _, r in seq]
    base_note = (f"정상 구간({floor}점 미만) 기준" if len(quiet) >= 20
                 else "정상 구간이 적어 하루 전체 기준")

    fired_raw = {m["raw"] for m in
                 reason_metrics(str(r0.get("reason") or ""),
                                (r0.get("hot_area") or "").strip())}

    items = []
    for m in _metrics(cfg):
        v = _num(r0.get(m["key"]))
        if v is None:
            continue
        vals = [x for x in (_num(b.get(m["key"])) for b in base_rows) if x is not None]
        if len(vals) < 10:
            continue
        med = _median(vals)
        sd = _scale(vals, med)
        if sd is None:                      # 하루 종일 같은 값이었다
            z = 0.0 if abs(v - med) < 1e-9 else float(c["z_cap"])
        else:
            z = (v - med) / sd
        # 눈금이 아무리 작아도 한 지표가 화면을 다 먹지 않게 상한을 둔다
        z = max(-float(c["z_cap"]), min(float(c["z_cap"]), z))
        raw = m.get("raw") or m["key"]
        fired = raw in fired_raw
        if abs(z) < float(c["min_z"]) and not fired:
            continue
        # ★룰이 떴는데 편차는 거의 없는 경우 — 오늘 하루 내내 높았다는 뜻이다.
        #   (예: STB 저장율이 아침부터 98%면 '평소 대비 상승' 은 0 이지만
        #    포화 자체가 원인이다.) 편차 0 으로 두면 화면에서 사라지므로
        #    최소 무게를 주고 '상시' 로 표시해 스파이크와 구분한다.
        chronic = fired and abs(z) < float(c["min_z"])
        w = max(abs(z), float(c["min_z"]) if fired else 0.0)
        items.append({
            "key": m["key"], "label": m.get("label") or m["key"], "raw": raw,
            "unit": m.get("unit") or "", "value": round(v, 2), "base": round(med, 2),
            "z": round(z, 2), "dir": "상승" if z >= 0 else "하락", "fired": fired,
            "chronic": chronic,
            "w": w * (float(c["fired_boost"]) if fired else 1.0),
        })

    total = sum(i["w"] for i in items)
    if not items or total <= 0:
        return {"ok": True, "at": dt.strftime("%Y-%m-%d %H:%M"), "score": round(sc, 1),
                "level": g["level"], "emoji": g["emoji"], "floor": floor,
                "baseline_n": len(base_rows), "items": [],
                "note": f"{base_note} — 평소와 뚜렷이 다른 지표가 없습니다"}

    for i in items:
        i["pct"] = round(100.0 * i["w"] / total)
        i.pop("w")
    items.sort(key=lambda d: (-d["pct"], -abs(d["z"])))
    return {"ok": True, "at": dt.strftime("%Y-%m-%d %H:%M"), "score": round(sc, 1),
            "level": g["level"], "emoji": g["emoji"], "floor": floor,
            "baseline_n": len(base_rows), "items": items[:int(c["top"])],
            "note": base_note}


def explain_html(rows: list[dict], at, cfg: dict | None = None) -> str:
    """구간 그래프 모달에 그대로 붙일 HTML 조각."""
    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    d = explain(rows, at, cfg)
    if not d.get("ok"):
        return (f'<div class="empty">기여도 분해 실패 — {esc(d.get("error", ""))}</div>')
    head = (f'<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap">'
            f'<b style="font-size:13px">기여도 추정</b>'
            f'<span class="note">{esc(d["at"])} · {d["emoji"]} {esc(d["level"])} '
            f'{d["score"]:.0f}점 · {esc(d["note"])} ({d["baseline_n"]}분)</span></div>'
            f'<div class="note" style="margin:2px 0 8px;color:var(--major)">'
            f'※ 점수식을 푼 값이 아닙니다. 평소 대비 얼마나 벗어났는지로 낸 '
            f'<b>추정</b>이며, reason 이 실제로 지목한 지표에 가중치를 줬습니다.</div>')
    if not d["items"]:
        return head + '<div class="empty">평소와 뚜렷이 다른 지표가 없습니다</div>'

    bars = []
    for i in d["items"]:
        col = "var(--crit)" if i["fired"] else "var(--tx3)"
        tag = ('<span class="chip lv위험" style="font-size:9.5px">발동</span>'
               if i["fired"] else "")
        if i.get("chronic"):
            tag += ('<span class="chip" style="font-size:9.5px">상시</span>')
        bars.append(
            f'<div style="display:grid;grid-template-columns:190px 1fr 78px;'
            f'gap:8px;align-items:center;margin:3px 0">'
            f'<div style="font-size:12px"><b style="color:var(--tx)">{esc(i["label"])}</b> {tag}'
            f'<div class="mono" style="font-size:10px;color:var(--tx3)">{esc(i["raw"])}</div></div>'
            f'<div style="background:var(--line);border-radius:5px;height:15px;overflow:hidden">'
            f'<div style="width:{i["pct"]}%;height:100%;background:{col}"></div></div>'
            f'<div style="font-size:12px;text-align:right">'
            f'<b>{i["pct"]}%</b><div class="note" style="font-size:10px">'
            f'{i["value"]}{esc(i["unit"])} · 평소 {i["base"]}{esc(i["unit"])}'
            f'{" · 하루 내내" if i.get("chronic") else ""}</div></div>'
            f'</div>')
    return head + "".join(bars)


if __name__ == "__main__":
    import json
    import sys
    from datetime import datetime
    from lp_client import load_config
    from store_csv import list_days, read_day
    cfg = load_config()
    day = sys.argv[1] if len(sys.argv) > 1 else \
        (list_days(cfg) or [{"day": datetime.now().strftime("%Y%m%d")}])[-1]["day"]
    rows = read_day(day, cfg)
    if len(sys.argv) > 2:
        at = datetime.strptime(f"{day} {sys.argv[2]}", "%Y%m%d %H:%M")
    else:                                        # 안 주면 그날 최고점
        from sentinel import _row_dt, _score
        at = max(((_row_dt(r), _score(r)) for r in rows if _row_dt(r)),
                 key=lambda x: x[1])[0]
    print(json.dumps(explain(rows, at, cfg), ensure_ascii=False, indent=2))
