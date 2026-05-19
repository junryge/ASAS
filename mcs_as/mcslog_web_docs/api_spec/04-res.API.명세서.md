# 04. res (자원 이력) 모듈 API 명세서

> SK hynix MCS Log 조회 시스템 — Resource History 조회 API

---

## 1. API 개요

### 1.1 모듈 설명

`res` 모듈은 MCS(Material Control System) 운영 중 발생하는 **자원(Resource) 상태 변경 이력**을 Logpresso 기반 로그 저장소로부터 조회하는 모듈이다. 사용자는 웹 UI(JSP) 화면에서 검색 조건(자원 이름, 상태, 시간 범위, FAB, Bay 등)을 입력하여 해당 자원 타입의 상태 변경 이력을 페이징 형태로 조회할 수 있다.

자원 타입은 총 6종이며, 각 자원 타입별로 1개의 화면 진입 엔드포인트와 1개의 AJAX 조회 엔드포인트(총 12개)가 제공된다.

| 자원 타입 | 설명 | 대응 Method 키 (Logpresso) |
|---|---|---|
| Crane | OHCV/OHT 등의 크레인 자원 상태 이력 | `createCraneHistory` |
| Machine | 머신(Stocker/Lifter/Conveyor 등) 자원 상태 이력 | `createMachineHistory` |
| Port | 머신 포트의 상태 이력 (적재/만재/IN/OUT 등) | `createPortHistory` |
| Shelf | Stocker 내부 Shelf(선반)의 상태 이력 | `createShelfHistory` |
| StorageFull | Storage(저장영역) Full 상태 이력 | `createStorageFullHistory` |
| Vehicle | 반송차(Vehicle) 상태 이력 | `createVehicleHistory` |

### 1.2 6개 서브-모듈 개요

| 서브모듈 | 컨트롤러 | ServiceImpl | VO | 화면 URL | AJAX URL |
|---|---|---|---|---|---|
| Crane | `ResCraneHistoryController` | `resCraneHistoryServiceImpl` | `ResCraneVo` | `/res/craneLogList` | `/res/ajax/getCraneLogList` |
| Machine | `ResMachineHistoryController` | `resMachineHistoryServiceImpl` | `ResMachineVo` | `/res/machineLogList` | `/res/ajax/getMachineLogList` |
| Port | `ResPortHistoryController` | `resPortHistoryServiceImpl` | `ResPortVo` | `/res/portLogList` | `/res/ajax/getPortLogList` |
| Shelf | `ResShelfHistoryController` | `resShelfHistoryServiceImpl` | `ResShelfVo` | `/res/shelfLogList` | `/res/ajax/getShelfLogList` |
| StorageFull | `ResStorageFullHistoryController` | `resStorageFullHistoryServiceImpl` | `ResStorageFullVo` | `/res/storageLogList` | `/res/ajax/getStorageLogList` |
| Vehicle | `ResVehicleHistoryController` | `resVehicleHistoryServiceImpl` | `ResVehicleVo` | `/res/vehicleLogList` | `/res/ajax/getVehicleLogList` |

### 1.3 공통 패턴

6개 자원 타입의 컨트롤러는 거의 동일한 패턴을 따른다.

**(A) 화면 진입 엔드포인트 (`/res/{type}LogList`)** — GET/POST 모두 허용 (`@RequestMapping` value만 지정).
- ViewName: `res/{type}LogList` (JSP)
- 처리 내용:
  1. Fab Site 결정 (request 파라미터 `fabSite` 또는 세션) — `Common.getFabSite()` / `Common.setFabSite()`
  2. `param.setFab(Common.getBasicFabList("res", sFabSite))` — 기본 FAB 리스트 세팅
  3. `param.setLevel([WELL, WARN, ERROR, FATAL])` — 기본 Level
  4. Model에 `fabsites`, `fabs`, `levels`, `param`, `params` 객체 추가

**(B) AJAX 엔드포인트 (`/res/ajax/get{Type}LogList`)** — JSON 응답 (`jsonView`).
- 처리 내용:
  1. 페이징: `page` (default `1`), `rows` (default `100`)
  2. 시간: `from`, `to` (default = 현재 - 10분 ~ 현재, `yyyyMMddHHmmss`)
  3. `fab1`,`fab2`,...,`level1`,`level2`,...,`machineTypes` (CSV) 파라미터 조립
  4. `areaName`, `bayName` 누락 시 `ALL`로 보정
  5. `resHistoryService.getDataList(param)` 호출 → Logpresso 쿼리 실행
  6. `Paging` 인스턴스로 페이지 메타데이터 계산 후 JSON 응답

**(C) Service 호출 흐름**

```
Controller → resHistoryService.getDataList(VO)
            → ServiceImpl.getQueryParser(VO)   // Logpresso 쿼리 문자열 빌드
            → resultQuery + " | limit OFFSET LIMIT | sort _time"
            → ResHistoryDAO.dbExecuteQuery(fabSite, queryStmt)
            → DBManager.executeQuery(queryStmt) → List<Map>
```

**(D) Logpresso 쿼리 템플릿 (공통 골격)**

```
fulltext from=YYYYMMDDhhmmss to=YYYYMMDDhhmmss "(method=\"create{Type}History\")"
  and (필드=값) and (필드=값) ...
  and (areaName="...") and (bayName="...")
  and (machineName="..." or machineName="...")
from   <테이블명(들)>
search in (machineType, "STOCKER","STB", ...)   // ALL 이면 생략
fields _time, time_ex, machineName, machineType, ... (타입별 컬럼)
| limit OFFSET LIMIT
| sort _time
```

