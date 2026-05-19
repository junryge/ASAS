# 07. tran (이송/Transfer) 모듈 API 명세서

> 패키지: `com.skhynix.supply.tran`
> 대상 컨트롤러: `TranController`, `TranCmdHistoryController`, `TranCmdFailController`, `TranJobHistoryController`, `TranJobFailController`
> 백엔드 저장소: Logpresso (Logpresso fulltext / table / proc 쿼리)
> 인증 모델: 서블릿 세션 기반 (Common.getFabSite / Common.setFabSite)

---

## 1. API 개요

`tran` 모듈은 자동반송(Transfer) 도메인의 로그를 5개 서브영역으로 분기해서 조회한다. 각 서브영역은 Logpresso의 메소드 키(`method=...`)로 구분되는 서로 다른 이벤트를 검색한다.

| 서브영역 | 의도 | 대상 method 키 (Logpresso) | 화면(JSP) 경로 |
| --- | --- | --- | --- |
| Tran (반환 로그) | 반송 Job/Command가 종료된 결과 이력 (state=COMPLETED / CANCELED) 조회 + Job 상세 (createTransport*Detail / 프로시저 호출) | `createTransportJobHistory` | `tran/returnLogList` |
| TranCmd (반송 명령 이력) | 반송 Command 생성 이력 조회 | `createTransportCommandHistory` | `tran/returnCmdLogList` |
| TranCmdFail (반송 명령 실패) | 반송 Command가 실패한 이력 조회 + Reason 팝업 | `createTransportCommandFailHistory` | `tran/returnCmdFailLogList` |
| TranJob (반송 작업 이력) | 반송 Job 생성 이력 조회 | `createTransportJobHistory` | `tran/returnJobLogList` |
| TranJobFail (반송 작업 실패) | 반송 Job이 실패한 이력 조회 | `createTransportJobFailHistory` | `tran/returnJobFailLogList` |

### 1.1 공통 패턴

- **컨트롤러 = 화면(GET) + ajax(POST/GET) 쌍 구조**
  - 화면 매핑: `tran/{name}LogList` → JSP `tran/{name}LogList`를 ModelAndView로 리턴, FabSite/Fab 리스트를 모델에 세팅한다.
  - 데이터 매핑: `tran/ajax/{name}` → `jsonView`로 리턴 (`page`, `total`, `records`, `rows`).
- **DI 분기**: 다섯 컨트롤러 모두 `TranService` 인터페이스를 주입받지만, `@Resource(name=...)`로 구현체를 다르게 바인딩한다.
  - `tranService` → `TranServiceImpl`
  - `tranCmdHistoryService` → `TranCmdHistoryServiceImpl`
  - `tranCmdFailService` → `TranCmdFailServiceImpl`
  - `tranJobHistoryService` → `TranJobHistoryServiceImpl`
  - `jobFailService` → `TranJobFailServiceImpl`
- **FabSite 처리** (2022.06.15 X0122410 변경)
  - 요청 파라미터 `fabSite`가 없으면 세션에서 가져오고(`Common.getFabSite`), 있으면 세션에 새로 저장(`Common.setFabSite`)한다.
  - 모델 `fabsites`에 `Common.FabSites` 상수를 같이 내려준다.
- **다중선택 파라미터 파싱**:
  - `fab1`이 `ALL`이면 사이트에 속한 전체 Fab 리스트로 채운다.
  - 그 외에는 `fab1..fabN`을 순회하면서 채운다 (n은 fabList.size()+1까지).
  - `transportMachineTypes` / `fromMachineTypes` / `toMachineTypes` / `states`는 콤마(`,`) 문자열을 split하여 List로 변환하되, 첫 토큰이 `ALL`이면 빈 리스트로 클리어한다.
- **기본값**:
  - `page`=1, `rows`=100
  - `from` 미지정 시 현재 시각의 10분 전(`yyyyMMddHHmmss`), `to` 미지정 시 현재 시각
  - `transport/from/toAreaName`, `transport/from/toBayName` 미지정 시 `Common.sALL`
- **Logpresso 쿼리 생성**: 각 ServiceImpl의 `getXxxQueryParser`가 `Common.sFulltext_Arg0_key1` (`fulltext from=... to=... key1=...`) 포맷을 기반으로 method 조건과 조건절(AREA/BAY/MACHINE/CARRIER/STATE 등), Fab별 테이블 명, `search in` 절, `fields` 절, `limit`, `sort _time`을 차례로 붙여 만든다.
- **Fab별 테이블 매핑**: `getTableFromFab(fabSite, fab)` switch문이 fabSite에 따라 `Common.sTS_TRANSPORT_*` 상수를 반환한다. switch에는 `break`가 없어 의도적/비의도적 fall-through가 발생한다(아래 6.4 참조).
- **페이징**: `Paging` 유틸이 `Paging.nTotalCount`를 정적으로 참조하여 `records`/`total`/`page`를 산출한다.
- **데이터 액세스**: `TranDAO.dbExecuteQuery(fabSite, queryStmt)`는 `DBManager(fabSite)` 인스턴스로 Logpresso에 쿼리를 던지고 `List<Map>`을 반환한다. 실패 시 warn 로그만 남기고 `null` 또는 `dataList` 반환.
- **예외 처리**: `ExceptionControllerAdvice`가 `Exception.class`를 잡아 `common/error/errorPage` 뷰로 포워딩하면서 `name`(예외 단순 클래스명)과 `message`를 모델에 추가한다.

