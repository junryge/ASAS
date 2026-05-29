# V4 — 룰베이스 + ML 통합 운영 패키지

> M16A HUBROOM OHS 시스템 30분 사전 정체 예측
> 룰베이스 v4.1 (8영역 통합) + XGBoost ML (10/30분 모델)
> 한 폴더에서 학습 / 평가 / 실시간 운영 모두 가능

---

## 빠른 시작

### 운영 시작 (1줄)
```cmd
cd V4
python run_ml.py
```

→ 3 스레드 자동 시작 (수집기 + 룰베이스 + ML).

### 학습 (처음 1회)
세부 명령은 [`ML_사용법.md`](ML_사용법.md) 참조.

---

## 폴더 구조

```
V4/                                        ← 본 패키지
├── [실행 진입점]
│   └── run_ml.py                          ★ 운영 시작 (3 스레드)
│
├── [데이터 파이프라인]
│   ├── aws_idc_realtime_collector.py     수집기 (Oracle SQL → CSV)
│   ├── hubroom_predictor.py              룰베이스 v4.1
│   └── ml_predict_runner_v41.py          ML 추론 (10/30분)
│
├── [ML 모듈]
│   ├── feature_builder_v41.py            피처 빌더 (raw + 발동이벤트)
│   ├── ml_predictor.py                   XGBoost 로더
│   ├── train_xgboost.py                  학습
│   ├── evaluate.py                       평가
│   ├── make_incidents.py                 라벨 A (룰 S3)
│   ├── make_incidents_risk65.py          라벨 C (risk≥65)
│   ├── messenger_to_incidents.py         라벨 B (메신저) ★
│   └── 운영로그_파서.py                  메신저 txt → CSV
│
├── [Logpresso 적재]
│   ├── Rule_LO.py                        룰 → test_table3
│   └── ML_LO.py                          ML → test_table4
│
├── [예약 — 내일 작업]
│   └── hybrid_predictor.py               하이브리드 (비활성)
│
├── [점검 도구]
│   ├── 룰베이스검증.py
│   └── sample_sender.py
│
├── [설정]
│   ├── config.json                       Logpresso URL / 테이블명
│   ├── api_key.txt.example               (api_key.txt 로 rename + 키 입력)
│   └── incidents_sample.json
│
├── [모델 — 학습 후 생성]
│   ├── model_v41_10m.json + _features.json
│   └── model_v41_30m.json + _features.json
│
├── [자동 생성 폴더 — 실행 시]
│   ├── predict/                          수집기 출력 (M16A_HUBROOM_PR.csv)
│   ├── predict_tobe/                     룰베이스 출력 (발동이벤트.csv)
│   └── ml_predict/                       ML 출력 (predictions.csv)
│
└── [문서]
    ├── ML_사용법.md                       ★ 학습/평가/운영 전체 명령
    ├── ML_출력_컬럼설명.md                ml_score 운영자 가이드
    ├── 발동이벤트_컬럼설명.md             룰베이스 50컬럼 설명
    ├── HUBROOM_PREDICTOR_구조설명.md       룰엔진 구조
    ├── RISK_FACTORS_가이드.md             risk_score 의미
    ├── RULES_DETAIL.md                    룰 정의
    ├── AWS_IDC_v4.1_컬럼_전체정리.md      IDC 265 컬럼
    ├── IDC_컬럼정의서.md
    ├── MAIN_UIS_분석_통합예측기_계획.md
    ├── 고객설명서.md
    ├── ML_README.md
    ├── RUN_PY_PATCH.md
    └── README_legacy_v3.md                v3 시절 매뉴얼 (참고)
```

---

## 동작 흐름

### 운영 시 (실시간, 매분)
```
[Oracle IDC]
   ↓ SQL 매분
[aws_idc_realtime_collector] → predict/M16A_HUBROOM_PR.csv (90분 윈도우)
       │
       ├──→ [hubroom_predictor] → predict_tobe/{YYYYMMDD}_발동이벤트.csv
       │      ↓ Logpresso
       │    test_table3 (file=Rule_system)
       │
       └──→ [ml_predict_runner_v41] → ml_predict/{YYYYMMDD}_predictions.csv
              ↓ Logpresso
            test_table4 (file=ML_system)
              컬럼: ml_score_10m, ml_score_30m
```

