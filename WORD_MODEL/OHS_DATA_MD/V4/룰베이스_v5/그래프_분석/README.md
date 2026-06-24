# 그래프 분석 — 발동이벤트 / 사건단위 → SVG

> 룰베이스가 매일 출력하는 발동이벤트.csv / 사건단위.csv 로 분석 그래프 생성.
> matplotlib 등 의존성 X — 표준 라이브러리만.
> Oracle DB / raw 수집기 안 거치고 **이미 적재된 CSV 만** 사용.

## 파일

| 파일 | 역할 |
|---|---|
| `raw_columns.py` | **aws_idc_realtime_collector.py 의 265 컬럼 + 룰 매핑 정리** — reason/relation → raw 풀네임 컬럼 식별 |
| `svg_lib.py` | 공통 SVG 빌더 (24h / 위험사건) — raw 풀네임 + 한글 라벨 동시 표시 |
| `발동이벤트_24h.py` | 발동이벤트.csv → 24시간 점수 추이 + 최고점 reason 발동 컬럼 그래프 |
| `위험사건_그래프.py` | 사건단위 + 발동이벤트 → 사건마다 ±60분 그래프 |
| `일괄생성.py` | 하루치 한 번에 처리 |

## 사용

### ① 발동이벤트 24h 그래프
```cmd
python 발동이벤트_24h.py predict_tobe\20260525_발동이벤트.csv -o ./out
```
→ `20260525_발동이벤트_24h.svg`

### ② 위험사건 그래프 (사건당 1개)
```cmd
python 위험사건_그래프.py predict_tobe\20260525_사건단위.csv predict_tobe\20260525_발동이벤트.csv -o ./out
```
옵션 `-l 위험` 으로 등급 필터 (기본 ≥주의).
→ `20260525_1757_위험_M16HUB.svg`, `20260525_2205_위험_M16B.svg` …

### ③ 한 번에
```cmd
python 일괄생성.py 20260525 --in ../predict_tobe -o ./out
```

## 사용 컬럼 (발동이벤트.csv 안)
- `unified_risk_score / unified_risk_level / hot_area`
- 시계열 값: `M16HUB_ra`, `M16HUB_rd_fab`, `M16HUB_stb_util`, `M16HUB_rev_count`, `sla_*`, `sorter_*`, `*_rd_oht`
- `reason` (발동이벤트) / `relation` (사건단위) 텍스트를 파싱해 어느 컬럼을 그릴지 자동 결정

## raw 컬럼 추적 (raw_columns.py)

`aws_idc_realtime_collector.py` 의 **265개 IDC 컬럼 + 8영역 룰 매핑** 을 정리.
DB 접속 없이 reason/relation 텍스트만 보고 어느 raw 풀네임 컬럼이 발동했는지 식별.

| 룰 | 영역 매핑 | 예 |
|---|---|---|
| R-A | RA_COL | M16HUB → `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` |
| R-B | RB_COL | M14 → `M14.QUE.ALL.3F_TO_HUB_JOB` |
| R-D(FAB/STB) | RD_FAB_COL / RD_STB_COL | `M16HUB.STRATE.ALL.FABSTORAGERATIO` 등 |
| R-D(OHT) | RD_OHT_COL | M16B → `M16B.QUE.OHT.OHTUTIL` |
| SLA | SLA_COL | M14 → `M14.QUE.ALL.TRANSPORT4MINOVERRATIO` |
| Sorter | SORTER_COL | M14 → `M14.SORTER.ABN.SORTERWAITCOUNTOVER` |
| R-C' (리프터 역증가) | 다중 LFT 컬럼 추세 | `M16HUB.LFT.*` (대표명) |

그래프 좌측에 `한글 친화 라벨 (단위)` + 그 아래 monospace 로 `raw 풀네임` 같이 표시.

→ raw CSV / DB 없이도 사건 ±60분 시계열 가능 (발동이벤트.csv 값 사용, 라벨만 풀네임).
