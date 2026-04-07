# smartATLAS Architecture 정의서 & ATLAS JOB Data 구조

> **원본**: M15 Ph2 생산정보시스템 구축_MCSLOG_Architecture정의서 (2022.07, AMHS운영팀)  
> **정리일**: 2026.04.02 이준력 
> **목적**: 원본 PPT(43슬라이드) + JOB Data 구조를 구조화하여 재정리

---

## PART 1: ATLAS JOB Data 구조

ATLAS Job은 반송 명령의 라이프사이클을 추적하는 핵심 데이터 객체이다.  
Job은 **생성(Created) → 시작(Started) → 완료(Completed) 또는 중지(Aborted)** 의 상태 흐름을 가지며, 하나 이상의 Command를 통해 OHT, STK, Conveyor 등 반송장비에 세부 명령을 수행한다.

### 1.1 기본 식별 정보

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| id | - | Y | string | Job 고유 ID |
| carrierId | - | Y | string | Carrier ID |
| requestor | - | Y | string | 반송명령 주체 |
| router | - | Y | string | 목적지 설정 방법 |
| stepId | - | Y | string | 공정 ID |
| batchId | - | Y | string | Batch 반송 ID |
| batchSeq | - | Y | int | Batch 반송 순번 |
| processType | - | N (Complete후) | - | ALL, FOUP, POD, CU, FOSB, CLEANFOUP, WTFOUP, POD_RSP150, POD_RSP200, POD_EUVPELLICLE, POD_EUVNONPELLICLE |

### 1.2 시간 관련 필드

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| createTime | firstCreateTime | Y | Date(yyyy-MM-dd HH:mm:ss) | 최초 생성 시점 |
| wakeupTime | createTime | Y | Date(yyyy-MM-dd HH:mm:ss) | 반송명령을 새로 받거나 목적지 변경, Wakeup이 된 시점 |
| startTime | - | Y | Date(yyyy-MM-dd HH:mm:ss) | 반송 시작 시점 (MCSMHS_TRANSPORT_JOB_STARTED_EVENT 발생시점) |
| endTime | - | Y | Date(yyyy-MM-dd HH:mm:ss) | 반송 완료 시점 |
| cancelTime | - | Y | Date(yyyy-MM-dd HH:mm:ss) | MCSMHS_TRANSPORT_JOB_ABORTED_EVENT 수신 시점 |
| alternatingTime | - | Y | Date(yyyy-MM-dd HH:mm:ss) | 생산장비로 가던 중 STB나 STK로 대체 반송 시작된 시점 |
| etaTime | - | Y | Date(yyyy-MM-dd HH:mm:ss) | 갱신된 도착 예상 시점 |
| newFromToMLEtaTime | initialEtaTime | Y | Date(yyyy-MM-dd HH:mm:ss) | ML을 통해 정합률을 개선한 도착 예상 시점 |
| newFromToEtaTime | initialOrgEtaTime | Y | yyyy-MM-dd HH:mm:ss | 새로 명령 받아 예측한 도착 예상 시점 |
| newFromToPredictStartTime | initialPredictTime | Y | - | 새로 명령받아 경로예측을 실시한 시점 |
| vhlErrTime | - | Y | yyyy-MM-dd HH:mm:ss | OHT이동중 VHL_STATE.ABNORMAL이 발생한 시점 |
| vhlJamTime | - | Y | yyyy-MM-dd HH:mm:ss | OHT이동중 VHL_STATE.JAM이 발생한 시점 |
| wakeupEndIntervalT | createEndIntervalT | N (Complete후) | long(ms) | job.getEndTime() - job.getWakeupTime() |
| createEndIntervalT | orgCreateEndIntervalT | N (Complete후) | long(ms) | job.getEndTime() - job.getCreateTime() |
| startEndIntervalT | - | N (Complete후) | long(ms) | job.getEndTime() - job.getStartTime() |

### 1.3 위치/경로 정보 (출발지)

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| fromNodeId | orgFromNodeId | Y | string | 최초 출발지 Node ID |
| newFromNodeId | fromNodeId | Y | string | 새로 명령받은 시점의 출발지 Node ID |
| currentEqpId | currentEqp | N (실시간) | string | Carrier의 현재 위치한 EqpId. UiCollect.queryJob()에서 실시간 조합 |
| currentLocId | currentLoc | N (실시간) | string | Carrier의 현재 위치. UiCollect.queryJob()에서 실시간 조합 |
| fromFabId | - | Y | string | 출발 FAB ID |
| fromEqpId | - | Y | string | 출발 장비 ID |
| fromEqpTyp | - | Y | string | 최초 출발지 장비 유형 |
| fromDetEqpTyp | - | Y (신규) | string | 최초 출발지 장비 상세 유형 |
| fromEqpGrpNm | - | Y (신규) | string | 최초 출발지 장비 그룹명 |
| fromFabMcpNm | - | N (Complete후, 신규) | string | 최초 출발지에서 목적지까지 경로상 첫번째 FAB+":"+McpName |
| fromRailArea | - | N (Complete후, 신규) | string | 최초 출발지에서 목적지까지 경로상 첫번째 OHT RAIL AREA ID |
| newFromEqpId | fromEqpId | Y | string | 새로 명령받은 시점의 출발지 장비ID |
| newfromContainerId | fromContainerId | Y | string | 새로 명령받은 시점의 출발지 Container ID |

### 1.4 위치/경로 정보 (목적지)

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| toNodeId | - | Y | string | 목적지 Node ID |
| tmpToNodeId | - | Y | string | STB Group, 혹은 목적지가 Group인 경우 임시목적지를 ATLAS가 임의로 설정. 경로 탐색 및 소요시간예측 등에 사용 |
| toFabId | - | Y | string | 목적지 FAB ID |
| toEqpId | - | Y | string | 목적지 장비 ID |
| toNodeGrpId | toGroupId | Y | string | 목적지 Node Group ID |
| toEqpTyp | - | Y | string | 목적지 장비 유형 |
| toDetEqpTyp | - | Y (신규) | string | 목적지 장비 상세 유형 |
| toEqpGrpNm | - | Y (신규) | string | 목적지 장비 그룹명 |
| toFabMcpNm | - | N (Complete후, 신규) | string | 목적지 경로상 FAB+McpName |
| toRailArea | - | N (Complete후, 신규) | string | 목적지 경로상 OHT RAIL AREA ID |

