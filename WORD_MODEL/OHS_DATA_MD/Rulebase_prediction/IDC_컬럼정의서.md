# IDC 컬럼 정의서 (v4.1, 265개)

> **수집기(aws_idc_realtime_collector.py v4.1) 가 수집하는 265개 IDC 컬럼**
> **각 컬럼이 어느 영역을 보는지, 어느 룰에서 사용되는지, 왜 사용되는지** 정리

---

## 📊 전체 통계

| 구분 | 컬럼 수 | 비율 |
|---|---|---|
| **수집기 v4.1 수집** | **265개** | 100% |
| └ predictor v4.1 룰에서 직접 사용 | **80개** | 30% |
| └ 수집만 (ML 학습 / 추후 룰 추가 대비) | **185개** | 70% |

## 영역별 컬럼 수

| 영역 | 총 컬럼 | 룰 사용 | 비고 |
|---|---|---|---|
| **M16HUB** | 110개 | 28개 | 중심 허브 (M14↔M16 연결) |
| **M14B** | 42개 | 9개 | M14B 7F (4ABLD 리프터) |
| **M14** | 41개 | 15개 | M14A 3F (CNV로 HUB 연결) |
| **M16A** | 37개 | 11개 | M16A 6F (6ABL60 리프터로 HUB 연결) |
| **M16B** | 16개 | 6개 | M16B 10F (M16A 경유 HUB) |
| **M16** | 11개 | 3개 | SFAB 반송 (FAB 간) |
| **M16_PKT** | 4개 | 4개 | M16EUV 2F |
| **M16_WT** | 4개 | 4개 | M16WT 2F (WIS STK 연결) |

---

## 1. 컬럼 명명 규칙 (네이밍)

```
{영역}.{카테고리}.{서브}.{지표명}

예시:
  M16HUB.QUE.TIME.AVGTOTALTIME1MIN
  ──────  ───  ────  ─────────────
   영역    카테고리   서브        지표
```

### 영역 (8개)
| 영역 | 의미 | 층 |
|---|---|---|
| `M16HUB` | M16 HUB ROOM (중심 허브) | 3F |
| `M14` | M14A FAB | 3F |
| `M14B` | M14B FAB | 7F |
| `M16A` | M16A FAB | 6F (+ 2F EUV 측) |
| `M16B` | M16B FAB | 10F |
| `M16` | SFAB 반송 (FAB 간) | - |
| `M16_PKT` | M16 EUV 측 PKT | 2F |
| `M16_WT` | M16 WT (WIS STK 경유) | 2F |

### 카테고리 (주요)
| 카테고리 | 의미 |
|---|---|
| `QUE.ALL` | 전체 큐 (CURRENTQCNT, COMPLETED, CREATED 등) |
| `QUE.TIME` | 시간 지표 (AVGTOTALTIME 등) |
| `QUE.LOAD` | Load 반송 시간 (AVGLOADTIME) |
| `QUE.OHT` | OHT (차량) 관련 |
| `QUE.CNV` | 컨베이어 관련 |
| `QUE.LFT` | 리프터 관련 |
| `QUE.STB` | 스토커 임시저장 (ZFS) |
| `QUE.ABN` | 비정상 (AOTRANSDELAY, QUETIMEDELAY) |
| `QUE.SFAB` | FAB 간 반송 |
| `QUE.MLUD` | Manual Load/Unload 장치 |
| `LFT.*` | 개별 리프터 (4ABLD, 6ABL 등) |
| `CNV.*` | 컨베이어 (4AFC 등) |
| `OHT.STATECNT` | OHT 상태 (HTSTOP, CONGESTED, ABNORMAL) |
| `OHT.ALERT` | OHT 알람 (OHTMCPALARM) |
| `SORTER.ABN` | Sorter 비정상 (WAITCOUNT, TRANSFERFAIL) |
| `STRATE` | 저장률 |