---

## 2. API 목록

| # | HTTP | URL | 컨트롤러 | 메서드 | 종류 | 반환 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GET/POST | `/tran/returnLogList` | TranController | returnLogList | 화면 | View `tran/returnLogList` |
| 2 | GET/POST | `/tran/ajax/getReturnLogList` | TranController | getReturnLogList | AJAX | JSON (rows, page, total, records) |
| 3 | GET/POST | `/tran/ajax/getTranJobHistoryDetail` | TranController | getTranJobHistoryDetail | AJAX | JSON (rows, commandListRow, historyListRow) |
| 4 | GET/POST | `/tran/ajax/getReasonList` | TranController | getReasonList | AJAX | JSON (list) |
| 5 | GET/POST | `/tran/returnCmdLogList` | TranCmdHistoryController | returnCmdLogList | 화면 | View `tran/returnCmdLogList` |
| 6 | GET/POST | `/tran/ajax/getReturnCmdLogList` | TranCmdHistoryController | getReturnCmdLogList | AJAX | JSON |
| 7 | GET/POST | `/tran/returnCmdFailLogList` | TranCmdFailController | returnCmdFailLogList | 화면 | View `tran/returnCmdFailLogList` |
| 8 | GET/POST | `/tran/ajax/getReturnCmdFailLogList` | TranCmdFailController | getReturnCmdFailLogList | AJAX | JSON |
| 9 | GET/POST | `/tran/pop/reasonPop` | TranCmdFailController | machineNamePop | 팝업 | View `tran/pop/reasonPop` |
| 10 | GET/POST | `/tran/returnJobLogList` | TranJobHistoryController | returnLogList | 화면 | View `tran/returnJobLogList` |
| 11 | GET/POST | `/tran/ajax/getReturnJobLogList` | TranJobHistoryController | getReturnJobLogList | AJAX | JSON |
| 12 | GET/POST | `/tran/returnJobFailLogList` | TranJobFailController | tranJobFail | 화면 | View `tran/returnJobFailLogList` |
| 13 | GET/POST | `/tran/ajax/getReturnJobFailLogList` | TranJobFailController | getReturnJobFailLogList | AJAX | JSON |

> 총 13개 엔드포인트 (화면 5 + AJAX 7 + 팝업 1)
>
> `@RequestMapping`은 method를 지정하지 않으므로 모든 HTTP method를 허용한다(실무상은 GET/POST).

---

## 3. 상세 API 명세

각 화면 엔드포인트의 Request 파라미터는 `@ModelAttribute`로 VO에 바인딩된다. AJAX 엔드포인트는 화면 엔드포인트와 동일한 VO를 사용하며 추가로 `page`, `rows`, `fab1..N`, `transportMachineTypes`/`fromMachineTypes`/`toMachineTypes`/`states`, `transportMachineType1`/`fromMachineType1`/`toMachineType1`/`state1` 파라미터를 사용한다.

---

### 3.1 Tran (반환 로그)

#### 3.1.1 GET `/tran/returnLogList` — 반환 로그 조회 화면

- **컨트롤러**: `TranController#returnLogList`
- **설명**: 반송 이력 조회 화면 진입. 세션 fabSite/fab 리스트를 초기화하고 JSP로 포워딩.
- **Request 파라미터** (`@ModelAttribute TranVo`): 4장 TranVo 필드 참조. 핵심은 `fabSite`만 의미 있음.
- **Response**: `ModelAndView`
  - `viewName` = `tran/returnLogList`
  - `fabsites` = `Common.FabSites`
  - `fabs` = `Common.getFabList("tran", fabSite)`
  - `param`, `params` = 입력 VO (fab는 기본 fab list로 세팅됨)
- **Error**: `ExceptionControllerAdvice`가 잡아 `common/error/errorPage` 뷰로 포워딩.
- **Example**:
  - 요청: `GET /tran/returnLogList?fabSite=M14`
  - 응답: JSP 렌더링 (HTML)

#### 3.1.2 POST `/tran/ajax/getReturnLogList` — 반환 로그 데이터 조회

