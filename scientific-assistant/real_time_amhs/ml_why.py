#!/usr/bin/env python3
"""ml_why.py — ML 조기예측이 "왜 이랬는지" 를 답한다.

무엇이 문제였나
    최근 기록에 확률과 단계만 줄줄이 찍혔다. 03:12 에 선제경보가 떴다는
    것은 알겠는데 **왜** 떴는지가 없다. 그 답이 없으면 화면을 보고 할 수
    있는 일이 없다 — 관제 화면의 존재 이유가 사라진다.

어떻게 답하나 (순서가 중요하다)
    1) **근거를 먼저 계산한다.** ML 추이(앞뒤 몇 분), 그 순간 룰베이스
       점수와 기여 지표, 둘이 같은 말을 했는지.
    2) 그 근거를 LLM 에게 **읽히고 설명만** 시킨다.

    ★LLM 에게 원본 CSV 를 던지고 "분석해 줘" 하지 않는다. 그러면 숫자를
      지어낸다. 계산은 우리가 하고, LLM 은 계산된 것을 사람 말로 옮긴다.
    ★LLM 이 죽어도 근거는 그대로 보여 준다. 설명이 없는 것과 아무것도 없는
      것은 다르다.

ML 과 룰베이스는 독립이다
    눈금이 다르다(룰 0~100점 / ML 은 분 단위 반송시간의 초과 확률). 그래서
    "누가 맞다" 가 아니라 **"둘이 같은 말을 했나, 누가 먼저 말했나"** 를
    본다. 엇갈렸다면 그 자체가 봐야 할 신호다.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

WINDOW_MIN = 20          # 앞뒤로 몇 분을 같이 보나
TOP_ITEMS = 5            # 기여 지표 몇 개까지 설명에 넣나


def _f(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _dt(s) -> datetime | None:
    """시각 파싱은 한 군데(lp_client.parse_dt)만 쓴다 — 표기가 여럿이라
    각자 파싱하면 어딘가는 반드시 어긋난다."""
    from lp_client import parse_dt
    return parse_dt(s)


# ── 1) ML 쪽 근거 ────────────────────────────────────────────────
def ml_evidence(at: datetime, cfg: dict) -> dict:
    """그 시각 ML 행 + 앞뒤 추이 + 단계가 언제 바뀌었는지."""
    import ml_feed
    rows = ml_feed.read_day(at.strftime("%Y%m%d"), cfg)
    seq = []
    for r in rows:
        d = _dt(r.get("datetime"))
        if d is not None:
            seq.append((d, r))
    if not seq:
        return {"ok": False, "error": "그 날 ML 예측 파일에 행이 없습니다"}
    seq.sort(key=lambda x: x[0])

    dt0, row = min(seq, key=lambda x: abs((x[0] - at).total_seconds()))
    if abs((dt0 - at).total_seconds()) > 300:
        return {"ok": False, "error": f"{at:%H:%M} 근처에 ML 예측이 없습니다"}

    lo, hi = dt0 - timedelta(minutes=WINDOW_MIN), dt0 + timedelta(minutes=WINDOW_MIN)
    win = [(d, r) for d, r in seq if lo <= d <= hi]
    trend = [{"t": d.strftime("%H:%M"),
              "p10": _f(r.get("ml_score_10m")), "p30": _f(r.get("ml_score_30m")),
              "smoothed": _f(r.get("smoothed")), "raw": _f(r.get("raw_value")),
              "stage": str(r.get("stage") or "0").strip()} for d, r in win]

    # 단계가 언제 올라갔나 — 이 줄이 '언제부터 이랬나' 의 답이다
    stage_now = str(row.get("stage") or "0").strip()
    onset = None
    prev = None
    for d, r in seq:
        if d > dt0:
            break
        st = str(r.get("stage") or "0").strip()
        if prev is not None and st != prev and st >= "1":
            onset = {"at": d.strftime("%H:%M"), "from": prev, "to": st}
        prev = st

    def _delta(key):
        """20분 전 대비 얼마나 움직였나. ★값 하나만 보면 '높다' 는 알아도
        '올라오는 중' 인지 '내려가는 중' 인지를 모른다."""
        base = [x for x in trend if x["t"] <= (dt0 - timedelta(minutes=WINDOW_MIN)
                                               ).strftime("%H:%M")]
        first = (base or trend)[0].get(key)
        now = next((x.get(key) for x in reversed(trend)
                    if x["t"] == dt0.strftime("%H:%M")), None)
        if first is None or now is None:
            return None
        return round(now - first, 4)

    smoothed, thr = _f(row.get("smoothed")), _f(row.get("threshold"))
    return {
        "ok": True,
        "at": dt0.strftime("%Y-%m-%d %H:%M"),
        "p10": _f(row.get("ml_score_10m")), "p30": _f(row.get("ml_score_30m")),
        "level10": row.get("ml_level_10m") or "", "level30": row.get("ml_level_30m") or "",
        "stage": stage_now, "stage_name": row.get("stage_name") or "",
        "smoothed": smoothed, "raw": _f(row.get("raw_value")), "threshold": thr,
        "near_pct": round(smoothed / thr * 100, 1) if (smoothed and thr) else None,
        "lead_min": row.get("lead_min") or "", "reason": row.get("reason") or "",
        "backend": row.get("backend") or "",
        "onset": onset,
        "d_p10": _delta("p10"), "d_p30": _delta("p30"),
        "d_smoothed": _delta("smoothed"),
        "trend": trend,
    }


# ── 2) 룰베이스(실시간 관제) 쪽 근거 ──────────────────────────────
def rule_evidence(at: datetime, cfg: dict) -> dict:
    """그 순간 우리 점수는 몇이었고, 어느 지표가 밀어올렸나.

    ★ML 이 '반송시간이 임계를 넘겠다' 고 할 때, 현장에서 실제로 무슨 일이
      벌어지고 있었는지는 이쪽에만 있다. 이게 있어야 '왜' 에 답이 된다.
    """
    try:
        from store_csv import read_day
        from contrib import explain
        from sentinel import alarm_floor
    except Exception as e:
        return {"ok": False, "error": f"모듈 로드 실패: {e}"}

    rows = read_day(at.strftime("%Y%m%d"), cfg)
    if not rows:
        return {"ok": False, "error": "그 날 실시간 관제 데이터가 없습니다"}
    try:
        ex = explain(rows, at, cfg)
    except Exception as e:
        return {"ok": False, "error": f"기여도 분해 실패: {type(e).__name__}: {e}"}
    if not ex.get("ok"):
        return {"ok": False, "error": ex.get("error") or "기여도 분해 실패"}

    items = [i for i in (ex.get("items") or []) if i.get("fired")] \
        or list(ex.get("items") or [])
    items = sorted(items, key=lambda i: -(i.get("pct") or 0))[:TOP_ITEMS]
    return {
        "ok": True,
        "score": ex.get("score"), "level": ex.get("level"),
        "floor": ex.get("floor", alarm_floor(cfg)),
        "note": ex.get("note") or "",
        # ★contrib 의 'raw' 는 값이 아니라 **원본 컬럼명**이다
        #   (M16HUB.QUE.TIME.AVGTOTALTIME1MIN). 숫자는 'value' 다. 이걸
        #   헷갈리면 LLM 에게 값 대신 컬럼명을 줘서, 숫자를 지어내게 만든다.
        "items": [{"label": i.get("label"), "value": i.get("value"),
                   "col": i.get("raw"),
                   "unit": i.get("unit") or "", "pct": i.get("pct"),
                   "base": i.get("base"), "dir": i.get("dir"),
                   "fired": bool(i.get("fired"))} for i in items],
    }


# ── 3) 둘이 같은 말을 했나 ───────────────────────────────────────
def agreement(ml: dict, rule: dict, p_on: float) -> dict:
    """★'누가 맞다' 가 아니다. 엇갈렸다는 사실 자체가 봐야 할 신호다."""
    ml_fired = bool(ml.get("ok")) and str(ml.get("stage") or "0") >= "2"
    rule_ok = bool(rule.get("ok"))
    rule_fired = rule_ok and (rule.get("score") or 0) >= (rule.get("floor") or 60)
    if not rule_ok:
        verdict = "룰베이스 쪽 근거를 못 읽어 비교할 수 없습니다"
    elif ml_fired and rule_fired:
        verdict = "둘 다 이상하다고 봤습니다"
    elif ml_fired and not rule_fired:
        verdict = ("ML 만 먼저 반응했습니다 — 아직 점수로는 안 드러난 "
                   "조짐일 수 있습니다")
    elif rule_fired and not ml_fired:
        verdict = ("룰베이스만 반응했습니다 — 반송시간까지는 아직 "
                   "안 번진 상태일 수 있습니다")
    else:
        verdict = "둘 다 평온합니다"
    return {"ml_fired": ml_fired, "rule_fired": rule_fired,
            "rule_readable": rule_ok, "verdict": verdict}


# ── 4) 근거를 LLM 이 읽을 수 있게 ────────────────────────────────
def _pct(v):
    return "–" if v is None else f"{v * 100:.0f}%"


def evidence_text(ev: dict) -> str:
    """계산된 근거를 짧은 글로. ★원본 CSV 를 던지지 않는다 — 던지면 숫자를
    지어낸다. 우리가 센 것만 준다."""
    ml, rule, ag = ev["ml"], ev["rule"], ev["agree"]
    L = [f"[시각] {ev['at']}"]
    if ml.get("ok"):
        L += [
            "",
            "[ML 조기예측 · chronos-2 · 재학습 없음]",
            f"- 10분 내 임계 초과 확률 {_pct(ml['p10'])} ({ml['level10']})",
            f"- 30분 내 초과 확률 {_pct(ml['p30'])} ({ml['level30']})",
            f"- 단계: {ml['stage_name']}"
            + (f" · 약 {ml['lead_min']}분 뒤 예상" if ml.get("lead_min") else ""),
            f"- 10분 평균 반송시간 {ml['smoothed']}분 / 임계 {ml['threshold']}분"
            + (f" (임계의 {ml['near_pct']}%)" if ml.get("near_pct") else ""),
            f"- 순간값 {ml['raw']}분",
        ]
        if ml.get("d_p10") is not None:
            L.append(f"- 최근 {WINDOW_MIN}분 변화: 10분확률 {ml['d_p10']:+.2f}"
                     f" · 10분평균 {ml['d_smoothed']:+.2f}분"
                     if ml.get("d_smoothed") is not None
                     else f"- 최근 {WINDOW_MIN}분 변화: 10분확률 {ml['d_p10']:+.2f}")
        if ml.get("onset"):
            o = ml["onset"]
            L.append(f"- 이 단계는 {o['at']} 부터입니다 (단계 {o['from']}→{o['to']})")
        if ml.get("reason"):
            L.append(f"- ML 이 붙인 사유: {ml['reason']}")
    else:
        L += ["", f"[ML] 근거 없음 — {ml.get('error')}"]

    if rule.get("ok"):
        L += ["", "[같은 시각 실시간 관제 (룰베이스, 0~100점)]",
              f"- 점수 {rule['score']} ({rule['level']}) · 경보 기준 {rule['floor']}점"]
        if rule.get("items"):
            L.append(f"- 점수를 밀어올린 지표 ({rule.get('note') or '평소 대비 편차 기준'}):")
            for i in rule["items"]:
                L.append(f"  · {i['label']} {i['value']}{i['unit']}"
                         f" (평소 {i['base']}{i['unit']}, 기여 {i['pct']}%)")
    else:
        L += ["", f"[실시간 관제] 근거 없음 — {rule.get('error')}"]

    L += ["", f"[두 시스템 비교] {ag['verdict']}"]
    return "\n".join(L)


_SYSTEM_EXTRA = """
너는 지금 **ML 조기예측이 왜 이 판정을 냈는지** 를 관제 담당자에게 설명한다.

