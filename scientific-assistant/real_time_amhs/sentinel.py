#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 실시간 관제 코어 (독립)

로그프레소 폴링 → 이상감지 → 케이스 생성/갱신 → 심각도 라우팅/에스컬레이션.
데모스(demos_v1) 어떤 모듈도 import 하지 않는다.

정책 (config.json policy):
  · 감지는 항상 실시간이다.
  · "이상 없음" 판정은 케이스를 닫지 않고 재확인 예약만 갱신한다.
  · 종결 후에도 억제 창(suppression window) 동안 재발은 같은 케이스로 묶인다.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta

from lp_client import load_config
from lp_query import fetch_amos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ────────────────────────────── 등급 ──────────────────────────────
_LEVEL_META = {"경계": ("🟠", "경계/주의(확인필요)"),
               "위험": ("🔴", "위험/경고(모니터링 필요)"),
               "초위험": ("⛔", "초위험/심각(조치필요)")}


def grade_cuts(cfg: dict | None = None) -> tuple[int, int, int]:
    """등급 시작점 3개 (경계·위험·초위험) — **이 시스템** 기준.

    기본은 config.grade.bands 의 min 들. grade.by_sys[시스템] 이 있으면
    그 값(warn/danger/critical)으로 덮는다. FAB 마다 점수 분포가 달라서
    임계가 다를 수 있다 — 정책 탭에서 시스템별로 저장한다.
    """
    cfg = cfg or load_config()
    g = cfg.get("grade", {}) or {}
    mins = [b.get("min") for b in (g.get("bands") or [])[:3]] + [None] * 3
    base = [int(m) if isinstance(m, (int, float)) else d
            for m, d in zip(mins, (60, 71, 85))]
    o = (g.get("by_sys") or {}).get(str(cfg.get("_sys") or "ALL").upper()) or {}
    return (int(o.get("warn", base[0])), int(o.get("danger", base[1])),
            int(o.get("critical", base[2])))


def _sys_grade(cfg: dict) -> dict:
    """이 시스템의 등급 블록 — by_sys 오버라이드가 있으면 밴드를 합성한다.

    오버라이드가 없으면 config.grade 를 **그대로** 돌려준다 (사용자가 밴드를
    직접 꾸민 경우 그 모양 유지).
    """
    g = cfg.get("grade", {}) or {}
    o = (g.get("by_sys") or {}).get(str(cfg.get("_sys") or "ALL").upper())
    if not o:
        return g
    w, d, c = grade_cuts(cfg)

    def band(lo, hi, lv):
        em, sev = _LEVEL_META[lv]
        return {"min": lo, "max": hi, "level": lv, "emoji": em, "severity": sev}
    return {"normal_max": w - 1,
            "bands": [band(w, d - 1, "경계"), band(d, c - 1, "위험"),
                      band(c, 100, "초위험")]}


def grade(score: float, cfg: dict | None = None) -> dict:
    """점수 → 등급 밴드. 임계 미만은 정상(무알람). 시스템별 컷 반영."""
    cfg = cfg or load_config()
    g = _sys_grade(cfg)
    for b in g.get("bands", []):
        if b["min"] <= score <= b["max"]:
            return b
    return {"level": "정상", "emoji": "🟢", "severity": "정상", "min": 0, "max": g.get("normal_max", 59)}


def alarm_floor(cfg: dict | None = None) -> int:
    """알람 최소 점수 (피드백 보정 반영). 시스템별 컷 반영."""
    cfg = cfg or load_config()
    bands = _sys_grade(cfg).get("bands", [])
    base = min((b["min"] for b in bands), default=60)
    return max(1, min(100, base + _threshold_nudge(cfg)))


def _threshold_nudge(cfg: dict) -> int:
    """리포트 피드백 누적 → 임계 점수 보정 (±10 제한)."""
    fb = cfg.get("feedback", {})
    path = os.path.join(BASE_DIR, fb.get("store", "data/feedback.jsonl"))
    if not os.path.isfile(path):
        return 0
    step, n = fb.get("threshold_nudge", 2), fb.get("apply_last_n", 20)
    delta = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for rec in [json.loads(l) for l in f.read().splitlines() if l.strip()][-n:]:
                v = rec.get("verdict")
                if v == "과다탐지":
                    delta += step
                elif v == "누락":
                    delta -= step
    except Exception:
        return 0
    return max(-10, min(10, delta))


