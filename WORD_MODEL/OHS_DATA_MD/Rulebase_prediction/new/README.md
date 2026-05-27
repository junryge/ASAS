# M16 HUBROOM 통합 이벤트 예측기 (v4.1)

> **8개 FAB 영역 통합 룰베이스 정체/데드락 예측기**
> M16HUB · M14 · M14B · M16A · M16B · M16 · M16_PKT · M16_WT
> 매분 1행 데이터 처리 → 90분 슬라이딩 윈도우 → S3 확정 시 사건 자동 기록

---

## 📌 빠른 시작

```bash
# 실시간 감시 모드 (수집기 매분 동기, 5초 offset)
python3 hubroom_predictor.py --watch

# 백테스트 (일괄 처리)
python3 hubroom_predictor.py path/to/INPUT.csv -o ./predict_tobe
```

**의존성**: Python 3.7+ / 표준 라이브러리만 (외부 패키지 0개)

---

## 1. 무엇을 하는가

반도체 FAB 8개 영역의 시계열 데이터를 매분 받아서, **정체/데드락 사건이 발생하기 전에 사전 감지**합니다.

- **목적**: 정체/병목/데드락 예측 (단일 장비 Error 알람은 범위 외)
- **방법**: 5종 룰베이스 (영역별 4축 + 흐름 + SLA + Sorter + MAXCAPA)
- **출력**: 매분 발동이벤트 + 사건 단위 CSV (날짜별 자동 분할)
- **검증**: 1~5월 실제 메신저 사건과 매칭 — 5월 91% 적중, 평균 38분 사전 감지

---

## 2. 폴더 / 파일 구조

```
M16_HUBROOM_PREDICTOR/
├── hubroom_predictor.py       # 본체 (1100+ lines, 표준 라이브러리만)
├── predict/                   # 입력 (수집기가 매분 갱신)
│   └── M16A_HUBROOM_PR.csv   # 최근 90분 슬라이딩 윈도우
├── predict_tobe/              # 출력 (날짜별 자동 분할)
│   ├── YYYYMMDD_발동이벤트.csv  # 매분 1행
│   ├── YYYYMMDD_사건단위.csv    # S3 종료 시 1건 (경계 이상)
│   └── predictor.log
└── README.md                  # 본 문서
```

---

## 3. 룰베이스 구조 (Layer 1 ~ 3)

```
Layer 3: 통합 융합
   ├─ unified_risk_score (0~500)
   ├─ unified_risk_level (정상/관심/경계/주의/위험/매우위험)
   ├─ hot_area (가장 점수 높은 영역 = 발원지 추정)
   └─ propagation_chain (영역별 첫 발동 시점 정렬 = 전파 경로)
              ▲
Layer 2: 5종 룰 평가
   ① 영역별 4축    R-A'(시간) · R-B(양) · R-C'(위치) · R-D(공간) × 8영역
   ② 흐름 룰       9개 핵심 노드 (현재 / 30분평균 비율 1.5x / 2x / 3x)
   ③ SLA 룰        4분초과 RATIO/CNT (M16HUB/M14/M16A/M16B)
   ④ Sorter 룰     SORTERWAITCOUNTOVER (5영역, graceful)
   ⑤ MAXCAPA 룰    운영자 변수 6개 컬럼 감지 (★ 신규)
              ▲
Layer 1: 8 영역 원천 데이터 정규화 (265개 컬럼)
```

---

## 4. 데이터 평가 윈도우 (몇 분을 보는가)

| 룰 | 사용 윈도우 | 평가 방법 |
|---|---|---|
| R-A' (시간) | 최근 10분 + 최근 5분 | 10분 중 임계초과 1회+, 5분 중 지속 3회+ |
| R-B (30분) | 30분 전 vs 현재 | `rb_diff_30 ≥ 임계` |
| R-B fast | 10분 전 vs 현재 | `rb_diff_10 ≥ 임계` |
| R-C' (위치) | 20분 전 vs 현재 | 리프터 합 감소 + 개별 역증가 ≥ 2개 |
| R-D (공간) | 현재값 즉시 | FABSTORAGE / STB / OHTUTIL ≥ 임계 |
| 흐름 룰 | 현재 vs 30분 평균 | 비율 ≥ 1.5x/2x/3x |
| SLA | 현재 + 10분차 | RATIO ≥ 임계 또는 CNT spike +20 |
| Sorter | 현재값 즉시 | SORTERWAITCOUNTOVER ≥ 임계 |
| MAXCAPA | 현재값 즉시 | 정상값 → 임계 이하 감소 감지 |

