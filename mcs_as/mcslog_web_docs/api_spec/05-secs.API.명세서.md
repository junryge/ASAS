# SECS / EI 통신 로그 API 명세서

> SK hynix MCS Log 조회 시스템 — `com.skhynix.supply.secs` 패키지 (SECS/EI 통신 로그 모듈)

---

## 1. API 개요

### 1.1. 모듈 정의

본 모듈은 반도체 FAB 자동화 시스템(MCS, Material Control System)이 장비와 주고받는 통신 로그를 조회하기 위한 API 들을 제공한다.

| 약어 | 풀이 | 설명 |
| --- | --- | --- |
| SECS | SEMI Equipment Communications Standard | SEMI에서 정의한 반도체 장비 통신 표준. 호스트(MCS) ↔ 장비(EQP) 간 메시지(S/F, SECS-II Stream/Function) 송수신 로그 |
| EI | Equipment Interface | MCS의 장비 인터페이스 컴포넌트 군. 본 모듈에서는 EI 컴포넌트와 그 보조 컴포넌트(TS, CS, DS) 로그를 가리킴 |
| TS | Transport Service | OHT/STK 등 반송장치 인터페이스 컴포넌트 |
| CS | Carrier Service | 캐리어(FOUP) 관리 컴포넌트 |
| DS | Dispatch Service | 작업 디스패칭 컴포넌트 |

### 1.2. 서브 모듈 비교

본 모듈은 두 개의 서브 모듈로 구성된다.

| 항목 | EI (Equipment Interface) | SECS |
| --- | --- | --- |
| Controller | `EiLogController` | `SecsLogController` |
| Service | `EiService` / `EiServiceImpl` | `SecsService` / `SecsServiceImpl` |
| DAO | `EiDAO` | `SecsDAO` |
| VO | `EiVo` | `SecsVo` |
| 대상 로그 | TS · EI · CS · DS 4종 멀티 로그 | SECS 통신 로그 (S/F, SB, NAME, DATA) |
| 핵심 분기 | `logType(TS/EI/CS/DS) × fab × fabSite` 3중 분기로 테이블명 결정 | `fab × fabSite` 2중 분기로 단일 테이블 결정 |
| 화면 컬럼 | `_time, TIME_EX, FAB, LOG, LEVEL, THREAD, CLASS, TEXT, HOST, PROCESS, TEXT_XML` | `_time, TIME_EX, SECS, LEVEL, S/F, SB, NAME, DATA, TEXT, SKEY, HOST` |
| 화면 LEVEL | `WELL / WARN / ERROR / FATAL` (기본) | `TIME / INFO / WARN / RECV / SEND` (ALL 기본) |
| 보조 검색 | `PROCESS`, `TEXT` (콤마 분리 + AND/OR) | `SECS`, `TEXT` (콤마 분리 + AND/OR) |

### 1.3. 응답 패턴

모든 컨트롤러 응답은 Spring `ModelAndView` 또는 `@ResponseBody` 직렬화이며, JSON 응답 시 Bean 명이 `jsonView`인 `MappingJackson2JsonView`를 사용한다.

* **페이지 진입 응답** : `ModelAndView` + JSP 뷰명 (예: `ei/eiLogList`, `secs/secsLogList`)
* **데이터 조회(Ajax) 응답** : `jsonView` (`page`, `total`, `records`, `rows`)
* **콤보/필터(Ajax) 응답** : `jsonView` (`list` 또는 List 직접 반환)
* **쿼리 중단 응답** : `void` (HTTP 200, 본문 없음)
* **공통 예외 응답** : `ExceptionControllerAdvice` 가 가로채서 `common/error/errorPage` 뷰로 렌더링 (`name`, `message` 모델)

데이터 영속화는 MyBatis가 아니라 **Logpresso(=Araqne) 쿼리 엔진**을 통해 이루어진다.  `DBManager(fabSite).executeQuery(queryStmt)` 가 Logpresso 쿼리(`table from=... to=...`)를 실행하고 Map 리스트를 반환한다.

---

## 2. API 목록

총 10개 엔드포인트.

