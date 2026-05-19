# 06. tot(Total / 통합 모니터링·분석) 모듈 API 명세서

> 본 문서는 SK hynix MCS Log 조회 시스템의 **tot 모듈** REST/AJAX API 명세서다. tot 모듈은 시스템 전체에서 가장 큰 모듈로, 통합 로그 조회 / 분석 대시보드 / 모니터 / 팝업 / 필터 ajax / 신규(Carrier 흐름) 로그 조회를 한 데 묶어 제공한다.
>
> - 패키지: `com.skhynix.supply.tot`
> - 컨트롤러: `TotalController`, `TotalNewController`
> - 서비스: `TotalService` (인터페이스) / `TotalServiceImpl`(@Service `totalService`) / `TotalNewServiceImpl`(@Service `totalNewService`)
> - DAO: `TotalDAO`(@Repository `totalDAO`) → `DBManager.executeQuery()`
> - VO: `TotalVo`, `TotalNewVo`
> - 외부 의존: Logpresso(파이프라인 검색엔진) `memlookup`, `table`, `search`, `stats`, `fields`, `sort`, `limit`, `eval`, `proc` 등
> - 공통 예외: `com.skhynix.supply.common.error.ExceptionControllerAdvice`

---

## 1. API 개요

### 1.1 모듈 개요

tot 모듈은 다음 카테고리의 엔드포인트를 제공한다.

1. **Total(통합) 로그 조회** — `tot/totalLogList`, `tot/ajax/getTotalLogList`, `tot/ajax/getTotalLogListStop`
2. **TotalNew(Carrier 흐름 분석) 로그 조회** — `totNew/totalNewLogList`, `totNew/ajax/totalNewLogList`, `totNew/ajax/getCarrierElapsed`
3. **대시보드/분석 화면** — `tot/dashboard/elapsedAnalysis`, `tot/dashboard/compressAnalysis`, `tot/dashboard/monitor`, `tot/dashboard/elapsed3`
4. **팝업** — `tot/pop/machineNamePop`, `tot/pop/filterPop`, `totNew/pop/machineNamePop`, `common/pop/settingPop`
5. **필터 ajax(@ResponseBody, 6종)** — Area/Bay/MachineName/CommMsg/Message/Operation 리스트
6. **데이터 조회 ajax** — Machine/Bay/Area/MachineType/Fab 동적 목록
7. **메인/엔트리** — `tot/main`, `tot/{query}` catch-all, view-controller(`tot/main`, `tot/index`)

### 1.2 Total vs TotalNew 차이

| 항목 | Total | TotalNew |
|---|---|---|
| 컨트롤러 | `TotalController` | `TotalNewController` |
| 서비스 빈 | `totalService` (`TotalServiceImpl`) | `totalNewService` (`TotalNewServiceImpl`) |
| VO | `TotalVo` | `TotalNewVo` |
| 주 검색 단위 | 로그 라인 (process/thread/gtxnId/transactionId/messageName/commMsg/operationName/carrier/commandId/unit/text/fulltext/key) | Carrier(반송체) 흐름·완료 |
| 핵심 쿼리 | `table FROM TO ... | fields ... | search level in(...)` 혹은 fulltext `search` | `proc COMPLETED_CARRIER_FROM_TO[_CARRIER]` + machineType `search in` |
| Detail | `getDetailDataList` 미구현(null 반환) | `getDetailDataList`로 `addQuery` 그대로 DB 실행 |
| 인터페이스 공유 | 동일한 `TotalService`를 구현. `TotalNewServiceImpl`은 대부분 메서드를 `return null` 더미로 둠 |

### 1.3 응답 형식

| 형식 | 사용처 |
|---|---|
| `jsonView` (Spring `MappingJackson2JsonView`) | ajax 엔드포인트 대부분. `mav.addObject("list"|"rows"|"page"|"total"|"records", …)` 후 jsonView 렌더 → JSON |
| `@ResponseBody List<List>` | `tot/filter/ajax/get*` 6종 (직렬화) |
| Tiles/JSP 뷰 | 화면 진입(`tot/totalLogList`, `tot/main`, dashboard, popup) |
| `void @ResponseBody` | `tot/ajax/getTotalLogListStop` (HTTP 200, body 없음) |

### 1.4 공통 HTTP 메서드

모든 `@RequestMapping`은 method 미지정 → **GET/POST 모두 허용**. 예외: `tot/{query}`는 `method=RequestMethod.GET`로 명시.

### 1.5 공통 에러 응답

`ExceptionControllerAdvice`(@ControllerAdvice)가 모든 `Exception`을 가로채 `common/error/errorPage` JSP로 포워딩한다.

```java
mav.addObject("name", e.getClass().getSimpleName());
mav.addObject("message", e.getMessage());
mav.setViewName("common/error/errorPage");
```

ajax 호출의 경우 JSON 대신 errorPage HTML이 반환되므로 클라이언트 측에서 응답 Content-Type 검사 필요.

---

## 2. API 목록 (전체 28건)

