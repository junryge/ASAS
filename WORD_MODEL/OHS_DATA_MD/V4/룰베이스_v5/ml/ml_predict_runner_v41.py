#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ml_predict_runner_v41 — ML 실시간 예측기 (Chronos-2 판)
# ============================================================================
# 기존 v4.1(XGBoost 2모델: model_v41_10m/30m.json + feature_builder_v41)을
# Chronos-2 zero-shot 예측(ml_v2)으로 갈아끼운 것이다.
#
# 룰베이스(run_ml.py)와 프로세스를 분리해 이 파일을 단독 실행한다.
#   chronos-forecasting / torch 가 별도 파이썬에 설치돼 있어 같은 프로세스로는
#   import 가 안 되기 때문이다. 창 두 개를 띄워 각각 돌린다.
#
#       (룰베이스)  python run_ml.py
#       (ML)        <chronos 파이썬> ml_predict_runner_v41.py     ← 이 파일
#
#   두 프로세스는 파일로만 만난다 — 서로 import 하지 않는다.
#       읽기 : predict/M16A_HUBROOM_PR.csv   (수집기가 매분 갱신)
#       쓰기 : ml_predict/{YYYYMMDD}_predictions.csv
#   룰베이스의 발동이벤트.csv 는 건드리지 않는다.
#
# ── 무엇이 바뀌었나 ─────────────────────────────────────────────
#   전                                  후
#   피처 31개 + 발동이벤트 join          M16HUB 반송시간 1개 (10분 이동평균)
#   XGBoost 2모델(10m/30m) 학습          Chronos-2 zero-shot (가중치 학습 없음)
#   모델 model_v41_*.json               model_config.json (임계·통계만)
#   점수 = 모델 출력                     점수 = P(이동평균이 임계를 넘음)
#
#   ※ 발동이벤트.csv 는 더 이상 입력으로 쓰지 않는다. Chronos-2 는 타깃
#     시계열만으로 예측한다(단변량 zero-shot). 룰베이스와 입력이 분리되어
#     서로 영향을 주지 않는다 — 두 판정을 독립적으로 비교할 수 있다.
#
# ── 필요한 것 ──────────────────────────────────────────────────
#   같은 폴더(또는 ./ml_v2, ../ml_v2)에  data.py · detect.py
#   model_config.json          학습 산출물 (임계 14.765 등)
#   chronos_2/                 모델 폴더 (config.json, model.safetensors …)
#   pip install "chronos-forecasting>=2.0" torch
#
# ── 출력 ───────────────────────────────────────────────────────
#   ml_predict/{YYYYMMDD}_predictions.csv   (매분 1행 append — 경로·이름 그대로)
#   Logpresso test_table4                   (ML_LO 있으면)
#
#   앞 7칸은 기존 헤더 그대로라 다운스트림이 안 깨진다. 뒤에 Chronos 고유
#   정보를 덧붙였다.
#     datetime, prediction_for_10m, prediction_for_30m,
#     ml_score_10m, ml_score_30m, ml_level_10m, ml_level_30m,
#     raw_value, smoothed, threshold, stage, stage_name, lead_min, reason, backend
#
#   ml_score_10m = 앞으로 10분 안에 임계를 넘을 확률 (지평 1~10분 최대)
#   ml_score_30m = 앞으로 30분 안에 임계를 넘을 확률 (지평 1~30분 최대)
#   → 누적 확률이라 30m >= 10m 이 항상 성립한다.
#
# ── 실행 ───────────────────────────────────────────────────────
#   python ml_predict_runner_v41.py                     계속 실행 (매분 판정)
#   python ml_predict_runner_v41.py --once              한 번만 (점검용)
#   python ml_predict_runner_v41.py --model D:\모델\chronos_2 --device cuda
#
#   윈도우면 배치파일로 두면 편하다 (run_chronos.bat):
#       @echo off
#       D:\python311\python.exe "%~dp0ml_predict_runner_v41.py"
#       pause
#
# ── 정상 기동 확인 ─────────────────────────────────────────────
#   ✅ 모델 로드: backend=chronos_2      ← 이게 떠야 실모델
#   ⚠ Chronos-2 로드 실패 …             ← 뜨면 baseline (--model 경로 확인)
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# ── ml_v2 모듈(data.py · detect.py) 찾기 ────────────────────────
for _cand in (_HERE, _HERE / 'ml_v2', _HERE.parent / 'ml_v2', _HERE.parent):
    if (_cand / 'detect.py').exists() and (_cand / 'data.py').exists():
        sys.path.insert(0, str(_cand))
        break
