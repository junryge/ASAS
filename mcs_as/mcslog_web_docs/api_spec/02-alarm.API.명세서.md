# 02-alarm.API.명세서

## 1. API 개요

본 문서는 SK hynix MCS Log 조회 시스템의 `alarm` 모듈(설비 알람 리포트 로그 조회) API 명세서이다.

- **모듈**: `com.skhynix.supply.alarm`
- **컨트롤러**: `AlarmReportController` (`@Controller`)
- **서비스**: `AlarmReportService` / `AlarmReportServiceImpl` (`@Service("alarmReportService")`)
- **DAO**: `AlarmReportDAO` (참고: 실제 컨트롤러/서비스 경로에서는 `TotalDAO` 가 주입되어 사용됨. `AlarmReportDAO` 는 `@Repository("alarmReportDAO")` 로 등록만 되고 alarm 흐름에서는 직접 호출되지 않는 사실상의 dead code)
- **VO**: `AlarmReportVo` (`@ModelAttribute` 바인딩)
- **백엔드 데이터 저장소**: RDBMS+MyBatis 가 아닌 **Logpresso(로그 검색 엔진)**. `AlarmReportServiceImpl#getQueryParser(...)` 가 `table xxx FAB=... | search ... | fields ... | limit ... | sort ...` 형태의 파이프라인 쿼리 문자열을 직접 조립하여 `TotalDAO#dbExecuteQuery(fabSite, query)` 로 실행
- **요청/응답 포맷**:
  - 화면(View) 호출 → `application/x-www-form-urlencoded` 요청, JSP(`InternalResourceViewResolver` 또는 Tiles) 뷰 응답
  - AJAX 호출 → `application/x-www-form-urlencoded` 요청, `jsonView` (`net.sf.json` 기반 JSON) 응답
- **HTTP 메서드**: `@RequestMapping` 에 `method` 미지정 → Spring 4 기본 동작상 GET/POST 모두 수신
- **컨텍스트 패스**: 본 명세에서는 표기를 생략한다. 실제 URL 은 `http://{SERVER_URL}/{contextPath}/<URL>` 형태가 된다.

## 2. API 목록

| No | Method | URL | 설명 | 응답형식 |
|---|---|---|---|---|
| 1 | GET, POST | `/alarm/alarmReportLogList` | Alarm 리포트 로그 조회 화면(JSP) | JSP View (`alarm/alarmReportLogList`) |
| 2 | GET, POST | `/alarm/ajax/getAlarmReportLogList` | Alarm 리포트 로그 조회 결과 데이터 (AJAX, jqGrid 형식) | JSON (`jsonView`) |

## 3. 상세 API 명세

### 3.1 Alarm 리포트 로그 조회 화면

Alarm 리포트 로그를 검색하는 메인 화면을 렌더링한다. 화면 진입 시 기본 조건(`fabSite`, `fab`, `level`)을 모델에 담아 JSP 로 전달한다.

**Request**

Request Syntax (curl):

```bash
# 1) GET (쿼리스트링)
curl -X GET 'http://{SERVER_URL}/alarm/alarmReportLogList?fabSite=IC'

# 2) POST (form-urlencoded)
curl -X POST 'http://{SERVER_URL}/alarm/alarmReportLogList' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'fabSite=IC'
```

| 메서드 | 요청 URL |
|---|---|
| GET, POST | `/alarm/alarmReportLogList` |

Request Header:

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| Content-Type | string | 조건부 | POST + form 전송 시 `application/x-www-form-urlencoded` |
| Cookie | string | N | 세션 쿠키 (`JSESSIONID`) — `Common.getFabSite/setFabSite` 가 세션에 fabSite 를 보관 |

