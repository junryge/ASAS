# 04. Resource History 모듈 (`com.skhynix.supply.res`)

본 문서는 `mcslog_web_src/src/main/java/com/skhynix/supply/res/` 하위 20개 파일(컨트롤러 6, 서비스 인터페이스 1, 서비스 구현 6, DAO 1, VO 6)의 구조와 동작을 정리한다. 본 모듈은 Crane, Machine, Port, Shelf, StorageFull, Vehicle 등 MCS 리소스의 이력 로그를 InfluxDB 계열 fulltext 쿼리로 조회하여 화면(jqGrid)에 제공한다.

---

## 엔드포인트 요약

6개의 컨트롤러는 모두 동일한 패턴(화면 매핑 1개 + Ajax 매핑 1개)을 따른다.

| 컨트롤러 | 화면 URL | View 이름 | Ajax URL | 사용 VO | 서비스 빈명 |
|---|---|---|---|---|---|
| `ResCraneHistoryController` | `res/craneLogList` | `res/craneLogList` | `res/ajax/getCraneLogList` | `ResCraneVo` | `resCraneHistoryServiceImpl` |
| `ResMachineHistoryController` | `res/machineLogList` | `res/machineLogList` | `res/ajax/getMachineLogList` | `ResMachineVo` | `resMachineHistoryServiceImpl` |
| `ResPortHistoryController` | `res/portLogList` | `res/portLogList` | `res/ajax/getPortLogList` | `ResPortVo` | `resPortHistoryServiceImpl` |
| `ResShelfHistoryController` | `res/shelfLogList` | `res/shelfLogList` | `res/ajax/getShelfLogList` | `ResShelfVo` | `resShelfHistoryServiceImpl` |
| `ResStorageFullHistoryController` | `res/storageLogList` | `res/storageLogList` | `res/ajax/getStorageLogList` | `ResStorageFullVo` | `resStorageFullHistoryServiceImpl` |
| `ResVehicleHistoryController` | `res/vehicleLogList` | `res/vehicleLogList` | `res/ajax/getVehicleLogList` | `ResVehicleVo` | `resVehicleHistoryServiceImpl` |

모든 Ajax 응답은 `jsonView`로 직렬화되며 jqGrid 응답 구조(`page`, `total`, `records`, `rows`)를 갖는다.

---

## 1. Controller 계층

여섯 컨트롤러는 거의 동일한 구조를 가지며, 차이점은 사용 VO 타입과 등록된 서비스 빈명/View 명/URL 뿐이다. 공통 동작:

- `@Controller` 등록 (`@RequestMapping` 클래스 레벨 없음)
- `@Resource(name="<리소스별 ServiceImpl>")`로 `ResHistoryService` 주입
- `@Resource(name="totalService")`로 `TotalService` 주입 (현재 코드에서는 사용처가 모두 주석 처리됨)
- 화면 핸들러: fab site/fab list/level 기본값을 모델에 적재 후 해당 JSP로 forward
- Ajax 핸들러: 페이지/행수/fab/level/machineType/areaName/bayName/from/to 파라미터 정규화 후 `service.getDataList(param)` 호출, `Paging`으로 페이지 메타 부착

### 1.1 `controller/ResCraneHistoryController.java`

