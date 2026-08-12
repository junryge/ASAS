# ml_v2 — 심각한 정체만, 미리 잡는다

> **예측 가능한 심각한 상황만 ML로 예측한다.**
> 1분 순간 블립(예측 불가 노이즈)은 버리고, 30~156분 지속되는 큰 정체만 타깃.

파일 4개. 표준 라이브러리만으로 돌아가고, Chronos-2 있으면 자동으로 실모델을 쓴다.

| 파일 | 역할 |
|---|---|
| `data.py` | CSV 로딩 · 이동평균 · **심각 사건(라벨) 정의** |
| `detect.py` | **Chronos-2 로 이동평균 예측 → 선제 감지** |
| `evaluate.py` | 사건 단위 채점 (recall/precision/**lead 분포**) |
| `main.py` | 학습 → 감지 → 채점 한 번에 |
| `aws_idc_history_downloader.py` | (보조) 과거 기간 DB→날짜별 CSV 다운로드 |

---

## 왜 새로 만들었나 — 구버전 실패의 진짜 원인

`RAW/FINDINGS_RAW분석.md` 참고. 4~5월 61일(87,840분) 분석 결과:

**순간값이 임계를 넘은 것을 "정체"로 셌더니, 그 78%가 1분 만에 사라지는 블립이었다.**

| 임계 | 사건 | 1분 블립 | 5분+ 지속 |
|---:|---:|---:|---:|
| 16.7 (p99) | 657 | **513 (78%)** | 8 |
| 20 | 369 | 317 (86%) | **0** |

→ **원리적으로 예측 불가한 노이즈를 예측하라고 시킨 것.** 모델 문제가 아니라 라벨 정의 문제였다.
그래서 구버전 Chronos-2 의 lead 가 1~6분에 머물렀다.

**해결: 이동평균으로 전환.** 10분 이동평균 기준으로 보면 657건 → **18건**(월 9건),
평균 52분, 최장 156분. 그리고 이 중 **15건(83%)이 사건 전 buildup 을 갖는다 = 예측 가능.**

---

## 성과 (4월 학습 → 5월 평가, baseline 예측기 기준)

| | 구버전 (순간값 예측) | **V2 (이동평균 예측)** |
|---|---|---|
| Recall | 80% | **100%** (25/25) |
| **평균 lead** | 1~6분 | **13.6~14.1분** |
| ≥10분 전 감지 | 2~3건 | **12건** |

> ⚠ 위 수치는 **baseline 폴백** 예측기 결과다. 실 Chronos-2 로 돌리면 개선이 기대된다.
> Precision(23%)은 4월(조용)→5월(바쁨) 부하 차이로 임계가 낮게 학습된 영향이 크다.
> 실전(4~5월 61일 학습 → 6월 평가)에서는 임계가 안정적이라 개선될 여지가 있다.

---

## 사용법

### 준비
```
ml_v2/
├── chronos_2/          ← Chronos-2 모델 폴더 (없으면 baseline 폴백)
├── RAW/                ← 학습 데이터 4~7월 데일리 CSV 전부
├── RAW8/               ← 평가/운영 대상 데이터
└── data.py detect.py evaluate.py main.py
```
4~5월 학습 데이터는 저장소에서 복원 가능:
```bash
python3 ../RAW/decode_raw.py --out ./RAW      # 4/1~5/31 CSV 61개
```

**6·7월은 DB 에서 직접 다운로드** (`aws_idc_history_downloader.py`):
```bash
pip install oracledb
export ORA_USER=STAREAD  ORA_PASS='****'  ORA_DSN=10.40.41.103:1521/ICASTARPP

python aws_idc_history_downloader.py --from 2026-06-01 --to 2026-07-31 \
    --columns-from RAW/M16A_HUBROOM_PR_20260401.CSV --out RAW
```
→ `RAW/` 에 4~7월이 모두 모여 그대로 학습에 쓰인다 (컬럼 265개 동일 보장).

이 스크립트는 기존 실시간 수집기(`aws_idc_realtime_collector.py`)의 개조판이다.
원본은 쿼리가 `SYSDATE - 90/1440` 로 고정되어 과거를 못 뽑으므로, 시간조건만
날짜 바인드(`:d0 ~ :d1`)로 바꾸고 기간 루프·날짜별 저장을 추가했다.
컬럼 정의·PIVOT 방식·로깅은 원본 그대로.

| 옵션 | 설명 |
|---|---|
| `--split day` | `M16A_HUBROOM_PR_20260701.CSV` (기본, 4~5월과 동일) |
| `--split hour` | `M16A_HUBROOM_PR_2026070101.csv` (시간별, `--ext .csv` 와 함께) |
| `--columns-from` | 기존 CSV 헤더에서 컬럼 읽기 (265컬럼 일치). 생략 시 내장 59컬럼 |
| `--overwrite` | 기존 파일 덮어쓰기 (기본은 건너뜀 → 중단 후 이어받기 가능) |

### ① 학습 — 4월~7월로 한 번만 (결과를 파일로 저장해 재사용)
```bash
python main.py learn --train "RAW/*.CSV" \
    --window 10 --pct 0.99 --min-duration 10 \
    --out-config model_config.json
```
출력 예:
```
기간   : 2026-04-01 ~ 2026-07-31  (176400분 / 122일)
임계   : 15.152   (10분 이동평균 p99.0)
심각사건: 36건 (월 8.9건) · 평균 52분 · 최장 156분
저장: model_config.json   ← 이후 --config 로 재사용
```
`model_config.json` 에 **임계·이동평균 창·지속조건·분포통계**가 들어간다.
이후 모든 감지·채점이 이 파일을 그대로 쓰므로 기준이 흔들리지 않는다.

### ② 감지 + 채점 — 저장된 학습 결과로
```bash
python main.py all --config model_config.json \
    --eval "RAW8/*.CSV" \
    --model chronos_2 --device cuda \
    --horizon 15 --context 90 \
    --out-actions actions.csv --out-report report.csv
```

### 단계별로도 가능
```bash
# 사건 구조만 확인
python data.py --data "RAW/*.CSV" --window 10 --pct 0.99 --min-duration 10

# 감지만 (저장된 학습 결과 사용)
python detect.py --data "RAW8/*.CSV" --config model_config.json \
    --model chronos_2 --device cuda --horizon 15 --context 90 --out actions.csv

# 채점만 (학습과 같은 정의로)
python evaluate.py --actions actions.csv --data "RAW8/*.CSV" \
    --config model_config.json --out report.csv
```

> **판단 기준**: 모델은 **직전 90분**(`--context 90`)의 이동평균 이력을 보고
> 앞으로 **15분**(`--horizon 15`)을 예측한다.

---

## 튜닝 다이얼

| 옵션 | 기본 | 효과 |
|---|---|---|
| `--window` | 10 | 이동평균 창. 크게 = 더 큰 것만, 더 안정 |
| `--min-duration` | 10 | 심각 사건 최소 지속(분). 20~30 = 더 큰 것만 |
| `--horizon` | 15 | 예측 지평. 크게 = lead↑ (불확실↑) |
| `--context` | 90 | 모델이 보는 직전 이력(분) |
| `--p-on` | 0.6 | 경보 문턱. 높이면 헛울림↓ recall↓ |
| `--pct` | 0.99 | 임계 분위수. 높이면 사건 수↓ |
| `--stride` | 1 | 평가 간격. CPU면 3~5 로 가속 |

**헛울림이 많으면**: `--p-on 0.8`, `--pct 0.995`, `--min-duration 20` 순으로 조이기
**더 미리 잡으려면**: `--horizon 20~30`

---

## 설계 원칙 (지킬 것)

1. **임계는 학습기간에서만** 산출 → 평가기간 leakage 없음
2. **예측은 인과적** — 매 분, 직전까지의 데이터만 사용
3. **라벨·예측·채점이 같은 정의**(이동평균)를 쓴다 → 지표가 실제 운영 의미를 가짐
4. 이동평균은 **과거만 보는** 창 (미래 누수 없음)

---

## 남은 일

- [ ] **실 Chronos-2 로 6월 평가** (여기 결과는 baseline 폴백)
- [ ] precision 튜닝 (p_on / pct / min-duration 스윕)
- [ ] 실시간 러너 (매분 수집기 CSV 감시 → 경보)
- [ ] 선행지표(컨베이어·저장률) covariate 투입 검토