- **컨트롤러**: `TranController#getReturnLogList`
- **설명**: Logpresso에서 `method=createTransportJobHistory` 이벤트를 검색하고 state=COMPLETED/CANCELED 조건을 적용해 페이징된 반환 이력 목록을 반환한다.
- **Request 파라미터** (`@ModelAttribute TranVo` + raw):
  - `fabSite` (String): 미지정 시 세션에서 가져옴.
  - `page` (String, default `"1"`), `rows` (String, default `"100"`)
  - `from`, `to` (String, `yyyyMMddHHmmss`): 미지정 시 (현재-10분, 현재)
  - `fab1..N` 또는 `fab1=ALL` → `fab`
  - `transportMachineType1` + `transportMachineTypes` → `transportMachineType` (List)
  - `fromMachineType1` + `fromMachineTypes` → `fromMachineType` (List)
  - `toMachineType1` + `toMachineTypes` → `toMachineType` (List)
  - `state` (단일 String) → `state` (List 크기 1; 단 ServiceImpl에서 ALL이면 미적용)
  - `carrier`, `lotId`, `transportJobId`
  - `transportAreaName`, `transportBayName`, `fromAreaName`, `fromBayName`, `toAreaName`, `toBayName`: 미지정 시 `ALL`.
- **Logpresso 쿼리 (TranServiceImpl.getTranQueryParser)**:
  ```
  fulltext from=... to=... key1=(method="createTransportJobHistory")
    and (CARRIER="...") and (TRANSPORTJOBID="...") and (LOTID="...")
    and (TRANSPORTAREANAME="...") and (TRANSPORTBAYNAME="...")
    and (SOURCEAREANAME="...") and (SOURCEBAYNAME="...")
    and (DESTAREANAME="...") and (DESTBAYNAME="...")
    and (TRANSPORTMACHINENAME=... or ...) and (SOURCEMACHINENAME=...) and (DESTMACHINENAME=...)
    and (STATE="COMPLETED" or STATE="CANCELED") from <Fab tables>
    | search in TRANSPORTTYPE2 ( ... )
    | search in SOURCEMACHINETYPE2 ( ... )
    | search in DESTTYPE2 ( ... )
    | fields TIME_EX, TRANSPORTJOBID, STATE, CARRIER, REASON, FIXEDROUTE, PRIORITY, LOTID, BATCHID, STEPID, PROCESSID, DESCRIPTION, SOURCEMACHINENAME, SOURCEAREANAME, SOURCEBAYNAME, SOURCEUNITNAME, SOURCEMACHINETYPE, SOURCEMACHINETYPE2, DESTMACHINENAME, DESTAREANAME, DESTBAYNAME, DESTTYPE, DESTTYPE2, DESTUNITNAME, CREATEUSER, BATCHTYPE, METHOD
    | limit <offset> <limit>
    | sort _time
  ```
- **Response**: `ModelAndView` (`viewName`=`jsonView`)
  ```json
  {
    "page": 1,
    "total": 0,
    "records": 100,
    "rows": [ { "TIME": "...", "TRANSPORTJOBID": "...", "STATE": "COMPLETED", "CARRIER": "...", ... } ]
  }
  ```
- **Error**: 쿼리 실패 시 `TranDAO.dbExecuteQuery`가 warn 로그 후 `null`을 반환 → `rows`가 `null`이 될 수 있음. 그 외는 ExceptionControllerAdvice가 처리.
- **Example**:
  - 요청: `POST /tran/ajax/getReturnLogList`
    Body: `fabSite=M14&page=1&rows=50&from=20240101000000&to=20240101010000&fab1=ALL&state=COMPLETED&transportMachineTypes=OHT,STOCKER`

#### 3.1.3 POST `/tran/ajax/getTranJobHistoryDetail` — 반환 Job 상세 조회

- **컨트롤러**: `TranController#getTranJobHistoryDetail`
- **설명**: 특정 `transportJobId`에 대한 Job + Command 상세를 한 번에 가져와서 `method` 키에 따라 command/history로 분리한다.
- **Request 파라미터** (`@ModelAttribute TranVo`):
  - `fabSite`, `from`, `to`, `transportJobId`
- **Logpresso 쿼리 (TranServiceImpl.getTranJobHistoryDetailQueryParser)**:
  - `to-from > 1시간` → `Common.sProc + Common.sFulltext_From_TRAN` (Logpresso `proc` 호출, fulltext 모드)
  - 그 외 → `Common.sProc + Common.sTable_From_TRAN` (table 모드)
- **Response 분기 처리**: 결과 row를 `method == Common.METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY`이면 `commandListRow`로, 그 외는 `historyListRow`로 분류.
  ```json
  {
    "rows": [...전체...],
    "commandListRow": [...command rows...],
    "historyListRow": [...history rows...]
  }
  ```
- **Error**: SimpleDateFormat parse 실패는 catch(Exception ignore)로 무시되어 빈 쿼리가 만들어진다 → `dataList`는 `null`.
- **Example**: `POST /tran/ajax/getTranJobHistoryDetail?fabSite=M14&from=20240101000000&to=20240101010000&transportJobId=TJ-001`

