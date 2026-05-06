# CNV (Conveyor) 개발 가이드

> SK Hynix Fab 환경 — Atlas 서버 UDP 수신 기반 CNV 시스템 개발 레퍼런스

---

## 1. 시스템 아키텍처

```
┌──────────┐   SECS/GEM   ┌──────────────┐   UDP/IP    ┌───────────────┐
│   HOST   │◄────────────►│   FabScope   │◄──────────►│  STK MCP7     │
│ (MES/ERP)│              │ (SysView+MSS)│  3600/3500  │  (CNV 제어)   │
└──────────┘              └──────┬───────┘            └───────┬───────┘
                                 │                            │
                           UDP/IP│                     TCP/IP │ AMP Remote.DLL
                                 │                            │
                          ┌──────▼───────┐            ┌───────▼───────┐
                          │ Atlas 서버   │            │   CNV 설비    │
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

Atlas 서버에서 STK MCP가 보내는 UDP 패킷을 수신하여 CNV 상태를 모니터링합니다.

```
[STK MCP7] ──UDP──► [Atlas 서버 (포트 3600/3500)]
                          │
                          ├── Text ID:1   MCP On-Line 보고 (5초 주기)
                          ├── Text ID:4   기기 상태 보고 ★ CNV 핵심
                          │
                          ├── Text ID:1   (MSS) 장비 상태 보고
                          ├── Text ID:3   (MSS) 이상/복구 보고
                          ├── Text ID:13  (MSS) 작업 데이터 보고
                          ├── Text ID:21  (MSS) Zone 정보 보고
                          ├── Text ID:201 (SysView) 반송기기 현재 위치 보고
                          └── Text ID:202 (SysView) 기기상 재하정보 보고
```

### 2.3 UDP 패킷 파싱

수신된 UDP 패킷은 CSV 형태이므로 콤마로 분리하여 파싱합니다.

```
수신 패킷 예시 (기기 상태 보고):
"4,STK_MCP01,303,CNV001,1,0000"

