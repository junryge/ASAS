# 리프터 ↔ 근방 HID 매핑 & 2D 맵 (M16A_BR)

> OHT 리프터(`*ABL*`)별 **근방 HID 구역**을 구하고 2D 지도로 시각화하는 도구 모음.
> 검증: M16A_BR, 리프터 17기 (2026-06-07)

---

## 1. 산출물

| 파일 | 내용 |
|------|------|
| **`리프터_HID.csv`** | 리프터별 근방 HID 요약 (Lifter, FAB, HID Zone번호/HID_No) |
| `HID_Zone_Master_M16A_BR.csv` | HID 구역 원본 (HID_ID=리프터포트, Zone_ID=HID번호) |
| `BR.map.html` | 2D 지도 (리프터 + 근방 HID 표시) |

### `리프터_HID.csv` 컬럼
| 컬럼 | 설명 |
|------|------|
| Lifter | 리프터 장비명 (4=M14, 6=M16) |
| FAB | M14 / M16 |
| 근방HID_개수 | 그 리프터가 걸친 HID 구역 수 |
| 근방HID_Zone번호 | HID Zone_ID 목록 (예: `33; 11091`) |
| 근방HID_No | HID 정식번호 (예: `HID-OHT-033; HID-OHT-11091`) |
| 포트수 | 그 리프터의 IN/OUT 포트 수 |

---

## 2. 리프터 → 근방 HID (M16A_BR, 17기)

| Lifter | FAB | 근방 HID Zone |
|--------|-----|---------------|
| 4ABLD111 | M14 | 3 |
| 4ABLD112 | M14 | 10631, 10711 |
| 4ABLD121 | M14 | 10611, 10641 |
| 4ABLD122 | M14 | 3, 10681, 10711 |
| 4ABLD131 | M14 | 10641 |
| 4ABLD132 | M14 | 3, 10681, 10721 |
| 4ABLH401 | M14 | 10651 |
| 6ABL0111 | M16 | 11041, 11082, 11091 |
| 6ABL0112 | M16 | 11082, 11091, 11101, 11111 |
| 6ABL0121 | M16 | 33, 11091 |
| 6ABL0122 | M16 | 11091, 11101, 11121 |
| 6ABL6011 | M16 | 10771 |
| 6ABL6012 | M16 | 33, 10781 |
| 6ABL6021 | M16 | 34, 10771 |
| 6ABL6022 | M16 | 10771, 10811 |
| 6ABL6031 | M16 | 10831, 10851 |
| 6ABL6032 | M16 | 10831 |

---

## 3. 원리 — 어떻게 근방 HID 를 구하나

```
layout.xml(McpZone) ──hid_zone_csv_cre.py──> HID_Zone_Master_M16A_BR.csv
                                                  │ (HID_ID=리프터포트, Zone_ID=HID번호)
                                                  ▼
                          리프터포트 → Zone_ID 직접 매핑 → 리프터_HID.csv
```

- **HID** = OHT 레일의 인터록(고밀도) 구역. 차량 혼잡/지연 관리 단위.
- HID_Zone_Master CSV의 `HID_ID` 컬럼에 리프터 포트(`6ABL0111_AI313` 등)가,
  같은 행 `Zone_ID` 에 그 포트가 속한 HID 번호가 들어있다.
- 즉 **리프터 포트 → 그 포트가 속한 HID 구역** 을 그대로 읽으면 "근방 HID" 가 된다.
- 한 리프터의 포트들이 여러 HID 에 걸치면 근방 HID 도 여러 개.

---

## 4. 입력 파일 (필요한 것)

| 파일 | 역할 | 위치 |
|------|------|------|
| `BR.layout.zip` | 레이아웃 (내부 layout/layout.xml) | `MAP/M16A/` |
| `BR.station.dat` | 포트→주소 | `MAP/M16A/` |

> 둘 다 FAB 레이아웃 패키지의 설계 파일. layout.xml 은 수십 MB라 보통 zip 으로 보관.

---

## 5. 사용법

### 5.1 2D 지도 생성 (근방 HID 자동 포함)
```
python make_map.py MAP\M16A\BR.layout.zip BR.map.html MAP\M16A\BR.station.dat
```
- 출력 `BR.map.html` 은 **make_map.py 를 실행한 폴더**에 생성된다. (콘솔에 절대경로 표시)
- `HID_Zone_Master_M16A_BR.csv` 가 없으면 자동 생성한다.
- 지도 조작: 휠=확대/축소, 드래그=이동, H=좌우반전, F=상하반전, R=리셋
- 표시: ●IN(노랑)/OUT(초록), ▭리프터범위(M16주황/M14파랑), 박스 아래 `HID n`(근방 HID, 청록)

### 5.2 HID 원본 CSV 만 따로 생성
```
python hid_zone_csv_cre.py --fab M16A --layout BR
```

### 5.3 다른 FAB/구역 적용
`MAP/<FAB>/<PREFIX>.layout.zip` + `<PREFIX>.station.dat` 를 두고 동일하게 실행.
(`make_map.py`, `hid_zone_csv_cre.py` 는 같은 폴더에 함께 둘 것)

---

## 6. 파일 구성
```
실행폴더/
├── make_map.py                   # 2D 맵 생성
├── hid_zone_csv_cre.py           # HID_Zone_Master 생성기
├── 리프터_HID.csv                # ★ 리프터-근방HID 매핑 (결과)
├── HID_Zone_Master_M16A_BR.csv   # HID 구역 원본 (자동생성)
├── BR.map.html                   # 2D 지도 (결과)
└── MAP/M16A/
    ├── BR.layout.zip
    └── BR.station.dat
```
