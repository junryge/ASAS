# 룰베이스 v6 — 코드 사용법 README

> Python 3 만 있으면 동작 (pandas/numpy 등 외부 패키지 설치 불필요).
> 모든 코드는 같은 폴더에 두고 실행 권장.

---

## 파일 한눈에

| 파일 | 역할 | 인자 |
|---|---|---|
| `hubroom_predictor.py` | 룰베이스 본체 (예측) | 있음 |
| `thresholds.json` | v6 임계 설정 (자동 로드) | — |
| `운영로그_파서_v2.py` | 메신저 → 정답지 변환 | 있음 |
| `사건_예측검증.py` | 매칭/평가 (기본) | 있음 |
| `종합검증_v6.py` | 등급별 분석 | 없음 |
| `RA완화_CAPA제외_검증.py` | 시나리오 비교 | 없음 |
| `v6_신규컬럼_검증.py` | 신규 컬럼 검증 | 없음 |

---

## 1. `hubroom_predictor.py` — 룰베이스 본체 ⭐

설비 센서 데이터를 읽어서 장애를 예측. 발동이벤트.csv + 사건단위.csv 생성.

### (A) 실시간 운영 (매분 자동)
```bash
python hubroom_predictor.py
```
- `predict/M16A_HUBROOM_PR.csv` (수집기가 만든 매분 데이터) 를 자동으로 읽음
- 매분 `predict_tobe/` 에 결과 CSV 생성
- ⚠️ 입력 데이터를 만드는 **수집기가 별도로 돌고 있어야** 함

### (B) 과거 데이터 백테스트 (파일 통째로)
```bash
python hubroom_predictor.py <설비데이터.csv> -o <출력폴더>
```
예시:
```bash
python hubroom_predictor.py AWS_IDC_DATA_HIS_202605.CSV -o ./predict_tobe
```

### 필요 조건
- `thresholds.json` 이 **같은 폴더** 에 있어야 v6 설정(RA v4.1, gap 60 등) 적용
- 없으면 코드 기본값으로 동작 (안 깨지지만 v6 튜닝 일부 미반영)

### 출력
| 파일 | 내용 |
|---|---|
| `predict_tobe/YYYYMMDD_발동이벤트.csv` | 매분 메트릭 + 등급/지속성/예측유형 (135컬럼) |
| `predict_tobe/YYYYMMDD_사건단위.csv` | 사건당 1행, 점수 100+ 만 (170컬럼) |

### (C) OHT 가감점 (2026-10) — 오탐 줄이기
입력 CSV 의 FAB 별 OHT 컬럼 `{FAB}_OHT_report · _missing · _JAM · _HT_STOP` 을 보고 점수를 올리고 내린다.

| 조건 (FAB 하나) | ALL 점수 `unified_risk_score` | FAB 점수 `{FAB}_score_raw` |
|---|---|---|
| 미보고 ≥5 **와** JAM ≥10 같이 | +15 | +15 |
| 미보고 ≤5 **와** JAM ≤10 같이 | −10 | −15 |
| HT_STOP ≥1 | +10 | +10 |
| HT_STOP 0 | 그대로 | 그대로 |

- 설정은 전부 `thresholds.json` — 켜기/끄기, 적용 FAB, 기준 숫자, 점수 (수정 후 재시작)
  ```json
  "OHT_ADJ_ENABLED": true,                 // false = 예전 점수 그대로
  "OHT_ADJ_FABS": ["M16HUB"],              // 적용 FAB (M16HUB · M14 · M14B · M16A · M16B)
  "OHT_ADJ_ALL": {"enabled": true, "plus_missing": 5, "plus_jam": 10, "plus_score": 15,
                  "minus_missing": 5, "minus_jam": 10, "minus_score": -10,
                  "ht_min": 1, "ht_score": 10},
  "OHT_ADJ_FAB": { …같은 키… , "M16A": {"plus_score": 20}}   // FAB 이름 키 = 그 FAB 만 덮어쓰기
  ```
- 경계값(미보고 5 · JAM 10 정확히)은 둘 다 해당 → **+ 가 우선**
- 미보고만 높고 JAM 은 낮은 경우(예: 미보고 20 · JAM 3)는 +/− 둘 다 아님 → 0
- ALL 은 FAB 여러 개일 때 하나라도 + 면 +15, 모두 − 면 −10, HT 는 하나라도 있으면 +10 (각각 한 번)
- 보고(`_OHT_report`) 가 비었거나 0 인 FAB 은 가감하지 않는다 → OHT 수집이 멈춰도 감점 안 됨
- ALL 가감은 0~100 안에서 → **등급 · 사건 시작/종료도 가감된 점수로** 판단
- FAB 가감은 `{FAB}_score_raw` 에만 (영역 점수 `{FAB}_score` · ALL 합산에는 안 들어감)
- 발동이벤트 추가 칸: `unified_risk_score_orig`(가감 전), `oht_all_adj`, `{FAB}_oht_adj`,
  `{FAB}_score_raw_orig`(가감 전), `oht_signals`(근거) · reason 에도 `OHT(…)` 로 남는다
