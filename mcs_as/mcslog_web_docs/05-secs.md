# 05. SECS / EI 로그 모듈

본 문서는 `com.skhynix.supply.secs` 패키지의 10개 파일을 정리한다. 이 패키지는 반도체 장비와의 통신 로그를 조회하는 두 개의 하위 모듈로 구성된다.

- **SECS** (SEMI Equipment Communications Standard, 반도체 장비 통신 표준): 호스트와 장비 간 메시지 송수신 로그
- **EI** (Equipment Interface): EI / CS / DS / TS 등 장비 인터페이스 통합 로그

---

## 엔드포인트 요약

| HTTP URL | Controller 메서드 | 반환 View / Body | 설명 |
|---|---|---|---|
| `ei/eiLogList` | `EiLogController.eiLocLogList` | `ei/eiLogList` | EI 로그 조회 화면 초기 진입 |
| `/ei/ajax/getEiLogList.do` | `EiLogController.getList` | `jsonView` | EI 로그 목록 Ajax 조회 (페이징) |
| `ei/pop/textDetailPop` | `EiLogController.filterPop` | `ei/pop/textDetailPop` | 텍스트 상세 팝업 |
| `ei/pop/textAreaPop` | `EiLogController.textFilterPop` | `ei/pop/textAreaPop` | 텍스트 입력(area) 팝업 |
| `ei/ajax/getEiQueryStop` | `EiLogController.getEiQueryStop` | (void) | EI 조회 쿼리 강제 취소 |
| `tot/filter/ajax/getProcessList` | `EiLogController.getSecsList` | `@ResponseBody List<List>` | TS Process 목록 조회 |
| `tot/filter/ajax/getSelectProcessList` | `EiLogController.getSecsFabList` | `jsonView` | 선택된 Fab/Type 기준 Process 목록 |
| `secs/secsLogList` | `SecsLogController.secsLocLogList` | `secs/secsLogList` | SECS 로그 조회 화면 초기 진입 |
| `/secs/ajax/getsecsLogList.do` | `SecsLogController.getList` | `jsonView` | SECS 로그 목록 Ajax 조회 (페이징) |
| `tot/filter/ajax/getSecsList` | `SecsLogController.getSecsList` | `@ResponseBody List<List>` | SECS 장비(SECSII) 목록 |
| `tot/filter/ajax/getSecsFabList` | `SecsLogController.getSecsFabList` | `jsonView` | 선택된 Fab 기준 SECSII 목록 |
| `ei/ajax/getSecsQueryStop` | `SecsLogController.getSecsQueryStop` | (void) | SECS 조회 쿼리 강제 취소 (URL prefix는 ei로 등록되어 있음) |

---

## EI vs SECS 비교

| 항목 | EI 모듈 | SECS 모듈 |
|---|---|---|
| 대상 로그 | TS, EI, CS, DS (Equipment Interface 계열) | SECS-II 메시지 송수신 로그 |
| 주요 컬럼 | CLASS, FAB, LOG, HOST, TEXT_XML, PROCESS | S/F, SB, NAME, DATA, SKEY, SECS, HOST |
| 필터 조건 | logType, fab, level, host, process, text | fab, level, host, secs(SECSII 장비명), text |
| Level 옵션 기본값 | WELL, WARN, ERROR, FATAL | ALL (TIME, INFO, WARN, RECV, SEND) |
| 화면 진입 URL | `ei/eiLogList` | `secs/secsLogList` |
| 데이터 조회 URL | `/ei/ajax/getEiLogList.do` | `/secs/ajax/getsecsLogList.do` |
| 보조 목록 조회 | Process 목록 (`getProcessList`) | SECSII 장비 목록 (`getSecsList` → machine_list) |
| Controller | `EiLogController` | `SecsLogController` |
| Service | `EiService` / `EiServiceImpl` | `SecsService` / `SecsServiceImpl` |
| DAO | `EiDAO` | `SecsDAO` |
| VO | `EiVo` (process, log, eiTextConditionCheckBox) | `SecsVo` (carrier, vehicle, secs, ports, secsTextConditionCheckBox) |

---

## 파일별 상세

### 1) controller/EiLogController.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/controller/EiLogController.java`
- **목적**: EI / CS / DS / TS 로그 조회 화면 및 Ajax 데이터 제공 컨트롤러. FabSite 세션 처리, 검색 파라미터(fab, logType, host, level, time) 수집 후 서비스에 위임.
- **클래스 시그니처**: `@Controller public class EiLogController`
- **주입 의존성**: `@Resource(name="eiService") EiService eiService`

