# 06. Total 통합 로그 조회 모듈

`tot` 패키지는 **Total(통합/집계 모니터링)** 기능을 담당한다.
MCS Log 시스템 내 여러 FAB·머신·레벨의 로그를 모아 조회하는 통합 검색 화면과 신버전(`TotalNew`)에서 도입된 Carrier 흐름 분석 화면을 제공한다.

- 패키지: `com.skhynix.supply.tot`
- 구성: `controller` / `service` / `service.impl` / `dao` / `vo`
- 데이터 소스: 사내 시계열 검색 엔진(`memlookup`, `table`, `search`, `stats`, `sort`, `fields`, `limit` 등의 파이프(`|`) 기반 쿼리)을 사용한다. SQL 매퍼는 없으며, `DBManager`가 fabSite별 접속을 캡슐화한다.

---

## 엔드포인트 요약

| URL | HTTP | Controller#Method | 설명 | View |
|---|---|---|---|---|
| `tot/totalLogList` | GET/POST | TotalController#totalLogList | 통합 로그 조회 화면 진입 | `tot/totalLogList` |
| `tot/ajax/getTotalLogList` | GET/POST | TotalController#getTotalLogList | 통합 로그 조회 결과(JSON, 페이징) | `jsonView` |
| `tot/ajax/getTotalLogListStop` | GET/POST | TotalController#getTotalLogListStop | 진행 중인 조회 강제 중지 | (no view, @ResponseBody void) |
| `tot/pop/machineNamePop` | GET/POST | TotalController#machineNamePop | Machine 선택 팝업 | `tot/pop/machineNamePop` |
| `tot/ajax/getMachineList` | GET/POST | TotalController#getMachineList | Machine 목록(JSON) | `jsonView` |
| `tot/ajax/getMachineListMachineTypeNotNull` | GET/POST | TotalController#getMachineListMachineTypeNotNull | MACHINETYPE not null Machine 목록 | `jsonView` |
| `tot/ajax/getBayFromArea` | GET/POST | TotalController#getBayFromArea | Area 변경 시 Bay 목록 | `jsonView` |
| `tot/ajax/getAreaFromFab` | GET/POST | TotalController#getAreaFromFab | FAB 기준 Area 목록 | `jsonView` |
| `tot/ajax/getMachineTypeFromFab` | GET/POST | TotalController#getMachineTypeFromFab | FAB 기준 MachineType 목록 | `jsonView` |
| `tot/ajax/getFabFromFabSite` | GET/POST | TotalController#getFabFromFabSite | FabSite 기준 FAB 목록(기본/전체) | `jsonView` |
| `tot/main` | GET/POST | TotalController#main | 메인 화면 진입 | `tot/main` |
| `tot/{query}` | GET | TotalController#getRequest | 동적 경로 진입(`tot/main` 렌더) | `tot/main` |
| `tot/filter/ajax/getAreaList` | GET/POST | TotalController#getAreaList | Area 리스트(JSON `@ResponseBody`) | - |
| `tot/filter/ajax/getBayList` | GET/POST | TotalController#getBayList | Bay 리스트(JSON `@ResponseBody`) | - |
| `tot/filter/ajax/getMachineNameList` | GET/POST | TotalController#getMachineNameList | MachineName 리스트(JSON) | - |
| `tot/filter/ajax/getCommMsgNameList` | GET/POST | TotalController#getCommMsgNameList | CommMsg 리스트(JSON) | - |
| `tot/filter/ajax/getMessageNameList` | GET/POST | TotalController#getMessageNameList | Message 리스트(JSON) | - |
| `tot/filter/ajax/getOperationNameList` | GET/POST | TotalController#getOperationNameList | Operation 리스트(JSON) | - |
| `tot/pop/filterPop` | GET/POST | TotalController#filterPop | 필터 팝업 | `tot/pop/filterPop` |
| `common/pop/settingPop` | GET/POST | TotalController#settingPop | 환경설정 팝업 | `common/pop/settingPop` |
| `tot/dashboard/elapsedAnalysis` | GET/POST | TotalController#elapsed | Elapsed 분석 화면 | `tot/elapsedAnalysis` |
| `tot/dashboard/compressAnalysis` | GET/POST | TotalController#elapsed2 | Compress 분석 화면 | `tot/compressAnalysis` |
| `tot/dashboard/monitor` | GET/POST | TotalController#monitor | 모니터 화면 | `tot/monitor` |
| `tot/dashboard/elapsed3` | GET/POST | TotalController#elapsed3 | Dashboard3 화면 | `tot/dashboard3` |
| `totNew/totalNewLogList` | GET/POST | TotalNewController#totalNewLogList | 신규(Carrier 기준) 로그 조회 화면 | `tot/totalNewLogList` |
| `totNew/ajax/totalNewLogList` | GET/POST | TotalNewController#totalNewLogListAjax | 신규 로그 조회 결과(JSON) | `jsonView` |
| `totNew/pop/machineNamePop` | GET/POST | TotalNewController#machineNamePop | 신규 Machine 팝업 | `tot/pop/machineNamePop` |
| `totNew/ajax/getCarrierElapsed` | GET/POST | TotalNewController#getCarrierElapsed | Carrier Elapsed 상세 데이터 | `jsonView` |

