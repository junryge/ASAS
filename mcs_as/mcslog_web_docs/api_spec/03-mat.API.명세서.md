# 03. Material(자재/캐리어) 모듈 API 명세서

## 1. API 개요

### 1.1 모듈 설명
SK hynix MCS Log 조회 시스템의 **Material(자재/캐리어)** 모듈은 MCS(Material Control System)에서 발생하는 Carrier(웨이퍼 캐리어/FOUP)의 위치 이력(Carrier Location History)을 조회하는 기능을 제공한다.

- Carrier가 어떤 Machine(Stocker/STB/Lifter/Conveyor/Process/OHT)의 어떤 Unit에 위치했었는지에 대한 이력 로그를 조회한다.
- MCS 로그 메시지 중 `method=createCarrierLocationHistory` 이벤트를 기준으로 조회한다.
- Fab Site / Fab / Level / Area / Bay / Machine Type / Machine Name / Carrier / LotId / CommandId / Unit / 기간 등으로 조건 필터링이 가능하다.

### 1.2 기술 스택
| 항목 | 내용 |
| --- | --- |
| 프레임워크 | Spring MVC (Controller / Service / DAO 구조) |
| 데이터 저장소 | **Logpresso** (MyBatis 아님) — `com.skhynix.supply.common.DBManager` 가 Logpresso 쿼리를 실행 |
| Logpresso 대상 테이블 | `Common.sTS_MATERIAL_*` (Fab Site / Fab별 분기) |
| 트리거 메서드명 | `createCarrierLocationHistory` (MCS Log 내부 method 필드 값) |
| 쿼리 빌더 | `MeterialServiceImpl#getQueryParser(MaterialVo)` — Logpresso 쿼리 동적 생성 |
| 페이징 | `com.skhynix.supply.common.Paging` 적용, 결과에 `limit offset limit` 및 `sort _time` 후처리 |
| 응답 포맷 | `jsonView` (JSON) / `mat/carrierLocLogList` (JSP 뷰) |
| 예외 처리 | `ExceptionControllerAdvice` — 모든 Exception을 `common/error/errorPage` 뷰로 포워딩 (HTTP 200으로 에러 페이지 반환) |

### 1.3 응답 포맷
- **JSP 뷰**: 초기 화면 진입 시 `mat/carrierLocLogList` 뷰를 렌더링하며, Model에 화면 구성에 필요한 코드 리스트(fabsites, fabs, levels, param)를 담아 반환한다.
- **JSON**: AJAX 호출 시 `jsonView` 빈을 이용해 `MappingJacksonJsonView` 형태로 JSON 응답을 내려준다. (`page`, `total`, `records`, `rows` 키)

---

## 2. API 목록

| No | Method | URL | 설명 | 응답형식 |
| --- | --- | --- | --- | --- |
| 1 | GET / POST | `/mat/carrierLocLogList` | Carrier 위치 이력 조회 화면(초기 진입) 및 조건 영역 코드 로드 | JSP (`mat/carrierLocLogList`) |
| 2 | GET / POST | `/mat/ajax/getCarrierLocLogList.do` | Carrier 위치 이력 조회(목록, 페이징) AJAX 호출 | JSON (`jsonView`) |

> 비고: `@RequestMapping` 에 `method` 가 지정되어 있지 않으므로 GET / POST 모두 허용된다.

---

## 3. 상세 API 명세

### 3.1 Carrier 위치 이력 조회 화면 (`/mat/carrierLocLogList`)

#### 3.1.1 개요
- Carrier 위치 이력 조회 메뉴의 **초기 진입 페이지**를 렌더링한다.
- 검색 조건 영역(Fab Site, Fab, Level)에 필요한 코드 리스트를 Model에 담아 JSP로 전달한다.
- 기본 Level 값은 `WELL`, `WARN`, `ERROR`, `FATAL` 4개로 세팅된다.

#### 3.1.2 Request

##### Syntax
```bash
curl -X GET "http://{host}:{port}/{contextPath}/mat/carrierLocLogList" \
     -H "Cookie: JSESSIONID=xxxxxxxxxxxx"

# 또는 POST 도 허용
curl -X POST "http://{host}:{port}/{contextPath}/mat/carrierLocLogList" \
     -H "Cookie: JSESSIONID=xxxxxxxxxxxx" \
     --data-urlencode "fabSite=M14"
```

