# OHS 분석 산출물 설명서

> 작성일: 2026-04-15
> 목적: 1차 분석에서 생성된 모든 MD/PY 파일 설명 및 2차 분석 활용 가이드

---

## 1. 파일 전체 목록

### PY 코드 (3개)

| 파일 | 용도 | 실행 방법 |
|------|------|----------|
| `analyze_oht_xsohs.py` | M14_OHT 단독 분석 | `python OHS/analyze_oht_xsohs.py` |
| `analyze_combined.py` | 1차 결합 분석 (4개 데이터 통합 → 리포트 자동 생성) | `python OHS/analyze_combined.py` |
| `analyze_phase1_inject.py` | 1차 스타/로그프레소 데이터 주입 분석 | `python OHS/analyze_phase1_inject.py` |

### MD 문서 (6개)

| 파일 | 내용 | 대상 |
|------|------|------|
| `OHT_UDP_ANALYSIS_REPORT.md` | M14_OHT 단독 분석 리포트 (11개 섹션) | 내부 |
| `CSV_ANALYSIS_METHOD.md` | CSV 데이터 구조 + 필드 매핑 + 분석 방법론 | 내부 |
| `OHT_1차_결합분석_리포트.md` | 4개 데이터 결합 분석 결과 (11개 섹션) | 내부 |
| `OHT_DIJKSTRA_ARCHITECTURE.md` | Dijkstra 경로 최적화 아키텍처 설명 | 내부 |
| `OHT_WORLD_MODEL_FEASIBILITY.md` | 월드 모델 예측 가능성 기술 평가 | 내부 |
| `OHT_예측모델_검토보고서.md` | 고객 보고용 예측 모델 검토 보고서 | **고객** |

### 데이터 (4개 소스)

| 데이터 | 파일 | 출처 | 건수 |
|--------|------|------|------|
| M14_OHT | `OHT_UDP_extracted/raw.csv` | OHT_UDP (스타) | 534,540건 |
| 스타 | `OHT_컬럼수집_DATA.CSV` | 스타 | 510건 |
| HID_INOUT | `LOGPRESSO_extracted/M14A_ATLAS_HID_INOUT_*.csv` | 로그프레소 | 342,570건 |
| RAIL_CUT | `LOGPRESSO_extracted/ATLAS_OHT_RAIL_CUT_*.csv` | 로그프레소 | 16건 |

---

## 2. PY 코드 상세

### 2.1 analyze_oht_xsohs.py

**M14_OHT(VHL_STATE_REPORT) 단독 분석 스크립트**

```bash
# 기본 실행 (기본 경로 사용)
python OHS/analyze_oht_xsohs.py

# 경로 지정
python OHS/analyze_oht_xsohs.py [CSV경로] [출력리포트경로]
```

- 입력: M14_OHT raw.csv
- 출력: `OHT_UDP_ANALYSIS_REPORT.md`
- 분석 항목: 데이터 개요, Fleet 현황, 차량 상태, 가동률/적재율, 속도, 운반 사이클, 스테이션, 시간대별 패턴, 이상 상태, IN_SERVICE, 월드 모델 파라미터
- 외부 패키지 불필요 (표준 라이브러리만 사용)

### 2.2 analyze_combined.py

**4개 데이터 결합 분석 → 리포트 자동 생성**

```bash
python OHS/analyze_combined.py
```

- 입력: M14_OHT + 스타 + HID_INOUT + RAIL_CUT (4개)
- 출력: `OHT_1차_결합분석_리포트.md`
- 분석 항목 (11개 섹션):
  1. 데이터 개요
  2. 스타 운영 지표 추이
  3. M14_OHT + 스타 결합 (큐 vs VHL 상태 상관)
  4. HID 구간 흐름 (통과량, 속도, 저속 구간)
  5. HID + 스타 결합 (큐 vs HID 속도 상관)
  6. RAIL_CUT 분석
  7. 월드 모델 파라미터
  8. **병목 여부 자동 판단**
  9. **예측 가능 여부 자동 판단**
  10. 2차 분석 방향
  11. 데이터 출처 및 코드 안내

파일 경로 변경 시 `__main__` 블록 수정:
```python
if __name__ == '__main__':
    generate_report(
        m14_path='OHS/OHT_UDP_extracted/raw.csv',
        quwa_path='OHS/OHT_컬럼수집_DATA.CSV',
        hid_path='OHS/LOGPRESSO_extracted/M14A_ATLAS_HID_INOUT_202604140830_1700.csv',
        rail_path='OHS/LOGPRESSO_extracted/ATLAS_OHT_RAIL_CUT_202604140830_202604141700.csv',
        output_path='OHS/OHT_1차_결합분석_리포트.md',
    )
```

### 2.3 analyze_phase1_inject.py

**1차 스타/로그프레소 데이터 주입 분석**

```bash
python OHS/analyze_phase1_inject.py
```