### 지표 (주요)
| 지표 | 의미 |
|---|---|
| `CURRENTQCNT` | 현재 큐 수 |
| `CURRENTQCOMPLETED` | 최근 10분 완료 |
| `CURRENTQCREATED` | 최근 10분 생성 |
| `AVGTOTALTIME` | 10분 평균 반송시간 |
| `AVGTOTALTIME1MIN` | 1분 평균 반송시간 ★ |
| `AVGLOADTIME` | 10분 평균 Load 시간 |
| `AVGLOADTIME1MIN` | 1분 평균 Load 시간 ★ |
| `OHTUTIL` | OHT 사용률 (%) |
| `FABSTORAGERATIO` | FAB 저장률 (%) |
| `TRANSPORT4MINOVERCNT` | 4분 이상 반송 COUNT |
| `TRANSPORT4MINOVERRATIO` | 4분 이상 반송 RATIO (%) |
| `MESCURRENTQCNT` | MES 기준 현재 큐 |
| `JOB` / `JOB_ALT` | HUB 입/출 JOB (ALT=우회) |
| `CMD` | 진행중 OHT 명령 |
| `MAXCAPA` | 최대 수용량 ★★ (운영자 변수) |

---

## 2. 영역별 핵심 컬럼 (predictor v4.1 룰 사용 80개)

### 🎯 M16HUB (중심 허브) — 28개 룰 사용 / 110개 수집

#### 🔴 R-A' (시간) — 1개
| 컬럼 | 임계 | 목적 |
|---|---|---|
| `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` | ≥9.0분 | HUB 정체 시간 핵심 지표 |

#### 🔴 R-B (양 / 인플로) — 1개
| 컬럼 | 임계 | 목적 |
|---|---|---|
| `M16HUB.QUE.M14TOM16.MESCURRENTQCNT` | +100/30분 | M14→M16 인플로 폭증 |

#### 🔴 R-C' (위치 / 리프터 역증가) — 10개
| 컬럼 (10개 모두) | 용도 |
|---|---|
| `M16HUB.LFT.6ABL6011.TOTAL_CURRENTQCNT` | M16A 6F 연결 LFT 큐 |
| `M16HUB.LFT.6ABL6012.TOTAL_CURRENTQCNT` | M16A 6F 연결 |
| `M16HUB.LFT.6ABL6021.TOTAL_CURRENTQCNT` | M16A 6F 연결 |
| `M16HUB.LFT.6ABL6022.TOTAL_CURRENTQCNT` | M16A 6F 연결 |
| `M16HUB.LFT.6ABL6031.TOTAL_CURRENTQCNT` | M16A 6F 연결 |
| `M16HUB.LFT.6ABL6032.TOTAL_CURRENTQCNT` | M16A 6F 연결 |
| `M16HUB.LFT.6ABL0111.TOTAL_CURRENTQCNT` | M16EUV 2F 연결 |
| `M16HUB.LFT.6ABL0112.TOTAL_CURRENTQCNT` | M16EUV 2F 연결 |
| `M16HUB.LFT.6ABL0121.TOTAL_CURRENTQCNT` | M16EUV 2F 연결 |
| `M16HUB.LFT.6ABL0122.TOTAL_CURRENTQCNT` | M16EUV 2F 연결 |

→ 20분 전 대비 합 감소 + 개별 리프터 2대 이상 역증가 시 발동

#### 🔴 R-D (공간) — 3개
| 컬럼 | 임계 | 목적 |
|---|---|---|
| `M16HUB.STRATE.ALL.FABSTORAGERATIO` | ≥25% | FAB 저장률 |
| `M16HUB.STRATE.STB.3F_STORAGE_UTIL` | ≥99% | STB 저장 사용률 |
| `M16HUB.QUE.OHT.OHTUTIL` | ≥95% | OHT 가동률 |

#### 🟡 흐름 룰 — 2개
| 컬럼 | 노드 |
|---|---|
| `M16HUB.QUE.OHT.CURRENTOHTQCNT` | `HUB_OHT_QCNT` (현재 OHT 적체) |
| `M16HUB.QUE.M14TOM16.MESCURRENTQCNT` | `M14_TO_M16` (M14 인플로 흐름) |

#### 🟢 SLA — 2개
| 컬럼 | 임계 |
|---|---|
| `M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO` | ≥5% |
| `M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT` | 10분 +20 spike |

