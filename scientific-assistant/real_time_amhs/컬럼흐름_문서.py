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


def _grade_cuts():
    """관제 쪽 등급 컷 — **화면(정책 탭)에서 정한 값**을 그대로 읽는다.

    ★코드에 60/71/85 를 적어 두면 안 된다. 사람이 화면에서 바꾸는 값이라
      문서만 옛날 값으로 남는다. 못 읽으면 '읽지 못함' 으로 둔다.
    """
    try:
        sys.path.insert(0, BASE_DIR)
        import sentinel
        from lp_client import load_config
        return sentinel.grade_cuts(load_config())
    except Exception:                                   # noqa: BLE001
        return ("?", "?", "?")


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
    """모듈 최상위 대입에서 dict/list 상수를 꺼낸다.

    ★TH_RB_10 만 예외다. 코드에서 dict 컴프리헨션으로 만든다:
        TH_RB_10 = _TD('TH_RB_10', {k: max(10, int(v*0.3)) for k,v in TH_RB_30…})
      literal 이 아니라 ast 로는 못 읽는다. 그냥 비워 두면 그림에 '—' 가
      찍혀서 '임계가 없다' 로 보인다 — 같은 규칙으로 만들어 주고 문서에
      '자동 산출' 이라고 밝힌다.
    """
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
    if "TH_RB_10" not in out and isinstance(out.get("TH_RB_30"), dict):
        m = re.search(r"TH_RB_10\s*=\s*_TD\([^)]*?int\(v\s*\*\s*([\d.]+)\)", src)
        r = float(m.group(1)) if m else 0.3
        out["TH_RB_10"] = {k: max(10, int(v * r)) for k, v in out["TH_RB_30"].items()}
        out["_TH_RB_10_derived"] = r
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


# ─────────────────────────────────────────────────────────────────────
# 출력 컬럼 설명
#
# ★131개를 하나씩 손으로 적으면 컬럼이 늘 때 빠진다. 그래서 **꼴(패턴)로**
#   적는다. 영역 이름만 갈아 끼우면 되는 것이 대부분이다.
# ★설명이 없는 컬럼이 생기면 시험이 잡는다 (test_컬럼흐름문서).
# ─────────────────────────────────────────────────────────────────────
RULE_KO = {
    "RA": "R-A′ 반송지연", "RA_sus": "R-A′ 지속", "RB": "R-B 반입급증(30분)",
    "RB_fast": "R-B 반입급증(10분)", "RC": "R-C′ 역증가·쏠림",
    "RD": "R-D 저장/가동 포화", "SLA": "SLA 4분초과",
    "SORT": "소터 대기/실패", "MAXCAPA": "MAXCAPA 축소",
}

# 정확히 이 이름인 컬럼
COL_EXACT = {
    "file": ("입력 파일 이름", "어느 원본에서 나온 행인지", "M16A_HUBROOM_PR.csv"),
    "datetime": ("그 분의 시각", "TOTAL.CSV·LLM.CSV 와 조인하는 열쇠",
                 "2026-08-26 14:07"),
    "date": ("날짜만", "일 단위로 묶을 때", "2026-08-26"),
    "time": ("시각만", "하루 안의 시간대를 볼 때", "14:07"),
    "stage": ("단계 0~3", "0 이벤트없음 · 1 조기경보 · 2 주의보 · 3 확정", "2"),
    "stage_name": ("단계 이름", "stage 를 사람 말로", "2단계 주의보"),
    "prev_stage": ("직전 분의 단계", "올라갔는지 내려갔는지 보려고", "1"),
    "transition": ("단계가 바뀐 표시", "바뀐 분에만 채워진다 (0 이면 비움)", "1→2"),
    "unified_risk_score": ("★ALL 점수 0~500",
                           "8영역 합 + 흐름·SLA·소터·MAXCAPA 가산. "
                           "관제 ALL 화면이 이 값을 본다", "137"),
    "unified_risk_level": ("ALL 등급", "예측기 자체 6단계 (관제 등급과 다르다)",
                           "주의"),
    "hot_area": ("가장 높은 영역", "area_score 가 제일 큰 영역", "M16HUB"),
    "hot_score": ("그 영역의 점수", "hot_area 의 area_score", "35"),
    "affected_areas": ("걸린 영역 목록",
                       "area_score 가 전파 기준 이상인 영역을 ';' 로", "M16HUB;M14"),
    "propagation_chain": ("전파 사슬",
                          "최근 되돌아보기 구간 안에서 영역이 걸린 순서. "
                          "어디서 시작해 어디로 번졌는지",
                          "M14(14:02,RA) → M16HUB(14:05,RA+RD)"),
    "flow_signals": ("흐름 신호",
                     "평소 대비 배수가 임계를 넘은 노드를 ';' 로",
                     "M14_TO_HUB_JOB=2.3x(위험)"),
    "maxcapa_signals": ("운영자 조치 신호",
                        "정상값보다 줄어든 MAXCAPA 컬럼", "M16HUB:3F_LFT_MAXCAPA=80(<=100)"),
    "reason": ("판정 근거 한 줄",
               "어느 영역의 어느 룰이 어떤 값으로 켜졌는지. "
               "stage 0 이면 비어 있다",
               "발동: M16HUB[R-A′(12.5분/기준9),R-D(FAB저장=31.2%,STB=99.4%)]"),
    "layer1_total": ("영역 점수 합", "8영역 area_score 를 그냥 더한 값", "62"),
    "flow_score": ("흐름 가산", "흐름 노드 등급별 가산의 합", "45"),
    "sla_score_total": ("SLA 가산", "SLA 켜진 영역 수 × 배점", "10"),
    "sorter_score_total": ("소터 가산", "소터 켜진 영역 수 × 배점", "3"),
    "mc_score_total": ("MAXCAPA 가산", "영역별 바뀐 컬럼 수 × 배점의 합", "10"),
    "M16HUB_rd_fab": ("M16HUB FAB 저장율(%)", "R-D 가 보는 값", "31.2"),
    "M16HUB_stb_util": ("M16HUB STB 3F 저장율(%)", "R-D 가 보는 또 하나", "99.4"),
    "M16HUB_rev_count": ("역증가 호기 수", "합은 줄었는데 늘어난 리프터 개수", "3"),
    "M16HUB_rev_lids": ("역증가 호기 이름", "어느 리프터인지", "6ABL0111,6ABL6012"),
    "M16HUB_rc_trend": ("리프터 합 변화",
                        "20분 전 대비 합계 증감 (음수여야 R-C′)",
                        "-14"),
    "M14_cnv_skew": ("M14 CNV 쏠림 비율", "북/남 중 큰 쪽 ÷ 합", "0.78"),
}

# {영역}_ 또는 _{영역} 꼴 — 영역 이름만 갈아 끼우면 되는 것
COL_PAT = [
    (r"^(?P<a>\w+)_score$", "{a} 영역 점수 0~{cap}",
     "그 영역의 룰 배점 합. <b>FAB 화면이 보는 값</b>이고 영역분리 뒤 "
     "area_score 가 된다", "35"),
    (r"^(?P<a>\w+)_score_raw$", "{a} 영역 점수 (자르기 전)",
     "{cap} 점에서 잘리기 전 원본. 캡에 걸렸는지 확인용", "58"),
    (r"^(?P<a>\w+)_signals$", "{a} 켜진 룰 이름",
     "'+' 로 이어 붙인다 — 어느 룰이 켜져서 그 점수가 나왔는지", "RA+RD+SLA"),
    (r"^(?P<a>\w+)_pts_(?P<r>\w+)$", "{a} · {rk} 배점",
     "이 룰 하나가 준 점수. 룰 조합을 분석하려고 따로 남긴다", "10"),
    (r"^(?P<a>\w+)_ra$", "{a} 반송/적재 시간 (분)",
     "R-A′ 가 보는 실측값 — 그 분의 값", "12.5"),
    (r"^(?P<a>\w+)_ra_count$", "{a} R-A′ 초과 횟수",
     "최근 10분 중 임계를 넘은 분의 수", "3"),
    (r"^(?P<a>\w+)_rb_diff30$", "{a} 30분 증가량",
     "허브행 대기 수가 30분 전보다 얼마나 늘었나", "118"),
    (r"^(?P<a>\w+)_rb_diff10$", "{a} 10분 증가량",
     "같은 것을 10분 창으로 — 빠르게 차오르는지", "42"),
    (r"^(?P<a>\w+)_rd_oht$", "{a} OHT 가동률 (%)",
     "M16HUB 밖의 영역에서 R-D 가 보는 값", "96.1"),
    (r"^(?P<a>\w+)_sla_cnt$", "{a} 4분 초과 건수",
     "비율이 아니라 <b>건수</b>. 10분 만에 20건 이상 늘면 SLA 가 켜진다",
     "134"),
    (r"^(?P<a>\w+)_sorter_fail$", "{a} 소터 반송 실패",
     "1건만 있어도 소터 신호가 켜진다", "2"),
    (r"^sla_(?P<a>\w+)$", "{a} 4분 초과 비율 (%)",
     "SLA 가 보는 실측값", "21.4"),
    (r"^sorter_(?P<a>\w+)$", "{a} 소터 대기 초과 수",
     "소터 룰이 보는 실측값", "412"),
]


