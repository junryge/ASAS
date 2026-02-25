# AGV(Automated Guided Vehicle) 시스템 통신 인터페이스 설계서

**Communication Interface Design Specification**

| 항목 | 내용 |
|------|------|
| 문서 버전 | v2.0.0 |
| 작성일 | 2026-02-25 |
| 작성 근거 | FabScope-MCP 통신사양서, SysView 통신사양서, AMP API Guide, FMS 메시지 샘플사양서, Atlas Server Java 소스 |
| 적용 대상 | AGV (Automated Guided Vehicle) |
| 관련 시스템 | FabScope, SysView, CLW MCP7, AMP, Atlas Server, Logpresso |

---

## 목차

1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [AGV 상태 보고 (Text ID:2)](#3-agv-상태-보고-fabscope--mcp-text-id2)
4. [공통 메시지 인터페이스](#4-공통-메시지-인터페이스)
5. [AMP Remote Interface](#5-amp-remote-interface)
6. [Atlas Server — UDP 수신 구현 (Java)](#6-atlas-server--udp-수신-구현-java)
7. [Logpresso 데이터 저장](#7-logpresso-데이터-저장)
8. [상태 코드 매핑](#8-상태-코드-매핑-fabscope--amp--java-enum)
9. [개정 이력](#9-개정-이력)

---

## 1. 개요

### 1.1 문서 목적

AGV 시스템과 상위 시스템(FabScope, AMP, Atlas Server) 간 통신 프로토콜을 정의하고, 메시지 포맷 및 데이터 필드의 상세 규격을 제시합니다. 또한 Vehicle 상태 보고 메시지 체계와 Atlas Server의 UDP 수신 및 Logpresso DB 저장 방식을 명시합니다.

### 1.2 적용 범위

- 적용 시스템: AGV, CLW MCP7, FabScope, AMP, Atlas Server
- 통신 프로토콜: UDP/IP(FabScope↔MCP), TCP/IP(AMP↔설비), UDP(Atlas Server)
- FAB 대상: M14A, M14B, M16A, M16B

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| AGV | Automated Guided Vehicle - 자동 유도 차량 |
| OHT | Overhead Hoist Transport - 높이 운반 시스템 |
| MCP | Material Control Port - 재료 제어 포트 |
| AMP | Automatic Monitoring Platform - 자동 모니터링 플랫폼 |
| FMS | Fab Management System - 팹 관리 시스템 |
| FOUP | Front Opening Unified Pod - 전면 개폐식 운반 용기 |
| E84 | Enhanced Equipment 8th & 4th pin - 장비 통신 표준 |
| PIO | Programmable Input/Output - 프로그래밍 가능 입출력 |
| Logpresso | 데이터 수집/저장 플랫폼 (Tuple 기반 API 제공) |
| Atlas Server | Java 기반 UDP 수신 서버 (MCP로부터 AGV 상태 수신) |

---

## 2. 시스템 아키텍처

### 2.1 전체 시스템 구성도

```
HOST/MES → FabScope (SysView + MSS) → CLW MCP7 → AGV
AMP ←(TCP/IP)→ AGV Controller
Atlas Server ←(UDP)→ MCP → Logpresso DB
```

### 2.2 통신 계층별 역할

| 계층 | 시스템 | 역할 |
|------|--------|------|
| 상위 감시 | FabScope | 전체 AGV 상태 모니터링 및 제어 |
| 모니터링 | AMP | 실시간 장비 성능 모니터링 |
| 데이터 수집 | Atlas Server | Logpresso DB로 AGV 상태 저장 |
| 반송 제어 | CLW MCP7 | AGV 경로 및 작업 할당 제어 |
| 하위 장비 | AGV | 자재 운반 및 상태 보고 |

### 2.3 통신 프로토콜

| 연결 | 시스템 | 프로토콜 | 포트 |
|------|--------|----------|------|
| FabScope↔MCP | SysView | UDP | 3600 |
| FabScope↔MCP | MSS | UDP | 3500 |
| AMP↔설비 | AGV Controller | TCP/IP | 10000 |
| MCP→Atlas | UDP Server | UDP | 설정포트 |

---

## 3. AGV 상태 보고 (FabScope ← MCP: Text ID:2)

### 3.1 보고 조건

- MCP7 기동시
- Vehicle 상태 변화시
- 상태보고요구(ID:51) 수신시
- 5초 주기 정기 보고

### 3.2 메시지 필드 구성

| No | 텍스트ID | 필드명 | 설명 | 값 예 |
|----|----------|--------|------|-------|
| 0 | 2 | 텍스트ID | 메시지 타입 | 2 |
| 1 | | MCP명칭 | MCP 장비명 | OHT |
| 2 | | Vehicle명 | AGV 이름 | V047 |
| 3 | | 상태 | 1:운전~11:HT-STOP | 1 |
| 4 | | 재하정보 | FOUP 적재 여부 | 1 |
| 5 | | Error Code | 오류 코드 | 0000 |
| 6 | | 통신상태 | 통신 연결 상태 | 1 |
| 7 | | 현재번지 | 현재 위치 ID | 1232 |
| 8 | | 거리 | 목적지까지 거리(m) | 0 |
| 9 | | 다음번지 | 다음 목표 위치 | 1202 |
| 10 | | 실행Cycle | 현재 사이클 번호 | 4 |
| 11 | | Vehicle실행Cycle진척 | 사이클 진행률 | 4 |
| 12 | | CarrierID | 운반중인 FOUP ID | PIN2702 |
| 13 | | Destination | 목적지 코드 | 20308 |
| 14 | | E/M상태 | 장비/운영자 상태 | 00000000 |
| 15 | | GroupID | 그룹 할당 ID | 0000 |
| 16 | | 반송원Port | 출발지 포트 | IR5S005S_2 |
| 17 | | 반송처Port | 도착지 포트 | STB031-R08 |
| 18 | | 반송우선도 | 작업 우선 순위 | 50 |
| 19 | | 작업상태상세 | 작업 세부 상태 | 0 |
| 20 | | 대차주행거리 | AGV 누적 주행 거리 | 0 |
| 21 | | CommandID | 현재 작업 명령 ID | |
| 22 | | Bay명칭 | 위치 베이 정보 | |
| 23 | | ETA | 예상 도착 시간 | |
| 24 | | 예약CommandID | 다음 예약 명령 | |

### 3.3 FMS 메시지 샘플

```
2,OHT,V047,1,1,0000,1,1232,0,1202,4,4,PIN2702,20308,00000000,0000,IR5S005S_2,STB031-R08,50,0,0
```

---

## 4. 공통 메시지 인터페이스

### 4.1 MCP On-Line 보고 (Text ID:1)

- 보고 주기: 5초
- 다운 판정: 15초

| 텍스트ID | MCP명칭 | 필드명 | 설명 |
|----------|---------|--------|------|
| 1 | OHT | Control상태 | 제어 시스템 상태 |
| | | TSC상태 | TSC 통신 상태 |
| | | Alarm상태 | 알람 여부 |
| | | MCP상태구분 | MCP 운영 상태 |

### 4.2 기기 상태 보고 (Text ID:4)

| 텍스트ID | 기종번호 | 기기명칭 | 상태 | Error Code |
|----------|----------|----------|------|------------|
| 4 | 00: CLW MCP | 장비 이름 | 1~5 | 0000 |
| | 10: VHL | | | |
| | 50: BZ | | | |
| | 60: MTL | | | |
| | 91: AD/FD | | | |
| | 92: HID | | | |
| | 93: FFU | | | |

### 4.3 대차 주행 경로 보고 (Text ID:15)

AGV의 현재 위치와 예정된 경로 정보를 주기적으로 보고합니다.

### 4.4 MSS계 메시지

- Text ID:3 — 이상/복구 메시지
- Text ID:13 — 작업 데이터 보고
- Text ID:17 — 삽체/정체 상태 보고

---

## 5. AMP Remote Interface

### 5.1 초기화 및 시작

```
Initialize(EqpID, ExeName, Version, PortNo, MonitoringTime, DelayTime)
→ Start()
→ Stop()
```

### 5.2 필수 수집 항목

- ControlState: 제어 상태
- SCState: 스캐너 상태
- EQMode: 장비 모드
- AlarmInfo: 알람 정보
- CarrierInfo: 운반품 정보
- TrInfo: 전송 정보

### 5.3 Car 클래스 (AGV 전용)

| 속성명 | 설명 |
|--------|------|
| EqpID | 장비 ID |
| FaultCode | 오류 코드 |
| CarrierID | 운반품 ID |
| Kind | AGV 종류 |
| UnitState | 유닛 상태 |
| ProcessStatus | 처리 상태 |
| Location | 현재 위치 |
| XY Position | X, Y 좌표 |
| VehicleState | 1:REMOVED ~ 14:AVOID |
| AssignEnable | 작업 할당 가능 여부 |
| GroupID | 그룹 ID |

### 5.4 Event 인터페이스

- **MonitorGetData**: 모니터링 데이터 수신
- **OperationEvent**: 운영 이벤트
- **TransferEvent**: 운반 이벤트
- **CarrierEvent**: 운반품 이벤트
- **ControlStatusEvent**: 제어 상태 변경
- **EQModeEvent**: 장비 모드 변경
- **GlobalTransferEvent**: 전역 운반 이벤트
- **ErrorEvent**: 오류 이벤트

---

## 6. Atlas Server — UDP 수신 구현 (Java)

### 6.1 OhtUdpListener

DatagramSocket을 이용하여 UDP 메시지를 수신하며, **1500byte** 크기의 버퍼를 사용합니다. 수신된 데이터는 DataService 큐로 전달되어 처리됩니다.

```java
// OhtUdpListener 핵심 구조
DatagramSocket socket = new DatagramSocket(port);
byte[] buffer = new byte[1500];
DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
socket.receive(packet);
// → DataService 큐로 전달
```

### 6.2 OhtMsgWorkerRunnable

CSV 파싱: `splitPreserveAllTokens`를 사용하여 모든 토큰 보존

Text ID 라우팅:

```java
switch (textId) {
    case "2":  // Vehicle 상태 처리
    case "1":  // MCP 상태 처리
    case "4":  // 기기 상태 처리
}
```

### 6.3 Vehicle 상태 처리

| 항목 | 설명 | 매핑 대상 |
|------|------|-----------|
| Vhl Object | Vehicle 객체 업데이트 | VHL_STATE enum |
| VHL_STATE | Vehicle 기본 상태 | IDLE, MOVING, UNLOAD, LOAD |
| VHL_DET_STATE | Vehicle 상세 상태 | 0:NONE ~ 106:PARKING_MOVING |
| RUN_CYCLE | 현재 사이클 상태 | 0:NONE ~ 2F:EVACUATION |

### 6.4 RailEdge 속력 업데이트

가중 이동 평균(Weighted Moving Average)을 사용하여 경로상의 속력을 계산합니다.

- `getCost()`: 인접 경로의 비용 산출
- `getDensity()`: 교통 밀도 반영

---

## 7. Logpresso 데이터 저장

> **CRITICAL**: 데이터는 반드시 Logpresso DB에 저장해야 합니다. CSV 파일로 저장하지 마세요.

### 7.1 Tuple API

```java
// 데이터 삽입
LogpressoAPI.setInsertTuples(tableName, tuples, timeout);
Util.insertInLogpressoDatabase(tuples, tableName, caller);
```

### 7.2 테이블 구조

**ATLAS_OHT_HID_OFF**

| 컬럼 | 설명 |
|------|------|
| FAB_ID | FAB 식별자 |
| MCP_NM | MCP 이름 |
| VHL_ID | Vehicle ID |
| HID_ID | HID ID |
| OFF_TIME | Off 시간 |
| FROM_ADDRESS | 출발지 주소 |
| TO_ADDRESS | 도착지 주소 |

**ATLAS_HID_INFO**

| 컬럼 | 설명 |
|------|------|
| FAB_ID | FAB 식별자 |
| MCP_NM | MCP 이름 |
| HID_ID | HID ID |
| START | 시작 여부 |
| ADDRESS | 주소 |

**ATLAS_RAIL_TRAFFIC**

| 컬럼 | 설명 |
|------|------|
| createTime | 생성 시간 |
| fabId | FAB 식별자 |
| mcpName | MCP 이름 |
| railEdgeId | Rail Edge ID |
| velocity | 속력 |
| maxVelocity | 최대 속력 |
| absoluteVelocity | 절대 속력 |
| vhlCnt | Vehicle 수 |
| passCnt | 통과 수 |
| HID_ID | HID ID |

### 7.3 TrafficBatch

1분 주기의 Quartz Job으로 RailEdge별 속력 데이터를 수집하여 Logpresso에 일괄 저장합니다.

### 7.4 Logpresso 조회

```java
XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");
XmlUtil.loadLogpressoParm();
```

### 7.5 Logpresso API 요약

| API명 | 파라미터 | 반환값 |
|-------|----------|--------|
| setInsertTuples | tableName, tuples, timeout | Insert 결과 |
| selectLogpressoQuery | queryName | 조회 결과 목록 |
| loadLogpressoParm | (없음) | 설정값 |

---

## 8. 상태 코드 매핑 (FabScope ↔ AMP ↔ Java Enum)

### 8.1 Vehicle 상태 3-Way 매핑

| 상태코드 | FabScope | AMP VehicleState | Java VHL_STATE |
|----------|----------|------------------|----------------|
| 1 | 운전 | MOVING | MOVING |
| 2 | 정지 | IDLE | IDLE |
| 3 | 상차 | LOAD | LOAD |
| 4 | 하차 | UNLOAD | UNLOAD |
| 5 | 복귀 | RETURN | RETURN |
| 6 | 검사 | INSPECT | INSPECT |
| 7 | 충전 | CHARGING | CHARGING |
| 8 | 대기 | WAITING | WAITING |
| 9 | 오류 | FAULT | FAULT |
| 10 | 비상정지 | ESTOP | ESTOP |
| 11 | HT-STOP | HT-STOP | HT_STOP |

### 8.2 VHL_DET_STATE (상세 상태)

범위: 0:NONE ~ 106:PARKING_MOVING

| 범위 | 분류 |
|------|------|
| 0~10 | 기본 상태 |
| 11~50 | 운행 중 상태 |
| 51~100 | 작업 상태 |
| 101~106 | 특수 상태 |

### 8.3 RUN_CYCLE (사이클 상태)

범위: 0:NONE ~ 2F:EVACUATION

| 범위 | 분류 |
|------|------|
| 0~5 | 준비 단계 |
| 6~15 | 수송 단계 |
| 16~25 | 작업 단계 |
| 26~2F | 완료/복귀 단계 |

### 8.4 VHL_CYCLE (차량 사이클)

범위: 0:NONE ~ 8:INPUT

| 값 | 상태 |
|----|------|
| 0 | 없음 (NONE) |
| 1 | 초기화 |
| 2 | 경로탐색 |
| 3 | 이동 |
| 4 | 도착 |
| 5 | 상차 준비 |
| 6 | 상차 |
| 7 | 하차 |
| 8 | 입력 (INPUT) |

---

## 9. 개정 이력

| 버전 | 작성일 | 작성자 | 주요 내용 |
|------|--------|--------|-----------|
| v1.0.0 | 2026-02-25 | 설계팀 | 초판 작성 |
| v2.0.0 | 2026-02-25 | 설계팀 | Atlas Server UDP 수신 및 Logpresso DB 저장 추가, AGV 전용 분리 |

---

**END OF DOCUMENT**
