# AGV (Automated Guided Vehicle) 개발 가이드

> SK Hynix Fab 환경 — Atlas 서버 UDP 수신 기반 AGV 시스템 개발 레퍼런스

---

## 1. 시스템 아키텍처

```
┌──────────┐   SECS/GEM   ┌──────────────┐   UDP/IP    ┌───────────────┐
│   HOST   │◄────────────►│   FabScope   │◄──────────►│  CLW MCP7     │
│ (MES/ERP)│              │ (SysView+MSS)│  3600/3500  │  (AGV 제어)   │
└──────────┘              └──────┬───────┘            └───────┬───────┘
                                 │                            │
                           UDP/IP│                     TCP/IP │ AMP Remote.DLL
                                 │                            │
                          ┌──────▼───────┐            ┌───────▼───────┐
                          │ Atlas 서버   │            │   AGV 설비    │
                          │ (UDP 수신)   │            │  프로그램     │
                          └──────────────┘            └───────────────┘
```

---

## 2. UDP 통신 사양

### 2.1 프로토콜 기본 정보

| 항목 | SysView계 | MSS계 |
|------|----------|-------|
| 프로토콜 | UDP/IP | UDP/IP |
| 포트 번호 | 3600 (기본) | 3500 (기본) |
| 메시지 형식 | CSV (콤마 구분) | CSV (콤마 구분) |
| 문자 코드 | ASCII | ASCII |
| 최대 크기 | 1500 byte (MTU) | 1500 byte (MTU) |
| 빈 항목 표기 | `,,` | `,,` |

### 2.2 Atlas 서버 UDP 수신 구조

Atlas 서버에서 MCP가 보내는 UDP 패킷을 수신하여 AGV 상태를 모니터링합니다.

```
[CLW MCP7] ──UDP──► [Atlas 서버 (포트 3600/3500)]
                          │
                          ├── Text ID:1  MCP On-Line 보고 (5초 주기)
                          ├── Text ID:2  Vehicle 상태 보고 ★ AGV 핵심
                          ├── Text ID:4  기기 상태 보고
                          ├── Text ID:15 대차 주행 경로 보고
                          │
                          ├── Text ID:3  이상/복구 보고 (MSS)
                          ├── Text ID:13 작업 데이터 보고 (MSS)
                          └── Text ID:17 삽체/정체 보고 (MSS)
```

### 2.3 UDP 패킷 파싱 방법

수신된 UDP 패킷은 CSV 형태이므로 콤마로 분리하여 파싱합니다.

```
수신 패킷 예시:
"2,OHT,V047,1,1,0000,1,1232,0,1202,4,4,PIN2702,20308,00000000,0000,IR5S005S_2,STB031-R08,50,0,0"

파싱: Split(',') → fields[0]=텍스트ID, fields[1]=MCP명칭, fields[2]=Vehicle명, ...
```

### 2.4 텍스트 ID 범위

| ID 범위 | 용도 |
|---------|------|
| 1 ~ 100 | 공용 |
| 101 ~ 200 | CLW MCP 전용 |
| 201 ~ 300 | STK MCP, SSS 전용 |

---

## 3. AGV 관련 SysView계 메시지

### 3.1 Text ID:1 — MCP On-Line 보고

**보고 주기**: 5초 / 상태변화 시 / 기동 시
**Down 판정**: 15초 이상 미수신 시 MCP Down 인식

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `1` |
| 1 | MCP 명칭 | 유니크 명칭 |
| 2 | Control 상태 | `ON-LINE` / `OFF-LINE` |
| 3 | TSC 상태 | `AUTO` / `PAUSED` / `PAUSING` |
| 4 | Alarm 상태 | `NO ALARMS` / `ALARMS` |
| 5 | MCP 상태 구분 | `0`:통상, `1`:선반 충진율 over |

### 3.2 Text ID:2 — Vehicle 상태 보고 ★ AGV 핵심

**보고 조건**: MCP 기동 / Vehicle 상태 변화 / 상태보고요구 수신 (Vehicle 수만큼 전송)

