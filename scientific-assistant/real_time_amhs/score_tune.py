#!/usr/bin/env python3
"""
스코어 등급 컷 자동 조정 — 최근 8시간 분포를 LLM 이 보고 유지/변경을 정한다.

왜 8시간인가
    교대 근무 한 텀이다 (07~15 · 15~23 · 23~07). 한 조가 실제로 겪은 구간을
    통째로 보고 판단해야, "우리 조에는 알람이 하루 종일 떴다/한 번도 안 떴다"
    는 이야기가 숫자로 잡힌다.

왜 2시간마다인가
    OHT·물류가 한 사이클 도는 데 대략 120분이다. 그보다 자주 물으면 같은
    사이클 안을 두 번 보는 것이라 새로 알 게 없고, 훨씬 뜸하면 분포가
    내려앉은 걸 한참 뒤에 안다.

무엇을 하지 않는가
    · 배점표(fab_score.WATCH)는 안 건드린다. 그건 현장 예측기가 정한 것이다.
      여기서 옮기는 것은 **등급 경계**뿐이다.
    · 한 번에 크게 안 옮긴다 (max_step). 2시간마다 도는 것이라, 정말 크게
      옮겨야 하면 몇 번에 걸쳐 걸어간다 — 한 번의 헛발질로 안 망가진다.
    · 표본이 모자라면 아무것도 안 한다.

★LLM 이 지금 값을 제대로 읽었는지 대조한다
    제안과 함께 **지금 컷을 그대로 되읽어** 적게 하고, 서버가 실제 값과
    맞춰 본다. 틀리면 그 시스템은 건너뛴다. 지금 값을 잘못 본 모델이 낸
    '변경' 은 근거가 없다.

기록
    돌 때마다 data/score_tune.jsonl 에 **전·후·이유·그때 분포**를 남긴다.
    유지도 남긴다 — "왜 안 바꿨나" 도 답할 수 있어야 한다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from lp_client import load_config, sys_cfg   # noqa: F401  (load_config 은 외부에서 씀)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    # ★기본은 꺼 둔다. 등급 컷은 알람이 뜨고 안 뜨고를 가르는 값이라,
    #   자동으로 도는 것을 켜는 판단은 사람이 한다.
    #   꺼져 있어도 화면 버튼으로 언제든 돌릴 수 있다.
    "enabled": False,
    "hours": 8,                  # 볼 구간 — 교대 한 텀
    # 2시간마다. 07 시(교대 시작)에 맞춰 짝을 맞춘다.
    "at": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23],
    "max_step": 10,              # 한 번에 옮길 수 있는 최대 점수 (컷마다)
    "min_rows": 60,              # 이만큼 안 되면 안 바꾼다 (1분 1행 = 1시간)
    # ★정책 확인 전용 모델. 관제 대화용 모델과 따로 두는 이유는, 여기서
    #   필요한 건 말솜씨가 아니라 **분포를 보고 숫자를 고르는 일관성**이라서다.
    #   이 모델이 죽거나 게이트웨이에 없으면 **다른 모델로 갈아타지 않는다** —
    #   현재 컷을 그대로 유지하고 왜 못 했는지만 기록한다. 등급 컷은 알람이
    #   뜨고 안 뜨고를 가르는 값이라, 아무 모델이나 대신 정하게 두면 안 된다.
    "model": "gaia-Qwen3.6-35B-A3B",
    # ★프롬프트를 설정으로 뺀다. 화면에서 보고 고칠 수 있어야 한다 —
    #   무엇을 물어보고 있는지 모르면 답을 믿을 수도, 못 믿을 수도 없다.
    #   비워 두면 아래 SYSTEM(기본 프롬프트)을 쓴다.
    "prompt": "",
    # ★이유가 없으면 안 바꾼다. 근거를 못 대는 변경은 나중에 되짚을 수가 없다 —
    #   "왜 컷이 이래?" 에 "LLM 이 그랬다" 는 답이 되지 않는다.
    "need_why": True,            # why 가 비면 그 시스템은 유지
    "why_min": 8,                # why 최소 길이 (한두 글자는 이유가 아니다)
    "need_number": True,         # why 에 숫자 근거가 있어야 한다
    "store": "data/score_tune.jsonl",
}

SHIFTS = ((7, 15), (15, 23), (23, 7))     # 교대 — 화면에 그대로 보여 준다


def cfg_of(cfg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((cfg.get("policy", {}) or {}).get("auto_tune") or {})
    try:
        c["at"] = sorted({int(h) % 24 for h in (c.get("at") or [])})
    except (TypeError, ValueError):
        c["at"] = list(DEFAULTS["at"])
    return c


def shift_of(t: datetime) -> str:
    """그 시각이 어느 교대인가 — 기록에 남겨 조별로 훑어볼 수 있게."""
    h = t.hour
    if 7 <= h < 15:
        return "주간(07~15)"
    if 15 <= h < 23:
        return "저녁(15~23)"
    return "야간(23~07)"


def _num(v):
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return None if f != f else f          # NaN 은 없는 값으로


def _pct(vals: list[float], p: float) -> float:
    """백분위 — 선형 보간. 표본이 적어도 안 터진다."""
    if not vals:
        return 0.0
    if len(vals) == 1:
        return round(vals[0], 1)
    k = (len(vals) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 1)


def window_rows(hours: int, cfg: dict, now: datetime | None = None) -> list[dict]:
    """최근 N시간 행.

    ★자정을 넘으면 어제 파일도 읽어야 한다 — 01시 실행이면 구간이 전날
      17시부터다. 하루 파일만 읽던 때 야간 조는 늘 '표본 부족' 이었다.
    """
    from sentinel import _row_dt
    from store_csv import read_day
    now = now or datetime.now()
    start = now - timedelta(hours=max(1, int(hours)))
    days = {start.strftime("%Y%m%d"), now.strftime("%Y%m%d")}
    out = []
    for d in sorted(days):
        for r in read_day(d, cfg) or []:
            t = _row_dt(r)
            if t is not None and start <= t <= now:
                out.append(r)
    return out


def stats(rows: list[dict], cuts: tuple[int, int, int]) -> dict:
    """그 시스템의 점수 분포 + 지금 컷으로는 얼마나 울리는가.

    ★비율이 핵심이다. '최고 몇 점' 만 보면 하루에 한 번 튄 값으로 컷을
      정하게 된다. 사람이 궁금한 것은 '몇 분이나 알람이 떠 있었나' 다.
    """
    vals = sorted(v for v in (_num(r.get("unified_risk_score")) for r in rows)
                  if v is not None)
    n = len(vals)
    if not n:
        return {"n": 0}
    w, d, c = cuts

    def over(t):
        return sum(1 for v in vals if v >= t)

    return {
        "n": n,
        "min": round(vals[0], 1), "max": round(vals[-1], 1),
        "avg": round(sum(vals) / n, 1),
        "p50": _pct(vals, 50), "p75": _pct(vals, 75), "p90": _pct(vals, 90),
        "p95": _pct(vals, 95), "p99": _pct(vals, 99),
        # 지금 컷 기준 — 몇 분(%)이 각 등급이었나
        "pct_warn": round(100.0 * over(w) / n, 1),
        "pct_danger": round(100.0 * over(d) / n, 1),
        "pct_crit": round(100.0 * over(c) / n, 1),
        "min_warn": over(w), "min_danger": over(d), "min_crit": over(c),
    }


def snapshot(cfg: dict, hours: int, systems: list[str],
             now: datetime | None = None) -> dict:
    """시스템별 {현재 컷, 최근 분포}."""
    from sentinel import grade_cuts
    out = {}
    for s in systems:
        c = sys_cfg(cfg, s)
        cuts = grade_cuts(c)
        out[s] = {"cuts": {"warn": cuts[0], "danger": cuts[1],
                           "critical": cuts[2]},
                  "stats": stats(window_rows(hours, c, now), cuts)}
    return out


# ────────────────────────────── LLM ──────────────────────────────
SYSTEM = (
    "너는 반도체 물류(AMHS) 관제의 **등급 경계**를 정하는 담당이다.\n"
    "받은 것은 시스템별 최근 8시간(교대 한 텀) 위험 점수 분포와, 지금 쓰는 컷이다.\n"
    "\n"
    "물어보는 것은 하나다 — **지금 컷이 이 분포에 맞나?**\n"
    "  맞으면  verdict 를 \"유지\" 로 하고 지금 값을 그대로 적는다.\n"
    "  안 맞으면 verdict 를 \"변경\" 으로 하고 새 값을 적는다.\n"
    "\n"
    "판단 기준\n"
    "· 경계(warn) 는 **알람이 시작되는 점수**다. 이 위로 올라간 시간이 너무\n"
    "  길면 사람이 알람을 안 본다. 너무 짧으면 놓친다.\n"
    "· 대체로 최근 구간의 상위 10~20% 가 경계 이상, 상위 3~7% 가 위험 이상,\n"
    "  상위 1~2% 가 초위험이 되는 자리가 좋다.\n"
    "· 다만 **분포가 평평하면(p90 과 p99 가 거의 같으면) 옮기지 마라** —\n"
    "  그런 구간은 조용한 것이지 컷이 틀린 게 아니다.\n"
    "· **바꾸는 것이 일이 아니다.** 지금 컷이 이미 그 자리면 \"유지\" 가 정답이다.\n"
    "· 표본(n)이 적은 시스템은 손대지 마라 — \"유지\" 로 답한다.\n"
    "\n"
    "반드시 지킬 것\n"
    "· now 에 **지금 쓰는 컷을 그대로 옮겨 적어라.** 서버가 실제 값과 대조한다.\n"
    "  여기가 틀리면 그 시스템 제안은 버려진다.\n"
    "· 1 ≤ warn < danger < critical ≤ 100 (정수)\n"
    "· why 는 **한 줄 한국어**. 숫자를 근거로 들어라 (예: \"p90 이 41 인데 경계가\n"
    "  35 라 8시간 중 27% 가 알람이었다\").\n"
    "· ★\"유지\" 일 때도 why 를 반드시 적어라. 사람은 안 바꾼 이유도 알아야 한다 —\n"
    "  \"경계이상 14% 로 적정 범위(10~20%) 안이다\" 처럼.\n"
    "· JSON 만 출력한다. 설명·코드펜스 금지.\n"
    "\n"
    "형태:\n"
    '{"by_sys": {"ALL": {"now": {"warn": 35, "danger": 50, "critical": 70},\n'
    '                    "verdict": "변경",\n'
    '                    "warn": 41, "danger": 55, "critical": 72,\n'
    '                    "why": "..."}},\n'
    ' "note": "전체 한 줄 요약"}'
)


def system_prompt(cfg: dict) -> str:
    """실제로 보내는 지시문. 설정에 적어 두면 그것을, 없으면 기본값을."""
    return (cfg_of(cfg).get("prompt") or "").strip() or SYSTEM


def preview(cfg: dict, systems: list[str], hours: int | None = None,
            now: datetime | None = None) -> dict:
    """지금 누르면 **무엇이 모델에게 가는가** — 화면에 그대로 보여 준다.

    ★사람이 프롬프트를 고치려면 두 가지를 봐야 한다: 지시문과, 거기 붙는
      실제 데이터. 지시문만 보여 주면 "왜 이렇게 판단했지" 를 못 짚는다.
    """
    tc = cfg_of(cfg)
    hours = int(hours or tc["hours"])
    now = now or datetime.now()
    snap_ = snapshot(cfg, hours, systems, now)
    msgs = build_messages(snap_, hours, now, cfg)
    return {"model": tc.get("model") or "", "hours": hours,
            "shift": shift_of(now),
            "system": msgs[0]["content"], "user": msgs[1]["content"],
            "custom": bool((tc.get("prompt") or "").strip()),
            "chars": sum(len(m["content"]) for m in msgs)}


def build_messages(snap: dict, hours: int,
                   now: datetime | None = None,
                   cfg: dict | None = None) -> list[dict]:
    now = now or datetime.now()
    lines = [f"기준 시각 {now.strftime('%Y-%m-%d %H:%M')} · {shift_of(now)}",
             f"최근 {hours}시간 구간이다. 각 시스템의 지금 컷과 점수 분포다.", ""]
    for s, d in snap.items():
        st, c = d["stats"], d["cuts"]
        if not st.get("n"):
            lines.append(f"[{s}] 데이터 없음 — 지금 컷 "
                         f"{c['warn']}/{c['danger']}/{c['critical']} · 유지할 것")
            lines.append("")
            continue
        lines.append(
            "[{s}] 지금 컷  경계 {w} · 위험 {d} · 초위험 {c}\n"
            "  표본 {n}분 · 평균 {avg} · 최소 {mn} · 최고 {mx}\n"
            "  분포  p50 {p50} · p75 {p75} · p90 {p90} · p95 {p95} · p99 {p99}\n"
            "  지금 컷으로는  경계이상 {pw}% ({mw}분) · 위험이상 {pd}% ({md}분)"
            " · 초위험 {pc}% ({mc}분)".format(
                # ★.get 으로 읽는다 — 옛 기록에서 다시 그릴 때처럼 칸이
                #   덜 찬 snapshot 이 들어와도 프롬프트 만들다 죽지 않게.
                s=s, w=c["warn"], d=c["danger"], c=c["critical"],
                n=st.get("n", 0), avg=st.get("avg", "?"),
                mn=st.get("min", "?"), mx=st.get("max", "?"),
                p50=st.get("p50", "?"), p75=st.get("p75", "?"),
                p90=st.get("p90", "?"), p95=st.get("p95", "?"),
                p99=st.get("p99", "?"),
                pw=st.get("pct_warn", "?"), mw=st.get("min_warn", "?"),
                pd=st.get("pct_danger", "?"), md=st.get("min_danger", "?"),
                pc=st.get("pct_crit", "?"), mc=st.get("min_crit", "?")))
        lines.append("")
    return [{"role": "system", "content": system_prompt(cfg or {})},
            {"role": "user", "content": "\n".join(lines)}]


def parse(txt: str) -> dict | None:
    """LLM 이 준 글에서 JSON 만. 코드펜스·앞뒤 군말을 걷어낸다."""
    s = (txt or "").strip()
    if "```" in s:
        s = max(s.split("```"), key=len)
        if s.lstrip()[:4].lower() == "json":
            s = s.lstrip()[4:]
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(s[i:j + 1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def why_ok(why: str, tc: dict | None = None) -> bool:
    """이유라고 부를 만한가 — 길이가 있고 숫자 근거가 있어야 한다."""
    tc = tc or DEFAULTS
    why = (why or "").strip()
    if len(why) < int(tc.get("why_min", 8)):
        return False
    if tc.get("need_number", True) and not any(c.isdigit() for c in why):
        return False
    return True


def decide(want: dict, snap: dict, tc: dict) -> tuple[dict, list[dict]]:
    """LLM 제안 → 실제로 적용할 값 + 시스템별 판정 줄.

    돌려주는 것
        applied  {SYS: {warn, danger, critical, why}}  — 실제로 바꿀 것만
        rows     [{sys, verdict, from, to, why, note}] — 화면·기록용 전부
    """
    step = max(1, int(tc.get("max_step", 10)))
    min_rows = int(tc.get("min_rows", 60))
    applied, rows = {}, []

    for s, cur in snap.items():
        c = cur["cuts"]
        now3 = (c["warn"], c["danger"], c["critical"])
        st = cur["stats"] or {}
        n = st.get("n", 0)
        row = {"sys": s, "from": list(now3), "to": list(now3),
               "verdict": "유지", "why": "", "note": "", "n": n}
        want_row = (want.get("by_sys") or {}).get(s)

        if n < min_rows:
            row["note"] = f"표본 {n}분 (최소 {min_rows}분) — 안 건드린다"
            rows.append(row)
            continue
        if not isinstance(want_row, dict):
            row["note"] = "LLM 이 이 시스템을 안 봤다 — 그대로 둔다"
            rows.append(row)
            continue

        row["why"] = str(want_row.get("why") or "").strip()[:300]

        # ★① 지금 값을 제대로 읽었나 — 되읽은 값과 실제를 대조한다.
        #    여기가 틀린 모델의 '변경' 은 근거가 없다.
        echo = want_row.get("now")
        if isinstance(echo, dict):
            try:
                got = (int(echo["warn"]), int(echo["danger"]),
                       int(echo["critical"]))
            except (KeyError, TypeError, ValueError):
                got = None
            if got is not None and got != now3:
                row["note"] = ("LLM 이 현재값을 {}/{}/{} 로 잘못 읽었다 "
                               "(실제 {}/{}/{}) — 제안을 버린다"
                               .format(*got, *now3))
                rows.append(row)
                continue
        else:
            row["note"] = "LLM 이 현재값을 안 적었다 — 확인이 안 돼 그대로 둔다"
            rows.append(row)
            continue

        verdict = str(want_row.get("verdict") or "").strip()
        try:
            new3 = [int(want_row["warn"]), int(want_row["danger"]),
                    int(want_row["critical"])]
        except (KeyError, TypeError, ValueError):
            row["note"] = "제안이 숫자가 아니다 — 그대로 둔다"
            rows.append(row)
            continue

        if verdict == "유지" or tuple(new3) == now3:
            # ★맞으면 조용히 넘어가지 않는다 — '맞다' 도 알려야 할 결과다.
            #   사람은 안 바꾼 이유도 알아야 다음에 손댈지 말지 정한다.
            row["note"] = row["note"] or (why_ok(row["why"])
                                          and "지금 컷이 분포에 맞다"
                                          or "지금 컷이 분포에 맞다 (이유 없음)")
            rows.append(row)
            continue

        # ★③ 이유가 없으면 안 바꾼다.
        #    근거를 못 대는 변경은 나중에 되짚을 수가 없다 — 몇 달 뒤
        #    "왜 컷이 이래?" 에 "LLM 이 그랬다" 는 답이 되지 않는다.
        #    프롬프트에서 '숫자를 근거로' 라고 시켰으니, 숫자도 함께 본다.
        if tc.get("need_why", True) and not why_ok(row["why"], tc):
            row["note"] = (("이유를 안 적었다" if len(row["why"]) < 8
                            else "이유에 숫자 근거가 없다 (\"%s\")" % row["why"][:40])
                           + " — 근거 없는 변경은 안 한다")
            rows.append(row)
            continue

        # ★④ 한 걸음 제한 — 2시간마다 도니 크게 옮겨야 하면 걸어서 간다
        clipped = any(abs(new - old) > step for old, new in zip(now3, new3))
        walked = [old + max(-step, min(step, new - old))
                  for old, new in zip(now3, new3)]
        w, d, cr = (max(1, min(100, v)) for v in walked)

        # ★⑤ 순서 — 1 ≤ 경계 < 위험 < 초위험 ≤ 100
        if not (w < d < cr):
            row["note"] = f"순서가 어긋난 제안 ({w}/{d}/{cr}) — 그대로 둔다"
            rows.append(row)
            continue
        if (w, d, cr) == now3:
            row["note"] = "한 걸음 제한을 걸고 나니 지금과 같다"
            rows.append(row)
            continue

        row["verdict"] = "변경"
        row["to"] = [w, d, cr]
        if clipped:
            row["note"] = (f"제안 {new3[0]}/{new3[1]}/{new3[2]} 이 한 걸음"
                           f"({step}점)을 넘어 여기까지만 옮겼다")
        applied[s] = {"warn": w, "danger": d, "critical": cr,
                      "why": row["why"]}
        rows.append(row)

    return applied, rows


# ────────────────────────────── 기록 ──────────────────────────────
def _store_path(cfg: dict, tc: dict | None = None) -> str:
    tc = tc or cfg_of(cfg)
    return os.path.join(BASE_DIR, tc.get("store", DEFAULTS["store"]))


def record(rec: dict, cfg: dict) -> None:
    """★유지도 남긴다 — '왜 안 바꿨나' 도 답할 수 있어야 한다."""
    p = _store_path(cfg)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def history(cfg: dict, limit: int = 30, changed_only: bool = False) -> list[dict]:
    """최근 기록 — 새 것이 위로."""
    p = _store_path(cfg)
    if not os.path.isfile(p):
        return []
    out = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    if changed_only:
        out = [r for r in out
               if any(x.get("verdict") == "변경" for x in (r.get("rows") or []))]
    return out[-limit:][::-1]


def run(cfg: dict, systems: list[str], hours: int | None = None,
        by: str = "수동", now: datetime | None = None) -> dict:
    """한 번 돌린다 → 기록 dict. **적용은 부르는 쪽(server)이 한다.**

    여기서 config 를 직접 안 고치는 이유: 저장 경로(메모리 + config.json)가
    server 에 있고, 화면의 '수동 변경' 과 **같은 길**로 나가야 하기 때문이다.
    두 길이 생기면 한쪽만 고쳐지는 사고가 난다.
    """
    import llm_client
    tc = cfg_of(cfg)
    hours = int(hours or tc["hours"])
    now = now or datetime.now()
    snap = snapshot(cfg, hours, systems, now)
    model = str(tc.get("model") or "").strip()

    rec = {"at": now.isoformat(timespec="seconds"), "by": by, "hours": hours,
           "shift": shift_of(now), "snapshot": snap, "model": model,
           "applied": {}, "rows": [], "note": "", "error": ""}

    if not sum((d["stats"] or {}).get("n", 0) for d in snap.values()):
        rec["error"] = f"최근 {hours}시간 데이터가 없습니다"
        return rec

    # ★이 호출만 정책 확인 모델로 바꾼다. CFG 를 건드리면 안 된다 —
    #   같은 dict 를 관제 전체가 공유해서 관제 대화 모델까지 바뀐다.
    #   llm 블록만 갈아 낀 얕은 사본을 쓴다.
    use = cfg
    if model:
        use = dict(cfg)
        use["llm"] = dict(cfg.get("llm") or {})
        use["llm"]["model"] = model

    txt, err = llm_client.chat_json(build_messages(snap, hours, now, cfg), use,
                                    max_tokens=1500)
    if err:
        # ★모델이 죽었거나 게이트웨이에 없다 → **현재 값 유지.**
        #   다른 모델로 갈아타지 않는다. 등급 컷은 알람이 뜨고 안 뜨고를
        #   가르는 값이라, 대신 정해 줄 모델을 우리가 고르면 안 된다.
        rec["error"] = "모델({}) 호출 실패 — 현재 컷을 그대로 둡니다: {}".format(
            model or "기본", err)
        rec["rows"] = [{"sys": s, "verdict": "유지",
                        "from": [d["cuts"]["warn"], d["cuts"]["danger"],
                                 d["cuts"]["critical"]],
                        "to": [d["cuts"]["warn"], d["cuts"]["danger"],
                               d["cuts"]["critical"]],
                        "why": "", "note": "모델을 못 불러 그대로 둔다",
                        "n": (d["stats"] or {}).get("n", 0)}
                       for s, d in snap.items()]
        return rec
    want = parse(txt)
    if not want:
        # 모델이 살아는 있는데 형식을 못 지켰다 — 이것도 근거가 없는 것이다
        rec["error"] = ("모델({}) 응답에서 JSON 을 못 찾았습니다 — "
                        "현재 컷을 그대로 둡니다".format(model or "기본"))
        rec["raw"] = (txt or "")[:400]
        return rec

    rec["applied"], rec["rows"] = decide(want, snap, tc)
    rec["note"] = str(want.get("note") or "").strip()[:300]
    return rec
