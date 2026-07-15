#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다변량 ML 고도화 타당성 프로브 (순수 파이썬)
=============================================
질문: 265개 컬럼 중 선행지표를 피처로 넣으면, '30분 뒤 정체'를
      단일신호(자기 지속성)보다 잘 맞추는가?

방법 (leakage 없음):
  1) 시간순 train/test 분할 (앞 train_frac, 뒤 test)
  2) 임계값 = train 구간 타깃 p-분위수
  3) 라벨 = 타깃[t+H] >= 임계   (H분 뒤 정체 여부)
  4) 피처 선택 = train 구간에서 |corr(col[t], 타깃[t+H])| 상위 K개 (선행지표)
     - 선택도 train만 보고 함 → test leakage 없음
  5) 두 모델 로지스틱 회귀 비교:
       · univariate : 타깃 자신의 최근값(지속성)만
       · multivariate: 타깃 지속성 + 선행지표 K개
  6) test 구간 AUC / precision·recall 로 비교

주의: 하루 데이터면 근거가 약하다(과적합 위험). 정식은 Apr~May train / June test.
      이 프로브는 '고도화 이득이 있나' 방향성 확인용.
"""
from __future__ import annotations

import csv
import math
import sys

TARGET = "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"


# ------------------------- 데이터 로드 -------------------------
def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    fields = [c for c in rows[0].keys() if c != "CRT_TM"]
    data = {}
    for c in fields:
        vals = []
        for r in rows:
            try:
                f = float(r.get(c, ""))
                vals.append(f if math.isfinite(f) else None)
            except Exception:
                vals.append(None)
        data[c] = vals
    return data, fields, len(rows)


def ffill(vals):
    out, last = [], None
    for v in vals:
        if v is not None:
            last = v
        out.append(last if last is not None else 0.0)
    return out


# ------------------------- 통계 유틸 -------------------------
def pctl(vals, p):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return float("nan")
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def corr_future(x, tgt, lead, lo, hi):
    xs, ys = [], []
    for t in range(lo, hi - lead):
        a, b = x[t], tgt[t + lead]
        if a is not None and b is not None:
            xs.append(a); ys.append(b)
    if len(xs) < 30:
        return 0.0
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
    return cov / (sx * sy)


# ------------------------- 로지스틱 회귀 (순수 파이썬) -------------------------
class Logit:
    def __init__(self, dim, lr=0.1, l2=1e-3, epochs=300):
        self.w = [0.0] * dim
        self.b = 0.0
        self.lr, self.l2, self.epochs = lr, l2, epochs

    @staticmethod
    def _sig(z):
        if z < -30:
            return 0.0
        if z > 30:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def fit(self, X, y):
        n = len(X)
        dim = len(self.w)
        for _ in range(self.epochs):
            gw = [0.0] * dim
            gb = 0.0
            for i in range(n):
                p = self._sig(sum(self.w[j] * X[i][j] for j in range(dim)) + self.b)
                e = p - y[i]
                for j in range(dim):
                    gw[j] += e * X[i][j]
                gb += e
            for j in range(dim):
                self.w[j] -= self.lr * (gw[j] / n + self.l2 * self.w[j])
            self.b -= self.lr * (gb / n)

    def prob(self, x):
        return self._sig(sum(self.w[j] * x[j] for j in range(len(self.w))) + self.b)


def standardize(cols_train, cols_all):
    """train 통계로 표준화 (mu,sd) → 모든 구간 적용."""
    stats = []
    for c in cols_train:
        mu = sum(c) / len(c)
        sd = math.sqrt(sum((v - mu) ** 2 for v in c) / len(c)) or 1.0
        stats.append((mu, sd))
    return stats


def auc(y, p):
    """rank 기반 AUC (pure python)."""
    pos = [p[i] for i in range(len(y)) if y[i] == 1]
    neg = [p[i] for i in range(len(y)) if y[i] == 0]
    if not pos or not neg:
        return float("nan")
    # Mann-Whitney U
    allp = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank = {}
    i = 0
    r = 1
    ranks = [0.0] * len(allp)
    # average ranks for ties
    vals = [v for v, _ in allp]
    j = 0
    while j < len(vals):
        k = j
        while k + 1 < len(vals) and vals[k + 1] == vals[j]:
            k += 1
        avg = (j + 1 + k + 1) / 2.0
        for m in range(j, k + 1):
            ranks[m] = avg
        j = k + 1
    sum_pos = sum(ranks[i] for i in range(len(allp)) if allp[i][1] == 1)
    n1 = len(pos); n0 = len(neg)
    return (sum_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def prec_recall(y, p, thr=0.5):
    tp = sum(1 for i in range(len(y)) if p[i] >= thr and y[i] == 1)
    fp = sum(1 for i in range(len(y)) if p[i] >= thr and y[i] == 0)
    fn = sum(1 for i in range(len(y)) if p[i] < thr and y[i] == 1)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f1


# ------------------------- 메인 -------------------------
def main():
    path = sys.argv[1]
    H = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    train_frac = 0.7

    data, fields, N = load(path)
    split = int(N * train_frac)

    tgt = ffill(data[TARGET])
    thr = pctl(data[TARGET][:split], 0.97)  # 임계는 train 구간에서

    # 라벨: t+H 시점 정체
    def label(t):
        return 1 if tgt[t + H] >= thr else 0

    # 후보 컬럼: 살아있고 결측 적은 것
    live = []
    for c in fields:
        v = [x for x in data[c] if x is not None]
        if len(v) > N * 0.5 and len(set(v)) > 3:
            live.append(c)

    # 선행지표 선택 (train 구간 상관 상위 K) — target 자신 제외
    scored = []
    for c in live:
        if c == TARGET:
            continue
        r = corr_future(ffill(data[c]), tgt, H, 0, split)
        scored.append((abs(r), r, c))
    scored.sort(reverse=True)
    selected = [(c, r) for _, r, c in scored[:K]]

    # 피처 구성
    #  · univariate: 타깃 지속성 (현재값, 5분평균, 10분평균, 기울기)
    #  · multivariate: 위 + 선행지표 K개 현재값
    def tgt_feats(t):
        cur = tgt[t]
        w5 = tgt[max(0, t - 4):t + 1]
        w10 = tgt[max(0, t - 9):t + 1]
        avg5 = sum(w5) / len(w5)
        avg10 = sum(w10) / len(w10)
        slope = (tgt[t] - tgt[max(0, t - 10)]) / 10.0
        return [cur, avg5, avg10, slope]

    ff = {c: ffill(data[c]) for c, _ in selected}

    def build(t, multi):
        f = tgt_feats(t)
        if multi:
            f = f + [ff[c][t] for c, _ in selected]
        return f

    idx = list(range(10, N - H))  # 앞 10분(윈도우), 뒤 H분(라벨) 확보
    tr = [t for t in idx if t < split]
    te = [t for t in idx if t >= split]

    def run(multi):
        Xtr = [build(t, multi) for t in tr]
        ytr = [label(t) for t in tr]
        Xte = [build(t, multi) for t in te]
        yte = [label(t) for t in te]
        # 표준화 (train 통계)
        dim = len(Xtr[0])
        mus = [sum(row[j] for row in Xtr) / len(Xtr) for j in range(dim)]
        sds = [math.sqrt(sum((row[j] - mus[j]) ** 2 for row in Xtr) / len(Xtr)) or 1.0
               for j in range(dim)]
        def norm(X):
            return [[(row[j] - mus[j]) / sds[j] for j in range(dim)] for row in X]
        m = Logit(dim, lr=0.3, l2=1e-3, epochs=400)
        m.fit(norm(Xtr), ytr)
        pte = [m.prob(x) for x in norm(Xte)]
        return yte, pte

    y_uni, p_uni = run(False)
    y_mul, p_mul = run(True)

    n_pos_tr = sum(label(t) for t in tr)
    n_pos_te = sum(y_uni)
    print("=" * 72)
    print(f" 다변량 ML 고도화 프로브 — {path.split('/')[-1]}")
    print(f" 타깃: 반송시간, H={H}분 뒤 정체 예측 | 임계(train p97)={thr:.2f}")
    print(f" train {len(tr)}(정체 {n_pos_tr}건) / test {len(te)}(정체 {n_pos_te}건)"
          f"  | test 정체비율 {100*n_pos_te/len(y_uni):.1f}%")
    print("=" * 72)
    print(" 선택된 선행지표 (train 상관 상위):")
    for c, r in selected:
        print(f"   {c[:52]:<52} corr(t+{H})={r:+.2f}")
    print("-" * 72)
    au = auc(y_uni, p_uni); am = auc(y_mul, p_mul)
    pu = prec_recall(y_uni, p_uni); pm = prec_recall(y_mul, p_mul)
    print(f"{'모델':<26}{'AUC':>8}{'precision':>11}{'recall':>9}{'F1':>7}")
    print(f"{'단일신호(지속성)':<24}{au:>8.3f}{pu[0]:>11.2f}{pu[1]:>9.2f}{pu[2]:>7.2f}")
    print(f"{'다변량(+선행지표)':<23}{am:>8.3f}{pm[0]:>11.2f}{pm[1]:>9.2f}{pm[2]:>7.2f}")
    print("=" * 72)
    lift = (am - au)
    print(f" AUC 이득(다변량-단일): {lift:+.3f}")
    if n_pos_te < 10:
        print(f" ⚠ test 정체 사건이 {n_pos_te}건뿐 → AUC/이득이 통계적으로 무의미(노이즈).")
        print("   이 프로브는 '파이프라인이 돈다'만 증명. 승패 판정 금지.")
    else:
        print("  →  " + ("다변량이 유의미하게 나음 ✅" if lift > 0.02 else
                          "단일신호 대비 이득 미미"))
    print(" ※ 정식 결론은 사건 충분한 Apr~May train / June test 필요.")


if __name__ == "__main__":
    main()
