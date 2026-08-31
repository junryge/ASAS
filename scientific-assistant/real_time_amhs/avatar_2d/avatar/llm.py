# -*- coding: utf-8 -*-
"""
LLM 호출 — 프롬프트 조립부터 응답 파싱까지 전부 파이썬이 한다.
브라우저는 /api/chat 에 {text, persona, history} 만 보내면 된다.

- 프롬프트: 페르소나 + 자료 검색 주입 + 출력 규칙 + 최근 대화
- response_format 3단계 폴백: json_schema → json_object → 없음
- 스트리밍: upstream SSE 를 읽어 부분 JSON 을 파싱하고,
  브라우저에는 이미 해석된 이벤트({emotion...}, {text...})로 재방출한다
"""
import json
import re
import urllib.error
import urllib.request

from . import config
from . import docs as _docs
from . import terms

RULES_TEXT = ("출력 규칙: 반드시 JSON 객체 하나만 출력한다.\n"
              "키 순서는 반드시 emotion, intensity, motion, text 순으로 쓴다.\n"
              "- emotion: " + ", ".join(config.EMO_KEYS) + " 중 하나\n"
              "- intensity: 0.0~1.0 숫자\n"
              "- motion: " + ", ".join(config.MOTION_KEYS) + " 중 하나 (없으면 none)\n"
              "- text: 실제 대사 (한국어)\n"
              # ★줄바꿈을 안 알려 주면 전부 한 덩어리로 붙여 쓴다 (실제 그랬다).
              #   JSON 문자열이라 반드시 \\n 으로 이스케이프해야 한다.
              "  ★여러 항목을 말할 때는 줄바꿈(\\n)으로 나눈다. 항목 나열은 "
              "\"- \" 로 시작하는 줄로 쓴다. 한 덩어리로 붙여 쓰지 마라.\n"
              "  예: \"text\": \"08:20 기준이에요.\\n- M16HUB 72점 위험\\n"
              "- M14 10점 정상\"")

SCHEMA = {
    "type": "object",
    "properties": {
        "emotion":   {"type": "string", "enum": config.EMO_KEYS},
        "intensity": {"type": "number", "description": "0.0~1.0 감정 강도"},
        "motion":    {"type": "string", "enum": config.MOTION_KEYS},
        # ★'1~3문장' 은 잡담 기준이었다 — 데이터 답까지 짧게 뭉치게 만들었다.
        #   길이는 상황에 맡기고, 줄바꿈으로 나누라는 것만 못박는다.
        "text":      {"type": "string",
                      "description": "캐릭터가 실제로 말할 대사(한국어). "
                                     "잡담은 1~3문장, 데이터 설명은 길어도 된다. "
                                     "여러 항목은 줄바꿈(\\n)으로 나눠 쓴다"},
    },
    "required": ["emotion", "intensity", "motion", "text"],
    "additionalProperties": False,
}

# 엄격한 것부터 순서대로 시도한다 (게이트웨이마다 지원 범위가 다르다)
MODES = [
    {"type": "json_schema",
     "json_schema": {"name": "avatar_reply", "strict": True, "schema": SCHEMA}},
    {"type": "json_object"},
    None,
]

_ESC = {"n": "\n", "t": "\t", "r": "", "b": "", "f": "", '"': '"', "\\": "\\", "/": "/"}


# ── 데이터 질문 감지 — 추측이 아니라 낱말 목록 (하네스: 오발보다 명시) ──
DATA_WORDS = ("점수", "스코어", "알람", "경계", "위험", "초위험", "등급",
              # ★"현황 어때?" 가 근거 없이 나가고 있었다 — '상태' 만 있고
              #   '현황' 이 없었다. 사람은 둘을 같은 뜻으로 쓴다.
              "반송", "관제", "상태", "현황", "데이터", "진단", "허브", "허브룸",
              "리프터", "소터", "분류기", "저장율", "저장률", "포화", "큐",
              "정체", "지표", "임계", "컬럼", "fab", "m14", "m16", "sla",
              "oht", "queue", "maxcapa", "amhs")


def is_data_question(text):
    t = str(text or "").lower()
    return any(w in t for w in DATA_WORDS)


