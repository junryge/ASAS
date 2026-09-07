"""real_time_amhs/정합성_문서.py — 고객 제출용 '정합성 검사 서류' 를 만든다

    python 정합성_문서.py                          → docs/정합성_검사_서류.html
    python 정합성_문서.py --from 20260826 --to 20260930
    python 정합성_문서.py --md                     → .md 도 같이

무엇을 답하는 문서인가
    고객이 물은 것은 넷이다.
        ① 룰 개정 이력
        ② 룰 제작에 활용한 데이터 기간
        ③ 평가 데이터 기간
        ④ 성능 (Precision / Recall / F1)
    ①② 는 **룰베이스 예측기**(hubroom_predictor.py) 의 사실이다. 그 파일의
    머리말과 thresholds.json 에 이미 적혀 있다 — 여기서 **직접 읽어** 온다.
    ③④ 는 이 폴더가 직접 답한다 — data/ 의 CSV 에서 계산한다.

    이 폴더는 룰을 만들지 않는다. 받아서 읽고, 재현해 보고, 판단하고,
    사후에 채점한다. 문서에 그 경계를 먼저 밝힌다.

왜 손으로 안 쓰나
    fab_score_doc.py 와 같은 이유다. 손으로 쓴 문서는 임계가 바뀌면 옛날
    값으로 남는다. 여기 숫자는 전부 코드와 데이터에서 뽑는다:
        등급 컷      sentinel.grade_cuts()
        임계·룰      fab_score.WATCH / RULES
        재현 일치     fab_score.compare() 를 기간 전체로
        성능         store_csv 의 {날짜}_LLM.CSV 판정 컬럼
    데이터가 없으면 **없다고 적는다.** 빈 칸을 그럴듯한 숫자로 채우지 않는다.

★이 문서는 '우리가 만든 룰의 성능' 이 아니다
    이 폴더가 채점하는 대상은 **LLM 이 그 분에 내린 판단**이다
    (실제이상 예/아니오). 룰 자체의 성능은 예측 잡 쪽에서 낸다.
    그 둘을 섞어 적으면 나중에 더 크게 틀어진다 — 문서에 그대로 밝힌다.
"""
from __future__ import annotations

import argparse
import html
import os
import subprocess
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE_DIR, "docs")
OUT_HTML = os.path.join(DOC_DIR, "정합성_검사_서류.html")
OUT_MD = os.path.join(DOC_DIR, "정합성_검사_서류.md")

# ─────────────────────────────────────────────────────────────────────
# 룰 원본을 어디서 찾나
#
# ★룰은 이 폴더가 만들지 않는다. hubroom_predictor.py (룰베이스 예측기) 가
#   만들고, 임계는 thresholds.json 이 덮는다. 그래서 **그 두 파일을 직접
#   읽어** 버전·학습 기간·검증 결과를 뽑는다 — 손으로 옮겨 적으면 룰이
#   바뀔 때 문서만 옛날 값으로 남는다 (fab_score_doc.py 와 같은 이유).
# ★못 찾으면 RULE_FALLBACK 을 쓰고, 문서에 '파일을 못 찾아 받아 적은
#   값' 이라고 밝힌다. 어디서 온 숫자인지가 정합성 문서의 절반이다.
# ─────────────────────────────────────────────────────────────────────
RULE_FILES = ["hubroom_predictor.py"]
TH_FILES = ["thresholds.json"]

RULE_DIRS = [
    "rool_skill_test",
    os.path.join("M16_BR_개인지식", "스크립트"),
    os.path.join("WORD_MODEL", "OHS_DATA_MD", "Rulebase_prediction"),
    os.path.join("월드모델", "OHS_DATA_MD", "Rulebase_prediction"),
    ".",
]


def _find(names, dirs=None, ups=4):
    """__file__ 기준으로 위로 올라가며 찾는다. 회사 PC 는 배치가 다르다.
    RULE_SRC 환경변수로 자리를 직접 줄 수도 있다.

    ★dirs 를 기본 인자로 묶어 두면 안 된다 — 기본값은 def 때 한 번만
      잡혀서, 나중에 RULE_DIRS 를 바꿔도 안 따라온다 (시험에서 잡혔다).
    """
    dirs = dirs or RULE_DIRS
    env = (os.environ.get("RULE_SRC") or "").strip()
    if env and os.path.isfile(env):
        return env
    base = BASE_DIR
    for _ in range(ups + 1):
        for d in dirs:
            for n in names:
                p = os.path.join(base, d, n)
                if os.path.isfile(p):
                    return p
        nxt = os.path.dirname(base)
        if nxt == base:
            break
        base = nxt
    return ""


# ★파일을 못 찾았을 때만 쓰는 값. 출처를 문서에 그대로 밝힌다.
RULE_FALLBACK = {
    "version": "M16 HUBROOM 통합 이벤트 예측기 v4.1 (룰베이스 8영역)",
    "train": "2026-03-24 14:39 ~ 2026-04-30 정상분포 (p95/p99) 기반",
    "test": "2026-05-01 ~",
}