테이블 매핑(`getTableFromFab(fabSite, fab)` — 6개 ServiceImpl 동일):

| Fab Site | Fab | 테이블 상수 |
|---|---|---|
| M14 | (any) | `Common.sTS_RESOURCE_M14A` |
| M15 | M15A / M15B | `sTS_RESOURCE_M15A` / `sTS_RESOURCE_M15B` |
| M11 | M11A / M11B | `sTS_RESOURCE_M11A` / `sTS_RESOURCE_M11B` |
| C2 | C2 / C2F | `sTS_RESOURCE_C2` / `sTS_RESOURCE_C2F` |
| IC | M14A / M16A / M16B | `sTS_RESOURCE_M14A` / `sTS_RESOURCE_M16A` / `sTS_RESOURCE_M16B` |

---

## 2. API 목록

총 **12개** 엔드포인트.

| # | HTTP | URL | 컨트롤러 메서드 | 응답 ViewName | VO |
|---|---|---|---|---|---|
| 1 | GET/POST | `/res/craneLogList` | `ResCraneHistoryController.carrierLocLogList` | `res/craneLogList` (JSP) | `ResCraneVo` |
| 2 | GET/POST | `/res/ajax/getCraneLogList` | `ResCraneHistoryController.getCraneLogList` | `jsonView` | `ResCraneVo` |
| 3 | GET/POST | `/res/machineLogList` | `ResMachineHistoryController.carrierLocLogList` | `res/machineLogList` (JSP) | `ResMachineVo` |
| 4 | GET/POST | `/res/ajax/getMachineLogList` | `ResMachineHistoryController.getMachineLogList` | `jsonView` | `ResMachineVo` |
| 5 | GET/POST | `/res/portLogList` | `ResPortHistoryController.portLogList` | `res/portLogList` (JSP) | `ResPortVo` |
| 6 | GET/POST | `/res/ajax/getPortLogList` | `ResPortHistoryController.getPortLogList` | `jsonView` | `ResPortVo` |
| 7 | GET/POST | `/res/shelfLogList` | `ResShelfHistoryController.portLogList` | `res/shelfLogList` (JSP) | `ResShelfVo` |
| 8 | GET/POST | `/res/ajax/getShelfLogList` | `ResShelfHistoryController.getShelfLogList` | `jsonView` | `ResShelfVo` |
| 9 | GET/POST | `/res/storageLogList` | `ResStorageFullHistoryController.carrierLocLogList` | `res/storageLogList` (JSP) | `ResStorageFullVo` |
| 10 | GET/POST | `/res/ajax/getStorageLogList` | `ResStorageFullHistoryController.getStorageLogList` | `jsonView` | `ResStorageFullVo` |
| 11 | GET/POST | `/res/vehicleLogList` | `ResVehicleHistoryController.portLogList` | `res/vehicleLogList` (JSP) | `ResVehicleVo` |
| 12 | GET/POST | `/res/ajax/getVehicleLogList` | `ResVehicleHistoryController.getVehicleLogList` | `jsonView` | `ResVehicleVo` |

---

## 3. 상세 API 명세

### 3.0 공통 패턴

**Request Header (공통)**

| 헤더 | 값 | 필수 | 비고 |
|---|---|---|---|
| `Content-Type` | `application/x-www-form-urlencoded` | △ | POST 사용 시 |
| `Cookie` | `JSESSIONID=...` | ○ | 세션 유지 (FAB Site 세션 저장용) |
| `Accept` | `text/html` (화면) / `application/json` (AJAX) | △ | 선택 |

**Request Elements — 화면 진입 공통**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `fabSite` | String | × | 세션 값 또는 `Common` 기본 | FAB Site 식별자 (예: `M14`, `M15`, `M11`, `C2`, `IC`) |

**Request Elements — AJAX 공통**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `fabSite` | String | × | 세션 | FAB Site 식별자 |
| `page` | String(int) | × | `1` | 페이지 번호 (1-base) |
| `rows` | String(int) | × | `100` | 페이지당 행 수 |
| `from` | String(`yyyyMMddHHmmss`) | × | 현재시각 - 10분 | 조회 시작 시간 |
| `to` | String(`yyyyMMddHHmmss`) | × | 현재시각 | 조회 종료 시간 |
| `fab1`,`fab2`,...,`fabN` | String | × | 기본 FAB 리스트 | 다중 FAB 선택. `fab1=ALL` 이면 전체 |
| `level1`,`level2`,...,`levelN` | String | × | `[WELL,WARN,ERROR,FATAL]` | 다중 Level 선택 (단, 현재 ServiceImpl 코드에서는 LEVEL이 쿼리에 반영되지 않고 주석처리되어 있음) |
| `machineTypes` | String (CSV) | × | (없음) | 쉼표 구분 다중 MachineType. 값이 `ALL`이면 무시 |
| `areaName` | String | × | `ALL` | 지역명. `ALL`이면 쿼리 조건에서 제외 |
| `bayName` | String | × | `ALL` | Bay명. `ALL`이면 쿼리 조건에서 제외 |
| `machineName` (List 바인딩) | String[] | × | (없음) | 머신명 다중 선택 |

> 자원 타입별 **추가 조건 필드**는 각 절(3.1 ~ 3.6)에서 별도로 명세함.

**Response — 화면 진입 공통 (HTML / JSP Model)**

| 모델 키 | 타입 | 설명 |
|---|---|---|
| `fabsites` | `List<String>` | 선택 가능한 FAB Site 목록 |
| `fabs` | `List<String>` | 해당 FAB Site의 FAB 목록 |
| `levels` | `List<String>` | Level 옵션 목록 |
| `param` | VO | 입력 파라미터 (양식 유지용) |
| `params` | VO | 입력 파라미터 (alias) |