| 순번 | 필드 | FMS | 내용 |
|------|------|-----|------|
| 0 | 텍스트 ID | O | `2` |
| 1 | MCP 명칭 | | 유니크 명칭 |
| 2 | Vehicle명 | O | Vehicle 식별 명칭 |
| 3 | 상태 | O | `1`:운전, `2`:정지, `3`:이상, `4`:수동, `5`:추출, `6`:OBS/BZ-STOP, `7`:삽체, `8`:정체, `9`:E84 Timeout, `10`:주회없음 E84 Timeout, `11`:HT-STOP |
| 4 | 재하 정보 | | `0`:없음, `1`:있음 |
| 5 | Error Code | | `0000`~`FFFF` |
| 6 | 통신 상태 | | `1`:정상, `2`:통신단절 |
| 7 | 현재 번지 | O | 현재 위치 번지 |
| 8 | 현재 번지 거리 | | 100mm 단위 |
| 9 | 다음 번지 | O | 이동 목표 번지 |
| 10 | 실행 Cycle | | `0`:없음, `1`:위치확인, `2`:이동, `3`:Unload, `4`:Load, `5`:추출, `9`:층간이동, `21`:주회, `22`:수동, `23`:주행학습, `24`:이재부학습, `25~27`:테스트, `2C`:계측, `2D`:흡인구, `2E`:동간이동, `2F`:퇴피이동, `3C`:휠교체, `3D`:퇴피추출, `3E`:검사, `3F`:세차 |
| 11 | 실행 Cycle 진척 | O | `0`:없음, `1`:이동, `2`:Unload이동, `3`:Unload이재, `4`:Load이동, `5`:Load이재, `6`:유지보수이동, `7`:대체대기, `8`:투입, `9`:Unload도착, `10`:Load도착 |
| 12 | Carrier ID | O | 적재 Carrier ID |
| 13 | Destination | O | 목적지 Station |
| 14 | E/M 상태 | | Bit 배치 (배터리 정보) |
| 15 | GroupID | | 없으면 `0000` |
| 16 | 반송원 Port | | Source Port ID |
| 17 | 반송처 Port | | Dest Port ID |
| 18 | 반송 우선도 | | `0`:무효, `1`~`99` |
| 19 | 작업상태 상세 | | `0~6`:대기계, `101~113`:이동계 |
| 20 | 대차 주행거리 | | mm 단위 (도착시만) |
| 21 | Command ID | | |
| 22 | Bay 명칭 | | |
| 23 | 도착 예상 시간 | | 경로 확정시 시간 (실시간 갱신X) |
| 24 | 예약 Command ID | | |

#### 샘플 메시지 해석

```
2,OHT,V047,1,1,0000,1,1232,0,1202,4,4,PIN2702,20308,00000000,0000,IR5S005S_2,STB031-R08,50,0,0
```

→ V047 호기 | 운전중(1) | Carrier있음(1) | 1232번지 → 1202번지 | Load이동중 | PIN2702 적재 | 목적지 20308 | 반송원 IR5S005S_2 → 반송처 STB031-R08 | 우선도 50

### 3.3 Text ID:4 — 기기 상태 보고

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `4` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | `10`:VHL, `50`:BZ, `60`:MTL, `91`:AD/FD, `92`:HID, `93`:FFU |
| 3 | 기기명칭 | |
| 4 | 상태 | `1`:정상, `2`:이상, `3`:유지보수, `4`:운전OFF, `5`:분리 |
| 5 | Error Code | `0000`~`FFFF` |

### 3.4 Text ID:15 — 대차 주행 경로 보고

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `15` |
| 1 | 기종 코드 | |
| 2 | Machine ID | |
| 3 | 기본 분기 방향 | `0`:왼쪽, `1`:오른쪽 |
| 4 | 주행 플래그 | `0`:정지, `1`:주행중 |
| 5 | 시작 번호 | |
| 6 | 종료 번호 | |
| 7 | 기본 외 분기 번지 수 | 0~300 |
| 8+ | 기본 외 분기 번지 | 쉼표 구분 |
| 마지막 | Command ID | |

### 3.5 Text ID:101 — TSC 운용상태 보고 (CLW MCP)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `101` |
| 1 | MCP 명칭 | |
| 2 | HID 만료 | |
| 3 | GridLock 발생 상태 | |
| 4 | 삽체 상태 | |
| 5 | EMG 상태 | `0`:정상, `1`:비상, `2`:거절 |
| 6 | 반송수 | |
| 7 | 가동 VHL 수 | |
| 8 | 반송 부하율 | |

