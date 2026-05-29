# hubroom_predictor.py 구조 설명

> 3단계 데드락 룰베이스 실시간 예측기 — 설계 문서

---

## 1. 전체 흐름

```
┌─────────────────────────┐
│ aws_idc_realtime_collector.py │  ← 매분 00초, 73컬럼 수집
└──────────────┬──────────┘
               │ 덮어쓰기
               ▼
   ./predict/M16A_HUBROOM_PR.csv   ← 과거 90분 슬라이딩 윈도우
               │
               │ 매분 05초 읽음 (5초 offset)
               ▼
┌─────────────────────────┐
│  hubroom_predictor.py    │  ← 본 스크립트
│                          │
│  1) CSV 마지막 행 1개 신규 추출   │
│  2) 윈도우(deque)에 push          │
│  3) 4개 룰 평가 (R-A', R-B, R-C', R-D) │
│  4) S1/S2/S3 단계 판정             │
│  5) FSM(IncidentTracker)로 사건 추적 │
│  6) CSV 2종 append                 │
└──────────────┬──────────┘
               ▼
   ./predict_tobe/
     YYYYMMDD_발동이벤트.csv      ← 매분 1행 (이벤트 없는 분도 기록)
     YYYYMMDD_사건단위.csv        ← S3 종료 시점에 1건
```

---

## 2. 핵심 컴포넌트

### 2.1 데이터 윈도우 (deque)
- `WINDOW_MIN = 90` (90분치 보관)
- 4개 윈도우 동시 유지:
  | 윈도우 | 내용 |
  |---|---|
  | `t1_window` | 1분 평균 반송시간 (`.QUE.TIME.AVGTOTALTIME1MIN`) |
  | `m14_window` | M14→M16 큐 (`.QUE.M14TOM16.MESCURRENTQCNT`) |
  | `lft_window` | 10개 리프터 dict (`6ABL6011~0122`) |
  | `v3_window` | M14B/M14 OHT/PKT/WT 등 보강 dict |

### 2.2 룰 4종

#### R-A' (반송시간 룰)
```
TH_RA_VALUE = 9.0          # 1MIN >= 9분 임계
ra_trig = 최근 10분창 중 1회 이상 ≥9분
ra_sustained = 최근 5분창 중 ≥6분이 3회 이상  (보조)
ra_count = 최근 10분창 중 ≥9분 횟수
```

#### R-B (M14→M16 큐 급증)
```
TH_RB_DIFF_30 = 100        # 30분간 +100 이상
TH_RB_DIFF_10 = 30         # 10분간 +30 이상 (fast)
rb_diff = m14[-1] - m14[-31]   # 30분차
rb_diff_10 = m14[-1] - m14[-11] # 10분차
rb_trig = rb_diff >= 100
rb_fast = rb_diff_10 >= 30
```

#### R-C' (리프터 역증가)
```
TH_RC_REVERSE = 2          # 2개 이상 역증가
20분 전 대비 현재:
  rc_trend = 현재합 - 20분전합  (음수면 전체 감소)
  rev_count = 개별 리프터 중 증가한 개수
  rc_trig = (rc_trend < 0) AND (rev_count >= 2)
```

#### R-D (FAB 저장률)
```
TH_RD_FABSTORAGE = 25.0    # 25% 이상
rd_trig = STRATE.ALL.FABSTORAGERATIO >= 25%
```

### 2.3 단계 판정

```python
S1 = (ra_count >= 2) OR ra_sustained               # 조기경보
S2 = rb_trig OR rb_fast                            # 주의보
S3 = ra_trig AND rc_trig AND (rb_trig OR rd_trig)  # ⭐ 확정 (데드락)
```

---

## 3. 사건 추적 FSM (`IncidentTracker`)

상태 2개: `IDLE` / `IN_INCIDENT`

```
   ┌──── IDLE ────┐
   │      │       │
   │  S3 발동      │  (S3 없으면 그대로 IDLE)
   │      ▼       │
   │ IN_INCIDENT  │ ← 새 사건 시작 (_start_new)
   │      │       │
   │  S3 지속      │ ← 사건 갱신 (_update_current)
   │      │       │
   │  S3 끊긴 후 10분 경과
   │      ▼       │
   └──── 사건 종료 (_end_current) ───┘
```

### 사건 객체 구조
```python
current = {
    'predict_time': ...,   # S1/S2 처음 발동 시점 (룩백 60분 내)
    'start_time': ...,     # S3 확정 시점
    'last_s3_time': ...,   # 마지막 S3 발동
    'end_time': ...,       # 종료 (last_s3 + 10분 무발동)
    'refire_count': 0,     # 재발동 횟수
    'max_1min': ...,       # 사건 중 최대 반송시간
    'max_rb_diff': ...,    # 최대 큐 증가
    'max_rev': ...,        # 최대 역증가 리프터 수
    'rev_lids_union': {...}, # 사건 동안 역증가한 리프터 IDs
    'max_rd_fabstorage': ..., # 최대 저장률
    'rd_triggered': bool,  # R-D 한 번이라도 켜졌나
}
```

