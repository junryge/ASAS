# 02. Alarm 모듈 (alarmReport)

본 문서는 `com.skhynix.supply.alarm` 패키지의 모든 파일을 분석한 결과입니다. 이 모듈은 MCS(Material Control System)의 알람 리포트(AlarmReport) 로그를 검색/조회하는 기능을 담당합니다. 데이터 저장소는 일반적인 RDB가 아니라 InfluxDB 계열의 시계열 DB이며, MyBatis가 아닌 자체 `DBManager`를 통해 파이프라인 기반 쿼리(`|`)를 동적으로 빌드하여 호출합니다.

---

## 엔드포인트 요약

| URL | HTTP | Controller 메서드 | 반환 View | 기능 |
|---|---|---|---|---|
| `alarm/alarmReportLogList` | GET/POST (default) | `AlarmReportController.alarmReportLogList` | `alarm/alarmReportLogList` (JSP) | AlarmReport 로그 조회 **화면(JSP)** 초기 진입. FabSite, Fab, Level 등 초기 검색조건 셋업. |
| `alarm/ajax/getAlarmReportLogList` | GET/POST (default) | `AlarmReportController.getAlarmReportLogList` | `jsonView` | AlarmReport 로그 데이터 **AJAX 조회**. 페이징, 필터(level/fab/machineType/areaName/bayName/time)를 받아 결과 JSON 반환. |

---

## 1. AlarmReportController.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/alarm/controller/AlarmReportController.java`
- **목적**: AlarmReport 로그 조회 화면 진입과 AJAX 데이터 조회를 처리하는 Spring MVC 컨트롤러. 화면 초기값 셋팅과 검색 파라미터 정규화를 담당.
- **클래스 시그니처**:
  ```java
  @Controller
  public class AlarmReportController
  ```
- **의존성 주입(@Resource)**:
  - `AlarmReportService alarmReportService` (`name="alarmReportService"`) — 알람 조회 비즈니스 로직
  - `TotalService totService` (`name="totalService"`) — 공통 코드/리스트 조회 (현재 메서드 내부에서는 직접 호출은 주석 처리됨)
- **공통 유틸**: `Common`(상수/유틸), `Paging`(페이지 계산)

### 메서드 1) `alarmReportLogList`
- **시그니처**: `public ModelAndView alarmReportLogList(@ModelAttribute AlarmReportVo param, HttpServletRequest request) throws Exception`
- **@RequestMapping**: `value = "alarm/alarmReportLogList"`
- **반환**: `ModelAndView` (View = `alarm/alarmReportLogList`)
- **로직 설명 (Korean)**:
  1. `Common.FabSites`를 화면에 전달(콤보박스용).
  2. `param.getFabSite()`가 비어 있으면 세션/요청에서 `Common.getFabSite(request)`로 가져와 셋업. 값이 있으면 `Common.setFabSite(request, sFabSite)`로 세션에 반영.
  3. 해당 FabSite에 대응되는 Fab 리스트(`Common.getFabList("alarm", sFabSite)`)와 기본 Fab(`getBasicFabList`)을 모델/파라미터에 셋업.
  4. Level 콤보(`Common.Levels`) 전달 및 기본 선택값(`WELL/WARN/ERROR/FATAL`)을 `param.setLevel(...)`으로 셋업.
  5. 모델 키 `param`, `params`로 동일한 VO를 추가하여 JSP에서 둘 다 참조 가능.
  6. 뷰 이름 `alarm/alarmReportLogList`(JSP) 반환 → 화면 렌더링.

### 메서드 2) `getAlarmReportLogList`
- **시그니처**: `public ModelAndView getAlarmReportLogList(@ModelAttribute AlarmReportVo param, HttpServletRequest request) throws Exception`
- **@RequestMapping**: `value = "alarm/ajax/getAlarmReportLogList"`
- **반환**: `ModelAndView` (View = `jsonView` — JSON 응답)
- **로직 설명 (Korean)**:
  1. 현재 시각(`yyyyMMddHHmmss`)과 10분 전 시각을 계산 → 기본 시간 범위로 사용.
  2. `page`(기본 `"1"`), `rows`(기본 `"100"`) 파라미터 보정.
  3. FabSite 정규화 로직(메서드1과 동일).
  4. `fab1` 파라미터가 `Common.sALL`이면 전체 Fab 리스트 셋업, 그렇지 않으면 `fab1...fabN` 파라미터를 모아 `param.setFab(...)`.
  5. `level1...levelN` 파라미터를 모아 `param.setLevel(...)`.
  6. `machineTypes` 파라미터(콤마 구분 문자열)를 split. 첫 값이 `ALL`이면 빈 리스트(전체), 아니면 각 항목을 `machineType` 리스트로 셋업.
  7. `areaName`, `bayName`이 비어 있으면 `Common.sALL`로 기본화.
  8. `pageNum`, `rowNum`, `from`, `to` 보정(시간 범위 기본은 최근 10분).
  9. `Paging`을 생성하고 `alarmReportService.getDataList(param)`을 호출하여 결과 조회.
  10. 결과가 있으면 `Paging.nTotalCount`로 전체 레코드 수를 셋업하여 페이징 계산.
  11. JSON 응답 모델(`page`, `total`, `records`, `rows`)을 셋업 후 `jsonView`로 응답.