#### 🟢 Sorter (graceful) — 1개
- `M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER` (DB에 없으면 자동 스킵)

#### ⭐ MAXCAPA 운영자 변수 — 3개
| 컬럼 | 정상 | 감지 |
|---|---|---|
| `M16HUB.QUE.LFT.3F_LFT_MAXCAPA` | 165 | ≤100 |
| `M16HUB.QUE.LFT.3F_M14BLFT_MAXCAPA` | 66 | ≤50 |
| `M16HUB.QUE.CNV.3F_CNV_MAXCAPA` | 129 | ≤80 |

#### 🟢 HUB 출구 — 5개 (대시보드 표시용)
- `M16HUB.QUE.ALL.3F_TO_M16A_6F_JOB`
- `M16HUB.QUE.ALL.3F_TO_M16A_2F_JOB`
- `M16HUB.QUE.ALL.3F_TO_M14A_3F_JOB`
- `M16HUB.QUE.ALL.3F_TO_M14B_7F_JOB`
- `M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB`

#### 🔵 ML 피처 — 1개
- `M16HUB.OHT.ALERT.OHTMCPALARMCNT`
- `M16HUB.QUE.ABN.AOTRANSDELAY`

---

### 🎯 M14 (M14A 3F) — 15개 룰 사용 / 41개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M14.QUE.LOAD.AVGLOADTIME1MIN` | ≥3.3분 |
| R-B + 흐름룰 | `M14.QUE.ALL.3F_TO_HUB_JOB` | +80/30분 |
| R-C' (CNV 쏠림) | `M14.QUE.CNV.M14ATONORTHCURRENTQCNT` | 70% 쏠림 |
| R-C' (CNV 쏠림) | `M14.QUE.CNV.M14ATOSOUTHCURRENTQCNT` | 70% 쏠림 |
| R-D | `M14.QUE.OHT.OHTUTIL` | ≥95% |
| SLA | `M14.QUE.ALL.TRANSPORT4MINOVERRATIO` | ≥25% |
| SLA | `M14.QUE.ALL.TRANSPORT4MINOVERCNT` | spike |
| Sorter | `M14.SORTER.ABN.SORTERWAITCOUNTOVER` | ≥100 |
| 흐름룰 ★ | `M14.QUE.CNV.M14ATOM16ACURRNETQCNT` | 2.PNG 최대 병목 |
| MAXCAPA | `M14.QUE.CNV.3F_CNV_MAXCAPA` | 정상 244 → ≤150 |
| ML 피처 | `M14.QUE.ALL.3F_TO_HUB_JOB_ALT` | 우회 |
| ML 피처 | `M14.QUE.OHT.3F_TO_HUB_CMD` | 진행중 |
| ML 피처 | `M14.OHT.STATECNT.HTSTOP` | 차량 정지 |
| ML 피처 | `M14.OHT.STATECNT.CONGESTED` | 차량 정체 |
| ML 피처 | `M14.OHT.STATECNT.ABNORMAL` | 차량 이상 |

---

### 🎯 M14B (M14B 7F) — 9개 룰 사용 / 42개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M14B.QUE.TIME.AVGTOTALTIME1MIN` | ≥5.0분 |
| R-B + 흐름룰 | `M14B.QUE.ALL.7F_TO_HUB_JOB` | +150/30분 |
| R-D | `M14B.QUE.OHT.OHTUTIL` | ≥95% |
| R-D 보조 | `M14B.QUE.ALL.7F_TO_HUB_JOB_ALT` | 우회 |
| Sorter | `M14B.SORTER.ABN.SORTERWAITCOUNTOVER` | ≥75 |
| 흐름룰 ★ | `M14B.LFT.4ABLD122.TOTAL_CURRENTQCNT` | 2.PNG 1.69x |
| ML 피처 | `M14B.QUE.OHT.7F_TO_HUB_CMD` | 진행중 |
| ML 피처 | `M14B.QUE.ABN.AOTRANSDELAY` | 장비 출구 |
| ML 피처 | `M14B.OHT.ALERT.OHTMCPALARMCNT` | 알람 |

---