##### URL
| Item | 값 | 비고 |
| --- | --- | --- |
| URL | `/mat/carrierLocLogList` | `@RequestMapping(value="mat/carrierLocLogList")` |
| Method | GET, POST | `method` 미지정 → 모두 허용 |
| Content-Type | `application/x-www-form-urlencoded` | 일반 form submit |

##### Header
| Header | 필수 | 설명 |
| --- | --- | --- |
| Cookie | 선택 | `JSESSIONID` — Fab Site 세션 유지를 위한 쿠키 |

##### Elements (Form Parameter / `MaterialVo` 바인딩)
> `@ModelAttribute MaterialVo param` 으로 바인딩됨. 초기 화면이지만 VO의 모든 필드를 form 파라미터로 전달 가능하다.

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| fabSite | String | N | 세션값(`Common.getFabSite(request)`) | Fab Site (예: `M14`, `M15`, `M11`, `C2`, `IC`). 값 지정 시 세션에 저장 |
| pageNum | String | N | - | 페이지 번호 (화면 초기 진입시 미사용) |
| rowNum | String | N | - | 한 페이지 행 수 (화면 초기 진입시 미사용) |
| areaName | String | N | - | Area 명 (`ALL` 또는 특정 값) |
| bayName | String | N | - | Bay 명 (`ALL` 또는 특정 값) |
| machineType | List\<String\> | N | - | Machine Type (ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT) |
| machineName | List\<String\> | N | - | Machine 명 |
| fab | List\<String\> | N | `Common.getBasicFabList("mat", fabSite)` | Fab (M14A/M14B/M15A/…) — 초기엔 기본 Fab 리스트로 세팅 |
| level | List\<String\> | N | `[WELL, WARN, ERROR, FATAL]` | 로그 Level — 화면 진입 시 강제 세팅됨 |
| carrier | String | N | - | Carrier ID |
| lotId | String | N | - | Lot ID |
| commandId | String | N | - | Transport Command ID |
| unit | String | N | - | Unit 명 |
| from | String | N | - | 조회 시작 시각 (`yyyyMMddHHmmss`) |
| to | String | N | - | 조회 종료 시각 (`yyyyMMddHHmmss`) |

#### 3.1.3 Response

##### Syntax
- View Name: `mat/carrierLocLogList` (JSP)
- Model 키:

```text
Model:
  - fabsites : List<String>        // Common.FabSites
  - fabs     : List<String>        // 선택된 fabSite에 해당하는 Fab 리스트
  - levels   : List<String>        // Common.Levels
  - param    : MaterialVo          // 화면 바인딩용 (fab/level 기본값 적용 상태)
  - params   : MaterialVo          // param과 동일 객체 참조
```

##### Elements (Model)
| 키 | 타입 | 설명 |
| --- | --- | --- |
| fabsites | List\<String\> | 전체 Fab Site 코드 리스트 (`Common.FabSites`) |
| fabs | List\<String\> | 현재 Fab Site의 Fab 리스트 (`Common.getFabList("mat", fabSite)`) |
| levels | List\<String\> | 전체 Level 리스트 (`Common.Levels`) |
| param | MaterialVo | 검색 조건 VO. `fabSite`, `fab`(기본), `level`(WELL/WARN/ERROR/FATAL) 가 세팅된 상태 |
| params | MaterialVo | `param`과 동일한 객체(중복 등록) |

#### 3.1.4 Error Codes
| 상황 | HTTP | 응답 | 비고 |
| --- | --- | --- | --- |
| 정상 | 200 | `mat/carrierLocLogList` 뷰 | - |
| 임의의 Exception 발생 | 200 (View 포워딩) | `common/error/errorPage` 뷰 (`name`, `message` Model) | `ExceptionControllerAdvice#exception(Exception)` 가 모든 예외를 catch — HTTP status를 별도로 변경하지 않으므로 200으로 응답될 수 있음 |
| 잘못된 fabSite 값 | 200 | 빈 fabs 리스트 또는 에러 페이지 | `Common.getFabList()` 가 매칭 불가 시 빈 리스트 반환 가능 |

#### 3.1.5 Examples