### 1.5 반송장비/Command 정보

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| currentCommandSeq | - | Y | int | 현재 Command 순번 |
| commandIdList | - | Y | string | command 목록 |
| transEqpTypeList | - | N (Complete후, 신규) | string | 반송에 사용된 반송장비 유형 목록 |
| transEqpIdList | - | N (Complete후, 신규) | string | 반송에 사용된 반송장비 ID 목록 |

### 1.6 경로 예측/탐색

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| predictionRouteIdList | - | Y | string | 반송명령 수신 시점의 예측 경로 |
| newPredictionRouteIdList | - | Y | - | 반송중 갱신된 예측 경로 |
| routeSelectionSet | - | Y | - | OHT에 설정된 Area간 반송에 대한 경유지 설정 정보 |
| routeSelectLongEdgeIdList | - | Y | - | routeSelectionSet을 기준으로 도출된 경유해야하는 LongEdgeId 목록 |
| routeSelectPassLongEdgeIdList | - | Y | - | routeSelectLongEdgeIdList중 실제 경유한 LongEdgeId 목록 |
| routeSelectSetObj | - | N (Complete후) | - | UI에서 routeSelectSet만 사용하면 제거 가능 |
| bjePath | - | N (Complete후) | - | OHT Rail(BranchJoinEdge) 이동 경로 |
| predictAreaVhlCntStr | - | Y | - | 경로 예측당시 예측 경로상 Area별 VHL 수량 |
| predictAreaVhlObsCntStr | - | Y | - | 경로 예측당시 예측 경로상 Area별 OBS_BZ_STOP 상태인 VHL 수량 |
| predictAreaVhlJamCntStr | - | Y | - | 경로 예측당시 예측 경로상 Area별 JAM상태인 VHL 수량 |
| predictAreaPredictQueueCntStr | - | Y | - | 경로 예측당시 예측 경로상 Area별 LongEdge의 pathPredictQueue 수량 평균 |

### 1.7 VHL/Assign 예측

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| predictVhlId | - | Y | - | 경로 예측 당시 예상한 Assign VHL ID (첫번째 OHT 명령에만 해당) |
| assignedVhlId | - | Y | - | 실제 Assign된 VHL ID (첫번째 OHT 명령에만 해당) |
| vhlEmptyPredictCost | - | N (Complete후) | - | 경로 예측당시 Empty VHL 호출 예상 소요시간 |
| vhlEmptyRealCost | - | N (Complete후) | - | 마지막 OHT 명령시점부터 VhlAcquireCompleted 까지 소요시간 |
| newFromToPredictedCost | initialPredictedCost | Y | long(ms) | 새로 명령 받아 예측한 결과에 대해 ML을 통해 정합률을 개선한 도착 예상 소요시간 |

### 1.8 통계/비용 정보

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| newFromToRanDistance | ranDistance | N (Complete후) | long(mm) | 새로명령받은 시점 이후 Acquire를 제외한 실제 이동 거리 합계 |
| newFromToPredictDistance | predictDistance | N (Complete후) | long(mm) | 예상 이동 경로상 거리 합계 |
| fromToRanDistance | orgFromToDistance | N (Complete후) | long(mm) | 전체 이동경로상 Acquire를 제외한 실제 이동 거리 합계 |
| ppCostSum | - | Y | long ms | 경로 예측 당시 LongEdge별 단순 getCost() 합계 |
| ppCntSum | - | Y | long | 경로 예측 당시 LongEdge별 단순 pathPredictQueueSize 합계 |
| futureTransCntSumMap | - | N (Complete후) | - | 예측 경로의 RouteItemDetType별 FutureTransCnt 합계 |
| futureAcqCnt | - | N (Complete후) | - | 예측 경로의 futureAcqCnt 합계 |
| futureDpstCnt | - | N (Complete후) | - | 예측 경로의 futureDpstCnt 합계 |
| costSumMap | - | N (Complete후) | - | 예측 경로의 예측시점 RouteItemDetType별 Cost 합계 |
| realCost | - | N (Complete후) | - | job.getEndTime() - job.getStartTime() |
| realEdgeCostSum | - | N (Complete후) | - | 이동경로상 실제 소요된 시간 합계 |
| passedAreaAndCostSumMap | - | N (Complete후) | - | FAB Area별 소요시간 합계(Acquire 제외) |
| predictedAreaAndCostSumMap | - | N (Complete후) | - | 예측경로상 Area별 예상 소요시간 합계 |
| predictedAreaJunctionTransCntSumMap | - | N (Complete후) | - | 예측경로상 Area별 합류지점의 FutureTransCnt 합계 |
| predictedFabMcpJunctionTransCntSumMap | - | N (Complete후) | - | 예측경로상 FAB:OHTLineNm별 합류지점의 FutureTransCnt합계 |

### 1.9 상태/이력 필드

| 필드명 | 기존 필드명 | Job class 선언 | Format | 설명 |
|--------|------------|---------------|--------|------|
| state | - | Y | string | 현재 상태 |
| oldState | - | Y | string | 이전 상태 |
| isAbnormalJob | - | N (Complete후) | true/false | command.getResultCode() > 1인 이력이 존재 |
| cycleExists | - | N (Complete후) | true/false | 반송 경로상 한번 지나간 경로를 다시 지나갔는지 여부 |
| fromNodeIdHistory | - | Y | - | 새로 명령 받은 시점순 FromNode이력 |
| toNodeIdHistory | - | Y | - | 새로 명령 받은 시점순 ToNode이력 |
| idHistory | - | Y | - | 반송중 JobID가 변경된 이력 |

---

## PART 2: smartATLAS Architecture 설계

### 2.1 시스템 구성도