**Response — AJAX 공통 (JSON `jsonView`)**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page` | int | 현재 페이지 번호 |
| `total` | int | 총 페이지 수 (Paging.numberOfRecords) |
| `records` | int | 페이지당 행 수 |
| `rows` | `List<Map>` | 자원 이벤트 행 리스트 — 각 Row는 Logpresso `fields` 절에 명시된 컬럼들의 Map |

**Error Codes (공통)**

| HTTP | 발생 조건 | 처리 |
|---|---|---|
| 200 | 정상 (결과 0건이어도 200) | `rows: []` 또는 null |
| 200 (HTML) | 컨트롤러 내 `Exception` 발생 | `ExceptionControllerAdvice`가 `common/error/errorPage` JSP를 반환, model에 `name`(예외 클래스명), `message`(예외 메시지) 포함 |
| 500 | View 렌더 실패 등 Spring 내부 오류 | 표준 톰캣 오류 페이지 |

> `ExceptionControllerAdvice`(`@ControllerAdvice`)는 모든 `Exception`을 `errorPage`로 통합 처리한다. AJAX 호출에서 예외가 발생해도 HTML 형태의 에러 페이지가 반환되므로 클라이언트 측에서는 응답 Content-Type 검증이 필요하다.

**Error Response Example (HTML)**

```html
<!-- common/error/errorPage.jsp 렌더링 결과 -->
<html>
<body>
  <h2>NumberFormatException</h2>
  <pre>For input string: "abc"</pre>
</body>
</html>
```

---

### 3.1 Crane 서브모듈

#### 3.1.1 `GET/POST /res/craneLogList` — Crane 이력 조회 화면 진입

자원 Crane 이력 조회 페이지의 입력 폼을 렌더링한다. (`carrierLocLogList`라는 메서드명은 historical artifact — 실제로는 Crane 이력 화면 진입)

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/craneLogList` |
| Content-Type | `application/x-www-form-urlencoded` (POST 시) |

**Request — Header** : 공통 헤더 참조 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터 (3.0). `ResCraneVo`의 모든 필드를 폼 바인딩으로 전달 가능 (4절 참조).

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  "http://<host>/res/craneLogList?fabSite=M14"
```

**Response — JSP Model**

| 모델 키 | 타입 | 설명 |
|---|---|---|
| `fabsites` | `List<String>` | FAB Site 옵션 |
| `fabs` | `List<String>` | FAB 옵션 |
| `levels` | `List<String>` | Level 옵션 |
| `param` / `params` | `ResCraneVo` | 입력 폼 VO (FAB·Level 기본값 세팅됨) |

ViewName: `res/craneLogList`

**Response 예시 (Model JSON 표현)**

```json
{
  "fabsites": ["M14","M15","M11","C2","IC"],
  "fabs": ["M14A"],
  "levels": ["ALL","DEBUG","INFO","FINE","WELL","WARN","ERROR","FATAL"],
  "param": {
    "fabSite": "M14",
    "fab": ["M14A"],
    "level": ["WELL","WARN","ERROR","FATAL"]
  }
}
```

**Error Codes** : 공통 (3.0)

---

#### 3.1.2 `GET/POST /res/ajax/getCraneLogList` — Crane 이력 AJAX 조회

Crane 이력 검색 결과를 JSON으로 반환한다.

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getCraneLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (Crane 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 (`page`,`rows`,`from`,`to`,`fab*`,`level*`,`machineTypes`,`areaName`,`bayName`,`machineName`,`fabSite`) |
| `craneName` | String | × | (없음) | 크레인 이름 — Logpresso 조건 `craneName="..."` |
| `state` | String | × | (없음) | 상태 — `state="..."` |
| `subState` | String | × | (없음) | 서브 상태 — `subState="..."` |
| `processingState` | String | × | (없음) | 처리 상태 — `processingState="..."` |
| `transportCommandId` | String | × | (없음) | 운반명령 ID — `transportCommandId="..."` |

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M14&fab1=M14A&page=1&rows=100" \
  -d "from=20240101000000&to=20240101010000" \
  -d "craneName=OHCV01&state=Running&machineTypes=STOCKER,LIFTER" \
  "http://<host>/res/ajax/getCraneLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "_time": "2024-01-01 00:05:12+0900",
      "time_ex": "20240101000512123",
      "machineName": "STK001",
      "machineType": "STOCKER",
      "craneName": "OHCV01",
      "state": "Running",
      "processingState": "Idle",
      "transportCommandId": "TC-0001",
      "idReadState": "OK",
      "subState": "Ready"
    }
  ]
}
```

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page` | int | 현재 페이지 |
| `total` | int | 총 페이지 수 |
| `records` | int | 페이지당 레코드 수 |
| `rows[].‌_time` | String | 이벤트 시각 |
| `rows[].time_ex` | String | 마이크로초 정밀 시각 |
| `rows[].machineName` | String | 머신 이름 |
| `rows[].machineType` | String | 머신 타입 |
| `rows[].craneName` | String | 크레인 이름 |
| `rows[].state` | String | 상태 |
| `rows[].processingState` | String | 처리 상태 |
| `rows[].transportCommandId` | String | 운반명령 ID |
| `rows[].idReadState` | String | ID 리드 상태 |
| `rows[].subState` | String | 서브 상태 |

**Error Codes** : 공통 (3.0). 특히 `page`/`rows`가 비숫자일 경우 `NumberFormatException` 발생 가능 → 에러 페이지 렌더.

---

### 3.2 Machine 서브모듈

#### 3.2.1 `GET/POST /res/machineLogList` — Machine 이력 조회 화면 진입

머신 이력 조회 페이지를 렌더링한다.

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/machineLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터. `ResMachineVo` 폼 바인딩.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  "http://<host>/res/machineLogList?fabSite=M15"
```