### 학습 시 (1회, 또는 주기 재학습)
```
[Oracle 1~5월 데이터 CSV]
   ↓
[hubroom_predictor.py] → predict_tobe/*_발동이벤트.csv (146 파일)
   ↓
[운영로그_파서 + messenger_to_incidents] → incidents_B_messenger.json (사건 라벨)
   ↓
[feature_builder_v41] → features_v41.csv (~700 피처)
   ↓
[train_xgboost] × 2 (lead_min=10/30) → model_v41_10m.json + model_v41_30m.json
   ↓
[evaluate] → 사건 탐지율 / 위양성 확인
```

---

## 운영 출력 컬럼 (ML)

`ml_predict/{YYYYMMDD}_predictions.csv`:

| 컬럼 | 의미 |
|---|---|
| `datetime` | 현재 시각 |
| `prediction_for_10m` | 10분 뒤 시각 |
| `prediction_for_30m` | 30분 뒤 시각 |
| `ml_score_10m` | 10분 뒤 사건 확률 (0~1) |
| **`ml_score_30m`** ★ | **30분 뒤 사건 확률 (메인)** |
| `ml_level_10m/30m` | OK / INFO / WARNING / CRITICAL |

운영자는 **`ml_score_30m ≥ 0.7`** 보면 사전 대응 시작.

---

## 운영자 SOP

| 룰 stage | ML score 30m | 판단 |
|---|---|---|
| 3 | ≥ 0.7 | **확정 위험** — 즉시 대응 |
| < 3 | ≥ 0.85 | **ML 선행 알람** — 30분 내 룰 발동 예상 |
| 3 | < 0.3 | 위양성 의심 — 룰 사유 확인 |
| < 3 | < 0.7 | 정상 |

---

## config.json — 운영 모드

```json
{
  "logpresso_base": "http://10.40.42.27:8888/logpresso",
  "api_key_file": "api_key.txt",
  "table_name": "test_table3",
  "file_label": "Rule_system",
  "ml_table_name": "test_table4",
  "ml_file_label": "ML_system",
  "enabled": true,
  "ml_enabled": true
}
```

> 백테스트 시에는 `enabled: false`, `ml_enabled: false` 로.

---

## 사전 체크리스트

| 항목 | 확인 |
|---|---|
| ☐ Python 라이브러리 | `xgboost`, `requests`, `urllib3`, Oracle 드라이버 |
| ☐ Oracle 접속 | 수집기 DB 정보 |
| ☐ Logpresso 접근 | `config.json` 의 URL 핑 가능 |
| ☐ API key | `api_key.txt` (1줄, Logpresso 키) |
| ☐ 모델 파일 4개 | `model_v41_10m/30m.json` + `_features.json` |
| ☐ config.json | `enabled / ml_enabled: true` |

---

## 종료
`Ctrl+C` — 3 스레드 모두 종료.

---

## 핵심 성능 (참고 — 평가 결과)

학습 데이터: 2026-03-24 ~ 2026-05-31 (~68일, 메신저 라벨 B 79건)

| 모델 | 탐지율 (3월 24일 이후) | 위양성 | 최대 사전인지 |
|---|---|---|---|
| 10분 | 100% | 0.03% | - |
| **30분** ★ | **100%** | **0.05%** | **28분** |

→ 운영 사용 가능.

---

## 자세한 내용
- 학습/평가/운영 전체 명령: [`ML_사용법.md`](ML_사용법.md)
- ML 출력 운영자 가이드: [`ML_출력_컬럼설명.md`](ML_출력_컬럼설명.md)
- 룰베이스 컬럼: [`발동이벤트_컬럼설명.md`](발동이벤트_컬럼설명.md)
- 룰 정의: [`RULES_DETAIL.md`](RULES_DETAIL.md)

---

*v4.1 (XGBoost binary classification + 룰베이스 8영역 통합)*
*문서 작성: 2026-05-29*