- 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/res/controller/ResCraneHistoryController.java`
- 목적: Crane 리소스 이력 화면/조회 컨트롤러
- 클래스 시그니처: `@Controller public class ResCraneHistoryController`
- 의존성:
  - `ResHistoryService resHistoryService` (`@Resource(name="resCraneHistoryServiceImpl")`)
  - `TotalService totService` (`@Resource(name="totalService")`)
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `carrierLocLogList(ResCraneVo param, HttpServletRequest request)` | `res/craneLogList` (`@RequestMapping`) | `@ModelAttribute ResCraneVo param`, `HttpServletRequest` | `ModelAndView` | Crane 이력 화면 진입. fabSite 세션 처리(`Common.getFabSite`/`setFabSite`), `Common.getFabList("res", fabSite)`로 fab 목록 모델 적재, level 기본값(WELL/WARN/ERROR/FATAL) 부여, view `res/craneLogList` 반환 |
| `getCraneLogList(ResCraneVo param, HttpServletRequest request)` | `res/ajax/getCraneLogList` | `@ModelAttribute ResCraneVo param`, `HttpServletRequest` | `ModelAndView` | jqGrid Ajax 핸들러. `page`/`rows` 기본값(1, 100), 현재 시각 기준 10분 전 ~ 현재로 from/to 기본값, fab/level/machineType/area/bay 정규화 후 `resHistoryService.getDataList(param)` 호출, `Paging`으로 페이지 메타 셋업, `jsonView` 반환 |

### 1.2 `controller/ResMachineHistoryController.java`

- 경로: `.../res/controller/ResMachineHistoryController.java`
- 목적: Machine 리소스 이력 화면/조회
- 클래스 시그니처: `@Controller public class ResMachineHistoryController`
- 의존성: `resMachineHistoryServiceImpl`, `totalService`
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `carrierLocLogList(ResMachineVo, HttpServletRequest)` | `res/machineLogList` | `@ModelAttribute ResMachineVo`, `HttpServletRequest` | `ModelAndView` | Machine 이력 화면 진입. Crane 컨트롤러와 동일 패턴, view `res/machineLogList` |
| `getMachineLogList(ResMachineVo, HttpServletRequest)` | `res/ajax/getMachineLogList` | 동일 | `ModelAndView` | jqGrid Ajax 핸들러. 동일한 정규화 흐름으로 Machine 이력 조회 |

### 1.3 `controller/ResPortHistoryController.java`

- 경로: `.../res/controller/ResPortHistoryController.java`
- 목적: Port 리소스 이력 화면/조회
- 클래스 시그니처: `@Controller public class ResPortHistoryController`
- 의존성: `resPortHistoryServiceImpl`, `totalService`
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `portLogList(ResPortVo, HttpServletRequest)` | `res/portLogList` | `@ModelAttribute ResPortVo` | `ModelAndView` | Port 이력 화면 진입, view `res/portLogList` |
| `getPortLogList(ResPortVo, HttpServletRequest)` | `res/ajax/getPortLogList` | 동일 | `ModelAndView` | Port 이력 Ajax 조회 |

### 1.4 `controller/ResShelfHistoryController.java`

- 경로: `.../res/controller/ResShelfHistoryController.java`
- 목적: Shelf 리소스 이력 화면/조회
- 클래스 시그니처: `@Controller public class ResShelfHistoryController`
- 의존성: `resShelfHistoryServiceImpl`, `totalService`
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `portLogList(ResShelfVo, HttpServletRequest)` | `res/shelfLogList` | `@ModelAttribute ResShelfVo` | `ModelAndView` | Shelf 이력 화면 진입, view `res/shelfLogList` (메서드명은 Port에서 복사 흔적) |
| `getShelfLogList(ResShelfVo, HttpServletRequest)` | `res/ajax/getShelfLogList` | 동일 | `ModelAndView` | Shelf 이력 Ajax 조회 |

### 1.5 `controller/ResStorageFullHistoryController.java`

- 경로: `.../res/controller/ResStorageFullHistoryController.java`
- 목적: StorageFull(스토커 만재) 리소스 이력 화면/조회
- 클래스 시그니처: `@Controller public class ResStorageFullHistoryController`
- 의존성: `resStorageFullHistoryServiceImpl`, `totalService`
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `carrierLocLogList(ResStorageFullVo, HttpServletRequest)` | `res/storageLogList` | `@ModelAttribute ResStorageFullVo` | `ModelAndView` | StorageFull 이력 화면 진입, view `res/storageLogList` |
| `getStorageLogList(ResStorageFullVo, HttpServletRequest)` | `res/ajax/getStorageLogList` | 동일 | `ModelAndView` | StorageFull 이력 Ajax 조회 |

### 1.6 `controller/ResVehicleHistoryController.java`

- 경로: `.../res/controller/ResVehicleHistoryController.java`
- 목적: Vehicle(OHT 등) 리소스 이력 화면/조회
- 클래스 시그니처: `@Controller public class ResVehicleHistoryController`
- 의존성: `resVehicleHistoryServiceImpl`, `totalService`
- public 메서드:

| 메서드 | URL | 파라미터 | 반환 | 설명 |
|---|---|---|---|---|
| `portLogList(ResVehicleVo, HttpServletRequest)` | `res/vehicleLogList` | `@ModelAttribute ResVehicleVo` | `ModelAndView` | Vehicle 이력 화면 진입, view `res/vehicleLogList` |
| `getVehicleLogList(ResVehicleVo, HttpServletRequest)` | `res/ajax/getVehicleLogList` | 동일 | `ModelAndView` | Vehicle 이력 Ajax 조회 |

---

## 2. Service 계층

### 2.1 `service/ResHistoryService.java` (인터페이스)

- 경로: `.../res/service/ResHistoryService.java`
- 목적: 6개 리소스 이력 조회 메서드를 오버로드로 묶은 공통 서비스 계약
- 시그니처: `public interface ResHistoryService`
- 메서드(모두 `List<Map> getDataList(...) throws Exception`):
  - `getDataList(ResCraneVo)`
  - `getDataList(ResStorageFullVo)`
  - `getDataList(ResMachineVo)`
  - `getDataList(ResPortVo)`
  - `getDataList(ResShelfVo)`
  - `getDataList(ResVehicleVo)`

각 구현체는 자신이 담당하는 한 메서드만 실제 구현하고, 나머지 5개는 `return null` 스텁이다. 이는 동일 인터페이스 타입으로 컨트롤러가 주입받되, Spring 빈명으로 리소스를 구분하기 위한 패턴이다.

### 2.2 `service/impl/ResCraneHistoryServiceImpl.java`

- 경로: `.../service/impl/ResCraneHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resCraneHistoryServiceImpl") public class ResCraneHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client` (`@Resource(name="resHistoryDAO")`)
- 핵심 메서드:
  - `getDataList(ResCraneVo)` — 페이지 offset/limit 계산 → `getQueryParser(vo)` → `| limit offset n | sort _time` 부착 → `Client.dbExecuteQuery(fabSite, query)` 호출
  - 나머지 오버로드는 스텁
  - `getQueryParser(ResCraneVo)` — `method="createCraneHistory"` 필터를 기본으로, `craneName`/`state`/`subState`/`processingState`/`transportCommandId`/`areaName`/`bayName` 단일조건, `machineType`(search in), `machineName`(OR 목록), `fab`별 테이블 결합을 거쳐 fulltext 쿼리 구성 후 `_time, time_ex, machineName, machineType, craneName, state, processingState, transportCommandId, idReadState, subState` 필드를 SELECT
  - `getTableFromFab(fabSite, fab)` — fabSite/fab 조합에 따라 `Common.sTS_RESOURCE_*` 상수(M14A/M15A/M15B/M11A/M11B/C2/C2F/M16A/M16B)로 매핑