---

## 4. AGV 관련 MSS계 메시지

### 4.1 Text ID:3 — 이상/복구 보고

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `3` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | |
| 3 | 기기명칭 | |
| 4 | 상태 변화 일시 | `YYYY-MM-DD HH:MM:SS` |
| 5 | 상태 | `1`:정상, `2`:고장, `3`:유지보수, `4`:추출 |
| 6 | Error Code | |
| 7 | 도메인 명칭 | RM이상시: From→To 포트 |
| 8 | 포트 ID | EQ/AZFS PortID |

### 4.2 Text ID:13 — 작업 데이터 보고 (v2.0+)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `13` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | |
| 3 | 기기명칭 | (대체시 대체 후 Vehicle) |
| 4 | Carrier명칭 | |
| 5 | 반송 Priority | |
| 6 | From 포트 | |
| 7 | To 포트 | |
| 8 | 반송지시 수신일시 | |
| 9 | 공Carrier 반송 개시 | |
| 10 | Unload 시작 | |
| 11 | 실Carrier 반송 개시 | |
| 12 | Load 개시 | |
| 13 | 반송 완료 | |
| 14 | 반송 지연 요인 | `00010`:주회, `00100`:Paused |
| 15 | 반송 중지 요인 | `2`:Unsuccessful, `3`:Alternate, `4`:수동중단, `5`:Intermediate |
| 16 | Command ID | |
| 17 | MCP 내 Priority | |
| 18 | Reroute 횟수 | CLW-MCP만 |

### 4.3 Text ID:17 — 삽체/정체 보고

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `17` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | |
| 3 | 기기명칭 | |
| 4 | 상태 변화 일시 | |
| 5 | 상태 | `1`:정상, `2`:삽체, `3`:정체 |
| 6 | 번지 | |
| 7 | 거리 | |
| 8 | 다음 번지 | |

### 4.4 Text ID:102 — 대차 투입/추출 보고

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `102` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | |
| 3 | 기기명칭 | |
| 4 | 일시 | |
| 5 | 보고 구분 | `1`:투입, `2`:추출 |

---

## 5. AMP Remote Interface (설비 ↔ AMP)

### 5.1 초기화 및 연결

```csharp
CRemoteServer m_RemoteServer = new CRemoteServer();

// 이벤트 등록
m_RemoteServer.MonitorGetData      = GetData;
m_RemoteServer.ErrorEvent         += ErrorHandler;
m_RemoteServer.OperationEvent     += OperationHandler;
m_RemoteServer.CarrierEvent       += CarrierHandler;
m_RemoteServer.TransferEvent      += TransferHandler;
m_RemoteServer.ControlStatusEvent += ControlStatusHandler;
m_RemoteServer.EQModeEvent        += EQModeHandler;
m_RemoteServer.GlobalTransferEvent += GlobalTransferHandler;

// 초기화 → 시작
m_RemoteServer.Initialize("AGV_001", "AGV_EQP.exe", "v1.0.0.0", 10000, 500, 100);
m_RemoteServer.Start();
```

### 5.2 AGV 데이터 수집 (MonitorGetData)

```csharp
public void GetData(string EQPID, CRemoteObject Obj)
{
    // 필수: 상태
    Obj.ControlState = eControlState.ONLINE_LOCAL;
    Obj.SCState      = eSCState.RUN;
    Obj.EQMode       = eEqMode.OPERATOR;

    // 필수: Alarm
    Obj.AlarmInfo ??= new Dictionary<string, Alarm>();

    // 필수: Carrier / Transfer
    Obj.CarrierInfo ??= new Dictionary<string, Carrier>();
    Obj.TrInfo      ??= new Dictionary<string, Transfer>();

    // ★ AGV 전용: Car 정보
    Obj.CarInfo ??= new Dictionary<string, Car>();
    // → 각 Vehicle의 위치, 상태, 경로, VehicleState 등 설정

    // 선택: Zone, Port
    Obj.ZoneInfo ??= new Dictionary<string, Zone>();
    Obj.PortInfo ??= new Dictionary<string, Port>();
}
```

