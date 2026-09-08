"""real_time_amhs/컬럼흐름_문서.py — '어느 컬럼이 어떻게 점수가 되나' 문서

    python 컬럼흐름_문서.py          → docs/컬럼흐름_상세.html
    python 컬럼흐름_문서.py 파일.html

무엇을 답하나
    ① FAB 별로 M16A_HUBROOM_PR.CSV 의 **어느 컬럼**을 실제로 쓰나
    ② hubroom_predictor 가 **새로 만드는 컬럼**은 무엇인가
    ③ ALL 의 unified_risk_score 는 어떻게 만들어지나
    ④ FAB 별 area_score 는 어떻게 만들어지고, 영역분리에서 어떻게 옮겨지나

왜 생성하나 — 손으로 쓰면 어긋난다
    fab_score_doc.py 와 같은 이유다. 임계 하나 바뀌면 문서만 옛날 값으로
    남는다. 여기 표는 전부 **hubroom_predictor.py 를 직접 읽어서** 만든다:
        컬럼 지도   RA_COL · RB_COL · SLA_COL · SORTER_COL · …
        임계        TH_RA · TH_RB_30 · TH_SLA_RATIO · …
        배점        eval_area_rules() 의 ra_pts / rb_pts / …
        융합        evaluate_unified() 의 flow/sla/sorter/maxcapa 배점
        출력 컬럼   EVENT_FIELDS
    ★못 읽은 값은 '읽지 못함' 이라고 적는다. 지어내지 않는다.
    ★소스 자리를 못 찾으면 어디를 봐야 하는지 알려 준다:
        set RULE_SRC=C:\\...\\hubroom_predictor.py

읽는 방법
    ast 로 읽는다 — import 하지 않는다. 예측기는 로그·경로·업로더를 만지고
    thresholds.json 을 찾아 읽는다. 문서 만들자고 그걸 돌릴 이유가 없다.
"""
from __future__ import annotations

import ast
import html
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE_DIR, "docs")
OUT = os.path.join(DOC_DIR, "컬럼흐름_상세.html")

RULE_DIRS = [
    "rool_skill_test",
    os.path.join("M16_BR_개인지식", "스크립트"),
    os.path.join("WORD_MODEL", "OHS_DATA_MD", "Rulebase_prediction"),
    os.path.join("월드모델", "OHS_DATA_MD", "Rulebase_prediction"),
    ".",
]


def e(s) -> str:
    return html.escape("" if s is None else str(s))


def find_rule_src():
    env = (os.environ.get("RULE_SRC") or "").strip()
    if env and os.path.isfile(env):
        return env
    base = BASE_DIR
    for _ in range(5):
        for d in RULE_DIRS:
            p = os.path.join(base, d, "hubroom_predictor.py")
            if os.path.isfile(p):
                return p
        nxt = os.path.dirname(base)
        if nxt == base:
            break
        base = nxt
    return ""


# ─────────────────────────────────────────────────────────────────────
# 소스에서 값 뽑기
#
# ★import 하지 않고 ast 로 읽는다. 예측기를 돌리면 로그 폴더를 만들고
#   thresholds.json 을 찾아 읽고 업로더를 붙인다 — 문서 하나 만들자고
#   그걸 다 하게 둘 이유가 없다.
# ★_TD('TH_RA', {...}) 꼴은 **두 번째 인자**가 코드 기본값이다.
#   운영에서는 thresholds.json 이 이 값을 덮는다 — 문서에 그렇게 밝힌다.
# ─────────────────────────────────────────────────────────────────────
def _lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:                                   # noqa: BLE001
        return None


def read_consts(src):
    """모듈 최상위 대입에서 dict/list 상수를 꺼낸다."""
    out = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        v = node.value
        # _T('이름', 기본값) / _TD('이름', {…}) → 두 번째 인자가 코드 기본값
        if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                and v.func.id in ("_T", "_TD") and len(v.args) >= 2):
            got = _lit(v.args[1])
        else:
            got = _lit(v)
        if got is not None:
            out[tgt.id] = got
    return out


def read_extract_map(src):
    """iter_unified_rows() 가 FAB 별로 읽는 원시 컬럼을 뽑는다.

    d['M16HUB'] = { 'ra': safe_float(g('...')), ... } 꼴에서
    **g('컬럼') 안의 문자열**을 항목 이름과 함께 모은다.
    f-string(리프터 번호 붙이기)은 문자열이 아니라 값을 못 읽으므로
    '패턴' 으로 표시한다.
    """
    out = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "iter_unified_rows"),
              None)
    if fn is None:
        return out
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        t = node.targets[0]
        if not (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                and t.value.id == "d"):
            continue
        area = _lit(t.slice)
        if not isinstance(area, str) or not isinstance(node.value, ast.Dict):
            continue
        items = []
        for k, v in zip(node.value.keys, node.value.values):
            key = _lit(k)
            if not isinstance(key, str):
                continue
            items.append({"key": key, "cols": _g_cols(v),
                          "kind": _kind(v)})
        out[area] = items
    return out


_G_STR = re.compile(r"g\(\s*(['\"])(.+?)\1\s*\)")
_G_F = re.compile(r"g\(\s*f(['\"])(.+?)\1\s*\)")


