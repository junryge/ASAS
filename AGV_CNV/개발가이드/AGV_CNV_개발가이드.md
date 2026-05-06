# AGV / CNV 통합 개발 가이드

> **목적**: SK Hynix 반도체 Fab 환경에서 AGV(Automated Guided Vehicle) 및 CNV(Conveyor) 시스템을 개발하기 위한 통합 레퍼런스 문서
>
> **참조 문서**:
> - AMP API GUIDE v1.0.1.7 (SITKOREA)
> - C_FABSCOPE-MCP 통신사양서 (Daifuku)
> - SYSVIEW 통신사양서 v1.8.0 (Daifuku)
> - 메세지 FMS 샘플사양서

---

## 1. 시스템 아키텍처 개요

### 1.1 전체 구조

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────┐
│  HOST    │◄───►│ FabScope │◄───►│  MCP (CLW/   │◄───►│ AGV/CNV │
│ (MES/ERP)│     │(SysView+ │     │  STK/STBC)   │     │ 설비    │
│          │     │   MSS)   │     │              │     │         │
└─────────┘     └──────────┘     └──────────────┘     └─────────┘
     ▲               ▲                 ▲                    ▲
     │               │                 │                    │
  S6F11/12      UDP/IP 3600       TCP/IP (AMP)         하드웨어
  SECS/GEM      UDP/IP 3500       Remote.DLL            제어
```

### 1.2 통신 계층별 역할

| 계층 | 구성요소 | 프로토콜 | 역할 |
|------|---------|---------|------|
| **상위** | HOST (MES/ERP) | SECS/GEM | 반송 지시, 공정 관리 |
| **중위-1** | FabScope | UDP/IP (3500/3600) | 모니터링, 이상정보 수집 |
| **중위-2** | AMP | TCP/IP (포트 지정) | 설비 원격 제어/모니터링 |
| **하위** | MCP (CLW/STK) | TCP/IP → AMP Remote.DLL | 반송 제어, 기기 관리 |
| **설비** | AGV / CNV | 직접 제어 | 물리적 반송 수행 |

### 1.3 메시지 흐름도

```
[AGV/CNV 설비]
    │
    ├──► AMP (Remote.DLL) ──► 실시간 데이터 수집
    │       ├── Car 정보 (AGV/OHT)
    │       ├── Conveyor 정보 (CNV)
    │       ├── Transfer 정보 (반송)
    │       ├── Carrier 정보
    │       └── Alarm 정보
    │
    ├──► MCP (CLW/STK) ──► FabScope (SysView계)
    │       ├── Text ID:1  MCP On-Line 보고
    │       ├── Text ID:2  Vehicle 상태 보고
    │       ├── Text ID:3  Station 상태 보고
    │       ├── Text ID:4  기기 상태 보고
    │       └── Text ID:15 대차 주행 경로 보고
    │
    └──► MCP ──► FabScope (MSS계)
            ├── Text ID:3  이상/복구 보고
            ├── Text ID:5  작업 데이터 보고
            ├── Text ID:13 작업 데이터 보고 (v2.0+)
            └── Text ID:17 삽체/정체 보고
```

---

## 2. AMP Remote Interface (설비 ↔ AMP)

### 2.1 초기화 및 연결

AGV/CNV 설비 프로그램에서 AMP와 통신하기 위한 기본 흐름:

```csharp
// 1. CRemoteServer 인스턴스 생성
CRemoteServer m_RemoteServer = new CRemoteServer();

// 2. 이벤트 핸들러 등록
m_RemoteServer.MonitorGetData     = GetData;              // 데이터 수집
m_RemoteServer.ErrorEvent        += ErrorHandler;          // 에러 처리
m_RemoteServer.OperationEvent    += OperationHandler;      // 조작 명령
m_RemoteServer.CarrierEvent      += CarrierHandler;        // Carrier 명령
m_RemoteServer.TransferEvent     += TransferHandler;       // 반송 명령
m_RemoteServer.ControlStatusEvent += ControlStatusHandler;  // Online 상태
m_RemoteServer.EQModeEvent       += EQModeHandler;         // EQ Mode
m_RemoteServer.ParameterEvent    += ParameterHandler;      // 파라미터
m_RemoteServer.GlobalTransferEvent += GlobalTransferHandler;// 연계반송

// 3. 초기화
bool result = m_RemoteServer.Initialize(
    EqpID: "AGV_001",        // 설비명
    ExeName: "AGV_EQP.exe",  // 실행파일명
    Version: "v1.0.0.0",     // 버전
    PortNo: 10000,            // AMP TCP/IP 포트
    MonitoringTime: 500,      // 데이터 전송 간격 (ms)
    DelayTime: 100            // Thread 유휴 시간 (ms)
);

// 4. 통신 시작
m_RemoteServer.Start();