#### Public 메서드

| 메서드 | @RequestMapping | 파라미터 | 반환 | 설명 (Korean) |
|---|---|---|---|---|
| `eiLocLogList` | `ei/eiLogList` | `@ModelAttribute EiVo param`, `HttpServletRequest` | `ModelAndView` (view: `ei/eiLogList`) | EI 로그 조회 화면 진입. FabSite를 세션에서 가져오거나 갱신하고, fab 목록·level(WELL/WARN/ERROR/FATAL 기본)을 model에 세팅. |
| `getList` | `/ei/ajax/getEiLogList.do` | `@ModelAttribute EiVo param`, `HttpServletRequest` | `ModelAndView` (jsonView) | 페이지(page, rows), 검색지연(searchDelay), fab/logType(TS/EI/CS/DS)/host/level 파라미터 수집. From/To 기본값은 현재시각과 10분 전. `Paging`으로 페이징 처리 후 `eiService.getDataList` 호출. |
| `getSecsList` | `tot/filter/ajax/getProcessList` | `String fabSite` | `@ResponseBody List<List>` | TS Process 목록 조회. `eiService.getProcessList(fabSite)` 결과를 List<List>로 래핑하여 반환. |
| `filterPop` | `ei/pop/textDetailPop` | `@ModelAttribute TotalVo`, `HttpServletRequest` | `ModelAndView` | 텍스트 상세보기 팝업 뷰 리턴. |
| `textFilterPop` | `ei/pop/textAreaPop` | `@ModelAttribute TotalVo`, `HttpServletRequest` | `ModelAndView` | 텍스트 입력용 팝업 뷰 리턴. |
| `getSecsFabList` | `tot/filter/ajax/getSelectProcessList` | `@ModelAttribute MachineVo`, `HttpServletRequest` | `ModelAndView` (jsonView) | 선택된 fab/type 기준 Process 목록 조회. `eiService.getSelectProcessList` 호출. |
| `getEiQueryStop` | `ei/ajax/getEiQueryStop` | `HttpServletRequest` | `void` (`@ResponseBody`) | 실행 중인 EI 조회 쿼리를 즉시 중단. `eiService.getRawLogQueryStop()` 호출. |

---

### 2) controller/SecsLogController.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/controller/SecsLogController.java`
- **목적**: SECS 메시지 로그 조회 화면 및 Ajax 데이터 제공 컨트롤러. SECSII 장비 목록 조회·쿼리 취소 기능 포함.
- **클래스 시그니처**: `@Controller public class SecsLogController`
- **주입 의존성**: `@Resource(name="secsService") SecsService secsService`

#### Public 메서드

| 메서드 | @RequestMapping | 파라미터 | 반환 | 설명 (Korean) |
|---|---|---|---|---|
| `secsLocLogList` | `secs/secsLogList` | `@ModelAttribute SecsVo param`, `HttpServletRequest` | `ModelAndView` (`secs/secsLogList`) | SECS 로그 조회 화면 진입. FabSite 세션 처리, fab 목록 및 SECS용 level 목록(TIME/INFO/WARN/RECV/SEND), 기본값 ALL 세팅. |
| `getList` | `/secs/ajax/getsecsLogList.do` | `@ModelAttribute SecsVo param`, `HttpServletRequest` | `ModelAndView` (jsonView) | page/rows/searchDelay/fab/host/level 파라미터 수집. From/To 기본값은 현재시각과 10분 전. `secsService.getDataList`로 데이터 조회 후 페이징. |
| `getSecsList` | `tot/filter/ajax/getSecsList` | `String fabSite` | `@ResponseBody List<List>` | SECSII 장비 목록(`machine_list`) 조회. List<List>로 래핑. |
| `getSecsFabList` | `tot/filter/ajax/getSecsFabList` | `@ModelAttribute MachineVo`, `HttpServletRequest` | `ModelAndView` (jsonView) | 선택된 Fab 기준 SECSII 장비 목록 조회. `secsService.getSecsFabList` 호출. |
| `getSecsQueryStop` | `ei/ajax/getSecsQueryStop` | `HttpServletRequest` | `void` (`@ResponseBody`) | 실행 중인 SECS 조회 쿼리를 즉시 중단. (URL 접두사가 `ei/`로 등록된 점 유의) |

---

### 3) service/EiService.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/service/EiService.java`
- **목적**: EI/CS/DS/TS 로그 조회용 서비스 인터페이스 정의.
- **클래스 시그니처**: `public interface EiService`

#### 메서드