#### 3.1.4 POST `/tran/ajax/getReasonList` — Reason 코드 목록

- **컨트롤러**: `TranController#getReasonList`
- **설명**: Logpresso `memlookup name=reasonList`에서 REASON 코드를 정렬해서 가져온다.
- **Request 파라미터** (`@ModelAttribute FabVo`): `fabSite`
- **Logpresso 쿼리**: `memlookup name=reasonList | fields REASON | sort REASON`
- **Response** (`viewName`=`jsonView`):
  ```json
  { "list": [ { "REASON": "AREA_FULL" }, { "REASON": "CONFLICT" } ] }
  ```
- **Error**: 표준 처리.
- **Example**: `GET /tran/ajax/getReasonList?fabSite=M14`

---

### 3.2 TranCmd (반송 명령 이력)

#### 3.2.1 GET `/tran/returnCmdLogList` — 반송 CMD 이력 조회 화면

- **컨트롤러**: `TranCmdHistoryController#returnCmdLogList`
- **설명**: 3.1.1과 동일한 패턴. `viewName`=`tran/returnCmdLogList`.
- **Request 파라미터**: `TranVo` (`fabSite` 만 의미 있음).
- **Response**: ModelAndView (`fabsites`, `fabs`, `param`, `params`).

#### 3.2.2 POST `/tran/ajax/getReturnCmdLogList` — 반송 CMD 이력 데이터 조회

- **컨트롤러**: `TranCmdHistoryController#getReturnCmdLogList`
- **설명**: `method=createTransportCommandHistory` 이벤트를 페이징하여 반환한다.
- **Request 파라미터**: 3.1.2와 유사하되 추가로
  - `state1`/`states` (List, ALL 토큰 처리)
  - `transportCommandId`, `transportUnit`, `fromUnit`, `toUnit` (TranVo)
  - `transportUnit`/`fromUnit`/`toUnit`은 ServiceImpl이 `_` 또는 `-`로 split해 여러 유닛 OR 절을 생성한다.
- **Logpresso 쿼리 (TranCmdHistoryServiceImpl.getTranCmdHistoryQueryParser)**:
  ```
  fulltext from=... to=... key1=(method="createTransportCommandHistory")
    and (CARRIER="...") and (TRANSPORTCOMMANDID="...")
    and ((STATE="...") or (STATE="...") ...)
    and ((TRANSPORTUNITNAME="A") and (TRANSPORTUNITNAME="B") ...)
    and (SOURCEUNITNAME ...) and (DESTUNITNAME ...)
    and AREA/BAY 조건 ... and MACHINENAME OR ... from <Fab tables>
    | search in TRANSPORTTYPE2 (...) | search in SOURCEMACHINETYPE2 (...) | search in DESTTYPE2 (...)
    | fields TRANSPORTCOMMANDID, TRANSPORTJOBID, STATE, CARRIER, PRIORITY, DESCRIPTION, FIXEDROUTE,
             SOURCEMACHINENAME, SOURCEUNITNAME, SOURCEAREANAME, SOURCEBAYNAME, SOURCEMACHINETYPE,
             DESTMACHINENAME, DESTAREANAME, DESTBAYNAME, DESTTYPE, DESTTYPE2, DESTUNITNAME, TIME_EX,
             TRANSPORTMACHINENAME, TRANSPORTTYPE2, TRANSPORTUNITNAME
    | limit <offset> <limit> | sort _time
  ```
- **Response**: `{ page, total, records, rows }`
- **Example**: `POST /tran/ajax/getReturnCmdLogList?fabSite=M14&page=1&rows=100&fab1=ALL&state1=ALL`

---

### 3.3 TranCmdFail (반송 명령 실패)

#### 3.3.1 GET `/tran/returnCmdFailLogList` — 반송 CMD 실패 화면

- **컨트롤러**: `TranCmdFailController#returnCmdFailLogList`
- **Request 파라미터**: `@ModelAttribute TranCmdFailVo`.
- **Response**: ModelAndView, `viewName`=`tran/returnCmdFailLogList`.

#### 3.3.2 POST `/tran/ajax/getReturnCmdFailLogList` — 반송 CMD 실패 데이터 조회

- **컨트롤러**: `TranCmdFailController#getReturnCmdFailLogList`
- **설명**: `method=createTransportCommandFailHistory` 이벤트를 페이징.
- **Request 파라미터** (`TranCmdFailVo` + raw):
  - 시간/페이징/Fab/MachineType은 공통.
  - `carrier`, `transportCmdId` (주의: VO 필드명이 `transportCmdId`, 컨트롤러에서는 `transportCommandId`가 아님)
  - `reason` (List<String>): 다중 OR 처리.
  - `state` 파라미터는 본 컨트롤러에서 미처리(없음).
