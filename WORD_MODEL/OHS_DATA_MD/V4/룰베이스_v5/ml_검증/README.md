# ML 검증 — TabPFN v2 vs XGBoost (30분 사전 예측)

> 메신저 정체 라벨로 "운영자 인지 30분 전 ML 예측"이 학습 가능한지 검증.
> 2026 최신 **TabPFN v2**(소량라벨 SOTA) 와 **XGBoost**(검증된 베이스) 비교.

## 사전 검증 결과 (이 환경, 라이브러리 없이 라벨만)

| 항목 | 값 |
|---|---|
| 메신저 정체 라벨 | **56건** (정체/병목 30 · 브릿지 12 · 리프터 8 · CNV 5 · MLUD 1) |
| 분포 | 20일 (2026-05-06~05-29) |
| 30분 윈도우 양성률 | 5.1% (불균형 19:1) |
| 판정 | 56건은 적음 → **TabPFN v2(소량강점) 유리**, XGBoost는 scale_pos_weight 필수 |

→ 라벨이 적은 게 TabPFN v2 에 유리. 두 모델 비교가 타당.

## 실행 (★ 회사 PC 전용 — 이 환경엔 라이브러리/데이터 없음)

```bash
pip install tabpfn xgboost scikit-learn pandas numpy   # TabPFN v2 는 GPU 권장

python ml_검증_TabPFN_vs_XGB.py \
    --features features_all.csv \
    --episodes 20260612_065558_episode.csv \
    --lead_min 30 --out ./out_검증
```

### 입력
| 인자 | 내용 |
|---|---|
| `--features` | 피처 원천 CSV — **발동이벤트.csv 들을 합친 것**(datetime + 수치컬럼) 또는 raw 265 |
| `--episodes` | 메신저 `*_episode.csv` (라벨 원천) |
| `--lead_min` | 사전예측 분 (기본 30) |
| `--only` | `both`(기본) / `xgb` / `tabpfn` |

### 출력
- `검증_비교.csv` — TabPFN vs XGBoost: **PR-AUC / ROC-AUC / 평균리드타임 / 탐지율**
- `xgb_feature_importance.csv` — XGBoost 피처 중요도 top30

## 평가 지표 (정확도 X — 불균형이라 거짓말)
| 지표 | 목표 |
|---|---|
| PR-AUC (test) | ≥ 0.4 |
| 평균 리드타임 | ≥ 25분 |
| 탐지율 | ≥ 60% |

## 핵심 설계 (누수 차단)
- 피처는 **시각 t 까지만** (롤링/델타 모두 과거). 라벨은 t+1~t+lead.
- **시간 분할** train(70%)→val(15%)→test(15%), 랜덤 금지.
- 룰 점수(`*_score`)는 기본 제외 — 룰 흉내 방지. `--only` 로 포함 비교 가능.

## 다음 단계
1. 회사 PC 에서 발동이벤트 56일치 합쳐 `features_all.csv` 생성
2. 이 스크립트로 TabPFN vs XGBoost 검증 → 승자 채택
3. 승자로 본 학습 파이프라인(`ml_runner`) 구축