# ────────────────────────────── 시각 파싱 ──────────────────────────────
def _row_dt(row: dict) -> datetime | None:
    s = (row.get("datetime") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    d, t = (row.get("date") or "").strip(), (row.get("time") or "").strip()
    if d and t:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(f"{d} {t}", fmt)
            except ValueError:
                continue
    return None


def _score(row: dict) -> float:
    try:
        return float(row.get("unified_risk_score") or 0)
    except (TypeError, ValueError):
        return 0.0


# 룰 코드 → 한글명 (스킬 규칙: 답변에 룰 코드 노출 금지)
# 실제 표기는 두 가지 — reason 은 'R-A_sus', signals 는 'RA_sus'
_RULE_KR = [
    (r"R-?A_sus\b", "반송지연 지속"),
    (r"R-?B_fast\b", "Queue 상승"),
    (r"R-?A\b", "반송지연"),
    (r"R-?B\b", "Queue 누적"),
    (r"R-?C\b", "리프터 정체"),
    (r"R-?D\b", "Storage FULL"),
    (r"MAXCAPA", "운영자 용량변경"),
    (r"SORT", "분류기 대기"),
    (r"SLA", "4분초과"),
]


def _reason_blocks(txt: str) -> list[tuple[str, str]]:
    """'발동:' 뒤의 `영역[룰,룰,…]` 을 (영역, 블록) 목록으로 뽑는다.

    ★닫는 ']' 가 없어도 끝까지 읽는다. reason 은 길어지면 잘려서 들어오는
      경우가 있는데(룰마다 괄호 안에 수치가 붙어 금방 길어진다), 예전에는
      '[…]' 를 못 찾아 요약이 빈 문자열이 되고 → 호출부가 **원문을 그대로**
      화면에 뿌렸다. 그래서 화면에 이런 게 튀어나왔다:
        hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=6.30분…
      룰 코드도 금지어('역증가')도 그대로 노출됐다.
    """
    import re
    seg = txt.split("발동:", 1)[1] if "발동:" in txt else txt
    return [(m.group(1), m.group(2))
            for m in re.finditer(r"([A-Za-z0-9_]+)\s*\[([^\]]*)(?:\]|$)", seg)]


def _rule_names(block: str) -> list[str]:
    """룰 코드 블록 → 한글 이름 목록. R-A' 처럼 프라임이 붙어도 잡는다."""
    import re
    names, seen = [], set()
    for code, kr in _RULE_KR:                      # 긴 코드부터 매칭
        if re.search(r"R?-?" + code + r"\b", block) and kr not in seen:
            seen.add(kr)
            names.append(kr)
    return names


# ── PIO 반송실패 ────────────────────────────────────────────────────────
# reason 끝에 이런 꼴로 붙어 온다:  PIO(M14A<-M14B=4건/10분,합6)
#   경로 = 그 10분에 가장 많이 실패한 구간, 합 = 12경로 10분 총합
# ★설비 지표(큐·반송시간)는 '밀리는 중' 을 보고, PIO 는 **이미 실패한 결과**다.
#   실측 상관계수 +0.22 — 거의 안 겹친다. 그래서 따로 말해 줘야 한다.
_PIO_RE = re.compile(r"PIO\(([^)]*)\)")
# ★예측기가 써 보내는 원문은 아직 "…=4건" 이다. 읽을 때는 건/개 둘 다
#   받고, 사람에게 보여 줄 때만 "개" 로 쓴다 (사용자 표기 요청).
_PIO_PATH_RE = re.compile(r"([A-Za-z0-9_]+\s*(?:<-|->)\s*[A-Za-z0-9_]+)\s*=\s*(\d+)\s*[건개]")
_PIO_SUM_RE = re.compile(r"합\s*(\d+)")


def pio_of(reason: str) -> dict:
    """reason 에서 PIO 부분만 떼어 읽는다.

    반환 {"paths": [(경로, 개수)…], "total": 10분 총합} · 없으면 {}
    ★없는 것과 0 은 다르다. PIO 표기가 아예 없으면 {} 를 준다 —
      '실패 0개' 가 아니라 '이 행에는 PIO 정보가 없다' 는 뜻이다.
    """
    m = _PIO_RE.search(reason or "")
    if not m:
        return {}
    inner = m.group(1)
    paths = [(p.replace(" ", ""), int(n)) for p, n in _PIO_PATH_RE.findall(inner)]
    tot = _PIO_SUM_RE.search(inner)
    out = {"paths": paths}
    if tot:
        out["total"] = int(tot.group(1))
    elif paths:
        out["total"] = sum(n for _p, n in paths)
    return out


# 10분 총합 구간 — PIO 명세의 3일 실측 분포. 기준선은 **고정**이다.
#   최근 데이터로 평소치를 다시 계산하면 설비가 나빠질수록 기준선도 같이
#   올라가서 악화를 못 잡는다 (명세가 특히 못 박은 것).
PIO_BANDS = [(81, "최고"), (61, "심각"), (41, "이상"),
             (26, "확실히 많음"), (16, "조금 많음")]

# ★화면에 **띄울** 최소 개수. 3일 중 88.9%가 0~15 라, 이 아래는 평소다.
#   평소 값까지 다 적으면 reason 과 실제지표가 PIO 로 늘 차 있어서 정작
#   봐야 할 때 눈에 안 띈다 — 평소는 접어 두고 넘을 때만 말한다.
#   (판정 임계 PIO_10MIN_THR=16 과 한 칸 차이는 의도한 것이다. 임계 직전
#    15 까지는 '보이기만' 하고 점수에는 안 들어간다.)
PIO_SHOW_MIN = 15


def pio_band(total) -> str:
    """10분 총합 → 한글 수준. 15 이하는 평소(3일 중 88.9%)라 빈 문자열."""
    try:
        n = int(total)
    except (TypeError, ValueError):
        return ""
    for thr, name in PIO_BANDS:
        if n >= thr:
            return name
    return ""


def pio_text(reason: str) -> str:
    """사람이 읽을 한 줄. 없으면 빈 문자열.

    예) 'PIO 반송실패 18개/10분(조금 많음) · 주 M14A<-M14B 4개'

    ★경로는 **1개만** 적는다. 두 개를 적었더니 reason 칸(이미 발동 룰로 꽉
      차 있다)이 넘쳐 목록에서 줄이 밑으로 흘러내렸다. 그렇다고 아예 빼면
      '어디가 터졌나' 를 그래프까지 열어야 알 수 있어서, 가장 많이 실패한
      한 구간만 남긴다. 나머지 경로는 더블클릭 그래프의 'PIO 주 경로'
      막대에서 시각별로 본다.
    """
    p = pio_of(reason)
    if not p:
        return ""
    tot = p.get("total")
    if tot is None or tot < PIO_SHOW_MIN:
        return ""                       # 평소 수준 — 굳이 말하지 않는다
    band = pio_band(tot)
    out = "PIO 반송실패 {}개/10분{}".format(tot, f"({band})" if band else "")
    top = sorted(p.get("paths") or [], key=lambda x: -x[1])[:1]
    if top:
        out += " · 주 {} {}개".format(top[0][0], top[0][1])
    return out


def summarize_reason(reason: str, area: str = "") -> str:
    """reason 원문에서 발동 룰을 뽑아 한글 한 줄로. 룰 코드는 노출하지 않는다.

    예) 'hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C,R-D(STB=100.0%)]; M14[R-A_sus]'
        → 'M16HUB 반송지연 지속 · 리프터 정체 · Storage FULL'

    ★어떤 경우에도 원문(룰 코드·영문 컬럼명·'역증가' 같은 금지어)을 돌려주지
      않는다. 못 알아본 룰이 있어도 한글로 '이상 감지' 라고만 말한다.
      원문이 필요하면 호출부가 따로 갖고 있는 reason_raw 를 쓴다(툴팁).
    """
    txt = reason or ""
    if not txt:
        return ""

    blocks = _reason_blocks(txt)
    block = ""
    if area:
        block = next((b for a, b in blocks if a.upper() == area.upper()), "")
    if not block and blocks:
        block = blocks[0][1]
    if not block:
        # 대괄호 형식이 아예 아니다 — 문장 전체에서 룰 코드를 찾아본다
        block = txt.split("발동:", 1)[-1]

    names = _rule_names(block)
    head = f"{area} " if area else ""
    # ★PIO 는 영역 블록 **밖**에 붙는다 (12경로 지표라 한 영역 것이 아니다).
    #   블록만 읽으면 통째로 사라진다 — 실제로 화면에 안 나왔다.
    pio = pio_text(reason)
    if not names:
        # 룰 코드를 하나도 못 알아봤다(새 룰이거나 형식이 바뀜).
        # 원문을 뱉지 말고 한글로만 알린다.
        base = (head + "이상 감지").strip()
        return (base + " · " + pio) if pio else base
    out = head + " · ".join(names)
    return (out + " · " + pio) if pio else out


def reason_metrics(reason: str, area: str = "", row: dict | None = None) -> list[dict]:
    """발동한 룰 → **실제 raw 지표 컬럼명**. 화면 '실제지표' 칸에 쓴다.

    한글 요약("반송지연 지속 · 리프터 정체")만 보면 '무슨 숫자를 보고 그렇게
    판단했나' 를 알 수 없다. 룰마다 대응하는 실제 컬럼을 같이 보여준다.
        반송지연  → M16HUB.QUE.TIME.AVGTOTALTIME1MIN
        리프터 정체 → M16HUB.QUE.LFT.3F_LFT_REVERSALCNT
        Storage FULL → M16HUB.STRATE.STB.3F_STORAGE_UTIL 등

    매핑은 report_graphs.parse_reason_metrics 하나만 쓴다 (리포트 그래프가
    'reason 이 실제로 발동시킨 컬럼' 을 고를 때 쓰는 것과 같은 표).
    area 를 주면 그 영역 블록만 본다 — 요약 문구와 칸이 어긋나지 않게.

    반환 [{"col","raw","label","unit"}, …] (등장 순서, 중복 제거)
    """
    txt = reason or ""
    if not txt:
        return []
    try:
        from report_graphs import parse_reason_metrics
    except Exception:
        return []
    if area:
        blk = next((b for a, b in _reason_blocks(txt) if a.upper() == area.upper()), "")
        if blk:
            # ★PIO 는 **영역 것이 아니다** (12경로 지표라 FAB 하나에 속하지
            #   않는다). 영역으로 거르면서 같이 잘려서, 어느 영역을 보든
            #   PIO 가 '발동이 지목한 지표' 에서 빠졌다 — 기여도 추정에서
            #   가중을 못 받아 순위가 밀렸다. 다시 붙여 준다.
            pio = _PIO_RE.search(txt)
            txt = f"발동: {area}[{blk}]" + (f"; PIO({pio.group(1)})" if pio else "")
    try:
        mets = parse_reason_metrics(txt)
    except Exception:
        return []
    return _pio_add_rowpaths(mets, row)


def _row_fab(row) -> str:
    """이 행이 **어느 FAB 의 분리 파일 행**인가 — 통합(ALL) 행이면 "".

    ★area(hot_area)로 판단하면 안 된다. ALL 행의 hot_area 는 '그 분 제일
      높은 FAB' 이라, 그걸로 PIO 경로를 거르면 ALL 화면에서 나머지 경로가
      통째로 사라진다. 실제로 제일 많이 실패하는 M14A<-M14B 가 M16HUB 행에서
      빠진다. 분리 파일 행인지는 all_score 로만 안다 (jupyter_csv._fab_rows).
    """
    if not row or not str(row.get("all_score") or "").strip():
        return ""
    f = str(row.get("hot_area") or "").strip().upper()
    try:
        import fab_score as F
        return f if f in F.PIO_FAB_PATHS else ""
    except Exception:                                   # noqa: BLE001
        return ""


# ★reason 은 그 10분에 **가장 많이 실패한 한 구간**만 적어 온다. 그래서
#   같은 분에 다른 경로에서 실패가 나도 '실제지표' 에 이름이 안 떴다 —
#   화면에서 'PIO 주 경로 개수가 안 보인다' 던 게 이것이다.
#   행에 값이 실제로 온 경로를 뒤에 붙여 준다 (0 은 붙이지 않는다 —
#   12경로를 다 적으면 실제지표 칸이 PIO 로만 찬다).
_PIO_COL_SUF = "_PIOERROR_DEPOSITED"


def _pio_add_rowpaths(mets: list, row) -> list:
    """행에 값이 실제로 온 PIO 경로를 붙인다. FAB 행이면 **그 FAB 것만**.

    ★2026-09-16 'PIO_ERROR FAB별 연동 명세' — FAB 분리 파일에도 12경로가 다
      실려 오므로, 안 거르면 M16B 화면 '실제지표' 에 M14A<-M14B 가 뜬다.
      현장은 그걸 보고 자기 FAB 을 뒤진다 (남의 구간이다).
    ★여기는 **화면 표시** 자리다 — 점수를 계산하거나 바꾸지 않는다.
    """
    fab = _row_fab(row)
    if not row or not any(m.get("col") in ("pio_10min_cnt", "area_pio_wsum10")
                          for m in mets) and not fab:
        return mets                     # PIO 가 발동한 행이 아니다 — 손대지 않는다
    have = {m.get("col") for m in mets}
    keep = set()
    if fab:
        try:
            import fab_score as F
            keep = {x["path"] for x in F.pio_paths_of(fab)}
        except Exception:                               # noqa: BLE001
            keep = set()
    add = []
    if fab:
        # ★pio_10min_cnt 는 **12경로 전부의 합** 이다. FAB 화면에서 그냥 두면
        #   그 FAB 가중합과 숫자가 달라 "둘 중 뭐가 맞나" 가 된다. 지우지 않고
        #   무엇인지 이름에 적는다 — 전체 맥락도 봐야 할 수가 있다.
        for m in mets:
            if m.get("col") == "pio_10min_cnt" and "전체" not in (m.get("label") or ""):
                m["label"] = "PIO 반송실패 10분 합 (전체 12경로)"
        # 그 FAB 의 점수·가중합을 맨 앞에 — '왜 그 점수냐' 의 ①②다.
        for col, raw, lb, un in (
                ("area_pio_score", f"PIO.DEPOSIT.{fab}.SCORE",
                 f"PIO 반송실패 점수 ({fab})", "점"),
                ("area_pio_wsum10", f"PIO.DEPOSIT.{fab}.WSUM10",
                 "PIO 10분 가중합 (직접×2 + 간접×1)", "")):
            if col in have:
                continue
            try:
                if float(str(row.get(col) or "").strip()) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            have.add(col)
            mets = mets + [{"col": col, "raw": raw, "label": lb, "unit": un}]
    for k, v in row.items():
        if not isinstance(k, str) or not k.endswith(_PIO_COL_SUF) or k in have:
            continue
        name = k[:-len(_PIO_COL_SUF)]
        if keep and name not in keep:
            continue
        try:
            if float(str(v).strip()) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        add.append({"col": k, "raw": f"PIO.DEPOSIT.{name}",
                    "label": f"PIO 반송실패 {name}", "unit": "개"})
    return mets + sorted(add, key=lambda m: m["col"])


# ═══════════ FAB 화면 전용 — 발동 룰 · 실제지표 · PIO_ERROR 개수 ═══════════
# 고객(2026-09-22): "실시간 관제·과거 데이터 조회 ALL 숨기자, 각 FAB 만" ·
#   "발동률도 각 FAB 에 해당하는 것만 보여줘야, 실제지표도 마찬가지" ·
#   "PIO_ERROR 경우 [경로 컬럼] 이거 보여줘, 다른 PIO 보여주지 말고, 관련 FAB 만" ·
#   "발동률은 PIO_ERROR 몇 개가 생겼는지 이야기 해주면 돼, 데이터에 나와 있어" ·
#   "area_pio_wsum1 이거 보지 말고 [경로 컬럼] 이걸 봐야 돼" ·
#   "잘 모르겠으면 이거 봐 — 컬럼흐름 상세도(FAB별 HTML)".
#
# ★기준은 **컬럼흐름 상세도(FAB별 HTML) 2절 표** — 룰마다 그 FAB 이 실제로 읽는
#   원본 컬럼. 그 표는 fab_score.WATCH 와 같은 이름이라 거기서 읽는다(두 벌로
#   적으면 갈라진다). 상세도에서 FAB 마다 다른 자리:
#     R-D  M16HUB = 적재율·STB·MLUD·수동큐·CNV (괄호 안 글자로 어느 것인지 적혀 온다)
#          나머지   = {FAB}.QUE.OHT.OHTUTIL — OHT 가동률 **하나뿐**
#     R-C  M16HUB = 리프터 10대 TOTAL_CURRENTQCNT · M14 = CNV 북/남 편중 · 나머지 없음
# ★summarize_reason · reason_metrics 는 **그대로 둔다**. 리포트·4단계 분석·아바타가
#   ALL 기준으로 부르고, 배포가 파일 단위라 서명도 못 바꾼다. 관제 표가 FAB 화면일
#   때만 아래 함수를 쓴다 (server.api_feed).
# ★무엇이 틀렸었나 (FAB 분리 파일에도 reason 은 **전체 것**이 실려 온다 —
#   'M16HUB[…]; M14[…]; M16A[…]; PIO(…)' 가 다 들어 있다)
#     ① 발동 룰: 그 FAB 블록이 없으면 **첫 블록(남의 FAB)을 빌려 와 이름만 바꿔**
#        붙였다 — M16B 화면에 'M16B 반송지연 지속 · Storage FULL' 이 떴는데 그건
#        M16HUB 가 발동한 것이었다.
#     ② 실제지표: 그 FAB 블록이 없으면 reason **전체**를 봤고, 있어도 R-D 를 FAB 과
#        상관없이 M16HUB 적재율로 적었다(상세도: M14·M14B·M16A·M16B 의 R-D 는 OHT 가동률).
#        PIO 는 남의 경로 + '10분 합 (전체 12경로)' 가 늘 붙었다.
#     ③ PIO 문구: '22개/10분 · 주 M14A<-M14B 9개' 가 어느 FAB 화면이든 똑같았다.
# ★점수를 계산하거나 바꾸지 않는다 — 이미 적힌 값을 골라서 보여 주기만 한다.


def _fab_code(fab) -> str:
    """관제 FAB 코드면 그대로(M16HUB·M16A·M16B·M14B·M14), 아니면 ""."""
    f = str(fab or "").strip().upper()
    try:
        import fab_score as F
        return f if f in F.PIO_FAB_PATHS else ""
    except Exception:                                   # noqa: BLE001
        return ""


def fab_pio(row: dict | None, fab: str) -> dict:
    """그 행(그 1분)의 PIO_ERROR 개수 — **그 FAB 경로 컬럼만** 읽는다.

    반환 {"n": 합, "paths": [(경로, 개수)…]} — 많은 순(같으면 배정표 순).
    ★읽는 곳은 {경로}_PIOERROR_DEPOSITED 뿐이다 (고객: "area_pio_wsum1 이거 보지
      말고 … 이걸 봐야 돼"). 값은 그 분(1분)의 DEPOSIT 실패 건수다(상세도 4-P-1).
    ★reason 의 PIO(…=N건/10분) 는 안 쓴다 — 10분 누적이고 상위 경로만 적혀 와서
      그 FAB 경로가 빠져 있을 수 있다.
    ★경로 배정은 fab_score.pio_paths_of (상세도 4-P-1 과 같다:
      M16HUB 7 · M14 5 · M16A 4 · M14B 3 · M16B 2).
    """
    f = _fab_code(fab)
    if not f or not row:
        return {"n": 0, "paths": []}
    import fab_score as F
    order = [x["path"] for x in F.pio_paths_of(f)]
    got = []
    for p in order:
        try:
            v = float(str(row.get(p + _PIO_COL_SUF) or "").strip())
        except (TypeError, ValueError):
            continue
        if v > 0:
            got.append((p, int(round(v))))
    got.sort(key=lambda x: (-x[1], order.index(x[0])))
    return {"n": sum(n for _p, n in got), "paths": got}


def fab_pio_text(row: dict | None, fab: str) -> str:
    """'PIO_ERROR 3개/1분 (M16A->M16B 2, M16B->M16A 1)' — 없으면 "".

    ★괄호 안 경로는 쉼표로 잇는다. 관제 표(reasonCell)가 ' · ' 에서 줄을 끊어서,
      가운뎃점으로 이으면 괄호가 두 줄로 쪼개지고 룰 개수(파랑 기준)도 부풀어 오른다.
    """
    d = fab_pio(row, fab)
    if not d["n"]:
        return ""
    head = ", ".join(f"{p} {n}" for p, n in d["paths"][:3])
    more = f" 외 {len(d['paths']) - 3}" if len(d["paths"]) > 3 else ""
    return f"PIO_ERROR {d['n']}개/1분 ({head}{more})"


def _fab_block(reason: str, fab: str) -> tuple[str, bool]:
    """(그 FAB 블록, reason 이 영역 블록 형식인가).

    ★블록 형식인데 그 FAB 것이 없으면 "" — **남의 블록을 빌려 오지 않는다**.
    ★블록 형식이 아예 아니면(옛 모양) 누구 것인지 가릴 수 없어 '발동:' 뒤 전체.
    """
    txt = reason or ""
    blocks = _reason_blocks(txt)
    if blocks:
        return next((b for a, b in blocks if a.upper() == fab), ""), True
    return (txt.split("발동:", 1)[-1] if "발동:" in txt else ""), False


# 블록 안 표기 → 상세도의 룰. 차례는 _RULE_KR 과 같다(표에 늘 같은 순서로 선다).
# ★_rule_names 를 안 쓰는 이유 — FAB 블록에서 두 가지를 놓쳤다:
#     'MAXCAPA1개변경' (뒤에 글자가 바로 붙어 \b 가 안 걸린다 — 실데이터 표기)
#     'Sorter(…)'      (대소문자)
#   _rule_names 는 ALL 요약이 같이 써서(리포트·아바타) 여기서 따로 둔다.
_FAB_RULE_RE = [
    ("RA_sus",  re.compile(r"(?<![A-Za-z0-9])R-?A_sus")),
    ("RB_fast", re.compile(r"(?<![A-Za-z0-9])R-?B_fast")),
    ("RA",      re.compile(r"(?<![A-Za-z0-9])R-?A(?![A-Za-z0-9_])")),
    ("RB",      re.compile(r"(?<![A-Za-z0-9])R-?B(?![A-Za-z0-9_])")),
    ("RC",      re.compile(r"(?<![A-Za-z0-9])R-?C(?![A-Za-z0-9_])")),
    ("RD",      re.compile(r"(?<![A-Za-z0-9])R-?D(?![A-Za-z0-9_])")),
    ("MAXCAPA", re.compile(r"MAXCAPA")),
    ("SORT",    re.compile(r"(?i:sort)|소터|분류기")),
    ("SLA",     re.compile(r"SLA|4분초과")),
]
_FAB_RULE_KR = {"RA_sus": "반송지연 지속", "RB_fast": "Queue 상승", "RA": "반송지연",
                "RB": "Queue 누적", "MAXCAPA": "운영자 용량변경",
                "SORT": "분류기 대기", "SLA": "4분초과"}


def _fab_rules(block: str) -> list[tuple[str, str]]:
    """블록 → [(룰 코드, 그 룰 토막)] — 토막은 괄호 안 근거(R-D(FAB저장=…))를 본다."""
    parts = [t.strip() for t in re.split(r",(?![^()]*\))", block or "") if t.strip()]
    out, seen = [], set()
    for code, rx in _FAB_RULE_RE:
        for t in parts:
            if rx.search(t) and code not in seen:
                # R-A_sus 는 R-A 로도 읽히면 안 된다 — 위 정규식이 막는다
                seen.add(code)
                out.append((code, t))
                break
    return out


def _fab_rule_name(code: str, f: str) -> str:
    """상세도의 룰 이름 — R-C · R-D 는 FAB 마다 보는 것이 달라 이름도 다르다."""
    if code == "RD":
        return "Storage FULL" if f == "M16HUB" else "OHT 가동률"
    if code == "RC":
        return "컨베이어 편중" if f == "M14" else "리프터 정체"
    return _FAB_RULE_KR.get(code, code)


# M16HUB R-D 괄호 안 글자 → 그 조건의 원본 컬럼 (상세도 M16HUB 2절 R-D 다섯 줄)
_HUB_RD = [
    (("FAB저장", "적재"), "M16HUB.STRATE.ALL.FABSTORAGERATIO", "FAB 적재율", "%"),
    (("STB",), "M16HUB.STRATE.STB.3F_STORAGE_UTIL", "3F STB 점유율 (기록용)", "%"),
    (("MLUD",), "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB", "MLUD 잡 누적", "개"),
    (("수동", "MANUAL"), "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT", "수동 이동 큐", "개"),
    (("CNV",), "M16HUB.CNV.SENDFAB.TO_M14A_CURRENTQCNT", "CNV 현재량", "개"),
]
_HUB_LIFTERS = ("6ABL6011", "6ABL6012", "6ABL6021", "6ABL6022", "6ABL6031",
                "6ABL6032", "6ABL0111", "6ABL0112", "6ABL0121", "6ABL0122")
_M14_RC = (("M14.QUE.CNV.M14ATONORTHCURRENTQCNT", "M14A → 북측 CNV 물량"),
           ("M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT", "M14A → 남측 CNV 물량"))


def _fab_rule_cols(code: str, tok: str, f: str, row: dict | None) -> list[dict]:
    """그 룰이 그 FAB 에서 읽는 원본 컬럼 [{col, raw, label, unit}] — 상세도 2절."""
    import fab_score as F
    w = F.WATCH.get(f) or {}

    def one(raw, label, unit, col=""):
        return {"col": col or raw, "raw": raw, "label": f"{f} {label}", "unit": unit}

    if code in ("RA", "RA_sus", "RB", "RB_fast"):
        it = (w.get(code[:2]) or [None])[0]              # 지속·급증도 같은 컬럼
        return [one(it["amos"], it["label"], it.get("unit") or "", it.get("csv"))] if it else []
    if code == "RD":
        if f != "M16HUB":
            it = (w.get("RD") or [None])[0]              # OHT 가동률 하나
            return [one(it["amos"], it["label"], it.get("unit") or "", it.get("csv"))] if it else []
        got = [one(raw, lb, un) for keys, raw, lb, un in _HUB_RD
               if any(k in tok for k in keys)]
        return got or [one(*_HUB_RD[0][1:])]               # 근거가 안 적혀 오면 적재율
    if code == "RC":
        if f == "M14":
            return [one(raw, lb, "개") for raw, lb in _M14_RC]
        if f == "M16HUB":
            ids = [x for x in _HUB_LIFTERS if x in tok]  # R-C'(역증가4개:6ABL6021,…)
            if not ids:
                return [one("M16HUB.LFT.{6ABL6011…6ABL0122}.TOTAL_CURRENTQCNT",
                            "리프터 10대 대기량", "대")]
            return [one(f"M16HUB.LFT.{x}.TOTAL_CURRENTQCNT", f"리프터 {x} 대기량", "대")
                    for x in ids]
        return []                                        # 상세도: M14B·M16A·M16B 는 R-C 없음
    if code in ("SLA", "SORT"):
        return [one(it["amos"], it["label"], it.get("unit") or "", it.get("csv"))
                for it in (w.get(code) or []) if not it.get("record_only")]
    if code == "MAXCAPA":
        items = [it for it in (w.get("MAXCAPA") or [])]
        try:
            hit = [h.split("=", 1)[0].strip() for h in F._maxcapa_hits(row or {}, f)]
        except Exception:                               # noqa: BLE001
            hit = []
        pick = [it for it in items if any(it["amos"].endswith("." + h) for h in hit)]
        return [one(it["amos"], it["label"], it.get("unit") or "") for it in (pick or items)]
    return []


def fab_reason(reason: str, fab: str, row: dict | None = None) -> str:
    """FAB 화면 '발동 룰' — 그 FAB 블록의 룰 + 그 분 그 FAB 경로의 PIO_ERROR 개수.

    예) M16B 화면 · 'M16HUB[R-A_sus]; M16A[SLA(…)]; PIO(…)' · M16A->M16B 2개
        → 'M16B PIO_ERROR 2개/1분 (M16A->M16B 2)'
        (예전: 'M16B 반송지연 지속 · … · PIO 반송실패 22개/10분 · 주 M14A<-M14B 9개')
    그 FAB 것이 하나도 없으면 "" — 표가 '정상 운영'/'–' 로 채운다.
    """
    f = _fab_code(fab)
    if not f:
        return summarize_reason(reason, fab)
    block, _ = _fab_block(reason, f)
    rules = _fab_rules(block)
    names = []
    for code, _t in rules:
        nm = _fab_rule_name(code, f)
        if nm not in names:
            names.append(nm)
    if block and not names:
        names = ["이상 감지"]          # 못 알아본 룰 — 원문은 흘리지 않는다
    pio = fab_pio_text(row, f)
    if pio:
        names.append(pio)
    return (f"{f} " + " · ".join(names)) if names else ""


def fab_metrics(reason: str, fab: str, row: dict | None = None) -> list[dict]:
    """FAB 화면 '실제지표' — 그 FAB 블록 룰의 **원본 컬럼**(상세도 2절) + 그 FAB PIO 경로.

    ★남의 FAB 컬럼 · 남의 PIO 경로 · 전체 12경로 합(pio_10min_cnt) · 가중합
      (area_pio_wsum1/10) 은 올리지 않는다.
    ★PIO 는 그 분에 실패가 난 경로의 **실제 컬럼 이름**({경로}_PIOERROR_DEPOSITED)
      으로 적는다 — 고객이 준 목록이 그 이름이고, 현장은 그걸로 원 데이터를 찾아간다.
    """
    f = _fab_code(fab)
    if not f:
        return reason_metrics(reason, fab, row)
    block, _ = _fab_block(reason, f)
    mets: list[dict] = []
    have: set = set()
    for code, tok in _fab_rules(block):
        for m in _fab_rule_cols(code, tok, f, row):
            if m["raw"] in have:
                continue
            have.add(m["raw"])
            mets.append(m)
    for p, _n in fab_pio(row, f)["paths"]:
        col = p + _PIO_COL_SUF
        if col in have:
            continue
        have.add(col)
        mets.append({"col": col, "raw": col, "label": f"PIO_ERROR {p}", "unit": "개"})
    return mets


def hid_zones(tokens: str) -> list[str]:
    """HID_32_FROM_SUM_A → HID32 (순서 보존·중복 제거)."""
    out, seen = [], set()
    for tok in (tokens or "").replace(",", " ").split():
        parts = tok.split("_")
        if len(parts) >= 2 and parts[0].upper() == "HID" and parts[1].isdigit():
            z = f"HID{parts[1]}"
            if z not in seen:
                seen.add(z)
                out.append(z)
    return out


# ────────────────────────────── 케이스 ──────────────────────────────
class CaseStore:
    """활성/확인/종결 케이스 관리. 파일에 원자적 저장.

    ★아래 세 값은 **클래스 기본값**으로도 둔다. report.py 는 실시간 저장소를
      건드리지 않으려고 CaseStore.__new__ 로 빈 껍데기를 만들어 쓰는데,
      __init__ 을 안 타므로 인스턴스에 이 값들이 없다. 없으면 ingest 가
      그 자리에서 터진다(실제로 리포트 구간조회가 그렇게 죽었다).
    """

    rev = 0                 # 판번호 — /api/cases 캐시가 본다
    _pruned_at = 0.0        # 마지막으로 오래된 것을 치운 시각
    prunable = True         # 임시 저장소는 False — 보관 파일을 건드리면 안 된다

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.path = os.path.join(BASE_DIR, self.cfg.get("storage", {}).get("cases", "data/cases.json"))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # ★RLock — save() 가 잠금을 잡는데, ingest·ack·mark_normal·close 는
        #   **이미 잠금을 쥔 채** save() 를 부른다. 그냥 Lock 이면 제 잠금에
        #   제가 걸려 서버가 그 자리에서 멎는다.
        self._lock = threading.RLock()
        # ★판번호 — 저장할 때마다 오른다. 화면이 3초마다 부르는 /api/cases 가
        #   "지난번과 같은 판인가" 를 이 숫자 하나로 가른다 (전체를 다시
        #   직렬화해 보고 비교하면 그게 곧 비용이다).
        self.rev = 0
        self._pruned_at = 0.0               # 마지막으로 오래된 것을 치운 시각
        self.cases: list[dict] = self._load()
        # ★여기서 prune() 을 부르지 않는다. **만드는 것만으로 파일이 바뀌면**
        #   시험이나 도구가 저장소를 그냥 만들어 보다가 운영 파일을 건드린다
        #   (실제로 시험 한 번에 data/cases_old 가 생겼다). 서버가 뜰 때
        #   server.py 가 한 번 부른다 — 부르는 자리를 눈에 보이게 둔다.

    def _load(self) -> list[dict]:
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save(self) -> None:
        """★잠금 + **제 임시파일**.

        예전에는 둘 다 없었다. 임시파일 이름이 늘 'cases.json.tmp' 하나라,
        LLM 자동 판단이 여럿 동시에 끝나면(_auto_judge 는 케이스마다 실을
        하나씩 띄운다) 같은 파일에 같이 쓰다가, 먼저 끝난 실이 os.replace 로
        그 파일을 걷어가고 나머지는 FileNotFoundError 로 터졌다 —
        **12번 중 7번**이 그랬다(재 봤다). 터진 저장은 호출부가
        '자동 판단 예외' 한 줄로만 찍고 넘어가, 그 판단이 파일에 안 남았다.
        운 나쁘면 두 실의 글이 한 파일에 섞여 cases.json 자체가 깨진다.

        ★속도 때문이 아니다 — 재 보니 저장 폭풍이 화면 요청을 늦추지는
          않았다(json.dump 는 쓸 때마다 GIL 을 놓는다). 잃는 것은 판단이다.
        """
        with self._lock:
            self.rev += 1                      # 내용이 바뀌었다 — 화면 캐시를 깬다
            tmp = f"{self.path}.{os.getpid()}.{threading.get_ident()}.tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.cases, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            except Exception:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                raise

    # ── 오래된 케이스 치우기 ──────────────────────────────────────
    # ★왜 필요한가 — 예전에는 지우는 코드가 아예 없어서 케이스가 영원히
    #   쌓였다. 화면이 3초마다 부르는 /api/cases 가 그만큼 무거워지고
    #   (800건 = 2.9MB), 저장도 느려진다(94ms). 날마다 조금씩 느려지던
    #   이유가 이것이다. 고객이 정한 보관 기간: **30일**.
    # ★지우지 않고 **옮긴다**. data/cases_old/YYYYMM.json 에 붙여 둔다 —
    #   관제 기록을 말없이 없애면 나중에 "그때 그 건" 을 못 찾는다.
    #   보관까지 끄려면 storage.cases_archive 를 빈 값으로 두면 된다.
    # ★언제를 기준으로 하나 — 그 케이스의 **마지막 움직임**이다
    #   (종결 시각 · 마지막 감지 · 없으면 연 시각). 30일 동안 아무 일도
    #   없었던 건이면 화면에서 볼 일이 없다.
    RETENTION_DEFAULT = 30

    def _last_touch(self, c: dict) -> datetime | None:
        for k in ("closed_at", "last_seen", "opened_at"):
            v = c.get(k)
            if v:
                try:
                    return datetime.fromisoformat(v)
                except (TypeError, ValueError):
                    continue
        return None

    def prune(self, now: datetime | None = None, force: bool = False) -> int:
        """보관 기간을 넘긴 케이스를 보관 파일로 옮긴다. 옮긴 건수를 돌려준다.

        ★한 시간에 한 번만 실제로 돈다(force 면 바로). ingest 마다 전체를
          훑으면 그게 또 비용이다 — 하루 한 번만 줄어들어도 충분하다.
        """
        if not self.prunable:               # 리포트용 임시 저장소 등
            return 0
        days = self.cfg.get("policy", {}).get("case_retention_days",
                                              self.RETENTION_DEFAULT)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = self.RETENTION_DEFAULT
        if days <= 0:                       # 0 이하 = 안 치움 (옛 동작 그대로)
            return 0
        t = time.time()
        if not force and t - self._pruned_at < 3600:
            return 0
        self._pruned_at = t

        now = now or datetime.now()
        cut = now - timedelta(days=days)
        with self._lock:
            old = [c for c in self.cases
                   if (self._last_touch(c) or now) < cut]
            if not old:
                return 0
            # ★보관에 실패하면 **안 치운다**. 관제 기록을 아무 데도 안 남기고
            #   없애느니, 파일이 큰 채로 두고 경고를 보는 편이 낫다.
            #   (보관을 아예 끈 설정이면 _archive 가 True 를 돌려준다 — 그때는
            #    사람이 '버려도 된다' 고 정한 것이다.)
            if not self._archive(old):
                return 0
            gone = {id(c) for c in old}
            self.cases = [c for c in self.cases if id(c) not in gone]
            self.save()
        print(f"[케이스] {len(old)}건을 보관으로 옮김 "
              f"(마지막 움직임이 {days}일 넘음, 남은 {len(self.cases)}건)")
        return len(old)

    def _archive(self, old: list[dict]) -> bool:
        """옮긴 케이스를 달마다 한 파일에 붙여 둔다.

        성공하면 True — 그때만 본 목록에서 뺀다. 실패하면 False 라 아무것도
        안 없앤다(파일이 큰 채로 두고 경고를 보는 편이 낫다).
        """
        rel = self.cfg.get("storage", {}).get("cases_archive", "data/cases_old")
        if not rel:
            return True                     # 보관 안 함 — 사람이 그렇게 정했다
        try:
            d = os.path.join(BASE_DIR, rel)
            os.makedirs(d, exist_ok=True)
            by_month: dict[str, list[dict]] = {}
            for c in old:
                t = self._last_touch(c) or datetime.now()
                by_month.setdefault(t.strftime("%Y%m"), []).append(c)
            for ym, lst in by_month.items():
                p = os.path.join(d, f"{ym}.json")
                cur = []
                if os.path.isfile(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            cur = json.load(f)
                    except Exception:       # noqa: BLE001
                        cur = []            # 깨진 보관본 때문에 관제가 멎으면 안 된다
                have = {c.get("id") for c in cur}
                cur.extend(c for c in lst if c.get("id") not in have)
                tmp = f"{p}.{os.getpid()}.{threading.get_ident()}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(cur, f, ensure_ascii=False, indent=2)
                os.replace(tmp, p)
            return True
        except Exception as e:              # noqa: BLE001
            print(f"[케이스] ⚠️ 보관 실패 — **아무것도 안 치웁니다**: "
                  f"{type(e).__name__}: {e}")
            return False

    # ── 조회 ──
    def active(self) -> list[dict]:
        return [c for c in self.cases if c["status"] != "종결"]

    def by_id(self, cid: str) -> dict | None:
        return next((c for c in self.cases if c["id"] == cid), None)

    def _match(self, area: str, now: datetime) -> dict | None:
        """같은 설비/위치의 케이스를 억제 창 안에서만 매칭.

        활성 케이스라도 마지막 감지가 억제 창보다 오래됐으면 별개 사건으로 본다
        (예: 10:27 사건과 15:40 사건은 같은 M16HUB 라도 다른 케이스).
        """
        win = timedelta(minutes=self.cfg.get("policy", {}).get("suppression_window_min", 30))
        for c in reversed(self.cases):
            if c["area"] != area:
                continue
            ref = c.get("closed_at") if c["status"] == "종결" else c.get("last_seen", c["opened_at"])
            if ref and now - datetime.fromisoformat(ref) <= win:
                return c            # 억제 창 안 → 같은 케이스로 병합/재개
            if c["status"] != "종결":
                self._stale_close(c, ref)   # 창 넘긴 활성 케이스는 자동 종료
        return None

    def _stale_close(self, c: dict, ref: str | None) -> None:
        """억제 창을 넘겨 갱신이 끊긴 활성 케이스를 자동 종료."""
        end = datetime.fromisoformat(ref) if ref else datetime.now()
        c["status"] = "종결"
        c["closed_at"] = end.isoformat()
        self._tl(c, end, "자동종결", "억제 창 경과 후 추가 감지 없음 — 자동 종료")

    # ── 감지 반영 ──
    def ingest(self, area: str, dt: datetime, score: float, row: dict) -> dict:
        """감지 1건을 케이스에 반영 (신규 생성 또는 갱신)."""
        self.prune(now=dt)                  # 한 시간에 한 번만 실제로 돈다
        with self._lock:
            g = grade(score, self.cfg)
            c = self._match(area, dt)
            if c is None:
                c = {
                    "id": f"C{dt.strftime('%Y%m%d%H%M%S')}-{area}",
                    "area": area,
                    "location": (row.get("hot_area") or area).strip(),
                    "opened_at": dt.isoformat(),
                    "status": "활성",
                    "peak_score": score,
                    "peak_at": dt.isoformat(),
                    "level": g["level"],
                    "severity": g["severity"],
                    "emoji": g["emoji"],
                    "acked_at": None,
                    "closed_at": None,
                    "recheck_at": None,
                    "timeline": [],
                    "escalations": [],
                    "llm": None,
                    "evidence": {},
                }
                self.cases.append(c)
                self._tl(c, dt, "감지", f"{g['emoji']} {g['level']} {score:.0f}점 최초 감지")
                c["_new"] = True                    # 자동 LLM 판단 대상 표시
            else:
                # 이미 반영한 시각이면 아무것도 하지 않는다 (재폴링 시 중복 방지)
                if c.get("last_seen") and dt <= datetime.fromisoformat(c["last_seen"]) \
                        and score <= c["peak_score"]:
                    return c
                if c["status"] == "종결":
                    c["status"] = "활성"
                    c["closed_at"] = None
                    self._tl(c, dt, "재발", f"억제 창 내 재발 — 같은 케이스로 병합 ({score:.0f}점)")
                    c["_new"] = True

            is_peak = score >= c["peak_score"]
            if score > c["peak_score"]:
                c["peak_score"] = score
                c["peak_at"] = dt.isoformat()
                g2 = grade(score, self.cfg)
                if g2["level"] != c["level"]:
                    self._tl(c, dt, "상향", f"{c['level']} → {g2['level']} ({score:.0f}점)")
                    c["_new"] = True            # 등급 상향 → LLM 재판단
                c.update(level=g2["level"], severity=g2["severity"], emoji=g2["emoji"])

            c["last_seen"] = dt.isoformat()
            # 근거 데이터는 최고점 시점 기준 (AMOS 이상감지 시각 = 사건 최고점 시각)
            if is_peak or not c.get("evidence"):
                c["evidence"] = self._evidence(row)
            self._reschedule(c, dt)
            self.save()
            return c

    def _evidence(self, row: dict) -> dict:
        """근거 데이터 · DB 스냅샷 — 원본 컬럼 그대로 (한글 라벨 붙이지 않음)."""
        bott = " ".join(x for x in (row.get("BOTTLENECK_downward_anomaly_cols", ""),
                                    row.get("BOTTLENECK_upward_anomaly_cols", "")) if x)
        queue = [x for x in " ".join(
            y for y in (row.get("QUEUE_downward_anomaly_cols", ""),
                        row.get("QUEUE_upward_anomaly_cols", "")) if y).split() if x]
        raw_reason = (row.get("reason") or "").strip()
        area = (row.get("hot_area") or "").strip()
        return {
            "zones": hid_zones(bott),
            "items": queue,
            "reason": summarize_reason(raw_reason, area),   # 원문 fallback 금지
            "reason_raw": raw_reason,
            "chain": (row.get("propagation_chain") or "").strip(),
            "flow": (row.get("flow_signals") or "").strip(),
            "maxcapa": (row.get("maxcapa_signals") or "").strip(),
            "affected": [a for a in (row.get("affected_areas") or "").replace(";", " ").split() if a],
        }

    def _tl(self, c: dict, dt: datetime, kind: str, text: str) -> None:
        c["timeline"].append({"at": dt.isoformat(), "kind": kind, "text": text})

    def _routing(self, level: str) -> dict:
        for r in self.cfg.get("policy", {}).get("routing", []):
            if r["level"] == level:
                return r
        return {}

    def _reschedule(self, c: dict, now: datetime) -> None:
        mins = self._routing(c["level"]).get("recheck_min", 5)
        c["recheck_at"] = (now + timedelta(minutes=mins)).isoformat()

    # ── 운영자 액션 ──
    def ack(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            now = datetime.now()
            c["acked_at"] = now.isoformat()
            c["status"] = "확인"
            self._tl(c, now, "확인", f"{who} 확인 처리" + (f" — {note}" if note else ""))
            self._reschedule(c, now)
            self.save()
            return c

    def mark_normal(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        """'이상 없음' — 케이스를 닫지 않고 재확인 예약만 갱신 (정책)."""
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            now = datetime.now()
            self._tl(c, now, "이상없음", f"{who} 이상 없음 판정 — 재확인 예약 갱신" + (f" — {note}" if note else ""))
            self._reschedule(c, now)
            self.save()
            return c

    def close(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            if self.cfg.get("policy", {}).get("close_requires_ack") and not c.get("acked_at"):
                return {"error": "확인 처리 후에 종결할 수 있습니다", "case": c}
            now = datetime.now()
            c["status"] = "종결"
            c["closed_at"] = now.isoformat()
            win = self.cfg.get("policy", {}).get("suppression_window_min", 30)
            self._tl(c, now, "종결", f"{who} 종결" + (f" — {note}" if note else "")
                     + f" (억제 창 {win}분: 재발 시 같은 케이스로 병합)")
            self.save()
            return c

    # ── 에스컬레이션 ──
    def check_escalations(self, now: datetime | None = None) -> list[dict]:
        """미확인 경과 시간에 따른 에스컬레이션 발생분 반환."""
        now = now or datetime.now()
        fired = []
        with self._lock:
            for c in self.cases:
                if c["status"] != "활성" or c.get("acked_at"):
                    continue
                r = self._routing(c["level"])
                elapsed = (now - datetime.fromisoformat(c["opened_at"])).total_seconds() / 60
                for mins, key in ((5, "unack_5m"), (15, "unack_15m")):
                    if elapsed >= mins and key not in [e["stage"] for e in c["escalations"]]:
                        targets = r.get(key, [])
                        if not targets:
                            continue
                        e = {"stage": key, "at": now.isoformat(), "targets": targets}
                        c["escalations"].append(e)
                        self._tl(c, now, "에스컬레이션", f"미확인 {mins}분 → {', '.join(targets)}")
                        fired.append({"case": c["id"], **e})
            if fired:
                self.save()
        return fired

    def due_rechecks(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        return [c for c in self.active()
                if c.get("recheck_at") and datetime.fromisoformat(c["recheck_at"]) <= now]


# ────────────────────────────── 폴링 ──────────────────────────────
def catch_up_range(cfg: dict | None = None) -> tuple[str, str, int]:
    """가져올 구간을 정한다 — 저장된 마지막 시각 ~ 현재.

    · 오늘 저장분이 없으면 오늘 00:00:00 부터 (서버를 늦게 켜도 하루치가 채워진다)
    · 있으면 그 시각부터 (중간에 멈췄던 구간을 메운다)
    반환 (from_dt, to_dt, 빈구간_분)
    """
    cfg = cfg or load_config()
    now = datetime.now()
    day = now.strftime("%Y%m%d")

    last = None
    try:
        from store_csv import last_time
        last = last_time(day, cfg)
    except Exception:
        pass

    start = last if last else now.replace(hour=0, minute=0, second=0, microsecond=0)
    gap = max(0, int((now - start).total_seconds() // 60))
    return start.strftime("%Y%m%d%H%M%S"), now.strftime("%Y%m%d%H%M%S"), gap


def source_mode(cfg: dict | None = None) -> str:
    """데이터를 어디서 받나 — "logpresso"(기본) 또는 "jupyter".

    config.source.mode 로 고른다. jupyter 는 예측 잡이 떨궈 놓는 날짜별
    발동이벤트 CSV 를 그대로 받아 쓴다 (로그프레소·AMOS 조인 불필요).
    """
    cfg = cfg or load_config()
    src = cfg.get("source") or {}
    mode = str(src.get("mode") or "logpresso").strip().lower()
    if mode == "jupyter" and not ((src.get("jupyter") or {}).get("enabled", True)):
        return "logpresso"
    return mode if mode in ("logpresso", "jupyter") else "logpresso"


def scan_once(store: CaseStore, rows: list[dict] | None = None,
              cfg: dict | None = None) -> dict:
    """1회 스캔 — 로그프레소 조회 → 임계 초과분을 케이스에 반영."""
    cfg = cfg or load_config()
    warn, saved, gap = None, None, None
    if rows is None:
        if source_mode(cfg) == "jupyter":
            # ── 주피터 CSV 경로 — 로그프레소를 거치지 않는다 ──
            #   예측 잡이 그 날짜 파일을 계속 갱신하므로, 매 주기 통째로 받아
            #   append_rows 로 넣는다. 이미 있는 시각은 건너뛰므로 결과적으로
            #   증분 수집이 되고, 중간에 빠진 분도 다음 주기에 저절로 메워진다.
            from jupyter_csv import fetch_day
            r = fetch_day("", cfg, verbose=False)
            if not r.get("ok"):
                return {"ok": False, "error": r.get("error"),
                        "detected": 0, "rows": 0, "source": "jupyter"}
            saved = {"written": r["written"], "skipped": r["skipped"],
                     "files": r.get("files") or []}
            gap = None
            # ★방금 파싱한 행을 그대로 쓴다. CSV 를 다시 읽으면 파일명 날짜와
            #   행의 날짜가 어긋날 때(자정 전후, 파일에 전날 꼬리가 섞인 경우)
            #   엉뚱한 빈 날짜를 보게 된다.
            rows = r.get("data") or []
        else:
            # 마지막 저장 시각 ~ 현재까지 (없으면 오늘 00:00부터) — 빈 구간을 메운다
            start, end, gap = catch_up_range(cfg)
            # 기존 데이터 + AMOS 4개 컬럼(ATLAS 2개 테이블 조인)
            rows, err = fetch_amos(from_dt=start, to_dt=end)
            if err and not err.get("warn"):
                return {"ok": False, "error": err.get("reason"),
                        "detected": 0, "rows": 0}
            if err:
                warn = err.get("reason")   # 조인 경고는 감지를 막지 않는다

            # 가져온 데이터를 날짜별 CSV 에 한 줄씩 누적 (나중에 그대로 열어볼 수 있게)
            try:
                from store_csv import append_rows
                saved = append_rows(rows, cfg)
            except Exception as e:
                print(f"[CSV] ⚠️ 저장 실패: {e}")

    floor = alarm_floor(cfg)
    touched = []
    for row in rows:
        dt, sc = _row_dt(row), _score(row)
        if dt is None or sc < floor:
            continue
        area = (row.get("hot_area") or "").strip() or "UNKNOWN"
        touched.append(store.ingest(area, dt, sc, row)["id"])

    fired = store.check_escalations()
    return {
        "ok": True,
        "rows": len(rows),
        "detected": len(touched),
        "cases": sorted(set(touched)),
        "escalations": fired,
        "alarm_floor": floor,
        "active": len(store.active()),
        "amos_warn": warn,
        "saved": saved,
        "gap_min": gap,            # 이번에 메운 빈 구간(분)
        # ★받아온 파일에서 **가장 최근 행의 시각**. 화면이 뒤처져 보일 때
        #   원인이 어디인지 이걸로 갈린다 — 이 값이 이미 몇 분 전이면
        #   예측 잡(원본 CSV)이 늦은 것이고, 이 값은 최신인데 화면이 옛날이면
        #   우리 쪽(수집·표시)이 늦은 것이다.
        "latest": max((d.isoformat() for d in
                       (_row_dt(r) for r in rows) if d), default=None),
        "source": source_mode(cfg),
        "all_rows": rows,          # 정상 포함 전체 — 화면 피드용
    }


if __name__ == "__main__":
    cfg = load_config()
    st = CaseStore(cfg)
    print(f"알람 임계 : {alarm_floor(cfg)}점 (기본 60 + 피드백 보정 {_threshold_nudge(cfg):+d})")
    res = scan_once(st, cfg=cfg)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    for c in st.active():
        print(f"  {c['emoji']} {c['id']} {c['severity']} peak={c['peak_score']:.0f} "
              f"status={c['status']} zones={c['evidence'].get('zones')}")