// 5. 종료 시
m_RemoteServer.Stop();
```

### 2.2 API 메서드 요약

| 메서드 | 시그니처 | 설명 |
|--------|---------|------|
| `Initialize` | `bool Initialize(string EqpID, string ExeName, string Version, int PortNo, int MonitoringTime, int DelayTime)` | AMP 통신 초기화 |
| `Start` | `bool Start()` | 통신 시작 |
| `Stop` | `bool Stop()` | 통신 종료 |

### 2.3 이벤트 핸들러 상세

#### 2.3.1 MonitorGetData — 실시간 데이터 수집 (필수)

AMP가 주기적으로 호출하여 설비 데이터를 수집합니다.

```csharp
public void GetData(string EQPID, CRemoteObject Obj)
{
    // ═══════════ 필수 수집 항목 ═══════════

    // (1) Host 상태
    Obj.ControlState = eControlState.ONLINE_LOCAL;  // OnLine 모드
    Obj.SCState      = eSCState.RUN;                // 가동 상태
    Obj.EQMode       = eEqMode.OPERATOR;            // EQ Mode

    // (2) Alarm 정보
    if (Obj.AlarmInfo == null)
        Obj.AlarmInfo = new Dictionary<string, Alarm>();
    // → 현재 발생 중인 Alarm을 Add, Clear된 것은 제거

    // (3) Carrier 정보
    if (Obj.CarrierInfo == null)
        Obj.CarrierInfo = new Dictionary<string, Carrier>();

    // (4) Transfer(반송) 정보
    if (Obj.TrInfo == null)
        Obj.TrInfo = new Dictionary<string, Transfer>();

    // ═══════════ AGV 전용 항목 ═══════════

    // (5) Car 정보 — AGV, OHT 설비만 해당
    if (Obj.CarInfo == null)
        Obj.CarInfo = new Dictionary<string, Car>();
    // → 각 Vehicle의 위치, 상태, 경로 등

    // ═══════════ CNV 전용 항목 ═══════════

    // (6) Conveyor 정보 — 컨베이어 설비만 해당
    if (Obj.ConveyorInfo == null)
        Obj.ConveyorInfo = new Dictionary<string, Conveyor>();

    // ═══════════ 선택 항목 ═══════════

    // (7) Shelf 정보 — STK 설비 해당
    if (Obj.ShelfInfo == null)
        Obj.ShelfInfo = new Dictionary<string, Shelf>();

    // (8) Port 정보 — Port가 있는 설비
    if (Obj.PortInfo == null)
        Obj.PortInfo = new Dictionary<string, Port>();

    // (9) Zone 정보
    if (Obj.ZoneInfo == null)
        Obj.ZoneInfo = new Dictionary<string, Zone>();
}
```

#### 2.3.2 OperationEvent — 원격 조작 명령

AMP에서 설비로 보내는 조작 명령입니다.

```csharp
eAckCode OperationHandler(IPAddress IpAddress, eRemoteCommand Cmd, string UnitID)
{
    switch (Cmd)
    {
        case eRemoteCommand.Run:          // 운전 명령
        case eRemoteCommand.Stop:         // 정지 명령
        case eRemoteCommand.AlarmClear:   // Alarm Clear
        case eRemoteCommand.Home:         // Servo Home (CNV용)
        case eRemoteCommand.StepClear:    // Step Clear (CNV용)
        case eRemoteCommand.DataClear:    // Data Clear (CNV용)
        case eRemoteCommand.SetPMMode:    // PM Mode 설정
    }
    // 처리 불가 시 return eAckCode.Nak
    return eAckCode.Ack;
}
```

#### 2.3.3 TransferEvent — 반송 명령

```csharp
eAckCode TransferHandler(IPAddress IpAddress, eRemoteCommand Cmd, Transfer Transfer)
{
    switch (Cmd)
    {
        case eRemoteCommand.Creat:   // 반송 명령 생성
        case eRemoteCommand.Cancel:  // 반송 명령 취소 (실행 전)
        case eRemoteCommand.Abort:   // 반송 명령 중지 (실행 중)
    }
    return eAckCode.Ack;
}
```

#### 2.3.4 CarrierEvent — Carrier 관리

```csharp
eAckCode CarrierHandler(IPAddress IpAddress, eRemoteCommand Cmd, Carrier Carrier)
{
    switch (Cmd)
    {
        case eRemoteCommand.Install:  // Carrier 설치
        case eRemoteCommand.Remove:   // Carrier 제거
    }
    return eAckCode.Ack;
}
```

#### 2.3.5 ControlStatusEvent — Online 상태 변경

```csharp
eAckCode ControlStatusHandler(IPAddress IpAddress, eRemoteCommand Cmd)
{
    switch (Cmd)
    {
        case eRemoteCommand.OffLine:  // OffLine 전환
        case eRemoteCommand.Local:    // Local 전환
        case eRemoteCommand.Remote:   // Remote 전환
    }
    return eAckCode.Ack;
}
```

#### 2.3.6 EQModeEvent — EQ Mode 변경

```csharp
eAckCode EQModeHandler(IPAddress IpAddress, eRemoteCommand Cmd, string UnitID)
{
    switch (Cmd)
    {
        case eRemoteCommand.Operation:  // Operation Mode
        case eRemoteCommand.Engr:       // Engineering Mode
        case eRemoteCommand.Maint:      // Maintenance Mode
    }
    return eAckCode.Ack;
}
```

#### 2.3.7 GlobalTransferEvent — 연계반송 (설비간)

```csharp
void GlobalTransferHandler(IPAddress IpAddress, string CarrierID,
    string SourceEqpID, string SourceUnitID,
    string DestEqpID, string DestUnitID)
{
    // HOST로 S6F11 Global Transfer 전송
    // S6F12 Ack Code에 따라 응답
}

// S6F12 ACK 수신 후 호출
public void GlobalTransfer_Request_Ack(IPAddress IpAddr, eAckCode AckCode);
```

---

## 3. AMP 데이터 클래스 상세

### 3.1 CRemoteObject — 메인 데이터 객체

모든 실시간 데이터를 담는 최상위 클래스입니다.

```csharp
public class CRemoteObject
{
    // ── 상태 정보 ──
    public eSCState      SCState      = eSCState.STOP;            // 가동 상태
    public eControlState ControlState = eControlState.OFFLINE;    // OnLine 상태
    public eEqMode       EQMode       = eEqMode.OPERATOR;        // EQ Mode

    // ── 필수 데이터 ──
    public Dictionary<string, Alarm>    AlarmInfo;     // Alarm 목록
    public Dictionary<string, Carrier>  CarrierInfo;   // Carrier 목록
    public Dictionary<string, Transfer> TrInfo;        // 반송 목록

    // ── AGV/OHT 전용 ──
    public Dictionary<string, Car>      CarInfo;       // Vehicle 목록

    // ── CNV 전용 ──
    public Dictionary<string, Conveyor> ConveyorInfo;  // 컨베이어 목록

    // ── 공통 선택 ──
    public Dictionary<string, Shelf>    ShelfInfo;     // 선반 목록
    public Dictionary<string, Port>     PortInfo;      // Port 목록
    public Dictionary<string, Zone>     ZoneInfo;      // Zone 목록

    // ── ACS 전용 ──
    public Dictionary<string, HostLocation> HostLocationInfo;  // EQ 정보
    public Dictionary<string, Location>     LocationInfo;      // Point 정보
    public Dictionary<string, Node>         NodeInfo;          // Node 정보
    public Dictionary<string, RackBuffer>   RackBufferInfo;    // Rack Buffer 정보
}
```

### 3.2 Car 클래스 — AGV/OHT Vehicle 정보

```csharp
public class Car
{
    // ── 식별 정보 ──
    public string EqpID;       // 설비 ID
    public string UnitID;      // 자체 관리 Unit ID
    public string HostID;      // Host 관리 Unit ID
    public string ZoneName;    // Host 관리 Zone Name

    // ── 상태 정보 ──
    public int FaultCode;      // Alarm Code (정상: 0)
    public int UnitState;      // Unit 상태 (아래 표 참조)
    public int ProcessStatus;  // Process 상태 (아래 표 참조)
    public string CarrierID;   // 적재 Carrier ID

    // ── 종류 ──
    public int Kind;           // Unit 종류 (아래 표 참조)

    // ── 위치/경로 정보 ──
    public string Location;    // 현재 위치
    public int    XPosition;   // 화면 X 좌표
    public int    YPosition;   // 화면 Y 좌표
    public string FullPath;    // 전체 경로
    public string RunPath;     // 지역 경로
    public int    MotionStep;  // Motion Step

    // ── Vehicle 전용 ──
    public int    VehicleJob;      // JOB 형태
    public int    VehicleState;    // VEHICLE 상태
    public int    VehicleType;     // VEHICLE TYPE
    public bool   AssignEnable;    // ASSIGN 가능 여부
    public string GroupID;         // 소속 GROUP
    public string BayID;           // 소속 BAY

