---
name: m16_hub_일반
description: hubroom_predictor.py (M16A HUBROOM 룰베이스 v6) 의 실행·사용 방법 스킬. 어떻게 돌리는지(실시간/백테스트), 입력·출력 파일, 필요 파일, 옵션을 묻거나 실행을 도울 때 사용. "어떻게 실행", "돌리는 법", "사용법", "백테스트" 요청 시.
---

# m16_hub 일반 — hubroom_predictor.py 실행/사용 (초안)

> 배경 개념은 `m16_hub_카파시` 스킬 참조. 이 스킬은 **실행 방법** 중심.

## 1. 무엇을 하는 프로그램인가
`predict/M16A_HUBROOM_PR.csv`(설비 데이터)를 매분 읽어 8영역×9룰 평가 → `predict_tobe/` 에 발동이벤트.csv + 사건단위.csv 출력.

## 2. 실행 방법

### (A) 실시간 운영 (1회 처리 후 종료가 기본, --watch 로 상시)
```bash
python hubroom_predictor.py
```
- 입력: `predict/M16A_HUBROOM_PR.csv` (기본 경로)
- 출력: `predict_tobe/YYYYMMDD_발동이벤트.csv`, `_사건단위.csv`
- 상시 감시 모드: `python hubroom_predictor.py --watch`

### (B) 과거 데이터 백테스트
```bash
python hubroom_predictor.py <설비데이터.csv> -o <출력폴더>
# 예) python hubroom_predictor.py AWS_IDC_DATA_HIS_202605.CSV -o ./predict_tobe
```

## 3. 필요 파일
| 파일 | 필수? | 역할 |
|---|---|---|
| `hubroom_predictor.py` | ✅ | 본체 |
| `thresholds.json` | 권장 | 임계 설정(없으면 코드 기본값). v6 성능 위해 같이 둘 것 |
| `predict/M16A_HUBROOM_PR.csv` | ✅ | 입력 (수집기가 생성) |
| `Rule_LO.py` + `config.json` + `api_key.txt` | 선택 | Logpresso 적재 시만 |

## 4. 출력 파일
| 파일 | 단위 | 기록 시점 | 컬럼 |
|---|---|---|---|
| `YYYYMMDD_발동이벤트.csv` | 매분 1행 | 즉시 | 135 |
| `YYYYMMDD_사건단위.csv` | 사건당 1행 | 사건 종료+60분 후, 점수 100+ 만 | 170 |

## 5. 의존성
- Python 3 표준 라이브러리만 (pandas/numpy 불필요).
- Logpresso 적재 시: `requests`, `urllib3`.

## 6. 동작 흐름 (요약)
```
매분 → 8영역 룰 평가 → 점수/등급/단계 산출
  → 발동이벤트.csv 1행 기록 (항상)
  → S3 지속 구간을 사건으로 묶음 (gap 60분)
  → 사건 종료 시 점수 100+ 면 사건단위.csv 기록
```

## 7. 자주 쓰는 시나리오
```bash
# 1) 과거 데이터로 사건 생성
python hubroom_predictor.py 설비데이터.csv -o ./predict_tobe

# 2) 결과 확인 — 사건단위.csv 를 엑셀로 열어 max_risk_level=위험/발동 우선 검토
```

## 8. 주의
- 입력 데이터를 만드는 **수집기는 별도로 돌고 있어야** 함.
- thresholds.json 없이 돌리면 코드 기본값 → v6 튜닝 일부 미반영.
- Logpresso 적재 실패(RemoteDisconnected/405)는 Rule_LO.py 문제 — 본체와 무관, CSV 는 정상 저장됨.
