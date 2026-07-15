#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""265개 컬럼 EDA — ML 고도화 가능성(선행지표) 탐색. 순수 파이썬."""
import csv, math, sys
from collections import defaultdict

F = sys.argv[1]
TARGET = "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"

rows = list(csv.DictReader(open(F, encoding="utf-8-sig")))
fields = [c for c in rows[0].keys() if c != "CRT_TM"]
N = len(rows)

def col(c):
    out = []
    for r in rows:
        v = r.get(c, "")
        try:
            f = float(v)
            out.append(f if math.isfinite(f) else None)
        except Exception:
            out.append(None)
    return out

data = {c: col(c) for c in fields}

# 1) 컬럼 건강도: 상수/결측/변동
def stats(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return dict(n=0, nn=0, std=0, uniq=0, mean=0, mn=0, mx=0)
    mean = sum(v)/len(v)
    std = math.sqrt(sum((x-mean)**2 for x in v)/len(v))
    return dict(n=len(vals), nn=len(v), std=std, uniq=len(set(v)),
                mean=mean, mn=min(v), mx=max(v))

st = {c: stats(data[c]) for c in fields}

dead = [c for c in fields if st[c]["nn"] == 0]
const = [c for c in fields if st[c]["nn"] > 0 and st[c]["uniq"] <= 1]
nearconst = [c for c in fields if st[c]["uniq"] > 1 and st[c]["std"] < 1e-9]
live = [c for c in fields if st[c]["nn"] > 0 and st[c]["std"] > 0]

# 카테고리 분류
def cat(c):
    p = c.split(".")
    return p[1] if len(p) > 1 else "ETC"
bycat = defaultdict(list)
for c in fields:
    bycat[cat(c)].append(c)

print("="*70)
print(f" EDA: {F.split('/')[-1]}  |  {N}행 × {len(fields)}컬럼")
print("="*70)
print(f" 살아있는 컬럼(변동 있음): {len(live)}")
print(f" 죽은 컬럼(전부 결측): {len(dead)}")
print(f" 상수 컬럼(값 1종): {len(const)}")
print(f" 사실상 상수(std≈0): {len(nearconst)}")
print("\n 카테고리별 살아있는/전체 컬럼:")
for ct in sorted(bycat, key=lambda k: -len(bycat[k])):
    liven = sum(1 for c in bycat[ct] if c in live)
    print(f"   {ct:<12} {liven:>3}/{len(bycat[ct]):<3} 살아있음")

# 2) 상관 (동시점 + 선행 lag)
tgt = data[TARGET]

def pearson_lag(x, lead):
    """corr( x[t], target[t+lead] )  — lead>0 이면 x가 미래 target을 예측(선행지표)."""
    xs, ys = [], []
    for t in range(N-lead):
        a, b = x[t], tgt[t+lead]
        if a is not None and b is not None:
            xs.append(a); ys.append(b)
    if len(xs) < 30:
        return None
    mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
    sx = math.sqrt(sum((a-mx)**2 for a in xs))
    sy = math.sqrt(sum((b-my)**2 for b in ys))
    if sx < 1e-12 or sy < 1e-12:
        return None
    cov = sum((xs[i]-mx)*(ys[i]-my) for i in range(len(xs)))
    return cov/(sx*sy)

# 각 살아있는 컬럼에 대해 lead=0,10,30 상관 (target 자기자신 제외)
results = []
for c in live:
    if c == TARGET:
        continue
    r0 = pearson_lag(data[c], 0)
    r10 = pearson_lag(data[c], 10)
    r30 = pearson_lag(data[c], 30)
    if r10 is None and r30 is None:
        continue
    results.append((c, r0, r10, r30))

# 미래(10분후) 상관 절대값 기준 정렬 = 선행지표 후보
def absval(x): return abs(x) if x is not None else 0
results.sort(key=lambda r: absval(r[2]), reverse=True)

print("\n" + "="*70)
print(" 선행지표 후보 TOP 20 (|corr(x[t], 반송시간[t+10])| 기준)")
print(" r0=동시점  r10=10분후  r30=30분후 상관")
print("="*70)
print(f"{'컬럼':<46}{'r0':>7}{'r10':>7}{'r30':>7}")
print("-"*70)
def fmt(x): return f"{x:+.2f}" if x is not None else "  -"
for c, r0, r10, r30 in results[:20]:
    short = c.replace("M16HUB.","H.").replace(".CURRENTQCNT","").replace("CURRENTQCNT","")
    print(f"{short[:46]:<46}{fmt(r0):>7}{fmt(r10):>7}{fmt(r30):>7}")

# target 자기상관 (persistence) — ML 하한선 참고
r_self10 = pearson_lag(tgt, 10)
r_self30 = pearson_lag(tgt, 30)
print("\n 참고: 반송시간 자기상관  10분후={}  30분후={}".format(fmt(r_self10), fmt(r_self30)))
print(" → 자기상관이 높으면 단일신호 예측만으로도 상당 가능. 낮으면 covariate 필요.")