Request Elements (`@ModelAttribute AlarmReportVo param`):

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| fabSite | String | N | 세션값 또는 시스템 기본 | Setter: `setFabSite`. 값 없으면 `Common.getFabSite(request)` 사용, 값 있으면 `Common.setFabSite(request, ...)` 로 세션 갱신 |
| pageNum | String | N | (미사용) | Setter: `setPageNum` |
| rowNum | String | N | (미사용) | Setter: `setRowNum` |
| areaName | String | N | - | Setter: `setAreaName` |
| bayName | String | N | - | Setter: `setBayName` |
| machineType | String[] | N | - | Setter: `setMachineType(List<String>)` (Spring 바인딩으로 동일 이름 다중값 → List) |
| machineName | String[] | N | - | Setter: `setMachineName(List<String>)` |
| fab | String[] | N | 컨트롤러가 `Common.getBasicFabList("alarm", sFabSite)` 로 덮어씀 | Setter: `setFab(List<String>)` |
| level | String[] | N | 컨트롤러가 `[WELL, WARN, ERROR, FATAL]` 로 덮어씀 | Setter: `setLevel(List<String>)` |
| unit | String | N | - | Setter: `setUnit` |
| alarmId | String | N | - | Setter: `setAlarmId` |
| alarmCode | String | N | - | Setter: `setAlarmCode` |
| alarmText | String | N | - | Setter: `setAlarmText` |
| state | String | N | - | Setter: `setState` |
| from | String | N | - | Setter: `setFrom` (`yyyyMMddHHmmss`) |
| to | String | N | - | Setter: `setTo` (`yyyyMMddHHmmss`) |

> 본 화면 엔드포인트는 조회 데이터를 조회하지 않으며, AJAX 엔드포인트(3.2)에서 실제 검색이 이루어진다.

**Response**

응답: `ModelAndView`, ViewName = `alarm/alarmReportLogList` (JSP).

Response Elements (Model 키):

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| fabsites | List/Map | Y | `Common.FabSites` — 전체 FabSite 목록(IC/M14/M15/M11/C2 등) |
| fabs | List<String> | Y | `Common.getFabList("alarm", sFabSite)` — 현재 FabSite 의 Fab 코드 목록 |
| levels | List<String> | Y | `Common.Levels` — 전체 Level 목록(ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL) |
| param | AlarmReportVo | Y | 화면 기본 폼 바인딩용 VO (fab/level 기본값 세팅) |
| params | AlarmReportVo | Y | `param` 과 동일한 인스턴스 (중복 등록) |

Error Codes:

| HTTP | 상황 | 응답 |
|---|---|---|
| 200 | 정상 | JSP `alarm/alarmReportLogList` 렌더링 |
| 200 | Exception 발생 | `ExceptionControllerAdvice` 에 의해 `common/error/errorPage` JSP 렌더링 (Model: `name`, `message`) |

Examples:

요청:
```
GET /alarm/alarmReportLogList?fabSite=M14
```

응답: JSP `alarm/alarmReportLogList.jsp` 렌더링(Model 키 `fabsites`, `fabs`, `levels`, `param`, `params` 사용).

---

### 3.2 Alarm 리포트 로그 조회(AJAX, jqGrid)

Alarm 리포트 로그 검색 결과를 페이지/행 단위로 조회한다. jqGrid 호환 JSON 응답(`page`, `total`, `records`, `rows`)을 반환한다.

**Request**

Request Syntax (curl):

```bash
# 1) POST form-urlencoded
curl -X POST 'http://{SERVER_URL}/alarm/ajax/getAlarmReportLogList' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'fabSite=IC' \
  --data-urlencode 'page=1' \
  --data-urlencode 'rows=100' \
  --data-urlencode 'from=20240101000000' \
  --data-urlencode 'to=20240101235959' \
  --data-urlencode 'fab1=M14A' \
  --data-urlencode 'fab2=M16A' \
  --data-urlencode 'level1=ERROR' \
  --data-urlencode 'level2=FATAL' \
  --data-urlencode 'machineTypes=STOCKER,OHT' \
  --data-urlencode 'areaName=ALL' \
  --data-urlencode 'bayName=ALL' \
  --data-urlencode 'unit=' \
  --data-urlencode 'alarmId=' \
  --data-urlencode 'alarmCode=' \
  --data-urlencode 'alarmText=' \
  --data-urlencode 'state='

# 2) GET 쿼리스트링도 동일하게 동작
curl -X GET 'http://{SERVER_URL}/alarm/ajax/getAlarmReportLogList?fabSite=IC&page=1&rows=100&from=20240101000000&to=20240101235959&fab1=M14A&level1=ERROR&machineTypes=ALL&areaName=ALL&bayName=ALL'
```

| 메서드 | 요청 URL |
|---|---|
| GET, POST | `/alarm/ajax/getAlarmReportLogList` |

Request Header:

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| Content-Type | string | 조건부 | POST 시 `application/x-www-form-urlencoded` |
| X-Requested-With | string | N | `XMLHttpRequest` (관례) |
| Cookie | string | N | 세션 쿠키 (`JSESSIONID`) |

Request Elements:

A) `@ModelAttribute AlarmReportVo param` 바인딩 (Spring 자동 바인딩, 폼 파라미터명 = VO 필드명)

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| fabSite | String | N | 세션값 | Setter: `setFabSite`. 값 없으면 세션에서 로드, 있으면 세션에 저장 |
| pageNum | String | N | request `page` 로 덮어씀 | Setter: `setPageNum`. 컨트롤러에서 `page` 파라미터로 덮어쓰기 |
| rowNum | String | N | request `rows` 로 덮어씀 | Setter: `setRowNum`. 컨트롤러에서 `rows` 파라미터로 덮어쓰기 |
| areaName | String | N | `ALL` | Setter: `setAreaName`. null/공백이면 `Common.sALL` 로 강제 세팅 |
| bayName | String | N | `ALL` | Setter: `setBayName`. null/공백이면 `Common.sALL` 로 강제 세팅 |
| machineName | String[] | N | - | Setter: `setMachineName(List<String>)`. 동일 이름 반복(`machineName=...&machineName=...`) |
| unit | String | N | - | Setter: `setUnit`. `_` 또는 `-` 포함 시 split 후 다중 AND 절로 변환 |
| alarmId | String | N | - | Setter: `setAlarmId` |
| alarmCode | String | N | - | Setter: `setAlarmCode` |
| alarmText | String | N | - | Setter: `setAlarmText`. 공백/`( ) / - _` 포함 시 토큰 분해 후 다중 AND 절로 변환 |
| state | String | N | - | Setter: `setState` |
| from | String | N | 현재시각 -10분 (`yyyyMMddHHmmss`) | Setter: `setFrom` |
| to | String | N | 현재시각 (`yyyyMMddHHmmss`) | Setter: `setTo` |
| fab | String[] | (사용안함) | - | `@ModelAttribute` 바인딩되더라도 컨트롤러가 `fab1..fabN` 또는 ALL 처리로 덮어씀 |
| level | String[] | (사용안함) | - | `@ModelAttribute` 바인딩되더라도 컨트롤러가 `level1..levelN` 으로 덮어씀 |
| machineType | String[] | (사용안함) | - | `@ModelAttribute` 바인딩되더라도 컨트롤러가 `machineTypes`(CSV) 로 덮어씀 |

B) `HttpServletRequest` 로 직접 읽는 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| page | String | N | `1` | jqGrid 현재 페이지 번호. `pageNum` 으로 매핑 |
| rows | String | N | `100` | jqGrid 페이지당 행수. `rowNum` 으로 매핑 |
| fab1 | String | N | - | Fab 코드. `fab1=ALL` 이면 fabList 전체 사용 |
| fab2..fabN | String | N | - | 추가 Fab 코드 (N = fabList.size + 1 까지 루프). 빈 값/null 은 무시 |
| level1 | String | N | - | Level 코드 1개 |
| level2..levelN | String | N | - | 추가 Level 코드 (N = `Common.Levels.size + 1` 까지 루프). 빈 값/null 은 무시 |
| machineTypes | String (CSV) | N | - | 콤마 구분 MachineType 목록. 첫 토큰이 `ALL` 이면 조건 없음(전체) |

Request Body 예시 (form-urlencoded):

```
fabSite=IC&page=1&rows=100&from=20240101000000&to=20240101235959
&fab1=M14A&fab2=M16A
&level1=ERROR&level2=FATAL
&machineTypes=STOCKER,OHT
&areaName=ALL&bayName=ALL
&unit=&alarmId=&alarmCode=&alarmText=&state=
```

**Response**

응답: `ModelAndView`, ViewName = `jsonView` → JSON 직렬화.

Response Syntax (JSON 예시):

```json
{
  "page": 1,
  "total": 3,
  "records": 100,
  "rows": [
    {
      "_time": "2024-01-01 12:34:56",
      "TIME_EX": "20240101123456000",
      "MACHINENAME": "OHT0001",
      "MACHINETYPE": "OHT",
      "UNIT": "ARM1",
      "STATE": "SET",
      "ALARMID": "A0001",
      "ALARMCODE": "1001",
      "ALARMTEXT": "Door open"
    }
  ]
}
```

