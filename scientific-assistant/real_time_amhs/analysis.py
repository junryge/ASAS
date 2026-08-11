"""
real_time_amhs/analysis.py — 4-LLM 파이프라인 분석 (분석 탭)

구조 (모델 4종 — 게이트웨이가 이 팀에 허용한 이름만 쓴다)
    1차  gaia-GLM-5.2            데이터 훑기 (★병렬)
    2차  gaia-Qwen3.6-35B-A3B    원인·전파 분석
    3차  gaia-lst-gpt-oss-120b   교차 검증 + 조치 (1·2차·최종과 다른 계열)
    최종 gaia-Qwen3.5-397B-A17B  통합 판정 리포트

    ※ 실호출로 죽은 것을 뺀 결과다 — gaia-GLM-5.1(400 Invalid model name),
      gaia-solution-Qwen3-235B…(403 team not allowed), gaia-cc-gpt-oss-120b(없음).
      그래도 모델이 거부되면 _fallbacks() 가 자동으로 갈아타고, 모든 단계는
      최대 retries(기본 3)회까지 재시도한다. 3차의 대체 순서는 gpt-oss 계열을
      먼저 두어, 갈아타더라도 '다른 눈' 이라는 성격을 최대한 유지한다.

왜 이 구조인가
    - **1차가 병렬이다.** 분석 구간을 시간 조각으로 쪼개 GLM-5.2 를 조각마다
      동시에 부른다. 조각당 데이터가 작아져 관찰이 촘촘해지고, 벽시계 시간은
      조각 1개 값이다. 1차는 '사실 관찰'만 시킨다 — 해석은 다음 단계 몫.
    - **2차는 취합·해석.** 1차 관찰들과 전체 통계를 받아 원인과 전파 순서를
      재구성한다.
    - **3차는 남이 검증.** 다른 모델이 1·2차 주장을 데이터 요약과 대조해
      확인/의심/반박으로 판정하고 조치를 만든다. 같은 모델이 자기 답을
      검증하면 후하게 주는(self-bias) 문제를 모델을 바꿔 줄인다.
    - **최종은 최대 모델.** 검증까지 끝난 재료로 관제용 리포트만 쓴다.
    - 어느 단계가 실패해도 멈추지 않는다 — 실패를 표시하고 남은 재료로 간다.

데이터
    하루 전체 또는 시간 구간(HH:MM~HH:MM). CSV 원문 대신 다이제스트
    (시간대 집계 + 사건 구간 + 지표 요약 + 분단위 표본)를 쓴다.

결과 저장
    data/analysis/A{day}_{HHMMSS}.json — UI 는 목록/조회만 한다.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime

from lp_client import load_config
from sentinel import _row_dt, _score, alarm_floor, grade

_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 단계 정의 ──────────────────────────────────────────────────────
STAGES = {
    "p1": {"name": "1차 — 데이터 훑기", "icon": "🔍",
           "model": "gaia-GLM-5.2", "parallel": True},
    "p2": {"name": "2차 — 원인·전파 분석", "icon": "🧩",
           "model": "gaia-Qwen3.6-35B-A3B", "parallel": False},
    "p3": {"name": "3차 — 교차 검증·조치", "icon": "⚖️",
           "model": "gaia-lst-gpt-oss-120b", "parallel": False},
    "final": {"name": "최종 — 통합 판정", "icon": "📋",
              "model": "gaia-Qwen3.5-397B-A17B", "parallel": False},
}

DEFAULTS = {
    "digest_max_chars": 7000,
    "chunk_max": 3,              # 1차 병렬 조각 수 상한
    "p1_max_tokens": 1500,
    "p2_max_tokens": 1400,
    "p3_max_tokens": 1600,
    "final_max_tokens": 2200,
    "timeout_s": 150,
    "retries": 3,            # 단계별 최대 시도 횟수
    "retry_backoff_s": 2,    # 일시 오류 재시도 간격(회차에 비례)
}


def _acfg(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg.get("llm", {}) or {}).get("analysis") or {})
    return c


def _stage_model(cfg: dict, sid: str) -> str:
    """단계별 모델 — config.llm.analysis.roles.{id}.model → 없으면 위 기본값."""
    a = (cfg.get("llm", {}) or {}).get("analysis") or {}
    r = (a.get("roles") or {}).get(sid) or {}
    return r.get("model") or STAGES[sid]["model"]


def _stage_cfg(cfg: dict, sid: str) -> dict:
    c = dict(cfg)
    lc = dict(cfg.get("llm", {}))
    lc["model"] = _stage_model(cfg, sid)
    c["llm"] = lc
    return c


# ────────────────────────── 데이터 준비 ──────────────────────────
def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _metrics(cfg: dict) -> list[dict]:
    ui = cfg.get("ui") or {}
    for g in (ui.get("metric_groups") or []):
        ms = [m for m in (g.get("metrics") or [])
              if isinstance(m, dict) and m.get("key") and m["key"] != "unified_risk_score"]
        if ms:
            return ms[:8]
    return [m for m in (ui.get("strip_metrics") or [])
            if isinstance(m, dict) and m.get("key") != "unified_risk_score"][:8]


def _window_seq(day: str, cfg: dict, start: str = "", end: str = ""):
    """그 날짜 CSV 의 [start,end] 구간을 (dt, score, row) 시퀀스로."""
    from store_csv import read_day
    seq = []
    for r in (read_day(day, cfg) or []):
        d = _row_dt(r)
        if d is None:
            continue
        hm = d.strftime("%H:%M")
        if start and hm < start:
            continue
        if end and hm > end:
            continue
        seq.append((d, _score(r), r))
    seq.sort(key=lambda x: x[0])
    return seq


def _overview(seq, cfg: dict, span: str) -> tuple[str, dict]:
    """전체 통계 요약 (2차·3차·최종에 공통으로 주는 머리) + 메타.

    ★검증이 가능하려면 판정 기준과 근거 원자료가 프롬프트 안에 있어야 한다.
      등급 기준 · 임계 · 사건 목록 · AMOS 발동 지표(raw 컬럼) · 지표 통계를
      모두 싣는다. 3차 검증가는 이 숫자로 1·2차 주장을 대조한다.
    """
    from daily import (_minutes as day_minutes, amos_rows, incidents as day_incidents,
                       incident_rows)
    floor = alarm_floor(cfg)
    scores = [s for _, s, _ in seq]
    peak_i = max(range(len(seq)), key=lambda i: seq[i][1])
    peak_d, peak_s, peak_r = seq[peak_i]
    g = grade(peak_s, cfg)
    raw = [{**r, "datetime": d.strftime("%Y-%m-%d %H:%M")} for d, s, r in seq]
    mins = day_minutes(raw, cfg)
    inc_objs = day_incidents(mins)
    incs = incident_rows(inc_objs)

    bands = ", ".join(f"{b['min']}~{b['max']} {b['level']}"
                      for b in (cfg.get("grade", {}) or {}).get("bands", []))
    L = [f"[판정 기준] 알람 임계 {floor}점 · 등급: "
         f"{(cfg.get('grade',{}) or {}).get('normal_max',49)} 이하 정상, {bands}",
         "",
         f"[전체 통계] 구간 {span} · {len(seq)}분",
         f"- 최고 {g['emoji']} {g['level']} {peak_s:.0f}점 ({peak_d:%H:%M}, "
         f"{peak_r.get('hot_area') or '-'}) · 평균 {sum(scores)/len(scores):.0f}점 "
         f"· 최저 {min(scores):.0f}점 · 임계 이상 {sum(1 for s in scores if s >= floor)}분"]

    L.append("\n[사건 목록] (점수 50+ 연속 구간 · 시각=최고점)")
    if incs:
        for i in incs:
            L.append(f"- #{i['번호']} {i['구간']} ({i['지속분']}분) 최고 {i['최고점수']}점 "
                     f"{i['최고등급']} · 시작영역 {i['시작영역']}")
    else:
        L.append("- 없음 (임계를 넘은 구간 없음)")

    # AMOS 발동 지표 — 어떤 raw 컬럼이 실제로 떴는지 (검증의 핵심 근거)
    try:
        arows = amos_rows(inc_objs, mins)
    except Exception:
        arows = []
    if arows:
        L.append("\n[AMOS 이상감지] (사건별 HID 구간 + 발동한 raw 컬럼)")
        for a in arows:
            L.append(f"- #{a.get('번호')} {a.get('이상감지 시간')} {a.get('심각도')}")
            L.append(f"  구간: {str(a.get('이상감지 구간','')).replace('<br>', ' ')}")
            L.append(f"  항목: {str(a.get('이상감지 항목','')).replace('<br>', ' / ')}")

    L.append("\n[지표 통계] (지표 | 최소 | 최대 | 평균 | 최고점 시각의 값)")
    for m in _metrics(cfg):
        pairs = [(d, _num(r.get(m["key"]))) for d, _, r in seq]
        vals = [v for _, v in pairs if v is not None]
        if not vals:
            continue
        at_peak = next((v for d, v in pairs if d == peak_d and v is not None), None)
        L.append(f"- {m.get('label') or m['key']}({m.get('unit','')}) [{m.get('raw') or m['key']}] "
                 f"| {min(vals):.1f} | {max(vals):.1f} | {sum(vals)/len(vals):.1f} | "
                 f"{at_peak if at_peak is not None else '-'}")

    meta = {"peak": {"score": round(peak_s, 1), "time": f"{peak_d:%H:%M}",
                     "level": g["level"], "emoji": g["emoji"],
                     "area": peak_r.get("hot_area") or "-"},
            "incidents": len(incs), "floor": floor, "minutes": len(seq)}
    return "\n".join(L), meta


def _chunks(seq, cfg: dict) -> list[dict]:
    """1차 병렬용 시간 조각 — 연속 구간을 최대 chunk_max 개로 등분.

    사건이 조각 경계에 걸려도 2차가 관찰을 취합하며 잇는다. 조각마다
    분단위 라인(점수·구역·발동사유)을 그대로 준다 — 1차는 원자료를 본다.
    """
    from sentinel import summarize_reason
    n = max(1, min(int(_acfg(cfg)["chunk_max"]), (len(seq) + 59) // 60))
    size = (len(seq) + n - 1) // n
    floor = alarm_floor(cfg)
    out = []
    for i in range(0, len(seq), size):
        part = seq[i:i + size]
        if not part:
            continue
        lines = []
        for d, s, r in part:
            why = summarize_reason(str(r.get("reason") or ""),
                                   r.get("hot_area") or "") if s >= floor else ""
            lines.append(f"{d:%H:%M} | {s:.0f} | {r.get('hot_area') or '-'}"
                         + (f" | {why}" if why else ""))
        # 조각 안 지표 스냅샷 (시작→끝 변화)
        mets = []
        for m in _metrics(cfg):
            vals = [v for v in (_num(r.get(m["key"])) for _, _, r in part) if v is not None]
            if vals:
                mets.append(f"{m.get('label') or m['key']}: {vals[0]:.1f}→{vals[-1]:.1f}"
                            f" (최대 {max(vals):.1f}{m.get('unit','')})")
        out.append({"span": f"{part[0][0]:%H:%M}~{part[-1][0]:%H:%M}",
                    "text": ("[분단위: 시각 | 점수 | 구역 | 발동사유]\n"
                             + "\n".join(lines[:90])
                             + "\n[지표 변화]\n" + "\n".join(mets))})
    return out


# ────────────────────────── LLM 호출 공통 ──────────────────────────
def _repair_json(t: str) -> dict | None:
    """잘린 JSON 살리기 — 열린 괄호를 닫고 다시 파싱한다.

    max_tokens 에 걸려 배열 중간에서 끊기면 균형 잡힌 {…} 가 없어 통째로
    버려진다. 문자열을 닫고 열린 [ { 를 역순으로 닫아 주면 대부분 살아난다.
    """
    s = str(t or "").strip()
    i = s.find("{")
    if i < 0:
        return None
    s = s[i:]
    depth, instr, esc = [], False, False
    for ch in s:
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch in "[{":
            depth.append(ch)
        elif ch in "]}":
            if depth:
                depth.pop()
    fixed = s.rstrip().rstrip(",")
    if instr:
        fixed += '"'
    for ch in reversed(depth):
        fixed += "}" if ch == "{" else "]"
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


def _parse_or_none(txt: str, required: tuple = ()) -> dict | None:
    """JSON 추출 — 단, **산문이 JSON 으로 둔갑하는 것을 막는다.**

    프리필('{"원인": "')이 붙은 상태로 모델이 산문을 쓰면, 괄호 복구가
    {"원인": "…산문…"} 같은 '형식은 맞지만 내용은 쓰레기' 를 만들어낸다.
    그래서 스키마의 주요 키가 최소 2개는 있어야 통과시킨다.
    """
    from llm_client import _json_candidates, scrub

    def ok(v):
        if not isinstance(v, dict):
            return False
        if not required:
            return True
        hit = sum(1 for k in required if k in v)
        return hit >= min(2, len(required))

    t = scrub(txt or "")
    for cand in reversed(_json_candidates(t)):
        try:
            v = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if ok(v):
            return v
    v = _repair_json(t)                    # 잘린 응답 구제
    return v if ok(v) else None


# 3차(검증)는 1·2차와 **다른 계열**이어야 의미가 있다. 그래서 대체 순서도
# 단계마다 다르게 둔다 — 검증 단계는 gpt-oss 계열을 먼저 시도하고,
# 앞 단계가 쓴 모델은 맨 뒤로 민다.
_FALLBACK_BY_ROLE = {
    "p1": ("gaia-Qwen3.6-35B-A3B", "gaia-Qwen3.5-397B-A17B", "GaiA-LLM-Latest"),
    "p2": ("gaia-GLM-5.2", "gaia-Qwen3.5-397B-A17B", "GaiA-LLM-Latest"),
    # 검증 — 다른 계열(gpt-oss) 우선, 마지막에야 앞 단계와 같은 계열로
    "p3": ("gpt-oss-120b", "GaiA-LLM-Latest", "gaia-Qwen3.5-397B-A17B",
           "gaia-Qwen3.6-35B-A3B"),
    "final": ("gaia-GLM-5.2", "gaia-Qwen3.6-35B-A3B", "GaiA-LLM-Latest"),
}


def _fallbacks(cfg: dict, sid: str) -> list[str]:
    """이 단계의 대체 모델 순서 — 지정 모델이 400/403 이면 이 순서로 갈아탄다.

    config.llm.analysis.fallback_by_role.{sid} → fallback_models → 위 기본값.
    """
    a = (cfg.get("llm", {}) or {}).get("analysis") or {}
    cur = _stage_model(cfg, sid)
    by_role = (a.get("fallback_by_role") or {}).get(sid)
    if isinstance(by_role, list) and by_role:
        return [m for m in by_role if m and m != cur]
    fb = a.get("fallback_models")
    if isinstance(fb, list) and fb:
        return [m for m in fb if m and m != cur]
    return [m for m in _FALLBACK_BY_ROLE.get(sid, ()) if m != cur]


_MODEL_ERR = ("Invalid model name", "team not allowed", "HTTP 400", "HTTP 403", "HTTP 404")


def _call_stage(sid: str, user: str, prefill: str, max_tokens: int, cfg: dict,
                want_json: bool = True,
                required: tuple = ()) -> tuple[object, str, float, str, list[str]]:
    """단계 1회 — **성공할 때까지 최대 N회 재시도**. (결과, 안내/오류, 초, 모델, 로그)

    실패는 세 종류이고 대응이 다르다.
      · 모델 거부(400 Invalid model / 403 not allowed / 404) → 다음 대체 모델로.
        같은 모델로 다시 걸어도 영원히 같은 답이라 즉시 갈아탄다.
      · 일시 오류(타임아웃·5xx·네트워크) → 잠깐 쉬었다 같은 모델로 다시.
      · JSON 이 아니거나 잘림 → 괄호 복구 시도 → 안 되면 '짧게 JSON 만' 을
        덧붙여 다시. 그래도 안 되면 모델을 바꿔 본다.

    want_json=False 면 마크다운 본문을 그대로 받는다 (최종 단계).
    """
    from llm_client import build_system_prompt, chat
    t0 = time.time()
    a = _acfg(cfg)
    tries = max(1, int(a.get("retries", 3)))
    backoff = float(a.get("retry_backoff_s", 2))
    sys_msg = {"role": "system", "content": build_system_prompt(cfg)}
    primary = _stage_model(cfg, sid)
    models = [primary] + _fallbacks(cfg, sid)
    log: list[str] = []

    def call(model: str, u: str):
        c = dict(cfg)
        lc = dict(cfg.get("llm", {}))
        lc["model"] = model
        c["llm"] = lc
        try:
            return chat([sys_msg, {"role": "user", "content": u}], c,
                        max_tokens=max_tokens, prefill=prefill)
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    mi, hint, last_err = 0, "", ""
    for attempt in range(1, tries + 1):
        model = models[min(mi, len(models) - 1)]
        txt, err = call(model, user + hint)

        if err and any(k in str(err) for k in _MODEL_ERR):
            log.append(f"{attempt}회 {model}: 모델 거부 → 대체")
            last_err = err
            mi += 1
            if mi >= len(models):
                break
            continue

        if err:
            log.append(f"{attempt}회 {model}: {str(err)[:80]}")
            last_err = err
            if attempt < tries:
                time.sleep(backoff * attempt)      # 일시 오류 → 쉬었다 재시도
            continue

        if not want_json:
            log.append(f"{attempt}회 {model}: 성공")
            note = "" if model == primary else f"(대체 모델: {model})"
            if attempt > 1:
                note = (note + f" ({attempt}회째 성공)").strip()
            return txt, note, round(time.time() - t0, 1), model, log

        res = _parse_or_none(txt, required)
        if res is not None:
            log.append(f"{attempt}회 {model}: 성공")
            note = "" if model == primary else f"(대체 모델: {model})"
            if attempt > 1:
                note = (note + f" ({attempt}회째 성공)").strip()
            return res, note, round(time.time() - t0, 1), model, log

        log.append(f"{attempt}회 {model}: JSON 형식 아님/키 부족")
        last_err = "JSON 형식 아님 (필수 키 없음)"
        hint = ("\n\n★앞 응답이 JSON 형식이 아니었다. 설명·서론·코드펜스 없이 "
                "**JSON 하나만** 출력하라. 배열 항목은 2개 이내로 짧게.")
        if attempt >= 2:                     # 두 번 틀리면 모델을 바꿔 본다
            mi += 1
        if attempt < tries:
            time.sleep(min(backoff, 1.5))

    return (None, f"{tries}회 시도 모두 실패 — {last_err} [{' / '.join(log)}]",
            round(time.time() - t0, 1), models[min(mi, len(models) - 1)], log)


# 단계별 필수 키 — 이게 없으면 '형식만 JSON' 인 쓰레기로 보고 재시도한다
_REQUIRED = {
    "p1": ("구간", "최고점수", "점수흐름", "관찰"),
    "p2": ("원인", "핫구역", "전파경로", "요약"),
    "p3": ("검증", "즉시조치", "요약"),
}


def _ask_json(sid: str, user: str, prefill: str, max_tokens: int,
              cfg: dict) -> tuple[dict | None, str, float, str]:
    """JSON 단계 — _call_stage 의 얇은 껍데기 (기존 호출부 유지)."""
    res, note, took, model, _log = _call_stage(sid, user, prefill, max_tokens, cfg,
                                               want_json=True,
                                               required=_REQUIRED.get(sid, ()))
    return (res if isinstance(res, dict) else None), note, took, model


_KOREAN_RULE = "★한국어로만. 추론 과정 금지. 데이터에 없는 것을 지어내지 마라.\n"


# ────────────────────────── 단계별 실행 ──────────────────────────
def _stage1(chunks: list[dict], cfg: dict, prog: dict) -> tuple[list[dict], list[str], list[str]]:
    """1차 (병렬) — 조각마다 GLM-5.2 가 '사실 관찰'만 뽑는다."""
    a = _acfg(cfg)
    results: list = [None] * len(chunks)
    errors: list[str] = []
    models_used: set = set()

    def work(i: int, ch: dict):
        user = (f"[역할] 너는 반송 데이터 1차 분석가다. 아래 {ch['span']} 구간 "
                f"분단위 데이터를 훑고 **관찰된 사실만** 정리하라. 원인 해석은 하지 마라.\n\n"
                f"{ch['text']}\n\n" + _KOREAN_RULE +
                "다음 JSON 만 출력하라:\n"
                '{"구간": "%s", "최고점수": 숫자, "최고시각": "HH:MM", '
                '"점수흐름": "한 줄 (예: 20점대 유지 후 08:06부터 급상승)", '
                '"이상구역": ["구역명"], '
                '"관찰": ["사실 관찰 2~4개 — 수치 포함"], '
                '"특이지표": ["눈에 띄게 변한 지표와 수치"]}' % ch["span"])
        res, err, took, used = _ask_json("p1", user, '{"구간": "',
                                         int(a["p1_max_tokens"]), cfg)
        results[i] = res
        if used:
            models_used.add(used)
        if err:
            errors.append(f"조각{i+1}({ch['span']}): {err}")
        done = sum(1 for r in results if r is not None) + len(errors)
        prog["roles"]["p1"]["status"] = f"분석중 {done}/{len(chunks)}"

    threads = [threading.Thread(target=work, args=(i, ch), daemon=True)
               for i, ch in enumerate(chunks)]
    for t in threads:
        t.start()
    deadline = time.time() + float(a["timeout_s"])
    for t in threads:
        t.join(max(1.0, deadline - time.time()))
    obs = [r for r in results if r]
    return obs, errors, sorted(models_used)


def _stage2(overview: str, obs: list[dict], cfg: dict) -> tuple[dict | None, str, float, str]:
    """2차 — 1차 관찰을 취합해 원인·전파를 해석한다."""
    a = _acfg(cfg)
    user = (f"[역할] 너는 반송 데이터 2차 분석가다. 전체 통계와 1차 분석가들의 "
            f"구간별 관찰을 받아 **원인과 전파 순서**를 해석하라.\n\n"
            f"{overview}\n\n[1차 관찰 (구간별 병렬 분석)]\n"
            f"{json.dumps(obs, ensure_ascii=False)}\n\n" + _KOREAN_RULE +
            "다음 JSON 만 출력하라:\n"
            '{"원인": "근본 원인 1~2문장 (수치 근거 포함)", '
            '"핫구역": ["가장 문제인 구역"], '
            '"전파경로": "A구역 HH:MM → B구역 HH:MM 형식 (전파 없으면 \\"단일 구역\\")", '
            '"선행신호": "가장 먼저 움직인 지표와 시각", '
            '"구역진단": [{"구역": "이름", "상태": "한 줄", "근거": "수치"}], '
            '"요약": "3문장 이내"}')
    return _ask_json("p2", user, '{"원인": "', int(a["p2_max_tokens"]), cfg)


def _stage3(overview: str, obs: list[dict], p2: dict | None, chunks: list[dict],
            cfg: dict) -> tuple[dict | None, str, float, str]:
    """3차 — 다른 모델이 1·2차 주장을 **원자료와 직접 대조**해 검증한다.

    검증가에게 1·2차의 '말'만 주면 그럴듯함만 보고 통과시킨다. 그래서 분단위
    원자료를 함께 주고, 판정마다 그 자료에서 뽑은 수치를 쓰게 강제한다.
    """
    a = _acfg(cfg)
    cap = int(a["digest_max_chars"])
    raw = "\n\n".join(f"[{c['span']}]\n{c['text']}" for c in chunks)[:cap]
    user = (f"[역할] 너는 3차 검증 분석가다. 1·2차 분석가의 주장을 **원자료와 직접 "
            f"대조**해 판정하라. 그럴듯하다고 통과시키지 마라.\n\n"
            f"판정 규칙 (엄격히):\n"
            f"- 확인 = 원자료에서 그 수치/시각을 직접 찾을 수 있다\n"
            f"- 의심 = 방향은 맞지만 수치·시각이 어긋나거나 근거가 부족하다\n"
            f"- 반박 = 원자료와 어긋난다 (틀린 수치·없는 시각·없는 구역)\n"
            f"- 근거에는 **원자료에서 뽑은 실제 수치와 시각**을 반드시 쓴다. "
            f"근거를 못 대면 '확인' 을 줄 수 없다.\n\n"
            f"{overview}\n\n[원자료 — 분단위]\n{raw}\n\n"
            f"[1차 관찰]\n{json.dumps(obs, ensure_ascii=False)}\n\n"
            f"[2차 해석]\n{json.dumps(p2 or {}, ensure_ascii=False)}\n\n" + _KOREAN_RULE +
            "다음 JSON 만 출력하라:\n"
            '{"검증": [{"주장": "1·2차의 주요 주장 (원문 그대로)", "판정": "확인|의심|반박", '
            '"근거": "원자료에서 뽑은 수치·시각"}], '
            '"확인된사실": ["검증을 통과한 사실만 1~4개"], '
            '"즉시조치": ["확인된 사실만 근거로 한 조치 1~3개"], '
            '"모니터링": ["지켜볼 것 1~3개"], '
            '"에스컬레이션": "필요 없으면 \\"불필요\\", 필요하면 누구에게 무엇을", '
            '"요약": "2문장 — 무엇이 확인됐고 무엇이 의심인가"}')
    return _ask_json("p3", user, '{"검증": [{"주장": "', int(a["p3_max_tokens"]), cfg)


def _stage_final(overview: str, obs: list[dict], p2: dict | None, p3: dict | None,
                 cfg: dict) -> tuple[str, str, float, str]:
    """최종 — 최대 모델이 검증까지 끝난 재료로 관제 리포트를 쓴다."""
    from llm_client import build_system_prompt, chat, scrub
    a = _acfg(cfg)
    t0 = time.time()
    ver = (p3 or {}).get("검증") or []
    rej = [v.get("주장", "") for v in ver if str(v.get("판정", "")) == "반박"]
    sus = [v.get("주장", "") for v in ver if str(v.get("판정", "")) == "의심"]
    user = (f"검증까지 끝난 분석 재료로 관제 통합 리포트를 작성하라.\n"
            f"★3차에서 '반박'된 주장은 **절대 싣지 마라**: "
            f"{json.dumps(rej, ensure_ascii=False) if rej else '(없음)'}\n"
            f"★'의심' 인 것은 단정하지 말고 '가능성' 으로만 쓰고 주의 섹션에 남겨라: "
            f"{json.dumps(sus, ensure_ascii=False) if sus else '(없음)'}\n\n"
            f"{overview}\n\n[1차 관찰]\n{json.dumps(obs, ensure_ascii=False)}\n\n"
            f"[2차 해석]\n{json.dumps(p2 or {}, ensure_ascii=False)}\n\n"
            f"[3차 검증·조치]\n{json.dumps(p3 or {}, ensure_ascii=False)}\n\n"
            "형식 (markdown, 한국어만, 추론 과정 금지):\n"
            "## 종합 판정\n(등급·핵심 결론 2~3문장)\n"
            "## 구역 상황\n(핫구역과 전파 양상 — 검증된 것 위주)\n"
            "## 조치\n(우선순위대로 불릿)\n"
            "## 주의\n(다음 구간에서 지켜볼 것 + 의심으로 남은 부분)\n"
            "'## 종합 판정' 부터 바로 시작하라.")
    txt, note, took, model, _log = _call_stage(
        "final", user, "## 종합 판정\n", int(a["final_max_tokens"]), cfg,
        want_json=False)
    if not txt:
        return "", note or "최종 리포트 생성 실패", took, model
    return scrub(str(txt)), note, took, model


def _fallback_final(meta: dict, obs: list[dict], p2: dict | None, p3: dict | None) -> str:
    """최종 LLM 실패 시 — 있는 재료로 골격은 채운다."""
    pk = meta.get("peak") or {}
    L = ["## 종합 판정",
         f"최고 {pk.get('emoji','')} {pk.get('level','')} {pk.get('score','')}점 "
         f"({pk.get('time','')}, {pk.get('area','')}) · 사건 {meta.get('incidents',0)}건 "
         "— (최종 LLM 미연결, 단계 결과 나열)"]
    if p2:
        L += ["## 구역 상황", p2.get("요약") or p2.get("원인") or json.dumps(p2, ensure_ascii=False)[:300]]
    if p3:
        acts = p3.get("즉시조치") or []
        if acts:
            L.append("## 조치")
            L += [f"- {x}" for x in acts]
    if obs:
        L += ["## 1차 관찰"] + [f"- {o.get('구간','')}: {o.get('점수흐름','')}" for o in obs]
    return "\n".join(L)


# ────────────────────────── 실행·저장 ──────────────────────────
def _graph_svg(seq, cfg: dict) -> str:
    """분석 구간 점수 그래프 (SVG 문자열).

    글자만 있으면 판단 근거를 눈으로 못 본다. 리포트 바로 위에 같은 구간의
    점수 추이를 붙여, LLM 이 말한 시각·최고점을 그래프에서 바로 확인하게 한다.
    실패해도 분석은 그대로 간다 — 그림은 부가물이다.
    """
    if not seq:
        return ""
    try:
        from graphs import render
        rows = [r for _, _, r in seq]
        t0, t1 = seq[0][0], seq[-1][0]
        minutes = max(10, int((t1 - t0).total_seconds() / 60) + 2)
        center = t0 + (t1 - t0) / 2
        return render(rows, center, minutes=minutes, width=1100, cfg=cfg) or ""
    except Exception as e:
        print(f"[분석] ⚠️ 그래프 생성 실패(무시): {e}")
        return ""


def _store_dir(cfg: dict) -> str:
    d = (cfg.get("storage", {}) or {}).get("dir", "data")
    if not os.path.isabs(d):
        d = os.path.join(_DIR, d)
    d = os.path.join(d, "analysis")
    os.makedirs(d, exist_ok=True)
    return d


def run_analysis(day: str, cfg: dict | None = None, start: str = "",
                 end: str = "", progress: dict | None = None) -> dict:
    """4-LLM 파이프라인 1회 — 완료까지 블로킹 (서버는 스레드에서 부른다)."""
    cfg = cfg or load_config()
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    span = f"{start or '00:00'}~{end or '24:00'}"
    t0 = time.time()
    prog = progress if progress is not None else {}

    def _init_roles():
        return {sid: {"name": s["name"], "icon": s["icon"],
                      "model": _stage_model(cfg, sid), "status": "대기"}
                for sid, s in STAGES.items()}

    prog.update(stage="digest", roles=_init_roles(), done=False, error=None)

    seq = _window_seq(day, cfg, start, end)
    if not seq:
        err = f"{day} {span} 데이터 없음"
        prog.update(done=True, error=err)
        return {"ok": False, "error": err}

    overview, meta = _overview(seq, cfg, f"{day[:4]}-{day[4:6]}-{day[6:8]} {span}")
    chunks = _chunks(seq, cfg)
    stages_out: dict = {}

    # ── 1차 (병렬) ──
    prog["roles"]["p1"]["status"] = f"분석중 0/{len(chunks)}"
    t1 = time.time()
    obs, errs1, m1 = _stage1(chunks, cfg, prog)
    stages_out["p1"] = {
        "ok": bool(obs), "name": STAGES["p1"]["name"], "icon": STAGES["p1"]["icon"],
        "model": ", ".join(m1) or _stage_model(cfg, "p1"),
        "took_s": round(time.time() - t1, 1),
        "result": {"조각수": len(chunks), "성공": len(obs), "관찰": obs},
        "error": "; ".join(errs1) if errs1 and not obs else
                 ("; ".join(errs1) if errs1 else None),
    }
    prog["roles"]["p1"].update(status="완료" if obs else "실패",
                               took_s=stages_out["p1"]["took_s"],
                               error=stages_out["p1"]["error"])

    # ── 2차 ──
    prog["roles"]["p2"]["status"] = "분석중"
    p2, e2, tk2, m2 = _stage2(overview, obs, cfg)
    stages_out["p2"] = {"ok": p2 is not None, "name": STAGES["p2"]["name"],
                        "icon": STAGES["p2"]["icon"], "model": m2 or _stage_model(cfg, "p2"),
                        "took_s": tk2, "result": p2,
                        "error": None if p2 else (e2 or None),
                        "note": e2 if (p2 and e2) else None}
    prog["roles"]["p2"].update(status="완료" if p2 else "실패", took_s=tk2,
                               error=None if p2 else (e2 or None))

    # ── 3차 ──
    prog["roles"]["p3"]["status"] = "분석중"
    p3, e3, tk3, m3 = _stage3(overview, obs, p2, chunks, cfg)
    stages_out["p3"] = {"ok": p3 is not None, "name": STAGES["p3"]["name"],
                        "icon": STAGES["p3"]["icon"], "model": m3 or _stage_model(cfg, "p3"),
                        "took_s": tk3, "result": p3,
                        "error": None if p3 else (e3 or None),
                        "note": e3 if (p3 and e3) else None}
    prog["roles"]["p3"].update(status="완료" if p3 else "실패", took_s=tk3,
                               error=None if p3 else (e3 or None))

    # ── 최종 ──
    prog["roles"]["final"]["status"] = "작성중"
    prog["stage"] = "final"
    body, ef, tkf, mf = _stage_final(overview, obs, p2, p3, cfg)
    # 최종은 마크다운이어야 한다. 모델이 JSON 이나 산문을 뱉으면 리포트 자리에
    # 원문이 그대로 박히므로, 헤딩이 없으면 실패로 보고 골격으로 대체한다.
    if body and "##" not in body:
        ef = (ef or "") + " (마크다운 형식 아님 — 골격으로 대체)"
        body = ""
    if not body:
        body = _fallback_final(meta, obs, p2, p3)
    prog["roles"]["final"].update(status="완료" if body and "실패" not in str(ef or "")
                                  else "실패", took_s=tkf,
                                  error=ef if "실패" in str(ef or "") else None)
    # 최종도 단계 기록에 남긴다 — UI 가 pipeline 순서대로 카드를 그리므로
    # 여기 없으면 빈 카드가 뜬다. 본문은 rec["final"] 에 따로 있다.
    _fin_ok = bool(body) and "실패" not in str(ef or "")
    stages_out["final"] = {
        "ok": _fin_ok, "name": STAGES["final"]["name"], "icon": STAGES["final"]["icon"],
        "model": mf or _stage_model(cfg, "final"), "took_s": tkf,
        "result": {"통합리포트": "아래 본문 참조", "글자수": len(body)},
        "error": None if _fin_ok else (ef or None),
        "note": ef if (_fin_ok and ef) else None,
    }

    rec = {
        "id": f"A{day}_{datetime.now():%H%M%S}",
        "day": day, "span": span, "minutes": meta["minutes"],
        "peak": meta["peak"], "incidents": meta["incidents"], "floor": meta["floor"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "took_s": round(time.time() - t0, 1),
        "pipeline": ["p1", "p2", "p3", "final"],
        "graph": _graph_svg(seq, cfg),          # 리포트 위에 붙일 구간 점수 그래프
        "roles": stages_out, "final": body, "final_error": ef or None,
    }
    path = os.path.join(_store_dir(cfg), rec["id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    rec["path"] = path
    prog.update(stage="done", done=True, id=rec["id"])
    return {"ok": True, **rec}


def list_analyses(cfg: dict | None = None, limit: int = 30) -> list[dict]:
    cfg = cfg or load_config()
    d = _store_dir(cfg)
    out = []
    for fn in sorted(os.listdir(d), reverse=True)[:limit]:
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                r = json.load(f)
            roles = r.get("roles") or {}
            ok_n = sum(1 for v in roles.values() if v.get("ok"))
            out.append({"id": r.get("id"), "day": r.get("day"), "span": r.get("span"),
                        "minutes": r.get("minutes"), "peak": r.get("peak"),
                        "generated_at": r.get("generated_at"),
                        "took_s": r.get("took_s"),
                        "roles_ok": ok_n, "roles_n": len(roles) or 4})
        except (json.JSONDecodeError, OSError):
            continue
    return out


def get_analysis(aid: str, cfg: dict | None = None) -> dict | None:
    cfg = cfg or load_config()
    if not re.fullmatch(r"A\d{8}_\d{6}", str(aid or "")):
        return None
    p = os.path.join(_store_dir(cfg), aid + ".json")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    cfg = load_config()
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    start = sys.argv[2] if len(sys.argv) > 2 else ""
    end = sys.argv[3] if len(sys.argv) > 3 else ""
    r = run_analysis(day, cfg, start, end)
    print(json.dumps({k: v for k, v in r.items() if k != "roles"},
                     ensure_ascii=False, indent=2)[:2000])
