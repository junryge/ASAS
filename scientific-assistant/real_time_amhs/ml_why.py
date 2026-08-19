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

import re
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


HEADS = ("무슨 일인가", "왜 이렇게 나왔나", "무엇을 보면 되나")
MAX_TOKENS = 1400          # ★사고 모델이 서론을 쓰다 답을 못 끝내던 폭을 감안


def models(cfg: dict) -> list[dict]:
    """고를 수 있는 모델 — 기본 모델 + 분석 4단계 모델.

    ★어떤 모델이 답했는지 모르면, 답이 이상할 때 무엇을 바꿔야 할지 알 수
      없다. 고를 수 있게 하고, 쓴 모델을 화면에 적는다.
    """
    lc = (cfg.get("llm") or {})
    out, seen = [], set()

    def add(mid, note):
        mid = str(mid or "").strip()
        if mid and mid not in seen:
            seen.add(mid)
            out.append({"id": mid, "note": note})

    add((lc.get("ml_why") or {}).get("model"), "ML 해석 지정")
    add(lc.get("model"), "기본")
    roles = ((lc.get("analysis") or {}).get("roles") or {})
    for key, label in (("final", "최종 통합"), ("p2", "원인 해석"),
                       ("p1", "데이터 훑기"), ("p3", "대조 검증")):
        add((roles.get(key) or {}).get("model"), label)
    return out


def default_model(cfg: dict) -> str:
    m = models(cfg)
    return m[0]["id"] if m else ""


_HEAD_RE = re.compile(r"\*{0,2}\s*(무슨 일인가|왜 이렇게 나왔나|무엇을 보면 되나)\s*\*{0,2}")
_END_OK = ("다.", "요.", "다", "요", ".", "!", "?", "요·")


def _clean_answer(raw: str) -> tuple[str, str]:
    """모델 출력에서 답만 꺼낸다 → (본문, 거절사유).

    ★실제로 이런 게 왔다 —
        "Thinking Process:\n1. Analyze the Request: * Role: SK Hynix …"
      영어 사고과정을 통째로 쏟고, 그러다 max_tokens 에 걸려 답은 문장
      중간에 잘렸다. 부탁으로는 안 막힌다. 나온 걸 검사해서 걸러야 한다.
    """
    import llm_client
    t = llm_client._strip_think(raw or "")
    # 첫 소제목 앞은 전부 서론·사고과정이다 — 잘라 버린다
    m = _HEAD_RE.search(t)
    if not m:
        return "", "형식이 어긋남 (소제목이 없음 — 사고과정만 왔을 수 있음)"
    t = t[m.start():].strip()

    got = [h for h in HEADS if h in t]
    if len(got) < len(HEADS):
        return "", f"형식이 어긋남 (빠진 항목: {', '.join(h for h in HEADS if h not in got)})"
    if not llm_client._is_korean(t, 0.25):
        return "", "한국어가 아님 (영어로 답했습니다)"
    # ★마지막 항목이 문장 중간에 끊긴 것 — 잘린 답을 보여 주면 안 된다
    tail = t.rstrip().rstrip("*_ ").rstrip()
    if not tail.endswith(_END_OK):
        return "", "답이 중간에 잘림 (사고과정에 토큰을 다 씀)"
    return llm_client.scrub(t), ""


def _ask(cfg: dict, model: str, user: str) -> tuple[str, str, str]:
    """한 번 물어본다 → (본문, 사유, 실제 쓴 모델).

    ★사고 차단은 '부탁' 이 아니라 게이트웨이 옵션으로 건다. 이 저장소가
      JSON 경로에서 이미 배운 것이다 — '/no_think' 는 무시당한다.
      모르는 키를 받은 게이트웨이는 400 을 내므로, 400 이면 옵션을 빼고
      한 번 더 부른다 (400 은 즉답이라 사실상 공짜다).
    """
    import llm_client
    lc = dict(cfg.get("llm") or {})
    use = str(model or "").strip() or default_model(cfg)
    c2 = dict(cfg)
    if use:
        lc["model"] = use
        c2 = {**cfg, "llm": lc}
    sysmsg = llm_client.build_system_prompt(c2) + "\n" + _SYSTEM_EXTRA
    msgs = [{"role": "system", "content": sysmsg},
            {"role": "user", "content": "[근거]\n" + user}]

    tiers = [{"chat_template_kwargs": {"enable_thinking": False}}, None]
    last = ""
    for extra in tiers:
        txt, err = llm_client.chat(msgs, cfg=c2, temperature=0.2,
                                   max_tokens=MAX_TOKENS, extra=extra)
        if err:
            last = err
            if "400" in str(err):          # 게이트웨이가 모르는 옵션 — 빼고 재시도
                continue
            return "", err, use
        body, why = _clean_answer(txt or "")
        if body:
            return body, "", use
        last = why
        break
    return "", last or "LLM 빈 응답", use