| # | URL | HTTP | Controller#Method | 응답 | 카테고리 |
|---|---|---|---|---|---|
| 1 | `tot/totalLogList` | GET/POST | TotalController#totalLogList | `tot/totalLogList` JSP | 화면진입 |
| 2 | `tot/ajax/getTotalLogList` | GET/POST | TotalController#getTotalLogList | jsonView(jqGrid) | ajax(조회) |
| 3 | `tot/ajax/getTotalLogListStop` | GET/POST | TotalController#getTotalLogListStop | void(@ResponseBody) | ajax(제어) |
| 4 | `tot/pop/machineNamePop` | GET/POST | TotalController#machineNamePop | `tot/pop/machineNamePop` JSP | 팝업 |
| 5 | `tot/ajax/getMachineList` | GET/POST | TotalController#getMachineList | jsonView | ajax(목록) |
| 6 | `tot/ajax/getMachineListMachineTypeNotNull` | GET/POST | TotalController#getMachineListMachineTypeNotNull | jsonView | ajax(목록) |
| 7 | `tot/ajax/getBayFromArea` | GET/POST | TotalController#getBayFromArea | jsonView | ajax(목록) |
| 8 | `tot/ajax/getAreaFromFab` | GET/POST | TotalController#getAreaFromFab | jsonView | ajax(목록) |
| 9 | `tot/ajax/getMachineTypeFromFab` | GET/POST | TotalController#getMachineTypeFromFab | jsonView | ajax(목록) |
| 10 | `tot/ajax/getFabFromFabSite` | GET/POST | TotalController#getFabFromFabSite | jsonView | ajax(목록) |
| 11 | `tot/main` | GET/POST | TotalController#main | `tot/main` JSP | 화면진입 |
| 12 | `tot/{query}` (catch-all) | **GET only** | TotalController#getRequest | `tot/main` JSP | 화면진입(폴백) |
| 13 | `tot/filter/ajax/getAreaList` | GET/POST | TotalController#getAreaList | @ResponseBody List<List> | 필터ajax |
| 14 | `tot/filter/ajax/getBayList` | GET/POST | TotalController#getBayList | @ResponseBody List<List> | 필터ajax |
| 15 | `tot/filter/ajax/getMachineNameList` | GET/POST | TotalController#getMachineNameList | @ResponseBody List<List> | 필터ajax |
| 16 | `tot/filter/ajax/getCommMsgNameList` | GET/POST | TotalController#getCommMsgNameList | @ResponseBody List<List> | 필터ajax |
| 17 | `tot/filter/ajax/getMessageNameList` | GET/POST | TotalController#getMessageNameList | @ResponseBody List<List> | 필터ajax |
| 18 | `tot/filter/ajax/getOperationNameList` | GET/POST | TotalController#getOperationNameList | @ResponseBody List<List> | 필터ajax |
| 19 | `tot/pop/filterPop` | GET/POST | TotalController#filterPop | `tot/pop/filterPop` JSP | 팝업 |
| 20 | `common/pop/settingPop` | GET/POST | TotalController#settingPop | `common/pop/settingPop` JSP | 팝업 |
| 21 | `tot/dashboard/elapsedAnalysis` | GET/POST | TotalController#elapsed | `tot/elapsedAnalysis` JSP | 대시보드 |
| 22 | `tot/dashboard/compressAnalysis` | GET/POST | TotalController#elapsed2 | `tot/compressAnalysis` JSP | 대시보드 |
| 23 | `tot/dashboard/monitor` | GET/POST | TotalController#monitor | `tot/monitor` JSP | 대시보드 |
| 24 | `tot/dashboard/elapsed3` | GET/POST | TotalController#elapsed3 | `tot/dashboard3` JSP | 대시보드 |
| 25 | `totNew/totalNewLogList` | GET/POST | TotalNewController#totalNewLogList | `tot/totalNewLogList` JSP | 화면진입 |
| 26 | `totNew/ajax/totalNewLogList` | GET/POST | TotalNewController#totalNewLogListAjax | jsonView | ajax(조회) |
| 27 | `totNew/pop/machineNamePop` | GET/POST | TotalNewController#machineNamePop | `tot/pop/machineNamePop` JSP | 팝업 |
| 28 | `totNew/ajax/getCarrierElapsed` | GET/POST | TotalNewController#getCarrierElapsed | jsonView | ajax(조회/Detail) |

**view-controller (Spring MVC `<view-controller>` 직접 매핑, 컨트롤러 코드 없음)**

| # | URL | View name | 비고 |
|---|---|---|---|
| V1 | `tot/main` | `main` | `servlet-context.xml` `<view-controller path="tot/main" view-name="main" />` — TotalController#main과 경로 충돌 시 컨트롤러가 우선. tiles 뷰 `main` 직접 렌더 백업 경로. |
| V2 | `tot/index` | `index` | `<view-controller path="tot/index" view-name="index" />` — 별도 컨트롤러 없음. tiles 뷰 `index` 렌더. |

---

## 3. 상세 API 명세

각 엔드포인트별로 Request / Response / Error / Example을 기술한다.

---

### 3.1 화면 진입 / 대시보드 / 메인

#### 3.1.1 `tot/totalLogList` — 통합 로그 조회 화면 진입

- **Method**: GET/POST
- **Controller**: `TotalController#totalLogList(@ModelAttribute TotalVo param, HttpServletRequest request)`
- **View**: `tot/totalLogList` (Tiles 또는 InternalResourceViewResolver → `/WEB-INF/views/tot/totalLogList.jsp`)

**Request Parameters** (모두 optional; `TotalVo`에 바인딩)

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `fabSite` | string | 세션값(`Common.getFabSite(request)`) | 비어있으면 세션값 사용, 값이 있으면 `Common.setFabSite(request, …)`로 세션 갱신 |
| 그 외 `TotalVo` 필드 전체 | - | - | 화면 재진입 시 폼 복원용 |