- **Logpresso 쿼리 (TranCmdFailServiceImpl.getCmdFailQueryParser)**:
  ```
  fulltext from=... to=... key1=(method="createTransportCommandFailHistory")
    and (CARRIER="...") and (TRANSPORTCOMMANDID="...")
    and ((REASON="...") or (REASON="...") ...)
    and AREA/BAY 조건 ... and MACHINENAME OR ... from <Fab tables>
    | search in TRANSPORTTYPE2/SOURCEMACHINETYPE2/DESTTYPE2 (...)
    | fields CARRIER, TRANSPORTJOBID, TRANSPORTCOMMANDID, SOURCEMACHINENAME, SOURCEAREANAME,
             SOURCEBAYNAME, SOURCEMACHINETYPE, SOURCEMACHINETYPE2, DESTMACHINENAME, DESTAREANAME,
             DESTBAYNAME, DESTTYPE, DESTTYPE2, DESTUNITNAME, REASON, PRIORITY, DESCRIPTION,
             TIME_EX, SOURCEUNITNAME
    | limit <offset> <limit> | sort _time
  ```
- **Response**: `{ page, total, records, rows }`
- **Example**: `POST /tran/ajax/getReturnCmdFailLogList?fabSite=M14&reason=AREA_FULL`

#### 3.3.3 GET `/tran/pop/reasonPop` — Reason 팝업 화면

- **컨트롤러**: `TranCmdFailController#machineNamePop` (메서드명 주의 — 아래 6.1 참조)
- **설명**: Reason 선택 팝업 뷰. 어떠한 데이터 처리도 수행하지 않고 단순히 JSP만 리턴.
- **Request 파라미터** (`@ModelAttribute TranCmdFailVo`): 사용되지 않음.
- **Response**: ModelAndView, `viewName`=`tran/pop/reasonPop`
- **Error**: 표준 처리.

---

### 3.4 TranJob (반송 작업 이력)

#### 3.4.1 GET `/tran/returnJobLogList` — 반송 JOB 이력 화면

- **컨트롤러**: `TranJobHistoryController#returnLogList` (메서드명은 `returnLogList`로 TranController와 동일)
- **Request 파라미터**: `TranVo`
- **Response**: ModelAndView, `viewName`=`tran/returnJobLogList`

#### 3.4.2 POST `/tran/ajax/getReturnJobLogList` — 반송 JOB 이력 데이터 조회

- **컨트롤러**: `TranJobHistoryController#getReturnJobLogList`
- **설명**: `method=createTransportJobHistory`를 검색하지만, 3.1.2(Tran)와 달리 state=COMPLETED/CANCELED 강제 필터가 없고, 결과 fields가 Job 위주이다.
- **Request 파라미터**: 3.1.2와 거의 동일. `state1`/`states`를 다중 처리.
- **Logpresso 쿼리 (TranJobHistoryServiceImpl.getTranJobHistoryQueryParser)**:
  ```
  fulltext from=... to=... key1=(method="createTransportJobHistory")
    and (CARRIER="...") and (TRANSPORTJOBID="...") and (LOTID="...")
    and (STATE 다중 OR) and AREA/BAY ... and MACHINENAME OR ... from <Fab tables>
    | search in TRANSPORTTYPE2/SOURCEMACHINETYPE2/DESTTYPE2 (...)
    | fields TIME_EX, TRANSPORTJOBID, STATE, FIXEDROUTE, LOTID, BATCHID, STEPID, PROCESSID,
             CARRIER, PRIORITY, DESCRIPTION, REASON, SOURCEMACHINENAME, SOURCEAREANAME,
             SOURCEBAYNAME, SOURCEMACHINETYPE, SOURCEMACHINETYPE2, DESTMACHINENAME, DESTAREANAME,
             DESTBAYNAME, DESTTYPE, DESTTYPE2, DESTUNITNAME, SOURCEUNITNAME, CREATEUSER, BATCHTYPE
    | limit <offset> <limit> | sort _time
  ```
- **Response**: `{ page, total, records, rows }`
- **Example**: `POST /tran/ajax/getReturnJobLogList?fabSite=M14`

---

### 3.5 TranJobFail (반송 작업 실패)

#### 3.5.1 GET `/tran/returnJobFailLogList` — 반송 JOB 실패 화면

- **컨트롤러**: `TranJobFailController#tranJobFail`
- **Request 파라미터**: `@ModelAttribute TranJobFailVo`
- **Response**: ModelAndView, `viewName`=`tran/returnJobFailLogList`

#### 3.5.2 POST `/tran/ajax/getReturnJobFailLogList` — 반송 JOB 실패 데이터 조회

- **컨트롤러**: `TranJobFailController#getReturnJobFailLogList`
- **설명**: `method=createTransportJobFailHistory` 이벤트를 페이징.
- **Request 파라미터** (`TranJobFailVo` + raw):
  - 시간/페이징/Fab/MachineType은 공통.
  - `carrier`, `lotId`, `transportJobId`
  - `reason` (List<String>): 다중 OR.
  - `state` 없음.
