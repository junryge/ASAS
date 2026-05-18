# 07. util / comm / db 패키지 상세 분석 (28 파일)

> 본 문서는 SmartAtlas 의 **공통 유틸리티**(`util/` 19), **외부 통신 단순 래퍼**(`comm/` 2), **DB 클라이언트**(`db/logpresso/` 1 + `db/mongodb/` 5 + `db/mybatis/` 1) 총 **28 파일**에 대한 라인 단위 정밀 분석이다. `DataService.java`(5,500 LOC), `Util.java`(1,304 LOC), `LayoutUtil.java`(309 LOC), `XmlUtil.java`(852 LOC) 는 별도의 큰 섹션으로 다룬다.

---

## §0. 패키지 개요

### 0.1 파일 인벤토리 (LOC + 한 줄 요약)

| # | 패키지 | 파일 | LOC | 한 줄 요약 |
|---|--------|------|-----|----------|
| 1 | util | AleadyClosedException.java | 17 | `ThreadPool` 가 종료된 후 호출시 던지는 예외 (오타: Already→Aleady) |
| 2 | util | AsyncUtil.java | 70 | 비동기 결과 캐시 (key→List<Map>) + 1h TTL 청소 스레드 |
| 3 | util | CryptoUtil.java | 84 | AES/GCM/NoPadding (BouncyCastle) 암복호화 — 32B 키 패딩 |
| 4 | util | **DataService.java** | **5,500** | **싱글톤 상태 저장소** — fab/MCP/맵/Tibrv senders/queues 등 시스템 중추 |
| 5 | util | FilePathUtil.java | 67 | `SMARTFX_REPOSITORY` 기준 경로 상수 + 팩토리별 dataaccessfx 경로 |
| 6 | util | JsonToStringBuilder.java | 173 | Eclipse 커스텀 toString 빌더 (JSON 포맷 출력) |
| 7 | util | JsonUtil.java | 74 | Gson TLS 싱글톤 + `Tuple`/`JsonElement` 상호변환 |
| 8 | util | LayoutUtil.java | 309 | **HID/VHL/RAILCUT/VIBRATION 알람 메시지 Map 빌더** |
| 9 | util | MemoryTailerUtil.java | 93 | 메모리 기반 tail 버퍼 (24h TTL) — UI 로그 스트리밍 보조 |
| 10 | util | ParseUtil.java | 94 | 문자열→int, "K:V\|K:V,..." 파싱, XML 문서 파싱 |
| 11 | util | PythonUtil.java | 150 | `python <fileName> <params...>` ProcessBuilder 실행 → JSON 결과 파싱 |
| 12 | util | QueryUtil.java | 149 | 날짜 포맷 변환(yyyyMMddHHmmssSSS) + MongoDB ObjectId + TS partition 명 |
| 13 | util | ReflectionUtil.java | 7 | `getCurrentMethodName()` 단일 메서드 |
| 14 | util | RemoteCommandUtil.java | 37 | `plink -ssh` 외부 프로세스로 원격 명령 실행 |
| 15 | util | SecurityUtil.java | 111 | AccessLevel enum + `assertNull`/`assertAccessLevel` + 안전 정규식 |
| 16 | util | SmsUtil.java | 45 | `INSERT_STA_SMS_HIS` MyBatis 호출로 SMS 발송/카운트 |
| 17 | util | ThreadPool.java | 97 | FixedThreadPool 래퍼 + pause/resume + 전역 풀 레지스트리 |
| 18 | util | **Util.java** | **1,304** | **거대 잡탕 유틸** — FTP 다운로드, 암복호화, switch 반영, CSV 작성 |
| 19 | util | **XmlUtil.java** | **852** | **XML 메시지/쿼리 로더 + Tibrv layout 메시지 빌더** |
| 20 | comm | OracleAPI.java | 36 | `QueryExecutorFactory.build()` 1줄 try-with-resources 래퍼 |
| 21 | comm | TibrvAPI.java | 74 | Tibrv `send()`/`listen()` 정적 함수 (transport/queue 즉시 정리) |
| 22 | db/logpresso | LogpressoAPI.java | 453 | **Logpresso 클라이언트 풀 + 2 노드 fallback + Canceller 타이머** |
| 23 | db/mongodb | MongodbAPI.java | 114 | MongoClient 풀 (fab→DB) + find/aggregate/insertMany |
| 24 | db/mongodb | MongodbAggregateLinq.java | 99 | `AggregateIterable` 빌더 체인 (allowDiskUse/maxTime/explain…) |
| 25 | db/mongodb | MongodbFindLinq.java | 167 | `FindIterable` 빌더 체인 (filter/limit/sort/projection…) |
| 26 | db/mongodb | MongodbLinq.java | 96 | LINQ 추상 베이스 + `toList(limit)` / `toListTask()` (FutureTask) |
| 27 | db/mongodb | MongodbQueryPool.java | 94 | `repository/dataaccessfx/mongodb.xml` 의 `If/IfNotBlank` 태그 평가 |
| 28 | db/mybatis | MybatisQueryHandler.java | 72 | `mcs_*.xml` MyBatis 매퍼 파일 목록·내용 조회/갱신 |

### 0.2 패키지 간 의존 그래프

```mermaid
graph TD
    subgraph util
        DS[DataService<br/>5500L<br/>SINGLETON]
        U[Util.java<br/>FTP+암호+switch]
        XU[XmlUtil<br/>alarmMessage/<br/>logpressoQuery]
        LU[LayoutUtil<br/>알람 Map 빌더]
        FPU[FilePathUtil<br/>경로 상수]
        TP[ThreadPool]
        ACE[AleadyClosed<br/>Exception]
        AU[AsyncUtil]
        CU[CryptoUtil]
        JU[JsonUtil]
        JTSB[JsonToString<br/>Builder]
        MTU[MemoryTailer<br/>Util]
        PU[ParseUtil]
        PY[PythonUtil]
        QU[QueryUtil]
        RU[ReflectionUtil]
        RCU[RemoteCommand<br/>Util]
        SU[SecurityUtil]
        SMS[SmsUtil]
    end
    subgraph comm
        OA[OracleAPI]
        TA[TibrvAPI]
    end
    subgraph db
        LP[LogpressoAPI<br/>2-node fallback]
        MA[MongodbAPI]
        MF[MongodbFindLinq]
        MAG[MongodbAggregate<br/>Linq]
        ML[MongodbLinq]
        MQ[MongodbQueryPool]
        MY[MybatisQuery<br/>Handler]
    end

    DS --> XU
    DS --> U
    DS --> TP
    DS --> LP
    DS --> OA
    DS --> JU
    DS --> FPU
    XU --> LP
    XU --> FPU
    U --> LP
    U --> CU
    U --> FPU
    LU --> XU
    SMS --> |QueryExecutorFactory| OA
    LP --> CU
    MA --> CU
    MA --> MF
    MA --> MAG
    MF --> ML
    MAG --> ML
    TP --> ACE
    MY --> XU
    PY --> FPU
```

### 0.3 외부 라이브러리 의존성 매트릭스

| 외부 라이브러리 | 사용 파일 |
|----------------|----------|
| BouncyCastle (`org.bouncycastle`) | CryptoUtil L14, Util L40 |
| Gson (`com.google.gson`) | JsonUtil, DataService, PythonUtil |
| Jackson (`com.fasterxml.jackson`) | PythonUtil L14 |
| Apache Commons Net FTP | Util L36-39 |
| Apache Commons Lang3 | SecurityUtil L5, Util L35, MongodbQueryPool L6 |
| JDOM2 | MongodbQueryPool L7-8 |
| W3C DOM / javax.xml | XmlUtil, ParseUtil, MybatisQueryHandler |
| dom4j | Util L41-42 (`Node`/`Element`) |
| Logpresso client (`com.logpresso`) | LogpressoAPI, JsonUtil, XmlUtil, Util |
| MongoDB driver | MongodbAPI/Linq 군 |
| TIBCO Rendezvous (`com.tibco.tibrv`) | TibrvAPI |
| SmartFX (`com.skhynix.smartfx.dataaccessfx`) | OracleAPI, SmsUtil, MybatisQueryHandler |
| BizExecutionContext | SecurityUtil |

---

## §1. util/ 19 파일

### 1.1 AleadyClosedException.java (17 LOC)

- **한 줄**: `WorkQueue.enqueue/dequeue` 호출시 이미 닫힌 상태라면 발생하는 체크드 예외. (클래스명 오타: Already→Aleady)
- **필드**: `serialVersionUID = -2099140208827396780L` (L9)
- **public 메서드**:
  - L11 `AleadyClosedException(String msg)` — 메시지 전파
  - L15 `AleadyClosedException()` — 기본 생성자
- **사용처**: `ThreadPool.execute()`, `ThreadPool.close()` (ThreadPool.java L30, L48)

### 1.2 AsyncUtil.java (70 LOC)

- **한 줄**: 비동기 결과(`List<Map<String,Object>>`) 를 키별 캐시하고 1시간 무접근시 만료 청소하는 메모리 캐시.
- **싱글톤 패턴**: ❌ (static 전역) — `private static Thread _CheckerThread`(L9)
- **필드** (모두 `private static`):
  - L10 `_DefaultLifetime = 60*60*1000L` (1h)
  - L11 `_AsyncResult : Map<String, List<Map<String,Object>>>` — ConcurrentHashMap
  - L12 `_ResultLifetime : Map<String, Long>` — 마지막 접근 시각
- **public 메서드**:
  - L41 `get(String asyncKey)` — 조회 + lifetime 연장; 없으면 빈 List
  - L52 `put(String asyncKey, List<Map<String,Object>> result)` — 첫 호출시 `startThread()`로 청소기 기동
  - L65 `remove(String asyncKey)` — 캐시 제거
- **private**:
  - L14 `startThread()` — 60s 주기로 `removeExpired()` 호출하는 무한 루프 스레드 시작
  - L26 `removeExpired()` — `currentTimeMillis - _ResultLifetime[k] > 1h` 인 키 제거
  - L37 `extendLifetime(String asyncKey)` — 현재 시각으로 갱신
- **사용처**: 패키지 전반의 비동기 데이터 조회 결과 임시 저장 (UI/Batch가 `get()` 으로 폴링)

### 1.3 CryptoUtil.java (84 LOC)

- **한 줄**: 32바이트 키 패딩 → `AES/GCM/NoPadding` (BouncyCastle) 양방향 Base64 인코딩.
- **static block** L17-19: `Security.addProvider(new BouncyCastleProvider())`
- **public 메서드**:
  - L21 `static String encrypt(String target, String key)` — Cipher.ENCRYPT_MODE → Base64
  - L53 `static String decrypt(String target, String key)` — Base64 디코드 → Cipher.DECRYPT_MODE
- **키 패딩 로직** (L24-27, L56-59):
  ```java
  while(newKey.getBytes().length < 32) { newKey += key; }
  byte[] k = newKey.substring(0,32).getBytes();
  ```
  IV 도 동일 32바이트 (취약점: 동일 키-IV 조합).