##### 예시 1) 초기 진입 (Fab Site 미지정 → 세션값 사용)
```http
GET /mat/carrierLocLogList HTTP/1.1
Host: mcslog.example.com
Cookie: JSESSIONID=abcd1234
```
Response: `mat/carrierLocLogList` JSP — `param.fabSite`는 세션 값으로 세팅.

##### 예시 2) Fab Site 변경 (M15 선택)
```http
POST /mat/carrierLocLogList HTTP/1.1
Host: mcslog.example.com
Content-Type: application/x-www-form-urlencoded

fabSite=M15
```
Response: `mat/carrierLocLogList` JSP — 세션의 Fab Site가 `M15` 로 변경되며, `fabs` Model 에는 `M15A`, `M15B` 등이 담긴다.

---

### 3.2 Carrier 위치 이력 목록 조회 AJAX (`/mat/ajax/getCarrierLocLogList.do`)

#### 3.2.1 개요
- Carrier 위치 이력 검색 조건을 받아 Logpresso 쿼리를 동적 생성하여 결과를 JSON으로 반환한다.
- 페이징 처리: `Paging` 클래스를 통해 `limit offset limit` 절을 부여하고 `sort _time`을 적용한다.
- 기간이 비어 있으면 자동으로 **최근 10분** (`현재시각 - 10분 ~ 현재시각`, `yyyyMMddHHmmss`)으로 채워진다.
- 호출 흐름: `MaterialController#getList` → `materialService.getDataList(param)` → `MeterialServiceImpl#getQueryParser` → `MaterialDAO#dbExecuteQuery(fabSite, query)` → `DBManager.executeQuery`.

#### 3.2.2 Request

##### Syntax
```bash
curl -X POST "http://{host}:{port}/{contextPath}/mat/ajax/getCarrierLocLogList.do" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "Cookie: JSESSIONID=xxxxxxxxxxxx" \
     --data-urlencode "page=1" \
     --data-urlencode "rows=100" \
     --data-urlencode "fabSite=M14" \
     --data-urlencode "fab1=ALL" \
     --data-urlencode "level1=WELL" \
     --data-urlencode "level2=WARN" \
     --data-urlencode "machineTypes=STOCKER,OHT" \
     --data-urlencode "areaName=ALL" \
     --data-urlencode "bayName=ALL" \
     --data-urlencode "carrier=ABC123" \
     --data-urlencode "lotId=" \
     --data-urlencode "commandId=" \
     --data-urlencode "unit=" \
     --data-urlencode "from=20230101000000" \
     --data-urlencode "to=20230101010000"
```

##### URL
| Item | 값 | 비고 |
| --- | --- | --- |
| URL | `/mat/ajax/getCarrierLocLogList.do` | `@RequestMapping(value="/mat/ajax/getCarrierLocLogList.do")` |
| Method | GET, POST | `method` 미지정 → 모두 허용 |
| Content-Type | `application/x-www-form-urlencoded` | - |

##### Header
| Header | 필수 | 설명 |
| --- | --- | --- |
| Cookie | 선택 | `JSESSIONID` — Fab Site 세션 유지 |
| X-Requested-With | 선택 | `XMLHttpRequest` — 일반 AJAX 헤더 |

