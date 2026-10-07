#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 구간 그래프 (독립 SVG 렌더러)

발동이벤트_요약 / report_graphs 와 같은 형식으로 그린다:

  ┌ 스코어 패널 ─ unified_risk_score, 등급 밴드(60/71/85), 사건 표시
  ├ 실제지표 ──── 더블클릭한 그 줄 실시간 표 '실제지표' 칸 그대로 (2026-10-07)
  │   칸 ┌ M16HUB.QUE.TIME.AVGTOTALTIME1MIN   ← 윗줄: 실제 컬럼 이름
  │      ├ ▲1.2배  M16HUB 반송시간           ← 아랫줄: 배수 · 한글 이름
  │      └ 10.41분 최고 @21:08 … 임계 9분 + 추이
  ├ 신규 지표 ─── 그 줄 룰이 본 계산 컬럼 (rb_diff30 · rev_count …)
  └ 값이 안 온 컬럼 한 줄

지표 목록은 metric_sets() — 더블클릭한 그 줄 실시간 표 '실제지표' 칸과 같은 함수로 고른다.
데모스를 import 하지 않고 외부 라이브러리도 쓰지 않는다(순수 SVG).
"""
from __future__ import annotations

import html
import math
import re
from datetime import timedelta

from lp_client import load_config, parse_dt

_RA = {"M16HUB": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "M14": "M14.QUE.LOAD.AVGLOADTIME1MIN",
       "M14B": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "M16A": "M16A.QUE.LOAD.AVGLOADTIME1MIN",
       "M16B": "M16B.QUE.LOAD.AVGLOADTIME1MIN"}
_FAB = "M16HUB.STRATE.ALL.FABSTORAGERATIO"
_STB = "M16HUB.STRATE.STB.3F_STORAGE_UTIL"
_REV = "M16HUB.QUE.LFT.3F_LFT_REVERSALCNT"

# ── 다크 테마 (dashboard.html CSS 변수와 동일) ──
_BG = "#0D1119"      # --panel
_BG2 = "#0F1622"     # 스코어 패널 정상 구간
_LINE = "#1C2431"    # --line
_GRID = "#2E3A4C"    # 눈금선
_TX = "#E6EDF6"      # --tx
_TX2 = "#8FA0B6"     # --tx2
# ★--tx3(#5E6E85)를 그대로 쓰면 이 배경 위에서 3.64:1 이라 기준(3.9)에
#   못 미친다. 화면 글자는 확대·선택이 되지만 그래프는 박힌 그림이라
#   더 필요하다 — 한 톤만 올린다(범위·눈금 같은 작은 글자에 쓰인다).
_TX3 = "#6B7C94"     # --tx3 를 그래프용으로 한 톤 올린 값

# 지표 패널 색 — 반송시간(빨강) → 저장율(주황/호박) → 리프터(자홍) → 4분초과율(청록/파랑)
# 어두운 배경에서 읽히도록 밝기를 올린 값
_PALETTE = ["#FF6B5E", "#FFA53D", "#F2C94C", "#FF6FB5", "#3DDBE8", "#5FB8FF", "#7C9CFF"]
# 지표 종류별 고정 색 (같은 지표는 항상 같은 색)
_COLOR_BY_KIND = {
    "ra": "#FF6B5E",        # 반송시간
    "rd_fab": "#FFA53D",    # FAB저장율
    "stb_util": "#F2C94C",  # STB저장율
    "rev_count": "#FF6FB5",  # 리프터 정체
    "sla": "#3DDBE8",       # 4분초과율
    "sorter": "#5FB8FF",    # 분류기 대기
    "rd_oht": "#7C9CFF",    # OHT가동률
    # PIO 반송실패 — 설비 지표(선)와 성격이 다른 '실패 개수' 라 색도 따로 준다
    "pio_10min_cnt": "#C58CFF",         # 10분 합 (판정 기준)
    "PIOERROR_DEPOSITED": "#8F7BFF",    # 경로별 1분 개수
}
# PIO 주 경로 막대 — 한 패널에 쌓으므로 경로마다 색이 달라야 한다
_PATH_COLORS = ["#C58CFF", "#5FB8FF", "#3DDBE8", "#F2C94C", "#FF6FB5"]
_SCORE_COLOR = "#3DDBE8"   # --cy
_SEL_COLOR = "#E6EDF6"     # 더블클릭한 시각 표시색 (밝게)
_EVT_COLOR = "#FF9F2E"     # --major
_CRIT_COLOR = "#FF4D5E"    # --crit
# 등급 밴드 — 다크 배경 위에 등급색을 옅게 깐 톤. 경계선은 시스템별
# 설정(grade.by_sys)을 따르므로 그릴 때 cfg 로 계산한다.
_BAND_COLORS = (_BG2, "#2B2612", "#33210F", "#331419")

# ══ 흰 배경용 한 벌 ═══════════════════════════════════════════════════
# 화면은 [배경] 단추로 검정↔흰색을 고르는데 그래프만 늘 검게 나왔다 —
# 흰 화면 한가운데 검은 상자가 박혀서 거기만 눈이 아프다.
# ★순백(#FFF)을 쓰지 않는다. 관제실 조명 아래서 눈이 부시다 —
#   종이 톤(#F4F7FB)까지만 올린다.
# ★선 색은 어두운 배경용을 그대로 못 쓴다. 노랑(#F2C94C)·청록(#3DDBE8)은
#   흰 바탕에서 거의 안 보인다. 같은 '종류' 를 유지하되 채도를 내린다.
_LIGHT = {
    "bg": "#E7ECF4", "bg2": "#DBE2EC", "line": "#BFC9D8", "grid": "#9FADC0",
    "tx": "#0F1720", "tx2": "#42526A", "tx3": "#5C6B82",
    "score": "#0A6B75", "sel": "#1B2430", "evt": "#96500A", "crit": "#BE1B2C",
    "bands": ("#DBE2EC", "#EDE6CB", "#EFDCC0", "#EFCFD3"),
    "palette": ["#C43426", "#944F00", "#7A6000", "#AC2A6E", "#0A6B75",
                "#1B63BC", "#4350C0"],
    "kind": {"ra": "#C43426", "rd_fab": "#944F00", "stb_util": "#7A6000",
             "rev_count": "#AC2A6E", "sla": "#0A6B75", "sorter": "#1B63BC",
             "rd_oht": "#4350C0",
             "pio_10min_cnt": "#6E37BD", "PIOERROR_DEPOSITED": "#4F3BAF"},
    "path": ["#6E37BD", "#1B63BC", "#0A6B75", "#7A6000", "#AC2A6E"],
}
_DARK = {
    "bg": _BG, "bg2": _BG2, "line": _LINE, "grid": _GRID,
    "tx": _TX, "tx2": _TX2, "tx3": _TX3,
    "score": _SCORE_COLOR, "sel": _SEL_COLOR, "evt": _EVT_COLOR,
    "crit": _CRIT_COLOR, "bands": _BAND_COLORS,
    "palette": _PALETTE, "kind": _COLOR_BY_KIND, "path": _PATH_COLORS,
}

# ══ 네이비 · 고대비 한 벌씩 ═══════════════════════════════════════════
# 화면 테마가 넷(다크·화이트·네이비·고대비)인데 그래프는 둘뿐이라, 네이비를
# 골라도 그래프만 다크(#0D1119)로 나왔다 — 남색 화면 한가운데 다른 검정
# 상자가 박혀 거기만 튀어 보였다.
# ★색은 눈으로 고르지 않았다. 각 배경 위에서 글자·선이 3.9:1 이상 나오는지
#   재서 골랐다 (tests/test_theme.py 가 네 벌 모두 같은 기준으로 지킨다).
#   네이비 tx3 는 화면 토큰(#647894)을 그대로 쓰면 3.73 이라 한 톤 올렸다 —
#   화면에서는 작은 보조 글자지만 그래프에서는 눈금 숫자에 쓰인다.
_NAVY = {
    "bg": "#0E1E30", "bg2": "#122A42", "line": "#1B3049", "grid": "#2E4A68",
    "tx": "#E4EDF8", "tx2": "#93A8C2", "tx3": "#7086A4",
    "score": "#54D2E0", "sel": "#F2F8FF", "evt": "#FFA63F", "crit": "#FF5C6B",
    "bands": ("#122A42", "#33301A", "#3A2A16", "#38202A"),
    "palette": ["#FF7E72", "#FFB25A", "#F7D45E", "#FF85C2", "#54D2E0",
                "#77C4FF", "#93AEFF"],
    "kind": {"ra": "#FF7E72", "rd_fab": "#FFB25A", "stb_util": "#F7D45E",
             "rev_count": "#FF85C2", "sla": "#54D2E0", "sorter": "#77C4FF",
             "rd_oht": "#93AEFF",
             "pio_10min_cnt": "#CE9CFF", "PIOERROR_DEPOSITED": "#A78BFF"},
    "path": ["#CE9CFF", "#77C4FF", "#54D2E0", "#F7D45E", "#FF85C2"],
}
_CONTRAST = {
    "bg": "#0A0A0A", "bg2": "#141414", "line": "#33383F", "grid": "#4A515B",
    "tx": "#FFFFFF", "tx2": "#B9C4D2", "tx3": "#8B97A6",
    "score": "#5BE9F5", "sel": "#FFFFFF", "evt": "#FFB454", "crit": "#FF6B79",
    "bands": ("#141414", "#3A3410", "#3A2A0E", "#3A1418"),
    "palette": ["#FF8B80", "#FFC06A", "#FFE64D", "#FF95CC", "#5BE9F5",
                "#8FD0FF", "#A8BEFF"],
    "kind": {"ra": "#FF8B80", "rd_fab": "#FFC06A", "stb_util": "#FFE64D",
             "rev_count": "#FF95CC", "sla": "#5BE9F5", "sorter": "#8FD0FF",
             "rd_oht": "#A8BEFF",
             "pio_10min_cnt": "#D9AFFF", "PIOERROR_DEPOSITED": "#BCA0FF"},
    "path": ["#D9AFFF", "#8FD0FF", "#5BE9F5", "#FFE64D", "#FF95CC"],
}
_PALS = {"light": _LIGHT, "dark": _DARK, "navy": _NAVY, "contrast": _CONTRAST}
# 밖에서 "고를 수 있는 테마" 를 물을 때 쓴다 (server.py 가 검사에 쓴다).
THEMES = frozenset(_PALS)


def _pal(theme) -> dict:
    """테마 이름 → 색 한 벌. 모르는 값은 다크 — 예전 주소(?theme= 없음)가
    그대로 돌아간다."""
    return _PALS.get(str(theme or "").lower(), _DARK)


def _bands_of(cfg, pal: dict | None = None) -> list:
    from sentinel import grade_cuts
    w, d, c = grade_cuts(cfg or {})
    edges = (0, w, d, c, 100)
    band = (pal or _DARK)["bands"]
    return [(edges[i], edges[i + 1], band[i]) for i in range(4)]


def _kind_color(col: str, idx: int, pal: dict | None = None) -> str:
    """컬럼명으로 지표 종류를 알아 고정 색을 준다 (사진과 같은 색 배치)."""
    pal = pal or _DARK
    for key, c in pal["kind"].items():
        if col.endswith("_" + key) or col.startswith(key + "_") or col.endswith(key):
            return c
    return pal["palette"][idx % len(pal["palette"])]


def parse_reason_metrics(reason: str, fab: str = "") -> list[dict]:
    """reason → [{col, raw, label, unit}] (등장 순서, 중복 제거, M16_PKT/M16_WT 제외).

    fab 을 주면 그 FAB 화면용이다 — PIO 는 **그 FAB 것만** 남긴다
    (2026-09-16 'PIO_ERROR FAB별 연동 명세'). 안 주면 지금까지와 똑같다.
    """

    out, seen = [], set()
    body = (reason or "").split("발동:", 1)[-1]
    body = re.split(r"흐름:|운영자조치:", body)[0]

    def add(col, raw, label, unit, bar=False):
        if col and col not in seen and not any(x in col for x in ("M16_PKT", "M16_WT")):
            seen.add(col)
            out.append({"col": col, "raw": raw, "label": label, "unit": unit,
                        "bar": bar})

    # ★FAB 화면이면 **그 FAB 블록만** 본다 (고객: "스코어는 보이고 관련된 그래프만
    #   보이게", "실제지표 각 FAB 에 연관관계가 있는걸"). reason 원문은 FAB 분리
    #   파일에도 **전체 것**이 실려 와서 M16HUB[…]; M14[…] 가 같이 들어 있다. 예전엔
    #   fab 을 받아 놓고 PIO 에만 썼기 때문에 M16B 그래프에 M14·M16HUB 반송시간이 떴다.
    #   fab 을 안 주면(ALL) 지금까지와 똑같이 모든 블록을 본다.
    only = _fab_ok(fab)
    # ★M16HUB 전용 칸(FAB 저장율·STB·리프터 정체)은 ALL 이나 M16HUB 화면에서만 선다.
    #   컬럼흐름 상세도(FAB별 HTML 2절): M14·M14B·M16A·M16B 의 R-D 는 **OHT 가동률
    #   하나**, R-C 는 M14 만 있고 **CNV 편중**(M14_cnv_skew)이다. 예전엔 어느 블록이든
    #   R-C 를 M16HUB 리프터로 그렸다.
    hub_ok = (not only) or only == "M16HUB"
    for m in re.finditer(r"(M16HUB|M14B|M16A|M16B|M14)\s*\[(.*?)\]", body):
        area, inner = m.group(1), m.group(2)
        if only and area.upper() != only:
            continue
        if "AVGTOTALTIME1MIN" in inner or "AVGLOADTIME1MIN" in inner or "R-A" in inner:
            add(f"{area}_ra", _RA.get(area, f"{area}.QUE.TIME.AVGTOTALTIME1MIN"),
                f"{area} 반송시간", "분")
        if only and re.search(r"(?<![A-Za-z0-9])R-?B", inner):
            # FAB 화면만 — 상세도 2절: R-B 는 {FAB} 대기물량의 30분·10분 증가량.
            # 우리가 계산해 만든 컬럼이라 '신규 지표' 묶음에 선다 (metric_sets).
            # ★ALL 은 예전 그대로 안 세운다 — ALL 실시간 표 '실제지표' 칸에도 R-B 는
            #   없다(report_graphs: 대응하는 단일 원본 컬럼이 없다).
            add(f"{area}_rb_diff30", f"{area}_rb_diff30", f"{area} Queue 증감(30분)", "건")
            if "R-B_fast" in inner or "RB_fast" in inner:
                add(f"{area}_rb_diff10", f"{area}_rb_diff10", f"{area} Queue 증감(10분)", "건")
        if hub_ok and "FAB저장" in inner:
            add("M16HUB_rd_fab", _FAB, "M16HUB FAB저장율", "%")
        if hub_ok and re.search(r"\bSTB", inner):
            # R-D 판정에서 빠진 값이다 (2026-08) — 기록용임을 이름에 남긴다
            add("M16HUB_stb_util", _STB, "M16HUB STB저장율 (기록용)", "%")
        if "OHT=" in inner or "OHT가동" in inner or \
                (only and area.upper() != "M16HUB"
                 and re.search(r"(?<![A-Za-z0-9])R-?D(?![A-Za-z0-9_])", inner)):
            add(f"{area}_rd_oht", f"{area}.QUE.OHT.OHTUTIL", f"{area} OHT가동률", "%")
        if "R-C" in inner:
            if hub_ok and area.upper() == "M16HUB":
                add("M16HUB_rev_count", _REV, "M16HUB 리프터 정체", "회")
            elif area.upper() == "M14" and only:
                add("M14_cnv_skew", "M14_cnv_skew", "M14 컨베이어 편중", "")
            elif hub_ok:
                add("M16HUB_rev_count", _REV, "M16HUB 리프터 정체", "회")
        if "SLA(" in inner or "4분초과" in inner:
            add(f"sla_{area}", f"{area}.QUE.ALL.TRANSPORT4MINOVERRATIO", f"{area} 4분초과율", "%")
        if "SORT(" in inner or "소터" in inner or (only and re.search(r"(?i)sort", inner)):
            add(f"sorter_{area}", f"{area}.SORTER.ABN.SORTERWAITCOUNTOVER", f"{area} 분류기 대기", "건")

    # ── PIO 반송실패 ────────────────────────────────────────────────
    # ★PIO 는 영역 블록 **밖**에 붙는다 —
    #     …발동: M16HUB[R-A_sus]; PIO(M14A<-M14B=4건/10분,합6)
    #   위 영역 루프만 돌면 통째로 빠져서, 더블클릭 그래프에 PIO 가 안 떴다.
    #   설비 지표와 실측 상관이 +0.22 라, 빠지면 대신 볼 것이 없다.
    # ★선이 아니라 **막대**다. 1분 개수는 0/1/2 로 뚝뚝 끊기는 값이라 선으로
    #   이으면 없는 중간값을 그린 것처럼 보인다 — 0 과 4 사이를 지나가는
    #   선은 거짓이다. 개수는 막대가 맞다.
    # ★설비 지표 **뒤**에 붙인다. 앞에 끼우면 늘 보던 패널 순서가 밀린다.
    _pio = re.search(r"PIO\(([^)]*)\)", reason or "")
    if _pio:
        # ★pio_10min_cnt 는 **12경로 전부의 합(ALL)** 이다. FAB 화면에 그대로
        #   올리면 M16B 칸에 M14 의 실패까지 더해진 수가 뜬다 — 남의 데이터다.
        #   FAB 은 예측기가 그 FAB 몫으로 적어 준 가중합을 쓴다.
        if _fab_ok(fab):
            add("area_pio_wsum10", "PIO.DEPOSIT.WSUM10",
                "PIO 10분 가중합 (직접×2 + 간접×1)", "", bar=True)
        else:
            add("pio_10min_cnt", "PIO.DEPOSIT.10MIN.CNT",
                "PIO 반송실패 10분 합", "개", bar=True)
        out[-1]["rolling"] = True      # 겹쳐 더한 값 — 구간 합을 또 내면 거짓이다
        # 주 경로는 **한 패널에 쌓아** 그린다. 경로마다 패널을 따로 만들면
        # 그래프가 한 화면을 넘어가고, 정작 알고 싶은 '이 분에 총 몇 개'가
        # 어디에도 안 남는다. 쌓으면 막대 높이가 곧 그 분의 총 개수다.
        paths, pseen = [], set()
        for _p in re.findall(
                r"([A-Za-z0-9_]+\s*(?:<-|->)\s*[A-Za-z0-9_]+)\s*=\s*\d+\s*[건개]",
                _pio.group(1)):
            _p = _p.replace(" ", "")
            if _p not in pseen:
                pseen.add(_p)
                paths.append({"col": f"{_p}_PIOERROR_DEPOSITED", "name": _p})
        paths = _pio_keep(paths, fab)
        if paths:
            out.append({"col": paths[0]["col"], "raw": "PIO.DEPOSIT.{경로}",
                        "label": _pio_label([x["name"] for x in paths], fab),
                        "unit": "개",
                        "bar": True, "cols": paths, "pio_stack": True})
    return out


# ── PIO 주 경로는 reason 이 아니라 '데이터' 로 채운다 ──────────────────
# reason 은 그 10분에 **가장 많이 실패한 한 구간**만 적어 온다. 그런데
#   · 그 컬럼이 이 창에 안 오면  → 패널이 통째로 사라지고
#   · 다른 경로에서 실패가 나도  → 이름이 안 적혔으니 안 그려진다
# 실제로 화면에서 'PIO 주 경로가 안 뜬다' 던 게 이것이다. 그래서 창 안에서
# 값이 온 경로를 전부 모아 쌓는다 — 막대 높이가 그 1분의 총 실패 개수다.
_PIO_SUF = "_PIOERROR_DEPOSITED"
_PIO_STACK_MAX = 6      # 한 패널에 쌓을 경로 수 (범례가 한 줄을 안 넘는 선)
_PIO_IN_RE = re.compile(r"PIO\(([^)]*)\)")
_PIO_KV_RE = re.compile(
    r"([A-Za-z0-9_]+\s*(?:<-|->)\s*[A-Za-z0-9_]+)\s*=\s*(\d+)\s*[건개]")


def _fab_ok(fab: str) -> str:
    """FAB 코드로 쓸 수 있는 값인가 — 아니면 "" (= ALL 로 본다)."""
    f = str(fab or "").strip().upper()
    try:
        import fab_score as F
        return f if f in F.PIO_FAB_PATHS else ""
    except Exception:                                   # noqa: BLE001
        return ""


def row_fab(r) -> str:
    """이 행이 **어느 FAB 의 분리 파일 행**인가 — 통합(ALL) 행이면 "".

    ★render() 서명은 못 바꾼다 (배포가 파일 단위다). 그래서 '지금 어느 FAB
      화면인가' 를 인자로 못 받고 **행 자체**에서 읽는다.
      jupyter_csv._fab_rows 가 정규화하면서 all_score 를 남기고 hot_area 를
      그 FAB 코드로 바꿔 둔 것이 유일하고 확실한 표식이다.
    """
    r = r or {}
    if not str(r.get("all_score") or "").strip():
        return ""
    return _fab_ok(r.get("hot_area"))


def _pio_kinds(fab: str) -> dict:
    """{경로: (직접/간접, 가중)} — 그 FAB 것만. ALL 이면 빈 dict."""
    f = _fab_ok(fab)
    if not f:
        return {}
    try:
        import fab_score as F
    except Exception:                                   # noqa: BLE001
        return {}
    return {x["path"]: (x["kind"], x["w"]) for x in F.pio_paths_of(f)}


def _pio_keep(paths: list[dict], fab: str) -> list[dict]:
    """그 FAB 에 배정된 경로만 남기고, 직접(×2) 을 앞으로 · 이름에 가중을 적는다.

    ★M16B 화면에 M14A<-M14B 가 뜨면 현장은 자기 FAB 을 뒤진다 — 남의 구간이다.
    ★가중을 이름에 적는 이유: 같은 8건이라도 보낸 쪽은 16.0, 받은 쪽은 8.0 이
      된다. 막대 높이만 보면 왜 점수가 다른지 알 수가 없다.
    """
    k = _pio_kinds(fab)
    if not k:
        return paths
    out = []
    for x in paths:
        kw = k.get(x["name"])
        if not kw:
            continue
        # ★name 은 **경로 원래 이름 그대로** 둔다 — _pio_val 이 reason 에서
        #   값을 찾을 때 이 이름으로 맞춰 본다. 꾸민 이름은 legend 로 따로.
        out.append(dict(x, kind=kw[0], w=kw[1],
                        legend=f"{x['name']} ×{kw[1]:g}"))
    out.sort(key=lambda x: (x["kind"] != "직접",))
    return out


def _pio_reason_map(r) -> dict:
    """그 분 reason 의 PIO(…) 에서 {경로: 개수}.

    ★1분 컬럼이 CSV 에 0 으로만 들어오는 현장이 있다. 그때도 reason 에는
      'M14A<-M14B=4개/10분' 처럼 경로별 숫자가 그대로 실려 온다 — 화면에
      '범위 0~0개' 만 뜨던 게 이것이다. 마지막 수단으로 이 값을 쓴다.
      단위가 다르다(1분 개수가 아니라 10분 누적) — 이름표에 적어 준다.
    """
    m = _PIO_IN_RE.search(str((r or {}).get("reason") or ""))
    if not m:
        return {}
    return {p.replace(" ", ""): float(n) for p, n in _PIO_KV_RE.findall(m.group(1))}


def _pio_val(r, x):
    """스택 한 칸의 값 — CSV 컬럼이 원칙, reason 은 대체."""
    if x.get("from_reason"):
        return _pio_reason_map(r).get(x["name"])
    return _f(r.get(x["col"]))


def _pio_paths_in(pts, fab: str = "") -> list[str]:
    """창 안에서 **실제로 실패가 온** PIO 경로 — 구간 합이 많은 순.

    0 과 빈칸은 세지 않는다. 12경로 중 평소 값이 나오는 건 3개뿐이라,
    0 인 경로까지 쌓으면 범례만 길어지고 막대는 그대로다.

    fab 을 주면 **그 FAB 에 배정된 경로만** 본다. FAB 분리 파일에도 12경로가
    다 실려 오므로, 안 거르면 M16B 화면에 M14 의 실패가 쌓인다.
    """
    keep = set(_pio_kinds(fab))
    tot: dict[str, float] = {}
    for _t, r in pts:
        for k, v in (r or {}).items():
            if not isinstance(k, str) or not k.endswith(_PIO_SUF):
                continue
            name = k[:-len(_PIO_SUF)]
            if keep and name not in keep:
                continue
            f = _f(v)
            if f:
                tot[name] = tot.get(name, 0.0) + f
    return [p for p, _n in sorted(tot.items(), key=lambda x: (-x[1], x[0]))]


def _pio_label(names: list[str], fab: str = "") -> str:
    head = " · ".join(names[:3])
    more = f" 외 {len(names) - 3}" if len(names) > 3 else ""
    who = f" {_fab_ok(fab)}" if _fab_ok(fab) else ""
    return f"PIO{who} 주 경로 ({head}{more})"


def _pio_fill(metrics: list[dict], pts, fab: str = "") -> list[dict]:
    """'PIO 주 경로' 패널을 창 안 데이터로 다시 만든다.

    ★reason 에 PIO 가 없으면 손대지 않는다. PIO 컬럼이 실려 온다는 이유만으로
      아무 그래프에나 패널을 하나 더 붙이면, 늘 보던 화면이 바뀐다.
    """
    idx = next((i for i, m in enumerate(metrics) if m.get("pio_stack")), -1)
    has_pio = any(m.get("col") in ("pio_10min_cnt", "area_pio_wsum10")
                  for m in metrics)
    if idx < 0 and not has_pio:
        return metrics
    found = _pio_paths_in(pts, fab)[:_PIO_STACK_MAX]
    if found:
        cols = _pio_keep([{"col": p + _PIO_SUF, "name": p} for p in found], fab)
        if not cols:
            return metrics          # 이 FAB 경로에서는 실패가 안 왔다
        md = {"col": cols[0]["col"], "raw": "PIO.DEPOSIT.{경로}",
              "label": _pio_label([x["name"] for x in cols], fab), "unit": "개",
              "bar": True, "cols": cols, "pio_stack": True}
    else:
        # ★1분 컬럼이 창 내내 0 이면 막대가 하나도 안 선다 — 화면에
        #   'PIO 주 경로 (M14A<-M14B) · 범위 0~0개' 만 떴다. 정작 보려던
        #   '어느 구간이 얼마나' 는 reason 에 숫자로 들어 있다. 그걸 쓴다.
        tot: dict[str, float] = {}
        for _t, r in pts:
            for name, v in _pio_reason_map(r).items():
                if v:
                    tot[name] = max(tot.get(name, 0.0), v)
        if not tot:
            return metrics      # 어디에도 숫자가 없다 — 있는 그대로 둔다
        names = [p for p, _n in sorted(tot.items(), key=lambda x: (-x[1], x[0]))
                 ][:_PIO_STACK_MAX]
        cols = _pio_keep([{"col": p + _PIO_SUF, "name": p, "from_reason": True}
                          for p in names], fab)
        if not cols:
            return metrics
        md = {"col": cols[0]["col"], "raw": "PIO.DEPOSIT.{경로} (reason)",
              "label": _pio_label([x["name"] for x in cols], fab) + " · 10분 누적",
              "unit": "개",
              # 겹쳐 더한 값이라 '구간 합' 을 내면 같은 실패를 열 번 센다
              "bar": True, "rolling": True, "cols": cols, "pio_stack": True}
    if idx >= 0:
        metrics[idx] = md
    else:
        metrics.append(md)
    return metrics


# 명세 6장 '권장 색상 단계' — 점수는 0·1·3·5·8·10 여섯 칸뿐이고, 각 칸이
# 실측 분포의 어디인지가 정해져 있다. 그대로 옮긴다 (우리가 정한 값이 아니다).
PIO_BAND_NAME = {0: "평상", 1: "중간값↑ p50", 3: "상위 25% p75",
                 5: "상위 10% p90", 8: "상위 5% p95", 10: "상위 1% p99"}


def _pio_band(v):
    """점수 → (이름, 몇 번째 칸인가 0~5). 사이 값은 아래 칸으로 읽는다."""
    lad = [0, 1, 3, 5, 8, 10]
    i = 0
    for k, b in enumerate(lad):
        if v is not None and v >= b:
            i = k
    return PIO_BAND_NAME.get(lad[i], ""), i


def _pio_score_cell(metrics: list[dict], pts, fab: str) -> list[dict]:
    """그 FAB 의 PIO **점수** 칸을 만든다 (2026-09-16 명세).

    ★reason 에 PIO 가 안 적혔어도 점수는 붙을 수 있다 — reason 은 ALL 기준으로
      쓰이고, FAB 점수는 예측기가 따로 계산한다. reason 에만 기대면 "점수는
      올랐는데 그래프에는 아무것도 없다" 가 된다.
    ★임계는 안 만든다. 구간표가 잠정이라(명세 8장) 우리가 선을 그으면 예측기와
      갈라진다. 대신 명세가 준 여섯 칸(0·1·3·5·8·10)을 그대로 색으로 쓴다.
    """
    f = _fab_ok(fab)
    if not f or any(m.get("pio_score") for m in metrics):
        return metrics
    try:
        import fab_score as F
    except Exception:                                   # noqa: BLE001
        return metrics
    sc, wc = F.PIO_AREA_COLS
    a1, a2 = F.PIO_FAB_COLS
    col = next((c for c in (sc, f"{f}_{a1}")
                if any(_f((r or {}).get(c)) is not None for _t, r in pts)), "")
    if not col:
        return metrics                  # 그 날 파일에 PIO 컬럼이 아직 없다
    if not any((_f((r or {}).get(col)) or 0) > 0 for _t, r in pts):
        return metrics                  # 창 내내 0 — 빈 칸을 세우지 않는다
    metrics.append({"col": col, "raw": f"PIO.DEPOSIT.{f}.SCORE",
                    "label": f"PIO 반송실패 점수 ({f})", "unit": "점",
                    "bar": True, "pio_score": True})
    # 가중합 칸이 아직 없으면 같이 세운다 — 점수만 있으면 '왜 그 점수냐' 가
    # 화면에 안 남는다 (명세 6장 드릴다운 ①②③ 중 ②).
    wcol = next((c for c in (wc, f"{f}_{a2}")
                 if any(_f((r or {}).get(c)) is not None for _t, r in pts)), "")
    if wcol and not any(m.get("col") == wcol for m in metrics):
        metrics.append({"col": wcol, "raw": f"PIO.DEPOSIT.{f}.WSUM10",
                        "label": "PIO 10분 가중합 (직접×2 + 간접×1)",
                        "unit": "", "bar": True, "rolling": True})
    return metrics


def _fab_real_cells(metrics: list[dict], pts, fab: str) -> list[dict]:
    """FAB 화면 — 그 FAB 의 **실제지표 그래프를 늘** 세운다.

    고객: "실제지표 나오는 그래프가 보여야 하는데. 실시간 관제도 더블클릭 그래프도
    마찬가지 … 그래프 추가해서 보여야 돼" · "실제데이터 그래프를 보여줘야 하는데
    그것도 없네" (UI대쉬보드 더블클릭).
    ★예전엔 그 분 reason 에 그 FAB 블록이 있을 때만 칸이 섰다. 룰이 안 걸린 분엔
      점수 그래프 하나만 떠서, 무엇이 얼마였는지 볼 길이 없었다.
    ★칸은 **컬럼흐름 상세도 2절의 룰 컬럼** — fab_score.WATCH 의 csv 이름(그 FAB
      분리 파일에 실제로 실려 오는 이름)이다. 걸린 룰은 앞에서 이미 들어왔고
      (col 이 같으면 다시 안 넣는다), 여기서는 나머지를 채운다. 순서는 뒤에서
      '임계 대비 배수' 로 다시 정렬되므로 넘은 것이 늘 먼저 보인다.
    ★빼는 것 — 기록용(STB, 판정 미사용) · 누적 건수(op=diff10: 누적값을 임계로
      나누면 배수가 거짓이 된다) · CSV 에 값이 없는 조건(MAXCAPA 등) · 창 안에
      값이 하나도 없는 컬럼(빈 칸은 높이만 먹는다).
    ★PIO 는 그 FAB 경로 컬럼({경로}_PIOERROR_DEPOSITED)에 실패가 왔으면 막대 칸을
      세운다 — reason 에 PIO 가 안 적힌 분에도 (고객: "PIO_ERROR 경우 이거 보여줘").
    ALL 화면(fab="")에는 아무것도 안 한다 — 지금까지와 똑같다.
    """
    f = _fab_ok(fab)
    if not f:
        return metrics
    try:
        import fab_score as F
    except Exception:                                   # noqa: BLE001
        return metrics
    have = {m.get("col") for m in metrics}
    derived = ("_rb_diff30", "_rb_diff10", "_cnv_skew", "_rev_count")
    for code in ("RA", "RB", "RB_fast", "RC", "RD", "SLA", "SORT"):
        for it in (F.WATCH.get(f) or {}).get(code) or []:
            col = it.get("csv") or ""
            if not col or col in have or it.get("record_only"):
                continue
            if (it.get("op") or "") == "diff10":
                continue
            if not any(_f((r or {}).get(col)) is not None for _t, r in pts):
                continue
            amos = str(it.get("amos") or "")
            # 원본을 그대로 옮긴 컬럼은 AMOS 이름으로, 창에서 새로 계산한 컬럼은
            # CSV 이름으로 적는다 — 현장이 그 이름으로 원 데이터를 찾아간다.
            raw = col if (col.endswith(derived) or any(x in amos for x in "{…/÷ ")
                          or not amos) else amos
            lb = str(it.get("label") or col)
            if lb.startswith("같은 "):
                # R-B_fast 는 상세도 표에 '같은 대기 10분 증가' 로 적혀 있다 — 칸 이름만
                # 보면 무엇과 같은지 모른다. R-B 이름에서 '30분' 만 '10분' 으로 바꿔 쓴다.
                rb = str(((F.WATCH.get(f) or {}).get("RB") or [{}])[0].get("label") or "")
                lb = re.sub(r"\d+분(\s*증가)$", r"10분\1", rb) if rb else lb
            metrics.append({"col": col, "raw": raw, "label": f"{f} {lb}",
                            "unit": it.get("unit") or ""})
            have.add(col)
    if not any(m.get("pio_stack") for m in metrics):
        found = _pio_paths_in(pts, f)[:_PIO_STACK_MAX]
        cols = _pio_keep([{"col": p + _PIO_SUF, "name": p} for p in found], f) if found else []
        if cols:
            metrics.append({"col": cols[0]["col"], "raw": "PIO.DEPOSIT.{경로}",
                            "label": _pio_label([x["name"] for x in cols], f), "unit": "개",
                            "bar": True, "cols": cols, "pio_stack": True})
    return metrics


# ══ 실제지표 · 신규 지표 ═══════════════════════════════════════════════
# 고객(2026-10-06): "실시간 보면 실제지표 컬럼들을 그래프로 보여주라 기여도도
#   마찬가지 실제지표로" · "우리가 만든 rb… 지표는 신규 지표라고 해서 따로 …
#   실제지표로 따로 신규지표로 따로".
#   실제지표 = 실시간 표 '실제지표' 칸에 뜨는 **원본 컬럼**(AMOS 이름)과 PIO 경로
#             개수. CSV 가 원본 값을 다른 이름으로 옮겨 싣는 것(M16HUB_ra ←
#             AVGTOTALTIME1MIN)도 값은 원본 그대로라 여기다 — 칸 제목은 원본 이름.
#   신규 지표 = 원본에서 **새로 계산해 만든** CSV 컬럼 — 증가량(rb_diff)·편중·
#             역증가 호기 수·추세·PIO 점수/가중합/10분 합. AMOS 에는 없는 이름이다.
_NEW_SUF = ("_rb_diff30", "_rb_diff10", "_cnv_skew", "_rev_count", "_rc_trend",
            "_ra_count", "_PIO_SCORE", "_PIO_WSUM10", "_PIO_WSUM1")
_NEW_COLS = frozenset(("pio_10min_cnt", "pio_score", "area_pio_score",
                       "area_pio_wsum10", "area_pio_wsum1", "area_score_raw"))
# 비교가 되는 부호 — diff10(누적 건수의 10분 증가)·ratio30 같은 것은 컬럼 값을
# 그대로 임계와 견주는 룰이 아니다. 누적값을 임계로 나누면 배수가 거짓이 된다.
_CMP_OPS = (">=", ">", "<=", "<")


def is_new_metric(col: str) -> bool:
    """우리가 계산해 만든 CSV 컬럼인가 (= 신규 지표)."""
    c = str(col or "")
    return c in _NEW_COLS or c.endswith(_NEW_SUF)


def _amos_name(s: str) -> bool:
    """AMOS 원본 컬럼 이름처럼 생겼나 — 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN'.

    자리표('{6ABL6011…}')·계산식('÷', ' / ')·PIO 자리 이름('PIO.DEPOSIT.…')은
    아니다 — 그런 이름으로는 CSV 에서 값을 찾을 수 없다.
    """
    s = str(s or "")
    return "." in s and not s.startswith("PIO.") and not any(x in s for x in "{}…/÷ ()")


def _watch_raw() -> tuple[dict, dict, dict, set]:
    """fab_score.WATCH 에서 원본 컬럼 기준 표 넷을 읽는다.

      label {AMOS: 'M16B 10F→HUB 대기'}    — 칸 아랫줄 한글 이름
      copy  {AMOS: 'M16B_ra'}              — 원본 값을 그대로 옮긴 CSV 컬럼
      thr   {AMOS: (임계, 부등호, 단위)}   — **원본 값을 그대로** 견주는 룰만
      cumul {컬럼, …}                      — 누적 건수 (룰은 10분 증가를 본다)
    ★R-B 의 원본(대기 물량)에 R-B 임계(30분 증가 100건)를 그으면 안 된다 — 임계는
      증가량에 거는 값이다. CSV 가 계산 컬럼(rb_diff30)인 룰은 thr 에서 뺀다.
    """
    try:
        import fab_score as F
    except Exception:                                   # noqa: BLE001
        return {}, {}, {}, set()
    order = {r["code"]: i for i, r in enumerate(F.RULES)}
    label, copy, thr, cumul = {}, {}, {}, set()
    for f, rules in (F.WATCH or {}).items():
        for code, specs in sorted((rules or {}).items(), key=lambda kv: order.get(kv[0], 99)):
            for sp in specs or []:
                amos, csv = str(sp.get("amos") or ""), str(sp.get("csv") or "")
                if (sp.get("op") or "") == "diff10":
                    cumul.update(c for c in (amos, csv) if c)
                if not _amos_name(amos):
                    continue
                derived = bool(csv) and is_new_metric(csv)
                lb = str(sp.get("label") or "")
                if derived:
                    # 'M14→M16 대기 30분 증가' → 'M14→M16 대기' (원본은 대기 물량이다)
                    lb = re.sub(r"\s*\d+분\s*증가$", "", lb)
                if lb and not lb.startswith("같은 "):
                    label.setdefault(amos, (f"{f} {lb}", sp.get("unit") or ""))
                if csv and not derived:
                    copy.setdefault(amos, csv)
                if (not derived and not sp.get("record_only") and sp.get("thr") is not None
                        and (sp.get("op") or ">=") in _CMP_OPS):
                    thr.setdefault(amos, (sp["thr"], sp.get("op") or ">=", sp.get("unit") or ""))
    return label, copy, thr, cumul


_PIO_NAME = "{경로}" + "_PIOERROR_DEPOSITED"


def metric_value(m: dict, r) -> float | None:
    """그 지표의 그 분 값. PIO 쌓기 칸은 경로 합, 나머지는 src 순서대로 첫 값.

    ★src 는 [CSV 컬럼, 원본 컬럼] 순이다 — CSV 가 옮겨 실은 값이 원칙이고, 그
      컬럼이 없는 파일(원본 이름으로만 싣는 곳)에서는 원본 이름으로 읽는다.
    """
    r = r or {}
    if m.get("lid"):
        # 리프터 호기 — CSV 에 대기량 값이 없어 역증가 호기 목록에 들었는지(1/0)
        v = r.get(m.get("lids_col") or "")
        if v is None:
            return None
        return 1.0 if m["lid"] in {x.strip() for x in str(v).split(",")} else 0.0
    if m.get("pio_stack"):
        # ★경로 묶음은 _pio_val 로 읽는다 — 1분 컬럼이 창 내내 0 이면 _pio_fill 이
        #   reason 에서 읽는 칸으로 바꿔 끼우는데, CSV 만 보면 그 칸이 통째로 0 이 된다.
        got = [v for v in (_pio_val(r, x) for x in m.get("cols") or []) if v is not None]
        return sum(got) if got else None
    for c in m.get("src") or [m.get("col")]:
        v = _f(r.get(c)) if c else None
        if v is not None:
            return v
    return None


_PIO_ROW_COLS = frozenset(("pio_10min_cnt", "pio_score", "area_pio_score",
                           "area_pio_wsum10", "area_pio_wsum1"))


def _is_pio(m: dict) -> bool:
    """PIO 쪽 지표인가 — 경로 컬럼 · 10분 합 · 점수 · 가중합."""
    col, raw = str(m.get("col") or ""), str(m.get("raw") or "")
    return (bool(m.get("pio_stack")) or col.endswith(_PIO_SUF) or col in _PIO_ROW_COLS
            or col.endswith(("_PIO_SCORE", "_PIO_WSUM10", "_PIO_WSUM1"))
            or raw.startswith("PIO."))


# M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT → (M16HUB, 6ABL6011)
_LFT_RE = re.compile(r"^([A-Z0-9]+)\.LFT\.([0-9A-Z]+)\.TOTAL_CURRENTQCNT$")


def _norm(s) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(s).upper())


def _find_col(name: str, keys) -> str | None:
    """CSV 에 그 이름 그대로가 없을 때 — **구분자·대소문자만 다른** 컬럼을 찾는다.

    예) M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT ↔ M16HUB_LFT_6ABL6011_TOTAL_CURRENTQCNT
    ★후보가 딱 하나일 때만 쓴다. 둘 이상이면 어느 쪽인지 모르니 안 고른다.
    ★리프터는 호기 번호(6ABL6011)가 FAB 안에서 하나뿐이라 앞뒤가 달라도
      그 번호 · 같은 끝말(TOTAL_CURRENTQCNT)이면 같은 컬럼으로 본다.
      다른 지표는 FAB 이름이 빠지면 남의 FAB 컬럼을 집을 수 있어 안 넓힌다.
    """
    want = _norm(name)
    hits = [k for k in keys if _norm(k) == want]
    if len(hits) == 1:
        return hits[0]
    lm = _LFT_RE.match(str(name))
    if lm:
        hits = [k for k in keys if lm.group(2) in str(k).upper()
                and _norm(k).endswith("TOTALCURRENTQCNT")]
        if len(hits) == 1:
            return hits[0]
    return None


def row_metrics(row, fab: str = "") -> list[dict]:
    """그 줄의 실시간 표 '실제지표' 칸 — 서버 /api/feed 와 **같은 함수 · 같은 인자**.

    FAB 분리 행이면 sentinel.fab_metrics(reason, FAB, 행),
    ALL 이면 sentinel.reason_metrics(reason, hot_area 또는 'UNKNOWN', 행).
    """
    row = row or {}
    reason = (row.get("reason") or "").strip()
    try:
        import sentinel as S
        f = _fab_ok(fab)
        if f:
            return S.fab_metrics(reason, f, row)
        if not reason:
            return []
        return S.reason_metrics(reason, (row.get("hot_area") or "").strip() or "UNKNOWN", row)
    except Exception:                                   # noqa: BLE001
        return []


def metric_sets(pts, sel_row, fab: str = "") -> tuple[list, list, list, bool]:
    """더블클릭한 **그 줄의 '실제지표' 칸 그대로** → (실제지표, 신규 지표, 값 없음, 대신 보임).

    고객(2026-10-07): "실제지표에 M16HUB.QUE.M14TOM16.MESCURRENTQCNT ·
      M16HUB.QUE.TIME.AVGTOTALTIME1MIN · M16HUB.STRATE.ALL.FABSTORAGERATIO 이런게 나오면
      더블클릭했을 저 그래프들이 나와야지" · "1개는 똑바로 나오고 나머지는 전혀 다른게
      나와 — 실제지표에 맞게 하라고" · "pio 대표 1개만 표시해라 전부다".
    ★실제지표 = 그 줄 표 칸과 **같은 함수**(row_metrics)가 낸 컬럼 — 더하지도 빼지도
      않는다. 예전엔 창 앞뒤 30분 다른 분의 실제지표 · FAB 룰 컬럼까지 끼워 넣어서,
      표에는 셋인데 그래프에는 엉뚱한 칸이 열몇 개 섰다.
    ★값은 그 컬럼 이름으로 읽고, CSV 가 다른 이름으로 옮겨 싣는 값(M16HUB_ra ←
      AVGTOTALTIME1MIN)이 있으면 그것도 읽는다. 둘 다 없으면 칸 대신 맨 아래
      '값이 안 온 실제지표' 줄에 이름이 남는다 — 말없이 빠지지 않는다.
    ★PIO 는 **한 칸** — 그 FAB(ALL 이면 전체) 경로 컬럼을 한 칸에 쌓는다. 10분 합 ·
      점수 · 가중합 칸은 따로 안 세운다.
    ★신규 지표 = 그 줄 룰이 실제로 본 **계산 컬럼**만 (R-B → rb_diff30/10,
      R-C → rev_count · cnv_skew). 그 줄과 상관없는 계산 컬럼은 안 세운다.
    ★그 줄에 실제지표가 하나도 없으면(룰이 안 걸린 분) FAB 화면은 그 FAB 룰 컬럼을
      대신 보여 준다 — 점수만 뜨면 무엇이 얼마였는지 볼 길이 없다 (2026-09 고객).
      그때 넷째 값(대신 보임)이 True — 그래프가 제목에 그렇게 적는다.
    """
    fabc = _fab_ok(fab)
    sel_row = sel_row or {}
    lab, copy, _thr, cumul = _watch_raw()
    table = row_metrics(sel_row, fabc)
    fallback = False
    if not table and fabc:
        # 룰이 안 걸린 분 — 그 FAB 룰 컬럼 (PIO 는 창 안에 실패가 왔으면 한 칸)
        table = _fab_real_cells([], pts, fabc)
        fallback = bool(table)

    real, new, empty = {}, {}, []
    has_pio = False

    def add_real(m, name, src):
        got = real.get(name)
        if got is None:
            real[name] = dict(m, kind="real", name=name, src=list(dict.fromkeys(src)))
        else:
            got["src"] = list(dict.fromkeys(got["src"] + src))

    def add_new(m):
        col = str(m.get("col") or "")
        if col and col not in new:
            new[col] = dict(m, kind="new", name=col, src=[col])

    for m in table:
        if _is_pio(m):
            has_pio = True
            continue
        col, raw = str(m.get("col") or ""), str(m.get("raw") or "")
        if is_new_metric(col):
            add_new(m)
            if not (_amos_name(raw) and raw != col):
                continue
            # ★실시간 표의 R-B 는 col=rb_diff30 · raw=대기 물량(AMOS) 으로 온다. 표 칸에
            #   적히는 것은 raw(대기 물량)다 — 그 이름으로 실제지표 칸을 세우고, 증가량은
            #   신규 지표로 따로. 한 칸에 두면 '증가량' 선 위에 '대기 물량' 이름이 붙는다.
            lb, un = lab.get(raw, (re.sub(r"\s*\d+분\s*증가$", "", str(m.get("label") or raw)),
                                   m.get("unit") or ""))
            m = {"col": raw, "raw": raw, "label": lb, "unit": un}
            col = raw
        name = raw if _amos_name(raw) else col
        add_real(m, name, [c for c in (col, copy.get(name), raw) if c])

    # 그 줄 룰이 본 계산 컬럼 — FAB 화면만 (ALL 표 칸은 그 블록만 보므로 표에 이미 있다)
    if fabc and not fallback:
        for m in parse_reason_metrics(sel_row.get("reason") or "", fabc):
            if is_new_metric(m.get("col")) and not _is_pio(m):
                add_new(m)
                if str(m.get("col")) == "M16HUB_rev_count":
                    # ★R-C'(리프터 정체)는 '역증가 호기 수' 와 '10대 합의 20분 변화(음수)'
                    #   둘을 같이 본다. 호기별 대기량은 CSV 에 없어서(위 리프터 주석)
                    #   리프터 대기량을 **값으로** 볼 수 있는 건 이 합 하나뿐이다.
                    add_new({"col": "M16HUB_rc_trend", "raw": "M16HUB_rc_trend",
                             "label": "M16HUB 리프터 10대 합 20분 변화", "unit": "대"})

    # PIO — 대표 한 칸
    stack = None
    if has_pio:
        got = _pio_fill([{"col": "pio_10min_cnt"}], pts, fabc)
        stack = next((dict(m, kind="real") for m in got if m.get("pio_stack")), None)
        if stack is None:
            empty.append(("{경로}" + _PIO_SUF, "PIO 반송실패 (창 안에 경로 값이 없음)"))
    if stack is not None:
        names = [x["name"] for x in stack.get("cols") or []]
        if any(x.get("from_reason") for x in stack.get("cols") or []):
            # ★값을 reason 에서 읽은 칸이다 — CSV 컬럼 이름을 적으면 현장에서
            #   찾아가도 그 컬럼에는 0 만 있다. 실제로 읽은 곳을 적는다.
            stack["name"] = stack.get("raw") or "PIO.DEPOSIT.{경로} (reason)"
        else:
            stack["name"] = (names[0] + _PIO_SUF) if len(names) == 1 else _PIO_NAME
        stack["src"] = [x["col"] for x in stack.get("cols") or []]

    # ★CSV 에 그 이름 그대로가 없는 칸 — 구분자만 다른 컬럼을 찾아 읽는다 (_find_col).
    # ★리프터 호기(M16HUB.LFT.{호기}.TOTAL_CURRENTQCNT)는 주피터 발동이벤트 CSV 에
    #   **값 컬럼 자체가 없다** (예측기 EVENT_FIELDS 에 호기별 대기량이 없고, 역증가로
    #   걸린 호기 이름만 {FAB}_rev_lids 에 실린다). 고객(2026-10-07): "리프터 데이터는
    #   왜 안 나오는데 — 2개는 나오는데". 값이 없다고 칸을 지우면 표의 실제지표와
    #   그래프가 또 어긋난다 — 칸은 세우고 **그 호기가 역증가로 걸린 분**을 막대로
    #   그린다. 대기량 값이 아니라는 것은 이름 아랫줄에 적는다.
    #   예측기 CSV 에 호기별 컬럼이 생기면 위의 이름 찾기가 먼저 걸려 값으로 바뀐다.
    keys = set()
    for _t, r in pts:
        keys.update((r or {}).keys())
    for m in real.values():
        if any(c in keys for c in m["src"]):
            continue
        alt = _find_col(m["name"], keys)
        if alt:
            m["src"].append(alt)
            continue
        lm = _LFT_RE.match(str(m["name"]))
        if lm and f"{lm.group(1)}_rev_lids" in keys:
            base = re.sub(r"\s*대기량$", "", str(m.get("label") or f"{lm.group(1)} 리프터 {lm.group(2)}"))
            m.update(lid=lm.group(2), lids_col=f"{lm.group(1)}_rev_lids", bar=True, unit="",
                     label=f"{base} — 역증가로 걸린 분 (대기량 값은 CSV에 없음)")

    # ★누적 건수(4분 초과 건수 등) — 하루 동안 계속 커지는 값이라 선 높이는
    #   '지금 심하다' 가 아니다(룰은 10분 증가를 본다). 이름에 적어 둔다.
    for m in real.values():
        if any(c in cumul for c in m.get("src") or []):
            m["cumul"] = True
            if "누적" not in str(m.get("label") or ""):
                m["label"] = f"{m.get('label') or m['name']} (누적)"
    out_r = list(real.values()) + ([stack] if stack is not None else [])
    keep_r, keep_n = [], []
    for src, dst in ((out_r, keep_r), (list(new.values()), keep_n)):
        for m in src:
            n = sum(1 for _t, r in pts if metric_value(m, r) is not None)
            if n < 2:
                empty.append((m.get("name") or m.get("col"), m.get("label") or ""))
            else:
                dst.append(m)
    return keep_r, keep_n, empty, fallback


def _f(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _text_w(t, size=9.5):
    """글자 폭 어림 — 한글/한자는 라틴의 약 1.7배다.

    ★len(t)*6.2 로 재던 자리가 있는데, 한글이 섞이면 실제 폭의 60% 로 나온다.
      그 값으로 딱지 폭을 잡으면 글자가 배경 밖으로 삐져나온다.
    """
    w = 0.0
    for ch in str(t):
        w += size * (1.0 if ord(ch) > 0x1100 and ord(ch) not in (0x00b7,) else 0.58)
    return w


def _e(s):
    return html.escape(str(s), quote=True)


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def window_rows(rows, center, minutes=60, cfg=None):
    cfg = cfg or load_config()
    tc = cfg.get("amos", {}).get("base_time_col", "datetime")
    half = timedelta(minutes=minutes / 2)
    lo, hi = center - half, center + half
    out = [(parse_dt(r.get(tc)), r) for r in rows]
    out = [(t, r) for t, r in out if t and lo <= t <= hi]
    out.sort(key=lambda x: x[0])
    return out


def _incidents(pts, floor=60):
    """점수가 임계 이상인 연속 구간마다 최고점 1개."""
    out, run = [], []
    for t, r in pts:
        sc = _f(r.get("unified_risk_score")) or 0
        if sc >= floor:
            run.append((t, r, sc))
        elif run:
            out.append(max(run, key=lambda x: x[2]))
            run = []
    if run:
        out.append(max(run, key=lambda x: x[2]))
    return out


def _fab_color(code: str) -> str:
    """FAB 선 색 — fab_score 가 원본이다 (화면·구간 그래프가 같은 색이어야
    한다). 못 불러와도 그래프는 나와야 하니 회색으로 물러선다."""
    try:
        import fab_score
        return fab_score.fab_color(code)
    except Exception:                                  # noqa: BLE001
        return "#8FA0B6"


def _fab_series(pts, fabs, cfg):
    """[(FAB, [(시각, 점수), …]), …] — 체크한 FAB 만, 값이 있는 분만.

    점수는 fab_score.area_table 이 낸다 — 목록·추이 그래프와 **같은 함수**다.
    여기서 따로 계산하면 같은 시각인데 화면마다 다른 수가 나온다.
    """
    codes = [str(f or "").upper() for f in (fabs or []) if str(f or "").strip()]
    if not codes or not pts:
        return []
    try:
        import fab_score
        days = sorted({t.strftime("%Y%m%d") for t, _r in pts})
        tab = fab_score.area_table([r for _t, r in pts], day=days, cfg=cfg)
    except Exception as e:                             # noqa: BLE001
        print(f"[GRAPH] ⚠️ FAB 점수 계산 실패 — 선을 뺍니다: {e}")
        return []
    order = [c for c in tab.get("fabs", []) if c in codes]   # 설정 순서를 따른다
    out = []
    for c in order:
        series = []
        for t, _r in pts:
            got = tab["rows"].get(t.replace(second=0, microsecond=0).isoformat())
            v = (got or {}).get("s", {}).get(c)
            if v is not None:
                series.append((t, float(v)))
        if series:
            out.append((c, series))
    return out


# ══ 구간 그래프 — 임계 대비로 읽는 격자 ══════════════════════════
# ★2026-09 전면 개편. 그 전에는 지표를 세로로 쌓고 패널마다 자기
#   min~max 로 정규화했다. 그러면 임계의 0.9배(정상)인 값이 2.5배
#   (심각)인 값과 똑같이 꽉 차 보여서, 그래프를 봐도 어디를 봐야
#   할지 알 수 없었다. 색은 '넘었다' 는 뜻으로만 쓰고, 안 넘은 것은
#   회색으로 죽이고, 배수 큰 순으로 깐다.
#   높이도 1054px(지표 6개)에서 680px 로 줄었다 — 모달이 92vh 라
#   전에는 늘 스크롤이었다.

def thresholds() -> dict:
    """{csv컬럼: (임계, 부등호, 이름, 단위)} — 룰 원본에서 읽는다.

    ★한 컬럼에 임계가 둘인 경우가 있다 (반송시간 9.0 / 지속 6.62). 룰 정의
      순서가 앞선 쪽(본 임계)을 쓴다 — 낮은 쪽을 쓰면 늘 '넘음' 으로 뜬다.
    """
    try:
        import fab_score as F
    except Exception:
        return {}
    order = {r["code"]: i for i, r in enumerate(F.RULES)}
    best: dict = {}
    for src in (F.WATCH, {"_ALL": F.WATCH_ALL}):
        for _fab, rules in (src or {}).items():
            for code, specs in (rules or {}).items():
                for sp in specs or []:
                    c = sp.get("csv")
                    if not c or sp.get("thr") is None or sp.get("record_only"):
                        continue
                    k = order.get(code, 99)
                    if c not in best or k < best[c][0]:
                        best[c] = (k, sp["thr"], sp.get("op", ">="),
                                   sp.get("label"), sp.get("unit"))
    return {c: v[1:] for c, v in best.items()}


def _ratio(v, thr, op):
    """임계 대비 배수. 작을수록 나쁜 지표(<=)는 뒤집어 잰다."""
    if v is None or not thr:
        return None
    try:
        v, thr = float(v), float(thr)
    except (TypeError, ValueError):
        return None
    if thr == 0:
        return None
    return (thr / v) if (op in ("<=", "<") and v) else (v / thr)



HEAD_H = 30          # 제목 줄
LBL_H = 18           # 섹션 라벨 줄 — 제목과 겹치지 않게 자리를 따로 준다
SCORE_H = 170        # 스코어 패널
AXIS_H = 16          # 시간축 글자 줄
PAD = 16
GAP = 10
# ══ 지표 가로줄 — 스코어처럼 한 줄에 하나 ══════════════════════════════
# ★고객(2026-10-07): "실제지표 더블클릭하면 데이터 표시가 되야지 — 가로줄 스코어 처럼" ·
#   "신규 지표도 마찬가지" · "거기 실제지표 가로줄 검은색줄로 표시가 되야지 — 그게
#   없으니까 헷갈리네". 예전엔 3열 작은 칸(스파크라인)이라 시각이 스코어와 안 맞고,
#   더블클릭한 분이 어디인지 표시가 없었다.
#   이제 지표마다 스코어처럼 **가로 전체 폭** 한 줄 — 스코어와 **같은 시간축**이라
#   위아래로 같은 분이 같은 자리에 온다. 더블클릭한 분은 스코어처럼 세로선을 긋고,
#   그 분 값 높이에 **가로줄**(흰 배경이면 검정 — 스코어의 고른 분 색)을 긋고,
#   오른쪽 위에 그 분 값을 적는다.
PANEL_H = 112        # 지표 한 줄 높이
PANEL_TOP = 46       # 그 안에서 그림이 시작하는 자리 (위 두 줄은 이름)
PANEL_BOT = 10       # 그림 아래 여백
PANEL_GAP = 8


def _nice_ceil(v: float) -> float:
    """눈금 맨 위 — 23.62 같은 값 대신 25 처럼 읽기 쉬운 수로 올린다."""
    if v <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(v))
    for f in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if v <= f * e * (1 + 1e-9):
            return f * e
    return 10 * e


def _tick_txt(v) -> str:
    """왼쪽 눈금 글자 — 자리가 좁다(테두리~그림 사이). 1000 이 넘으면 k 로 줄인다."""
    v = float(v)
    if abs(v) >= 1000:
        return _fmt(round(v / 1000, 1)) + "k"
    return _fmt(round(v, 2))


def _badge(o, x, y, ratio, color, dim):
    """배수 배지 — 넘은 것만 색. '몇 배' 는 한 칸에서 제일 먼저 읽혀야 한다."""
    if ratio is None:
        return
    over = ratio >= 1.0
    txt = ("▲%.1f배" % ratio) if over else ("%.1f배" % ratio)
    w = _text_w(txt, 10.5) + 12
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="17" rx="8.5" '
             f'fill="{color}" opacity="{0.16 if over else 0.10}"/>')
    o.append(f'<text x="{x + w / 2:.1f}" y="{y + 12.3:.1f}" font-size="10.5" '
             f'font-weight="700" text-anchor="middle" '
             f'fill="{color if over else dim}">{_e(txt)}</text>')
    return w


def _hpanel(o, x, y, w, h, m, pts, P, X, L, R, si):
    """지표 가로줄 하나 — 이름 두 줄 · 배수 · 최고/임계 · 스코어와 같은 시간축 그림 ·
    더블클릭한 분 (세로선 + 그 분 값 높이의 가로줄 + 값)."""
    thr = m.get("thr")
    _PATH_COLORS = P["path"]
    unit = m.get("unit") or ""
    # ★pts 와 같은 번호로 읽는다 — 그래야 X 가 스코어 패널과 같은 분을 가리킨다
    vals = [metric_value(m, r) for _t, r in pts]
    have = [(i, v) for i, v in enumerate(vals) if v is not None]
    if not have:
        return
    # 리프터 호기 칸(값 대신 '역증가로 걸린 분' — metric_sets 주석)은 1/0 을 말로 적는다
    lid = bool(m.get("lid"))
    fv = (lambda v: "걸림" if v else "안 걸림") if lid else (lambda v: f"{_fmt(v)}{unit}")
    # ★배지(배수)는 구간 최악값으로 잰다 — 같은 값을 '최고' 로 적어 서로 맞춘다
    ratio = m.get("ratio")
    worst = m.get("worst")
    if worst is None:
        worst = have[-1][1]
    at = next((pts[i][0] for i, v in have if v == worst), None)
    over = ratio is not None and ratio >= 1.0
    nhit = sum(1 for _i, v in have if v) if lid else 0
    if lid:
        over = nhit > 0                  # 그 룰이 이 호기를 짚었다 — 넘은 것과 같이 칠한다
    # ★색은 '넘었다' 는 뜻으로만. 안 넘은 줄은 회색으로 죽인다
    color = (P["crit"] if (ratio or 0) >= 2 else P["evt"]) if over else P["tx3"]
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
             f'fill="{P["bg2"]}" stroke="{P["line"]}"/>')
    if over:
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" '
                 f'rx="1.5" fill="{color}"/>')

    # ── 1줄: 컬럼 이름(굵게) ············ 더블클릭한 분 · 그 값 ──────────
    # ★윗줄 = 실시간 표 '실제지표' 칸에 뜨는 그 이름, 아랫줄 = 한글 이름 (2026-10-06)
    name = str(m.get("name") or m.get("raw") or m["col"])
    sv = vals[si] if 0 <= si < len(vals) else None
    sel_txt = f"{pts[si][0]:%H:%M} · " + (fv(sv) if sv is not None else "값 없음")
    sel_w = _text_w(sel_txt, 12) * 1.05
    room = (w - 24) - sel_w - 16
    fs = 11.5
    while fs > 10 and _text_w(name, fs) * 1.05 > room:
        fs -= 0.5
    shown = name
    while shown and _text_w(shown, fs) * 1.05 > room:
        shown = shown[1:]
    if shown != name:
        shown = "…" + shown[1:]
    tip = f'<title>{_e(name)}</title>' if shown != name else ""
    # class="mname" — 줄을 컬럼 이름으로 찾는 쪽(시험·화면 검색)이 이걸로 집는다
    o.append(f'<text class="mname" x="{x + 12:.1f}" y="{y + 19:.1f}" font-size="{fs:g}" '
             f'font-weight="700" fill="{P["tx"] if over else P["tx2"]}" '
             f'font-family="Consolas,monospace">{_e(shown)}{tip}</text>')
    # 더블클릭한 분의 값 — 스코어 패널의 '고른 분' 과 같은 색. 마우스를 대면 같은
    # 자리에 그 분 값이 덮어 뜬다 (호버 글자에 바탕이 깔린다)
    # ★12px — 칸 제목(11.5/700)과 같은 모양이면 제목을 세는 쪽(시험)이 둘로 센다
    o.append(f'<text class="msel" x="{x + w - 12:.1f}" y="{y + 19:.1f}" font-size="12" '
             f'font-weight="700" text-anchor="end" fill="{P["sel"]}" '
             f'font-family="Consolas,monospace">{_e(sel_txt)}</text>')

    # ── 2줄: 배수 · 한글 이름 · (PIO 범례) ········ 최고값 @시각 · 임계 ─────
    bw = _badge(o, x + 12, y + 25, ratio, color, P["tx3"]) or 0
    right = []                                   # (글자, 크기, 굵기, 색) — 오른쪽부터
    if lid:
        first = next((pts[i][0] for i, v in have if v), None)
        if first is not None:
            right.append((f" 처음 @{first:%H:%M}", 9.5, 400, P["tx3"]))
        right.append((f"{nhit}분 걸림" if nhit else "이 구간 안 걸림", 14, 800,
                      color if over else P["tx2"]))
    else:
        if thr:
            right.append((f" · 임계 {_fmt(thr)}{unit}", 10, 400, P["tx3"]))
        if at is not None:
            right.append((f" 최고 @{at:%H:%M}", 9.5, 400, P["tx3"]))
        right.append((f"{_fmt(worst)}{unit}", 14, 800, color if over else P["tx2"]))
    rx_ = x + w - 12
    for txt, size, wt, cc in right:
        o.append(f'<text x="{rx_:.1f}" y="{y + 38:.1f}" font-size="{size:g}" '
                 f'font-weight="{wt}" text-anchor="end" fill="{cc}" '
                 f'font-family="Consolas,monospace">{_e(txt)}</text>')
        rx_ -= _text_w(txt, size) * 1.05
    lb = str(m.get("label") or "")
    stack = m.get("cols") if m.get("pio_stack") else None
    if stack:
        # 경로 목록은 범례가 맡는다 — 괄호만 떼고 뒤('· 10분 누적' 같은 단위)는 남긴다
        lb = re.sub(r"\s*\([^)]*\)", "", lb)
    lbx = x + 12 + (bw + 7 if bw else 0)
    full = lb
    while lb and lbx + _text_w(lb, 10.5) * 1.08 > rx_ - 12:
        lb = lb[:-1]
    ltip = f'<title>{_e(full)}</title>' if lb != full else ""
    # class="mlbl" — 줄을 한글 이름으로 찾는 쪽(시험·화면 검색)이 이걸로 집는다
    o.append(f'<text class="mlbl" x="{lbx:.1f}" y="{y + 37.5:.1f}" '
             f'font-size="10.5" fill="{P["tx2"]}">{_e(lb)}{ltip}</text>')

    # ── 그림 — 0 과 임계×2 사이로 **모든 줄이 같은 자로** 잰다 ──────────
    # ★줄마다 자기 min~max 로 재면 정상인 값도 꽉 차 보인다. 임계를 기준으로 재야
    #   위아래 줄끼리 비교가 된다.
    pt, pb = y + PANEL_TOP, y + h - PANEL_BOT
    vmax = max(v for _i, v in have)
    vmin = min(v for _i, v in have)
    if lid:
        lo, hi = 0.0, 1.0
    else:
        hi = float(thr) * 2 if thr else 0.0
        if vmax * 1.05 > hi:
            # 맨 위 눈금이 23.62 처럼 읽히지 않게 둥근 수로 올린다
            hi = _nice_ceil(vmax * 1.05)
        # ★음수도 그린다 — 리프터 합 20분 변화(rc_trend)·증가량(rb_diff)은 줄면 음수다.
        #   0 아래를 바닥에 붙여 버리면 '줄었다' 가 '0 이다' 로 읽힌다.
        lo = -_nice_ceil(-vmin * 1.05) if vmin < 0 else 0.0
        hi = hi or 1.0
    Y = lambda v: pb - (pb - pt) * ((min(max(v, lo), hi) - lo) / (hi - lo))  # noqa: E731
    y0 = Y(0.0)                                   # 0 의 높이 (음수가 없으면 바닥)
    # 눈금 — 스코어 패널처럼 왼쪽에 (맨 위 값 · 임계 · 0 · 맨 아래 음수)
    tick = lambda v, yy: o.append(  # noqa: E731
        f'<text x="{L - 5:.1f}" y="{yy + 3.5:.1f}" font-size="9" text-anchor="end" '
        f'fill="{P["tx3"]}" font-family="Consolas,monospace">{_e(v)}</text>')
    if not lid:
        tick(_tick_txt(hi), pt)
        if (thr and lo <= float(thr) <= hi and abs(Y(float(thr)) - pt) > 10
                and abs(Y(float(thr)) - y0) > 10):
            tick(_tick_txt(thr), Y(float(thr)))
        if abs(y0 - pt) > 10:
            tick("0", y0)
        if lo < 0 and abs(pb - y0) > 10:
            tick(_tick_txt(lo), pb)
    n = len(pts)
    if m.get("bar"):
        bwd = max(1.4, min(7.0, (R - L) / max(1, n) - 0.8))
        if stack:
            # ★경로마다 색을 달리해 쌓는다 — 합쳐 한 색으로 그리면 **어느 경로에서
            #   실패했는지**(조치 지점)가 사라진다. 막대 높이가 그 분의 총 개수다.
            cmap = {sp["name"]: _PATH_COLORS[k % len(_PATH_COLORS)]
                    for k, sp in enumerate(stack)}
            lmap = {sp["name"]: (sp.get("legend") or sp["name"]) for sp in stack}
            for i, _v in have:
                r = pts[i][1] or {}
                base = pb
                for sp in stack:
                    # CSV 가 원칙, reason 은 대체 — _pio_val 이 그 규칙이다
                    v = _pio_val(r, sp) or 0
                    if v <= 0:
                        continue
                    hh = max(1.0, pb - Y(v))
                    o.append(f'<rect x="{X(i) - bwd / 2:.1f}" y="{base - hh:.1f}" '
                             f'width="{bwd:.1f}" height="{hh:.1f}" '
                             f'fill="{cmap[sp["name"]]}" opacity="0.95"/>')
                    base -= hh
            # 색만으로 경로를 구분하게 두지 않는다 — 한글 이름 뒤에 이름을 같이 적는다.
            # ★굵은 대문자(M16HUB<-M14A)는 _text_w 보다 1.27배 넓다 (브라우저에서 잰 값)
            lx = lbx + _text_w(lb, 10.5) * 1.08 + 14
            for nm, cc in cmap.items():
                nm = lmap.get(nm, nm)
                tw = _text_w(nm, 8.5) * 1.3 + 13
                if lx + tw > rx_ - 12:
                    break               # 오른쪽 숫자를 침범하느니 범례를 줄인다
                o.append(f'<rect x="{lx:.1f}" y="{y + 30.5:.1f}" width="7" height="7" '
                         f'rx="1.5" fill="{cc}"/>')
                o.append(f'<text x="{lx + 10:.1f}" y="{y + 37.5:.1f}" font-size="8.5" '
                         f'fill="{cc}" font-weight="700">{_e(nm)}</text>')
                lx += tw + 4
        else:
            for i, v in have:
                if v == 0:
                    continue
                hh = max(1.0, abs(y0 - Y(v)))
                o.append(f'<rect x="{X(i) - bwd / 2:.1f}" y="{min(y0, Y(v)) if v < 0 else y0 - hh:.1f}" '
                         f'width="{bwd:.1f}" height="{hh:.1f}" rx="1.2" fill="{color}" '
                         f'opacity="{0.95 if over else 0.5}"/>')
    else:
        # 값이 빈 분은 선을 끊는다 — 없는 값을 잇지 않는다
        segs, cur = [], []
        for i, v in enumerate(vals):
            if v is None:
                if cur:
                    segs.append(cur)
                cur = []
            else:
                cur.append((i, v))
        if cur:
            segs.append(cur)
        for seg in segs:
            d = " ".join(f"{'M' if k == 0 else 'L'}{X(i):.1f},{Y(v):.1f}"
                         for k, (i, v) in enumerate(seg))
            if len(seg) > 1:
                # 면적은 10% 워시 — 진하게 채우면 선이 안 보인다
                o.append(f'<path d="{d} L{X(seg[-1][0]):.1f},{y0:.1f} '
                         f'L{X(seg[0][0]):.1f},{y0:.1f} Z" '
                         f'fill="{color}" opacity="{0.10 if over else 0.06}"/>')
            o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round" '
                     f'opacity="{1 if over else 0.65}"/>')
    if thr and lo <= float(thr) <= hi:
        ty = Y(float(thr))
        o.append(f'<line x1="{L:.1f}" y1="{ty:.1f}" x2="{R:.1f}" '
                 f'y2="{ty:.1f}" stroke="{P["crit"]}" stroke-width="1" opacity=".55"/>')
    o.append(f'<line x1="{L:.1f}" y1="{pb:.1f}" x2="{R:.1f}" '
             f'y2="{pb:.1f}" stroke="{P["line"]}" stroke-width="1"/>')
    if lo < 0:
        o.append(f'<line x1="{L:.1f}" y1="{y0:.1f}" x2="{R:.1f}" y2="{y0:.1f}" '
                 f'stroke="{P["tx3"]}" stroke-width=".8" stroke-dasharray="2 3" opacity=".7"/>')
    # ── 더블클릭한 분 — 스코어 패널과 같은 세로선 + 그 분 값 높이의 가로줄 ──
    sx = X(si)
    o.append(f'<line class="gsel" x1="{sx:.1f}" y1="{pt - 4:.1f}" x2="{sx:.1f}" '
             f'y2="{pb:.1f}" stroke="{P["sel"]}" stroke-width="1.4"/>')
    if sv is not None:
        sy = Y(sv)
        if not lid:      # 걸림/안 걸림 칸은 높이가 값이 아니다 — 세로선과 점만
            o.append(f'<line class="gsel" x1="{L:.1f}" y1="{sy:.1f}" x2="{R:.1f}" y2="{sy:.1f}" '
                     f'stroke="{P["sel"]}" stroke-width="1.1" stroke-dasharray="6 3" opacity=".9"/>')
        o.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="4" fill="{P["bg"]}" '
                 f'stroke="{P["sel"]}" stroke-width="2.2"/>')
    _hpanel_hover(o, x, y, w, h, m, vals, pts, X, L, R, unit, P, color, fv)


# 한 띠가 이보다 좁으면 마우스로 집을 수가 없다 — 분을 묶는다.
HIT_MIN_W = 6.0


def _readout(o, rx, ry, txt):
    """'시각 · 값' 한 줄 — **늘 같은 자리**에 뜬다.

    ★마우스를 따라다니는 말풍선을 쓰지 않는다. 눈이 글자를 쫓아가느라
      정작 그래프를 못 본다. 자리가 고정이면 거기만 보면 된다.
    ★글자 모양(색·크기·테두리)은 전부 <style> 규칙이다. 칸마다 속성을 적으면
      히트가 수백 개라 파일이 두 배가 된다. 색은 바깥 <g> 에서 물려받는다.
    """
    # ★SVG <text> 는 줄바꿈을 안 먹는다. 여러 줄이면 글자를 따로 세워야 한다
    #   — 그냥 넣으면 한 줄로 이어 붙어서 무슨 말인지 알 수가 없다.
    lines = [x.strip() for x in str(txt).split("\n")]
    wid = max((_text_w(x, 10.5) for x in lines), default=0) + 12
    o.append(f'<rect class="hvr" x="{rx - wid:.0f}" y="{ry - 11:.0f}" '
             f'width="{wid:.0f}" height="{4 + 14 * len(lines):.0f}" rx="4"/>')
    for k, line in enumerate(lines):
        o.append(f'<text class="hvt" x="{rx - 6:.0f}" y="{ry + k * 14:.0f}">'
                 f'{_e(line)}</text>')


def _hpanel_hover(o, x, y, w, h, m, vals, pts, X, L, R, unit, P, color=None, fv=None):
    """줄 위에 분마다 투명한 띠를 깔고, 마우스를 대면 그 분 값을 오른쪽 위에 띄운다.

    ★자바스크립트를 안 쓴다 — 서버가 그려 보내는 SVG 라 과거 조회·리포트에 그대로
      붙어 나가도 똑같이 돈다. 말풍선(<title>)도 안 쓴다 (1초 늦고 금방 사라진다).
    ★띠가 HIT_MIN_W 보다 좁아지면 분을 묶는다 (180분 창). 묶은 띠는 그 구간의
      **최고값**을 말한다 — 배지가 최고값으로 재는 것과 같은 자다.
    ★data-at 을 실어 **누르면 그 분이 고정**된다 — 스코어 패널과 같은 동작.
    """
    n = len(pts)
    if n < 2:
        return
    stk = m.get("cols") if m.get("pio_stack") else None
    op = m.get("op", ">=")
    thr = m.get("thr")
    hi = op in (">=", ">")
    step = max(1, math.ceil(n / max(1.0, (R - L) / HIT_MIN_W)))
    for i in range(0, n, step):
        grp = [(pts[j][0], vals[j], pts[j][1]) for j in range(i, min(i + step, n))
               if vals[j] is not None]
        if not grp:
            continue
        best = max(grp, key=lambda g: g[1]) if hi else min(grp, key=lambda g: g[1])
        lx = L if i == 0 else (X(i) + X(i - 1)) / 2
        rx = R if i + step >= n else (X(i + step - 1) + X(min(i + step, n - 1))) / 2
        when = (f"{grp[0][0]:%H:%M}" if len(grp) == 1
                else f"{grp[0][0]:%H:%M}~{grp[-1][0]:%H:%M} 최고")
        # ★임계값을 띠마다 다시 적지 않는다 — 넘었는지만 ▲ 한 글자로
        over = thr and ((best[1] >= float(thr)) if hi else (best[1] <= float(thr)))
        val = fv(best[1]) if fv else f"{_fmt(best[1])}{unit}"
        tip = f"{when} · {val}{' ▲' if over else ''}"
        if stk:
            # 쌓은 줄은 합만 보여 주면 '어느 경로냐' 가 안 남는다 — 조치 지점이다
            part = [(sp.get("legend") or sp["name"], _pio_val(best[2] or {}, sp) or 0)
                    for sp in stk]
            part = [f"{nm} {_fmt(v)}" for nm, v in part if v]
            if part:
                tip += "\n" + " · ".join(part)
        o.append(f'<g class="hv" fill="{color}"><rect class="ghit" '
                 f'data-at="{_e(best[0].isoformat())}" '
                 f'x="{lx:.0f}" y="{y + PANEL_TOP - 6:.0f}" '
                 f'width="{max(1.0, rx - lx):.0f}" height="{h - PANEL_TOP - PANEL_BOT + 6:.0f}"/>')
        # 오른쪽 위 — 평소엔 '더블클릭한 분 값' 이 있는 자리. 호버하는 동안만 덮는다
        _readout(o, x + w - 12, y + 19, tip)
        o.append("</g>")


def render(rows, center, minutes=60, width=1000, cfg=None, fabs=None,
           theme="dark") -> str:
    """구간 그래프 — 스코어 패널 + 지표 줄 (스코어처럼 가로 전체 폭, 같은 시간축).

    fabs 를 주면 그 FAB 의 영역점수를 스코어 패널에 겹쳐 그린다. 화면의 추이
    그래프에서 체크한 것이 그대로 넘어온다 — 추이에서 켜 놓고 더블클릭했는데
    여기서 사라지면 같은 걸 두 번 골라야 한다.

    theme 은 dark/light/navy/contrast. 화면 배경을 바꿔도 그래프만 검게 남으면
    거기만 눈이 아프다.

    ★2026-09 전면 개편 — 무엇이 달라졌는지는 위 블록 주석에.
      바뀌지 않은 것: 함수 서명, 분마다 호버, 사건 딱지, FAB 겹쳐보기.
    """
    from sentinel import grade_cuts, load_config, summarize_reason
    cfg = cfg or load_config()
    P = _pal(theme)
    pts = window_rows(rows, center, minutes, cfg)
    if not pts:
        return (f'<div style="padding:28px;color:{P["tx2"]};font-size:13px">'
                f'이 구간에 자료가 없습니다</div>')

    # ── 지표 모으기 + 배수 재기 ───────────────────────────────────────
    sel = min(pts, key=lambda tr: abs((tr[0] - center).total_seconds()))
    # ★어느 FAB 화면인지는 **행에서** 읽는다 (서명을 못 바꾼다 — row_fab 주석).
    # ★실시간 표 '실제지표' 칸에 뜨는 컬럼을 **전부** 세우고, 우리가 계산해 만든
    #   컬럼(rb_diff 등)은 '신규 지표' 로 따로 깐다 — metric_sets 주석.
    # ★값이 하나도 없거나 딱 한 점뿐이면 칸을 안 만든다. 빈 칸을 그리면
    #   높이만 먹고 아무 말도 안 한다. 대신 **왜 안 보이는지**는 아래에
    #   한 줄로 남긴다 — 그냥 지우기만 하면 "왜 안 뜨나" 에 답이 없다.
    fabc = row_fab(sel[1])
    real, new, empty, fallback = metric_sets(pts, sel[1], fabc)
    TH, THR = thresholds(), _watch_raw()[2]
    sections = []
    for title, sub, ms in (
            ("실제지표", (f"이 분은 발동한 룰이 없어 {fabc} 룰 컬럼" if fallback
                          else "그 분 실시간 표 '실제지표' 칸 그대로"), real),
            ("신규 지표", "그 룰이 본 계산 컬럼", new)):
        ms = [_measure(m, pts, TH, THR) for m in ms]
        ms.sort(key=lambda m: -(m["sort"] if m.get("sort") is not None
                                else (m["ratio"] or 0)))
        sections.append((title, sub, ms))
    # ★실제지표는 늘 첫 줄에 선다 — 비었어도 "없다" 를 말해야 한다.
    #   신규 지표는 칸이 있을 때만 (ALL 화면은 대개 없다).
    sections = [s for k, s in enumerate(sections) if k == 0 or s[2]]

    # ── 자리 잡기 ─────────────────────────────────────────────────────
    incs = _incidents(pts, floor=grade_cuts(cfg)[1])
    chip_h = 17 if incs else 0
    y_slbl = HEAD_H + LBL_H
    top_s = y_slbl + 6 + chip_h
    y_axis = top_s + SCORE_H + AXIS_H
    # ★지표는 스코어처럼 **한 줄에 하나, 가로 전체 폭** (PANEL_* 주석). 예전 3열
    #   작은 칸은 시간축이 스코어와 달라 '그 분' 을 위아래로 맞춰 볼 수가 없었다.
    lay, y = [], y_axis + 22
    for title, sub, ms in sections:
        lay.append((y, y + 10, title, sub, ms))
        # 줄이 없으면 '없다' 한 줄 자리만 (30px)
        y = y + 10 + (len(ms) * (PANEL_H + PANEL_GAP) - PANEL_GAP if ms else 30) + 22
    y_end = y - 22
    # 맨 아래 시간축 — 줄이 여럿이면 스코어 밑 시간축은 스크롤 위로 사라진다
    y_bax = y_end + AXIS_H if any(s[4] for s in lay) else None
    height = (y_bax or y_end) + PAD + (14 if empty else 0)

    o = [f'<svg viewBox="0 0 {width} {height:.0f}" width="100%" '
         f'style="display:block" role="img" xmlns="http://www.w3.org/2000/svg">',
         # ★fill/커서를 인라인으로 적으면 히트 영역 하나당 50자가 더 붙는다.
         #   칸마다 분 단위 히트를 깔면서 수백 개가 됐다 — 규칙으로 뺀다.
         # ★말풍선을 안 쓴다. 브라우저 기본 <title> 은 1초쯤 늦게 뜨고 마우스를
         #   조금만 움직이면 사라졌다 다시 센다 — 지표 그래프를 훑으며 값을
         #   읽는 데는 못 쓴다. 자바스크립트도 안 쓴다(리포트·저장한 SVG 에서도
         #   그대로 돌아야 한다). 칸마다 '시각 · 값' 글자를 미리 그려 두고
         #   **그 칸에 마우스가 오면 그것만 보이게** 한다. CSS 한 줄이면 된다.
         f'<style>.ghit{{fill:{P["tx"]};fill-opacity:0;cursor:pointer}}'
         f'.hv:hover .ghit{{fill-opacity:.07}}'
         f'.hv .hvt,.hv .hvr{{opacity:0}}'
         f'.hv:hover .hvt{{opacity:1}}.hv:hover .hvr{{opacity:.97}}'
         # ★글자 모양은 전부 여기 한 줄로 모은다. 히트가 수백 개라 칸마다
         #   font·색을 적으면 파일이 두 배가 된다 (색만 바깥 <g> 에서 물려받음).
         # ★바탕을 깐다. 처음엔 글자에 배경색 테두리만 둘렀는데, 글자 **사이**는
         #   안 덮여서 밑에 있던 '임계 3.3분' 이 비쳤다 — 눈으로 보고 알았다.
         f'.hvt{{font:700 10.5px Consolas,monospace;text-anchor:end}}'
         f'.hvr{{fill:{P["bg2"]}}}</style>',
         f'<rect width="100%" height="100%" fill="{P["bg"]}"/>']

    # ── 제목 ─────────────────────────────────────────────────────────
    r0 = sel[1]
    sc = _f(r0.get("unified_risk_score"))
    bands = [(lo, hi, nm, c) for (lo, hi, c), nm
             in zip(_bands_of(cfg, P), ("정상", "경계", "위험", "초위험"))]
    lvl, lvc = "정상", P["tx2"]
    for lo, hi, nm, c in bands:
        if sc is not None and lo <= sc <= hi:
            lvl, lvc = nm, c
    o.append(f'<text x="{PAD}" y="21" font-size="13.5" font-weight="700" '
             f'fill="{P["tx"]}">{_e(sel[0].strftime("%Y-%m-%d %H:%M"))}'
             f'<tspan fill="{P["tx3"]}" font-weight="400"> · </tspan>'
             f'<tspan fill="{P["tx2"]}">{_e(r0.get("hot_area") or "")}</tspan>'
             f'<tspan fill="{P["tx3"]}" font-weight="400" font-size="11">'
             f'  {_e(pts[0][0].strftime("%H:%M"))}~{_e(pts[-1][0].strftime("%H:%M"))}'
             f'</tspan></text>')
    if sc is not None:
        # ★정상일 때 lvc 는 흐린 회색이라, 그대로 쓰면 제일 큰 글자가 제일
        #   안 읽힌다. 알약만 등급색으로 깔고 숫자는 본문색으로 쓴다.
        txt, sub2 = f"{sc:.0f}", f" {lvl}"
        bw2 = _text_w(txt, 20) + _text_w(sub2, 12) + 24
        o.append(f'<rect x="{width - PAD - bw2:.1f}" y="3" width="{bw2:.1f}" '
                 f'height="25" rx="12.5" fill="{lvc}" opacity="0.18" '
                 f'stroke="{lvc}" stroke-opacity="0.45"/>')
        o.append(f'<text x="{width - PAD - 12:.1f}" y="21.5" font-size="20" '
                 f'font-weight="800" text-anchor="end" fill="{P["tx"]}" '
                 f'font-family="Consolas,monospace">{txt}'
                 f'<tspan font-size="12" font-weight="700" fill="{P["tx2"]}">'
                 f'{_e(sub2)}</tspan></text>')

    # ── 스코어 패널 ───────────────────────────────────────────────────
    # ★지표 줄도 **이 L · R · X 를 그대로** 쓴다 — 위아래로 같은 분이 같은 자리.
    #   R 을 테두리(width-PAD)에서 조금 들인다. 끝 분이 테두리 위에 겹쳐 안 보였다.
    L, R = PAD + 40, width - PAD - 12
    pw = R - L
    SY = lambda v: top_s + SCORE_H * (1 - max(0.0, min(100.0, v)) / 100.0)
    n = len(pts)
    X = lambda i: L + pw * (i / max(1, n - 1))
    at = {t: i for i, (t, _r) in enumerate(pts)}
    o.append(f'<text x="{PAD}" y="{y_slbl + chip_h:.1f}" font-size="10.5" '
             f'font-weight="700" fill="{P["tx2"]}">스코어'
             f'<tspan fill="{P["tx3"]}" font-weight="400" font-size="9.5" '
             f'font-family="Consolas,monospace">  unified_risk_score</tspan></text>')
    for lo, hi, nm, c in bands:
        y1, y2 = SY(min(hi, 100)), SY(lo)
        o.append(f'<rect x="{L}" y="{y1:.1f}" width="{pw:.1f}" height="{y2 - y1:.1f}" '
                 f'fill="{c}" opacity="0.10"/>')
        if lo:
            o.append(f'<line x1="{L}" y1="{y2:.1f}" x2="{R}" y2="{y2:.1f}" '
                     f'stroke="{c}" stroke-width="1" opacity="0.30"/>')
            o.append(f'<text x="{L - 5}" y="{y2 + 3.5:.1f}" font-size="9.5" '
                     f'text-anchor="end" fill="{P["tx3"]}" '
                     f'font-family="Consolas,monospace">{lo:g}</text>')
    o.append(f'<line x1="{L}" y1="{top_s + SCORE_H:.1f}" x2="{R}" '
             f'y2="{top_s + SCORE_H:.1f}" stroke="{P["line"]}"/>')

    # 체크한 FAB 의 영역점수 — 본선보다 먼저, 더 가늘게
    fab_lines = _fab_series(pts, fabs, cfg)
    for code, series in fab_lines:
        if len(series) < 2:
            continue
        fd = " ".join(f"{'M' if k == 0 else 'L'}{X(at[t]):.1f},{SY(v):.1f}"
                      for k, (t, v) in enumerate(series) if t in at)
        o.append(f'<path d="{fd}" fill="none" stroke="{_fab_color(code)}" '
                 f'stroke-width="1.2" opacity="0.9"/>')

    sv = [(i, _f(r.get("unified_risk_score"))) for i, (_t, r) in enumerate(pts)]
    sv = [(i, v) for i, v in sv if v is not None]
    if sv:
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(i):.1f},{SY(v):.1f}"
                     for k, (i, v) in enumerate(sv))
        o.append(f'<path d="{d}" fill="none" stroke="{P["score"]}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')

    # ── 분마다 호버 ───────────────────────────────────────────────────
    # ★마우스를 대면 **그 자리에** '시각 · 점수 · 등급 · 주 영역' 이 한 줄로
    #   뜬다. 말풍선(<title>)은 안 쓴다 — 1초쯤 늦게 뜨고, 마우스를 조금만
    #   움직여도 사라졌다 다시 센다. 선을 따라 훑으며 값을 읽을 수가 없다.
    # ★발동 룰까지 여기 적지 않는다. 한 줄로 안 들어가고, 그건 **눌러서**
    #   고정한 표가 제대로 보여 준다 (data-at 이 그 길이다).
    hw = max(3.0, pw / max(1, n))
    for i, (t, r) in enumerate(pts):
        v = _f(r.get("unified_risk_score"))
        lv2, lc2 = "", P["tx"]
        for lo, hi, nm, c2 in bands:
            if v is not None and lo <= v <= hi:
                lv2, lc2 = nm, (P["tx"] if nm == "정상" else c2)
        ho = (r.get("hot_area") or "").strip()
        tip = (f"{t:%H:%M} · {'—' if v is None else f'{v:.0f}점'} {lv2}"
               + (f" · {ho}" if ho else "")).rstrip()
        # ★첫 줄은 '시각 · 값' 이다 — 그게 훑으면서 읽으려는 것이다.
        #   발동 룰은 **둘째 줄**로 내린다. 빼 버리면 "왜 이 점수냐" 가 호버에서
        #   사라져, 매번 눌러서 표를 열어야 한다.
        #   CSV 의 reason 은 기계 글자라 그대로 못 쓴다 — 화면 목록과 같은
        #   한글 요약(summarize_reason)을 쓴다.
        rs = summarize_reason(str(r.get("reason") or "").strip(), ho)
        if rs:
            while rs and _text_w(rs, 10.5) > pw * 0.72:
                rs = rs[:-1]
            tip += "\n" + rs
        o.append(f'<g class="hv" fill="{lc2}"><rect class="ghit" '
                 f'data-at="{_e(t.isoformat())}" '
                 f'x="{X(i) - hw / 2:.0f}" y="{top_s}" width="{hw:.0f}" '
                 f'height="{SCORE_H}"/>')
        _readout(o, width - PAD, top_s + 15, tip)
        o.append("</g>")

    # ── 사건 표시 ─────────────────────────────────────────────────────
    # ★딱지는 스코어 패널 **위** 줄에 둔다. 밴드(붉은 띠) 위에 맨 글자를 얹으면
    #   같은 계열이라 안 읽혀서, 배경 깔린 알약으로 그린다.
    used = []
    for k, (it, ir, isc) in enumerate(incs, 1):
        if it not in at:
            continue
        x = X(at[it])
        o.append(f'<line x1="{x:.1f}" y1="{top_s}" x2="{x:.1f}" '
                 f'y2="{top_s + SCORE_H:.1f}" stroke="{P["evt"]}" stroke-width="1" '
                 f'stroke-dasharray="4 3" opacity="0.8"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{SY(isc):.1f}" r="3.4" fill="{P["evt"]}"/>')
        lb = f'사건{k} {isc:.0f}점 @{it:%H:%M}'
        lw = _text_w(lb, 9.5) + 12
        x1 = max(L, min(R - lw, x - lw / 2))
        # 앞 딱지와 겹치면 오른쪽으로 민다 — 줄을 늘리면 그림이 다시 길어진다
        for ux1, ux2 in used:
            if x1 < ux2 + 4 and x1 + lw > ux1 - 4:
                x1 = min(R - lw, ux2 + 5)
        used.append((x1, x1 + lw))
        ty = y_slbl + chip_h - 4
        o.append(f'<g style="cursor:help"><title>{_e(f"사건{k} · {it:%H:%M} · {isc:.0f}점")}'
                 f'</title><rect x="{x1:.1f}" y="{ty - 12:.1f}" width="{lw:.1f}" '
                 f'height="15" rx="4" fill="{P["bg"]}" stroke="{P["evt"]}" '
                 f'stroke-width="0.9"/><text x="{x1 + lw / 2:.1f}" y="{ty - 1:.1f}" '
                 f'font-size="9.5" font-weight="700" text-anchor="middle" '
                 f'fill="{P["evt"]}">{_e(lb)}</text></g>')

    # ── 고른 시각 ─────────────────────────────────────────────────────
    si = at[sel[0]]
    o.append(f'<line x1="{X(si):.1f}" y1="{top_s}" x2="{X(si):.1f}" '
             f'y2="{top_s + SCORE_H:.1f}" stroke="{P["sel"]}" stroke-width="1.4"/>')
    if sc is not None:
        o.append(f'<circle cx="{X(si):.1f}" cy="{SY(sc):.1f}" r="5" fill="{P["bg"]}" '
                 f'stroke="{P["sel"]}" stroke-width="2.4"/>')
    # ★고른 분이 창 **끝**이면(실시간 화면은 늘 마지막 분이다) 고른 시각과 끝 시각이
    #   한자리에 겹쳐 '23:2344' 로 읽혔다. 가까우면 양끝 글자를 빼고, 고른 시각은
    #   칸 밖으로 안 나가게 그쪽 끝에 맞춘다.
    sx = X(si)
    near_l, near_r = sx - L < 44, R - sx < 44
    anchor, ax = (("start", L) if sx - L < 16 else ("end", R) if R - sx < 16
                  else ("middle", sx))

    def time_axis(ya):
        """시작 · 고른 분 · 끝 — 스코어 밑과 맨 아래(지표 줄 밑) 두 곳에 같은 모양으로."""
        if not near_l:
            o.append(f'<text x="{L}" y="{ya:.1f}" font-size="9.5" fill="{P["tx3"]}" '
                     f'font-family="Consolas,monospace">{_e(pts[0][0].strftime("%H:%M"))}</text>')
        o.append(f'<text x="{ax:.1f}" y="{ya:.1f}" font-size="9.5" '
                 f'text-anchor="{anchor}" fill="{P["sel"]}" font-weight="700" '
                 f'font-family="Consolas,monospace">{_e(sel[0].strftime("%H:%M"))}</text>')
        if not near_r:
            o.append(f'<text x="{R}" y="{ya:.1f}" font-size="9.5" text-anchor="end" '
                     f'fill="{P["tx3"]}" font-family="Consolas,monospace">'
                     f'{_e(pts[-1][0].strftime("%H:%M"))}</text>')
    time_axis(y_axis)

    # FAB 범례 — 색만으로 구분하게 두지 않는다
    if fab_lines:
        # ★시간축 줄에 두면 가운데 시각(선택한 분)과 겹친다. 스코어 패널
        #   안 왼쪽 위 빈자리로 옮긴다 — 선 색을 바로 옆에서 대조하게 된다.
        lx = L + 6
        ly = top_s + 13
        for code, _s in fab_lines:
            c = _fab_color(code)
            o.append(f'<rect x="{lx:.1f}" y="{ly - 4:.1f}" width="10" height="3" '
                     f'rx="1.5" fill="{c}"/>')
            o.append(f'<text x="{lx + 14:.1f}" y="{ly:.1f}" font-size="9.5" '
                     f'fill="{c}" font-weight="700">{_e(code)}</text>')
            lx += 24 + _text_w(code, 9.5)
        # 무슨 값을 그린 선인지 — 색과 이름만으로는 'M16HUB 의 무엇' 인지 모른다
        o.append(f'<text x="{lx + 2:.1f}" y="{ly:.1f}" font-size="9" '
                 f'fill="{P["tx3"]}" font-family="Consolas,monospace">area_score</text>')

    # ── 지표 줄 — 실제지표 / 신규 지표 ───────────────────────────────
    # ★고객(2026-10-06): "실제지표로 따로 신규지표로 따로". 두 묶음을 위아래로,
    #   묶음마다 '임계 넘은 것부터'. 줄마다 스코어와 같은 시간축(PANEL_* 주석).
    # ★예전 ALL 화면은 '발동 지표' 라고 불렀다. 이제 ALL 도 실시간 표 '실제지표'
    #   칸의 컬럼을 그대로 세우므로 이름도 같다.
    for y_lbl, y_grid, title, sub, ms in lay:
        nover = sum(1 for m in ms if (m["ratio"] or 0) >= 1)
        o.append(f'<text x="{PAD}" y="{y_lbl:.1f}" font-size="10.5" font-weight="700" '
                 f'fill="{P["tx2"]}">{title} '
                 f'<tspan fill="{P["tx3"]}" font-weight="400">— {sub} · 임계 넘은 것부터 · '
                 f'{nover}/{len(ms)}개 넘음</tspan></text>')
        if not ms:
            o.append(f'<text x="{PAD}" y="{y_grid + 20:.1f}" font-size="12" '
                     f'fill="{P["tx3"]}">이 구간에 그릴 {title}가 없습니다</text>')
        for k, m in enumerate(ms):
            _hpanel(o, PAD, y_grid + k * (PANEL_H + PANEL_GAP), width - PAD * 2,
                    PANEL_H, m, pts, P, X, L, R, si)
    if y_bax:
        time_axis(y_bax)
    if empty:
        # ★컬럼 이름으로 적는다 — 칸 윗줄과 같은 이름이라야 "그 칸이 왜 없나" 가
        #   바로 이어진다. 한글 이름은 괄호로. 한 줄을 넘으면 '외 N개' 로 접고,
        #   접었을 때만 말풍선에 전부 싣는다.
        items = [f"{n} ({lb})" if lb and lb != n else str(n) for n, lb in empty]
        head = "값이 안 온 컬럼 — "
        room = width - PAD * 2 - _text_w(head, 9.5) - _text_w(" 외 99개", 9.5)
        shown, used = [], 0.0
        for it in items:
            w = _text_w(it + " · ", 9.5)
            if shown and used + w > room:
                break
            shown.append(it)
            used += w
        more = len(items) - len(shown)
        tip = f'<title>{_e(" · ".join(items))}</title>' if more else ""
        o.append(f'<text x="{PAD}" y="{height - 8:.1f}" font-size="9.5" '
                 f'fill="{P["tx3"]}">{_e(head + " · ".join(shown))}'
                 f'{_e(f" 외 {more}개") if more else ""}{tip}</text>')
    o.append("</svg>")
    return "".join(o)


def _measure(m: dict, pts, TH: dict, THR: dict) -> dict:
    """칸 하나 — 임계·부등호·구간 최악값·배수를 잰다.

    ★임계는 CSV 컬럼(thresholds) → 원본 컬럼(_watch_raw) 순서로 찾는다. 실시간
      표가 원본 이름으로만 싣는 컬럼(MLUD 잡·MAXCAPA 등)도 임계선이 서야 한다.
    ★diff10(누적 건수의 10분 증가) 같은 룰의 임계는 긋지 않는다 — 누적값을
      그 임계로 나누면 배수가 거짓이 된다.
    """
    thr, op = None, ">="
    for c in m.get("src") or [m.get("col")]:
        if c in TH:
            thr, op = TH[c][0], TH[c][1] or ">="
            break
        if c in THR:
            thr, op = THR[c][0], THR[c][1]
            break
    if op not in _CMP_OPS:
        thr, op = None, ">="
    vs = [v for v in (metric_value(m, r) for _t, r in pts) if v is not None]
    m = dict(m, thr=thr, op=op)
    # ★배수는 **구간 최악값**으로 잰다. 마지막 값으로 재면 이미 지나간
    #   급증이 회색으로 죽어서, 방금 무슨 일이 있었는지가 안 보인다.
    worst = (max(vs) if op in (">=", ">") else min(vs)) if vs else None
    m["ratio"] = _ratio(worst, thr, op)
    m["worst"] = worst
    if m.get("pio_score") and worst is not None:
        # ★임계가 없으니 배수도 없다. 그대로 두면 정렬에서 맨 뒤로 밀려
        #   '10점(상위 1%)' 인데 화면 맨 아래에 처박힌다. 명세가 준 여섯
        #   칸을 자리값으로 쓴다 — 8점부터 걸린 지표들 사이로 올라온다.
        m["sort"] = _pio_band(worst)[1] / 5.0 * 1.5
    return m
