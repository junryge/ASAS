#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
realtime.py — 실시간 판정 러너
==============================
수집기가 매분 덮어쓰는 `predict/M16A_HUBROOM_PR.csv` (직전 90분, 분당 1행)를
감시하면서, 학습된 기준(model_config.json)으로 매분 정체를 선제 판정한다.

    [수집기] --매분 덮어씀--> predict/M16A_HUBROOM_PR.csv (90행)
                                      │
                                      ▼
                        realtime.py (매분 00초+오프셋)
                                      │
              10분 이동평균 → Chronos-2 예측 → 초과확률 → 단계
                                      │
                                      ▼
                    콘솔 출력 + ml_predict/{날짜}_ml_chronos_2.csv
                             + (선택) 경보 훅

수집기 윈도우가 90분이라 `--context 90` 과 정확히 맞는다.
러너는 자체 이력도 누적하므로 재시작 후에도 이동평균이 끊기지 않는다.

사용:
    python realtime.py --config model_config.json \\
        --input predict/M16A_HUBROOM_PR.csv \\
        --model chronos_2 --device cuda --p-on 0.30

    # 한 번만 판정하고 종료 (테스트용)
    python realtime.py --config model_config.json --input ... --once

    # 경보 시 외부 명령 실행 (메신저·Logpresso 연동)
    python realtime.py ... --on-alert "python notify.py"
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime

from data import moving_avg, load_config, TARGET, TIME_COL
from detect import Forecaster, exceed_prob

STAGE_NAME = {0: "정상", 1: "관찰", 2: "선제경보", 3: "정체 진행중"}
STAGE_MARK = {0: "  ", 1: "· ", 2: "⚠ ", 3: "🚨"}


# ──────────────────────────────────────────────────────────────
# 입력 읽기
# ──────────────────────────────────────────────────────────────
def read_snapshot(path, retries=5, delay=0.4):
    """
    수집기가 쓰는 중일 수 있으므로 재시도하며 읽는다.
    반환: [(datetime, value|None), ...] 시각순
    """
    last_err = None
    for _ in range(retries):
        try:
            rows = []
            with open(path, encoding="utf-8-sig", newline="") as f:
                rd = csv.DictReader(f)
                if rd.fieldnames is None or TARGET not in rd.fieldnames:
                    raise ValueError(f"'{TARGET}' 컬럼이 없습니다")
                for r in rd:
                    t = (r.get(TIME_COL) or "").strip()
                    if not t:
                        continue
                    try:
                        dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    raw = (r.get(TARGET) or "").strip()
                    try:
                        v = float(raw)
                    except ValueError:
                        v = None
                    rows.append((dt, v))
            if rows:
                rows.sort(key=lambda x: x[0])
                return rows
            last_err = "빈 파일"
        except Exception as e:
            last_err = e
        time.sleep(delay)
    raise RuntimeError(f"입력을 읽지 못했습니다: {path} ({last_err})")


# ──────────────────────────────────────────────────────────────
# 상태 (재시작 대비)
# ──────────────────────────────────────────────────────────────
def load_state(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        hist = [(datetime.strptime(t, "%Y-%m-%d %H:%M:%S"), v)
                for t, v in s.get("history", [])]
        return {"history": hist, "active": s.get("active", False),
                "last": s.get("last")}
    except Exception:
        return None


def save_state(path, history, active, last):
    if not path:
        return
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "history": [[t.strftime("%Y-%m-%d %H:%M:%S"), v]
                            for t, v in history],
                "active": active, "last": last,
            }, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"  (상태 저장 실패: {e})", file=sys.stderr)


# ──────────────────────────────────────────────────────────────
# 출력
# ──────────────────────────────────────────────────────────────
OUT_COLS = ["datetime", "raw_value", "smoothed", "stage", "stage_name",
            "prob", "lead_min", "threshold", "reason"]


def append_result(path, row):
    if not path:
        return
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(OUT_COLS)
        w.writerow(row)


def out_path(pattern, now):
    """--out 에 날짜 포맷(%Y%m%d 등)이 있으면 치환 → 날짜별 파일."""
    return now.strftime(pattern) if pattern and "%" in pattern else pattern


