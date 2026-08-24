"""
real_time_amhs/fab_score.py — FAB(영역)별 위험도 스코어와 FAB 간 비교

왜 필요한가
    화면은 지금 전체 점수(unified_risk_score) 하나로 돌아간다. 그런데 그 점수는
    **여러 영역이 동시에 걸려야 오르는 구조**다. 스코어 산출 문서의 검증표
    ("예측기 코드를 그대로 호출해 나온 결과") 마지막 줄이 그 말을 한다 —

        허브 한 곳에서 9개 룰이 전부 켜지고 흐름까지 심각해도  ······  44점

    경계 하한이 60 으로 올라간 지금, **한 FAB 만 아무리 심해도 전체 화면에는
    등급조차 안 뜬다.** M16B 는 가중치가 0.5 라 더 심하다. 그래서 FAB 를
    따로 세워 놓고 나란히 봐야 한다. 이 파일이 그걸 한다.

무엇이 추정이고 무엇이 아닌가 — contrib.py 와 정반대다
    contrib.py 는 점수식을 모른 채 '평소 대비 얼마나 벗어났나'로 기여도를
    **추정**한다. 여기는 다르다. 예측기가 룰별 배점을 CSV 에 그대로 떨궈
    준다({FAB}_pts_RA … 9개). 영역점수는 그것들의 합이고, 우리는 그 합을
    저장된 {FAB}_score 와 맞춰 본다. 즉 **여기 숫자는 재현이지 추정이 아니다.**
    맞지 않으면 지어내지 않고 어긋났다고 말한다(`mismatch`).

왜 비교가 되나 — 눈금이 절대값이어서
    9개 룰의 배점(10·5·10·5·8·7·5·3·10×n)과 50점 상한은 **모든 영역이 똑같다.**
    다른 것은 임계값뿐인데, 그건 FAB 마다 평소 수준이 다르니 당연히 달라야
    한다. 그래서 영역점수는 그 자체로 FAB 간 비교가 된다.
    ★반대로 contrib.py 의 robust-z 로는 비교가 안 된다. 늘 나쁜 FAB 은 평소
      기준선도 나빠서 '평소와 같음' 으로 보인다. 비교하려면 상대편차가 아니라
      절대 임계여야 한다 — 이 파일이 z 를 한 번도 쓰지 않는 이유다.

눈금
    area  0~50   예측기가 실제로 쓰는 값. 그대로 둔다.
    risk  0~100  area × 2. 등급(경계 60 · 위험 71 · 초위험 85)과 붙이려고 편 것.
                 컷은 config.grade 에서 읽는다 — 여기에 숫자를 박지 않는다.
    ★risk 는 **그 FAB 자체 등급**이다. 전체 점수와 같은 뜻이 아니다.
      FAB 이 초위험인데 전체는 등급 없음일 수 있고, 그게 정확히 위에서 말한
      구조적 사각지대다.

출처
    임계값·배점·컬럼명은 전부 스코어 산출 문서(hubroom_predictor.py 의
    eval_area_rules / evaluate_unified, thresholds.json)에서 옮겼다.
    코드에 박아 두되 config.json 의 `fab_score` 로 덮을 수 있게 했다 —
    현장에서 thresholds.json 을 고치면 여기도 따라가야 하는데, 그때마다
    파이썬을 고치게 만들면 안 된다.
"""
from __future__ import annotations

# ────────────────────────── 룰 배점 (모든 영역 공통) ──────────────────────────
# 이 표가 FAB 간 비교를 가능하게 하는 근거다 — 배점이 같으니 점수가 같은 뜻이다.
RULES = [
    {"code": "RA",      "pts": 10, "label": "반송·적재 시간 초과",
     "when": "최근 10분 중 1회라도 임계 이상"},
    {"code": "RA_sus",  "pts": 5,  "label": "그 상태가 이어짐",
     "when": "최근 5분 중 3분 이상 · 임계는 R-A 의 70%"},
    {"code": "RB",      "pts": 10, "label": "대기 물량 30분 증가",
     "when": "31분 전 값과 비교"},
    {"code": "RB_fast", "pts": 5,  "label": "10분새 급증",
     "when": "11분 전과 비교 · 임계는 R-B 의 30%"},
    {"code": "RC",      "pts": 8,  "label": "리프터 역증가 · 컨베이어 쏠림",
     "when": "총합은 주는데 개별은 늘어남 (20분 전 대비)"},
    {"code": "RD",      "pts": 7,  "label": "저장·설비 포화",
     "when": "조건 하나만 걸려도 켜짐"},
    {"code": "SLA",     "pts": 5,  "label": "4분 초과 반송 비율",
     "when": "비율이 임계를 넘거나 초과건수가 10분새 +20"},
    {"code": "SORT",    "pts": 3,  "label": "소터 대기 · 이재 실패",
     "when": "이재 실패는 1건만 나도 켜짐"},
    {"code": "MAXCAPA", "pts": 10, "label": "설비 상한 하락", "per": True,
     "when": "임계 이하로 내려간 컬럼 1개당 10점"},
]
RULE_ORDER = [r["code"] for r in RULES]
RULE_BY_CODE = {r["code"]: r for r in RULES}

