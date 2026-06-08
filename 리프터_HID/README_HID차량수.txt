# 리프터 근방 HID 차량수 (1분 단위, 17기, 중복제거)

## 흐름 (2단계)
[STEP 1] 296MB OHT로그 -> 작은 진입이벤트 CSV (딱 한번)
  python extract_events.py 20260421.zip HID_Zone_Master_M16A_BR.csv 리프터_HID.csv 리프터근방_진입이벤트_BR_20260421.csv
  (이미 추출해둔 '리프터근방_진입이벤트_BR_20260421.csv' 가 있으면 STEP1 생략)

[STEP 2] 작은 파일로 1분 단위 카운트
  # 전체 시계열:
  python count_1min.py 리프터근방_진입이벤트_BR_20260421.csv 리프터_HID.csv 시계열.csv
  # 특정 분만:
  python count_1min.py 리프터근방_진입이벤트_BR_20260421.csv 리프터_HID.csv --at "2026-04-21 14:04"

## 규칙
- 1분 단위 / 리프터별 / 차량 중복제거 (한 분에 같은 차량은 1대)
- 17기 전부 (HID3 베이존까지 정확)

## 산출 예 (14:04): 6ABL6012=27, 6ABL6021=23 ... 6ABL6032=0