| # | HTTP | URL | Controller.Method | 응답 뷰 | 설명 |
| --- | --- | --- | --- | --- | --- |
| 1 | GET/POST | `ei/eiLogList` | `EiLogController.eiLocLogList` | `ei/eiLogList` (JSP) | EI 로그 조회 화면 진입 |
| 2 | GET/POST | `/ei/ajax/getEiLogList.do` | `EiLogController.getList` | `jsonView` | EI/TS/CS/DS 로그 데이터 조회 (페이징) |
| 3 | GET/POST | `tot/filter/ajax/getProcessList` | `EiLogController.getSecsList` | `@ResponseBody List<List>` | TS PROCESS 콤보 목록 (`ts*` 만) |
| 4 | GET/POST | `tot/filter/ajax/getSelectProcessList` | `EiLogController.getSecsFabList` | `jsonView` | FAB/Type 필터로 PROCESS 목록 재조회 |
| 5 | GET/POST | `ei/pop/textDetailPop` | `EiLogController.filterPop` | `ei/pop/textDetailPop` (JSP) | TEXT 상세 팝업 |
| 6 | GET/POST | `ei/pop/textAreaPop` | `EiLogController.textFilterPop` | `ei/pop/textAreaPop` (JSP) | TEXT 입력 영역 팝업 |
| 7 | GET/POST | `ei/ajax/getEiQueryStop` | `EiLogController.getEiQueryStop` | `void` | EI Logpresso 쿼리 강제 중단 |
| 8 | GET/POST | `secs/secsLogList` | `SecsLogController.secsLocLogList` | `secs/secsLogList` (JSP) | SECS 로그 조회 화면 진입 |
| 9 | GET/POST | `/secs/ajax/getsecsLogList.do` | `SecsLogController.getList` | `jsonView` | SECS 로그 데이터 조회 (페이징) |
| 10 | GET/POST | `tot/filter/ajax/getSecsList` | `SecsLogController.getSecsList` | `@ResponseBody List<List>` | SECS 장비 콤보 목록 (`machine_list`) |
| 11 | GET/POST | `tot/filter/ajax/getSecsFabList` | `SecsLogController.getSecsFabList` | `jsonView` | FAB 필터로 SECS 장비 목록 재조회 |
| 12 | GET/POST | `ei/ajax/getSecsQueryStop` | `SecsLogController.getSecsQueryStop` | `void` | SECS Logpresso 쿼리 강제 중단 **(URL이 `/ei/` prefix를 사용하는 이상치)** |

> **URL prefix 이상치**  
> `SecsLogController.getSecsQueryStop` 의 `@RequestMapping(value = "ei/ajax/getSecsQueryStop")` 는 SECS 모듈 기능임에도 불구하고 URL prefix가 `secs/` 가 아닌 `ei/` 로 되어있다. JSP 측 호출 URL과 정합성을 맞추기 위한 의도된 매핑일 수 있으나, REST 표기 규약상 일관성이 깨진 부분이다. (비고/이슈 6.2 참조)

---

## 3. 상세 API 명세

### 3.1. EI 서브모듈

---

#### 3.1.1. EI 로그 조회 화면 진입 — `ei/eiLogList`

* **Method** : `EiLogController.eiLocLogList`
* **Description** : EI/TS/CS/DS 로그 조회 화면(JSP)을 렌더링한다. 화면 초기 진입 시 fabSite를 세션에서 결정하고 fab 콤보·level 콤보의 기본값을 모델에 담는다.

##### Request
```bash
curl -X GET 'http://{HOST}/{ctx}/ei/eiLogList?fabSite=M14'
```

| Header | Value | 필수 | 비고 |
| --- | --- | --- | --- |
| Cookie | `JSESSIONID=...` | Y | Spring HttpSession 식별자 |

| Element (form/query) | Type | 필수 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | N | M14 / M15 / M11 / C2 / IC. 미전송 시 세션값 사용 |

##### Response
* **ViewName** : `ei/eiLogList`
* **Model**

| Key | Type | 설명 |
| --- | --- | --- |
| fabsites | List | `Common.FabSites` 전체 fabSite 목록 |
| fabs | List<String> | `Common.getFabList("ei", sFabSite)` 로 얻은 EI 가능 fab 목록 |
| levels | List | `Common.Levels` (전체 레벨 후보) |
| param / params | EiVo | 화면 기본값이 채워진 VO (fab=getBasicFabList, level=[WELL,WARN,ERROR,FATAL]) |

##### Error Codes
| HTTP | 상황 |
| --- | --- |
| 500 | `Common.getFabSite()` / `Common.setFabSite()` 실패. `ExceptionControllerAdvice`가 `errorPage`로 포워딩 |

---

#### 3.1.2. EI 로그 데이터 조회 — `/ei/ajax/getEiLogList.do`

* **Method** : `EiLogController.getList`
* **Description** : EI/TS/CS/DS 로그 데이터를 Logpresso에서 조회한다. `logType(TS/EI/CS/DS) × fab × fabSite` 3중 분기로 대상 테이블이 동적 결정된다.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/ei/ajax/getEiLogList.do' \
  --data 'page=1&rows=100&searchDelay=0&fabSite=M14' \
  --data 'eiFab1=ALL' \
  --data 'logType1=TS&logType2=EI&logType3=CS&logType4=DS' \
  --data 'host1=primary&host2=secondary' \
  --data 'level1=WELL&level2=WARN&level3=ERROR&level4=FATAL' \
  --data 'from=20240515000000&to=20240515235959' \
  --data 'process=ts0&text=ALARM,REPORT&eiTextConditionCheckBox=OR'
