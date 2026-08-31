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
    {"code": "RA",      "pts": 10, "label": "반송지연",
     "when": "최근 10분 중 1회라도 임계 이상"},
    {"code": "RA_sus",  "pts": 5,  "label": "반송지연 지속",
     "when": "최근 5분 중 3분 이상 · 임계는 시간 초과 기준의 70%"},
    {"code": "RB",      "pts": 10, "label": "Queue 누적",
     "when": "31분 전 값과 비교"},
    {"code": "RB_fast", "pts": 5,  "label": "Queue 급증",
     "when": "11분 전과 비교 · 임계는 30분 증가 기준의 30%"},
    {"code": "RC",      "pts": 8,  "label": "리프터 정체",
     "when": "총합은 주는데 개별은 늘어남 (20분 전 대비)"},
    {"code": "RD",      "pts": 7,  "label": "Storage FULL",
     "when": "조건 하나만 걸려도 켜짐"},
    {"code": "SLA",     "pts": 5,  "label": "4분초과",
     "when": "비율이 임계를 넘거나 초과건수가 10분새 +20"},
    {"code": "SORT",    "pts": 3,  "label": "분류기 대기",
     "when": "이재 실패는 1건만 나도 켜짐"},
    {"code": "MAXCAPA", "pts": 10, "label": "운영자 용량변경", "per": True,
     "when": "임계 이하로 내려간 컬럼 1개당 10점"},
]
RULE_ORDER = [r["code"] for r in RULES]
RULE_BY_CODE = {r["code"]: r for r in RULES}

AREA_CAP = 50          # 융합에 들어갈 때 잘리는 상한 (예측기의 SATURATE_AT)
# ★area_score 의 분모. 예측기(발동이벤트_영역분리.py)의 DEFAULT_DENOM 과
#   같은 값이어야 한다 — 여기를 AREA_CAP(50) 으로 쓰면 점수가 40% 부풀어
#   raw 35 가 70점(위험)이 된다. 실제로 그 오보를 냈다. 올바른 값은 50점.
AREA_DENOM = 70        # 영역등급.json 의 "분모" (config.fab_score.denom 로 덮음)
RAW_FULL = 220         # raw → 100점 환산 기준값 (도달 가능 최댓값이 아니다)
# ★M16B 가중 0.5 는 **취소**됐다 (2026-08) — 전 영역 1.0.
#   config.fab_score.area_weight 로 덮을 수 있게 두되 기본은 비운다.
AREA_WEIGHT: dict[str, float] = {}   # thresholds.json 의 AREA_WEIGHT. 기본 1.0

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
               # ★2026-08 고객 요청 — R-D 판정에서 STB 항 제거.
               #   값은 계속 수집·기록된다(M16HUB_stb_util 컬럼 유지)므로
               #   화면에는 보여 주되 **임계 판정은 하지 않는다**.
               #   thr=None + record_only 로, '넘음' 표시가 절대 안 붙는다.
               {"amos": "M16HUB.STRATE.STB.3F_STORAGE_UTIL", "csv": "M16HUB_stb_util",
                "label": "STB 저장율 (기록용·판정 미사용)", "unit": "%",
                "op": ">=", "thr": None, "record_only": True},
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

# ── ALL(전체)이 보는 컬럼 ──
# ALL 은 영역이 아니라서 R-A 같은 영역 룰이 없다. 그렇다고 보는 컬럼이 없는
# 것은 아니다 — **융합 단계에서 보는 것들**이 따로 있다. 이걸 빼면 "ALL 은
# 컬럼이 없다" 는 틀린 말이 된다.
#
#   FLOW  10개 흐름 노드. 임계값이 아니라 **최근 30분 평균 대비 몇 배**로
#         판정한다 (3.0배↑ 30점 · 2.0배↑ 15점 · 1.5배↑ 5점). 그래서 영역별
#         기준값이 없다 — 이 표에 thr 이 없는 이유다.
#   집계  SLA·Sorter·MAXCAPA 가 걸린 영역 수를 모아 놓은 CSV 컬럼.
#   판정  점수·최고구역·단계처럼 ALL 만 갖는 결과 컬럼.
FLOW_COLS = [
    ("M16HUB", "HUB_OHT_QCNT", "M16HUB.QUE.OHT.CURRENTOHTQCNT"),
    ("M16HUB", "M14_TO_M16", "M16HUB.QUE.M14TOM16.MESCURRENTQCNT"),
    ("M14", "M14_CNV_TO_HUB", "M14.QUE.CNV.M14ATOM16ACURRNETQCNT"),
    ("M14", "M14_TO_HUB_JOB", "M14.QUE.ALL.3F_TO_HUB_JOB"),
    ("M14B", "M14B_7F_TO_HUB", "M14B.QUE.ALL.7F_TO_HUB_JOB"),
    ("M14B", "M14B_LFT_4ABLD_SUM", "M14B.LFT.4ABLD_ALL.TOTAL_CURRENTQCNT_SUM"),
    ("M14B", "M14B_LFT_4ABLD_TO_HUB_SUM",
     "M14B.LFT.4ABLD_ALL.7F_TO_4F_CURRENTQCNT_SUM"),
    ("M16A", "M16A_6F_TO_HUB", "M16A.QUE.ALL.6F_TO_HUB_JOB"),
    ("M16A", "M16A_2F_TO_HUB", "M16A.QUE.ALL.2F_TO_HUB_JOB"),
    ("M16B", "M16B_10F_TO_HUB", "M16B.QUE.ALL.10F_TO_HUB_JOB"),
]

