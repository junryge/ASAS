# -*- coding: utf-8 -*-
"""
commands.py — 채팅창 슬래시 명령. LLM 을 거치지 않는 결정적 경로.

왜 명령인가 (하네스 관점)
    "스킬 만들어줘" 같은 자연어 의도 추측은 반드시 오발한다 — 잡담에서
    스킬이 생기거나, 만들라는데 잡담으로 받는다. 그래서 부작용이 있는
    동작(생성·삭제)은 전부 명시적 명령으로만 연다. 대화는 대화, 명령은 명령.

  /상태                    지금 관제 숫자 그대로 (LLM 없음)
  /진단                    데이터 문제 찾기 (LLM 없음)
  /스킬 목록
  /스킬 보기 <이름>        SKILL.md 전문 — 자르지 않는다
  /스킬 만들기 <이름> [주제]  최근 대화+근거로 LLM 이 초안 → 검증 → 저장
  /스킬 삭제 <이름>
  /도움말
"""
import re

from . import sentinel, skills

HELP = ("명령어예요:\n"
        "/상태 — 지금 관제 점수·등급 (실측값 그대로, 데이터 시각 포함)\n"
        "/상태 어제 08:20 — 과거 시각 조회 (2026-08-23 14시 처럼도 됨)\n"
        "/진단 — 데이터 문제 찾기 (재현 불일치·임계 미정의·오래된 데이터…)\n"
        "/알람기록 — 언제 어떤 알람이 울렸는지 (서버가 기억)\n"
        "/스킬 목록 · /스킬 보기 <이름> · /스킬 만들기 <이름> [주제] · /스킬 삭제 <이름>\n"
        "그냥 질문하셔도 돼요 — 데이터 얘기면 실측 근거를 보고 답해요. "
        "📎 로 파일을 붙이면 그 파일을 우선 근거로 봐요.")


def _reply(text, emotion="neutral", intensity=0.6, motion="none"):
    return {"text": text, "emotion": emotion,
            "intensity": intensity, "motion": motion}


def is_command(text):
    return str(text or "").strip().startswith("/")


def handle(text, store, gateway=None, model="", history=None, temperature=0.3):
    """명령 처리. 명령이 아니면 None (일반 대화로 진행)."""
    t = str(text or "").strip()
    if not t.startswith("/"):
        return None

    if t in ("/도움말", "/help", "/?"):
        return _reply(HELP, "smile", 0.6, "nod")

    m = re.match(r"^/(?:상태|status)(?:\s+(.+))?$", t)
    if m:
        # /상태 어제 08:20 · /상태 2026-08-23 · /상태 8월 23일 14시 — 과거 조회
        if m.group(1):
            when = sentinel.parse_when(m.group(1))
            if when is None:
                return _reply("시각을 못 읽었어요. 예: /상태 어제 08:20 · "
                              "/상태 2026-08-23 14시", "shy", 0.5, "shake")
            return _reply(sentinel.plain_status_at(*when), "think", 0.6, "none")
        msg = sentinel.plain_status()
        w = sentinel.watch()
        if w["ok"] and w["alarms"]:
            lv = w["alarms"][0]["level"]
            emo = "fear" if lv in ("위험", "초위험") else "surprise"
            return _reply(msg, emo, 0.9 if lv != "경계" else 0.7, "shiver")
        return _reply(msg, "smile" if w["ok"] else "think", 0.6, "nod")

    if t in ("/알람기록", "/알람", "/alarms"):
        msg = sentinel.history_text(20)
        head = ("최근 알람 기록이에요 (관찰 유지 {}분 규칙):\n"
                .format(sentinel.HOLD_MIN))
        return _reply(head + msg, "think", 0.6, "none")

    if t in ("/진단", "/diagnose"):
        msg = sentinel.diagnose_text()
        has = "짚이는 문제" in msg
        return _reply(msg, "think" if has else "smile", 0.7,
                      "tap" if has else "nod")

    m = re.match(r"^/스킬(?:\s+(.*))?$", t)
    if m:
        return _skill(m.group(1) or "", store, gateway, model,
                      history, temperature)

    return _reply("모르는 명령이에요. " + HELP, "shy", 0.5, "shake")