---

## 2. AlarmReportService.java (인터페이스)

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/alarm/service/AlarmReportService.java`
- **목적**: AlarmReport 로그 조회용 서비스 인터페이스. 컨트롤러와 구현체를 분리하는 계약 역할.
- **클래스 시그니처**:
  ```java
  public interface AlarmReportService
  ```
- **메서드**:
  - `public List<Map> getDataList(AlarmReportVo alarmReportVo) throws Exception`
    - VO의 검색 조건/페이징 정보를 받아 알람 로그 결과 리스트(`List<Map>`)를 반환.

---

## 3. AlarmReportServiceImpl.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/alarm/service/impl/AlarmReportServiceImpl.java`
- **목적**: AlarmReport 검색 조건을 시계열 DB용 파이프라인 쿼리 문자열로 변환한 뒤, 공용 DAO(`TotalDAO`)를 통해 실행하는 서비스 구현체.
- **클래스 시그니처**:
  ```java
  @Service("alarmReportService")
  public class AlarmReportServiceImpl implements AlarmReportService
  ```
- **의존성 주입(@Resource)**:
  - `TotalDAO Client` (`name="totalDAO"`) — 실제 DB 질의 실행 (이 모듈에서는 `AlarmReportDAO`가 아닌 공용 `TotalDAO`를 사용)

### 메서드 1) `getDataList(AlarmReportVo) : List<Map>`
- **로직 설명 (Korean)**:
  1. `pageNum`, `rowNum`으로 `offset`, `limit` 계산.
  2. `getQueryParser(alarmReportVo)`를 호출하여 검색 조건 쿼리 본문을 생성.
  3. 쿼리 뒤에 `| limit {offset} {limit}` 추가 (페이징).
  4. 쿼리 뒤에 `| sort _time` 추가 (시간 정렬).
  5. `Client.dbExecuteQuery(fabSite, resultQuery)` 실행하여 `List<Map>` 결과 반환.

### 메서드 2) `getQueryParser(AlarmReportVo) : String`
- **로직 설명 (Korean)**: 검색 조건을 기반으로 시계열 DB(파이프라인 문법) 쿼리 문자열을 동적으로 빌드하는 핵심 메서드.
  1. **기본 절**: `Common.sFulltext_Arg0_key1` 포맷에 `from`, `to`, `(METHOD="createAlarmReportHistory")` 적용. 즉 메서드 이름이 `createAlarmReportHistory`인 로그만 시간 범위로 풀텍스트 검색.
  2. **UNIT 조건**: `unit`에 `_`가 있으면 split 후 각 토큰을 `AND`로 묶음. `-`가 있으면 동일하게 처리. 단일 값이면 단일 `(UNIT="...")`.
  3. **ALARMID / ALARMCODE / STATE**: 각각 단순 `AND (KEY="value")` 형태로 append.
  4. **ALARMTEXT**: 공백/괄호/슬래시/하이픈/언더바 포함 시 모두 공백으로 치환 후 토큰 분리 → 각 토큰을 `(ALARMTEXT="token")` AND로 묶음. 단순 문자열이면 단일 절.
  5. **AREANAME / BAYNAME**: `ALL`이 아니면 `(AREANAME="value")`, `(BAYNAME="value")` 추가.
  6. **MACHINETYPE**: `Common.sSearch_in` 포맷으로 `search in MACHINETYPE` 구문을 만들고 각 값을 콤마로 append. `ALL` 포함 시 절 자체 제거. 결과 절은 `subMachineTypeQuery`에 보관(나중에 FROM 절 뒤에 삽입).
  7. **MACHINENAME**: 여러 값을 `OR`로 연결하여 `(MACHINENAME="m1" OR MACHINENAME="m2" ...)` 절 추가. `NOTDESIGNATED` 만나면 break.
  8. **LEVEL 절**은 현재 주석 처리(사용 안 함).
  9. **FROM(테이블) 절 결정**: `getTableFromFab(fabSite, fab)`를 각 fab마다 호출하여 알람 테이블명을 결정하고 콤마로 연결.
  10. 최종 쿼리에 `FROM {tables}`, `subMachineTypeQuery`, `FIELDS _time, TIME_EX, MACHINENAME, MACHINETYPE, UNIT, STATE, ALARMID, ALARMCODE, ALARMTEXT`를 차례로 append.
  11. 완성된 쿼리 문자열을 반환.