AREA_CAP = 50          # 한 영역 점수 상한 — 한 곳이 전체를 밀어올리는 것 방지
RAW_FULL = 220         # raw → 100점 환산 기준값 (도달 가능 최댓값이 아니다)
AREA_WEIGHT = {"M16B": 0.5}   # thresholds.json 의 AREA_WEIGHT. 나머지는 1.0

# 융합(STEP 4)에서 한 번 더 더해지는 항 — 그래서 실질 가중치가 두 배다
FUSE_AGAIN = {"SLA": 5, "SORT": 3, "MAXCAPA": 10}
FLOW_BANDS = [(3.0, 30), (2.0, 15), (1.5, 5)]   # 30분 평균 대비 배수 → 점수

# ──────────────────────── FAB 별 '실제로 보고 있는' 컬럼 ────────────────────────
# amos : AMOS 실제 컬럼명 (현장이 아는 이름)
# csv  : 그 값이 실려 오는 발동이벤트 CSV 컬럼 — 없으면 "" (화면에 값이 안 뜬다)
# op   : ">=" 이면 클수록 나쁨, "<=" 이면 작을수록 나쁨
# thr  : 임계값. None 이면 문서에 정의가 없다는 뜻 — 지어내지 않는다.
WATCH: dict[str, dict[str, list[dict]]] = {
    "M16HUB": {
        "RA": [{"amos": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "csv": "M16HUB_ra",
                "label": "반송시간", "unit": "분", "op": ">=", "thr": 9.0}],
        "RA_sus": [{"amos": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN", "csv": "M16HUB_ra",
                    "label": "반송시간 지속", "unit": "분", "op": ">=", "thr": 6.3}],
        "RB": [{"amos": "M16HUB.QUE.M14TOM16.MESCURRENTQCNT", "csv": "M16HUB_rb_diff30",
                "label": "M14→M16 대기 30분 증가", "unit": "건", "op": ">=", "thr": 100}],
        "RB_fast": [{"amos": "M16HUB.QUE.M14TOM16.MESCURRENTQCNT", "csv": "M16HUB_rb_diff10",
                     "label": "같은 대기 10분 증가", "unit": "건", "op": ">=", "thr": 30}],
        "RC": [{"amos": "M16HUB.LFT.{6ABL6011…6ABL0122}.TOTAL_CURRENTQCNT",
                "csv": "M16HUB_rev_count", "label": "역증가 리프터", "unit": "대",
                "op": ">=", "thr": 4}],
        "RD": [{"amos": "M16HUB.STRATE.ALL.FABSTORAGERATIO", "csv": "M16HUB_rd_fab",
                "label": "FAB 저장율", "unit": "%", "op": ">=", "thr": 25.75},
               {"amos": "M16HUB.STRATE.STB.3F_STORAGE_UTIL", "csv": "M16HUB_stb_util",
                "label": "STB 저장율", "unit": "%", "op": ">=", "thr": 99.3},
               {"amos": "M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB", "csv": "",
                "label": "3F→3F MLUD", "unit": "건", "op": ">=", "thr": 50},
               {"amos": "M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT", "csv": "",
                "label": "M14 수동 대기", "unit": "건", "op": ">=", "thr": 30},
               {"amos": "M16HUB.CNV.SENDFAB.TO_M14A_CURRENTQCNT ÷ M16HUB.QUE.CNV.3F_CNV_MAXCAPA",
                "csv": "", "label": "컨베이어 점유율", "unit": "", "op": ">=", "thr": 0.85}],
        "SLA": [{"amos": "M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO", "csv": "sla_M16HUB",
                 "label": "4분 초과율", "unit": "%", "op": ">=", "thr": 5.0},
                {"amos": "M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT", "csv": "M16HUB_sla_cnt",
                 "label": "4분 초과 건수", "unit": "건", "op": "diff10", "thr": 20}],
        "SORT": [{"amos": "M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER", "csv": "sorter_M16HUB",
                  "label": "소터 대기", "unit": "건", "op": ">=", "thr": 30}],
        "MAXCAPA": [{"amos": "M16HUB.QUE.LFT.3F_LFT_MAXCAPA", "csv": "",
                     "label": "3F 리프터 상한", "unit": "", "op": "<=", "thr": 100, "normal": 165},
                    {"amos": "M16HUB.QUE.LFT.3F_M14BLFT_MAXCAPA", "csv": "",
                     "label": "3F M14B 리프터 상한", "unit": "", "op": "<=", "thr": 50, "normal": 66},
                    {"amos": "M16HUB.QUE.CNV.3F_CNV_MAXCAPA", "csv": "",
                     "label": "3F 컨베이어 상한", "unit": "", "op": "<=", "thr": 80, "normal": 129}],
    },
    "M14": {
        "RA": [{"amos": "M14.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M14_ra",
                "label": "적재시간", "unit": "분", "op": ">=", "thr": 3.3}],
        "RA_sus": [{"amos": "M14.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M14_ra",
                    "label": "적재시간 지속", "unit": "분", "op": ">=", "thr": 2.31}],
        "RB": [{"amos": "M14.QUE.ALL.3F_TO_HUB_JOB", "csv": "M14_rb_diff30",
                "label": "3F→HUB 대기 30분 증가", "unit": "건", "op": ">=", "thr": 80}],
        "RB_fast": [{"amos": "M14.QUE.ALL.3F_TO_HUB_JOB", "csv": "M14_rb_diff10",
                     "label": "같은 대기 10분 증가", "unit": "건", "op": ">=", "thr": 24}],
        "RC": [{"amos": "M14.QUE.CNV.M14ATONORTHCURRENTQCNT / …SOUTH…", "csv": "M14_cnv_skew",
                "label": "컨베이어 편중", "unit": "", "op": ">=", "thr": 0.70}],
        "RD": [{"amos": "M14.QUE.OHT.OHTUTIL", "csv": "M14_rd_oht",
                "label": "OHT 가동률", "unit": "%", "op": ">=", "thr": 95.0}],
        "SLA": [{"amos": "M14.QUE.ALL.TRANSPORT4MINOVERRATIO", "csv": "sla_M14",
                 "label": "4분 초과율", "unit": "%", "op": ">=", "thr": 25.45},
                {"amos": "M14.QUE.ALL.TRANSPORT4MINOVERCNT", "csv": "M14_sla_cnt",
                 "label": "4분 초과 건수", "unit": "건", "op": "diff10", "thr": 20}],
        "SORT": [{"amos": "M14.SORTER.ABN.SORTERWAITCOUNTOVER", "csv": "sorter_M14",
                  "label": "소터 대기", "unit": "건", "op": ">=", "thr": 148}],
        "MAXCAPA": [{"amos": "M14.QUE.CNV.3F_CNV_MAXCAPA", "csv": "",
                     "label": "3F 컨베이어 상한", "unit": "", "op": "<=", "thr": 150, "normal": 244}],
    },
    "M14B": {
        "RA": [{"amos": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "csv": "M14B_ra",
                "label": "반송시간", "unit": "분", "op": ">=", "thr": 5.0}],
        "RA_sus": [{"amos": "M14B.QUE.TIME.AVGTOTALTIME1MIN", "csv": "M14B_ra",
                    "label": "반송시간 지속", "unit": "분", "op": ">=", "thr": 3.5}],
        "RB": [{"amos": "M14B.QUE.ALL.7F_TO_HUB_JOB", "csv": "M14B_rb_diff30",
                "label": "7F→HUB 대기 30분 증가", "unit": "건", "op": ">=", "thr": 150}],
        "RB_fast": [{"amos": "M14B.QUE.ALL.7F_TO_HUB_JOB", "csv": "M14B_rb_diff10",
                     "label": "같은 대기 10분 증가", "unit": "건", "op": ">=", "thr": 45}],
        "RC": [],
        "RD": [{"amos": "M14B.QUE.OHT.OHTUTIL", "csv": "M14B_rd_oht",
                "label": "OHT 가동률", "unit": "%", "op": ">=", "thr": 95.0}],
        # ★문서의 SLA 표에 M14B 행이 없다. 컬럼(sla_M14B)은 CSV 에 있는데 임계가
        #   안 적혀 있다 — 지어내지 않고 None 으로 두고 화면에 '임계 미정의' 라고
        #   띄운다. 현장이 thresholds.json 을 보고 채워 넣으면 된다.
        "SLA": [{"amos": "M14B.QUE.ALL.TRANSPORT4MINOVERRATIO", "csv": "sla_M14B",
                 "label": "4분 초과율", "unit": "%", "op": ">=", "thr": None}],
        "SORT": [{"amos": "M14B.SORTER.ABN.SORTERWAITCOUNTOVER", "csv": "sorter_M14B",
                  "label": "소터 대기", "unit": "건", "op": ">=", "thr": 109}],
        "MAXCAPA": [],
    },
    "M16A": {
        "RA": [{"amos": "M16A.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M16A_ra",
                "label": "적재시간", "unit": "분", "op": ">=", "thr": 3.2}],
        "RA_sus": [{"amos": "M16A.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M16A_ra",
                    "label": "적재시간 지속", "unit": "분", "op": ">=", "thr": 2.24}],
        "RB": [{"amos": "M16A.QUE.ALL.6F_TO_HUB_JOB", "csv": "M16A_rb_diff30",
                "label": "6F→HUB 대기 30분 증가", "unit": "건", "op": ">=", "thr": 84}],
        "RB_fast": [{"amos": "M16A.QUE.ALL.6F_TO_HUB_JOB", "csv": "M16A_rb_diff10",
                     "label": "같은 대기 10분 증가", "unit": "건", "op": ">=", "thr": 25}],
        "RC": [],
        "RD": [{"amos": "M16A.QUE.OHT.OHTUTIL", "csv": "M16A_rd_oht",
                "label": "OHT 가동률", "unit": "%", "op": ">=", "thr": 95.0}],
        "SLA": [{"amos": "M16A.QUE.ALL.TRANSPORT4MINOVERRATIO", "csv": "sla_M16A",
                 "label": "4분 초과율", "unit": "%", "op": ">=", "thr": 14.05},
                {"amos": "M16A.QUE.ALL.TRANSPORT4MINOVERCNT", "csv": "M16A_sla_cnt",
                 "label": "4분 초과 건수", "unit": "건", "op": "diff10", "thr": 20}],
        "SORT": [{"amos": "M16A.SORTER.ABN.SORTERWAITCOUNTOVER", "csv": "sorter_M16A",
                  "label": "소터 대기", "unit": "건", "op": ">=", "thr": 180},
                 {"amos": "M16A.SORTER.ABN.SORTERTRANSFERFAIL", "csv": "M16A_sorter_fail",
                  "label": "이재 실패", "unit": "건", "op": ">=", "thr": 1}],
        "MAXCAPA": [{"amos": "M16A.QUE.LFT.2F_LFT_MAXCAPA", "csv": "",
                     "label": "2F 리프터 상한", "unit": "", "op": "<=", "thr": 40, "normal": 54},
                    {"amos": "M16A.QUE.LFT.6F_LFT_MAXCAPA", "csv": "",
                     "label": "6F 리프터 상한", "unit": "", "op": "<=", "thr": 100, "normal": 149}],
    },
    "M16B": {
        "RA": [{"amos": "M16B.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M16B_ra",
                "label": "적재시간", "unit": "분", "op": ">=", "thr": 3.5}],
        "RA_sus": [{"amos": "M16B.QUE.LOAD.AVGLOADTIME1MIN", "csv": "M16B_ra",
                    "label": "적재시간 지속", "unit": "분", "op": ">=", "thr": 2.45}],
        "RB": [{"amos": "M16B.QUE.ALL.10F_TO_HUB_JOB", "csv": "M16B_rb_diff30",
                "label": "10F→HUB 대기 30분 증가", "unit": "건", "op": ">=", "thr": 32}],
        "RB_fast": [{"amos": "M16B.QUE.ALL.10F_TO_HUB_JOB", "csv": "M16B_rb_diff10",
                     "label": "같은 대기 10분 증가", "unit": "건", "op": ">=", "thr": 10}],
        "RC": [],
        "RD": [{"amos": "M16B.QUE.OHT.OHTUTIL", "csv": "M16B_rd_oht",
                "label": "OHT 가동률", "unit": "%", "op": ">=", "thr": 95.0}],
        "SLA": [{"amos": "M16B.QUE.ALL.TRANSPORT4MINOVERRATIO", "csv": "sla_M16B",
                 "label": "4분 초과율", "unit": "%", "op": ">=", "thr": 22.05},
                {"amos": "M16B.QUE.ALL.TRANSPORT4MINOVERCNT", "csv": "M16B_sla_cnt",
                 "label": "4분 초과 건수", "unit": "건", "op": "diff10", "thr": 20}],
        "SORT": [{"amos": "M16B.SORTER.ABN.SORTERWAITCOUNTOVER", "csv": "sorter_M16B",
                  "label": "소터 대기", "unit": "건", "op": ">=", "thr": 90},
                 {"amos": "M16B.SORTER.ABN.SORTERTRANSFERFAIL", "csv": "M16B_sorter_fail",
                  "label": "이재 실패", "unit": "건", "op": ">=", "thr": 1}],
        "MAXCAPA": [],
    },
}

