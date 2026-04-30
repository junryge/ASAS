# 📄 Hubroom_v8.3_아키텍처.md

# HUBROOM V8.3 아키텍처

> M16A 3F JOB Queue 변화량 예측 모델 — 상세 아키텍처 & 컬럼 분석

| 항목 | 값 |
|------|-----|
| 입력 컬럼 | 32개 (V7: 19 + V8: 13) |
| 생성 Feature | 222개 |
| 동시 예측 타겟 | 3개 (MIN / MAX / AVG 변화량) |
| 큰 변화 기준 | ±50 |

---

## 1. 예측 파이프라인 아키텍처

```
📡 Raw Time-Series    →    🪟 30분 시퀀스 추출    →    ⚙️ 222개 Feature 생성    →    🧠 MultiOutput XGBoost    →    📊 변화량 3개 출력
   32개 컬럼                  iloc[i-30:i]              통계/추세/모멘텀/Boolean        3개 독립 XGBRegressor          pred_min/max/avg
   1분 간격 데이터             현재값 = iloc[i-1]         복합 지표 계산                  n_estimators=250               + 병목 예측 플래그
```

### MultiOutputRegressor 구조

sklearn의 `MultiOutputRegressor`는 내부적으로 타겟 수만큼 독립 모델을 생성합니다.

- `estimators_[0]` → MIN 변화량 예측기
- `estimators_[1]` → MAX 변화량 예측기
- `estimators_[2]` → AVG 변화량 예측기

각 모델은 동일한 222개 Feature를 입력받지만, 서로 다른 패턴을 학습합니다.

---

## 2. 시퀀스 타이밍 구조

```
 ←──────── 시퀀스 30개 ────────→←───── 미래 구간 10개 ─────→
 │                              │                            │
 i-30                         i-1(현재)                    i+9(10분 후)
 │          iloc[i-30:i]        │        iloc[i:i+10]        │
```

### 타이밍 규칙

| 시점 | 인덱스 | 설명 |
|------|--------|------|
| 시퀀스 시작 | `iloc[i-30]` | 30분 전 |
| 현재값 | `iloc[i-1]` | 예측 기준 시점 |
| 미래 구간 | `iloc[i:i+10]` | i ~ i+9, 총 10개 |
| 10분 후 | `iloc[i+9]` | i-1+10 = i+9 |

> ⚠️ **절대 주의:** `iloc[i+10]`은 11분 후입니다. 10분 후는 반드시 `iloc[i+9]`를 사용해야 합니다.

### 타겟 계산

| 타겟 | 계산식 |
|------|--------|
| `change_min` | min(iloc[i:i+10]) − iloc[i-1] |
| `change_max` | max(iloc[i:i+10]) − iloc[i-1] |
| `change_avg` | mean(iloc[i:i+10]) − iloc[i-1] |

### 예측 출력

| 출력 | 의미 |
|------|------|
| `pred_min` | 현재값 + 예측 변화량(MIN). 10분 구간 내 최저점 예측 |
| `pred_max` | 현재값 + 예측 변화량(MAX). 10분 구간 내 최고점 예측 |
| `pred_avg` | 현재값 + 예측 변화량(AVG). 10분 구간 평균 수준 예측 |

---

## 3. 입력 컬럼 구성 (32개)

### V7 기존 컬럼 — 19개

#### storage (1개) — 스토리지 사용률

| 컬럼명 | 설명 |
|--------|------|
| `M16A_3F_STORAGE_UTIL` | M16A 3층 스토리지 사용률. OHT가 웨이퍼를 임시 보관하는 자동 창고의 점유율. 205 이상 위험, 207 이상 고위험 |

#### fs_storage (3개) — FS 스토리지 상세

| 컬럼명 | 설명 |
|--------|------|
| `CD_M163FSTORAGEUSE` | 현재 사용 중인 스토리지 슬롯 수. 절대량 지표 |
| `CD_M163FSTORAGETOTAL` | 전체 스토리지 슬롯 수. 잔여 용량 계산에 사용 |
| `CD_M163FSTORAGEUTIL` | 스토리지 사용률(%). 7% 이상 = 높음, 10% 이상 = 위험 |

#### hub (1개) — HUB 가용량

| 컬럼명 | 설명 |
|--------|------|
| `HUBROOMTOTAL` | HUB 가용 공간. OHT가 대기·분배되는 중앙 허브의 잔여 용량. **620 미만 = 경고, 590 미만 = 병목 경고, 550 미만 = 심각 병목. 핵심 병목 지표** |

#### cmd (2개) — 반송 명령 수

| 컬럼명 | 설명 |
|--------|------|
| `M16A_3F_CMD` | M16A 3층에서 처리 중인 반송 명령 수. 현재 처리량 지표 |
| `M16A_6F_TO_HUB_CMD` | M16A 6층 → HUB 반송 명령 수. 합산 220 미만 = 처리 부족, 200 미만 = 심각 |

