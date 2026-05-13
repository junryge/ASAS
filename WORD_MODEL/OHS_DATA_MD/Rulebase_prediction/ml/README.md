# ML (XGBoost) — 30분 사전 정체 예측

룰베이스를 보강하는 ML 파이프라인. **사건 발생 30분 전** 확률 점수 출력.

## 파일 구성

```
ml/
├── feature_builder.py   ← 1단계: CSV → 피처
├── train_xgboost.py     ← 2단계: 피처 + 사건 라벨 → 모델 학습
├── ml_predictor.py      ← 3단계: 모델 + 피처 → 확률 추론
├── incidents_sample.json← 검증된 사건 라벨 예시 (4건)
├── README.md            ← 본 문서
│
└── (학습 후 생성)
    ├── features.csv           ← 피처 데이터
    ├── model.json             ← XGBoost 모델
    ├── model_features.json    ← 피처명 순서
    └── model_report.txt       ← 학습 리포트
```

## 의존성

```bash
pip install xgboost pandas scikit-learn numpy
```

## 사용 흐름

### 1단계: 피처 추출
```bash
cd ml/
python3 feature_builder.py \
    --csv ../DATA/90min.csv \
    --out features.csv
```

- 90min.csv 한 줄씩 룰 평가 + 피처 생성
- 출력: 1분당 1행, 60+ 피처 컬럼

### 2단계: 모델 학습
```bash
python3 train_xgboost.py \
    --features features.csv \
    --incidents incidents_sample.json \
    --out model.json \
    --lead_min 30
```

- 라벨: t+30분이 사건 구간이면 1, 아니면 0
- 시계열 5-Fold 검증
- 출력: model.json, model_features.json, model_report.txt

### 3단계: 추론 (배치)
```bash
python3 ml_predictor.py \
    --model model.json \
    --features features.csv \
    --out predictions.csv
```

- 피처 CSV 전체에 확률 점수 부여

## ML 위험 레벨

| 점수 | 레벨 | 의미 |
|------|------|------|
| 0.00~0.29 | OK (정상) | 무시 |
| 0.30~0.69 | INFO (주의) | 모니터링 |
| 0.70~0.84 | WARNING (경보) | 사전 알람 ★ |
| 0.85~1.00 | CRITICAL (위험) | 즉시 대응 |

## 라벨 추가 방법 (운영 중)

새 사건 발생 시 `incidents_sample.json`에 추가 → 재학습:
```json
{
  "start": "2026-05-15 14:23:00",
  "end":   "2026-05-15 14:45:00",
  "desc":  "5/15 14시 정체"
}
```

매주/매월 학습 권장.

## 룰과 결합 (하이브리드)

```python
def hybrid_decision(rule_stage, ml_score):
    if rule_stage == 3:                       # 룰 사건 확정
        return '확정사건', 'CRITICAL', 0
    if rule_stage in (1, 2) and ml_score >= 0.7:
        return '사전경보', 'WARNING', 30      # 30분 lead time ★
    if rule_stage == 0 and ml_score >= 0.85:
        return '잠재위험', 'WATCH', 45
    if ml_score >= 0.3:
        return '모니터링', 'INFO', 0
    return '정상', 'OK', 0
```

## 데이터 요구사항

| 데이터 양 | 효과 |
|---|---|
| 1주 | 작동만 (불안정) |
| 1달 | 실용 시작 |
| 3달 | 안정 |
| 6달+ | 정밀 (계절성 학습) |

**최소 시작**: 1주일 정상 데이터 + 검증 사건 4건 (현재 보유).
