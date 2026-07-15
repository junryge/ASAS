# HUBROOM 데드락 예측 — Chronos-Bolt 예측 + 가드레일 PoC

정적 임계값 룰(반응형)의 오탐/미탐/수작업튜닝 문제를, **시계열 예측(Chronos-Bolt)
+ forecast-to-action 가드레일**(선제형)으로 완화하는 개념검증(PoC).

> 설계 배경·근거는 [`DESIGN.md`](./DESIGN.md) 참고.
> **핵심 목표: "몇 분 전에 잡느냐" — 10분 전 / 30분 전 예측.**

---

## ⭐ 메인 파이프라인 (문서 구조 그대로)

```
[예측·Forecast]  Chronos-2          →  미래 값 분포 (q10/q50/q90)
[행동·Action]    TightLoop Sentinel →  경보단계·예비조정·center·tail·lead
```

**모델은 최신 `amazon/chronos-2`** (2025-10 공개, 120M, GIFT-Eval SOTA,
chronos-bolt 대비 90%+ 승률, **다변량·covariate zero-shot 지원**). chronos-bolt 도
같은 코드로 로드 가능(`--model amazon/chronos-bolt-base`).

**① 단변량 실행 (반송시간만, 기본):**
```bash
pip install -r requirements.txt
python3 run_chronos_sentinel.py \
    --data  M16A_HUBROOM_PR_20260601~20260630.CSV \
    --signal M16HUB.QUE.TIME.AVGTOTALTIME1MIN \
    --horizon 10 --model amazon/chronos-2 \
    --threshold 12.0 --out actions_202606.csv
```
→ "문제 예측 시각" 리스트 + 분당 액션 CSV. 지평 10분 = 오탐 적고 신뢰도 높음.

**② 다변량 실행 (고도화 — 리프터·완료량 covariate 주입):**
```bash
python3 run_chronos2_covariates.py \
    --data JUNE.CSV --horizon 10 --stride 5 \
    --threshold 12.0 --covariates auto     # EDA 선행지표 자동선택
```
→ Chronos-2 `predict_df` 로 선행지표를 예측에 반영. 30분 지평에서 특히 이득
(FINDINGS_ml고도화.md 참고).

임계 자동학습: `--train APR_MAY.CSV --pct 0.99` (학습기간 분위수로 임계 산출).
torch/chronos 미설치 시 ①은 baseline 폴백으로 파이프라인만 동작, ②는 실모델 전용.

**핵심 파일:**
| 파일 | 역할 |
|---|---|
| `run_chronos_sentinel.py` | **메인 진입점(단변량)** — Chronos-2→Sentinel, 문제예측시각 출력 |
| `run_chronos2_covariates.py` | **다변량 진입점** — Chronos-2 covariate(predict_df)로 선행지표 주입 |
| `forecaster.py` | Chronos 어댑터. Chronos2Pipeline→bolt→baseline 폴백, device 자동 |
| `sentinel.py` | **TightLoop Sentinel 행동계층** — 분포→경보·예비·center·tail (bounded·causal) |
| `requirements.txt` | 예측계층 의존성 (chronos-forecasting>=2.0, torch, pandas) |

## 그 밖의 도구

| 파일 | 역할 |
|---|---|
| `guardrail.py` | 예측 분포 → stage/위험도 (sentinel 의 초기 버전, 비교/호환용) |
| `data_loader.py` | **실 수집기 CSV 로더** (CRT_TM + 265 메트릭, null/non-finite 정규화, 날짜 슬라이스) |
| `calibrate.py` | **임계값 자동 학습** — 학습기간 정상분포(p95/p99)에서 신호별 임계 산출 |
| `run_real.py` | **실데이터 학습→평가 실행기** (Apr~May 학습 → June 평가) |
| `scenario.py` | 합성 HUBROOM 정체 시나리오 생성 (실 데이터 없을 때) |
| `run_poc.py` | 룰베이스 vs 예측+가드레일 비교 하네스 — 합성 (지평 10분/30분) |
| `DESIGN.md` | 설계 문서 |

---

## 실행

```bash
cd scientific-assistant/M16_BR_개인지식/chronos_forecast

# 10분 전 / 30분 전 예측 비교
python3 run_poc.py --seed 42 --horizons 10 30

# 개별 모듈 스모크 테스트
python3 forecaster.py
python3 guardrail.py
python3 scenario.py
```

의존성 없이(순수 파이썬 표준 라이브러리) 바로 돈다. 실 Chronos-Bolt를 쓰려면:

```bash
pip install chronos-forecasting torch   # 사내/Jetson 환경
```

설치돼 있으면 `forecaster.py`가 자동으로 `amazon/chronos-bolt-base`를 로드한다.
없으면 baseline 예측기로 폴백해 **파이프라인·가드레일·평가**는 그대로 검증된다.

---

## 실데이터 워크플로우 (Apr~May 학습 → June 평가)