Response Elements:

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| page | int | Y | 현재 페이지 번호 (`Paging#getCurrentPageNo`) |
| total | int | Y | 총 페이지 수 (`Paging#getNumberOfRecords` — 클래스 내부에서 페이징 후 값으로 변환됨) |
| records | int | Y | 페이지당 레코드 수 (`Paging#getRecordsPerPage`) |
| rows | List<Map> | Y | Logpresso 쿼리 결과 행 목록. 각 row 의 키: `_time`, `TIME_EX`, `MACHINENAME`, `MACHINETYPE`, `UNIT`, `STATE`, `ALARMID`, `ALARMCODE`, `ALARMTEXT` |

Error Codes:

| HTTP | 상황 | 응답 |
|---|---|---|
| 200 | 정상 | 위 JSON |
| 200 | 결과 없음 | `{ "page": 0, "total": 0, "records": 0, "rows": [] 또는 null }` (paging 미수행 시 기본값) |
| 200 | Logpresso 접속/쿼리 실패 | `AlarmReportDAO` 의 `try/catch` 가 `log.warn` 만 하고 null 반환. 단, 본 알람 흐름은 `TotalDAO` 를 사용하므로 그쪽 동작을 따른다. 일반적으로 `rows: null` 형태로 응답 가능 |
| 200 | 컨트롤러/서비스 단계에서 Exception 발생 | `ExceptionControllerAdvice` 에 의해 `common/error/errorPage` JSP 로 포워딩 (JSON 아님 — AJAX 클라이언트에 HTML 이 반환될 수 있는 일관성 이슈) |

Examples:

요청 1 — 최근 10분 ERROR/FATAL, OHT 만:
```
POST /alarm/ajax/getAlarmReportLogList
fabSite=IC&page=1&rows=50&level1=ERROR&level2=FATAL&machineTypes=OHT&fab1=M14A
```

응답 1:
```json
{
  "page": 1,
  "total": 1,
  "records": 50,
  "rows": [
    { "_time": "2024-05-19 09:00:01", "MACHINENAME": "OHT0102", "MACHINETYPE": "OHT",
      "UNIT": "ARM1", "STATE": "SET", "ALARMID": "A0011", "ALARMCODE": "2031",
      "ALARMTEXT": "Pickup fail", "TIME_EX": "20240519090001000" }
  ]
}
```

요청 2 — 모든 Fab 모든 Level (machineTypes=ALL):
```
GET /alarm/ajax/getAlarmReportLogList?fabSite=M15&page=1&rows=100&fab1=ALL&level1=ALL&machineTypes=ALL&from=20240101000000&to=20240131235959
```

응답 2: 동일한 jqGrid JSON 구조.

## 4. 자원(Resource) 모델

### 4.1 AlarmReportVo 필드

| 필드 | 타입 | Setter / Getter | 화면 폼 파라미터명 | 설명 |
|---|---|---|---|---|
| fabSite | String | setFabSite / getFabSite | `fabSite` | FabSite 코드 (예: `IC`, `M14`, `M15`, `M11`, `C2`) |
| pageNum | String | setPageNum / getPageNum | `pageNum` | 페이지 번호 (컨트롤러는 `page` 파라미터로 덮어씀) |
| rowNum | String | setRowNum / getRowNum | `rowNum` | 페이지당 행수 (컨트롤러는 `rows` 파라미터로 덮어씀) |
| areaName | String | setAreaName / getAreaName | `areaName` | Area 명 (`ALL` 또는 실제 area) |
| bayName | String | setBayName / getBayName | `bayName` | Bay 명 (`ALL` 또는 실제 bay) |
| machineType | List<String> | setMachineType / getMachineType | (AJAX) `machineTypes`(CSV) → 컨트롤러에서 List 변환 | MachineType 목록(STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT 등) |
| machineName | List<String> | setMachineName / getMachineName | `machineName` (다중) | Machine 명 목록 |
| fab | List<String> | setFab / getFab | (AJAX) `fab1..fabN` → 컨트롤러에서 List 조립 | Fab 코드 목록 |
| level | List<String> | setLevel / getLevel | (AJAX) `level1..levelN` → 컨트롤러에서 List 조립 | Level 목록(DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL) |
| unit | String | setUnit / getUnit | `unit` | UNIT 검색어 (`_` 또는 `-` 포함 시 토큰 분해 AND 검색) |
| alarmId | String | setAlarmId / getAlarmId | `alarmId` | ALARMID 검색어 (정확일치) |
| alarmCode | String | setAlarmCode / getAlarmCode | `alarmCode` | ALARMCODE 검색어 (정확일치) |
| alarmText | String | setAlarmText / getAlarmText | `alarmText` | ALARMTEXT 검색어. 공백/`( ) / - _` 포함 시 토큰 분해 AND 검색 |
| state | String | setState / getState | `state` | STATE (`SET`, `CLEAR` 등) |
| from | String | setFrom / getFrom | `from` | 조회 시작시각 `yyyyMMddHHmmss` |
| to | String | setTo / getTo | `to` | 조회 종료시각 `yyyyMMddHHmmss` |

