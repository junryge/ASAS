# HANDOVER — M16A HUBROOM 반송정체 선제예측 (ml_v2)

> **다른 세션/담당자가 이 문서 하나만 읽고 이어서 작업할 수 있도록 쓴 전체 문서.**
> 코드를 고치기 전에 **§3 (바꾸면 안 되는 설계)** 와 **§10 (이미 밟은 지뢰)** 를 먼저 읽을 것.

| | |
|---|---|
| 대상 | SK하이닉스 M16A FAB · HUBROOM OHT 반송 정체 |
| 목적 | 정체가 **터지기 전에** 알린다 (목표 리드타임 10분) |
| 모델 | `amazon/chronos-2` (zero-shot 시계열 파운데이션 모델, 2025-10 공개) |
| 상태 | 학습·평가·실시간 3단계 모두 동작. 7월 평가 recall 100% / 평균 lead 9.8분 |
| 위치 | `ml_v2/` · 브랜치 `claude/ml-failure-rate-0e1fja` |

---

## 1. 한 장 요약

```
수집기 CSV(분당 1행)
   → 10분 이동평균 (블립 제거)
   → 직전 90분을 Chronos-2 에 입력
   → 앞 30분 분위수 예측 (q10/q50/q90)
   → 각 시점의 "임계 초과 확률" 계산
   → 확률이 p_on 넘으면 선제경보 (히스테리시스로 깜빡임 억제)
```

**이 프로젝트의 핵심은 모델이 아니라 라벨 정의다.** 자세한 건 §2.

---

## 2. 왜 이전 ML 은 실패했나 (근본 원인)

원본 데이터를 순간값 임계(16.7)로 "정체"를 세었더니:

| | |
|---|---|
| 검출된 사건 | 657건 |
| 그 중 **지속 1분** | **513건 (78%)** |
| 임계를 20 으로 올리면 | 5분 이상 지속 사건 **0건** |

즉 **"정체"의 78%가 1분 만에 사라지는 센서 블립**이었다.
임계를 높여도 지속시간이 오히려 짧아졌다 — 신호가 아니라 노이즈를 세고 있었다는 증거다.

**모델을 아무리 좋은 걸 써도 예측 불가능한 대상을 예측하라고 시킨 것**이 실패 원인이다.

### 해결 — 이동평균 라벨

10분 이동평균으로 바꾸자:

| | 순간값 | **10분 이동평균** |
|---|---|---|
| 사건 수 (61일) | 657건 | **18건** |
| 평균 지속 | 1분 | **52분** |
| 최장 지속 | — | **156분** |
| 사전 징후 있음(예측 가능) | — | **15/18 = 83%** |

남은 17%는 급발성(buildup 없이 터짐)이라 **원리적으로 미리 못 잡는다.**
이건 한계로 인정하고 즉시감지(stage 3)로 대응한다.

근거 원문: `RAW/FINDINGS_RAW분석.md`

---

## 3. 바꾸면 안 되는 설계 결정 5개

다른 세션이 "개선"하려다 되돌리기 쉬운 것들. **이유와 함께** 적는다.

| # | 결정 | 이유 | 되돌리면 |
|---|---|---|---|
| 1 | **10분 이동평균**을 예측 타깃이자 판정 기준으로 | 블립 78% 제거 (§2) | 예측 불가능한 노이즈를 쫓아 다시 실패 |
| 2 | 이동평균은 **과거만 보는 인과적(causal)** 구현 | 중앙이동평균은 미래를 봄 = 누설 | 성적이 허위로 좋아짐 |
| 3 | 임계는 **학습기간 분위수에서 자동 산출** (`--pct 0.99`) | 손으로 정한 임계가 실패했음 — 큐 100 은 최저값 107 보다 낮아 항상 초과, 저장률 30 은 최대 26 이라 한 번도 안 울림 | 임계가 데이터와 안 맞아 무용지물 |
| 4 | 임계 산출은 **학습기간에서만**, 평가기간은 절대 안 봄 | 누설 방지 | 성적 부풀림 |
| 5 | 예측 입력은 **시점 t 까지만** 자름 | 누설 방지 | 성적 부풀림 |

> Chronos-2 는 **zero-shot** 이다. "학습"이라고 부르는 ①단계는
> **가중치를 훈련하지 않는다.** 임계·통계만 뽑아 `model_config.json` 에 저장한다.
> 모델 파일을 fine-tune 하려 들지 말 것 — 그게 이 아키텍처의 장점이다.

---

## 4. 데이터 규격

