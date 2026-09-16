#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 구간 그래프 (독립 SVG 렌더러)

발동이벤트_요약 / report_graphs 와 같은 형식으로 그린다:

  ┌ 스코어 패널 ─ unified_risk_score, 등급 밴드(60/71/85), 사건 표시
  ├ 지표 패널 1 ─ M16HUB 반송시간 (분)
  │               M16HUB.QUE.TIME.AVGTOTALTIME1MIN   ← 실제 raw 컬럼
  │               범위 3.82~19.32분
  ├ 지표 패널 2 ─ …
  └ X축 (시각)

지표는 최고점 reason 에서 뽑는다. 각 패널은 자기 축을 가진다.
데모스를 import 하지 않고 외부 라이브러리도 쓰지 않는다(순수 SVG).
"""
from __future__ import annotations

import html
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

    for m in re.finditer(r"(M16HUB|M14B|M16A|M16B|M14)\s*\[(.*?)\]", body):
        area, inner = m.group(1), m.group(2)
        if "AVGTOTALTIME1MIN" in inner or "AVGLOADTIME1MIN" in inner or "R-A" in inner:
            add(f"{area}_ra", _RA.get(area, f"{area}.QUE.TIME.AVGTOTALTIME1MIN"),
                f"{area} 반송시간", "분")
        if "FAB저장" in inner:
            add("M16HUB_rd_fab", _FAB, "M16HUB FAB저장율", "%")
        if re.search(r"\bSTB", inner):
            # R-D 판정에서 빠진 값이다 (2026-08) — 기록용임을 이름에 남긴다
            add("M16HUB_stb_util", _STB, "M16HUB STB저장율 (기록용)", "%")
        if "OHT=" in inner or "OHT가동" in inner:
            add(f"{area}_rd_oht", f"{area}.QUE.OHT.OHTUTIL", f"{area} OHT가동률", "%")
        if "R-C" in inner:
            add("M16HUB_rev_count", _REV, "M16HUB 리프터 정체", "회")
        if "SLA(" in inner or "4분초과" in inner:
            add(f"sla_{area}", f"{area}.QUE.ALL.TRANSPORT4MINOVERRATIO", f"{area} 4분초과율", "%")
        if "SORT(" in inner or "소터" in inner:
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

    ★한 컬럼에 임계가 둘인 경우가 있다 (반송시간 9.0 / 지속 6.3). 룰 정의
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
CELL_H = 124
COLS = 3
PAD = 16
GAP = 10


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


def _cell(o, x, y, w, h, m, pts, P, X0):
    """지표 한 칸 — 배지 · 이름 · 값/임계 · 스파크라인 + 임계선."""
    col, thr, op = m["col"], m.get("thr"), m.get("op", ">=")
    _PATH_COLORS = P["path"]
    unit = m.get("unit") or ""
    stk = m.get("cols") if m.get("pio_stack") else None
    cols = m.get("sumcols") or [col]
    def _v(r):
        got = ([_pio_val(r, x) for x in stk] if stk
               else [_f(r.get(c)) for c in cols])
        got = [g for g in got if g is not None]
        return sum(got) if got else None
    vals = [(t, _v(r)) for t, r in pts]
    vals = [(t, v) for t, v in vals if v is not None]
    if not vals:
        return
    # ★배지(배수)는 구간 최악값으로 재는데 값만 마지막 것을 적으면 서로
    #   어긋난다 ("7.7배 / 20개"). 같은 값을 보여 준다 — 최악값과 그 시각.
    ratio = m.get("ratio")
    cur = m.get("worst", vals[-1][1])
    at = next((t for t, v in vals if v == cur), None)
    over = ratio is not None and ratio >= 1.0
    # ★색은 '넘었다' 는 뜻으로만. 안 넘은 칸은 회색으로 죽인다 —
    #   지금 화면이 전부 빨간 이유가 이걸 안 해서다.
    color = (P["crit"] if (ratio or 0) >= 2 else P["evt"]) if over else P["tx3"]
    band = ""
    if m.get("pio_score"):
        # PIO 점수는 임계가 없다 (구간표가 잠정이라 선을 안 긋는다). 대신
        # 명세 6장의 여섯 칸을 색으로 쓴다 — 0 회색 → 10 빨강.
        band, bi = _pio_band(cur)
        color = (P["tx3"], P["tx2"], P["palette"][2], P["evt"], P["evt"],
                 P["crit"])[bi]
        over = bi >= 3          # 5점(상위 10%) 부터는 눈에 띄어야 한다
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
             f'fill="{P["bg2"]}" stroke="{P["line"]}"/>')
    if over:
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" '
                 f'rx="1.5" fill="{color}"/>')
    if band:
        bw = _text_w(band, 9) + 12
        o.append(f'<rect x="{x + 12:.1f}" y="{y + 11:.1f}" width="{bw:.1f}" '
                 f'height="15" rx="7.5" fill="{color}" '
                 f'opacity="{0.20 if over else 0.13}"/>')
        o.append(f'<text x="{x + 12 + bw / 2:.1f}" y="{y + 22:.1f}" font-size="9" '
                 f'text-anchor="middle" font-weight="700" fill="{color}">'
                 f'{_e(band)}</text>')
    else:
        bw = _badge(o, x + 12, y + 11, ratio, color, P["tx3"]) or 0
    lb = str(m.get("label") or "")
    stk0 = m.get("cols") if m.get("pio_stack") else None
    if stk0:
        # 경로 목록은 범례가 맡는다 — 괄호만 떼고 뒤는 남긴다.
        # ★split(" (")[0] 로 자르면 뒤에 붙은 '· 10분 누적' 까지 날아간다.
        #   그건 단위 표시라 없으면 1분 개수로 읽혀 열 배로 잘못 본다.
        lb = re.sub(r"\s*\([^)]*\)", "", lb)
    lbx = x + 12 + bw + 8
    full = lb
    # ★범례 자리를 미리 빼 두면 경로가 넷일 때 이름표가 통째로 잘린다.
    #   이름표를 먼저 온전히 두고, 범례가 들어갈 만큼만 들어가게 한다
    #   (아래 범례 루프가 이름표를 만나면 멈춘다).
    room = (x + w - 12) - lbx
    while lb and _text_w(lb, 11.5) > room:
        lb = lb[:-1]
    # ★<title> 은 **잘렸을 때만** 붙인다. 늘 붙이면 안 잘린 칸에도 말풍선이
    #   하나 더 생겨, 글자를 찾는 쪽(시험·검색)이 본문 대신 말풍선을 집는다.
    tip = f'<title>{_e(m.get("label") or "")}</title>' if lb != full else ""
    o.append(f'<text x="{lbx:.1f}" y="{y + 23.5:.1f}" font-size="11.5" '
             f'font-weight="700" fill="{P["tx"] if over else P["tx2"]}">'
             f'{_e(lb)}{tip}</text>')
    # ★실제 AMOS 컬럼명 — 현장에서 이걸 보고 원 지표를 찾아간다. 이름표만
    #   있으면 "그게 어느 컬럼이냐" 를 다시 물어야 한다. 칸이 좁으면 앞을
    #   자르고 뒤(컬럼 이름)를 남긴다 — 뒤쪽이 무엇을 재는지를 말한다.
    raw = str(m.get("raw") or "")
    if raw:
        avail = w - 24
        shown = raw
        while shown and _text_w(shown, 9) > avail:
            shown = shown[1:]
        if shown != raw:
            shown = "…" + shown[1:]
        o.append(f'<text x="{x + 12:.1f}" y="{y + 37:.1f}" font-size="9" '
                 f'fill="{P["tx3"]}" font-family="Consolas,monospace">'
                 f'{_e(shown)}{"<title>" + _e(raw) + "</title>" if shown != raw else ""}</text>')
    o.append(f'<text x="{x + 12:.1f}" y="{y + 56:.1f}" font-size="14" '
             f'font-weight="800" fill="{color if over else P["tx2"]}" '
             f'font-family="Consolas,monospace">{_e(_fmt(cur))}{_e(unit)}</text>')
    if at is not None:
        o.append(f'<text x="{x + 12 + _text_w(_fmt(cur) + unit, 14) + 7:.1f}" '
                 f'y="{y + 56:.1f}" font-size="9.5" fill="{P["tx3"]}" '
                 f'font-family="Consolas,monospace">최고 @{at:%H:%M}</text>')
    if thr:
        o.append(f'<text x="{x + w - 12:.1f}" y="{y + 56:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{P["tx3"]}" '
                 f'font-family="Consolas,monospace">임계 {_e(_fmt(thr))}{_e(unit)}</text>')

    # 스파크라인 — 0 과 임계×2 사이로 **모든 칸이 같은 자로** 잰다.
    # ★여기가 현행과 갈리는 자리다. 칸마다 자기 min~max 로 재면 정상인 값도
    #   꽉 차 보인다. 임계를 기준으로 재야 칸끼리 비교가 된다.
    pt, pb = y + 66, y + h - 12
    lo, hi = 0.0, (float(thr) * 2 if thr else max(v for _t, v in vals) or 1.0)
    hi = max(hi, max(v for _t, v in vals) * 1.05, 1e-9)
    Y = lambda v: pb - (pb - pt) * ((min(max(v, lo), hi) - lo) / (hi - lo))
    n = len(vals)
    X = lambda i: x + 12 + (w - 24) * (i / max(1, n - 1))
    if m.get("bar"):
        bwd = max(1.4, min(7.0, (w - 24) / max(1, n) - 0.8))
        stack = m.get("cols") if m.get("pio_stack") else None
        if stack:
            # ★경로마다 색을 달리해 쌓는다. 합쳐 한 색으로 그리면 **어느
            #   경로에서 실패했는지**가 사라지는데, 그게 조치 지점이다.
            cmap = {x["name"]: _PATH_COLORS[k % len(_PATH_COLORS)]
                    for k, x in enumerate(stack)}
            # 범례 글자는 꾸민 이름(×2/×1)이 있으면 그걸 쓴다
            lmap = {x["name"]: (x.get("legend") or x["name"]) for x in stack}
            for i, (t, _tot) in enumerate(vals):
                r = pts[i][1] if i < len(pts) else {}
                base = pb
                for sp in stack:          # ★x 로 쓰면 칸 좌표를 덮는다
                    # CSV 가 원칙, reason 은 대체 — _pio_val 이 그 규칙이다
                    v = _pio_val(r, sp) or 0
                    if v <= 0:
                        continue
                    hh = max(1.0, pb - Y(v))
                    o.append(f'<rect x="{X(i) - bwd / 2:.1f}" y="{base - hh:.1f}" '
                             f'width="{bwd:.1f}" height="{hh:.1f}" '
                             f'fill="{cmap[sp["name"]]}" opacity="0.95"/>')
                    base -= hh
            # 색만으로 경로를 구분하게 두지 않는다 — 이름을 같이 적는다
            lx = x + w - 12
            for name, cc in reversed(list(cmap.items())):
                name = lmap.get(name, name)
                tw = _text_w(name, 8.5) + 13
                if lx - tw < lbx + _text_w(lb, 11.5) + 8:
                    break               # 이름표를 침범하느니 범례를 줄인다
                lx -= tw
                o.append(f'<rect x="{lx:.1f}" y="{y + 16:.1f}" width="7" height="7" '
                         f'rx="1.5" fill="{cc}"/>')
                o.append(f'<text x="{lx + 10:.1f}" y="{y + 22.5:.1f}" font-size="8.5" '
                         f'fill="{cc}" font-weight="700">{_e(name)}</text>')
                lx -= 4
        else:
            for i, (_t, v) in enumerate(vals):
                if v <= 0:
                    continue
                hh = max(1.0, pb - Y(v))
                o.append(f'<rect x="{X(i) - bwd / 2:.1f}" y="{pb - hh:.1f}" '
                         f'width="{bwd:.1f}" height="{hh:.1f}" rx="1.2" fill="{color}" '
                         f'opacity="{0.95 if over else 0.5}"/>')
    else:
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}"
                     for i, (_t, v) in enumerate(vals))
        # 면적은 10% 워시 — 현행 20% 는 칸을 덩어리로 만들어 선이 안 보인다
        o.append(f'<path d="{d} L{X(n - 1):.1f},{pb:.1f} L{X(0):.1f},{pb:.1f} Z" '
                 f'fill="{color}" opacity="{0.10 if over else 0.06}"/>')
        o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round" '
                 f'opacity="{1 if over else 0.65}"/>')
        o.append(f'<circle cx="{X(n - 1):.1f}" cy="{Y(vals[-1][1]):.1f}" r="4" '
                 f'fill="{color}" stroke="{P["bg2"]}" stroke-width="2"/>')
    if thr and lo <= float(thr) <= hi:
        ty = Y(float(thr))
        o.append(f'<line x1="{x + 12:.1f}" y1="{ty:.1f}" x2="{x + w - 12:.1f}" '
                 f'y2="{ty:.1f}" stroke="{P["crit"]}" stroke-width="1" opacity=".55"/>')
    o.append(f'<line x1="{x + 12:.1f}" y1="{pb:.1f}" x2="{x + w - 12:.1f}" '
             f'y2="{pb:.1f}" stroke="{P["line"]}" stroke-width="1"/>')




def render(rows, center, minutes=60, width=1000, cfg=None, fabs=None,
           theme="dark") -> str:
    """구간 그래프 — 스코어 패널 + 지표 격자.

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
    TH = thresholds()
    sel = min(pts, key=lambda tr: abs((tr[0] - center).total_seconds()))
    seen, metrics, empty = set(), [], []
    # ★reason 은 그 10분에 **가장 많이 실패한 한 경로**만 적어 온다. 데이터로
    #   나머지를 채우는 _pio_fill 을 **버리기 전에** 부른다 — 뒤에 부르면
    #   판단 근거(pio_10min_cnt)가 이미 버려져 칸이 통째로 사라진다.
    # ★어느 FAB 화면인지는 **행에서** 읽는다 (서명을 못 바꾼다 — row_fab 주석).
    #   ALL 이면 "" 이고, 그때는 지금까지와 한 글자도 다르지 않게 돈다.
    fabc = row_fab(sel[1])
    mets = _pio_fill(parse_reason_metrics(sel[1].get("reason") or "", fabc),
                     pts, fabc)
    mets = _pio_score_cell(mets, pts, fabc)
    for m in mets:
        c = m["col"]
        if c in seen:
            continue
        seen.add(c)
        # ★PIO 주 경로는 raw 가 'PIO.DEPOSIT.{경로}' 라는 자리표다. 현장에서
        #   찾아갈 수 없는 이름이라 실제 컬럼명으로 바꿔 적고, 값도 그 컬럼들의
        #   합으로 잰다 (첫 경로만 그리면 나머지가 화면에서 사라진다).
        sub = [x["col"] for x in (m.get("cols") or [])] if m.get("pio_stack") else None
        if sub:
            # ★raw 는 **실제로 읽은 곳**이어야 한다. reason 에서 읽은 칸에
            #   CSV 컬럼명을 적으면 현장에서 찾아가도 그 컬럼이 없다.
            from_reason = any(x.get("from_reason") for x in (m.get("cols") or []))
            m = dict(m, sumcols=sub,
                     raw=m.get("raw") if from_reason else " + ".join(sub))
            c = sub[0]
        cs = m.get("sumcols") or [c]
        vs = []
        for _t, r in pts:
            # ★경로 묶음은 _pio_val 로 읽는다 — 1분 컬럼이 창 내내 0 이면
            #   _pio_fill 이 reason 에서 읽는 칸으로 바꿔 끼우는데,
            #   CSV 만 보면 그 칸이 통째로 0 이 되어 버려진다.
            got = ([_pio_val(r, x) for x in m["cols"]] if sub
                   else [_f(r.get(k)) for k in cs])
            got = [x for x in got if x is not None]
            if got:
                vs.append(sum(got))
        # ★값이 하나도 없거나 딱 한 점뿐이면 칸을 안 만든다. 빈 칸을 그리면
        #   높이만 먹고 아무 말도 안 한다. 대신 **왜 안 보이는지**는 아래에
        #   한 줄로 남긴다 — 그냥 지우기만 하면 "왜 안 뜨나" 에 답이 없다.
        if len(vs) < 2:
            empty.append(m.get("label") or c)
            continue
        thr, op, _lb, _un = TH.get(c, (None, ">=", None, None))
        m = dict(m, thr=thr, op=op)
        # ★배수는 **구간 최악값**으로 잰다. 마지막 값으로 재면 이미 지나간
        #   급증이 회색으로 죽어서, 방금 무슨 일이 있었는지가 안 보인다.
        worst = max(vs) if op in (">=", ">") else min(vs)
        m["ratio"] = _ratio(worst, thr, op)
        m["worst"] = worst
        if m.get("pio_score"):
            # ★임계가 없으니 배수도 없다. 그대로 두면 정렬에서 맨 뒤로 밀려
            #   '10점(상위 1%)' 인데 화면 맨 아래에 처박힌다. 명세가 준 여섯
            #   칸을 자리값으로 쓴다 — 8점부터 걸린 지표들 사이로 올라온다.
            m["sort"] = _pio_band(worst)[1] / 5.0 * 1.5
        metrics.append(m)
    metrics.sort(key=lambda m: -(m["sort"] if m.get("sort") is not None
                                 else (m["ratio"] or 0)))

    # ── 자리 잡기 ─────────────────────────────────────────────────────
    incs = _incidents(pts, floor=grade_cuts(cfg)[1])
    # ★지표가 한둘인데 3열로 깔면 오른쪽 3분의 2 가 빈 자리로 남는다.
    #   열 수를 지표 수에 맞춰 줄여 칸을 넓게 쓴다.
    ncol = max(1, min(COLS, len(metrics) or 1))
    rowsn = (len(metrics) + ncol - 1) // ncol
    cw = (width - PAD * 2 - GAP * (ncol - 1)) / ncol
    chip_h = 17 if incs else 0
    y_slbl = HEAD_H + LBL_H
    top_s = y_slbl + 6 + chip_h
    y_axis = top_s + SCORE_H + AXIS_H
    y_mlbl = y_axis + 22
    y_grid = y_mlbl + 10
    height = y_grid + rowsn * (CELL_H + GAP) - (GAP if rowsn else 0) + PAD

    o = [f'<svg viewBox="0 0 {width} {height:.0f}" width="100%" '
         f'style="display:block" role="img" xmlns="http://www.w3.org/2000/svg">',
         '<style>.ghit:hover{fill-opacity:.07}</style>',
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
    L, R = PAD + 30, width - PAD
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
    # ★서버가 그린 SVG 라 <title> 이 곧 툴팁이다(JS 없이 뜬다). 선이 1px 라도
    #   손이 닿게 히트 영역을 칸 폭만큼 넓게 깐다. data-at 은 화면이 클릭으로
    #   그 분을 집을 때 쓴다.
    hw = max(3.0, pw / max(1, n))
    for i, (t, r) in enumerate(pts):
        v = _f(r.get("unified_risk_score"))
        lv2 = next((nm for lo, hi, nm, _c in bands
                    if v is not None and lo <= v <= hi), "")
        ln = [f"{t:%H:%M}  {'' if v is None else f'{v:.0f}점'} {lv2}".rstrip()]
        ho = (r.get("hot_area") or "").strip()
        if ho:
            ln.append(f"주 영역 {ho}")
        ft = (r.get("predicted_fault_type") or "").strip()
        if ft:
            ln.append(f"예측 {ft}")
        # ★발동 룰은 **한글 요약**으로 준다. CSV 의 reason 은
        #   "hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C,...]" 같은 기계
        #   글자다. 그걸 통째로 뿌리면 읽을 것이 아니라 덮는 것이 된다 —
        #   화면 목록이 쓰는 summarize_reason 과 같은 글을 쓴다.
        rs = summarize_reason(str(r.get("reason") or "").strip(), ho)
        if rs:
            ln += [x.strip() for x in rs.split(" · ") if x.strip()]
        o.append(f'<rect class="ghit" data-at="{_e(t.isoformat())}" '
                 f'x="{X(i) - hw / 2:.1f}" y="{top_s}" width="{hw:.1f}" '
                 f'height="{SCORE_H}" fill="{P["tx"]}" fill-opacity="0" '
                 f'style="cursor:pointer"><title>{_e(chr(10).join(ln))}</title></rect>')

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
    o.append(f'<text x="{L}" y="{y_axis:.1f}" font-size="9.5" fill="{P["tx3"]}" '
             f'font-family="Consolas,monospace">{_e(pts[0][0].strftime("%H:%M"))}</text>')
    o.append(f'<text x="{X(si):.1f}" y="{y_axis:.1f}" font-size="9.5" '
             f'text-anchor="middle" fill="{P["sel"]}" font-weight="700" '
             f'font-family="Consolas,monospace">{_e(sel[0].strftime("%H:%M"))}</text>')
    o.append(f'<text x="{R}" y="{y_axis:.1f}" font-size="9.5" text-anchor="end" '
             f'fill="{P["tx3"]}" font-family="Consolas,monospace">'
             f'{_e(pts[-1][0].strftime("%H:%M"))}</text>')

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

    # ── 지표 격자 ─────────────────────────────────────────────────────
    nover = sum(1 for m in metrics if (m["ratio"] or 0) >= 1)
    o.append(f'<text x="{PAD}" y="{y_mlbl:.1f}" font-size="10.5" font-weight="700" '
             f'fill="{P["tx2"]}">발동 지표 '
             f'<tspan fill="{P["tx3"]}" font-weight="400">— 임계 넘은 것부터 · '
             f'{nover}/{len(metrics)}개 넘음</tspan></text>')
    if not metrics:
        o.append(f'<text x="{PAD}" y="{y_grid + 22:.1f}" font-size="12" '
                 f'fill="{P["tx3"]}">이 분에 발동한 지표가 없습니다</text>')
    for k, m in enumerate(metrics):
        cx = PAD + (k % ncol) * (cw + GAP)
        cy = y_grid + (k // ncol) * (CELL_H + GAP)
        _cell(o, cx, cy, cw, CELL_H, m, pts, P, X)
    if empty:
        o.append(f'<text x="{PAD}" y="{height - 6:.1f}" font-size="9.5" '
                 f'fill="{P["tx3"]}">값이 안 온 컬럼 — {_e(" · ".join(empty))}</text>')
    o.append("</svg>")
    return "".join(o)