- 입력: 동일 4개 데이터
- 출력: `phase1_output/` 폴더에 분석 결과 생성
- 용도: 새 날짜 데이터가 들어왔을 때 동일 분석을 재실행
- 다일자 비교, CommandId 분석 등 2차 분석 확장 대비

---

## 3. MD 문서 상세

### 3.1 OHT_UDP_ANALYSIS_REPORT.md
- M14_OHT 단독 분석 결과
- `analyze_oht_xsohs.py` 실행으로 자동 생성
- 1,033대 V-Vehicle, 가동률 82.3%, 적재율 62.1%, 사이클 7.8분

### 3.2 CSV_ANALYSIS_METHOD.md
- raw.csv 데이터 구조 (메시지 유형 1/2/3/4)
- Type 2 VHL_STATE_REPORT 21개 필드 매핑
- State/RunCycle/VhlCycle/DetailState Enum 코드표
- 각 분석 항목별 계산 방법 상세

### 3.3 OHT_1차_결합분석_리포트.md
- 4개 데이터 결합 분석 결과
- `analyze_combined.py` 실행으로 자동 생성
- 병목 판단: 정상 운영 확인
- 예측 판단: 1일치로는 분석만 가능, 5일치 필요

### 3.4 OHT_DIJKSTRA_ARCHITECTURE.md
- Dijkstra 경로 최적화 알고리즘 구조
- LineCost 계산 공식 (기본 통과시간 + 페널티)
- EMA 속도 갱신 방식
- 경로 재계산 원리
- 비유와 그림 중심 설명

### 3.5 OHT_WORLD_MODEL_FEASIBILITY.md
- 매크로(가능) vs 마이크로(불가) 예측 판단
- 룰 베이스 vs ML 비교
- 10분/20분 예측 한계
- CommandId + layout.xml 확보 필요성
- 기술 수준 상세 문서

### 3.6 OHT_예측모델_검토보고서.md
- **고객 보고용** (기술 용어 최소화)
- 예측 가능 여부, 시뮬레이션 조건
- 스타 수집 요청 데이터 17개 항목
- 추진 로드맵
- 요약 표

---

## 4. 2차 분석 시 사용법

### 4.1 같은 날 새 데이터가 추가된 경우

파일을 교체하고 코드 재실행:
```bash
# 1. 새 데이터 파일을 해당 폴더에 배치
# 2. 코드 실행
python OHS/analyze_combined.py
# 3. OHT_1차_결합분석_리포트.md 자동 갱신
```

### 4.2 다른 날짜 데이터가 들어온 경우

`analyze_combined.py`의 파일 경로를 새 데이터로 변경:
```python
generate_report(
    m14_path='OHS/새날짜/raw.csv',
    quwa_path='OHS/새날짜/스타.CSV',
    hid_path='OHS/새날짜/HID_INOUT.csv',
    rail_path='OHS/새날짜/RAIL_CUT.csv',
    output_path='OHS/새날짜_결합분석_리포트.md',
)
```

### 4.3 23필드(CommandId) 데이터가 들어온 경우

`analyze_oht_xsohs.py`에서 CommandId 관련 분석 함수 추가 필요:
- 차량별 작업/idle 구분 (CommandId 빈값 = idle)
- 시간대별 작업 발생 패턴
- 작업 지속시간 분포

### 4.4 5일치 이상 데이터가 모인 경우

다일자 비교 분석 추가:
- 일별 큐 패턴 비교 → 반복 패턴 확인
- 일별 반송시간 비교 → 정상 범위 확정
- 요일별 물동량 차이 → 요일 예측
- HID 저속 구간 일별 비교 → 구조적 병목 확정

---

## 5. 디렉토리 구조

```
OHS/
├── analyze_oht_xsohs.py          ← M14_OHT 단독 분석
├── analyze_combined.py            ← 1차 결합 분석 (리포트 생성)
├── analyze_phase1_inject.py       ← 1차 데이터 주입 분석
│
├── OHT_UDP_ANALYSIS_REPORT.md       ← M14_OHT 단독 리포트
├── CSV_ANALYSIS_METHOD.md          ← CSV 구조/방법론
├── OHT_1차_결합분석_리포트.md       ← 결합 분석 리포트
├── OHT_DIJKSTRA_ARCHITECTURE.md   ← Dijkstra 아키텍처
├── OHT_WORLD_MODEL_FEASIBILITY.md ← 예측 가능성 기술 평가
├── OHT_예측모델_검토보고서.md       ← 고객 보고서
├── OHS_산출물_설명서.md             ← 이 문서
│
├── OHT_UDP.zip                      ← M14_OHT 원본
├── OHT_UDP_extracted/raw.csv        ← M14_OHT 데이터
├── OHT_컬럼수집_DATA.CSV           ← 스타 데이터
├── LOGPRESSO.zip                  ← 로그프레소 원본
└── LOGPRESSO_extracted/
    ├── M14A_ATLAS_HID_INOUT_*.csv ← HID_INOUT 데이터
    └── ATLAS_OHT_RAIL_CUT_*.csv   ← RAIL_CUT 데이터
```