try:
    from data import load_config, moving_avg, TARGET
    from detect import Forecaster, exceed_prob
except ImportError as e:
    raise SystemExit(
        f'❌ ml_v2 모듈을 못 찾음: {e}\n'
        f'   data.py 와 detect.py 를 {_HERE} 또는 그 아래 ml_v2/ 에 두세요.')


# ============================================================
# 기본 경로 (run_ml.py 에서 override 가능)
# ============================================================
BASE_DIR = _HERE

DEFAULT_INPUT_CSV  = BASE_DIR / 'predict' / 'M16A_HUBROOM_PR.csv'
DEFAULT_OUTPUT_DIR = _HERE / 'ml_predict'
DEFAULT_CONFIG     = _HERE / 'model_config.json'
DEFAULT_MODEL      = 'chronos_2'
DEFAULT_STATE      = _HERE / 'ml_runner_state.json'
DEFAULT_INTERVAL   = 60
SYNC_OFFSET_SEC    = 10        # 룰베이스(05초) 다음 5초

HORIZON = 30                   # 앞 30분 예측 (10m/30m 점수를 여기서 뽑는다)
CONTEXT = 90                   # 직전 90분 입력 — 수집기 WINDOW_MIN 과 일치
P_ON    = 0.30                 # 선제경보 문턱 (HANDOVER 권고값)
P_OFF   = 0.20                 # 히스테리시스 해제 문턱

# 확률 → 등급 (기존 ml_level_* 칸에 그대로 들어간다)
LEVEL_BANDS = [(0.60, '위험'), (P_ON, '경계')]

STAGE_NAME = {0: '정상', 1: '관찰', 2: '선제경보', 3: '진행중'}


# ============================================================
# 출력 헤더 — 앞 7칸은 기존과 동일 (다운스트림 호환)
# ============================================================
OUT_HEADER = [
    'datetime',
    'prediction_for_10m', 'prediction_for_30m',
    'ml_score_10m', 'ml_score_30m',
    'ml_level_10m', 'ml_level_30m',
    # ↓ Chronos-2 고유 정보
    'raw_value', 'smoothed', 'threshold',
    'stage', 'stage_name', 'lead_min', 'reason', 'backend',
]


def level_of(p):
    for th, name in LEVEL_BANDS:
        if p >= th:
            return name
    return ''


# ============================================================
# 입력 — 수집기 스냅샷 (90분 · 분당 1행)
# ============================================================
def read_snapshot(path, retries=5, delay=0.4):
    """수집기가 쓰는 중일 수 있어 몇 번 재시도한다. → [(datetime, value)]"""
    last_err = None
    for _ in range(retries):
        try:
            with open(path, encoding='utf-8-sig', newline='') as f:
                rd = csv.DictReader(f)
                out = []
                for row in rd:
                    ts = (row.get('CRT_TM') or '').strip()
                    if not ts:
                        continue
                    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                        try:
                            t = datetime.strptime(ts, fmt)
                            break
                        except ValueError:
                            t = None
                    if t is None:
                        continue
                    v = (row.get(TARGET) or '').strip()
                    try:
                        out.append((t, float(v)))
                    except ValueError:
                        out.append((t, None))
            if out:
                out.sort(key=lambda x: x[0])
                return out
        except Exception as e:
            last_err = e
        time.sleep(delay)
    if last_err:
        raise last_err
    return []


# ============================================================
# 상태 (재시작해도 이동평균·히스테리시스가 안 끊기게)
# ============================================================
def load_state(path):
    import json
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        hist = [(datetime.strptime(t, '%Y-%m-%d %H:%M:%S'), v)
                for t, v in d.get('history', [])]
        return hist, bool(d.get('active')), d.get('last')
    except Exception:
        return [], False, None


def save_state(path, history, active, last, keep=600):
    import json, tempfile
    h = history[-keep:]
    d = {'history': [[t.strftime('%Y-%m-%d %H:%M:%S'), v] for t, v in h],
         'active': bool(active), 'last': last}
    tmp = str(path) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, path)


def merge_history(history, snapshot, keep=600):
    """스냅샷을 이력에 합친다(같은 시각은 새 값으로 덮어씀)."""
    m = {t: v for t, v in history}
    m.update({t: v for t, v in snapshot})
    return sorted(m.items())[-keep:]