파싱: Split(',') → fields[0]=텍스트ID, fields[1]=MCP명칭, fields[2]=기종번호, ...
```

### 2.4 텍스트 ID 범위

| ID 범위 | 용도 |
|---------|------|
| 1 ~ 100 | 공용 |
| 101 ~ 200 | CLW MCP, STBC 전용 |
| 201 ~ 300 | STK MCP, SSS 전용 |

---

## 3. CNV 관련 SysView계 메시지

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

### 3.2 Text ID:4 — 기기 상태 보고 ★ CNV 핵심

MCP7 산하 기기(CNV 포함)의 상태를 보고합니다.

**보고 조건**: MCP 기동 / 상태 변화 / 상태보고요구 수신 (모든 기기에 대해 전송)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `4` |
| 1 | MCP 명칭 | 유니크 명칭 |
| 2 | 기종번호 | CNV 관련: 아래 표 참조 |
| 3 | 기기명칭 | 기기 식별 이름 |
| 4 | 상태 | `1`:정상, `2`:이상, `3`:유지보수, `4`:운전OFF(SSS), `5`:분리(SSS) |
| 5 | Error Code | `0000`~`FFFF` (상태≠2이면 `0000`) |

#### CNV 관련 기종번호

| 기종번호 | 기종 | 설명 |
|---------|------|------|
| `100` | STK MCP7 | MCP 자체 |
| **`303`** | **CNV (CONV)** | **컨베이어** |
| `320` | PIO_IF | PI/O Interface Panel |
| `324` | IFP | Interface Panel |
| `348` | PIO_IF_THROUGH | |
| `428` | S_ARM_TFE_W_TPORT_CNV | 단일 ARM TFE + 넓은 TPORT CNV |
| `434` | W_ARM_TFE_S_TPORT_CNV | 넓은 ARM TFE + 좁은 TPORT CNV |
| `437` | S_ARM_TFE_S_TPORT_CNV | 단일 ARM TFE + 좁은 TPORT CNV |
| `808` | CLL | Clean Lifter |
| `871` | SINGLE_LIFTER | 단일 리프터 |
| `872` | DOUBLE_LIFTER | 이중 리프터 |
| `909` | MIF | Middle Interface |
| `1111` | PNP | Picking & Place |

### 3.3 Text ID:201 — 반송기기 현재 위치 보고 (SSS → FabScope)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `201` |
| 1 | SC 명칭 | |
| 2+ | 기기 정보 (반복 MAX 10건) | 기기명, 위치 좌표 등 |

> 패킷 사이즈 관계상 10대 이상인 경우 여러 번 전송

### 3.4 Text ID:202 — 기기상 재하정보 보고 (SSS → FabScope)

CONV 및 VC(Vertical Carousel)의 재하 정보를 보고합니다.

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `202` |
| 1 | SC 명칭 | |
| 2+ | 기기 정보 (반복 MAX 10건) | |
| | 보고 구분 | `1`:CONV, `2`:VC |
| | Mode | `0`:None, `1`:입고, `2`:출고 (VC는 Empty) |
| | 최대 Buffer/Tray 수 | CONV: Buffer 수, VC: Tray 수 |
| | 실제 Buffer/Tray 수 | |
| | Full 발생시각 | `YYYY-MM-DD HH:MM:SS` |
| | Carrier ID 목록 | `\|CST1\|CST2\|...` (BCR 미완료: Empty) |

> CONV: END-P부터 순서대로 보고 / VC: Tray No 순서로 보고

---

## 4. CNV 관련 MSS계 메시지

### 4.1 Text ID:1 — 장비 상태 보고

MCP가 관리하는 모든 장비 상태를 보고합니다. 10대 이상 시 여러 번 전송.

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `1` |
| 1 | MCP 명칭 | |
| 2+ | 기기 정보 (반복 MAX 10건) | 상태: `1`:정상, `2`:고장, `3`:유지보수, `4`:추출 |

### 4.2 Text ID:3 — 이상/복구 보고

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
| 8 | 포트 ID | PortID 또는 유닛ID |

### 4.3 Text ID:13 — 작업 데이터 보고 (v2.0+)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `13` |
| 1 | MCP 명칭 | |
| 2 | 기종번호 | |
| 3 | 기기명칭 | |
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
| 18 | Load 선반 정보 | 설정에 따라 보고 |
| 19 | VLF 통과번지 | |
| 20 | Unload시 Tray 높이 | 예: `12270` (12.27mm) |
| 21 | 이중격납시 Tray 높이 | |

### 4.4 Text ID:21 — Zone 정보 보고 (STK-MCP)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `21` |
| 1 | MCP 명칭 | |
| 2 | Zone 구분 | `1`:MCP |
| 3 | ZONE명칭/MCP명칭 | |
| 4 | 데이터 보고 일시 | `YYYY-MM-DD HH:MM:SS` |
| 5 | 선반 총수 | |
| 6 | CST 수 | 금지 선반 CST 포함 |
| 7 | 유효 선반 수 | |

### 4.5 Text ID:203 — 정체 보고 (SSS)

| 순번 | 필드 | 내용 |
|------|------|------|
| 0 | 텍스트 ID | `203` |
| 1 | SC 명칭 | |
| 2 | 보고일시 | |
| 3 | 기종번호 | |
| 4 | 기기명칭 | |
| 5 | 보고 구분 | `1`:이재기, `2`:포트 |
| 6 | 상태 | `1`:정체 발생, `2`:정체 해제 |
| 7 | 최종 동작 일시 | |

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

// 초기화 → 시작
m_RemoteServer.Initialize("CNV_001", "CNV_EQP.exe", "v1.0.0.0", 10000, 500, 100);
m_RemoteServer.Start();
```