- **Logpresso 쿼리 (TranJobFailServiceImpl.getQueryParser)**:
  ```
  fulltext from=... to=... key1=(method="createTransportJobFailHistory")
    and (CARRIER="...") and (LOTID="...") and (TRANSPORTJOBID="...")
    and ((REASON="...") or ...)
    and AREA/BAY ... and MACHINENAME OR ... from <Fab tables>
    | search in TRANSPORTTYPE2/SOURCEMACHINETYPE2/DESTTYPE2 (...)
    | fields TIME_EX, TRANSPORTJOBID, CARRIER, PRIORITY, DESCRIPTION, REASON,
             SOURCEMACHINENAME, SOURCEAREANAME, SOURCEBAYNAME, SOURCEMACHINETYPE, SOURCEMACHINETYPE2,
             DESTMACHINENAME, DESTAREANAME, DESTBAYNAME, DESTTYPE, DESTTYPE2, DESTUNITNAME, SOURCEUNITNAME
    | limit <offset> <limit> | sort _time
  ```
- **Response**: `{ page, total, records, rows }`
- **Example**: `POST /tran/ajax/getReturnJobFailLogList?fabSite=M14&reason=AREA_FULL`

---

## 4. 자원 모델 (VO)

### 4.1 VO 필드 비교 (3종)

| 카테고리 | 필드 | TranVo | TranCmdFailVo | TranJobFailVo |
| --- | --- | :---: | :---: | :---: |
| 세션 | `fabSite` | O | O | O |
| 페이지 | `pageNum`, `rowNum` | O | O | O |
| Fab | `fab` (List) | O | O | O |
| Area/Bay | `transportAreaName`, `transportBayName` | O | O | O |
| Area/Bay | `fromAreaName`, `fromBayName` | O | O | O |
| Area/Bay | `toAreaName`, `toBayName` | O | O | O |
| Unit | `transportUnit`, `fromUnit`, `toUnit` | O | O | O |
| Machine Type | `transportMachineType`, `fromMachineType`, `toMachineType` | O | O | O |
| Machine Name | `transportMachineName`, `fromMachineName`, `toMachineName` | O | O | O |
| Time | `from`, `to` | O | O | O |
| Condition | `carrier` | O | O | O |
| Condition | `lotId` | O | X | O |
| Condition | `transportJobId` | O | X | O |
| Condition | `transportCommandId` | O | X | X |
| Condition | `transportCmdId` | X | O | X |
| Condition | `state` (List) | O | X | X |
| Condition | `reason` (List) | X | O | O |

> 공통 30 필드 + VO별 고유 필드. `transportCmdId` (TranCmdFailVo) ↔ `transportCommandId` (TranVo)는 다른 필드명이다.

### 4.2 TranVo — 모든 필드

| 필드 | 타입 | 설명 / 비고 |
| --- | --- | --- |
| `fabSite` | String | FabSite 세션 키 (M14/M15/M11/C2/IC). 2022.06.15 추가. |
| `pageNum` | String | 페이지 번호 (1부터). |
| `rowNum` | String | 한 페이지 행 수. |
| `fab` | List<String> | Fab 리스트 (M14A/M14B/M15A/M15B/M11A/M11B/C2/C2F/M16A/M16B 등). |
| `fromAreaName` | String | 출발 Area 이름 (ALL 가능). |
| `fromBayName` | String | 출발 Bay 이름 (ALL 가능). |
| `fromUnit` | String | 출발 Unit 이름. `_` 또는 `-`로 split하면 OR 조건 다중처리. |
| `toAreaName` | String | 도착 Area 이름. |
| `toBayName` | String | 도착 Bay 이름. |
| `toUnit` | String | 도착 Unit 이름. |
| `transportAreaName` | String | 운반 Area 이름. |
| `transportBayName` | String | 운반 Bay 이름. |
| `transportUnit` | String | 운반 Unit 이름. |
| `fromMachineType` | List<String> | 출발 장비 타입. STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT. |
| `toMachineType` | List<String> | 도착 장비 타입. |
| `transportMachineType` | List<String> | 운반 장비 타입. |
| `fromMachineName` | List<String> | 출발 장비 명. |
| `toMachineName` | List<String> | 도착 장비 명. |
| `transportMachineName` | List<String> | 운반 장비 명. |
| `from` | String | 조회 시작 (`yyyyMMddHHmmss`). |
| `to` | String | 조회 종료 (`yyyyMMddHHmmss`). |
| `carrier` | String | Carrier ID. |
| `lotId` | String | Lot ID. |
| `transportJobId` | String | Transport Job ID. |
| `transportCommandId` | String | Transport Command ID (TranCmdHistory에서 사용). |
| `state` | List<String> | 상태 리스트 (COMPLETED/CANCELED/INITIATED 등). |