def explain_cols(fields, cap):
    """EVENT_FIELDS 를 설명이 붙은 목록으로."""
    import re as _re
    out = []
    for c in fields:
        if c in COL_EXACT:
            t, d, ex = COL_EXACT[c]
            out.append({"col": c, "title": t, "desc": d, "ex": ex, "ok": True})
            continue
        got = None
        for pat, t, d, ex in COL_PAT:
            m = _re.match(pat, c)
            if not m:
                continue
            g = m.groupdict()
            rk = RULE_KO.get(g.get("r") or "", g.get("r") or "")
            f = dict(g, cap=cap or "?", rk=rk)
            got = {"col": c, "title": t.format(**f), "desc": d.format(**f),
                   "ex": ex, "ok": True}
            break
        out.append(got or {"col": c, "title": "", "desc": "", "ex": "",
                           "ok": False})
    return out


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


# ─────────────────────────────────────────────────────────────────────
# 왜 이런 룰인가 — 현장에서 무엇을 잡으려는 것인가
#
# ★한글 룰 이름과 뜻은 **고객 답변용 스킬 문서**에서 그대로 가져왔다
#   (m16_hub_skills/…결과해석_도메인_고객인용). 여기서 새로 지어내지
#   않는다 — 같은 것을 두 이름으로 부르면 현장에서 못 알아듣는다.
# ★'왜 그 배점인가' 는 코드에도 스킬 문서에도 없다. 모른다고 적는다.
# ─────────────────────────────────────────────────────────────────────
WHY_RULES = [
    ("R-A′", "반송지연 / 반송지연 지속",
     "반송시간이 기준보다 길어짐",
     "물량이 안 빠지고 있다는 <b>가장 이른 신호</b>입니다. 아직 쌓이기 "
     "전에도 시간부터 늘어납니다.",
     "짧게 튄 것과 진짜를 갈라야 해서 <b>지속</b>을 따로 둡니다 — 한 번 "
     "튄 값으로 알람을 울리면 사람이 알람을 꺼 버립니다. "
     "그래서 10분 중 1회(민감) 와 5분 중 여러 회(확실) 를 나눠 둡니다."),
    ("R-B", "Queue 누적 / Queue 상승",
     "대기 물량이 쌓임",
     "허브로 <b>들어오는 쪽</b>을 봅니다. 나가는 속도보다 들어오는 속도가 "
     "빠르면 결국 막힙니다.",
     "절대량이 아니라 <b>증가량</b>을 봅니다. 영역마다 평소 물량이 달라서 "
     "'몇 개 이상' 으로는 같은 자로 못 잽니다. 30분(추세)과 10분(급증)을 "
     "둘 다 보는 것은, 천천히 차오르는 것과 갑자기 몰리는 것이 다른 "
     "일이기 때문입니다."),
    ("R-C′", "리프터 정체",
     "Storage 가 꽉 차 리프터가 Carrier 를 못 내려놓고 막혀 쌓임",
     "리프터에 물건이 걸려 있는 상태입니다. 내려놓을 자리가 없으면 "
     "리프터가 들고 서 있게 됩니다.",
     "<b>합은 줄었는데 개별로 늘어난</b> 경우를 잡습니다. 전체가 늘면 "
     "그냥 물량이 많은 것이지만, 전체는 빠지는데 특정 호기만 늘면 "
     "<b>그 호기가 막힌 것</b>입니다. 합만 보면 이걸 놓칩니다."),
    ("R-D", "Storage FULL",
     "STB / FAB Storage 가 FULL",
     "받을 자리가 없다는 뜻입니다. 자리가 없으면 그 앞이 전부 밀립니다.",
     "M16HUB 는 FAB 저장율과 STB 저장율을, 다른 영역은 OHT 가동률을 "
     "봅니다 — 영역마다 '포화' 가 드러나는 자리가 다릅니다."),
    ("SLA", "4분초과 (반송지연율)",
     "4분 넘는 반송 비율이 오름",
     "<b>고객이 체감하는 지표</b>입니다. 앞의 룰들이 '왜' 라면 이건 "
     "'얼마나 아픈가' 입니다.",
     "비율과 건수를 <b>둘 다</b> 봅니다. 물량이 적을 때는 비율이 쉽게 "
     "튀고, 물량이 많을 때는 비율이 안 움직여도 건수가 확 늡니다."),
    ("소터", "분류기 대기 / 반송 실패",
     "분류기에서 대기가 쌓이거나 반송이 실패함",
     "분류기에서 막히면 그 뒤가 전부 밀립니다.",
     "반송 <b>실패</b>는 1건만 있어도 켭니다 — 실패는 '조금 느림' 이 "
     "아니라 안 된 것입니다."),
    ("MAXCAPA", "운영자 용량변경",
     "운영자가 설비 한계치를 줄임",
     "사람이 손을 댄 흔적입니다. <b>신호이자 원인</b>입니다 — 뭔가 "
     "이상해서 줄였거나, 줄여서 막히기 시작했거나.",
     "다른 룰과 달리 <b>바뀐 컬럼 수만큼 곱합니다.</b> 여러 곳을 동시에 "
     "줄였다면 그만큼 크게 손댄 것이라고 봅니다."),
]


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


# ─────────────────────────────────────────────────────────────────────
# 그림 (SVG)
#
# ★그림도 **소스에서 읽은 값**으로 그린다. 임계·배점이 바뀌면 그림의
#   숫자도 같이 바뀐다. 그림만 옛날 값으로 남으면 표보다 더 나쁘다 —
#   사람은 그림을 먼저 믿는다.
# ★바깥 그림 라이브러리를 안 쓴다. 사내망에는 CDN 이 없고, 이 문서는
#   파일 하나로 열려야 한다.
# ─────────────────────────────────────────────────────────────────────
SVG_CSS = """
.d-bg{fill:#fff;stroke:#e5e7eb}
.d-box{fill:#f8fafc;stroke:#cbd5e1;rx:6}
.d-col{fill:#fff;stroke:#cbd5e1;rx:4}
.d-rule{fill:#eef2ff;stroke:#a5b4fc;rx:6}
.d-out{fill:#ecfdf5;stroke:#6ee7b7;rx:6}
.d-sum{fill:#fff7ed;stroke:#fdba74;rx:6}
.d-cap{fill:#fef2f2;stroke:#fca5a5;rx:6}
.d-t{font:600 12px "Malgun Gothic",system-ui;fill:#111827}
.d-s{font:11px "Malgun Gothic",system-ui;fill:#4b5563}
.d-m{font:10.5px Consolas,"D2Coding",monospace;fill:#1f2937}
.d-n{font:700 12.5px system-ui;fill:#111827}
.d-h{font:700 12.5px "Malgun Gothic",system-ui;fill:#4338ca}
.d-dim{font:10.5px "Malgun Gothic",system-ui;fill:#6b7280}
.d-ln{stroke:#94a3b8;fill:none;stroke-width:1.2}
.d-ln2{stroke:#6366f1;fill:none;stroke-width:1.6}
"""


def _esc(t):
    return html.escape(str(t))


def _wrapcol(c, n=44):
    """긴 컬럼 이름을 두 줄로 — 한 줄로 두면 그림 밖으로 나간다."""
    c = str(c)
    return [c] if len(c) <= n else [c[:n], c[n:]]


