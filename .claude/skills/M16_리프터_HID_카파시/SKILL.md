---
name: M16_리프터_HID_카파시
description: >
  M16A_BR OHT 리프터 근처 HID 구역의 용량(capacity)/포화도를 1분 단위로 산출한다.
  로그의 HID_VALUE(실제 점유)와 HID 용량(Vehicle_Max)으로 포화도%를 계산하고,
  HID 구역별 MAX VHL 수량까지 출력. LOGPRESSO_HID_INOUT 로그 + layout.zip +
  station.dat 를 줄 때 사용. "리프터 HID 용량", "포화도", "혼잡도", "카파시",
  "capacity", "MAX VHL", "병목", "점유율" 같은 요청에 발동. (SK하이닉스 M16A_BR OHT)
---

# M16 리프터 HID 카파시 스킬 (용량/포화도)

M16A_BR 리프터(`*ABL*`)별 **근처 HID4 구역**의 **점유 vs 용량(포화도)** 를 1분 단위로 산출.
개수만 필요하면 `M16_리프터_HID_일반스킬` 사용 — 이 스킬은 용량/포화도 + HID구역별 MAX 전용.

## 개수 vs 용량(이 스킬)
| | 일반스킬 | 카파시(이 스킬) |
|--|--|--|
| 값 | 1분간 들어온 차량(흐름) | 그 시점 머무는 차량 / 용량(포화) |
| 점유원 | - | 로그 **HID_VALUE** (실제 점유, ≤Vehicle_Max 검증됨) |
| 산출 | 진입개수 | 점유차량수, MAX_VHL, 포화도% |
| 단위 | 리프터별 | 리프터별 + **HID구역별** 둘 다 |

## 입력 (사용자 제공)
| 파일 | 설명 |
|------|------|
| `BR.layout.zip` | 레이아웃 |
| `BR.station.dat` | 포트→주소 (정상 ~113KB) |
| `LOGPRESSO_HID_INOUT_*.csv` | HID IN/OUT 로그 (HID_VALUE 포함) |

## 스크립트 (이 폴더)
- `hid_zone_csv_cre.py` : HID_Zone_Master CSV (Vehicle_Max/Precaution 포함)
- `gen_near_hid4.py` : 리프터 → 근처 HID4 매핑
- `count_capacity.py` : 용량/포화도 산출 (메인)

## 실행 순서
### STEP 1 — 매핑
```
python gen_near_hid4.py BR.layout.zip BR.station.dat HID_Zone_Master_M16A_BR.csv 리프터_근처HID4.csv
```
### STEP 2 — 용량/포화도 (핵심)
```
# 전체 시계열:
python count_capacity.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_M16A_BR.csv 용량.csv
# 특정 분:
python count_capacity.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_M16A_BR.csv --at "2026-04-21 14:04"
```

## 출력 (2개 자동 생성)
1. `용량.csv` (리프터별): `시각, Lifter, FAB, 근처HID, 경계mm, 점유차량수, 용량Max, 혼잡도%`
2. `용량_HID구역.csv` (HID구역별, 중복제거): `시각, HID, MAX_VHL, 주의_VHL, 점유차량수, 포화도%, 소속리프터`
   - **MAX_VHL** = 그 HID 최대 수용 (Vehicle_Max)
   - **주의_VHL** = 주의 임계 (Vehicle_Precaution)
   - **포화도%** = 점유차량수(HID_VALUE) ÷ MAX_VHL × 100

## 계산 규칙
- **점유차량수 = 로그 HID_VALUE** (그 HID의 실제 차량수). 분당 peak.
  (직접 IN-OUT 추적은 누적오류로 100% 초과 → 사용 금지. HID_VALUE가 정답.)
- **포화도%** = peak HID_VALUE ÷ Vehicle_Max × 100 (항상 ≤100%)
- **순간 병목** = 포화도 급등 구간. Vehicle_Precaution 초과 = 혼잡 경고.

## 주의
- HID_INOUT 로그는 HID4(1~37)만 기록 → HID4 기준. (작은 베이존 10xxx 불가)
- station.dat 깨지면 리프터 0기 → 정상 113KB 사용.
- HID37 등 max=5짜리 죽은 라인은 매핑에서 제외됨(트래픽 0).
- 출력은 실행 폴더에 생성.