(주석 처리되어 미사용: `transportFab`, `fromFab`, `toFab` — 모두 코멘트로 남아있음.)

### 4.3 TranCmdFailVo — 모든 필드

| 필드 | 타입 | 설명 / 비고 |
| --- | --- | --- |
| `fabSite` | String | FabSite 세션 키. |
| `pageNum` | String | 페이지 번호. |
| `rowNum` | String | 페이지당 행 수. |
| `fab` | List<String> | Fab 리스트. |
| `fromAreaName` | String | 출발 Area. |
| `fromBayName` | String | 출발 Bay. |
| `fromUnit` | String | 출발 Unit. (선언은 되어 있으나 ServiceImpl에서 unit 절은 생성하지 않음.) |
| `toAreaName` | String | 도착 Area. |
| `toBayName` | String | 도착 Bay. |
| `toUnit` | String | 도착 Unit. (미사용) |
| `transportAreaName` | String | 운반 Area. |
| `transportBayName` | String | 운반 Bay. |
| `transportUnit` | String | 운반 Unit. (미사용) |
| `fromMachineType` | List<String> | 출발 장비 타입. |
| `toMachineType` | List<String> | 도착 장비 타입. |
| `transportMachineType` | List<String> | 운반 장비 타입. |
| `fromMachineName` | List<String> | 출발 장비 명. |
| `toMachineName` | List<String> | 도착 장비 명. |
| `transportMachineName` | List<String> | 운반 장비 명. |
| `from` | String | 조회 시작. |
| `to` | String | 조회 종료. |
| `carrier` | String | Carrier ID. |
| `transportCmdId` | String | Transport Command ID. (필드명 비일관 — TranVo는 `transportCommandId`) |
| `reason` | List<String> | Reason 리스트 (memlookup의 REASON 값). |

(주석 처리되어 미사용: `transportFab`, `fromFab`, `toFab`)

### 4.4 TranJobFailVo — 모든 필드

| 필드 | 타입 | 설명 / 비고 |
| --- | --- | --- |
| `fabSite` | String | FabSite 세션 키. |
| `pageNum` | String | 페이지 번호. |
| `rowNum` | String | 페이지당 행 수. |
| `fab` | List<String> | Fab 리스트. |
| `fromAreaName` | String | 출발 Area. |
| `fromBayName` | String | 출발 Bay. |
| `fromUnit` | String | 출발 Unit. (미사용) |
| `toAreaName` | String | 도착 Area. |
| `toBayName` | String | 도착 Bay. |
| `toUnit` | String | 도착 Unit. (미사용) |
| `transportAreaName` | String | 운반 Area. |
| `transportBayName` | String | 운반 Bay. |
| `transportUnit` | String | 운반 Unit. (미사용) |
| `fromMachineType` | List<String> | 출발 장비 타입. |
| `toMachineType` | List<String> | 도착 장비 타입. |
| `transportMachineType` | List<String> | 운반 장비 타입. |
| `fromMachineName` | List<String> | 출발 장비 명. |
| `toMachineName` | List<String> | 도착 장비 명. |
| `transportMachineName` | List<String> | 운반 장비 명. |
| `from` | String | 조회 시작. |
| `to` | String | 조회 종료. |
| `carrier` | String | Carrier ID. |
| `lotId` | String | Lot ID. |
| `transportJobId` | String | Transport Job ID. |
| `reason` | List<String> | Reason 리스트. |

(주석 처리되어 미사용: `transportFab`, `fromFab`, `toFab`, `key`)

---

## 5. 인증 및 권한

- **인증 모델**: 서블릿 세션 기반. `Common.getFabSite(HttpServletRequest)`와 `Common.setFabSite(HttpServletRequest, String)`로 fabSite 세션 키를 관리한다. fabSite가 비어 있으면 세션에서 가져오고, 있으면 세션에 저장한다.
- **권한 검증**: 별도 인터셉터/시큐리티 어노테이션은 본 모듈에 없음. (전역 SecurityConfig가 있다면 별도 문서 참조.)
- **세션 만료**: fabSite가 세션에서도 NULL이면 `Common.FabSites`의 디폴트가 적용될 수 있음 (Common 구현에 의존).
- **데이터 격리**: `tranDAO.dbExecuteQuery(fabSite, query)`가 `DBManager(fabSite)`로 Logpresso 연결을 분기하여 fabSite별 데이터 소스를 격리한다.
- **CSRF**: Spring Security CSRF 설정에 의존 (본 컨트롤러에서는 별도 토큰 처리 없음).

---

## 6. 비고 / 이슈

### 6.1 `TranCmdFailController.machineNamePop` 메서드명/실동작 불일치