### 5.3 Car 클래스 (AGV Vehicle 정보)

```csharp
public class Car
{
    public string EqpID;         // 설비 ID
    public string UnitID;        // 자체 Unit ID
    public string HostID;        // Host Unit ID
    public int    FaultCode;     // Alarm Code
    public string CarrierID;     // 적재 Carrier
    public int    Kind;          // Unit 종류
    public int    UnitState;     // 0:Normal, 1:Stop, 2:Fault, 3:Disable/PM
    public int    ProcessStatus; // 0:Empty, 1:Idle, 2:Busy, 3:Pausing, 4:Paused
    public string Location;      // 현재 위치
    public int    XPosition;     // 화면 X
    public int    YPosition;     // 화면 Y
    public string FullPath;      // 전체 경로
    public string RunPath;       // 지역 경로
    public int    MotionStep;    // Motion Step
    public int    VehicleJob;    // 0:NONE, 1:SINGLE, 2:MULTI, 3:DOUBLE, 4:BATTERY
    public int    VehicleState;  // 2:NOTASSIGNED, 3:ENROUTE, 4:PARKED, 5:LOADING,
                                 // 6:UNLOADING, 7:ERROR, 8:DOWN, 9:CHARGE, 10:MOVING, 14:AVOID
    public int    VehicleType;   // 0:BROADBAND, 1:LOCAL
    public bool   AssignEnable;  // ASSIGN 가능
    public string GroupID;       // 소속 GROUP
    public string BayID;         // 소속 BAY
    public string ZoneName;      // Zone Name
}
```

### 5.4 조작 명령 처리

```csharp
eAckCode OperationHandler(IPAddress ip, eRemoteCommand cmd, string unitID)
{
    switch (cmd)
    {
        case eRemoteCommand.Run:        // 운전
        case eRemoteCommand.Stop:       // 정지
        case eRemoteCommand.AlarmClear: // 알람 해제
        case eRemoteCommand.SetPMMode:  // PM 모드
    }
    return eAckCode.Ack; // 불가시 eAckCode.Nak
}
```

### 5.5 연계반송 (GlobalTransfer)

```csharp
void GlobalTransferHandler(IPAddress ip, string carrierID,
    string srcEqpID, string srcUnitID, string destEqpID, string destUnitID)
{
    // HOST로 S6F11 Global Transfer 전송
    // S6F12 ACK 수신 후:
    m_RemoteServer.GlobalTransfer_Request_Ack(ip, eAckCode.Ack);
}
```

---

## 6. AGV 개발 체크리스트

### UDP 수신 (Atlas 서버)
- [ ] UDP 소켓 바인딩 (포트 3600 SysView / 3500 MSS)
- [ ] CSV 패킷 파싱 모듈
- [ ] Text ID별 핸들러 라우팅
- [ ] MCP Down 감지 (15초 타임아웃)

### AMP 연동 (설비)
- [ ] CRemoteServer 초기화/시작/종료
- [ ] MonitorGetData: Car, Alarm, Carrier, Transfer 수집
- [ ] OperationEvent: Run/Stop/AlarmClear/SetPMMode
- [ ] TransferEvent: Creat/Cancel/Abort
- [ ] CarrierEvent: Install/Remove
- [ ] ControlStatusEvent / EQModeEvent
- [ ] GlobalTransferEvent (연계반송)

### Vehicle 관리
- [ ] VehicleState 상태 전이
- [ ] 위치/경로 추적 (번지, 거리, FullPath)
- [ ] 삽체/정체 감지
- [ ] 배터리(E/M) 모니터링
- [ ] 주행거리 집계

### Atlas Server (Java) — Logpresso 저장
- [ ] OhtUdpListener — UDP 소켓 수신 (DatagramSocket, 1500byte 버퍼)
- [ ] OhtMsgWorkerRunnable — CSV 메시지 파싱 (splitPreserveAllTokens)
- [ ] Vehicle 상태 업데이트 (Vhl, VHL_STATE/VHL_DET_STATE 매핑)
- [ ] RailEdge 속력 업데이트 (addVelocity — 가중 이동 평균)
- [ ] TrafficBatch — 1분 주기 배치
- [ ] Logpresso Tuple API 연동 (LogpressoAPI.setInsertTuples)
- [ ] ATLAS_OHT_HID_OFF / ATLAS_HID_INFO / ATLAS_RAIL_TRAFFIC 테이블 저장