# ============================================================
# 판정 — 한 분
# ============================================================
def judge(history, cfg, fc, active):
    """→ dict(점수·등급·단계…) · active"""
    thr = cfg['threshold']
    window = cfg.get('window', 10)

    filled, last = [], None
    for _, v in history:
        if v is not None:
            last = v
        filled.append(last if last is not None else 0.0)
    sm = moving_avg(filled, window)
    cur = sm[-1]
    raw = history[-1][1]

    # 이미 임계 초과 — 예측할 것도 없이 진행중
    if cur >= thr:
        return dict(stage=3, p10=1.0, p30=1.0, lead=None, smoothed=cur, raw=raw,
                    reason=f'이동평균 {cur:.2f} ≥ 임계 {thr}'), True

    ctx = sm[-CONTEXT:]
    if len(ctx) < 15:
        return dict(stage=0, p10=0.0, p30=0.0, lead=None, smoothed=cur, raw=raw,
                    reason=f'이력 부족 ({len(ctx)}분)'), False

    f = fc.predict([ctx], HORIZON)[0]
    probs = [exceed_prob(f['q10'][h], f['q50'][h], f['q90'][h], thr)
             for h in range(HORIZON)]

    p10 = max(probs[:10]) if probs else 0.0      # 10분 안에 넘을 확률
    p30 = max(probs) if probs else 0.0           # 30분 안에 넘을 확률
    lead = next((h + 1 for h, p in enumerate(probs) if p >= P_ON), None)

    if p30 >= P_ON:
        active = True
    elif p30 < P_OFF:
        active = False

    if active and lead is not None:
        stage, reason = 2, f'약 {lead}분 뒤 임계 초과 예상 (확률 {p30:.2f})'
    elif p30 >= P_OFF:
        stage, reason = 1, f'상승 조짐 (확률 {p30:.2f})'
    else:
        stage, reason = 0, '정상'

    return dict(stage=stage, p10=p10, p30=p30, lead=lead, smoothed=cur, raw=raw,
                reason=reason), active