def read_rule_source():
    """룰 원본에서 버전·학습 기간·검증 결과를 읽는다."""
    import json
    import re as _re
    out = {"path": _find(RULE_FILES), "th_path": _find(TH_FILES),
           "version": "", "train": "", "test": "", "areas": "",
           "changes": {}, "th_note": "", "th_howto": "", "found": False}
    if out["path"]:
        try:
            with open(out["path"], encoding="utf-8", errors="replace") as f:
                head = f.read(4000)
            out["found"] = True
            m = _re.search(r"^(.*?예측기\s*(v[\d.]+).*)$", head, _re.M)
            if m:
                out["version"] = m.group(1).strip()
            for key, pat in (("areas", r"대상\s*영역\s*:\s*(.+)"),
                             ("train", r"학습\s*임계값\s*:\s*(.+)"),
                             ("test", r"테스트\s*구간\s*:\s*(.+)")):
                m = _re.search(pat, head)
                if m:
                    out[key] = m.group(1).strip()
        except Exception:                               # noqa: BLE001
            pass
    if out["th_path"]:
        try:
            with open(out["th_path"], encoding="utf-8") as f:
                th = json.load(f)
            out["th_note"] = str(th.get("_comment") or "")
            out["th_howto"] = str(th.get("_howto") or "")
            out["changes"] = th.get("_changes") or {}
        except Exception:                               # noqa: BLE001
            pass
    if not out["version"]:
        out["version"] = RULE_FALLBACK["version"]
        out["train"] = out["train"] or RULE_FALLBACK["train"]
        out["test"] = out["test"] or RULE_FALLBACK["test"]
    return out


def e(s) -> str:
    return html.escape("" if s is None else str(s))


def _d8(s) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())[:8]


def _dash(day: str) -> str:
    d = _d8(day)
    return "{}-{}-{}".format(d[:4], d[4:6], d[6:8]) if len(d) == 8 else day


# ────────────────────────────── 개정 이력 ──────────────────────────────
# 룰을 읽고 재현하고 채점하는 자리 — 여기가 바뀌면 판정이 달라질 수 있다.
HIST_PATHS = ["fab_score.py", "sentinel.py", "accuracy.py", "config.json",
              "store_csv.py", "jupyter_csv.py"]