- 시작 로그에 설정이 한 줄로 찍힌다 (`OHT 가감점: 켬 · FAB M16HUB …`)

---

## 2. `운영로그_파서_v2.py` — 메신저 → 정답지

운영자 메신저 채팅을 장애 단위(Episode)로 구조화. 룰베이스 채점용 정답지 생성.

```bash
python 운영로그_파서_v2.py <메신저로그.txt> --out <출력폴더>
```
예시:
```bash
python 운영로그_파서_v2.py MA202605.txt --out ./output
```

### 출력
| 파일 | 내용 |
|---|---|
| `YYYYMMDD_HHMMSS_episode.csv` | **정답지** (장애 1건 = 1행) |
| `YYYYMMDD_HHMMSS_message.csv` | 메시지 단위 분류 결과 |
| `YYYYMMDD_HHMMSS_summary.json` | 통계 요약 |

---

## 3. `사건_예측검증.py` — 매칭/평가 (기본)

룰베이스 예측과 메신저 정답지를 매칭해서 TP/FP/Miss, 리드타임 계산.

```bash
python 사건_예측검증.py "<사건단위 경로>" "<episode 파일>"
```
예시:
```bash
python 사건_예측검증.py "predict_tobe/*_사건단위.csv" "output/20260615_120000_episode.csv"
```

### 주의
- 사건단위 경로는 **와일드카드(`*`) 가능** (여러 일자 합침)
- episode 는 **파일명 1개 명시** (와일드카드 불가)

### 출력 (콘솔)
- window별 TP/FP/Miss
- 사전 예측 리드타임 (평균/최대/중앙값)
- 장애 유형별 매칭률
- `output/YYYYMMDD_HHMMSS_prediction_match.csv` 저장

---

## 4. `종합검증_v6.py` — 등급별 분석

5단계 등급(관심~발동)별 정밀도 + 사건 연속성(진동) 분석 + 베스트 사례.

```bash
python 종합검증_v6.py
```
- 인자 없음. 코드 내부에 데이터 경로 지정됨 (`데이터들/extracted/`)
- 다른 데이터로 돌리려면 코드 상단 경로 수정

### 출력 (콘솔)
- 전체 정밀도/재현율/리드타임
- 등급별 표 (관심/주의/경계/위험/발동)
- 사건 연속성 분석 (진동/지속시간 분포)
- 정탐 사건 TOP 10

---

## 5. `RA완화_CAPA제외_검증.py` — 시나리오 비교

임계 조정 효과 비교 (v4.1 vs blend vs RA완화+CAPA제외). 튜닝 근거 자료.

```bash
python RA완화_CAPA제외_검증.py
```
- 인자 없음. 4개 시나리오 정밀도/재현율 비교표 출력

---

## 6. `v6_신규컬럼_검증.py` — 신규 컬럼 검증

지속성(continuity_min)/재발생(refire_count)/예측유형(predicted_fault_type) 컬럼 검증.

```bash
python v6_신규컬럼_검증.py
```
- 인자 없음. 신규 컬럼 분포 + 채워짐 확인 출력

---

## 전형적 작업 순서 (성능 검증)

```bash
# 1) 룰베이스 돌려서 사건 생성
python hubroom_predictor.py 설비데이터.csv -o ./predict_tobe

# 2) 메신저 로그로 정답지 생성
python 운영로그_파서_v2.py 메신저.txt --out ./output

# 3) 매칭해서 성능 평가
python 사건_예측검증.py "predict_tobe/*_사건단위.csv" "output/최신_episode.csv"

# 4) (선택) 등급별 상세 분석
python 종합검증_v6.py
```

---

## 실시간 운영 시 최소 구성

```
실시간 예측 (CSV 출력만):
  hubroom_predictor.py  +  thresholds.json   ← 이 2개면 충분

+ Logpresso DB 적재까지:
  위 2개 + Rule_LO.py + config.json + api_key.txt
```

⚠️ `종합검증_v6.py`, `RA완화_CAPA제외_검증.py`, `v6_신규컬럼_검증.py` 3개는
**검증 분석 전용** 이라 코드 안에 데이터 경로가 박혀 있음.
고객 환경에서 돌릴 땐 코드 상단의 경로만 본인 환경에 맞게 수정.