def _g_cols(node):
    """이 값 안에서 g('컬럼') 으로 읽는 컬럼 이름들."""
    try:
        seg = ast.unparse(node)
    except Exception:                                   # noqa: BLE001
        return []
    cols = [m.group(2) for m in _G_STR.finditer(seg)]
    cols += ["{} (패턴)".format(m.group(2)) for m in _G_F.finditer(seg)]
    # RA_COL['M16HUB'] 처럼 지도를 거쳐 읽는 것도 밝힌다
    for m in re.finditer(r"\b([A-Z][A-Z0-9_]*_COLS?)\[", seg):
        cols.append("{} 지도" .format(m.group(1)))
    for m in re.finditer(r"\bfor\s+col\s+in\s+([A-Z][A-Z0-9_]*)", seg):
        cols.append("{} 전부".format(m.group(1)))
    seen, uniq = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _kind(node):
    try:
        seg = ast.unparse(node)
    except Exception:                                   # noqa: BLE001
        return ""
    if seg.startswith("safe_float"):
        return "실수"
    if seg.startswith("safe_int"):
        return "정수"
    if seg.startswith("sum("):
        return "합"
    if seg.startswith("{"):
        return "묶음"
    return ""


def read_points(src):
    """배점을 코드에서 읽는다 — ra_pts = 10 if … 꼴."""
    out = {}
    for m in re.finditer(r"^\s*(\w+_pts)\s*=\s*(\d+)\s*if\s+out\['(\w+)'\]",
                         src, re.M):
        out[m.group(1)] = {"pts": int(m.group(2)), "flag": m.group(3)}
    m = re.search(r"mc_pts\s*=\s*(\d+)\s*\*\s*out\['maxcapa_changed_n'\]", src)
    if m:
        out["mc_pts"] = {"pts": int(m.group(1)), "flag": "maxcapa_changed_n",
                         "per": True}
    m = re.search(r"out\['area_score'\]\s*=\s*min\((\d+)\s*,", src)
    out["_cap"] = int(m.group(1)) if m else None
    return out


def read_unified(src):
    """융합 점수 만드는 규칙을 읽는다."""
    out = {"flow": {}, "sla": None, "sorter": None, "mc": None,
           "cap": None, "levels": []}
    fn = re.search(r"def evaluate_unified\(.*?\n(.*?)\n# =", src, re.S)
    seg = fn.group(1) if fn else src
    for lv in ("심각", "위험", "주의"):
        m = re.search(r"level'\]\s*==\s*'{}'\s*:\s*\n\s*flow_score\s*\+=\s*(\d+)"
                      .format(lv), seg)
        if m:
            out["flow"][lv] = int(m.group(1))
    m = re.search(r"sla_score\s*=\s*sum\((\d+)\s+for", seg)
    out["sla"] = int(m.group(1)) if m else None
    m = re.search(r"sorter_score\s*=\s*sum\((\d+)\s+for", seg)
    out["sorter"] = int(m.group(1)) if m else None
    m = re.search(r"mc_score\s*\+=\s*(\d+)\s*\*\s*n", seg)
    out["mc"] = int(m.group(1)) if m else None
    m = re.search(r"unified_risk_score\s*=\s*min\((\d+)\s*,", seg)
    out["cap"] = int(m.group(1)) if m else None
    for m in re.finditer(
            r"unified_risk_score\s*>=\s*(\d+)\s*:\s*\n\s*unified_risk_level\s*=\s*'(\S+?)'",
            seg):
        out["levels"].append((int(m.group(1)), m.group(2)))
    m = re.search(r"else:\s*\n\s*unified_risk_level\s*=\s*'(\S+?)'", seg)
    if m:
        out["levels"].append((0, m.group(1)))
    m = re.search(r"triggered_areas\s*=\s*\[a for a, r in area_results\.items\(\)"
                  r"\s*if r\.get\('area_score', 0\)\s*>=\s*(\d+)\]", seg)
    out["prop_min"] = int(m.group(1)) if m else None
    return out


def read_flow_th(src):
    """흐름 룰의 배수 임계."""
    out = {}
    for name, lv in (("TH_FLOW_X3_0", "심각"), ("TH_FLOW_X2_0", "위험"),
                     ("TH_FLOW_X1_5", "주의")):
        m = re.search(r"{}\s*=\s*_T\('[^']+',\s*([\d.]+)\)".format(name), src)
        if m:
            out[lv] = float(m.group(1))
    m = re.search(r"avg_window\s*=\s*list\(flow_history\)\[-(\d+):\]", src)
    out["_avg"] = int(m.group(1)) if m else None
    return out


# ─────────────────────────────── 표 도우미 ───────────────────────────────
AREA_ORDER = ["M16HUB", "M14", "M14B", "M16A", "M16B", "M16", "M16_PKT", "M16_WT"]