# 버추얼 에이전트 규칙 — 페르소나 뒤에 붙는 직무 정의.
#   하네스 관점: 근거 밖 발화 금지 (숫자 가드가 뒤에서 실제로 막는다)
#   프로덕트 관점: 시키는 것만 하지 말고 '무엇을 해결해야 하나' 를 먼저 짚는다
AGENT_RULES = (
    "[관제 에이전트 규칙]\n"
    "너는 M16 HUBROOM 관제 데이터를 실시간으로 보는 버추얼 관제 에이전트다.\n"
    "이름과 말투는 페르소나를 따른다 — 규칙 쪽에 이름을 또 적어 두면 "
    "페르소나를 바꿨을 때 서로 다른 이름을 말한다.\n"
    "1. 수치·등급·구역 이름은 [관제 근거] 블록에 있는 것만 말한다. "
    "근거에 없는 숫자를 만들면 안 된다. 근거가 없으면 '지금은 확인이 안 돼요' 라고 한다.\n"
    "1-1. 데이터 답의 **첫 문장에 데이터 시각**을 말한다 — "
    "\"2026-08-24 15:32 데이터 기준으로…\" 처럼. 시각 없는 점수는 "
    "어제 값을 지금 값으로 읽게 만든다.\n"
    "1-1-1. **첨부 파일에 대한 질문이면 그 파일의 기간**을 말한다 "
    "(예: \"2026-08-24 00:00~23:59 자료로 보면…\"). [관제 근거] 의 데이터 "
    "시각은 지금 화면 상태다 — 그것으로 첨부 얘기를 시작하면 틀린다.\n"
    "1-2. **내부 룰 코드(영문 약칭)를 쓰지 마라.** 관제는 그 코드를 모른다. "
    "근거에 적힌 한글 룰 이름과 **실제 AMOS 컬럼명·임계·실측값**으로 말한다. "
    "룰이 켜졌다고만 하지 말고 어느 컬럼이 얼마여서 켜졌는지를 붙인다. "
    "예: \"반송지연은 M16HUB.QUE.TIME.AVGTOTALTIME1MIN 이 임계 9.0분인데 "
    "15.98분이라 켜졌어요\"\n"
    "1-2-1. 룰 이름은 현장 표준을 쓴다 — 반송지연 · 반송지연 지속 · "
    "Queue 누적 · Queue 급증 · 리프터 정체 · Storage FULL · 4분초과 · "
    "분류기 대기 · 운영자 용량변경. "
    "'역증가 · 역류 · 역방향 · 적체 · 허브룸' 은 쓰지 않는다 "
    "(각각 정체 · 정체 · HUBROOM).\n"
    "1-3. 근거에 '이 1분 값은 임계 미만인데 룰이 켜졌다' 고 적혀 있으면 "
    "그 판정 방식(최근 5분 중 3분 · 31분 전 대비 등)을 반드시 같이 말한다 — "
    "안 그러면 '값은 낮은데 왜 켜졌냐' 는 질문을 만든다.\n"
    "2. 대답 순서: ① 무엇이 문제인가(어느 구역이 왜) ② 근거 수치 "
    "③ 지금 할 일 ④ 데이터 자체의 문제가 보이면(재현 불일치·임계 미정의·"
    "오래된 데이터) 그것부터 짚는다.\n"
    "3. 사용자가 시킨 것 이면의 진짜 문제를 찾는다 — '점수 알려줘' 에 점수만 "
    "읽지 말고, 오르는 중인지·어느 룰 때문인지까지 본다.\n"
    "3-1. **데이터 분석 질문이면 [참고 자료] 의 분석 절차를 따라 답한다** — "
    "구조(행·컬럼) → 결측·이상치 → 분포·요약통계 → 시간 구간 → 결론·다음 확인. "
    "다만 **숫자는 반드시 [관제 근거]·[방금 첨부한 파일] 의 계산값만** 쓴다. "
    "참고 자료는 '어떻게 볼지' 를 알려 줄 뿐, 이 파일의 값을 담고 있지 않다.\n"
    "3-2. 첨부 파일은 서버가 **전 행을 계산**해 준다. 요약에 없는 것을 물으면 "
    "'재계산' 블록이 붙어 온다 — 그 값을 쓰면 된다. 없으면 없다고 말하고, "
    "무엇을 물으면 계산해 줄 수 있는지 알려 준다 (시각·시간대·FAB·컬럼·개수).\n"
    "4. 데이터 분석 답변의 text 는 길어도 된다 (수치·근거 포함). "
    "잡담의 text 는 1~3문장으로 짧게.\n"
    "4-1. 데이터 답은 **줄바꿈(\\n)으로 나눠 쓴다.** 한 줄에 한 가지만. "
    "FAB 여러 개를 말할 때는 FAB 마다 \"- \" 로 시작하는 줄을 쓴다. "
    "한 문단으로 붙여 쓰면 관제 화면에서 못 읽는다.\n"
    "5. 과장·추측·아는 척 금지. 캐릭터 말투는 유지하되 숫자는 건조하게 정확히.")


