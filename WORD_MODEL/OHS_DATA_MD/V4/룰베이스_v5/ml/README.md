# ml/ — TSPulse R1 이상탐지 파이프라인 (30분 사전예측)

> 계획서: `../ML_TSPulse_구축계획_20260701.md`
> 목표: **운영자가 메신저에 정체를 보고하기 30분 전, ML이 "이상 급증"을 미리 알림**
> 방식: TSPulse R1 = **정상만 학습**하는 이상탐지 → 평소와 다르면(급증=정체전조) 이상점수↑

---

## 0. 파이프라인 한눈에

```
raw 265컬럼 CSV                메신저 episode.csv
     │                              │
     ▼                              ▼
[1] features_31.py           [2] labels_채점지.py
   → features.csv               → labels.csv (is_normal, y_pre30)
   (핵심 31피처, 분단위)          → episodes_jam.csv (정체 56건)
     │        └──────────┬──────────┘
     ▼                   ▼
[3] tspulse_train.py  (정상구간 is_normal=1 만 학습)
   → tspulse/model + scaler.json
     │
     ▼
[4] tspulse_infer.py  (매분 과거창 → 재구성오차 → anomaly_score)
   → anomaly.csv (datetime, anomaly_score, ml_level)
     │
     ▼
[5] 검증_선행성.py  ★ Phase 3 게이트
   → 리드타임·탐지율·오경보 (정체 30분전 이상점수 올랐나?)
   통과 → TSPulse 확정 / 미달 → XGBoost 폴백
```

---

## 1. 환경 (★회사 PC — 이 원격환경은 학습 불가)

| 단계 | 필요 라이브러리 |
|---|---|
| [1][2][5] 피처·라벨·검증 | **표준 라이브러리만** (어디서든 실행) |
| [3][4] 학습·추론 | `pip install "granite-tsfm[notebooks]" torch pandas numpy scikit-learn` |

- 폐쇄망: granite-tsfm 휠 + TSPulse R1 가중치(`ibm-granite/granite-timeseries-tspulse-r1`, ~1M) 오프라인 반입.
- GPU 권장(없으면 CPU도 가능, 느림).

---

## 2. 데이터 준비

| 데이터 | 얻는 법 |
|---|---|
| raw 265 (`M16A_HUBROOM_PR_*.CSV`) | `../그래프_분석/aws_idc_일자다운로드.py 20260401 20260529` |
| 메신저 episode | `../운영로그_분석_v2/output/*_episode.csv` (이미 보유) |

> ⚠️ **2026-03-24 이전 22컬럼 NULL** → 학습구간 **2026-04-01 ~ 05-29** 만 사용.
> ⚠️ **정체 라벨(채점지)은 5/6~5/29 에만 존재** (56건). 4월은 정체 라벨 없는 순수 정상 → 학습에 유리, 채점은 5월 구간.

---

## 3. 실행 (순서대로)

```bash
RAW=./raw                       # aws_idc 로 받은 raw CSV 폴더
EP=../운영로그_분석_v2/output/20260612_065558_episode.csv
OUT=./out_ml

# [1] 핵심 31피처 추출 (표준 라이브러리)
python features_31.py --raw $RAW --start 2026-04-01 --end 2026-05-29 --out $OUT

# [2] 채점지 라벨 (정체 30분전 창 + 정상구간)
python labels_채점지.py --episode $EP --features $OUT/features.csv --lead 30 --guard 60 --out $OUT

# [3] TSPulse fine-tune (정상구간만 학습)  ★회사 PC
python tspulse_train.py --features $OUT/features.csv --labels $OUT/labels.csv \
       --context 512 --epochs 10 --out $OUT/tspulse

# [4] 매분 이상점수  ★회사 PC
python tspulse_infer.py --features $OUT/features.csv --model $OUT/tspulse \
       --labels $OUT/labels.csv --out $OUT/anomaly.csv

# [5] ★ Phase 3 선행성 검증 (핵심 게이트)
python 검증_선행성.py --anomaly $OUT/anomaly.csv --episodes $OUT/episodes_jam.csv \
       --lead 30 --look 120 --out $OUT
```

---

## 4. Phase 3 게이트 판정 (★가장 중요)

`검증_선행성.py` 콘솔 결과로 판단:

| 지표 | 통과 기준 | 미달 시 |
|---|---|---|
| 평균 리드타임 | **≥ 25분** | 피처/윈도우/임계 튜닝 → 안되면 XGBoost 폴백 |
| 탐지율 | **≥ 60%** | 위와 동일 |
| 선행성(정체 전 상승) | 명확 | **선행 안 하면 이상탐지 무의미 → 지도학습(XGBoost) 전환** |

→ **통과하면 TSPulse R1 확정.** 이후 Phase 4(XGBoost 비교) → Phase 5(운영 병행).

---

## 5. 산출물 (`out_ml/`)

| 파일 | 내용 |
|---|---|
| `features.csv` | datetime + 31피처 (분단위) |
| `labels.csv` | datetime, y_pre30(정체30분전), is_normal(정상구간), episode_id |
| `episodes_jam.csv` | 채점 대상 정체 56건 (t0, fault_type) |
| `tspulse/model/`, `scaler.json` | 학습된 모델 + 정규화 파라미터 |
| `anomaly.csv` | datetime, recon_err, anomaly_score[0~1], ml_level |
| `선행성_임계스윕.csv` | θ별 탐지율/평균리드/오경보 |
| `선행성_사건별.csv` | 사건별 리드타임/탐지여부 |

---

## 6. 핵심 원칙 (누수·오염 차단)

- **정상만 학습**: `is_normal=1` (정체 ±60분 제외) 구간만 fine-tune. 정규화 통계도 정상에서만.
- **미래정보 차단**: 추론 창은 항상 시각 t 까지의 과거만.
- **라벨은 채점지**: 정체 56건은 학습 아님(TSPulse). 검증/XGBoost 에서만 정답으로 사용.
- **룰과 병행**: `ml_level`(안전/관심/경계/위험)은 룰 50/71/85 와 **별개**. 융합은 나중.