# 룰 이름을 사람 말로 — 코드 약칭만 적으면 현장에서 못 읽는다
RULE_NAME = {
    "ra_trig": ("R-A′ 반송지연", "1분 평균 반송/적재 시간이 임계 이상인 분이 "
                "최근 10분에 1회 이상"),
    "ra_sustained": ("R-A′ 지속", "최근 5분 중 정해진 횟수 이상이 "
                     "임계×비율을 넘음 — 짧게 튄 것과 구분한다"),
    "rb_trig": ("R-B 반입 급증(30분)", "허브로 보내는 대기 수가 30분 전보다 "
                "임계만큼 늘었다"),
    "rb_fast": ("R-B 반입 급증(10분)", "같은 것을 10분 창으로 — 빠르게 "
                "차오르는 경우"),
    "rc_trig": ("R-C′ 리프터 역증가 / CNV 쏠림",
                "M16HUB: 리프터 합은 줄었는데 개별로 늘어난 호기가 임계 이상. "
                "M14: 북/남 CNV 한쪽 쏠림 비율"),
    "rd_trig": ("R-D 저장 포화", "M16HUB: FAB 저장율 또는 STB 3F 저장율. "
                "그 밖: OHT 가동률"),
    "sla_trig": ("SLA 4분 초과", "4분 초과 비율이 임계 이상이거나, "
                 "초과 건수가 10분 만에 20건 이상 늘었다"),
    "sorter_trig": ("소터 대기/실패", "소터 대기 초과 수가 임계 이상, "
                    "또는 반송 실패가 1건 이상"),
}


def points_table(pts):
    rows = [("ra_pts", "ra_trig"), ("ra_sus_pts", "ra_sustained"),
            ("rb_pts", "rb_trig"), ("rb_fast_pts", "rb_fast"),
            ("rc_pts", "rc_trig"), ("rd_pts", "rd_trig"),
            ("sla_pts", "sla_trig"), ("sort_pts", "sorter_trig")]
    h = ['<table><tr><th>룰</th><th>무엇을 보나</th><th class="n">배점</th>'
         '<th>코드</th></tr>']
    for var, flag in rows:
        got = pts.get(var) or {}
        name, desc = RULE_NAME.get(flag, (flag, ""))
        h.append('<tr><td><b>{}</b></td><td>{}</td><td class="n">{}</td>'
                 '<td><code>{}</code></td></tr>'.format(
                     e(name), e(desc),
                     got.get("pts", "<span class=dim>읽지 못함</span>"),
                     e(var)))
    mc = pts.get("mc_pts") or {}
    h.append('<tr><td><b>MAXCAPA 축소</b></td>'
             '<td>운영자가 용량을 줄였다 — 바뀐 컬럼 <b>1개마다</b> 가산</td>'
             '<td class="n">{} × n</td><td><code>mc_pts</code></td></tr>'
             .format(mc.get("pts", "?")))
    h.append("</table>")
    return "".join(h)