**Response — JSP Model** : 공통 (3.0). ViewName: `res/machineLogList`.

**Response 예시**

```json
{
  "fabsites": ["M14","M15","M11","C2","IC"],
  "fabs": ["M15A","M15B"],
  "levels": ["ALL","DEBUG","INFO","FINE","WELL","WARN","ERROR","FATAL"],
  "param": { "fabSite": "M15", "fab": ["M15A","M15B"], "level": ["WELL","WARN","ERROR","FATAL"] }
}
```

**Error Codes** : 공통 (3.0)

---

#### 3.2.2 `GET/POST /res/ajax/getMachineLogList` — Machine 이력 AJAX 조회

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getMachineLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (Machine 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 |
| `state` | String | × | (없음) | 머신 상태 |
| `connectionState` | String | × | (없음) | 연결 상태 |
| `controlState` | String | × | (없음) | 제어 상태 |
| `tscState` | String | × | (없음) | TSC(Transport Service Coordinator) 상태 |
| `processingState` | String | × | (없음) | 처리 상태 |

> Crane VO의 `craneName`,`subState`,`transportCommandId`는 Machine VO에 **없음**.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M15&fab1=M15A&page=1&rows=50" \
  -d "from=20240101000000&to=20240101010000" \
  -d "state=Running&controlState=Online&machineTypes=STOCKER" \
  "http://<host>/res/ajax/getMachineLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 50,
  "rows": [
    {
      "_time": "2024-01-01 00:10:01+0900",
      "time_ex": "20240101001001456",
      "machineName": "STK001",
      "machineType": "STOCKER",
      "state": "Running",
      "controlState": "Online",
      "connectionState": "Connected",
      "tscState": "Active",
      "processingState": "Idle"
    }
  ]
}
```

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page`,`total`,`records` | int | 페이징 메타 |
| `rows[].‌_time`, `time_ex` | String | 시각 |
| `rows[].machineName` / `machineType` | String | 머신 |
| `rows[].state` | String | 상태 |
| `rows[].controlState` | String | 제어 상태 |
| `rows[].connectionState` | String | 연결 상태 |
| `rows[].tscState` | String | TSC 상태 |
| `rows[].processingState` | String | 처리 상태 |

**Error Codes** : 공통 (3.0)

---

### 3.3 Port 서브모듈

#### 3.3.1 `GET/POST /res/portLogList` — Port 이력 조회 화면 진입

포트 이력 조회 페이지를 렌더링한다.

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/portLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터. `ResPortVo` 폼 바인딩.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" "http://<host>/res/portLogList?fabSite=M14"
```

**Response — JSP Model** : 공통 (3.0). ViewName: `res/portLogList`.

**Error Codes** : 공통 (3.0)

---

#### 3.3.2 `GET/POST /res/ajax/getPortLogList` — Port 이력 AJAX 조회

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getPortLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (Port 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 |
| `portName` | String | × | (없음) | 포트명. **`_`(underbar) 포함 시** `_`로 split 하여 `(portName="A") and (portName="B")` 형태로 다중 AND 조건 생성 |
| `state` | String | × | (없음) | 상태 |
| `subState` | String | × | (없음) | 서브 상태 |
| `processingState` | String | × | (없음) | 처리 상태 |
| `banned` | String | × | (없음) | 금지 여부 (`true`/`false`) |
| `craneAvailable` | String | × | (없음) | 크레인 가용 여부 |
| `inOutType` | String | × | (없음) | 입출 타입 (`IN`/`OUT` 등) |
| `manual` | String | × | (없음) | 수동 모드 여부 |
| `accessMode` | String | × | (없음) | 접근 모드 |
| `idReadState` | String | × | (없음) | ID 리드 상태 |

> VO에는 `occupied`, `transportUnitAccessible` 필드도 존재하나 `getQueryParser`의 조건절에는 사용되지 않고 응답 `fields`(`occupied`, `transportUnitAccessible`)로만 노출된다.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M14&fab1=M14A&page=1&rows=100" \
  -d "from=20240101000000&to=20240101010000" \
  -d "portName=P01_P02&state=ReadyToLoad&inOutType=OUT" \
  "http://<host>/res/ajax/getPortLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "_time": "2024-01-01 00:20:33+0900",
      "time_ex": "20240101002033111",
      "machineName": "STK001",
      "machineType": "STOCKER",
      "portName": "P01",
      "state": "ReadyToLoad",
      "processingState": "Idle",
      "subState": "Empty",
      "inOutType": "OUT",
      "manual": "false",
      "occupied": "false",
      "banned": "false",
      "transportUnitAccessible": "true",
      "idReadState": "OK",
      "accessMode": "Auto"
    }
  ]
}
```

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page`,`total`,`records` | int | 페이징 메타 |
| `rows[].‌_time`, `time_ex` | String | 시각 |
| `rows[].machineName`, `machineType` | String | 머신 |
| `rows[].portName` | String | 포트명 |
| `rows[].state` / `processingState` / `subState` | String | 상태들 |
| `rows[].inOutType` | String | 입출 타입 |
| `rows[].manual` | String | 수동 여부 |
| `rows[].occupied` | String | 점유 여부 |
| `rows[].banned` | String | 금지 여부 |
| `rows[].transportUnitAccessible` | String | 운반유닛 접근가능 여부 |
| `rows[].idReadState` | String | ID 리드 상태 |
| `rows[].accessMode` | String | 접근 모드 |

**Error Codes** : 공통 (3.0)

---

### 3.4 Shelf 서브모듈

#### 3.4.1 `GET/POST /res/shelfLogList` — Shelf 이력 조회 화면 진입

> 컨트롤러 메서드명이 `portLogList`로 잘못 명명되어 있다 (6절 비고 참조). URL 매핑은 `/res/shelfLogList`로 정상.

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/shelfLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터. `ResShelfVo` 폼 바인딩.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" "http://<host>/res/shelfLogList?fabSite=M14"
```