### 5.2 CNV 데이터 수집 (MonitorGetData)

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

    // ★ CNV 전용: Conveyor 정보
    Obj.ConveyorInfo ??= new Dictionary<string, Conveyor>();
    // → 각 Conveyor Unit의 상태, CarrierID, ProcessStatus 등

    // 선택: Shelf, Port, Zone
    Obj.ShelfInfo ??= new Dictionary<string, Shelf>();
    Obj.PortInfo  ??= new Dictionary<string, Port>();
    Obj.ZoneInfo  ??= new Dictionary<string, Zone>();
}
```

### 5.3 CNV 전용 조작 명령

CNV는 AGV와 달리 Home, StepClear, DataClear 명령이 추가로 있습니다.

```csharp
eAckCode OperationHandler(IPAddress ip, eRemoteCommand cmd, string unitID)
{
    switch (cmd)
    {
        case eRemoteCommand.Run:        // 운전
        case eRemoteCommand.Stop:       // 정지
        case eRemoteCommand.AlarmClear: // 알람 해제

        // ★ CNV 전용 명령
        case eRemoteCommand.Home:       // Servo Home
        case eRemoteCommand.StepClear:  // Step Clear
        case eRemoteCommand.DataClear:  // Data Clear

        case eRemoteCommand.SetPMMode:  // PM 모드
    }
    return eAckCode.Ack; // 불가시 eAckCode.Nak
}
```

### 5.4 Transfer 클래스 — CNV 전용 필드

Transfer 클래스에서 CNV에 특화된 필드:

```csharp
public class Transfer
{
    // ... 공통 필드 생략 ...

    // ★ CNV 전용
    public int State;
    // State = 10 (Moving) → AGV/CNV 전용 상태

    public DateTime ArrivedTime;
    // 목적지 도착 시간 (PORT일 경우 PIO 전 단계)
    // CNV / AGV 전용