#### inflow (3개) — HUB 유입량

| 컬럼명 | 설명 |
|--------|------|
| `M16A_6F_TO_HUB_JOB` | 6층 → HUB 유입 JOB 수. 주요 유입 경로 |
| `M16A_2F_TO_HUB_JOB2` | 2층 → HUB 유입 JOB 수 |
| `M14A_3F_TO_HUB_JOB2` | M14A 3층 → HUB 유입 JOB 수. 인접 건물로부터의 유입 |

#### outflow (3개) — HUB 유출량

| 컬럼명 | 설명 |
|--------|------|
| `M16A_3F_TO_M16A_6F_JOB` | 3층 → 6층 유출 JOB 수 |
| `M16A_3F_TO_M16A_2F_JOB` | 3층 → 2층 유출 JOB 수 |
| `M16A_3F_TO_M14A_3F_JOB` | 3층 → M14A 3층 유출 JOB 수. 유입-유출 차이 = net_flow |

#### maxcapa (2개) — 리프트 최대 용량

| 컬럼명 | 설명 |
|--------|------|
| `M16A_6F_LFT_MAXCAPA` | 6층 리프트 최대 처리 용량. last_value만 사용 (거의 고정) |
| `M16A_2F_LFT_MAXCAPA` | 2층 리프트 최대 처리 용량. 물리적 한계를 나타냄 |

#### que — V7 QUE (2개) — M16HUB 큐 기본

| 컬럼명 | 설명 |
|--------|------|
| `M16HUB.QUE.ALL.CURRENTQCNT` | 현재 대기 중인 큐 건수. 1200 이상 = 높음, 1400 이상 = 위험. 반송 대기열 체증 지표 |
| `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` | 최근 1분간 평균 반송 소요시간(분). 4.0 이상 = 높음, 4.5 이상 = 위험 |

---

### V8 신규 컬럼 — 13개

#### target_alt (1개) — 보완 타겟

| 컬럼명 | 설명 |
|--------|------|
| `CURRENT_M16A_3F_JOB` | 예측 타겟(`CURRENT_M16A_3F_JOB_2`)의 대체 소스. 동일 지표의 다른 수집 경로. 소스 간 차이가 이상 징후 감지에 활용됨 |

#### m16hub_que (5개) — M16HUB 큐 확장 지표

| 컬럼명 | 설명 |
|--------|------|
| `M16HUB.QUE.ALL.CURRENTQCOMPLETED` | 큐에서 완료된 반송 건수. 처리 속도 지표. 감소 시 체증 신호 |
| `M16HUB.QUE.ALL.FABTRANSJOBCNT` | FAB 간 반송 작업 수. 건물 간 이동 부하. 증가 시 HUB 부담 가중 |
| `M16HUB.QUE.TIME.AVGTOTALTIME` | 전체 평균 반송 소요시간(분). 1분 평균과 달리 누적 평균. 5.0 이상 = 높음, 6.0 이상 = 위험 |
| `M16HUB.QUE.OHT.CURRENTOHTQCNT` | 현재 OHT 대기 큐 건수. OHT 차량 대기열 길이 |
| `M16HUB.QUE.OHT.OHTUTIL` | **OHT 사용률(%). 85% 이상 = 높음, 90% 이상 = 위험. 핵심 V8 병목 지표** |

#### m16a_que (7개) — M16A 큐 상세 지표

| 컬럼명 | 설명 |
|--------|------|
| `M16A.QUE.ALL.CURRENTQCOMPLETED` | M16A 레벨 완료 건수. M16HUB와 별도의 M16A 영역 큐 |
| `M16A.QUE.ALL.CURRENTQCREATED` | M16A 레벨 신규 생성 건수. completed 대비 급증 시 체증 발생 |
| `M16A.QUE.OHT.CURRENTOHTQCNT` | M16A OHT 대기 큐 건수 |
| `M16A.QUE.OHT.OHTUTIL` | M16A OHT 사용률(%). 85% 이상 = 높음, 90% 이상 = 위험 |
| `M16A.QUE.LOAD.AVGLOADTIME1MIN` | 최근 1분 평균 로딩 시간(분). OHT가 웨이퍼를 집어 올리는 시간. 2.5 이상 = 높음, 2.8 이상 = 위험 |
| `M16A.QUE.ALL.TRANSPORT4MINOVERCNT` | **반송 4분 초과 건수. 40 이상 = 높음, 50 이상 = 위험. 핵심 지연 지표** |
| `M16A.QUE.ABN.QUETIMEDELAY` | 큐 시간 지연(이상). 정상 범위 초과 지연 건수. 1 이상 = 경고, 3 이상 = 위험 |