- **사용처**: LogpressoAPI(L89,96,101...), MongodbAPI L45 (비밀번호 복호화). `Util.decrypt()` 가 동일 로직을 더 견고하게 재구현 (`_transformer()` L930).

### 1.4 DataService.java (5,500 LOC) — **§1.A 별도 섹션 참조**

### 1.5 FilePathUtil.java (67 LOC)

- **한 줄**: `SMARTFX_REPOSITORY` 환경변수 기반 모든 외부 파일 경로 상수 모음.
- **private 생성자** L37: `private FilePathUtil() {}` — 인스턴스화 차단
- **public static 상수 (모두 String, L10-30)**:
  - `REPOSITORY_PATH` = `System.getProperty("SMARTFX_REPOSITORY")` (L10)
  - `PYTHON_FILE_PATH` = REPO + `/python` (L12)
  - `RECORD_FILE_PATH` = REPO + `/document` (L13)
  - `LOGPRESSO_CUSTOM_QUERY` / `_QUERY2` (L16-17)
  - `ALARM_MESSAGE_PATH` = `/alarm_message.xml` (L18)
  - `VARIABLE_ENV_PATH` = `/variable.xml` (L19)
  - `OHT_ALARM_MESSAGE_PATH` = `/oht_alarm_message.xml` (L20)
  - `SETTINGS_PROPERTIES_PATH` / `FAB_SET_PROPERTIES_PATH` / `RESET_PROPERTIES_PATH` (L23-25)
  - `COMMON_ALARM_FORMAT` = `cmessage/cfg/dataformat/CMESSAGE_CMN_FORMAT.xml` (L29)
  - `LAYOUT_DATA_FORMAT` = `cmessage/cfg/dataformat/CMESSAGE_LAYOUT_DATA.xml` (L30)
  - `MAP_ROOT_DIRECTORY = "map"` (private, L34)
- **public 메서드**:
  - L39 `factoryPath(String connectionId)` — `ENUM_DBCONNECTION_ID.fromString().fileName()` 으로 dataaccessfx 경로 조립; `"NODATA"` 면 null
  - L56 `getMapRootDirectoryPath()` — `"map"` 반환
  - L60 `getOhtAlarmCodeCsvFilePath(String fileName)` — REPO\fileName (역슬래시!)
  - L64 `getUdpMessagePath()` — REPO/udp_message
- **사용처**: XmlUtil(`LOGPRESSO_CUSTOM_QUERY`, `ALARM_MESSAGE_PATH`, …), DataService(`RECORD_FILE_PATH`, `MAP_ROOT_DIRECTORY`), PythonUtil(`REPOSITORY_PATH`), Util(전체 FTP 다운로드 경로).

### 1.6 JsonToStringBuilder.java (173 LOC)

- **한 줄**: Eclipse "Generate toString()" 커스텀 빌더 — 결과를 JSON 문자열로 출력. (외부 오픈소스, MIT)
- **필드**: `private StringBuilder aJson = new StringBuilder()` (L40, 256 capacity)
- **public 메서드**:
  - L42 `JsonToStringBuilder(Object o)` — 생성자 (인자 미사용)
  - L56 `append(String fieldName, Object fieldValue)` — `"key": <serialized>` 추가 후 self
  - L67 `build()` — `toString()` 동의어
  - L75 `@Override toString()` — `"{" + aJson + "}"`
- **내부 클래스**:
  - L79 `ValueSerializer` — null/Number/CharSequence/Enum/Collection/Object[]/Map 분기 직렬화 (L87)
  - L106 `LinearCollection` — `[item,item,…]` 출력 (L120)
  - L140 `MappedCollection` — `{"k":v,…}` 출력 (L154)
- **사용처**: Eclipse IDE 의 toString() 생성 기능 → 도메인 객체 toString 구현. 런타임 핫패스 사용 안 함.

### 1.7 JsonUtil.java (74 LOC)

- **한 줄**: Gson 인스턴스를 TLS(ThreadLocal Storage) 로 관리하는 싱글톤 + Logpresso `Tuple` 변환.
- **싱글톤 패턴 (L48-50)**: Holder idiom
  ```java
  private static class Singleton { private static final JsonUtil instance = new JsonUtil(); }
  ```
- **필드**:
  - L16 `static final Gson gson = new Gson()` (static MAPMAP 변환용)
  - L17 `static final Type MAPMAP = Map<String,Map<String,String>>`
  - L28 `final ThreadLocal<Gson> tlsGson` — 스레드별 Gson
  - L30 `static final Type TUPLEMAP = Map<String,Object>`
- **public 메서드**:
  - L19 `static Map<String,Map<String,String>> getMapMapFromJson(String json)`
  - L23 `static String getJsonFromMapMap(Map<String,Map<String,String>> mapmap)`
  - L38 `Gson gson()` — TLS 에서 꺼내거나 새로 생성 (Gson 스레드 안전성 회피)
  - L52 `static JsonUtil getInstance()`
  - L56 `static String convertJSON(Object object)` — 싱글톤 Gson 사용
  - L60 `static JsonElement toJsonTree(Object object)`
  - L64 `static Tuple getTupleByJsonElement(JsonElement je)` — JsonElement → Map → Logpresso `Tuple`
- **사용처**: DataService L234 (`_sendTibrvMessage()` JSON 포맷); 어디서나 객체→JSON 변환.

### 1.8 LayoutUtil.java (309 LOC) — **HID/VHL/RAILCUT/VIBRATION 알람 Map 빌더**

- **한 줄**: 5종 RecordItem(`HidOffRecordItem`, `VhlOffRecordItem`, `RailCutRecordItem`, `RailVibrationRecordItem`) 객체를 받아 Tibrv 송신용 표준 `Map<String,String>` 으로 변환.
- **public static 메서드**:
  - L18 `<T> Map<String,String> buildLayoutMessageDataMap(T data)` — 제네릭 진입점, `instanceof` 검사로 className 결정 후 분기
  - L158 `Map<String,String> buildLayoutMessageDataMap(String type, String fabId, String deviceName, String state, Object addressList, Object portList, String alarmMessageContents, String alarmCode, String facId, String alarmDescription, String alarmComment, boolean isOccurredAlarm)` — 실제 빌드 로직 (12개 인자!)

#### 1.8.1 첫 진입점 `buildLayoutMessageDataMap(T)` 분기

| className (L23-31) | 발생 시점 | 핵심 필드 추출 (L46-138) |
|---|---|---|
| `HidOffRecordItem` | HID 신호 OFF | `code = "HID%03d" % hidId`, alarmDescription= `OHT_LAYOUT_HID_OFF_DESC` (XmlUtil) |
| `VhlOffRecordItem` | 차량 정지 | `machineId`, stoppedFrom/To Address, alarmTitle=`OHT_LAYOUT_VHL_OFF_TITLE` |
| `RailCutRecordItem` | 레일 절단 | railCutFrom/To Address, alarmDescription=`OHT_LAYOUT_RAIL_CUT_DESC` |
| `RailVibrationRecordItem` | 레일 진동 | term1/term2 G-force, upDownRate, addressList=`OHT_LAYOUT_RAIL_VIBRATION_TOOLTIP` (7개 파라미터 포맷) |

- 모든 분기에서 `state.equals(OHT_TIB_STATE.ABNORMAL)` 검사 (L61, 81, 100, 118) 후에만 알람 텍스트 채움 → NORMAL 상태는 메시지만 송신.
- 진입 직후 L19: `XmlUtil.loadAlarmMessage()` 호출하여 `oht_alarm_message.xml` 적재.

#### 1.8.2 실제 빌더 `buildLayoutMessageDataMap(...12 args)` L158-291

1. **검증 (L174-218)**: type/fabId/deviceName/state/facId 비면 빈 HashMap 반환 + error log
2. **메시지 키 채움 (L228-274)**:
   - `DEVICE_TYP`, `FAB_ID`, `EVENT_DT` (현재 시각 `yyyy-MM-dd HH:mm:ss` L233-237), `DEVICE_NM`, `FALR_STAT_TYP`
   - `ADDRESS_LIST` / `PORT_LIST`: `String`/`List<String>`/`Set<String>` 3분기 (`String.join(",", …)`) — 다른 타입은 `IllegalArgumentException` (L249, 263)
   - `ALARM_DESC`, `ALARM_CMT`, `ALARM_MSG_CTN`, `ALARM_CD`, `FAC_ID`
3. **알람 레벨 자동 부여 (L275-286)**:
   - `HID_OFF` → 1
   - `VHL_OFF`, `RAIL_CUT` → 2
   - `RAIL_VIBRATION` → 3
4. `ALARM_YN = isOccurredAlarm ? "Y" : "N"` (L288)

#### 1.8.3 내부 정적 클래스 `LAYOUT_MEMBER` (L293-308)

13개 String 상수 — Tibrv 페이로드의 XML/CMESSAGE 필드명 정의:
`DEVICE_TYP`, `FAB_ID`, `EVENT_DT`, `DEVICE_NM`, `FALR_STAT_TYP`, `FALR_RAISE_ADDR_LVAL`, `FALR_AFFECT_PORT_LVAL`, `ALARM_MSG_CTN`, `ALARM_CMT`, `ALARM_CD`, `FAC_ID`, `ALARM_DESC`, `ALARM_LEVEL_VAL`, `ALARM_YN`

- **외부 의존**:
  - `XmlUtil.getMessage(code, params…)` — alarm_message.xml 의 MessageFormat 템플릿 치환
  - `OhtMsgWorkerRunnable.OHT_TIB_STATE.ABNORMAL` (state 비교)
  - `TibrvService.SEND_SUB_SUBJECT.*` (type → 알람 레벨 매핑)
- **사용처**: OhtMsgWorkerRunnable 가 HID/VHL/RAILCUT/VIBRATION 감지시 호출 → `DataService.addTibrvMessageQueue()` 로 전달.

### 1.9 MemoryTailerUtil.java (93 LOC)

- **한 줄**: 키별 텍스트 버퍼를 메모리에 누적하고 24h TTL 청소 — UI 의 실시간 로그 tail 기능 지원.
- **필드 (모두 `private static`)**:
  - L7 `_Expired : HashMap<String, Date>` — 마지막 활동 시각
  - L8 `_Content : HashMap<String, String>` — 누적 텍스트
  - L9 `_ExpiredTailersRemover : Thread` — 청소 스레드
- **public 메서드**:
  - L11 `startListener(String uniqueName)` — 키 등록 + 청소 스레드 lazy 시작, "Start Listen\n" 초기 메시지 추가
  - L26 `stopListener(String uniqueName)` — `_Content.remove()` + `_Expired.remove()`
  - L31 `getContent(String uniqueName)` — `GetAndClearContent` (조회와 동시에 빈 문자열로 초기화)
  - L39 `appendContent(String uniqueName, String content)` — `\n` 구분자로 누적
- **private**:
  - L47 `synchronized commandContent(uniqueName, command, content)` — switch 분기:
    - `ContainsKey` — 존재 여부 String 반환
    - `RemoveKey` — 삭제
    - `GetAndClearContent` — 기존 내용 반환 후 빈 문자열로
    - `AppendContent` — 기존 + `\n` + 신규
  - L68 `RemoveExpiredTailer()` — 1h 주기로 24h 초과 키 정리
