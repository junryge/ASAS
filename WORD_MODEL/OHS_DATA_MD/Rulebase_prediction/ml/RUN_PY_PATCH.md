# run.py 에 ML 예측기 추가하기

기존 `run.py` (수집기 + 예측기) **그대로 두고** ML 예측기 1개 스레드만 추가.

## 1. 폴더 구조 (사용자 환경 가정)

```
ML학습하기/
├── run.py                          ← 여기에 ML 예측기 스레드 추가
├── aws_idc_realtime_collector.py   ← 기존 (수집기)
├── hubroom_predictor.py            ← 기존 (예측기)
├── 3DO_PRETIME.py                  ← 룰 엔진 (이름 변경됨)
├── feature_builder.py              ← ml.zip
├── ml_predictor.py                 ← ml.zip
├── ml_predict_runner.py            ← ml.zip ★ 신규
├── model.json                      ← 학습 결과
├── model_features.json             ← 학습 결과
├── predict/
│   └── M16_HUBROOM_PR.csv          ← 1분마다 갱신되는 입력
└── ml_predict/                     ← 자동 생성 (날짜별 출력)
    ├── 20260513_predictions.csv
    └── 20260514_predictions.csv
```

## 2. run.py 수정 (기존 코드 그대로 + 3줄 추가)

```python
# -*- coding: utf-8 -*-
"""
M16A HUBROOM 수집 + 예측 + ML 예측 동시 실행
- 수집기 스레드 시작 (백그라운드 데몬)
- 0.5초 뒤 예측기 watch 시작 (메인)
- ML 예측기 스레드 시작 (백그라운드 데몬)  ★ 신규
- Ctrl+C 한 번으로 같이 종료
"""

import threading
import time

import aws_idc_realtime_collector as collector
import hubroom_predictor as predictor
import ml_predict_runner as ml_runner          # ★ 추가

# 수집기 (백그라운드 데몬 — 메인 종료 시 같이 죽음)
threading.Thread(target=collector.main, daemon=True).start()

# ML 예측기 (백그라운드 데몬) ★ 추가
threading.Thread(target=ml_runner.run_watch, daemon=True).start()

# 0.5초 후 예측기 watch (메인 스레드)
time.sleep(0.5)

out_dir = predictor.DEFAULT_OUTPUT_DIR
out_dir.mkdir(parents=True, exist_ok=True)
logger = predictor.setup_logger(out_dir)
predictor.run_watch(predictor.DEFAULT_INPUT_CSV, out_dir, logger)
```

**변경 사항 (3줄만 추가)**:
1. `import ml_predict_runner as ml_runner`
2. `threading.Thread(target=ml_runner.run_watch, daemon=True).start()`

## 3. 동작 흐름

```
[수집기]   AWS IDC → predict/M16_HUBROOM_PR.csv (1분마다 갱신)
                ↓
[예측기]   기존 예측 처리 (룰 기반 등)
                ↓
[ML 예측기 ★] M16_HUBROOM_PR.csv 1분 폴링
                ↓
                매 분: 90분 윈도우 → 피처 → ML → 30분 후 확률
                ↓
            ml_predict/20260513_predictions.csv (append)
            ml_predict/20260514_predictions.csv (다음 날)
```

## 4. 출력 예시 (`ml_predict/20260513_predictions.csv`)

```csv
datetime,prediction_for,ml_score,ml_level,ml_level_kr,rule_s1,rule_s2,rule_s3
2026-05-13 14:00:00,2026-05-13 14:30:00,0.1234,OK,정상,0,0,0
2026-05-13 14:01:00,2026-05-13 14:31:00,0.1456,OK,정상,0,0,0
2026-05-13 14:02:00,2026-05-13 14:32:00,0.4523,INFO,주의,1,0,0
2026-05-13 14:03:00,2026-05-13 14:33:00,0.7821,WARNING,경보,1,0,0  ← ★ 30분 후 정체 예측
...
```

## 5. 화면 로그 (콘솔)

ML 예측기 시작 시:
```
🤖 ML 예측기 시작
   입력: predict/M16_HUBROOM_PR.csv
   출력: ml_predict
   모델: model.json
   폴링: 60초
```

경보/위험만 로그:
```
  [14:03] 경보 score=0.782 → 30분 뒤(14:33) 정체 예상  [20260513_predictions.csv]
  [14:08] 위험 score=0.891 → 30분 뒤(14:38) 정체 예상  [20260513_predictions.csv]
```

(정상은 CSV에만 기록, 콘솔은 깔끔하게)

## 6. 단독 실행도 가능

run.py 안 거치고 ML 예측기만 돌리고 싶으면:
```cmd
python ml_predict_runner.py
```

또는 경로 지정:
```cmd
python ml_predict_runner.py --input predict\M16_HUBROOM_PR.csv --out_dir ml_predict --model model.json --interval 60
```

## 7. 종료

`Ctrl+C` 한 번이면 수집기/예측기/ML 예측기 다 같이 종료 (daemon=True).