분당 1행 CSV. **필수 컬럼은 2개뿐.**

| 컬럼 | 필수 | 설명 |
|---|---|---|
| `CRT_TM` | ✅ | 시각 `YYYY-MM-DD HH:MM:SS` |
| `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` | ✅ | **예측 대상** — HUB 평균 반송시간 |
| 나머지 263개 | ❌ | 현재 예측에 안 씀. `data.LEADING` 에 5개만 정의(확장 대비) |

- 파일이 날짜별로 쪼개져 있어도 됨 — 글롭으로 병합 후 시각순 자동 정렬
- 결측은 직전 값으로 채움 (`Series.filled`)
- 학습기간과 평가기간이 **겹치면 안 된다**

`data.LEADING` (선행지표 — 현재 미사용, covariate 확장용):
```
M14.QUE.CNV.SOUTHCURRENTQCNT        남측 컨베이어 큐
M14.QUE.CNV.NORTHCURRENTQCNT        북측 컨베이어 큐
M16HUB.STRATE.ALL.FABSTORAGERATIO   FAB 저장률
M16HUB.QUE.ALL.CURRENTQCOMPLETED    완료 반송량 (줄면 적체)
M16HUB.QUE.M14TOM16.MESCURRENTQCNT  M14→M16 큐
```

---

## 5. 알고리즘 상세

### 5-1. 이동평균 (`data.moving_avg`)
`window=10`. 시점 t 는 `t-9 ~ t` 만 본다. **미래를 안 본다.**

### 5-2. 임계 (`data.learn_threshold`)
학습기간 이동평균값의 p99. 4~6월 기준 **14.765**.

### 5-3. 사건 = 정답 라벨 (`data.find_events`)
```
이동평균 >= 임계 인 구간
  → gap(10분) 이내 간격은 같은 사건으로 병합
  → 지속 min_duration(10분) 미만은 버림   ← 블립 제거
```

### 5-4. 예측 (`detect.Forecaster`)
Chronos-2 에 직전 `context=90`분을 넣어 앞 `horizon=30`분의 q10/q50/q90 을 받는다.

- **호출 규격이 Bolt 와 다르다**: Chronos-2 는 `predict_quantiles(inputs, ...)` 이고
  `inputs` 는 **3-D 텐서 `(n_series, n_variates, history_length)`**.
  Bolt 는 `context=` 2-D. 그래서 `Forecaster._forms()` 가 5가지 호출 형태를
  순서대로 시도하고 성공한 형태를 기억한다.
- 정상 시 이 줄이 뜬다: `[모델 호출 형태] inputs 3-D (n_series,n_variates,history)`
- 모델을 못 찾으면 내장 `_baseline` (선형추세+잔차분위수) 로 폴백하고
  **"이 결과는 Chronos-2 성적이 아닙니다" 경고를 띄운다.**

### 5-5. 초과 확률 (`detect.exceed_prob`)
q10/q50/q90 세 점을 (값, 누적확률) 로 놓고 선형보간해 CDF 를 근사 → `P(X > 임계)`.
분위수 밴드가 좁으면(= 모델이 확신하면) 확률이 급격히 0/1 로 갈린다.

### 5-6. 단계 판정 (`detect.decide` / `realtime.judge`)

| stage | 조건 | 뜻 |
|---|---|---|
| **3** | 현재 이동평균 >= 임계 | 정체 **진행중** (이미 터짐) |
| **2** | 최대확률 >= `p_on` 이고 lead 존재 | **선제경보** — N분 뒤 초과 예상 |
| **1** | 최대확률 >= `p_off` | 관찰 (상승 조짐) |
| **0** | 그 외 | 정상 |

**히스테리시스**: 한 번 켜지면(`>= p_on`) `p_off` 밑으로 떨어질 때까지 유지한다.
문턱 하나만 쓰면 경계에서 경보가 깜빡거린다(alarm flapping).

`lead` = 예측 지평 안에서 처음으로 확률이 `p_on` 을 넘는 시점(분).

### 5-7. 채점 (`evaluate.py`)
**분 단위가 아니라 사건 단위**로 센다.
- 사건 시작 `pre`분 전 ~ 시작 사이에 stage>=2 가 있으면 **감지**
- lead = 사건 시작 − 첫 경보 시각
- 어느 사건에도 안 붙는 경보 구간 = **헛울림**

---

## 6. 파일 지도

