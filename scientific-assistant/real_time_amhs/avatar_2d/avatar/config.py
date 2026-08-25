# -*- coding: utf-8 -*-
"""
앱의 모든 '내용 설정'은 여기 한 파일에 모여 있다.
스케줄, FAB, 알람 등급, 사원증, 의상/배경, 기본 페르소나까지 —
브라우저(app.js)는 시작할 때 /api/config 로 이 값을 받아서 그대로 쓴다.
바꾸고 싶으면 이 파일만 고치고 서버를 재시작하면 된다.
"""

# ── LLM 엔드포인트 목록 (run.py 시작 메뉴) ──────────────────────────────
ENDPOINTS = [
    ("http://hcp.llm.skhynix.com",     "HCP (운영)"),
    ("http://dev.hcp.llm.skhynix.com", "HCP (개발)"),
    ("http://common.llm.skhynix.com",  "Common"),
    ("https://api.openai.com",         "OpenAI"),
]

# ── 감정/모션 (LLM 출력 스키마의 enum — app.js 의 EMO/MOTION 과 같아야 한다) ──
EMO_KEYS = ["neutral", "smile", "joy", "sad", "angry", "surprise",
            "shy", "think", "smug", "fear", "sleepy", "love"]
MOTION_KEYS = ["none", "nod", "shake", "bounce", "jump", "lean",
               "shiver", "pop", "wave", "handup", "tap", "cross"]

# ── 하루 일과 (시간이 되면 배경·의상·사원증이 자동으로 바뀐다) ───────────
#    from > to 면 자정을 넘어가는 구간으로 해석한다.
SCHEDULE = [
    {"from": "07:00", "to": "08:30", "bg": "정문"},
    {"from": "08:31", "to": "10:00", "bg": "공장"},
    {"from": "10:01", "to": "11:30", "bg": "회의실"},
    {"from": "11:31", "to": "13:30", "bg": "정문"},
    {"from": "13:31", "to": "14:30", "bg": "회의실"},
    {"from": "14:31", "to": "16:50", "bg": "공장"},
    {"from": "16:51", "to": "17:10", "bg": "회의실"},
    {"from": "17:11", "to": "19:30", "bg": "테라스"},
    {"from": "19:31", "to": "06:59", "bg": "집"},
]

# ── 배경 (costume: COSTUMES 인덱스, badge: 사원증 표시 여부. 없으면 유지) ──
BACKGROUNDS = [
    {"name": "기본",   "img": None},
    {"name": "공장",   "img": "assets/bg_factory.jpg", "costume": 2, "badge": True},
    {"name": "회의실", "img": "assets/bg_meeting.jpg", "costume": 0, "badge": True},
    {"name": "정문",   "img": "assets/bg_gate.jpg",    "costume": 1, "badge": True},
    {"name": "테라스", "img": "assets/bg_terrace.jpg", "costume": 3, "badge": False},
    {"name": "집",     "img": "assets/bg_room.jpg",    "costume": 4, "badge": False},
]

# ── 의상 (patch: 손 위치가 다른 그림만 armA/armB 좌표를 덮어쓴다) ────────
COSTUMES = [
    {"name": "정장",   "src": "assets/suit.png",  "real": False},
    {"name": "가운",   "src": "assets/coat.png",  "real": False},
    {"name": "무진복", "src": "assets/clean.png", "real": False,
     "patch": {"armA": [0.382, 0.848], "armB": [0.598, 0.848],
               "armA_rad": [0.070, 0.056], "armB_rad": [0.070, 0.056]}},
    {"name": "반팔",   "src": "assets/tee.png",   "real": False,
     "patch": {"armA": [0.382, 0.848], "armB": [0.598, 0.848],
               "armA_rad": [0.070, 0.056], "armB_rad": [0.070, 0.056]}},
    # 잠옷은 손을 맞잡고 있어서 두 팔 영역이 겹치면 손가락이 찢어진다.
    # 팔 영역을 소매 쪽으로 빼고 반경을 줄여 중앙 손깍지는 건드리지 않는다.
    {"name": "잠옷",   "src": "assets/pj.png",    "real": False,
     "patch": {"armA": [0.352, 0.852], "armB": [0.636, 0.852],
               "armA_rad": [0.058, 0.050], "armB_rad": [0.058, 0.050]}},
]

# ── 사원증 ────────────────────────────────────────────────────────────────
BADGE = {"name": "미라", "en": "MIRA", "dept": "물류기술팀 · AMHS", "id": "SKH-2026-0417"}
BADGE_LOGO = "assets/logo.png"

# ── 관제 서버 (real_time_amhs) ────────────────────────────────────────────
# 버추얼 에이전트의 데이터 소스. run.py --sentinel 로 덮을 수 있다.
#   url        관제 서버 주소 (기본: 같은 PC 의 8989)
#   poll_ms    브라우저 알람 폴링 주기 (서버 캐시 5초라 더 줄여도 소용없다)
SENTINEL = {
    "url": "http://127.0.0.1:8989",
    "poll_ms": 5000,
}