### 메서드 3) `getTableFromFab(String fabSite, String fab) : String` (private)
- **로직 설명 (Korean)**: FabSite와 Fab 조합에 대응되는 시계열 알람 테이블 상수를 반환하는 매핑 함수.
  - `M14` → `TS_ALARM_M14A`
  - `M15` → `TS_ALARM_M15A` / `TS_ALARM_M15B`
  - `M11` → `TS_ALARM_M11A` / `TS_ALARM_M11B`
  - `C2`  → `TS_ALARM_C2` / `TS_ALARM_C2F`
  - `IC`  → fab가 `M14A` → `TS_ALARM_M14A`, `M16A` → `TS_ALARM_M16A`, `M16B` → `TS_ALARM_M16B`
  - 그 외: `null` 반환
  - **주의**: `switch-case`에 `break;`가 없어 의도와 다르게 fall-through 가능성이 있음 (단, 각 case 내부에서 `return`하므로 매칭이 되면 반환되어 실질 문제는 없으나, `M15`에서 fab가 `M15A/M15B`가 아니면 다음 case `M11`로 떨어짐 → 잠재적 버그 소지).

---

## 4. AlarmReportDAO.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/alarm/dao/AlarmReportDAO.java`
- **목적**: 알람 조회 전용 DAO. 내부에 `DBManager`(자체 시계열 DB 커넥션 매니저)를 생성하여 쿼리를 실행. (단, **실제로 컨트롤러/서비스에서는 사용되지 않고 있으며**, `AlarmReportServiceImpl`는 `TotalDAO`를 사용 중.)
- **클래스 시그니처**:
  ```java
  @Repository("alarmReportDAO")
  public class AlarmReportDAO
  ```
- **필드**:
  - `DBManager dbManager` — 시계열 DB 커넥션 매니저
  - `Log log` — 커먼즈 로깅
- **MyBatis 사용 여부**: **사용하지 않음.** 본 DAO는 MyBatis SqlSession이나 namespace를 사용하지 않고, `DBManager.executeQuery(String queryStmt)`에 사전에 빌드된 파이프라인 쿼리 문자열을 그대로 전달하여 시계열 DB에 직접 질의. 따라서 별도의 mybatis namespace ID 목록은 없음.

### 메서드 1) `AlarmReportDAO()` (생성자)
- 빈 생성자.

### 메서드 2) `dbExecuteQuery(String fabSite, String queryStmt) : List<Map>`
- **로직 설명 (Korean)**:
  1. `new DBManager(fabSite)`로 FabSite별 커넥션 생성.
  2. `dbManager.executeQuery(queryStmt)`로 쿼리 실행.
  3. 예외 발생 시 `log.warn`으로 기록하고 null 반환.
  4. `finally`에서 `dbManager`를 null로 초기화하여 참조 해제.
- **참고**: 하단에 `ThreadPool` 기반 비동기 실행 코드가 주석 처리되어 있음 (`2021.10.08 X0122410 ThreadPool 적용`).

### 메서드 3) `dbExecuteQueryStop() : void`
- **로직 설명 (Korean)**: 진행 중인 쿼리 실행을 중단(`dbManager.executeQueryStop()`)하고 `dbManager`를 null로 해제. 화면에서 사용자가 조회 취소 등을 요청할 때 호출하기 위한 인터페이스. 예외 발생 시 로그 경고.

### SQL/쿼리 목록
| 쿼리 | 형태 | 목적 |
|---|---|---|
| 동적 파이프라인 쿼리 (서비스에서 빌드) | `fulltext ... | search in MACHINETYPE ... | fields ... | limit O L | sort _time` | AlarmReport 시계열 로그 조회 |
| `executeQueryStop` 내부 호출 | 시계열 DB cancel API | 진행 중인 조회 중단 |

---

## 5. AlarmReportVo.java

