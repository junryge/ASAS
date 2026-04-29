# AGV / CNV UDP 인터페이스 정의서

> **문서 목적**: `AGV_CNV_UDP_DATA.txt` 실측 데이터 기반 UDP 수신 패킷 포맷 정의
> **데이터 출처**: MCP → FabScope(SysView) UDP 수신 로그 (`[ICPKT]` 태그)
> **참조 코드**: `AGV/AGV_JAVA/AgvMsgWorkerRunnable.java`, `CNV/CNV_JAVA/CnvMsgWorkerRunnable.java`
> **개정 사유**: 실측 데이터에서 두 번째 토큰에 `AGV`/`CNV` 장비 타입 마커가 포함된 것이 확인되어, 기존 코드의 인덱스 정의(`VHL_STATE_REPORT`)와 오프셋이 1 차이 발생

---

## 1. 개요

### 1.1 통신 방식

| 항목 | 값 |
|------|---|
| 프로토콜 | UDP/IP |
| 인코딩 | ASCII (CSV) |
| 구분자 | `,` (쉼표) |
| 빈 값 | 연속된 쉼표(`,,`)로 표현 |
| 메시지 종단 | 패킷 단위 (개행 없음) |
| 로그 태그 | `[ICPKT] <AGV|CNV> 수신 패킷: <message>` |

### 1.2 공통 패킷 구조

모든 AGV/CNV 상태 보고 패킷은 **20개 필드**를 가지며, 다음 공통 헤더로 시작합니다.

```
<TXT_ID>,<DEVICE_TYPE>,<MCP_NM>,<NODE_ID>,<NAME>,<F5>,<F6>,<F7>, ... ,<F19>
```

| 인덱스 | 필드명 | 설명 | 예시 |
|--------|--------|------|------|
| 0 | TXT_ID | 메시지 ID (`2` = State Report) | `2` |
| 1 | DEVICE_TYPE | 장비 타입 (`AGV` / `CNV`) | `AGV` / `CNV` |
| 2 | MCP_NM | MCP/Area 명칭 | `6AAV3B01`, `P4ACV5R01`, `6ACV3B01`, `6ACV3M01` |

> ⚠️ **주의**: 기존 `AgvMsgWorkerRunnable.VHL_STATE_REPORT` 인덱스 정의는 `MCP_NM_IDX=1`로 되어있습니다. 실제 wire 포맷에서는 `DEVICE_TYPE` 마커가 인덱스 1에 추가되어 있어 모든 후속 인덱스가 **+1 시프트** 되어야 정확히 매핑됩니다.

---

## 2. AGV 상태 보고 (TXT_ID = 2)

### 2.1 필드 정의 (20 fields)

| Idx | 필드명 | 타입 | 설명 | 비고 |
|-----|--------|------|------|------|
| 0 | TXT_ID | String | 고정값 `2` | Vehicle State Report |
| 1 | DEVICE_TYPE | String | 고정값 `AGV` | |
| 2 | MCP_NM | String | MCP 명칭 | 예: `6AAV3B01` |
| 3 | VHL_ID | Integer | 차량 번호 | 예: `8131`, `32`, `22`, `55` |
| 4 | VHL_NAME | String | 차량 식별자 또는 위치 ID | `AGV32` 또는 주행 중일 때 `6ARB0111-2R291` 형식 |
| 5 | ONLINE | 0/1 | 통신 상태 (1=online) | 항상 `1` |
| 6 | FULL | 0/1 | 재하 여부 (1=carrier 재하) | |
| 7 | BUSY | 0/1 | 작업 진행 여부 | |
| 8 | ALARM_CODE | String | 알람 코드 | 정상 시 빈 값. 예: `19032`, `130`, `47`, `25`, `46`, `407`, `12029` |
| 9 | ALARM_NAME | String | 알람 메시지 | 정상 시 빈 값. 예: `Delay Move VC Warning`, `X Axis  BW LimitError`, `1F Load Place Axis Servo   Error`, `Bumper Detect Alarm`, `OBS Detected Warning`, `AGV ABNORMAL EXIT [Warning]` |
| 10 | CUR_ADDRESS | String | 현재 번지 | 예: `8012`, `10000`, `6ARB0111-2R291` |
| 11 | DISTANCE | Integer | 현재 번지로부터 거리 | 빈 값 가능 |
| 12 | NEXT_ADDRESS | String | 다음 번지 / 목적지 노드 | 예: `6ARB03ZZ-2R072`, `6B3BM615_1`, `16518` |
| 13 | CARRIER_ID | String | Carrier(반송품) ID | 예: `HIRA0894`, `HIRM1620` |
| 14 | DEST_CARRIER | String | 목적지 Carrier ID | 동일 ID 또는 별도 ID |
| 15 | EM_STATUS | Integer | E/M 상태 | 빈 값 또는 정수 |
| 16 | RUN_CYCLE | Integer | 실행 사이클 | `0`, `1`, `3` |
| 17 | BAY_NM | String | Bay 명칭 / 그룹 ID | 예: `6ARB0111`, `6ARB0312` |
| 18 | MODE | String | 운전 모드 | `M` (Manual) / `A` (Auto) |
| 19 | FORK_DIR | String | Fork 방향 | `LEFT` / `RIGHT` / `BOTH` |

