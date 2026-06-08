---
name: lifter-hid-capacity
description: >
  OHT 리프터 근처 HID 구역의 '용량(capacity)/혼잡도'를 1분 단위로 산출한다. HID 에
  들어와 안 나간 차량(점유)을 추적해 용량(Vehicle_Max) 대비 혼잡도(%)를 계산. 사용자가
  FAB 레이아웃(layout.zip), station.dat, HID IN/OUT 로그(LOGPRESSO_HID_INOUT_*.csv)를
  줄 때 사용. "리프터 HID 용량", "혼잡도", "capacity", "카파시톤", "점유율", "포화도"
  같은 요청에 발동. (SK하이닉스 M16A_BR 등 OHT 데이터)
---

# 리프터 근처 HID 용량/혼잡도 스킬 (카파시톤)

리프터(`*ABL*`)별 **근처 HID4 구역**의 **점유 차량수**를 추적해, 그 HID 의
**용량(Vehicle_Max) 대비 혼잡도(%)**를 1분 단위로 산출한다.
(개수만 필요하면 `lifter-hid-count` 스킬 사용 — 이 스킬은 '용량/혼잡도' 전용)

## 개수(count) vs 용량(capacity) 차이
| | lifter-hid-count | lifter-hid-capacity (이 스킬) |
|--|--|--|
| 값 | 1분간 들어온 차량 수 (흐름) | 그 시점 HID에 머무는 차량 수 / 용량 (포화) |
| 계산 | TO_HIDID 중복제거 카운트 | IN-OUT 추적한 점유(peak) ÷ Vehicle_Max |
| 산출 | 근처차량수 | 점유차량수, 용량Max, 혼잡도% |

## 입력 파일 (사용자가 제공)
| 파일 | 설명 |
|------|------|
| `<PREFIX>.layout.zip` | FAB 레이아웃 (내부 layout/layout.xml) |
| `<PREFIX>.station.dat` | 포트→주소 (정상 ~113KB, 6ABL/4ABL 포함) |
| `LOGPRESSO_HID_INOUT_*.csv` | HID IN/OUT 이벤트 로그 |

## 처리 단계 (스크립트는 이 폴더에)

### STEP 1 — (없으면) HID 구역 마스터
```
python hid_zone_csv_cre.py <PREFIX>.layout.zip HID_Zone_Master_<FAB>_<PREFIX>.csv
```
HID 구역의 Vehicle_Max / Vehicle_Precaution(용량) 포함 CSV 생성.

### STEP 2 — 리프터 → 근처 HID4 매핑
```
python gen_near_hid4.py <PREFIX>.layout.zip <PREFIX>.station.dat HID_Zone_Master_<FAB>_<PREFIX>.csv 리프터_근처HID4.csv
```
출력 `리프터_근처HID4.csv`: `Lifter, FAB, 근처HID4, 경계mm`

### STEP 3 — 용량/혼잡도 산출 (핵심)
```
# 전체 1분 시계열:
python count_capacity.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_<FAB>_<PREFIX>.csv 용량.csv
# 특정 분만:
python count_capacity.py LOGPRESSO_HID_INOUT_*.csv 리프터_근처HID4.csv HID_Zone_Master_<FAB>_<PREFIX>.csv --at "2026-04-21 14:04"
```
출력 2개 자동 생성:
- `용량.csv` (리프터별): `시각, Lifter, FAB, 근처HID, 경계mm, 점유차량수, 용량Max, 혼잡도%`
- `용량_HID구역.csv` (HID구역별, 중복제거): `시각, HID, MAX_VHL, 주의_VHL, 점유차량수, 포화도%, 소속리프터`
  - **MAX_VHL** = 그 HID에 들어올 수 있는 최대 차량수 (Vehicle_Max)
  - **주의_VHL** = 주의 임계 (Vehicle_Precaution)
  - **포화도%** = 점유차량수 ÷ MAX_VHL × 100

## 계산 규칙
- **점유** = HID 에 들어와서(IN/TO_HIDID) 아직 안 나간(OUT/FROM_HIDID) 차량 (차량단위, 중복없음)
- **분당값** = 그 분 동안의 **최대 점유(peak)**
- **혼잡도%** = peak ÷ Vehicle_Max × 100
- Vehicle_Precaution = 주의 임계(이 값 이상이면 혼잡 경고로 활용 가능)

## 표준 실행 순서
1. 입력 3개를 작업 폴더에 둔다.
2. STEP 2 → `리프터_근처HID4.csv` (없으면 STEP1 먼저).
3. STEP 3 → `용량.csv` (또는 --at).
4. 혼잡도 높은 리프터/시간대(예: >80%, Vehicle_Precaution 초과)를 보고.

## 주의
- HID_INOUT 로그는 HID4(1~37)만 기록 → HID4 기준만 가능 (작은 베이존 10xxx 불가).
- 점유는 하루 시작부터 IN-OUT 누적 추적이라 초반 몇 분은 과소집계될 수 있음.
- station.dat 깨지면 리프터 0기 → 정상 station.dat(113KB) 사용.
- 출력은 명령 실행 폴더에 생성.
