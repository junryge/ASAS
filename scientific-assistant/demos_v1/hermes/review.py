"""
demos_v1/hermes/review.py — 백그라운드 리뷰 (대화 종료 후 스스로 저장 판단)

- 카운터 임계(메모리) 도달 시 백그라운드 데몬 스레드로 실행.
- LLM 호출은 호스트가 주입(set_completion). 주입 없으면 no-op(포터블 유지).
- 리뷰는 "메모리(사실/선호)"만 자동 저장. 스킬은 확인형이라 리뷰에서 자동 생성 안 함.
- 본 대화를 절대 차단하지 않음. 실패는 로그만, 카운터는 finally 에서 리셋(무한 재시도 방지).
"""
from __future__ import annotations
import threading

from demos_v1.hermes import protocol, memory, counters, sessions

_COMPLETE_FN = None   # fn(messages: list[dict]) -> str  (호스트가 주입)

REVIEW_SYS = (
    "너는 대화 리뷰어다. 아래 '최근 대화'에서 장기 기억할 가치가 있는 "
    "선언적 사실(memory)이나 사용자 선호(user)를 찾아라.\n"
    "- 이미 '현재 기억'에 있는 건 다시 저장하지 마라.\n"
    "- 저장할 게 있으면 ```hermes:memory 블록(들)로만 출력하라. 설명/잡담 금지.\n"
    "- 명령형 금지, 선언형 한 문장. 환경·역할·시스템·도구·데이터는 store: memory, "
    "형식·말투·언어 취향은 store: user.\n"
    "- 저장할 게 없으면 '없음' 한 단어만 출력."
)


def set_completion(fn) -> None:
    """호스트가 LLM 완성 함수를 주입. fn(messages)->str."""
    global _COMPLETE_FN
    _COMPLETE_FN = fn


def _recent_conversation(user_id: str, limit: int = 20) -> list[dict]:
    msgs = sessions._load_all(user_id)[-limit:]
    return [{"role": m.get("role"), "content": m.get("content", "")}
            for m in msgs if m.get("content")]


def _do_review(user_id: str) -> None:
    try:
        if _COMPLETE_FN is None:
            return
        convo = _recent_conversation(user_id)
        if not convo:
            return
        existing = memory.snapshot(user_id) or "(없음)"
        convo_text = "\n".join(f"{m['role']}: {(m['content'] or '')[:400]}" for m in convo)
        user_prompt = f"=== 현재 기억 ===\n{existing}\n\n=== 최근 대화 ===\n{convo_text}"
        messages = [{"role": "system", "content": REVIEW_SYS},
                    {"role": "user", "content": user_prompt}]
        text = _COMPLETE_FN(messages) or ""
        _clean, blocks = protocol.parse_blocks(text)
        saved = 0
        for b in blocks:
            if b.get("kind") != "memory":
                continue
            a, sn = b.get("action", "add"), b.get("store", "memory")
            if a == "add":
                ok, _ = memory.add(user_id, sn, b.get("text", ""))
            elif a == "replace":
                ok, _ = memory.replace(user_id, sn, b.get("target", ""), b.get("text", ""))
            elif a == "remove":
                ok, _ = memory.remove(user_id, sn, b.get("target", ""))
            else:
                ok = False
            if ok:
                saved += 1
        if saved:
            print(f"  ♻️ 헤르메스 리뷰: {user_id} 기억 {saved}건 저장")
    except Exception as e:
        print(f"  ⚠️  헤르메스 리뷰 실패(무시): {e}")
    finally:
        # 성공/실패 무관 카운터 리셋 → 매 턴 재시도 방지
        try:
            counters.reset_memory(user_id)
        except Exception:
            pass


def run_async(user_id: str) -> bool:
    """백그라운드 리뷰 시작. 완성함수 미주입이면 no-op."""
    if _COMPLETE_FN is None:
        return False
    threading.Thread(target=_do_review, args=(user_id,), daemon=True).start()
    return True