---

## Total vs TotalNew 차이

| 항목 | Total (`TotalController` / `TotalServiceImpl`) | TotalNew (`TotalNewController` / `TotalNewServiceImpl`) |
|---|---|---|
| 주 검색 단위 | 로그 라인(레벨/머신/메시지/operation 등 광범위 조건) | Carrier(반송체) 진행/완료 흐름 |
| 핵심 쿼리 | `table FROM TO ... | fields ... | search level in(...)` 또는 fulltext `search` | `proc COMPLETED_CARRIER_FROM_TO[_CARRIER]` 프로시저 + machineType 필터 |
| VO | `TotalVo` (검색 조건 풍부: process/thread/gtxnId/transactionId/messageName/comMsgName/operationName/carrier/commandId/unit/text/fulltext/key 등) | `TotalNewVo` (Carrier 흐름 분석 위주: carrier/totalElapsedTime/elapsedTime/command/comment 등) |
| 추가 메서드 | `getDetailDataList`는 미구현(null) | `getDetailDataList`로 Carrier 상세(addQuery) 수행 |
| 미구현 메서드 | 거의 모든 메서드 실제 동작 | 다수의 인터페이스 메서드를 `return null`로 미구현(같은 `TotalService` 인터페이스를 공유하기 때문) |
| 화면 | `tot/totalLogList`, `tot/main`, dashboard 4종 | `tot/totalNewLogList` 한 화면 + Carrier popup/detail |

요약: **TotalNew는 Carrier 단위 통합 분석을 위해 별도 서비스 구현체와 VO를 두었으며, `TotalService` 인터페이스를 공유하되 Carrier 관련 메서드(`getDataList(TotalNewVo)`, `getDetailDataList`)만 실제 구현되어 있다.**

---

## controller/TotalController.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/controller/TotalController.java`
- **목적**: 통합(Total) 로그 조회 화면 진입 및 AJAX 데이터 제공. 화면별 필터(FAB/Area/Bay/MachineType/Machine/Level), 페이징, fabSite 세션 처리를 담당한다.
- **클래스 시그니처**
  ```java
  @Controller
  public class TotalController
  ```
- **주입 의존성**
  - `@Resource(name = "totalService") private TotalService totService` — Total 비즈니스 로직
  - `@Autowired SessionLocaleResolver localeResolver` — i18n 처리
  - `Log log` / `org.slf4j.Logger logger`

### Public methods