```

| Element | Type | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | String | N | "1" | 페이지 번호 (1-base) |
| rows | String | N | "100" | 한 페이지 행 수 |
| searchDelay | String | **Y** | — | 검색 지연(초). 정수 변환됨. **누락 시 `NumberFormatException` 발생** (비고 6.3) |
| fabSite | String | N | 세션값 | M14 / M15 / M11 / C2 / IC |
| eiFab1 ~ eiFabN | String | N | basic fab | `eiFab1=ALL`이면 전체 fab. 그 외 1~N 인덱스로 다중 선택 |
| logType1 ~ logType5 | String | N | (없음) | `logType1=ALL`이면 TS/EI/CS/DS 모두. 그 외 1~5 인덱스로 다중 선택 |
| host1 ~ host3 | String | N | (없음) | primary / secondary |
| level1 ~ levelN | String | N | (없음) | ALL / WELL / WARN / ERROR / FATAL / DEBUG / INFO / FINE |
| from | String | N | 현재시각-10분 | `yyyyMMddHHmmss` |
| to | String | N | 현재시각 | `yyyyMMddHHmmss` |
| process | String | N | — | PROCESS 필터(콤마 분리 시 OR 조건 자동 적용) |
| text | String | N | — | TEXT 필터 (콤마 분리 + `eiTextConditionCheckBox` 로 AND/OR) |
| eiTextConditionCheckBox | String | N | OR | TEXT 콤마 분리 시 AND/OR 선택 |

##### Response

```json
{
  "page": 1,
  "total": 10,
  "records": 12345,
  "rows": [
    {
      "No": 1,
      "_time": "2024-05-15 10:00:00",
      "TIME_EX": "2024-05-15 10:00:00.123",
      "FAB": "M14A",
      "LOG": "EI",
      "LEVEL": "WARN",
      "THREAD": "EI-Worker-3",
      "CLASS": "com.skhynix.eqp.EiHandler",
      "TEXT": "EQP timeout - retry...",
      "HOST": "primary",
      "PROCESS": "ei_m14a_0",
      "TEXT_XML": "<msg>...</msg>"
    }
  ]
}
```

| 필드 | Type | 설명 |
| --- | --- | --- |
| page | int | 현재 페이지 |
| total | int | 총 페이지 수 |
| records | int | 페이지당 레코드 수 |
| rows | List<Map> | 행 목록 |
| rows[].No | long | 페이징 오프셋 + seq() |
| rows[]._time | string | Logpresso `_time` 컬럼 (행 정렬 기준) |
| rows[].TIME_EX | string | 확장 시간(ms 포함) |
| rows[].FAB | string | FAB 식별자. TS의 경우 PROCESS 문자열로부터 case eval로 산출 |
| rows[].LOG | string | TS / EI / CS / DS. TS의 경우 case eval로 산출 |
| rows[].LEVEL | string | 로그 레벨 |
| rows[].THREAD | string | 로그 스레드 |
| rows[].CLASS | string | TS의 경우 `OPERATION_NAME` 컬럼을 `CLASS`로 eval |
| rows[].TEXT | string | 로그 본문 |
| rows[].HOST | string | primary/secondary. TS는 PROCESS가 `ts0*`이면 primary |
| rows[].PROCESS | string | TS 프로세스명 (예: `ts0_m14a`) |
| rows[].TEXT_XML | string | TS의 경우 `XML` 컬럼 alias |

##### TS 케이스 PROCESS → FAB/LOG/HOST 산출 (case eval)

TS 로그 선택 시 `PROCESS` 문자열을 검사하여 다음 컬럼을 동적으로 산출한다.

* **FAB** : `contains(PROCESS,"m11a")→"M11A"`, `m11b→M11B`, `m14a→M14A`, `m14b→M14B`, `m15→M15`, `m16a→M16A`, `m16b→M16B`, `c2→C2`, `c2f→C2F`
* **LOG** : `contains(PROCESS,"ts")→"TS"`
* **HOST** : `contains(PROCESS,"ts0")→"primary"` else `"secondary"`
* **CLASS** : `OPERATION_NAME` alias
* **TEXT_XML** : `XML` alias

##### Error Codes
| HTTP | 상황 |
| --- | --- |
| 500 | `NumberFormatException` (searchDelay/page/rows 변환 실패), Logpresso 연결 오류 등 → `ExceptionControllerAdvice` |

---

#### 3.1.3. TS PROCESS 콤보 목록 — `tot/filter/ajax/getProcessList`

* **Method** : `EiLogController.getSecsList`
* **Description** : EI 화면 진입 시 TS PROCESS 콤보를 채울 목록을 반환한다. 내부적으로 `memlookup name=ProcessList2 | sort PROCESS | search PROCESS == "ts*" | stats count by PROCESS | fields PROCESS` 를 실행.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/tot/filter/ajax/getProcessList' --data 'fabSite=M14'
```