# ──────────────────────────────────────────────────────────────
# 판정 1회
# ──────────────────────────────────────────────────────────────
def judge(history, cfg, fc, horizon, context, p_on, p_off, active):
    """history: [(dt, value)] → (stage, prob, lead, smoothed, reason, active)"""
    thr = cfg["threshold"]
    window = cfg["window"]

    filled, last = [], None
    for _, v in history:
        if v is not None:
            last = v
        filled.append(last if last is not None else 0.0)
    sm = moving_avg(filled, window)
    cur = sm[-1]

    # 이미 임계 초과 → 진행 중
    if cur >= thr:
        return 3, 1.0, None, cur, f"이동평균 {cur:.2f} ≥ 임계 {thr}", True

    ctx = sm[-context:]
    if len(ctx) < 15:
        return 0, 0.0, None, cur, "이력 부족", False

    fcst = fc.predict([ctx], horizon)[0]
    best_p, lead = 0.0, None
    for h in range(horizon):
        p = exceed_prob(fcst["q10"][h], fcst["q50"][h], fcst["q90"][h], thr)
        if p > best_p:
            best_p = p
        if lead is None and p >= p_on:
            lead = h + 1

    if best_p >= p_on:
        active = True
    elif best_p < p_off:
        active = False

    if active and lead is not None:
        return 2, best_p, lead, cur, f"약 {lead}분 뒤 임계 초과 예상", active
    if best_p >= p_off:
        return 1, best_p, None, cur, "상승 조짐", active
    return 0, best_p, None, cur, "정상", active


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="실시간 정체 선제 판정")
    ap.add_argument("--config", required=True, help="learn 산출물 model_config.json")
    ap.add_argument("--input", default="predict/M16A_HUBROOM_PR.csv",
                    help="수집기가 매분 덮어쓰는 CSV")
    ap.add_argument("--out", default="ml_predict/%Y%m%d_ml_chronos_2.csv",
                    help="결과 append 경로 (날짜 포맷 사용 가능)")
    ap.add_argument("--state", default="realtime_state.json",
                    help="재시작 대비 상태 파일")
    ap.add_argument("--model", default="chronos_2")
    ap.add_argument("--device", default=None)
    ap.add_argument("--horizon", type=int, default=30, help="예측 지평(분)")
    ap.add_argument("--context", type=int, default=90, help="입력 이력(분)")
    ap.add_argument("--p-on", type=float, default=0.30)
    ap.add_argument("--p-off", type=float, default=0.20)
    ap.add_argument("--interval", type=int, default=60, help="주기(초)")
    ap.add_argument("--offset", type=int, default=8,
                    help="매분 몇 초 뒤에 읽을지 (수집기 쓰기 완료 대기)")
    ap.add_argument("--history", type=int, default=600,
                    help="러너가 유지할 이력 길이(분)")
    ap.add_argument("--on-alert", default=None,
                    help="stage>=2 일 때 실행할 외부 명령 (환경변수로 값 전달)")
    ap.add_argument("--once", action="store_true", help="한 번만 판정하고 종료")
    a = ap.parse_args()

    cfg = load_config(a.config)
    thr, window = cfg["threshold"], cfg["window"]

    print("=" * 72)
    print(" 실시간 정체 선제 판정")
    print(f"  기준     : 임계 {thr} · {window}분 이동평균  (학습 {cfg['train_span']})")
    print(f"  입력     : {a.input}")
    print(f"  출력     : {out_path(a.out, datetime.now())}")
    print(f"  예측     : 직전 {a.context}분 → 앞 {a.horizon}분 · 경보문턱 {a.p_on}")
    print("=" * 72)

    fc = Forecaster(a.model, a.device)
    if fc.pipe is None:
        print(f"⚠ Chronos-2 로드 실패 → baseline 으로 동작합니다: {fc.err}")
    else:
        print(f"모델 로드 완료: {fc.backend} ({getattr(fc, 'device', '?')})")

    st = load_state(a.state)
    hist = deque(st["history"], maxlen=a.history) if st else deque(maxlen=a.history)
    active = st["active"] if st else False
    last_ts = st["last"] if st else None
    if hist:
        print(f"이전 상태 복원: 이력 {len(hist)}분, 마지막 {last_ts}")

    print("\n시각    반송시간  이동평균  판정")
    print("-" * 72)

    while True:
        try:
            rows = read_snapshot(a.input)
        except Exception as e:
            print(f"  입력 오류: {e}", file=sys.stderr)
            if a.once:
                return 1
            time.sleep(a.interval)
            continue

        # 새 시각만 이력에 추가 (수집기 윈도우가 겹치므로 중복 제거)
        known = {t for t, _ in hist}
        added = 0
        for t, v in rows:
            if t not in known:
                hist.append((t, v))
                known.add(t)
                added += 1
        if added:
            hist = deque(sorted(hist, key=lambda x: x[0]), maxlen=a.history)

        newest = rows[-1][0]
        stamp = newest.strftime("%Y-%m-%d %H:%M:%S")
        if stamp == last_ts and not a.once:
            time.sleep(2)                      # 아직 갱신 전 — 잠깐 뒤 재확인
            continue

        stage, prob, lead, sm_now, reason, active = judge(
            list(hist), cfg, fc, a.horizon, a.context, a.p_on, a.p_off, active)

        raw_now = rows[-1][1]
        mark = STAGE_MARK[stage]
        name = STAGE_NAME[stage]
        extra = ""
        if stage == 2:
            extra = f" — 약 {lead}분 뒤 임계 초과 예상 (확률 {prob:.2f})"
        elif stage == 1:
            extra = f" (확률 {prob:.2f})"
        elif stage == 3:
            extra = f" (이동평균 {sm_now:.2f})"
        rawtxt = "  --" if raw_now is None else f"{raw_now:6.2f}"
        print(f"{newest:%H:%M}  {rawtxt}  {sm_now:8.2f}  {mark}{name}{extra}",
              flush=True)

        append_result(out_path(a.out, newest), [
            stamp, "" if raw_now is None else raw_now, round(sm_now, 3),
            stage, name, round(prob, 3), lead if lead is not None else "",
            thr, reason,
        ])

        if stage >= 2 and a.on_alert:
            env = dict(os.environ,
                       ALERT_TIME=stamp, ALERT_STAGE=str(stage),
                       ALERT_PROB=f"{prob:.3f}",
                       ALERT_LEAD=str(lead or ""),
                       ALERT_SMOOTHED=f"{sm_now:.3f}",
                       ALERT_THRESHOLD=str(thr), ALERT_REASON=reason)
            try:
                subprocess.Popen(a.on_alert, shell=True, env=env)
            except Exception as e:
                print(f"  (경보 훅 실패: {e})", file=sys.stderr)

        last_ts = stamp
        save_state(a.state, list(hist), active, last_ts)

        if a.once:
            return 0

        # 다음 분 00초 + offset 까지 대기
        now = time.time()
        wait = a.interval - (now % a.interval) + a.offset
        if wait > a.interval:
            wait -= a.interval
        time.sleep(max(1.0, wait))


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print("\n중단됨")
