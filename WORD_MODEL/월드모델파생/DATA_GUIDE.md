# OHT 월드모델 데이터 수집 가이드

> 새 날짜 데이터를 추가하려면 이 문서를 따라주세요.

---

## 1. 폴더 생성

`OHS_DATA_MD` 아래에 **날짜 8자리** 폴더를 만드세요.

```
OHS_DATA_MD/
  20260414/    <- 기존
  20260415/    <- 기존
  20260417/    <- 새 폴더 (예시)
```

---

## 2. CSV 파일 넣기

아래 파일을 해당 폴더에 넣으세요. 파일명 뒤 `XXXXXXXX` 부분은 날짜/시간이 달라도 자동 인식됩니다.

| # | 파일명 패턴 | 내용 | 필수 여부 | 건수 (04-15 기준) |
|---|------------|------|----------|-----------------|
| 1 | `LOGPRESSO_OHT_DATA_XXXXXXXX.csv` | OHT 차량 raw 데이터 (위치, 상태, 속도) | **필수** | 1,610,871건 |
| 2 | `LOGPRESSO_HID_INOUT_XXXXXXXX.csv` | HID 구간 통과 이벤트 (구간 속도) | **필수** | 871,017건 |
| 3 | `LOGPRESSO_OHT_RAIL_CUT_XXXXXXXX.csv` | 레일 차단 이벤트 | **필수** | 19건 |
| 4 | `STAR_OHT_컬럼수집_DATA_XXXXXXXX.csv` | 스타 지표 (큐, OBS, 가동률) | **필수** | 1,352건 |
| 5 | `LOGPRESSO_oht_data_m14a_XXXXXXXX.csv` | 파싱된 OHT (컬럼 분리 버전) | 있으면 좋음 | 1,338,676건 |
| 6 | `LOGPRESSO_ts_resource_m14a_XXXXXXXX.csv` | 작업 명령 (TRANSPORTCOMMANDID) | 있으면 좋음 | 3,282,497건 |
| 7 | `LOGPRESSO_oht_time_avg_XXXXXXXX.csv` | TAT 평균 (반송 시간) | 있으면 좋음 | 8,233건 |

---

## 3. 자동 인식 키워드

파일명에 아래 키워드가 포함되면 자동으로 매칭됩니다.

| 데이터 | 자동 인식 키워드 |
|--------|----------------|
| OHT raw | `OHT_DATA` 또는 `OHT_날짜` |
| HID 통과 | `HID_INOUT` |
| 레일 차단 | `RAIL_CUT` |
| 스타 지표 | `STAR_OHT` 또는 `컬럼수집` |
| 파싱 OHT | `oht_data_m14a` |
| 작업 명령 | `ts_resource` |
| TAT 평균 | `oht_time_avg` |

---

## 4. 서버 실행

```bash
cd WORLD_SIM
python main.py
```

브라우저에서 http://localhost:10005 접속 후 드롭다운에서 날짜 선택.

**폴더만 넣고 서버 재시작하면 자동으로 드롭다운에 나타납니다.**

---

## 5. 참고

- 데이터가 많으면 로딩에 30초~1분 소요 (1.6M건 기준)
- 최소 필수 4개 파일만 있으면 시뮬레이션 가능
- 5일치 이상 모이면 패턴 예측 정확도가 올라감
- 파일 크기: 1일 기준 약 700MB~1.2GB