def area_rules(d, area):
    """이 영역에 **실제로 붙는 룰**만 골라 준다.

    ★eval_area_rules() 의 조건을 그대로 옮긴다. 영역마다 붙는 룰이 다르다:
        R-A′  : TH_RA 에 있는 영역만        (M16 은 없다)
        R-B   : TH_RB_30 에 있는 영역만     (M16_PKT·M16_WT 는 없다)
        R-C′  : M16HUB(리프터) · M14(CNV 쏠림) 둘뿐
        R-D   : M16HUB(FAB·STB) · RD_OHT_COL 에 있는 영역(OHT)
        SLA   : SLA_COL 에 있는 영역만
        소터  : TH_SORTER_WAIT 에 있는 영역만
        MAXCAPA: MAXCAPA_NORMAL 에 그 영역 컬럼이 있는 영역만
    ★그래서 **어떤 영역은 아예 받을 수 없는 점수가 있다.** 그림마다 그
      영역이 받을 수 있는 최대 점수를 같이 적는다 — 안 적으면 "왜 M16 은
      점수가 낮냐" 를 매번 다시 설명해야 한다.
    """
    C = d["C"]
    ra_c = (C.get("RA_COL") or {}).get(area)
    rb_c = (C.get("RB_COL") or {}).get(area)
    sla_c = (C.get("SLA_COL") or {}).get(area)
    so_c = (C.get("SORTER_COL") or {}).get(area)
    sf_c = (C.get("SORTER_FAIL_COL") or {}).get(area)
    oht_c = (C.get("RD_OHT_COL") or {}).get(area)
    # ★area 뒤에 점을 붙여야 한다. 'M16' 로만 보면 M16A·M16HUB 컬럼까지
    #   딸려 온다 (실제로 그랬다).
    mc_cols = sorted(k for k in (C.get("MAXCAPA_NORMAL") or {})
                     if k.startswith(area + "."))

    def th(name, dflt="—"):
        m = C.get(name)
        if isinstance(m, dict):
            return m.get(area, dflt)
        return m if m is not None else dflt

    rows = []
    if area in (C.get("TH_RA") or {}):
        rows.append(("R-A′ 반송지연", [ra_c or "—"],
                     "≥ {} 분이 10분 중 1회+".format(th("TH_RA")), "ra_pts"))
        rows.append(("R-A′ 지속", ["(위와 같은 컬럼)"],
                     "≥ {}×{} 가 5분 중 {}회+".format(
                         th("TH_RA"), C.get("TH_RA_SUSTAINED_RATIO", "?"),
                         C.get("TH_RA_SUSTAINED_COUNT", "?")), "ra_sus_pts"))
    if area in (C.get("TH_RB_30") or {}):
        rows.append(("R-B 반입급증(30분)", [rb_c or "—"],
                     "30분 전 대비 +{} 이상".format(th("TH_RB_30")), "rb_pts"))
        rows.append(("R-B 반입급증(10분)", ["(위와 같은 컬럼)"],
                     "10분 전 대비 +{} 이상{}".format(
                         th("TH_RB_10"),
                         "  (30분 임계의 {:.0%})".format(C["_TH_RB_10_derived"])
                         if C.get("_TH_RB_10_derived") else ""), "rb_fast_pts"))
    if area == "M16HUB":
        rows.append(("R-C′ 리프터 역증가",
                     ["M16HUB.LFT.{{호기}}.TOTAL_CURRENTQCNT  ×{}대".format(
                         len(C.get("LIFTER_IDS") or []))],
                     "합은 감소 + 개별 증가 {}대 이상".format(
                         C.get("TH_RC_REVERSE", "?")), "rc_pts"))
    elif area == "M14":
        rows.append(("R-C′ CNV 쏠림",
                     ["M14.QUE.CNV.M14ATONORTHCURRENTQCNT",
                      "M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT"],
                     "북·남 중 큰 쪽 ÷ 합 ≥ 0.70", "rc_pts"))
    if area == "M16HUB":
        rows.append(("R-D 저장 포화",
                     ["M16HUB.STRATE.ALL.FABSTORAGERATIO",
                      "M16HUB.STRATE.STB.3F_STORAGE_UTIL"],
                     "FAB ≥ {}%  또는  STB ≥ {}%".format(
                         C.get("TH_RD_FABSTORAGE", "?"),
                         C.get("TH_RD_HUB_STB_UTIL", "?")), "rd_pts"))
    elif oht_c:
        rows.append(("R-D OHT 포화", [oht_c],
                     "OHT 가동률 ≥ {}%".format(C.get("TH_RD_OHT_UTIL", "?")),
                     "rd_pts"))
    if sla_c:
        rows.append(("SLA 4분초과",
                     [sla_c, sla_c.replace("OVERRATIO", "OVERCNT")],
                     "비율 ≥ {}%  또는  건수 10분 +20".format(
                         (C.get("TH_SLA_RATIO") or {}).get(area, "?")),
                     "sla_pts"))
    if area in (C.get("TH_SORTER_WAIT") or {}):
        cols = [so_c or "—"] + ([sf_c] if sf_c else [])
        rows.append(("소터 대기{}".format("/실패" if sf_c else ""), cols,
                     "대기 ≥ {}{}".format(
                         (C.get("TH_SORTER_WAIT") or {}).get(area, "?"),
                         "  또는  실패 ≥ {}".format(
                             C.get("TH_SORTER_TRANSFER_FAIL", "?")) if sf_c
                         else ""), "sort_pts"))
    if mc_cols:
        rows.append(("MAXCAPA 축소", mc_cols,
                     "정상값보다 줄어든 컬럼 1개마다", "mc_pts"))
    return rows


def svg_area(d, area="M16HUB", idx=None):
    """한 영역에서 컬럼 → 룰 → 배점 → area_score 까지."""
    C, pts = d["C"], d["pts"]
    cap = pts.get("_cap") or 50
    rows = area_rules(d, area)
    if not rows:
        return ""

    L, CX, RX = 24, 470, 790          # 컬럼 / 룰 / 배점 x
    y, o = 62, []
    a = o.append
    heights = [max(46, 20 + max(1, sum(len(_wrapcol(c)) for c in (cols or ["—"])))
                   * 15) for _, cols, _, _ in rows]
    H = y + sum(heights) + len(rows) * 6 + 178

    a('<svg viewBox="0 0 1040 {}" width="100%" role="img" '
      'aria-label="{} 영역에서 컬럼이 룰을 거쳐 area_score 가 되는 과정">'
      .format(H, _esc(area)))
    a("<style>{}</style>".format(SVG_CSS))
    a('<text x="24" y="24" class="d-h">{}{} — 어느 컬럼이 어느 룰로 들어가 '
      '점수가 되나</text>'.format(
          "그림 A-{} · ".format(idx) if idx else "", _esc(area)))
    a('<text x="24" y="44" class="d-dim">원시 컬럼 (M16A_HUBROOM_PR.CSV)</text>')
    a('<text x="{}" y="44" class="d-dim">룰 · 임계</text>'.format(CX))
    a('<text x="{}" y="44" class="d-dim">배점</text>'.format(RX))
    a('<text x="{}" y="44" class="d-dim">누적</text>'.format(RX + 110))

    run = 0
    for (name, cols, thtxt, var), h in zip(rows, heights):
        p = (pts.get(var) or {}).get("pts", 0)
        per = (pts.get(var) or {}).get("per")
        a('<rect x="{}" y="{}" width="{}" height="{}" class="d-col"/>'
          .format(L, y, CX - L - 34, h))
        ty = y + 17
        for c in (cols or ["—"]):
            for ln in _wrapcol(c):
                a('<text x="{}" y="{}" class="d-m">{}</text>'.format(
                    L + 9, ty, _esc(ln)))
                ty += 15
        a('<path d="M{} {} H{}" class="d-ln" marker-end="url(#ah)"/>'.format(
            CX - 30, y + h / 2, CX - 6))
        a('<rect x="{}" y="{}" width="{}" height="{}" class="d-rule"/>'
          .format(CX, y, RX - CX - 34, h))
        a('<text x="{}" y="{}" class="d-t">{}</text>'.format(
            CX + 10, y + 18, _esc(name)))
        a('<text x="{}" y="{}" class="d-s">{}</text>'.format(
            CX + 10, y + 34, _esc(thtxt)))
        a('<path d="M{} {} H{}" class="d-ln" marker-end="url(#ah)"/>'.format(
            RX - 30, y + h / 2, RX - 6))
        a('<rect x="{}" y="{}" width="76" height="26" class="d-out"/>'.format(
            RX, y + h / 2 - 13))
        a('<text x="{}" y="{}" class="d-n" text-anchor="middle">+{}{}</text>'
          .format(RX + 38, y + h / 2 + 5, p, " × n" if per else ""))
        run += p if not per else 0
        a('<text x="{}" y="{}" class="d-dim">{}</text>'.format(
            RX + 92, y + h / 2 + 5, "…" if per else "누적 {}".format(run)))
        y += h + 6

    has_mc = any(v == "mc_pts" for _, _, _, v in rows)
    y += 10
    a('<rect x="{}" y="{}" width="400" height="34" class="d-sum"/>'.format(CX, y))
    a('<text x="{}" y="{}" class="d-t">합계 = 최대 {}{}</text>'.format(
        CX + 12, y + 22, run,
        " + MAXCAPA {}×n".format((pts.get("mc_pts") or {}).get("pts", "?"))
        if has_mc else ""))
    y += 42
    a('<rect x="{}" y="{}" width="400" height="38" class="d-cap"/>'.format(CX, y))
    a('<text x="{}" y="{}" class="d-t">area_score = min({}, 합계)</text>'.format(
        CX + 12, y + 24, cap))
    # ★이 영역이 실제로 받을 수 있는 최대 — 안 적으면 "왜 낮냐" 를 또 묻는다
    reach = cap if has_mc else min(cap, run)
    a('<text x="{}" y="{}" class="d-dim">이 영역이 받을 수 있는 최대: '
      '<tspan class="d-n">{}</tspan>점{}</text>'.format(
          CX, y + 58, reach,
          "  (MAXCAPA 가 있어 캡까지 간다)" if has_mc
          else "  — 붙는 룰이 {}개라 {}점을 다 못 채운다".format(len(rows), cap)))
    a('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
      'markerWidth="7" markerHeight="7" orient="auto">'
      '<path d="M0 0 L10 5 L0 10 z" fill="#94a3b8"/></marker></defs>')
    a("</svg>")
    return "".join(o)