**서버 측 기본값 설정**
- `mav.addObject("fabsites", Common.FabSites)` — 사이트 목록
- `param.setFab(Common.getBasicFabList("tot", sFabSite))` — 기본 FAB 자동 체크
- `param.setLevel(["WELL","WARN","ERROR","FATAL"])` — 기본 4개 레벨

**Response (Model)**
- `fabsites: List<String>`
- `fabs: List<String>`
- `levels: List<String>` (`Common.Levels`)
- `param: TotalVo`
- `params: TotalVo` (동일 객체, JSP 호환)

**Error**: `ExceptionControllerAdvice` → `common/error/errorPage`

**Example**
```
GET /tot/totalLogList?fabSite=M14
```

---

#### 3.1.2 `tot/main` — 메인 페이지

- **Method**: GET/POST
- **Controller**: `TotalController#main`
- **View**: `tot/main`

**Request**: `TotalVo`(fabSite만 사용), `HttpServletRequest`(세션·Locale 로깅 목적)

**Model**
- `fabsites`: `Common.FabSites`
- `param`: 입력 그대로
- `location`: `Common.getLocale().toString()`

**Example**
```
GET /tot/main
```

---

#### 3.1.3 `tot/{query}` — 동적 경로 catch-all (GET only)

- **Method**: **GET** (명시적)
- **Controller**: `TotalController#getRequest(@ModelAttribute TotalVo param, @PathVariable String query, HttpServletRequest request)`
- **View**: `tot/main` (모든 path variable에 대해 main 뷰로 폴백)

**Request**
- `@PathVariable String query` — `tot/xxx` 의 `xxx` 부분(로깅 외 미사용)
- `fabSite` — 동일 세션 처리

**Model**: `fabsites`, `param`, `location`

**부작용**: 본 매핑이 흡수하는 URL 범위가 광범위함. `tot/anything-not-mapped`에 GET 요청이 들어오면 `tot/main`이 렌더된다. 보안·라우팅 측면 위험: 비고 6장 참조.

**Example**
```
GET /tot/whateverPath        → tot/main 렌더
GET /tot/totalLogList        → 위 3.1.1 우선(더 구체적 매핑)
```

---

#### 3.1.4 `tot/dashboard/elapsedAnalysis` — Elapsed 분석

- Controller: `TotalController#elapsed`
- View: `tot/elapsedAnalysis`
- Request: `TotalVo`(미사용)
- Model: 없음 (뷰 단순 진입)

#### 3.1.5 `tot/dashboard/compressAnalysis` — Compress 분석

- Controller: `TotalController#elapsed2`
- View: `tot/compressAnalysis`
- Model: 없음

#### 3.1.6 `tot/dashboard/monitor` — 모니터 화면

- Controller: `TotalController#monitor`
- View: `tot/monitor`
- Model: 없음

#### 3.1.7 `tot/dashboard/elapsed3` — Dashboard3 화면

- Controller: `TotalController#elapsed3`
- View: `tot/dashboard3`
- Model: 없음

---

### 3.2 Total 로그 조회 ajax

#### 3.2.1 `tot/ajax/getTotalLogList` — 통합 로그 조회 결과

- **Method**: GET/POST
- **Controller**: `TotalController#getTotalLogList`
- **View**: `jsonView` (jqGrid 형식)

**Request Parameters**

| 파라미터 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `searchDelay` | int | (필수, `Integer.parseInt` — null이면 NPE) | 초 단위. `>0`이면 `Common.searchDelayTime = delayTime * 1000` **정적 필드 갱신** |
| `page` | string | `"1"` | jqGrid 현재 페이지 |
| `rows` | string | `"100"` | 페이지당 행수 |
| `fabSite` | string | 세션 | 동일 처리 |
| `fab1`…`fabN` | string | - | `fab1=ALL`이면 전체 FAB. 그 외 `fab1, fab2 …`를 누적해 `param.setFab(...)` |
| `level1`…`levelN` | string | - | `Common.Levels.size()+1`까지 반복 수집. `ALL` 단일 처리 없이 그대로 누적 |
| `machineTypes` | csv string | - | 콤마 split. 첫 토큰이 `ALL`이면 빈 리스트(=조건 없음) |
| `areaName` | string | `"ALL"` | 빈값이면 `ALL` |
| `bayName` | string | `"ALL"` | 빈값이면 `ALL` |
| `from` | yyyyMMddHHmmss | 현재시각−10분 | |
| `to` | yyyyMMddHHmmss | 현재시각 | |
| TotalVo 나머지 필드 | - | - | `@ModelAttribute` 바인딩 (process/thread/gtxnId/transactionId/messageName/comMsgName/operationName/carrier/commandId/unit/text/fulltext/searchOption 등) |

**처리**
1. 페이징·필터 파라미터 정규화
2. `totService.getDataList(TotalVo)` 호출 → 내부에서 `getQueryParser()`로 Logpresso 쿼리 생성
3. 결과 List 크기 > 0이면 `Paging.nTotalCount`(정적 필드) 사용해 페이지 정보 생성

**Response (jsonView)**
```json
{
  "page": 1,
  "total": <total page count>,
  "records": <records per page>,
  "rows": [
    { "_TIME": "...", "MACHINENAME": "...", "LEVEL": "...", "TEXT": "...", "No": 1, ... },
    ...
  ]
}
```