### 2.2 AGV 패킷 패턴 분류

#### (1) 정상 주행 중 (Carrier 재하 + 이동)

```
2,AGV,6AAV3B01,8131,6ARB0111-2R291,1,1,1,,,6ARB0111-2R291,,6ARB03ZZ-2R072,HIRA0894,HIRA0894,,1,6ARB0111,M,BOTH
```

- 차량 8131이 Bay `6ARB0111`에서 `6ARB03ZZ-2R072` 방향으로 이동
- Carrier `HIRA0894` 재하, Manual 모드, BOTH fork

#### (2) 알람 발생 (Delay Move 등)

```
2,AGV,6AAV3B01,32,AGV32,1,1,1,19032,Delay Move VC Warning,8012,,,HIRM1620,HIRM1677,3,0,,,
```

- 차량 32, 알람코드 `19032` (Delay Move VC Warning)
- 현재 번지 `8012`, 사이클 `3`, Bay 정보 없음

#### (3) Idle / 대기 상태

```
2,AGV,6AAV3B01,55,AGV55,1,0,0,,,,,,,,1,,,,
```

- 차량 55 대기 중, 미재하, 알람 없음

#### (4) 통신 단절 / 위치 미상

```
2,AGV,6AAV3B01,22,AGV22,1,0,0,19022,Delay Move VC Warning,10000,,16518,,HIRA1868,1,0,,,
```

- Carrier ID 1 슬롯만 채워진 상태 (CARRIER_ID 빈 값, DEST_CARRIER만 존재)

### 2.3 관측된 알람 코드 목록

| 코드 | 메시지 |
|------|--------|
| 19xxx | `Delay Move VC Warning` (xxx는 차량 번호) |
| 130 | `X Axis  BW LimitError` |
| 47 | `1F ������ Time Out` (인코딩 깨짐 — 원문은 한글) |
| 25 | `2F Load Place Axis Servo   Error` |
| 19 | `1F Load Place Axis Servo   Error` |
| 46 | `Bumper Detect Alarm` |
| 407 | `OBS Detected Warning` |
| 12029 / 12041 | `AGV ABNORMAL EXIT [Warning]` |

---

## 3. CNV 상태 보고 (TXT_ID = 2)

### 3.1 필드 정의 (20 fields)