smartATLAS(MCSLOG)는 MCS, OHT(CLWMCP), smartSTAR 등으로부터 데이터를 수집하여 반송 이력 추적, 경로 예측, 실시간 모니터링을 수행하는 시스템이다.

**데이터 소스:**

- **MCS → smartATLAS**: LOG(FTP/TIB), 반송 이벤트 Msg(TIB), 장비/재고상태(DB)
- **OHT → smartATLAS**: OHT 반송 상태(UDP), Layout Data(FTP)
- **smartSTAR → smartATLAS**: 반송 이력 정보, smartFX DB

**인프라 구성:**

- M15A MCS: APP1/APP2 이중화, DB1/DB2, CLWMCP1/CLWMCP2
- M15B MCS: APP1/APP2 이중화, DB1/DB2, CLWMCP1/CLWMCP2
- smartSTAR: APP1/APP2 이중화, DB1/DB2

---

### 2.2 객체 관계도

#### 2.2.1 장비(EQP) 유형

| 장비유형 | 설명 |
|---------|------|
| **EQP** | 생산장비. smartATLAS에서는 양방향 Load/Unload 포트만 가진 장비로 취급 |
| **FIO** | AMHS에 Carrier를 입/출고하는 용도. 자체 저장공간 없음. OHT를 통해 다른 AMHS로 반송하거나 출고 |
| **OHT** | VHL을 제어하는 장비 (OCS, CLWMCP). VHL을 이용하여 장비간 반송 수행 |
| **STK** | OHT/Manual로 Carrier 입출고 가능. Shelf로 저장. RM(RackMaster/Crane)으로 내부 반송. N2STK은 N2Purge 가능. LIFTER/ZIPTOWER/INTERLAYER는 층간반송 |
| **CONVEYOR** | 다수의 입고/출고 포트. 동시에 많은 수의 Carrier를 이동. 동간 반송에 주로 사용 |

#### 2.2.2 Node 유형

- **StkPortNode**: LP(LoadPort - OHT/사람 Access), BP(BufferPort - LP↔OP 이동구간), OP(OperationPort - Crane Access)
- **CnvPortNode**: physicalType 0=Zone, 1=QS/Lifter bed, 2=input, 3=output, 4=QS, 5=lifter
- **StkRmNode**: Stocker RM(Crane)
- **StkShelfNode**: Stocker Shelf 저장소
- **StbNode**: isN2(N2 Purge기능), isReader(RF Reader용 - Carrier 저장 불가)
- **EqpPortNode**: 생산장비 Port (가장 단순)
- **FioPortNode**: LP, OP, BP SubPort 존재 가능

#### 2.2.3 Edge 유형

| Edge 유형 | 설명 |
|-----------|------|
| **RAIL_EDGE** | OHT Rail 구간 |
| **TRANSFER_EDGE** | Station과 Port간 연결 (ACQUIRE / DEPOSIT) |
| **RM_EDGE** | Stocker 내부 RM 이동 |
| **CNV_ZONE_EDGE** | 컨베이어 Zone간 이동 |
| **LONG_EDGE** | BRANCH~JUNCTION 사이 EDGE의 집합 |
| **BRANCH_JOIN_EDGE** | RailBranch~Junction 사이의 RailEdge 집합 |

#### 2.2.4 Job & Command 관계

- **Job**은 적어도 1개 이상의 **Command**를 가짐
- Command별 Agent:
  - OHT → VHL
  - STK → RM
  - CNV → CnvTask
  - STB, EQP, FIO는 반송 수행 Agent가 **없음**
- Job의 목적지/JobId가 바뀌는 경우:
  - FAB간/동간 반송중 MCS가 바뀌는 경우
  - 목적지가 바뀌는 경우
  - 중복 명령을 수신하는 경우
- smartATLAS는 JobId 변경시 기존 Job에 대해 ID를 변경하고 History를 기록하여 **출발지~목적지간 완결된 이력** 생성

#### 2.2.5 통합 Map 구성

- **물리적 연결**: 실제 Rail/장비간 연결
- **논리적 연결**: TransferEdge를 통한 논리적 연결
- **Node 종류**: STATION, RAIL_JUNCTION, RAIL_BRANCH, STK_AI/AO/SHELF/RM/MI/MO, CNV_ZONE, STB/EQP

---

### 2.3 수집 서버 구조

#### 2.3.1 메시지 수신 및 처리 흐름

| Worker | 소스 | 처리 내용 |
|--------|------|-----------|
| **OhtMsgWorker** | UDP (OHT MCP) | VHL상태 추적, RailEdge/TransferEdge별 속도 Update, OHT기준 Carrier위치 |
| **TsMsgWorker** | TIB/RV (MCS) | Job 생성/완료처리 |
| **EiMsgWorker** | TIB/RV (MCS EI) | Command 생성/완료처리, Carrier위치, RmEdge Cost Update |
| **CnvMsgWorker** | Socket.IO (Conveyor) | CnvTask 추적, Cnv 상태 Update |
| **UiMsgWorker** | TIB/RV (MCS UI) | 포트/장비 상태 Update, Job wakeup 처리 |
| **RoutePrediction** | - | 반송경로 예측 |

**데이터 적재:**
- LogpressoInsertApi / Udp → Job, Command, Route, Log, VHL 등
- UiCollect → RealTime Monitoring, 상태Data 조회
- UiLogpresso → PlayBack, Job이력 조회 등 History성 Data

#### 2.3.2 Properties 파일 설명

**공통 설정:**
- `Env`: REAL|TEST|QA (TIB/rv의 Subject 생성에 영향)
- `FabIdList`: MCS기준 FAB ID 목록 (콤마 구분)
- `ProcessType`: DATAMAKER(수집서버) | QUERY(Logpresso Query 전용 서버)