```bash
# 1) 학습기간 임계 자동 학습 확인 (손임계와 비교)
python3 calibrate.py <학습CSV> 0.99

# 2) 정식: 학습기간에서 임계 학습 → 평가기간에 선제예측 vs 룰베이스
python3 run_real.py \
    --train "data/2026-04*.CSV" "data/2026-05*.CSV" \
    --eval  "data/2026-06*.CSV" \
    --signal M16HUB.QUE.TIME.AVGTOTALTIME1MIN \
    --horizons 10 30 --pct 0.99

# 샘플(하루) plumbing 데모 — 하루를 앞/뒤로 쪼갬
python3 run_real.py --sample <April1.CSV> --split "12:00" --horizons 10 30
```

**설계 원칙 (leakage 방지):**
- 임계값은 **학습기간에서만** 산출 → 평가기간에 그대로 lock.
- 예측은 **인과적**(매 분, 직전 context만) → 미래 정보 누수 없음.
- ground-truth 정체 = 평가기간에서 신호가 (학습)임계를 실제로 넘은 구간
  → "임계 넘기 전에 미리 잡았나(lead)" 를 실측.

**왜 임계 자동학습인가 (실데이터가 증명):** April 1 실측 —

| 신호 | 손임계 | 학습임계(p99) | 손임계 문제 |
|---|---|---|---|
| 반송시간 AVGTOTALTIME1MIN | 12.0 | 10.6 | 조금 높음 |
| 큐누적 MESCURRENTQCNT | 100 | 259 | **min이 107 → 항상 초과(무의미)** |
| FAB저장률 FABSTORAGERATIO | 30 | 22.5 | **max 26 → 절대 미달** |

손으로 정한 임계는 라인 분포와 어긋난다. "추천 vs v4.1 원본" 임계 두 벌을 계속
저울질하던 문제의 근본 원인 → 데이터에서 학습하면 사라진다.

---

## PoC 결과 (합성 데이터, 예시)

```
지표                     룰베이스     예측 h=10분   예측 h=30분
평균 lead(분)              11.0        15.5         20.8
≥10분 전 감지               5           5           10
≥30분 전 감지               2           3            5
오탐 분                    0           8           10
churn(전환수)             26          16           18
```

**읽는 법 (방향성만 — 절대 수치는 합성데이터라 무의미):**
- 지평(h)을 늘릴수록 **더 미리** 잡는다 → `≥30분 전 감지`가 늘어난다.
- 대가는 **오탐 분 증가** — 먼 미래일수록 불확실하기 때문. 이 균형점을 고르는 게 튜닝 포인트.
- `churn`(경보 켜졌다 꺼졌다)은 히스테리시스 덕에 룰베이스보다 항상 낮다 → 알람 피로 감소.

여러 시드에서 **lead 개선 + churn 감소** 방향은 일관됨.
baseline 예측기로도 이 정도이고, **실 Chronos-Bolt는 먼 지평(30분) 예측이 강점**이라
30분 전 감지 신뢰도는 더 좋아질 것으로 기대된다.

---

## 동작 원리 (왜 미리 잡히나)

```
룰베이스:  "지금 값 >= 임계"           → 임계 넘은 순간에야 발동 (반응형)
가드레일:  "h분 뒤 값이 임계 넘을 확률" → 넘기 전에 미리 발동 (선제형)
```

1. 매 분 최근 context를 Chronos-Bolt에 넣어 **미래 h분 q10/q50/q90** 예측 (인과적 — 미래 누수 없음).
2. 각 미래 스텝에서 **P(예측구간이 임계 초과)** 계산.
3. 확률이 켜짐임계(`p_on`)를 넘는 **가장 이른 스텝** = 선제 감지 lead.
4. 히스테리시스(켜짐/꺼짐 임계 분리)로 경계 근처 요동 억제.
5. 출력은 기존 `hubroom_predictor` 스키마와 호환 (`stage`, `unified_risk_score` 등)
   → 기존 LLM 해석기·대시보드·사건단위 로직 재사용 가능.

---

## 한계 / 다음 단계

**이 PoC의 한계:**
- 합성 데이터다. 실제 M16 raw CSV가 이 환경에 없어 파이프라인 동작·방향성만 검증.
- 이 컨테이너엔 chronos/torch 미설치 → baseline 예측기로 실행됨.
- 임계·가중치·`p_on/p_off`는 `04_임계값.md` 추천값 기반 초기값 (튜닝 대상).

**사내 인계 시 (실 데이터·실 모델):**
1. `pip install chronos-forecasting torch` → 자동으로 실모델 사용.
2. `scenario.make_series` 대신 실제 수집 CSV의 신호 컬럼을 넣는 로더 작성
   (컬럼명은 `guardrail.default_configs()` 참고 — `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` 등).
3. **Shadow 운영**: 기존 룰베이스는 그대로 두고 예측 파이프라인을 병렬 로깅
   → 실제 `lead_min` 개선 / 오탐율을 실데이터로 확인 (DESIGN.md 5장).
4. 지표가 좋으면 Hybrid → Forecast-first 로 승격.

**멀티 신호·8영역 확장:**
현재 하네스는 단일 신호 데모. `guardrail.ForecastGuardrail`는 이미 다신호를 받도록
설계돼 있어(`default_configs()`에 6개 신호 정의), 실데이터 로더만 붙이면 8영역 통합 판정으로 확장된다.