- **주의**: `==` 로 String 비교 (L12, 32, 40) — Java 에서는 잘못된 패턴이지만 `String.valueOf(boolean)` 의 interned 값으로 우연히 동작.
- **사용처**: UI 의 로그/이벤트 실시간 스트림 (그러나 패키지 외부 호출은 거의 없음 — `/listener` 의 사용 흔적은 보이지 않음).

### 1.10 ParseUtil.java (94 LOC)

- **한 줄**: 정수 안전 파싱 + 콤마/파이프 구분 "K:V|K:V,…" 포맷 → `List<Map<String,String>>` 변환 + XML 문서 파서.
- **public static 메서드**:
  - L19 `int parseIntOrDefault(String s, int defaultValue)` — 예외시 default
  - L31 `List<Map<String,String>> parseStringToMap(String content)` — `,` split → `\|` split → `:` split (2개 토큰만 사용)
  - L70 `Document parseStringToXmlDocument(String xmlData) throws Exception` — `<?xml ?>` 선언 자동 prepend, namespace-aware, whitespace 무시
- **사용처**: 사용처는 적으나 ParseUtil.parseStringToMap 은 설정 파일/속성에서 K:V 직렬화 파싱시 사용.

### 1.11 PythonUtil.java (150 LOC) — **외부 Python 프로세스 실행 흐름**

- **한 줄**: `python <repository\python\fileName> <params>` 를 `ProcessBuilder` 로 실행 → stdout JSON 배열을 `List<Map<String,Object>>` 으로 파싱.
- **상수**:
  - L20 `Logger logger = LoggerFactory.getLogger("PYTHON")` — 전용 PYTHON 로거명
  - L21 `PYTHON_FILE_CMD = "python"`
  - L22-23 `PYTHON_FILE_PATH = REPOSITORY_PATH + "\python"` (역슬래시 — **Windows 전용**)
- **public 메서드**:
  - L25 `executeWithParam(String fileName, boolean stderrFlag)` — 인자 없는 래퍼
  - L35 `executeWithParam(String fileName, boolean stderrFlag, String... params)` — 메인

#### 1.11.1 실행 흐름 (L35-115)

```mermaid
sequenceDiagram
    autonumber
    participant Caller
    participant PU as PythonUtil
    participant FS as Filesystem
    participant Py as python.exe
    Caller->>PU: executeWithParam("predict.py", false, "arg1")
    PU->>FS: new File(REPO/python/predict.py).exists()
    alt 파일 없음
        PU-->>Caller: return null (DEBUG log, no error)
    end
    PU->>Py: ProcessBuilder(["python","REPO/python/predict.py","arg1"]).start()
    PU->>Py: reader = stdout (UTF-8)
    loop while readLine
        Py-->>PU: line (JSON 일부)
        PU->>PU: jsonOutput.append(line)
    end
    PU->>PU: JsonParser.parseString(jsonOutput)
    alt isJsonArray
        loop each element
            PU->>PU: ObjectMapper.readValue(elt, Map.class) → result.add(map)
        end
    else
        PU->>PU: logger.error("unexpected JSON type")
    end
    PU->>Py: process.waitFor() → exitCode
    PU->>PU: process.destroy()
    PU->>PU: _printResult(result, fileName)
    PU-->>Caller: List<Map<String,Object>>
```

- **stderr 처리**: `redirectErrorStream(stderrFlag)` — true 면 stderr 가 stdout 으로 합쳐짐.
- **UTF-8 명시** (L71): `StandardCharsets` 미사용 — 주석에 "no using StandardCharsets" (파싱 예외 발생)
- **private** L121 `_printResult(data, fileName)` — 결과를 행/열로 보기 좋게 로그 출력 ("PREDICTION RESULT" 헤더)
- **사용처**: 예측 모델 호출 (railcut/vibration 예측). 모델 파일이 항상 배치되어 있지 않으므로 파일 부재시 `logger.info()` 로만 기록.

### 1.12 QueryUtil.java (149 LOC)

- **한 줄**: Logpresso 쿼리 더미 제거 + 날짜 변환 (yyyyMMddHHmmssSSS ↔ Date/UTC/ObjectId) + TS partition 컬렉션 명 생성.
- **public static 메서드**:
  - L10 `replaceDummy(String query)` — `| search (1) and `/` or `/`(1)` 패턴 제거 (조건 빌더가 만든 placeholder 제거)
  - L22 `convertToQueryString(Date date)` — yyyyMMddHHmmss 포맷
  - L37 `convertToDate(String dateTimeString)` — `yyyyMMddHHmmssSSS` 파싱 (`%-17s` 로 우측 0 패딩)
  - L55 `convertToUtcTimezone(String dateTimeString)` — `yyyy-MM-ddTHH:mm:ss.SSSZ` 형식
  - L80 `convertToObjectId(String dateTimeString)` — `Long.toHexString(epoch/1000)` 24자 패딩 → MongoDB ObjectId 의 timestamp 부분
  - L107 `convertToCommonDateFormat(String dateTimeString)` — `yyyy-MM-dd HH:mm:ss.SSS`
  - L128 `getTsViewPartitionCollection(String collection, Date from, Date to)` — `_1`/`_2`/`_3`/`_4` 등 일자 기반 파티션 suffix (day/3 → 4분기, day==31 보정)
- **사용처**: `LogpressoConditionUtil`/`queryformat` 패키지에서 사용자 입력 날짜 → Logpresso/Mongo 쿼리 변환시.

### 1.13 ReflectionUtil.java (7 LOC)

- **한 줄**: 현재 메서드명을 stackTrace 에서 추출.
- **public 메서드**: L4 `static String getCurrentMethodName()` — `new Throwable().getStackTrace()[1].getMethodName()`
- **사용처**: 거의 없음 (디버그용 보조).

### 1.14 RemoteCommandUtil.java (37 LOC) — **plink 외부 프로세스 실행**

- **한 줄**: PuTTY `plink -ssh` 로 원격 SSH 명령 실행, stdout 라인 수집해 반환.
- **public 메서드**:
  - L8 `execute(String ip, String serverID, String serverPassword, String command)` — inputFile 없는 래퍼
  - L12 `execute(ip, serverID, serverPassword, command, String inputFile)` — 메인
- **흐름** (L13-35):
  1. `ProcessBuilder("plink","-ssh","ID@IP","-pw","PWD","-batch","cmd")` (L13) — 비밀번호 평문 노출 보안 주의
  2. `redirectOutput(PIPE)`, `redirectError(PIPE)` (L14-15)
  3. `inputFile != null` 면 stdin 으로 파일 redirect (L17-19)
  4. `Scanner(prs.getInputStream())` 로 라인 수집 (L22-28)
  5. finally `outputStream.close()`
- **사용처**: 원격 서버 점검/restart 같은 운영 명령 — 호출처 거의 없음 (보안 정책상 제한적).

### 1.15 SecurityUtil.java (111 LOC)