- **파일 경로**: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/alarm/vo/AlarmReportVo.java`
- **목적**: AlarmReport 검색 화면의 입력 파라미터를 담는 POJO. 페이지/머신/팹/레벨/조건/시간 등 검색 조건을 한 객체에 집약.
- **클래스 시그니처**: `public class AlarmReportVo` (애노테이션 없음, 표준 getter/setter 제공)

### 필드 표

| 이름 | 타입 | 역할 |
|---|---|---|
| `fabSite` | `String` | FabSite 식별자 (M14/M15/M11/C2/IC 등). 2022.6.15 추가됨. |
| `pageNum` | `String` | 페이지 번호 |
| `rowNum` | `String` | 한 페이지에 보여줄 행 수 |
| `areaName` | `String` | Area 이름 (`ALL` 또는 특정 값) |
| `bayName` | `String` | Bay 이름 (`ALL` 또는 특정 값) |
| `machineType` | `List<String>` | 머신 타입 (`ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT`) |
| `machineName` | `List<String>` | 머신 이름 목록 |
| `fab` | `List<String>` | Fab 목록 (`ALL/M14A/M14B/...`) |
| `level` | `List<String>` | 알람 레벨 (`ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL`) |
| `unit` | `String` | UNIT 검색 조건 (`_`나 `-`로 다중 토큰 가능) |
| `alarmId` | `String` | Alarm ID 검색 조건 |
| `alarmCode` | `String` | Alarm Code 검색 조건 |
| `alarmText` | `String` | Alarm Text 검색 조건 (다중 토큰 가능) |
| `state` | `String` | Alarm State 검색 조건 |
| `from` | `String` | 검색 시작 시각 (`yyyyMMddHHmmss`) |
| `to` | `String` | 검색 종료 시각 (`yyyyMMddHHmmss`) |

각 필드는 모두 표준 getter/setter를 제공.

---

## 데이터 흐름

```
[Browser/JSP]
      │  GET/POST  alarm/alarmReportLogList            ─▶ 화면 진입(JSP 렌더)
      │  AJAX      alarm/ajax/getAlarmReportLogList    ─▶ JSON 응답
      ▼
[AlarmReportController]
      - @ModelAttribute AlarmReportVo 로 파라미터 바인딩
      - FabSite/Fab/Level/MachineType/페이지/시간 기본값 정규화
      - Paging 객체 생성
      ▼
[AlarmReportService (interface)]
      ▼
[AlarmReportServiceImpl]
      - getQueryParser(VO)  : 검색 조건을 시계열 DB 파이프라인 쿼리 문자열로 빌드
        · fulltext + (METHOD="createAlarmReportHistory")
        · UNIT/ALARMID/ALARMCODE/ALARMTEXT/STATE/AREANAME/BAYNAME 필터
        · search in MACHINETYPE(...)
        · MACHINENAME OR 절
        · FROM TS_ALARM_{FAB}  (getTableFromFab 매핑)
        · FIELDS _time, TIME_EX, MACHINENAME, MACHINETYPE, UNIT, STATE, ALARMID, ALARMCODE, ALARMTEXT
      - 끝에 "| limit offset limit | sort _time" 부착
      ▼
[TotalDAO.dbExecuteQuery(fabSite, queryStmt)]   ※ AlarmReportDAO는 정의만 되어 있고 본 흐름에서는 미사용
      ▼
[DBManager(fabSite).executeQuery(queryStmt)]
      ▼
[시계열 DB (FabSite별 TS_ALARM_* 테이블)]
      │
      ▼ List<Map> 결과
[Service → Controller]
      - Paging.nTotalCount 로 전체 건수 세팅, 페이징 계산
      - mav: page, total, records, rows
      ▼
[jsonView] → 브라우저 그리드에 표시
```

**주의/특이사항**
- DAO 레이어가 두 종류 존재: 본 모듈에 `AlarmReportDAO`가 선언되어 있으나 실제로는 `TotalDAO`(`com.skhynix.supply.tot.dao.TotalDAO`)가 사용됨. `AlarmReportDAO`는 호출되지 않는 코드(dead code 가능성).
- MyBatis namespace 매핑은 없으며, 동적 문자열 쿼리(파이프라인 문법)를 그대로 시계열 DB로 전송.
- `getTableFromFab`의 `switch-case`에 `break`가 누락된 케이스 존재 (잠재적 fall-through 버그).
- Level 필터링은 서비스 레이어에서 주석 처리되어 현재 LEVEL 조건은 실제 쿼리에 반영되지 않음 (컨트롤러에서는 셋업하지만 사용되지 않음).