`rows`의 각 row 필드 (Logpresso `fields`로 명시되는 컬럼):
`_TIME, TIME_EX, MACHINENAME, MACHINETYPE, UNIT, CARRIER, COMMANDID, COMMAND, OPERATIONNAME, MESSAGENAME, PROCESS, TRANSACTIONID, TEXT, THREADNAME, [KEY,] LEVEL, XML, SECS, RESULTCODE, No`

**Error**
- `searchDelay` 미전송 → `NumberFormatException` → errorPage
- Logpresso 쿼리 오류 → `DBManager.executeQuery` 내부에서 잡힘 → `dataList=null` → 빈 응답

**Example**
```
POST /tot/ajax/getTotalLogList
  page=1&rows=100&searchDelay=0&fabSite=M14
  &fab1=M14A&level1=WARN&level2=ERROR
  &machineTypes=STOCKER,OHT
  &from=20260101000000&to=20260101010000
  &carrier=ABC1234
```

---

#### 3.2.2 `tot/ajax/getTotalLogListStop` — 진행 조회 중지

- **Method**: GET/POST
- **Controller**: `TotalController#getTotalLogListStop`
- **Response**: `void @ResponseBody` (HTTP 200, body 없음)
- **처리**: `totService.getTotalLogListStop()` → `DBManager.executeQueryStop()` 호출

**Error**: 내부 예외는 서비스단에서 로그만 남기고 무시.

**Example**
```
GET /tot/ajax/getTotalLogListStop
```

---

### 3.3 데이터 조회 ajax (Machine/Area/Bay/Type/Fab)

#### 3.3.1 `tot/ajax/getMachineList` — Machine 목록

- **Controller**: `TotalController#getMachineList(@ModelAttribute MachineVo param, request)`
- **Response**: jsonView, `{ "list": [ { "MACHINENAME": "..." }, ... ], "fabsites": [...] }`
- **서비스**: `TotalServiceImpl.getMachineNameList(MachineVo)`
  - Logpresso: `memlookup name=machine_list | search in(SHOPNAME, ...) | search in(TYPE, ...) | search AREANAME="..." | search BAYNAME="..." | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME`
- **MachineVo 주요 파라미터**: `fabSite`, `selectFab[]`, `machineType[]`, `areaName`, `bayName`

#### 3.3.2 `tot/ajax/getMachineListMachineTypeNotNull`

- 동일하되 `isnotnull(MACHINETYPE)` 조건이 추가됨
- 서비스: `getMachineNameListMachineTypeNotNull(MachineVo)` → `getMachineQueryParserMachineTypeNotNull`

#### 3.3.3 `tot/ajax/getBayFromArea` — Area → Bay

- 서비스: `getBayFromAreaList(MachineVo)` → `getAreaBayQueryParser`
- 쿼리: `memlookup name=machine_list | search in(SHOPNAME, ...) | search AREANAME="..." |  | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1`
- Response: `{ "list": [ {"BAYNAME": "..."}, ... ] }`

#### 3.3.4 `tot/ajax/getAreaFromFab` — Fab → Area

- 서비스: `getAreaFromFabList(MachineVo)` → `getAreaBayQueryParser` (areaName 없음 분기)
- 쿼리: `memlookup name=machine_list | search in(SHOPNAME, ...) |  | stats count by AREANAME | fields AREANAME | sort AREANAME | search len(AREANAME) > 1`
- Response: `{ "list": [ {"AREANAME": "..."}, ... ] }`

#### 3.3.5 `tot/ajax/getMachineTypeFromFab` — Fab → MachineType

- 서비스: `getMachineTypeFromFab(MachineVo)`
- 쿼리: `memlookup name=machine_list | search in(SHOPNAME, ...) | stats count by TYPE | sort TYPE`
- Response: `{ "list": [ {"TYPE": "..."}, ... ] }`

#### 3.3.6 `tot/ajax/getFabFromFabSite` — FabSite → Fab

- **Controller**: `TotalController#getFabFromFabSite(@ModelAttribute FabVo param, request)`
- **Request**: `FabVo.fabSite`, `FabVo.menu`
- **Response**: jsonView,
  ```json
  {
    "list": ["M14A","M14B", ...],      // Common.getFabList(menu, fabSite)
    "basic_list": ["M14A", ...]         // Common.getBasicFabList(menu, fabSite)
  }
  ```

**Common 헬퍼**: 서비스 호출 없이 `Common`의 정적 메서드만 사용.

---

### 3.4 필터 ajax 6종 (`@ResponseBody List<List>`)

> 6건 모두 동일한 구조: 단일 `String fabSite` 파라미터, 서비스 호출 후 결과를 `List<List>`에 한 번 wrap해 JSON 반환.

| 엔드포인트 | 서비스 메서드 | Logpresso 쿼리 | 컬럼 |
|---|---|---|---|
| `tot/filter/ajax/getAreaList` | `getAreaNameList(String fabSite)` | `memlookup name=machine_list | stats count by AREANAME | fields AREANAME | search len(AREANAME) > 1` | AREANAME |
| `tot/filter/ajax/getBayList` | `getBayNameList(String fabSite)` | `memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1` | BAYNAME |
| `tot/filter/ajax/getMachineNameList` | `getMachineNameList(String fabSite)` | `memlookup name=machine_list | search len(MACHINENAME) > 1 | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME` | MACHINENAME |
| `tot/filter/ajax/getCommMsgNameList` | `getCommMsgNameList(String fabSite)` | `memlookup name=comm_msg_name | sort COMM_MSG` | COMM_MSG |
| `tot/filter/ajax/getMessageNameList` | `getMessageNameList(String fabSite)` | `memlookup name=message_name | sort MESSAGE` | MESSAGE |
| `tot/filter/ajax/getOperationNameList` | `getOperationNameList(String fabSite)` | `memlookup name=operation_name | sort OPERATION` | OPERATION |

