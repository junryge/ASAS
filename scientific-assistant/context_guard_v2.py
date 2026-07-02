# -*- coding: utf-8 -*-
"""context_guard_v2 — 축출 포함 무한루프 보장. 토큰수 캐시로 O(n) per turn."""
from ctx_compress import compress, retrieve, _rough_tokens

def _t(m):
    if "_tok" not in m:
        m["_tok"] = _rough_tokens(m.get("content", ""))
    return m["_tok"]

class ContextGuardV2:
    def __init__(self, budget_tokens=128000, keep_recent=6, trigger_ratio=0.70):
        self.budget=budget_tokens; self.keep_recent=keep_recent
        self.trigger=trigger_ratio; self.all_refs={}; self.evicted=0

    def maybe_compress(self, messages):
        total=sum(_t(m) for m in messages)
        if total < self.budget*self.trigger:
            return messages
        keep=self.keep_recent
        head,tail=messages[:-keep],messages[-keep:]
        for m in head:
            if not m.get("_folded"):
                folded,refs=compress(m.get("content",""))
                if refs: self.all_refs.update(refs)
                m["content"]=folded; m["_folded"]=True; m["_tok"]=_rough_tokens(folded)
        sys_head=[m for m in head if m.get("role")=="system"]
        body=[m for m in head if m.get("role")!="system"]
        cur=sum(_t(m) for m in sys_head)+sum(_t(m) for m in body)+sum(_t(m) for m in tail)
        while body and cur>=self.budget:
            drop=body.pop(0); cur-=_t(drop)
            _,refs=compress(drop.get("content","")); 
            if refs: self.all_refs.update(refs)
            self.evicted+=1
        return sys_head+body+tail

    def make_retrieve_tool(self):
        def ctx_retrieve(ref_id): return retrieve(ref_id,self.all_refs) or "(복구 실패: ref 없음)"
        return ctx_retrieve