def code_history(limit=40):
    """이 폴더가 언제 무엇을 바꿨나 — git 에서 뽑는다.

    ★왜 git 인가. 개정 이력을 손으로 관리하면 반드시 빠진다. 저장소가
      이미 정확한 이력을 갖고 있으니 그걸 그대로 쓴다.
    ★git 이 없는 PC 에서는 빈 목록이다 — 문서에 '뽑지 못했다' 고 적는다.
    """
    try:
        out = subprocess.run(
            ["git", "log", "--format=%h\x1f%ad\x1f%s", "--date=short",
             "-n", str(limit), "--"] + HIST_PATHS,
            cwd=BASE_DIR, capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return []
        rows = []
        for ln in out.stdout.splitlines():
            p = ln.split("\x1f")
            if len(p) == 3:
                rows.append({"hash": p[0], "date": p[1], "subject": p[2]})
        return rows
    except Exception:                                   # noqa: BLE001
        return []


# ────────────────────────────── 성능 ──────────────────────────────
# accuracy.py 가 쓰는 판정 이름과 **같아야 한다** — 두 벌이 되면 한쪽만
# 고쳐서 숫자가 갈린다.
HIT, FP, FN, EFFECT = "적중", "과다탐지", "누락", "조치효과"
H_TP, H_FP = "정탐", "오탐"


def _prf(tp, fp, fn):
    """Precision / Recall / F1. 분모가 0 이면 None — 0.0 으로 쓰지 않는다.

    ★0.0 과 '잴 수 없음' 은 다르다. 표에 0.0 이 찍히면 고객은 '성능이
      바닥' 으로 읽는다. 표본이 없으면 없다고 적어야 한다.
    """
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f = (2 * p * r / (p + r)) if (p and r) else None
    return p, r, f


def score_days(days, cfg, sys_code):
    """한 시스템의 여러 날을 모아 TP/FP/FN 을 센다.

    ★조치효과는 **분모에서 뺀다.** 잘 잡았는데 운영자 조치로 회복된 것을
      과다탐지로 세면, 조치를 잘할수록 성능이 나빠 보인다 (accuracy.py 와
      같은 규칙이다 — 거기서 정한 것을 여기서 다시 정하지 않는다).
    ★사람이 직접 누른 판정(정탐/오탐)은 따로 센다. 자동 채점과 섞으면
      어느 쪽 숫자인지 말할 수 없다.
    """
    import store_csv
    from lp_client import sys_cfg
    c = sys_cfg(cfg, sys_code)
    n = {HIT: 0, FP: 0, FN: 0, EFFECT: 0}
    hn = {H_TP: 0, H_FP: 0}
    seen, waiting, rows_total = [], 0, 0
    for day in days:
        rows = store_csv.read_llm_day(day, c)
        if not rows:
            continue
        seen.append(day)
        for r in rows:
            rows_total += 1
            v = (r.get("판정") or "").strip()
            if v in n:
                n[v] += 1
            elif v in hn:
                hn[v] += 1
            elif (r.get("실제이상") or "").strip() in ("예", "아니오"):
                waiting += 1        # 판단은 했는데 검증 창이 아직 안 찼다
    p, r_, f = _prf(n[HIT], n[FP], n[FN])
    return {"sys": sys_code, "days": seen, "rows": rows_total,
            "tp": n[HIT], "fp": n[FP], "fn": n[FN], "effect": n[EFFECT],
            "human_tp": hn[H_TP], "human_fp": hn[H_FP], "waiting": waiting,
            "precision": p, "recall": r_, "f1": f,
            "n": n[HIT] + n[FP] + n[FN]}


# ────────────────────────────── 정합성(재현) ──────────────────────────────
def reproduce_days(days, cfg, max_points_per_day=24):
    """예측 잡이 준 점수를 우리가 룰로 다시 계산해 맞는지 본다.

    ★이것이 '정합성 검사' 그 자체다. 우리가 읽는 값이 예측 잡이 뜻한 값과
      같은지 확인하는 것 — 값이 어긋나면 그 뒤 판단·채점이 전부 헛것이다.
    ★하루 전체 1440 분을 다 돌리면 문서 한 장 만드는 데 오래 걸린다.
      고르게 뽑아(기본 24 지점) 표본으로 본다 — 표본 수를 문서에 밝힌다.
    """
    import fab_score
    import store_csv
    from lp_client import parse_dt
    ok = bad = 0
    notes, checked_days = [], []
    for day in days:
        rows = store_csv.read_day(day, cfg)
        if not rows:
            continue
        checked_days.append(day)
        step = max(1, len(rows) // max(1, max_points_per_day))
        for i in range(0, len(rows), step):
            t = (rows[i].get("datetime") or "").strip()
            if not t:
                continue
            try:
                out = fab_score.compare(rows, parse_dt(t), cfg, day=_d8(day))
            except Exception as ex:                     # noqa: BLE001
                bad += 1
                notes.append("{} {} — {}: {}".format(
                    _dash(day), t[-8:], type(ex).__name__, str(ex)[:80]))
                continue
            if not out.get("ok"):
                bad += 1
                notes.append("{} {} — {}".format(
                    _dash(day), t[-8:], str(out.get("error"))[:80]))
                continue
            miss = [x for x in (out.get("rows") or []) if x.get("mismatch")]
            if miss:
                bad += 1
                notes.append("{} {} — {}".format(
                    _dash(day), t[-8:], str(miss[0].get("mismatch"))[:110]))
            else:
                ok += 1
    tot = ok + bad
    return {"days": checked_days, "ok": ok, "bad": bad, "total": tot,
            "rate": (ok / tot) if tot else None, "notes": notes[:20]}


# ────────────────────────────── 날짜 모으기 ──────────────────────────────
def pick_days(cfg, day_from=None, day_to=None):
    """볼 날짜 목록. 안 주면 **어제까지** 있는 날 전부.

    ★오늘은 뺀다. 검증 창(기본 20분)이 안 찬 행이 많아 누락처럼 보인다 —
      그대로 성능에 넣으면 실제보다 나쁘게 나온다.
    """
    import store_csv
    have = []
    d = store_csv.data_dir(cfg)
    for fn in sorted(os.listdir(d)):
        u = fn.upper()
        if u.endswith("_TOTAL.CSV") or u.endswith("_LLM.CSV"):
            k = _d8(fn)
            if len(k) == 8 and k not in have:
                have.append(k)
    y = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    lo = _d8(day_from) if day_from else ""
    hi = _d8(day_to) if day_to else y
    return [k for k in sorted(have) if (not lo or k >= lo) and k <= hi]


# ────────────────────────────── 글 만들기 ──────────────────────────────
def _pct(v):
    return "—" if v is None else "{:.1f}%".format(v * 100)


def _f3(v):
    return "—" if v is None else "{:.3f}".format(v)


def build(day_from=None, day_to=None):
    """문서에 들어갈 것을 모두 모은다 (HTML·MD 가 같은 것을 본다)."""
    sys.path.insert(0, BASE_DIR)
    from lp_client import load_config
    import fab_score
    import sentinel

    cfg = load_config()
    days = pick_days(cfg, day_from, day_to)
    warn, danger, crit = sentinel.grade_cuts(cfg)

    perf = [score_days(days, cfg, s) for s in ["ALL"] + fab_score.fabs(cfg)]
    repro = reproduce_days(days, cfg)

    return {
        "rule": read_rule_source(),
        "made": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "days": days,
        "period": ("{} ~ {}".format(_dash(days[0]), _dash(days[-1]))
                   if days else ""),
        "cuts": (warn, danger, crit),
        "watch": fab_score.WATCH,
        "perf": perf,
        "repro": repro,
        "history": code_history(),
    }


# ────────────────────────────── HTML ──────────────────────────────
CSS = """
:root{--ink:#111827;--dim:#6b7280;--line:#e5e7eb;--acc:#4f46e5;--bad:#b91c1c;
 --ok:#047857;--warn:#b45309;--bg:#f8fafc}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);line-height:1.7;
 font-family:"Malgun Gothic","맑은 고딕",-apple-system,system-ui,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:36px 24px 80px}
h1{font-size:26px;margin:0 0 6px}
.sub{color:var(--dim);font-size:13px;margin:0 0 28px}
h2{font-size:18px;margin:34px 0 10px;padding-top:16px;border-top:2px solid var(--ink)}
h3{font-size:14.5px;margin:20px 0 8px;color:#374151}
p,li{font-size:13.5px}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;
 vertical-align:top}
th{background:var(--bg);font-weight:700;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code,.mono{font-family:Consolas,"D2Coding",monospace;font-size:12.5px;
 background:var(--bg);padding:1px 5px;border-radius:4px}
.note{background:var(--bg);border-left:4px solid var(--acc);padding:10px 14px;
 margin:12px 0;font-size:13px}
.miss{background:#fef2f2;border-left-color:var(--bad)}
.miss b{color:var(--bad)}
.flow{font-family:Consolas,"D2Coding",monospace;font-size:12.5px;
 background:var(--bg);border:1px solid var(--line);border-radius:8px;
 padding:14px 16px;white-space:pre;overflow-x:auto;line-height:1.6}
.big{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}
.dim{color:var(--dim)}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;
 background:var(--bg);border:1px solid var(--line);color:var(--dim)}
@media print{.wrap{max-width:none;padding:0} h2{page-break-after:avoid}}
"""


def _perf_table(perf):
    h = ['<table><tr><th>시스템</th><th class="n">적중(TP)</th>'
         '<th class="n">과다탐지(FP)</th><th class="n">누락(FN)</th>'
         '<th class="n">표본 N</th><th class="n">Precision</th>'
         '<th class="n">Recall</th><th class="n">F1</th>'
         '<th class="n">조치효과<br><span class="dim">(분모 제외)</span></th>'
         '<th class="n">채점 대기</th></tr>']
    for p in perf:
        h.append(
            '<tr><td><b>{}</b></td><td class="n">{}</td><td class="n">{}</td>'
            '<td class="n">{}</td><td class="n">{}</td><td class="n">{}</td>'
            '<td class="n">{}</td><td class="n">{}</td><td class="n">{}</td>'
            '<td class="n">{}</td></tr>'.format(
                e(p["sys"]), p["tp"], p["fp"], p["fn"], p["n"],
                _f3(p["precision"]), _f3(p["recall"]), _f3(p["f1"]),
                p["effect"], p["waiting"]))
    h.append("</table>")
    return "".join(h)


def render_html(d):
    w = [],
    out = []
    a = out.append
    warn, danger, crit = d["cuts"]
    a('<!doctype html><html lang="ko"><head><meta charset="utf-8">')
    a('<meta name="viewport" content="width=device-width,initial-scale=1">')
    a("<title>정합성 검사 서류 — AMHS Sentinel (real_time_amhs)</title>")
    a("<style>{}</style></head><body><div class=wrap>".format(CSS))

    a("<h1>정합성 검사 서류 — AMHS Sentinel</h1>")
    a('<p class="sub">real_time_amhs · 작성 {} · '
      '<span class="tag">이 문서의 숫자는 코드와 저장된 데이터에서 자동으로 '
      '뽑았습니다</span></p>'.format(e(d["made"])))

    # ── 0. 한 장 요약 ────────────────────────────────────────────────
    allp = next((p for p in d["perf"] if p["sys"] == "ALL"), None)
    a("<h2>0. 요약</h2>")
    a("<table><tr><th>항목</th><th>값</th><th>출처</th></tr>")
    a("<tr><td>평가 데이터 기간</td><td>{}</td><td>data/ 의 날짜 CSV "
      "(오늘 제외 — 검증 창 미충족)</td></tr>".format(
          e(d["period"]) or '<b class="dim">데이터 없음</b>'))
    a("<tr><td>평가 일수</td><td>{}일</td><td>같음</td></tr>".format(len(d["days"])))
    if allp:
        a("<tr><td>ALL Precision / Recall / F1</td>"
          "<td><span class=big>{} / {} / {}</span> "
          "<span class=dim>(표본 {}건)</span></td>"
          "<td>{{날짜}}_LLM.CSV 의 판정 컬럼</td></tr>".format(
              _f3(allp["precision"]), _f3(allp["recall"]), _f3(allp["f1"]),
              allp["n"]))
    r = d["repro"]
    a("<tr><td>점수 재현 일치율</td><td><span class=big>{}</span> "
      "<span class=dim>({}/{} 지점)</span></td>"
      "<td>fab_score.compare() — 예측 잡이 준 점수와 대조</td></tr>".format(
          _pct(r["rate"]), r["ok"], r["total"]))
    a("</table>")

    if not d["days"]:
        a('<div class="note miss"><b>저장된 데이터가 없습니다.</b> '
          'data/ 에 날짜 CSV 가 있어야 3·4·5 장의 숫자가 채워집니다. '
          '이 문서는 지금 <b>방법과 기준만</b> 담고 있습니다.</div>')

    # ── 1. 시스템 구성 ──────────────────────────────────────────────
    a("<h2>1. 시스템 구성과 데이터 흐름</h2>")
    a("<p><b>이 시스템은 룰을 만들지 않습니다.</b> 룰은 룰베이스 예측기가 "
      "만들고, 이 시스템은 그 결과를 받아 <b>읽고 · 재현하고 · 판단하고 · "
      "사후에 채점</b>합니다. 책임 경계를 먼저 밝힙니다.</p>")
    a('<div class="flow">'
      "[룰베이스 예측기]  {}\n"
      "   │  8영역 룰(R-A'·R-B·R-C'·R-D + SLA·소터·MAXCAPA)로 점수를 만든다\n"
      "   │  단계 판정 S1 / S2 / S3\n"
      "   ↓  {{날짜}}_발동이벤트.csv\n"
      "   │     ALL : unified_risk_score\n"
      "   │     FAB : area_score\n"
      "[real_time_amhs]\n"
      "   ├─ 읽기      store_csv → data/{{시스템}}/{{날짜}}_TOTAL.CSV\n"
      "   ├─ 재현 검산  fab_score.compare()  ← ★정합성 검사\n"
      "   ├─ 등급 판정  sentinel.grade()     경계 {} / 위험 {} / 초위험 {}\n"
      "   ├─ LLM 판단   1분마다 '지금 대응이 필요한 진짜 이상인가' (예/아니오)\n"
      "   └─ 사후 채점  accuracy.py → {{날짜}}_LLM.CSV 의 판정 컬럼\n"
      "                 ← ③평가 데이터 기간 · ④성능은 이쪽 소관"
      "</div>".format(e(d["rule"]["version"]), warn, danger, crit))

    # ── 2. 판단 기준 ────────────────────────────────────────────────
    a("<h2>2. 판단 기준</h2>")
    a("<h3>2-1. 어느 값을 보는가</h3>")
    a("<table><tr><th>대상</th><th>보는 컬럼</th><th>뜻</th></tr>"
      "<tr><td><b>ALL</b></td><td><code>unified_risk_score</code></td>"
      "<td>전체 통합 위험도</td></tr>"
      "<tr><td><b>FAB</b> (M14·M14B·M16A·M16B·M16HUB)</td>"
      "<td><code>area_score</code></td>"
      "<td>그 FAB 영역의 위험도. FAB 분리 파일을 읽는 순간 "
      "<code>unified_risk_score</code> 자리로 정규화됩니다"
      " (<code>jupyter_csv.py</code>)</td></tr></table>")
    a('<div class="note">두 값 모두 <b>예측 잡이 계산해 CSV 에 적어 준 '
      '값</b>입니다. 이 시스템이 다시 만들지 않습니다 — 다만 같은 룰로 '
      '되계산해 <b>맞는지 확인</b>합니다(4장).</div>')

    a("<h3>2-2. 등급 컷</h3>")
    a("<table><tr><th>등급</th><th class=n>점수</th><th>처리</th></tr>"
      "<tr><td>정상</td><td class=n>0 ~ {}</td><td>알람 없음</td></tr>"
      "<tr><td>경계</td><td class=n>{} ~ {}</td><td>확인 필요</td></tr>"
      "<tr><td>위험</td><td class=n>{} ~ {}</td><td>모니터링</td></tr>"
      "<tr><td>초위험</td><td class=n>{} ~ 100</td><td>조치</td></tr></table>"
      .format(warn - 1, warn, danger - 1, danger, crit - 1, crit))
    a('<p class="dim">출처: <code>config.grade.bands</code> → '
      '<code>sentinel.grade_cuts()</code>. 시스템별로 다르게 두면 '
      '<code>grade.by_sys</code> 가 덮습니다.</p>')

    # ── 3. 개정 이력 ────────────────────────────────────────────────
    a("<h2>3. 룰 — 버전 · 제작 데이터 · 검증</h2>")
    ru = d["rule"]
    a("<h3>3-1. 룰베이스 예측기</h3>")
    a("<table><tr><th>항목</th><th>값</th></tr>")
    a("<tr><td><b>버전</b></td><td><b>{}</b></td></tr>".format(e(ru["version"])))
    if ru["areas"]:
        a("<tr><td>대상 영역</td><td>{}</td></tr>".format(e(ru["areas"])))
    a("<tr><td><b>룰 제작(학습) 데이터 기간</b></td><td><b>{}</b></td></tr>"
      .format(e(ru["train"]) or "—"))
    a("<tr><td>예측기 자체 테스트 구간</td><td>{}</td></tr>".format(
        e(ru["test"]) or "—"))
    a("<tr><td>출처</td><td>{}</td></tr>".format(
        "<code>{}</code>".format(e(ru["path"])) if ru["found"]
        else '<b class="dim">파일을 못 찾아 머리말을 받아 적은 값</b>'))
    a("</table>")
    if not ru["found"]:
        a('<div class="note miss">룰 원본(<code>hubroom_predictor.py</code>)을 '
          '못 찾았습니다. 이 표는 <b>받아 적은 값</b>이라 룰이 바뀌면 어긋납니다. '
          '자리를 알려 주면 자동으로 읽습니다: '
          '<code>set RULE_SRC=...\\hubroom_predictor.py</code></div>')

    a("<h3>3-2. 임계 개정 (thresholds.json)</h3>")
    if ru["th_note"] or ru["changes"]:
        if ru["th_note"]:
            a('<div class="note"><b>개정 근거·검증 결과</b><br>{}</div>'.format(
                e(ru["th_note"])))
        if ru["changes"]:
            a("<table><tr><th>임계</th><th>바뀐 내용</th></tr>")
            for k, v in ru["changes"].items():
                a("<tr><td><code>{}</code></td><td>{}</td></tr>".format(
                    e(k), e(v)))
            a("</table>")
        if ru["th_howto"]:
            a('<p class="dim">{}</p>'.format(e(ru["th_howto"])))
        a('<p class="dim">출처: <code>{}</code></p>'.format(e(ru["th_path"])))
    else:
        a('<div class="note miss"><code>thresholds.json</code> 을 못 찾았습니다 '
          '— 임계는 예측기 코드 기본값으로 돌고 있습니다.</div>')
    a('<div class="note"><b>중요.</b> 룰이나 임계가 바뀐 날 이전의 판정은 '
      '<b>지금 룰의 성능이 아닙니다.</b> 성능표(5장)를 낼 때는 '
      '<b>최종 변경일 다음날부터</b>로 기간을 자르거나 버전별로 표를 '
      '나눠야 합니다. 섞으면 그 수치는 어느 룰의 것도 아닙니다.</div>')

    a("<h3>3-3. 이 시스템 (판정에 영향을 주는 코드)</h3>")
    hist = d["history"]
    if hist:
        a('<p class="dim">아래는 점수를 읽고·재현하고·채점하는 파일'
          '(<code>{}</code>)의 변경 이력입니다.</p>'.format(
              e(" · ".join(HIST_PATHS))))
        a("<table><tr><th>날짜</th><th>변경</th><th>커밋</th></tr>")
        for h in hist:
            a("<tr><td>{}</td><td>{}</td><td><code>{}</code></td></tr>".format(
                e(h["date"]), e(h["subject"]), e(h["hash"])))
        a("</table>")
    else:
        a('<div class="note miss">이력을 뽑지 못했습니다 '
          '(이 PC 에 git 이 없거나 저장소가 아닙니다). '
          '개발 PC 에서 다시 생성하면 채워집니다.</div>')

    # ── 4. 정합성 검사 ──────────────────────────────────────────────
    a("<h2>4. 정합성 검사 — 받은 점수를 다시 계산해 맞춰 본다</h2>")
    a("<p>예측 잡이 준 점수를 그대로 믿지 않고, <b>같은 룰로 되계산해 "
      "대조</b>합니다. 여기서 어긋나면 그 뒤의 판단과 채점이 모두 헛것이 "
      "되므로 성능보다 먼저 봅니다.</p>")
    a("<table><tr><th>항목</th><th>값</th></tr>"
      "<tr><td>방법</td><td><code>fab_score.compare()</code> — 저장된 "
      "<code>unified_risk_score</code>/<code>area_score</code> 와 "
      "룰 배점 합을 대조 (±1 이내를 일치로 봅니다)</td></tr>"
      "<tr><td>검사한 날</td><td class=n>{}일</td></tr>"
      "<tr><td>검사 지점</td><td class=n>{}</td></tr>"
      "<tr><td>일치</td><td class=n>{}</td></tr>"
      "<tr><td>불일치</td><td class=n>{}</td></tr>"
      "<tr><td><b>일치율</b></td><td><span class=big>{}</span></td></tr>"
      "</table>".format(len(r["days"]), r["total"], r["ok"], r["bad"],
                        _pct(r["rate"])))
    if r["notes"]:
        a("<h3>불일치 내역 (최대 20건)</h3><table>"
          "<tr><th>시각</th><th>내용</th></tr>")
        for ln in r["notes"]:
            t, _, rest = ln.partition(" — ")
            a("<tr><td class=mono>{}</td><td>{}</td></tr>".format(e(t), e(rest)))
        a("</table>")
    elif r["total"]:
        a('<div class="note"><b>불일치 없음.</b> 검사한 모든 지점에서 '
          '저장된 점수와 되계산 값이 일치했습니다.</div>')

    # ── 5. 성능 ────────────────────────────────────────────────────
    a("<h2>5. 성능 평가</h2>")
    a('<div class="note"><b>무엇을 채점한 값인가.</b> 이 표는 '
      '<b>룰 자체의 성능이 아니라</b>, 그 분의 상태를 두고 LLM 이 내린 '
      '판단(“지금 대응이 필요한 진짜 이상인가 — 예/아니오”)이 이후 '
      '데이터와 맞았는지를 잰 값입니다. 룰의 성능은 예측 잡 쪽에서 '
      '냅니다. 두 값을 같은 표에 섞지 마십시오.</div>')
    a("<h3>5-1. 판정 정의</h3>")
    a("<table><tr><th>판정</th><th>뜻</th><th>계산에서</th></tr>"
      "<tr><td>적중</td><td>이상이라 했고 실제로 이상이었다</td>"
      "<td>TP</td></tr>"
      "<tr><td>과다탐지</td><td>이상이라 했는데 아니었다</td><td>FP</td></tr>"
      "<tr><td>누락</td><td>아니라 했는데 이상이었다</td><td>FN</td></tr>"
      "<tr><td>조치효과</td><td>맞게 잡았는데 운영자 조치로 회복됐다</td>"
      "<td><b>분모에서 제외</b></td></tr>"
      "<tr><td>정탐 / 오탐</td><td>사람이 화면에서 직접 누른 판정</td>"
      "<td>자동 채점과 따로 셉니다</td></tr></table>")
    a('<p class="dim">조치효과를 오탐으로 세면 <b>조치를 잘할수록 성능이 '
      '나빠 보입니다.</b> 그래서 분모에서 뺍니다 '
      '(<code>accuracy.py</code> 와 같은 규칙).</p>')
    a("<h3>5-2. 계산식</h3>")
    a('<div class="flow">'
      "Precision = 적중 / (적중 + 과다탐지)\n"
      "Recall    = 적중 / (적중 + 누락)\n"
      "F1        = 2 · Precision · Recall / (Precision + Recall)\n\n"
      "· 분모가 0 이면 '—' 로 둡니다. 0.000 으로 적지 않습니다\n"
      "  (표본이 없는 것과 성능이 0 인 것은 다릅니다)"
      "</div>")
    a("<h3>5-3. 결과 <span class=dim>({})</span></h3>".format(
        e(d["period"]) or "데이터 없음"))
    a(_perf_table(d["perf"]))
    a('<p class="dim">‘채점 대기’ 는 LLM 이 판단은 했으나 검증 창이 아직 '
      '차지 않아 판정이 비어 있는 행입니다. 오늘 날짜를 넣으면 이 값이 '
      '커지고 성능이 실제보다 나쁘게 보이므로, 이 문서는 <b>어제까지</b>만 '
      '봅니다.</p>')

    # ── 6. 한계 ────────────────────────────────────────────────────
    a("<h2>6. 이 문서가 말하지 않는 것</h2>")
    a("<ul>"
      "<li><b>룰 자체의 성능이 아닙니다.</b> LLM 판단의 성능입니다 (5장 머리말).</li>"
      "<li><b>룰 제작 데이터 기간은 이 시스템이 모릅니다.</b> 예측 잡에서 "
      "받아야 합니다 (3-1).</li>"
      "<li><b>판정에 룰 버전 도장이 없습니다.</b> 지금은 날짜로만 구분할 수 "
      "있습니다 — 룰 변경일을 받아 기간을 자르십시오.</li>"
      "<li><b>표본 수를 반드시 함께 보십시오.</b> 표본이 적으면 소수 몇 건에 "
      "값이 크게 흔들립니다.</li>"
      "<li>재현 검산은 하루 전체가 아니라 <b>고르게 뽑은 표본 지점</b>입니다 "
      "(4장에 지점 수를 적었습니다).</li>"
      "</ul>")
    a('<p class="sub">이 문서는 <code>python 정합성_문서.py</code> 로 다시 '
      '만들 수 있습니다. 값이 바뀌면 문서도 같이 바뀝니다 — 손으로 고치지 '
      '마십시오.</p>')
    a("</div></body></html>")
    return "\n".join(out)


# ────────────────────────────── Markdown ──────────────────────────────
def render_md(d):
    warn, danger, crit = d["cuts"]
    r = d["repro"]
    o = []
    a = o.append
    a("# 정합성 검사 서류 — AMHS Sentinel (real_time_amhs)")
    a("")
    a("작성 {} · 이 문서의 숫자는 코드와 저장된 데이터에서 자동으로 뽑았습니다."
      .format(d["made"]))
    a("")
    a("## 0. 요약")
    a("")
    a("| 항목 | 값 |")
    a("|---|---|")
    a("| 평가 데이터 기간 | {} |".format(d["period"] or "**데이터 없음**"))
    a("| 평가 일수 | {}일 |".format(len(d["days"])))
    allp = next((p for p in d["perf"] if p["sys"] == "ALL"), None)
    if allp:
        a("| ALL P / R / F1 | {} / {} / {} (표본 {}건) |".format(
            _f3(allp["precision"]), _f3(allp["recall"]), _f3(allp["f1"]),
            allp["n"]))
    a("| 점수 재현 일치율 | {} ({}/{} 지점) |".format(
        _pct(r["rate"]), r["ok"], r["total"]))
    a("")
    a("## 1. 책임 경계")
    a("")
    a("- **룰은 룰베이스 예측기가 만듭니다** — {}. 이 시스템은 받아서 "
      "읽고·재현하고·판단하고·채점합니다.".format(d["rule"]["version"]))
    a("- 룰 개정 이력 · 룰 제작 데이터 기간 → **예측기 소관** (3장)")
    a("- 평가 데이터 기간 · 성능(P/R/F1) → **이 시스템 소관**")
    a("")
    a("## 2. 판단 기준")
    a("")
    a("| 대상 | 컬럼 |")
    a("|---|---|")
    a("| ALL | `unified_risk_score` |")
    a("| FAB | `area_score` |")
    a("")
    a("등급 컷 — 경계 {} / 위험 {} / 초위험 {} (`sentinel.grade_cuts()`)"
      .format(warn, danger, crit))
    a("")
    a("## 3. 룰 — 버전 · 제작 데이터 · 검증")
    a("")
    ru = d["rule"]
    a("| 항목 | 값 |")
    a("|---|---|")
    a("| **버전** | {} |".format(ru["version"]))
    if ru["areas"]:
        a("| 대상 영역 | {} |".format(ru["areas"]))
    a("| **룰 제작(학습) 데이터 기간** | {} |".format(ru["train"] or "—"))
    a("| 예측기 자체 테스트 구간 | {} |".format(ru["test"] or "—"))
    a("| 출처 | {} |".format(
        "`{}`".format(ru["path"]) if ru["found"]
        else "**파일을 못 찾아 머리말을 받아 적은 값**"))
    a("")
    if ru["th_note"]:
        a("### 임계 개정 (thresholds.json)")
        a("")
        a("> {}".format(ru["th_note"]))
        a("")
    if ru["changes"]:
        a("| 임계 | 바뀐 내용 |")
        a("|---|---|")
        for k, v in ru["changes"].items():
            a("| `{}` | {} |".format(k, v))
        a("")
    a("> **룰·임계가 바뀐 날 이전의 판정은 지금 룰의 성능이 아닙니다.** "
      "기간을 자르거나 버전별로 표를 나누십시오.")
    a("")
    if d["history"]:
        a("### 이 시스템 쪽 변경 이력 (판정에 영향을 주는 파일)")
        a("")
        a("| 날짜 | 변경 | 커밋 |")
        a("|---|---|---|")
        for h in d["history"][:20]:
            a("| {} | {} | `{}` |".format(h["date"], h["subject"], h["hash"]))
        a("")
    a("## 4. 정합성 검사 (점수 재현)")
    a("")
    a("`fab_score.compare()` 로 저장된 점수와 룰 배점 합을 대조 (±1 이내 일치).")
    a("")
    a("- 검사한 날 {}일 · 지점 {} · 일치 {} · 불일치 {} · **일치율 {}**"
      .format(len(r["days"]), r["total"], r["ok"], r["bad"], _pct(r["rate"])))
    for ln in r["notes"]:
        a("  - {}".format(ln))
    a("")
    a("## 5. 성능")
    a("")
    a("> 룰 자체가 아니라 **LLM 판단**의 성능입니다.")
    a("")
    a("```")
    a("Precision = 적중 / (적중 + 과다탐지)")
    a("Recall    = 적중 / (적중 + 누락)")
    a("F1        = 2PR / (P + R)          조치효과는 분모에서 제외")
    a("```")
    a("")
    a("| 시스템 | TP | FP | FN | N | Precision | Recall | F1 | 조치효과 | 대기 |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for p in d["perf"]:
        a("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            p["sys"], p["tp"], p["fp"], p["fn"], p["n"],
            _f3(p["precision"]), _f3(p["recall"]), _f3(p["f1"]),
            p["effect"], p["waiting"]))
    a("")
    a("## 6. 한계")
    a("")
    a("- 룰 자체의 성능이 아니라 LLM 판단의 성능입니다.")
    a("- 룰 제작 데이터 기간은 이 시스템이 모릅니다 (예측 잡 소관).")
    a("- 판정에 룰 버전 도장이 없습니다 — 날짜로만 구분됩니다.")
    a("- 표본 수를 반드시 함께 보십시오.")
    a("- 재현 검산은 표본 지점입니다 (전 구간이 아님).")
    return "\n".join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description="정합성 검사 서류 생성")
    ap.add_argument("--from", dest="day_from", help="시작 날짜 YYYYMMDD")
    ap.add_argument("--to", dest="day_to", help="끝 날짜 YYYYMMDD (기본 어제)")
    ap.add_argument("--md", action="store_true", help="Markdown 도 같이")
    ap.add_argument("--out", help="HTML 저장 경로")
    a = ap.parse_args(argv)

    d = build(a.day_from, a.day_to)
    os.makedirs(DOC_DIR, exist_ok=True)
    out = a.out or OUT_HTML
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_html(d))
    print("만들었습니다: {}".format(out))
    if a.md:
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write(render_md(d))
        print("만들었습니다: {}".format(OUT_MD))

    # 화면에도 한 줄 — 파일을 안 열어 봐도 상태를 알 수 있게
    r = d["repro"]
    allp = next((p for p in d["perf"] if p["sys"] == "ALL"), None)
    print("  평가 기간 : {}".format(d["period"] or "(데이터 없음)"))
    print("  재현 일치 : {} ({}/{} 지점)".format(
        _pct(r["rate"]), r["ok"], r["total"]))
    if allp:
        print("  ALL P/R/F1: {} / {} / {}  (표본 {}건)".format(
            _f3(allp["precision"]), _f3(allp["recall"]), _f3(allp["f1"]),
            allp["n"]))
    print("  룰 버전  : {}".format(d["rule"]["version"]))
    if not d["rule"]["found"]:
        print("  ★룰 원본(hubroom_predictor.py)을 못 찾아 받아 적은 값입니다 — "
              "set RULE_SRC=<경로> 로 자리를 알려 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