def svg_unified(d):
    """8영역 + 전체 가산 → unified_risk_score."""
    C, pts, uni, fl = d["C"], d["pts"], d["uni"], d["flow_th"]
    cap = pts.get("_cap") or 50
    areas = C.get("AREAS_ALL") or AREA_ORDER
    o = []
    a = o.append
    a('<svg viewBox="0 0 1040 470" width="100%" role="img" '
      'aria-label="8영역 점수와 전체 가산이 합쳐져 unified_risk_score 가 '
      '되는 과정">')
    a("<style>{}</style>".format(SVG_CSS))
    a('<text x="24" y="24" class="d-h">그림 B — ALL 점수 '
      'unified_risk_score 가 만들어지는 과정</text>')

    # 8영역
    a('<text x="24" y="52" class="d-dim">① 영역 점수 (각 0~{})</text>'.format(cap))
    x = 24
    for ar in areas[:8]:
        a('<rect x="{}" y="60" width="112" height="40" class="d-box"/>'.format(x))
        a('<text x="{}" y="78" class="d-t" text-anchor="middle">{}</text>'
          .format(x + 56, _esc(ar)))
        a('<text x="{}" y="93" class="d-dim" text-anchor="middle">area_score'
          '</text>'.format(x + 56))
        a('<path d="M{} 100 V126" class="d-ln"/>'.format(x + 56))
        x += 120
    a('<path d="M80 126 H{}" class="d-ln"/>'.format(24 + 7 * 120 + 56))
    a('<path d="M520 126 V150" class="d-ln2" marker-end="url(#ah2)"/>')
    a('<rect x="330" y="156" width="380" height="34" class="d-sum"/>')
    a('<text x="520" y="178" class="d-t" text-anchor="middle">'
      'layer1_total = Σ area_score  (8영역 전부)</text>')

    # 가산 4개
    a('<text x="24" y="222" class="d-dim">② 전체 관점 가산 — 영역 밖에서 '
      '한 번 더 본다</text>')
    adds = [
        ("흐름 (flow)", "{}개 노드 · 지금값 ÷ 30분평균".format(
            len(C.get("FLOW_NODES") or {})),
         "심각 ≥{}× → +{}   위험 ≥{}× → +{}   주의 ≥{}× → +{}".format(
             fl.get("심각", "?"), uni["flow"].get("심각", "?"),
             fl.get("위험", "?"), uni["flow"].get("위험", "?"),
             fl.get("주의", "?"), uni["flow"].get("주의", "?"))),
        ("SLA", "SLA 켜진 영역 수", "× {}".format(uni["sla"] or "?")),
        ("소터", "소터 켜진 영역 수", "× {}".format(uni["sorter"] or "?")),
        ("MAXCAPA", "영역별 바뀐 컬럼 수", "× {}".format(uni["mc"] or "?")),
    ]
    x = 24
    for name, what, how in adds:
        w = 300 if name.startswith("흐름") else 220
        a('<rect x="{}" y="232" width="{}" height="66" class="d-rule"/>'
          .format(x, w))
        a('<text x="{}" y="252" class="d-t">{}</text>'.format(x + 10, _esc(name)))
        a('<text x="{}" y="269" class="d-s">{}</text>'.format(x + 10, _esc(what)))
        a('<text x="{}" y="286" class="d-m">{}</text>'.format(x + 10, _esc(how)))
        a('<path d="M{} 298 V322" class="d-ln"/>'.format(x + w / 2))
        x += w + 14
    a('<path d="M174 322 H{}" class="d-ln"/>'.format(24 + 300 + 14 + 220 + 110))
    a('<path d="M520 322 V346" class="d-ln2" marker-end="url(#ah2)"/>')

    a('<rect x="250" y="352" width="540" height="38" class="d-cap"/>')
    a('<text x="520" y="376" class="d-t" text-anchor="middle">'
      'unified_risk_score = min({}, layer1_total + 흐름 + SLA + 소터 + MAXCAPA)'
      '</text>'.format(uni["cap"] or "?"))
    a('<text x="520" y="412" class="d-dim" text-anchor="middle">'
      '★SLA·소터·MAXCAPA 는 두 번 센다 — area_score 안에서 한 번(그 영역의 '
      '문제로), 여기서 또 한 번(전체로 번질 신호로).</text>')
    a('<text x="520" y="430" class="d-dim" text-anchor="middle">'
      '일부러 그렇게 둔 것이라, ALL 점수를 FAB 점수 합으로 되계산하면 '
      '맞지 않는다.</text>')
    a('<text x="520" y="452" class="d-dim" text-anchor="middle">'
      'ALL 은 0~{}, FAB 은 0~{} — 자가 다르다.</text>'.format(
          uni["cap"] or "?", cap))
    a('<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" '
      'markerWidth="8" markerHeight="8" orient="auto">'
      '<path d="M0 0 L10 5 L0 10 z" fill="#6366f1"/></marker></defs>')
    a("</svg>")
    return "".join(o)


def svg_split(d):
    """영역분리 — 자리 이동."""
    o = []
    a = o.append
    # ★높이는 줄 수에서 계산한다. 손으로 300 이라고 적어 뒀더니 마지막
    #   설명 줄이 밖으로 나가 잘렸다 (시험이 잡았다).
    a('<svg viewBox="0 0 1040 {}" width="100%" role="img" '
      'aria-label="영역분리 뒤 area_score 가 unified_risk_score 자리로 '
      '옮겨지는 과정">'.format(60 + 5 * 44 + 46))
    a("<style>{}</style>".format(SVG_CSS))
    a('<text x="24" y="24" class="d-h">그림 C — 영역분리 뒤 자리 이동 '
      '(M14 파일을 예로)</text>')
    left = [("unified_risk_score", "137", "전체 점수"),
            ("area_score", "28", "M14 점수"),
            ("unified_risk_level", "주의", "전체 등급"),
            ("area_level", "관심", "M14 등급"),
            ("hot_area", "M16HUB", "전체 기준")]
    right = [("all_score", "137", "전체 점수 (원본 보존)"),
             ("unified_risk_score", "28", "★M14 점수가 이 자리로"),
             ("all_level", "주의", "전체 등급 (원본 보존)"),
             ("unified_risk_level", "관심", "★M14 등급"),
             ("hot_area", "M14", "★자기 영역으로")]
    a('<text x="24" y="52" class="d-dim">받은 그대로 — FAB 파일</text>')
    a('<text x="580" y="52" class="d-dim">관제가 읽는 순간 정규화 '
      '(jupyter_csv._fab_rows)</text>')
    y = 60
    for (lc, lv, ln), (rc, rv, rn) in zip(left, right):
        star = rn.startswith("★")
        a('<rect x="24" y="{}" width="440" height="36" class="d-col"/>'.format(y))
        a('<text x="34" y="{}" class="d-m">{}</text>'.format(y + 16, _esc(lc)))
        a('<text x="34" y="{}" class="d-dim">{}</text>'.format(y + 30, _esc(ln)))
        a('<text x="452" y="{}" class="d-n" text-anchor="end">{}</text>'.format(
            y + 23, _esc(lv)))
        a('<path d="M474 {} H566" class="d-ln{}" marker-end="url(#ah3)"/>'
          .format(y + 18, "2" if star else ""))
        a('<rect x="580" y="{}" width="440" height="36" class="{}"/>'.format(
            y, "d-out" if star else "d-col"))
        a('<text x="590" y="{}" class="d-m">{}</text>'.format(y + 16, _esc(rc)))
        a('<text x="590" y="{}" class="d-dim">{}</text>'.format(y + 30, _esc(rn)))
        a('<text x="1008" y="{}" class="d-n" text-anchor="end">{}</text>'.format(
            y + 23, _esc(rv)))
        y += 44
    a('<text x="24" y="{}" class="d-dim">한 자리에서 한 번만 바꾼다. '
      '그래프·예보·기여도·리포트·정확도가 모두 unified_risk_score 와 '
      'hot_area 를 읽으므로, 여기서 바꿔 두면 하위 모듈을 하나도 안 고치고 '
      'FAB 화면이 자기 데이터를 본다.</text>'.format(y + 18))
    a('<defs><marker id="ah3" viewBox="0 0 10 10" refX="9" refY="5" '
      'markerWidth="7" markerHeight="7" orient="auto">'
      '<path d="M0 0 L10 5 L0 10 z" fill="#6366f1"/></marker></defs>')
    a("</svg>")
    return "".join(o)


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
.fig{border:1px solid var(--line);border-radius:10px;padding:10px 12px;
 margin:14px 0;background:#fff;overflow-x:auto}
.fig svg{display:block;min-width:760px}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;
 background:var(--bg);border:1px solid var(--line);color:var(--dim)}