### 🎯 M16A (M16A 6F + 2F) — 11개 룰 사용 / 37개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M16A.QUE.LOAD.AVGLOADTIME1MIN` | ≥3.2분 |
| R-B + 흐름룰 | `M16A.QUE.ALL.6F_TO_HUB_JOB` | +80/30분 |
| 흐름룰 | `M16A.QUE.ALL.2F_TO_HUB_JOB` | EUV 측 인플로 |
| R-D | `M16A.QUE.OHT.OHTUTIL` | ≥95% |
| SLA | `M16A.QUE.ALL.TRANSPORT4MINOVERRATIO` | ≥13% |
| SLA | `M16A.QUE.ALL.TRANSPORT4MINOVERCNT` | spike |
| Sorter | `M16A.SORTER.ABN.SORTERWAITCOUNTOVER` | ≥180 |
| Sorter (graceful) | `M16A.SORTER.ABN.SORTERTRANSFERFAIL` | ≥1 |
| MAXCAPA | `M16A.QUE.LFT.2F_LFT_MAXCAPA` | 정상 54 → ≤40 |
| MAXCAPA | `M16A.QUE.LFT.6F_LFT_MAXCAPA` | 정상 149 → ≤100 |
| ML 피처 | `M16A.QUE.OHT.{2F,6F}_TO_HUB_CMD` | 진행중 |

---

### 🎯 M16B (M16B 10F) — 6개 룰 사용 / 16개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M16B.QUE.LOAD.AVGLOADTIME1MIN` | ≥3.5분 |
| R-B + 흐름룰 | `M16B.QUE.ALL.10F_TO_HUB_JOB` | +30/30분 |
| R-D | `M16B.QUE.OHT.OHTUTIL` | ≥95% |
| SLA | `M16B.QUE.ALL.TRANSPORT4MINOVERRATIO` | ≥18% |
| Sorter | `M16B.SORTER.ABN.SORTERWAITCOUNTOVER` | ≥90 |
| Sorter (graceful) | `M16B.SORTER.ABN.SORTERTRANSFERFAIL` | ≥1 |

---

### 🎯 M16 (SFAB 반송) — 3개 룰 사용 / 11개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-B | `M16.QUE.SFAB.SENDQUEUETOTAL` | +20/30분 |
| 피처 | `M16.QUE.SFAB.RECEIVEQUEUETOTAL` | RECV 큐 |
| 피처 | `M16.QUE.SFAB.RETURNQUEUETOTAL` | RETURN 큐 |

---

### 🎯 M16_PKT (M16EUV 2F) — 4개 룰 사용 / 4개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M16_PKT.QUE.TIME.AVGTOTALTIME1MIN` | ≥7.5분 |
| R-D | `M16_PKT.QUE.OHT.OHTUTIL` | ≥95% |
| ML 피처 | `M16_PKT.QUE.ABN.AOTRANSDELAY` | 장비 출구 |
| ML 피처 | `M16_PKT.OHT.ALERT.OHTMCPALARMCNT` | 알람 |

---

### 🎯 M16_WT (M16WT 2F) — 4개 룰 사용 / 4개 수집

| 룰 | 컬럼 | 임계 |
|---|---|---|
| R-A' | `M16_WT.QUE.TIME.AVGTOTALTIME1MIN` | ≥2.8분 |
| R-D | `M16_WT.QUE.OHT.OHTUTIL` | ≥95% |
| ML 피처 | `M16_WT.QUE.ABN.AOTRANSDELAY` | 장비 출구 |
| ML 피처 | `M16_WT.OHT.ALERT.OHTMCPALARMCNT` | 알람 |

---

## 3. "수집만" 컬럼 185개 — 왜 수집하나?

> predictor v4.1 룰에서는 직접 사용하지 않지만 다음 목적으로 미리 수집:

### 3.1 추후 룰 추가 대비
- 단일 리프터 방향별 (3F→6F, 6F→3F 등) 80개 컬럼 → R-C' 정밀화 가능
- 4ABLD 6대 × 방향 12개 → M14B R-C' 신설 가능

### 3.2 ML 학습 데이터셋
- 계획서 Phase 3 ML 모델 학습 시 필요 (피처 200개+ 목표)
- 현재 80개 → ML 학습 후 200개+ 활용 가능