#### 제외 컬럼

`M16A_BR_AVG_VELOCITY`, `M14A_A_AVG_VELOCITY` (OHT 평균 속도) — 실험 결과 예측력 기여 미미하여 V8에서 제외

---

## 4. Feature 생성 상세 (222개)

### Feature 추출 전략

#### 전략 1 — Full Statistics (7개/컬럼)

적용 그룹: `cmd`, `storage`, `fs_storage`, `hub`, `que`, `target_alt`, `m16hub_que`, `m16a_que`

| Feature | 계산 |
|---------|------|
| `{col}_mean` | 30분 평균값 |
| `{col}_std` | 30분 표준편차 (변동성) |
| `{col}_max` | 30분 최대값 |
| `{col}_min` | 30분 최소값 |
| `{col}_last_value` | 가장 최근 값 (현재) |
| `{col}_last_5_mean` | 최근 5분 평균 (단기 추세) |
| `{col}_slope` | 1차 선형회귀 기울기 (추세 방향/강도) |

#### 전략 2 — Flow Summary (3개/컬럼)

적용 그룹: `inflow`, `outflow`

| Feature | 계산 |
|---------|------|
| `{col}_mean` | 30분 평균 유입/유출량 |
| `{col}_last_value` | 최근 유입/유출량 |
| `{col}_slope` | 유입/유출 추세 |

#### 전략 3 — Static Value (1개/컬럼)

적용 그룹: `maxcapa` (물리적 한계, 변화 거의 없음)

| Feature | 계산 |
|---------|------|
| `{col}_last_value` | 현재 최대 용량값 |

---

### 파생 Feature 상세

#### 🎯 타겟 기본 통계 — 11개

CURRENT_M16A_3F_JOB_2의 30분 시퀀스에서 추출

| Feature | Type | 설명 |
|---------|------|------|
| `target_mean` | float | 30분 평균값. 현재 수준의 기준선 |
| `target_std` | float | 30분 표준편차. 변동성이 클수록 급변 가능성 높음 |
| `target_max` | float | 30분 내 최대값 |
| `target_min` | float | 30분 내 최소값 |
| `target_last_value` | float | 현재값 (seq_target[-1]). 변화량 계산의 기준점 |
| `target_last_5_mean` | float | 최근 5분 평균. 직전 단기 추세 |
| `target_last_10_mean` | float | 최근 10분 평균. 중기 추세 |
| `target_slope` | float | polyfit(degree=1) 기울기. 양수 = 상승 추세, 음수 = 하락 추세 |
| `target_acceleration` | float | 모멘텀 가속도. (최근5분 평균 − 그 이전5분 평균) / 5 |
| `target_is_rising` | bool(0/1) | 상승 중 여부. 현재값 > 5분 전 값 |
| `target_rapid_rise` | bool(0/1) | 급상승 여부. 5분간 +10 이상 상승 |

#### 📦 FS Storage 특수 Feature — 5개

CD_M163F 3개 컬럼의 조합 파생

| Feature | Type | 설명 |
|---------|------|------|
| `storage_use_rate` | float | (현재 사용량 − 30분 전 사용량) / 30. 분당 스토리지 증가율 |
| `storage_remaining` | float | 전체 − 현재 사용량. 잔여 스토리지 슬롯 수 |
| `storage_util_last` | float | 현재 스토리지 사용률(%) |
| `storage_util_high` | bool(0/1) | 사용률 ≥ 7%. 높은 사용 상태 플래그 |
| `storage_util_critical` | bool(0/1) | 사용률 ≥ 10%. 위험 수준 플래그 |

#### 🏗️ HUBROOMTOTAL 특수 Feature — 5개

HUB 가용량 기반 단계별 경보

| Feature | Type | 설명 |
|---------|------|------|
| `hub_critical` | bool(0/1) | HUB < 590. 병목 임박 상태 |
| `hub_high` | bool(0/1) | HUB < 610. 고부하 상태 |
| `hub_warning` | bool(0/1) | HUB < 620. 경고 상태 |
| `hub_decrease_rate` | float | (30분 전 HUB − 현재 HUB) / 30. HUB 감소 속도 |
| `hub_storage_risk` | bool(0/1) | HUB < 610 AND 스토리지 사용률 ≥ 7%. 복합 위험 |

#### 🔗 복합 & 위험도 Feature — 10개

여러 지표 조합으로 생성되는 파생 Feature