.big{font-size:19px;font-weight:800}
ol.steps{padding-left:20px} ol.steps>li{margin:8px 0}
@media print{.wrap{max-width:none;padding:0} h2{page-break-after:avoid}}
"""


def render(d):
    C, pts, uni, fl = d["C"], d["pts"], d["uni"], d["flow_th"]
    cap = pts.get("_cap") or 50
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
      "8종을 각각 판정하고, <b>켜진 룰의 배점을 더합니다.</b> 아래 그림이 "
      "<b>어느 컬럼이 어느 룰로 들어가는지</b> 그대로 보여 줍니다 — "
      "룰을 다 가진 M16HUB 를 예로 들었습니다.</p>")
    a("<h3>3-0. 왜 이런 룰인가 — 무엇을 잡으려는 것인가</h3>")
    a("<p>룰 이름과 뜻은 <b>고객 답변용 스킬 문서</b>에서 그대로 가져왔습니다 "
      "(<code>m16_hub_skills/</code>). 같은 것을 두 이름으로 부르면 현장에서 "
      "못 알아듣습니다.</p>")
    a("<table><tr><th>룰</th><th>현장 이름</th><th>무엇을 잡나</th>"
      "<th>왜 이렇게 봤나</th></tr>")
    for code, ko, mean, what, why in WHY_RULES:
        a("<tr><td><b>{}</b></td><td><b>{}</b><br>"
          '<span class="dim">{}</span></td><td>{}</td><td>{}</td></tr>'
          .format(e(code), e(ko), e(mean), what, why))
    a("</table>")
    a('<div class="note">읽는 순서가 있습니다 — '
      '<b>R-A′(시간이 는다) → R-B(물량이 쌓인다) → R-C′·R-D(자리가 없다) '
      '→ SLA(고객이 아프다).</b> 단계 판정 S3 이 이 셋을 모두 요구하는 것도 '
      '같은 까닭입니다 (4-3): 시간도 늘고, 자리도 없고, 물량도 몰릴 때가 '
      '진짜 막히는 때입니다.</div>')

    a("<h3>3-0-1. 배점</h3>")
    a(points_table(pts))
    a('<div class="note"><b>배점의 근거는 코드에 적혀 있지 않습니다.</b> '
      '왜 R-A′ 가 10점이고 소터가 3점인지는 예측기 소스에 이유가 없습니다 — '
      '룰을 만든 쪽에 확인해서 이 문서에 채워야 합니다. 지금은 '
      '<b>값만</b> 옮겨 적었습니다.</div>')

    a("<h3>3-1. 영역마다 붙는 룰이 다릅니다</h3>")
    a("<p>모든 영역이 룰 8종을 다 갖지는 않습니다. <b>그 영역에서 읽을 수 "
      "있는 컬럼이 있어야</b> 룰이 붙습니다. 그래서 <b>영역마다 받을 수 있는 "
      "최대 점수가 다릅니다</b> — 점수를 영역끼리 그대로 비교하면 안 되는 "
      "까닭입니다.</p>")
    rule_cols = [("R-A′", "TH_RA"), ("R-B", "TH_RB_30"), ("R-C′", None),
                 ("R-D", None), ("SLA", "SLA_COL"),
                 ("소터", "TH_SORTER_WAIT"), ("MAXCAPA", None)]
    a("<table><tr><th>영역</th>"
      + "".join("<th class=n>{}</th>".format(e(n)) for n, _ in rule_cols)
      + "<th class=n>붙는 룰</th><th class=n>최대 점수</th></tr>")
    for ar in (C.get("AREAS_ALL") or AREA_ORDER):
        rr = area_rules(d, ar)
        names = [x[0] for x in rr]
        has = {
            "R-A′": any(n.startswith("R-A") for n in names),
            "R-B": any(n.startswith("R-B") for n in names),
            "R-C′": any(n.startswith("R-C") for n in names),
            "R-D": any(n.startswith("R-D") for n in names),
            "SLA": any(n.startswith("SLA") for n in names),
            "소터": any(n.startswith("소터") for n in names),
            "MAXCAPA": any(n.startswith("MAXCAPA") for n in names),
        }
        run = sum((pts.get(v) or {}).get("pts", 0) for _, _, _, v in rr
                  if v != "mc_pts")
        reach = cap if has["MAXCAPA"] else min(cap, run)
        a("<tr><td><b>{}</b></td>".format(e(ar))
          + "".join('<td class="n">{}</td>'.format("O" if has[n] else "·")
                    for n, _ in rule_cols)
          + '<td class="n">{}</td><td class="n"><b>{}</b></td></tr>'.format(
              len(rr), reach))
    a("</table>")
    a('<div class="note miss"><b>M16 · M16_PKT · M16_WT 를 보십시오.</b> '
      'M16 은 R-B 만, M16_PKT·M16_WT 는 R-A′ 만 붙습니다. '
      'M16_PKT·M16_WT 는 OHT 가동률(<code>rd_oht</code>)을 <b>읽기는 하는데</b> '
      'R-D 판정 대상(<code>RD_OHT_COL</code>)에 없어서 그 값이 점수로 가지 '
      '않습니다. 의도한 것인지 예측기 쪽에 확인이 필요합니다.</div>')

    a("<h3>3-2. 영역별 그림 — 어느 컬럼이 어느 룰로 들어가나</h3>")
    for i, ar in enumerate(C.get("AREAS_ALL") or AREA_ORDER, 1):
        g = svg_area(d, ar, i)
        if not g:
            continue
        a('<div class="fig">{}</div>'.format(g))
    a('<div class="flow">'
      "area_score = RA + RA_sus + RB + RB_fast + RC + RD + SLA + SORT + MAXCAPA×n\n"
      "area_score = min({cap}, 위 합)        ← {cap} 점에서 자른다\n\n"
      "· 자르기 전 원본은 area_score_raw 로 같이 남긴다\n"
      "· 룰별 분해 점수는 pts_RA · pts_RB … 로 각각 남긴다 (조합 분석용)"
      "</div>".format(cap=cap or "?"))
    a('<div class="note"><b>왜 {}점에서 자르나.</b> MAXCAPA 는 바뀐 컬럼 '
      '수만큼 곱해지므로 한 영역이 무한정 커질 수 있습니다. 한 영역이 전체를 '
      '삼키지 않게 상한을 둡니다.</div>'.format(cap or "?"))
    a("<h3>3-3. 판정에 창(window)이 왜 필요한가</h3>")
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
    a('<div class="fig">{}</div>'.format(svg_unified(d)))
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
      '예측기가 0~{} 자로 매긴 등급입니다. 관제(real_time_amhs)는 받은 점수를 '
      '<b>0~100 자</b>로 다시 보고, <b>등급 경계는 실시간 관제 화면에서 '
      '설정합니다</b> — 코드에 박힌 값이 아닙니다.</div>'.format(
          uni["cap"] or "?"))
    a("<h4>관제 쪽 등급은 화면에서 정한다</h4>")
    a("<table><tr><th>어디서</th><th>무엇을</th><th>어떻게 읽히나</th></tr>"
      "<tr><td>관제 화면 <b>정책</b> 탭</td>"
      "<td>경계 · 위험 · 초위험 시작점</td>"
      "<td><code>config.grade.bands</code> 에 저장 → "
      "<code>sentinel.grade_cuts()</code></td></tr>"
      "<tr><td>같은 화면, <b>시스템별</b></td>"
      "<td>ALL · FAB 다섯을 각각 다르게</td>"
      "<td><code>config.grade.by_sys[시스템]</code> 이 위를 덮는다</td></tr>"
      "</table>")
    a('<p class="dim">지금 설정된 값은 <b>경계 {} / 위험 {} / 초위험 {}</b> '
      '입니다 (이 문서를 만든 시점). FAB 마다 점수 분포가 달라 시스템별로 '
      '다르게 둘 수 있으므로, <b>고객에게 낼 때는 그 시점의 설정값을 같이 '
      '적어야 합니다</b> — 나중에 바꾸면 예전 알람의 등급을 설명할 수 없게 '
      '됩니다.</p>'.format(*_grade_cuts()))

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
    a("<h2>5. 예측기가 새로 만드는 컬럼 — 하나씩</h2>")
    ef = C.get("EVENT_FIELDS")
    if not isinstance(ef, list):
        a('<div class="note miss">EVENT_FIELDS 를 읽지 못했습니다.</div>')
    else:
        a("<p><code>{{날짜}}_발동이벤트.csv</code> — 매분 1행, "
          "<b>이벤트가 없는 분도 기록</b>합니다 (없는 분을 빼면 나중에 "
          "분모를 못 셉니다). 전체 <b>{}개</b> 컬럼을 묶음별로 "
          "하나씩 적었습니다.</p>".format(len(ef)))
        cols = explain_cols(ef, cap)
        by = {c["col"]: c for c in cols}

        def area_of(name):
            for ar in sorted(AREA_ORDER, key=len, reverse=True):
                if name.startswith(ar + "_") or name.endswith("_" + ar):
                    return ar
            return ""

        groups = [
            ("① 식별 — 언제·어디서 나온 행인가",
             ["file", "datetime", "date", "time"], None),
            ("② 단계 — 지금 몇 단계인가",
             ["stage", "stage_name", "prev_stage", "transition"],
             "단계는 S1/S2/S3 판정 결과입니다 (4-3 참조). "
             "<code>transition</code> 은 <b>바뀐 분에만</b> 채워지므로, "
             "'언제 올라갔나' 를 셀 때 이 컬럼만 보면 됩니다."),
            ("③ ALL 점수와 그 근거",
             ["unified_risk_score", "unified_risk_level", "hot_area",
              "hot_score", "affected_areas", "propagation_chain",
              "flow_signals", "maxcapa_signals", "reason"],
             "<b>관제 ALL 화면이 보는 값이 <code>unified_risk_score</code></b> "
             "입니다. <code>reason</code> 한 줄에 어느 영역의 어느 룰이 어떤 "
             "값으로 켜졌는지가 다 들어 있어, 사람이 읽는 첫 컬럼입니다."),
            ("④ ALL 점수 분해 — 무엇이 얼마를 보탰나",
             ["layer1_total", "flow_score", "sla_score_total",
              "sorter_score_total", "mc_score_total"],
             "이 다섯을 더하면 <code>unified_risk_score</code> 가 됩니다 "
             "(캡 전). <b>점수가 왜 그렇게 나왔는지</b> 를 따질 때 여기부터 "
             "봅니다."),
            ("⑤ FAB 점수 — 영역분리 뒤 area_score 가 되는 값",
             [c for c in ef if c.endswith("_score") and c != "hot_score"],
             "<b>관제 FAB 화면이 보는 값</b>입니다. 영역분리에서 그 FAB 의 "
             "것만 <code>area_score</code> 로 나갑니다 (6장)."),
            ("⑥ FAB 점수 원본 — 자르기 전",
             [c for c in ef if c.endswith("_score_raw")],
             "{} 점 캡에 걸렸는지 확인용입니다. "
             "<code>_score_raw</code> 가 <code>_score</code> 보다 크면 "
             "잘린 것입니다.".format(cap)),
            ("⑦ 켜진 룰 이름",
             [c for c in ef if c.endswith("_signals")
              and not c.startswith(("flow", "maxcapa"))],
             "'+' 로 이어 붙입니다. 점수만 보면 <b>왜</b> 가 없으므로 "
             "이 컬럼을 같이 봅니다."),
            ("⑧ 룰별 분해 점수 (5영역 × 9룰)",
             [c for c in ef if "_pts_" in c],
             "룰 하나가 준 점수를 따로 남깁니다. <b>어떤 룰 조합이 실제 "
             "사건과 이어졌나</b> 를 뒤에서 분석하려고 둔 자리입니다 "
             "— 성능을 룰 단위로 볼 수 있습니다."),
            ("⑨ 룰이 본 실측값 — R-A′",
             [c for c in ef if c.endswith("_ra") or c.endswith("_ra_count")],
             "임계와 나란히 놓고 봐야 '왜 켜졌나/왜 안 켜졌나' 를 말할 수 "
             "있습니다."),
            ("⑩ 룰이 본 실측값 — R-B",
             [c for c in ef if "_rb_diff" in c], None),
            ("⑪ 룰이 본 실측값 — R-C′ · R-D",
             [c for c in ef if c in ("M16HUB_rd_fab", "M16HUB_stb_util",
                                     "M16HUB_rev_count", "M16HUB_rev_lids",
                                     "M16HUB_rc_trend", "M14_cnv_skew")
              or c.endswith("_rd_oht")],
             "R-C′ 는 <b>합은 줄었는데 개별은 늘어난</b> 경우를 잡습니다 — "
             "그래서 <code>rc_trend</code>(합 변화)와 "
             "<code>rev_count</code>(늘어난 호기 수)를 같이 남깁니다."),
            ("⑫ 룰이 본 실측값 — SLA · 소터",
             [c for c in ef if c.startswith(("sla_", "sorter_"))
              or c.endswith(("_sla_cnt", "_sorter_fail"))],
             "SLA 는 <b>비율</b>과 <b>건수</b> 둘 다 봅니다. 비율이 낮아도 "
             "건수가 10분 만에 20건 이상 늘면 켜집니다."),
        ]
        used = set()
        for title, names, note in groups:
            names = [n for n in names if n in by and n not in used]
            if not names:
                continue
            used.update(names)
            a("<h3>{} <span class=tag>{}개</span></h3>".format(
                e(title), len(names)))
            if note:
                a('<p class="dim">{}</p>'.format(note))
            # ★같은 꼴이 반복되면 묶는다. 영역만 다른 설명을 8번 되풀이하면
            #   사람이 안 읽는다 — 꼴 하나와 '해당 영역' 목록이 낫다.
            shapes = {(area_of(n) and n.replace(area_of(n), "{영역}")) or n
                      for n in names}
            if len(shapes) < len(names):
                a('<table><tr><th>컬럼 꼴</th><th>뜻</th><th>예</th></tr>')
                seen_shape = set()
                for n in names:
                    ar = area_of(n)
                    shape = n.replace(ar, "{영역}") if ar else n
                    if shape in seen_shape:
                        continue
                    seen_shape.add(shape)
                    c = by[n]
                    a("<tr><td><code>{}</code></td><td><b>{}</b><br>"
                      '<span class="dim">{}</span></td>'
                      '<td class="mono">{}</td></tr>'.format(
                          e(shape),
                          e(c["title"].replace(ar, "{영역}") if ar else c["title"]),
                          c["desc"], e(c["ex"])))
                a("</table>")
                a('<p class="dim">해당 영역: {}</p>'.format(
                    " · ".join("<code>{}</code>".format(e(x)) for x in
                               sorted({area_of(n) for n in names if area_of(n)},
                                      key=AREA_ORDER.index))))
            else:
                a('<table><tr><th>컬럼</th><th>뜻</th><th>설명</th>'
                  '<th>예</th></tr>')
                for n in names:
                    c = by[n]
                    a("<tr><td><code>{}</code></td><td><b>{}</b></td>"
                      "<td>{}</td><td class=mono>{}</td></tr>".format(
                          e(n), e(c["title"]), c["desc"], e(c["ex"])))
                a("</table>")
        rest = [c for c in ef if c not in used]
        if rest:
            a("<h3>그 밖 <span class=tag>{}개</span></h3>".format(len(rest)))
            a("<table><tr><th>컬럼</th><th>뜻</th></tr>")
            for n in rest:
                c = by[n]
                a("<tr><td><code>{}</code></td><td>{}</td></tr>".format(
                    e(n), e(c["title"]) or '<span class=dim>설명 없음</span>'))
            a("</table>")
        miss = [c["col"] for c in cols if not c["ok"]]
        if miss:
            a('<div class="note miss"><b>설명이 없는 컬럼 {}개</b>: {}<br>'
              '컬럼흐름_문서.py 의 <code>COL_EXACT</code>/<code>COL_PAT</code> '
              '에 적어 주십시오.</div>'.format(
                  len(miss), " · ".join("<code>{}</code>".format(e(m))
                                        for m in miss[:20])))

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
    a('<div class="fig">{}</div>'.format(svg_split(d)))
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


# ─────────────────────────────────────────────────────────────────────
# MCP 위키에 넣을 MD
#
# ★왜 여러 장으로 쪼개나. 위키 검색(BM25)은 **초점이 좁은 페이지**에서
#   잘 맞는다. 한 장에 다 넣으면 "M14 는 어느 컬럼 봐?" 에 그 큰 문서가
#   통째로 걸려 아바타가 필요 없는 데까지 읽는다.
# ★tags 가 중요하다. 아바타는 wikiWords(제목·태그)로 '이 질문에 위키를
#   뒤질까' 를 정한다 — 태그에 없는 말로 물으면 아예 안 뒤진다. 그래서
#   사람이 실제로 칠 말(M14 · area_score · 반송지연 · 리프터 정체…)을
#   전부 넣는다.
# ★summary 는 페이지마다 다르게 쓴다. 한 번에 여러 개를 올리면 화면의
#   '설명' 칸은 전부 같은 값이 붙는데, md 가 자기 summary 를 갖고 있으면
#   그걸 쓴다 (app.md_desc).
# ─────────────────────────────────────────────────────────────────────
WIKI_DOMAIN = "관제"

# 현장 이름 ↔ 코드 — 태그에 둘 다 넣는다. 사람은 한글로 묻고 코드는
# 영문으로 적혀 있다.
# ★붙여 쓴 말과 띄어 쓴 말을 **둘 다** 넣는다. 태그를 '리프터정체' 로만
#   두면 "리프터 정체가 뭐야?" 라고 물었을 때 아예 안 걸린다 (실제로
#   시험에서 놓쳤다). 낱말 관문은 글자 그대로 견주기 때문이다.
RULE_TAGS = ["반송지연", "Queue누적", "Queue 누적", "리프터정체", "리프터 정체",
             "리프터", "StorageFULL", "Storage FULL", "저장포화",
             "4분초과", "4분 초과", "운영자용량변경", "용량변경", "소터", "분류기",
             "RA", "RB", "RC", "RD", "SLA", "SORT", "MAXCAPA"]


def _fm(title, summary, tags, ptype="concept"):
    # ★겹치는 태그를 지운다 (M16 은 밑줄을 떼도 M16 이라 두 번 들어간다).
    #   순서는 지킨다 — 앞쪽이 그 페이지를 가장 잘 나타내는 말이다.
    seen, uniq = set(), []
    for t in tags:
        t = str(t).strip()
        if t and t not in seen:
            seen.add(t)
            uniq.append(t)
    tags = uniq
    return ("---\n"
            "title: {}\n"
            "type: {}\n"
            "domain: {}\n"
            "tags: [{}]\n"
            "summary: {}\n"
            "sources: []\n"
            "author: \n"
            "updated: \n"
            "---\n\n".format(title, ptype, WIKI_DOMAIN,
                             ", ".join(tags), summary))


def _md_table(head, rows):
    o = ["| " + " | ".join(head) + " |",
         "|" + "|".join(["---"] * len(head)) + "|"]
    for r in rows:
        o.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(o)


def wiki_pages(d):
    """위키에 올릴 MD 여러 장 — [(파일이름, 글), …]"""
    C, pts, uni, fl = d["C"], d["pts"], d["uni"], d["flow_th"]
    cap = pts.get("_cap") or 50
    ucap = uni.get("cap") or 500
    areas = C.get("AREAS_ALL") or AREA_ORDER
    ver = d["version"] or "룰베이스 예측기"
    w, dg, cr = _grade_cuts()
    out = []

    # ── 00 개요 ──────────────────────────────────────────────────────
    b = [_fm("관제 점수 개요 — ALL 과 FAB 은 다른 자다",
             "관제가 보는 두 점수. ALL 은 unified_risk_score(0~{}), FAB 은 "
             "area_score(0~{}). 자가 달라서 그대로 비교하면 안 된다."
             .format(ucap, cap),
             ["관제", "점수", "unified_risk_score", "area_score", "ALL", "FAB",
              "위험도", "스코어", "판단기준"])]
    b.append("## 관제는 무엇을 보고 판단하나\n")
    b.append(_md_table(["대상", "보는 값", "자", "무엇인가"], [
        ["**ALL**", "`unified_risk_score`", "0~{}".format(ucap),
         "8영역 점수 합 + 전체 관점 가산"],
        ["**FAB**", "`area_score`", "0~{}".format(cap),
         "그 영역의 룰 배점 합"],
    ]))
    b.append("\n> ★**두 값을 같은 자로 비교하면 안 된다.** ALL 이 137 이고 "
             "M14 가 28 이라고 해서 ALL 이 다섯 배 나쁜 것이 아니다. "
             "재는 대상과 눈금이 다르다.\n")
    b.append("\n## 점수는 어디서 오나\n")
    b.append("```\n"
             "룰베이스 예측기 ({ver})\n"
             "   │  M16A_HUBROOM_PR.CSV (원시 265 컬럼) 를 읽어\n"
             "   │  8영역 룰로 점수를 만든다\n"
             "   ↓  {{날짜}}_발동이벤트.csv\n"
             "관제 (real_time_amhs)\n"
             "   │  읽고 · 재현 검산하고 · 등급 매기고 · LLM 이 판단하고\n"
             "   ↓  사후에 채점한다\n"
             "```\n".format(ver=ver))
    b.append("\n**관제는 룰을 만들지 않는다.** 룰은 예측기가 만들고, 관제는 "
             "받아서 읽는다. 룰 개정 이력·룰 제작 데이터 기간을 물으면 "
             "예측기 쪽 소관이다.\n")
    b.append("\n## 등급\n")
    b.append("등급 경계는 **실시간 관제 화면(정책 탭)에서 정한다.** "
             "코드에 박힌 값이 아니다. 시스템별로 다르게 둘 수도 있다.\n")
    b.append("\n" + _md_table(["등급", "점수", "처리"], [
        ["정상", "0 ~ {}".format(w - 1) if isinstance(w, int) else "—", "알람 없음"],
        ["경계", "{} ~ {}".format(w, dg - 1) if isinstance(w, int) else "—", "확인 필요"],
        ["위험", "{} ~ {}".format(dg, cr - 1) if isinstance(dg, int) else "—", "모니터링"],
        ["초위험", "{} ~ 100".format(cr), "조치"],
    ]) + "\n")
    b.append("\n> 위 값은 이 문서를 만든 시점의 설정이다. 화면에서 바꾸면 "
             "달라진다.\n")
    out.append(("00_관제-점수-개요.md", "".join(b)))

    # ── 01 ALL ──────────────────────────────────────────────────────
    b = [_fm("ALL 점수 unified_risk_score 계산 방법",
             "8영역 area_score 합에 흐름·SLA·소터·MAXCAPA 가산을 더해 "
             "min({}) 로 자른다. SLA·소터·MAXCAPA 는 두 번 세므로 FAB 합과 "
             "안 맞는다.".format(ucap),
             ["unified_risk_score", "ALL", "전체점수", "융합", "layer1_total",
              "flow_score", "흐름", "위험도등급"])]
    b.append("## 계산\n\n```\n"
             "layer1_total = Σ area_score            (8영역 전부)\n"
             "flow_score   = 흐름 노드마다  심각 +{s} / 위험 +{dd} / 주의 +{ww}\n"
             "sla_score    = SLA 켜진 영역 수 × {sla}\n"
             "sorter_score = 소터 켜진 영역 수 × {so}\n"
             "mc_score     = Σ (영역별 MAXCAPA 바뀐 컬럼 수 × {mc})\n\n"
             "unified_risk_score = min({cap}, 위 다섯의 합)\n```\n".format(
                 s=uni["flow"].get("심각", "?"), dd=uni["flow"].get("위험", "?"),
                 ww=uni["flow"].get("주의", "?"), sla=uni["sla"], so=uni["sorter"],
                 mc=uni["mc"], cap=ucap))
    b.append("\n> ★**SLA·소터·MAXCAPA 는 두 번 센다.** area_score 안에서 한 번"
             "(그 영역의 문제로), 융합에서 또 한 번(전체로 번질 신호로). "
             "일부러 그렇게 둔 것이라, **ALL 점수를 FAB 점수 합으로 되계산하면 "
             "맞지 않는다.**\n")
    b.append("\n## 흐름 룰\n\n노드마다 **지금 값 ÷ 최근 {}분 평균** 배수를 "
             "본다. 절대값이 아니라 평소 대비라, 노드마다 크기가 달라도 같은 "
             "자로 잰다.\n\n".format(fl.get("_avg", "?")))
    b.append(_md_table(["배수", "등급", "가산"],
                       [["≥ {}×".format(fl.get(lv, "?")), lv,
                         "+{}".format(uni["flow"].get(lv, "?"))]
                        for lv in ("심각", "위험", "주의")]) + "\n")
    if isinstance(C.get("FLOW_NODES"), dict):
        b.append("\n### 흐름 노드 {}개\n\n".format(len(C["FLOW_NODES"])))
        b.append(_md_table(["노드", "영역", "컬럼"], [
            [k, (v[0] if isinstance(v, (list, tuple)) else ""),
             "`{}`".format(v[1] if isinstance(v, (list, tuple)) else v)]
            for k, v in C["FLOW_NODES"].items()]) + "\n")
    b.append("\n## 예측기 자체 등급 (관제 등급과 다르다)\n\n")
    if uni["levels"]:
        lv = sorted(uni["levels"], key=lambda x: -x[0])
        b.append(_md_table(["점수", "등급"], [
            ["{} 이상".format(mn) if i == 0 else "{} ~ {}".format(mn, lv[i-1][0]-1),
             nm] for i, (mn, nm) in enumerate(lv)]) + "\n")
    b.append("\n> 이름이 같아도 관제 등급과 **다른 값**이다. 예측기는 0~{} "
             "자, 관제는 0~100 자다.\n".format(ucap))
    out.append(("01_ALL-점수-unified_risk_score.md", "".join(b)))

    # ── 02 FAB ──────────────────────────────────────────────────────
    b = [_fm("FAB 점수 area_score 계산 방법",
             "룰 8종의 배점을 더해 min({}) 로 자른다. 영역마다 붙는 룰이 "
             "달라서 받을 수 있는 최대 점수가 다르다.".format(cap),
             ["area_score", "FAB", "영역점수", "배점", "룰", "min50",
              "area_score_raw", "캡"])]
    b.append("## 배점\n\n")
    rows = [("R-A′ 반송지연", "ra_pts"), ("R-A′ 지속", "ra_sus_pts"),
            ("R-B 반입급증(30분)", "rb_pts"), ("R-B 반입급증(10분)", "rb_fast_pts"),
            ("R-C′ 역증가·쏠림", "rc_pts"), ("R-D 저장/가동 포화", "rd_pts"),
            ("SLA 4분초과", "sla_pts"), ("소터 대기/실패", "sort_pts")]
    b.append(_md_table(["룰", "배점"],
                       [[n, "+{}".format((pts.get(v) or {}).get("pts", "?"))]
                        for n, v in rows]
                       + [["MAXCAPA 축소",
                           "+{} × 바뀐 컬럼 수".format(
                               (pts.get("mc_pts") or {}).get("pts", "?"))]]) + "\n")
    b.append("\n```\narea_score = min({}, 켜진 룰 배점의 합)\n```\n".format(cap))
    b.append("\n자르기 전 값은 `{{영역}}_score_raw` 로 따로 남는다 — "
             "캡에 걸렸는지 확인용이다.\n")
    b.append("\n> 배점의 근거(왜 R-A′ 가 {} 점인가)는 예측기 소스에 적혀 있지 "
             "않다. 룰을 만든 쪽에 확인이 필요하다.\n".format(
                 (pts.get("ra_pts") or {}).get("pts", "?")))
    b.append("\n## 영역마다 붙는 룰이 다르다\n\n")
    rr_rows = []
    for ar in areas:
        rr = area_rules(d, ar)
        names = [x[0] for x in rr]
        has = lambda pre: "O" if any(n.startswith(pre) for n in names) else "·"
        run = sum((pts.get(v) or {}).get("pts", 0) for _, _, _, v in rr
                  if v != "mc_pts")
        mc = any(v == "mc_pts" for _, _, _, v in rr)
        rr_rows.append([ar, has("R-A"), has("R-B"), has("R-C"), has("R-D"),
                        has("SLA"), has("소터"), "O" if mc else "·",
                        "**{}**".format(cap if mc else min(cap, run))])
    b.append(_md_table(["영역", "R-A′", "R-B", "R-C′", "R-D", "SLA", "소터",
                        "MAXCAPA", "최대 점수"], rr_rows) + "\n")
    b.append("\n> **M16 은 R-B 만, M16_PKT·M16_WT 는 R-A′ 만 붙는다.** "
             "그래서 최대 15 점이다. 점수가 낮다고 그 영역이 안전한 것이 "
             "아니라, 그 영역에서 볼 수 있는 컬럼이 적은 것이다.\n")
    b.append("\n> M16_PKT·M16_WT 는 OHT 가동률을 **읽기는 하는데** R-D 판정 "
             "대상이 아니어서 그 값이 점수로 가지 않는다. 의도한 것인지 "
             "예측기 쪽 확인이 필요하다.\n")
    out.append(("02_FAB-점수-area_score.md", "".join(b)))

    # ── 03 룰 설명 ──────────────────────────────────────────────────
    b = [_fm("관제 룰 8종 — 무엇을 잡고 왜 그렇게 보나",
             "R-A′ 반송지연 · R-B Queue 누적 · R-C′ 리프터 정체 · "
             "R-D Storage FULL · SLA 4분초과 · 소터 · MAXCAPA. "
             "현장 이름과 코드 이름을 같이 적는다.",
             RULE_TAGS + ["룰", "판정", "임계", "R-A", "R-B", "R-C", "R-D"])]
    b.append("## 답변할 때는 한글 이름을 쓴다\n\n")
    b.append(_md_table(["코드", "현장 이름", "뜻"],
                       [[c, ko, mean] for c, ko, mean, _, _ in WHY_RULES]) + "\n")
    b.append("\n> '역증가'·'역류' 라는 말은 쓰지 않는다. **리프터 정체**, "
             "**Queue 밀림** 으로 말한다.\n")
    b.append("\n## 무엇을 잡나 · 왜 그렇게 봤나\n")
    import re as _re
    for code, ko, mean, what, why in WHY_RULES:
        strip = lambda t: _re.sub(r"<[^>]+>", "", t)
        b.append("\n### {} — {}\n\n".format(code, ko))
        b.append("- **무엇을 잡나**: {}\n".format(strip(what)))
        b.append("- **왜 그렇게 봤나**: {}\n".format(strip(why)))
    b.append("\n## 읽는 순서\n\n"
             "**시간이 는다(R-A′) → 물량이 쌓인다(R-B) → 자리가 없다"
             "(R-C′·R-D) → 고객이 아프다(SLA).**\n\n"
             "단계 판정 S3 가 이 셋을 모두 요구하는 것도 같은 까닭이다. "
             "시간도 늘고, 자리도 없고, 물량도 몰릴 때가 진짜 막히는 때다.\n")
    out.append(("03_관제-룰-8종.md", "".join(b)))

    # ── 04 영역별 ───────────────────────────────────────────────────
    for i, ar in enumerate(areas, 1):
        rr = area_rules(d, ar)
        if not rr:
            continue
        run = sum((pts.get(v) or {}).get("pts", 0) for _, _, _, v in rr
                  if v != "mc_pts")
        mc = any(v == "mc_pts" for _, _, _, v in rr)
        reach = cap if mc else min(cap, run)
        # ★이 영역에 **실제로 붙는 룰**만 태그로 단다. 없는 룰을 달면
        #   "리프터 정체" 를 물었을 때 리프터가 없는 M16 페이지까지 딸려 온다.
        mine = []
        for n, _c, _t, _v in rr:
            for code, ko, _m, _w, _y in WHY_RULES:
                if n.startswith(code) or (code == "소터" and n.startswith("소터")):
                    mine += [ko.split(" / ")[0], code]
                    for extra in RULE_TAGS:
                        if extra.replace(" ", "") in ko.replace(" ", ""):
                            mine.append(extra)
        b = [_fm("{} 영역이 보는 컬럼과 임계".format(ar),
                 "{} 는 룰 {}종이 붙고 최대 {}점까지 간다. 어느 컬럼을 "
                 "어느 임계로 보는지.".format(ar, len(rr), reach),
                 [ar, ar.replace("_", ""), "area_score", "컬럼", "임계",
                  "{} 점수".format(ar), "{} 컬럼".format(ar)] + mine,
                 "entity")]
        b.append("## {} 가 보는 것\n\n".format(ar))
        b.append(_md_table(["룰", "읽는 컬럼", "임계", "배점"], [
            [n, "<br>".join("`{}`".format(c) for c in (cols or ["—"])),
             th, "+{}{}".format((pts.get(v) or {}).get("pts", "?"),
                                " × n" if v == "mc_pts" else "")]
            for n, cols, th, v in rr]) + "\n")
        b.append("\n```\narea_score = min({}, 켜진 룰 배점의 합)\n"
                 "{} 가 받을 수 있는 최대: {}점\n```\n".format(cap, ar, reach))
        if not mc:
            b.append("\n> 붙는 룰이 {}종이라 {}점을 다 못 채운다. 점수가 낮다고 "
                     "안전한 것이 아니라 볼 수 있는 컬럼이 적은 것이다.\n"
                     .format(len(rr), cap))
        ra_c = (C.get("RA_COL") or {}).get(ar)
        if ra_c and "AVGLOADTIME" in ra_c:
            b.append("\n> ★{} 의 반송지연은 `AVGLOADTIME1MIN`(적재시간) 을 "
                     "본다. M16HUB·M14B 처럼 `AVGTOTALTIME1MIN` 이 아니다.\n"
                     .format(ar))
        out.append(("04_{}_영역-{}.md".format(i, ar), "".join(b)))

    # ── 05 컬럼 사전 ────────────────────────────────────────────────
    ef = C.get("EVENT_FIELDS") or []
    if ef:
        b = [_fm("발동이벤트 CSV 컬럼 사전",
                 "예측기가 매분 만드는 {}개 컬럼의 뜻. 매분 1행이고 "
                 "이벤트가 없는 분도 기록한다.".format(len(ef)),
                 ["발동이벤트", "컬럼", "CSV", "EVENT_FIELDS", "reason",
                  "hot_area", "stage", "propagation_chain", "컬럼사전"])]
        b.append("## 매분 1행 · {}개 컬럼\n\n"
                 "**이벤트가 없는 분도 기록한다.** 없는 분을 빼면 나중에 "
                 "분모를 못 센다.\n\n".format(len(ef)))
        cols = explain_cols(ef, cap)
        seen_shape, rows2 = set(), []
        for c in cols:
            n = c["col"]
            ar = ""
            for a2 in sorted(AREA_ORDER, key=len, reverse=True):
                if n.startswith(a2 + "_") or n.endswith("_" + a2):
                    ar = a2
                    break
            shape = n.replace(ar, "{영역}") if ar else n
            if shape in seen_shape:
                continue
            seen_shape.add(shape)
            t = c["title"].replace(ar, "{영역}") if ar else c["title"]
            rows2.append(["`{}`".format(shape), t,
                          _re.sub(r"<[^>]+>", "", c["desc"])])
        b.append(_md_table(["컬럼", "뜻", "설명"], rows2) + "\n")
        b.append("\n> `{영역}` 자리에 M16HUB · M14 · M14B · M16A · M16B · "
                 "M16 · M16_PKT · M16_WT 가 들어간다.\n")
        out.append(("05_발동이벤트-컬럼사전.md", "".join(b)))

    # ── 06 영역분리 ─────────────────────────────────────────────────
    b = [_fm("영역분리 — FAB 파일에서 area_score 가 자리를 옮긴다",
             "FAB 파일에는 전체 점수와 그 FAB 점수가 같이 들어 있다. "
             "관제가 받는 순간 area_score 를 unified_risk_score 자리로 "
             "옮기고 원본은 all_* 로 남긴다.",
             ["영역분리", "area_score", "all_score", "정규화", "FAB파일",
              "jupyter_csv", "hot_area", "all_hot_area"])]
    b.append("## 왜 자리를 바꾸나\n\n"
             "FAB 파일에는 **전체 점수와 그 FAB 점수가 같이** 들어 있다. "
             "관제가 그대로 읽으면 M14 화면이 전체 점수로 등급을 매기고 "
             "케이스 영역이 M16HUB 로 찍힌다 — 화면 전체가 남의 데이터를 "
             "보게 된다.\n\n")
    b.append(_md_table(["받은 그대로", "정규화 후", "값"], [
        ["`unified_risk_score` (전체)", "`all_score`", "137"],
        ["`area_score` (M14)", "**`unified_risk_score`**", "28"],
        ["`unified_risk_level` (전체)", "`all_level`", "주의"],
        ["`area_level` (M14)", "**`unified_risk_level`**", "관심"],
        ["`hot_area` (전체 기준)", "`all_hot_area`", "M16HUB"],
        ["—", "**`hot_area`**", "M14"],
    ]) + "\n")
    b.append("\n**한 자리에서 한 번만 바꾼다.** 그래프·예보·기여도·리포트·"
             "정확도가 모두 `unified_risk_score` 와 `hot_area` 를 읽으므로, "
             "받는 자리에서 바꿔 두면 하위 모듈을 하나도 안 고치고 FAB 화면이 "
             "자기 데이터를 본다. 원본은 `all_*` 로 남겨 전체와 비교할 수 "
             "있게 둔다.\n")
    out.append(("06_영역분리와-정규화.md", "".join(b)))
    return out


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    wiki_dir = ""
    if "--wiki" in argv:
        i = argv.index("--wiki")
        argv.pop(i)
        wiki_dir = (argv.pop(i) if i < len(argv) and not argv[i].startswith("-")
                    else os.path.join(DOC_DIR, "위키_MD"))
    out = argv[0] if argv else OUT
    d = build()
    if wiki_dir:
        os.makedirs(wiki_dir, exist_ok=True)
        pages = wiki_pages(d)
        for name, body in pages:
            with open(os.path.join(wiki_dir, name), "w", encoding="utf-8") as f:
                f.write(body)
        print("위키 MD {}장: {}".format(len(pages), wiki_dir))
        for name, _ in pages:
            print("   {}".format(name))
        return 0
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