| Method | @RequestMapping | 주요 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `totalLogList` | `tot/totalLogList` | `@ModelAttribute TotalVo param`, `HttpServletRequest request` | `ModelAndView` | Total 로그 조회 화면 이동. `fabSite` 세션 적용 후 기본 fab/level(WELL,WARN,ERROR,FATAL)을 모델에 채워 `tot/totalLogList` 뷰로 이동. |
| `getTotalLogList` | `tot/ajax/getTotalLogList` | `TotalVo param`, `request` | `ModelAndView`(jsonView) | AJAX 통합 로그 조회. `searchDelay`, `page`, `rows`, `fab[1..n]`, `level[1..n]`, `machineTypes`(콤마구분), `from/to`(기본: 현재시각·10분전)를 정규화하여 `totService.getDataList(TotalVo)` 호출. `Paging`을 적용하고 jqGrid 형식(`page/total/records/rows`)으로 응답. |
| `getTotalLogListStop` | `tot/ajax/getTotalLogListStop` | `request` | `void` `@ResponseBody` | 진행 중인 조회를 강제 중지(`totService.getTotalLogListStop()`). |
| `machineNamePop` | `tot/pop/machineNamePop` | `TotalVo param`, `request` | `ModelAndView` | Machine 선택 팝업. `totService.getMachineTypeFromFab(new MachineVo())` 결과를 `machineTypeInfoList`로 전달. |
| `getMachineList` | `tot/ajax/getMachineList` | `MachineVo param`, `request` | jsonView | fabSite 기준 Machine 목록(`getMachineNameList(MachineVo)`). |
| `getMachineListMachineTypeNotNull` | `tot/ajax/getMachineListMachineTypeNotNull` | `MachineVo`, `request` | jsonView | MACHINETYPE not null 조건의 Machine 목록. |
| `getBayFromArea` | `tot/ajax/getBayFromArea` | `MachineVo`, `request` | jsonView | 선택 Area의 Bay 목록. |
| `getAreaFromFab` | `tot/ajax/getAreaFromFab` | `MachineVo`, `request` | jsonView | 선택 FAB의 Area 목록. |
| `getMachineTypeFromFab` | `tot/ajax/getMachineTypeFromFab` | `MachineVo`, `request` | jsonView | 선택 FAB의 MachineType 목록. |
| `getFabFromFabSite` | `tot/ajax/getFabFromFabSite` | `FabVo`, `request` | jsonView | FabSite/메뉴 기준 FAB 전체 리스트(`Common.getFabList`) 및 기본 리스트(`Common.getBasicFabList`)를 함께 반환. |
| `main` | `tot/main` | `TotalVo`, `request` | `ModelAndView` | 메인 페이지(`tot/main`)로 이동. 세션/Locale 정보 로깅. |
| `getRequest` | `tot/{query}` (GET) | `@PathVariable String query` | `ModelAndView` | 동적 경로 진입을 수용하여 `tot/main` 뷰로 폴백 처리. |
| `getAreaList` | `tot/filter/ajax/getAreaList` | `String fabSite` | `@ResponseBody List<List>` | Area 리스트(필터용). |
| `getBayList` | `tot/filter/ajax/getBayList` | `String fabSite` | `@ResponseBody List<List>` | Bay 리스트. |
| `getMachineNameList` | `tot/filter/ajax/getMachineNameList` | `String fabSite` | `@ResponseBody List<List>` | MachineName 리스트. |
| `getCommMsgNameList` | `tot/filter/ajax/getCommMsgNameList` | `String fabSite` | `@ResponseBody List<List>` | CommMsg 리스트. |
| `getMessageNameList` | `tot/filter/ajax/getMessageNameList` | `String fabSite` | `@ResponseBody List<List>` | Message 리스트. |
| `getOperationNameList` | `tot/filter/ajax/getOperationNameList` | `String fabSite` | `@ResponseBody List<List>` | Operation 리스트. |
| `filterPop` | `tot/pop/filterPop` | `TotalVo`, `request` | `ModelAndView` | 필터 팝업 뷰. |
| `settingPop` | `common/pop/settingPop` | `TotalVo`, `request` | `ModelAndView` | 환경설정 팝업 뷰. |
| `elapsed` | `tot/dashboard/elapsedAnalysis` | `TotalVo` | `ModelAndView` | Elapsed 분석 뷰. |
| `elapsed2` | `tot/dashboard/compressAnalysis` | `TotalVo` | `ModelAndView` | Compress 분석 뷰. |
| `monitor` | `tot/dashboard/monitor` | `TotalVo` | `ModelAndView` | 모니터링 뷰. |
| `elapsed3` | `tot/dashboard/elapsed3` | `TotalVo` | `ModelAndView` | Dashboard3 뷰. |