- 메서드명은 `machineNamePop`이고 Javadoc도 "reason 팝업 조회"라고 적혀 있지만, URL은 `tran/pop/reasonPop`이며 실제로는 Reason 팝업 JSP만 리턴한다. 또한 `@ModelAttribute TranCmdFailVo param`을 받지만 어디에도 사용하지 않는다. 메서드명을 `reasonPop`으로 정리하거나 Javadoc만 남기는 것이 명확하다.

### 6.2 `getTableFromFab` switch fall-through

- 다섯 ServiceImpl 모두 동일한 `getTableFromFab(fabSite, fab)` 사본을 가지고 있고, 각 `case`에 `break;`가 없다. 의도된 동작인지 불명확하며, 예를 들어:
  - `fabSite=M15`이고 `fab`이 `M15A`/`M15B`도 `M11A`/`M11B`도 아닐 경우, 코드 흐름이 M11 → C2 → IC case로 흘러가며 잘못된 테이블 명을 반환할 가능성이 있다.
  - 다만 정상 케이스에서는 if문 안에서 return을 하므로 fall-through가 외부로 노출되지 않는다.
- 동일한 `getTableFromFab` 메소드가 5개 ServiceImpl에 중복 구현되어 있다. 공통 유틸로 추출 필요.

### 6.3 `getDataList` 오버로드 + 빈 구현 패턴

- `TranService`는 `getDataList(TranVo)`, `getDataList(TranCmdFailVo)`, `getDataList(TranJobFailVo)` 3개의 오버로드를 모두 선언한다. 각 ServiceImpl은 자기 영역의 한 메서드만 구현하고 나머지는 모두 `return null;` (TODO 주석)을 반환한다.
- `getTranJobHistoryDetail`, `getReasonList`도 마찬가지로 `TranServiceImpl`만 실구현하고 나머지는 빈 구현이다.
- 결과적으로 각 컨트롤러는 잘못된 `@Resource(name=...)`을 주입받으면 정상적인 비즈니스 로직이 호출되지 않고 `null`을 받는다.

### 6.4 메서드 키 중복

- `TranController#getReturnLogList`와 `TranJobHistoryController#getReturnJobLogList`는 둘 다 `method=createTransportJobHistory` 이벤트를 검색한다. 차이는 state=COMPLETED/CANCELED 강제 적용 여부와 결과 fields 구성뿐이다. Logpresso 인덱스 입장에서는 동일 키를 검색하므로 두 화면은 데이터적으로 중복된다.

### 6.5 state 파라미터 파싱 비일관

- `TranController#getReturnLogList`는 `request.getParameter("state")` 단일 String만 받아 List(size=1)에 담는다 → ServiceImpl은 ALL 시 미적용, 단일 값이면 STATE=... 절은 적용하지 않고 COMPLETED/CANCELED 강제 절만 추가. (state 단일 선택이 실질적으로 영향을 주지 않을 수 있음.)
- `TranCmdHistoryController#getReturnCmdLogList`와 `TranJobHistoryController#getReturnJobLogList`는 `state1`/`states` 다중 처리 패턴을 사용한다.

### 6.6 `transportCmdId` 필드명 비일관

- `TranVo`는 `transportCommandId`, `TranCmdFailVo`는 `transportCmdId`로 필드명이 다르다. 클라이언트(JSP) 입장에서는 파라미터명을 영역별로 다르게 보내야 하므로 혼동의 여지가 있다.

### 6.7 Carrier/Reason OR 절 생성의 size==1 분기 중복

- 다수의 ServiceImpl에서 List size==1 / >1을 별도 분기하는 코드가 반복된다. 단일 OR 생성기로 리팩토링 가능.

### 6.8 `transportFab`/`fromFab`/`toFab` Dead Code

- 모든 VO 및 ServiceImpl에 fab별 출발/도착/운반 fab을 별도로 처리하는 코드가 길게 주석으로 남아 있다. 2021.04.12부터 `fab` 단일 필드로 통합되었지만, 잔존 주석이 가독성을 떨어뜨린다.

### 6.9 `TranDAO.dbExecuteQueryStop()` 사용처 없음

- DAO에 쿼리 중단 메소드가 정의되어 있지만 본 모듈의 컨트롤러/서비스에서 호출하는 경로가 없다 (외부 모듈에서 호출될 가능성 있음).

### 6.10 SimpleDateFormat parse 예외 무시

- `TranServiceImpl.getTranJobHistoryDetailQueryParser`는 `from/to` 파싱 실패 시 `catch (Exception ignore) {}` 처리하여 빈 쿼리를 반환한다. 결과적으로 `dataList`가 null이 되며 클라이언트는 에러 사유를 알 수 없다.

### 6.11 컨트롤러 메서드명 충돌

- `TranController#returnLogList`와 `TranJobHistoryController#returnLogList`는 같은 메서드명을 사용한다 (URL은 다름). 메서드명을 영역에 맞춰 정리하면 가독성이 개선된다 (예: TranJobHistoryController는 `returnJobLogList`).