##### Elements (Form Parameter)
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | String | N | `"1"` | 페이지 번호 (없거나 빈 문자열이면 1) |
| rows | String | N | `"100"` | 페이지당 행 수 |
| fabSite | String | N | 세션값 | Fab Site (M14/M15/M11/C2/IC). 지정시 세션에 저장 |
| fab1 ~ fabN | String | N | - | Fab 코드. `fab1=ALL` 인 경우 해당 Fab Site의 전체 Fab을 자동 세팅. 그 외엔 `fab1, fab2, …` 순서대로 수집 |
| level1 ~ levelN | String | N | - | Level 코드. `level1, level2, …` 순서대로 수집되어 `MaterialVo.level` 리스트에 담김. **단, 현재 Logpresso 쿼리에서 Level 필터는 주석 처리되어 실제 적용되지 않음** (Section 6 참고) |
| machineTypes | String | N | - | Machine Type 콤마 구분 문자열 (예: `STOCKER,OHT`). 첫 토큰이 `ALL`이면 전체로 간주하여 필터 미적용 |
| areaName | String | N | `ALL` | Area 명. 비어있거나 `ALL` 포함 시 필터 미적용 |
| bayName | String | N | `ALL` | Bay 명. 비어있거나 `ALL` 포함 시 필터 미적용 |
| machineName | List\<String\> | N | - | Machine 명 목록(VO 바인딩). `NOTDESIGNATED` 포함 시 해당 위치에서 break |
| carrier | String | N | - | Carrier ID. 값 있으면 `CARRIER="값"` 필터 추가 |
| lotId | String | N | - | Lot ID. 값 있으면 `LOTID="값"` 필터 추가 |
| commandId | String | N | - | Transport Command ID. 값 있으면 `TRANSPORTCOMMANDID="값"` 필터 추가 |
| unit | String | N | - | Unit 명. `_` 또는 `-` 구분자가 있으면 분해하여 각 토큰별로 `CURRENTUNITNAME="…"` AND 조건 생성 |
| from | String | N | 현재시각-10분 (`yyyyMMddHHmmss`) | 조회 시작 시각 |
| to | String | N | 현재시각 (`yyyyMMddHHmmss`) | 조회 종료 시각 |

> 추가 참고: `MaterialVo` 의 `pageNum`/`rowNum` 은 컨트롤러 내부에서 `page`/`rows` 파라미터로부터 재설정된다.

#### 3.2.3 Response

##### Syntax
- View Name: `jsonView` (스프링 빈 `MappingJacksonJsonView` 가정)

```json
{
  "page": 1,
  "total": 5,
  "records": 100,
  "rows": [
    {
      "_time": "2023-01-01 00:00:01",
      "TIME_EX": "2023-01-01 00:00:01.123",
      "CARRIER": "ABC123",
      "LOTID": "LOT0001",
      "TRANSPORTCOMMANDID": "TC0001",
      "CURRENTMACHINENAME": "STK001",
      "MACHINETYPE": "STOCKER",
      "CURRENTUNITNAME": "U01"
    }
  ]
}
```

##### Elements (Model / JSON)
| 키 | 타입 | 설명 |
| --- | --- | --- |
| page | int | 현재 페이지 번호 (`Paging.getCurrentPageNo()`) |
| total | int | 전체 페이지 수 (`Paging.getNumberOfRecords()`) — 변수명과 다르게 페이지 수임에 유의 |
| records | int | 페이지당 행 수 (`Paging.getRecordsPerPage()`) |
| rows | List\<Map\> | Logpresso 결과 행 목록. 각 행은 아래 필드를 포함 |

##### `rows[]` 원소 필드 (Logpresso 쿼리 fields 절에 명시된 컬럼)
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `_time` | String/Date | 로그 발생 시각 (Logpresso 시스템 컬럼) |
| `TIME_EX` | String | 확장 시각(ms 단위 포함) |
| `CARRIER` | String | Carrier ID |
| `LOTID` | String | Lot ID |
| `TRANSPORTCOMMANDID` | String | Transport Command ID |
| `CURRENTMACHINENAME` | String | 현재 Machine 명 |
| `MACHINETYPE` | String | Machine Type |
| `CURRENTUNITNAME` | String | 현재 Unit 명 |

#### 3.2.4 Error Codes
> `ExceptionControllerAdvice` 가 모든 Exception을 catch하여 `common/error/errorPage` 뷰로 포워딩한다. 별도 HTTP status 변경이 없어 일반적으로 **HTTP 200**으로 에러 페이지가 반환된다. 다만 AJAX 호출에서 JSON이 아닌 HTML이 반환되는 형태가 되므로 클라이언트에서 파싱 오류가 발생할 수 있다.

| 상황 | HTTP | 동작 | 원인 |
| --- | --- | --- | --- |
| Logpresso 쿼리 실행 실패 (SQL/Syntax/연결 에러) | 200 | `common/error/errorPage` 또는 빈 결과 | `MaterialDAO.dbExecuteQuery()` 내에서 catch 후 `null` 반환됨 → 컨트롤러에서 `list==null` 이면 페이징 미적용. 로그만 `log.warn` 남김 |
| 잘못된 파라미터 (`page`/`rows`가 숫자가 아닌 경우) | 200 | `errorPage` | `Integer.parseInt`, `Long.parseLong` 에서 `NumberFormatException` → ExceptionControllerAdvice 처리 |
| `fabSite` 가 매핑 불가 값 | 200 | 빈 결과 | `getTableFromFab()` 가 `null` 반환 → `tQuery` 가 비어 `from` 절 비정상이 되어 Logpresso 쿼리 실행 실패 가능 |
| `MaterialVo` 가 null | 200 | 빈 결과 | `getQueryParser` 에서 null 체크 후 `null` 반환 → DAO 호출 생략 |
| 임의의 RuntimeException | 200 | `errorPage` (`name`, `message`) | `ExceptionControllerAdvice#exception(Exception)` |