> 패턴: 모든 메서드에서 `param.getFabSite()`가 비어 있으면 세션의 fabSite를 읽고(`Common.getFabSite`), 값이 있으면 세션에 setter(`Common.setFabSite`). 이는 멀티 FAB 사이트 간 컨텍스트 전환을 지원하기 위한 일관된 처리이다.

---

## controller/TotalNewController.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/controller/TotalNewController.java`
- **목적**: 신규(Carrier 흐름 중심) 로그 조회 화면을 위한 Controller.
- **클래스 시그니처**
  ```java
  @Controller
  public class TotalNewController
  ```
- **주입 의존성**
  - `@Resource(name = "totalNewService") private TotalService totService` — TotalNewServiceImpl 빈을 주입(같은 `TotalService` 인터페이스).
  - `Log log`

### Public methods

| Method | @RequestMapping | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `totalNewLogList` | `totNew/totalNewLogList` | `@ModelAttribute TotalNewVo param`, `request` | `ModelAndView`(`tot/totalNewLogList`) | 신규 Carrier 로그 조회 화면 진입 + 첫 조회. fabSite 세션 동기화, `machineTypes` 콤마 파싱, 기본 from/to(현재·10분전), `Paging` 적용. 결과의 첫 행 `count` 필드로 전체건수 계산. |
| `totalNewLogListAjax` | `totNew/ajax/totalNewLogList` | `TotalNewVo`, `request` | `ModelAndView`(jsonView) | 동일 로직의 AJAX 버전. `total/records/paging/rows/param`을 jsonView로 반환. |
| `machineNamePop` | `totNew/pop/machineNamePop` | `TotalVo`, `request` | `ModelAndView`(`tot/pop/machineNamePop`) | 신규 화면용 Machine 팝업. `totService.getSelectList(fabSite)`로 BAY/MACHINE/COMM_MSG/MESSAGE 통합 목록을 가져옴(TotalNewServiceImpl에서는 미구현되어 null). |
| `getCarrierElapsed` | `totNew/ajax/getCarrierElapsed` | `TotalNewVo`, `request` | jsonView | `addQuery` 파라미터로 임의의 검색식을 받아 `totService.getDetailDataList(fabSite, addQuery)`를 호출. Carrier 상세 분석 데이터를 반환. |

---

## service/TotalService.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/TotalService.java`
- **목적**: Total/TotalNew 두 구현체가 공유하는 통합 서비스 인터페이스. 로그 조회 + 필터용 lookup 조회를 모두 정의한다.
- **시그니처**: `public interface TotalService`
- **공개 메서드 목록**

| Method | 파라미터 | 반환 | 설명 |
|---|---|---|---|
| `getDataList(TotalVo)` | `TotalVo` | `List<Map>` | 통합 로그 조회 |
| `getTotalLogListStop()` | - | `void` | 진행 중 조회 중단 |
| `getDataList(TotalNewVo)` | `TotalNewVo` | `List<Map>` | Carrier 신규 로그 조회 |
| `getDetailDataList(String fabSite, String addQuery)` | - | `List<Map>` | 신규 로그 상세(임의 쿼리) |
| `getSelectList(String fabSite)` | - | `List<Map>` | BAY/MACHINE/COMM_MSG/MESSAGE 통합 목록 |
| `getBayNameList(String fabSite)` | - | `List<Map>` | BayName 리스트 |
| `getMachineNameList(MachineVo)` | - | `List<Map>` | MachineName 리스트(Vo 필터) |
| `getMachineNameListMachineTypeNotNull(MachineVo)` | - | `List<Map>` | MACHINETYPE not null Machine 리스트 |
| `getMachineNameList(String fabSite)` | - | `List<Map>` | MachineName 리스트(전체) |
| `getCommMsgNameList(String fabSite)` | - | `List<Map>` | CommMsg 리스트 |
| `getMessageNameList(String fabSite)` | - | `List<Map>` | Message 리스트 |
| `getMachineNameListByType(TotalVo)` | - | `List<Map>` | MachineType별 Machine 리스트 |
| `getMachineNameListByTypeMachineTypeNotNull(TotalVo)` | - | `List<Map>` | 위 + MACHINETYPE not null |
| `getOperationNameList(String fabSite)` | - | `List<Map>` | Operation 리스트 |
| `getAreaNameList(String fabSite)` | - | `List<Map>` | Area 리스트 |
| `getBayFromAreaList(MachineVo)` | - | `List<Map>` | Area 기준 Bay 리스트 |
| `getAreaFromFabList(MachineVo)` | - | `List<Map>` | FAB 기준 Area 리스트 |
| `getMachineTypeFromFab(MachineVo)` | - | `List<Map>` | FAB 기준 MachineType 리스트 |