| Idx | 필드명 | 타입 | 설명 | 비고 |
|-----|--------|------|------|------|
| 0 | TXT_ID | String | 고정값 `2` | |
| 1 | DEVICE_TYPE | String | 고정값 `CNV` | |
| 2 | MCP_NM | String | MCP/Area 명칭 | `P4ACV5R01`, `6ACV3B01`, `6ACV3M01` |
| 3 | NODE_ID | Integer | 컨베이어 위치 번지 (zero-padded 5자리) | 예: `10427`, `08874`, `02016` |
| 4 | NODE_NAME | String | 위치 명 또는 특수 위치 식별자 | 보통 NODE_ID와 동일. 특수 위치는 `P4ACV5R01_ARRIVED02`, `6ACV3R01_COT2` 등 |
| 5 | ONLINE | 0/1 | 통신 상태 | 항상 `1` |
| 6 | LOADED | 0/1 | 재하 여부 (1=carrier 점유) | |
| 7 | RESERVED | 0/1 | 예약/센서 상태 | CNV는 대부분 `0` |
| 8 | ALARM_CODE | String | 알람 코드 | CNV는 대부분 빈 값 |
| 9 | ALARM_NAME | String | 알람 메시지 | CNV는 대부분 빈 값 |
| 10 | ADDRESS | String | 번지 (NODE_ID와 동일) | |
| 11 | DISTANCE | Integer | 거리 | 빈 값 |
| 12 | DEST_NODE | String | 다운스트림/목적지 노드 ID | 예: `6ACV3R01_BR-PKT`, `6ACV3B01_6B3SC011-CO1`, `6ACV3R01_COF1`, `P4ACV5R01_BR-LFT` |
| 13 | CARRIER_ID | String | Carrier ID | 예: `HITD9817`, `HITB3621`, `PUPD5768`, `TGPD0008` |
| 14 | UPSTREAM_CARRIER | String | 직전 위치 Carrier ID | 빈 값 가능 |
| 15 | EM_STATUS | Integer | E/M 상태 | 빈 값 |
| 16 | CONGEST_FLAG | 0/1 | Congestion Zone 소속 여부 | `1`이면 17번 필드에 zone명 |
| 17 | CONGEST_ZONE | String | Congestion / Sort Zone 이름 | 예: `6ACV3B01_CZ-SRT1`, `6ACV3B01_CZ-SRT3`, `6ACV3M01_CZ-ATM`, `6ACV3M01_CZ-MK-LIS`, `6ACV3M01_CZ-SCHEDULE` |
| 18 | (reserved) | - | - | 항상 빈 값 |
| 19 | (reserved) | - | - | 항상 빈 값 |

### 3.2 CNV 패킷 패턴 분류

#### (1) 빈 위치 (Carrier 없음)

```
2,CNV,P4ACV5R01,10427,10427,1,0,0,,,10427,,,,HITD9817,,0,,,
```

- 위치 `10427` 미점유, 다만 직전 carrier 정보(`HITD9817`)는 14번에 유지

#### (2) Carrier 재하 + 다운스트림 노드 명시

```
2,CNV,6ACV3B01,08234,08234,1,1,0,,,08234,,6ACV3B01_6B3SC011-CO1,HITB0076,,,0,6ACV3B01_CZ-SRT3,,
```

- 위치 `08234`에 carrier `HITB0076` 재하
- 다음 노드 `6ACV3B01_6B3SC011-CO1`로 진행 예정
- Sort Zone `6ACV3B01_CZ-SRT3` 소속

#### (3) Sort Zone 내 점유

```
2,CNV,6ACV3B01,08874,08874,1,1,0,,,08874,,,HITE9904,,,1,6ACV3B01_CZ-SRT1,,
```

- Congest flag = 1, Zone = `6ACV3B01_CZ-SRT1`

#### (4) 특수 위치 (도착 포인트)

```
2,CNV,P4ACV5R01,12221,P4ACV5R01_ARRIVED02,1,0,0,,,12221,,,,TGPD0841,,0,,,
```

- NODE_NAME이 `P4ACV5R01_ARRIVED02` 와 같이 의미적 식별자

#### (5) Branch / Lift 진입

```
2,CNV,P4ACV5R01,12237,12237,1,1,0,,,12237,,P4ACV5R01_BR-LFT,TGPD1414,TWPD4026,,0,,,
```

- 다음 노드가 `P4ACV5R01_BR-LFT` (Branch-Lift)

### 3.3 관측된 MCP / Zone 식별자

| MCP_NM | 설명 | 주요 노드 패턴 |
|--------|------|---------------|
| `P4ACV5R01` | Rail 라인 컨베이어 | `6ACV3R01_BR-PKT`, `6ACV3R01_COF1`, `6ACV3R01_COF3`, `P4ACV5R01_BR-LFT`, `P4ACV5R01_ARRIVED02`, `6ACV3R01_COT2` |
| `6ACV3B01` | B 라인 컨베이어 | `6ACV3B01_6B3SC011-CO1`, `6ACV3B01_6AST3B0[1-8]-CO[1-2]`, `6ACV3B01_6B3AS001-CO1`, `6ACV3B01_6ATM3B04-CO1` |
| `6ACV3M01` | M 라인 컨베이어 | `6ACV3M01_6AST3M[03-04]-CO[1-2]`, `6ACV3M01_6M3M0302-CO1`, `6ACV3M01_6ASU3M01-CO1`, `6ACV3M01_CZ-TR-EMPTY` |

