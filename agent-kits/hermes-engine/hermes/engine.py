"""
hermes/engine.py — 오케스트레이션 (프롬프트 조립 + 응답 블록 적용)
"""
from __future__ import annotations

from . import memory, skills, protocol, counters

PROTOCOL_GUIDE = """\
=== 헤르메스 능력 (텍스트 프로토콜) ===
너는 대화에서 배우고 기억하는 에이전트다. 아래 블록을 답변 끝에 덧붙여 사용한다.
(블록은 사용자에게 안 보이게 시스템이 처리한다. 남발 금지 — 정말 가치 있을 때만.)

1) 대화에서 기억할 정보가 나오면 저장한다. 두 종류를 반드시 구분한다:
   · store: memory = 환경·프로젝트 "사실" — 담당 FAB/라인, 시스템·도구, 데이터 종류, 제약, 도메인 용어 등
   · store: user   = 사용자 "선호" — 답변 형식/말투/언어/길이 등
   ★ 사용자가 자신의 역할·담당·사용 시스템·도구·데이터·도메인을 드러내면 → 반드시 store: memory 로 저장한다.

예) 환경·프로젝트 사실(memory):
```hermes:memory
store: memory
action: add
text: 사용자는 M16_BR FAB의 OHT 반송 시스템(OHS) 정체를 분석한다
```
예) 사용자 선호(user):
```hermes:memory
store: user
action: add
text: 사용자는 답변을 표로 정리하는 것을 선호한다
```
- 선언형만(명령형 "항상 ~하라" 금지), 한 문장. 절차·방법은 메모리가 아니라 스킬로.
- 새 사실/선호가 나올 때마다 적극적으로 저장하되, 중복·사소한 잡담은 생략.
- action: add(신규) | replace(target=기존 일부) | remove(target=기존 일부)

2) 재사용 가치 있는 절차/해법을 발견하면(여러 단계 작업 완료·까다로운 오류 해결·비자명 워크플로):
```hermes:skill
action: create         # create | patch
name: <소문자-하이픈 클래스명>   # 일회성/날짜 이름 금지
when: <언제 쓰는 스킬인지 한 줄>
body: |
  1. ...
  2. ...
```
- 저장 전 사용자 승인을 받는다(시스템이 처리).

3) 요청이 모호하면 추측하지 말고 먼저 되묻는다:
```hermes:ask
- <핵심 질문1>
- <핵심 질문2>
```
"""


def build_system_prompt(user_id: str, query: str = "") -> str:
    parts = []
    mem = memory.snapshot(user_id)
    if mem:
        parts.append(mem)
    idx = skills.index_text(user_id)
    if idx:
        parts.append(idx)
    if query:
        recalled = skills.recall(user_id, query, top_k=2)
        if recalled:
            bodies = "\n\n".join(f"--- 스킬: {r['name']} ---\n{r['body']}" for r in recalled)
            parts.append("=== 관련 개인 스킬 본문 ===\n" + bodies)
    parts.append(PROTOCOL_GUIDE)
    return "\n\n".join(parts)


def apply_response(user_id: str, answer: str) -> dict:
    clean, blocks = protocol.parse_blocks(answer)
    out = {"clean": clean, "memory_results": [], "pending_skills": [],
           "questions": [], "snapshot_changed": False}
    for b in blocks:
        if b["kind"] == "memory":
            a = b.get("action", "add")
            sn = b.get("store", "memory")
            if a == "add":
                ok, msg = memory.add(user_id, sn, b.get("text", ""))
            elif a == "replace":
                ok, msg = memory.replace(user_id, sn, b.get("target", ""), b.get("text", ""))
            elif a == "remove":
                ok, msg = memory.remove(user_id, sn, b.get("target", ""))
            else:
                ok, msg = False, f"알 수 없는 메모리 액션: {a}"
            out["memory_results"].append({"ok": ok, "msg": msg, "action": a, "store": sn})
            if ok and msg != "이미 존재 (스킵)":
                out["snapshot_changed"] = True
        elif b["kind"] == "skill":
            out["pending_skills"].append({k: b.get(k, "") for k in
                                          ("action", "name", "when", "body", "find", "replace")})
        elif b["kind"] == "ask":
            out["questions"].extend(b.get("questions", []))
    return out


def confirm_skill(user_id: str, spec: dict) -> tuple[bool, str]:
    a = (spec.get("action") or "create").lower()
    name = spec.get("name", "")
    if a == "create":
        ok, msg = skills.create(user_id, name, spec.get("when", ""), spec.get("body", ""))
    elif a == "patch":
        ok, msg = skills.patch(user_id, name, spec.get("find", ""), spec.get("replace", ""))
    elif a == "edit":
        ok, msg = skills.edit(user_id, name, spec.get("when", ""), spec.get("body", ""))
    elif a == "delete":
        ok, msg = skills.delete(user_id, name)
    else:
        return False, f"알 수 없는 스킬 액션: {a}"
    if ok:
        counters.reset_skill(user_id)
    return ok, msg