WATCH_ALL = {
    # ★흐름 노드 10개는 **CSV 에 값 컬럼이 없다** — 무엇을 보는지 알려 주는
    #   정의일 뿐이라, 이것만 두면 화면에 빈 줄 열 개가 선다.
    #   실제로 실려 오는 flow_signals(어느 노드가 몇 배인지 글자)를 같이 준다.
    "FLOW": [{"amos": "(집계)", "csv": "flow_signals",
              "label": "흐름 — 어느 노드가 몇 배인가", "unit": "",
              "op": "text", "thr": None}]
            + [{"amos": amos, "csv": "", "label": f"{area} · {node}",
                "unit": "배", "op": "ratio30", "thr": None, "area": area,
                "no_csv": True}
               for area, node, amos in FLOW_COLS],
    "SLA": [{"amos": "(집계)", "csv": "sla_score_total",
             "label": "SLA 합계 — 걸린 영역 수 × 5", "unit": "점",
             "op": "sum", "thr": None}],
    "SORT": [{"amos": "(집계)", "csv": "sorter_score_total",
              "label": "Sorter 합계 — 걸린 영역 수 × 3", "unit": "점",
              "op": "sum", "thr": None}],
    "MAXCAPA": [{"amos": "(집계)", "csv": "mc_score_total",
                 "label": "MAXCAPA 합계 — 내려간 컬럼 수 × 10 × 영역수",
                 "unit": "점", "op": "sum", "thr": None},
                {"amos": "(집계)", "csv": "maxcapa_signals",
                 "label": "어느 컬럼이 내려갔나", "unit": "", "op": "text",
                 "thr": None}],
    "FUSE": [{"amos": "(집계)", "csv": "flow_score", "label": "흐름 항 점수",
              "unit": "점", "op": "sum", "thr": None},
             {"amos": "(집계)", "csv": "layer1_total", "label": "1층 합계",
              "unit": "점", "op": "sum", "thr": None}],
    "SCORE": [{"amos": "unified_risk_score", "csv": "unified_risk_score",
               "label": "전체 점수", "unit": "점", "op": "score", "thr": None},
              {"amos": "hot_area", "csv": "hot_area", "label": "최고 위험 구역",
               "unit": "", "op": "text", "thr": None},
              {"amos": "stage", "csv": "stage", "label": "단계",
               "unit": "", "op": "text", "thr": None}],
}
ALL_RULES = [
    {"code": "FLOW", "pts": 30, "label": "흐름 — 30분 평균 대비 배수",
     "when": "노드마다 3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5", "per": True},
    {"code": "SLA", "pts": 5, "label": "SLA — 걸린 영역 수만큼", "per": True},
    {"code": "SORT", "pts": 3, "label": "Sorter — 걸린 영역 수만큼", "per": True},
    {"code": "MAXCAPA", "pts": 10, "label": "MAXCAPA — 내려간 컬럼 수만큼",
     "per": True},
    {"code": "FUSE", "pts": 0, "label": "융합 집계"},
    {"code": "SCORE", "pts": 0, "label": "판정 결과"},
]
ALL_RULE_ORDER = [r["code"] for r in ALL_RULES]

# 점수만 있고 상세 컬럼이 없는 영역 — 문서의 '대상 영역 8개' 중 나머지 셋.
# 비교표에 함께 세워야 "전체 점수가 왜 그 숫자인가" 가 맞아떨어진다.
# ★M16_PKT 제외 (2026-08 고객 요청) — 예측기에서 영역 자체가 빠져
#   M16_PKT_score 컬럼도 더는 안 온다. 발동이벤트는 135 → 134 컬럼.
EXTRA_AREAS = [("M16", "M16_score"), ("M16_WT", "M16_WT_score")]

# 흐름 항이 보는 노드 — 영역별 개수가 다르다(단독 상한 계산에 쓴다).
# FLOW_COLS 에서 세므로 두 곳에 숫자를 적지 않는다.
FLOW_NODES = {a: sum(1 for x, _n, _c in FLOW_COLS if x == a)
              for a, _n, _c in FLOW_COLS}


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
    src = WATCH_ALL if f == "ALL" else (WATCH.get(f) or {})
    base = {k: [dict(x) for x in v] for k, v in src.items()}
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


def screen_metrics(sys: str, cfg: dict | None = None) -> list[dict]:
    """**화면이 이미 그리고 있는** 지표 목록 — 새로 정의하지 않는다.

      ALL  config.ui.metric_groups 의 'AMOS 컬럼' 묶음 (20개)
      FAB  lp_client._fab_strip(FAB)  (12개 안팎)

    ★이 파일이 WATCH 로 따로 표를 만든 것은 '어느 룰의 어느 임계에 걸리는가'
      를 붙이기 위해서지, 컬럼 목록을 새로 정하려던 게 아니다. 목록은 여기,
      이미 있는 정의에서 가져온다. 두 곳에 적으면 반드시 갈라진다.
    """
    s = str(sys or "ALL").strip().upper()
    if s in ("", "ALL"):
        groups = ((cfg or {}).get("ui") or {}).get("metric_groups") or []
        for g in groups:
            if str(g.get("id") or "").lower() == "amos":
                return [dict(m) for m in (g.get("metrics") or []) if m.get("key")]
        return [dict(m) for m in ((groups[0].get("metrics") if groups else []) or [])
                if m.get("key")]
    from lp_client import _fab_strip
    return [dict(m) for m in _fab_strip(s)]


def join_columns(sys: str, cfg: dict | None = None) -> dict:
    """화면 지표 ⇄ 룰/임계 를 맞춰 본다.

    돌려주는 것
      metrics  화면 지표마다 → 어느 룰이 쓰는지, 임계는 얼마인지
               ('룰이 안 쓰는 지표' 는 참고용 표시 지표라는 뜻이다)
      only_rule 룰은 보는데 화면 목록에 없는 컬럼 (화면에서 근거를 못 본다)
    """
    s = str(sys or "ALL").strip().upper() or "ALL"
    w = watch(s, cfg)
    by_csv: dict[str, list[tuple[str, dict]]] = {}
    for rule in rule_order(s):
        for it in (w.get(rule) or []):
            if it.get("csv"):
                by_csv.setdefault(it["csv"], []).append((rule, it))

    out, seen = [], set()
    for m in screen_metrics(s, cfg):
        key = m.get("key")
        seen.add(key)
        used = by_csv.get(key) or []
        out.append({
            "key": key, "raw": m.get("raw") or key,
            "label": m.get("label") or key, "unit": m.get("unit") or "",
            "rules": [r for r, _ in used],
            "thr": [it.get("thr") for _, it in used],
            "op": [it.get("op") for _, it in used],
            "used": bool(used),
        })
    only_rule = []
    for csv_col, used in by_csv.items():
        if csv_col in seen:
            continue
        rule, it = used[0]
        only_rule.append({"key": csv_col, "raw": it["amos"], "label": it["label"],
                          "rules": [r for r, _ in used], "thr": it.get("thr")})
    # 컬럼이 아예 없는 룰 항목(MAXCAPA 등)도 알려 준다 — 화면에 값이 안 뜬다
    no_csv = []
    for rule in rule_order(s):
        for it in (w.get(rule) or []):
            if not it.get("csv"):
                no_csv.append({"rule": rule, "raw": it["amos"],
                               "label": it["label"], "thr": it.get("thr")})
    return {"sys": s, "metrics": out, "only_rule": only_rule, "no_csv": no_csv,
            "n_used": sum(1 for m in out if m["used"]), "n_screen": len(out)}


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


