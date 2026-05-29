# ML v4.1 학습/운영 사용법

> 회사 PC 에서 처음부터 다시 할 때 이 문서 그대로 따라가면 됨.
> 폴더 위치: `Rulebase_prediction/` 한 곳에서 모든 명령 실행.

---

## 전체 흐름

```
[1] 백테스트         → predict_tobe/*_발동이벤트.csv
[2] 메신저 라벨     → incidents_B_messenger.json
[3] 피처            → features_v41.csv
[4] 학습 (3 모델)   → model_v41_10m/20m/30m.json
[5] 평가            → 사건 탐지율 / 위양성 확인
[6] 운영            → run_ml.py 실행 (실시간)
```

---

## [1] 룰베이스 백테스트 (~20분)

```cmd
python hubroom_predictor.py AWS_IDC_DATA_HIS_202601.csv -o ./predict_tobe
```

**출력**: `predict_tobe/{YYYYMMDD}_발동이벤트.csv` 146개 + `_사건단위.csv`

**전제**: `config.json` 의 `enabled: false` (Logpresso 적재 OFF — 백테스트 모드)

**검증**:
```cmd
dir predict_tobe\*_발동이벤트.csv
```

---

## [2] 운영자 메신저 → 사건 라벨 B (~1분)

### 2-1. 메신저 텍스트 → CSV
```cmd
python 운영로그_파서.py masame.txt 운영로그.csv
```

→ 약 1,476건 추출. 그중 사건성 (DEADLOCK/BRIDGE/MLUD/Q_OVER) 약 129건.

### 2-2. CSV → 사건 JSON
```cmd
python messenger_to_incidents.py --csv 운영로그.csv --out incidents_B_messenger.json
```

→ 60분 클러스터링 후 **약 71건 사건** 라벨 생성.

**검증**:
```cmd
python -c "import json; print(f'{len(json.load(open(\"incidents_B_messenger.json\")))} 건')"
```

---

## [3] 피처 빌더 (~10분)

```cmd
python feature_builder_v41.py --raw AWS_IDC_DATA_HIS_202601.csv --events_dir predict_tobe --out features_v41.csv --from 2026-03-24 --to 2026-05-31
```

**옵션 의미**:
- `--from 2026-03-24`: 1~3월 22컬럼 NULL 회피 (이 이전 데이터는 신뢰도 ↓)
- `--to 2026-05-31`: 학습 데이터 종료일

**출력**: `features_v41.csv` (약 92,045행 × 728컬럼)

**검증**:
```
✅ 92,045행 × 728컬럼 → features_v41.csv
   raw 현재값: ~265
   sliding 통계+delta: ~432
   event 룰 컨텍스트: ~30
```

---

## [4] XGBoost 학습 (3 모델, 각 ~10~15분)

```cmd
python train_xgboost.py --features features_v41.csv --incidents incidents_B_messenger.json --out model_v41_10m.json --lead_min 10
python train_xgboost.py --features features_v41.csv --incidents incidents_B_messenger.json --out model_v41_20m.json --lead_min 20
python train_xgboost.py --features features_v41.csv --incidents incidents_B_messenger.json --out model_v41_30m.json --lead_min 30
```

**출력** (각 모델당):
- `model_v41_*.json` — XGBoost 모델
- `model_v41_*_features.json` — 피처 순서
- `model_v41_*_report.txt` — 학습 리포트 (PR-AUC, 피처 중요도 등)

**기대 지표**:
- PR-AUC ≥ 0.99 (in-sample)
- ROC-AUC ≥ 0.99
- F1 ≥ 0.90
- 피처 중요도 top 1 < 30% (leakage 방지)

---

## [5] 평가 — 3 모델 비교

```cmd
python evaluate.py --features features_v41.csv --model model_v41_10m.json --incidents incidents_B_messenger.json --threshold 0.7 --lookback 30
python evaluate.py --features features_v41.csv --model model_v41_20m.json --incidents incidents_B_messenger.json --threshold 0.7 --lookback 50
python evaluate.py --features features_v41.csv --model model_v41_30m.json --incidents incidents_B_messenger.json --threshold 0.7 --lookback 60
```

**인자**:
- `--threshold 0.7`: 경보 임계 (score ≥ 0.7 → 위험)
- `--lookback`: 사건 시작 N분 전부터 검사 (lead_min × 2 권장)

**기대 결과** (참고치 — 이전 실행 결과):
| 지표 | 10분 | 20분 | 30분 ⭐ |
|---|---|---|---|
| 탐지율 | 36/37 | 36/37 | **37/37** ★ |
| 놓친 사건 | 1건 | 1건 | **0건** ★ |
| 위양성 | 4분 | 11분 | **4분** ★ |
| 최대 사전인지 | 0분 | 0분 | **28분** ★ |