---

## 7. Atlas Server — Java UDP 수신 및 Logpresso 저장

> **중요**: 데이터는 반드시 Logpresso DB에 저장. CSV 파일 저장 금지.

### 7.1 OhtUdpListener — UDP 소켓 수신

```java
public class OhtUdpListener implements Runnable {
    private DatagramSocket socket;
    private byte[] buffer = new byte[1500];  // MTU

    public OhtUdpListener(int port, String fabId, String mcpName) {
        this.socket = new DatagramSocket(port);
    }

    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
            socket.receive(packet);
            String message = new String(packet.getData()).trim();

            Msg msg = new Msg();
            msg.setFabId(fabId);
            msg.setMcpName(mcpName);
            msg.setMsg(message);
            msg.setMillis(System.currentTimeMillis());
            DataService.getInstance().queue.add(msg);
        }
    }
}
```

### 7.2 OhtMsgWorkerRunnable — 메시지 파싱

```java
public class OhtMsgWorkerRunnable implements Runnable {
    @Override
    public void run() {
        while (true) {
            Msg msg = DataService.getInstance().queue.poll();
            if (msg == null) { Thread.sleep(10); continue; }

            String[] tokens = StringUtils.splitPreserveAllTokens(msg.getMsg(), ',');
            String messageId = tokens[0];

            switch (messageId) {
                case "2":  _processOhtReport(tokens, msg);    break;
                case "1":  _processMcpOnline(tokens, msg);    break;
                case "4":  _processDeviceStatus(tokens, msg); break;
            }
        }
    }

    private void _processOhtReport(String[] tokens, Msg msg) {
        String vhlName = tokens[2], state = tokens[3];
        String curAddr = tokens[7], nextAddr = tokens[9];

        Vhl vhl = DataService.getDataSet().getVhlMap().get(vhlName);
        if (vhl != null) {
            vhl.setState(VHL_STATE.fromCode(state));
            vhl.setDetailState(VHL_DET_STATE.fromCode(tokens[11]));
            vhl.setRunCycle(RUN_CYCLE.fromCode(tokens[10]));

            RailEdge edge = findRailEdge(curAddr, nextAddr);
            if (edge != null) {
                edge.addVelocity(calculatedVelocity);
                edge.addHistory();
            }
        }
    }
}
```

### 7.3 RailEdge — 속력 업데이트 (가중 이동 평균)

```java
public class RailEdge extends AbstractEdge {
    private double maxVelocity = -1, velocity = -1;
    private long hisCnt = 0;
    private boolean changedVelocity = false;
    private int hidId = -1, fromAddress, toAddress;

    public void addVelocity(double velocity) {
        if (Double.isNaN(velocity) || Double.isInfinite(velocity)) return;
        velocity = Math.max(1.5, Math.min(velocity, maxVelocity));

        if (hisCnt > 0) {
            double w = PredictionPara.getInstance().getLastHisWeight();
            this.velocity = (this.velocity * w) + (velocity * (1.0 - w));
        } else {
            this.velocity = velocity;
        }
        this.changedVelocity = true;
    }

    public long getCost(String carrierId) {
        if (velocity <= 0) velocity = 1;
        return (long)(length / (velocity * 1000 / 60 / 1000));
    }

    public float getDensity() {
        float vhlLen = fabId.startsWith("M14") ? 1084f : 1243f;
        float railLen = Math.max((float)length - ((float)length % vhlLen), vhlLen);
        return Math.min((vhlLen * vhlIdMap.size()) / railLen * 100f, 100f);
    }
}
```

### 7.4 Logpresso 저장 — Tuple API

