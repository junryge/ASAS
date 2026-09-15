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


def parse_reason_metrics(reason: str) -> list[dict]:
    """reason → [{col, raw, label, unit}] (등장 순서, 중복 제거, M16_PKT/M16_WT 제외)."""
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
        if paths:
            names = " · ".join(x["name"] for x in paths)
            out.append({"col": paths[0]["col"], "raw": "PIO.DEPOSIT.{경로}",
                        "label": f"PIO 주 경로 ({names})", "unit": "개",
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


def _pio_paths_in(pts) -> list[str]:
    """창 안에서 **실제로 실패가 온** PIO 경로 — 구간 합이 많은 순.

    0 과 빈칸은 세지 않는다. 12경로 중 평소 값이 나오는 건 3개뿐이라,
    0 인 경로까지 쌓으면 범례만 길어지고 막대는 그대로다.
    """
    tot: dict[str, float] = {}
    for _t, r in pts:
        for k, v in (r or {}).items():
            if not isinstance(k, str) or not k.endswith(_PIO_SUF):
                continue
            f = _f(v)
            if f:
                name = k[:-len(_PIO_SUF)]
                tot[name] = tot.get(name, 0.0) + f
    return [p for p, _n in sorted(tot.items(), key=lambda x: (-x[1], x[0]))]


def _pio_label(names: list[str]) -> str:
    head = " · ".join(names[:3])
    more = f" 외 {len(names) - 3}" if len(names) > 3 else ""
    return f"PIO 주 경로 ({head}{more})"


def _pio_fill(metrics: list[dict], pts) -> list[dict]:
    """'PIO 주 경로' 패널을 창 안 데이터로 다시 만든다.

    ★reason 에 PIO 가 없으면 손대지 않는다. PIO 컬럼이 실려 온다는 이유만으로
      아무 그래프에나 패널을 하나 더 붙이면, 늘 보던 화면이 바뀐다.
    """
    idx = next((i for i, m in enumerate(metrics) if m.get("pio_stack")), -1)
    has_pio = any(m.get("col") == "pio_10min_cnt" for m in metrics)
    if idx < 0 and not has_pio:
        return metrics
    found = _pio_paths_in(pts)[:_PIO_STACK_MAX]
    if found:
        cols = [{"col": p + _PIO_SUF, "name": p} for p in found]
        md = {"col": cols[0]["col"], "raw": "PIO.DEPOSIT.{경로}",
              "label": _pio_label(found), "unit": "개",
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
        cols = [{"col": p + _PIO_SUF, "name": p, "from_reason": True} for p in names]
        md = {"col": cols[0]["col"], "raw": "PIO.DEPOSIT.{경로} (reason)",
              "label": _pio_label(names) + " · 10분 누적", "unit": "개",
              # 겹쳐 더한 값이라 '구간 합' 을 내면 같은 실패를 열 번 센다
              "bar": True, "rolling": True, "cols": cols, "pio_stack": True}
    if idx >= 0:
        metrics[idx] = md
    else:
        metrics.append(md)
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


def render(rows, center, minutes=60, width=1000, cfg=None, fabs=None,
           theme="dark") -> str:
    """구간 그래프.

    fabs 를 주면 그 FAB 의 영역점수(area_score)를 스코어 패널에 겹쳐 그린다.
    화면의 추이 그래프에서 체크한 것이 그대로 넘어온다 — 추이에서 켜 놓고
    더블클릭했는데 여기서 사라지면 같은 걸 두 번 골라야 한다.

    theme="light" 면 흰 배경용 색으로 그린다. 화면 배경을 흰색으로 바꿔도
    그래프만 검게 남으면 거기만 눈이 아프다.
    """
    # ★모듈 상수를 **지역 이름으로 덮는다**. 아래 f-string 수십 군데가
    #   그대로 지역값을 쓰게 되어, 색 한 벌을 더 넣는 데 그림 코드는
    #   손대지 않는다 (두 벌로 갈라지면 한쪽만 고치게 된다).
    P = _pal(theme)
    _BG, _BG2, _LINE, _GRID = P["bg"], P["bg2"], P["line"], P["grid"]
    _TX, _TX2, _TX3 = P["tx"], P["tx2"], P["tx3"]
    _SCORE_COLOR, _SEL_COLOR = P["score"], P["sel"]
    _EVT_COLOR, _CRIT_COLOR = P["evt"], P["crit"]
    _PATH_COLORS = P["path"]

    def _kc(col, idx):
        return _kind_color(col, idx, P)

    cfg = cfg or load_config()
    pts = window_rows(rows, center, minutes, cfg)
    if not pts:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="110">'
                '<rect width="100%%" height="100%%" fill="%s"/>'
                '<text x="%d" y="60" fill="%s" font-size="14" text-anchor="middle">'
                '해당 구간에 데이터가 없습니다</text></svg>'
                % (width, _BG, width // 2, _TX2))

    from sentinel import grade_cuts
    floor = grade_cuts(cfg)[0]
    t0, t1 = pts[0][0], pts[-1][0]
    span = max(1.0, (t1 - t0).total_seconds())
    incs = _incidents(pts, floor)
    peak_t, peak_r, peak_sc = max(
        ((t, r, _f(r.get("unified_risk_score")) or 0) for t, r in pts), key=lambda x: x[2])
    pts_sc = [(t, r, _f(r.get("unified_risk_score")) or 0) for t, r in pts]
    metrics = parse_reason_metrics(peak_r.get("reason") or "")
    metrics = _pio_fill(metrics, pts)
    # ★값이 두 점도 안 되는 지표는 **패널을 만들지 않는다.** 예전엔 88px 짜리
    #   빈 칸을 그려 놓고 "데이터 없음" 만 적었다 — 그래프가 길어지기만 하고
    #   볼 것은 없다. 대신 어느 컬럼이 안 오는지 한 줄로 밝힌다 (그 사실도
    #   정보다 — 수집이 빠진 것인지 확인해야 하니까).
    def _has_line(md):
        # ★막대(개수)는 한 점이면 충분하다 — 1분에 4개 터진 그 한 점이
        #   정확히 봐야 할 것이라, 선 그래프 기준(2점)으로 자르면 안 된다.
        need = 1 if md.get("bar") else 2
        cols = (md.get("cols") or []) or [{"col": md["col"]}]
        n = 0
        for _t, r in pts:
            if any(_pio_val(r, c) is not None for c in cols):
                n += 1
                if n >= need:
                    return True
        return False

    empty = [m for m in metrics if not _has_line(m)]
    metrics = [m for m in metrics if _has_line(m)]
    area = (peak_r.get("hot_area") or "").strip()

    L, R = 62, 22
    pw = width - L - R
    # ★MET_H 를 88 → 116 으로 키웠다. 지표 이름표를 왼쪽 여백(46px)에 두었는데
    #   '(PIO 반송실패 10분 합(개)' 같은 한글 이름은 150px 라 막대 위로 흘러
    #   나와 둘 다 안 읽혔다. 이름표를 패널 **위 두 줄**로 올리고, 그림 높이
    #   (72px)는 예전 그대로 지키려고 그 두 줄만큼 더 준다.
    SCORE_H, MET_H, GAP = 150, 116, 12

    # ── 사건·최고점 딱지 자리를 **먼저** 잡는다 ──────────────────────
    # ★예전엔 head 를 50 으로 박아 두고 딱지를 text-anchor="middle" 로 그냥
    #   찍었다. 그래서 (a) 구간 끝의 사건은 그림 밖으로 잘리고
    #   ('사건3 76점 @0' 에서 끊김) (b) 사건이 가까우면 글자끼리 포개지고
    #   (c) 최고점이 사건과 같은 분이면 셋이 겹쳤다.
    #   이제 겹치지 않는 줄을 먼저 찾아 두고, 쓴 줄 수만큼 머리 공간을 늘린다.
    def _cx(t):
        return L + pw * ((t - t0).total_seconds() / span)

    _warn, _danger, _crit = grade_cuts(cfg)

    def _tip(head, t, r, sc):
        """마우스 올렸을 때 나오는 글 — SVG <title> 은 브라우저가 그려 준다.

        ★딱지에는 '사건2 119점 @07:35' 만 들어간다(좁아서). 무엇 때문에
          걸린 사건인지는 reason 에 있는데 그림에는 자리가 없다 — 올리면
          보이게 한다. JS 없이 되는 방법이라 서버가 그린 SVG 그대로 쓴다.
        """
        # ★sentinel.grade 를 쓰면 안 된다 — 밴드 최대가 100 이라 그 위(예: 119)는
        #   어느 밴드에도 안 걸려 '정상' 으로 떨어진다. 컷으로 직접 가른다.
        lv = ('\ucd08\uc704\ud5d8' if sc >= _crit else
              '\uc704\ud5d8' if sc >= _danger else
              '\uacbd\uacc4' if sc >= _warn else '\uc815\uc0c1')
        ln = [f'{head} \u00b7 {t:%H:%M}',
              f'\uc810\uc218 {sc:.0f}' + (f' \u00b7 {lv}' if lv else '')]
        a = (r.get("hot_area") or "").strip()
        if a:
            ln.append(f'\uc601\uc5ed {a}')
        rs = str(r.get("reason") or "").strip()
        if rs:
            # reason 은 한 줄로 길다 — 룰 단위로 끊어 읽기 좋게
            for part in [x.strip() for x in re.split(r"\s*;\s*", rs) if x.strip()]:
                ln.append(part)
        return _e("\n".join(ln))

    _chips, _rows_used = [], []       # _rows_used: [(줄, 왼쪽x, 오른쪽x)]

    def _plan(t, text, color, tip=""):
        w = _text_w(text) + 12
        x1 = max(L + 1, min(L + pw - w - 1, _cx(t) - w / 2))   # 패널 밖으로 못 나간다
        row = 0
        while any(r == row and not (x1 + w + 4 < a or x1 > b + 4)
                  for r, a, b in _rows_used):
            row += 1
        _rows_used.append((row, x1, x1 + w))
        _chips.append((row, x1, w, text, color, tip))

    # 최고점을 먼저 — 제일 중요한 딱지라 맨 아랫줄(그래프에 가장 가까운 줄)을
    # 갖고, 사건 딱지가 그 위로 비켜 간다.
    _plan(peak_t, f'\u25b2 \ucd5c\uace0 {peak_sc:.0f}\uc810 \u00b7 {peak_t:%H:%M}'
                  + (f' \u00b7 {_e(area)}' if area else ''), _CRIT_COLOR,
          _tip('\ucd5c\uace0\uc810', peak_t, peak_r, peak_sc))
    for _i, (_it, _ir, _isc) in enumerate(incs, 1):
        _plan(_it, f'\uc0ac\uac74{_i} {_isc:.0f}\uc810 @{_it:%H:%M}', _EVT_COLOR,
              _tip('\uc0ac\uac74%d' % _i, _it, _ir, _isc))

    _chip_rows = max((r for r, *_ in _chips), default=0) + 1
    head = 24 + _chip_rows * 15     # 제목 한 줄 + 딱지 줄 수만큼
    sec_head = 30 if metrics else 0
    top_score = head
    y_met0 = top_score + SCORE_H + 18 + sec_head
    height = y_met0 + (MET_H + GAP) * len(metrics) + 34 + (16 if empty else 0)

    def X(t):
        return L + pw * ((t - t0).total_seconds() / span)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" '
         f'font-family="-apple-system,Segoe UI,Malgun Gothic,sans-serif">',
         f'<rect width="100%" height="100%" fill="{_BG}"/>']

    # ── 제목 ──
    o.append(f'<text x="{L-46}" y="21" font-size="14" font-weight="700" fill="{_TX}">'
             f'📅 {t0:%Y-%m-%d} M16 BR 구간 ({len(incs)}건) · {t0:%H:%M}~{t1:%H:%M}</text>')

    # ── 스코어 패널 ──
    def SY(v):
        return top_score + SCORE_H * (1 - max(0.0, min(100.0, v)) / 100.0)

    bands = _bands_of(cfg, P)
    for lo_, hi_, col in bands:
        y2, y1 = SY(lo_), SY(hi_)
        o.append(f'<rect x="{L}" y="{y1:.1f}" width="{pw}" height="{y2-y1:.1f}" fill="{col}"/>')
    for v in [b[0] for b in bands[1:]] + [100]:
        y = SY(v)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="{_GRID}" '
                 f'stroke-width="0.8" stroke-dasharray="3 3"/>')
        o.append(f'<text x="{L-7}" y="{y+4:.1f}" font-size="10" fill="{_TX2}" '
                 f'text-anchor="end">{v}</text>')

    # ── 체크한 FAB 의 영역점수를 같은 축에 겹쳐 그린다 ──
    # ★본선보다 **먼저** 긋는다. 전체 점수가 위에 있어야 무엇이 기준선인지
    #   흐려지지 않는다. 굵기도 본선(1.6)보다 가늘게(1.15) 한다.
    fab_lines = _fab_series(pts, fabs, cfg)
    for code, series in fab_lines:
        if len(series) < 2:
            continue
        fd = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{SY(v):.1f}"
                      for k, (t, v) in enumerate(series))
        o.append(f'<path d="{fd}" fill="none" stroke="{_fab_color(code)}" '
                 f'stroke-width="1.15" opacity="0.95"/>')

    sv = [(t, _f(r.get("unified_risk_score")) or 0) for t, r in pts]
    d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{SY(v):.1f}" for k, (t, v) in enumerate(sv))
    o.append(f'<path d="{d}" fill="none" stroke="{_SCORE_COLOR}" stroke-width="1.6"/>')

    # ── 사건·최고점 딱지 그리기 (자리는 위에서 이미 잡았다) ──────────
    for _i, (_it, _ir, _isc) in enumerate(incs, 1):
        x = _cx(_it)
        o.append(f'<line x1="{x:.1f}" y1="{top_score}" x2="{x:.1f}" y2="{top_score+SCORE_H}" '
                 f'stroke="{_EVT_COLOR}" stroke-width="1" stroke-dasharray="4 3" opacity="0.85"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{SY(_isc):.1f}" r="3.4" fill="{_EVT_COLOR}"/>')
        # ★마우스 판을 따로 깐다 — 점선은 1px 이라 마우스로 맞히기가 어렵다.
        #   투명한 14px 띠를 얹어 그 구간 어디에 올려도 말풍선이 뜨게 한다.
        _etip = _tip('\uc0ac\uac74%d' % _i, _it, _ir, _isc)
        o.append(f'<rect x="{x-7:.1f}" y="{top_score}" width="14" height="{SCORE_H}" '
                 f'fill="transparent" style="cursor:help">'
                 f'<title>{_etip}</title></rect>')
    # ★칩(배경 깔린 알약)으로 그린다 — 등급 밴드(붉은·주황 띠) 위에 맨 글자를
    #   얹으면 같은 계열 색이라 읽히지 않는다.
    for row, x1, w, text, color, tip in _chips:
        y = top_score - 7 - row * 15
        o.append(f'<g style="cursor:help"><title>{tip}</title>'
                 f'<rect x="{x1:.1f}" y="{y-10:.1f}" width="{w:.1f}" height="14" rx="3.5" '
                 f'fill="{_BG}" stroke="{color}" stroke-width="0.9" opacity="0.97"/>'
                 f'<text x="{x1+w/2:.1f}" y="{y:.1f}" font-size="9.5" fill="{color}" '
                 f'font-weight="700" text-anchor="middle">{text}</text></g>')

    # ── 더블클릭한 시각 표시 (선택 시각 + 그 시각 스코어) ──
    sel_t, sel_r, sel_sc = min(pts_sc, key=lambda x: abs((x[0] - center).total_seconds()))
    sx = X(sel_t)
    o.append(f'<line x1="{sx:.1f}" y1="{top_score}" x2="{sx:.1f}" y2="{top_score+SCORE_H}" '
             f'stroke="{_SEL_COLOR}" stroke-width="1.4" opacity="0.8"/>')
    o.append(f'<circle cx="{sx:.1f}" cy="{SY(sel_sc):.1f}" r="4.6" fill="{_BG}" '
             f'stroke="{_SEL_COLOR}" stroke-width="2.2"/>')
    _lb = f'선택 {sel_t:%H:%M} · {sel_sc:.0f}점'
    _lw = len(_lb) * 6.2 + 12
    _lx = max(L + 2, min(L + pw - _lw - 2, sx - _lw / 2))
    _ly = SY(sel_sc) + (16 if sel_sc > 60 else -30)
    o.append(f'<rect x="{_lx:.1f}" y="{_ly:.1f}" width="{_lw:.1f}" height="19" rx="4" '
             f'fill="{_SEL_COLOR}"/>')
    o.append(f'<text x="{_lx+_lw/2:.1f}" y="{_ly+13.5:.1f}" font-size="10.5" fill="{_BG}" '
             f'font-weight="700" text-anchor="middle">{_e(_lb)}</text>')

    # 스코어 = 실제 컬럼명 명시
    o.append(f'<text x="{L}" y="{top_score+SCORE_H+14:.1f}" font-size="10.5" '
             f'fill="{_SCORE_COLOR}" font-weight="700">스코어</text>')
    o.append(f'<text x="{L+44}" y="{top_score+SCORE_H+14:.1f}" font-size="9.5" fill="{_TX2}" '
             f'font-family="ui-monospace,Menlo,Consolas,monospace">unified_risk_score</text>')

    # ── FAB 범례 — 색만으로 구분하지 않게 이름을 같이 적는다 ──
    if fab_lines:
        lx = L + 190
        for code, series in fab_lines:
            c = _fab_color(code)
            o.append(f'<line x1="{lx}" y1="{top_score+SCORE_H+10.5:.1f}" x2="{lx+13}" '
                     f'y2="{top_score+SCORE_H+10.5:.1f}" stroke="{c}" stroke-width="2.4"/>')
            top = max((v for _t, v in series), default=0)
            txt = f'{code} 최고 {top:.0f}' if series else f'{code} 값 없음'
            o.append(f'<text x="{lx+17}" y="{top_score+SCORE_H+14:.1f}" font-size="9.5" '
                     f'fill="{c}" font-weight="700">{_e(txt)}</text>')
            lx += 22 + len(txt) * 6.0
        o.append(f'<text x="{L}" y="{top_score+SCORE_H+27:.1f}" font-size="9" fill="{_TX2}">'
                 f'가는 선 = 각 FAB 영역점수(area_score) · 굵은 청록 = 전체 점수</text>')

    # ── 지표 섹션 ──
    if metrics:
        o.append(f'<text x="{L-46}" y="{top_score+SCORE_H+40:.1f}" font-size="11" '
                 f'fill="{_TX}" font-weight="700">'
                 f'최고점({peak_t:%H:%M} · {peak_sc:.0f}점{" · " + _e(area) if area else ""}) '
                 f'발동 지표 — 실제 raw 컬럼 {minutes}분 추이</text>')

    for i, md in enumerate(metrics):
        y = y_met0 + (MET_H + GAP) * i
        col = _kc(md["col"], i)
        stack = md.get("cols") or []
        if stack:
            # 경로별 값과 그 분의 합. 막대 높이 = 합 = 그 1분의 총 실패 개수.
            rowsv = []
            for t, r in pts:
                raw = [(x["name"], _pio_val(r, x)) for x in stack]
                if all(v is None for _n, v in raw):
                    continue            # 그 분에 PIO 컬럼이 통째로 안 온 것
                per = [(n_, v or 0.0) for n_, v in raw]
                rowsv.append((t, per, sum(v for _n, v in per)))
            vals = [(t, tot) for t, _per, tot in rowsv]
        else:
            rowsv = []
            vals = [(t, _f(r.get(md["col"]))) for t, r in pts]
            vals = [(t, v) for t, v in vals if v is not None]
        if not vals:
            continue

        o.append(f'<rect x="{L-46}" y="{y}" width="4" height="{MET_H}" fill="{col}" rx="2"/>')
        # 이름표 두 줄 — 그림 위에 둔다(왼쪽 여백은 46px 뿐이라 글자가 막대를 덮었다)
        o.append(f'<text x="{L-38}" y="{y+13}" font-size="11.5" font-weight="700" fill="{col}">'
                 f'{_e(md["label"])} ({_e(md["unit"])})</text>')
        o.append(f'<text x="{L-38}" y="{y+27}" font-size="9" fill="{_TX2}" '
                 f'font-family="ui-monospace,Menlo,Consolas,monospace">{_e(md["raw"])}</text>')

        is_bar = bool(md.get("bar"))
        # ★개수 막대는 **0 부터** 그린다. 최소값을 바닥으로 잡으면 3~4개가
        #   0~4개처럼 보여서 두 배로 부풀어 읽힌다. 개수는 0 이 기준이다.
        vmin = 0.0 if is_bar else min(v for _, v in vals)
        vmax = max(v for _, v in vals)
        rng = (vmax - vmin) or 1.0
        # ★10분 합은 **이미 겹쳐 더한 값**이라 구간 합을 또 내면 안 된다.
        #   1시간이면 같은 실패를 열 번씩 세어 250개 같은 거짓 숫자가 나온다.
        #   더할 수 있는 건 1분 개수뿐이다.
        if is_bar and not md.get("rolling"):
            _rng_txt = (f'범위 0~{_fmt(vmax)}{_e(md["unit"])} · '
                        f'구간 합 {_fmt(sum(v for _, v in vals))}{_e(md["unit"])}')
        elif is_bar:
            _pk = max(vals, key=lambda x: x[1])
            _rng_txt = (f'범위 0~{_fmt(vmax)}{_e(md["unit"])} · '
                        f'최고 {_fmt(_pk[1])}{_e(md["unit"])} @{_pk[0]:%H:%M}')
        else:
            _rng_txt = f'범위 {_fmt(vmin)}~{_fmt(vmax)}{_e(md["unit"])}'
        # 범위·합계는 이름표 둘째 줄의 **오른쪽 끝**에 — 왼쪽은 raw 컬럼명이
        # 쓰고 있어 같은 자리에 두면 긴 이름과 겹친다.
        o.append(f'<text x="{L+pw}" y="{y+27}" font-size="9" fill="{_TX3}" '
                 f'text-anchor="end">{_rng_txt}</text>')

        # 그림은 이름표 두 줄 아래에서 시작한다 (높이는 예전과 같은 72px)
        pt, pb = y + 36, y + MET_H - 8

        def MY(v):
            return pb - (pb - pt) * ((v - vmin) / rng)

        o.append(f'<line x1="{L}" y1="{pb:.1f}" x2="{L+pw}" y2="{pb:.1f}" stroke="{_LINE}"/>')
        if is_bar:
            # 막대 폭은 1분 간격에 맞춘다. 구간이 길면 1px 밑으로 내려가므로
            # 최소 폭을 둔다 — 안 그러면 급증이 화면에서 사라진다.
            bw = max(1.6, min(9.0, pw / max(1, len(pts)) - 1.0))
            if stack:
                # 경로마다 색을 달리해 아래에서부터 쌓는다.
                cmap = {x["name"]: _PATH_COLORS[k % len(_PATH_COLORS)]
                        for k, x in enumerate(stack)}
                for t, per, _tot in rowsv:
                    base = pb
                    for name, v in per:
                        if v <= 0:
                            continue
                        h = max(1.0, (pb - MY(v)))
                        o.append(f'<rect x="{X(t)-bw/2:.1f}" y="{base-h:.1f}" '
                                 f'width="{bw:.1f}" height="{h:.1f}" '
                                 f'fill="{cmap[name]}" opacity="0.95"/>')
                        base -= h
                # 범례 — 색만으로 경로를 구분하게 두지 않는다.
                # ★그림 안 오른쪽 위(pt+1)에 두었더니 그 자리의 막대·사건 값
                #   딱지와 겹쳐 둘 다 안 읽혔다. 이름표 첫 줄 오른쪽으로 올린다.
                lx = L + pw
                for name, c in reversed(list(cmap.items())):
                    tw = _text_w(name, 9) + 16
                    lx -= tw
                    o.append(f'<rect x="{lx:.1f}" y="{y+5:.1f}" width="8" height="8" '
                             f'rx="1.5" fill="{c}"/>')
                    o.append(f'<text x="{lx+11:.1f}" y="{y+12.5:.1f}" font-size="9" '
                             f'fill="{c}" font-weight="700">{_e(name)}</text>')
                    lx -= 6
            else:
                for t, v in vals:
                    if v <= 0:
                        continue                  # 0 은 막대를 안 그린다 (바닥선이 곧 0)
                    h = max(1.0, pb - MY(v))
                    o.append(f'<rect x="{X(t)-bw/2:.1f}" y="{pb-h:.1f}" width="{bw:.1f}" '
                             f'height="{h:.1f}" fill="{col}" opacity="0.92" rx="0.8"/>')
        else:
            area_d = (f"M{X(vals[0][0]):.1f},{pb:.1f} "
                      + " ".join(f"L{X(t):.1f},{MY(v):.1f}" for t, v in vals)
                      + f" L{X(vals[-1][0]):.1f},{pb:.1f} Z")
            o.append(f'<path d="{area_d}" fill="{col}" opacity="0.20"/>')
            d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{MY(v):.1f}"
                         for k, (t, v) in enumerate(vals))
            o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.4"/>')

        # 사건 시각의 실제 값 표시
        vmap = dict(vals)
        for it, _ir, _isc in incs:
            x = X(it)
            o.append(f'<line x1="{x:.1f}" y1="{pt:.1f}" x2="{x:.1f}" y2="{pb:.1f}" '
                     f'stroke="{_EVT_COLOR}" stroke-width="0.9" stroke-dasharray="4 3" opacity="0.8"/>')
            v = vmap.get(it)
            if v is None:
                continue
            o.append(f'<circle cx="{x:.1f}" cy="{MY(v):.1f}" r="2.8" fill="{_EVT_COLOR}"/>')
            # ★구간 끝의 사건은 값 딱지가 그림 밖으로 잘렸다. 오른쪽에 자리가
            #   없으면 점 **왼쪽**에 적는다(끝 사건은 늘 마지막 분이라 흔하다).
            _vt = f'{_fmt(v)}{_e(md["unit"])}'
            _vw = _text_w(_vt, 9)
            _right = x + 4 + _vw <= L + pw
            # ★값이 최고점이면 MY(v)=pt 라 딱지가 그림 **위로** 튀어나가
            #   이름표 줄(범위·합계)과 겹쳤다. 그림 안으로 물린다.
            _vy = max(pt + 9, MY(v) - 5)
            o.append(f'<text x="{(x+4) if _right else (x-4):.1f}" y="{_vy:.1f}" '
                     f'font-size="9" fill="{_EVT_COLOR}" font-weight="700" '
                     f'text-anchor="{"start" if _right else "end"}">{_vt}</text>')

        # 선택 시각 — 지표 패널에도 세로선 + 그 시각 실제 값
        o.append(f'<line x1="{sx:.1f}" y1="{pt:.1f}" x2="{sx:.1f}" y2="{pb:.1f}" '
                 f'stroke="{_SEL_COLOR}" stroke-width="1.2" opacity="0.55"/>')
        sv_ = vmap.get(sel_t)
        if sv_ is not None:
            o.append(f'<circle cx="{sx:.1f}" cy="{MY(sv_):.1f}" r="3.4" fill="{_BG}" '
                     f'stroke="{_SEL_COLOR}" stroke-width="1.8"/>')
            _t = f'{_fmt(sv_)}{md["unit"]}'
            _tw = len(_t) * 6.0
            _tx = max(L + _tw / 2, min(L + pw - _tw / 2, sx))
            o.append(f'<text x="{_tx:.1f}" y="{pt+9:.1f}" font-size="9" fill="{_SEL_COLOR}" '
                     f'font-weight="700" text-anchor="middle">{_e(_t)}</text>')

    # ── X 축 ──
    ybase = height - 20
    step = max(1, int(minutes // 8))
    tick = t0
    while tick <= t1:
        x = X(tick)
        o.append(f'<text x="{x:.1f}" y="{ybase}" font-size="9.5" fill="{_TX2}" '
                 f'text-anchor="middle">{tick:%H:%M}</text>')
        tick += timedelta(minutes=step)

    # ★값이 안 오는 컬럼은 패널 대신 한 줄로 — 빈 칸을 그리지 않으면서도
    #   "이건 왜 안 보이나" 에 답이 된다 (수집이 빠진 것인지 확인해야 한다).
    if empty:
        names = " · ".join(_e(m["label"]) for m in empty[:6])
        more = f" 외 {len(empty)-6}개" if len(empty) > 6 else ""
        o.append(f'<text x="{L-46}" y="{ybase+14:.1f}" font-size="9.5" '
                 f'fill="{_TX3}">이 구간에 값이 안 온 컬럼: {names}{more}</text>')

    o.append("</svg>")
    return "".join(o)