### 4.2 Logpresso 쿼리 — 대상 테이블

`AlarmReportServiceImpl#getTableFromFab(fabSite, fab)` 의 매핑:

| fabSite | fab | 테이블 상수(`Common.*`) |
|---|---|---|
| `M14` | (무관) | `sTS_ALARM_M14A` |
| `M15` | `M15A` | `sTS_ALARM_M15A` |
| `M15` | `M15B` | `sTS_ALARM_M15B` |
| `M11` | `M11A` | `sTS_ALARM_M11A` |
| `M11` | `M11B` | `sTS_ALARM_M11B` |
| `C2`  | `C2`  | `sTS_ALARM_C2` |
| `C2`  | `C2F` | `sTS_ALARM_C2F` |
| `IC`  | `M14A` | `sTS_ALARM_M14A` |
| `IC`  | `M16A` | `sTS_ALARM_M16A` |
| `IC`  | `M16B` | `sTS_ALARM_M16B` |
| 그 외 | -    | `null` |

> 본 switch 문에는 `break` 가 없다(6번 이슈 참조). 여러 Fab 이 다중 선택되면 콤마(`,`) 로 구분되어 `from {table1, table2, ...}` 로 결합된다.

### 4.3 Logpresso 쿼리 — 사용 컬럼(필드)

`fields` 절에 출력되는 컬럼:

| 컬럼 | 설명 |
|---|---|
| `_time` | 이벤트 시각 |
| `TIME_EX` | 확장 시각 |
| `MACHINENAME` | Machine 명 |
| `MACHINETYPE` | Machine 타입 |
| `UNIT` | Unit |
| `STATE` | 알람 상태 |
| `ALARMID` | 알람 ID |
| `ALARMCODE` | 알람 코드 |
| `ALARMTEXT` | 알람 메시지 |

조건(검색)에 사용되는 컬럼: `METHOD`, `UNIT`, `ALARMID`, `ALARMCODE`, `ALARMTEXT`, `STATE`, `AREANAME`, `BAYNAME`, `MACHINETYPE`, `MACHINENAME` 및 시간 범위.

### 4.4 조립되는 Logpresso 쿼리 개요

```
table from=<from> to=<to> <table1,table2,...>
  | search ( METHOD="createAlarmReportHistory" )
      AND (UNIT="...")            # unit 조건
      AND (ALARMID="...")
      AND (ALARMCODE="...")
      AND (ALARMTEXT="...")
      AND (STATE="...")
      AND (AREANAME="...")        # ALL 이면 미추가
      AND (BAYNAME="...")         # ALL 이면 미추가
      AND (MACHINENAME="..." OR ...)
  | search in (MACHINETYPE, "...", "...")   # ALL 이면 미추가
  | fields _time, TIME_EX, MACHINENAME, MACHINETYPE, UNIT, STATE, ALARMID, ALARMCODE, ALARMTEXT
  | limit <offset> <limit>
  | sort _time
```

(정확한 토큰/연산자 명칭은 `com.skhynix.supply.common.Common` 의 `sFulltext_Arg0_key1`, `sSearch_in`, `sFrom`, `sFields`, `sPipeLine`, `sSort` 등을 따른다.)

## 5. 인증 및 권한

현재 코드(`AlarmReportController`, `AlarmReportService(Impl)`, `AlarmReportDAO`)에는 별도의 인증/인가 체크 로직(Spring Security `@PreAuthorize`, 세션 사용자 검증, 권한 코드 비교 등)이 존재하지 않는다. `Common.getFabSite/setFabSite(request, ...)` 로 세션의 FabSite 값을 읽고 쓰는 정도이며 사용자 식별/접근 제어는 수행하지 않는다.

따라서 본 모듈의 보호는 **컨테이너 레벨(WAS) 또는 상위 리버스 프록시/WAF 또는 전역 ServletFilter/Interceptor 설정에 의존**하는 것으로 추정된다(상위 인프라/공통 모듈에서 보호되는 전제).

