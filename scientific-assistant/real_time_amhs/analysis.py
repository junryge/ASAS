"""
real_time_amhs/analysis.py — 4-LLM 병렬 분석 (데이터 분석 오피스)

구조
    저장된 CSV(하루 전체 또는 시간 구간)를 요약(다이제스트)한 뒤,
    역할이 다른 LLM 4개가 **같은 데이터를 병렬로** 분석하고,
    다섯 번째 호출이 4개 결과를 하나의 통합 리포트로 종합한다.

        ① 위험도 종합  — 전체 위험 수준·추세·최고점
        ② 구역 진단    — 핫구역과 구역별 상태
        ③ 전파 경로    — 정체가 어느 구역에서 어느 구역으로 번졌나
        ④ 조치 요약    — 지금 할 일 / 모니터링 / 에스컬레이션
        ⑤ 통합 리포트  — ①~④를 합친 최종 판정 (markdown)

    모델은 config.llm.analysis.roles 에서 역할별로 바꿀 수 있다 (기본: GAIA).
    한 역할이 실패해도 나머지는 계속 간다 — 실패는 결과에 그대로 표시한다.

데이터 다이제스트
    LLM 에 CSV 원문을 다 줄 수는 없다 (하루 1,440분 × 수십 컬럼).
    - 하루 전체  → 시간대(1h)별 통계 + 사건 구간 + 지표 요약
    - 시간 구간  → 분단위 그대로 (구간이 길면 자동 표본화)
    어느 쪽이든 프롬프트는 상한(digest_max_chars) 안으로 준다.

결과 저장
    data/analysis/A{day}_{HHMMSS}.json — UI 는 목록/조회만 한다.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime

from lp_client import load_config
from sentinel import _row_dt, _score, alarm_floor, grade

_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 역할 정의 — 프롬프트와 응답 JSON 골격 ──────────────────────────────
ROLES = [
    {
        "id": "risk", "name": "위험도 종합", "icon": "📊",
        "goal": "구간 전체의 위험 수준을 판정한다",
        "ask": (
            "다음 JSON 만 출력하라 (설명 금지):\n"
            '{"등급": "정상|경계|위험|초위험", "최고점수": 숫자, "최고시각": "HH:MM", '
            '"추세": "상승|하락|유지|반복", "정체분": 숫자, '
            '"요약": "3~4문장 — 구간 전체 위험 수준과 그렇게 판단한 근거", '
            '"근거": ["근거1", "근거2", "근거3"]}'
        ),
        "prefill": '{"등급": "',
    },
    {
        "id": "zone", "name": "구역 진단", "icon": "📍",
        "goal": "어느 구역이 문제인지 지목한다",
        "ask": (
            "다음 JSON 만 출력하라 (설명 금지):\n"
            '{"핫구역": ["가장 문제인 영역"], '
            '"구역진단": [{"구역": "영역명", "상태": "한 줄 상태", "근거": "수치 근거"}], '
            '"영향구역": ["함께 영향받은 영역"], '
            '"요약": "2~3문장 — 어디가 왜 문제인가"}'
        ),
        "prefill": '{"핫구역": ["',
    },
    {
        "id": "path", "name": "전파 경로", "icon": "🔀",
        "goal": "정체가 시간 순서로 어떻게 번졌는지 재구성한다",
        "ask": (
            "다음 JSON 만 출력하라 (설명 금지):\n"
            '{"전파경로": "A영역 HH:MM → B영역 HH:MM 형식 (전파 없으면 \\"단일 구역\\")", '
            '"선행신호": "가장 먼저 움직인 지표와 시각", '
            '"시간정합": "전파 순서가 데이터와 맞는지 한 줄", '
            '"요약": "2~3문장 — 전파 양상"}'
        ),
        "prefill": '{"전파경로": "',
    },
    {
        "id": "action", "name": "조치 요약", "icon": "🛠️",
        "goal": "관제가 지금 해야 할 일을 정한다",
        "ask": (
            "다음 JSON 만 출력하라 (설명 금지):\n"
            '{"즉시조치": ["지금 할 일 1~3개"], '
            '"모니터링": ["지켜볼 것 1~3개"], '
            '"에스컬레이션": "필요 없으면 \\"불필요\\", 필요하면 누구에게 무엇을", '
            '"요약": "2문장 — 조치 우선순위"}'
        ),
        "prefill": '{"즉시조치": ["',
    },
]

DEFAULTS = {
    "digest_max_chars": 7000,
    "role_max_tokens": 900,
    "final_max_tokens": 2200,
    "timeout_s": 120,
}


def _acfg(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg.get("llm", {}) or {}).get("analysis") or {})
    return c


def _role_model(cfg: dict, role_id: str) -> str:
    """역할별 모델 — config.llm.analysis.roles.{id}.model → 없으면 기본 모델."""
    a = (cfg.get("llm", {}) or {}).get("analysis") or {}
    r = (a.get("roles") or {}).get(role_id) or {}
    return r.get("model") or cfg.get("llm", {}).get("model", "gaia-Qwen3.5-397B-A17B")


# ────────────────────────── 데이터 다이제스트 ──────────────────────────
def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _metrics(cfg: dict) -> list[dict]:
    """요약에 쓸 지표 — 화면 추이 그래프와 같은 목록 (AMOS 묶음 우선)."""
    ui = cfg.get("ui") or {}
    for g in (ui.get("metric_groups") or []):
        ms = [m for m in (g.get("metrics") or [])
              if isinstance(m, dict) and m.get("key") and m["key"] != "unified_risk_score"]
        if ms:
            return ms[:8]
    return [m for m in (ui.get("strip_metrics") or [])
            if isinstance(m, dict) and m.get("key") != "unified_risk_score"][:8]


def _window_rows(day: str, cfg: dict, start: str = "", end: str = "") -> list[dict]:
    """그 날짜 CSV 에서 [start, end] (HH:MM) 구간만. 비우면 하루 전체."""
    from store_csv import read_day
    rows = read_day(day, cfg) or []
    if not (start or end):
        return rows
    out = []
    for r in rows:
        d = _row_dt(r)
        if d is None:
            continue
        hm = d.strftime("%H:%M")
        if start and hm < start:
            continue
        if end and hm > end:
            continue
        out.append(r)
    return out


def build_digest(day: str, cfg: dict, start: str = "", end: str = "") -> dict:
    """LLM 4개가 공유할 데이터 요약. 하루 전체면 시간대 집계, 구간이면 분단위."""
    rows = _window_rows(day, cfg, start, end)
    floor = alarm_floor(cfg)
    mets = _metrics(cfg)

    seq = []
    for r in rows:
        d = _row_dt(r)
        if d is None:
            continue
        seq.append((d, _score(r), r))
    seq.sort(key=lambda x: x[0])
    if not seq:
        return {"ok": False, "error": f"{day} {start or '00:00'}~{end or '24:00'} 데이터 없음"}

    scores = [s for _, s, _ in seq]
    peak_i = max(range(len(seq)), key=lambda i: seq[i][1])
    peak_d, peak_s, peak_r = seq[peak_i]
    g = grade(peak_s, cfg)

    # 사건 구간 (스킬 규칙과 동일: 점수 50+ 런, 간격 60분) — daily._minutes 로 정규화
    from daily import _minutes as day_minutes, incidents as day_incidents, incident_rows
    raw = [{**r, "datetime": d.strftime("%Y-%m-%d %H:%M")} for d, s, r in seq]
    incs = incident_rows(day_incidents(day_minutes(raw, cfg)))

    # 시간대(1h) 집계 — 하루 전체 모드
    hourly = {}
    for d, s, r in seq:
        h = d.strftime("%H시")
        cur = hourly.setdefault(h, {"n": 0, "max": 0.0, "sum": 0.0, "over": 0,
                                    "area": {}})
        cur["n"] += 1
        cur["sum"] += s
        cur["max"] = max(cur["max"], s)
        cur["over"] += 1 if s >= floor else 0
        a = (r.get("hot_area") or "").strip()
        if a and s >= floor:
            cur["area"][a] = cur["area"].get(a, 0) + 1

    L = [f"# 분석 대상: {day[:4]}-{day[4:6]}-{day[6:8]} "
         f"{start or '00:00'} ~ {end or '24:00'} ({len(seq)}분)",
         f"- 알람 임계 {floor}점 · 최고 {g['emoji']} {g['level']} {peak_s:.0f}점 "
         f"({peak_d:%H:%M}, {peak_r.get('hot_area') or '-'}) · 평균 {sum(scores)/len(scores):.0f}점 "
         f"· 임계 이상 {sum(1 for s in scores if s >= floor)}분", ""]

    L.append("## 시간대별 (시각 | 분수 | 최고 | 평균 | 임계이상분 | 주요구역)")
    for h in sorted(hourly):
        c = hourly[h]
        areas = ", ".join(sorted(c["area"], key=lambda k: -c["area"][k])[:2]) or "-"
        L.append(f"{h} | {c['n']} | {c['max']:.0f} | {c['sum']/c['n']:.0f} | {c['over']} | {areas}")

    L.append("\n## 사건 구간 (임계 이상 연속 구간)")
    if incs:
        for i in incs:
            L.append(f"- #{i['번호']} {i['구간']} ({i['지속분']}분) 최고 {i['최고점수']}점 "
                     f"{i['최고등급']} · 시작영역 {i['시작영역']} · 사유 {str(i.get('발동사유') or '')[:160]}")
    else:
        L.append("- 없음 (임계를 넘은 구간 없음)")

    L.append("\n## 지표 요약 (지표 | 최소 | 최대 | 평균 | 마지막 | 최고점시각값)")
    for m in mets:
        vals = [(_num(r.get(m["key"])), d) for d, _, r in seq]
        vals = [(v, d) for v, d in vals if v is not None]
        if not vals:
            continue
        vs = [v for v, _ in vals]
        at_peak = next((v for v, d in vals if d == peak_d), None)
        L.append(f"{m.get('label') or m['key']}({m.get('unit','')}) | "
                 f"{min(vs):.1f} | {max(vs):.1f} | {sum(vs)/len(vs):.1f} | {vs[-1]:.1f} | "
                 f"{at_peak if at_peak is not None else '-'}")

    # 분단위 상세 — 구간 모드거나 사건이 있으면 최고점 주변을 준다
    detail_rows = seq
    if len(detail_rows) > 120:          # 표본화: 사건 주변 우선
        picked = [x for x in seq if abs((x[0] - peak_d).total_seconds()) <= 3600]
        step = max(1, len(picked) // 90)
        detail_rows = picked[::step] if picked else seq[:: max(1, len(seq) // 90)]
    L.append("\n## 분단위 (시각 | 점수 | 구역 | 발동사유 요약)")
    from sentinel import summarize_reason
    for d, s, r in detail_rows[:120]:
        why = summarize_reason(str(r.get("reason") or ""), r.get("hot_area") or "") \
            if s >= floor else ""
        L.append(f"{d:%H:%M} | {s:.0f} | {r.get('hot_area') or '-'}"
                 + (f" | {why}" if why else ""))

    txt = "\n".join(L)
    cap = int(_acfg(cfg)["digest_max_chars"])
    if len(txt) > cap:
        txt = txt[:cap] + "\n(…이하 생략)"
    return {"ok": True, "digest": txt, "minutes": len(seq),
            "peak": {"score": round(peak_s, 1), "time": f"{peak_d:%H:%M}",
                     "level": g["level"], "emoji": g["emoji"],
                     "area": peak_r.get("hot_area") or "-"},
            "incidents": len(incs), "floor": floor,
            "span": f"{start or '00:00'}~{end or '24:00'}"}


# ────────────────────────── 역할 실행 ──────────────────────────
def _role_cfg(cfg: dict, role_id: str) -> dict:
    """chat() 에 넘길 cfg — 역할별 모델만 갈아끼운 얕은 복사."""
    c = dict(cfg)
    lc = dict(cfg.get("llm", {}))
    lc["model"] = _role_model(cfg, role_id)
    c["llm"] = lc
    return c


def _run_role(role: dict, digest: str, cfg: dict, out: dict) -> None:
    """역할 1개 실행 — 스레드에서 돈다. 결과/오류를 out[role_id] 에 넣는다."""
    from llm_client import build_system_prompt, chat, scrub, _json_candidates
    t0 = time.time()
    rid = role["id"]
    model = _role_model(cfg, rid)
    a = _acfg(cfg)
    user = (f"[역할] 너는 '{role['name']}' 담당 분석가다. 목표: {role['goal']}.\n"
            f"아래 반송 데이터 요약만 근거로 분석하라. 데이터에 없는 것을 지어내지 마라.\n\n"
            f"{digest}\n\n"
            f"★한국어로만. 추론 과정 금지.\n{role['ask']}")
    try:
        txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                         {"role": "user", "content": user}],
                        _role_cfg(cfg, rid),
                        max_tokens=int(a["role_max_tokens"]),
                        prefill=role["prefill"])
        parsed = None
        if txt:
            for cand in reversed(_json_candidates(scrub(txt))):
                try:
                    parsed = json.loads(cand)
                    break
                except json.JSONDecodeError:
                    continue
        if err:
            out[rid] = {"ok": False, "error": err}
        elif parsed is None:
            out[rid] = {"ok": False, "error": "JSON 파싱 실패",
                        "raw": scrub(txt)[:600]}
        else:
            out[rid] = {"ok": True, "result": parsed}
    except Exception as e:
        out[rid] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    out[rid].update(model=model, took_s=round(time.time() - t0, 1),
                    name=role["name"], icon=role["icon"])


def _final_report(digest_meta: dict, roles_out: dict, cfg: dict) -> tuple[str, str]:
    """⑤ 통합 리포트 — 4개 결과를 markdown 으로 종합. (본문, 오류)"""
    from llm_client import build_system_prompt, chat, scrub
    a = _acfg(cfg)
    ok_parts = []
    for r in ROLES:
        o = roles_out.get(r["id"]) or {}
        if o.get("ok"):
            ok_parts.append(f"### {r['name']}\n{json.dumps(o['result'], ensure_ascii=False)}")
        else:
            ok_parts.append(f"### {r['name']}\n(분석 실패: {o.get('error','?')})")
    pk = digest_meta.get("peak") or {}
    user = (f"4개 분석 결과를 하나의 관제 통합 리포트로 종합하라.\n"
            f"대상 구간: {digest_meta.get('span')} · {digest_meta.get('minutes')}분 · "
            f"최고 {pk.get('emoji','')} {pk.get('level','')} {pk.get('score','')}점 ({pk.get('time','')})\n\n"
            + "\n\n".join(ok_parts) +
            "\n\n형식 (markdown, 한국어만, 추론 과정 금지):\n"
            "## 종합 판정\n(등급·핵심 결론 2~3문장)\n"
            "## 구역 상황\n(핫구역과 전파 양상)\n"
            "## 조치\n(우선순위대로 불릿)\n"
            "## 주의\n(다음 구간에서 지켜볼 것)\n"
            "'## 종합 판정' 부터 바로 시작하라.")
    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}],
                    _role_cfg(cfg, "final"),
                    max_tokens=int(a["final_max_tokens"]),
                    prefill="## 종합 판정\n")
    if err:
        return "", err
    return scrub(txt), ""


def _fallback_report(digest_meta: dict, roles_out: dict) -> str:
    """⑤가 실패해도 4개 결과(성공분)로 골격은 채운다."""
    pk = digest_meta.get("peak") or {}
    L = ["## 종합 판정",
         f"최고 {pk.get('emoji','')} {pk.get('level','')} {pk.get('score','')}점 "
         f"({pk.get('time','')}, {pk.get('area','')}) · 사건 {digest_meta.get('incidents',0)}건 "
         f"— (통합 LLM 미연결, 역할 결과 나열)"]
    for r in ROLES:
        o = roles_out.get(r["id"]) or {}
        L.append(f"\n## {r['name']}")
        if o.get("ok"):
            res = o["result"]
            smy = res.get("요약") if isinstance(res, dict) else None
            L.append(smy or json.dumps(res, ensure_ascii=False)[:500])
        else:
            L.append(f"(실패: {o.get('error','?')})")
    return "\n".join(L)


# ────────────────────────── 실행·저장 ──────────────────────────
def _store_dir(cfg: dict) -> str:
    d = (cfg.get("storage", {}) or {}).get("dir", "data")
    if not os.path.isabs(d):
        d = os.path.join(_DIR, d)
    d = os.path.join(d, "analysis")
    os.makedirs(d, exist_ok=True)
    return d


def run_analysis(day: str, cfg: dict | None = None, start: str = "",
                 end: str = "", progress: dict | None = None) -> dict:
    """4-LLM 병렬 분석 1회 — 완료까지 블로킹 (서버는 스레드에서 부른다).

    progress 를 주면 진행 상황을 그 dict 에 계속 반영한다 (UI 폴링용).
    """
    cfg = cfg or load_config()
    day = "".join(ch for ch in str(day) if ch.isdigit())[:8]
    t0 = time.time()
    prog = progress if progress is not None else {}
    prog.update(stage="digest", roles={}, done=False, error=None)

    dg = build_digest(day, cfg, start, end)
    if not dg.get("ok"):
        prog.update(done=True, error=dg.get("error"))
        return {"ok": False, "error": dg.get("error")}

    prog.update(stage="roles",
                roles={r["id"]: {"name": r["name"], "icon": r["icon"],
                                 "model": _role_model(cfg, r["id"]),
                                 "status": "분석중"} for r in ROLES})

    out: dict = {}
    threads = []
    for r in ROLES:
        th = threading.Thread(target=_run_role, args=(r, dg["digest"], cfg, out),
                              daemon=True)
        th.start()
        threads.append(th)
    timeout = float(_acfg(cfg)["timeout_s"])
    deadline = time.time() + timeout
    for th in threads:
        th.join(max(1.0, deadline - time.time()))
    for r in ROLES:
        o = out.get(r["id"])
        if o is None:
            out[r["id"]] = {"ok": False, "error": f"시간 초과({timeout:.0f}초)",
                            "model": _role_model(cfg, r["id"]),
                            "name": r["name"], "icon": r["icon"], "took_s": timeout}
        pr = prog["roles"].get(r["id"], {})
        pr.update(status="완료" if out[r["id"]].get("ok") else "실패",
                  took_s=out[r["id"]].get("took_s"),
                  error=out[r["id"]].get("error"))

    prog.update(stage="final")
    body, ferr = _final_report(dg, out, cfg)
    if not body:
        body = _fallback_report(dg, out)

    rec = {
        "id": f"A{day}_{datetime.now():%H%M%S}",
        "day": day, "span": dg["span"], "minutes": dg["minutes"],
        "peak": dg["peak"], "incidents": dg["incidents"], "floor": dg["floor"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "took_s": round(time.time() - t0, 1),
        "roles": out, "final": body, "final_error": ferr or None,
        "digest_chars": len(dg["digest"]),
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
            ok_n = sum(1 for v in (r.get("roles") or {}).values() if v.get("ok"))
            out.append({"id": r.get("id"), "day": r.get("day"), "span": r.get("span"),
                        "minutes": r.get("minutes"), "peak": r.get("peak"),
                        "generated_at": r.get("generated_at"),
                        "took_s": r.get("took_s"), "roles_ok": ok_n})
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