**Response — JSP Model** : 공통 (3.0). ViewName: `res/shelfLogList`.

**Error Codes** : 공통 (3.0)

---

#### 3.4.2 `GET/POST /res/ajax/getShelfLogList` — Shelf 이력 AJAX 조회

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getShelfLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (Shelf 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 |
| `shelfName` | String | × | (없음) | Shelf 이름. **`-`(minus) 포함 시** `-`로 split 하여 다중 AND 조건 생성 |
| `state` | String | × | (없음) | 상태 |
| `processingState` | String | × | (없음) | 처리 상태 |
| `banned` | String | × | (없음) | 금지 여부 |

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M14&fab1=M14A&page=1&rows=100" \
  -d "from=20240101000000&to=20240101010000" \
  -d "shelfName=SHELF-01-A&state=Occupied" \
  "http://<host>/res/ajax/getShelfLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "_time": "2024-01-01 00:30:11+0900",
      "time_ex": "20240101003011001",
      "machineName": "STK001",
      "machineType": "STOCKER",
      "shelfName": "SHELF-01",
      "state": "Occupied",
      "processingState": "Idle",
      "banned": "false"
    }
  ]
}
```

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page`,`total`,`records` | int | 페이징 메타 |
| `rows[].‌_time`, `time_ex` | String | 시각 |
| `rows[].machineName`, `machineType` | String | 머신 |
| `rows[].shelfName` | String | Shelf 이름 |
| `rows[].state` | String | 상태 |
| `rows[].processingState` | String | 처리 상태 |
| `rows[].banned` | String | 금지 여부 |

**Error Codes** : 공통 (3.0)

---

### 3.5 StorageFull 서브모듈

#### 3.5.1 `GET/POST /res/storageLogList` — StorageFull 이력 조회 화면 진입

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/storageLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터. `ResStorageFullVo` 폼 바인딩.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" "http://<host>/res/storageLogList?fabSite=M14"
```

**Response — JSP Model** : 공통 (3.0). ViewName: `res/storageLogList`.

**Error Codes** : 공통 (3.0)

---

#### 3.5.2 `GET/POST /res/ajax/getStorageLogList` — StorageFull 이력 AJAX 조회

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getStorageLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (StorageFull 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 |
| `state` | String | × | (없음) | 상태 |
| `fullState` | String | × | (없음) | Full 상태 (`Full`/`NotFull` 등) |
| `processingState` | String | × | (없음) | 처리 상태 |

> StorageFull VO에는 자원 고유 식별자 컬럼(`storageName` 등)이 **없다**. `machineName` 단위로만 조회된다.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M14&fab1=M14A&page=1&rows=100" \
  -d "from=20240101000000&to=20240101010000" \
  -d "fullState=Full&state=Active" \
  "http://<host>/res/ajax/getStorageLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "time_ex": "20240101004555001",
      "_time": "2024-01-01 00:45:55+0900",
      "machineName": "STK001",
      "machineType": "STOCKER",
      "state": "Active",
      "processingState": "Idle",
      "fullState": "Full"
    }
  ]
}
```

> 참고: `fields` 절의 순서가 `time_ex, _time, ...`이므로 다른 모듈과 키 순서가 다르다 (`ResStorageFullHistoryServiceImpl.getQueryParser` 250-253 라인).

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page`,`total`,`records` | int | 페이징 메타 |
| `rows[].time_ex` | String | 마이크로초 정밀 시각 (필드 순서가 다른 점 유의) |
| `rows[].‌_time` | String | 이벤트 시각 |
| `rows[].machineName`, `machineType` | String | 머신 |
| `rows[].state` | String | 상태 |
| `rows[].processingState` | String | 처리 상태 |
| `rows[].fullState` | String | Full 상태 |

**Error Codes** : 공통 (3.0)

---

### 3.6 Vehicle 서브모듈

#### 3.6.1 `GET/POST /res/vehicleLogList` — Vehicle 이력 조회 화면 진입

> 컨트롤러 메서드명이 `portLogList`로 명명되어 있으나 (6절 비고 참조), 실제로는 Vehicle 화면 진입.

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/vehicleLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements** : 공통 화면 진입 파라미터. `ResVehicleVo` 폼 바인딩.

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" "http://<host>/res/vehicleLogList?fabSite=M14"
```

**Response — JSP Model** : 공통 (3.0). ViewName: `res/vehicleLogList`.

**Error Codes** : 공통 (3.0)

---

#### 3.6.2 `GET/POST /res/ajax/getVehicleLogList` — Vehicle 이력 AJAX 조회

**Request — URL**

| 항목 | 값 |
|---|---|
| Method | GET / POST |
| URL | `/res/ajax/getVehicleLogList` |

**Request — Header** : 공통 (3.0)

**Request — Elements (Vehicle 고유 + 공통)**