→ **WINDOW_MIN = 90분** 보관 (가장 긴 R-B 30분차에 충분)
→ **매분 1번 평가** (`INTERVAL_SEC = 60`, `SYNC_OFFSET_SEC = 5`)

---

## 5. 위험 등급 (6단계)

| 단계 | score | 색상 | 사건단위 기록 |
|---|---|---|---|
| 정상 | 0 ~ 29 | 회색 | ❌ |
| 관심 | 30 ~ 64 | 노랑 | ❌ |
| **경계** ★ | **65 ~ 79** | **주황** | ✅ |
| **주의** | **80 ~ 149** | **빨강** | ✅ |
| **위험** | **150 ~ 249** | **진빨강** | ✅ |
| **매우위험** | **250 ~ 500** | **진빨강+굵게** | ✅ |

> "관심" 이하는 사건단위.csv에 기록 안 됨 (위양성 방어). 발동이벤트.csv 에는 전부 기록.

---

## 6. 영역별 임계값 (2026-03-24 ~ 04-30 정상분포 p95/p99 기반)

### R-A' (시간 1MIN) — 영역별 컬럼 다름!

| 영역 | 컬럼 | 임계 |
|---|---|---|
| M16HUB / M14B / M16_PKT / M16_WT | `*.QUE.TIME.AVGTOTALTIME1MIN` | 9.0 / 5.0 / 7.5 / 2.8 분 |
| M14 / M16A / M16B | `*.QUE.LOAD.AVGLOADTIME1MIN` | 3.3 / 3.2 / 3.5 분 |

### R-B (인플로 큐 변화량)

| 영역 | 컬럼 | 30분 | 10분 (fast) |
|---|---|---|---|
| M16HUB | M14TOM16.MESCURRENTQCNT | +100 | +30 |
| M14 | ALL.3F_TO_HUB_JOB | +80 | +24 |
| M14B | ALL.7F_TO_HUB_JOB | +150 | +45 |
| M16A | ALL.6F_TO_HUB_JOB | +80 | +24 |
| M16B | ALL.10F_TO_HUB_JOB | +30 | +10 |
| M16 | SFAB.SENDQUEUETOTAL | +20 | +10 |

### R-C' (M16HUB 리프터 역증가)
- `TH_RC_REVERSE = 2` (20분 전 대비 합 감소 + 개별 2대 이상 역증가)
- 대상: 6ABL6011 / 6012 / 6021 / 6022 / 6031 / 6032 / 0111 / 0112 / 0121 / 0122 (10대)

### R-D (공간)
- HUB FABSTORAGERATIO ≥ **25%**
- HUB STB.3F_STORAGE_UTIL ≥ **99%**
- 영역별 OHTUTIL ≥ **95%**

### SLA (4분초과 RATIO)
| 영역 | 임계 |
|---|---|
| M16HUB | ≥ 5% |
| M14 | ≥ 25% |
| M16A | ≥ 13% |
| M16B | ≥ 18% |

### Sorter (LOT 적체)
| 영역 | 임계 |
|---|---|
| M14 | ≥ 100 |
| M14B | ≥ 75 |
| M16A | ≥ 180 |
| M16B | ≥ 90 |
| M16HUB | ≥ 30 (graceful) |

### MAXCAPA (운영자 변수)
| 컬럼 | 정상 | 임계 |
|---|---|---|
| M16HUB.QUE.LFT.3F_LFT_MAXCAPA | 165 | ≤ 100 |
| M16HUB.QUE.LFT.3F_M14BLFT_MAXCAPA | 66 | ≤ 50 |
| M16HUB.QUE.CNV.3F_CNV_MAXCAPA | 129 | ≤ 80 |
| M14.QUE.CNV.3F_CNV_MAXCAPA | 244 | ≤ 150 |
| M16A.QUE.LFT.2F_LFT_MAXCAPA | 54 | ≤ 40 |
| M16A.QUE.LFT.6F_LFT_MAXCAPA | 149 | ≤ 100 |