**Request**
```
GET /tot/filter/ajax/getAreaList?fabSite=M14
```

**Response** (예: getAreaList)
```json
[
  [
    {"AREANAME": "AREA01"},
    {"AREANAME": "AREA02"}
  ]
]
```

> 주의: 외부 배열이 한 겹 추가됨(`List<List>`). 클라이언트는 `data[0]`로 접근.

---

### 3.5 팝업

#### 3.5.1 `tot/pop/machineNamePop` — Total Machine 팝업

- **Controller**: `TotalController#machineNamePop`
- **View**: `tot/pop/machineNamePop`
- **Model**: `machineTypeInfoList` — `totService.getMachineTypeFromFab(new MachineVo())` 결과
- **주의**: 전달된 `MachineVo`가 새 인스턴스이므로 `fabSite=null` → `DBManager(null)` 동작은 `Common.DEFAULT_FABSITE` 처리에 의존

#### 3.5.2 `totNew/pop/machineNamePop` — TotalNew Machine 팝업

- **Controller**: `TotalNewController#machineNamePop(@ModelAttribute TotalVo param, request)`
- **View**: `tot/pop/machineNamePop` (같은 JSP 재사용)
- **Model**: `list` — `totService.getSelectList(fabSite)` 결과 (machine_list/comm_msg_name/message_name 합본)
- **fabSite**: `param.getFabSite() → Common.setFabSite(request, …)` 적용

#### 3.5.3 `tot/pop/filterPop` — 필터 팝업

- **Controller**: `TotalController#filterPop`
- **View**: `tot/pop/filterPop`
- **Model**: 없음

#### 3.5.4 `common/pop/settingPop` — 환경설정 팝업

- **Controller**: `TotalController#settingPop`
- **View**: `common/pop/settingPop`
- **Model**: 없음

---

### 3.6 TotalNew (Carrier 흐름)

#### 3.6.1 `totNew/totalNewLogList` — 신규 로그 조회 화면

- **Controller**: `TotalNewController#totalNewLogList(@ModelAttribute TotalNewVo param, request)`
- **View**: `tot/totalNewLogList`

**Request (TotalNewVo)**

| 파라미터 | 기본 | 비고 |
|---|---|---|
| `fabSite` | 세션 | |
| `pageNum` | `"1"` | |
| `rowNum` | `"100"` | (버그) `getRowNum()==null` 검사 시 `getPageNum().equals("")` 비교 |
| `from` | 현재−10분 | |
| `to` | 현재 | |
| `areaName` | `ALL` | |
| `bayName` | `ALL` | |
| `machineTypes` | csv | `ALL`이면 무조건 |
| `carrier` | - | 값이 있으면 `getCompletedCarrierListQueryByCarrier` 분기 |

**서비스 호출**: `totService.getDataList(TotalNewVo)` →
- carrier 있음: `proc COMPLETED_CARRIER_FROM_TO_CARRIER(from, to, carrier)` + machineType
- carrier 없음: `proc COMPLETED_CARRIER_FROM_TO(from, to)` + machineType
- 공통 suffix: `| limit offset limit | sort _TIME`

**Response (Model)**
- `list`, `paging`, `param`, `params`, `fabsites`
- 첫 row의 `count` 컬럼을 totalRecord로 사용

#### 3.6.2 `totNew/ajax/totalNewLogList` — 신규 로그 조회 ajax

- **Controller**: `TotalNewController#totalNewLogListAjax`
- **View**: `jsonView`
- 위 화면 진입과 동일 로직, 응답만 JSON

**Response**
```json
{
  "total": 100,
  "records": 50,
  "paging": { ... },
  "param": { ... },
  "params": { ... },
  "rows": [ ... ]
}
```

#### 3.6.3 `totNew/ajax/getCarrierElapsed` — Carrier Elapsed 상세

- **Controller**: `TotalNewController#getCarrierElapsed(@ModelAttribute TotalNewVo param, request)`
- **View**: `jsonView`

**Request**

| 파라미터 | 비고 |
|---|---|
| `fabSite` | 세션 처리 |
| `addQuery` | **클라이언트가 전송한 Logpresso 쿼리 문자열을 그대로 실행** |

**처리 (위험)**
```java
if (request.getParameter("addQuery") != null && !... .equals("")) {
    list = totService.getDetailDataList(fabSite, request.getParameter("addQuery"));
}
```
→ `TotalNewServiceImpl.getDetailDataList` 가 `Client.dbExecuteQuery(fabSite, addQuery)`를 그대로 호출.

**Response**
```json
{ "list": [ ... ] }
```

**Error**: 잘못된 쿼리는 DAO에서 catch → 빈 결과.

**Example**
```
POST /totNew/ajax/getCarrierElapsed
  fabSite=M14
  addQuery=table FROM=20260101000000 TO=20260101010000 ts_data_m14a | search CARRIER="ABC1234"
```

> 보안 이슈: 임의 쿼리 인젝션 가능. 비고 6장 참조.

---

### 3.7 view-controller (코드 없음)

`servlet-context.xml` 내 `<view-controller>`로 직접 정의된 매핑.