**수집서버 전용:**
- `Atlas.Daemon`: Atlas 자체 tib/rv 통신 daemon 서버
- `Atlas.Gid`: cmessage 통신 그룹 ID
- `Atlas.ThreadPool.size`: Worker Thread 수 (일반적으로 CPU 코어 수)
- `Atlas.MonitoringMode`: Y|N (Y시 CPU부하 많은 함수 Disable)
- `Logpresso.Host` / `Host2`: Logpresso 1/2번 서버 주소
- `Logpresso.Port`: Java client용 Port
- `Logpresso.UdpHost` / `UdpHost2` / `UdpPort`: UDP 전송 설정
- `Logpresso.User` / `Password`: 접속계정 (암호화된 Password)

**FAB별 설정 (`[FABID].*`):**
- `.FacId`: Factory ID (M14A → M14)
- `.BridgeFrom` / `.BridgeTo`: Bridge 장비 목록
- `.InlineConnection`: STK RM을 통해 연결되는 장비 세트
- `.MapDir`: OHT Map 폴더 위치
- `.daemon`: MCS 통신 rvd daemon 주소
- `.ei.subject` / `.ei.gid`: EI프로세스 TIB/RV 수신 설정
- `.mcsmhs.subject` / `.gid`: MCS→MHS 메시지 수신
- `.mhsmcs.subject` / `.gid`: MHS→MCS 메시지 수신
- `.mcsui.subject` / `.gid`: MCS→UI 메시지 수신
- `.atlasmcs.gid` / `.req.subject` / `.dqlisten.subject` / `.daemon`: ATLAS↔MCS 통신
- `.atlasrtd.*`: ATLAS↔RTD 통신
- `.conveyor`: SEMI-TS 컨베이어 접속정보 세트
- `.McpNamePairs`: CLWMCP 장비명과 영역명 쌍
- `.oht.[영역명].port`: CLWMCP UDP Port
- `.oht.[영역명].ftp.*`: CLWMCP Layout FTP 설정 (ip/user/password/lanecut/mcp75/station/route/layout)

#### 2.3.3 Batch Job 목록

| Batch | 주기 | 내용 | 적재 테이블 |
|-------|------|------|------------|
| **AreaVhlCountBatch** | 6/10초 | Area별 VHL 수량 집계 → UDP → Logpresso | ATLAS_VHL_COUNT |
| **BranchTrafficBatch** | 4/10초 | BranchJoinEdge/Area 통계 → UDP + TIB/RV | ATLAS_BRANCH_TRAFFIC, ATLAS_AREA_TRAFFIC |
| **BridgeEqpMonitorBatch** | 매분 | FAB간/층간 장비 처리량/부하/소요시간 모니터링 | ATLAS_HIS_BRG_STK_IN/OUT/RM/DIR, ATLAS_HIS_BRG_CNV_OUT/DIR |
| **BridgeEqpNaviBatch** | 30초 | 장비기준 인접 Lifter/Conveyor 순서정보 → MCS 제공 | ATLAS_HIS_BRG_COST_PRED |
| **CurrentJobListBatch** | 10초 | 현재 수행중 Job 목록 → UI Publish | - |
| **DataSetRefreshBatch** | 매일 10시 | 전체 Layout/장비/Port 정보 갱신 | - |
| **ExportAllLayoutToLogpressoBatch** | 20분 | EDGE/LONGEDGE/BJE/VHL/STATION/EQP/AREA/BAY 정보 적재 | ATLAS_MAS_* |
| **HelloBatch** | 매분 | Old Job Cleaning(6h), Garbage Route Cleaning(30min) | - |
| **PredictionClean** | 5/10초 | LongEdge pathPredictQueue 정리 (30초 경과/미소속 Route 제거) | - |
| **LaneCutRefreshBatch** | 5/10분 | FTP lanecut.dat → RailEdge LaneCut 상태, CNV Layout 갱신 | - |
| **LifterRmStateBatch** | 매초 | 최근10분 RM Carrier/Command 수량 → BridgeEqpMonitorBatch 부하율 | - |
| **ObjOnMapDiffUpdateBatch** | 매초 | OHT/Command 통계 적재 | ATLAS_OHT_STATS_HIS |
| **ObjOnMapUpdateBatch** | 30초 | 모든 Port/Eqp 현재 상태 적재 | - |
| **ServerStatusBatch** | 2초 | CPU/Memory/Storage/Thread/Exception 서버상태 | - |
| **StbOccupyBatch** | 8/10초 | STB/Stocker MaxCapa/OccupancyCnt/isFull | - |
| **TrafficBatch** | 3/10초 | RailEdge별 통계 (velocity/density/passCount/vhlCount 등) | - |
| **VhlBatch** | 1분 | 전체 VHL 상태 → Logpresso 적재 | - |

**BranchTrafficBatch 상세 Data:**
- Length(mm), Speed(m/min, 지수평활법), ElapsedTime, passCnt(10초간 VHL 통과수량)
- pathPredictQueueSizeAvg, edgeIds, isAvailable(laneCut여부)
- jobCost(최근1분 ATLAS_ROUTE상 itemCost 평균)
- railTrafficInputCnt/OutputCnt/InOutCnt, vhlCnt
- Density: vhl길이×vhlCnt / (rail길이 – rail길이%vhl길이)
- passJobCnts[0~4]: 과거1~5분 지나간 vhl 수량
- pathPredictQCnts[0~4]: 향후1~5분 예상 Job 수량

**TrafficBatch 상세 Data:**
- maxVelocity(OHT 설정속도), velocity(지수평활법), absoluteVelocity(velocity/maxVelocity)
- passCount, inputCnt, outCnt, inOutCnt
- vhlDensityWeight, isAvailable
- predictQueueAllCnt, predictUnder1minCnt~predictOver5minCnt
- vhlObsBzStopCnt, vhlJamCnt, vhlAbnormalCnt, vhlE84Cnt
- vhlAcquireMovingCnt, vhlDepositMovingCnt, vhlAllWaitCnt, vhlStageWaitCnt, vhlIdleCnt

**ObjOnMapDiffUpdateBatch 상세 Data:**
- vhlCnt, vhlTransferringCnt, vhlStageCnt, vhlAbnormalCnt, vhlE84Cnt, vhlManualCnt, vhlHtStopCnt, vhlOfflineCnt, vhlJamCnt, vhlObsStopCnt
- trCnt, trQueuedCnt, trWaitingCnt, trTransferringCnt, trPausedCnt, trCancelingCnt, trAbortingCnt, trUpdatingCnt
- trDelay0_1Cnt, trDelay1_2Cnt, ..., trDelay5OverCnt