    public DateTime LocationChangeTime;
    // 위치 변경 시간 기록
}
```

#### Transfer.State — 반송 상태값 (CNV 주요)

| 값 | 상태 | CNV 관련 |
|----|------|---------|
| 0 | None | |
| 1 | Queue | 대기열 |
| 2 | Transfering | 반송 중 |
| 3 | Complete | 완료 |
| 4 | Alternate | 대체 |
| 5 | Paused | 일시정지 |
| 6 | Cancelling | 취소 중 |
| 7 | Canceled | 취소됨 |
| 8 | Aborting | 중단 중 |
| 9 | Aborted | 중단됨 |
| **10** | **Moving** | **★ CNV/AGV 전용** |

### 5.5 Unit Kind — CNV 관련 Unit 종류

| 값 | 종류 | 설명 |
|----|------|------|
| 0 | Unknown | 알 수 없음 |
| 1 | Lift | 리프트 |
| 2 | Diverter | 분기기 |
| **3** | **Conveyor** | **컨베이어** |
| 4 | DiverterInPort | 분기기 입력 포트 |
| 5 | DiverterOutPort | 분기기 출력 포트 |
| **6** | **ConveyorInPort** | **컨베이어 입력 포트** |
| **7** | **ConveyorOutPort** | **컨베이어 출력 포트** |
| 8 | Crain | 크레인 |
| 9 | Shelf | 선반 |
| 10 | Auto_In_Port | 자동 입력 포트 |
| 11 | Auto_Out_Port | 자동 출력 포트 |
| 12 | Auto_Both_Port | 자동 양방향 포트 |
| 13 | Manual_In_Port | 수동 입력 포트 |
| 14 | Manual_Out_Port | 수동 출력 포트 |
| 15 | Manual_Both_Port | 수동 양방향 포트 |

### 5.6 UnitState / ProcessStatus (공통)

| UnitState | 상태 | ProcessStatus | 상태 |
|-----------|------|--------------|------|
| 0 | Normal | 0 | Empty |
| 1 | Stop | 1 | Idle |
| 2 | Fault | 2 | Busy |
| 3 | Disable/PM | 3 | Pausing |
| | | 4 | Paused |

---

## 6. Enum 정리

### eRemoteCommand — CNV 관련 명령

| 값 | 용도 | 대상 이벤트 | CNV |
|----|------|-----------|-----|
| Run | 운전 | OperationEvent | 공통 |
| Stop | 정지 | OperationEvent | 공통 |
| AlarmClear | 알람 해제 | OperationEvent | 공통 |
| **Home** | **Servo Home** | **OperationEvent** | **★ CNV** |
| **StepClear** | **Step Clear** | **OperationEvent** | **★ CNV** |
| **DataClear** | **Data Clear** | **OperationEvent** | **★ CNV** |
| SetPMMode | PM 모드 | OperationEvent | 공통 |
| Install | Carrier 설치 | CarrierEvent | 공통 |
| Remove | Carrier 제거 | CarrierEvent | 공통 |
| Creat | 반송 생성 | TransferEvent | 공통 |
| Cancel | 반송 취소 | TransferEvent | 공통 |
| Abort | 반송 중단 | TransferEvent | 공통 |

---

## 7. CNV 개발 체크리스트

### UDP 수신 (Atlas 서버)
- [ ] UDP 소켓 바인딩 (포트 3600 SysView / 3500 MSS)
- [ ] CSV 패킷 파싱 모듈
- [ ] Text ID별 핸들러 라우팅
- [ ] MCP Down 감지 (15초 타임아웃)

### AMP 연동 (설비)
- [ ] CRemoteServer 초기화/시작/종료
- [ ] MonitorGetData: Conveyor, Alarm, Carrier, Transfer 수집
- [ ] OperationEvent: Run/Stop/AlarmClear/Home/StepClear/DataClear/SetPMMode
- [ ] TransferEvent: Creat/Cancel/Abort
- [ ] CarrierEvent: Install/Remove
- [ ] ControlStatusEvent / EQModeEvent

### CNV 고유 관리
- [ ] Conveyor Unit 상태 관리 (Kind=3,6,7)
- [ ] Transfer.State=10 (Moving) 처리
- [ ] Transfer.ArrivedTime 도착 시간 관리
- [ ] Zone 정보 관리 (Text ID:21)
- [ ] 재하 정보 관리 (Text ID:202)
- [ ] 정체 감지 및 보고 (Text ID:203)
- [ ] Buffer Full 상태 모니터링

### Atlas Server (Java) — Logpresso 저장
- [ ] OhtUdpListener — UDP 소켓 수신 (DatagramSocket, 1500byte 버퍼)
- [ ] OhtMsgWorkerRunnable — CSV 메시지 파싱
- [ ] CnvEdge avgTransferIntervalT 비용 관리 (300~30000ms)
- [ ] Logpresso Tuple API 연동 (LogpressoAPI.setInsertTuples)
- [ ] ATLAS_RAIL_TRAFFIC 테이블 저장

---

## 8. Atlas Server — Java UDP 수신 및 Logpresso 저장

> **중요**: 데이터는 반드시 Logpresso DB에 저장. CSV 파일 저장 금지.

### 8.1 OhtUdpListener — UDP 소켓 수신

Atlas 서버에서 STK MCP가 보내는 UDP 패킷을 수신하여 CNV 상태를 업데이트하고 Logpresso DB에 저장합니다.

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

### 8.2 메시지 파싱 처리

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
                case "1":  _processMcpOnline(tokens, msg);    break;  // MCP On-Line
                case "4":  _processDeviceStatus(tokens, msg); break;  // 기기 상태 (CNV 핵심)
            }
        }
    }
}
```

### 8.3 CnvEdge — Conveyor 구간 모델