#### 3.7.1 `tot/main` (view-controller)

```xml
<view-controller path="tot/main" view-name="main" />
```
- 별도 Java 컨트롤러 메서드 없이 `main` 뷰로 직행
- 그러나 `TotalController#main`이 같은 경로(`tot/main`)에 매핑되어 있어 **컨트롤러가 우선** 적용된다(Spring 기본 동작)
- 백업/리졸브 안전망 역할

#### 3.7.2 `tot/index` (view-controller)

```xml
<view-controller path="tot/index" view-name="index" />
```
- 컨트롤러 미매핑. 순수 view-controller만 존재
- Tiles `index` 정의 또는 `/WEB-INF/views/index.jsp` 리졸브

**비고**: `tot/{query}` GET 매핑이 모든 미정의 GET 경로를 흡수하므로, `view-controller`로만 등록한 `tot/index`도 `getRequest` catch-all과 매핑 우선순위가 충돌할 수 있음(보다 구체적인 매핑이 우선이라 view-controller가 먼저 적용되나, Spring 버전·등록 순서에 따라 달라질 수 있음).

---

## 4. 자원 모델

### 4.1 TotalVo 필드 (전체)

> Package: `com.skhynix.supply.tot.vo.TotalVo`

| 필드 | 타입 | 분류 | 설명 |
|---|---|---|---|
| `fabSite` | String | Site | M14/M15/M11/C2/IC 등 |
| `pageNum` | String | Page | 페이지 번호 |
| `rowNum` | String | Page | 페이지 행수 |
| `areaName` | String | Machine | ALL or 특정 area |
| `bayName` | String | Machine | ALL or 특정 bay |
| `machineType` | List<String> | Machine | STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT 등 |
| `machineName` | List<String> | Machine | 다중 machine name |
| `fab` | List<String> | FAB | M14A/M14B/M16A 등 |
| `level` | List<String> | Level | ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL |
| `searchOption` | String | Condition | "AND"/"OR" (소문자 변환되어 쿼리 합성) |
| `process` | String | Condition | PROCESSNAME (쉼표 다중) |
| `thread` | String | Condition | THREADNAME (쉼표 다중) |
| `gtxnId` | String | Condition | M16 Global Transaction Id (쉼표 다중) |
| `transactionId` | String | Condition | TRANSACTIONID (쉼표 다중) |
| `messageName` | String | Condition | MESSAGENAME 단일 |
| `comMsgName` | String | Condition | COMMSGNAME or MESSAGENAME OR 검색 |
| `operationName` | String | Condition | OPERATIONNAME 단일 |
| `carrier` | String | Condition | CARRIER (쉼표 다중) |
| `commandId` | String | Condition | COMMANDID (쉼표 다중) |
| `unit` | String | Condition | UNIT (쉼표 다중) |
| `text` | String | Condition | TEXT contains, *…* (쉼표 다중, `"` 이스케이프, `*` 제거) |
| `fulltext` | String | Condition | TEXT 와일드카드(*xxx*), `"`/`*` 처리 |
| `key` | List<String> | XML | (현재 미사용 — `getXmlList` 주석 처리됨) |
| `messageName_m` | String | M14통합 | 보조 필드 (Setter/Getter 만 존재) |
| `comMsgName_m` | String | M14통합 | 보조 필드 |
| `operationName_m` | String | M14통합 | 보조 필드 |
| `from` | String | Time | yyyyMMddHHmmss |
| `to` | String | Time | yyyyMMddHHmmss |

### 4.2 TotalNewVo 필드 (전체)

> Package: `com.skhynix.supply.tot.vo.TotalNewVo`

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | |
| `pageNum` | String | |
| `rowNum` | String | |
| `areaName` | String | ALL or 특정 area |
| `bayName` | String | ALL or 특정 bay |
| `machineType` | List<String> | |
| `machineName` | List<String> | |
| `level` | List<String> | |
| `searchOption` | String | |
| `carrier` | String | TotalNew 핵심 필터 |
| `totalElapsedTime` | String | Carrier 누적 elapsed |
| `elapsedTime` | String | 단일 구간 elapsed |
| `command` | String | |
| `messageName` | String | |
| `process` | String | |
| `transactionId` | String | |
| `commandId` | String | |
| `unit` | String | |
| `thread` | String | |
| `comment` | String | |
| `from` | String | |
| `to` | String | |

### 4.3 Logpresso 대상 테이블 / 룩업

| 자원 | 종류 | 사용 메서드 | 비고 |
|---|---|---|---|
| `machine_list` | memlookup | `getMachineNameList`, `getAreaNameList`, `getBayNameList`, `getMachineTypeFromFab`, `getAreaBayQueryParser`, `getMachineQueryParser*` | 과거 `machine_info`에서 마이그레이션(2021.04.01) |
| `comm_msg_name` | memlookup | `getCommMsgNameList`, `getSelectList` | |
| `message_name` | memlookup | `getMessageNameList`, `getSelectList` | |
| `operation_name` | memlookup | `getOperationNameList` | |
| `ts_data_m14a` (`Common.sTS_DATA_M14A`) | table | `getQueryParser` | M14 FAB A 전체 |
| `ts_data_view_m14a` (`Common.sTS_DATA_VIEW_M14A`) | table | `getQueryParser` | M14 FAB A view (level 필터링 적용본) |
| `ts_data_m14b` / `..._view_m14b` | table | M14 FAB B | |
| `ts_data_m15a` / `..._view_m15a` | table | M15 FAB A | |
| `ts_data_m15b` / `..._view_m15b` | table | M15 FAB B | |
| `ts_data_m11a` / `..._view_m11a` | table | M11 FAB A | |
| `ts_data_m11b` / `..._view_m11b` | table | M11 FAB B | |
| `ts_data_c2` / `..._view_c2` | table | C2 (메인) | |
| `ts_data_c2f` / `..._view_c2f` | table | C2 (front?) | |
| `ts_data_m16a` / `..._view_m16a` | table | IC fabSite의 M16 FAB A | |
| `ts_data_m16b` / `..._view_m16b` | table | IC fabSite의 M16 FAB B | |
| `proc COMPLETED_CARRIER_FROM_TO(from,to)` | stored proc | TotalNew | Carrier 완료 흐름 |
| `proc COMPLETED_CARRIER_FROM_TO_CARRIER(from,to,carrier)` | stored proc | TotalNew | Carrier 단건 흐름 |