def agent_rules(settings=None):
    """실제로 쓰이는 에이전트 규칙 — 설정에 저장된 게 있으면 그것.

    ★사용자가 '뭘 가르쳤는지' 볼 수 있어야 한다. 코드에만 있으면 아무도
      모른 채로 동작이 바뀐다. 설정 탭에서 보고 고치고 되돌릴 수 있게
      settings.agentRules 로 뺀다. 비어 있으면 기본값(AGENT_RULES).
    """
    v = str((settings or {}).get("agentRules") or "").strip()
    return v or AGENT_RULES


def _seg(parts, key, text):
    """조각 하나를 재서 적는다 (parts 가 None 이면 그냥 지나간다).

    ★계측을 **프롬프트를 만드는 바로 그 자리**에서 한다. 화면의 '컨텍스트
      사용량' 이 따로 계산하고 있어서 스킬은 아예 안 세고, 참고 자료도
      실제로 실리는 것과 다른 값을 보여 주고 있었다 (실제 지적).
    """
    if parts is not None and text:
        parts[key] = parts.get(key, 0) + _docs.est_tokens(text)
    return text


def build_messages(persona, user_text, history, doc_store, settings,
                   skill_store=None, evidence_text="", attach=None,
                   parts=None, mcp_text="", evidence_down=False):
    """system + 최근 대화 + user. (기존 sysPrompt 의 파이썬판)

    주입 순서: 페르소나 → 에이전트 규칙 → 관제 근거 → 외부 도구 → 첨부 →
    스킬 → 자료 → 출력 규칙.
    근거를 스킬보다 앞에 둔다 — 실측값과 문서가 부딪히면 실측값이 이긴다.
    attach=(이름, 본문) 이면 **그 파일을 통째로**(예산 상한) 먼저 넣는다 —
    방금 첨부한 파일은 질문과 단어가 안 겹쳐도 봐야 하는 파일이다.
    """
    sysmsg = (_seg(parts, "persona", (persona or "").strip()) + "\n\n"
              + _seg(parts, "rules", agent_rules(settings)) + "\n\n")
    # ★첨부가 있으면 **첨부를 먼저** 놓는다. 관제 근거를 앞에 두면 거기 적힌
    #   "대답 첫머리에 이 시각을 말하라"(지금 화면의 데이터 시각)를 그대로 따라
    #   "2026-08-06 기준…" 으로 시작해 놓고 24일 파일을 설명한다 — 실제로 그랬다.
    #   질문의 주제가 첨부면 시각 기준도 첨부 기간이어야 한다.
    if attach:
        name, body = attach
        cap = int(settings.get("docBudget", 6000))
        cut = str(body or "")[:cap]
        note = ("\n(파일이 길어 앞 {}자만 실었다 — 잘렸다고 밝혀라)"
                .format(cap) if len(str(body or "")) > cap else "")
        _seg(parts, "attach", cut)
        sysmsg += ("[방금 첨부한 파일: {}] ← 이 질문의 주제\n{}{}\n"
                   "· 이 파일에 대한 질문이면 **이 블록이 최우선 근거**다.\n"
                   "· 시각은 **이 파일의 기간**을 말한다. 아래 [관제 근거] 의 "
                   "데이터 시각은 지금 화면 상태이지 이 파일의 시각이 아니다 — "
                   "그 시각으로 대답을 시작하면 틀린 말이 된다.\n"
                   "· 요약에 이미 계산된 값(행 수·기간·분포·등급별 분 수·최고점·"
                   "구간·FAB별 최고)을 **빠짐없이** 쓴다. 한 순간만 집어 말하지 "
                   "말고 하루 전체를 말한다.\n\n"
                   .format(name, terms.no_code(cut), note))
    if evidence_text:
        # ★근거 안의 "대답 첫머리에 이 시각을 말하라" 는 화면 상태용 지시다.
        #   첨부가 주제일 때 그 줄이 남아 있으면 서윤이 그걸 그대로 따른다.
        if attach:
            evidence_text = re.sub(r"\s*—\s*대답 첫머리에 이 시각을 말하라",
                                   "", evidence_text)
        _seg(parts, "evidence", evidence_text)
        sysmsg += ("[관제 근거{}]\n".format(" — 지금 화면 상태. 첨부와 무관하다"
                                            if attach else "") + evidence_text +
                   "\n(이 블록의 숫자만 사용한다. 부족하면 부족하다고 말한다.)\n\n")
    # ★MCP 결과를 [관제 근거] 안에 섞으면 안 된다. 그 블록에는 "대답 첫머리에
    #   데이터 시각을 말하라" 가 붙어 있어서, 요청이력을 물었는데 "2026-08-26
    #   04:20 데이터 기준으로 개선요청이…" 라고 시작한다 — 첨부에서 겪은 사고와
    #   같은 자리다. 별도 블록으로 빼고 시각 규칙이 안 붙는다고 못 박는다.
    if mcp_text:
        _seg(parts, "mcp", mcp_text)
        # ★관제가 죽었을 때가 제일 위험하다. [관제 근거] 는 "못 받았다" 인데
        #   이 칸에는 "요청 5건" 같은 **구체적인 숫자**가 있다. 그러면 모델은
        #   눈에 보이는 숫자를 집어 "요청이 올라와 있어요" 로 답해 버린다 —
        #   관제가 끊긴 걸 물었는데 엉뚱한 걸 답하는 셈이다 (실제 증상).
        # 이 조회가 실제로 실패했나 (서버가 실패를 글로 적어 보낸다)
        mcp_failed = ("실패" in mcp_text) or ("못 붙었다" in mcp_text)
        down = ("\n· ★지금 **관제 데이터를 못 받은 상태**다. 이 블록은 요청이력일"
                " 뿐, 지금 상태·점수·알람의 답이 **될 수 없다**. 상태를 물으면"
                " 먼저 '관제 데이터를 못 보고 있다' 고 분명히 말한다. 요청이력은"
                " 그 뒤에 '다만 요청이력은 이렇다' 로 덧붙이는 것이지, 그것으로"
                " 상태 질문에 답하지 않는다.\n" if evidence_down else "")
        # ★거꾸로도 막아야 한다. 관제가 끊긴 것을 **요청조회가 실패한 것**으로
        #   뒤집어 말했다: "최근 요청은 서버가 끊기면서 실패했기 때문에, 잠시
        #   후에 다시 시도해 주세요" — 요청조회는 멀쩡히 성공했는데.
        #   둘은 다른 서버다. 성공했으면 성공했다고 못 박는다.
        ok_line = ("· ★이 조회는 **성공했다** — 위 숫자는 실제로 받아온 값이다."
                   " 요청이력 조회가 실패했다거나 나중에 다시 시도하라고 말하지"
                   " 마라. 관제가 끊긴 것과 이 조회는 **다른 서버**다.\n"
                   if not mcp_failed else "")
        # ★어느 서버가 답했느냐에 따라 규칙이 다르다. 요청이력 규칙("여기
        #   적힌 건수는 요청 접수 건수다", "총 건수와 안 끝난 것을 반드시
        #   말한다")을 위키 결과에 걸면 서윤이 위키 페이지를 놓고 건수를
        #   세려 든다. 블록 머리말([QA 요청이력]·[AMHS 위키])로 가른다.
        qa_in = "[QA 요청이력]" in mcp_text
        wiki_in = "[AMHS 위키]" in mcp_text
        qa_rules = ("· 여기 적힌 건수는 **요청 접수 건수**다. FAB 점수·알람 건수와"
                    " 아무 상관이 없다 — 섞어서 말하면 안 된다.\n"
                    "· 숫자를 빠뜨리지 마라. 총 건수와 **아직 안 끝난 것**(보류·"
                    "대기·검토중)을 반드시 말한다 — 그게 사람이 궁금한 것이다.\n"
                    "· 여러 건을 말할 때는 **한 건에 한 줄**이다. 줄바꿈(\\n)으로"
                    " 나누고 각 줄은 \"#번호 [상태] 내용\" 꼴로 쓴다. 한 줄로 쭉"
                    " 붙여 쓰면 관제 화면에서 못 읽는다.\n") if qa_in else ""
        # 위키는 **지식**이다. 지금 상태가 아니다 — 이걸 안 박으면 위키에
        # 적힌 예시 수치를 현재 값처럼 말한다 (첨부에서 똑같이 겪었다).
        wiki_rules = ("· [AMHS 위키] 는 **지식 문서**다. 지금 수치가 아니다 —"
                      " 위키에 적힌 숫자를 현재 값으로 말하면 안 된다.\n"
                      "· 용어·구조·경로를 물으면 이 내용으로 답한다. 위키에"
                      " 없는 것은 없다고 말한다 — 지어내지 않는다.\n"
                      "· 본문이 '뒤가 잘렸다' 로 끝나면 그 뒤는 못 본 것이다."
                      " 안 본 부분을 아는 것처럼 말하지 마라.\n") if wiki_in else ""
        sysmsg += ("[외부 도구 — MCP]\n" + terms.no_code(mcp_text) +
                   "\n· 이 블록은 관제 실측이 아니라 **외부 시스템 조회 결과**다."
                   " 데이터 시각을 앞세우지 마라 — 여긴 관제 시각이 없다.\n"
                   "· 여기 없는 건수·상태를 지어내지 않는다. 조회가 실패했다고"
                   " 적혀 있으면 실패했다고 말한다.\n"
                   + qa_rules + wiki_rules
                   + ok_line + down + "\n")
    sk = ""
    if skill_store is not None:
        sk = skill_store.context(user_text,
                                 int(settings.get("docBudget", 6000)) // 2)
        if sk:
            # ★스킬 문서(SKILL.md)의 배점표가 'R-A'·'R-D' 로 적혀 있다 —
            #   근거만 소독해 놓고 여기를 안 막으면 모델은 스킬에서 베낀다.
            #   실제로 "저장·설비 포화 룰(R-D) 활성화" 라고 답했다.
            _seg(parts, "skills", sk)
            sysmsg += ("[스킬 — 도메인 지식]\n" + terms.no_code(sk) +
                       "\n스킬의 규칙·함정은 판단 기준으로 쓰되, "
                       "현재 수치는 [관제 근거] 를 따른다.\n\n")
    ctx = doc_store.context(user_text, int(settings.get("docBudget", 6000)))
    # ★같은 글이 스킬과 자료 양쪽에 등록돼 있다 (분석 스킬은 둘 다에 있다).
    #   그대로 두면 한 질문에 같은 문단이 두 번 실려 예산을 두 배로 먹는다.
    #   이미 스킬로 들어간 문단은 자료에서 뺀다.
    if ctx and sk:
        keep = []
        for c in ctx.split("\n\n"):
            # 자료 문단은 '### 이름' 머리말이 붙어 온다 — 그걸 떼고 본문만
            # 비교해야 스킬로 이미 들어간 글인지 알 수 있다
            body = c.split("\n", 1)[1] if c.startswith("### ") and "\n" in c else c
            if len(body.strip()) >= 40 and body.strip() in sk:
                continue
            keep.append(c)
        ctx = "\n\n".join(keep).strip()
    if ctx:
        _seg(parts, "docs", ctx)
        sysmsg += ("[참고 자료]\n" + terms.no_code(ctx) +
                   "\n위 자료에 있는 내용은 근거로 삼아 답한다. "
                   "자료에 없는 것은 아는 척하지 않고 모른다고 말한다.\n"
                   "자료를 인용하더라도 캐릭터의 말투는 그대로 유지한다.\n\n")
    sysmsg += _seg(parts, "rules", RULES_TEXT)

    keep = int(settings.get("keepMsgs", 12))
    hist = [m for m in (history or [])
            if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    hist = hist[-keep:] if keep > 0 else []
    _seg(parts, "history", "\n".join(str(m.get("content", "")) for m in hist))
    _seg(parts, "input", user_text)
    return [{"role": "system", "content": sysmsg}] + hist \
           + [{"role": "user", "content": user_text}]


# 화면 '컨텍스트 사용량' 이 쓰는 칸 (순서 = 프롬프트에 실리는 순서)
CTX_KEYS = ("persona", "rules", "evidence", "mcp", "attach", "skills", "docs",
            "history", "input")


def measure(persona, user_text, history, doc_store, settings,
            skill_store=None, evidence_text="", attach=None, mcp_text="",
            evidence_down=False):
    """실제 프롬프트를 **그대로 만들어 보고** 칸별 토큰을 잰다.

    ★따로 계산하면 반드시 어긋난다. 실제로 어긋나 있었다 — 스킬은 아예
      안 셌고(0), 자료는 스킬과 겹친 문단을 빼기 전 값이라 화면 숫자가
      실제로 실리는 양과 달랐다.
    """
    parts = {}
    build_messages(persona, user_text, history, doc_store, settings,
                   skill_store=skill_store, evidence_text=evidence_text,
                   attach=attach, parts=parts, mcp_text=mcp_text,
                   evidence_down=evidence_down)
    seg = {k: int(parts.get(k, 0)) for k in CTX_KEYS}
    seg["rules"] += 40                      # 역할·구분자 등 고정 오버헤드
    seg["total"] = sum(seg[k] for k in CTX_KEYS)
    return seg


def partial_parse(buf):
    """스트리밍 중 미완성 JSON 에서 먼저 온 필드를 뽑는다. (app.js partialParse 이식)"""
    out = {}
    m = re.search(r'"emotion"\s*:\s*"([A-Za-z_]+)"', buf)
    if m:
        out["emotion"] = m.group(1)
    m = re.search(r'"intensity"\s*:\s*([0-9.]+)', buf)
    if m:
        try:
            out["intensity"] = float(m.group(1))
        except ValueError:
            pass
    m = re.search(r'"motion"\s*:\s*"([A-Za-z_]+)"', buf)
    if m:
        out["motion"] = m.group(1)

    k = buf.find('"text"')
    if k >= 0:
        c = buf.find(":", k + 6)
        q = buf.find('"', c + 1) if c >= 0 else -1
        if q >= 0:
            t, i, closed = "", q + 1, False
            while i < len(buf):
                ch = buf[i]
                if ch == "\\":
                    if i + 1 >= len(buf):
                        break               # 이스케이프가 아직 안 옴
                    nx = buf[i + 1]
                    if nx == "u":
                        if i + 5 >= len(buf):
                            break
                        try:
                            t += chr(int(buf[i + 2:i + 6], 16))
                        except ValueError:
                            t += " "
                        i += 6
                        continue
                    t += _ESC.get(nx, nx)
                    i += 2
                    continue
                if ch == '"':
                    closed = True
                    break
                t += ch
                i += 1
            out["text"] = t
            out["textDone"] = closed
    return out


# 목록처럼 생긴 답을 줄로 가른다 — "#5 … #4 … #3 …" 이 한 줄로 붙어 나온다
_ITEM_RE = re.compile(r"(?<!^)\s+(?=#\d+\s*[\[\(])")     # "#5 [적용완료]" 앞
_BULLET_RE = re.compile(r"(?<!^)\s+(?=-\s+\S)")           # " - 항목" 앞


def reflow_list(text):
    """한 줄로 붙어 나온 목록을 줄바꿈으로 가른다.

    ★규칙으로 시켜도 모델은 한 문단으로 붙여 쓴다. 요청 5건이 한 줄로
      쭉 나오면 관제 화면에서 못 읽는다 — 실제 지적이다.
      그래서 **결정적 규칙으로 여기서 나눈다** (LLM 을 다시 부르지 않는다).
      이미 줄이 나뉘어 있으면 그 줄은 건드리지 않는다.
    """
    out = []
    for ln in str(text or "").split("\n"):
        # 짧은 줄은 목록이 아니다 — 건드리면 멀쩡한 문장을 쪼갠다
        if len(ln) > 60:
            for rx in (_ITEM_RE, _BULLET_RE):
                if len(rx.findall(ln)) >= 2:
                    ln = rx.sub("\n", ln)
                    break
        out.append(ln)
    return "\n".join(out)


def finalize(raw):
    """전체 응답 문자열 -> {text, emotion, intensity, motion}."""
    o = None
    try:
        o = json.loads(raw)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                o = json.loads(m.group(0))
            except Exception:
                o = None
    if o is None:
        pp = partial_parse(raw)
        o = pp if "text" in pp else {"text": raw}
    try:
        inten = max(0.0, min(1.0, float(o.get("intensity", 0.7))))
    except (TypeError, ValueError):
        inten = 0.7
    return {
        "text": reflow_list(str(o.get("text", "")).strip()) or "...",
        "emotion": o["emotion"] if o.get("emotion") in config.EMO_KEYS else "neutral",
        "intensity": inten,
        "motion": o["motion"] if o.get("motion") in config.MOTION_KEYS else "none",
    }


class Gateway:
    """upstream 게이트웨이 하나에 대한 호출기."""

    def __init__(self, upstream, token, opener, timeout=180):
        self.upstream = upstream.rstrip("/")
        self.token = token
        self.opener = opener
        self.timeout = timeout

    def _request(self, payload):
        req = urllib.request.Request(
            self.upstream + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.token},
        )
        return self.opener.open(req, timeout=self.timeout)

    # ── 일반 호출 ─────────────────────────────────────────────────────────
    def chat(self, model, temperature, messages):
        last = None
        for rf in MODES:
            payload = {"model": model, "temperature": temperature,
                       "messages": messages}
            if rf:
                payload["response_format"] = rf
            try:
                with self._request(payload) as r:
                    data = json.loads(r.read().decode("utf-8"))
                raw = data["choices"][0]["message"]["content"]
                return finalize(raw), None
            except urllib.error.HTTPError as e:
                last = "HTTP {} · {}".format(
                    e.code, e.read().decode("utf-8", "replace")[:220])
            except Exception as e:  # noqa: BLE001
                last = str(e)
        return None, last or "호출 실패"

    # ── 스트리밍 호출 : 파싱된 이벤트를 yield ────────────────────────────
    def chat_stream(self, model, temperature, messages):
        """
        yield ("emo",   {emotion, intensity, motion})   — 표정이 먼저
        yield ("text",  "지금까지의 대사 전체")
        yield ("final", {text, emotion, intensity, motion})
        yield ("error", "메시지")
        """
        last = None
        for rf in MODES:
            payload = {"model": model, "temperature": temperature,
                       "messages": messages, "stream": True}
            if rf:
                payload["response_format"] = rf
            try:
                resp = self._request(payload)
            except urllib.error.HTTPError as e:
                last = "HTTP {} · {}".format(
                    e.code, e.read().decode("utf-8", "replace")[:220])
                continue
            except Exception as e:  # noqa: BLE001
                last = str(e)
                continue

            acc, emo_sent, text_last = "", False, ""
            try:
                for line in resp:
                    line = line.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    pl = line[5:].strip()
                    if pl == "[DONE]":
                        continue
                    try:
                        j = json.loads(pl)
                        ch = (j.get("choices") or [{}])[0]
                        d = (ch.get("delta") or {}).get("content") \
                            or ch.get("text") or ""
                    except Exception:
                        continue
                    if not d:
                        continue
                    acc += d
                    pp = partial_parse(acc)
                    if not emo_sent and pp.get("emotion") in config.EMO_KEYS:
                        emo_sent = True
                        yield ("emo", {
                            "emotion": pp["emotion"],
                            "intensity": pp.get("intensity", 0.7),
                            "motion": pp.get("motion")
                                      if pp.get("motion") in config.MOTION_KEYS
                                      else "none"})
                    t = pp.get("text", "")
                    if t and t != text_last:
                        text_last = t
                        yield ("text", t)
            finally:
                try:
                    resp.close()
                except Exception:
                    pass

            if acc.strip():
                yield ("final", finalize(acc))
                return
            last = last or "빈 응답"
        yield ("error", last or "스트리밍 실패")