> 주석으로 정의되어 있던 `getXmlList`, `getXmlListGroup`은 200827 hgJeon이 사용안함 주석처리(인터페이스에 노출 안됨).

---

## service/impl/TotalServiceImpl.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/impl/TotalServiceImpl.java`
- **목적**: Total 통합 로그 조회 핵심 구현체. fabSite/fab별 테이블 매핑, 페이지 limit/offset, level/processName/threadName/gtxnId/transactionId/messageName/comMsgName/operationName/carrier/commandId/unit/text/fulltext 등 다양한 조건을 파이프(`|`) 기반 검색 쿼리로 빌드한다.
- **클래스 시그니처**
  ```java
  @Service("totalService")
  public class TotalServiceImpl implements TotalService
  ```
- **주입 의존성**: `@Resource(name = "totalDAO") TotalDAO Client`

### 주요 메서드

| Method | 설명 |
|---|---|
| `getDataList(TotalVo)` | (offset, limit) 계산 → `getQueryParser(totVo)`로 쿼리 빌드 → `limit`/`sort`/`eval No=seq()+offset` 추가 → `Client.dbExecuteQuery(fabSite, query)` 호출. |
| `getTotalLogListStop()` | `Client.dbExecuteQueryStop()` 호출. |
| `getSelectList(String fabSite)` | `machine_list`(BAYNAME), `machine_list`(MACHINENAME), `comm_msg_name`, `message_name` 4개 lookup을 합쳐 반환. |
| `getMachineNameListByType(TotalVo)` | `Common.sGetMachineQuery` + `search TYPE="..."` 형태로 머신 리스트 조회. |
| `getMachineNameListByTypeMachineTypeNotNull(TotalVo)` | 위와 동일하지만 `search isnotnull(MACHINETYPE)` 조건 추가. |
| `getAreaNameList(String fabSite)` | `memlookup name=machine_list | stats count by AREANAME | fields AREANAME | search len(AREANAME) > 1` |
| `getBayNameList(String fabSite)` | `memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1` |
| `getMachineNameList(MachineVo)` | `getMachineQueryParser(machineVo)` 빌드 → 실행. |
| `getMachineNameListMachineTypeNotNull(MachineVo)` | `getMachineQueryParserMachineTypeNotNull(machineVo)` 빌드 → 실행. |
| `getMachineNameList(String fabSite)` | `memlookup name=machine_list | search len(MACHINENAME) > 1 | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME` |
| `getCommMsgNameList(String fabSite)` | `memlookup name=comm_msg_name | sort COMM_MSG` |
| `getMessageNameList(String fabSite)` | `memlookup name=message_name | sort MESSAGE` |
| `getOperationNameList(String fabSite)` | `memlookup name=operation_name | sort OPERATION` |
| `getAreaFromFabList(MachineVo)` / `getBayFromAreaList(MachineVo)` | `getAreaBayQueryParser(machineVo)`로 공통 쿼리 생성. AreaName 유무에 따라 Bay 또는 Area를 stats한다. |
| `getMachineTypeFromFab(MachineVo)` | `memlookup name=machine_list` + `SHOPNAME` IN-필터(`Common.getColumnFromFab(fabSite, fab)`) + `stats count by TYPE | sort TYPE` |
| `getDataList(TotalNewVo)` | 본 클래스에서는 `return null` (TotalNew 전용). |
| `getDetailDataList(String, String)` | 본 클래스에서는 `return null` (TotalNew 전용). |