#### 2.3.4 수집 서버 초기화 프로세스

**시작점**: `LauncherListener.onStarted()`

1. **DataService Singleton 생성** → Properties load
2. **loadFabData(prop)**
   - `loadFab()`: FabProperties, MCP별 Properties
   - `Util.getAllOhtLayoutFileOverFtp(fp)`: MCP별 Layout parsing, Mcp75Config 생성
   - Conveyor 접속 및 Layout parsing
   - bridgeFrom/bridgeTo, InlineConnection Data parsing
   - `getFixedLongEdgeIds`: Logpresso에서 ATLAS_MAS_LONGEDGE/BJE 추출 → ID 유지용

3. **createNewDataSet**
   - leftRawPointsMap / rightRawPointsMap: MCP별 좌/우측 분기 Address 목록
   - **Left RailEdge 생성** (Multi-thread)
   - **Right RailEdge 생성** (Multi-thread)
   - mapFromNode2RailEdge / mapToNode2RailEdge 생성
   - RailEdge별 Hid 정보 설정
   - **RailNode 생성**: isBranch(분기), isRailBranch(Rail분기)
   - **StkPortNode 생성**: SELECT_STK_PORT_INF, Bridge장비 중복방지, SubPort(LP/BP/OP)
   - **CnvPortNode 생성**: FAB간 Conveyor 분할 표시
   - **StkRmNode 생성**: SELECT_STK_RM_INF, Bridge Owner FAB에서만
   - **StkShelfNode 생성**: SELECT_STK_SHELF_INF
   - **StbNode 생성**: SELECT_STB_PORT_INF (isN2, isReader)
   - **EqpPortNode 생성**: SELECT_EQP_PORT_INF
   - **FioPortNode 생성**: SELECT_FIO_PORT_INF
   - outPortNameNodeMap / inPortNameNodeMap 생성

4. **Station & TransferEdge building**
   - DUAL_ACCESS → TransferEdge 2개 (Acquire + Deposit)
   - ACQUIRE: `fabId:TRANS_EDGE_PREFIX:fromNodeId-toStationId`
   - DEPOSIT: `fabId:TRANS_EDGE_PREFIX:fromStationId-toNodeId`

5. **Eqps, StkRmEdge, Vhl building** (SELECT_EQP_INF)
   - FIO/OHT/STBGROUP/STK/CONVEYOR/EQP 각각 장비 생성

6. **Setting From/To Edges & Junction & Branch** → Node별 합류/분기 여부

7. **BranchJoinEdge building** → 직전 ID 재사용 (Map 재생성시 ID 변경 방지)

8. **LongEdge building**, Area/Bay 설정, PortAlias building

9. **inlineConnect** (STK→EQP 직접연결), **fabConnect** (FAB간 STK/CNV 연결)

10. **setNodeEdgeRef, setRailEdgeRef**: 직접참조 추가로 성능 향상

11. **updateEqpExtInfo**: smartSTAR 연계 기준정보 (detEqpTyp, eqpGrpNm)

12. **AtlasMcsCommDQ / AtlasRtdCommDQ**: Request Interface open

13. **clearCarrierList**: 내부 Map 초기화

14. **메시지 Listener 생성 및 start**:
    - MCS EI Listener, MCSMHS Listener, MHSMCS Listener, MCSUI Listener
    - reconcileCarriers (초기 Carrier/Job/Command 생성)
    - OHT UDP/TIB/RV Listener
    - Conveyor Socket.IO Listener
    - ExpiringMap (1초 이내 동일메시지 무시)
    - Message Dispatcher, HelloBatch, UiCollect enable

---

### 2.4 메시지 처리

#### 2.4.1 TS Msg 처리 (TsMsgWorkerRunnable)

**Job 생성 전 초기정보 수신:**
- `MHSMCS_MATERIAL_DEST_REP` / `MHSMCS_TRANSPORT_JOB_SCHEDULE_REQ`
- MES→MCS 반송명령. Carrier, Requestor, Router, StepId, 목적지 정보 포함
- 목적지는 MCS가 임의 변경/거부 가능 → 이 시점에 JOB 생성하지 않음, Carrier에만 정보 기록
- 현재 수행중 JOB 있으면 해당 JOB에 반영

**Job 생성/변경:**
- `MCSMHS_TRANSPORT_JOB_CREATED_EVENT` / `CHANGED_EVENT`
- JobId는 MCS를 따름. 없으면 MCS에 Query → 그래도 없으면 임시 ID 자체 생성
- 기존 미종료 동일 Carrier JOB이 남아있으면 해당 JOB 갱신
- **목적지 설정 규칙:**
  - 포트까지 명확: toNodeId 지정 + Port Reserved
  - 포트 미확정: tmpToNodeId 임시 지정
  - DESTINATION_ID가 생산장비명, DETAIL_DESTINATION_ID 공백: 인접 STB를 임시 목적지
  - STB Group Partition1: Round Robin으로 STB 선정
  - 포트 그룹명(4ABL_M10 등): `getCandidateToNodeByDetDestGroupId` 함수로 선정

**Job 시작:** `MCSMHS_TRANSPORT_JOB_STARTED_EVENT`

**Job 종료:** `MCSMHS_TRANSPORT_JOB_COMPLETED_EVENT`

**Job 중지:** `MCSMHS_TRANSPORT_JOB_ABORTED_EVENT`

**Carrier 제거 종료:** `MCSMHS_CARRIER_REMOVED_FROM_MANUAL_OUTPUT_PORT_EVENT` → 잔여 JOB 완료처리

#### 2.4.2 EI Msg 처리 - OHT (EiMsgWorkerRunnable)

**OHT Command 라이프사이클:**

