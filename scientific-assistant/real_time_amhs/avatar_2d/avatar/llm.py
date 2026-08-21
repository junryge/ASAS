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
              "- text: 실제 대사 (한국어)")

SCHEMA = {
    "type": "object",
    "properties": {
        "emotion":   {"type": "string", "enum": config.EMO_KEYS},
        "intensity": {"type": "number", "description": "0.0~1.0 감정 강도"},
        "motion":    {"type": "string", "enum": config.MOTION_KEYS},
        "text":      {"type": "string",
                      "description": "캐릭터가 실제로 말할 대사(한국어, 1~3문장)"},
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


def build_messages(persona, user_text, history, doc_store, settings):
    """system + 최근 대화 + user. (기존 sysPrompt 의 파이썬판)"""
    ctx = doc_store.context(user_text, int(settings.get("docBudget", 6000)))
    sysmsg = (persona or "").strip() + "\n\n"
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