```
ml_v2/
├── data.py        로딩 · 이동평균 · 사건정의 · 학습결과 저장      (표준 라이브러리만)
├── detect.py      Chronos-2 예측 → 초과확률 → 단계 판정
├── evaluate.py    사건 단위 채점
├── main.py        학습·평가 진입점 (learn / sweep / all)
├── realtime.py    실시간 러너 (매분 판정)
├── aws_idc_history_downloader.py   (보조) Oracle → 날짜별 CSV
├── HANDOVER.md    ← 이 문서
├── 실행명령어.md   복붙용 명령어
├── 인수인계.md     요약본
├── 명령어.md       옵션 설명
├── RESULTS.md      성적 상세
├── README.md       설계 배경
└── docs/           고객설명·기술구조 HTML
```

| 파일 | 핵심 함수 |
|---|---|
| `data.py` | `load` `moving_avg` `find_events` `learn_threshold` `learn` `save_config` `load_config` |
| `detect.py` | `Forecaster.predict` `exceed_prob` `predict_curves`(모델 호출) `decide`(후처리) `run` |
| `evaluate.py` | `read_actions` `alarm_spans` `evaluate` `print_report` `save_report` |
| `main.py` | `cmd_learn` `cmd_sweep` `cmd_all` |
| `realtime.py` | `read_snapshot` `judge` `load_state`/`save_state` `append_result` |

> **`predict_curves`(모델 호출)와 `decide`(순수 후처리)가 분리돼 있다.**
> 그래서 `sweep` 이 모델을 1번만 돌리고 p_on 을 여러 개 비교할 수 있다.
> 이 분리를 없애지 말 것 — 합치면 스윕이 N배 느려진다.

---

## 7. 실행 (명령 4개)

`실행명령어.md` 에 복붙용으로 정리돼 있다. 요약:

```bash
# 설치
pip install "chronos-forecasting>=2.0" torch

# ① 학습 — 기준 산출 (한 번만, 모델 불필요, ~1분)
python main.py learn --train "RAW/M16A_HUBROOM_PR_202604*.CSV" "RAW/M16A_HUBROOM_PR_202605*.CSV" "RAW/M16A_HUBROOM_PR_202606*.CSV" --out-config model_config.json

# ② 평가(스윕) — 모델 1회 실행으로 p_on 비교
python main.py sweep --config model_config.json --eval "RAW/M16A_HUBROOM_PR_202607*.CSV" --model chronos_2 --device cuda --horizon 30 --stride 3

# ③ 평가(확정)
python main.py all --config model_config.json --eval "RAW/M16A_HUBROOM_PR_202607*.CSV" --model chronos_2 --device cuda --horizon 30 --p-on 0.30 --out-actions actions.csv --out-report report.csv

# ④ 실시간 (운영)
python realtime.py --config model_config.json --input predict/M16A_HUBROOM_PR.csv --model chronos_2 --device cuda --p-on 0.30
```

### 실시간 동작 (④)
- 수집기가 `predict/M16A_HUBROOM_PR.csv` 를 매분 덮어쓴다 —
  **직전 90분 · 분당 1행**. 수집기 `WINDOW_MIN=90` 이 `--context 90` 과 정확히 일치한다.
- 러너는 매분 `00초 + --offset 8초` 에 읽는다 (수집기 쓰기 완료 대기).
  읽기는 5회 재시도(`read_snapshot`).
- 마지막 시각이 직전과 같으면(아직 미갱신) 2초 뒤 재확인 → **중복 판정 없음**
- 자체 이력을 `--history 600`분 유지하고 `realtime_state.json` 에 저장 →
  **재시작해도 10분 이동평균이 안 끊긴다**
- 모델은 **기동 시 1회만** 로드
- `--once` 로 단발 점검, `--on-alert "명령"` 으로 외부 연동

---

## 8. 산출물 스키마

### `model_config.json` (①의 결과 — ②③④의 입력)
```json
{
  "target": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN",
  "window": 10, "pct": 0.99, "min_duration": 10, "gap": 10,
  "threshold": 14.765,
  "smoothed_p50": ..., "smoothed_p95": ..., "smoothed_p99": ..., "smoothed_max": ...,
  "train_span": "2026-04-01 ~ 2026-06-30",
  "train_rows": 109440, "train_days": 91,
  "train_events": 23, "train_events_per_month": 7.6,
  "train_event_mean_duration": 51.8, "train_event_max_duration": 235,
  "leading_available": [...]
}
```

### `actions.csv` (②③ — 분당 판정)
`datetime, raw_value, stage, prob, lead_min, kind, reason`