| 메서드 | 반환 | 설명 |
|---|---|---|
| `getDataList(EiVo eiVo)` | `List<Map>` | EI 로그 메인 조회. |
| `getProcessList(String fabSite)` | `List<Map>` | TS 관련 Process 목록 조회 (초기 로딩 시 `ts*` 검색). |
| `getSelectProcessList(MachineVo machineVo)` | `List<Map>` | 사용자가 선택한 type/fab 조건의 Process 목록. |
| `getRawLogQueryStop()` | `void` | 실행 중인 쿼리 cancel. |

---

### 4) service/SecsService.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/service/SecsService.java`
- **목적**: SECS 로그 조회용 서비스 인터페이스 정의.
- **클래스 시그니처**: `public interface SecsService`

#### 메서드

| 메서드 | 반환 | 설명 |
|---|---|---|
| `getDataList(SecsVo secsVo)` | `List<Map>` | SECS 로그 메인 조회. |
| `getSelectList(String fabSite)` | `List<Map>` | `machine_list`에서 SECSII/FAB 목록 (MACHINETYPE not null 필터). |
| `getSecsList(String fabSite)` | `List<Map>` | `machine_list`에서 SECSII 정렬 목록. |
| `getSecsFabList(MachineVo machineVo)` | `List<Map>` | 선택된 Fab 조건의 SECSII 목록. |
| `getRawLogQueryStop()` | `void` | 실행 중인 쿼리 cancel. |

---

### 5) service/impl/EiServiceImpl.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/service/impl/EiServiceImpl.java`
- **목적**: EI 로그 조회 비즈니스 로직 구현. 화면에서 선택된 logType(TS/EI/CS/DS)·fab·level에 따라 동적으로 테이블명을 결정하고 검색 쿼리(파이프라인 형식)를 구성한다.
- **클래스 시그니처**: `@Service("eiService") public class EiServiceImpl implements EiService`
- **주입 의존성**: `@Resource(name="eiDAO") EiDAO Client`

#### 메서드

| 메서드 | 설명 |
|---|---|
| `getDataList(EiVo eiVo)` | `getQueryParser` 결과에 `limit`/`sort`/`eval No=seq()+offset` 추가 후 `Client.dbExecuteQuery(fabSite, query)` 실행. |
| `getQueryParser(EiVo)` *(private)* | `table=` 절, FAB/LEVEL/HOST search, PROCESS·TEXT 조건(쉼표 분리 multi 검색, AND/OR 옵션, `*` 와일드카드 처리), fields 정렬을 단계적으로 조립. TS인 경우 PROCESS 문자열을 case로 분기해 FAB/LOG/HOST를 eval로 산출. |
| `getTableSelect(fabSite, fab, logType, isAll)` *(private)* | logType별로 TS/EI/CS/DS 테이블명을 결정 (LinkedHashSet으로 중복 제거). |
| `getTSTableFromFab` / `getEITableFromFab` / `getCSTableFromFab` / `getDSTableFromFab` *(private)* | fabSite(M14/M15/M11/C2/IC)·fab 조합에 따라 `Common.sTS_DATA_*`, `Common.sEI_DATA_*`, `Common.sCS_DATA_*`, `Common.sDS_DATA_*` 상수를 반환. TS의 경우 `isAll`이 false면 `_VIEW_` 테이블을 사용. |
| `getProcessList(String fabSite)` | `memlookup name=ProcessList2 \| sort PROCESS \| search PROCESS=="ts*" \| stats count by PROCESS \| fields PROCESS` 쿼리 실행. |
| `getSelectProcessList(MachineVo)` | `getSelectProcessQuery`로 PROCESS/FAB 필터링 쿼리 조립 후 실행. |
| `getSelectProcessQuery(MachineVo)` *(private)* | `memlookup name=ProcessList2 \| sort PROCESS` 기반으로 selectType/selectFab을 search in 절로 추가. |
| `getRawLogQueryStop()` | `Client.dbExecuteQueryStop()` 호출, 실패 시 로그만 남김. |

---

### 6) service/impl/SecsServiceImpl.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/service/impl/SecsServiceImpl.java`
- **목적**: SECS 로그 조회 비즈니스 로직 구현. fab별 SECS 테이블 라우팅, SECS·LEVEL·HOST·TEXT 검색 조건을 파이프라인 쿼리로 조립.
- **클래스 시그니처**: `@Service("secsService") public class SecsServiceImpl implements SecsService`
- **주입 의존성**: `@Resource(name="secsDAO") SecsDAO Client`

#### 메서드