→ **30분 모델이 가장 좋음**. 운영 메인 사용.

> [1~34] 사건이 "사건 전 데이터 없음" 으로 표시되는 건 정상.
> `--from 2026-03-24` 로 그 이전 데이터를 제외했기 때문 (NULL 컬럼 회피).

---

## [6] 실시간 운영

### 6-1. 모델 파일 같은 폴더에 (이미 있으면 OK)
```cmd
dir model_v41_10m.json model_v41_30m.json
```

> 운영은 10분/30분 2개 모델만 사용 (`ml_predict_runner_v41.py`).
> 20분은 평가 비교용으로만 학습.

### 6-2. config.json 운영 모드
```json
{
  "enabled": true,
  "ml_enabled": true,
  "table_name": "test_table3",
  "ml_table_name": "test_table4"
}
```

### 6-3. 운영 시작
```cmd
python run_ml.py
```

→ **3 스레드 자동 시작**:
1. 수집기 (`aws_idc_realtime_collector.py`)
2. 룰베이스 (`hubroom_predictor.py`)
3. ML (`ml_predict_runner_v41.py`) — 10/30 모델 자동 로드

### 6-4. 출력
| 파일 | 매분 내용 |
|---|---|
| `predict_tobe/{YYYYMMDD}_발동이벤트.csv` | 룰베이스 50컬럼 |
| `predict_tobe/{YYYYMMDD}_사건단위.csv` | S3 사건 (score≥65) |
| `ml_predict/{YYYYMMDD}_predictions.csv` | ML score 10/30분 |
| Logpresso `test_table3` | 룰 적재 (file=Rule_system) |
| Logpresso `test_table4` | ML 적재 (file=ML_system) |

### 6-5. 종료
`Ctrl+C` 한 번 — 3 스레드 같이 종료.

---

## 트러블슈팅

### A. `PermissionError: ...발동이벤트.csv`
원인: Excel 등으로 csv 열어둠 / 다른 Python 중복 실행
해결:
- Excel 닫기
- `tasklist | findstr python` → 다른 프로세스 죽이기
- `hubroom_predictor.py` 의 `append_rows_csv` 가 10회 자동 재시도 (이미 패치됨)

### B. `Logpresso HTTP 400`
원인: 백테스트 중 Logpresso 켜져 있음
해결: `config.json` 의 `enabled: false` 로 변경

### C. `ModuleNotFoundError: No module named 'ml_predictor'`
원인: `ml_predictor.py` 가 같은 폴더에 없음
해결: 같은 폴더 (`Rulebase_prediction/`) 에 두기

### D. `1월~3월 사건 전 데이터 없음`
정상 — `--from 2026-03-24` 옵션 때문에 그 이전은 피처 없음.
무시 OK.

### E. 학습 너무 오래 걸림
정상 — 5-fold CV + 최종학습 = 6번 학습 (모델당 ~10분).
빠르게 하려면 `train_xgboost.py` 의 `n_splits=5 → 2`, `n_estimators=300 → 100` 으로 변경.

---

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `hubroom_predictor.py` | 룰베이스 v4.1 — 발동이벤트.csv 생성 |
| `운영로그_파서.py` | 메신저 txt → CSV |
| `messenger_to_incidents.py` | CSV → 사건 라벨 JSON |
| `feature_builder_v41.py` | 피처 (raw + 발동이벤트 join) |
| `train_xgboost.py` | XGBoost 학습 |
| `evaluate.py` | 평가 (사건 탐지율, 위양성) |
| `ml_predict_runner_v41.py` | 실시간 ML 추론 (운영용) |
| `run_ml.py` | 운영 시작 (3 스레드) |
| `Rule_LO.py` | 룰베이스 Logpresso 적재 |
| `ML_LO.py` | ML Logpresso 적재 |

---

## 권장 운영 SOP (1주일 후)

1. 매일 `ml_predict/{YYYYMMDD}_predictions.csv` 확인
2. `ml_score_30m ≥ 0.7` 시점에 실제 사건 있었는지 점검
3. 새 사건 운영자 인지 시 → `masame.txt` 에 추가
4. 1개월 후 → 누적 사건으로 재학습 (`train_xgboost.py` 재실행)
5. 모델 드리프트 감지 시 → PR-AUC 모니터링

---

## 임계 튜닝 (선택)

`ml_predictor.py` 의 `level()` 함수:
- WARNING: 0.70 (기본)
- CRITICAL: 0.85 (기본)

위양성 너무 많으면 → 0.75 / 0.90 으로 상향
탐지율 너무 낮으면 → 0.60 / 0.80 으로 하향

---

*작성일: 2026-05-28*
*ML v4.1 (XGBoost binary classification) + 룰베이스 v4.1 통합 운영*
