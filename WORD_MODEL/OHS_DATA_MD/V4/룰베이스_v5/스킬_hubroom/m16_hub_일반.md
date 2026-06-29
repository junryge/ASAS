---
name: m16_hub_일반
description: hubroom_predictor.py (M16 HUBROOM 룰베이스 v7) 의 실행·사용 방법 스킬. 어떻게 돌리는지(실시간/백테스트), 입력·출력 파일, 필요 파일, 옵션, 데모스에 데이터 주는 두 방식을 묻거나 실행을 도울 때 사용. "어떻게 실행", "돌리는 법", "사용법", "백테스트" 요청 시.
---

# m16_hub 일반 — hubroom_predictor.py 실행/사용 (v7 / 0~100 3등급)

> 배경 개념은 `m16_hub_카파시`, 결과 읽는 법은 `m16_hub_결과해석` 참조. 이 스킬은 **실행 방법** 중심.

## 0. 데모스에서 분석하는 두 방식
| 방식 | 주는 데이터 | 동작 |
|---|---|---|
| **(A) 결과 CSV 해석** | 발동이벤트.csv / 사건단위.csv | 스크립트 안 돌리고 바로 해석 |
| **(B) 원본 → 스크립트** | 수집 원본(M16A_HUBROOM_PR.csv) | hubroom_predictor.py 가 결과 CSV 생성 후 해석 |

## 1. 무엇을 하는 프로그램인가
`predict/M16A_HUBROOM_PR.csv`(설비 데이터)를 매분 읽어 8영역×9룰 평가 → `predict_tobe/` 에
발동이벤트.csv(24시간 전체) + 사건단위.csv(문제 발생 시) 출력.

## 2. 실행 방법 (직접 CLI)

### (A) 1회 처리 후 종료 (기본)
```bash
python hubroom_predictor.py
```
- 입력: `predict/M16A_HUBROOM_PR.csv` (기본 경로)
- 출력: `predict_tobe/YYYYMMDD_발동이벤트.csv`, `_사건단위.csv`

### (B) 상시 감시 (수집기 동기, 매분 00초+5초)
```bash
python hubroom_predictor.py --watch
```

### (C) 과거 데이터 백테스트
```bash
python hubroom_predictor.py <설비데이터.csv> -o <출력폴더>
# 예) python hubroom_predictor.py AWS_IDC_DATA_HIS_202605.CSV -o ./predict_tobe
```
> 백테스트 모드는 Logpresso 적재를 **자동 비활성화**(테스트 데이터가 운영 DB 에 안 들어가게).

## 3. 필요 파일
| 파일 | 필수? | 역할 |
|---|---|---|
| `hubroom_predictor.py` | ✅ | 본체 |
| `thresholds.json` | 권장 | 임계 설정(없으면 코드 기본값). 같이 둘 것 |
| `predict/M16A_HUBROOM_PR.csv` | ✅(B,실시간) | 입력 (수집기가 생성) |
| `Rule_LO.py` + `config.json` + `api_key.txt` | 선택 | Logpresso 적재 시만 |

## 4. 출력 파일
| 파일 | 범위 | 기록 시점 | 컬럼 |
|---|---|---|---|
| `YYYYMMDD_발동이벤트.csv` | 24시간 전체(매분 1행) | 즉시 | 135 |
| `YYYYMMDD_사건단위.csv` | 문제 발생 시(사건당 1행) | 사건 종료+60분 후, **점수 100+ 만** | 170 |

## 5. 의존성
- Python 3 **표준 라이브러리만** (pandas/numpy 불필요).
- Logpresso 적재 시에만: `requests`, `urllib3`.

## 6. 동작 흐름 (요약)
```
매분 → 8영역 룰 평가 → 점수/등급/단계 산출
  → 발동이벤트.csv 1행 기록 (항상, 24시간 전체)
  → S3 지속 구간을 사건으로 묶음 (gap 60분, 진동 흡수)
  → 사건 종료 시 점수 100+ 면 사건단위.csv 기록
```

## 7. 자주 쓰는 시나리오
```bash
# 1) 과거 데이터로 사건 생성
python hubroom_predictor.py 설비데이터.csv -o ./predict_tobe

# 2) 결과 확인 — 사건단위.csv 를 열어 max_risk_level=위험/발동 우선 검토
#    또는 데모스에 발동이벤트/사건단위 CSV 를 붙여넣어 해석 요청
```

## 8. 주의
- 입력 데이터를 만드는 **수집기는 별도로 돌고 있어야** 함(실시간/B 케이스).
- thresholds.json 없이 돌리면 코드 기본값 → 튜닝 일부 미반영.
- Logpresso 적재 실패(RemoteDisconnected/405)는 Rule_LO.py 문제 — 본체와 무관, CSV 는 정상 저장됨.