지켜야 할 것
1. **아래 [근거] 에 있는 숫자만 쓴다.** 없는 값을 지어내지 마라. 근거에
   없으면 "그 값은 없습니다" 라고 써라.
2. ML 과 룰베이스는 **독립된 두 시스템**이다. 눈금이 다르다(룰 0~100점 /
   ML 은 반송시간 초과 확률). 누가 맞다고 판정하지 말고, 둘이 같은 말을
   했는지·누가 먼저 말했는지를 짚어라.
3. 확률이 낮아도 10분 평균이 임계에 가까우면 그게 더 중요한 신호다.
4. 길게 쓰지 마라. 아래 형식 그대로, 전체 400자 이내.

형식 (이 세 줄만):
**무슨 일인가** — 한두 문장.
**왜 이렇게 나왔나** — 근거의 숫자를 짚어서 두세 문장.
**무엇을 보면 되나** — 지금 확인할 것 한 가지. 조치를 지시하지는 마라.
"""


def explain(at, cfg: dict, use_llm: bool = True) -> dict:
    """그 1분에 대한 근거 + (되면) LLM 설명.

    ★LLM 이 죽어도 근거는 그대로 돌려준다. 설명이 없는 것과 아무것도 없는
      것은 다르다.
    """
    import ml_feed
    if not isinstance(at, datetime):
        at = _dt(at)
    if at is None:
        return {"ok": False, "error": "시각을 읽을 수 없습니다"}

    mc = ml_feed.cfg_of(cfg)
    ml = ml_evidence(at, cfg)
    rule = rule_evidence(at, cfg)
    ev = {"ok": True, "at": at.strftime("%Y-%m-%d %H:%M"),
          "ml": ml, "rule": rule,
          "agree": agreement(ml, rule, _f(mc.get("p_on"), 0.30))}
    ev["evidence_text"] = evidence_text(ev)

    if not use_llm:
        return ev
    if not ml.get("ok") and not rule.get("ok"):
        ev["llm_error"] = "근거가 없어 LLM 에 묻지 않았습니다"
        return ev
    try:
        import llm_client
        sysmsg = llm_client.build_system_prompt(cfg) + "\n" + _SYSTEM_EXTRA
        txt, err = llm_client.chat(
            [{"role": "system", "content": sysmsg},
             {"role": "user", "content": "[근거]\n" + ev["evidence_text"]}],
            cfg=cfg, temperature=0.2, max_tokens=700)
        if err or not (txt or "").strip():
            ev["llm_error"] = err or "LLM 빈 응답"
        else:
            ev["why"] = llm_client.scrub(txt.strip())
    except Exception as e:
        ev["llm_error"] = f"{type(e).__name__}: {e}"
    return ev