#### 3.2.5 Examples

##### 예시 1) 기본 검색 (시간 미지정 → 최근 10분, Fab Site M14)
Request:
```http
POST /mat/ajax/getCarrierLocLogList.do HTTP/1.1
Content-Type: application/x-www-form-urlencoded

page=1&rows=100&fabSite=M14&fab1=ALL&areaName=ALL&bayName=ALL
```
Response (JSON):
```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "_time": "2023-05-01 10:00:01",
      "TIME_EX": "2023-05-01 10:00:01.456",
      "CARRIER": "FOUP0001",
      "LOTID": "LOTA001",
      "TRANSPORTCOMMANDID": "TC10001",
      "CURRENTMACHINENAME": "STK01",
      "MACHINETYPE": "STOCKER",
      "CURRENTUNITNAME": "U01"
    }
  ]
}
```

##### 예시 2) Carrier ID 및 기간 지정 (Fab Site M15, M15A/M15B 둘 다)
Request:
```http
POST /mat/ajax/getCarrierLocLogList.do HTTP/1.1
Content-Type: application/x-www-form-urlencoded

page=1&rows=50&fabSite=M15&fab1=M15A&fab2=M15B
&carrier=FOUP0001
&from=20230501000000&to=20230501235959
&machineTypes=STOCKER,OHT
&areaName=ALL&bayName=ALL
```
Response (JSON):
```json
{
  "page": 1,
  "total": 0,
  "records": 50,
  "rows": []
}
```

---

## 4. 자원 모델

### 4.1 MaterialVo 필드 전체

| 필드 | 타입 | 의미 / 용도 |
| --- | --- | --- |
| fabSite | String | Fab Site 코드 (M14/M15/M11/C2/IC). DBManager 접속 분기 및 테이블 결정에 사용 |
| pageNum | String | 페이지 번호 (Service에서 `Long.parseLong` 변환 후 offset 계산) |
| rowNum | String | 페이지당 행 수 (Service에서 `Integer.parseInt` 변환 후 limit 적용) |
| areaName | String | Area 명. 빈 값 또는 `ALL` 시 필터 미적용 |
| bayName | String | Bay 명. 빈 값 또는 `ALL` 시 필터 미적용 |
| machineType | List\<String\> | Machine Type 리스트. `ALL` 포함 시 필터 비움. 그 외 토큰들은 `search_in` 형태로 쿼리 조립 |
| machineName | List\<String\> | Machine 명 리스트. `NOTDESIGNATED` 포함 시 해당 인덱스에서 break, OR 조건으로 묶임 |
| fab | List\<String\> | Fab 코드 리스트. 각 Fab을 `getTableFromFab()` 로 변환하여 `from` 절의 테이블 목록을 구성 |
| level | List\<String\> | 로그 Level 리스트. 현재 Logpresso 쿼리에서는 **주석 처리되어 미사용** (이슈 참고) |
| carrier | String | Carrier ID 단건 검색 |
| lotId | String | Lot ID 단건 검색 |
| commandId | String | Transport Command ID 단건 검색 |
| unit | String | Unit 명. `_` 또는 `-` 포함 시 분해하여 다중 `CURRENTUNITNAME` AND 조건 생성 |
| from | String | 조회 시작 시각 (`yyyyMMddHHmmss`) |
| to | String | 조회 종료 시각 (`yyyyMMddHHmmss`) |

### 4.2 Logpresso 대상 테이블 (Fab Site / Fab 매핑)

`MeterialServiceImpl#getTableFromFab(fabSite, fab)` 의 분기 결과:

| Fab Site | Fab | 테이블 (Common 상수) |
| --- | --- | --- |
| `M14` | (모든 fab) | `Common.sTS_MATERIAL_M14A` |
| `M15` | `M15A` | `Common.sTS_MATERIAL_M15A` |
| `M15` | `M15B` | `Common.sTS_MATERIAL_M15B` |
| `M11` | `M11A` | `Common.sTS_MATERIAL_M11A` |
| `M11` | `M11B` | `Common.sTS_MATERIAL_M11B` |
| `C2` | `C2` | `Common.sTS_MATERIAL_C2` |
| `C2` | `C2F` | `Common.sTS_MATERIAL_C2F` |
| `IC` | `M14A` | `Common.sTS_MATERIAL_M14A` |
| `IC` | `M16A` | `Common.sTS_MATERIAL_M16A` |
| `IC` | `M16B` | `Common.sTS_MATERIAL_M16B` |
| 그 외 | - | `null` (테이블 결정 실패) |

> 주의: `switch` 문에 `break`가 없어 case fall-through 가 발생할 수 있다 (Section 6 이슈 참고).

### 4.3 Logpresso 조회 컬럼

`fields` 절에 명시되는 결과 컬럼:
- `_time`
- `TIME_EX`
- `CARRIER`
- `LOTID`
- `TRANSPORTCOMMANDID`
- `CURRENTMACHINENAME`
- `MACHINETYPE`
- `CURRENTUNITNAME`

### 4.4 동적 쿼리 구조 (의사 코드)

```text
fulltext from=<from> to=<to> ( method="createCarrierLocationHistory" )
  [ AND ( CARRIER="<carrier>" ) ]
  [ AND ( LOTID="<lotId>" ) ]
  [ AND ( TRANSPORTCOMMANDID="<commandId>" ) ]
  [ AND ( CURRENTUNITNAME="<unit>" ) | 분해형 ]
  [ AND ( AREANAME="<areaName>" ) ]
  [ AND ( BAYNAME="<bayName>" ) ]
  [ AND ( CURRENTMACHINENAME="<name>" OR … ) ]
from <table1>[, <table2>, …]
[ search in(MACHINETYPE, "T1", "T2", …) ]
fields _time, TIME_EX, CARRIER, LOTID, TRANSPORTCOMMANDID,
       CURRENTMACHINENAME, MACHINETYPE, CURRENTUNITNAME
| limit <offset> <limit>
| sort _time
```

---

## 5. 인증 및 권한

코드 검토 결과:
- `MaterialController` 및 `MaterialService` / `MaterialDAO` 어느 곳에도 **`@Secured` / `@PreAuthorize` / 인증 체크 로직이 존재하지 않는다.**
- 인증/인가는 별도의 **Spring Security 필터** 또는 **Servlet Filter / Interceptor 레벨**에서 처리되는 것으로 추정된다. (본 모듈 소스에는 명시되어 있지 않음)
- 세션 기반 식별만 사용: `Common.getFabSite(request)` / `Common.setFabSite(request, fabSite)` 로 Fab Site를 세션에 저장하여 사용자별 컨텍스트를 유지한다.
- 즉, 본 모듈 자체는 별도의 권한 검사 없이 호출 가능한 구조이며, 권한 통제는 컨테이너/공통 필터 레벨에 위임된다.

---

## 6. 비고 / 이슈

### 6.1 클래스명 오타
- 서비스 구현 클래스명이 **`MeterialServiceImpl`** 로 오타되어 있다 (정상은 `MaterialServiceImpl`).
- 빈 이름은 `@Service("materialService")` 로 등록되어 있어 주입은 정상 동작한다.
- 파일 경로: `com.skhynix.supply.mat.service.impl.MeterialServiceImpl`

### 6.2 `getTableFromFab` switch 문 — break 누락 (잠재 버그)
- `MeterialServiceImpl#getTableFromFab` 의 모든 `case` 블록에 `break` 가 없다.
- 각 case 가 `return` 으로 종료되는 경우가 대부분이지만, **case M15 에서 fab 이 M15A/M15B 가 아닌 경우 return 이 실행되지 않아** 다음 case(`M11`) 로 fall-through 한다.
- 동일한 위험이 `M11`, `C2`, `IC` case 에도 존재 (예: M11 의 fab 이 M11A/M11B 가 아니면 C2 case 로 fall-through).
- 결과: 잘못된 Fab 값이 들어오면 의도하지 않은 다른 Fab Site 의 테이블이 사용될 가능성이 있음.

