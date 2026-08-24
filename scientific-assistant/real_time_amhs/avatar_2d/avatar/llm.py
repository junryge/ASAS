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
              "반송", "관제", "상태", "데이터", "진단", "허브", "허브룸",
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
    "너는 M16 허브룸 관제 데이터를 실시간으로 보는 버추얼 에이전트다.\n"
    "1. 수치·등급·구역 이름은 [관제 근거] 블록에 있는 것만 말한다. "
    "근거에 없는 숫자를 만들면 안 된다. 근거가 없으면 '지금은 확인이 안 돼요' 라고 한다.\n"
    "1-1. 데이터 답의 **첫 문장에 데이터 시각**을 말한다 — "
    "\"2026-08-24 15:32 데이터 기준으로…\" 처럼. 시각 없는 점수는 "
    "어제 값을 지금 값으로 읽게 만든다.\n"
    "2. 대답 순서: ① 무엇이 문제인가(어느 구역이 왜) ② 근거 수치 "
    "③ 지금 할 일 ④ 데이터 자체의 문제가 보이면(재현 불일치·임계 미정의·"
    "오래된 데이터) 그것부터 짚는다.\n"
    "3. 사용자가 시킨 것 이면의 진짜 문제를 찾는다 — '점수 알려줘' 에 점수만 "
    "읽지 말고, 오르는 중인지·어느 룰 때문인지까지 본다.\n"
    "4. 데이터 분석 답변의 text 는 길어도 된다 (수치·근거 포함). "
    "잡담의 text 는 1~3문장으로 짧게.\n"
    "4-1. 데이터 답은 **줄바꿈(\\n)으로 나눠 쓴다.** 한 줄에 한 가지만. "
    "FAB 여러 개를 말할 때는 FAB 마다 \"- \" 로 시작하는 줄을 쓴다. "
    "한 문단으로 붙여 쓰면 관제 화면에서 못 읽는다.\n"
    "5. 과장·추측·아는 척 금지. 캐릭터 말투는 유지하되 숫자는 건조하게 정확히.")


def build_messages(persona, user_text, history, doc_store, settings,
                   skill_store=None, evidence_text="", attach=None):
    """system + 최근 대화 + user. (기존 sysPrompt 의 파이썬판)

    주입 순서: 페르소나 → 에이전트 규칙 → 관제 근거 → 첨부 → 스킬 → 자료 → 출력 규칙.
    근거를 스킬보다 앞에 둔다 — 실측값과 문서가 부딪히면 실측값이 이긴다.
    attach=(이름, 본문) 이면 **그 파일을 통째로**(예산 상한) 먼저 넣는다 —
    방금 첨부한 파일은 질문과 단어가 안 겹쳐도 봐야 하는 파일이다.
    """
    sysmsg = (persona or "").strip() + "\n\n" + AGENT_RULES + "\n\n"
    if evidence_text:
        sysmsg += ("[관제 근거]\n" + evidence_text +
                   "\n(이 블록의 숫자만 사용한다. 부족하면 부족하다고 말한다.)\n\n")
    if attach:
        name, body = attach
        cap = int(settings.get("docBudget", 6000))
        cut = str(body or "")[:cap]
        note = ("\n(파일이 길어 앞 {}자만 실었다 — 잘렸다고 밝혀라)"
                .format(cap) if len(str(body or "")) > cap else "")
        sysmsg += ("[방금 첨부한 파일: {}]\n{}{}\n"
                   "질문이 이 파일에 대한 것이면 이 내용을 최우선 근거로 쓴다.\n\n"
                   .format(name, cut, note))
    if skill_store is not None:
        sk = skill_store.context(user_text,
                                 int(settings.get("docBudget", 6000)) // 2)
        if sk:
            sysmsg += ("[스킬 — 도메인 지식]\n" + sk +
                       "\n스킬의 규칙·함정은 판단 기준으로 쓰되, "
                       "현재 수치는 [관제 근거] 를 따른다.\n\n")
    ctx = doc_store.context(user_text, int(settings.get("docBudget", 6000)))
    if ctx:
        sysmsg += ("[참고 자료]\n" + ctx +
                   "\n위 자료에 있는 내용은 근거로 삼아 답한다. "
                   "자료에 없는 것은 아는 척하지 않고 모른다고 말한다.\n"
                   "자료를 인용하더라도 캐릭터의 말투는 그대로 유지한다.\n\n")
    sysmsg += RULES_TEXT

    keep = int(settings.get("keepMsgs", 12))
    hist = [m for m in (history or [])
            if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    hist = hist[-keep:] if keep > 0 else []
    return [{"role": "system", "content": sysmsg}] + hist \
           + [{"role": "user", "content": user_text}]


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
        "text": str(o.get("text", "")).strip() or "...",
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
