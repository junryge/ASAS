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

    # ── 나중에 추가한 옷 ────────────────────────────────────────────
    # ★새 옷은 **뒤에만 붙인다**. BACKGROUNDS 가 의상을 인덱스로 가리키므로
    #   (공장=2 · 회의실=0 · 정문=1 · 테라스=3 · 집=4) 중간에 끼워 넣으면
    #   배경이 엉뚱한 옷을 입힌다.
    # ★badge: 그 옷을 고르면 사원증을 켤지/끌지. 없으면 지금 상태를 유지한다
    #   (배경의 badge 와 같은 규칙). 배경으로 옷이 바뀐 경우엔 배경 쪽 값이
    #   이긴다 — 장면이 정한 것이 옷보다 우선이다.
    #   평상복만 사원증을 뗀다. 나머지 넷은 근무 중에 입는 옷이다.
    # ★손 위치(armA/armB)는 patch 를 안 걸었다. 그림을 받아 보고 재야 하는
    #   값이라 눈대중으로 적으면 기본값보다 나빠진다. 화면 오른쪽 조절
    #   손잡이로 맞추면 의상별로 저장된다(설정에 cfgs 로 남는다).
    {"name": "평상복",   "src": "assets/casual.png",     "real": False, "badge": False},
    {"name": "셔츠",     "src": "assets/shirt.png",      "real": False, "badge": True},
    {"name": "자켓",     "src": "assets/jacket.png",     "real": False, "badge": True},
    {"name": "테크자켓", "src": "assets/tech.png",       "real": False, "badge": True},
    {"name": "민소매",   "src": "assets/sleeveless.png", "real": False, "badge": True},
]

# ── 사원증 ────────────────────────────────────────────────────────────────
BADGE = {"name": "미라", "en": "MIRA", "dept": "물류기술팀 · AMHS", "id": "SKH-2026-0417"}
BADGE_LOGO = "assets/logo.png"

# ── 관제 서버 (real_time_amhs) ────────────────────────────────────────────
# 버추얼 에이전트의 데이터 소스. run.py --sentinel 로 덮을 수 있다.
#   url        관제 서버 주소 (기본: 같은 PC 의 8989)
#   poll_ms    브라우저 알람 폴링 주기 (서버 캐시 5초라 더 줄여도 소용없다)
#   watch_sec  **서버가 스스로** 보는 주기. 브라우저가 없어도 이만큼마다
#              본다 — 창을 닫아도 알람 이력이 쌓인다. 0 이면 상시 감시 끔.
SENTINEL = {
    "url": "http://127.0.0.1:8989",
    "poll_ms": 5000,
    "watch_sec": 10,
}

# ── MCP 서버 (외부 도구) ──────────────────────────────────────────────────
# 서윤이 관제 밖의 자료를 볼 때 쓴다. 폐쇄망이라 공식 SDK 는 안 쓰고
# stdio JSON-RPC 로 직접 붙는다 (avatar/mcp_client.py).
#
#   key       내부 이름
#   name      근거 블록에 찍힐 이름 (사람이 읽는다)
#   enabled   False 면 아예 안 띄운다
#   when      질문에 이 말이 있어야 띄운다. 없으면 **평소엔 비용 0**
#   command/args/cwd/env   띄우는 방법
#   calls     부를 도구들. pick 은 질문에서 인자를 뽑는 규칙
#
# ★읽기 전용만 연다. 등록·수정·삭제는 일부러 안 준다 — 서윤이 사람 대신
#   요청을 지우거나 상태를 바꾸면 이력 관리의 의미가 없어진다.
MCP_SERVERS = [
    {
        "key": "qa", "name": "QA 요청이력", "enabled": True,
        "when": ["요청", "개선", "이슈", "민원", "접수", "요청이력",
                 "개선요청", "요청관리", "응답", "반려", "보류", "적용완료",
                 "제안", "문의", "검토중", "미결", "이력"],
        # ★낱말이 하나도 없어도 **컬럼·룰 이름**이 나오면 본다.
        #   "AVGTOTALTIME1MIN 왜 썼어?" 의 답이 보류 건에 그대로 있는데
        #   '요청' 이라는 말이 없다고 안 걸려서 못 찾아 줬다.
        #   ★맨 FAB 이름(M16HUB·M14·ALL)은 코드로 안 본다 — 그러면 "M16HUB
        #     지금 몇 점이야?" 같은 관제 질문마다 요청이력을 뒤진다.
        #     그래서 '밑줄·점이 있거나 아주 긴 것' 만 코드로 친다.
        #   AVGTOTALTIME1MIN · M16_PKT · FABSTORAGERATIO ·
        #   M16HUB.STRATE.ALL.FABSTORAGERATIO · R-A · FAB별_위험도_스코어
        "when_re": (r"\b(?:[A-Z][A-Z0-9]*[_.][A-Z0-9_.]*[A-Z0-9]"
                    r"|[A-Z][A-Z0-9]{9,})\b"
                    r"|R-[A-Z](?![A-Z])"
                    r"|[가-힣A-Z0-9]+_[가-힣A-Z0-9_]+"),
        "command": None,          # None = 지금 파이썬 (sys.executable)
        "args": ["qa/mcp_server.py"],
        "cwd": None,              # None = real_time_amhs 폴더 (server.py 가 채운다)
        "env": {"QA_BASE": "http://127.0.0.1:10500"},
        "timeout": 20,
        "calls": [
            {"tool": "qa_meta", "label": "현황"},
            # ★목록은 **항상** 준다. 예전엔 FAB 이름이 있을 때만 줬는데,
            #   등록된 요청의 대상이 전부 'ALL' 이라 한 번도 안 나왔다 —
            #   "총 5건" 만 말하고 그 5건이 뭔지는 못 말했다.
            #   질문에 단서가 있으면 그걸로 좁히고, 없으면 최근 것부터 준다.
            {"tool": "qa_items", "label": "관련 요청", "pick_opt": {
                "status": {"kind": "oneof",
                           "values": ["대기", "검토중", "적용완료",
                                      "보류", "반려"]},
                "target": {"kind": "oneof",
                           "values": ["M16HUB", "M16A", "M16B", "M14B",
                                      "M14", "ALL"]},
                # 검색어 — 컬럼·룰 이름이 먼저, 없으면 사람 이름
                "q": {"kind": "any", "of": [
                    # AVGTOTALTIME1MIN · M16_PKT · M16HUB.STRATE.…
                    {"kind": "regex",
                     "re": r"\b([A-Z][A-Z0-9]*[_.][A-Z0-9_.]*[A-Z0-9])\b"},
                    {"kind": "regex", "re": r"\b([A-Z][A-Z0-9]{9,})\b"},
                    # R-A 룰 / R-D 룰 — 뒤에 한글이 붙으면 \b 가 안 선다
                    {"kind": "regex", "re": r"(R-[A-Z])(?![A-Z])"},
                    # FAB별_위험도_스코어 처럼 한글에 밑줄이 섞인 이름
                    {"kind": "regex", "re": r"([가-힣A-Z0-9]+_[가-힣A-Z0-9_]+)"},
                    # 김윤환TL님 · 이준력님 — '님' 이 붙은 것만 (오검출 방지)
                    {"kind": "regex", "re": r"([가-힣]{2,4}(?:TL)?)님"},
                ]},
            }},
            {"tool": "qa_item", "label": "지목한 건",
             "pick": {"seq": {"kind": "regex", "re": r"(?:No\.?|#)\s*(\d+)",
                              "int": True}}},
        ],
    },
]

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