## 6. 비고/이슈

- **DAO 미사용(dead code)**: `AlarmReportDAO` 는 `@Repository("alarmReportDAO")` 로 빈 등록되지만, `AlarmReportServiceImpl` 은 `TotalDAO Client` 를 주입받아 `Client.dbExecuteQuery(fabSite, query)` 를 호출한다. `AlarmReportDAO#dbExecuteQuery` 와 `dbExecuteQueryStop` 은 alarm 흐름에서 호출되지 않는다.
- **`getTableFromFab` switch fall-through 버그**: `case` 블록마다 `break;` 가 없다. 예를 들어 `fabSite=M15` 가 들어와도 case 가 `M15` 블록에서 매칭 후 fab 이 `M15A/M15B` 가 아니면 `return` 되지 않고 다음 `case M11:` 블록으로 흘러 내려간다. 의도된 동작으로 보기 어렵다.
- **`subMachineTypeQuery` null 체크 오류**: `if (subMachineTypeQuery != null || !(subMachineTypeQuery.toString().isEmpty()))` — 항상 true(StringBuilder 인스턴스 자체는 null 아님). 의도는 `&&` 였을 가능성. 또한 `subMachineTypeQuery.toString().indexOf("(") >= 0` 검사는 `Common.sSearch_in` 포맷 결과에 `(` 가 포함될 때만 closing `)` 를 붙이는 방식이라 입력에 따라 괄호 짝이 맞지 않을 위험이 있다.
- **잠재적 Logpresso 쿼리 인젝션**: 모든 사용자 입력(`unit`, `alarmId`, `alarmCode`, `alarmText`, `state`, `areaName`, `bayName`, `machineName`, `from`, `to` 등)이 이스케이프/화이트리스트 검증 없이 직접 문자열 연결로 쿼리에 삽입된다. `"` (큰따옴표)나 파이프(`|`), 개행을 포함한 입력이 들어오면 쿼리 구조가 변형될 수 있다. PreparedStatement 와 같은 파라미터 바인딩 메커니즘이 없으므로 입력 검증을 컨트롤러 단에서 강화하는 것이 바람직하다.
- **Exception 응답 일관성**: AJAX 엔드포인트(`/alarm/ajax/getAlarmReportLogList`) 에서도 Exception 발생 시 `ExceptionControllerAdvice` 가 `common/error/errorPage` JSP 를 렌더링한다. 결과적으로 클라이언트는 JSON 을 기대했지만 HTML 응답을 받게 되어 jqGrid 가 깨질 수 있다. AJAX 전용 예외 처리(JSON 에러 응답)가 별도로 필요.
- **Dead code (주석된 `LEVEL` 필터)**: 컨트롤러에서 `level` 을 `List<String>` 으로 채워 VO 에 세팅하지만, `getQueryParser` 의 LEVEL 검색 블록은 모두 주석 처리되어 있어 **실제 쿼리에 level 조건이 반영되지 않는다**. (사용자가 화면에서 level 을 선택해도 무효)
- **검색 fall-through (`alarmText` 토큰화)**: `alarmText` 가 공백/특수문자를 포함하면 토큰 단위 AND 검색으로 분해되어, 사용자가 입력한 정확한 문자열과 다른 매칭 결과가 나올 수 있다(예: `"door open"` 입력 → `(ALARMTEXT="door") AND (ALARMTEXT="open")`).
- **page/rows 비검증**: `Integer.parseInt(page)`, `Long.parseLong(pageNum)` 등에서 비숫자 입력 시 `NumberFormatException` → 500 (Exception advice 의 errorPage). 컨트롤러 단에서 page/rows 가 비어 있을 때만 기본값을 주고, 숫자 검증은 하지 않음.
- **HTTP 메서드 미지정**: `@RequestMapping` 에 `method` 명시가 없어 GET/POST 모두 허용된다. CSRF 보호가 없다면 GET 으로도 검색이 가능해 캐싱/로깅 측면에서 노출 위험.
- **세션 부수효과**: 화면 진입(`/alarm/alarmReportLogList`)과 AJAX 호출(`/alarm/ajax/getAlarmReportLogList`) 모두 `fabSite` 가 전달되면 세션을 갱신한다(`Common.setFabSite`). 사용자가 다른 탭/메뉴와 fabSite 를 공유할 때 의도치 않은 상태 전파가 발생할 수 있다.