### 3.3 도메인 분석/디버깅
- `QUE.ALL.CURRENTQCNT` (영역별) — 전체 큐 추이
- `QUE.ALL.CURRENTQCOMPLETED` — 처리량
- `QUE.ALL.CURRENTQCREATED` — 생성량
- CNV 시간 지표 (`NORTHCNVTOM14TIME` 등) — 컨베이어 분석

---

## 4. 도메인 지식 매핑 (FAB 연결)

| 연결 | 컬럼 | 룰 |
|---|---|---|
| 4-1. M14A↔HUB CNV (4AFC3201/3301) | `M14.QUE.CNV.*` (10개) | M14 흐름룰 |
| 4-4. M14B↔HUB LFT (4ABLD) | `M14B.LFT.4ABLD*` (18개) | M14B 흐름룰 |
| 4-6. M16A↔HUB LFT (6ABL60) | `M16HUB.LFT.6ABL60*` (40개) | M16HUB R-C' |
| 4-8. M16A↔M16EUV LFT (6ABL01) | `M16HUB.LFT.6ABL01*` (24개) | M16HUB R-C' |
| 4-10. M16EUV↔M16WT WIS STK | `M16.CNV.SENDFAB.TO_M16WT_*` | 피처 |
| 5-1. Sorter | `*.SORTER.ABN.SORTERWAITCOUNTOVER` (9개) | Sorter 룰 |
| 5-2. M16HUB MLUD | `M16HUB.QUE.*.MLUD.*` | HUB 출구 |

❌ 데이터 자체 없음 (수집 SQL에 미포함):
- 4-2. M14A↔M10A (M10A 컬럼 0개)
- 4-3. M14B↔M14A 4ALF (4ALF 컬럼 0개)
- 4-5. M14분석실 B1F (0개)
- 4-7. M16A↔M16B 6ALF (0개)
- 4-9. M16A↔R4 (R4 컬럼 0개)

---

## 5. 사용 예시 (predictor 코드 참조)

### 예: M16HUB R-A' (시간 룰)
```python
# hubroom_predictor.py
RA_COL = {
    'M16HUB': 'M16HUB.QUE.TIME.AVGTOTALTIME1MIN',
    ...
}
TH_RA = {'M16HUB': 9.0, ...}

# 평가
ra_value = row.get(RA_COL['M16HUB'])  # 1분 평균 반송시간
if ra_value >= TH_RA['M16HUB']:  # ≥9.0분
    out['ra_trig'] = True
```

### 예: 흐름 룰 (M14_CNV_TO_HUB — 2.PNG 최대 병목)
```python
FLOW_NODES = {
    'M14_CNV_TO_HUB': ('M14', 'M14.QUE.CNV.M14ATOM16ACURRNETQCNT'),
    ...
}

# 현재 vs 30분 평균 비율
ratio = current / avg30
if ratio >= 2.0:  # 2x 위험
    level = '위험'
```

### 예: MAXCAPA 운영자 변수
```python
MAXCAPA_NORMAL = {
    'M16HUB.QUE.LFT.3F_LFT_MAXCAPA': (165, 100),  # (정상, 임계)
    ...
}

# 평가
val = row.get('M16HUB.QUE.LFT.3F_LFT_MAXCAPA')
if val <= 100:  # 운영자가 165→100 이하로 줄였음
    out['maxcapa_changed'].append('운영자 조치 감지')
```

---

## 6. 컬럼 추가/삭제 절차

### 컬럼 추가
1. `aws_idc_realtime_collector.py` 의 `IDC_COLUMNS` 리스트에 추가
2. (predictor 룰 사용 원할 시) `hubroom_predictor.py` 의 매핑 딕셔너리 (RA_COL, RB_COL 등) 에 추가
3. 본 정의서에 추가

### 컬럼 제거
- 수집 부담 줄이려면 `IDC_COLUMNS` 에서 제거 (단, predictor 룰 사용 컬럼은 제거 금지)

---



---

*작성: 2026-05-27*
*기준: hubroom_predictor.py v4.1 + aws_idc_realtime_collector.py v4.1*