    // ── 작업 목록 ──
    public List<VehicleFlowStep> VehicleFlowStepList;
    public RemoteVehicleInfo     vehicleinfo;
}
```

#### Car.UnitState — Unit 상태값

| 값 | 상태 | 설명 |
|----|------|------|
| 0 | Normal | 정상 |
| 1 | Stop | 정지 |
| 2 | Fault | 이상 |
| 3 | Disable, PM | 비활성/예방정비 |

#### Car.ProcessStatus — Process 상태값

| 값 | 상태 | 설명 |
|----|------|------|
| 0 | Empty | 비어있음 |
| 1 | Idle | 대기 |
| 2 | Busy | 작업 중 |
| 3 | Pausing | 일시정지 중 |
| 4 | Paused | 일시정지 |

#### Car.VehicleJob — JOB 형태

| 값 | 형태 |
|----|------|
| 0 | NONE |
| 1 | SINGLE_JOB |
| 2 | MULTI_JOB |
| 3 | DOUBLE_JOB |
| 4 | BATTERY_JOB |

#### Car.VehicleState — Vehicle 상태

| 값 | 상태 | 설명 |
|----|------|------|
| 1 | REMOVED | 제거됨 |
| 2 | NOTASSIGNED | 미할당 |
| 3 | ENROUTE | 경로 이동 중 |
| 4 | PARKED | 주차 |
| 5 | LOADING | 적재 중 |
| 6 | UNLOADING | 하역 중 |
| 7 | ERROR | 에러 |
| 8 | DOWN | 다운 |
| 9 | CHARGE | 충전 중 |
| 10 | MOVING | 이동 중 |
| 14 | AVOID | 회피 중 |

#### Car.VehicleType

| 값 | 타입 |
|----|------|
| 0 | BROADBAND |
| 1 | LOCAL |

#### Car.Kind — Unit 종류 (공통)

| 값 | 종류 | 설명 |
|----|------|------|
| 0 | Unknown | 알 수 없음 |
| 1 | Lift | 리프트 |
| 2 | Diverter | 분기기 |
| 3 | Conveyor | 컨베이어 |
| 4 | DiverterInPort | 분기기 입력 포트 |
| 5 | DiverterOutPort | 분기기 출력 포트 |
| 6 | ConveyorInPort | 컨베이어 입력 포트 |
| 7 | ConveyorOutPort | 컨베이어 출력 포트 |
| 8 | Crain | 크레인 |
| 9 | Shelf | 선반 |
| 10 | Auto_In_Port | 자동 입력 포트 |
| 11 | Auto_Out_Port | 자동 출력 포트 |
| 12 | Auto_Both_Port | 자동 양방향 포트 |
| 13 | Manual_In_Port | 수동 입력 포트 |
| 14 | Manual_Out_Port | 수동 출력 포트 |
| 15 | Manual_Both_Port | 수동 양방향 포트 |

### 3.3 Transfer 클래스 — 반송 정보

```csharp
public class Transfer
{
    // ── 식별 정보 ──
    public string EqpID;         // 설비 ID
    public string CommandID;     // Command ID
    public string CarrierID;     // Carrier ID
    public string LotID;         // Lot ID
    public string CarrierType;   // 종류 (REAL, EMPTY)

    // ── 반송 경로 ──
    public string HostSourceID;  // Host 관리 Source ID
    public string HostDestID;    // Host 관리 Dest ID
    public string SourceUnitID;  // 자체 관리 Source Unit ID
    public string DestUnitID;    // 자체 관리 Dest Unit ID
    public string CurrentEqp;    // 현재 장비
    public string CurrentLoc;    // 현재 위치
    public string Path;          // 경로 (CNV/AGV 전용)
    public int    Priority;      // 우선 순위

    // ── 시간 정보 ──
    public DateTime CreateTime;      // 명령 생성 시간
    public DateTime InitiateTime;    // 반송 시작 시간
    public DateTime DT;              // DT
    public DateTime TT;              // TT
    public DateTime LocationChangeTime; // 위치 변경 시간
    public DateTime ArrivedTime;     // 목적지 도착 시간 (CNV/AGV)
    public DateTime TransferingTime; // 반송 개시 시간 (ACS)

    // ── 반송 상태 ──
    public int State;  // 반송 상태 (아래 표 참조)

    // ── STK 전용 ──
    public string OriginHostSourceID;  // ALT 시 원본 Source ID
    public string AltDestUnitID;       // ALT용 목적지

    // ── ACS/OCS 전용 ──
    public string VehicleID;       // 할당된 Vehicle ID
    public string HostVehicleID;   // Host Vehicle ID
    public int    VehicleJob;      // Vehicle JOB 형태
    public string PreAssignEQ;     // PreAssign EQ ID
    public int    SourceArm;       // GET ARM (0:UNKNOWN, 1:UPPER, 2:LOWER)
    public int    DestArm;         // PUT ARM
    public bool   Enabled;         // 사용 가능 여부
    public string SBayID;          // Source Bay ID
    public string DBayID;          // Dest Bay ID
    public string LiftHostID;      // 예약 LIFT HOST ID
    public string AbcsHostID;      // 예약 ABCS HOST ID
    public string Rack_Total_Qty;  // Rack 총 수량
    public string Rack_Sequence;   // Rack 순번
}
```

#### Transfer.State — 반송 상태값

| 값 | 상태 | 설명 |
|----|------|------|
| 0 | None | 없음 |
| 1 | Queue | 대기열 |
| 2 | Transfering | 반송 중 |
| 3 | Complete | 완료 |
| 4 | Alternate | 대체 |
| 5 | Paused | 일시정지 |
| 6 | Cancelling | 취소 중 |
| 7 | Canceled | 취소됨 |
| 8 | Aborting | 중단 중 |
| 9 | Aborted | 중단됨 |
| **10** | **Moving** | **이동 중 (AGV/CNV 전용)** |

### 3.4 Carrier 클래스 — Carrier 정보

```csharp
public class Carrier
{
    // ── 식별 정보 ──
    public string EqpID;          // 설비 ID
    public string CarrierID;      // Carrier ID
    public string LotID;          // Lot ID
    public string StepID;         // Step ID
    public string CarrierType;    // 종류 (COVER, EMPTY, REAL)
    public string FlowID;         // 공정코드

    // ── 상태 정보 ──
    public int    CarrierState;   // Carrier 상태 (아래 표)
    public int    HandOffType;    // 투입 상태 (0:Auto, 1:Manual)

    // ── 위치 정보 ──
    public string Location;       // 현재 위치
    public string OldLocation;    // 이전 위치
    public string CurrentZone;    // 현재 Zone
    public string PortName;       // 포트명

    // ── Tray 관련 ──
    public int    TrayCnt;        // Tray 수량
    public string TrayThick;      // Tray 두께
    public string TType;          // 트레이타입 (예: 07.50X11.00)
    public int    ChipCount;      // 제품수량
    public string OwnerCode;      // 오너코드

    // ── 시간 정보 ──
    public DateTime EnterZoneTime;       // Zone 진입 시간
    public DateTime CreateTime;          // 생성 시간
    public DateTime MappingStartDate;    // 매핑 시작
    public DateTime MappingEndDate;      // 매핑 종료
    public DateTime LocationChangeTime;  // 위치 변경 시간

    // ── 기타 ──
    public string JobName;        // Job Name
    public string Comment;        // Comment