---

## 7. S1/S2/S3 단계 판정

```python
unified_s1 = 어느 영역이든 R-A' OR R-A_sus 발동
unified_s2 = 어느 영역이든 R-B OR R-B_fast 발동
unified_s3 = unified_s1
             AND (어느 영역이든 R-D OR SLA OR M16HUB R-C')
             AND (unified_s2 OR 흐름룰 위험/심각)
```

`unified_risk_score (0~500)` 구성:
- 영역별 4축 점수 (영역마다 0~50점) × 8영역 = **최대 300**
- 흐름 룰 9노드 (주의 5 / 위험 15 / 심각 30) = **최대 90**
- SLA 룰 (4영역 × 5점) = **최대 20**
- Sorter 룰 (5영역 × 3점) = **최대 15**
- MAXCAPA (6컬럼 × 10점) = **최대 60**

---

## 8. 출력 CSV 정의

### `YYYYMMDD_발동이벤트.csv` (매분 1행)
| 컬럼 | 의미 |
|---|---|
| `file`, `datetime`, `date`, `time` | 시점 |
| `stage` (0~3), `stage_name`, `prev_stage`, `transition` | 단계 |
| `unified_risk_score`, `unified_risk_level` | 통합 점수/레벨 |
| `hot_area`, `affected_areas`, `propagation_chain` | 발원지/전파 |
| `flow_signals`, `maxcapa_signals` | 흐름·운영자 신호 |
| `M16HUB_score` ... `M16_WT_score` | 영역별 점수 (8개) |
| `M16HUB_signals` ... | 영역별 발동 룰 |
| `M16HUB_ra` ... `M16HUB_rb_diff30` | 영역별 핵심값 |
| `sla_*`, `sorter_*` | SLA / Sorter 값 |
| `reason` | 한 줄 요약 |

### `YYYYMMDD_사건단위.csv` (S3 종료 시 1건, score ≥ 65)
| 컬럼 | 의미 |
|---|---|
| `predict_time` | 사전 신호 처음 발동 시점 |
| `start_time` | S3 확정 시점 |
| `end_time` | 사건 종료 |
| `lead_min` | 사전 인지 시간 (예측~확정 분) |
| `duration_min` | 사건 지속 분 |
| `max_risk_score`, `max_risk_level` | 사건 중 최고 위험도 |
| `hot_area`, `affected_areas`, `propagation_chain` | 발원지/전파 |
| **`triggered_rules`** | 영역별 발동 룰 (예: M16HUB:RA+RC+RD; M14:RA_sus+SLA) |
| **`risk_factors`** | 임계 초과 컬럼-값-기준 (운영자 즉시 판단용) |
| **`maxcapa_changes`** | 사건 중 변경된 MAXCAPA 이력 |
| **`relation`** | 룰별 상세 (`[M16HUB R-A'] AVGTOTAL=9.37분 (기준 9.0분) \| ...`) |

---

## 9. 운영자 모니터링 방법

### 9.1 Excel로 즉시 위험 시점 보기

`YYYYMMDD_사건단위.csv` 열기 → 조건부 서식:
- `max_risk_level = 매우위험` : 진빨강 + 굵게
- `max_risk_level = 위험` : 빨강
- `max_risk_level = 주의` : 주황
- `max_risk_level = 경계` : 노랑

### 9.2 실시간 터미널 모니터링

**Windows PowerShell**:
```powershell
Get-Content predict_tobe\$(Get-Date -Format yyyyMMdd)_발동이벤트.csv -Wait -Tail 5 |
  Where-Object { $_ -match ',3,' }
```

**Linux/Mac**:
```bash
tail -f predict_tobe/$(date +%Y%m%d)_발동이벤트.csv | grep ',3,'
```

### 9.3 핵심 컬럼 우선순위
1. `stage = 3` → 위험 확정 (즉시 조치)
2. `unified_risk_level = 위험/매우위험` → 긴급
3. `transition` = `→3` → 사건 시작 시점
4. `hot_area` → 어느 영역부터 조치할지
5. `risk_factors` → 무엇이 임계 초과했는지
6. `affected_areas` 4개 이상 → 대형 사건