def rule_order(sys: str) -> list[str]:
    """그 시스템의 룰 순서. ALL 은 영역 룰이 아니라 융합 항을 쓴다."""
    return ALL_RULE_ORDER if str(sys or "").upper() == "ALL" else RULE_ORDER


def rules_of(sys: str) -> list[dict]:
    return ALL_RULES if str(sys or "").upper() == "ALL" else RULES


def readings(row: dict, fab: str, cfg: dict | None = None) -> list[dict]:
    """그 1분에 이 시스템의 감시 컬럼들이 각각 얼마였나 (ALL 포함).

    CSV 에 값이 없는 컬럼도 **빼지 않고** 넣는다. 화면에서 '이건 이걸 본다'
    를 보여 주는 게 목적이라, 값이 안 실려 오는 컬럼이라는 사실 자체가 정보다.
    """
    out = []
    w = watch(fab, cfg)
    for rule in rule_order(fab):
        for it in (w.get(rule) or []):
            # ★op="text" 는 글자 컬럼이다 (hot_area·flow_signals·maxcapa_signals).
            #   예전엔 이것도 _num() 으로 읽어서 'M16HUB' 가 None 이 됐다 —
            #   값이 멀쩡히 있는데 화면에는 늘 '값 없음' 으로 떴다.
            is_text = (it.get("op") or "") == "text"
            if not it.get("csv"):
                v = None
            elif is_text:
                v = str(row.get(it["csv"]) or "").strip() or None
            else:
                v = _num(row.get(it["csv"]))
            out.append({
                "rule": rule, "amos": it["amos"], "csv": it.get("csv") or "",
                "label": it["label"], "unit": it.get("unit") or "",
                "op": it.get("op") or ">=", "thr": it.get("thr"),
                "normal": it.get("normal"),
                "value": v, "over": _over(v, it.get("op") or ">=", it.get("thr")),
                "has_value": v is not None,
                # ★기록만 하고 판정에는 안 쓰는 컬럼 (2026-08 R-D 의 STB).
                #   '임계 미정의(값이 없어 판정 불가)' 와 구분해야 한다 —
                #   이건 값이 있는데 **일부러 판정에서 뺀** 것이다.
                "record_only": bool(it.get("record_only")),
                "is_text": is_text,
                # ★값 컬럼이 아예 없는 정의 항목 (흐름 노드 10개 등).
                #   화면은 이걸 한 줄로 묶어야 한다 — 빈 줄 열 개는 화면이
                #   아니라 소음이다.
                "no_csv": bool(it.get("no_csv")) or not it.get("csv"),
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
def _is_fab_row(row: dict) -> bool:
    """jupyter_csv._fab_rows() 가 정규화한 FAB 분리 파일의 행인가.

    정규화하면 area_score 가 unified_risk_score 자리로 옮겨 가고, 원래 전체
    점수는 all_score 로 밀려난다. all_score 가 있으면 그 행이다.
    """
    return bool(str(row.get("all_score") or "").strip())


def _stored_area(row: dict, fab: str) -> tuple[float | None, str]:
    """그 FAB 의 **저장된** 영역점수를 찾는다 — 파일마다 이름이 다르다.

    ★이 시스템은 이미 area_score 라는 이름을 쓰고 있다. 새로 지어내지 않고
      쓰던 이름을 그대로 따라간다.

      통합 파일 ({day}_발동이벤트.csv)      {FAB}_score
      FAB 분리 파일 (fab분리/…_{FAB}.csv)   area_score   ← 그 FAB 자기 점수
      정규화된 행 (jupyter_csv._fab_rows)   unified_risk_score
                                            (area_score 를 여기로 옮겼다.
                                             lp_client._fab_strip 이 이 키를
                                             raw='area_score' 로 그린다)

    찾은 값과 **어느 컬럼에서 찾았는지**를 같이 준다 — 어긋났다고 말할 때
    어느 이름이 어긋났는지 못 밝히면 확인할 수가 없다.
    """
    f = str(fab or "").upper()
    for col in (f"{f}_score", "area_score"):
        v = _num(row.get(col))
        if v is not None:
            return v, col
    # 정규화된 FAB 행이면 unified_risk_score 가 그 FAB 의 점수다.
    # ★hot_area 도 FAB 코드로 바뀌어 있으므로 남의 FAB 점수를 집지 않는다.
    if _is_fab_row(row) and str(row.get("hot_area") or "").strip().upper() == f:
        v = _num(row.get("unified_risk_score"))
        if v is not None:
            return v, "unified_risk_score(=area_score)"
    return None, ""



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
    stored, stored_col = _stored_area(row, f)
    stored_raw = _num(row.get(f"{f}_score_raw"))
    has_pts = any(row.get(f"{f}_pts_{c}") not in (None, "") for c in RULE_ORDER)

    # pts 컬럼이 아예 없는 옛 파일(90컬럼 시절)이면 저장된 점수를 쓴다
    if not has_pts and stored is not None:
        capped, total = stored, (stored_raw if stored_raw is not None else stored)

    mismatch = ""
    if has_pts and stored is not None and abs(capped - stored) > 0.51:
        mismatch = (f"룰 배점 합 {capped:g} ≠ 저장된 {stored_col} {stored:g} — "
                    f"예측기 배점이 바뀌었을 수 있습니다")
    return {
        "fab": f, "area": round(capped, 1), "raw": round(total, 1),
        "capped": total > AREA_CAP, "pts": pts, "fired": fired,
        "signals": str(row.get(f"{f}_signals") or "").strip(),
        "stored": stored, "stored_col": stored_col, "stored_raw": stored_raw,
        "mismatch": mismatch,
        "has_pts": has_pts, "weight": area_weight(f, cfg),
        "maxcapa": _maxcapa_hits(row, f),
    }


def area_denoms(cfg: dict | None = None) -> dict:
    """영역별 **실효 분모** — 발동이벤트_영역분리.py 의 load_denoms 와 같은 규칙.

        점수 = raw × 100 ÷ 분모 × 조정 ÷ 100   →   실효 분모 = 분모 ÷ (조정/100)

    현장 설정은 영역등급.json 에 있고, 여기서는 config.json 의
    fab_score.denom / fab_score.adjust 로 덮는다.
    """
    fs = _cfg(cfg or {}) or {}
    base = fs.get("denom", AREA_DENOM)
    adj = fs.get("adjust") or {}
    out = {}
    for f in fabs(cfg):
        try:
            b = float(base[f]) if isinstance(base, dict) else float(base)
        except (KeyError, TypeError, ValueError):
            b = float(AREA_DENOM)
        try:
            p = float(adj.get(f, 100)) or 100.0
        except (TypeError, ValueError):
            p = 100.0
        out[f] = b / (p / 100.0) if b > 0 else float(AREA_DENOM)
    return out


def area_score_100(raw: float, fab: str = "", cfg: dict | None = None) -> int:
    """raw(룰 배점 합, 상한 없음) → **area_score 0~100**.

    ★예측기(발동이벤트_영역분리.py)의 정의 그대로다:
          area_score = min(100, round(score_raw × 100 ÷ 실효분모))
      분모 기본값은 **70**. 예전엔 여기서 AREA_CAP(50)으로 나눴는데,
      그건 '융합에 들어갈 때 잘리는 상한' 이지 점수 분모가 아니다.
      그래서 raw 35 가 70점(위험)으로 나와 **경계 60 인데 35에서 울렸다**
      (실제 지적). 올바른 값은 50점 — 정상이다.
    """
    den = area_denoms(cfg).get(str(fab or "").upper(), float(AREA_DENOM))
    if den <= 0:
        return 0
    return int(min(100, round(max(0.0, float(raw)) * 100.0 / den)))


def risk(area: float) -> int:
    """(옛 이름) 영역점수 → 0~100.

    ★분모가 AREA_CAP(50) 이라 예측기와 40% 어긋났다. 새 코드는
      area_score_100(raw, fab, cfg) 을 쓴다 — 이 함수는 옛 호출부 호환용으로만
      남기고, 등급 판정에는 쓰지 않는다.
    """
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


# ────────────────────────────── ALL (전체) ──────────────────────────────
def all_row(row: dict, cfg: dict | None = None) -> dict:
    """전체(ALL) 를 FAB 과 같은 줄에 세운다.

    ★왜 따로 만드나 — ALL 은 FAB 이 아니다.
      FAB 은 '영역' 이고 9개 룰을 임계와 대조해 0~50 점을 받는다.
      ALL 은 그 8개 영역 점수에 흐름·SLA·Sorter·MAXCAPA 를 더해 raw 를 만들고
      raw 220 을 100 으로 환산한 값이다. 그래서 ALL 에는
        · 자기 임계값이 없고 (영역이 아니니까)
        · 단독 상한도 없고 (자기가 전체니까)
        · 영역점수(0~50)도 없다 (이미 0~100 이다)
      대신 ALL 만 가진 것이 있다 — 융합 5개 항, 8개 영역 중 몇 곳이 걸렸나,
      룰별로 몇 개 영역에서 켜졌나, 단계·최고구역.

    ★눈금 주의 — ALL 의 100점과 FAB 위험도의 100점은 **뜻이 다르다.**
      ALL 60점은 실제로 경보가 나는 지점이고, FAB 60점은 그 FAB 의 영역점수가
      30점(상한 50 중)이라는 뜻이다. 같은 자에 올려 놓고 보되, 화면과 문서에
      무엇을 잰 값인지 반드시 같이 적는다.
    """
    from sentinel import grade
    from lp_client import load_config
    cfg = cfg or load_config()

    # ★FAB 분리 파일의 행이면 unified_risk_score 는 **그 FAB 의 점수**다
    #   (정규화가 area_score 를 거기로 옮겨 놨다). 그대로 읽으면 한 FAB 의
    #   점수를 전체 점수라고 화면에 띄우게 된다. 원본은 all_score 에 있다.
    from_fab_file = _is_fab_row(row)
    sc = _num(row.get("all_score" if from_fab_file else "unified_risk_score")) or 0.0
    g = grade(sc, cfg)

    # 룰마다 '몇 개 영역에서 켜졌나' — 전체 점수가 왜 그 숫자인지 한눈에 본다
    per_rule, hit_fabs = {}, []
    for code in RULE_ORDER:
        n = sum(1 for f in fabs(cfg) if (_num(row.get(f"{f}_pts_{code}")) or 0) > 0)
        per_rule[code] = n
    for f in fabs(cfg):
        a = area_score(row, f, cfg)
        if a["area"] > 0:
            hit_fabs.append(f)

    fuse = fuse_check(row, cfg)
    extra = []
    for name, col in EXTRA_AREAS:
        v = _num(row.get(col))
        if v is not None:
            extra.append({"area_name": name, "col": col, "score": round(v, 1)})
    n_extra = sum(1 for x in extra if x["score"] > 0)
    return {
        "fab": "ALL", "is_all": True,
        "score": round(sc, 1), "level": g["level"], "emoji": g["emoji"],
        "measures": "8개 영역 융합 → raw ÷ %d × 100" % RAW_FULL,
        "from_fab_file": from_fab_file,
        "score_col": "all_score" if from_fab_file else "unified_risk_score",
        "readings": readings(row, "ALL", cfg),
        "areas_hit": len(hit_fabs) + n_extra, "areas_total": len(fabs(cfg)) + len(extra),
        "hit_fabs": hit_fabs,
        "per_rule": per_rule,
        "fuse": fuse,
        "extra_areas": extra,
        "hot_area": str(row.get("hot_area") or "").strip(),
        "stage": str(row.get("stage") or "").strip(),
        "stage_name": str(row.get("stage_name") or "").strip(),
        "flow_signals": str(row.get("flow_signals") or "").strip(),
        "maxcapa_signals": str(row.get("maxcapa_signals") or "").strip(),
        "reason": str(row.get("reason") or "").strip(),
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


def fab_area_at(day: str, at, fab: str, cfg: dict | None = None) -> dict | None:
    """FAB **분리 파일**(data/{FAB}/{day}_TOTAL.CSV)의 그 시각 area_score.

    ★이게 그 FAB 의 **진짜 점수**다. 통합(ALL) 파일의 {FAB}_pts_* 를 더해
      되계산하는 것보다 이쪽이 원본이다 — 예측기가 배점을 바꾸면 되계산은
      틀리지만 area_score 는 예측기가 직접 적어 준 값이라 안 틀린다.
      (실제 지적: "FAB 폴더 안에 area_score 컬럼 다 있는데 왜 다른 걸 보냐")

    반환 {area, col, at, day} 또는 None (그 파일·그 시각이 없으면).
    """
    from lp_client import load_config, sys_cfg
    from store_csv import read_day
    cfg = cfg or load_config()
    f = str(fab or "").upper()
    try:
        rows = read_day(day, sys_cfg(cfg, f))
    except Exception:                                  # noqa: BLE001
        return None
    if not rows:
        return None
    dt, row = _row_at(rows, at)
    if row is None:
        return None
    for col in ("area_score", "unified_risk_score", f"{f}_score", "score"):
        v = _num(row.get(col))
        if v is not None:
            return {"area": round(float(v), 1), "col": col, "at": dt, "day": day,
                    # 예측기가 같이 적어 준 등급·포화 — 우리가 다시 매기지 않는다
                    "level": str(row.get("area_level") or "").strip(),
                    "saturated": str(row.get("area_saturated") or "").strip() == "Y",
                    "raw": _num(row.get("area_score_raw") or row.get(f"{f}_score_raw"))}
    return None


def _delta(rows: list[dict], at, fab: str, now: float, back_min: int, cfg) -> float | None:
    """back_min 분 전 대비 영역점수 변화. 그때 행이 없으면 None (0 이 아니다)."""
    if at is None:
        return None
    from datetime import timedelta
    _d0, r0 = _row_at(rows, at - timedelta(minutes=back_min))
    if r0 is None:
        return None
    return round(now - area_score(r0, fab, cfg)["area"], 1)


def _all_delta(rows: list[dict], at, now: float, back_min: int) -> float | None:
    """전체 점수의 back_min 분 전 대비 변화. 그때 행이 없으면 None."""
    if at is None:
        return None
    from datetime import timedelta
    _d0, r0 = _row_at(rows, at - timedelta(minutes=back_min))
    if r0 is None:
        return None
    return round(now - (_num(r0.get("unified_risk_score")) or 0.0), 1)


def _fab_cfg(cfg, fab):
    """그 FAB 의 설정 뷰 — 등급 컷이 시스템별로 다르다.

    ★lp_client.sys_cfg 는 얕은 사본에 _sys 만 바꾼다. grade 블록은 공유하므로
      정책을 고치면 여기도 바로 따라온다.
    """
    if not cfg:
        return {}          # ★None 을 돌려주면 grade() 가 터진다
    try:
        from lp_client import sys_cfg
        return sys_cfg(cfg, str(fab or "").upper()) or cfg
    except Exception:      # noqa: BLE001  (설정이 없어도 매기는 건 계속돼야 한다)
        return cfg


def compare(rows: list[dict], at=None, cfg: dict | None = None,
            day: str | None = None) -> dict:
    """한 시각을 잡고 **ALL + FAB 다섯**을 나란히 세운다 — 화면용 진입점.

    rows 는 **ALL 시스템**(전체 CSV)의 행이어야 한다. FAB 분리 파일은 자기
    영역 컬럼만 있어서 비교가 안 된다.

    day 를 주면 각 FAB 의 **분리 파일**(data/{FAB}/{day}_TOTAL.CSV)에서
    area_score 를 읽어 그 FAB 점수로 쓴다 — 예측기가 직접 적어 준 원본이라,
    통합 파일의 배점 합으로 되계산하는 것보다 정확하다. 없으면 되계산으로
    물러서고, 두 값이 다르면 mismatch 에 적는다.

    ★반환값 rows[] 가 화면이 그대로 돌면 되는 목록이다 — 첫 줄이 ALL,
      그 다음이 FAB 다섯. 관제 화면의 시스템 고르기(ALL + FAB 5)와 같은
      구성이라, 화면에 있는 시스템이 비교표에 없는 일이 생기지 않는다.
      score 는 여섯 줄 모두 0~100 이지만 **잰 대상이 다르다** — 각 줄의
      measures 에 무엇을 잰 값인지 적어 둔다.
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
    day_q = "".join(ch for ch in str(day or "") if ch.isdigit())[:8] \
        or (dt.strftime("%Y%m%d") if dt is not None else "")
    for f in fabs(cfg):
        a = area_score(row, f, cfg)
        # ★FAB 분리 파일(data/{FAB}/{day}_TOTAL.CSV)의 area_score 가 있으면
        #   그것이 원본이다 — 통합 파일에서 되계산한 값보다 우선한다.
        #   (실제 지적: "FAB 폴더에 area_score 컬럼 다 있는데 왜 다른 걸 보냐")
        own = fab_area_at(day_q, dt, f, cfg) if day_q else None
        # ★눈금을 섞지 않는다 — 둘은 다른 수다.
        #     area       0~50   룰 배점 합을 융합 상한에서 자른 값 (융합 기여분)
        #     area_score 0~100  예측기가 매기는 점수 = min(100, raw×100÷분모)
        #   등급(60/71/85)은 **area_score** 에 붙는다.
        if own is not None and own["col"] == "area_score":
            r = int(round(float(own["area"])))        # 예측기가 적어 준 그 값
            a["source"], a["score_col"] = "fab_file", own["col"]
        else:
            r = area_score_100(a.get("raw", a["area"]), f, cfg)
            a["source"] = "calc"
            a["score_col"] = "{}_score_raw ÷ 분모".format(f)
            if own is not None:                        # area_score 는 아니지만 값은 있다
                a["file_value"] = own["area"]
                a["file_col"] = own["col"]
        a["area_score"] = r
        # ★FAB 마다 **자기 컷**으로 매긴다. 예전엔 루프 밖에서 한 번 읽은
        #   cfg 로 여섯 줄을 다 매겼다 — ALL 화면에서 부르면 M14 를 40 으로
        #   낮춰 놔도 ALL 의 60 으로 매겨져서, 정책 탭에서 시스템별로
        #   설정한 것이 화면에 하나도 안 나타났다 (실제 지적).
        fcfg = _fab_cfg(cfg, f)
        # ★등급은 **정책이 정한다**. 예전엔 FAB 분리 파일의 area_level 이
        #   있으면 그걸 그대로 썼다. 그러면 정책 탭에서 컷을 내려도 FAB 줄이
        #   안 따라온다 — 실제 증상: "M14 가 70 까지 올라가는데 왜 이상이
        #   없다고 하지?" (컷은 경계 35 로 보이는데 등급만 '정상' 이었다.
        #   예측기가 자기 기준으로 '정상' 이라고 적어 둔 값이 이긴 것이다.)
        #
        #   ALL 줄은 원래부터 정책으로 매긴다(all_row). 여기만 파일을 따르면
        #   한 표 안에서 두 줄이 서로 다른 자로 재는 셈이다.
        #
        #   예측기가 뭐라고 했는지는 **버리지 않고** 같이 싣는다 — 다르면
        #   그 사실이 보여야 한다. 조용히 한쪽을 고르면 나중에 왜 다른지 모른다.
        g = grade(r, fcfg)
        fl = str((own or {}).get("level") or "").strip()
        if fl and fl != g["level"]:
            a["file_level"] = fl
            a["level_mismatch"] = ("예측기는 '{}' 로 적었지만 지금 정책(경계 {})"
                                   "으로는 '{}' 입니다"
                                   .format(fl, grade_cuts(fcfg)[0], g["level"]))
        elif fl:
            a["file_level"] = fl
        fw, fd, fc = grade_cuts(fcfg)
        a.update({
            "is_all": False,
            # ★이 줄의 등급이 어느 컷으로 매겨진 것인지 같이 준다. 안 주면
            #   화면이 ALL 컷으로 다시 칠해서 서버와 다른 색을 낸다.
            "cuts": {"warn": fw, "danger": fd, "critical": fc},
            "saturated": bool(own and own.get("saturated")),
            "risk": r, "score": r, "level": g["level"], "emoji": g["emoji"],
            "measures": (f"FAB 분리 파일의 area_score {r:g}점 (예측기 값)"
                         if a.get("source") == "fab_file"
                         else f"raw {a.get('raw', 0):g} × 100 ÷ 분모 "
                              f"{area_denoms(cfg).get(f, AREA_DENOM):g} = {r:g}점"),
            "contrib": round(a["area"] * a["weight"], 1),
            "delta": _delta(rows, dt, f, a["area"], back, cfg),
            "solo": solo_ceiling(f, cfg),
            "max_area": max_area(f, cfg),
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
                          "risk": area_score_100(v, name, cfg)})

    # ★ALL 을 첫 줄에 세운다. 관제 화면의 시스템 고르기가 ALL + FAB 5 이므로
    #   비교표도 같은 여섯 줄이어야 한다 (하나라도 빠지면 "내 시스템이 없다").
    a_all = all_row(row, cfg)
    a_all.update({"rank": 0, "risk": a_all["score"],
                  "delta": _all_delta(rows, dt, a_all["score"], back)})
    six = [a_all] + out

    blind = [d["fab"] for d in out if d["solo"]["score"] < warn]
    return {
        "ok": True,
        "at": dt.strftime("%Y-%m-%d %H:%M"),
        "cuts": {"warn": warn, "danger": danger, "critical": crit},
        # 화면은 이 목록만 돌면 된다 — 첫 줄 ALL, 그 다음 FAB 다섯
        "rows": six,
        "all": a_all,
        # 옛 이름들 — 이미 쓰고 있는 화면이 깨지지 않게 그대로 둔다
        "unified": {"score": a_all["score"], "level": a_all["level"],
                    "emoji": a_all["emoji"], "hot_area": a_all["hot_area"],
                    "stage": a_all["stage"], "stage_name": a_all["stage_name"],
                    "flow_score": _num(row.get("flow_score")),
                    "reason": a_all["reason"]},
        "fabs": out, "extra_areas": extra, "delta_min": back,
        "rules": RULES, "area_cap": AREA_CAP, "raw_full": RAW_FULL,
        "blind": blind,
        "note": (f"여섯 줄 모두 0~100 이고 등급 컷도 같습니다 "
                 f"(경계 {warn} · 위험 {danger} · 초위험 {crit}). "
                 f"다만 **잰 대상이 다릅니다** — ALL 은 8개 영역을 융합한 "
                 f"전체 점수(실제로 경보가 나는 값)이고, FAB 은 그 영역의 "
                 f"영역점수({AREA_CAP} 상한)를 100점으로 편 값입니다. "
                 f"{AREA_CAP} 은 등급 컷이 아니라 영역점수 상한입니다."),
    }


# ── FAB 선 색 ──────────────────────────────────────────────────────────
# 추이 그래프·구간 그래프에 FAB 영역점수를 겹쳐 그릴 때 쓰는 색.
#
# ★눈으로 고른 값이 아니다. 다크 배경(#0D1119)에서 다섯이 서로, 그리고
#   전체 점수선(시안 #3DDBE8)·등급 점(노랑·주황·빨강)과도 구분되는지
#   OKLab ΔE 로 재서 골랐다 — 적록색약 8.1(기준 8) · 정상시야 15.9(기준 15) ·
#   등급 밴드 네 개 위에서 대비 3.08:1 이상.
#   손으로 고른 조합은 전부 떨어졌다: 파랑과 보라는 눈에는 달라 보여도
#   적록색약에서 ΔE 1.3 까지 붙는다. 바꾸려면 다시 재고 바꿀 것.
# ★주황·빨강 계열은 통과하는 조합이 있어도 뺐다. 관제 화면에서 그 색은
#   '위험' 이라는 뜻이라, 그냥 FAB 선인데 경보로 읽힌다.
# ★static/dashboard.html 의 FAB_COLOR 와 **같아야 한다**
#   (tests/test_area_table.py 가 두 표가 어긋나면 실패시킨다).
FAB_COLOR = {
    "M14":    "#3f93f7",
    "M14B":   "#3d8f40",
    "M16A":   "#824df9",
    "M16B":   "#b973c6",
    "M16HUB": "#d7038b",
}
FAB_COLOR_FALLBACK = "#8FA0B6"


def fab_color(fab: str) -> str:
    return FAB_COLOR.get(str(fab or "").upper(), FAB_COLOR_FALLBACK)


def files_sig(day: str, cfg: dict | None = None) -> tuple:
    """FAB 분리 파일 다섯의 (mtime, 크기) — 피드 캐시 서명용.

    area_table() 이 이 파일들을 읽으므로, 화면 캐시는 이 파일이 바뀐 것도
    알아야 한다. 지금 보는 시스템의 파일만 보고 캐시하면 FAB 컬럼만 옛
    값에 얼어붙는다 — 오래된 값을 보여주는 게 안 보여주는 것보다 나쁘다.

    stat 다섯 번이라 읽기보다 훨씬 싸다. 없는 파일도 자리를 남겨서
    '생겼다/없어졌다' 가 서명에 잡히게 한다.
    """
    import os
    try:
        from lp_client import load_config, sys_cfg
        from store_csv import day_path
    except Exception:                                   # noqa: BLE001
        return ()
    cfg = cfg or load_config()
    out = []
    for f in fabs(cfg):
        try:
            st = os.stat(day_path(day, sys_cfg(cfg, f)))
            out.append((f, st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((f, None, None))
    return tuple(out)


def divergence(row: dict, cfg: dict | None = None) -> dict | None:
    """ALL 점수와 FAB 다섯 점수가 **엇갈릴 때** 그게 무슨 뜻인가.

    ★ALL 과 FAB 은 배점표가 겹치지 않는다. 그래서 한쪽만 올라가는 일이
      구조적으로 생긴다 — 그걸 사람이 매번 눈으로 맞춰 보고 있었다.
        ALL 에만  FLOW 30점 (30분 평균 대비 배수 · 10개 노드)
        FAB 에만  RA 10 · RA_sus 5 · RB 10 · RB_fast 5 · RC 8 · RD 7 = 45점
        공통      SLA 5 · SORT 3 · MAXCAPA 10 (걸린 영역 수만큼)

    돌려주는 네 갈래
      전체물량   ALL 이 컷 이상인데 FAB 은 전부 정상
                 → FAB 배점에 없는 것은 FLOW 뿐이다. 물량이 올라온 것이다.
      단일FAB    ALL 은 컷 미만인데 FAB **한 곳**이 경계 이상
                 → 한 FAB 만 걸려서는 ALL 이 구조적으로 못 따라온다
                   (FAB 40점이 ALL 로는 최대 18점). 놓치기 쉬운 자리다.
      FAB전이    ALL 은 컷 미만인데 FAB **두 곳 이상**이 경계 이상
                 → ★전이라고 단정하지 않는다. propagation_chain 이 있으면
                   그 방향을 그대로 쓰고, 없으면 '확정 못 함' 으로 둔다.
                   없는 인과를 만들면 관제가 엉뚱한 FAB 을 본다.
      None       엇갈리지 않는다 (둘 다 올랐거나 둘 다 조용하다) — 할 말 없음

    row 에 {FAB}_pts_* 가 없으면(ALL 파일이 아니면) None. 남의 FAB 점수를
    지어내지 않는다.
    """
    from lp_client import load_config, sys_cfg
    from sentinel import grade_cuts
    cfg = cfg or load_config()
    codes = fabs(cfg)
    if not codes:
        return None

    all_sc = _num(row.get("unified_risk_score"))
    if all_sc is None:
        return None
    all_cut = grade_cuts(sys_cfg(cfg, "ALL"))[0]

    hot, quiet, known = [], [], 0
    for f in codes:
        a = area_score(row, f, cfg)
        # ★근거가 있는 FAB 만 센다. 없는 것을 0(정상)으로 채우면
        #   "FAB 전부 정상" 이라는 잘못된 결론이 나온다.
        if not (a["has_pts"] or _num(row.get(f"{f}_score")) is not None):
            continue
        known += 1
        sc = area_score_100(a.get("raw", a["area"]), f, cfg)
        cut = grade_cuts(sys_cfg(cfg, f))[0]     # ★FAB 마다 컷이 다르다
        (hot if sc >= cut else quiet).append({"fab": f, "score": sc, "cut": cut})
    if not known:
        return None

    hot.sort(key=lambda x: -x["score"])
    base = {"all": round(all_sc, 1), "all_cut": all_cut,
            "hot": hot, "quiet": quiet, "known": known}
    chain = (row.get("propagation_chain") or "").strip()

    if all_sc >= all_cut and not hot:
        return {**base, "kind": "전체물량",
                "text": ("ALL 이 {:.0f}점({}점 이상)인데 FAB 다섯은 전부 자기 "
                         "경계 미만이다. FAB 배점에 없고 ALL 에만 있는 것은 "
                         "흐름(30분 평균 대비 배수)뿐이므로, 특정 FAB 고장이 "
                         "아니라 **전체적으로 물량이 올라온 것**으로 읽어야 "
                         "한다.").format(all_sc, all_cut)}

    if all_sc < all_cut and len(hot) == 1:
        h = hot[0]
        return {**base, "kind": "단일FAB",
                "text": ("ALL 은 {:.0f}점으로 {}점 미만인데 {} 가 {}점(경계 {}) "
                         "으로 올라와 있다. 한 FAB 만 걸리면 ALL 이 구조적으로 "
                         "못 따라온다 — **{} 에서 문제가 진행 중일 수 있다.** "
                         "ALL 이 조용하다고 정상으로 보면 안 된다."
                         ).format(all_sc, all_cut, h["fab"], h["score"],
                                  h["cut"], h["fab"])}

    if all_sc < all_cut and len(hot) >= 2:
        names = ", ".join("{}({}점)".format(x["fab"], x["score"]) for x in hot)
        if chain:
            tail = ("전이 경로가 **{}** 로 적혀 있다 — 그 방향대로 한 FAB 이 "
                    "다른 FAB 에 영향을 주고 있는 것으로 읽어라.").format(chain)
        else:
            tail = ("전이 경로가 비어 있어 **한 FAB 이 옮긴 것인지 각각 따로 "
                    "생긴 것인지는 확정할 수 없다.** 둘 다 짚되 원인을 하나로 "
                    "단정하지 마라.")
        return {**base, "kind": "FAB전이",
                "text": ("ALL 은 {:.0f}점으로 {}점 미만인데 FAB 두 곳 이상이 "
                         "경계 이상이다 — {}. {}").format(all_sc, all_cut,
                                                          names, tail)}
    return None


def area_table(rows: list[dict], day: str | list | None = None,
               cfg: dict | None = None) -> dict:
    """하루치 행 전부의 **FAB 다섯 점수(0~100)** 를 한 번에 낸다 — 목록용.

    compare() 는 한 시각만 세우지만 관제 목록은 하루치(1440행)를 통째로
    그린다. 행마다 compare()/fab_area_at() 을 부르면 FAB 분리 파일을 행
    수만큼 다시 훑고 정렬하게 돼서(1440×5) 화면이 멈춘다. 그래서 **FAB 당
    파일 한 번**만 읽어 분 단위로 색인해 두고 행을 훑는다.

    ★점수 정의는 compare() 와 **똑같다** — FAB 분리 파일의 area_score 가
      있으면 그게 원본이고, 없을 때만 통합 파일의 배점 합으로 되계산한다.
      정의를 여기서 새로 지으면 같은 시각인데 목록과 비교표가 다른 수를
      보여준다. 다른 것은 '한 번에 훑는다' 뿐이다.

    ★어느 화면에서 불러도 된다. 다섯 점수의 원본은 **FAB 분리 파일**이라
      (data/{FAB}/{day}_TOTAL.CSV) 지금 보고 있는 시스템이 M14 든 ALL 이든
      똑같이 읽어 온다. rows 는 되계산 fallback 에만 쓴다.

    반환
        fabs  비교 대상 FAB 과 그 순서
        cuts  {FAB: {warn, danger, critical}} — FAB 마다 컷이 다르다.
              화면은 이 컷으로 글자색을 칠한다. 한 벌만 내려 주고 ALL 컷으로
              칠하게 두면 서버와 다른 색이 난다 (compare() 가 줄마다 cuts 를
              같이 주는 것과 같은 이유).
        rows  {분(ISO): {s: {FAB: 점수}, hi: 제일 높은 FAB, hi_score: 그 점수,
                         lv: {FAB: 등급}}}
              s 에 **없는 FAB 은 값을 모르는 것**이다 (그 날 분리 파일이
              없거나 그 분이 비었다). 0 과 구분해야 해서 빼고 보낸다.
              lv 는 **예측기가 적어 준 등급이 컷 판정과 다를 때만** 넣는다
              (compare() 가 area_level 을 우선하는 것과 같은 규칙). 매 행마다
              다 실으면 하루치가 그만큼 무거워진다.
    """
    from sentinel import _row_dt, grade, grade_cuts
    from lp_client import load_config
    cfg = cfg or load_config()
    codes = fabs(cfg)

    def _key(d):
        return d.replace(second=0, microsecond=0).isoformat()

    # ── FAB 분리 파일을 FAB 당 한 번만 읽어 분 단위로 색인 ──────────────
    own: dict[str, dict] = {}
    # day 는 하나여도 되고 여러 개여도 된다 — 구간 그래프는 자정을 걸치면
    # 이틀치를 본다. 그때 한 날만 색인하면 나머지 날은 되계산으로 떨어져,
    # 같은 화면 안에서 앞뒤 값의 출처가 달라진다.
    days = [day] if isinstance(day, str) else list(day or [])
    day_q = []
    for d in days:
        q = "".join(ch for ch in str(d or "") if ch.isdigit())[:8]
        if q and q not in day_q:
            day_q.append(q)
    if day_q:
        from lp_client import sys_cfg
        from store_csv import read_day
        for f in codes:
            ix = {}
            for dq in day_q:
                try:
                    frows = read_day(dq, sys_cfg(cfg, f))
                except Exception:                      # noqa: BLE001
                    continue                           # 그 날만 되계산으로
                for fr in frows or []:
                    d = _row_dt(fr)
                    if d is None:
                        continue
                    # 정규화된 FAB 행은 area_score 가 unified_risk_score 자리로
                    # 옮겨져 있다 (jupyter_csv._fab_rows) — 둘 다 본다.
                    for col in ("area_score", "unified_risk_score"):
                        v = _num(fr.get(col))
                        if v is not None:
                            ix[_key(d)] = {"area": int(round(float(v))),
                                           "level": str(fr.get("area_level") or "").strip()}
                            break
            if ix:
                own[f] = ix

    cuts, fcfgs = {}, {}
    for f in codes:
        fcfgs[f] = _fab_cfg(cfg, f)
        w, dg, c = grade_cuts(fcfgs[f])
        cuts[f] = {"warn": w, "danger": dg, "critical": c}

    out: dict[str, dict] = {}
    for r in rows or []:
        d = _row_dt(r)
        if d is None:
            continue
        k = _key(d)
        s, lv = {}, {}
        for f in codes:
            o = (own.get(f) or {}).get(k)
            if o is not None:
                s[f] = o["area"]
                # 예측기 등급이 우리 컷 판정과 다르면 그 사실을 실어 보낸다.
                # 우리가 조용히 다시 매기면 등급 기준이 두 벌이 된다.
                if o["level"] and o["level"] != grade(s[f], fcfgs[f])["level"]:
                    lv[f] = o["level"]
            else:
                # ★되계산은 **그 FAB 이름이 붙은 컬럼**이 이 행에 있을 때만
                #   한다. _stored_area() 는 {f}_score 가 없으면 area_score 로
                #   물러서는데, M14 분리 파일 행에서 M16A 를 물으면 그 값이
                #   M14 자기 점수라 남의 점수를 M16A 것으로 집어온다.
                a = area_score(r, f, cfg)
                if a["has_pts"] or _num(r.get(f"{f}_score")) is not None:
                    s[f] = area_score_100(a.get("raw", a["area"]), f, cfg)
                # 근거가 없으면 **넣지 않는다**. 0 으로 채우면 화면이 그
                # FAB 을 '정상' 으로 읽는다 — 모르는 것과 괜찮은 것은 다르다.
        hi, hs = "", -1
        for f in codes:                     # 동점이면 fabs() 순서가 앞선 FAB
            if f in s and s[f] > hs:
                hi, hs = f, s[f]
        # 다섯이 전부 0 이면 '제일 높은 FAB' 이라는 말이 성립하지 않는다.
        # 아무 데도 안 걸린 분에 M14 를 지목하면 그게 오보다.
        out[k] = {"s": s, "hi": (hi if hs > 0 else ""), "hi_score": max(hs, 0)}
        if lv:
            out[k]["lv"] = lv
    return {"fabs": codes, "cuts": cuts, "rows": out}


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
    from store_csv import latest_day, read_day
    cfg = load_config()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    # ★[-1] 은 '가장 오래된 날' 이었다 (list_days 는 최신순)
    day = args[0] if args else (latest_day(cfg) or
                                datetime.now().strftime("%Y%m%d"))
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
    c = d["cuts"]
    print(f"■ {d['at']}   등급 컷 경계 {c['warn']} · 위험 {c['danger']} · "
          f"초위험 {c['critical']}")
    a = d["all"]
    print(f"  ALL      전체 {a['score']:5.1f}/100 {a['emoji']}{a['level']:4s}  "
          f"영역 {a['areas_hit']}/{a['areas_total']} 걸림 · 최고구역 "
          f"{a['hot_area']} · {a['stage_name']}")
    print(f"           raw {a['fuse']['raw']:g} = 영역합 {a['fuse']['areas']:g} + "
          f"흐름 {a['fuse']['flow']:g} + SLA {a['fuse']['sla']:g} + "
          f"소터 {a['fuse']['sorter']:g} + MC {a['fuse']['maxcapa']:g}")
    for f in d["fabs"]:
        print(f"  {f['rank']}. {f['fab']:8s} 영역 {f['area']:5.1f}/{AREA_CAP}  "
              f"위험도 {f['risk']:3d} {f['emoji']}{f['level']:4s}  "
              f"룰 {'+'.join(f['fired']) or '-':28s} "
              f"단독상한 {f['solo']['score']}점")
    print(f"  ※ {AREA_CAP} 은 영역점수 상한이지 등급 컷이 아니다 "
          f"(경계는 {c['warn']}).")
    print("  사각지대(단독으로는 경계에 못 닿는 FAB):", ", ".join(d["blind"]) or "없음")
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    if "--verify" in sys.argv:
        _dt, r = _row_at(rows, at)
        print(json.dumps(fuse_check(r, cfg), ensure_ascii=False, indent=2))