### 내부 헬퍼 (private/package)

- `getQueryParser(TotalVo)` — 가장 큰 메서드(약 800라인 분량). 조건 미지정 시 `table` 형식 기본 쿼리, 조건 존재 시 `fulltext` 검색 쿼리로 분기. process/carrier/thread/gtxnId/transactionId/messageName/comMsgName/operationName/commandId/unit/text/areaName/bayName/machineType/machineName/level 등 모든 조건의 단일·콤마 멀티값을 `AND/OR` 검색 식으로 결합. fulltext 검색 시 `*term*` 와일드카드와 따옴표 이스케이프 처리.
- `getMachineQueryParser(MachineVo)` / `getMachineQueryParserMachineTypeNotNull(MachineVo)` — Machine 조회용 SHOPNAME(=FAB)/TYPE/AREA/BAY 필터 + `stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME`.
- `getAreaBayQueryParser(MachineVo)` — SHOPNAME(FAB) 필터링 후 AreaName 입력 시 Bay 조회, 미입력 시 Area 조회 쿼리.
- `getTableFromFab(String fabSite, String fab, boolean isAll)` — fabSite × fab 조합으로 대상 시계열 테이블 상수를 매핑(`Common.sTS_DATA_*` 또는 `Common.sTS_DATA_VIEW_*`). M14(A/B), M15(A/B), M11(A/B), C2(C2/C2F), IC(M14A/M14B/M16A/M16B)를 지원. `isAll=true`이면 INFO/FINE/DEBUG 포함, `false`면 view 테이블(레벨 축소).

---

## service/impl/TotalNewServiceImpl.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/service/impl/TotalNewServiceImpl.java`
- **목적**: Carrier 단위 신규 로그 조회 서비스. `TotalService`를 구현하지만, Carrier 관련 메서드(`getDataList(TotalNewVo)`, `getDetailDataList`, `getBayNameList`, `getCommMsgNameList`, `getMessageNameList`, `getMachineTypeFromFab`)만 실제 구현되어 있고 나머지는 빈 구현(`return null`).
- **클래스 시그니처**
  ```java
  @Service("totalNewService")
  public class TotalNewServiceImpl implements TotalService
  ```
- **주입 의존성**: `@Resource(name = "totalDAO") TotalDAO Client`

### 주요 메서드

| Method | 설명 |
|---|---|
| `getDataList(TotalNewVo)` | Carrier 값이 있으면 `getCompletedCarrierListQueryByCarrier`, 없으면 `getCompletedCarrierListQuery`로 `proc COMPLETED_CARRIER_FROM_TO[_CARRIER]` 호출 쿼리를 만들고 `limit offset limit` + `sort _TIME`을 append하여 실행. |
| `getDetailDataList(String fabSite, String addQuery)` | 컨트롤러로부터 전달된 임의 검색식을 그대로 실행 (Carrier 상세). |
| `getBayNameList(String fabSite)` | `memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search BAYNAME != ""` |
| `getCommMsgNameList(String fabSite)` | `memlookup name=comm_msg_name | sort COMM_MSG` |
| `getMessageNameList(String fabSite)` | `memlookup name=message_name | sort MESSAGE` |
| `getMachineTypeFromFab(MachineVo)` | `memlookup name=machine_list` + SHOPNAME(FAB) 필터 + `stats count by TYPE | sort TYPE`. TotalServiceImpl과 동일 로직. |
| 그 외 메서드들 | `getDataList(TotalVo)`, `getSelectList`, `getMachineNameList(*)`, `getMachineNameListByType*`, `getAreaNameList`, `getOperationNameList`, `getBayFromAreaList`, `getAreaFromFabList`, `getTotalLogListStop`, `getMachineNameListMachineTypeNotNull` 등은 모두 `return null;` 또는 비어있는 메서드 본문. |