| 이벤트 | cmdState | 처리내용 |
|--------|----------|---------|
| `RAIL-CARRIERTRANSFERREPLY` | QUEUED | ResultCode 0 or 4일 때만 Command 생성. toEqp가 STBGROUP이면 toNodeId 변경. 생산장비→STB/STK인 경우 alternatingTime 설정 |
| `RAIL-VEHICLEASSIGNED` | ACQMOVING | TransUnitId, AssignTime 설정. VHL에 CommandId Set. TransferEdge에 Assign VHL/CarrierId 설정 |
| `RAIL-VEHICLEUNASSIGNED` | QUEUED | VHL에서 cmdId 제거. TransferEdge Assign 해제 |
| `RAIL-VEHICLEARRIVED` | - | Source/Dest 구분하여 ArrivedTime 설정. Acquire/DepositTryCnt +1 |
| `RAIL-VEHICLEACQUIRESTARTED` | ACQUIRING | AcquireStartedTime. STK Port이면 avgRemovalIntervalT 갱신 |
| `RAIL-CARRIERINSTALLED` | - | Carrier 위치→VHL. InstalledTime 갱신 |
| `RAIL-VEHICLEACQUIRECOMPLETED` | - | AcquireCmpltTime. TransferEdge avgTransferCost/avgVhlCallCost 갱신. **경로 재탐색** |
| `RAIL-VEHICLEDEPARTED` | DESTMOVING | DepartedTime 설정 |
| `RAIL-VEHICLEDEPOSITSTARTED` | DEPOSITING | DepositStartTime 설정 |
| `RAIL-VEHICLEDEPOSITCOMPLETED` | - | Carrier 위치 변경. TransferEdge avgTransferCost Update. toNodeId≠현재위치시 **경로 재탐색** |
| `RAIL-CARRIERREMOVED` | - | VHL에서 carrierId 삭제 |
| `RAIL-TRANSFERCOMPLETED` | COMPLETED | Carrier 위치/InstalledTime/CmpltTime/ResultCode 업데이트 |
| `RAIL-TRANSFERUPDATECOMPLETED` | - | 목적지 변경시 업데이트 + **경로 재탐색** |
| `RAIL-TRANSFERINITIATED` | - | initTime 업데이트 |

#### 2.4.3 EI/CNV Msg 처리 - Conveyor

**Conveyor 이벤트 흐름:**

| 이벤트 | cmdState | carrierState | 처리내용 |
|--------|----------|-------------|---------|
| `EVENT_CARRIER_DETECTED` | - | - | Task 생성. fromNodeLocateTime 설정 |
| `EVENT_READ_RFID` | - | - | Carrier 위치→컨베이어 포트 |
| `INTERRAIL-CARRIERTRANSFERREPLY` | QUEUED | TRANSFERRING | Command 생성. Group 내 최소이동량 Port 임시 목적지 |
| `INTERRAIL-OPERATORINITIATEDACTION` | QUEUED | TRANSFERRING | Timeout등 CNV 자체 Command 생성 |
| `EVENT_TRANSFER_INITIATED` | - | - | transUnit=taskId. initTime 설정 |
| `EVENT_TRANSFER_TRANSFERRING` | DESTMOVING | - | AcquireCmpltTime, DepartedTime 설정 |
| `tcmTransferInfo` | - | - | Zone간 이동속도 생성. zoneIdTo 있으면 destNodeId 확정 |
| `EVENT_TRANSFER_COMPLETED` | COMPLETED | WAIT_OUT | Task CompleteTime. Command 완료 |
| `EVENT_CARRIER_REMOVED` | - | - | removedTime 기록. avgRemovalIntervalTime 갱신 |
| `UpdateZoneState` | - | - | Zone isAvailable 변경 |
| `INTERRAIL-CARRIERINSTALLED` | - | INSTALLED | Carrier 위치 변경 |
| `INTERRAIL-TRANSFERCOMPLETED` | - | - | ResultCode, DestNode 재설정 |

#### 2.4.4 EI Msg 처리 - STK (Stocker)

**STK 이벤트 흐름:**

| 이벤트 | cmdState | carrierState | 처리내용 |
|--------|----------|-------------|---------|
| `STORAGE-ZIPTOWERCARRIERLOCATIONCHANGED` | - | - | 동일STK 내부 Node간/Node내/다른장비간 이동 처리. Bridge→OwnerFAB만 |
| `STORAGE-CARRIERWAITIN` | - | WAIT_IN | 입고. 장비명/위치 업데이트 |
| `STORAGE-CARRIERWAITOUT` / `LIFTERCARRIERWAITOUT` / `ZIPTOWERCARRIERWAITOUT` | - | WAIT_OUT | 출고. OP이면 depositCmpltTime/destArrivedTime 업데이트. RM cmdId/carrierId 제거 |
| `STORAGE-CARRIERTRANSFER` | REQUESTED | TRANSFERRING | STK 반송명령 수신 (REPLY에는 출발지/목적지 없으므로 여기서 Command 생성) |
| `STORAGE-CARRIERTRANSFERREPLY` / `ZIPTOWERCARRIERTRANSFERREPLY` | QUEUED | - | ReplyCode 설정 |
| `STORAGE-TRANSFERCANCELCOMPLETED` | CANCELED | COMPLETED | QUEUED 명령 MCS 취소 |
| `STORAGE-TRANSFERINITIATED` / `CARRIERRESUMED` / `ZIPTOWERTRANSFERINITIATED` | ACQMOVING | - | RM에 cmdId 추가. AcqEdge에 currentMovingCarrierId |
| `STORAGE-CRANEACTIVE` / `ZIPTOWERCRANEACTIVE` | - | - | AcquireStartTime. AcquireTryCnt+1 |
| `STORAGE-CARRIERTRANSFERRING` / `ZIPTOWERCARRIERTRANSFERRING` | DEPOSITING | - | TransUnitId, AcquireCmpltTime, DepartedTime, DepositStartTime. AcqEdge→DpstEdge 전환 |
| `STORAGE-CRANEIDLE` / `ZIPTOWERCRANEIDLE` | - | - | destArrivedTime, DepositCmpltTime. RM에서 cmdId 제거. DpstEdge AvgCost 갱신 |
| `STORAGE-CARRIERSTOREDALT` | STOREDALT | ALTERNATE | 목적지 Port 이슈→Shelf 임시 저장. RM에서 carrier 제거 |
| `STORAGE-CARRIERSTORED` | - | COMPLETED | Shelf에 저장. RM에서 carrier 제거 |
| `STORAGE-TRANSFERCOMPLETED` / `LIFTERTRANSFERCOMPLETED` / `ZIPTOWERTRANSFERCOMPLETED` | COMPLETED | - | CmpltTime, ResultCode. transEqpId==MachineName 확인 |

