# -*- coding: utf-8 -*-
"""context_guard.py — 채팅 턴 루프 앞단 컨텍스트 압축 가드.

폐쇄망 원칙: stdlib only, 단일파일, ctx_compress.py 만 의존.

쓰는 법 (LLM 호출 직전 한 줄):
    from context_guard import ContextGuard
    _guard = ContextGuard(budget_tokens=32000, keep_recent=4)
    messages = _guard.maybe_compress(messages)   # ← 이 한 줄
    # ... 이후 기존대로 LLM 호출 ...

동작:
- 총 토큰이 budget*trigger 미만이면 손 안 댐(일반 짧은 대화는 무변형).
- 넘치면 오래된 메시지의 '도구 결과'부터 접고(microcompact),
  그래도 넘치면 오래된 본문까지 접고, 최후엔 오래된 것을 축출(evict)한다.
- 최근 keep_recent 개 메시지는 항상 원본 보존.
- 접기/축출한 원본은 all_refs 에 보관 → make_retrieve_tool() 로 복구 가능.

안전장치(프로덕션): content 가 str 이 아니어도(예: 비전 content_parts 리스트)
절대 예외를 내지 않고 그 메시지는 건드리지 않고 통과시킨다.
"""
from ctx_compress import compress, retrieve, _rough_tokens


def _content_str(m):
    """메시지 content 를 문자열로. 리스트/기타면 None(=압축 대상 아님)."""
    c = m.get("content", "")
    return c if isinstance(c, str) else None


def _tok(m):
    """토큰 수(캐시). str 아니면 대략 길이로 근사, 실패해도 0."""
    if "_tok" in m:
        return m["_tok"]
    c = _content_str(m)
    if c is None:
        try:
            n = _rough_tokens(str(m.get("content", "")))
        except Exception:
            n = 0
    else:
        n = _rough_tokens(c)
    m["_tok"] = n
    return n


class ContextGuard:
    def __init__(self, budget_tokens=32000, keep_recent=4, trigger_ratio=0.70,
                 enable_evict=True):
        self.budget = budget_tokens
        self.keep_recent = max(0, keep_recent)
        self.trigger = trigger_ratio
        self.enable_evict = enable_evict
        self.all_refs = {}       # 누적 복구맵 (CCR)
        self.evicted = 0

    def _total(self, messages):
        return sum(_tok(m) for m in messages)

    def maybe_compress(self, messages):
        """LLM 호출 직전에 부른다. 실패해도 원본을 그대로 돌려줘 안전."""
        try:
            return self._run(messages)
        except Exception:
            return messages   # 무슨 일이 있어도 채팅은 끊기지 않게

    def _run(self, messages):
        if not messages or self._total(messages) < self.budget * self.trigger:
            return messages

        keep = self.keep_recent
        if keep > 0:
            head, tail = messages[:-keep], messages[-keep:]
        else:
            head, tail = list(messages), []

        # 1단계 microcompact: 오래된 '도구 결과'만 접기 (이미 접은 건 skip)
        for m in head:
            if m.get("_folded"):
                continue
            if m.get("role") == "tool":
                s = _content_str(m)
                if s is None:
                    continue
                folded, refs = compress(s)
                if refs:
                    self.all_refs.update(refs)
                m["content"] = folded
                m["_folded"] = True
                m["_tok"] = _rough_tokens(folded)

        # 2단계: 그래도 넘치면 오래된 본문(도구 아닌 것 포함)까지 접기
        if self._total(head) + self._total(tail) >= self.budget:
            for m in head:
                if m.get("_folded"):
                    continue
                s = _content_str(m)
                if s is None:
                    continue
                folded, refs = compress(s)
                if refs:
                    self.all_refs.update(refs)
                m["content"] = folded
                m["_folded"] = True
                m["_tok"] = _rough_tokens(folded)

        # 3단계: 접어도 넘치면 오래된 것 축출(원본은 all_refs 로 복구가능). system 은 보존.
        if self.enable_evict:
            sys_head = [m for m in head if m.get("role") == "system"]
            body = [m for m in head if m.get("role") != "system"]
            cur = self._total(sys_head) + self._total(body) + self._total(tail)
            while body and cur >= self.budget:
                drop = body.pop(0)
                cur -= _tok(drop)
                s = _content_str(drop)
                if s is not None:
                    _, refs = compress(s)
                    if refs:
                        self.all_refs.update(refs)
                self.evicted += 1
            head = sys_head + body

        return head + tail

    def make_retrieve_tool(self):
        """접힌/축출된 원본을 ref_id 로 복구하는 함수. 도구로 등록해서 쓴다."""
        def ctx_retrieve(ref_id: str) -> str:
            return retrieve(ref_id, self.all_refs) or "(복구 실패: ref 없음)"
        return ctx_retrieve
