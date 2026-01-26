# M14 OHT2 레이아웃 데이터 분석 보고서

**대상**: SK하이닉스 M14 반도체 공장 OHT 시스템  
**분석일**: 2025년 2월  
**설정버전**: 2025/02/07-09:09

---

## 1. 시스템 개요

| 항목 | 값 |
|------|-----|
| 프로젝트명 | M14-Pro |
| 클라이언트 | HYNIX |
| 맵 버전 | M14-Pro Ver.1.22.2 (2023/08/01) |
| 설정 버전 | 08.55.08.00 |
| 플랫폼 | Linux |
| 파일 크기 | 211.4 MB (2,400,315 라인) |

---

## 2. 시스템 규모

### 2.1 레이아웃 통계

| 구성 요소 | 수량 | 설명 |
|-----------|------|------|
| Address | 9,404개 | OHT 레일 주소 포인트 |
| Station | 22,972개 | 로딩/언로딩 스테이션 |
| NextAddr | 18,806개 | 주소 연결 정보 |

### 2.2 최대 용량

| 설정 | 값 |
|------|-----|
| 최대 장비 연결 | 4,000 |
| 최대 OHT 차량 | 2,000 |
| 최대 이송 작업 | 4,000 |
| 간접 통신 장비 | 1,000 |

### 2.3 레이아웃 파라미터

| 파라미터 | 값 |
|----------|-----|
| 도면 영역 | 11,389 x 4,769 |
| 스케일 | 30.0 |
| 펄스레이트 Lift | 0.00335 |
| 펄스레이트 Slide | 0.002 |
| 펄스레이트 Turn | 0.004263483 |
| Junction Entry Offset | 1,900mm |
| Junction Exit Offset | 900mm |

---

## 3. 스케줄러 설정

### 3.1 핵심 파라미터

| 설정 | 값 | 설명 |
|------|-----|------|
| SCH_MODE | 3 | 동적 최적화 모드 |
| SCH_MODE_INTERVAL | 100ms | 스케줄 실행 간격 |
| HOTLOT_PRIORITY | 99 | HotLot 우선순위 |
| HOTLOT_TIMEOUT | 120초 | HotLot 유효시간 |
| BUMP_DISTANCE | 19,932mm | 충돌 방지 거리 |
| DISPATCH_DISTANCE | 5,779mm | 디스패치 거리 |
| BRANCH_DISTANCE | 4,929mm | 분기 감지 거리 |
| COMMUNICATION_TIMEOUT | 30,000ms | 통신 타임아웃 |
| STATUS_REPORT_INTERVAL | 10,000ms | 상태 리포트 간격 |

### 3.2 곡선 반경별 속도

| 반경 | 진입 | 곡선 | 출구 |
|------|------|------|------|
| R400 | 8 | 8 | 13 |
| R450 | 16 | 14 | 16 |
| R500 | 11 | 11 | 17 |
| R600 | 11 | 11 | 14 |

---

## 4. 파일 구조

```
OHT2/
├── mcp75.cfg              (9MB)    MCP 메인 설정
├── station.dat            (3.5MB)  스테이션 바이너리
├── inactive_SCH_1.dat     (378B)   비활성 LANE 설정
└── layout/
    ├── MCP/
    │   ├── system.cfg              시스템 옵션
    │   ├── scheduler.cfg           스케줄러 설정
    │   ├── pio.cfg                 PIO 인터페이스
    │   ├── secs.cfg                SECS 통신 설정
    │   ├── vhl_speed.cfg           차량 속도 설정
    │   └── ...
    └── layout/
        ├── layout.xml     (211MB)  메인 레이아웃
        └── route.xml      (22KB)   루트 학습 데이터
```

---

## 5. 루트 학습 현황

총 **24개** 루트 정의 (DAIFUKU Station Editor 형식)

