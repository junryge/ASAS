# `{FAB}_ATLAS_HID_INOUT` 적재 관련 자바 소스 모음

`main/` 에서 `{FAB}_ATLAS_HID_INOUT` 테이블 적재에 직접/간접 관여하는
파일들을 한 폴더에 복사한 것입니다. (원본 그대로 — 수정 없음)

## 파일 목록 & 역할

| 파일 | 원본 경로 | 핵심 내용 (라인) |
|---|---|---|
| `OhtMsgWorkerRunnable.java` | `process/` | `_processHidInout()` (473-522), HID_INOUT 스위치 분기 (310) |
| `HidEdgeInOutQueueFlushBatch.java` | `batch/` | Quartz Job. 1분마다 drain → Logpresso insert (전체) |
| `HidEdgeInOutUpdateMasterBatch.java` | `batch/` | 마스터 테이블 갱신 (참고용, INOUT 본 테이블엔 미관여) |
| `DataSet.java` | `data/` | `edgeInOutCountMap` 필드 선언 (116), getter/setter (995-1024) |
| `Vhl.java` | `map/` | `hidId` 필드 초기값 -1 (452), `getHidId/setHidId` (529-535) |
| `RailEdge.java` | `map/edge/` | `getHIDId()`, `getVelocity()` 등 — 평균속도 계산 입력 |
| `RawHid.java` | `data/raw/` | `getVhlMax()`, `getVhlPreCaution()` — limit/precaution 출처 |
| `McpProperties.java` | `data/` | `getMcp75Config().getRawHidMap()` 진입점 |
| `FunctionItem.java` | `environment/type/` | `HID_INOUT` enum 정의 (422), 스위치 check 로직 |
| `LogpressoAPI.java` | `db/logpresso/` | `setInsertTuples(table, list, timeoutSecond)` (408), 내부 3회 재시도 (413-419) |
| `BizDataInitializer.java` | `service/` | `new OhtMsgWorkerRunnable(fabId, ...)` 워커 생성 (190) |

## 핵심 호출 경로 (요약)

```
BizDataInitializer.java:190
  → new OhtMsgWorkerRunnable(fabId, message, mcpName, ...)
     → OhtMsgWorkerRunnable.java:310    if (functionItem.getUseFunction(HID_INOUT))
        → OhtMsgWorkerRunnable.java:473  _processHidInout(hidId, vehicle, fi)
           - vehicle.getHidId()                     ← Vhl.java:529
           - McpProperties.getMcp75Config           ← McpProperties.java
             .getRawHidMap()                        ← Mcp75Config
             .getVhlMax() / getVhlPreCaution()      ← RawHid.java
           - RailEdge.getHIDId() / getVelocity()    ← RailEdge.java
           - DataSet.getEdgeInOutCountMap()         ← DataSet.java:995
             .merge(edgeKey, 1, Integer::sum)       ← OhtMsgWorker:519

Quartz trigger (1분)
  → HidEdgeInOutQueueFlushBatch.execute()
     - DataSet.getEdgeInOutCountMap().forEach(...)  ← copy
     - DataSet.setEdgeInOutCountMap(new ...)        ← swap
     - parts = key.split(":")                       (라인 58-70)
     - Tuple.put(...) × 14컬럼                       (라인 72-86)
     - LogpressoAPI.setInsertTuples(                ← LogpressoAPI.java:408
         fabId + "_ATLAS_HID_INOUT", tuples, 100)
        → setInsertTuplesInternal (Logpresso client.insert + flush)
        → TimeoutException 시 3회 재시도
```

## 관련 문서

상세 흐름/다이어그램: `../HID_INOUT_FLOW.md` 참조.