# ────────────────────────────── /스킬 ──────────────────────────────
def _skill(rest, store, gateway, model, history, temperature):
    rest = rest.strip()
    if rest in ("", "목록", "list"):
        items = store.list()
        if not items:
            return _reply("저장된 스킬이 없어요. `/스킬 만들기 <이름>` 으로 "
                          "지금 대화에서 하나 만들 수 있어요.", "shy", 0.5)
        L = ["스킬 {}개:".format(len(items))]
        for s in items:
            L.append("· {} — {} ({}줄)".format(
                s["name"], s["description"] or "설명 없음", s["lines"]))
        L.append("전문은 `/스킬 보기 <이름>`, 파일은 /api/skills/md?name=<이름>")
        return _reply("\n".join(L), "smile", 0.6, "nod")

    m = re.match(r"^(보기|show)\s+(\S+)$", rest)
    if m:
        md = store.read(m.group(2))
        if md is None:
            return _reply("'{}' 스킬이 없어요. /스킬 목록 으로 확인해 보세요."
                          .format(m.group(2)), "shy", 0.5, "shake")
        # ★자르지 않는다 — '완전하게 내준다' 가 요구사항이다
        return _reply(md, "smile", 0.6, "none")

    m = re.match(r"^(삭제|delete)\s+(\S+)$", rest)
    if m:
        ok = store.delete(m.group(2))
        return _reply("'{}' 스킬을 지웠어요.".format(m.group(2)) if ok
                      else "'{}' 스킬이 없어요.".format(m.group(2)),
                      "neutral" if ok else "shy", 0.5)

    m = re.match(r"^(만들기|만들어|create)\s+(\S+)(?:\s+(.+))?$", rest)
    if m:
        return _create(m.group(2), m.group(3) or "", store, gateway,
                       model, history, temperature)

    return _reply("스킬 명령은 목록 / 보기 <이름> / 만들기 <이름> [주제] / "
                  "삭제 <이름> 이에요.", "shy", 0.5)


def _create(name, topic, store, gateway, model, history, temperature):
    if not skills.NAME_RE.match(name) or len(name) > 64:
        return _reply("스킬 이름은 소문자+숫자+하이픈만 돼요 (예: oht-check). "
                      "'{}' 는 안 돼요.".format(name), "shy", 0.6, "shake")
    if store.read(name):
        return _reply("'{}' 스킬이 이미 있어요. 다른 이름으로 하거나 먼저 "
                      "/스킬 삭제 {} 하세요.".format(name, name), "shy", 0.6)
    if gateway is None:
        return _reply("LLM 게이트웨이가 연결돼 있지 않아 초안을 못 만들어요. "
                      "run.py 로 실행했는지 확인해 주세요.", "sad", 0.6)

    # 재료 = 최근 대화 + (있으면) 관제 근거. 재료에 없는 건 못 쓰게 프롬프트로 못박는다.
    hist_txt = "\n".join(
        "{}: {}".format("사용자" if h.get("role") == "user" else "미라",
                        str(h.get("content", ""))[:800])
        for h in (history or [])[-12:] if isinstance(h, dict))
    ev = sentinel.evidence()
    material = ("[최근 대화]\n" + (hist_txt or "(없음)") + "\n\n"
                + ("[관제 근거]\n" + ev["text"] if ev["ok"] else ""))
    ask = "스킬 이름: {}\n주제: {}\n\n재료:\n{}".format(
        name, topic or "최근 대화의 핵심 지식", material)

    msgs = [{"role": "system", "content": skills.DRAFT_PROMPT},
            {"role": "user", "content": ask}]
    body, err = _plain_llm(gateway, model, temperature, msgs)
    if not body:
        return _reply("스킬 초안 생성이 실패했어요: {}".format(err), "sad", 0.7)

    desc = (topic or "대화에서 만든 스킬").replace("<", "").replace(">", "")[:180]
    md = skills.compose(name, desc, body)
    ok, errors, warnings = store.save(name, md)
    if not ok:
        return _reply("초안이 검증에 걸렸어요: {}".format(" / ".join(errors)),
                      "sad", 0.7)
    note = (" (경고: " + " / ".join(warnings) + ")") if warnings else ""
    return _reply(
        "'{}' 스킬을 만들었어요{}.\n"
        "· 전문 보기: /스킬 보기 {}\n"
        "· md 받기: /api/skills/md?name={}\n"
        "· html 받기: /api/skills/html?name={}\n"
        "이제 관련 질문이 오면 이 스킬을 근거로 같이 봐요.\n\n"
        "---\n{}".format(name, note, name, name, name, md),
        "joy", 0.9, "wave")


def _plain_llm(gateway, model, temperature, msgs):
    """스킬 초안용 일반 텍스트 호출 — 감정 JSON 스키마를 끼우면 안 된다.

    gateway.chat() 은 아바타 대사용이라 응답을 {emotion,text} 로 강제한다.
    스킬 본문은 마크다운 원문이 필요하므로 response_format 없이 직접 부른다.
    """
    import json as _json
    payload = {"model": model, "temperature": temperature, "messages": msgs}
    try:
        with gateway._request(payload) as r:          # noqa: SLF001 — 같은 패키지
            data = _json.loads(r.read().decode("utf-8"))
        raw = (data["choices"][0]["message"]["content"] or "").strip()
        # 추론 모델이 <think> 를 앞에 붙이면 벗긴다 — 본문에 새면 스킬이 오염된다
        raw = re.sub(r"(?s)^<think>.*?</think>\s*", "", raw)
        raw = re.sub(r"(?s)^```(?:markdown|md)?\s*\n(.*?)\n```\s*$", r"\1", raw)
        return raw.strip(), ""
    except Exception as e:  # noqa: BLE001
        return "", "{}: {}".format(type(e).__name__, e)