| 파라미터 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| (공통 AJAX 파라미터) | — | — | — | 3.0 참조 |
| `vehicleName` | String | × | (없음) | 반송차 이름 |
| `state` | String | × | (없음) | 상태 |
| `subState` | String | × | (없음) | 서브 상태. **`_` 포함 시** `_`로 split 하여 다중 AND 조건 |
| `processingState` | String | × | (없음) | 처리 상태 |
| `transportCommandId` | String | × | (없음) | 운반명령 ID |
| `carrier` | String | × | (없음) | 캐리어 ID |
| `transportName` | String | × | (없음) | 운반/이송 포트명 (Logpresso 필드: `transferPortName`). **`_` 포함 시** `_`로 split, 아니면 **`-` 포함 시** `-`로 split 하여 다중 AND 조건 |
| `idReadState` | String | × | (없음) | ID 리드 상태 |

**curl 예시**

```bash
curl -b "JSESSIONID=ABC123" \
  -X POST \
  -d "fabSite=M14&fab1=M14A&page=1&rows=100" \
  -d "from=20240101000000&to=20240101010000" \
  -d "vehicleName=V001&state=Moving&transportName=P01_P02&carrier=CAR-0001" \
  "http://<host>/res/ajax/getVehicleLogList"
```

**Response — JSON**

```json
{
  "page": 1,
  "total": 1,
  "records": 100,
  "rows": [
    {
      "_time": "2024-01-01 00:55:21+0900",
      "time_ex": "20240101005521789",
      "messageName": "VehicleStateChange",
      "machineName": "OHT-CTRL-01",
      "machineType": "OHT",
      "vehicleName": "V001",
      "state": "Moving",
      "processingState": "Transport",
      "subState": "Loaded",
      "transportCommandId": "TC-0001",
      "carrier": "CAR-0001",
      "transferPortName": "P02",
      "idReadState": "OK"
    }
  ]
}
```

**Response Elements**

| 필드 | 타입 | 설명 |
|---|---|---|
| `page`,`total`,`records` | int | 페이징 메타 |
| `rows[].‌_time`, `time_ex` | String | 시각 |
| `rows[].messageName` | String | 메시지명 |
| `rows[].machineName`, `machineType` | String | 머신 |
| `rows[].vehicleName` | String | 반송차 이름 |
| `rows[].state` / `processingState` / `subState` | String | 상태들 |
| `rows[].transportCommandId` | String | 운반명령 ID |
| `rows[].carrier` | String | 캐리어 ID |
| `rows[].transferPortName` | String | 이송 포트명 |
| `rows[].idReadState` | String | ID 리드 상태 |

**Error Codes** : 공통 (3.0)

---

## 4. 자원 모델 (VO)

### 4.1 VO 비교 표

공통 필드 ✓ / 자원 고유 필드 ●

| 필드 | 타입 | Crane | Machine | Port | Shelf | StorageFull | Vehicle |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `fabSite` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `pageNum` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `rowNum` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `areaName` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `bayName` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `machineType` | List\<String\> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `machineName` | List\<String\> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `fab` | List\<String\> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `level` | List\<String\> | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `from` / `to` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `state` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `processingState` | String | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `subState` | String | ● | — | ● | — | — | ● |
| `craneName` | String | ● | — | — | — | — | — |
| `transportCommandId` | String | ● | — | — | — | — | ● |
| `connectionState` | String | — | ● | — | — | — | — |
| `controlState` | String | — | ● | — | — | — | — |
| `tscState` | String | — | ● | — | — | — | — |
| `portName` | String | — | — | ● | — | — | — |
| `banned` | String | — | — | ● | ● | — | — |
| `occupied` | String | — | — | ● | — | — | — |
| `transportUnitAccessible` | String | — | — | ● | — | — | — |
| `craneAvailable` | String | — | — | ● | — | — | — |
| `inOutType` | String | — | — | ● | — | — | — |
| `manual` | String | — | — | ● | — | — | — |
| `accessMode` | String | — | — | ● | — | — | — |
| `idReadState` | String | — | — | ● | — | — | ● |
| `shelfName` | String | — | — | — | ● | — | — |
| `fullState` | String | — | — | — | — | ● | — |
| `vehicleName` | String | — | — | — | — | — | ● |
| `carrier` | String | — | — | — | — | — | ● |
| `transportName` | String | — | — | — | — | — | ● |

### 4.2 ResCraneVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 (ALL or etc) |
| `bayName` | String | Bay명 (ALL or etc) |
| `machineType` | List\<String\> | ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | All / M14A / M14B / etc |
| `level` | List\<String\> | ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL |
| `craneName` | String | 크레인 이름 |
| `state` | String | 상태 |
| `subState` | String | 서브 상태 |
| `processingState` | String | 처리 상태 |
| `transportCommandId` | String | 운반명령 ID |
| `from` | String | 조회 시작 (`yyyyMMddHHmmss`) |
| `to` | String | 조회 종료 (`yyyyMMddHHmmss`) |

### 4.3 ResMachineVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 |
| `bayName` | String | Bay명 |
| `machineType` | List\<String\> | 머신 타입 (다중) |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | FAB (다중) |
| `level` | List\<String\> | Level (다중) |
| `state` | String | 머신 상태 |
| `connectionState` | String | 연결 상태 |
| `controlState` | String | 제어 상태 |
| `tscState` | String | TSC 상태 |
| `processingState` | String | 처리 상태 |
| `from` | String | 시작 시간 |
| `to` | String | 종료 시간 |