    // ── ACS 전용 ──
    public int    BIBType;
    public int    BallType;
    public string BIBSoketType;
    public string PreAssignEQ;
    public string BayID;
    public string GroupID;
    public string Rack_Total_Qty;
    public string Rack_Sequence;
}
```

#### Carrier.CarrierState — Carrier 상태값

| 값 | 상태 | 설명 |
|----|------|------|
| 0 | None | 없음 |
| 1 | WaitIn | 입고 대기 |
| 2 | Transferring | 반송 중 |
| 3 | Complete | 완료 |
| 4 | Alternate | 대체 |
| 5 | WaitOut | 출고 대기 |
| 6 | Install | 설치됨 |
| 7 | Block | 차단 |

### 3.5 Alarm 클래스

```csharp
public class Alarm
{
    public string   EqpID;            // 설비 ID
    public int      AlarmCode;        // Host 보고 Alarm Code
    public int      AlarmLevel;       // 0: Warning, 1: Heavy Alarm
    public string   HostID;           // Alarm 발생 Host Unit ID
    public string   UnitID;           // Alarm 발생 Unit ID
    public string   strAlarmText;     // Alarm 이름
    public string   strAlarmComment;  // Alarm 처리 방안
    public DateTime OccurTime;        // 발생 시간
}
```

### 3.6 Zone 클래스

```csharp
public class Zone
{
    public string EqpID;           // 설비 ID
    public int    ZoneName;        // Zone Name
    public int    MaxCount;        // 최대 수량
    public string CurrentCount;    // 현재 수량
    public string IncommingCount;  // 예약 수량
}
```

### 3.7 ACS 관련 클래스

```csharp
// EQ 정보
public class HostLocation
{
    public string HostID;     // Host 관리 UNIT ID
    public bool   Enabled;    // 사용 유무
}

// Point 정보
public class Location
{
    public string HostID;          // 자체 관리 UNIT ID
    public bool   Enabled;         // 사용 유무
    public string VehicleID;       // 현재 위치 Vehicle ID
    public bool   WaitPosition;    // 대기 위치 유무
    public string WaitVehicleID;   // 예약 Vehicle ID
}

// Node(Segment) 정보
public class Node
{
    public string KeyID;     // Key ID
    public bool   Enabled;   // 사용 유무
}