---

## 4. 입력 CSV 파싱 (`iter_star_rows`)

- 인코딩 폴백: `utf-8-sig` → `utf-8` → `cp949`
- `detect_prefix()`: 헤더에서 `.QUE.ALL.CURRENTQCNT` 끝나는 컬럼 찾아서 prefix 추출 (예: `M16HUB`)
  - 다른 환경(M14A 등)에도 자동 적응
- 각 행 → `(datetime, star_dict, prefix)` 튜플로 yield
- `star_dict` 키 17개: `avgtotal1min`, `m14_to_m16`, `lft_list`(10개 dict), `fabstorage_ratio`, `m14b_*`, `m14_*`, `m16pkt_*`, `m16wt_*`

---

## 5. 출력 CSV 2종

### 5.1 `YYYYMMDD_발동이벤트.csv` — 매분 1행

| 컬럼 | 설명 |
|---|---|
| `file` | 입력 CSV 파일명 |
| `datetime` | `2026-05-26 00:00` |
| `date` / `time` | 분리 형태 |
| `stage` | 0/1/2/3 |
| `stage_name` | `이벤트없음` / `1단계 조기경보` / `2단계 주의보` / `3단계 ⭐확정` |
| `prev_stage` | 이전 단계 |
| `transition` | 예: `0→1`, `2→3` |
| `reason` | 발동 사유 텍스트 |
| `relation` | 룰별 상세 (`[R-A' Y] AVGTOTAL=9.31분 ...`) |

### 5.2 `YYYYMMDD_사건단위.csv` — S3 종료 시 1건

| 컬럼 | 설명 |
|---|---|
| `severity` | `확정` (R-B 만족) / `주의` |
| `predict_time` | 조기 인지 시점 |
| `start_time` | S3 확정 시점 |
| `end_time` | 종료 |
| `lead_min` | predict_time → start_time 차 (몇 분 먼저 인지) |
| `duration_min` | start → end 지속 |
| `refire_count` | 사건 중 S3 재발동 횟수 |
| `max_1min` / `max_m14_diff` / `max_reverse_lifters` | 사건 중 최대값 |
| `primary_cause` | 주도 룰 (R-A'/R-B/R-C') |
| `contrib_breakdown` | 각 룰 기여도 % |
| `anomaly_explanation` | 자연어 설명 |
| `early_warning` | "HH:MM 1·2단계 발동 → HH:MM 3단계 확정 (N분 먼저 인지)" |
| `relation` | 룰별 상세 |

---

## 6. 실행 모드

### Watch 모드 (실시간, 기본 추천)
```bash
python3 hubroom_predictor.py --watch
```
- 매분 `00초 + 5초` (offset)에 깨어남
- 수집기가 매분 00초에 CSV 덮어쓰는 시점과 동기
- Ctrl+C 로 안전 종료

### 일괄 모드 (백테스트 1회)
```bash
python3 hubroom_predictor.py path/to/INPUT.csv -o ./predict_tobe
```
- 입력 CSV 전체 한 번 처리
- 백테스트 / 과거 데이터 분석에 사용

### `run.py` 통합 실행
```bash
python3 run.py
```
- collector + predictor 동시 실행 (스레드)
- 0.5초 지연 후 predictor watch 시작

---

## 7. 임계값 (튜닝 포인트)

| 상수 | 기본값 | 의미 |
|---|---|---|
| `WINDOW_MIN` | 90 | 윈도우 크기 (분) |
| `TH_RA_VALUE` | 9.0 | R-A' 1MIN 임계 |
| `TH_RA_SUSTAINED_VALUE` | 6.0 | R-A' 지속 임계 |
| `TH_RA_SUSTAINED_COUNT` | 3 | R-A' 5분창 중 6분+ 횟수 |
| `TH_RB_DIFF_30` | 100 | R-B 30분차 |
| `TH_RB_DIFF_10` | 30 | R-B fast 10분차 |
| `TH_RC_REVERSE` | 2 | R-C' 역증가 최소 |
| `TH_RD_FABSTORAGE` | 25.0 | R-D 저장률 (%) |
| `INCIDENT_END_GAP_MIN` | 10 | S3 무발동 종료 갭 |
| `PREDICT_LOOKBACK_MIN` | 60 | 조기인지 룩백 |
| `SYNC_OFFSET_SEC` | 5 | 수집기 대비 offset |

→ 146일치 백테스트로 위 값들 검증·튜닝 필요.

---

## 8. 의존성

표준 라이브러리만 사용 (외부 패키지 0개).
- `csv`, `logging`, `os`, `sys`, `time`
- `collections.deque`
- `datetime`, `pathlib.Path`

---

## 9. 향후 확장 포인트

1. **임계값 외부화** — 코드에 박힌 상수 → YAML/ENV
2. **다중 영역 룰** — 현재 M16HUB 중심 → M14B/M16A 룰 추가
3. **ML 융합** — 룰 stage + ML score 결합
4. **알람 전송** — S3 확정 시 슬랙/메일 후크
5. **시각화** — 사건 timeline 차트 자동 생성