| 메서드 | 설명 |
|---|---|
| `getDataList(SecsVo)` | `getQueryParser` 결과에 limit/sort/`No=seq()+offset` 적용 후 `Client.dbExecuteQuery(fabSite, query)` 실행. |
| `getQueryParser(SecsVo)` *(private)* | `table=` 절, FAB별 테이블 조회, LEVEL search, SECS·HOST·TEXT 조건(쉼표 분리 multi 검색, AND/OR 옵션), `fields _TIME, TIME_EX, SECS, LEVEL, S/F, SB, NAME, DATA, TEXT, SKEY, HOST` 출력 컬럼 조립. |
| `getTableFromFab(fabSite, fab)` *(private)* | fabSite·fab 조합에 따라 `Common.sSECS_DATA`, `sSECS_DATA_M15A/B`, `sSECS_DATA_M11A/B`, `sSECS_DATA_C2/C2F`, `sSECS_DATA_M14B`, `sSECS_DATA_M16A/B` 등 SECS 테이블 상수를 반환. |
| `getSelectList(String fabSite)` | `memlookup name=machine_list \| search isnotnull(MACHINETYPE) \| eval SECSII=MACHINENAME, FAB=SHOPNAME \| fields FAB, SECSII` 실행. |
| `getSecsList(String fabSite)` | 위와 동일 쿼리에 `sort SECSII` 추가 후 실행. |
| `getSecsFabList(MachineVo)` | `getSecsFabQuery`로 selectFab을 `search in FAB` 절로 추가한 쿼리 실행. |
| `getSecsFabQuery(MachineVo)` *(private)* | `machine_list` 기반 쿼리에 fab 필터를 부착. |
| `getRawLogQueryStop()` | `Client.dbExecuteQueryStop()` 호출. |

---

### 7) dao/EiDAO.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/dao/EiDAO.java`
- **목적**: EI 로그 조회용 DAO. MyBatis SQL Mapper를 사용하지 않고 `DBManager`를 직접 인스턴스화하여 임의 쿼리 문자열을 실행한다.
- **클래스 시그니처**: `@Repository("eiDAO") public class EiDAO`
- **필드**: `DBManager dbManager`

> 본 DAO는 SQL Mapper ID가 아닌 **동적 쿼리 문자열(서비스에서 조립된 파이프라인 쿼리)** 을 `DBManager.executeQuery(queryStmt)`로 실행하는 패턴이다. 호출되는 매퍼 ID는 없다.

#### 메서드

| 메서드 | 설명 |
|---|---|
| `dbExecuteQuery(String fabSite, String queryStmt)` | `new DBManager(fabSite)` 생성 → `executeQuery(queryStmt)` 실행 → 결과 `List<Map>` 반환. finally에서 `dbManager = null`로 해제. |
| `dbExecuteQueryStop()` | 현재 dbManager가 있으면 `executeQueryStop()` 호출하여 진행 중인 쿼리 취소. |

---

### 8) dao/SecsDAO.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/dao/SecsDAO.java`
- **목적**: SECS 로그 조회용 DAO. 구조 및 동작은 `EiDAO`와 동일.
- **클래스 시그니처**: `@Repository("secsDAO") public class SecsDAO`
- **필드**: `DBManager dbManager`

> SQL Mapper ID 없이 `DBManager`를 통해 동적 파이프라인 쿼리를 직접 실행한다.

#### 메서드

| 메서드 | 설명 |
|---|---|
| `dbExecuteQuery(String fabSite, String queryStmt)` | fabSite 기반 `DBManager` 생성 후 쿼리 실행, 결과 반환. |
| `dbExecuteQueryStop()` | 진행 중인 SECS 조회 쿼리를 취소. |

---

### 9) vo/EiVo.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/vo/EiVo.java`
- **목적**: EI/CS/DS/TS 로그 조회 화면의 검색조건 VO.
- **클래스 시그니처**: `public class EiVo`

#### 필드

| 이름 | 타입 | 역할 |
|---|---|---|
| `fabSite` | String | Fab Site 식별자 (M14/M15/M11/C2/IC 등) |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `fab` | List\<String\> | Fab 코드 목록 (ALL/C2/C2F 등) |
| `level` | List\<String\> | 로그 레벨 (ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL) |
| `host` | List\<String\> | Host 종류 (Primary/Secondary) |
| `log` | List\<String\> | LogType 목록 (TS/EI/CS/DS) |
| `process` | String | PROCESS 검색 조건 (쉼표 multi 가능) |
| `text` | String | TEXT 검색 조건 (쉼표 multi, `*` 제거됨) |
| `eiTextConditionCheckBox` | String | TEXT multi 검색 시 AND/OR 옵션 |
| `from` | String | 조회 시작시각 (yyyyMMddHHmmss) |
| `to` | String | 조회 종료시각 (yyyyMMddHHmmss) |