#### 2.4.5 MCSUI Msg 처리 (UiMsgWorkerRunnable)

| 메시지 | 처리내용 |
|--------|---------|
| `UI-UNIT_PORT` / `UI-UNIT_SHELF` | Port/Shelf 상태 업데이트. INSERVICE && !banned, Reserved 상태 |
| `UI-MACHINE` | 장비 상태 업데이트. 조건: INSERVICE && ONLINEREMOTE && CONNECTED |
| `UI-MACHINE-STORAGE-CAPACITY` | Storage maxCapa, occupancyCnt, isFull 업데이트. 조건: INSERVICE && ONLINEREMOTE && CONNECTED |
| `COMMON-CARRIERTRANSPORT-AWAKE` / `COMMON-AWAKE` | ALT대기 JOB의 Awake → 경로 재탐색 |

---

### 2.5 경로 탐색 알고리즘

#### 2.5.1 변형 Dijkstra 알고리즘 (DijkstraFromToPath.java)

**변형 이유:** RailNode와 Station을 통한 포트 연결이 일반 Dijkstra로는 불가능한 케이스 발생

**핵심 변형 내용:**
- TRANSEDGE_ACQUIRE를 통해 RailNode에 진입시, 해당 RailNode를 **"미방문" 처리**
- 동일 RailEdge상에서 offset이 **큰 쪽으로만** 이동 가능하도록 제한
- 이후 다른 경로(3→4→5→2)를 통해 해당 RailNode를 다시 방문 가능
- 이를 통해 1→2→6 직접 경로가 논리적으로 불가능한 것을 반영

**경로 기록 (ComparableNode):**
- Source로부터 해당 Node까지의 Cost
- 방문여부
- 선행 노드 이력 (Predecessor)
- Other 노드 이력 (Acquire Edge를 통한 경우 RailNode 재방문 Backup)
- Other Cost (Source→RailNode까지 Cost Backup)

**경로 추출 방법:**
1. 목적지 Node의 경로기록을 가져옴
2. Other노드이력이 있으면 해당 경로기록 가져옴 (재진입 방지)
3. 선행 노드이력의 Edge → HeadNode → 경로기록 → 반복
4. 출발지까지 역순 추적 후 순서 뒤집기 → 완성된 경로

#### 2.5.2 Navigator.java (경로 탐색 호출)

**호출:** `UpdateNewRoutePredictionRunnable` / `NewRouteReqRunnable`  
→ `new Navigator().getPathFromTo(fromContainer, toNodeId, job)`

**탐색 흐름:**

1. Job에서 routeSelection으로 통과해야 할 LongEdge 목록 취득
2. fromContainer가 VHL이면 출발지를 RailNode로 설정
3. **M14A↔M14B 반송 판단:**
   - 이미 ZipTower/PodZipTower 이동중 → 해당 ZipTower RM 기준 경로 탐색
   - 다른 장비 이동중 → 현재 cmd destNode 기준 분할 탐색
   - M14A→M14B (이동중 아님) → **SSSP** → bridge 장비별 최단 RM 선정
   - M14B→M14A (이동중 아님) → **Reverse SSSP** → bridge 장비별 최단 RM 선정
4. 기타: currentCommandId 있으면 분할 탐색, 없으면 전체 경로 탐색
5. **SubPath 분할**: edge유형 변경시마다 subPath로 나눔
6. **RouteSelection 반영:**
   - RailEdge subPath의 시작/종료 BayId로 RouteSelection 해당 여부 판단
   - viaLongEdges (경유 LongEdge 목록) 도출
   - 기존 subPath와 Cost 비교: 1분 이상 증가시 기존 유지 (RouteSelection 폐기)
   - 이미 통과한 LongEdge 재통과시 기존 유지
7. 선행 SubPath 변경시 후속 SubPath 재계산

#### 2.5.3 RouteSelection

- `route_SCH_1.dat` 파일에 기록
- 예: B26→B21 이동시 B26에서 OUT01로 나가고, 4926번지 경유, B21의 IN02로 진입
- Bay 정의: `mcp75.cfg` 파일 내 정의

---

### 2.6 Dynamic Dijkstra & Edge Cost

#### 2.6.1 Dynamic Dijkstra (SSSP)

- OHT/MCP에서 Routing한 경로 또는 예측 경로를 각 Edge상에 기록
- 각 Edge의 **ExpiringMap** 또는 **Redis**(timeout 설정)에 적재:
  - Edge별 도착 예상시간, OHT ID, CarrierId
  - 반송 완료시 제거
- 새로운 Carrier 경로 예측시: 해당 Edge 도착시점의 **겹치는 경로 수량**에 따라 Cost 결정
- 모든 Node별 계산 완료 → 특정 노드뿐 아니라 여러 노드로의 경로도 빠르게 조회 가능
- **Return**: Source~Dest 구간 LongEdgeId 목록 + 소요시간/누적소요시간(ROUTE) + 전체 COST

#### 2.6.2 Edge Cost 계산 (LongEdge)

| 메서드 | 계산 방식 | 용도 |
|--------|----------|------|
| `getCost(carrierId)` | 지수평활법 기반 평균 속도 → 예상 소요시간 | UI상 RailEdge 현재 통과 속도 표시 |
| `getPPCost()` | getCost("") + pathPredictQueue.size() × 60ms | 도착지 기준 각 출발지별 소요시간 (N:1) |
| `getVhlCountCost()` | RailEdge 현재 VHL 수량 penalty | VHL Assign 예측 (근거리 반송) |
| `getLast1HourCost()` | 최근 1시간 이력 평균 통과 소요시간 | 기동 초기 FutureCost 대체 |