| Element | Type | 필수 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | Y | 조회 대상 fabSite |

##### Response

`@ResponseBody List<List<Map>>` — 외곽이 1개의 List로 감싸진 형태.

```json
[
  [
    {"PROCESS": "ts0_m14a"},
    {"PROCESS": "ts0_m14b"},
    {"PROCESS": "ts1_m14a"}
  ]
]
```

##### Error Codes
| HTTP | 상황 |
| --- | --- |
| 500 | Logpresso 실행 실패 |

---

#### 3.1.4. FAB/Type 조건부 PROCESS 목록 — `tot/filter/ajax/getSelectProcessList`

* **Method** : `EiLogController.getSecsFabList`
* **Description** : 사용자가 화면에서 FAB·Type 필터를 변경했을 때 매칭되는 PROCESS 목록을 재조회한다. `MachineVo.selectType` 으로 PROCESS prefix, `MachineVo.selectFab` 으로 FAB 필터링.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/tot/filter/ajax/getSelectProcessList' \
  --data 'fabSite=M14&selectType=ts&selectFab=M14A'
```

| Element | Type | 필수 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | N | 세션값 fallback |
| selectType[] | List<String> | N | PROCESS prefix (ALL이면 무필터) |
| selectFab[] | List<String> | N | FAB 필터 (ALL이면 무필터) |

##### Response
```json
{
  "fabsites": [...],
  "list": [
    {"PROCESS": "ts0_m14a"},
    {"PROCESS": "ts1_m14a"}
  ]
}
```

---

#### 3.1.5. TEXT 상세 팝업 — `ei/pop/textDetailPop`

* **Method** : `EiLogController.filterPop`
* **Description** : 행의 TEXT(또는 TEXT_XML) 상세를 표시할 팝업 JSP 진입. 파라미터 처리 없이 뷰만 반환.

##### Request
```bash
curl -X GET 'http://{HOST}/{ctx}/ei/pop/textDetailPop'
```

##### Response — `ei/pop/textDetailPop` (JSP)

---

#### 3.1.6. TEXT 영역 입력 팝업 — `ei/pop/textAreaPop`

* **Method** : `EiLogController.textFilterPop`
* **Description** : 다중 TEXT 검색 키워드 입력용 팝업 JSP.

##### Request
```bash
curl -X GET 'http://{HOST}/{ctx}/ei/pop/textAreaPop'
```

##### Response — `ei/pop/textAreaPop` (JSP)

---

#### 3.1.7. EI 쿼리 강제 중단 — `ei/ajax/getEiQueryStop`

* **Method** : `EiLogController.getEiQueryStop`
* **Description** : EI 조회 중인 Logpresso 쿼리를 강제 중단(Emergency Stop). `eiService.getRawLogQueryStop()` → `EiDAO.dbExecuteQueryStop()` → `DBManager.executeQueryStop()` 체인.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/ei/ajax/getEiQueryStop'
```

##### Response
HTTP 200, 본문 없음 (`void` 반환).

##### Error Codes
컨트롤러는 예외를 throw하지만 서비스 내부에서 `try-catch` 후 `log.info("getRawLogQueryStop Exception!!")` 만 남기고 흡수한다.

---

### 3.2. SECS 서브모듈

---

#### 3.2.1. SECS 로그 조회 화면 진입 — `secs/secsLogList`

* **Method** : `SecsLogController.secsLocLogList`
* **Description** : SECS 로그 조회 화면(JSP) 렌더링. SECS 전용 LEVEL 콤보 (`TIME / INFO / WARN / RECV / SEND`) 및 ALL 기본 선택을 셋업.

##### Request
```bash
curl -X GET 'http://{HOST}/{ctx}/secs/secsLogList?fabSite=M14'
```

| Element | Type | 필수 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | N | M14 / M15 / M11 / C2 / IC |

##### Response

* **ViewName** : `secs/secsLogList`
* **Model**

| Key | Type | 설명 |
| --- | --- | --- |
| fabsites | List | `Common.FabSites` |
| fabs | List<String> | `Common.getFabList("secs", sFabSite)` |
| levels | List<String> | `[TIME, INFO, WARN, RECV, SEND]` 하드코딩 |
| param / params | SecsVo | fab=getBasicFabList, level=[ALL] 기본값 |

---

#### 3.2.2. SECS 로그 데이터 조회 — `/secs/ajax/getsecsLogList.do`