// RackBuffer 정보 (ACS)
public class RackBuffer
{
    public string EqpID;
    public int    FaultCode;
    public string CarrierID;
    public int    Kind;             // Unit 종류 (Car.Kind 참조)
    public int    UnitState;        // Unit 상태
    public int    ProcessStatus;    // Process 상태
    public string UnitID;
    public string HostID;
    public string ZoneName;
    public string BufferType;       // Buffer Type
    public string Slot;             // Slot No
    public bool   Enabled;          // 사용 유무
    public bool   SemiAuto;         // SEMI AUTO Type
    public bool   CarrierDetect;    // Carrier 감지 유무
    public bool   Reserved;         // 반송 예약 상태
    public bool   ReservedRackSend; // 배출 예약 상태
    public string ReservedLotID;    // 예약 LotID
    public int    ReservedSqNumber; // 예약 Sq Number
}
```

---

## 4. FabScope 통신 — SysView계 메시지

### 4.1 통신 프로토콜 기본 정보

| 항목 | 값 |
|------|-----|
| 프로토콜 | UDP/IP |
| 포트 (SysView계) | 3600 (기본) |
| 포트 (MSS계) | 3500 (기본) |
| 메시지 형식 | CSV (콤마 구분) |
| 문자 코드 | ASCII |
| 최대 크기 | Ethernet MTU 1500byte 이하 |
| 빈 항목 | `,,` (콤마 두 개) |

### 4.2 텍스트 ID 범위

| ID 범위 | 용도 |
|---------|------|
| 1 ~ 100 | 공용 |
| 101 ~ 200 | CLW MCP, STBC 전용 |
| 201 ~ 300 | STK MCP, SSS 전용 |

### 4.3 Text ID:1 — MCP On-Line 보고 (공통)

CLW MCP7, STK MCP7, STBC 공통 메시지. MCP7의 참가 상태를 보고합니다.

**보고 조건**: MCP 기동시 / 상태 변화시 / 상태보고요구 수신시 / 5초 주기

> FabScope는 등록된 MCP7로부터 15초 이상 어떤 메시지도 수신하지 않으면 해당 MCP7을 **Down**으로 인식합니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `1` |
| MCP 명칭 | 각 MCP7의 유니크 명칭 |
| Control 상태 | `ON-LINE` / `OFF-LINE` |
| TSC 상태 | `AUTO` / `PAUSED` / `PAUSING` (ON-LINE일 때만 유효) |
| Alarm 상태 | `NO ALARMS` / `ALARMS` |
| MCP 상태 구분 | `0`: 통상 / `1`: 선반 충진율 over |

### 4.4 Text ID:2 — Vehicle 상태 보고 (CLW MCP7)

CLW MCP7이 관리하는 Vehicle(AGV/OHT)의 상태를 보고합니다.

**보고 조건**: MCP 기동시 / 상태 변화시 / 상태보고요구 수신시 (Vehicle 수 만큼 전송)

| 필드 | 내용 | 비고 |
|------|------|------|
| 텍스트 ID | `2` | |
| MCP 명칭 | 유니크 명칭 | |
| Vehicle명 | Vehicle 식별 명칭 | |
| 상태 | `1`:운전중, `2`:정지, `3`:이상, `4`:수동, `5`:추출중, `6`:OBS-STOP/BZ-STOP, `7`:삽체, `8`:정체, `9`:E84 Timeout, `10`:주회없음 E84 Timeout, `11`:HT-STOP | |
| 재하 정보 | `0`:없음, `1`:있음 | |
| Error Code | `0000`~`FFFF` (상태≠3이면 `0000`) | |
| 통신 상태 | `1`:정상, `2`:통신 끊김 | |
| 현재 번지 | 현재 번지 | 알 수 없으면 빈 값 |
| 현재 번지로부터 거리 | 100mm 단위 | |
| 다음 번지 | | |
| 실행 Cycle | `0`:없음, `1`:위치확인, `2`:이동, `3`:Unload, `4`:Load, `5`:추출, `9`:층간이동, `21`:주회주행, `22`:수동조작, `23`:주행학습, `24`:이재부학습, `25`~`27`:테스트, `2C`:계측, `2D`:흡인구이동, `2E`:동간이동, `2F`:퇴피이동, `3C`:휠교체, `3D`:퇴피추출, `3E`:검사, `3F`:세차 | |
| Vehicle 실행 Cycle 진척 | `0`:없음, `1`:이동중, `2`:Unload이동, `3`:Unload이재, `4`:Load이동, `5`:Load이재, `6`:유지보수이동, `7`:대체지시대기, `8`:투입중, `9`:Unload도착, `10`:Load도착 | |
| Carrier ID | 관련 Carrier ID | |
| Destination | 목적지 Station | |
| E/M 상태 | Bit 배치 | |
| GroupID | 유효 문자열 (없으면 `0000`) | |
| 반송원 Port | | |
| 반송처 Port | | |
| 반송 우선도 | `0`:무효, `1`~`99` (99가 최고) | |
| 작업 상태 상세 | `0`:없음, `1`:대기, `2`:STAGE대기, `3`:Standby대기, `4`:반송허가대기, `5`:Carrier회수대기, `6`:MAP배달대기, `101`:이동중, `102`:Parking주행, `103`~`106`:각종이동, `107`:Forecast이동, `108`:세차이동, `109`:검사이동, `110`:휠교체이동, `111`:계측이동, `112`:청소이동, `113`:선회이동 | |
| 대차 주행거리 | mm 단위 (도착시 설정, 그 외 0) | |
| Command ID | | |
| Bay 명칭 | | |
| 도착 예상 시간(ETA) | 경로 확정 시 시간 | |
| 예약 Command ID | | |

### 4.5 Text ID:4 — 기기 상태 보고 (공통)

MCP7 산하 기기의 상태를 보고합니다. CLW MCP7은 Vehicle, Station은 이 메시지로 보내지 않습니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `4` |
| MCP 명칭 | |
| 기종번호 | 기종 식별 구분 번호 |
| 기기명칭 | |
| 상태 | `1`:정상, `2`:이상, `3`:유지보수, `4`:운전OFF, `5`:분리 |
| Error Code | `0000`~`FFFF` (상태≠2이면 `0000`) |

#### 기종번호 참조

| CLW MCP7 | STK MCP7 | STBC |
|----------|----------|------|
| `00` CLW MCP7 | `100` STK MCP7 | `R00` STBC |
| `10` VHL(Vehicle) | `202` CLS Stocker | `R10` RFC |
| `50` BZ(Blocking Zone) | `260` CMS Stocker | `R20` NPC |
| `60` MTL(Maintenance Lifter) | `261` ZIP Stocker | `R21` Purge선반 |
| `91` AD/FD(Auto/Fire Door) | `303` CNV(CONV) | |
| `92` HID | `320` PIO_IF | |
| `93` FFU | `324` IFP | |
| | `808` CLL(Clean Lifter) | |
| | `871` SINGLE_LIFTER | |
| | `872` DOUBLE_LIFTER | |
| | `909` MIF(Middle Interface) | |
| | `1111` PNP(Picking & Place) | |

### 4.6 Text ID:15 — 대차 주행 경로 보고 (CLW MCP7)

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `15` |
| 기종 코드 | |
| Machine ID | |
| 기본 분기 방향 | `0`:왼쪽, `1`:오른쪽 |
| 주행 플래그 | `0`:정지, `1`:주행중 |
| 시작 번호 | |
| 종료 번호 | |
| 기본 외 분기 번지 수 | 0~300 |
| 기본 외 분기 번지 | 반대 방향 분기 번지 (쉼표 구분) |
| Command ID | |

---

## 5. FabScope 통신 — MSS계 메시지

### 5.1 Text ID:1 — 장비 상태 보고

MCP가 관리하는 모든 장비의 상태를 보고합니다. 10대 이상 시 여러 번 전송합니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `1` |
| MCP 명칭 | |
| (반복) 기기 정보 | 상태: `1`:정상, `2`:고장, `3`:유지보수, `4`:추출중 |

### 5.2 Text ID:3 — 이상/복구 보고

기기가 이상/유지보수/추출 상태가 되거나 정상 복귀했을 때 보고합니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `3` |
| MCP 명칭 | |
| 기종번호 | |
| 기기명칭 | |
| 상태 변화 일시 | `YYYY-MM-DD HH:MM:SS` |
| 상태 | `1`:정상, `2`:고장, `3`:유지보수, `4`:추출중 |
| Error Code | 고장 외 `0000` |
| 도메인 명칭 | RM 이상 시: From 포트 To 포트명 |
| 포트 ID | CLW: EQ/AZFS PortID, STK: PortID 또는 유닛ID |

### 5.3 Text ID:13 — 작업 데이터 보고 (v2.0+)

반송 완료/대체/중단 등의 작업 데이터를 상세 보고합니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `13` |
| MCP 명칭 | |
| 기종번호 | |
| 기기명칭 | 대체시 대체 후 Vehicle 명칭 |
| Carrier명칭 | |
| 반송 Priority | 보고 시점 Priority |
| From 포트 | |
| To 포트 | |
| 반송지시 수신일시 | `YYYY-MM-DD HH:MM:SS` |
| 공(空)Carrier 반송 개시 일시 | Unload 이동 시작 |
| Unload 시작 일시 | |
| 실(実)Carrier 반송 개시 일시 | Load 이동 시작 |
| Load 개시 일시 | |
| 반송 완료 일시 | Abort/Unsuccessful 시 해당 시각 |
| 실제 반송 지연 요인 | `00010`:주회, `00100`:반송 Paused |
| 실제 반송 중지 요인 | `2`:Unsuccessful, `3`:Alternate, `4`:수동중단, `5`:Intermediate |
| Command ID | |
| MCP 내 Priority | |
| Load 선반 정보 | 설정에 따라 보고 |
| Reroute 횟수 | CLW-MCP만 |
| VLF 통과번지 | 예: `2000\|2100\|5000\|5200` |
| Unload시 Tray 높이 | 예: `12270` (12.27mm) |
| 이중격납 시 Tray 높이 | |

### 5.4 Text ID:17 — 삽체/정체 보고 (CLW MCP)

Vehicle이 삽체(Traffic jam) 또는 정체 상태가 되었거나 해제되었을 때 보고합니다.

| 필드 | 내용 |
|------|------|
| 텍스트 ID | `17` |
| MCP 명칭 | |
| 기종번호 | |
| 기기명칭 | |
| 상태 변화 일시 | `YYYY-MM-DD HH:MM:SS` |
| 상태 | `1`:정상, `2`:삽체(Traffic jam), `3`:정체 |
| 번지 | |
| 거리 | |
| 다음 번지 | |

---

## 6. FMS 메시지 샘플 (Vehicle 상태 보고)

### 6.1 샘플 메시지

```
Message=2,OHT,V047,1,1,0000,1,1232,0,1202,4,4,PIN2702,20308,00000000,0000,IR5S005S_2,STB031-R08,50,0,0
```

### 6.2 필드 분석

| 번호 | 구분 | FMS사용 | 값 | FMS 처리 내용 |
|------|------|---------|-----|--------------|
| 0 | 메시지 ID | O | `2` | Vehicle 상태 코드 |
| 1 | MCP명칭 | | `OHT` | |
| 2 | Vehicle 명칭 | O | `V047` | V047 호기 |
| 3 | 상태 | O | `1` | 운전중 |
| 4 | 재하정보 | | `1` | Carrier 적재 |
| 5 | Error Code | | `0` | |
| 6 | 통신 상태 | | `1` | 정상 |
| 7 | 현재 번지 | O | `1232` | 1232번지 위치 |
| 8 | 현재 번지 거리 | | `0` | |
| 9 | 다음 번지 | O | `1202` | 1202번지로 이동 |
| 10 | 실행 Cycle | | `4` | Load Cycle |
| 11 | Vehicle 실행 사이클 | O | `4` | Load 이동 중 |
| 12 | Carrier ID | O | `PIN2702` | 적재 Carrier |
| 13 | 목적지 Station | O | `20308` | 목적지 |
| 14 | E/M 상태 | | `0` | |
| 15 | GroupID | | `0` | |
| 16 | 반송원 Port | | `IR5S005S_2` | |
| 17 | 반송처 Port | | `STB031-R08` | |
| 18 | 반송 우선도 | | `50` | |
| 19 | 작업상태 상세 | | `0` | |
| 20 | 태차 주행거리 | | `0` | |

**해석**: V047 호기가 PIN2702 Carrier를 적재하고 1232번지 → 1202번지로 이동 중이며, 최종 목적지는 Station 20308 (반송원: IR5S005S_2, 반송처: STB031-R08)

---

## 7. 상태값 Enum 정리

### 7.1 eControlState

| 값 | 상태 |
|----|------|
| OFFLINE | 오프라인 |
| ONLINE_LOCAL | 온라인 로컬 |
| ONLINE_REMOTE | 온라인 리모트 |

### 7.2 eSCState

| 값 | 상태 |
|----|------|
| STOP | 정지 |
| RUN | 가동 |

### 7.3 eEqMode

| 값 | 상태 |
|----|------|
| OPERATOR | 운전자 모드 |
| ENGR | 엔지니어링 모드 |
| MAINT | 유지보수 모드 |

### 7.4 eRemoteCommand

| 값 | 용도 | 대상 이벤트 |
|----|------|-----------|
| Run | 운전 | OperationEvent |
| Stop | 정지 | OperationEvent |
| AlarmClear | 알람 해제 | OperationEvent |
| Home | 서보 홈 (CNV) | OperationEvent |
| StepClear | 스텝 클리어 (CNV) | OperationEvent |
| DataClear | 데이터 클리어 (CNV) | OperationEvent |
| SetPMMode | PM 모드 설정 | OperationEvent |
| Install | Carrier 설치 | CarrierEvent |
| Remove | Carrier 제거 | CarrierEvent |
| Creat | 반송 생성 | TransferEvent |
| Cancel | 반송 취소 | TransferEvent |
| Abort | 반송 중단 | TransferEvent |
| OffLine | 오프라인 전환 | ControlStatusEvent |
| Local | 로컬 전환 | ControlStatusEvent |
| Remote | 리모트 전환 | ControlStatusEvent |
| Operation | 운전 모드 | EQModeEvent |
| Engr | 엔지니어링 모드 | EQModeEvent |
| Maint | 유지보수 모드 | EQModeEvent |

### 7.5 eAckCode

| 값 | 의미 |
|----|------|
| Ack | 처리 성공 |
| Nak | 처리 불가 |

---

## 8. AGV/CNV 개발 체크리스트

### 8.1 AMP 연동 필수 구현 항목

- [ ] `CRemoteServer` 인스턴스 생성 및 이벤트 등록
- [ ] `Initialize()` → `Start()` → `Stop()` 생명주기 관리
- [ ] `MonitorGetData` 이벤트에서 실시간 데이터 수집
  - [ ] ControlState / SCState / EQMode 설정
  - [ ] AlarmInfo 관리 (발생/해제)
  - [ ] CarrierInfo 관리
  - [ ] TrInfo (Transfer) 관리
  - [ ] **CarInfo (AGV)** 또는 **ConveyorInfo (CNV)** 관리
- [ ] `OperationEvent` 처리 (Run/Stop/AlarmClear/Home/StepClear/DataClear/SetPMMode)
- [ ] `TransferEvent` 처리 (Creat/Cancel/Abort)
- [ ] `CarrierEvent` 처리 (Install/Remove)
- [ ] `ControlStatusEvent` 처리 (OffLine/Local/Remote)
- [ ] `EQModeEvent` 처리 (Operation/Engr/Maint)
- [ ] `ErrorEvent` 로그/알람 처리

### 8.2 FabScope 연동 (MCP 통신)

- [ ] UDP/IP 송수신 모듈 구현
- [ ] SysView계 포트 3600 / MSS계 포트 3500 설정
- [ ] CSV 파싱/생성 모듈 구현
- [ ] Text ID:1 MCP On-Line 보고 (5초 주기)
- [ ] Text ID:2 Vehicle 상태 보고
- [ ] Text ID:4 기기 상태 보고
- [ ] Text ID:51 상태보고요구 수신 처리
- [ ] Text ID:3 (MSS) 이상/복구 보고
- [ ] Text ID:13 (MSS) 작업 데이터 보고

### 8.3 AGV 전용 체크리스트

- [ ] Car 클래스 데이터 관리 (위치, 경로, 상태)
- [ ] VehicleState 상태 전이 관리
- [ ] VehicleJob 작업 형태 관리
- [ ] 주행 경로 보고 (Text ID:15)
- [ ] 삽체/정체 감지 및 보고 (Text ID:17)
- [ ] 연계반송 (GlobalTransferEvent) 처리
- [ ] E/M 상태 (배터리) 모니터링

### 8.4 CNV 전용 체크리스트

- [ ] Conveyor 클래스 데이터 관리
- [ ] Home/StepClear/DataClear 명령 처리
- [ ] Transfer.ArrivedTime 도착 시간 관리
- [ ] Transfer.State=10 (Moving) 상태 관리

---

---

## 9. Atlas Server — UDP 수신 구현 (Java)

### 9.1 OhtUdpListener — UDP 소켓 수신

Atlas 서버에서 MCP가 보내는 UDP 패킷을 수신하여 Vehicle/Edge 상태를 업데이트하고 Logpresso DB에 저장합니다.

```java
// OhtUdpListener.java — UDP 수신 스레드
public class OhtUdpListener implements Runnable {
    private DatagramSocket socket;
    private byte[] buffer = new byte[1500];  // MTU 크기

