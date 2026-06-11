---
name: M16_BR_HID_리프터일반
description: >
  M16A_BR OHT 리프터 근처 HID 구역의 차량 개수(진입/점유/포화도)를 1분 단위로
  집계한다. LOGPRESSO_HID_INOUT 로그 + layout.zip + station.dat 를 줄 때 사용.
  "리프터 HID 개수", "1분당 차량수", "진입개수", "리프터 근처 차량", "리프터 지도",
  "M16 리프터 HID" 같은 요청에 발동. (SK하이닉스 M16A_BR OHT)
---

# M16 리프터 HID 일반 스킬 (개수)

M16A_BR 리프터(`*ABL*`)별 **근처 HID4 구역**의 차량 **개수**를 1분 단위로 산출.
한 결과 CSV 에 진입개수 + 점유 + MAX_VHL + 포화도 를 모두 출력.

## 입력 (사용자 제공)
| 파일 | 설명 |
|------|------|
| `BR.layout.zip` | 레이아웃 (내부 layout/layout.xml) |
| `BR.station.dat` | 포트→주소 (정상 ~113KB, 6ABL/4ABL 포함) |
| `LOGPRESSO_HID_INOUT_*.csv` | HID IN/OUT 로그 |

## 스크립트 (이 폴더)
- `hid_zone_csv_cre.py` : layout → HID_Zone_Master CSV (없으면 자동)
- `gen_near_hid4.py` : 리프터 → 근처 HID4 매핑
- `count_lifter_inout.py` : 1분당 결과 CSV (메인)
- `make_map.py` : (선택) 2D 지도

## 실행 순서
### STEP 1 — 리프터 → 근처 HID4 매핑
```
python gen_near_hid4.py BR.layout.zip BR.station.dat HID_Zone_Master_M16A_BR.csv 리프터_근처HID4.csv
```
출력 `리프터_근처HID4.csv`: `Lifter, FAB, 근처HID4, 경계mm`
(HID_Zone_Master CSV 없으면 먼저 `python hid_zone_csv_cre.py BR.layout.zip HID_Zone_Master_M16A_BR.csv`)

### STEP 2 — 1분당 개수 결과 (핵심)
```
# 전체 시계열:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_M16A_BR.csv 결과.csv
# 특정 분:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_M16A_BR.csv --at "2026-04-21 14:04"
```

## 결과.csv 컬럼
`시각, Lifter, FAB, 근처HID, 경계mm, 진입개수, 점유차량수, MAX_VHL, 포화도%`
- **진입개수** = 그 1분에 HID로 들어온 차량 (TO_HIDID, 중복제거) ← 핵심 "개수"
- **점유차량수** = 그 시점 머무는 차량 (로그 `HID_VALUE`)
- **MAX_VHL** = HID 최대수용 (Vehicle_Max)
- **포화도%** = 점유 ÷ MAX

## 핵심 규칙
- 1분 단위 / 리프터별 / 차량 중복제거
- 근처HID4 = 리프터에 경계 가장 가까운 HID4(1~37). HID_INOUT 로그가 HID4만 기록하므로 HID4 기준.
- 같은 HID4 구역 리프터는 같은 값.

## 주의
- "리프터 0기" → station.dat 손상(HTML 86KB). 정상 113KB 사용.
- "layout.xml 없음" → .zip 경로 주면 됨.
- 출력은 실행 폴더에 생성.
