# -*- coding: utf-8 -*-
import time
from context_guard_v2 import ContextGuardV2
from ctx_compress import _rough_tokens
def tok(m): 
    return sum(x.get("_tok", _rough_tokens(x.get("content",""))) for x in m)
def turn(t):
    log="\n".join(f"2026-07-02 09:{t%60:02d}:{k%60:02d} INFO worker[{k%8}] job {t*200+k} ok lat={k}ms" for k in range(120))+f"\nERROR job {t} timeout\n"*3
    return [{"role":"user","content":f"[{t}] 로그 분석"},{"role":"tool","content":log},{"role":"assistant","content":f"[{t}] 확인"}]
B=128000
for N in (400,2000):
    g=ContextGuardV2(B,keep_recent=6); conv=[{"role":"system","content":"시스템"}]; peak=0; t0=time.time()
    for t in range(N):
        conv+=turn(t); conv=g.maybe_compress(conv); peak=max(peak,tok(conv))
    dt=time.time()-t0
    print(f"[{N}턴/128K] 완주✅ 최대 {peak:,}토큰 {'(≤128K bounded✅)' if peak<=B else '(초과❌)'} 축출 {g.evicted} 복구맵 {len(g.all_refs)} {dt:.1f}s")
    if N==2000:
        rt=g.make_retrieve_tool(); rid=next(iter(g.all_refs),None)
        rec=rt(rid) if rid else None
        print(f"[축출후 복구] ctx_retrieve → {'✅ '+str(len(rec))+'자' if rec and '복구 실패' not in rec else '❌'}")