# 점수만 있고 상세 컬럼이 없는 영역 — 문서의 '대상 영역 8개' 중 나머지 셋.
# 비교표에 함께 세워야 "전체 점수가 왜 그 숫자인가" 가 맞아떨어진다.
EXTRA_AREAS = [("M16", "M16_score"), ("M16_PKT", "M16_PKT_score"),
               ("M16_WT", "M16_WT_score")]

# 흐름 항이 보는 노드 — 영역별 개수가 다르다(단독 상한 계산에 쓴다)
FLOW_NODES = {"M16HUB": 2, "M14": 2, "M14B": 3, "M16A": 2, "M16B": 1}


# ────────────────────────────── 설정 덮어쓰기 ──────────────────────────────
def _cfg(cfg: dict | None) -> dict:
    return ((cfg or {}).get("fab_score") or {})


def watch(fab: str, cfg: dict | None = None) -> dict[str, list[dict]]:
    """그 FAB 이 실제로 보고 있는 컬럼 — 룰별로.

    config.fab_score.watch.{FAB}.{RULE} 로 통째 덮거나,
    config.fab_score.thresholds.{FAB}.{RULE} = [값…] 으로 임계만 갈 수 있다.
    현장에서 thresholds.json 이 바뀌면 파이썬을 고치지 않고 여기만 맞춘다.
    """
    f = str(fab or "").upper()
    base = {k: [dict(x) for x in v] for k, v in (WATCH.get(f) or {}).items()}
    c = _cfg(cfg)
    over = ((c.get("watch") or {}).get(f) or {})
    for rule, items in over.items():
        if isinstance(items, list):
            base[rule] = [dict(x) for x in items]
    thr = ((c.get("thresholds") or {}).get(f) or {})
    for rule, vals in thr.items():
        items = base.get(rule) or []
        if not isinstance(vals, list):
            vals = [vals]
        for it, v in zip(items, vals):
            it["thr"] = v
    return base