---

### 10) vo/SecsVo.java

- **경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/secs/vo/SecsVo.java`
- **목적**: SECS 로그 조회 화면의 검색조건 VO.
- **클래스 시그니처**: `public class SecsVo`

#### 필드

| 이름 | 타입 | 역할 |
|---|---|---|
| `fabSite` | String | Fab Site 식별자 |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `fab` | List\<String\> | Fab 코드 목록 |
| `level` | List\<String\> | SECS 레벨 (ALL/TIME/INFO/WARN/RECV/SEND 등) |
| `host` | List\<String\> | Host (Primary/Secondary) |
| `carrier` | String | Carrier ID 조건 (확장 필드) |
| `vehicle` | String | Vehicle 조건 (확장 필드) |
| `secs` | String | SECSII 장비명 조건 (쉼표 multi 가능) |
| `carrierLoc` | String | Carrier Location 조건 |
| `commandId` | String | Command ID 조건 |
| `transferport` | String | Transfer Port 조건 |
| `sourceport` | String | Source Port 조건 |
| `destport` | String | Destination Port 조건 |
| `text` | String | TEXT 검색 조건 (쉼표 multi) |
| `secsTextConditionCheckBox` | String | TEXT multi 검색 시 AND/OR 옵션 |
| `from` | String | 조회 시작시각 |
| `to` | String | 조회 종료시각 |

> 비고: `carrier`, `vehicle`, `carrierLoc`, `commandId`, `transferport`, `sourceport`, `destport` 필드는 VO에 정의되어 있으나 `SecsServiceImpl.getQueryParser`에서는 현재 `secs`, `host`, `text`, `level`, `fab`만 쿼리 조건으로 사용된다.

---

## 데이터 흐름

```
JSP 화면 (eiLogList.jsp / secsLogList.jsp)
        │  (form submit / ajax)
        ▼
Controller (EiLogController / SecsLogController)
  - FabSite 세션 처리 (Common.getFabSite / setFabSite)
  - 화면 파라미터를 VO(EiVo / SecsVo)에 바인딩
  - fab/logType/host/level 다중선택 파라미터 수집
  - From/To 미입력 시 현재시각 ±10분 기본값 설정
  - Paging(page, rows) 객체 생성
        │
        ▼
Service (EiService / SecsService → *ServiceImpl)
  - getQueryParser(...)로 파이프라인 형식 검색쿼리 동적 생성
      · table= 절 (fabSite + fab + logType → Common.s*_DATA_* 상수)
      · search in FAB / LEVEL / HOST 조건
      · PROCESS / SECS / TEXT 조건 (쉼표 multi, AND/OR, * 처리)
      · fields 출력 컬럼 (TIME, LEVEL, TEXT, HOST 등)
  - limit/offset, sort _TIME, eval No=seq()+offset 부착
  - 부가 조회: getProcessList / getSecsList / getSelectProcessList /
              getSecsFabList → memlookup 기반 lookup 쿼리
        │
        ▼
DAO (EiDAO / SecsDAO)
  - new DBManager(fabSite)로 fabSite별 접속 생성
  - dbManager.executeQuery(queryStmt) 호출
  - dbExecuteQueryStop() 으로 진행 중 쿼리 cancel 지원
        │
        ▼
DBManager (com.skhynix.supply.common)
  - fabSite별 실제 데이터 소스(Splunk 류 검색엔진)에 쿼리 전송
        │
        ▼
List<Map> 결과
        │
        ▼
Service → Controller → ModelAndView(jsonView)
        │
        ▼
JSP/jqGrid에서 rows/page/total/records 로 렌더링
```

핵심 특징은 다음과 같다.

- **MyBatis Mapper 미사용**: 모든 SQL/검색쿼리가 Service 계층에서 문자열로 동적 조립되며, DAO는 단순히 `DBManager`를 거쳐 실행만 담당한다.
- **FabSite 라우팅**: 동일 모듈이 M11/M14/M15/C2/IC 등 여러 Fab Site의 서로 다른 테이블을 동적으로 선택하여 조회한다.
- **쿼리 취소 채널**: 별도 엔드포인트 (`getEiQueryStop`, `getSecsQueryStop`)로 사용자가 장시간 조회를 강제 종료할 수 있다.