def build_row(t, j, cfg, backend):
    return {
        'datetime': t.strftime('%Y-%m-%d %H:%M:%S'),
        'prediction_for_10m': (t + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
        'prediction_for_30m': (t + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
        'ml_score_10m': f'{j["p10"]:.4f}',
        'ml_score_30m': f'{j["p30"]:.4f}',
        'ml_level_10m': level_of(j['p10']),
        'ml_level_30m': level_of(j['p30']),
        'raw_value': '' if j['raw'] is None else f'{j["raw"]:.3f}',
        'smoothed': f'{j["smoothed"]:.3f}',
        'threshold': cfg['threshold'],
        'stage': j['stage'],
        'stage_name': STAGE_NAME.get(j['stage'], ''),
        'lead_min': '' if j['lead'] is None else j['lead'],
        'reason': j['reason'],
        'backend': backend,
    }


# ============================================================
# CSV append (날짜별 자동 분할 — 데이터 시각 기준)
# ============================================================
def append_pred_row(out_dir, row):
    ymd = row['datetime'][:10].replace('-', '')
    path = Path(out_dir) / f'{ymd}_predictions.csv'
    new_file = not path.exists() or path.stat().st_size == 0
    with open(path, 'a', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_HEADER)
        if new_file:
            w.writeheader()
        w.writerow(row)
    return path


def sleep_until_next_minute(offset_sec=SYNC_OFFSET_SEC):
    now = time.time()
    wait = (60 - now % 60) + offset_sec
    if wait > 60:
        wait -= 60
    if wait < 0.05:
        wait += 60
    time.sleep(wait)


# ============================================================
# 외부 API — run_watch (run_ml.py 스레드 진입점)
# ============================================================
def run_watch(input_csv=None, events_dir=None, out_dir=None,
              config=None, model=None, device=None,
              state=None, interval=DEFAULT_INTERVAL, once=False,
              # 예전 인자 — 받기만 하고 쓰지 않는다 (호출부 호환)
              model_10m=None, model_30m=None):
    input_csv = Path(input_csv or DEFAULT_INPUT_CSV)
    out_dir   = Path(out_dir or DEFAULT_OUTPUT_DIR)
    cfg_path  = Path(config or DEFAULT_CONFIG)
    state_p   = Path(state or DEFAULT_STATE)
    model     = model or DEFAULT_MODEL
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg):
        print(f'[ML_v41 {datetime.now():%H:%M:%S}] {msg}')

    if events_dir:
        _log('ℹ 발동이벤트는 Chronos-2 판에서 입력으로 쓰지 않습니다 (인자 무시)')

    try:
        cfg = load_config(str(cfg_path))
    except Exception as e:
        _log(f'❌ model_config 로드 실패: {cfg_path} — {e}')
        return

    _log('=' * 60)
    _log('🤖 ML 예측기 v4.1 (Chronos-2) 시작')
    _log(f'  입력   : {input_csv}')
    _log(f'  출력   : {out_dir}')
    _log(f'  설정   : {cfg_path}')
    _log(f'  타깃   : {cfg.get("target", TARGET)}')
    _log(f'  임계   : {cfg["threshold"]}  ({cfg.get("window",10)}분 이동평균)')
    _log(f'  학습   : {cfg.get("train_span","?")}')
    _log(f'  예측   : 직전 {CONTEXT}분 → 앞 {HORIZON}분 · 경보문턱 {P_ON}')
    _log('=' * 60)

    fc = Forecaster(model, device)          # 기동 시 1회만 로드
    if fc.pipe is None:
        _log('=' * 60)
        _log(f'⚠ Chronos-2 로드 실패 → baseline 으로 동작합니다: {fc.err}')
        _log('  이 결과는 Chronos-2 성적이 아닙니다. --model 경로를 확인하세요.')
        _log('=' * 60)
    else:
        _log(f'✅ 모델 로드: backend={fc.backend} · device={getattr(fc,"device","?")}')

    # Logpresso 적재 (선택 — 없으면 CSV 만)
    ML_LO = None
    try:
        sys.path.insert(0, str(BASE_DIR))
        import ML_LO as _lo
        _lo.start()
        ML_LO = _lo
        _log('✅ ML_LO 활성화')
    except Exception as e:
        _log(f'⚠ ML_LO 로드 실패 (CSV 적재만): {e}')

    history, active, last = load_state(state_p)
    if history:
        _log(f'  이력 복원 {len(history)}분 · 마지막 {last}')

    try:
        while True:
            t0 = time.time()
            try:
                snap = read_snapshot(str(input_csv))
                if not snap:
                    _log(f'⚠ 입력 비었음: {input_csv}')
                else:
                    history = merge_history(history, snap)
                    t_now = history[-1][0]
                    key = t_now.strftime('%Y-%m-%d %H:%M:%S')
                    if key == last:
                        _log(f'  미갱신 ({key}) — 건너뜀')
                    else:
                        j, active = judge(history, cfg, fc, active)
                        row = build_row(t_now, j, cfg, fc.backend)
                        path = append_pred_row(out_dir, row)
                        if ML_LO is not None:
                            try:
                                ML_LO.upload(OUT_HEADER, [row[k] for k in OUT_HEADER])
                            except Exception as e:
                                _log(f'  ML_LO 적재 오류: {e}')
                        last = key
                        save_state(state_p, history, active, last)
                        mark = '⚠' if j['stage'] >= 2 else ' '
                        _log(f'{mark} {key} 10m={row["ml_score_10m"]} '
                             f'30m={row["ml_score_30m"]} '
                             f'[{STAGE_NAME.get(j["stage"],"")}] {j["reason"]} → {path.name}')
            except Exception as e:
                _log(f'  ❌ 사이클 오류: {type(e).__name__}: {e}')

            if once:
                return
            _log(f'  cycle {time.time()-t0:.2f}s')
            sleep_until_next_minute(SYNC_OFFSET_SEC)

    except KeyboardInterrupt:
        _log('사용자 중단 (Ctrl+C)')
        if ML_LO is not None:
            try:
                ML_LO.stop()
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default=str(DEFAULT_INPUT_CSV))
    p.add_argument('--out_dir', default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument('--config', default=str(DEFAULT_CONFIG))
    p.add_argument('--model', default=DEFAULT_MODEL, help='chronos_2 폴더 경로')
    p.add_argument('--device', default=None, help='cuda / cpu (생략시 자동)')
    p.add_argument('--state', default=str(DEFAULT_STATE))
    p.add_argument('--interval', type=int, default=DEFAULT_INTERVAL)
    p.add_argument('--once', action='store_true', help='한 번만 판정하고 종료')
    a = p.parse_args()
    run_watch(input_csv=a.input, out_dir=a.out_dir, config=a.config,
              model=a.model, device=a.device, state=a.state,
              interval=a.interval, once=a.once)


if __name__ == '__main__':
    main()