### `report.csv` (②③ — 사건별 표, 엑셀로 열기)
`구분, 사건#, 정체시작, 정체종료, 지속(분), 이동평균피크, 순간최고, 감지시각, lead(분), lead구간, 확률, 사유`
맨 윗줄은 요약 코멘트. `구분` 이 `헛울림` 인 행은 오경보 목록.

### `ml_predict/{날짜}_ml_chronos_2.csv` (④ — 실시간, 매분 append)
`datetime, raw_value, smoothed, stage, stage_name, prob, lead_min, threshold, reason`
```csv
2026-08-19 06:48:00,12.927,9.613,2,선제경보,1.0,7,14.765,약 7분 뒤 임계 초과 예상
```
날짜는 **데이터 시각** 기준 → 자정 넘으면 자동으로 새 파일.

### `realtime_state.json` (④ — 재시작 대비)
`{"history": [[시각, 값], ...], "active": bool, "last": "마지막 처리 시각"}`

---

## 9. 현재 성적 (7월 평가 · 4~6월 학습 · 실모델 `backend=chronos_2`)

학습기간 심각사건 23건(월 7.6건) / 평가기간 **4건**.

| p_on | Recall | Precision | 평균 lead | ≥10분 전 | 헛울림 | /일 |
|---:|---:|---:|---:|---:|---:|---:|
| **0.30** | **100%** | 25% | **9.8분** | **3/4** | 12 | 0.4 |
| 0.40 | 100% | 31% | 8.2분 | 2/4 | 9 | 0.3 |
| 0.50 | 100% | 50% | 3.8분 | 0/4 | 4 | 0.1 |
| 0.60 | 100% | 80% | 3.8분 | 0/4 | 1 | 0.0 |

**모든 설정에서 recall 100%** — 심각 정체를 하나도 안 놓쳤다.
`p_on` 은 "얼마나 미리 알리나 ↔ 헛울림을 얼마나 참나" 다이얼이다.
데드락은 놓치면 손실이 크고 헛울림은 확인 한 번이면 되므로 **0.30 권고**.

### Chronos-2 vs baseline (같은 조건, p_on 0.6)
| | baseline | Chronos-2 |
|---|---|---|
| Precision | 33% | **80%** |
| 헛울림/일 | 0.3 | **0.03** |
| 평균 lead | 9.2분 | 3.8분 |

Chronos-2 는 정확해서 예측밴드가 좁다 → **확실할 때만 울린다**(헛울림 1/10).
대신 늦게 울리므로 p_on 을 낮춰 lead 를 되찾는 구조다.
즉 이득은 "**같은 lead 에서 헛울림이 훨씬 적다**" 로 나타난다.

---

## 10. 이미 밟은 지뢰 (재발 방지)

다른 세션이 같은 함정에 빠지지 않도록 남긴다.

| # | 증상 | 원인 / 해결 |
|---|---|---|
| 1 | 임계가 전혀 안 맞음 | 손으로 정한 값. 큐 100 은 최저 107 보다 낮아 항상 초과, 저장률 30 은 최대 26 이라 무발화 → **학습기간 분위수로 자동 산출** |
| 2 | `TypeError: predict_quantiles() missing 'inputs'` | Chronos-2 는 `inputs=`, Bolt 는 `context=`. **API 가 다르다** |
| 3 | `Expected 3-d tensor ... got shape (1, 16)` | Chronos-2 `inputs` 는 3-D `(n_series, n_variates, history)` → `t2d.unsqueeze(1)` |
| 4 | `ValueError: Could not infer frequency` | `predict_df` 사용 시 `freq="min"` 필요. 지금은 텐서 경로라 무관 |
| 5 | 헤더는 `backend=chronos_2` 인데 채점은 `(backend=baseline)` | **조용한 폴백**. 지금은 실패 사유를 즉시 출력하고 "Chronos-2 성적 아님" 경고를 띄운다. **채점 줄의 backend 를 반드시 확인할 것** |
| 6 | 추론이 극단적으로 느림 (44,640회 호출) | GPU 연산이 아니라 **호출당 오버헤드**가 지배. `--batch 256` 으로 배치화 → 호출 수 1/256 |
| 7 | p_on 스윕이 모델을 3번 돌림 | `predict_curves`(모델) / `decide`(후처리) 분리 + `main.py sweep`. **이 분리를 합치지 말 것** |
| 8 | 글롭이 안 먹힘 (`OSError: Invalid argument`) | 단일파일 로더를 쓴 실수. `data.load` (글롭 병합) 사용. 셸에서 **따옴표 필수** `"RAW/*.CSV"` |
| 9 | HTML 문서 한글 깨짐 | `<meta charset="utf-8">` 누락 |
| 10 | 사건이 1분짜리 투성이 | §2 — 순간값 라벨. 이동평균으로 전환 |