#### 2.6.3 Edge FutureCost 계산

**RailEdge:**
```
getFutureCost = cost 
  + (futureTransCnt + otherEdgeFutureTransCnt) × transWeight × junctionMultiple  [합류시]
  + futureTransCnt × transWeight  [합류 아닐시]
  + futureAcqCnt × acqTransWeight 
  + futureDpstCnt × dpstTransWeight
```

**TransferEdge_Acquire:**
- Assign VHL carrierId 일치시: vhlAssignCost = VHL 도착 예상 시간
- 불일치 & Carrier 현재위치=Edge 시작점: `DijkstraRailReverseShortestPath.getNearestVhlList()`로 최인접 VHL 선정
- vhlAssignCost > 0: cost + vhlAssignCost
- 그 외: avgVhlCallCost + futureTransCount × transWeight

**TransferEdge_Deposit:**
```
avgTransferCost + futureTransCount × transWeight
```

**ConveyorEdge:**
```
getCost(carrierId) + getFutureTransCount(carrierId, after) × transWeight
```

**StockerRmEdge:**
- 이미 init 상태 & 출발지 동일: 잔여 예상시간 (`avgTransferCost - 경과시간`)
- 그 외: `avgTransferCost + futureTransCnt × transWeight`

#### 2.6.4 FutureTransCount / FutureAcqCount / FutureDpstCount

**FutureTransCount:**
- TransferEdge: `after - transOverlapIntervalT` ~ `after + avgTransferCost + avgVhlCallCost` 구간의 PathPredictQueue 크기
- RailEdge: 동일 구간
- StkRmEdge: 현재 이동중이면 0. 아니면 `after - transOverlapIntervalT` ~ `after + avgRemovalIntervalT`
- CnvEdge: `after - transOverlapIntervalT` ~ `after + getCost()` 구간

**FutureAcqCount:** LongEdge toNode 진입 Edge중 TransferEdgeAcquire의 PathPredictQueue 수량

**FutureDpstCount:** ToNode 진출 Edge중 TransferEdgeDeposit의 PathPredictQueue 수량

---

### 2.7 예상 소요시간 보정 (ML/DL)

**배경:**
- 경로탐색의 목적이 정체구간 회피
- PathPredictQueue의 시간대별 분포가 **불균일** (1~3분 이내에 집중, 뒤로 갈수록 감소)
- 예측시간과 실제 소요시간 차이가 다소 큼

**보정 방법:**
- `Job.updatePredictionRoute(RouteResult rr)` 에서 호출
- `AtlasPredictEnhanceTibrvReq.getInstance().requestPredictEnhancedValue(...)` 

**입력 파라미터:**
- fromFabId, toFabId
- futureAcqCnt, futureDpstCnt
- ftcs_TRANS_ACQ, ftcs_TRANS_DPST, ftcs_STK, ftcs_CNV, ftcs_RAIL (FutureTransCount by type)
- cs_TRANS_ACQ, cs_TRANS_DPST, cs_STK, cs_CNV, cs_RAIL (Cost by type)
- predictDistance

---

### 2.8 OHT 위치/속도 추정

- 약 **5초 간격** 위치 보고
- 특정 위치가 아닌 몇 개 구간을 건너뛰어 보고하는 Case 존재 (Message 유실 등)

**추정 방법:**
1. A→B 위치보고시 중간 경로를 **Dijkstra 최단시간 경로**로 추정
2. 예: A→B 직접이 아닌 a→d→e→c 경로가 최단이면 해당 경로로 이동 추정
3. **가상 이동기록 생성**: 각 노드간 동일 속도로 이동 가정하여 도착시간 계산

---

### 2.9 Empty Vehicle Assign 예측

**AS-IS:**
- CarrierID에 따라 POD/FOUP VHL 구분 (4RP 여부)
- 가까운 VHL 선정:
  - Deposit moving중 VHL도 대상 (목적지가 동일 LongEdge 호출대상 Station 전에 속해야)
  - 동일 LongEdge IDLE VHL: 최소 정지거리 이전 VHL 대상

**개선 필요사항:**
- 출발지/목적지 Station의 carryType에 따른 VHL 구분:
  - 0: all, 1: 00001(FOUP), 2: 00010(POD), 5: 00101(FOUP), 9: 01001(FOUP), A: 01010(POD)
  - vhlType: 1=FOUP VHL, 2=POD VHL, 3=미사용, 4=청소 VHL
- 일정 거리내 적합 VHL이 없는 경우: 과거 이력 Base 예측치로 대체 검토

---

### 2.10 STB 재고정보 적재

**초기 적재:**
- MCS DB에서 현재 STB별 Carrier 목록 Query (반송명령 없는 Carrier만 대상)
- 조건: TYPE='STBPORT', TRANSPORTUNITACCESSIBLE='T', USERFREADER IS NULL, CONTROLSTATE='ONLINEREMOTE', STATE!='OUTOFSERVICE', TYPE='STB'

**실시간 추적 (UDP OHT Message):**
- **입고**: Carrier 위치가 VHL인 경우 해당 STB에서 제거
- **출고**: 목적지가 STB인 VHL이 Carrier를 갖고 있다가 Empty → 목적지로 위치 변경

**Abnormal Case 처리:**
- 출발지 오지정: Source Location Error 경보 (출발지 STB에 Carrier 없거나 다른 STB에 저장)
- 이미 점유된 STB 반송: Dest Location Occupied 경보

**기타:**
- 특정 시점의 재고 상태 조회 기능 (Data 훼손 대비)
- 재고정보 전송 전 조회 기능

---

### 2.11 향후 보완 필요 항목 (원본 미작성)

- 장애 Case별 대응 방안
- 패치/배포 유형별 절차서
- Logpresso 내 구현사항 설명
- UI 동작 구조 설명
- 개발환경 설정 방법
