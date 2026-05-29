# ALT/opss/decoded — 운영 디코딩 산출물 모음

`q.txt`, `s.txt`, `d.txt` (FOLDER_ARCHIVE_BASE64) 를 디코딩해 정리한 운영 자료 + 자바→Python 마이그레이션 결과물.

---

## 폴더 구성

| 폴더 | 출처 | 내용 |
|---|---|---|
| **01_ml_operation/** | `q.txt` (afagg.zip) | 운영 중인 Python ML 시스템 + ★마이그레이션 신규 배치 2개 |
| **02_config/** | `s.txt` (avav.zip) | 운영 설정 XML (쿼리/임계치/메시지/스케줄) |
| **03_mybatis_mapper/** | `d.txt` (fgfgfgfg.zip) | Oracle mybatis mapper (SQL 본문) |

⚠ 민감 파일 제외: `DBConnection.xml` / `Settings.properties` / `FabSet.properties` 는 평문 DB 비밀번호 포함 → 백업에서 제외함.

---

## 01_ml_operation/ — Python ML 운영 + 마이그레이션

```
Prediction_ml.py                  마스터 스케줄러 (매분 정각, 2사이트 병렬)
├── M14A_FAB/                      Q_TRANSFER 사이트
│   ├── M14A_FAB_data_make.py      데이터 수집 → QTRANSFER.csv
│   ├── V8.3.1_Q_TRANSFER_PREDICTOR_{10,15,25}m.py   예측 (모델 .pkl 별도)
│   ├── m14a_config.json
│   ├── QTransferPredictBatch.py   ★ 자바 마이그레이션 (알람 11종 + 통계 + 적재)
│   └── qtransfer_alarm_config.json★ 임계치16/메시지27/쿼리11/Oracle dbquery 3
└── M16A_BR/                       HUBROOM 사이트
    ├── M16BR_hubroom_data_make.py 데이터 수집 → HUBROOM_PIVOT_DATA.csv
    ├── V8_Categorical/Numerical_Real_time_{10,15,25}min.py  예측
    ├── m16br_config.json
    ├── HubroomTransPredictBatch.py★ 자바 마이그레이션 (WARN_YN 판정)
    └── hubroom_alarm_config.json  ★ WARN 판정 설정
```

### 마이그레이션 매핑 (자바 → Python)

| 자바 | Python | 저장 테이블 (구 → 테스트) |
|---|---|---|
| `HubroomTransPredictBatch.java` `_validWarnYN` | `HubroomTransPredictBatch.py` | `test_hubroom_predict` → **`test_table`** |
| `QTransferPredictBatch.java` `_alarmValid`+`_buildTransportAlarm` | `QTransferPredictBatch.py` | `test_currentjob_predict` → **`test_table5`**, `ATLAS_TS_PREDICT` → **`test_table6`**, `qtransfer_dashboard` → **`test_table7`** |

> ⚠ 현재 모든 적재 대상을 **테스트 테이블**(`test_table`/`test_table5`/`test_table6`/`test_table7`)로 변경함 (구조 동일). 운영 전환 시 config 의 `insert_table`/`predict_table`/`dashboard_table` 만 원복하면 됨.

### QTransfer 알람 11종 (전체 완성)
- ALARM1 VHL+MES / ALARM2 CNV+storage / ALARM3 M10 LFT / ALARM4 M14B LFT
- ALARM5 ALT JOB / ALARM6~11 IDC_HISTORY (Storage/Sorter/Q 등)
- Oracle(LFT 다운율, storage)은 `dbquery mcs_m14a/m14b/m16a` 로 Logpresso httpexport 경유 (oracledb 불필요)

---

## 02_config/ — 운영 설정

| 파일 | 용도 |
|---|---|
| `customQuery.xml` / `customQuery2.xml` | Logpresso 쿼리 (알람용 11종 포함) |
| `variable.xml` | 임계치 (QTRANSFER_LIMIT 등 16종) |
| `alarm_message.xml` / `oht_alarm_message.xml` | 알람 메시지 텍스트 |
| `BatchConfig.xml` | Quartz 스케줄 |
| `Prediction_ml.py` | 운영 마스터 사본 |

→ 이 값들을 `qtransfer_alarm_config.json` / `hubroom_alarm_config.json` 에 추출 반영함.

---

## 03_mybatis_mapper/ — Oracle SQL

| mapper | 마이그레이션에 쓰인 SQL |
|---|---|
| `mcs_m14a.xml` | `SELECT_M14TOM10LFT_DOWN_RATE` (ALARM3) |
| `mcs_m14b.xml` | `SELECT_M14LFT_DOWN_RATE` (ALARM4) |
| `mcs_m16a.xml` | `SELECT_M16A_STORAGE_UTIL` (ALARM2/3/4 storage) |
| `apm_m14.xml` | `SELECT_APM_RESOURCE_LIST` (ServerResource — 참고) |
| 기타 | mcs_m11~m16, iot, mongodb 등 (참고용) |

→ 세 SQL 은 `dbquery` 패턴으로 변환해 config 의 `oracle.queries` 에 반영.

---

## 실행 (운영서버)

```bash
cd 01_ml_operation
python Prediction_ml.py            # 매분 정각 자동 (data_make → 예측 → 알람배치)
# 단일 테스트
cd M14A_FAB && python QTransferPredictBatch.py --once
cd M16A_BR  && python HubroomTransPredictBatch.py --once
```

⚠ 모델 `.pkl` 은 용량상 git 미포함 — 운영서버 `model/` 폴더에 존재.

---

## 보안 메모

- `api_key.txt` 는 빈 파일 (운영 키 별도 보관)
- DB 접속정보 (`DBConnection.xml` 등) 는 백업 제외
- 노출 이력 있던 비번은 변경 권장 (DBA)