### 2.3 `service/impl/ResMachineHistoryServiceImpl.java`

- 경로: `.../service/impl/ResMachineHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resMachineHistoryServiceImpl") public class ResMachineHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client`
- 핵심: `getDataList(ResMachineVo)`만 구현. `getQueryParser(ResMachineVo)`는 `method="createMachineHistory"` 기본 필터 + `state/connectionState/controlState/tscState/processingState` 단일조건 + 공통 area/bay/machineType/machineName/fab 처리. SELECT 필드는 `_time, time_ex, machineName, machineType, state, controlState, connectionState, tscState, processingState`
- `getTableFromFab(...)`은 Crane과 동일 매핑 로직

### 2.4 `service/impl/ResPortHistoryServiceImpl.java`

- 경로: `.../service/impl/ResPortHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resPortHistoryServiceImpl") public class ResPortHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client`
- 핵심: `getDataList(ResPortVo)`만 구현. `getQueryParser(ResPortVo)`는 `method="createPortHistory"` + `portName`(언더바 split시 AND 그룹화 처리) + `state/subState/processingState/banned/craneAvailable/inOutType/manual/accessMode/idReadState` 단일조건 + 공통 area/bay/machineType/machineName/fab 처리. SELECT 필드는 `_time, time_ex, machineName, machineType, portName, state, processingState, subState, inOutType, manual, occupied, banned, transportUnitAccessible, idReadState, accessMode`

### 2.5 `service/impl/ResShelfHistoryServiceImpl.java`

