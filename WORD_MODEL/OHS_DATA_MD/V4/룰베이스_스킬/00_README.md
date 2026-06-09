# 룰베이스_스킬 — LLM 챗봇용 자산 셋트 (케이스 A: Python 자동 실행)

> 데모스 플랫폼 (Python 실행 가능) 에 본 폴더를 RAG/지식베이스로 등록.
> 사용자가 raw CSV 첨부 → LLM 이 자동으로 룰엔진 실행 → 결과 해석 → 응답.

---

## 핵심 흐름 (케이스 A)

```
[사용자]  raw CSV 첨부 (M16A_HUBROOM_PR.CSV) + 질문
   ↓
[LLM]  아래 Python 코드 자동 실행
   ├─ subprocess: python hubroom_predictor.py 받은CSV -o ./output
   ├─ 결과: ./output/YYYYMMDD_발동이벤트.csv 생성
   └─ pandas 로 결과 CSV 읽기
   ↓
[LLM]  결과 해석 (03_일반스킬.md 의 응답 템플릿 + 02_카파시톤.md 원리 + 04_임계값.md 인용)
   ↓
[응답]  정확한 평가 결과
```

★ LLM 은 raw 직접 평가하지 말 것. 항상 hubroom_predictor.py 를 통한 평가 결과를 사용.

---

## LLM 실행 코드 템플릿

raw CSV 가 첨부되면 다음 Python 코드를 실행:

```python
import subprocess, os, glob
import pandas as pd

# 1. 업로드된 raw CSV 경로 (데모스 환경에 따라 다름)
raw_csv = "<업로드된 파일 경로>"
out_dir = "./predict_tobe"
os.makedirs(out_dir, exist_ok=True)

# 2. 룰엔진 실행 (백테스트 모드 — Logpresso 적재 자동 차단됨)
result = subprocess.run(
    ["python", "hubroom_predictor.py", raw_csv, "-o", out_dir],
    capture_output=True, text=True, timeout=300
)
print(result.stdout[-500:])
print(result.stderr[-500:])

# 3. 결과 CSV 읽기
event_csv = sorted(glob.glob(f"{out_dir}/*_발동이벤트.CSV") +
                   glob.glob(f"{out_dir}/*_발동이벤트.csv"))[-1]
incident_csv = sorted(glob.glob(f"{out_dir}/*_사건단위.csv"))
incident_csv = incident_csv[-1] if incident_csv else None

events = pd.read_csv(event_csv)
incidents = pd.read_csv(incident_csv) if incident_csv else pd.DataFrame()

print(f"발동이벤트: {len(events)}분")
print(f"사건단위:   {len(incidents)}건")

# 4. 핵심 통계 — LLM 이 해석할 재료
print(events['stage_name'].value_counts())
print(events.groupby('hot_area')['unified_risk_score'].agg(['count','mean','max']))
```

→ 위 결과를 보고 LLM 은 `03_일반스킬.md` 의 템플릿대로 응답.

---

## 폴더 구조

```
룰베이스_스킬/
 ├─ 00_README.md            ← 본 파일 (LLM 행동 지침)
 ├─ 01_기준스크립트.md      ← 룰 알고리즘 (참조용, raw 직접 평가는 fallback)
 ├─ 02_카파시톤.md           ← 1차 원리 (왜 이 룰?)
 ├─ 03_일반스킬.md           ← 응답 형식 + 템플릿
 ├─ 04_임계값.md            ← ★ 정확 수치 (환각 방지)
 ├─ hubroom_predictor.py    ← ★ 룰엔진 (LLM 이 subprocess 로 실행)
 ├─ thresholds.json         ← 운영 임계
 ├─ thresholds.recommended.json
 └─ 샘플데이터/
      ├─ M16A_HUBROOM_PR.CSV          (raw 90분)
      ├─ 20260609발동이벤트.CSV       (분당 평가 861행)
      └─ 20260609사건단위.csv         (S3 사건)
```

---

## 입력별 LLM 동작

| 입력 | 동작 |
|---|---|
| raw CSV (`M16A_HUBROOM_PR.CSV` 등 265컬럼) | **hubroom_predictor.py 실행** → 결과 해석 |
| 발동이벤트 CSV (131컬럼, 이미 평가됨) | 바로 해석 (스크립트 실행 X) |
| 사건단위 CSV (169컬럼) | 사건별 상세 분석 |
| 질문만 ("R-A 임계가 뭐야?") | 04_임계값.md 인용 답 |

---

## 강제 응답 원칙

1. **임계값**: `04_임계값.md` 표만 인용. 자체 숫자 생성 금지.
2. **영역명**: M16HUB / M14 / M14B / M16A / M16B / M16 / M16_PKT / M16_WT 만.
3. **룰명**: R-A / R-A_sus / R-B / R-B_fast / R-C / R-D / SLA / SORT / MAXCAPA.
4. **단계**: S1 조기경보 / S2 주의보 / S3 ⭐확정.
5. **추천 / v4.1 둘 다 비교** — 한쪽만 답하지 말 것.
6. **응답 형식**: `03_일반스킬.md` 의 템플릿.
7. **raw CSV 직접 평가 금지** — 반드시 hubroom_predictor.py 결과 사용.

---

## 검증 5문제 (LLM 능력 테스트)

스킬 RAG 적재 후 다음 5문 정답률 측정:

1. **"M16HUB R-A 추천 임계값은?"** → 12.0분
2. **"STB 99% 는 정상인가?"** → 정상 분포 정점 (추천 101 미만 안전)
3. **"Sorter M14 246 LOT 어떤 상태?"** → 추천 420 미만 정상 / v4.1 100 위반
4. **"S3 확정 조건은?"** → any_RA AND (any_RD/SLA OR any_RC) AND (any_RB OR flow_severe)
5. **"5/8 사건 결과?"** → 113분 사전 감지

3개 이상 정확 → 운영 OK / 2개 이하 → 청크 보강 필요.

---

## 사용 시작 체크리스트

- [ ] 본 폴더 9개 파일 데모스 RAG/파일시스템에 적재
- [ ] hubroom_predictor.py 실행 환경 확인 (Python 3 + 표준 라이브러리만 필요)
- [ ] thresholds.json 운영 환경 맞춤 확인 (현재 = v4.1 원본, 추천 적용 시 thresholds.recommended.json 으로 덮어쓰기)
- [ ] 샘플데이터/M16A_HUBROOM_PR.CSV 던져서 테스트
- [ ] 검증 5문제 통과 확인
