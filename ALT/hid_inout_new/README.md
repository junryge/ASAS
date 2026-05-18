# {FABID}_ATLAS_HID_INOUT 신규 로직

기존 `com.skhynix.smartatlas.batch.HidEdgeInOutQueueFlushBatch` /
`HidEdgeInOutUpdateMasterBatch` 와 **별개 패키지**(`com.skhynix.smartatlas.hidinout`)
로 동작하는 리팩터링 버전입니다. 기존 파일은 변경하지 않으며 양쪽이 동일한
테이블에 적재 가능하므로, 운영 시 한쪽 Quartz Job 만 enable 해서 사용하세요.

## 디렉토리
```
ALT/hid_inout_new/src/com/skhynix/smartatlas/hidinout/
├── HidInoutTableSchema.java    # 테이블/컬럼 상수, 재시도 파라미터
├── HidInoutEventKey.java       # 누적 키 (타입 안전, ':' 충돌 없음)
├── HidInoutAggregate.java      # 키별 누적치 (transCnt + 스냅샷)
├── HidInoutCollector.java      # OHT 워커에서 호출되는 수집기 (싱글톤)
├── HidInoutFlushBatch.java     # Quartz Job — 분단위 {FAB}_ATLAS_HID_INOUT 적재
├── HidInoutMasterBatch.java    # Quartz Job — 일단위 마스터 두 개 갱신
└── HidInoutTibrvNotifier.java  # 임계치 초과 시 tibrv 송신 (기존 주석 분기 복원)
```

## 적재 테이블

| 테이블 | 주기 | 작성 클래스 |
|---|---|---|
| `{FAB}_ATLAS_HID_INOUT` | 1분 | `HidInoutFlushBatch` |
| `{FAB}_ATLAS_INFO_HID_INOUT_MAS` | 1일 | `HidInoutMasterBatch` |
| `{FAB}_ATLAS_HID_INFO_MAS` | 1일 | `HidInoutMasterBatch` |

컬럼은 기존 구현과 동일하므로 schema 변경 불요.

## 이벤트 흐름

```
OhtMsgWorkerRunnable
   │  (HID 변경 감지)
   ▼
HidInoutCollector.recordTransition(prevHid, currHid, fabId, mcp, vhl)
   │  - vhlCountLimit, vhlPrecaution     ← RawHid (layout.xml)
   │  - freeFlowSpeed                    ← 현재 HID RailEdge velocity 평균
   │  - hidValue                         ← DataSet.hidVehicleCountMap
   ▼
ConcurrentHashMap<HidInoutEventKey, HidInoutAggregate>
   │
   │  매 1분: Quartz trigger
   ▼
HidInoutFlushBatch.execute()
   ├─ drain() : atomic swap 으로 누적 map 통째 교체
   ├─ FAB 별로 Tuple 빌드 → LogpressoAPI.setInsertTuples(...)
   ├─ 실패 시 지수 백오프 (2s, 4s, 8s) 재시도
   ├─ 그래도 실패면 mergeBack() 으로 다음 사이클에 합산
   └─ HidInoutTibrvNotifier.notifyIfExceeded() (임계치 초과 행만)
```

```
HidInoutMasterBatch.execute()  (일 1회)
   ├─ FabProperties / McpProperties 순회 (HID_INOUT 스위치 ON 인 mcp 만)
   ├─ filterRailEdgesForFab(fabId)
   ├─ updateEdgeMaster:
   │    fromNodeId index 로 인접 엣지 O(N) 탐색 → HID 전환쌍 dedup
   │    → {FAB}_ATLAS_INFO_HID_INOUT_MAS
   └─ updateHidInfoMaster:
        HID 별 railLen/포트수/maxVelocity 평균 집계
        + RawHid 의 IN_CNT/OUT_CNT/VHL_MAX/ZCU_ID 반영
        → {FAB}_ATLAS_HID_INFO_MAS
```

## 호출부 연결 가이드 (기존 코드 미수정 — 별도 적용 시)

`OhtMsgWorkerRunnable._handleVehicleUpdate(...)` 의
`if (functionItem.getUseFunction(FunctionType.HID_INOUT)) { ... }`
블록에서 기존 `_processHidInout(...)` 호출을 다음으로 교체하면 신규 흐름이 활성화됨:

```java
HidInoutCollector.getInstance().recordTransition(
        vehicle.getHidId(),   // previousHidId
        hidId,                // currentHidId
        this.fabId,
        this.mcpName,
        vehicle);
vehicle.setHidId(hidId);      // 기존과 동일하게 최신 hid 반영
```

Quartz scheduler 등록 예시:
```java
JobDetail flushJob = JobBuilder.newJob(HidInoutFlushBatch.class)
        .withIdentity("hidInoutFlush").build();
Trigger flushTrigger = TriggerBuilder.newTrigger()
        .withSchedule(CronScheduleBuilder.cronSchedule("0 * * * * ?"))
        .build();

JobDetail masterJob = JobBuilder.newJob(HidInoutMasterBatch.class)
        .withIdentity("hidInoutMaster").build();
Trigger masterTrigger = TriggerBuilder.newTrigger()
        .withSchedule(CronScheduleBuilder.cronSchedule("0 30 2 * * ?"))
        .build();
```

## 기존 구현 대비 개선 요약

| 항목 | 기존 | 신규 |
|---|---|---|
| 누적 map drain | forEach + new map 할당 (race 존재) | `AtomicReference.getAndSet()` (원자적 swap) |
| 키 표현 | `String.split(":")` 11 토큰 | 타입화된 `HidInoutEventKey` |
| flush 실패 처리 | 손실 | 지수 백오프 재시도 + mergeBack |
| 빈 fabId | 전체 루프 `return` | 해당 행만 skip |
| 인접 엣지 탐색 | `O(N²)` 이중 루프 | `O(N)` fromNodeId index |
| 임계치 알림 | 주석 처리 | `HidInoutTibrvNotifier` 로 분리 |
| 마스터 IN/OUT/VHL_MAX/ZCU_ID | 0/빈값 고정 | RawHid 에서 실제 값 반영 |
| Quartz Job 예외 | 예외 흡수 | 개별 fab/mcp 만 실패 격리 |

## 운영 시 주의

1. `RawHid` 의 `getInCnt`, `getOutCnt`, `getZoneId`, `getZcuId` getter 가 빌드에
   따라 없을 수 있어 `HidInoutMasterBatch` 는 reflection 으로 안전 호출함.
   실제 코드베이스에서 getter 가 확정되면 직접 호출로 교체하는 것이 성능상 유리.
2. 기존 `HidEdgeInOutQueueFlushBatch` 와 동시에 실행하면 **이중 적재** 발생.
   둘 중 하나만 Quartz 에 등록할 것.
3. `HidInoutCollector` 는 싱글톤. 단일 JVM 인스턴스 가정. 다중 인스턴스
   환경이면 fab 단위 partition 또는 외부 큐(Kafka 등)로 확장 필요.
