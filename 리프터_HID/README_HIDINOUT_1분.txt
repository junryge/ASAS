# HID_INOUT 파일만으로 1분당 HID 차량수

## 입력 (이 파일 하나만)
LOGPRESSO_HID_INOUT_20260421.csv

## 실행
# 전체 1분 시계열 (HID별 IN/OUT):
python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv HID_1분_차량수.csv

# 특정 분만:
python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv --at "2026-04-21 14:04"

# 특정 HID만 (예 리프터 근방 33,34,3):
python hidinout_1min.py LOGPRESSO_HID_INOUT_20260421.csv --hid 33,34,3

## 출력: 시각, HID, IN_차량수, OUT_차량수
## 규칙: 1분 단위 / HID별 / 차량(VHL_ID) 중복제거
##   IN = TO_HIDID(진입),  OUT = FROM_HIDID(진출)

## 주의: HID_INOUT 로그는 메인 HID(HID4, 1~37)만 기록.
##   리프터 근방 중 HID33/34/3 은 이걸로 OK,
##   작은 베이존(10xxx)은 이 파일에 없음(그건 OHT위치로그 필요).