- 경로: `.../service/impl/ResShelfHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resShelfHistoryServiceImpl") public class ResShelfHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client`
- 핵심: `getDataList(ResShelfVo)`만 구현. `getQueryParser(ResShelfVo)`는 `method="createShelfHistory"` + `shelfName`(마이너스 split시 AND 그룹화) + `state/processingState/banned` 단일조건 + 공통 area/bay/machineType/machineName/fab 처리. SELECT 필드는 `_time, time_ex, machineName, machineType, shelfName, state, processingState, banned`

### 2.6 `service/impl/ResStorageFullHistoryServiceImpl.java`

- 경로: `.../service/impl/ResStorageFullHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resStorageFullHistoryServiceImpl") public class ResStorageFullHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client`
- 핵심: `getDataList(ResStorageFullVo)`만 구현. `getQueryParser(ResStorageFullVo)`는 `method="createStorageFullHistory"` + `state/fullState/processingState` 단일조건 + 공통 area/bay/machineType/machineName/fab 처리. SELECT 필드는 `time_ex, _time, machineName, machineType, state, processingState, fullState`

### 2.7 `service/impl/ResVehicleHistoryServiceImpl.java`

- 경로: `.../service/impl/ResVehicleHistoryServiceImpl.java`
- 클래스 시그니처: `@Service("resVehicleHistoryServiceImpl") public class ResVehicleHistoryServiceImpl implements ResHistoryService`
- 의존성: `ResHistoryDAO Client`
- 핵심: `getDataList(ResVehicleVo)`만 구현. `getQueryParser(ResVehicleVo)`는 `method="createVehicleHistory"` + `vehicleName/state/processingState/transportCommandId/carrier/idReadState` 단일조건 + `subState`(언더바 split AND 그룹화) + `transportName`(언더바 우선, 없으면 마이너스 split AND 그룹화)로 `transferPortName` 컬럼 매핑 + 공통 area/bay/machineType/machineName/fab 처리. SELECT 필드는 `_time, time_ex, messageName, machineName, machineType, vehicleName, state, processingState, subState, transportCommandId, carrier, transferPortName, idReadState`

> 6개의 ServiceImpl 모두 `getTableFromFab(fabSite, fab)` private 메서드를 동일하게 보유한다. switch 분기는 `sFABSITE_M14 / M15 / M11 / C2 / IC` 5종이며 각 fab(M14A, M15A/B, M11A/B, C2/C2F, M16A/B)을 대응 InfluxDB measurement(`Common.sTS_RESOURCE_*`)에 매핑한다.

---

## 3. DAO 계층

### 3.1 `dao/ResHistoryDAO.java`

- 경로: `.../res/dao/ResHistoryDAO.java`
- 클래스 시그니처: `@Repository("resHistoryDAO") public class ResHistoryDAO`
- 의존성: 없음 (메서드 내부에서 `new DBManager(fabSite)` 인스턴스 생성)
- 본 DAO는 MyBatis 매퍼를 사용하지 않는다. **SQL 매퍼 ID는 존재하지 않으며**, `DBManager.executeQuery(queryStmt)`를 통해 fulltext 쿼리 문자열을 직접 실행한다 (InfluxDB 계열 시계열 질의로 추정). 따라서 "매퍼 ID 목록" 항목은 해당 없음.
- public 메서드:

| 메서드 | 시그니처 | 반환 | 설명 |
|---|---|---|---|
| `ResHistoryDAO()` | 기본 생성자 | - | 빈 초기화용 |
| `dbExecuteQuery(String fabSite, String queryStmt)` | `throws Exception` | `List<Map>` | `new DBManager(fabSite)`로 fab site별 커넥션 매니저 생성 후 `executeQuery(queryStmt)`로 쿼리 실행. 예외 시 warn 로그, finally에서 `dbManager = null` 처리(코멘트상 ThreadPool 적용 흔적 존재) |
| `dbExecuteQueryStop()` | `throws Exception` | `void` | 진행 중 쿼리 중단 — `dbManager.executeQueryStop()` 호출, finally에서 참조 해제 |

---

## 4. VO 계층

### 4.1 공통 베이스 필드

6개 VO 모두 다음 필드를 공통으로 가진다.