### 내부 헬퍼

- `getCompletedCarrierListQueryByCarrier(TotalNewVo)` — `Common.sProc + COMPLETED_CARRIER_FROM_TO_CARRIER(from,to,carrier)` + machineType `search in` 필터.
- `getCompletedCarrierListQuery(TotalNewVo)` — Carrier 없이 from/to만 받는 동일 프로시저 호출 + machineType 필터.
- `getQueryParser(TotalNewVo)` — AreaName/BayName/MachineType/MachineName/Level/Process/Thread/TransactionId/MessageName/Carrier/CommandId/Unit를 조건으로 검색식을 만드는 헬퍼(현재 흐름에서는 직접 호출되지 않음, 향후 확장 대비).

---

## dao/TotalDAO.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/dao/TotalDAO.java`
- **목적**: Total 모듈의 단일 DAO. MyBatis Mapper를 사용하지 않고, `DBManager` 인스턴스를 매 호출마다 생성하여 외부 시계열 검색 엔진에 쿼리를 위임한다. SQL Mapper ID는 사용되지 않는다.
- **시그니처**
  ```java
  @Repository("totalDAO")
  public class TotalDAO
  ```
- **필드**: `DBManager dbManager`
- **메서드**

| Method | 시그니처 | 설명 |
|---|---|---|
| `TotalDAO()` | 기본 생성자 | - |
| `dbExecuteQuery(String fabSite, String queryStmt)` | `List<Map>` | `new DBManager(fabSite)` 생성 후 `dbManager.executeQuery(queryStmt)` 호출. 예외 시 warn 로그, finally에서 `dbManager=null`. (주석처리된 ThreadPool/Callable 비동기 실행 흔적이 남아있음.) |
| `dbExecuteQueryStop()` | `void` | 진행 중인 쿼리 중단(`dbManager.executeQueryStop()`). |

> **SQL Mapper IDs**: 없음. 모든 쿼리는 서비스 계층에서 문자열로 빌드되어 `dbExecuteQuery`로 전달된다.

---

## vo/TotalVo.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/vo/TotalVo.java`
- **목적**: 통합(Total) 로그 조회 화면의 전체 검색 조건 + 페이징 정보 캐리어 VO.

| 필드 | 타입 | 역할 |
|---|---|---|
| fabSite | String | 대상 FAB 사이트(M14/M15/M11/C2/IC 등). 세션과 동기화. |
| pageNum | String | 현재 페이지 번호 |
| rowNum | String | 페이지당 행 수 |
| areaName | String | Area(ALL/특정 Area명) |
| bayName | String | Bay(ALL/특정 Bay명) |
| machineType | List\<String> | Machine Type 다중선택(ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT 등) |
| machineName | List\<String> | Machine 다중선택 |
| fab | List\<String> | FAB 다중선택(ALL/M14A/M14B/...) |
| level | List\<String> | 로그 레벨 다중(ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL) |
| searchOption | String | 조건 결합자 AND/OR |
| process | String | Process 명(콤마 멀티 지원) |
| thread | String | Thread 명(콤마 멀티) |
| gtxnId | String | M16 Global Transaction Id |
| transactionId | String | Transaction Id |
| messageName | String | Message 명 |
| comMsgName | String | Comm Msg 명 |
| operationName | String | Operation 명 |
| carrier | String | Carrier ID |
| commandId | String | Command Id |
| unit | String | Unit |
| text | String | TEXT 단순 검색 |
| fulltext | String | TEXT fulltext 검색(`*term*` 와일드카드) |
| key | List\<String> | KEY 다중 |
| messageName_m | String | M14 통합 로그조회용 messageName |
| comMsgName_m | String | M14 통합 로그조회용 comMsgName |
| operationName_m | String | M14 통합 로그조회용 operationName |
| from | String | 검색 시작 시각 `yyyyMMddHHmmss` |
| to | String | 검색 종료 시각 `yyyyMMddHHmmss` |

