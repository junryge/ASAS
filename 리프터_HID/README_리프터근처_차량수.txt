# 리프터 근처 HID 구간 차량수 (1분단위, 17기 전부, HID_INOUT 파일만)

## 입력 (이 파일들)
- LOGPRESSO_HID_INOUT_20260421.csv   (HID IN/OUT 로그, 이거 하나만)
- 리프터_근처HID4.csv                 (리프터 -> 근처 HID4 구간 매핑, 제공됨)

## 실행
# 전체 1분 시계열:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_20260421.csv 리프터_근처HID4.csv 시계열.csv
# 특정 분만:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_20260421.csv 리프터_근처HID4.csv --at "2026-04-21 14:04"

## 출력: 시각, Lifter, FAB, 근처HID, 근처차량수
## 규칙: 1분 / 리프터별 / 차량 중복제거
##   - 각 리프터의 '근처 HID4 구간'에 그 분 진입한 차량(TO_HIDID) 수
##   - 같은 HID4 구역 리프터는 같은 값(구역 단위)

## 매핑 근거: 리프터에 경계가 가장 가까운 HID4(1~37) 구간.
##   4ABLD*=HID2, 6ABL011x=HID24, 6ABL012x=HID28,
##   6ABL6011/6012/6032=HID32, 6ABL6021/6031=HID33, 6ABL6022=HID35

## 예 (14:04): 4ABLD*=17, 6ABL6021/6031=13, 6ABL601x=12 ...
