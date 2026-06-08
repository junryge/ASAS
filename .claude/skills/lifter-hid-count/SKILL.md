---
name: lifter-hid-count
description: >
  OHT 리프터 근처 HID 구역의 차량(VHL/OHT) 개수를 1분 단위로 집계하고 2D 지도로
  시각화한다. 사용자가 FAB 레이아웃(layout.zip), station.dat, HID IN/OUT 로그
  (LOGPRESSO_HID_INOUT_*.csv)를 줄 때 사용. "리프터 근처 HID 차량수", "HID별 1분
  개수", "리프터 HID 매핑", "리프터 지도" 같은 요청에 발동. (M16A_BR 등 SK하이닉스
  OHT 데이터)
---

# 리프터 근처 HID 차량수 집계 스킬

리프터(`*ABL*`)별 **근처 HID4 구역**을 정하고, 그 구역에 **1분당 들어오는 차량 수**
(중복제거)를 집계한다. 2D 지도 시각화도 제공.

## 입력 파일 (사용자가 제공)
| 파일 | 설명 |
|------|------|
| `<PREFIX>.layout.zip` | FAB 레이아웃 (내부 layout/layout.xml). 예: BR.layout.zip |
| `<PREFIX>.station.dat` | 포트→주소 매핑. 예: BR.station.dat (정상 ~113KB, 6ABL/4ABL 포함) |
| `LOGPRESSO_HID_INOUT_*.csv` | HID IN/OUT 이벤트 로그 (FROM_HIDID/TO_HIDID/VHL_ID/_time) |

> 주의: station.dat 가 깨졌으면(예: HTML 86KB) 리프터 0기로 나온다. 원본(113KB)을 써야 함.

## 처리 단계 (스크립트 4개, 이 폴더에 있음)

### STEP 1 — HID 구역 마스터 생성 (필요시 자동)
```
python hid_zone_csv_cre.py <PREFIX>.layout.zip HID_Zone_Master_<FAB>_<PREFIX>.csv
```
layout.xml 의 McpZone 을 파싱해 HID 구역(IN/OUT lane, Zone_ID) CSV 생성.
(make_map.py / gen_near_hid4.py 가 없으면 자동 호출하기도 함)

### STEP 2 — 리프터 → 근처 HID4 매핑
```
python gen_near_hid4.py <PREFIX>.layout.zip <PREFIX>.station.dat HID_Zone_Master_<FAB>_<PREFIX>.csv 리프터_근처HID4.csv
```
각 리프터에 경계(lane)가 가장 가까운 HID4(1~37) 구역을 매핑.
출력 `리프터_근처HID4.csv`: `Lifter, FAB, 근처HID4, 경계mm`
- 경계mm=0 → 리프터 포트가 그 HID lane 노드와 동일(직결, 가장 정확)
- HID_INOUT 로그는 HID4(1~37)만 기록하므로 HID4 기준이어야 카운트 가능

### STEP 3 — 1분당 리프터 근처 차량수 (핵심 산출물)
```
# 전체 1분 시계열:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv 결과.csv
# 특정 분만:
python count_lifter_inout.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv --at "2026-04-21 14:04"
```
출력 `결과.csv`: `시각, Lifter, FAB, 근처HID, 경계mm, 근처차량수`
- 1분 단위 / 리프터별 / 차량(VHL_ID) 중복제거
- 같은 HID4 구역 리프터는 같은 값 (구역 단위)

### (선택) 2D 지도
```
python make_map.py <PREFIX>.layout.zip BR.map.html <PREFIX>.station.dat
```
출력 `BR.map.html`(실행 폴더): 노드/연결 + 리프터 박스 + 근처 HID 라벨 `HID33 (24mm)`.
`리프터_근처HID4.csv` 가 같은 폴더에 있으면 그 매핑(카운트와 동일)으로 라벨링.
조작: 휠=확대, 드래그=이동, H/F=좌우/상하 반전, R=리셋.

## 표준 실행 순서
1. 사용자가 준 layout.zip / station.dat / HID_INOUT.csv 를 작업 폴더에 둔다.
2. STEP 2 (gen_near_hid4) 실행 → `리프터_근처HID4.csv` (없으면 STEP1 자동).
3. STEP 3 (count_lifter_inout) 실행 → `결과.csv` (또는 --at 로 특정 분).
4. 필요시 STEP(지도) 실행.
5. 결과 요약(붐비는 리프터 상위 등)을 사용자에게 보고.

## 핵심 개념
- **HID** = OHT 레일을 나눈 인터록 구역. HID_INOUT 로그가 차량의 HID 간 이동을 기록.
- **IN(TO_HIDID)** = 그 HID로 진입, **OUT(FROM_HIDID)** = 진출.
- **근처 HID4** = 리프터에 가장 가까운 HID4(1~37) 구역. HID_INOUT 로그로 셀 수 있는 단위.
- **차량 중복제거** = 한 분에 같은 VHL_ID 는 1대로 계산.

## 자주 나는 문제
- "리프터 0기" → station.dat 손상(HTML로 덮어쓰임). 정상 station.dat(113KB) 사용.
- "layout.xml 없음" → .zip 경로를 주면 됨 (스크립트가 zip 내부에서 추출).
- 출력 파일은 **명령 실행한 폴더**에 생성됨 (하위 MAP 폴더 아님).
- HID4 외 작은 베이존(10xxx, HID3)은 HID_INOUT 로그에 없음 → HID4 기준만 가능.
