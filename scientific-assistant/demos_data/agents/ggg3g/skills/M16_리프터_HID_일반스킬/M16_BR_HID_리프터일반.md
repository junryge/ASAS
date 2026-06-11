---
name: M16_BR_HID_리프터일반
description: >
  M16A_BR OHT 리프터별 근처 HID4 구역의 '근처차량수'(1분당 그 구역을 거친 고유 차량 수)를
  1분 단위로 집계한다. LOGPRESSO_HID_INOUT 로그 + 리프터_근처HID4.csv 를 줄 때 사용.
  "리프터 HID 개수", "1분당 차량수", "근처차량수", "리프터 근처 차량",
  "M16 리프터 HID" 같은 요청에 발동. (SK하이닉스 M16A_BR OHT)
---

# M16 리프터 HID 일반 스킬 (근처차량수)

M16A_BR 리프터(`*ABL*`)별 **근처 HID4 구역**을 1분 동안 거친 **고유 차량 수(근처차량수)** 를 산출.
개수만 본다 — 포화도/용량 분석은 카파시 스킬(`count_capacity.py`).

## 입력 (사용자 제공)
| 파일 | 설명 |
|------|------|
| `LOGPRESSO_HID_INOUT_*.csv` | HID IN/OUT 로그 (_time/FROM_HIDID/TO_HIDID/VHL_ID) |
| `리프터_근처HID4.csv` | 리프터→근처HID4 매핑 (이 폴더에 동봉) |

## 스크립트 (이 폴더)
- `count_lifter_inout.py` : 1분당 근처차량수 결과 CSV (메인)
- `gen_near_hid4.py` : (사전 1회) 리프터 → 근처 HID4 매핑 생성
- `hid_zone_csv_cre.py`, `make_map.py` : (선택) 매핑 생성 보조/지도

## 실행 (핵심 — 입력 2개)
```
# 전체 시계열:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv 결과.csv
# 특정 분:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv --at "2026-04-21 14:04"
```
※ HID_Zone_Master 는 이 스킬(개수)엔 불필요. (포화도 보는 카파시 스킬에서만 사용)

## 결과.csv 컬럼
`시각, Lifter, FAB, 근처HID, 경계mm, 근처차량수`
- **근처차량수** = 그 1분에 그 HID4 구역을 거친(FROM 또는 TO 가 그 HID) **고유 차량(VHL_ID) 수**
- 같은 HID4 를 근처로 두는 리프터는 같은 값 (HID 단위 집계라서)

## 핵심 규칙
- 1분 단위 / 리프터별 / 차량 중복제거
- 근처HID4 = 리프터에 경계 가장 가까운 HID4(1~37). HID_INOUT 로그가 HID4만 기록하므로 HID4 기준.
- 같은 HID4 구역 리프터는 같은 값.

## 주의
- "리프터 0기" → station.dat 손상(HTML 86KB). 정상 113KB 사용.
- "layout.xml 없음" → .zip 경로 주면 됨.
- 출력은 실행 폴더에 생성.