def area_weight(fab: str, cfg: dict | None = None) -> float:
    w = dict(AREA_WEIGHT)
    w.update((_cfg(cfg).get("area_weight") or {}))
    try:
        return float(w.get(str(fab or "").upper(), 1.0))
    except (TypeError, ValueError):
        return 1.0


def fabs(cfg: dict | None = None) -> list[str]:
    """비교 대상 FAB — config.source.jupyter.fabs 순서를 따른다."""
    try:
        from lp_client import fab_codes
        codes = [c for c in fab_codes(cfg) if c in WATCH]
    except Exception:
        codes = []
    return codes or list(WATCH.keys())


# ────────────────────────────── 값 읽기 ──────────────────────────────
def _num(v):
    try:
        s = str(v).strip()
        return float(s) if s not in ("", "-", "None", "nan", "NaN") else None
    except (TypeError, ValueError):
        return None


def _over(val, op, thr) -> bool | None:
    """임계를 넘었나. 값이나 임계가 없으면 None — False 와 다르다."""
    if val is None or thr is None:
        return None
    try:
        thr = float(thr)
    except (TypeError, ValueError):
        return None
    if op == "<=":
        return val <= thr
    if op == "diff10":       # 10분 증가분 조건 — 여기서는 판정하지 않는다
        return None
    return val >= thr