| 루트명 | 작업자 | 작업일 | 스테이션 |
|--------|--------|--------|----------|
| 4ABL3301_AO4 | LEEJOUNGWON | 2025/01/07 | 7591 |
| 4AFC3201 | CFI | 2025/02/06 | 30537-30540 |
| 4EFD2301_RE | KIM SANG HYUK | 2024/12/10 | 5494-5496 |
| 4KTV5601 | LEE | 2025/01/23 | 12054-12056 |
| 4KTV5902_TEA | SHINJEGEUN | 2024/12/03 | 12653-12655 |
| B01_4KTV0104 | LEEJOUNGWON | 2024/12/24 | 1029-1031 |
| B05_4KCW0502 | JUNGGEONHO | 2024/12/27 | 1891-1894 |
| B25_4EFD2501 | CHOIHYUNGWOO | 2025/01/08 | 5825-5827 |
| B25_4KEF2506 | junggeonho | 2025/01/10 | 5897-5899 |
| B39_4DTN3902 | CFI | 2024/12/30 | 8625-8626 |
| B52_4DSA5209 | KIMDONGHYEON | 2024/12/31 | 13744-13746 |
| B60_4KTV6002 | KIMHWANGRAE | 2024/12/04 | 12805-12807 |
| B61_4TPW6101 | shinjegeun | 2025/01/17 | 13053-13055 |
| RE_4DSU3902 | YUN SANG DO | 2024/12/30 | 8631-8632 |
| RE_4POL2104 | YUN SANG DO | 2025/01/15 | 4823 |

**작업자**: LEEJOUNGWON, CFI, KIM SANG HYUK, LEE, SHINJEGEUN, JUNGGEONHO, CHOIHYUNGWOO, KIMDONGHYEON, KIMHWANGRAE, YUN SANG DO, LEE JUHO, JGH

---

## 6. 비활성 LANE (5개)

| 시작 노드 | 종료 노드 |
|-----------|-----------|
| 1293 | 15121 |
| 1302 | 15060 |
| 1465 | 15178 |
| 1470 | 15197 |
| 13178 | 13179 |

---

## 7. 시스템 아키텍처

```
┌─────────────────────────────────────┐
│     MCS (Material Control System)   │
│            Host Server              │
└──────────────┬──────────────────────┘
               │ SECS/GEM
               ▼
┌─────────────────────────────────────┐
│        MCP75 Controller             │
│      (M14-Pro Ver.1.22.2)           │
│  ┌─────────┬─────────┬─────────┐    │
│  │Scheduler│Vehicle  │Station  │    │
│  │ (4000)  │Mgr(2000)│Mgr(22972)│   │
│  └─────────┴─────────┴─────────┘    │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────┐
│ ZCU  │  │ OHT  │  │ MTL  │
│(Zone)│  │(2000)│  │(Lift)│
└──────┘  └──────┘  └──────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Stations (22,972개)             │
│  DUAL_ACCESS / ZFS / UNIVERSAL      │
└─────────────────────────────────────┘
```

---

## 8. FTP 서버 설정

| 용도 | 경로 |
|------|------|
| Vehicle Log | MCP_LOWER:/home/mcp7/vhldata/ |
| Map Set | STEDIT_FTP_SVR:/STEDIT/MCP001/adjust |
| ZCU Data | MCP_LOWER:/home/mcp7/zcudata/ |

---

## 9. 주요 발견사항

**시스템 규모**
- 최대 2,000대 OHT 차량 운영 가능
- 22,972개 스테이션 네트워크
- 9,404개 주소 포인트, 18,806개 연결

**최근 활동**
- 루트 학습: 2024/12 ~ 2025/02 활발히 진행
- 마지막 설정 업데이트: 2025/02/07 09:09

**특이사항**
- 5개 LANE 비활성화 상태
- HotLot 우선순위 시스템 활성화 (Priority 99)
- 동적 루트 최적화 모드 사용 (SCH_MODE=3)

---

## 10. 용어 정리

| 용어 | 설명 |
|------|------|
| OHT | Overhead Hoist Transport - 천장 레일 자동 운반 시스템 |
| MCP | Material Control Point - 물류 제어 포인트 |
| ZCU | Zone Control Unit - 구역 제어 장치 |
| MTL | Material Transfer Lifter - 층간 이송 리프터 |
| FOUP | Front Opening Unified Pod - 웨이퍼 운반 용기 |
| HID | Hoist ID - 호이스트 식별자 |
| PIO | Parallel I/O - 장비 인터페이스 |
| SECS/GEM | 반도체 장비 통신 표준 프로토콜 |
| HotLot | 긴급/우선 처리 화물 |

---

*보고서 작성일: 2025-01-26*