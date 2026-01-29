# JAVA_SIN - HID Zone 분석 코드

## 파일 구조

```
JAVA_SIN/
├── HidZoneAnalyzer.java    # HID Zone IN/OUT 분석
├── LogpressoExporter.java  # FABID별 분리 저장 (로그프레소용)
└── README.md
```

## 주요 기능

### 1. HidZoneAnalyzer.java
- HID_ZONE_Master.csv 로드
- Zone별 IN/OUT 카운트 분석
- HID 이벤트 처리
- FABID별 이벤트 분리

### 2. LogpressoExporter.java
- FABID별 CSV/JSON 파일 분리 저장
- 로그프레소 임포트용 포맷 생성
- 통계 요약 출력

## 사용법

### 컴파일
```bash
javac -encoding UTF-8 HidZoneAnalyzer.java LogpressoExporter.java
```

### 실행
```bash
java HidZoneAnalyzer
java LogpressoExporter
```

## 출력 파일

### FABID별 분리 저장
```
output_logpresso/
├── FABID_FAB1_hid_events.csv
├── FABID_FAB1_hid_events.json
├── FABID_FAB2_hid_events.csv
├── FABID_FAB2_hid_events.json
└── ...
```

### CSV 포맷
```csv
timestamp,zone_id,event_type,vehicle_id,fab_id,from_node,to_node
2024-01-01 12:00:00.000,1,IN,VH001,FAB1,3048,3023
```

### JSON 포맷 (로그프레소용)
```json
[
  {
    "timestamp": "2024-01-01 12:00:00.000",
    "zone_id": 1,
    "event_type": "IN",
    "vehicle_id": "VH001",
    "fab_id": "FAB1",
    "from_node": 3048,
    "to_node": 3023
  }
]
```

## 데이터 설명

| 필드 | 설명 |
|------|------|
| zone_id | HID Zone ID |
| event_type | IN (진입) / OUT (진출) |
| vehicle_id | OHT 차량 ID |
| fab_id | FAB 식별자 |
| from_node | 시작 노드 |
| to_node | 종료 노드 |