    public OhtUdpListener(int port, String fabId, String mcpName) {
        this.socket = new DatagramSocket(port);
    }

    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
            socket.receive(packet);

            String message = new String(packet.getData()).trim();
            _addMessageInAtlasMemory(fabId, mcpName, message);
        }
    }

    private void _addMessageInAtlasMemory(String fabId, String mcpName, String message) {
        Msg msg = new Msg();
        msg.setFabId(fabId);
        msg.setMcpName(mcpName);
        msg.setMsg(message);
        msg.setMillis(System.currentTimeMillis());
        DataService.getInstance().queue.add(msg);  // Worker 스레드가 처리
    }
}
```

> Multi-IP/FAB 지원: 설정에 따라 여러 포트/IP에서 동시 수신 가능. 각 리스너는 fabId + mcpName으로 식별됩니다.

### 9.2 OhtMsgWorkerRunnable — 메시지 파싱 처리

```java
// OhtMsgWorkerRunnable.java — 큐에서 메시지를 꺼내 처리
public class OhtMsgWorkerRunnable implements Runnable {
    private static final int MSG_ID_IDX = 0;

    @Override
    public void run() {
        while (true) {
            Msg msg = DataService.getInstance().queue.poll();
            if (msg == null) { Thread.sleep(10); continue; }

            // CSV 파싱 (콤마 구분, 빈 값 보존)
            String[] tokens = StringUtils.splitPreserveAllTokens(msg.getMsg(), ',');
            String messageId = tokens[MSG_ID_IDX];

            switch (messageId) {
                case "2":  _processOhtReport(tokens, msg);   break; // Vehicle 상태
                case "1":  _processMcpOnline(tokens, msg);   break; // MCP On-Line
                case "4":  _processDeviceStatus(tokens, msg); break; // 기기 상태
            }
        }
    }
}
```

### 9.3 Vehicle 상태 처리 및 업데이트

```java
private void _processOhtReport(String[] tokens, Msg msg) {
    String vhlName  = tokens[2];   // Vehicle명
    String state    = tokens[3];   // 상태 (1~11)
    String curAddr  = tokens[7];   // 현재 번지
    String nextAddr = tokens[9];   // 다음 번지
    String runCycle = tokens[10];  // 실행 Cycle
    String vhlCycle = tokens[11];  // Vehicle Cycle
    String carrier  = tokens[12];  // Carrier ID

    Vhl vhl = DataService.getDataSet().getVhlMap().get(vhlName);
    if (vhl != null) {
        vhl.setState(VHL_STATE.fromCode(state));
        vhl.setDetailState(VHL_DET_STATE.fromCode(vhlCycle));
        vhl.setRunCycle(RUN_CYCLE.fromCode(runCycle));

        // RailEdge 속력 업데이트
        RailEdge railEdge = findRailEdge(curAddr, nextAddr);
        if (railEdge != null) {
            railEdge.addVelocity(calculatedVelocity);
            railEdge.addHistory();
        }
    }
}
```

---

## 10. Logpresso 데이터 저장

> **중요**: 데이터는 반드시 Logpresso DB에 저장해야 합니다. CSV 파일로 저장하지 마세요.

### 10.1 Logpresso Tuple API — 데이터 삽입

#### 방법 1: LogpressoAPI.setInsertTuples() — 직접 삽입

```java
private boolean _insertHidOffLogpresso(HidOffRecordItem recordItem, long currentMilli) {
    Tuple tuple = new Tuple();
    tuple.put("FAB_ID",       recordItem.getFabId());
    tuple.put("MCP_NM",       recordItem.getMcpName());
    tuple.put("VHL_ID",       recordItem.getVhlId());
    tuple.put("HID_ID",       recordItem.getHidId());
    tuple.put("OFF_TIME",     currentMilli);
    tuple.put("FROM_ADDRESS", recordItem.getFromAddress());
    tuple.put("TO_ADDRESS",   recordItem.getToAddress());

    return LogpressoAPI.setInsertTuples("ATLAS_OHT_HID_OFF", List.of(tuple), 20);
}
```

#### 방법 2: Util.insertInLogpressoDatabase() — 유틸리티 래퍼

```java
List<Tuple> logpressoData = new ArrayList<>();