### 4.4 통합 검색 대상 도메인 (machine_list 기준 머신/타입)

`MACHINETYPE` 또는 `TYPE` 컬럼이 가질 수 있는 값(시스템 통합 검색 대상):

| 도메인 | 머신/장치 종류 |
|---|---|
| 반송 | CRANE, VEHICLE(OHT/AGV), LIFTER, CONVEYOR |
| 저장/포트 | SHELF, STORAGE, PORT, STOCKER, STB |
| 처리 | MACHINE(PROCESS), PROCESS |
| 매체 | CARRIER (반송체 단위) |
| 트랜잭션 | TRAN (transaction log) |
| 인프라 | ZIPTOWER |

> 위 도메인 분류는 시스템 통합 모니터링/검색의 논리 범주이며, 실제 컬럼 값은 fabSite/머신 디바이스 마스터에 따라 다양.

### 4.5 Common 상수/유틸 의존

`TotalServiceImpl`, `TotalNewServiceImpl`에서 사용하는 주요 `Common` 상수:

`sCRLF, sComma, sPipeLine, sSpace, sDoubleQuotation, sLeftParenthesis, sRightParenthesis, sAnd, sOr, sEquals, sEqual_1, sAsterisk, sCommaOrigin, sEmpty, sPlus, sFrom, sFields, sSort, sSearch_0/sSearch_1/sSearch_in, sFulltext/sFulltext0/sFulltext_Arg0, sTable_From, sOrder, sAsc, sParallel, sProc, sEval, sALL, sNOTDESIGNATED, sWELL/sWARN/sERROR/sFATAL, sLEVEL, sMACHINENAME, sMACHINETYPE, sTYPE, sUNIT, sCARRIER, sCOMMANDID, sCOMMAND, sOPERATIONNAME, sMESSAGENAME, sPROCESS, sPROCESSNAME, sTRANSACTIONID, sGTXN_ID, sTHREADNAME, sCOMMSGNAME, sTEXT, sKey, sXML, sSECS, sRESULTCODE, sAREANAME, sBAYNAME, s_TIME, sTIME_EX, sCOMPLETED_CARRIER_FROM_TO, sCOMPLETED_CARRIER_FROM_TO_CARRIER, sFABSITE_M14/M15/M11/C2/IC, sFAB_M14A/M14B/M15A/M15B/M11A/M11B/C2/C2F/M16A/M16B, sTS_DATA_*, sTS_DATA_VIEW_*, searchDelayTime(정적), FabSites, Levels`

전역 유틸:
- `Common.getFabSite(request)` / `Common.setFabSite(request, fabSite)` — 세션 기반 fabSite
- `Common.getFabList(menu, fabSite)` / `Common.getBasicFabList(menu, fabSite)` — FAB 목록/기본 체크
- `Common.getColumnFromFab(fabSite, fab)` — `search in(SHOPNAME, …)` 토큰 생성
- `Common.getLocale()` — i18n 로케일

---

## 5. 인증 및 권한

본 모듈에는 **명시적 인증/권한 검사 로직이 없다.** Spring Security 등 Filter/Interceptor 기반 인증이 외부에서 처리된다는 가정.

- `servlet-context.xml`에 등록된 인터셉터는 두 개뿐:
  - `LoggerInterceptor` (`/**`) — 로깅 전용
  - `LocaleChangeInterceptor` (`lang` 파라미터로 로케일 변경)
- 세션 사용처는 `HttpSession`을 통한 fabSite 저장/조회뿐이며, 사용자 인증·권한과는 무관.

→ 본 API는 사실상 **익명 접근 가능**한 상태로 동작한다. 외부 ECM/SSO/WAF 등이 전면에서 인증을 처리한다고 추정해야 한다.

---

## 6. 비고 / 이슈

### 6.1 `tot/{query}` catch-all 부작용

`@RequestMapping(path="tot/{query}", method=RequestMethod.GET)`은 **GET-only**임에도, `tot/` 하위의 미매핑 GET 경로를 모두 흡수해 `tot/main`을 렌더한다.

- 효과: 404가 발생하지 않고 메인 페이지가 반환됨. 로그/모니터링/오타 URL 감지 어려움.
- 보안: 의도치 않은 URL이 모두 200을 반환하므로 스캐닝 도구가 응답 차이로 경로 존재 여부를 판별하기 쉬워질 수 있음.
- 라우팅 우선순위: 구체적 매핑(`tot/totalLogList`, `tot/main`, `tot/dashboard/*`, `tot/ajax/*`, `tot/filter/ajax/*`, `tot/pop/*`)이 우선이므로 정상 동작은 보장. 다만 `view-controller path="tot/index"`와 `tot/{query}`의 우선순위는 Spring 내부 정렬에 의존(일반적으로 view-controller가 우선).
- 권장: catch-all을 제거하고 명시적 404 또는 명시적 redirect로 대체.