# ── FAB 알람 ──────────────────────────────────────────────────────────────
# ★관제 서버의 시스템 목록(ALL + FAB 5)과 같아야 한다. 예전 목록(M14/M16HUB/
#   M16)은 실제 관제와 어긋나서 M14B·M16A·M16B 알람을 못 그렸다.
#   건물 그림은 3장뿐이라 M14B 는 M14 그림, M16A·M16B 는 M16 그림을 같이 쓴다
#   (그림이 늘면 img 만 바꾸면 된다). ALL 은 전체 융합이라 허브 그림.
FABS = [
    {"key": "ALL",    "name": "전체",    "img": "assets/fab_m16hub.png"},
    {"key": "M14",    "name": "M14",     "img": "assets/fab_m14.png"},
    {"key": "M14B",   "name": "M14B",    "img": "assets/fab_m14.png"},
    {"key": "M16A",   "name": "M16A",    "img": "assets/fab_m16.png"},
    {"key": "M16B",   "name": "M16B",    "img": "assets/fab_m16.png"},
    {"key": "M16HUB", "name": "M16 HUB", "img": "assets/fab_m16hub.png"},
]

# lines 의 {n} 자리에 FAB 이름이 들어간다. pace 가 None 이면 제자리.
LEVELS = [
    {"key": "lv1", "name": "경계",   "nag": 8000, "tones": [880],
     "emo": ["think", "surprise"], "inten": 0.70, "pace": None,
     "lines": [
         "{n} FAB에 경계 알람이 떴어요. 한 번 봐주세요.",
         "아직 {n} 경계 상태예요. 지켜보고 있을게요.",
         "{n} 쪽 수치가 슬슬 올라와요… 확인 부탁드려요.",
         "{n} FAB 경계 알람, 아직 해제 안 됐어요.",
     ]},
    {"key": "lv2", "name": "위험",   "nag": 6000, "tones": [880, 660],
     "emo": ["fear", "angry"], "inten": 0.90,
     "pace": {"amp": 0.20, "freq": 0.42},
     "lines": [
         "{n} FAB 위험 알람이에요! 빨리 확인해 주세요!",
         "아직 {n} 위험 상태예요… 반송이 밀리고 있어요!",
         "{n} FAB 알람이 계속 울리고 있어요!",
         "{n} 쪽 좀 봐주세요, 저 혼자서는 못 막아요!",
     ]},
    {"key": "lv3", "name": "초위험", "nag": 4000, "tones": [990, 760, 990],
     "emo": ["fear", "angry"], "inten": 1.00,
     "pace": {"amp": 0.20, "freq": 0.42},   # 위험과 동일. 더 빠르면 무섭다
     "lines": [
         "{n} FAB 초위험이에요!! 지금 당장 조치해 주세요!!",
         "{n} 멈췄어요!! 초위험 단계예요!!",
         "{n} FAB 초위험… 이러다 라인 전체 밀려요!",
         "아직도 {n} 초위험이에요!! 제발요!!",
     ]},
]

# ── 서버측 기본 설정 (data/settings.json 이 있으면 그 값이 우선) ─────────
DEFAULT_SETTINGS = {
    "docBudget": 6000,      # 자료 주입 예산 (글자)
    "ctxLimit": 32768,      # 컨텍스트 한도 (토큰)
    "keepMsgs": 12,         # 프롬프트에 붙일 최근 대화 수
    "temperature": 0.8,
    "alarmHoldMin": 60,     # 정상 복귀 뒤 알람을 내리기까지 관찰하는 시간(분)
    "alarmKeep": 500,       # 알람 기록 보관 건수 (CSV 파일은 계속 쌓인다)
}

# ── 세션 보관 한도 ────────────────────────────────────────────────────────
SESS_MAX = 30           # 최근 30개
SESS_BYTES = 1_200_000  # 총 1.2MB

# ── 자료 보관 한도 ────────────────────────────────────────────────────────
DOCS_BYTES = 300_000    # 총 300KB


def public_config(model="", models=None, upstream=""):
    """브라우저가 /api/config 로 받아가는 것."""
    return {
        "baseUrl": "/v1",
        "model": model,
        "models": models or [],
        "upstream": upstream,
        "schedule": SCHEDULE,
        "backgrounds": BACKGROUNDS,
        "costumes": COSTUMES,
        "badge": BADGE,
        "badgeLogo": BADGE_LOGO,
        "fabs": FABS,
        "levels": LEVELS,
        "sessMax": SESS_MAX,
        "sentinel": {"pollMs": int(SENTINEL.get("poll_ms", 5000))},
    }