| Congestion Zone | 의미 |
|-----------------|------|
| `*_CZ-SRT1` ~ `CZ-SRT5` | Sorter Zone |
| `*_CZ-BANK` | Bank Zone |
| `*_CZ-ATM` | ATM Zone |
| `*_CZ-MK-LIS` | Marker / List Zone |
| `*_CZ-SCHEDULE` | Schedule Zone |
| `*_CZ-TR-EMPTY` | Empty Tray Zone |

---

## 4. 기존 코드 인덱스와의 매핑 차이

`AgvMsgWorkerRunnable.VHL_STATE_REPORT` 정의 vs. 실측 wire 포맷 비교:

| 코드 정의 (구) | Wire 포맷 (실측) | 차이 |
|----------------|------------------|------|
| `[0]` TXT_ID | `[0]` TXT_ID | 동일 |
| `[1]` MCP_NM | `[1]` **DEVICE_TYPE** ← 신규 | **+1 shift 시작** |
| `[2]` VHL_ID | `[2]` MCP_NM | |
| `[3]` STATE | `[3]` VHL_ID/NODE_ID | |
| `[4]` FULL | `[4]` VHL_NAME/NODE_NAME | |
| `[5]` ERROR_CODE | `[5]` ONLINE | |
| `[6]` ONLINE | `[6]` FULL/LOADED | |
| `[7]` ADDRESS | `[7]` BUSY/RESERVED | |
| ... | ... | ... |
| `[18]` PRIORITY | `[18]` MODE/(reserved) | |
| `[19]` DET_STATUS | `[19]` FORK_DIR/(reserved) | |
| `[20-22]` (없음) | - | wire에 존재하지 않음 |

### 4.1 권장 조치

1. **Worker 인덱스 갱신**: `AgvMsgWorkerRunnable.VHL_STATE_REPORT` / `CnvMsgWorkerRunnable.CNV_STATE_REPORT` 의 모든 `*_IDX` 상수를 `+1` 시프트
2. **DEVICE_TYPE 검증 로직 추가**: `tokens[1]`이 `"AGV"` / `"CNV"`인지 확인 후 분기 처리
3. **필드 길이 검증**: `tokens.length == 20` 체크 (구 정의의 23이 아님)

```java
// 예시 — 갱신 후 인덱스
public static class VHL_STATE_REPORT {
    public static final int TXT_ID_IDX        = 0;
    public static final int DEVICE_TYPE_IDX   = 1;  // 신규
    public static final int MCP_NM_IDX        = 2;  // (기존 1 → 2)
    public static final int VHL_ID_IDX        = 3;  // (기존 2 → 3)
    public static final int VHL_NAME_IDX      = 4;
    public static final int ONLINE_IDX        = 5;
    public static final int FULL_IDX          = 6;
    public static final int BUSY_IDX          = 7;
    public static final int ALARM_CODE_IDX    = 8;
    public static final int ALARM_NAME_IDX    = 9;
    public static final int CUR_ADDRESS_IDX   = 10;
    public static final int DISTANCE_IDX      = 11;
    public static final int NEXT_ADDRESS_IDX  = 12;
    public static final int CARRIER_ID_IDX    = 13;
    public static final int DEST_CARRIER_IDX  = 14;
    public static final int EM_STATUS_IDX     = 15;
    public static final int RUN_CYCLE_IDX     = 16;
    public static final int BAY_NM_IDX        = 17;
    public static final int MODE_IDX          = 18;
    public static final int FORK_DIR_IDX      = 19;
}
```

---

## 5. 데이터 의미 변경 여부 결론

> **질문**: "처음과 조금 다른 것 같은데, 변화는 없는 거야?"

| 항목 | 변경 여부 | 비고 |
|------|----------|------|
| 메시지 ID (TXT_ID) | ❌ 변경 없음 | `2` 유지 |
| 필드 의미 (Carrier, Address, Alarm 등) | ❌ 변경 없음 | 모든 정보 동일 |
| 필드 개수 | ⚠️ 20개 (구 정의 23개) | 후미 3필드 미사용 |
| **필드 위치(인덱스)** | ✅ **+1 shift** | 인덱스 1에 `AGV/CNV` 마커 신규 추가 |