- **한 줄**: SmartFX BizExecutionContext 와 연동하는 접근 권한 체크 + 정규식 안전화.
- **public enum** `AccessLevel` (L11-28): Disabled(0), SuperAdministrator(10), SystemAdministrator(20), Developer(30), User(40), Guest(50) — 숫자 작을수록 강한 권한
- **public static 메서드**:
  - L35 `assertNull(Object... assertObjects)` — `ObjectUtils.allNotNull()` 실패시 `AssertionError("Assertion-null : Required variables are missing")`
  - L47 `assertAccessLevel(AccessLevel allowMinimumLevel)` — `BizExecutionContext.securityContext().getAccessLevel()` 비교 → 부족시 `RestrictedAccessException`
  - L60 `getCurrentUserId()` — BizExecutionContext 에서 userId 추출 (예외시 빈 문자열)
  - L73 `safePatternInternal(String filter)` — 정규식 메타문자 12종 (`\`, `-`, `$`, `^`, `+`, `*`, `(`, `{`, `[`, `)`, `}`, `]`) 이스케이프 후 `Pattern.compile`
  - L100 `safeFileName(String fileName)` — `\` 와 `..` 제거 (path traversal 방지)
- **외부 의존**: `com.skhynix.smartfx.security.exception.RestrictedAccessException`, `com.skhynix.smartfx.server.api.BizExecutionContext`
- **사용처**: 모든 BizService 의 메서드 헤드 (예외 처리 패턴) — 권한 미달 사용자 차단.

### 1.16 SmsUtil.java (45 LOC)

- **한 줄**: `STA_SMS_HIS` 테이블에 SMS 발송 이력을 적재 (MyBatis 매퍼 ID 직접 호출).
- **public static 메서드**:
  - L14 `sendSMS(String receiver, String message)` — `INSERT_STA_SMS_HIS` 호출 → commit/rollback
  - L33 `getLast5MinCountSMS(String receiver, String message)` — `SELECT_STA_SMS_HIS` selectInt (최근 5분간 발송 카운트)
- **연결**: `QueryExecutorFactory.getQueryExecutor("stasms")` / `QueryExecutorFactory.build("stasms")` — connectionId="stasms"
- **사용처**: AlertingSystemStatus, MonitoringControlBatch 등 — 알람 임계치 초과시 관리자 SMS.

### 1.17 ThreadPool.java (97 LOC)

- **한 줄**: `Executors.newFixedThreadPool` 래퍼로 pause/resume/close 추가, 전역 풀 레지스트리 제공.
- **필드**:
  - L14 `static Map<String, ThreadPool> createdPools` — 이름→풀 레지스트리 (HashMap, **not concurrent**)
  - L16 `String poolName` ("No Name" 기본값)
  - L17 `ThreadPoolExecutor executor`
  - L18 `boolean closed`
  - L19 `boolean paused`
- **public 메서드**:
  - L21 `ThreadPool(String name, int maxThreadCount)` — `Executors.newFixedThreadPool` 생성 + 시작 로그 + `createdPools.put`
  - L30 `synchronized execute(Runnable work) throws AleadyClosedException` — closed 면 예외, paused 면 10ms 대기 루프
  - L48 `synchronized close() throws AleadyClosedException` — 중복 close 차단
  - L54 `getName()`
  - L58 `pause()` / L62 `resume()` — 단순 boolean 토글
  - L66 `getPoolSize()`, L70 `getQueuedSize()`, L74 `getCompletedThreadCount()`, L78 `getActiveThreadCount()`
  - L82 `static ThreadPool getCreatedPool(String name)`
  - L86 `static pauseAll()` / L92 `static resumeAll()` — 전체 일시정지/재개
- **사용처**: DataService L210 `new ThreadPool("TibrvQueue", Env.getTibrvQThreadPoolSize())`; `newMapLoad()` 가 `ThreadPool.pauseAll()` 호출하여 맵 업데이트 중 워커 동결 (DataService L3652).

### 1.18 Util.java (1,304 LOC) — **§1.B 별도 섹션 참조**

### 1.19 XmlUtil.java (852 LOC) — **§1.C 별도 섹션 참조**

---

## §1.A DataService.java (5,500 LOC) — 시스템 중추 싱글톤

### 1.A.0 한 줄 요약

전체 SmartAtlas 시스템의 **상태 저장소**이자 **초기화 진입점**. `BizDataInitializer` 가 부팅시 `initialization(Properties)` 를 호출하면 fab/MCP/맵/Tibrv 모든 자원을 구성하고, 이후 모든 컴포넌트(`batch/`, `process/`, `listener/`, `service/`)는 `DataService.getInstance()` 를 통해 데이터에 접근한다.

### 1.A.1 싱글톤 패턴 (L171-173, L181-185)

```java
private static class Singleton {
    private static final DataService instance = new DataService();  // L172
}
static public DataService getInstance() {
    _blocked();         // 초기화 중이면 대기
    return Singleton.instance;
}
```

- **블로킹 메커니즘** (L187-201): `isBlocked.get()` 이 true 면 10ms 슬립 루프 → 맵 갱신 중에는 데이터 사용 차단
- **L124**: `static public AtomicBoolean isBlocked = new AtomicBoolean(false)` (public — `newMapLoad()` 내부에서 set true/false)

### 1.A.2 핵심 필드 카탈로그

| 라인 | 필드 | 타입 | 용도 |
|------|------|------|------|
| L124 | `isBlocked` | `static AtomicBoolean` | 맵 업데이트 중 사용 차단 플래그 |
| L125 | `fabBitsMap` | `static ConcurrentMap<String,Integer>` | fabId → 비트마스크 (1,2,4,8…) |
| L127 | `isInitialized` | `static boolean` | 초기화 완료 표시 |
| L129 | **`dataQ`** | `Queue<DataSet>` | **현재 활성 DataSet 1개 보유 (peek 으로 접근)** |
| L130 | `queue` | `BlockingQueue<Msg>` | 일반 메시지 큐 |
| L131 | `recordQueue` | `BlockingQueue<Msg>` | 레코드 적재용 큐 |
| L132 | `tibrvMessageQueue` | `BlockingQueue<TibrvSendMsg>` | Tibrv 송신 대기 큐 |
| L134 | `isRailCutInitialized` | `boolean` | RailCut 초기화 플래그 |
| L136 | `firstEdgeInfoMap` | `ConcurrentMap<String,FirstEdgeInfo>` | 첫 엣지 정보 |
| L137 | **`tibrvSenderMap`** | `ConcurrentHashMap<String,TibrvService>` | **fab+type+target → 송신 TibrvService** (key 형식: `M14A:send:star`) |
| L138 | `tibrvReceiverMap` | `ConcurrentHashMap<String,TibrvService>` | 수신 TibrvService 맵 |
| L139 | **`fabPropertiesMap`** | `ConcurrentMap<String,FabProperties>` | **fabId → 팩토리 설정** |
| L140 | `ohtUdpListenerMap` | `ConcurrentHashMap<String,OhtUdpListener>` | OHT UDP 리스너 맵 |
| L141 | `ohtAlarmCodeListMap` | `ConcurrentMap<String,List<String>>` | alarm 코드 리스트 (HID_OFF/VHL_OFF) |
| L143 | `isTibrvSendRunning` | `boolean` | 송신 스레드 가동 여부 |
| L144 | `curMaxLongEdgeDirMap` | `ConcurrentMap<String,Integer>` | LongEdge 방향 최댓값 |
| L146 | `ampUrl` | `String` | AMP REST API URL |
| L147 | `ampListener` | `AmpListener` | AMP 리스너 인스턴스 |

### 1.A.3 모든 public 메서드 카탈로그

| 라인 | 시그니처 | 동작 |
|------|---------|------|
| L175 | `static DataSet getDataSet()` | `dataQ.peek()` — 활성 DataSet 1개 반환 (blocking 대기) |
| L181 | `static DataService getInstance()` | 싱글톤 (blocking 대기) |
| L260 | `boolean isDataServiceRunning()` | `!dataQ.isEmpty()` |
| L272 | `void initialization(Properties properties)` | **부팅 진입점** — `_loadFabData → _loadExtraXmlData → _readAndParsingTxtFile → _initializedVelocity → Util.reflectSwitch → writeRecording` |
| L773 | `DataSet _createNewDataSet(String fabId, DataSet ds, boolean isUpdate, int threadCnt)` | **거대 메서드 ~2800 LOC** — Mcp75 파싱, Raw 데이터 빌드, 엣지/노드/STK/CNV/FIO/Vhl/Station 맵 구성. `ForkJoinPool(threadCnt)` 로 병렬 처리 |
| L3640 | `void newMapLoad()` | 모든 fabId 에 대해 `_createNewDataSet(isUpdate=true)` → ThreadPool.pauseAll() → isBlocked=true → 기존 dataQ 의 모든 맵을 `_parallelUpdateDataSet()` 로 갱신 → isBlocked=false → ThreadPool.resumeAll() |
| L4298 | `ConcurrentHashMap<String,OhtUdpListener> getOhtUdpListenerMap()` | getter |
| L4302 | `void setOhtUdpListenerMap(...)` | setter |
| L4306 | `static int getFabBits(String fabId)` | fabBitsMap 조회 |
| L4310 | `ConcurrentMap<String,FabProperties> getFabPropertiesMap()` | getter |
| L4314 | `boolean getInitialized()` | isInitialized |
| L4318 | `ConcurrentMap<String,List<String>> getOhtAlarmCodeListMap()` | getter |
| L4322 | `ConcurrentMap<String,TibrvService> getTibrvSenderMap()` | 전체 송신 맵 |
| L4326 | `ConcurrentMap<String,TibrvService> getTibrvReceiverMap()` | 전체 수신 맵 |
| L4330 | `TibrvService getTibrvSenderMap(String key)` | 단일 키 (null 안전) |
| L4338 | `ConcurrentMap<String,TibrvService> getTibrvSenderLikeMap(String key)` | **prefix 매칭** — `"M14A:send:"` 같은 prefix 로 전체 매칭 송신자 반환 |
| L4354 | `void setRailCutInitialized(boolean)` | setter |
| L4358 | `boolean getRailCutInitialized()` | getter |
| L4363 | `void addTibrvMessageQueue(TibrvSendMsg data)` | 단일 메시지 add |
| L4367 | `void addTibrvMessageQueue(List<TibrvSendMsg> list)` | 일괄 add |
| L4371 | `<T> void addTibrvMessageQueue(String key, String type, Map<String,T> data)` | 키/타입 + 데이터 Map → TibrvSendMsg 생성 후 add |
| L4378 | `<T> void addTibrvMessageQueue(String key, String type, List<Map<String,T>> list)` | 리스트 버전 |
| L4393 | `<T> void addTibrvMessageQueue(String key, String type, SEND_MSG_FORMAT format, Map<String,T> data)` | 포맷(JSON/XML) 명시 |
| L5055 | `void updateEqpExtInfo(DataSet ds)` | `MEM_ATALS_MAS_EQP_EXT` (Oracle) 조회 → `detEqpTyp`/`eqpGrpNm` 갱신 |
| L5084 | `void writeRecording()` | RAIL_EDGE_*.csv, VEHICLE.csv 기록 (디버그용) |
| L5186 | `String getAmpUrl()` / L5190 `setAmpUrl(String)` | getter/setter |
| L5195 | `AmpListener getAmpListener()` / L5199 `setAmpListener(...)` | getter/setter |

### 1.A.4 private 핵심 메서드 (호출 흐름 이해용)

| 라인 | 시그니처 | 역할 |
|------|---------|------|
| L149-168 | `_START_PROCESS_LOG`/`_ELAPSED_TIME_LOG`/`_END_PROCESS_LOG` | 단계별 로그 헬퍼 |
| L187 | `_blocked()` | isBlocked.get() 동안 10ms 슬립 |
| L204 | **`_sendTibrvMessage()`** | **단일 스레드 시작** — `tibrvMessageQueue.drainTo(items,100)` → `ThreadPool("TibrvQueue")` 에 송신 작업 dispatch. format==JSON 이면 `JsonUtil.gson().toJson()`, 아니면 `XmlUtil.formatLayoutMessage()` 호출. (L233-244) |
| L264 | `_isIC(String fabId)` | M14A/M14B/M16A/M16B/ICPKT/ICPNT/R3/TSV/DWT/WLP/ICPKG 만 허용 |
| L302 | `_loadExtraXmlData()` | XmlUtil.loadLogpressoParm × 2, loadAlarmMessage, loadOhtAlarmMessage, loadVariableEnv |
| L314 | `_loadFabData(Properties)` | `_loadFab` 호출 후 `_inlineConnect → _fabConnect → _setSpnOhtFabId → _setNodeEdgeRef → _setRailEdgeRef → updateEqpExtInfo → dataQ.add(dataSet) → _setRailInfoAffectedForRailCut` |
| L368 | `_setRailInfoAffectedForRailCut()` | RailCutRecordMap 순회 → `new Navigator(railEdge)` 로 영향 port/address 계산 |
| L392 | `_loadFab(Properties)` | `FabIdList` 파싱 → 각 fabId 마다 `_setFabPropertiesFoundation → _setTibrvInfo(send) → _setTibrvInfo(rev) → _setMcpName → _setMcpInfo → _setConveyorToApiUrl → _setMcp75Info → _setBridge → _setInlineConn → _setTibrvDaemonInfo` → `_setAmpUrl` |
| L488 | `_setTibrvInfo(fabProperties, properties, k)` | k=true 송신/false 수신 — `{fabId}.{send/rev}.list` 파싱하여 각 target 별 gid/subject/daemon/service/network 설정 후 `_executeTibrv` |
| L537 | `_executeTibrv(...)` | key=`{fabId}:{send/rev}:{target}` 로 TibrvService 인스턴스화. 송신측은 첫 호출시 `_sendTibrvMessage()` 시작; 수신측은 `startListen()` |
| L593 | `_dynamicMethod(fabProperties, methodName, value)` | **리플렉션 setter/getter** — `FabProperties.class.getMethod(methodName, value.getClass()).invoke(...)` |
| L4175 | `_readAndParsingTxtFile()` | `OhtHidOffAlarmCodeList.txt`/`OhtVhlOffAlarmCodeList.txt` 읽어 alarmCode (4자) 만 List<String> 구성 |
| L4247 | `static resetLoopId(fabId, mcp75ConfigMap, mapRailEdge, mapFromNode2Edge)` | RawLoop 의 exit 으로부터 BFS 로 loop id 할당 |
| L4276 | `static resetLoopIdInLoop(...)` | 재귀 헬퍼 |
| L4406 | `_insertHidDataIntoLogpresso(Map<String,List<String>> data)` | `ATLAS_HID_INFO` 테이블에 `LogpressoAPI.setInsertTuples()` 로 적재 |
| L4452 | `_initializedVelocity()` | `XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY")` → RailEdge 속도 초기값 설정 |
| L4516 | `_setRailEdgeRef(DataSet)` | RailEdge 의 from/to 노드 참조 연결 |
| L4552 | `_setNodeEdgeRef(DataSet)` | Node↔Edge 양방향 참조 구성 |
| L4616 | `_setSpnOhtFabId(DataSet)` | SPN OHT → fabId 매핑 |
| L4651 | `_fabConnect(DataSet, boolean isUpdate)` | bridge 의 fab 연결 |
| L4927 | `_inlineConnect(DataSet, boolean isUpdate)` | inline conveyor 연결 |
| L5099 | `_writeRailEdgeRecording(fabId, mcpName)` | RAIL_EDGE_{fab}_{mcp}.csv 기록 |
| L5143 | `_writeVehicleRecording()` | VEHICLE.csv 기록 |
| L5174 | `_write(csvData, fileName)` | `Util.createAndOverwriteFile(RECORD_FILE_PATH, fileName, …)` |

### 1.A.5 내부 클래스

- **L5204 `RecursiveRailAreaBayNameSetter`** — RailNode/RailEdge 의 Area/Bay 이름을 BFS 로 전파
  - 5개 ConcurrentMap (railEdgeMap, edgeMap, railNodeMap, nodeMap, stationMap) + ForkJoinPool
  - 메서드: `setRemainedAreaBaySet`(L5354), `setRemainedAreaBaySetReverse`(L5379), `setAreaName`(L5404), `setBayName`(L5426), `setStationAreaName`(L5447), `setStationBayName`(L5460)
- **L5475 `RecursiveLoopNameSetter`** — loopId BFS 전파
  - 메서드: `setLoopId(AbstractNode, int loopId)` (L5491)

### 1.A.6 초기화 시퀀스

```mermaid
sequenceDiagram
    participant BDI as BizDataInitializer
    participant DS as DataService
    participant U as Util
    participant XU as XmlUtil
    participant LP as LogpressoAPI
    participant OA as OracleAPI

    BDI->>DS: initialization(props)
    DS->>DS: _loadFabData(props)
    DS->>DS: _loadFab(props)
    loop each fabId in FabIdList
        DS->>DS: _isIC(fabId)?
        DS->>DS: _setFabPropertiesFoundation
        DS->>DS: _setTibrvInfo(send) -> _executeTibrv -> _sendTibrvMessage() 시작
        DS->>DS: _setTibrvInfo(rev) -> _executeTibrv -> TibrvService.startListen()
        DS->>DS: _setMcpName/_setMcpInfo/_setConveyorToApiUrl
        DS->>DS: _setMcp75Info (Mcp75Config 파싱)
        DS->>DS: _setBridge/_setInlineConn/_setTibrvDaemonInfo
    end
    DS->>DS: _setAmpUrl(props)
    DS->>DS: _createNewDataSet(fabId, ds, false, 23) -- ForkJoinPool(23)
    DS->>DS: _inlineConnect/_fabConnect/_setSpnOhtFabId/_setNodeEdgeRef/_setRailEdgeRef
    DS->>OA: updateEqpExtInfo (MEM_ATALS_MAS_EQP_EXT)
    DS->>DS: dataQ.add(dataSet)
    DS->>DS: _setRailInfoAffectedForRailCut
    DS->>XU: _loadExtraXmlData (alarm/variable/customQuery 5종 적재)
    DS->>DS: _readAndParsingTxtFile (OhtHidOff/VhlOff CSV)
    DS->>LP: _initializedVelocity (FIND_RECENT_VELOCITY)
    DS->>U: Util.reflectSwitch(props) -- FunctionItem 스위치 반영
    DS->>DS: writeRecording (디버그 CSV)
    DS->>DS: isInitialized = true
```

### 1.A.7 사용처 (DataService.getInstance())

총 28개 파일에서 호출 — `batch/` 18개, `process/` 4개 (Oht/Cnv/Amp/Ui Worker), `listener/` 4개 (Amp/OhtUdp/AgvUdp/CnvSocketIO), `service/` 2개 (TibrvService, BizDataInitializer), `data/` 4개 (Job/Carrier/HidOff/VhlOff/RailCut RecordItem).

---

## §1.B Util.java (1,304 LOC) — 거대 잡탕 유틸

### 1.B.0 한 줄 요약

3가지 큰 책임이 한 클래스에 혼재: ① **FTP 기반 OHT 맵 파일 다운로드** (lanecut/layout/mcp75/station), ② **AES/GCM 암복호화** (CryptoUtil 의 중복 구현), ③ **FabSet.properties → switch 반영** (factory 별 기능 ON/OFF).

### 1.B.1 필드

| 라인 | 필드 | 타입 |
|------|------|------|
| L56 | `logger` | Logger |
| L57 | `mapFileLastModifiedTimeMap` | `static ConcurrentMap<String,Map<String,Long>>` — fab:mcp → 파일명 → ts |
| L58 | `RETRY_LIMIT_COUNT` | `static final int = 2` |
| L59 | `RETRY_DELAY_MINUTES` | `static final int = 1` |
| L910-912 | static init | `Security.addProvider(new BouncyCastleProvider())` |

### 1.B.2 public static 메서드 카탈로그

| 라인 | 시그니처 | 동작 |
|------|---------|------|
| L61 | `String getComputerName()` | `InetAddress.getLocalHost().getHostName()` (실패시 "Unknown PC") |
| L72 | `boolean isCurrentIC()` | DataService 초기화 완료 + fabIds 가 IC 지역인지 확인 (M14A/M14B/M16A/M16B/ICPKT/ICPNT/R3/TSV/DWT/WLP/ICPKG) |
| L93 | `String getTokenSafely(String[] tokens, int index, String defaultValue)` | 안전 인덱싱 |
| L97 | `int maxLength(List<String> list)` | 리스트 내 가장 긴 문자열 길이 (빈 리스트→0) |
| L124 | `int getIntOrZero(String content)` | 안전 정수 파싱 |
| L139 | `double getDoubleOrZero(String content)` | 안전 double 파싱 |
| L154 | `byte binaryStringToByte(String s)` | "10110010" → byte (8비트만, MSB-first) |
| L165 | `String getSingleNodeValue(Node n, String key)` | dom4j XPath 단일 노드 + attributeValue("value") |
| L177 | `String readFileString(String filePath)` | `Files.readString(path)` (예외시 "") |
| L189 | `boolean writeFileString(String filePath, String content)` | 디렉터리 자동 생성 + 절단 쓰기 |
| L224 | `List<Integer> getAllOhtLayoutFileOverFtp(String fabId, String mcpName, ...4개 boolean, boolean checkingModifiedTime)` | **FTP 맵 다운로드 진입점 (fabId 버전)** |
| L261 | `List<Integer> getAllOhtLayoutFileOverFtp(FabProperties, mcpName, ...4 boolean, checkingModifiedTime)` | **FTP 다운로드 메인 로직** — `_connectFtpServer → _loginFtp → _checkFtpDirectory × 4 → _comparisonOfModifiedTimes × 4 → _searchAndDownloadFile × 4` |
| L895 | `boolean isContentsEqualsCollection(Collection<?>, Collection<?>)` | HashSet 변환 비교 (순서 무시) |
| L915 | `String decrypt(String target, String key)` | AES/GCM 복호화 (`_transformer(false)`) |
| L920 | `String encrypt(String target, String key)` | AES/GCM 암호화 (`_transformer(true)`) |
| L978 | `void insertInLogpressoDatabase(List<Tuple>, String tableName, String className)` | `LogpressoAPI.setInsertTuples(table, list, 15)` 래퍼 + 결과 로그 |
| L995 | `<T> String composeCsvFileContent(List<Map<String,T>>)` | Map 리스트 → CSV (첫 행 헤더, 콤마/따옴표 이스케이프) |
| L1051 | `void createAndOverwriteFile(String directory, String fileName, String content)` | 디렉터리 mkdirs + 기존파일 삭제 + FileWriter 쓰기 |
| L1106 | `void printHelper(List<String> context)` | 테두리(`#`)로 둘러싼 로그 박스 출력 |
| L1134 | `void reflectSwitch(Properties properties)` | **FabSet.properties → FunctionItem 스위치 반영** — CMN/factory별/Conveyor/AMP 4단계로 `_setFunctionItem` 호출 |

### 1.B.3 private 헬퍼 메서드

| 라인 | 시그니처 | 역할 |
|------|---------|------|
| L478 | `_connectFtpServer(FTPClient, FabProperties, fabId, mcpName)` | FTP 21번 포트 connect, retry 2회 (1분 간격) — 실패시 `_reflect()` 로 FabSet.properties 재로드 |
| L548 | `_loginFtp(FTPClient, FabProperties, fabId, mcpName)` | `Util.decrypt(ftpPassword, key)` 후 login, 재시도 로직 동일 |
| L616 | `_checkFtpDirectory(ftpDirectory, fileType, FabProperties, FTPClient, fabId, mcpName)` | `client.listFiles(ftpDirectory)` 로 검증 |
| L692 | `_searchLastModifiedTimeOfFtpFile(ftpDir, ftpFileName, FTPClient)` | FTPFile.getTimestamp() |
| L730 | `_comparisonOfModifiedTimes(ftpDir, key, procCondition, FTPClient)` | mapFileLastModifiedTimeMap 과 비교, 변경시 갱신+true |
| L772 | `_searchAndDownloadFile(ftpDir, fabId, localFile, fileType, FTPClient)` | 로컬 파일 삭제 → createNewFile → `retrieveFile(ftpDir, FileOutputStream)` |
| L820 | `_reflect(processSequence, fileTypeSequence, fabId, mcpName, McpProperties)` | **switch fall-through** 으로 FabSet.properties 재로드 → IP/User/Password/Directory 갱신 |
| L930 | `_transformer(target, key, j)` | CryptoUtil 과 동일한 AES/GCM/NoPadding 로직 (j=true 면 encrypt) |
| L1193 | `_setFunctionItem(fabId, mcpName, properties)` | switchKey=`fabId:mcpName` 에 대해 `FunctionItem.FunctionType` 전체 순회하며 ON/OFF 적용 |
| L1281 | `_getFunctionProperty(FunctionType, fabId, mcpName, props)` | `{fabId}.{mcpName}.{functionType}=TRUE` 파싱 |

### 1.B.4 내부 정적 클래스

- **L1298 `DOWNLOAD_MAP_FILE_TYPE`** — int 상수:
  - `RAILCUT = 1` (inactive_SCH_1.dat)
  - `LAYOUT = 2` (layout.zip)
  - `MCP75CFG = 3` (mcp75.cfg)
  - `STATION = 4` (station.dat)

### 1.B.5 FTP 다운로드 흐름

```mermaid
sequenceDiagram
    participant Caller
    participant U as Util
    participant FTP as FTPClient
    participant Env

    Caller->>U: getAllOhtLayoutFileOverFtp(fabId, mcpName, 4 booleans, checkTime)
    U->>U: mapFileLastModifiedTimeMap = Env.getMapFileLastModifiedTime()
    U->>FTP: _connectFtpServer (port 21, retry 2회)
    alt 연결 실패
        U->>Env: _reflect → reloadFabsetProperties
        U->>FTP: retry connect
    end
    U->>FTP: setSoTimeout(3000), setBufferSize(1M)
    U->>FTP: _loginFtp (Util.decrypt(password) 후 login)
    par procLaneCut/Layout/Mcp75/Station 각각
        U->>FTP: _checkFtpDirectory (listFiles)
    end
    opt checkingModifiedTime
        U->>FTP: _comparisonOfModifiedTimes × 4 (timestamp 비교)
    end
    par 다운로드 활성 항목
        U->>FTP: _searchAndDownloadFile (retrieveFile → FileOutputStream)
    end
    U->>FTP: logout + disconnect
    U->>Env: setMapFileLastModifiedTime
    U-->>Caller: List<Integer> (다운로드된 항목 코드)
```

### 1.B.6 사용처

- **암복호화**: LogpressoAPI(`Util.decrypt`/`encrypt` 직접 사용 안함; CryptoUtil 사용 — Util 의 `decrypt` 는 `_loginFtp` L575 에서만 사용)
- **FTP**: `BizDataInitializer`, `MonitoringControlBatch` 등 부팅/스케줄에서 호출
- **`reflectSwitch`**: DataService L284 (initialization 마지막 단계), `SwitchSystemBatch.java`
- **`createAndOverwriteFile`**: DataService L5178, PythonUtil 가 csv 입력 파일 작성
- **`insertInLogpressoDatabase`**: 모든 `*Batch.java` 클래스 (가장 빈번한 적재 경로)

---

## §1.C XmlUtil.java (852 LOC) — XML 메시지/쿼리 로더 + Tibrv 메시지 빌더

### 1.C.0 한 줄 요약

5종의 XML 파일을 메모리 Map 으로 로드(`alarm_message.xml`, `oht_alarm_message.xml`, `variable.xml`, `customQuery.xml`, `customQuery2.xml`)하고, **`formatLayoutMessage()` 로 CMESSAGE 표준 형식의 Tibrv XML 페이로드를 빌드**한다.

### 1.C.1 static 캐시 필드 (L43-47)

| 필드 | 소스 XML | 내용 |
|------|----------|------|
| `alarmMessage` | alarm_message.xml | code → message 템플릿 |
| `ohtAlarmMessage` | oht_alarm_message.xml | OHT 전용 code → 템플릿 |
| `variableMessage` | variable.xml | variable code → 값 |
| `logpressoQuery` | customQuery.xml | query id → Logpresso SPL |
| `logpressoQuery2` | customQuery2.xml | query id → Logpresso SPL (2nd) |

### 1.C.2 public 메서드 카탈로그

| 라인 | 시그니처 | 동작 |
|------|---------|------|
| L49 | `boolean verifyXml(String content)` | `CharSequenceInputStream` + DocumentBuilder.parse — 파싱 성공 여부 |
| L72 | `void updateXml(filePath, tagName, queryId, queryContent)` | 특정 태그 id 의 textContent 갱신 → Transformer 로 저장 + DOCTYPE 유지 |
| L155 | `String loadRaw(filePath, tagName, key)` | `_loadXmlMessage(file, tagName, "id").get(key)` |
| L159 | `Map<String,Element> loadXmlMap(filePath, tagName)` | tagName 의 모든 Element 를 id → Element 매핑 |
| L185 | `String loadQuery(filePath, queryId)` | `<query id=…>` 우선, 없으면 `<select id=…>` (MyBatis 호환) |
| L200 | `List<Map<String,Object>> selectLogpressoQuery(String queryId)` | logpressoQuery 캐시 hit → `LogpressoAPI.responseResult(query)`. miss 면 LOGPRESSO_CUSTOM_QUERY 재로드 |
| L215 | `List<Map<String,Object>> selectLogpressoQuery2(String queryId)` | 동일하나 LOGPRESSO_CUSTOM_QUERY2 |
| L231 | `List<Map<String,Object>> selectLogpressoQuery(String path, String id)` | 임의 경로 버전 |
| L243 | `List<Tuple> convert(List<Map<String,Object>>)` | Map → Logpresso Tuple 변환 (null→"") |
| L261 | `void mapToTplConvert(Map<String,Object>, Tuple)` | 단건 Map 을 Tuple 에 put (null→"") |
| L277 | `<T> String formatLayoutMessage(String tibrvKey, String errorType, Map<String,T> data)` | `formatMessageToString(tibrvKey, LAYOUT_DATA_FORMAT, errorType, data)` |
| L334 | `String formatMessageToString(tibrvKey, filePath, messageType, dataMap)` | **CMESSAGE 표준 빌더** (§1.C.3) |
| L628 | `String DEFAULT_VALUE = "Unknown ALARM CODE: "` | 알람코드 미발견시 |
| L630 | `String getMessage(String alarmCode, Object... params)` | alarmMessage 에서 MessageFormat 으로 치환 |
| L646 | `String getOhtMessage(String alarmCode, Object... params)` | ohtAlarmMessage 사용 |
| L662 | `String getVariableEnv(String variableCode, Object... params)` | variableMessage 사용; params 없으면 raw 반환 |
| L684 | `void loadAlarmMessage()` | alarm_message.xml → alarmMessage 갱신 |
| L692 | `void loadOhtAlarmMessage()` | oht_alarm_message.xml |
| L700 | `void loadVariableEnv()` | variable.xml |
| L709 | `void loadLogpressoParm(String directory)` | customQuery.xml 또는 customQuery2.xml 분기 적재 |

### 1.C.3 `formatMessageToString()` 핵심 흐름 (L334-519)

`CMESSAGE_CMN_FORMAT.xml` (헤더 공통) + `CMESSAGE_LAYOUT_DATA.xml` (데이터 본문) 을 병합하여 최종 Tibrv 페이로드 생성.

```mermaid
flowchart TD
    Start([formatMessageToString]) --> P1[#1: XML 2개 파싱<br/>CMN_FORMAT 3회 retry]
    P1 --> P1a{둘 다 null?}
    P1a -- yes --> Fail[return '']
    P1a -- no --> RC[_removeComments cmnRoot/dataRoot]
    RC --> P2a[#2-1: TRANSACTIONID +1<br/>그리고 cmnDoc 저장]
    P2a --> P2b[#2-2: HEADER 의 MESSAGENAME=subject.type<br/>TIME=현재시각]
    P2b --> P2c[#2-3: ORIGINATED.ORIGINATEDNAME=messageType]
    P2c --> P3[#3: dataMap 의 key 별로<br/>dataRoot 의 해당 태그 textContent 설정]
    P3 --> P4[#4: dataRoot 의 child 노드를<br/>cmnDoc 의 commonDataElement 에 importNode]
    P4 --> Pretty[flattenDocument → prettyFormatXml]
    Pretty --> End([return XML String])
```

- **TRANSACTIONID 증분** (L402-411): 매 호출마다 +1 후 `_saveXmlFile()` 로 디스크 저장 — 동시성 문제 가능성
- **MESSAGENAME 구성** (L427-438): `DataService.getInstance().getTibrvSenderMap().get(tibrvKey).getSubject() + "." + messageType` → 예: `M14.IC.ATLAS.STARPDT.LAYOUT.HID_OFF`
- **CMN_FORMAT 파일 락 재시도** (L354-368): 3회까지 100ms 간격으로 retry — 다른 프로세스가 점유 중일 때

### 1.C.4 private 헬퍼

| 라인 | 시그니처 | 역할 |
|------|---------|------|
| L67 | `setDocTypeDeclarationMaintenance(Transformer)` | MyBatis DTD 선언 유지 |
| L101 | `_loadXml(directory)` | DocumentBuilder.parse + normalize |
| L521 | `_removeComments(Node)` | 재귀적으로 COMMENT_NODE/CDATA_SECTION_NODE 제거 |
| L536 | `_saveXmlFile(Document, File)` | Transformer 로 디스크 저장 |
| L578 | `flattenDocument(Document)` | `>\s+<` 공백 제거 + Transformer 출력 |
| L598 | `prettyFormatXml(String xml)` | 들여쓰기 4칸 적용 |
| L730 | `_loadXmlMessage(directory, tagName, key)` | tagName 의 attribute=key 값 → textContent 매핑 |

### 1.C.5 사용처

- **DataService** L236, L305-311, L4463 (`selectLogpressoQuery`)
- **LayoutUtil** L19, L62-131 (`getMessage`)
- **MybatisQueryHandler** L15 (`loadXmlMap`, `loadRaw`, `updateXml`)
- **모든 listener**: `XmlUtil.getMessage`, `XmlUtil.formatLayoutMessage` (Tibrv 송신 직전)

---

## §2. comm/ 2 파일

### 2.1 OracleAPI.java (36 LOC)

- **한 줄**: `QueryExecutorFactory.build(connectionId)` 를 try-with-resources 로 감싼 select/insert/delete 3개 정적 메서드.
- **public static 메서드**:
  - L12 `DataTable select(String connectionID, String mybatisID)` — 예외시 null
  - L20 `int insert(String connectionID, String mybatisID)` — 예외시 -1
  - L28 `int delete(String connectionID, String mybatisID)` — 예외시 -1
- **공통 패턴**:
  ```java
  try (var executor = QueryExecutorFactory.build(connectionID)) {
      return executor.<method>(mybatisID);
  } catch (Exception e) { return null/-1; }
  ```
- **외부 의존**: `com.skhynix.smartfx.dataaccessfx.{DataTable,QueryExecutorFactory}` — SmartFX 프레임워크가 connectionId → JDBC URL 매핑
- **사용처**: UiLogpresso, UpdatingDbMachineListBatch, UpdatingDbMasterDataBatch, AmpBufferFlushBatch — 모두 Oracle 마스터 데이터 갱신.

### 2.2 TibrvAPI.java (74 LOC)

- **한 줄**: TIBCO Rendezvous 의 `TibrvRvdTransport` 를 생성→사용→destroy 하는 stateless wrapper. (DataService 의 영속적 `TibrvService` 와 대조)
- **public static 메서드**:
  - L15 `boolean send(String service, String network, String daemon, String subject, String dataFieldName, String data)` — 단발 메시지 송신
    - `new TibrvRvdTransport(service, network, daemon)` (L20)
    - `tibrvMessage.setSendSubject(subject)` + `add(dataFieldName, data)` (L25-26)
    - `transport.send(tibrvMessage)` (L28)
    - finally: `transport.destroy()` + `tibrvMessage.dispose()` (L36-42)
  - L47 `TibrvListener listen(String service, String network, String daemon, String subject, TibrvMsgCallback callback)` — 리스너 생성
    - `new TibrvQueue()` + `new TibrvListener(queue, callback, transport, subject, null)` (L55-56)
    - 예외시 transport/queue destroy
- **외부 의존**: `com.tibco.tibrv.{TibrvListener,TibrvMsg,TibrvMsgCallback,TibrvQueue,TibrvRvdTransport}`
- **주의 (L41)**: send 메서드의 finally 블록에서 `tibrvMessage.dispose()` 가 null 일 수 있는데 null 체크 없음 — NPE 가능성
- **사용처**: 단순 일회성 송신/수신용. 대부분의 양산 코드는 `TibrvService` 를 사용.

---

## §3. db/ 패키지 (logpresso/mongodb/mybatis)

### 3.1 db/logpresso/LogpressoAPI.java (453 LOC)

- **한 줄**: Logpresso 클라이언트 연결 + **2 노드 fallback** + Canceller 타이머로 쿼리 강제 종료 + insert 재시도.
- **static 필드**:
  - L26 `timer = new ScheduledThreadPoolExecutor(1)` — 단일 스레드 스케줄러 (Canceller 용)
  - L27 `activeNode = 1` (public) — 외부에서 노드 변경 가능 (사용처 없음, 사실상 placeholder)
  - L28 `CONN_TIMEOUT = 500` ms
  - L29 `READ_TIMEOUT = 5000` ms
  - L30 `_ActiveNode = 1` (private) — 실제 사용 변수, 1↔2 fallback 시 갱신

#### 3.1.1 private 내부 클래스 `Canceller implements Runnable` (L39-60)

- **필드**: `Logpresso client`, `int queryId`
- **run()**: `client.stopQuery(queryId)` — 닫힌 클라이언트면 무시

#### 3.1.2 연결 메서드 (L62-150)

| 라인 | 시그니처 | 동작 |
|------|---------|------|
| L62 | `getConnection()` | fab=null, 기본 timeout |
| L66 | `getConnection(String fab)` | 단일 fab |
| L70 | `getConnection(String fab, int connectTimeout, int readTimeout)` | **메인** — fab=null 이면 `Env.getLogpressoPropertiesMap()` 의 첫 entry 사용 |

**2 노드 Fallback 로직** (L86-144):

```mermaid
flowchart TD
    Start([getConnection]) --> Active{_ActiveNode}
    Active -- 1 --> Try1[connect hosts[0]]
    Active -- 2 --> Try1b[connect hosts[0] 우선<br/>실패시 hosts[1]]
    Try1 -- fail --> Recovery
    Try1b -- both fail --> Recovery
    Try1 -- ok --> Return([return client])
    Try1b -- ok --> Return
    Recovery{현재 _ActiveNode가<br/>여전히 동일?} -- yes --> Switch
    Switch{active==1?}
    Switch -- yes --> Try1Again[hosts[0] 재시도<br/>실패시 _ActiveNode=2<br/>hosts[1]]
    Switch -- no --> SetActive1[_ActiveNode=1<br/>hosts[0]]
    Try1Again --> Return
    SetActive1 --> Return
```

- 비밀번호 복호화: `CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey())` (L89,96,101,123,131,137)

#### 3.1.3 쿼리 메서드 카탈로그

| 라인 | 시그니처 | 동작 | timeout/재시도 |
|------|---------|------|----------------|
| L158 | `responseResult(String paramQuery)` | fab=null 위임 | cursor.close/client.close 모두 **10초 FutureTask** 로 보호 (L196-220) |
| L165 | `responseResult(String fabSite, String paramQuery)` | **메인** — `client.query(paramQuery)` 후 `cursor.hasNext()` 루프 | M14→IC 변환 (L166-168) |
| L226 | `executeQuery(String queryStmt)` | limit=5000, delay=15s | |
| L230 | `executeQuery(String fabSite, String queryStmt)` | limit=0, delay=60s | |
| L235 | `executeQuery(String fabSite, String queryStmt, int limit, int delaySecond)` | **메인** — `createQuery → startQuery → schedule Canceller → waitUntil → getResult` | `timer.schedule(Canceller, delaySecond, SECONDS)` (L262) |
| L303 | `setDropTable(String sTable)` | `client.dropTable` | - |
| L327 | `setCreateTable(String sTable)` | `client.query("import create=t " + sTable)` | - |
| L352 | `setInsertTable(String sQuery)` | 따옴표/CR/LF 정리 후 `client.query` | - |
| L377 | `setPurgeTableData(String from, String to, String sTable)` | `client.query("purge from=A to=B sTable")` | - |
| L404 | `setInsertTuple(String table, Tuple tuple, int timeoutSecond)` | List.of(tuple) 로 위임 | |
| L408 | `setInsertTuples(String table, List<Tuple>, int timeoutSecond)` | **TimeoutException 3회 재시도 후 실패 로그** (L412-422) | |
| L430 | `setInsertTuplesInternal(...) throws Exception` | `Future<Integer> result = client.insert(table, tuples); client.flush(); result.get(timeout, SECONDS)` | |

#### 3.1.4 `responseResult()` 흐름 (L165-224)

```mermaid
sequenceDiagram
    participant Caller
    participant LP as LogpressoAPI
    participant Client as Logpresso
    Caller->>LP: responseResult("M14", query)
    LP->>LP: fabSite="IC" (M14→IC 변환)
    LP->>LP: getConnection("IC")
    LP->>Client: client.query(paramQuery) -> Cursor
    loop cursor.hasNext()
        Client-->>LP: cursor.next().toMap()
        LP->>LP: resultSetLocal.add(map)
    end
    LP->>LP: finally: FutureTask(cursor.close).get(10s)
    LP->>LP: finally: FutureTask(client.close).get(10s)
    LP-->>Caller: List<Map<String,Object>>
```

#### 3.1.5 `executeQuery()` 흐름 (L235-301)

`createQuery` → `startQuery` → `schedule Canceller(delaySecond)` → `waitUntil(limit OR null)` → `getResult` → finally `removeQuery + close`

- **CANCELLED 상태일 때는 결과 조회 skip** (L273)
- timeout 보호: Canceller 가 delaySecond 후 자동 `stopQuery` 호출
- `searchDelayMillsec = 15000` 은 사용되지 않고 로그에만 표시 (L284)

#### 3.1.6 `setInsertTuples` 재시도

```java
try { return setInsertTuplesInternal(...); }
catch (TimeoutException) {
    for (i=1; i<=3; i++) {
        try { return setInsertTuplesInternal(...); }  // 3회 추가 시도
        catch (TimeoutException) {}
    }
    logger.error("Timeout Failed");
}
```

- **사용처**: DataService(`_insertHidDataIntoLogpresso`), Util(`insertInLogpressoDatabase`), 모든 `*Batch.java`

### 3.2 db/mongodb/MongodbAPI.java (114 LOC)

- **한 줄**: fab → MongoDatabase 풀 캐시 + find/aggregate/insertMany 3개 정적 메서드 (Builder 체인 반환).
- **상수**:
  - L27 `TIMEOUT_MINUTE = 2`
  - L29 `_DatabasePool : HashMap<String, MongoDatabase>` — fab → DB 캐시
- **private** L31 `getDatabase(String fab)`:
  1. 풀에서 조회 → hit 면 반환
  2. miss 면 `Env.getMongodbPropertiesMap().get(fab)` 로 properties 추출
  3. 비밀번호 복호화: `URLEncoder.encode(CryptoUtil.decrypt(props.getPassword(), Env.getMongodbDecryptKey()), "UTF-8")` (L45)
  4. connectionString 조립: `mongodb://id:pwd@host1:port,host2:port,…/?authSource=mcslog` (L50-60)
  5. `MongoClients.create(connectionString).getDatabase(dbName)` → 풀에 저장
- **public static 메서드**:
  - L69 `MongodbFindLinq find(String fab, String collection, Bson filter)` — `.maxTime(2,MINUTES).allowDiskUse(true)` 기본값 (L72)
  - L82 `MongodbAggregateLinq aggregate(String fab, String collection, BsonArray filter)` — BsonArray 의 각 element 를 Document 로 변환하여 aggregate pipeline 구성 (L85-88)
  - L99 `boolean insertMany(String fab, String collection, List<Document>, InsertManyOptions)` — `MongoBulkWriteException` 은 options.isOrdered() 일 때만 로그

#### 3.2.1 Builder 패턴 (Linq 시리즈)

`find()` / `aggregate()` 의 반환 타입은 MongoDB Java Driver 의 `FindIterable`/`AggregateIterable` 을 감싼 **wrapper builder**. fluent chain 으로 옵션 추가 가능:

```java
MongodbAPI.find(fab, coll, filter)
    .sort(...)
    .projection(...)
    .limit(100)
    .toList();   // List<Map<String,Object>>
```

### 3.3 db/mongodb/MongodbLinq.java (96 LOC) — 베이스 클래스

- **제네릭**: `MongodbLinq<TIterable extends MongoIterable<Document>>` (L21)
- **필드**:
  - L24 `_BsonJson : String` — 디버그용 BSON JSON 표현
  - L25 `_Iterable : TIterable` (protected)
- **public 메서드**:
  - L27 `MongodbLinq(String bsonjson, TIterable iterable)`
  - L32 `MongoCursor<Document> iterator()` / L36 `cursor()` / L40 `Document first()`
  - L44 `<U> MongoIterable<U> map(Function<Document,U>)`
  - L48 `<A extends Collection<? super Document>> A into(A target)`
  - L52 `MongodbLinq<MongoIterable<Document>> batchSize(int)`
  - L56 `List<Map<String,Object>> toList()` → toList(-1)
  - L60 `List<Map<String,Object>> toList(int limit)` — **핵심** — batchSize 설정 후 Document 순회, `Objects.toString(value,"")` 로 모든 값을 String 변환 (L69)
  - L91 `FutureTask<List<Map<String,Object>>> toListTask(int limit)` — 비동기 실행용
- **예외 처리** (L78-81): `MongoInterruptedException`, `MongoExecutionTimeoutException` 은 silently swallow

### 3.4 db/mongodb/MongodbFindLinq.java (167 LOC)

- **상속**: `extends MongodbLinq<FindIterable<Document>>`
- **public 메서드** (모두 self 반환 빌더):
  - L19 `filter(Bson)`, L25 `limit(int)`, L31 `skip(int)`
  - L37 `maxTime(long, TimeUnit)`, L43 `maxAwaitTime(long, TimeUnit)`
  - L49 `projection(Bson)`, L55 `sort(Bson)`
  - L61 `noCursorTimeout(boolean)`, L67 `oplogReplay(boolean)` (deprecated), L74 `partial(boolean)`
  - L80 `cursorType(CursorType)`, L86 `collation(Collation)`
  - L92 `comment(String)`, L98 `comment(BsonValue)`
  - L104 `hint(Bson)`, L110 `hintString(String)`, L116 `let(Bson)`
  - L122 `max(Bson)`, L128 `min(Bson)`
  - L134 `returnKey(boolean)`, L140 `showRecordId(boolean)`, L146 `allowDiskUse(Boolean)`
  - L152~166 `explain()` 4 오버로드

### 3.5 db/mongodb/MongodbAggregateLinq.java (99 LOC)

- **상속**: `extends MongodbLinq<AggregateIterable<Document>>`
- **생성자**: `new MongodbAggregateLinq(BsonArray query, AggregateIterable<Document>)` — `_BsonJson` 을 `[a,b,c,…]` 로 직렬화 (L17)
- **public 메서드**:
  - L20 `void toCollection()` — `_Iterable.toCollection()` (out 단계 실행)
  - L24 `allowDiskUse(Boolean)`, L30 `maxTime(long,TimeUnit)`, L36 `maxAwaitTime(long,TimeUnit)`
  - L42 `bypassDocumentValidation(Boolean)`, L48 `collation(Collation)`
  - L54 `comment(String)`, L60 `comment(BsonValue)`
  - L66 `hint(Bson)`, L72 `hintString(String)`, L78 `let(Bson)`
  - L84~98 `explain()` 4 오버로드

### 3.6 db/mongodb/MongodbQueryPool.java (94 LOC)

- **한 줄**: `repository/dataaccessfx/mongodb.xml` 의 query 트리를 `If`/`IfNotBlank` 태그로 조건부 평가하여 최종 쿼리 문자열 생성.
- **필드 (모두 `static`)**:
  - L15 `_AcesssLock = new Object()` (오타: Access)
  - L16 `_QueryPool : Element` — JDOM Element (lazy init)
- **private**:
  - L18 `Element getQueryPool()` — double-checked locking 으로 `repository/dataaccessfx/mongodb.xml` 로딩 → `<Queries>` 자식 element
  - L37 `performTag(Element element, HashMap<String,Object> arguments)` — 재귀 순회:
    - `<If Key="x" Value="y">` 자식 — arguments[x] != y 면 `detach()` 로 제거
    - `<IfNotBlank Key="x">` 자식 — arguments[x] blank 면 detach
- **public**:
  - L78 `String getQuery(String id, HashMap<String,Object> arguments)` — `getQueryPool().getChild(id).clone()` → `performTag` 호출 → `queryTree.getValue()` 추출 → `#{key}` → `'value'`, `${key}` → `value` 치환 (L88-89)

### 3.7 db/mybatis/MybatisQueryHandler.java (72 LOC)

- **한 줄**: `repository/dataaccessfx/mcs_*.xml` MyBatis 매퍼 XML 파일 목록·내용·갱신 API.
- **상수**:
  - L20 `FILE_PATH = SMARTFX_REPOSITORY\dataaccessfx` (역슬래시)
  - L21 `PREFIX = "mcs_"`
- **import (L15)**: `static com.skhynix.smartatlas.util.XmlUtil.*` — `loadXmlMap`, `loadRaw`, `updateXml` 사용
- **public static 메서드**:
  - L23 `List<String> getAllQueryFileNames()` — dataaccessfx 디렉터리의 `mcs_` 접두사 파일명만
  - L30 `List<String> getQueryList(String fileName)` — 특정 mapper 파일의 `<select id="…">` ID 리스트
  - L40 `String getQueryContent(String fileName, String queryId)` — 해당 select 의 textContent
  - L49 `boolean updateQueryContent(fileName, queryId, queryContent)` — XmlUtil.updateXml 호출
- **private**:
  - L59 `getFilePath(String fileName)` — `Path.of(FILE_PATH\fileName).toString()`
  - L63 `List<Path> getAllQueryFiles()` — `Files.list(path).collect(toList())`
- **사용처**: UI 의 SQL 매퍼 편집기 (관리자 화면) — 운영 중 MyBatis 매퍼 수정 가능.

---

## §4. DB 접근 패턴 정리

### 4.1 시스템 전체 DB 토폴로지

```mermaid
graph LR
    subgraph SmartAtlas
        DS[DataService]
        Batch[*Batch.java<br/>~30개]
        Worker[*MsgWorkerRunnable<br/>4개]
        Listener[*Listener<br/>~5개]
        Service[*Service<br/>~3개]
        UI[UI 핸들러]
    end

    subgraph DB_APIs
        LP[LogpressoAPI<br/>2-node fallback]
        MA[MongodbAPI<br/>fab→DB 풀]
        OA[OracleAPI<br/>SmartFX 위임]
        MY[MybatisQueryHandler]
        SMS[SmsUtil]
    end

    subgraph External
        LPS[(Logpresso<br/>Cluster)]
        MGS[(MongoDB<br/>per-fab)]
        ORA[(Oracle<br/>via SmartFX)]
        MAP[mongodb.xml<br/>repository]
        MAPS[mcs_*.xml<br/>repository]
    end

    DS --> LP
    DS --> OA
    Batch --> LP
    Batch --> OA
    Worker --> LP
    Worker --> OA
    Service --> LP
    Listener --> OA
    UI --> MY
    UI --> MA
    SMS --> OA
    LP --> LPS
    MA --> MGS
    OA --> ORA
    MA --> MAP
    MY --> MAPS
```

### 4.2 각 컴포넌트가 사용하는 DB

| 컴포넌트 | 주 DB | 메서드 | 용도 |
|----------|-------|--------|------|
| **DataService** | Logpresso (insert), Oracle (select) | `LogpressoAPI.setInsertTuples`, `OracleAPI.select` | HID 정보 적재, EQP 마스터 갱신 |
| **batch/ (~30)** | Logpresso (mostly), Oracle | `executeQuery`/`responseResult`/`setInsertTuples` | 매트릭/통계 집계, 알람 검출, 마스터 갱신 |
| **process/ Worker** | Logpresso | `responseResult` (`XmlUtil.selectLogpressoQuery`) | 실시간 알람 컨텍스트 조회 |
| **service/UiLogpresso** | Logpresso + Oracle | both | UI 쿼리 API 백엔드 |
| **listener/AmpListener etc.** | Oracle | `OracleAPI.select` | 마스터 데이터 lookup |
| **SmsUtil** | Oracle (`stasms` connection) | `INSERT_STA_SMS_HIS`, `SELECT_STA_SMS_HIS` | SMS 발송 로깅 |
| **UI: MyBatis 편집기** | XML 파일 직접 | `MybatisQueryHandler.*` | 운영 중 SQL 수정 |
| **UI: Mongo 직접 조회** | MongoDB | `MongodbAPI.find/aggregate` + `MongodbQueryPool` | 시계열 차트 (mongodb.xml의 조건부 쿼리) |

### 4.3 쿼리 정의 위치 매트릭스

| 쿼리 종류 | 정의 위치 | 로더 | 사용 API |
|-----------|-----------|------|----------|
| Logpresso 사용자 정의 1 | `repository/customQuery.xml` | `XmlUtil.loadLogpressoParm` | `XmlUtil.selectLogpressoQuery` → LogpressoAPI |
| Logpresso 사용자 정의 2 | `repository/customQuery2.xml` | 동일 | `XmlUtil.selectLogpressoQuery2` |
| Logpresso 즉석 | 코드 인라인 (String) | - | `LogpressoAPI.responseResult/executeQuery` 직접 |
| MyBatis Oracle | `repository/dataaccessfx/<connId>.xml` (mcs_*) | SmartFX `QueryExecutorFactory` | OracleAPI/SmsUtil |
| MongoDB | `repository/dataaccessfx/mongodb.xml` | `MongodbQueryPool.getQueryPool()` (lazy, JDOM2) | `MongodbAPI.find/aggregate` |

### 4.4 timeout / 재시도 정책 비교

| API | 연결 timeout | 읽기 timeout | 재시도 |
|-----|--------------|-------------|--------|
| LogpressoAPI | 500ms | 5000ms | **연결: 2 노드 fallback (즉시)**, **insert: TimeoutException 3회** |
| MongodbAPI | (driver 기본) | `.maxTime(2, MINUTES)` | 없음 |
| OracleAPI | (SmartFX 위임) | (SmartFX 위임) | 없음 (예외시 null/-1) |
| `Util._connectFtpServer` (참고) | (TCP 기본) | `setSoTimeout(3000)` | 2회 (1분 간격) + properties 재로드 |

### 4.5 비밀번호 복호화 흐름

```mermaid
graph LR
    A[FabSet.properties /<br/>mongo/logpresso properties] --> B[Env.get*PropertiesMap]
    B --> C[encrypted password<br/>String]
    C --> D{API 선택}
    D --> E[CryptoUtil.decrypt<br/>password, decryptKey]
    D --> F[Util.decrypt<br/>password, key]
    E --> G[AES/GCM/NoPadding<br/>32B key padded]
    F --> G
    G --> H[plaintext password]
    H --> I[client.connect / FTP login]
```

- **CryptoUtil.decrypt** (84L) — 단순 정적 메서드, 예외시 null
- **Util.decrypt** (`_transformer`) — 동일 알고리즘, 더 상세한 로그
- 두 구현이 함수적으로 동등하지만 두 곳에 존재 (코드 중복)

### 4.6 동시성/스레드 모델 요약

| 컴포넌트 | 스레드 모델 |
|----------|-------------|
| `DataService.initialization` | 동기 호출, 내부에서 ForkJoinPool(23) 사용 |
| `DataService._sendTibrvMessage` | 단일 디스패처 스레드 + `ThreadPool("TibrvQueue")` |
| `DataService.newMapLoad` | `ThreadPool.pauseAll()` + `isBlocked=true` 로 dataQ 사용 모든 스레드 동결 후 갱신 |
| `LogpressoAPI.timer` | `ScheduledThreadPoolExecutor(1)` — Canceller 스케줄링 |
| `LogpressoAPI.responseResult` | finally 에서 FutureTask(10s) 로 close 보호 |
| `MongodbAPI` | MongoClient 자체 풀 사용, `MongodbLinq.toList` 는 호출자 스레드 |
| `AsyncUtil` | 무한 루프 청소 스레드 (60s) |
| `MemoryTailerUtil` | 무한 루프 청소 스레드 (1h) |
| `ThreadPool` | 사용자 정의 FixedThreadPool, pause/resume 가능 |

---

## 부록 A. 28 파일 전수 검증 체크리스트

- [x] util/AleadyClosedException.java (17L) — §1.1
- [x] util/AsyncUtil.java (70L) — §1.2
- [x] util/CryptoUtil.java (84L) — §1.3
- [x] util/DataService.java (5500L) — §1.A
- [x] util/FilePathUtil.java (67L) — §1.5
- [x] util/JsonToStringBuilder.java (173L) — §1.6
- [x] util/JsonUtil.java (74L) — §1.7
- [x] util/LayoutUtil.java (309L) — §1.8
- [x] util/MemoryTailerUtil.java (93L) — §1.9
- [x] util/ParseUtil.java (94L) — §1.10
- [x] util/PythonUtil.java (150L) — §1.11
- [x] util/QueryUtil.java (149L) — §1.12
- [x] util/ReflectionUtil.java (7L) — §1.13
- [x] util/RemoteCommandUtil.java (37L) — §1.14
- [x] util/SecurityUtil.java (111L) — §1.15
- [x] util/SmsUtil.java (45L) — §1.16
- [x] util/ThreadPool.java (97L) — §1.17
- [x] util/Util.java (1304L) — §1.B
- [x] util/XmlUtil.java (852L) — §1.C
- [x] comm/OracleAPI.java (36L) — §2.1
- [x] comm/TibrvAPI.java (74L) — §2.2
- [x] db/logpresso/LogpressoAPI.java (453L) — §3.1
- [x] db/mongodb/MongodbAPI.java (114L) — §3.2
- [x] db/mongodb/MongodbLinq.java (96L) — §3.3
- [x] db/mongodb/MongodbFindLinq.java (167L) — §3.4
- [x] db/mongodb/MongodbAggregateLinq.java (99L) — §3.5
- [x] db/mongodb/MongodbQueryPool.java (94L) — §3.6
- [x] db/mybatis/MybatisQueryHandler.java (72L) — §3.7

**총 28/28 파일 분석 완료. 총 LOC: 9,343 (util) + 110 (comm) + 1,095 (db) = 10,548 LOC**