---

## 11. 한계 (정직하게)

1. **평가기간 심각사건이 4건뿐** — 7월이 조용했다. recall 100% 는 4건 기준이라
   표본이 작다. → 5·6월 교차검증 필요.
2. **정답이 "이동평균 임계초과"** — 운영자가 실제로 문제라고 인식한 사건 로그와
   대조해야 진짜 정확도를 안다.
3. **급발성 정체(17%)는 원리적으로 미리 못 잡는다.** 현재 구조는 buildup 형(83%) 대상.
4. 이 저장소 컨테이너는 PyPI/HuggingFace 가 막혀 있어 **여기서는 실모델 검증 불가**.
   로직·CSV 적재·상태복원은 검증됐고, 실모델 경로는 GPU 장비에서 확인해야 한다.

---

## 12. 남은 작업

- [ ] **5·6월 교차검증** — 명령 ②③에서 `--eval` 만 바꾸면 됨 (사건 수 확보)
- [ ] 실제 사건 이력과 대조해 정확도 재검증
- [ ] `--on-alert` 로 메신저·Logpresso 연동
- [ ] (확장) `data.LEADING` 5개 선행지표를 covariate 로 투입 — Chronos-2 는
      multivariate zero-shot 을 지원한다. 현재는 타깃 단변량만 쓴다.
- [ ] (선택) 기존 CUSUM 4감지기와 결합 — v1 실험에서 CUSUM 은 lead 가 길고
      Chronos 는 정확했다. union 결합 시 recall↑, confirm 결합 시 precision↑

### 재학습 주기
**3개월마다 ①만 다시 돌린다** (`--train` 을 최근 3개월로).
`model_config.json` 이 갱신되고 ②③④ 는 그대로 쓴다.
직전 config 는 백업해 두면 성적 비교가 된다.

---

## 13. 결과를 바꾸고 싶을 때 고칠 위치

| 바꾸고 싶은 것 | 위치 |
|---|---|
| 더 일찍 알리고 싶다 | `--p-on` 낮추기 (0.30 → 0.20). 헛울림 늘어남 |
| 헛울림 줄이고 싶다 | `--p-on` 올리기. lead 짧아짐 |
| 더 먼 미래까지 보고 싶다 | `--horizon` 늘리기 (30 → 45) |
| 사건을 더/덜 잡고 싶다 | ① 재실행 시 `--pct` (0.99 → 0.97 이면 사건↑) |
| "심각"의 최소 지속 | ① 재실행 시 `--min-duration` (기본 10분) |
| 다른 컬럼을 예측 대상으로 | `data.TARGET` 수정 후 ①부터 재실행 |
| 판정 주기 | ④ `--interval` (기본 60초) |

---

## 14. 막힐 때

| 증상 | 해결 |
|---|---|
| `backend=baseline` | 모델 폴더 못 찾음 → `--model D:\경로\chronos_2` |
| `모든 호출 형태 실패` | chronos 버전 문제. 출력된 에러 4~5줄 확인 (§10-2,3) |
| `CSV 없음` | 글롭에 따옴표 필수 — `"RAW/*.CSV"` |
| 너무 느림 | `--stride 5 --batch 512` (④는 무관) |
| 사건 0건 | 평가기간이 조용했거나 임계가 높음 → `--pct 0.97` 로 재학습 |
| ④ `입력 오류` | 수집기 미가동 또는 `--input` 경로 오류 |
| ④ 결과가 안 쌓임 | 수집기 파일의 마지막 시각이 안 바뀜(수집기 정지) |
| ④ 한 줄만 나오고 끝 | `--once` 가 붙어 있음 |

---

## 부록. 환경

| 항목 | 요구 |
|---|---|
| Python | 3.9+ (검증 3.13) |
| 패키지 | `chronos-forecasting>=2.0`, `torch` — **끝.** `pandas` 불필요 |
| GPU | 선택. 없으면 `--device` 생략 (④는 분당 1회라 CPU 로 충분) |
| 모델 | `amazon/chronos-2`. 폐쇄망이면 `huggingface-cli download amazon/chronos-2 --local-dir ./chronos_2` 후 폴더 복사 |
| `oracledb` | `aws_idc_history_downloader.py` 쓸 때만. 비밀번호는 `ORA_PASS` 환경변수 (코드에 하드코딩 금지) |