### 4.4 ResPortVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 |
| `bayName` | String | Bay명 |
| `machineType` | List\<String\> | 머신 타입 (다중) |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | FAB (다중) |
| `level` | List\<String\> | Level (다중) |
| `portName` | String | 포트명 (`_` 다중 split 지원) |
| `state` | String | 상태 |
| `subState` | String | 서브 상태 |
| `processingState` | String | 처리 상태 |
| `banned` | String | 금지 여부 |
| `occupied` | String | 점유 여부 (응답만, 쿼리 조건 미반영) |
| `transportUnitAccessible` | String | 운반유닛 접근가능 (응답만, 쿼리 조건 미반영) |
| `craneAvailable` | String | 크레인 가용 여부 |
| `inOutType` | String | 입출 타입 |
| `manual` | String | 수동 모드 |
| `accessMode` | String | 접근 모드 |
| `idReadState` | String | ID 리드 상태 |
| `from` | String | 시작 시간 |
| `to` | String | 종료 시간 |

### 4.5 ResShelfVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 |
| `bayName` | String | Bay명 |
| `machineType` | List\<String\> | 머신 타입 (다중) |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | FAB (다중) |
| `level` | List\<String\> | Level (다중) |
| `shelfName` | String | Shelf 이름 (`-` 다중 split 지원) |
| `state` | String | 상태 |
| `processingState` | String | 처리 상태 |
| `banned` | String | 금지 여부 |
| `from` | String | 시작 시간 |
| `to` | String | 종료 시간 |

### 4.6 ResStorageFullVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 |
| `bayName` | String | Bay명 |
| `machineType` | List\<String\> | 머신 타입 (다중) |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | FAB (다중) |
| `level` | List\<String\> | Level (다중) |
| `state` | String | 상태 |
| `fullState` | String | Full 상태 |
| `processingState` | String | 처리 상태 |
| `from` | String | 시작 시간 |
| `to` | String | 종료 시간 |

### 4.7 ResVehicleVo

| 필드 | 타입 | 설명 |
|---|---|---|
| `fabSite` | String | FAB Site |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지당 행 수 |
| `areaName` | String | 지역명 |
| `bayName` | String | Bay명 |
| `machineType` | List\<String\> | 머신 타입 (다중) |
| `machineName` | List\<String\> | 다중 머신명 |
| `fab` | List\<String\> | FAB (다중) |
| `level` | List\<String\> | Level (다중) |
| `vehicleName` | String | 반송차 이름 |
| `state` | String | 상태 |
| `subState` | String | 서브 상태 (`_` 다중 split 지원) |
| `processingState` | String | 처리 상태 |
| `transportCommandId` | String | 운반명령 ID |
| `carrier` | String | 캐리어 ID |
| `transportName` | String | 이송 포트명 (`_` 또는 `-` 다중 split 지원, Logpresso 필드: `transferPortName`) |
| `idReadState` | String | ID 리드 상태 |
| `from` | String | 시작 시간 |
| `to` | String | 종료 시간 |

---

## 5. 인증 및 권한

- 본 모듈은 **별도의 `@PreAuthorize`, Spring Security 인증 어노테이션, 또는 Role 기반 권한 검사 없이** 동작한다. URL 매핑은 모두 공개되어 있으며, 서버 사이드 인가 로직은 코드 내에 존재하지 않는다.
- 단, 컨트롤러는 `HttpServletRequest`를 통해 **세션**에서 FAB Site 정보를 읽고 쓴다 (`Common.getFabSite(request)` / `Common.setFabSite(request, sFabSite)`).
- 따라서 세션 자체의 인증/세션 관리는 외부(애플리케이션 공통 필터, Web 서버 SSO 등)에 의존하는 구조이며, 본 모듈 단독으로 인증/권한을 제공하지 않는다.
- 실무에서는 인트라넷 망 + SSO 로 보호된다고 가정하고 설계된 것으로 보인다.

---

## 6. 비고 / 이슈

### 6.1 `ResHistoryService` 인터페이스 — Liskov 치환 원칙(LSP) 위반

`ResHistoryService` 인터페이스는 **6개의 `getDataList(...)` 오버로드 메서드**(`ResCraneVo`, `ResStorageFullVo`, `ResMachineVo`, `ResPortVo`, `ResShelfVo`, `ResVehicleVo` 각각)를 단일 인터페이스에 모두 선언하고 있다. 그러나 각 `*ServiceImpl`은 **본인 타입에 해당하는 메서드 1개만 실제 구현**하고, 나머지 5개는 `// TODO Auto-generated method stub`과 `return null`로 비워둔다.

예시 (`ResCraneHistoryServiceImpl`):
- `getDataList(ResCraneVo)` → 정상 구현 (Logpresso 쿼리 실행)
- `getDataList(ResStorageFullVo)` / `ResMachineVo` / `ResPortVo` / `ResShelfVo` / `ResVehicleVo` → `return null`

**문제점**
- LSP 위반: 인터페이스 계약 상 모든 VO에 대해 동작해야 하지만, 구현체는 단 하나의 VO에만 동작한다.
- 코드 중복: 각 Impl마다 5개의 unused stub 메서드가 존재 (= 6 × 5 = 30개의 dead stub).
- 컴파일 시점에 호출 가능한 메서드인지 알 수 없어, 잘못된 Bean을 주입하면 **런타임에 조용히 `null` 반환** → 화면이 빈 결과를 보여주는 버그를 유발할 수 있다.

**권장 리팩토링**
- 인터페이스를 6개로 분리 (`ResCraneHistoryService`, `ResMachineHistoryService`, ...)
- 또는 제네릭 `ResHistoryService<T>` 한 개 + 공통 추상 클래스로 통합.

### 6.2 컨트롤러 메서드 이름 오용 (`portLogList`)

다수 컨트롤러에서 메서드 이름이 화면 의도와 일치하지 않는다.