def readings(row: dict, fab: str, cfg: dict | None = None) -> list[dict]:
    """그 1분에 이 FAB 의 감시 컬럼들이 각각 얼마였나.

    CSV 에 값이 없는 컬럼도 **뺴지 않고** 넣는다. 화면에서 '이 FAB 은 이걸 본다'
    를 보여 주는 게 목적이라, 값이 안 실려 오는 컬럼이라는 사실 자체가 정보다.
    """
    out = []
    for rule in RULE_ORDER:
        for it in (watch(fab, cfg).get(rule) or []):
            v = _num(row.get(it["csv"])) if it.get("csv") else None
            out.append({
                "rule": rule, "amos": it["amos"], "csv": it.get("csv") or "",
                "label": it["label"], "unit": it.get("unit") or "",
                "op": it.get("op") or ">=", "thr": it.get("thr"),
                "normal": it.get("normal"),
                "value": v, "over": _over(v, it.get("op") or ">=", it.get("thr")),
                "has_value": v is not None,
            })
    return out


def _maxcapa_hits(row: dict, fab: str) -> list[str]:
    """maxcapa_signals 텍스트에서 이 FAB 것만 뽑는다.

    예: 'M16A:2F_LFT_MAXCAPA=36(<=40)' — MAXCAPA 는 값 컬럼이 CSV 에 없어서
    이 문자열이 유일한 근거다.
    """
    txt = str(row.get("maxcapa_signals") or "")
    f = str(fab or "").upper()
    out = []
    for part in txt.replace(";", ",").split(","):
        p = part.strip()
        if p.upper().startswith(f + ":"):
            out.append(p[len(f) + 1:].strip())
    return [p for p in out if p]