* **Method** : `SecsLogController.getList`
* **Description** : SECS 통신 로그(SECS-II Stream/Function 메시지)를 Logpresso에서 조회한다.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/secs/ajax/getsecsLogList.do' \
  --data 'page=1&rows=100&searchDelay=0&fabSite=M14' \
  --data 'secsFab1=ALL' \
  --data 'host1=primary&host2=secondary' \
  --data 'level1=ALL' \
  --data 'from=20240515000000&to=20240515235959' \
  --data 'secs=EQP01&text=S6F11,ALARM&secsTextConditionCheckBox=AND'
```

| Element | Type | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | String | N | "1" | |
| rows | String | N | "100" | |
| searchDelay | String | **Y** | — | 누락 시 `NumberFormatException` |
| fabSite | String | N | 세션값 | |
| secsFab1 ~ secsFabN | String | N | basic fab | `secsFab1=ALL`이면 전체 |
| host1 ~ host3 | String | N | — | primary / secondary |
| level1 ~ levelN | String | N | ALL | TIME / INFO / WARN / RECV / SEND / ALL |
| from | String | N | 현재-10분 | `yyyyMMddHHmmss` |
| to | String | N | 현재 | `yyyyMMddHHmmss` |
| secs | String | N | — | 장비명 필터 (`SECS` 컬럼, 콤마 OR) |
| text | String | N | — | TEXT 필터 (콤마 + `secsTextConditionCheckBox` AND/OR) |
| secsTextConditionCheckBox | String | N | OR | TEXT 조건 |

> **참고** : `SecsVo` 에는 carrier, vehicle, carrierLoc, commandId, transferport, sourceport, destport 필드가 존재하지만 `SecsServiceImpl.getQueryParser()` 에서 실제 쿼리에 반영되는 것은 **secs / text / level / host / fab / from / to** 만이다. 나머지 필드는 dead 상태 (비고 6.1 참조).

##### Response

```json
{
  "page": 1,
  "total": 10,
  "records": 12345,
  "rows": [
    {
      "No": 1,
      "_time": "2024-05-15 10:00:00",
      "TIME_EX": "2024-05-15 10:00:00.123",
      "SECS": "EQP01",
      "LEVEL": "RECV",
      "S/F": "S6F11",
      "SB": "0",
      "NAME": "EventReport",
      "DATA": "<L [3] ...>",
      "TEXT": "EVENT_ID=1001",
      "SKEY": "abc123",
      "HOST": "primary"
    }
  ]
}
```

| 필드 | Type | 설명 |
| --- | --- | --- |
| rows[]._time | string | Logpresso 행 시각 |
| rows[].TIME_EX | string | 확장 시간 |
| rows[].SECS | string | 장비명 (=`MACHINENAME`) |
| rows[].LEVEL | string | TIME / INFO / WARN / RECV / SEND |
| rows[]."S/F" | string | SECS-II Stream/Function (예: S6F11) |
| rows[].SB | string | Send/Body 식별 |
| rows[].NAME | string | 메시지 이름 |
| rows[].DATA | string | 메시지 본문 |
| rows[].TEXT | string | 로그 텍스트 |
| rows[].SKEY | string | Session/Sequence Key |
| rows[].HOST | string | primary / secondary |

##### Error Codes
| HTTP | 상황 |
| --- | --- |
| 500 | `NumberFormatException`(searchDelay 누락 등), Logpresso 오류 |

---

#### 3.2.3. SECS 장비 콤보 목록 — `tot/filter/ajax/getSecsList`

* **Method** : `SecsLogController.getSecsList`
* **Description** : SECS 화면 초기 진입 시 장비명 콤보용 목록. `memlookup name=machine_list | search isnotnull(MACHINETYPE) | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII` 실행.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/tot/filter/ajax/getSecsList' --data 'fabSite=M14'
```

| Element | Type | 필수 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | Y | |

##### Response

`@ResponseBody List<List<Map>>` (외곽 List 1개).

```json
[
  [
    {"FAB": "M14A", "SECSII": "EQP01"},
    {"FAB": "M14A", "SECSII": "EQP02"}
  ]
]
```

---

#### 3.2.4. FAB 조건부 SECS 장비 목록 — `tot/filter/ajax/getSecsFabList`

* **Method** : `SecsLogController.getSecsFabList`
* **Description** : 화면에서 FAB 필터 변경 시 매칭되는 장비 목록 재조회. `MachineVo.selectFab` 만 사용 (selectType은 미사용).

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/tot/filter/ajax/getSecsFabList' \
  --data 'fabSite=M14&selectFab=M14A'