for (RailEdge railEdge : railEdges) {
    Tuple tuple = new Tuple();
    tuple.put("fabId",      fabId);
    tuple.put("mcpName",    mcpName);
    tuple.put("railEdgeId", railEdge.getId());
    tuple.put("velocity",   railEdge.getVelocity());
    tuple.put("HID_ID",     railEdge.getHIDId());
    logpressoData.add(tuple);
}

Util.insertInLogpressoDatabase(logpressoData, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
```

#### 방법 3: HID 정보 삽입 (DataService.java)

```java
private void _insertHidDataIntoLogpresso(Map<String, List<String>> data) {
    List<Tuple> logpressoData = new ArrayList<>();

    for (Map.Entry<String, List<String>> entry : data.entrySet()) {
        Tuple tuple = new Tuple();
        tuple.put("FAB_ID",  fabId);
        tuple.put("MCP_NM",  mcpName);
        tuple.put("HID_ID",  entry.getKey());
        tuple.put("START",   entry.getValue().get(0));
        tuple.put("ADDRESS", String.join(",", entry.getValue()));
        logpressoData.add(tuple);
    }

    LogpressoAPI.setInsertTuples("ATLAS_HID_INFO", logpressoData, 20);
}
```

### 10.2 Logpresso 테이블 구조

#### ATLAS_OHT_HID_OFF — HID Off 기록

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| FAB_ID | String | Fab 식별자 (예: M14A) |
| MCP_NM | String | MCP 명칭 |
| VHL_ID | String | Vehicle 식별자 |
| HID_ID | int | HID 구간 ID |
| OFF_TIME | long | Off 시각 (밀리초) |
| FROM_ADDRESS | int | 시작 번지 |
| TO_ADDRESS | int | 종료 번지 |

#### ATLAS_HID_INFO — HID 구간 정보

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| FAB_ID | String | Fab 식별자 |
| MCP_NM | String | MCP 명칭 |
| HID_ID | String | HID 식별자 |
| START | String | 시작 주소 |
| ADDRESS | String | 주소 목록 (콤마 구분) |

#### ATLAS_RAIL_TRAFFIC — Rail 교통 속력 데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| createTime | long | 생성 시각 |
| fabId | String | Fab 식별자 |
| mcpName | String | MCP 명칭 |
| railEdgeId | String | Rail Edge ID |
| velocity | double | 현재 속력 (m/min) |
| maxVelocity | double | 최대 속력 (m/min) |
| absoluteVelocity | double | 절대 속력 비율 |
| vhlCnt | int | 구간 내 Vehicle 수 |
| passCnt | long | 통과 횟수 |
| HID_ID | int | HID 구간 ID |

### 10.3 Logpresso 데이터 조회

```java
// XML 설정 파일에서 쿼리 파라미터 로드
XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY);

// 쿼리 실행 (예: 최근 속력 데이터 조회)
List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");

for (Map<String, Object> row : queryData) {
    String railEdgeId = (String) row.get("railEdgeId");
    double velocity   = (double) row.get("velocity");

    RailEdge edge = DataService.getDataSet().getRailEdgeMap().get(railEdgeId);
    if (edge != null) {
        edge.setVelocity(velocity);
    }
}
```

#### Logpresso API 요약

| 메서드 | 용도 |
|--------|------|
| `LogpressoAPI.setInsertTuples(tableName, tuples, timeout)` | 테이블에 Tuple 리스트 삽입 |
| `Util.insertInLogpressoDatabase(tuples, tableName, caller)` | 삽입 래퍼 (로그 포함) |
| `XmlUtil.selectLogpressoQuery(queryName)` | XML 정의 쿼리 실행 |
| `XmlUtil.loadLogpressoParm(path)` | 쿼리 파라미터 로드 |

---

## 11. Java 데이터 모델

### 11.1 RailEdge — Rail 구간 정보

```java
public class RailEdge extends AbstractEdge {
    private double maxVelocity = -1;     // 최대 속력 (m/min)
    private double velocity    = -1;     // 현재 속력 (m/min)
    private long   hisCnt      = 0;      // 이력 카운트
    private boolean changedVelocity = false;
    private int    hidId = -1;           // HID 구간 ID
    private int    fromAddress, toAddress;
    private RAIL_DIRECTION railDir;      // LEFT / RIGHT
    private ConcurrentHashMap<String, Integer> vhlIdMap;

    // 속력 업데이트 (가중 이동 평균)
    public void addVelocity(double velocity) {
        if (Double.isNaN(velocity) || Double.isInfinite(velocity)) return;
        velocity = Math.max(1.5, Math.min(velocity, maxVelocity));
        setLastVelocity(this.velocity);

        if (hisCnt > 0) {
            double w = PredictionPara.getInstance().getLastHisWeight();
            this.velocity = (this.velocity * w) + (velocity * (1.0 - w));
        } else {
            this.velocity = velocity;
        }
        this.changedVelocity = true;
    }