# ────────────────────────────── 영역 점수 ──────────────────────────────
def area_score(row: dict, fab: str, cfg: dict | None = None) -> dict:
    """한 FAB 의 그 1분 점수 — 룰별 배점을 더하고 50에서 자른다.

    ★{FAB}_pts_* 를 더한 값과 저장된 {FAB}_score 를 **둘 다** 돌려준다.
      같으면 재현된 것이고, 다르면 mismatch 로 알린다. 하나만 골라서
      맞는 척하면, 예측기가 바뀐 날 아무도 모르게 된다.
    """
    f = str(fab or "").upper()
    pts, fired = {}, []
    for code in RULE_ORDER:
        v = _num(row.get(f"{f}_pts_{code}")) or 0.0
        pts[code] = v
        if v > 0:
            fired.append(code)
    total = sum(pts.values())
    capped = min(float(AREA_CAP), total)
    stored = _num(row.get(f"{f}_score"))
    stored_raw = _num(row.get(f"{f}_score_raw"))
    has_pts = any(row.get(f"{f}_pts_{c}") not in (None, "") for c in RULE_ORDER)

    # pts 컬럼이 아예 없는 옛 파일(90컬럼 시절)이면 저장된 점수를 쓴다
    if not has_pts and stored is not None:
        capped, total = stored, (stored_raw if stored_raw is not None else stored)

    mismatch = ""
    if has_pts and stored is not None and abs(capped - stored) > 0.51:
        mismatch = (f"룰 배점 합 {capped:g} ≠ 저장된 {f}_score {stored:g} — "
                    f"예측기 배점이 바뀌었을 수 있습니다")
    return {
        "fab": f, "area": round(capped, 1), "raw": round(total, 1),
        "capped": total > AREA_CAP, "pts": pts, "fired": fired,
        "signals": str(row.get(f"{f}_signals") or "").strip(),
        "stored": stored, "stored_raw": stored_raw, "mismatch": mismatch,
        "has_pts": has_pts, "weight": area_weight(f, cfg),
        "maxcapa": _maxcapa_hits(row, f),
    }


def risk(area: float) -> int:
    """영역점수(0~50) → 0~100. 등급과 붙이려고 눈금만 편 것이다."""
    return int(round(max(0.0, min(float(AREA_CAP), float(area))) * 100.0 / AREA_CAP))


def max_area(fab: str, cfg: dict | None = None) -> dict:
    """이 FAB 이 **받을 수 있는** 영역점수의 최대치.

    상한 50 은 모든 FAB 이 같지만, 룰이 없거나 임계가 안 적힌 FAB 은 거기까지
    갈 수가 없다. M14B 처럼 R-C·MAXCAPA 가 없고 SLA 임계도 미정의면 45점이
    아니라 40점이 천장이다 — 위험도로는 80점, 즉 **초위험 등급에 영원히 못
    간다.** 등급을 붙이기 전에 이걸 알아야 한다.
    """
    f = str(fab or "").upper()
    w = watch(f, cfg)
    gain, lost = 0, {}
    for r in RULES:
        items = w.get(r["code"]) or []
        if not items:
            lost[r["code"]] = ("룰 없음", r["pts"])
            continue
        if r["code"] == "MAXCAPA":
            gain += r["pts"] * len(items)
            continue
        if all(it.get("thr") is None for it in items):
            lost[r["code"]] = ("임계 미정의", r["pts"])
            continue
        gain += r["pts"]
    return {"fab": f, "possible": gain, "area_max": min(AREA_CAP, gain),
            "risk_max": risk(min(AREA_CAP, gain)), "lost": lost,
            "capped": gain >= AREA_CAP}