def plain_why(ev: dict) -> str:
    """LLM 없이 근거만으로 쓴 한국어 요약.

    ★"모델이 이상한 답을 냈습니다" 로 끝내면 관제는 아무것도 못 한다.
      숫자는 이미 다 계산해 뒀으니 문장으로 옮기는 건 우리가 할 수 있다.
    """
    ml, rule, ag = ev["ml"], ev["rule"], ev["agree"]
    L = []
    if ml.get("ok"):
        near = f" (임계 {ml['threshold']}분의 {ml['near_pct']}%)" if ml.get("near_pct") else ""
        L.append(f"**무슨 일인가** — {ev['at']} 기준 단계는 “{ml['stage_name']}”이고, "
                 f"10분 평균 반송시간은 {ml['smoothed']}분{near}입니다. "
                 f"10분 내 임계 초과 확률은 {_pct(ml['p10'])}입니다.")
        why = []
        if ml.get("d_smoothed") is not None:
            move = "올라오는 중" if ml["d_smoothed"] > 0 else (
                "내려가는 중" if ml["d_smoothed"] < 0 else "변화 없음")
            why.append(f"최근 {WINDOW_MIN}분 동안 10분 평균이 {ml['d_smoothed']:+.2f}분 움직여 {move}입니다")
        if ml.get("onset"):
            why.append(f"이 단계는 {ml['onset']['at']}부터입니다")
        if rule.get("ok") and rule.get("items"):
            top = rule["items"][0]
            # ★조사('로/으로')가 단위에 따라 갈리므로 아예 조사를 안 쓰는
            #   문장으로 짠다 — 억지로 붙이면 '8.6분 로' 같은 게 나온다
            why.append(f"같은 시각 실시간 관제 점수는 {rule['score']}점({rule['level']})이고, "
                       f"가장 크게 기여한 건 {top['label']}입니다 "
                       f"(평소 {top['base']}{top['unit']} → {top['value']}{top['unit']}, "
                       f"기여 {top['pct']}%)")
        L.append(("**왜 이렇게 나왔나** — " + ". ".join(why) + ".") if why
                 else "**왜 이렇게 나왔나** — 추가로 짚을 변화가 없습니다.")
    else:
        L.append(f"**무슨 일인가** — {ev['at']} 의 ML 예측을 찾지 못했습니다 "
                 f"({ml.get('error')}).")
        L.append("**왜 이렇게 나왔나** — 근거가 없어 설명할 수 없습니다.")
    L.append(f"**무엇을 보면 되나** — {ag['verdict'].rstrip('.')}. "
             + ("10분 평균이 임계에 계속 붙는지 보세요."
                if (ml.get("near_pct") or 0) >= 70 else "추이가 뒤집히는지 보세요."))
    out = "\n".join(L)
    try:                       # 조사 다듬기는 이미 있는 것을 쓴다
        import llm_client
        return llm_client._fix_josa(out)
    except Exception:
        return out


def explain(at, cfg: dict, use_llm: bool = True, model: str = "") -> dict:
    """그 1분에 대한 근거 + 설명.

    ★LLM 이 죽어도, 영어로 답해도, 답을 못 끝내도 — 근거는 그대로 두고
      한국어 요약이라도 낸다. 그리고 무엇으로 만들었는지 밝힌다.
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
          "agree": agreement(ml, rule, _f(mc.get("p_on"), 0.30)),
          "models": models(cfg)}
    ev["evidence_text"] = evidence_text(ev)

    if not use_llm:
        return ev
    if not ml.get("ok") and not rule.get("ok"):
        ev["llm_error"] = "근거가 없어 LLM 에 묻지 않았습니다"
        ev["why"], ev["used"] = plain_why(ev), "규칙"
        return ev
    try:
        body, why_err, used_model = _ask(cfg, model, ev["evidence_text"])
        ev["model"] = used_model
        if body:
            ev["why"], ev["used"] = body, "llm"
        else:
            ev["llm_error"] = why_err
            ev["why"], ev["used"] = plain_why(ev), "규칙"
    except Exception as e:
        ev["llm_error"] = f"{type(e).__name__}: {e}"
        ev["why"], ev["used"] = plain_why(ev), "규칙"
    return ev