> 전 필드에 getter/setter가 정의되어 있음.

---

## vo/TotalNewVo.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tot/vo/TotalNewVo.java`
- **목적**: 신규(Carrier 흐름) 로그 조회 화면의 검색 조건 캐리어 VO.

| 필드 | 타입 | 역할 |
|---|---|---|
| fabSite | String | FAB 사이트 |
| pageNum | String | 페이지 번호 |
| rowNum | String | 페이지당 행 수 |
| areaName | String | Area |
| bayName | String | Bay |
| machineType | List\<String> | MachineType 다중 |
| machineName | List\<String> | MachineName 다중 |
| level | List\<String> | 로그 레벨 다중 |
| searchOption | String | 조건 결합자(AND/OR) |
| carrier | String | Carrier ID(핵심 키) |
| totalElapsedTime | String | Carrier 총 소요 시간 |
| elapsedTime | String | 구간 소요 시간 |
| command | String | Command |
| messageName | String | Message |
| process | String | Process |
| transactionId | String | Transaction Id |
| commandId | String | Command Id |
| unit | String | Unit |
| thread | String | Thread |
| comment | String | 비고/Comment |
| from | String | 시작 시각 |
| to | String | 종료 시각 |

> 전 필드 getter/setter 제공. `TotalVo`와 달리 `gtxnId/comMsgName/operationName/text/fulltext/key/fab/*_m` 등은 없고, Carrier 분석용 `totalElapsedTime/elapsedTime/command/comment`가 추가됨.

---

## 데이터 흐름

```
[Browser/JSP]
    │  HTTP (tot/* or totNew/*)
    ▼
TotalController / TotalNewController
    │  - fabSite 세션 동기화 (Common.getFabSite / setFabSite)
    │  - request 파라미터 → TotalVo / TotalNewVo / MachineVo / FabVo 바인딩
    │  - Paging 객체 준비 (pageNum, rowNum)
    ▼
TotalService (interface)
    ├─ TotalServiceImpl       ("totalService" 빈)  → Total 일반 조회
    └─ TotalNewServiceImpl    ("totalNewService" 빈) → Carrier 흐름 조회
           │
           │  - Vo의 모든 조건을 파이프(|) 기반 검색식으로 빌드
           │     · getQueryParser(TotalVo) / getCompletedCarrierListQuery(TotalNewVo)
           │     · getMachineQueryParser / getAreaBayQueryParser / getTableFromFab
           │  - limit offset/rowNum, sort _TIME, eval No=seq() 추가
           ▼
TotalDAO ("totalDAO" 빈)
    │  - new DBManager(fabSite)
    │  - dbManager.executeQuery(queryStmt) 또는 executeQueryStop()
    ▼
DBManager (외부 시계열 검색 엔진 게이트웨이)
    │
    ▼
[memlookup / table / proc / search / stats / fields / sort 결과]
    ▲
    │  List<Map> 반환 (각 Map = 하나의 로그 row)
Service → Controller
    │
    │  - 첫 행의 count로 Paging.numberOfRecords 세팅 → makePaging()
    │  - jqGrid 호환(`page, total, records, rows`) 또는 모델 전달
    ▼
View (`tot/*` JSP, `jsonView`)
```

핵심 패턴 요약
1. **fabSite 컨텍스트**: 모든 컨트롤러 메서드가 동일한 if/else 패턴으로 세션 fabSite를 sync한다.
2. **쿼리 빌드는 서비스 계층**: DAO는 단순 실행기. 모든 조건문/멀티값/AND-OR 결합 로직은 서비스가 String/StringBuilder로 조립한다.
3. **두 가지 결과 표현**: 화면 진입(`ModelAndView` + JSP 뷰명)과 AJAX(`jsonView` + `rows/total/records`)가 분리되어 있다.
4. **TotalNew는 Carrier 중심**: `proc COMPLETED_CARRIER_FROM_TO[_CARRIER]` 프로시저 호출 결과를 `List<Map>`으로 받아 Carrier 단위 분석을 수행한다.