```java
public class CnvEdge extends AbstractEdge {
    private long avgTransferIntervalT = 150;  // 평균 반송 시간 (ms)

    // 비용 = 평균 반송 시간
    public long getCost(String carrierId) { return avgTransferIntervalT; }

    // 비용 업데이트 (가중 이동 평균, 300~30000ms 범위)
    public void addCost(long newCost) {
        newCost = Math.max(300, Math.min(newCost, 30000));
        double w = PredictionPara.getInstance().getLastHisWeight();
        setAvgTransferIntervalT(
            (long)((avgTransferIntervalT * w) + ((1.0 - w) * newCost))
        );
    }

    public void setAvgTransferIntervalT(long val) {
        this.avgTransferIntervalT = Math.max(300, Math.min(val, 30000));
    }

    // 가용성: 양쪽 노드 모두 사용 가능해야 함
    public boolean isAvailable() {
        return getFromNode().isAvailable() && getToNode().isAvailable();
    }
}
```

### 8.4 Logpresso 저장 — Tuple API

```java
// 방법 1: 직접 삽입 (LogpressoAPI)
Tuple tuple = new Tuple();
tuple.put("FAB_ID",  fabId);
tuple.put("MCP_NM",  mcpName);
tuple.put("HID_ID",  hidId);
tuple.put("START",   startAddr);
tuple.put("ADDRESS", addressList);

LogpressoAPI.setInsertTuples("ATLAS_HID_INFO", List.of(tuple), 20);

// 방법 2: 유틸리티 래퍼 (일괄 삽입)
List<Tuple> data = new ArrayList<>();
// ... Tuple 추가 ...
Util.insertInLogpressoDatabase(data, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
```

### 8.5 TrafficBatch — 교통 데이터 배치 (1분 주기)

```java
public class TrafficBatch implements Job {
    private static ConcurrentMap<String, Long> lastHisCntMap = new ConcurrentHashMap<>();

    public void execute(JobExecutionContext ctx) {
        List<Tuple> logpressoData = new ArrayList<>();

        for (RailEdge edge : DataService.getDataSet().getRailEdgeMap().values()) {
            Tuple t = new Tuple();
            t.put("createTime",  System.currentTimeMillis());
            t.put("railEdgeId",  edge.getId());
            t.put("fabId",       fabId);
            t.put("velocity",    edge.getVelocity());
            t.put("maxVelocity", edge.getMaxVelocity());
            t.put("vhlCnt",      edge.getVhlIdMap().size());
            t.put("HID_ID",      edge.getHIDId());
            logpressoData.add(t);
        }

        // Logpresso DB에 일괄 저장
        Util.insertInLogpressoDatabase(logpressoData, "ATLAS_RAIL_TRAFFIC", "TrafficBatch");
    }
}
```

### 8.6 Logpresso 테이블 구조

#### ATLAS_HID_INFO

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| FAB_ID | String | Fab ID |
| MCP_NM | String | MCP 명칭 |
| HID_ID | String | HID 식별자 |
| START | String | 시작 주소 |
| ADDRESS | String | 주소 목록 (콤마 구분) |

#### ATLAS_RAIL_TRAFFIC

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| createTime | long | 생성 시각 |
| fabId | String | Fab ID |
| railEdgeId | String | Rail Edge ID |
| velocity | double | 현재 속력 (m/min) |
| maxVelocity | double | 최대 속력 |
| vhlCnt | int | Vehicle 수 |
| HID_ID | int | HID 구간 ID |

### 8.7 Logpresso 조회

```java
XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY);
List<Map<String, Object>> data = XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");
```

| Logpresso API | 용도 |
|---------------|------|
| `LogpressoAPI.setInsertTuples(table, tuples, timeout)` | Tuple 삽입 |
| `Util.insertInLogpressoDatabase(tuples, table, caller)` | 삽입 래퍼 |
| `XmlUtil.selectLogpressoQuery(queryName)` | 쿼리 실행 |
| `XmlUtil.loadLogpressoParm(path)` | 파라미터 로드 |