| 필드 | 타입 | 역할 |
|---|---|---|
| `fabSite` | `String` | FAB site 식별자 (M14/M15/M11/C2/IC) — 2022.06.15 추가 |
| `pageNum` | `String` | 페이지 번호 |
| `rowNum` | `String` | 한 페이지에 보여줄 행수 |
| `areaName` | `String` | Area 이름 (ALL 또는 특정) |
| `bayName` | `String` | Bay 이름 (ALL 또는 특정) |
| `machineType` | `List<String>` | ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT |
| `machineName` | `List<String>` | 머신 이름 목록 |
| `fab` | `List<String>` | All/M14A/M14B/M15A/... 선택값 |
| `level` | `List<String>` | ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL |
| `from` | `String` | 조회 시작 시각 (`yyyyMMddHHmmss`) |
| `to` | `String` | 조회 종료 시각 (`yyyyMMddHHmmss`) |

### 4.2 `vo/ResCraneVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `craneName` | `String` | Crane 식별자 |
| `state` | `String` | 상태 |
| `subState` | `String` | 서브 상태 |
| `processingState` | `String` | 처리 상태 |
| `transportCommandId` | `String` | 운반 명령 ID |

### 4.3 `vo/ResMachineVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `state` | `String` | Machine 상태 |
| `connectionState` | `String` | 연결 상태 |
| `controlState` | `String` | 제어 상태 |
| `tscState` | `String` | TSC 상태 |
| `processingState` | `String` | 처리 상태 |

### 4.4 `vo/ResPortVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `portName` | `String` | Port 식별자 |
| `state` | `String` | 상태 |
| `subState` | `String` | 서브 상태 |
| `processingState` | `String` | 처리 상태 |
| `banned` | `String` | 사용 금지 여부 |
| `occupied` | `String` | 점유 여부 |
| `transportUnitAccessible` | `String` | 운송 유닛 접근 가능 여부 |
| `craneAvailable` | `String` | 크레인 사용 가능 여부 |
| `inOutType` | `String` | In/Out 타입 |
| `manual` | `String` | 수동 모드 여부 |
| `accessMode` | `String` | 접근 모드 |
| `idReadState` | `String` | ID 리딩 상태 |

### 4.5 `vo/ResShelfVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `shelfName` | `String` | Shelf 식별자 |
| `state` | `String` | 상태 |
| `processingState` | `String` | 처리 상태 |
| `banned` | `String` | 사용 금지 여부 |

### 4.6 `vo/ResStorageFullVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `state` | `String` | 상태 |
| `fullState` | `String` | 만재 상태 |
| `processingState` | `String` | 처리 상태 |

### 4.7 `vo/ResVehicleVo.java` — 고유 필드

| 필드 | 타입 | 역할 |
|---|---|---|
| `vehicleName` | `String` | Vehicle 식별자 |
| `state` | `String` | 상태 |
| `subState` | `String` | 서브 상태 |
| `processingState` | `String` | 처리 상태 |
| `transportCommandId` | `String` | 운반 명령 ID |
| `carrier` | `String` | 캐리어 ID |
| `transportName` | `String` | TransferPort 이름 (쿼리 시 `transferPortName` 컬럼으로 매핑) |
| `idReadState` | `String` | ID 리딩 상태 |

---

## VO 비교

다음 표는 6개 VO 간 공통 필드(O) 및 리소스 고유 필드 분포를 보여준다.

| 필드 | Crane | Machine | Port | Shelf | StorageFull | Vehicle |
|---|---|---|---|---|---|---|
| `fabSite` | O | O | O | O | O | O |
| `pageNum` | O | O | O | O | O | O |
| `rowNum` | O | O | O | O | O | O |
| `areaName` | O | O | O | O | O | O |
| `bayName` | O | O | O | O | O | O |
| `machineType` (List) | O | O | O | O | O | O |
| `machineName` (List) | O | O | O | O | O | O |
| `fab` (List) | O | O | O | O | O | O |
| `level` (List) | O | O | O | O | O | O |
| `from` | O | O | O | O | O | O |
| `to` | O | O | O | O | O | O |
| `state` | O | O | O | O | O | O |
| `processingState` | O | O | O | O | O | O |
| `subState` | O | - | O | - | - | O |
| `banned` | - | - | O | O | - | - |
| `idReadState` | - | - | O | - | - | O |
| `transportCommandId` | O | - | - | - | - | O |
| `craneName` | O | - | - | - | - | - |
| `connectionState` | - | O | - | - | - | - |
| `controlState` | - | O | - | - | - | - |
| `tscState` | - | O | - | - | - | - |
| `portName` | - | - | O | - | - | - |
| `occupied` | - | - | O | - | - | - |
| `transportUnitAccessible` | - | - | O | - | - | - |
| `craneAvailable` | - | - | O | - | - | - |
| `inOutType` | - | - | O | - | - | - |
| `manual` | - | - | O | - | - | - |
| `accessMode` | - | - | O | - | - | - |
| `shelfName` | - | - | - | O | - | - |
| `fullState` | - | - | - | - | O | - |
| `vehicleName` | - | - | - | - | - | O |
| `carrier` | - | - | - | - | - | O |
| `transportName` | - | - | - | - | - | O |