```

##### Response
```json
{
  "fabsites": [...],
  "list": [
    {"FAB": "M14A", "SECSII": "EQP01"}
  ]
}
```

---

#### 3.2.5. SECS 쿼리 강제 중단 — `ei/ajax/getSecsQueryStop`

* **Method** : `SecsLogController.getSecsQueryStop`
* **Description** : SECS 조회 중인 Logpresso 쿼리를 강제 중단.
* **URL 이상치** : `@RequestMapping(value = "ei/ajax/getSecsQueryStop")` — SECS 기능이지만 URL prefix가 `ei/` 로 시작된다. 모듈 분리 규약과 어긋남.

##### Request
```bash
curl -X POST 'http://{HOST}/{ctx}/ei/ajax/getSecsQueryStop'
```

##### Response
HTTP 200, 본문 없음.

##### Error Codes
서비스 내부에서 catch 후 흡수.

---

## 4. 자원 모델

### 4.1. VO 필드 비교

| 카테고리 | EiVo | SecsVo |
| --- | --- | --- |
| 세션 | fabSite | fabSite |
| 페이징 | pageNum, rowNum | pageNum, rowNum |
| FAB | fab : List<String> | fab : List<String> |
| LEVEL | level : List<String> | level : List<String> |
| HOST | host : List<String> | host : List<String> |
| 로그 종류 | log : List<String> (TS/EI/CS/DS) | — |
| 검색-키 | process : String | secs : String |
| 검색-텍스트 | text, eiTextConditionCheckBox | text, secsTextConditionCheckBox |
| (미사용 dead) | — | carrier, vehicle, carrierLoc, commandId, transferport, sourceport, destport |
| 시간 | from, to (yyyyMMddHHmmss) | from, to (yyyyMMddHHmmss) |

### 4.2. EiVo 필드 표

| 필드 | Type | 설명 |
| --- | --- | --- |
| fabSite | String | M14/M15/M11/C2/IC. 세션과 동기화 |
| pageNum | String | 페이지 번호 (1-base) |
| rowNum | String | 페이지당 행 수 |
| fab | List<String> | FAB 다중 선택 |
| level | List<String> | LEVEL 다중 선택 (ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL) |
| host | List<String> | primary/secondary |
| log | List<String> | TS/EI/CS/DS (로그 종류 다중) |
| process | String | PROCESS 검색 (콤마 분리 시 OR) |
| text | String | TEXT 검색 (콤마 + 조건) |
| eiTextConditionCheckBox | String | TEXT AND/OR 선택 |
| from | String | `yyyyMMddHHmmss` |
| to | String | `yyyyMMddHHmmss` |

### 4.3. SecsVo 필드 표

| 필드 | Type | 사용여부 | 설명 |
| --- | --- | --- | --- |
| fabSite | String | 사용 | 세션과 동기화 |
| pageNum | String | 사용 | 페이지 번호 |
| rowNum | String | 사용 | 페이지당 행 수 |
| fab | List<String> | 사용 | FAB 다중 선택 |
| level | List<String> | 사용 | TIME/INFO/WARN/RECV/SEND/ALL |
| host | List<String> | 사용 | primary/secondary |
| secs | String | 사용 | 장비명 검색 (콤마 OR) |
| text | String | 사용 | TEXT 검색 (콤마 + 조건) |
| secsTextConditionCheckBox | String | 사용 | TEXT AND/OR |
| from | String | 사용 | `yyyyMMddHHmmss` |
| to | String | 사용 | `yyyyMMddHHmmss` |
| carrier | String | **dead** | VO에는 있으나 쿼리 미반영 |
| vehicle | String | **dead** | VO에는 있으나 쿼리 미반영 |
| carrierLoc | String | **dead** | VO에는 있으나 쿼리 미반영 |
| commandId | String | **dead** | VO에는 있으나 쿼리 미반영 |
| transferport | String | **dead** | VO에는 있으나 쿼리 미반영 |
| sourceport | String | **dead** | VO에는 있으나 쿼리 미반영 |
| destport | String | **dead** | VO에는 있으나 쿼리 미반영 |

### 4.4. Logpresso 대상 테이블 — logType별 분기

`EiServiceImpl.getTableSelect(fabSite, fab, logType, isAll)` 가 logType × fabSite × fab 3중 분기로 테이블명을 결정한다. `isAll` 은 LEVEL이 ALL/INFO/FINE/DEBUG 중 하나라도 포함되는지 여부.

#### 4.4.1. TS 로그 (`getTSTableFromFab`)

| fabSite | fab | isAll=true (전체) | isAll=false (요약 view) |
| --- | --- | --- | --- |
| M14 | (무관) | `sTS_DATA_M14A, sTS_DATA_M14B` | `sTS_DATA_VIEW_M14A, sTS_DATA_VIEW_M14B` |
| M15 | M15A | `sTS_DATA_M15A` | `sTS_DATA_VIEW_M15A` |
| M15 | (그 외) | `sTS_DATA_M15B` | `sTS_DATA_VIEW_M15B` |
| M11 | M11A | `sTS_DATA_M11A` | `sTS_DATA_VIEW_M11A` |
| M11 | (그 외) | `sTS_DATA_M11B` | `sTS_DATA_VIEW_M11B` |
| C2 | C2 | `sTS_DATA_C2` | `sTS_DATA_VIEW_C2` |
| C2 | (그 외) | `sTS_DATA_C2F` | `sTS_DATA_VIEW_C2F` |
| IC | M14A | `sTS_DATA_M14A` | `sTS_DATA_VIEW_M14A` |
| IC | M14B | `sTS_DATA_M14B` | `sTS_DATA_VIEW_M14B` |
| IC | M16A | `sTS_DATA_M16A` | `sTS_DATA_VIEW_M16A` |
| IC | M16B | `sTS_DATA_M16B` | `sTS_DATA_VIEW_M16B` |

#### 4.4.2. EI 로그 (`getEITableFromFab`)

| fabSite | fab | Table |
| --- | --- | --- |
| M14 | (무관) | `sEI_DATA` |
| M15 | M15A | `sEI_DATA_M15A` |
| M15 | (그 외) | `sEI_DATA_M15B` |
| M11 | M11A | `sEI_DATA_M11A` |
| M11 | (그 외) | `sEI_DATA_M11B` |
| C2 | C2 | `sEI_DATA_C2` |
| C2 | (그 외) | `sEI_DATA_C2F` |
| IC | M14A | `sEI_DATA` |
| IC | M16A | `sEI_DATA_M16A` |
| IC | M16B | `sEI_DATA_M16B` |

#### 4.4.3. CS 로그 (`getCSTableFromFab`)

| fabSite | fab | Table |
| --- | --- | --- |
| M14 | (무관) | `sCS_DATA` |
| M15 | M15A | `sCS_DATA_M15A` |
| M15 | (그 외) | `sCS_DATA_M15B` |
| M11 | M11A | `sCS_DATA_M11A` |
| M11 | (그 외) | `sCS_DATA_M11B` |
| C2 | C2 | `sCS_DATA_C2` |
| C2 | (그 외) | `sCS_DATA_C2F` |
| IC | M14A | `sCS_DATA` |
| IC | M16A | `sCS_DATA_M16A` |
| IC | M16B | `sCS_DATA_M16B` |

#### 4.4.4. DS 로그 (`getDSTableFromFab`)

| fabSite | fab | Table |
| --- | --- | --- |
| M14 | (무관) | `sDS_DATA` |
| M15 | M15A | `sDS_DATA_M15A` |
| M15 | (그 외) | `sDS_DATA_M15B` |
| M11 | M11A | `sDS_DATA_M11A` |
| M11 | (그 외) | `sDS_DATA_M11B` |
| C2 | C2 | `sDS_DATA_C2` |
| C2 | (그 외) | `sDS_DATA_C2F` |
| IC | M14A | `sDS_DATA` |
| IC | M16A | `sDS_DATA_M16A` |
| IC | M16B | `sDS_DATA_M16B` |

#### 4.4.5. SECS 로그 (`SecsServiceImpl.getTableFromFab`)

| fabSite | fab | Table |
| --- | --- | --- |
| M14 | (무관) | `sSECS_DATA` |
| M15 | M15A | `sSECS_DATA_M15A` |
| M15 | M15B | `sSECS_DATA_M15B` |
| M11 | M11A | `sSECS_DATA_M11A` |
| M11 | M11B | `sSECS_DATA_M11B` |
| C2 | C2 | `sSECS_DATA_C2` |
| C2 | C2F | `sSECS_DATA_C2F` |
| IC | M14A | `sSECS_DATA` |
| IC | M14B | `sSECS_DATA_M14B` |
| IC | M16A | `sSECS_DATA_M16A` |
| IC | M16B | `sSECS_DATA_M16B` |

### 4.5. 출력 컬럼

#### EI 출력 (TS/EI/CS/DS 공통)
`_time, TIME_EX, FAB, LOG, LEVEL, THREAD, CLASS, TEXT, HOST, PROCESS, TEXT_XML`

#### SECS 출력
`_time, TIME_EX, SECS, LEVEL, S/F, SB, NAME, DATA, TEXT, SKEY, HOST`

---

## 5. 인증 및 권한

* **세션 인증** : 모든 엔드포인트는 Spring `HttpServletRequest` 의 세션을 통해 `fabSite` 를 식별/주입한다 (`Common.getFabSite(request)`, `Common.setFabSite(request, fabSite)`).
* **fabSite 권한** : 사용자가 접근 가능한 fabSite는 세션에 기록되며, 요청 파라미터의 `fabSite` 값이 우선되지만 결과적으로 세션과 동기화된다.
* **로그인 게이트** : 본 모듈 컨트롤러 자체에는 별도 `@Secured` / 인터셉터 어노테이션이 없다. 인증/인가는 전역 Spring Security 또는 인터셉터 (별도 모듈) 가 담당한다. (본 모듈 소스에서는 확인 불가.)
* **DBManager 접속 정보** : `new DBManager(fabSite)` 가 fabSite별 Logpresso 접속을 결정하므로, fabSite 가 권한적 isolation 역할을 일부 담당한다.

---

## 6. 비고 및 이슈

### 6.1. SecsVo 의 dead 필드
`SecsVo` 에는 `carrier`, `vehicle`, `carrierLoc`, `commandId`, `transferport`, `sourceport`, `destport` 7개 필드가 정의되어 있으나 `SecsServiceImpl.getQueryParser()` 에서 **단 한 번도 참조되지 않는다**. 과거 화면에 노출되었으나 현재는 제거된 검색조건으로 추정. VO 정리 또는 검색 로직 복원이 필요.

### 6.2. URL prefix 와 모듈 불일치
* `SecsLogController.getSecsQueryStop` 의 `@RequestMapping` 은 `ei/ajax/getSecsQueryStop` 로 매핑되어 있다. SECS 모듈 기능임에도 URL은 `/ei/` 로 시작한다.
* JSP 측 호출 URL과 정합성을 맞추기 위한 의도된 매핑일 수 있으나, 모듈 분리 규약·REST 표기 일관성 측면에서 `secs/ajax/getSecsQueryStop` 으로 정정하거나 alias 매핑을 추가하는 것이 바람직하다.

### 6.3. `searchDelay` 미전송 시 NumberFormatException
* `EiLogController.getList` 와 `SecsLogController.getList` 양쪽 모두 `Integer.parseInt(request.getParameter("searchDelay"))` 를 **null-check 없이** 호출한다.
* `searchDelay` 가 누락되면 `null` → `NumberFormatException` 이 발생하여 `ExceptionControllerAdvice` 가 `errorPage` 로 포워딩한다.
* 클라이언트(JSP)는 항상 `searchDelay` 를 0 이상으로 전송해야 한다. 향후 null/빈문자열 가드를 추가하는 것이 권장.

### 6.4. `eiLogList` 의 `fabs` 와 `EiVo.log`(TS) 매핑 의존
* EI 화면은 TS PROCESS 콤보(`getProcessList`)를 별도로 호출하여 채운다.
* TS의 `FAB/LOG/HOST` 컬럼이 원본 테이블에 존재하지 않고 PROCESS 문자열의 case eval로 산출되므로, **PROCESS 명명 규칙이 깨지면 FAB 분류가 누락**될 수 있다. (예: m11a/m11b/m14a/m14b/m15/m16a/m16b/c2/c2f 외 prefix가 등장하면 FAB가 빈 값)
* IC fabSite 의 일부 fab 조합(예: IC + M14B, IC + M15A 등)은 `getTSTableFromFab` 의 switch 분기에서 default fallthrough로 빈 문자열(`Common.sEmpty`) 을 반환할 수 있다 — switch case 의 break 누락 + fallthrough 처리 검토 필요.

### 6.5. 쿼리 Cancel 가시성 부족
* `EiServiceImpl.getRawLogQueryStop` / `SecsServiceImpl.getRawLogQueryStop` 은 예외를 catch 후 `log.info("getRawLogQueryStop Exception!!")` 만 출력하고 흡수한다.
* 컨트롤러 응답은 항상 HTTP 200 이며 클라이언트는 취소 실패를 감지할 수 없다.

### 6.6. 페이징 카운트
* 페이징의 총 레코드 수는 `Paging.nTotalCount` (static 필드) 에서 가져오며, 이는 Logpresso 쿼리 실행 시 DBManager가 채워주는 외부 상태값이다. 동시 요청 환경에서 race condition 위험이 있다.

### 6.7. `Common.searchDelayTime` 전역 mutate
* `if(delayTime > 0) { Common.searchDelayTime = delayTime * 1000; }` 코드가 **사용자 요청 파라미터로 전역 static 변수를 변경**한다. 한 사용자의 검색 지연 설정이 동시 사용자 전체에 영향을 준다 (멀티 테넌시/동시성 결함).

### 6.8. Common.sFAB_SITE 주석 처리 흔적
* 코드 곳곳에 `Common.sFAB_SITE` 를 사용하던 옛 분기가 주석 처리되어 있고, 2022.06.15. fabSite 세션 기반 분기로 전환되었다. 잔존 주석은 가독성을 해치므로 정리 권장.

---