| Feature | Type | 설명 |
|---------|------|------|
| `net_flow` | float | 유입합 − 유출합. 양수 = HUB에 물량 쌓이는 중 |
| `total_cmd` | float | CMD 합산. 현재 반송 처리량 |
| `total_cmd_low` | bool(0/1) | CMD 합산 < 220. 처리 부족 |
| `total_cmd_very_low` | bool(0/1) | CMD 합산 < 200. 심각한 처리 부족 |
| `hub_cmd_bottleneck` | bool(0/1) | HUB < 610 AND CMD < 220. HUB 포화 + 처리 부족 복합 |
| `storage_util_critical` | bool(0/1) | M16A_3F_STORAGE_UTIL ≥ 205 |
| `storage_util_high_risk` | bool(0/1) | M16A_3F_STORAGE_UTIL ≥ 207 |
| `surge_risk_score` | int(0~7) | 급증 위험도 = hub_high×3 + storage_util_critical×2 + total_cmd_low×1 + storage_util_high×1 |
| `surge_imminent` | bool(0/1) | 급증 임박: 현재값>280 AND 가속도>0.5 AND hub_high. 3개 조건 동시 충족 |

#### 📊 V7 QUE Boolean — 5개

M16HUB 큐 기본 임계값 플래그

| Feature | Type | 설명 |
|---------|------|------|
| `currentq_high` | bool | CURRENTQCNT ≥ 1200 (높음) |
| `currentq_critical` | bool | CURRENTQCNT ≥ 1400 (위험) |
| `avgtime1min_high` | bool | AVGTOTALTIME1MIN ≥ 4.0 (높음) |
| `avgtime1min_critical` | bool | AVGTOTALTIME1MIN ≥ 4.5 (위험) |
| `que_severe_bottleneck` | bool | CURRENTQCNT ≥ 1200 AND AVGTOTALTIME ≥ 4.0. V7 복합 병목 |

#### 🆕 V8 M16HUB QUE Boolean — 5개

V8에서 추가된 M16HUB 확장 플래그

| Feature | Type | 설명 |
|---------|------|------|
| `m16hub_ohtutil_high` | bool | OHTUTIL ≥ 85% (높음) |
| `m16hub_ohtutil_critical` | bool | OHTUTIL ≥ 90% (위험) |
| `m16hub_avgtime_high` | bool | AVGTOTALTIME ≥ 5.0 (높음) |
| `m16hub_avgtime_critical` | bool | AVGTOTALTIME ≥ 6.0 (위험) |
| `m16hub_severe_bottleneck` | bool | OHTUTIL ≥ 85% AND AVGTOTALTIME ≥ 5.0. V8 복합 병목 |

#### 🆕 V8 M16A QUE Boolean — 9개

V8에서 추가된 M16A 영역 상세 플래그

| Feature | Type | 설명 |
|---------|------|------|
| `m16a_ohtutil_high` | bool | M16A OHTUTIL ≥ 85% |
| `m16a_ohtutil_critical` | bool | M16A OHTUTIL ≥ 90% |
| `m16a_loadtime_high` | bool | AVGLOADTIME1MIN ≥ 2.5분 |
| `m16a_loadtime_critical` | bool | AVGLOADTIME1MIN ≥ 2.8분 |
| `m16a_transport4min_high` | bool | TRANSPORT4MINOVERCNT ≥ 40 |
| `m16a_transport4min_critical` | bool | TRANSPORT4MINOVERCNT ≥ 50 |
| `m16a_delay_warning` | bool | QUETIMEDELAY ≥ 1 |
| `m16a_delay_critical` | bool | QUETIMEDELAY ≥ 3 |
| `m16a_severe_bottleneck` | bool | OHTUTIL ≥ 85% AND TRANSPORT4MIN ≥ 40. M16A 복합 병목 |

---

## 5. 병목 예측 시스템

평가 코드에서 현재 상태 기반으로 10분 후 병목 발생을 예측합니다.

### 병목 등급

| 등급 | 조건 | 설명 |
|------|------|------|
| 🔴 심각 병목 | HUB < 550 | HUB 가용 공간 거의 소진. OHT 이동 불가 수준. 즉각 조치 필요 |
| 🟠 병목 경고 | HUB < 590 | HUB 고부하 상태. 추가 유입 시 심각 병목 전환 가능 |
| ⚠️ 반송 지연 | TRANSPORT4MIN > 40 | 4분 초과 반송이 40건 이상. 반송 시스템 과부하 |

### 복합 위험 조건

| 조건 | 결과 |
|------|------|
| HUB < 610 + TRANS > 35 | → 🟠 병목 경고 발동 |
| HUB < 610 + TRANS > 35 | → ⚠️ 반송 지연 발동 |

> 병목 예측은 현재 상태의 지표를 직접 임계값과 비교하는 **Rule-Based** 방식입니다. XGBoost 모델의 변화량 예측과는 별도로, 평가 코드에서 병목 플래그를 독립적으로 생성합니다.

---

*32 Columns → 222 Features → MultiOutput XGBoost → MIN/MAX/AVG ΔPrediction + Bottleneck Alert*