| 컨트롤러 | URL | 메서드명 | 비고 |
|---|---|---|---|
| `ResCraneHistoryController` | `/res/craneLogList` | `carrierLocLogList` | 잘못된 historical 이름 |
| `ResMachineHistoryController` | `/res/machineLogList` | `carrierLocLogList` | 동일 |
| `ResShelfHistoryController` | `/res/shelfLogList` | `portLogList` | Port용으로 명명 |
| `ResStorageFullHistoryController` | `/res/storageLogList` | `carrierLocLogList` | 동일 |
| `ResVehicleHistoryController` | `/res/vehicleLogList` | `portLogList` | Port용으로 명명 |
| `ResPortHistoryController` | `/res/portLogList` | `portLogList` | 유일한 정합 |

URL 매핑이 정상이므로 동작에는 문제가 없으나, 유지보수성 측면에서 메서드 이름을 통일하거나 자원별로 명명하는 것이 좋다(예: `craneLogList`, `machineLogList`, `shelfLogList` 등).

### 6.3 ServiceImpl 중복 코드 — `getTableFromFab` 동일 구현 6회

6개 `*ServiceImpl` 모두 동일한 `getTableFromFab(String fabSite, String fab)` private 메서드를 보유한다. `Common` 클래스 또는 공통 `AbstractResHistoryServiceImpl`로 추출 가능하다.

### 6.4 `level` 필터 파라미터 미사용

컨트롤러는 `level1`,`level2`,...를 모아 `param.setLevel(levels)`를 호출하지만, `*ServiceImpl.getQueryParser()` 내부의 `LEVEL` 처리 블록은 **전부 주석 처리되어** 있다. 따라서 사용자가 Level 체크박스를 변경해도 실제 Logpresso 쿼리에는 반영되지 않는다.

### 6.5 `machineTypes` 파라미터 CSV vs 다중 파라미터 불일치

컨트롤러는 `machineTypes` 단일 파라미터를 받아 `,`로 split하지만, 주석 처리된 코드(`machineType1`,`machineType2`,...)와 비교 시 클라이언트(JSP) 측의 파라미터 명세와 컨트롤러 명세가 동기화되지 않을 가능성이 있다. JSP 측 폼 정의를 함께 확인 필요.

### 6.6 `ResPortVo`의 `occupied`, `transportUnitAccessible` — 쿼리 미사용

`ResPortVo`는 `occupied`, `transportUnitAccessible` 필드를 가지나 `ResPortHistoryServiceImpl.getQueryParser()`는 이 두 필드를 WHERE 조건에 추가하지 않는다. 응답 `fields` 절에는 포함되어 결과 표시에는 사용된다.

### 6.7 `Paging.nTotalCount` 정적 변수 의존

각 컨트롤러는 `paging.setNumberOfRecords(Paging.nTotalCount)`로 **`Paging`의 정적 변수**를 참조한다. 동시 요청 시 Race Condition 발생 가능성이 있으며, 멀티 사용자 환경에서는 부정확한 `total` 페이지 수가 표시될 수 있다.

### 6.8 `ResHistoryDAO` — Logpresso 기반, MyBatis 미사용

본 모듈은 Logpresso(`DBManager.executeQuery(queryStmt)`)로 **로그 쿼리 문자열**을 직접 실행한다. MyBatis Mapper XML은 본 모듈에서 사용되지 않는다. 쿼리는 모든 `ServiceImpl.getQueryParser()` 내에서 문자열 연결로 빌드된다.

### 6.9 `craneAvailable` getter 시그니처 누락 없음 / 일관성 확인

`ResPortVo`의 `craneAvailable`, `inOutType` 등은 컨트롤러 단에서 별도 파라미터 추출 로직이 없고, Spring `@ModelAttribute` 자동 바인딩에 의존한다. 따라서 클라이언트는 폼 필드명을 VO 프로퍼티명과 일치시켜 전송해야 한다.

---

## 부록: Logpresso 쿼리 빌드 헬퍼 상수 (`Common`)

`getQueryParser()`가 사용하는 주요 상수 (Common 클래스에 정의됨):

| 상수 | 예상 값 | 용도 |
|---|---|---|
| `Common.sFulltext_Arg0_key1` | `fulltext from=%s to=%s "%s"` 형식 | 시작 절 템플릿 |
| `Common.sMETHOD` | `method` | method 필드명 |
| `Common.sAnd` | ` and ` | AND 연산자 |
| `Common.sOr` | ` or ` | OR 연산자 |
| `Common.sEquals` | `=` | 등호 |
| `Common.sLeftParenthesis` / `sRightParenthesis` | `(` / `)` | 괄호 |
| `Common.sDoubleQuotation` | `"` | 큰따옴표 |
| `Common.sCRLF` | 줄바꿈 | 쿼리 줄바꿈 |
| `Common.sSearch_in` | `search in (%s, ...)` 형식 | search in 절 |
| `Common.sFrom` | ` from ` | 테이블 절 |
| `Common.sFields` | ` fields ` | 출력 컬럼 절 |
| `Common.sPipeLine` | ` \| ` | Logpresso 파이프 |
| `Common.sSort` | `sort ` | 정렬 절 |
| `Common.s_TIME` / `sTIME_EX` | `_time` / `time_ex` | 시각 컬럼명 |
| `Common.sALL` / `sNOTDESIGNATED` | `ALL` / 미지정 | 특수 값 |
| `Common.sFABSITE_M14` 등 | `M14` 등 | FAB Site 값 |
| `Common.sTS_RESOURCE_M14A` 등 | 테이블명 | Resource 테이블 |

---

(문서 끝)