---

## 10. 검증 결과 (1월 ~ 5월 14일)

### 전체 적중률
| 항목 | 결과 |
|---|---|
| 실제 메신저 병목/데드락 사건 | **83건** |
| HIT (예측기 사건 매칭) | **57건 (68.7%)** |
| Deadlock 명시 사건 | **1/1 (100%)** ✅ |
| 평균 사전 감지 시간 | **38분 먼저** (최대 130분) |

### 월별 적중률
| 월 | 적중률 | 비고 |
|---|---|---|
| 2026-01 | **95%** | ✅ |
| 2026-02 | 60% | ⚠️ 22개 핵심 컬럼 NULL 시기 |
| 2026-03 | 42% | ❌ 3/24 까지 NULL |
| 2026-04 | 38% | ⚠️ 사건 수 적음 |
| **2026-05** | **91%** | ✅ 실 운영 환경 기준 |

### 5월 사건 분포 (총 334건, 경계 이상)
| 레벨 | 건수 |
|---|---|
| 위험 (score 150~249) | 7건 |
| 주의 (score 80~149) | 208건 |
| 경계 (score 65~79) | 119건 |

### 영역별 적중률
| 영역 | 적중률 |
|---|---|
| M14B | 71% |
| M16HUB | 70% |
| M16 | 66% |
| M16A | 62% |
| M14 | 52% |

---

## 11. 한계 / 추후 개선

### 한계
- **단일 장비 Error** (4ABLD111 Error 등) — 별도 알람 시스템 영역 (룰베이스 범위 외)
- **데이터 자체 한계** — 1~3월 22개 핵심 컬럼 NULL
- **M10A / M14분석실 / R4 / 4ALF / 6ALF** 영역 미수집

### 추후 개선
1. **장비 Error 보조 룰** (STATECNT.ABNORMAL/HTSTOP, AOTRANSDELAY) → MISS 40건 추가 적중 예상
2. **수집 SQL 보강** → 도메인 지식 완전 적용
3. **ML 융합** (계획서 Phase 3) → 90%+ 적중률 목표

---

## 12. 도메인 지식 적용 현황

| 도메인 연결 | 데이터 | 코드 반영 |
|---|---|---|
| 4-1. M14A↔HUB CNV (4AFC3201/3301) | 10개 | ✅ |
| 4-4. M14B↔HUB LFT (4ABLD) | 18개 | ✅ |
| 4-6. M16A↔HUB LFT (6ABL60) | 40개 | ✅ |
| 4-8. M16A↔M16EUV LFT (6ABL01) | 26개 | ✅ |
| 4-10. M16EUV↔M16WT WIS STK | 4개 | ⚠️ 부분 |
| 5-1. Sorter (SORTERWAITCOUNTOVER) | 9개 | ✅ |
| 5-2. M16HUB MLUD (6FIOB) | 1개 | ✅ |
| 4-2. M14A↔M10A | 0개 | ❌ 데이터 없음 |
| 4-3. M14B↔M14A (4ALF) | 0개 | ❌ 데이터 없음 |
| 4-5. M14분석실(B1F) | 0개 | ❌ 데이터 없음 |
| 4-7. M16A↔M16B (6ALF) | 0개 | ❌ 데이터 없음 |
| 4-9. M16A↔R4 | 0개 | ❌ 데이터 없음 |

→ 데이터에 있는 도메인 지식 **100% 반영**.

---

## 13. 변경 이력

### v4.1
- **6단계 위험 등급 도입**: 정상 / 관심 / **경계** / 주의 / 위험 / 매우위험
- 사건단위.csv 임계 `score ≥ 65` (관심 이하 제외)
- 5월 백테스트 334건 사건 (경계 119 + 주의 208 + 위험 7)

### v4.0
- 8영역 통합 룰베이스 (M16HUB 단독 → 8영역)
- 5종 룰 (영역별 4축 + 흐름 + SLA + Sorter + MAXCAPA)
- propagation_chain · hot_area · triggered_rules · risk_factors

### v3.1
- M16HUB 단일 영역 룰베이스 (R-A'/R-B/R-C'/R-D)