    // 비용 계산 (경로 탐색용)
    public long getCost(String carrierId) {
        if (velocity <= 0) velocity = 1;
        return (long)(length / (velocity * 1000 / 60 / 1000));
    }

    // 밀도 계산 (%)
    public float getDensity() {
        float vhlLen = fabId.startsWith("M14") ? 1084f : 1243f;
        float railLen = Math.max((float)length - ((float)length % vhlLen), vhlLen);
        return Math.min((vhlLen * vhlIdMap.size()) / railLen * 100f, 100f);
    }
}
```

### 11.2 CnvEdge — Conveyor 구간 정보

```java
public class CnvEdge extends AbstractEdge {
    private long avgTransferIntervalT = 150;  // 평균 반송 시간 (ms)

    public long getCost(String carrierId) { return avgTransferIntervalT; }

    // 비용 업데이트 (가중 이동 평균, 300~30000ms 범위)
    public void addCost(long newCost) {
        newCost = Math.max(300, Math.min(newCost, 30000));
        double w = PredictionPara.getInstance().getLastHisWeight();
        setAvgTransferIntervalT((long)((avgTransferIntervalT * w) + ((1.0 - w) * newCost)));
    }

    public void setAvgTransferIntervalT(long val) {
        this.avgTransferIntervalT = Math.max(300, Math.min(val, 30000));
    }

    public boolean isAvailable() {
        return getFromNode().isAvailable() && getToNode().isAvailable();
    }
}
```

### 11.3 TrafficBatch — Rail 교통 데이터 배치 (Quartz Job)

```java
public class TrafficBatch implements Job {
    private static ConcurrentMap<String, Long> lastHisCntMap = new ConcurrentHashMap<>();

    @Override
    public void execute(JobExecutionContext ctx) {
        for (FunctionItem fi : Env.getSwitchMap().values()) {
            if (!fi.isUseRailTraffic()) continue;

            List<Tuple> logpressoData = new ArrayList<>();
            double totalVel = 0; int count = 0;

            for (RailEdge edge : DataService.getDataSet().getRailEdgeMap().values()) {
                if (!edge.getFabId().equals(fi.getFabId())) continue;

                if (edge.isChangedVelocity()) { totalVel += edge.getVelocity(); count++; }

                Tuple t = new Tuple();
                t.put("createTime", System.currentTimeMillis());
                t.put("railEdgeId", edge.getId());
                t.put("fabId",      fi.getFabId());
                t.put("velocity",   edge.getVelocity());
                t.put("HID_ID",     edge.getHIDId());

                if (fi.isUseRailTrafficMaxVelocity())
                    t.put("maxVelocity", edge.getMaxVelocity());
                if (fi.isUseRailTrafficAbsoluteVelocity())
                    t.put("absoluteVelocity", edge.getVelocity() / edge.getMaxVelocity());
                if (fi.isUseRailTrafficVhlCnt())
                    t.put("vhlCnt", edge.getVhlIdMap().size());
                if (fi.isUseRailTrafficPassCnt()) {
                    long pass = edge.getHisCnt() - lastHisCntMap.getOrDefault(edge.getId(), 0L);
                    t.put("passCnt", Math.max(pass, 0));
                }

                logpressoData.add(t);
                lastHisCntMap.put(edge.getId(), edge.getHisCnt());
            }

            double avg = Math.round((totalVel / count) * 10) / 10.0;
            // Header Tuple 추가 후 Logpresso 저장
            Util.insertInLogpressoDatabase(logpressoData, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
        }
    }
}
```

### 11.4 Java Vehicle Enum (Atlas Server)

#### VHL_STATE

| 코드 | 상태 | 코드 | 상태 |
|------|------|------|------|
| 1 | RUN (운전중) | 6 | OBS_BZ_STOP |
| 2 | STOP (정지) | 7 | JAM (삽체) |
| 3 | ABNORMAL (이상) | 8 | HT_STOP (정체) |
| 4 | MANUAL (수동) | 9 | E84_TIMEOUT |
| 5 | REMOVING (추출중) | | |

#### VHL_DET_STATE (작업 상태 상세)

| 코드 | 상태 | 코드 | 상태 |
|------|------|------|------|
| 0 | NONE | 101 | MOVING |
| 1 | WAIT | 102 | PARKING_UTS_MOVING |
| 2 | STAGE_WAIT | 103 | STAGE_MOVING |
| 3 | STANDBY_WAIT | 104 | STANDBY_MOVING |
| 4 | DEPOSIT_SIG_WAIT | 105 | BALANCE_MOVING |
| 5 | ACQ_WAIT | 106 | PARKING_MOVING |
| 6 | MAP_WAIT | | |

#### RUN_CYCLE / VHL_CYCLE

| RUN_CYCLE 코드 | Cycle | VHL_CYCLE 코드 | Cycle |
|---------------|-------|---------------|-------|
| 0 | NONE | 0 | NONE |
| 1 | POSITION_DETECT | 1 | MOVING |
| 2 | MOVING | 2 | ACQUIRE_MOVING |
| 3 | ACQUIRE | 3 | ACQUIRING |
| 4 | DEPOSIT | 4 | DEPOSIT_MOVING |
| 5 | SAMPLING | 5 | DEPOSITING |
| 9 | FLOOR_TRANS | 6 | MAINT_MOVING |
| 21 | WHEELDRIVE | 7 | WAITING |
| 2E | BUILDING_TRANS | 8 | INPUT |
| 2F | EVACUATION | | |

---

## 12. AGV/CNV 개발 체크리스트 (확장)

### 12.1 Atlas Server (Java) 구현

- [ ] OhtUdpListener — UDP 소켓 수신 (DatagramSocket, 1500byte 버퍼)
- [ ] OhtMsgWorkerRunnable — CSV 메시지 파싱 (splitPreserveAllTokens)
- [ ] Vehicle 상태 업데이트 (Vhl 객체, VHL_STATE/VHL_DET_STATE 매핑)
- [ ] RailEdge 속력 업데이트 (addVelocity — 가중 이동 평균)
- [ ] TrafficBatch — 1분 주기 배치 (평균 속력, 개별 Edge 데이터)

### 12.2 Logpresso 데이터 저장

- [ ] Logpresso Tuple API 연동 (LogpressoAPI.setInsertTuples)
- [ ] ATLAS_OHT_HID_OFF 테이블 — HID Off 기록 저장
- [ ] ATLAS_HID_INFO 테이블 — HID 구간 정보 저장
- [ ] ATLAS_RAIL_TRAFFIC 테이블 — Rail 교통 속력 데이터 저장
- [ ] XmlUtil.selectLogpressoQuery — 초기 속력 데이터 조회
- [ ] Util.insertInLogpressoDatabase — 일괄 삽입 래퍼 사용

---

*본 문서는 AMP API GUIDE v1.0.1.7, C_FABSCOPE-MCP 통신사양서, SYSVIEW 통신사양서 v1.8.0, 메세지 FMS 샘플사양서, Atlas Server Java 소스를 기반으로 통합 작성되었습니다. 데이터 저장: Logpresso DB (Tuple API)*