**요약**: 데이터 내용·구조 자체는 동일하며, **장비 타입 마커(`AGV`/`CNV`) 한 컬럼이 인덱스 1에 추가**된 것이 유일한 차이입니다. 이로 인해 기존 파서(인덱스 기반)는 모든 필드를 한 칸씩 어긋나게 읽게 되므로, 위 §4.1의 인덱스 갱신이 필요합니다.

---

## 부록 A. 샘플 패킷 인덱스별 분해표

### A.1 AGV 정상 주행 샘플

```
2,AGV,6AAV3B01,8131,6ARB0111-2R291,1,1,1,,,6ARB0111-2R291,,6ARB03ZZ-2R072,HIRA0894,HIRA0894,,1,6ARB0111,M,BOTH
```

| Idx | 값 | 필드 |
|-----|----|----|
| 0 | `2` | TXT_ID |
| 1 | `AGV` | DEVICE_TYPE |
| 2 | `6AAV3B01` | MCP_NM |
| 3 | `8131` | VHL_ID |
| 4 | `6ARB0111-2R291` | VHL_NAME (위치) |
| 5 | `1` | ONLINE |
| 6 | `1` | FULL |
| 7 | `1` | BUSY |
| 8 | (empty) | ALARM_CODE |
| 9 | (empty) | ALARM_NAME |
| 10 | `6ARB0111-2R291` | CUR_ADDRESS |
| 11 | (empty) | DISTANCE |
| 12 | `6ARB03ZZ-2R072` | NEXT_ADDRESS |
| 13 | `HIRA0894` | CARRIER_ID |
| 14 | `HIRA0894` | DEST_CARRIER |
| 15 | (empty) | EM_STATUS |
| 16 | `1` | RUN_CYCLE |
| 17 | `6ARB0111` | BAY_NM |
| 18 | `M` | MODE |
| 19 | `BOTH` | FORK_DIR |

### A.2 CNV Sort Zone 점유 샘플

```
2,CNV,6ACV3B01,08234,08234,1,1,0,,,08234,,6ACV3B01_6B3SC011-CO1,HITB0076,,,0,6ACV3B01_CZ-SRT3,,
```

| Idx | 값 | 필드 |
|-----|----|----|
| 0 | `2` | TXT_ID |
| 1 | `CNV` | DEVICE_TYPE |
| 2 | `6ACV3B01` | MCP_NM |
| 3 | `08234` | NODE_ID |
| 4 | `08234` | NODE_NAME |
| 5 | `1` | ONLINE |
| 6 | `1` | LOADED |
| 7 | `0` | RESERVED |
| 8 | (empty) | ALARM_CODE |
| 9 | (empty) | ALARM_NAME |
| 10 | `08234` | ADDRESS |
| 11 | (empty) | DISTANCE |
| 12 | `6ACV3B01_6B3SC011-CO1` | DEST_NODE |
| 13 | `HITB0076` | CARRIER_ID |
| 14 | (empty) | UPSTREAM_CARRIER |
| 15 | (empty) | EM_STATUS |
| 16 | `0` | CONGEST_FLAG |
| 17 | `6ACV3B01_CZ-SRT3` | CONGEST_ZONE |
| 18 | (empty) | reserved |
| 19 | (empty) | reserved |

---

## 부록 B. 파서 검증 체크리스트

- [ ] `tokens.length == 20` 확인
- [ ] `tokens[0] == "2"` (TXT_ID)
- [ ] `tokens[1] in {"AGV","CNV"}` (DEVICE_TYPE)
- [ ] `tokens[5] == "1"` 정상 통신 확인
- [ ] AGV: `tokens[3]`을 정수 `VHL_ID`로 파싱
- [ ] CNV: `tokens[3]`을 zero-padded 번지로 유지
- [ ] `tokens[8]` 비어있지 않으면 알람 처리 분기
- [ ] AGV: `tokens[19]` ∈ {`LEFT`,`RIGHT`,`BOTH`} 검증
- [ ] CNV: `tokens[16] == "1"`이면 `tokens[17]` Zone 등록

---

*문서 끝.*