# ────────────────────────────── 단독 상한 ──────────────────────────────
def solo_ceiling(fab: str, cfg: dict | None = None, mode: str = "typical") -> dict:
    """이 FAB **하나만** 걸렸을 때 전체 점수가 최대 몇 점까지 가나.

    이 함수가 이 파일의 존재 이유다. 값이 경계 컷(60)보다 낮으면, 그 FAB 은
    아무리 망가져도 전체 화면에 등급이 안 뜬다.

    mode 두 가지 — 하나만 쓰면 거짓말이 된다
      "typical" 한 곳이 크게 망가졌을 때 흔히 나오는 모습.
                흐름 노드 1개 심각(30점) · MAXCAPA 1컬럼 하락.
                ★스코어 산출 문서의 검증표 "허브 한 곳에 룰 전부 + 흐름 심각
                  = 44점" 이 정확히 이 경우다. 우리 계산은 45점 (문서는 영역합
                  48, 우리는 상한 50 — 그 2점 차이). 예측기를 직접 호출해 나온
                  숫자와 맞아떨어지므로, 이 계산이 문서를 제대로 읽었다는
                  근거가 된다.
      "max"     그 FAB 의 흐름 노드가 **전부** 심각하고 MAXCAPA 컬럼도 **전부**
                내려간, 현실에서 거의 안 나오는 상한. 이걸로도 경계에 못 가면
                반박의 여지가 없다.

    가정을 숨기지 않는다 (반환값 assume 에 그대로 넣는다):
      · 영역점수는 상한 50 에 닿았다
      · SLA·SORT·MAXCAPA 는 융합에서 한 번 더 더해진다 (문서 STEP 4)
      · 나머지 일곱 영역은 0
    """
    f = str(fab or "").upper()
    w = area_weight(f, cfg)
    wt = watch(f, cfg)
    mc_cols = len(wt.get("MAXCAPA") or [])
    sla_ok = any(it.get("thr") is not None for it in (wt.get("SLA") or []))
    sort_ok = bool(wt.get("SORT"))
    nodes = int((_cfg(cfg).get("flow_nodes") or FLOW_NODES).get(f, 0))

    use_nodes = nodes if mode == "max" else min(1, nodes)
    use_mc = mc_cols if mode == "max" else min(1, mc_cols)

    area = AREA_CAP * w
    flow = use_nodes * FLOW_BANDS[0][1]
    sla = FUSE_AGAIN["SLA"] * w if sla_ok else 0.0
    sort = FUSE_AGAIN["SORT"] * w if sort_ok else 0.0
    mc = FUSE_AGAIN["MAXCAPA"] * use_mc * w
    raw = area + flow + sla + sort + mc
    score = int(min(100, round(raw * 100.0 / RAW_FULL)))
    return {
        "fab": f, "mode": mode, "score": score, "raw": round(raw, 1),
        "parts": {"영역점수": round(area, 1), "흐름": round(flow, 1),
                  "SLA": round(sla, 1), "Sorter": round(sort, 1),
                  "MAXCAPA": round(mc, 1)},
        "weight": w, "flow_nodes": nodes, "maxcapa_cols": mc_cols,
        "used": {"flow_nodes": use_nodes, "maxcapa_cols": use_mc},
        "assume": [f"영역점수 상한 {AREA_CAP} 도달",
                   (f"흐름 노드 {use_nodes}개 심각(3배↑, 노드당 {FLOW_BANDS[0][1]})"
                    if use_nodes else "흐름 0"),
                   f"MAXCAPA {use_mc}컬럼 하락",
                   "SLA·Sorter·MAXCAPA 융합 재가산 포함",
                   "나머지 일곱 영역 0"],
    }


# ────────────────────────────── 한 시각 비교 ──────────────────────────────
def _row_at(rows: list[dict], at):
    from sentinel import _row_dt
    seq = [(d, r) for d, r in ((_row_dt(r), r) for r in rows or []) if d is not None]
    if not seq:
        return None, None
    seq.sort(key=lambda x: x[0])
    if at is None:
        return seq[-1]
    d, r = min(seq, key=lambda x: abs((x[0] - at).total_seconds()))
    return (d, r) if abs((d - at).total_seconds()) <= 300 else (None, None)


def _delta(rows: list[dict], at, fab: str, now: float, back_min: int, cfg) -> float | None:
    """back_min 분 전 대비 영역점수 변화. 그때 행이 없으면 None (0 이 아니다)."""
    if at is None:
        return None
    from datetime import timedelta
    _d0, r0 = _row_at(rows, at - timedelta(minutes=back_min))
    if r0 is None:
        return None
    return round(now - area_score(r0, fab, cfg)["area"], 1)


def compare(rows: list[dict], at=None, cfg: dict | None = None) -> dict:
    """한 시각을 잡고 FAB 을 나란히 세운다 — 이 파일의 화면용 진입점.

    rows 는 **ALL 시스템**(전체 CSV)의 행이어야 한다. FAB 분리 파일은 자기
    영역 컬럼만 있어서 비교가 안 된다.
    """
    from sentinel import grade, grade_cuts
    from lp_client import load_config
    cfg = cfg or load_config()
    dt, row = _row_at(rows, at)
    if row is None:
        return {"ok": False, "error": ("데이터가 없습니다" if not rows
                                       else f"{at:%H:%M} 근처에 데이터가 없습니다")}

    warn, danger, crit = grade_cuts(cfg)
    back = int(_cfg(cfg).get("delta_min") or 30)

    out = []
    for f in fabs(cfg):
        a = area_score(row, f, cfg)
        r = risk(a["area"])
        g = grade(r, cfg)
        a.update({
            "risk": r, "level": g["level"], "emoji": g["emoji"],
            "contrib": round(a["area"] * a["weight"], 1),
            "delta": _delta(rows, dt, f, a["area"], back, cfg),
            "solo": solo_ceiling(f, cfg),
            "readings": readings(row, f, cfg),
        })
        out.append(a)
    out.sort(key=lambda d: (-d["area"], d["fab"]))
    for i, d in enumerate(out):
        d["rank"] = i + 1

    extra = []
    for name, col in EXTRA_AREAS:
        v = _num(row.get(col))
        if v is not None:
            extra.append({"area_name": name, "col": col, "score": round(v, 1),
                          "risk": risk(v)})

    uni = _num(row.get("unified_risk_score")) or 0.0
    ug = grade(uni, cfg)
    blind = [d["fab"] for d in out if d["solo"]["score"] < warn]
    return {
        "ok": True,
        "at": dt.strftime("%Y-%m-%d %H:%M"),
        "cuts": {"warn": warn, "danger": danger, "critical": crit},
        "unified": {"score": round(uni, 1), "level": ug["level"], "emoji": ug["emoji"],
                    "hot_area": str(row.get("hot_area") or "").strip(),
                    "stage": str(row.get("stage") or "").strip(),
                    "stage_name": str(row.get("stage_name") or "").strip(),
                    "flow_score": _num(row.get("flow_score")),
                    "reason": str(row.get("reason") or "").strip()},
        "fabs": out, "extra_areas": extra, "delta_min": back,
        "rules": RULES, "area_cap": AREA_CAP, "raw_full": RAW_FULL,
        "blind": blind,
        "note": (f"영역점수는 9개 룰의 배점(합 50 상한)이 모든 FAB 에서 같아 "
                 f"그대로 비교됩니다. 위험도는 그 점수를 100점으로 편 값이고 "
                 f"등급 컷은 {warn}/{danger}/{crit} 입니다 — "
                 f"**FAB 자체 등급이라 전체 점수와 같은 뜻이 아닙니다.**"),
    }