### 6.3 Level 필터 비활성
- `MaterialController#getList` 에서 `level1`~`levelN` 파라미터를 수집하여 `param.setLevel(levels)` 까지는 호출하지만,
- `MeterialServiceImpl#getQueryParser` 의 **LEVEL 처리 블록이 전부 주석 처리** 되어 있어 실제 Logpresso 쿼리에는 Level 조건이 적용되지 않는다.
- 화면에서 Level 체크박스를 변경해도 결과 필터링에 영향이 없다.

### 6.4 `subMachineTypeQuery` 적용 위치
- `subMachineTypeQuery` 가 `from` 절 뒤에 붙는 형태(`sQuery.append(Common.sFrom + tQuery); sQuery.append(Common.sCRLF + subMachineTypeQuery);`)로, 일반적인 `AND` 조건과 적용 위치가 다르다.
- Logpresso 의 `search in(...)` 구문이 `from` 다음에 파이프 없이 이어붙는 구조이므로, 쿼리 문법 또는 결과 정확성 측면에서 재검토 필요.

### 6.5 Dead Code / 주석 처리된 로직
- `MaterialController#carrierLocLogList` 의 `bayNameList`, `machineNameList`, `machineTypeInfoList`, `Common.sFAB_SITE` 관련 라인이 주석 처리됨.
- `MaterialController#getList` 의 level1~level8 수집 로직, fab session 강제 세팅, level1==ALL 분기, level 미지정시 기본값 세팅 로직 등이 주석 처리됨.
- `MeterialServiceImpl#getQueryParser` 의 `sTYPE` 기반 분기, LEVEL 필터 블록, `sTable` 단일 분기 코드가 주석 처리됨.
- `MaterialDAO#dbExecuteQuery` 의 `ThreadPool`/`Callable` 기반 코드가 주석 처리됨.

### 6.6 `dbExecuteQuery` 예외 삼킴
- `MaterialDAO#dbExecuteQuery` 는 내부에서 `catch (Exception ex)` 로 모든 예외를 잡고 `log.warn` 만 남긴 후 `null` 을 반환한다.
- 호출부(`MeterialServiceImpl`) 는 `null` 결과를 별도 처리하지 않고 그대로 반환하며, 컨트롤러는 `list == null` 시 페이징을 생략하고 응답에 `rows: null` 형태로 내려간다.
- 결과적으로 Logpresso 장애 시에도 호출자는 정상 응답을 받게 되며, 장애 원인은 서버 로그에만 남는다 → **에러 가시성이 낮음**.

### 6.7 `subMachineTypeQuery != null` 조건 (논리 오류)
- `MeterialServiceImpl#getQueryParser` 내 `if (subMachineTypeQuery != null || !(subMachineTypeQuery.toString().isEmpty()))` 는 `subMachineTypeQuery` 가 항상 non-null 이므로 사실상 **항상 true** 가 되는 의미 없는 조건이다. (`&&` 의도였을 가능성)

### 6.8 페이징 `Paging.nTotalCount` static 사용
- `paging.setNumberOfRecords(Paging.nTotalCount)` 가 **정적 변수** 를 사용한다. 동시 요청 시 다른 사용자의 카운트가 섞일 수 있는 **스레드 안전성 이슈** 우려.

### 6.9 `MaterialVo` 변수명과 의미 불일치
- VO 필드 주석에 따르면 `level` 은 `ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL` 을 의도하지만, 화면 진입 시 강제 세팅값은 `WELL/WARN/ERROR/FATAL` 4개로 제한된다.

### 6.10 응답 모델 키 명명
- 응답 JSON 의 `total` 키는 실제로는 "총 페이지 수" 를 의미하며, "총 레코드 수" 로 오해될 소지가 있다. (Paging 클래스 메서드명: `getNumberOfRecords` 이나 페이지 수를 의미)

### 6.11 `@SuppressWarnings("rawtypes")` 사용
- `List<Map>` 형태의 raw type 사용 — 타입 안전성 측면에서 `List<Map<String, Object>>` 로의 마이그레이션 검토 가능.

---
