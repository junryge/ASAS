# CNV(Conveyor) 시스템 통신 인터페이스 설계서

**Communication Interface Design Specification**

| 항목 | 내용 |
|------|------|
| 문서 버전 | v2.0.0 |
| 작성일 | 2026-02-25 |
| 작성 근거 | FabScope-MCP 통신사양서, SysView 통신사양서, AMP API Guide, Atlas Server Java 소스 |
| 적용 대상 | CNV (Conveyor System) |
| 관련 시스템 | FabScope, SysView, STK MCP7, SSS, AMP, Atlas Server, Logpresso |

---

## 목차

1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [CNV 기기 상태 보고 (Text ID:4)](#3-cnv-기기-상태-보고-text-id4)
4. [CNV 재하 정보 보고 (Text ID:202)](#4-cnv-재하-정보-보고-text-id202)
5. [공통 메시지 인터페이스](#5-공통-메시지-인터페이스)
6. [AMP Remote Interface](#6-amp-remote-interface)
7. [Atlas Server — UDP 수신 구현 (Java)](#7-atlas-server--udp-수신-구현-java)
8. [Logpresso 데이터 저장](#8-logpresso-데이터-저장)
9. [개정 이력](#9-개정-이력)

---

## 1. 개요

### 1.1 문서 목적

CNV 시스템과 상위 시스템(FabScope, AMP, Atlas Server) 간 통신 프로토콜 정의, 기기 상태 및 재하 정보 보고, Atlas Server UDP 수신 및 Logpresso DB 저장을 명시합니다.

### 1.2 적용 범위

- 적용 대상: CNV, STK MCP7, SSS, FabScope, AMP, Atlas Server
- 프로토콜: UDP/IP(FabScope↔MCP), TCP/IP(AMP↔설비), UDP(Atlas Server)
- FAB: M14A, M14B, M16A, M16B

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| CNV | Conveyor (컨베이어) |
| MCP | Material Control Point (물류 제어 포인트) |
| SSS | Stocker Subsystem (스토커 부분계) |
| STBC | Storage TRAY Buffer (스토커 트레이 버퍼) |
| AMP | Advanced Material Path (고급 물류 경로 시스템) |
| PIO | Physical Input/Output (물리 입출력) |
| Logpresso | 데이터 수집/저장 플랫폼 (Tuple 기반 API 제공) |
| Atlas Server | Java 기반 UDP 수신 서버 (Java-based UDP Receiver) |
| CnvEdge | Conveyor 구간 모델 (Conveyor Section Model) |

---

## 2. 시스템 아키텍처

### 2.1 전체 시스템 구성도

```
HOST/MES → FabScope (SysView + MSS) → STK MCP7/SSS → CNV
AMP ←(TCP/IP)→ CNV Controller
Atlas Server ←(UDP)→ MCP → Logpresso DB
```

### 2.2 통신 계층별 역할

| 계층 | 시스템 | 역할 |
|------|--------|------|
| 상위 감시 | FabScope | 전체 CNV 상태 모니터링 |
| 모니터링 | AMP | 실시간 장비 성능 모니터링 |
| 데이터 수집 | Atlas Server | Logpresso DB로 CNV 상태 저장 |
| 제어 | STK MCP7/SSS | CNV 제어 |
| 하위 장비 | CNV | Conveyor 운반 장치 |

### 2.3 통신 프로토콜

| 연결 | 프로토콜 | 포트 |
|------|----------|------|
| FabScope ↔ MCP (SysView) | UDP/IP | 3600 |
| FabScope ↔ MCP (MSS) | UDP/IP | 3500 |
| AMP ↔ 설비 | TCP/IP | 10000 |
| Atlas Server ↔ MCP | UDP | 설정포트 |

---

## 3. CNV 기기 상태 보고 (Text ID:4)

FabScope ← MCP

### 3.1 보고 조건

- MCP 기동시
- 상태 변화시
- 상태보고요구 수신시

### 3.2 메시지 구성

| 구성 요소 | 설명 |
|-----------|------|
| 텍스트ID | 4 |
| MCP명칭 | MCP 이름 |
| 기종번호 | Equipment Model Number |
| 기기명칭 | Equipment Name |
| 상태 | 1~5 (각 상태값 정의) |
| Error Code | 오류 코드 |

### 3.3 CNV 관련 기종번호

| 기종번호 | 장비명 |
|----------|--------|
| 100 | STK MCP7 |
| 303 | CNV/CONV |
| 320 | PIO_IF |
| 324 | IFP |
| 348 | PIO_IF_THROUGH |
| 428, 434, 437 | ARM_TFE variants |
| 808 | CLL |
| 871 | SINGLE_LIFTER |
| 872 | DOUBLE_LIFTER |
| 909 | MIF |
| 1111 | PNP |

---

## 4. CNV 재하 정보 보고 (Text ID:202)

FabScope ← SSS

### 4.1 보고 조건

- SSS 기동시
- 상태 변화시
- 상태보고요구 수신시

### 4.2 메시지 구성

| 구성 요소 | 설명 |
|-----------|------|
| 텍스트ID | 202 |
| SC명칭 | Storage Controller 이름 |
| 반복 (MAX 10건) | 기기명칭, 보고구분, 입출고MODE, 최대Buffer/Tray수, 실제Buffer/Tray수, Full발생시각, 재하정보(CST List) |
| 보고구분 | 1:CONV / 2:VC |

---

## 5. 공통 메시지 인터페이스

### 5.1 MCP On-Line 보고 (Text ID:1)

- 주기: 5초
- Down 판정: 15초

### 5.2 MSS계 메시지

| Text ID | 메시지명 | 설명 |
|---------|----------|------|
| 1 | 장비 상태 | Equipment Status |
| 3 | 이상/복구 | Alarm/Recovery |
| 13 | 작업데이터 | Job Data |
| 21 | Zone정보 | Zone Information |
| 203 | 정체 | Congestion |

---

## 6. AMP Remote Interface

### 6.1 초기화

```
Initialize → Start → Stop
```

### 6.2 필수 수집 정보

- ControlState
- SCState
- EQMode
- AlarmInfo
- CarrierInfo
- TrInfo

### 6.3 CNV 전용 정보

`ConveyorInfo` (Dictionary<string, Conveyor>)

### 6.4 CNV 전용 Operation 명령

- Run
- Stop
- AlarmClear
- **Home** (CNV 전용)
- **StepClear** (CNV 전용)
- **DataClear** (CNV 전용)
- SetPMMode

### 6.5 Transfer CNV 전용

| 속성 | 설명 |
|------|------|
| State=10 | Moving |
| ArrivedTime | 도착 시간 |
| LocationChangeTime | 위치 변경 시간 |

### 6.6 Unit Kind (CNV 관련)

| Unit Kind | 설명 |
|-----------|------|
| 3 | Conveyor |
| 6 | ConveyorInPort |
| 7 | ConveyorOutPort |

---

## 7. Atlas Server — UDP 수신 구현 (Java)

### 7.1 OhtUdpListener 구성

- DatagramSocket
- 1500byte buffer
- DataService queue

```java
DatagramSocket socket = new DatagramSocket(port);
byte[] buffer = new byte[1500];
DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
socket.receive(packet);
// → DataService 큐로 전달
```

### 7.2 메시지 파싱

CSV parsing + Text ID routing:

```java
switch (textId) {
    case "1":    // MCP 상태
    case "4":    // 기기 상태 (CNV 핵심)
    case "201":  // 위치 정보
    case "202":  // 재하 정보
}
```

### 7.3 CnvEdge 모델

| 항목 | 설명 |
|------|------|
| avgTransferIntervalT | 기본값: 150ms |
| getCost() | 비용 조회 |
| addCost() | 가중 이동 평균 (300~30000ms 범위) |
| isAvailable() | 가용성 확인 |

---

## 8. Logpresso 데이터 저장

> **CRITICAL**: 데이터는 반드시 Logpresso DB에 저장해야 합니다. CSV 파일로 저장하지 마세요.

### 8.1 Tuple API

```java
// 데이터 삽입
LogpressoAPI.setInsertTuples(tableName, tuples, timeout);
Util.insertInLogpressoDatabase(tuples, tableName, caller);
```

### 8.2 테이블 구조

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
| railEdgeId | Rail Edge ID |
| velocity | 속력 |
| maxVelocity | 최대 속력 |
| vhlCnt | Vehicle 수 |
| HID_ID | HID ID |

### 8.3 TrafficBatch (1분 주기)

1분 주기 Quartz Job → CnvEdge별 데이터 수집 → Logpresso 일괄 저장

### 8.4 Logpresso 조회

```java
XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");
XmlUtil.loadLogpressoParm();
```

### 8.5 Logpresso API 요약

| API 메소드 | 파라미터 | 설명 |
|-----------|----------|------|
| setInsertTuples() | tableName, tuples, timeout | 데이터 삽입 |
| selectLogpressoQuery() | queryName | 데이터 조회 |
| loadLogpressoParm() | (없음) | 설정 로드 |

---

## 9. 개정 이력

| 버전 | 작성일 | 작성자 | 내용 |
|------|--------|--------|------|
| v1.0.0 | 2026-02-25 | 설계팀 | 초판 작성 |
| v2.0.0 | 2026-02-25 | 설계팀 | Atlas Server UDP 수신 및 Logpresso DB 저장 추가, CNV 전용 분리 |

---

**END OF DOCUMENT**