def fuse_check(row: dict, cfg: dict | None = None) -> dict:
    """저장된 컬럼만으로 전체 점수를 다시 계산해 본다 (문서 STEP 4 재현).

    맞으면 우리가 문서를 제대로 읽은 것이고, 틀리면 어디가 다른지 보인다.
    화면에는 '검증' 칸으로만 쓴다 — 예측기 값을 이걸로 대체하지 않는다.
    """
    areas = sum(area_score(row, f, cfg)["area"] * area_weight(f, cfg)
                for f in fabs(cfg))
    for _name, col in EXTRA_AREAS:
        areas += (_num(row.get(col)) or 0.0)
    flow = _num(row.get("flow_score")) or 0.0
    sla = _num(row.get("sla_score_total")) or 0.0
    sort = _num(row.get("sorter_score_total")) or 0.0
    mc = _num(row.get("mc_score_total")) or 0.0
    raw = areas + flow + sla + sort + mc
    calc = int(min(100, round(raw * 100.0 / RAW_FULL)))
    stored = _num(row.get("unified_risk_score"))
    return {"areas": round(areas, 1), "flow": flow, "sla": sla, "sorter": sort,
            "maxcapa": mc, "raw": round(raw, 1), "calc": calc, "stored": stored,
            "match": stored is not None and abs(calc - stored) <= 1,
            "formula": f"min(100, round(raw × 100 ÷ {RAW_FULL}))"}


# ────────────────────────────── 명령줄 ──────────────────────────────
if __name__ == "__main__":
    import json
    import sys
    from datetime import datetime
    from lp_client import load_config
    from store_csv import list_days, read_day
    cfg = load_config()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    day = args[0] if args else (list_days(cfg) or
                                [{"day": datetime.now().strftime("%Y%m%d")}])[-1]["day"]
    rows = read_day(day, cfg)
    at = datetime.strptime(f"{day} {args[1]}", "%Y%m%d %H:%M") if len(args) > 1 else None
    if "--ceiling" in sys.argv:
        from sentinel import grade_cuts
        w0 = grade_cuts(cfg)[0]
        print(f"경계 컷 {w0}점 기준 — 이 FAB 하나만 걸렸을 때 전체 점수 상한")
        for f in fabs(cfg):
            t = solo_ceiling(f, cfg, "typical")
            m = solo_ceiling(f, cfg, "max")
            print(f"  {f:8s} 통상 {t['score']:3d}점 · 최대 {m['score']:3d}점  "
                  f"(가중치 {t['weight']:g}, 흐름노드 {t['flow_nodes']}, "
                  f"MAXCAPA {t['maxcapa_cols']}컬럼)"
                  f"{'   ← 최대로도 경계에 못 감' if m['score'] < w0 else ''}")
        raise SystemExit(0)
    d = compare(rows, at, cfg)
    if not d.get("ok"):
        print(d.get("error"))
        raise SystemExit(1)
    print(f"■ {d['at']}  전체 {d['unified']['score']}점 "
          f"{d['unified']['emoji']}{d['unified']['level']}  "
          f"최고구역 {d['unified']['hot_area']}")
    for f in d["fabs"]:
        print(f"  {f['rank']}. {f['fab']:8s} 영역 {f['area']:5.1f}/50  "
              f"위험도 {f['risk']:3d} {f['emoji']}{f['level']:4s}  "
              f"룰 {'+'.join(f['fired']) or '-':28s} "
              f"단독상한 {f['solo']['score']}점")
    print("  사각지대(단독으로는 경계에 못 닿는 FAB):", ", ".join(d["blind"]) or "없음")
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    if "--verify" in sys.argv:
        _dt, r = _row_at(rows, at)
        print(json.dumps(fuse_check(r, cfg), ensure_ascii=False, indent=2))