def build():
    src_path = find_rule_src()
    src = ""
    if src_path:
        with open(src_path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    C = read_consts(src)
    return {
        "path": src_path,
        "ok": bool(src),
        "version": (re.search(r"^(.*?예측기\s*v[\d.]+.*)$", src, re.M).group(1).strip()
                    if re.search(r"^(.*?예측기\s*v[\d.]+.*)$", src, re.M) else ""),
        "C": C,
        "extract": read_extract_map(src),
        "pts": read_points(src),
        "uni": read_unified(src),
        "flow_th": read_flow_th(src),
    }


CSS = """
:root{--ink:#111827;--dim:#6b7280;--line:#e5e7eb;--acc:#4f46e5;--bad:#b91c1c;
 --bg:#f8fafc;--hi:#eef2ff}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);line-height:1.7;
 font-family:"Malgun Gothic","맑은 고딕",-apple-system,system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:36px 24px 90px}
h1{font-size:25px;margin:0 0 6px}
.sub{color:var(--dim);font-size:13px;margin:0 0 26px}
h2{font-size:18px;margin:36px 0 10px;padding-top:16px;border-top:2px solid var(--ink)}
h3{font-size:14.5px;margin:22px 0 8px;color:#374151}
h4{font-size:13.5px;margin:16px 0 6px;color:#4b5563}
p,li{font-size:13.5px}
table{border-collapse:collapse;width:100%;margin:8px 0 4px;font-size:12.5px}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--bg);font-weight:700;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code,.mono{font-family:Consolas,"D2Coding",monospace;font-size:12px;
 background:var(--bg);padding:1px 5px;border-radius:4px;word-break:break-all}
.note{background:var(--hi);border-left:4px solid var(--acc);padding:10px 14px;
 margin:12px 0;font-size:13px}
.miss{background:#fef2f2;border-left-color:var(--bad)}
.flow{font-family:Consolas,"D2Coding",monospace;font-size:12.5px;background:var(--bg);
 border:1px solid var(--line);border-radius:8px;padding:14px 16px;white-space:pre;
 overflow-x:auto;line-height:1.65}
.dim{color:var(--dim)}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;
 background:var(--bg);border:1px solid var(--line);color:var(--dim)}
.big{font-size:19px;font-weight:800}
ol.steps{padding-left:20px} ol.steps>li{margin:8px 0}
@media print{.wrap{max-width:none;padding:0} h2{page-break-after:avoid}}
"""


def render(d):
    C, pts, uni, fl = d["C"], d["pts"], d["uni"], d["flow_th"]
    o = []
    a = o.append
    a('<!doctype html><html lang="ko"><head><meta charset="utf-8">')
    a('<meta name="viewport" content="width=device-width,initial-scale=1">')
    a("<title>컬럼 → 점수 상세 — AMHS Sentinel</title>")
    a("<style>{}</style></head><body><div class=wrap>".format(CSS))
    a("<h1>어느 컬럼이 어떻게 점수가 되나 — 상세</h1>")
    a('<p class="sub">{}{}</p>'.format(
        e(d["version"]) or "룰베이스 예측기",
        ' · 출처 <code>{}</code>'.format(e(d["path"])) if d["ok"] else ""))
    if not d["ok"]:
        a('<div class="note miss"><b>hubroom_predictor.py 를 못 찾았습니다.</b> '
          '이 문서의 표는 비어 있습니다. 자리를 알려 주십시오:<br>'
          '<code>set RULE_SRC=C:\\...\\hubroom_predictor.py</code></div>')
    a('<div class="note">이 문서의 표는 <b>예측기 소스를 그대로 읽어</b> '
      '만듭니다. 임계·배점이 바뀌면 문서도 같이 바뀝니다 — 손으로 고치지 '
      '마십시오. 임계 기본값은 코드 값이며, 운영에서는 '
      '<code>thresholds.json</code> 이 덮습니다.</div>')

    # ── 0. 전체 흐름 ─────────────────────────────────────────────────
    a("<h2>0. 전체 흐름</h2>")
    a('<div class="flow">'
      "M16A_HUBROOM_PR.CSV      수집기가 매분 덮어씀 · CRT_TM + 원시 265 컬럼\n"
      "        │\n"
      "        │  ① 읽기        iter_unified_rows()  — FAB 8영역이 각자 자기 컬럼만 뽑는다\n"
      "        │  ② 90분 창      WINDOW_MIN 만큼 쌓아 둔다 (차분·지속 판정에 필요)\n"
      "        ↓\n"
      "  ③ 영역 룰 평가   eval_area_rules(area, window)\n"
      "        │            R-A′ · R-B · R-C′ · R-D · SLA · 소터 · MAXCAPA\n"
      "        ↓            → area_score  (0~{cap})            ← FAB 판단 기준\n"
      "  ④ 흐름 룰 평가   eval_flow_rules(flow_history)   9~10개 노드, 30분 평균 대비 배수\n"
      "        ↓\n"
      "  ⑤ 통합 융합      evaluate_unified()\n"
      "        │            Σ area_score + 흐름 + SLA + 소터 + MAXCAPA\n"
      "        ↓            → unified_risk_score (0~{ucap})     ← ALL 판단 기준\n"
      "  {{날짜}}_발동이벤트.csv   매분 1행 (이벤트 없는 분도 기록)\n"
      "        │\n"
      "        │  ⑥ 영역분리 — FAB 별 파일로 나눔. 그 FAB 의 점수를 area_score 로\n"
      "        ↓\n"
      "  real_time_amhs   ALL: unified_risk_score / FAB: area_score 로 등급 판정"
      "</div>".format(cap=pts.get("_cap") or "?", ucap=uni.get("cap") or "?"))

    # ── 1. FAB 별 실제 컬럼 ─────────────────────────────────────────
    a("<h2>1. FAB 별로 실제 읽는 컬럼</h2>")
    a("<p><code>M16A_HUBROOM_PR.CSV</code> 에는 <b>CRT_TM + 원시 265 컬럼</b>이 "
      "있습니다. 예측기는 그중 <b>영역별로 정해진 컬럼만</b> 뽑아 씁니다. "
      "아래가 그 전부입니다 — <code>iter_unified_rows()</code> 에서 읽었습니다.</p>")

    # 룰별 대표 컬럼 지도 먼저
    a("<h3>1-1. 룰이 보는 대표 컬럼 (영역별로 다르다)</h3>")
    maps = [("RA_COL", "R-A′ 반송/적재 시간",
             "★영역마다 컬럼이 다릅니다. HUB·M14B·PKT·WT 는 "
             "<code>QUE.TIME.AVGTOTALTIME1MIN</code>, "
             "M14·M16A·M16B 는 <code>QUE.LOAD.AVGLOADTIME1MIN</code> 입니다"),
            ("RB_COL", "R-B 허브행 대기 수", ""),
            ("RD_OHT_COL", "R-D OHT 가동률", ""),
            ("SLA_COL", "SLA 4분 초과 비율", ""),
            ("SORTER_COL", "소터 대기 초과", ""),
            ("SORTER_FAIL_COL", "소터 반송 실패", "")]
    for name, what, note in maps:
        m = C.get(name)
        if not isinstance(m, dict):
            continue
        a("<h4>{} <span class=tag>{}</span></h4>".format(e(what), e(name)))
        if note:
            a('<p class="dim">{}</p>'.format(note))
        a("<table><tr><th>영역</th><th>컬럼</th></tr>")
        for k in AREA_ORDER:
            if k in m:
                a("<tr><td><b>{}</b></td><td><code>{}</code></td></tr>".format(
                    e(k), e(m[k])))
        for k in m:
            if k not in AREA_ORDER:
                a("<tr><td><b>{}</b></td><td><code>{}</code></td></tr>".format(
                    e(k), e(m[k])))
        a("</table>")

    # 영역별 전체 항목
    a("<h3>1-2. 영역별로 뽑는 항목 전부</h3>")
    ex = d["extract"]
    for area in AREA_ORDER:
        items = ex.get(area)
        if not items:
            continue
        a("<h4>{} <span class=tag>{}개 항목</span></h4>".format(
            e(area), len(items)))
        a("<table><tr><th>항목</th><th>형</th><th>읽는 컬럼</th></tr>")
        for it in items:
            cols = it["cols"] or ["<span class=dim>—</span>"]
            a("<tr><td><code>{}</code></td><td>{}</td><td>{}</td></tr>".format(
                e(it["key"]), e(it["kind"]),
                "<br>".join("<code>{}</code>".format(e(c)) if not c.startswith("<")
                            else c for c in cols)))
        a("</table>")
    if C.get("LIFTER_IDS"):
        a('<p class="dim">리프터 <b>{}</b>대: {} — '
          '<code>M16HUB.LFT.{{호기}}.TOTAL_CURRENTQCNT</code> 를 각각 읽습니다.'
          '</p>'.format(len(C["LIFTER_IDS"]),
                        e(" · ".join(C["LIFTER_IDS"]))))
    if C.get("HUB_OUT_COLS"):
        a("<h4>HUB 출구 <span class=tag>HUB_OUT_COLS</span></h4><table>"
          "<tr><th>컬럼</th></tr>")
        for c in C["HUB_OUT_COLS"]:
            a("<tr><td><code>{}</code></td></tr>".format(e(c)))
        a("</table>")

    # ── 2. 임계 ─────────────────────────────────────────────────────
    a("<h2>2. 임계값 (코드 기본값)</h2>")
    a('<p class="dim">운영에서는 <code>thresholds.json</code> 이 이 값을 '
      '덮습니다. 지금 돌고 있는 값은 그 파일을 보십시오.</p>')
    ths = [("TH_RA", "R-A′ 반송/적재 시간 (분)"),
           ("TH_RB_30", "R-B 30분 증가량"),
           ("TH_SLA_RATIO", "SLA 4분 초과 비율 (%)"),
           ("TH_SORTER_WAIT", "소터 대기 초과 수")]
    for name, what in ths:
        m = C.get(name)
        if not isinstance(m, dict):
            continue
        keys = [k for k in AREA_ORDER if k in m] + [k for k in m if k not in AREA_ORDER]
        a("<h4>{} <span class=tag>{}</span></h4>".format(e(what), e(name)))
        a("<table><tr>" + "".join("<th class=n>{}</th>".format(e(k)) for k in keys)
          + "</tr><tr>"
          + "".join('<td class="n">{}</td>'.format(e(m[k])) for k in keys)
          + "</tr></table>")
    a("<h4>그 밖</h4><table><tr><th>이름</th><th class=n>값</th><th>뜻</th></tr>")
    for name, what in (("TH_RA_SUSTAINED_RATIO", "지속 판정에 쓰는 임계 비율"),
                       ("TH_RA_SUSTAINED_COUNT", "최근 5분 중 몇 회 이상"),
                       ("TH_RC_REVERSE", "리프터 역증가 호기 수"),
                       ("TH_RD_FABSTORAGE", "FAB 저장율 (%)"),
                       ("TH_RD_HUB_STB_UTIL", "HUB STB 3F 저장율 (%)"),
                       ("TH_RD_OHT_UTIL", "OHT 가동률 (%)"),
                       ("TH_SORTER_TRANSFER_FAIL", "소터 반송 실패 건수"),
                       ("WINDOW_MIN", "창 길이 (분)"),
                       ("PREDICT_LOOKBACK_MIN", "전파 사슬 되돌아보기 (분)")):
        if name in C:
            a("<tr><td><code>{}</code></td><td class=n>{}</td><td>{}</td></tr>"
              .format(e(name), e(C[name]), e(what)))
    a("</table>")
    if isinstance(C.get("MAXCAPA_NORMAL"), dict):
        a("<h4>MAXCAPA 정상값 / 축소 판정선 <span class=tag>MAXCAPA_NORMAL</span></h4>")
        a('<p class="dim">운영자가 용량을 줄이면 값이 판정선 이하로 떨어집니다 — '
          '그 자체를 신호로 봅니다.</p>')
        a("<table><tr><th>컬럼</th><th class=n>정상</th><th class=n>판정선(≤)</th></tr>")
        for col, v in C["MAXCAPA_NORMAL"].items():
            n0, th = (v + (None, None))[:2] if isinstance(v, (list, tuple)) else (v, None)
            a("<tr><td><code>{}</code></td><td class=n>{}</td>"
              "<td class=n>{}</td></tr>".format(e(col), e(n0), e(th)))
        a("</table>")

    # ── 3. area_score ───────────────────────────────────────────────
    a("<h2>3. FAB 점수 <code>area_score</code> 가 만들어지는 과정</h2>")
    a("<p>영역 하나에 대해 <code>eval_area_rules(area, window)</code> 가 룰 "
      "8종을 각각 판정하고, <b>켜진 룰의 배점을 더합니다.</b></p>")
    a(points_table(pts))
    cap = pts.get("_cap")
    a('<div class="flow">'
      "area_score = RA + RA_sus + RB + RB_fast + RC + RD + SLA + SORT + MAXCAPA×n\n"
      "area_score = min({cap}, 위 합)        ← {cap} 점에서 자른다\n\n"
      "· 자르기 전 원본은 area_score_raw 로 같이 남긴다\n"
      "· 룰별 분해 점수는 pts_RA · pts_RB … 로 각각 남긴다 (조합 분석용)"
      "</div>".format(cap=cap or "?"))
    a('<div class="note"><b>왜 {}점에서 자르나.</b> MAXCAPA 는 바뀐 컬럼 '
      '수만큼 곱해지므로 한 영역이 무한정 커질 수 있습니다. 한 영역이 전체를 '
      '삼키지 않게 상한을 둡니다.</div>'.format(cap or "?"))
    a("<h3>3-1. 판정에 창(window)이 왜 필요한가</h3>")
    a("<table><tr><th>룰</th><th>보는 구간</th><th>판정</th></tr>"
      "<tr><td>R-A′</td><td>최근 10분</td><td>임계 이상인 분이 1회 이상</td></tr>"
      "<tr><td>R-A′ 지속</td><td>최근 5분</td>"
      "<td>임계×{} 이상인 분이 {}회 이상</td></tr>"
      "<tr><td>R-B (30분)</td><td>현재 − 31행 전</td><td>증가량이 임계 이상</td></tr>"
      "<tr><td>R-B (10분)</td><td>현재 − 11행 전</td><td>같음</td></tr>"
      "<tr><td>R-C′</td><td>현재 − 21행 전</td>"
      "<td>리프터 <b>합은 줄었는데</b> 개별로 늘어난 호기가 임계 이상</td></tr>"
      "<tr><td>SLA</td><td>현재 − 11행 전</td>"
      "<td>비율이 임계 이상 <b>또는</b> 초과 건수가 10분 만에 20건 이상 증가</td></tr>"
      "<tr><td>R-D · 소터 · MAXCAPA</td><td>현재 1행</td><td>임계 비교</td></tr>"
      "</table>".format(C.get("TH_RA_SUSTAINED_RATIO", "?"),
                        C.get("TH_RA_SUSTAINED_COUNT", "?")))
    a('<p class="dim">그래서 창(<code>WINDOW_MIN={}</code>분)이 채워지기 전에는 '
      '일부 룰이 판정되지 않습니다 — 재시작 직후 점수가 낮게 나오는 이유입니다.'
      '</p>'.format(C.get("WINDOW_MIN", "?")))

    # ── 4. unified_risk_score ───────────────────────────────────────
    a("<h2>4. ALL 점수 <code>unified_risk_score</code> 가 만들어지는 과정</h2>")
    a("<p><code>evaluate_unified()</code> 가 <b>영역 점수 합에 전체 관점의 "
      "가산을 더합니다.</b> ALL 은 영역이 아니라 <b>전체를 본 값</b>이라, "
      "FAB 점수와 자·단위가 다릅니다.</p>")
    a('<div class="flow">'
      "layer1_total = Σ area_score            (8영역 전부 더한다)\n"
      "flow_score   = 흐름 노드마다  심각 +{s} / 위험 +{d} / 주의 +{w}\n"
      "sla_score    = SLA 켜진 영역 수 × {sla}\n"
      "sorter_score = 소터 켜진 영역 수 × {sort}\n"
      "mc_score     = Σ (영역별 MAXCAPA 바뀐 컬럼 수 × {mc})\n"
      "\n"
      "unified_risk_score = min({cap}, layer1_total + flow + sla + sorter + mc)"
      "</div>".format(s=uni["flow"].get("심각", "?"),
                      d=uni["flow"].get("위험", "?"),
                      w=uni["flow"].get("주의", "?"),
                      sla=uni["sla"] or "?", sort=uni["sorter"] or "?",
                      mc=uni["mc"] or "?", cap=uni["cap"] or "?"))
    a('<div class="note"><b>SLA·소터·MAXCAPA 는 두 번 셉니다.</b> '
      'area_score 안에서 한 번(그 영역의 문제로), 융합에서 또 한 번(전체로 '
      '번질 신호로). 일부러 그렇게 둔 것이므로, ALL 점수를 FAB 점수 합으로 '
      '되계산하면 맞지 않습니다.</div>')

    a("<h3>4-1. 흐름 룰 — 무엇을 보나</h3>")
    a("<p>노드마다 <b>지금 값 ÷ 최근 {}분 평균</b> 배수를 봅니다. "
      "절대값이 아니라 <b>평소 대비</b>라, 노드마다 크기가 달라도 같은 자로 "
      "잽니다.</p>".format(fl.get("_avg", "?")))
    a("<table><tr><th class=n>배수</th><th>등급</th><th class=n>가산</th></tr>")
    for lv in ("심각", "위험", "주의"):
        a("<tr><td class=n>≥ {}×</td><td>{}</td><td class=n>+{}</td></tr>"
          .format(fl.get(lv, "?"), lv, uni["flow"].get(lv, "?")))
    a("</table>")
    if isinstance(C.get("FLOW_NODES"), dict):
        a("<h4>흐름 노드 <span class=tag>{}개</span></h4>".format(
            len(C["FLOW_NODES"])))
        a("<table><tr><th>노드</th><th>영역</th><th>컬럼</th></tr>")
        for node, v in C["FLOW_NODES"].items():
            ar, col = (list(v) + ["", ""])[:2] if isinstance(v, (list, tuple)) else ("", v)
            a("<tr><td><code>{}</code></td><td>{}</td><td><code>{}</code></td>"
              "</tr>".format(e(node), e(ar), e(col)))
        a("</table>")

    a("<h3>4-2. 위험도 등급 (예측기 자체 등급)</h3>")
    if uni["levels"]:
        a("<table><tr><th class=n>점수</th><th>등급</th></tr>")
        lv = sorted(uni["levels"], key=lambda x: -x[0])
        for i, (mn, name) in enumerate(lv):
            hi = "" if i == 0 else " ~ {}".format(lv[i - 1][0] - 1)
            a("<tr><td class=n>{}{}</td><td>{}</td></tr>".format(
                mn, hi if i else " 이상", e(name)))
        a("</table>")
    a('<div class="note"><b>관제 화면의 등급과 다릅니다.</b> 위 표는 '
      '예측기가 0~{} 자로 매긴 등급이고, 관제(real_time_amhs)는 받은 점수를 '
      '<b>0~100 자</b>로 다시 봅니다 (경계 60 / 위험 71 / 초위험 85). '
      '두 등급 이름이 같아도 같은 값이 아닙니다.</div>'.format(uni["cap"] or "?"))

    a("<h3>4-3. 단계(S1/S2/S3)와 hot_area</h3>")
    a('<div class="flow">'
      "S1 = 어느 영역이든 R-A′ 또는 R-A′지속\n"
      "S2 = 어느 영역이든 R-B 또는 R-B빠름\n"
      "S3 = (R-A′ 계열) AND (R-D 또는 SLA, 또는 M16HUB 의 R-C′)\n"
      "                AND (R-B 계열 또는 흐름 '위험'·'심각')\n"
      "\n"
      "stage      = 3 if S3 else 2 if S2 else 1 if S1 else 0\n"
      "hot_area   = area_score 가 가장 큰 영역\n"
      "전파 사슬  = area_score ≥ {p} 인 영역을 시간 순으로 (최근 {lb}분)"
      "</div>".format(p=uni.get("prop_min") or "?",
                      lb=C.get("PREDICT_LOOKBACK_MIN", "?")))

    # ── 5. 새로 만들어지는 컬럼 ─────────────────────────────────────
    a("<h2>5. 예측기가 새로 만드는 컬럼</h2>")
    ef = C.get("EVENT_FIELDS")
    if isinstance(ef, list):
        a("<p><code>{{날짜}}_발동이벤트.csv</code> — 매분 1행, "
          "<b>이벤트가 없는 분도 기록</b>합니다 (없는 분을 빼면 나중에 "
          "분모를 못 셉니다). 전체 <b>{}개</b> 컬럼.</p>".format(len(ef)))
        groups = [
            ("식별", ["file", "datetime", "date", "time"]),
            ("단계", ["stage", "stage_name", "prev_stage", "transition"]),
            ("ALL 점수", ["unified_risk_score", "unified_risk_level",
                          "hot_area", "hot_score", "affected_areas",
                          "propagation_chain", "flow_signals",
                          "maxcapa_signals"]),
            ("FAB 점수", [c for c in ef if c.endswith("_score")
                          and c != "hot_score"]),
            ("FAB 신호", [c for c in ef if c.endswith("_signals")
                          and not c.startswith(("flow", "maxcapa"))]),
            ("근거 값", [c for c in ef if c.endswith(("_ra", "_rb_diff30",
                                                     "_rd_fab", "_stb_util",
                                                     "_rev_count", "_rev_lids"))]),
            ("SLA·소터", [c for c in ef if c.startswith(("sla_", "sorter_"))]),
        ]
        used = set()
        a("<table><tr><th>묶음</th><th>컬럼</th></tr>")
        for name, cols in groups:
            cols = [c for c in cols if c in ef and c not in used]
            if not cols:
                continue
            used.update(cols)
            a("<tr><td><b>{}</b></td><td>{}</td></tr>".format(
                e(name), " · ".join("<code>{}</code>".format(e(c))
                                    for c in cols)))
        rest = [c for c in ef if c not in used]
        if rest:
            a("<tr><td><b>그 밖</b></td><td>{}</td></tr>".format(
                " · ".join("<code>{}</code>".format(e(c)) for c in rest)))
        a("</table>")
        a('<div class="note"><b>{FAB}_score 가 그 FAB 의 점수입니다.</b> '
          '통합 파일에는 8영역 점수가 나란히 들어 있고, ALL 점수는 '
          '<code>unified_risk_score</code> 입니다.</div>')
    else:
        a('<div class="note miss">EVENT_FIELDS 를 읽지 못했습니다.</div>')

    # ── 6. 영역분리 ─────────────────────────────────────────────────
    a("<h2>6. 영역분리 — FAB 파일에서 <code>area_score</code> 가 되는 과정</h2>")
    a("<p>영역분리는 통합 파일을 FAB 별 파일로 나눕니다. 그 파일에서 "
      "<b>그 FAB 의 점수가 <code>area_score</code> 라는 이름</b>으로 들어갑니다 "
      "(통합 파일의 <code>{FAB}_score</code> 와 같은 값입니다).</p>")
    a('<div class="flow">'
      "통합 파일  {날짜}_발동이벤트.csv\n"
      "   unified_risk_score = 전체 점수\n"
      "   M14_score          = M14 영역 점수\n"
      "        │\n"
      "        │  영역분리\n"
      "        ↓\n"
      "FAB 파일  {날짜}_발동이벤트_M14.csv\n"
      "   unified_risk_score = 전체 점수 (그대로 실려 온다)\n"
      "   area_score         = M14 영역 점수     ← 이 FAB 의 값\n"
      "   area_level         = M14 영역 등급"
      "</div>")
    a("<h3>6-1. 관제가 받는 순간 자리를 바꾼다</h3>")
    a("<p>FAB 파일에는 <b>전체 점수와 그 FAB 점수가 같이</b> 들어 있습니다. "
      "관제가 그대로 읽으면 M14 화면이 <b>전체 점수로</b> 등급을 매기고 "
      "케이스 영역이 M16HUB 로 찍힙니다. 그래서 "
      "<code>jupyter_csv._fab_rows()</code> 가 <b>받는 순간 한 번만</b> "
      "자리를 바꿉니다.</p>")
    a('<div class="flow">'
      "받은 그대로                     →  정규화 후\n"
      "  unified_risk_score = 전체       all_score          = 전체   (원본 보존)\n"
      "  area_score         = M14        unified_risk_score = M14    ← 자리 이동\n"
      "  unified_risk_level = 전체등급   all_level          = 전체등급\n"
      "  area_level         = M14등급    unified_risk_level = M14등급\n"
      "  hot_area           = 전체기준   all_hot_area       = 전체기준\n"
      "                                  hot_area           = M14"
      "</div>")
    a('<div class="note"><b>왜 한 자리에서만 바꾸나.</b> 그래프·예보·기여도·'
      '리포트·정확도가 모두 <code>unified_risk_score</code> 와 '
      '<code>hot_area</code> 를 읽습니다. 받는 자리에서 한 번 바꿔 두면 '
      '<b>하위 모듈을 하나도 안 고치고</b> FAB 화면이 자기 데이터를 봅니다. '
      '원본은 <code>all_*</code> 로 남겨 전체와 비교할 수 있게 둡니다.</div>')

    a("<h3>6-2. 그래서 화면의 두 값은 이렇게 정리됩니다</h3>")
    a("<table><tr><th>화면</th><th>보는 값</th><th>자</th><th>뜻</th></tr>"
      "<tr><td><b>ALL</b></td><td><code>unified_risk_score</code></td>"
      "<td>0~{u}</td><td>8영역 합 + 전체 관점 가산</td></tr>"
      "<tr><td><b>FAB</b></td><td><code>area_score</code><br>"
      "<span class=dim>(정규화 뒤 <code>unified_risk_score</code> 자리)</span></td>"
      "<td>0~{a}</td><td>그 영역의 룰 배점 합</td></tr></table>".format(
          u=uni["cap"] or "?", a=cap or "?"))
    a('<div class="note miss"><b>두 값을 같은 자로 비교하지 마십시오.</b> '
      'ALL 은 0~{u}, FAB 은 0~{a} 입니다. 관제 화면은 이 둘을 각각 0~100 으로 '
      '눈금을 맞춰 등급을 매깁니다 — 자세한 것은 '
      '<code>docs/FAB별_위험도_스코어.html</code> 를 보십시오.</div>'.format(
          u=uni["cap"] or "?", a=cap or "?"))

    a('<p class="sub">이 문서는 <code>python 컬럼흐름_문서.py</code> 로 다시 '
      '만듭니다. 예측기 소스가 바뀌면 표도 같이 바뀝니다.</p>')
    a("</div></body></html>")
    return "\n".join(o)


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    out = argv[0] if argv else OUT
    d = build()
    os.makedirs(DOC_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(d))
    print("만들었습니다: {}".format(out))
    if d["ok"]:
        print("  룰 원본  : {}".format(d["path"]))
        print("  영역     : {}개 · 흐름 노드 {}개 · 출력 컬럼 {}개".format(
            len(d["extract"]),
            len(d["C"].get("FLOW_NODES") or {}),
            len(d["C"].get("EVENT_FIELDS") or [])))
    else:
        print("  ★hubroom_predictor.py 를 못 찾았습니다 — "
              "set RULE_SRC=<경로> 로 알려 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