```java
// 방법 1: 직접 삽입
Tuple tuple = new Tuple();
tuple.put("FAB_ID",       fabId);
tuple.put("MCP_NM",       mcpName);
tuple.put("VHL_ID",       vhlId);
tuple.put("HID_ID",       hidId);
tuple.put("OFF_TIME",     currentMilli);
tuple.put("FROM_ADDRESS", fromAddr);
tuple.put("TO_ADDRESS",   toAddr);

LogpressoAPI.setInsertTuples("ATLAS_OHT_HID_OFF", List.of(tuple), 20);

// 방법 2: 유틸리티 래퍼 (일괄 삽입)
List<Tuple> data = new ArrayList<>();
// ... Tuple 추가 ...
Util.insertInLogpressoDatabase(data, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
```

### 7.5 TrafficBatch — 1분 주기 배치

```java
public class TrafficBatch implements Job {
    private static ConcurrentMap<String, Long> lastHisCntMap = new ConcurrentHashMap<>();

    public void execute(JobExecutionContext ctx) {
        List<Tuple> logpressoData = new ArrayList<>();

        for (RailEdge edge : DataService.getDataSet().getRailEdgeMap().values()) {
            Tuple t = new Tuple();
            t.put("createTime", System.currentTimeMillis());
            t.put("railEdgeId", edge.getId());
            t.put("fabId",      fabId);
            t.put("velocity",   edge.getVelocity());
            t.put("maxVelocity", edge.getMaxVelocity());
            t.put("absoluteVelocity", edge.getVelocity() / edge.getMaxVelocity());
            t.put("vhlCnt",     edge.getVhlIdMap().size());
            t.put("HID_ID",     edge.getHIDId());

            long pass = edge.getHisCnt() - lastHisCntMap.getOrDefault(edge.getId(), 0L);
            t.put("passCnt", Math.max(pass, 0));

            logpressoData.add(t);
            lastHisCntMap.put(edge.getId(), edge.getHisCnt());
        }

        Util.insertInLogpressoDatabase(logpressoData, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
    }
}
```

### 7.6 Logpresso 테이블 구조

#### ATLAS_OHT_HID_OFF

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| FAB_ID | String | Fab ID |
| MCP_NM | String | MCP 명칭 |
| VHL_ID | String | Vehicle ID |
| HID_ID | int | HID 구간 ID |
| OFF_TIME | long | Off 시각 (ms) |
| FROM_ADDRESS | int | 시작 번지 |
| TO_ADDRESS | int | 종료 번지 |

#### ATLAS_RAIL_TRAFFIC

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| createTime | long | 생성 시각 |
| fabId | String | Fab ID |
| railEdgeId | String | Rail Edge ID |
| velocity | double | 현재 속력 (m/min) |
| maxVelocity | double | 최대 속력 |
| absoluteVelocity | double | 속력 비율 |
| vhlCnt | int | Vehicle 수 |
| passCnt | long | 통과 횟수 |
| HID_ID | int | HID 구간 ID |

### 7.7 Java Vehicle Enum

| VHL_STATE | | VHL_DET_STATE | |
|-----------|------|-----------|------|
| 1: RUN | 6: OBS_BZ_STOP | 0: NONE | 101: MOVING |
| 2: STOP | 7: JAM | 1: WAIT | 102: PARKING_UTS |
| 3: ABNORMAL | 8: HT_STOP | 2: STAGE_WAIT | 103: STAGE_MOVING |
| 4: MANUAL | 9: E84_TIMEOUT | 3: STANDBY_WAIT | 104: STANDBY_MOVING |
| 5: REMOVING | | 4: DEPOSIT_SIG_WAIT | 105: BALANCE_MOVING |

### 7.8 Logpresso 조회

```java
XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY);
List<Map<String, Object>> data = XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");

for (Map<String, Object> row : data) {
    RailEdge edge = DataService.getDataSet().getRailEdgeMap().get(row.get("railEdgeId"));
    if (edge != null) edge.setVelocity((double) row.get("velocity"));
}
```

| Logpresso API | 용도 |
|---------------|------|
| `LogpressoAPI.setInsertTuples(table, tuples, timeout)` | Tuple 삽입 |
| `Util.insertInLogpressoDatabase(tuples, table, caller)` | 삽입 래퍼 |
| `XmlUtil.selectLogpressoQuery(queryName)` | 쿼리 실행 |
| `XmlUtil.loadLogpressoParm(path)` | 파라미터 로드 |