요약: 페이지·머신·FAB·시간·level 필드는 11종이 100% 공통. `state`와 `processingState` 또한 6 VO 모두 보유. `subState`는 Crane/Port/Vehicle 3종에 존재. 나머지 필드는 리소스 특성에 따른 고유 속성.

---

## 데이터 흐름

6개 리소스(Crane, Machine, Port, Shelf, StorageFull, Vehicle)는 동일한 파이프라인을 병렬적으로 가진다:

1. **화면 진입(View 핸들러)** — 사용자가 `res/<resource>LogList` 진입 시, 컨트롤러는 세션 또는 파라미터에서 `fabSite`를 결정하고 `Common.getFabList("res", fabSite)`로 FAB 후보, `Common.Levels`로 레벨 후보를 모델에 채운 뒤 기본 level(WELL/WARN/ERROR/FATAL)을 VO에 세팅, 해당 JSP를 forward.

2. **Ajax 조회 핸들러** — jqGrid가 `res/ajax/get<Resource>LogList`를 호출하면, 컨트롤러가:
   - `page`/`rows` 기본값(1, 100) 보정
   - `from`/`to` 기본값을 "현재 시각 -10분 ~ 현재 시각"(`yyyyMMddHHmmss`)으로 보정
   - `fab1..N`, `level1..N`, `machineTypes`(콤마 구분), `areaName`, `bayName` 파라미터를 VO 컬렉션/문자열로 정규화 (ALL 처리 포함)
   - 해당 ServiceImpl의 `getDataList(vo)` 호출

3. **서비스 계층 (리소스별 ServiceImpl)** — 각 ServiceImpl은 자신이 담당하는 VO 타입의 메서드 한 개만 실제 구현하며 다음을 수행:
   - `offset = (page-1) * rows`, `limit = rows` 계산
   - `getQueryParser(vo)`로 fulltext 쿼리 본문 생성: `from..to` 시간범위 + `method="create<Resource>History"` 기본 필터 + 리소스별 단일조건(`state`, `processingState`, `<name>` 등) + 공통 `areaName/bayName` 단일조건 + `machineType` (search in `(...)`) + `machineName` (OR 목록) + `fab` 목록을 InfluxDB measurement 이름으로 매핑하여 FROM 절 구성
   - 결과 쿼리 뒤에 `| limit offset n` 과 `| sort _time` 부착
   - `Client.dbExecuteQuery(fabSite, query)` 호출

4. **DAO/DBManager** — `ResHistoryDAO.dbExecuteQuery(fabSite, query)`는 fab site별 `DBManager` 인스턴스를 생성하여 InfluxDB 계열 fulltext 질의를 실행하고 `List<Map>`을 반환한다. MyBatis 매퍼 없이 동적으로 만든 쿼리 문자열을 직접 실행하는 구조다.

5. **응답** — 컨트롤러는 결과 리스트를 `Paging` 유틸과 함께 `rows`, `page`, `total`, `records` 형태로 묶어 `jsonView`로 직렬화하여 jqGrid에 반환.

병렬성 요지: 6개 리소스가 **동일한 인터페이스(`ResHistoryService`)와 단일 DAO(`ResHistoryDAO`)** 를 공유하면서, 각 리소스별 ServiceImpl이 (1) 서로 다른 `method` 필터, (2) 서로 다른 SELECT 필드 집합, (3) 자신만의 단일조건 컬럼만을 보유한다. 컨트롤러/VO/Service 한 묶음이 리소스 종류만큼 복제되어 있는 평행 구조이며, 변경 시 6개 파일을 동기화해야 하는 부담이 있다.