### 6.2 `TotalNewController#getCarrierElapsed`의 `addQuery` 쿼리 인젝션 가능성

```java
if(request.getParameter("addQuery") != null && !request.getParameter("addQuery").equals("")){
    list = totService.getDetailDataList(fabSite, request.getParameter("addQuery"));
}
```

- 클라이언트가 보낸 `addQuery` 파라미터를 그대로 Logpresso로 실행.
- Logpresso 쿼리 언어는 SQL과 별개지만, `table`, `search`, `proc`, `eval`, `lookup` 등 광범위한 데이터 접근 기능을 가짐. 임의 쿼리 인젝션이 가능.
- `fabSite` 세션 검증을 제외하면 입력 검증 0건. `addQuery` 길이 제한·화이트리스트도 없음.
- 권장: 화면이 필요로 하는 파라미터(예: carrier, from, to)만 받고 쿼리는 서버에서 조립.

### 6.3 정적 필드 멀티세션 간섭

- `Common.searchDelayTime`: `getTotalLogList`에서 `searchDelay` 요청 파라미터로 **전역 정적 필드를 덮어쓴다.** 한 사용자가 큰 값을 보내면 모든 사용자 세션에 영향.
- `Paging.nTotalCount`: `getTotalLogList`에서 `paging.setNumberOfRecords(Paging.nTotalCount)`를 사용. `nTotalCount`가 정적 필드라면, 동시 요청 간 페이징 카운트가 섞일 수 있음.
- 권장: 세션 범위 또는 요청 범위 필드로 옮길 것.

### 6.4 `searchDelay` NPE 위험

```java
int delayTime = Integer.parseInt(request.getParameter("searchDelay"));
```
- 파라미터 없으면 `Integer.parseInt(null)` → `NumberFormatException` → errorPage.
- 클라이언트가 항상 보낸다는 가정에 의존. 방어적 코딩 필요.

### 6.5 `getRowNum` 검사 버그 (TotalNewController)

```java
if (param.getRowNum() == null || param.getPageNum().equals("")) {
    param.setRowNum("100");
}
```
- `getRowNum` 체크인데 `getPageNum().equals("")`를 검사하는 복사·붙여넣기 오류. 빈 문자열 rowNum이 들어와도 100으로 덮이지 않음.

### 6.6 `TotalNewServiceImpl`의 인터페이스 더미 구현

`TotalNewServiceImpl`은 `TotalService`의 대부분 메서드를 `return null`로 비워두었기 때문에, `totalNewService` 빈을 다른 위치에서 잘못 주입하면 **NPE**가 발생하기 쉽다(`TotalController`는 `totalService`를, `TotalNewController`는 `totalNewService`를 정확히 주입함).

### 6.7 같은 URL을 가진 view-controller + 컨트롤러 매핑

`tot/main`은 `<view-controller>`와 `TotalController#main` 양쪽에 정의되어 있다.
- 컨트롤러가 우선 적용되지만, 컨트롤러를 제거하면 자동으로 view-controller가 폴백 됨.
- 의도된 안전망이지만, 양쪽이 동시에 존재한다는 사실은 코드를 읽는 사람에게 혼동을 줄 수 있다.

### 6.8 메인 컨트롤러에서의 세션 로깅 노출

`TotalController#main`은 `Session ID`, `Creation Time`, `Last Accessed Time`을 INFO 레벨로 로깅한다. 운영 로그가 외부 분석 도구로 송신되는 경우 세션 식별자가 유출될 수 있다.

### 6.9 동기 1-쓰레드 DAO

`TotalDAO.dbExecuteQuery`는 매 호출마다 `new DBManager(fabSite)`를 만들고 finally에서 `dbManager = null`만 설정한다. `executeQueryStop()`은 별도 인스턴스이면 의미가 없음(인스턴스 필드 `dbManager`가 메서드 종료 시 null로 바뀜).
- 결과: `tot/ajax/getTotalLogListStop`이 실질적으로 진행 중인 조회를 중단시키지 못할 수 있다.

### 6.10 `TotalServiceImpl.getDataList(TotalNewVo)`, `getDetailDataList(...)` 미구현

`totalService` 빈으로 `TotalNewVo` 흐름이 들어오면 **null이 반환**된다. 현재 코드 경로상 호출되지 않으나, 향후 잘못된 라우팅 위험.

---

## 7. 참고 소스 매핑

| 파일 | 경로 |
|---|---|
| TotalController | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/controller/TotalController.java` |
| TotalNewController | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/controller/TotalNewController.java` |
| TotalService | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/TotalService.java` |
| TotalServiceImpl | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/impl/TotalServiceImpl.java` |
| TotalNewServiceImpl | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/impl/TotalNewServiceImpl.java` |
| TotalDAO | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/dao/TotalDAO.java` |
| TotalVo | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/vo/TotalVo.java` |
| TotalNewVo | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/vo/TotalNewVo.java` |
| ExceptionControllerAdvice | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/common/error/ExceptionControllerAdvice.java` |
| servlet-context.xml | `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/webapp/WEB-INF/spring/appServlet/servlet-context.xml` |
