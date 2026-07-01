# -*- coding: utf-8 -*-
"""context_guard.py — 채팅 턴 루프 앞단 컨텍스트 압축 가드.

폐쇄망 원칙: stdlib only, 단일파일, ctx_compress.py 만 의존.

쓰는 법 (LLM 호출 직전 한 줄):
    from context_guard import ContextGuard
    _guard = ContextGuard(budget_tokens=32000, keep_recent=4)
    messages = _guard.maybe_compress(messages)   # ← 이 한 줄
    # ... 이후 기존대로 LLM 호출 ...

★ 안전 원칙 (다른 기능에 영향 없게):
- **입력 메시지/딕셔너리를 절대 변형하지 않는다(non-mutating).** 토큰 캐시 키를
  메시지에 심지 않고 로컬 dict(id 기준)로만 들고, 압축 시엔 새 딕셔너리를 만든다.
  → 호출부의 data["messages"] / 세션 히스토리는 그대로 보존.
- 총 토큰이 budget*trigger 미만이면 **입력 리스트를 그대로 반환**(무변형·무복사).
  일반 짧은 대화는 손도 안 댄다.
- maybe_compress 는 어떤 예외에도 원본을 그대로 돌려줘 채팅이 끊기지 않는다.
- content 가 str 이 아니어도(예: 비전 content_parts 리스트) 그 메시지는 건드리지 않는다.

동작(예산 초과 시에만):
- 오래된 '도구 결과'부터 접고 → 그래도 넘치면 오래된 본문까지 접고 →
  최후엔 오래된 것을 축출(evict). 최근 keep_recent 개는 항상 원본 보존.
- 접기/축출한 원본은 all_refs 에 보관 → make_retrieve_tool() 로 복구 가능.
"""
from ctx_compress import compress, retrieve, _rough_tokens


def _content_str(m):
    """메시지 content 를 문자열로. 리스트/기타면 None(=압축 대상 아님)."""
    c = m.get("content", "")
    return c if isinstance(c, str) else None


class ContextGuard:
    def __init__(self, budget_tokens=32000, keep_recent=4, trigger_ratio=0.70,
                 enable_evict=True, name="ctx", verbose=True):
        self.budget = budget_tokens
        self.keep_recent = max(0, keep_recent)
        self.trigger = trigger_ratio
        self.enable_evict = enable_evict
        self.name = name          # 로그 식별용 (예: "데모스", "코딩")
        self.verbose = verbose    # 압축 실제 발동 시 콘솔 로그
        self.all_refs = {}       # 누적 복구맵 (CCR)
        self.evicted = 0

    # ── 토큰 수: 메시지를 변형하지 않고 로컬 캐시(id 기준)로만 센다 ──
    def _tok(self, m, cache):
        key = id(m)
        if key in cache:
            return cache[key]
        c = _content_str(m)
        try:
            n = _rough_tokens(c) if c is not None else _rough_tokens(str(m.get("content", "")))
        except Exception:
            n = 0
        cache[key] = n
        return n

    def _total(self, messages, cache):
        return sum(self._tok(m, cache) for m in messages)

    def maybe_compress(self, messages):
        """LLM 호출 직전에 부른다. 실패해도 원본을 그대로 돌려줘 안전."""
        try:
            return self._run(messages)
        except Exception:
            return messages   # 무슨 일이 있어도 채팅은 끊기지 않게

    def _run(self, messages):
        cache = {}
        before = self._total(messages, cache)
        if not messages or before < self.budget * self.trigger:
            return messages   # 여유 → 입력 그대로(무변형·무복사)

        keep = self.keep_recent
        if keep > 0:
            head_src, tail = messages[:-keep], messages[-keep:]
        else:
            head_src, tail = list(messages), []

        n_folded = 0

        # 1단계 microcompact: 오래된 '도구 결과'만 접기 (새 딕셔너리로 — 원본 불변)
        # ★ system 메시지(스킬/지시)는 절대 건드리지 않는다 → 스킬 기능 무손실.
        head = []
        for m in head_src:
            if m.get("role") == "tool":
                s = _content_str(m)
                if s is not None:
                    folded, refs = compress(s)
                    if refs:
                        self.all_refs.update(refs)
                    if folded != s:
                        nm = dict(m); nm["content"] = folded
                        head.append(nm)
                        n_folded += 1
                        continue
            head.append(m)

        # 2단계: 그래도 넘치면 오래된 '본문'(user/assistant)까지 접기. ★system 은 제외.
        if self._total(head, cache) + self._total(tail, cache) >= self.budget:
            folded_head = []
            for m in head:
                if m.get("role") == "system":
                    folded_head.append(m)      # 스킬/시스템 지시는 보존
                    continue
                s = _content_str(m)
                if s is not None:
                    folded, refs = compress(s)
                    if refs:
                        self.all_refs.update(refs)
                    if folded != s:
                        nm = dict(m); nm["content"] = folded
                        folded_head.append(nm)
                        n_folded += 1
                        continue
                folded_head.append(m)
            head = folded_head

        # 3단계: 접어도 넘치면 오래된 것 축출(원본은 all_refs 로 복구가능). ★system 은 보존.
        if self.enable_evict:
            sys_head = [m for m in head if m.get("role") == "system"]
            body = [m for m in head if m.get("role") != "system"]
            cur = self._total(sys_head, cache) + self._total(body, cache) + self._total(tail, cache)
            while body and cur >= self.budget:
                drop = body.pop(0)
                cur -= self._tok(drop, cache)
                s = _content_str(drop)
                if s is not None:
                    _, refs = compress(s)
                    if refs:
                        self.all_refs.update(refs)
                self.evicted += 1
            head = sys_head + body

        result = head + tail
        after = self._total(result, {})
        if self.verbose and after < before:
            try:
                print(f"[ctx_compress] {self.name} 압축: {before:,} → {after:,} 토큰 "
                      f"(접음 {n_folded}개, 축출 {self.evicted}개, 복구맵 {len(self.all_refs)}개)",
                      flush=True)
            except Exception:
                pass
        return result

    def make_retrieve_tool(self):
        """접힌/축출된 원본을 ref_id 로 복구하는 함수. 도구로 등록해서 쓴다."""
        def ctx_retrieve(ref_id: str) -> str:
            return retrieve(ref_id, self.all_refs) or "(복구 실패: ref 없음)"
        return ctx_retrieve
