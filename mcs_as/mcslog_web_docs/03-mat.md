# 03. Material (Carrier 위치 이력 조회) 모듈

본 문서는 `com.skhynix.supply.mat` 패키지 산하의 모든 클래스(Controller, Service 인터페이스/구현, DAO, VO)를 다룬다.
Material 모듈은 Fab 내에서 Carrier(반송 단위)의 위치 이력(Location History)을 조회하기 위한 화면 및 데이터 API를 제공한다.

## 엔드포인트 요약

| URL | HTTP Method | Controller Method | View | 설명 |
|---|---|---|---|---|
| `mat/carrierLocLogList` | ANY (GET/POST) | `MaterialController#carrierLocLogList` | `mat/carrierLocLogList` (JSP) | Carrier 위치 이력 조회 화면(초기 진입). Fab/Level 등 검색 조건 초기화. |
| `/mat/ajax/getCarrierLocLogList.do` | ANY (GET/POST) | `MaterialController#getList` | `jsonView` | 조회 조건을 받아 Carrier 위치 이력 데이터를 JSON으로 반환(jqGrid 페이징 응답). |

---

## 1. MaterialController

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/mat/controller/MaterialController.java`
- 목적(Purpose): Carrier 위치 이력 조회 화면 진입 및 AJAX 데이터 조회를 처리하는 Spring MVC Controller. 사용자가 선택한 Fab Site / Fab / Level / MachineType / 검색 조건을 정규화하여 `MaterialService`에 위임한다.

### 클래스 시그니처 및 어노테이션

```java
@Controller
public class MaterialController
```

- `@Controller` : Spring MVC Controller 빈으로 등록.

### 주입 의존성(Injected Dependencies)

| 필드 | 타입 | 주입 방식 | 용도 |
|---|---|---|---|
| `materialService` | `MaterialService` | `@Resource(name = "materialService")` | Carrier 위치 이력 데이터 조회 서비스 호출 |
| `totService` | `TotalService` | `@Resource(name = "totalService")` | (현재 코드 상에서는 주입만 되어있고 호출 없음 — 과거 bay/machine name 리스트 조회용. 주석 처리됨) |
| `log` | `org.apache.commons.logging.Log` | `LogFactory` | 로깅 |

### Public 메서드

#### 1) `carrierLocLogList`

- 시그니처: `public ModelAndView carrierLocLogList(@ModelAttribute MaterialVo param, HttpServletRequest request) throws Exception`
- Request Mapping: `@RequestMapping(value = "mat/carrierLocLogList")`
- 파라미터:
  - `@ModelAttribute MaterialVo param` : 화면 필터(폼) 파라미터 바인딩. Fab Site 등은 사용자가 선택한 값이 있을 수 있음.
  - `HttpServletRequest request` : 세션 기반 FabSite 처리에 사용.
- 반환: `ModelAndView` (view: `mat/carrierLocLogList`)
- 동작 설명(Korean):
  1. `Common.FabSites`를 모델에 담아 화면 Fab Site Select 박스를 구성.
  2. 사용자가 넘긴 `fabSite`가 비어있으면 세션(`Common.getFabSite`)에서 가져오고, 값이 있으면 세션에 반영(`Common.setFabSite`).
  3. 해당 fab site에 대한 `mat` 모듈 Fab 목록을 조회하여 `fabs`로 노출하고, 기본 Fab 목록을 `param.fab`에 세팅.
  4. 로그 Level Select 목록(`Common.Levels`)을 모델에 추가하고, 기본 선택 Level(`WELL/WARN/ERROR/FATAL`)을 `param.level`에 세팅.
  5. 최종적으로 `param`을 `param`, `params` 두 이름으로 모델에 추가하여 JSP 렌더링.

#### 2) `getList`

- 시그니처: `public ModelAndView getList(@ModelAttribute MaterialVo param, HttpServletRequest request) throws Exception`
- Request Mapping: `@RequestMapping(value = "/mat/ajax/getCarrierLocLogList.do")`
- 추가 어노테이션: `@SuppressWarnings("rawtypes")`
- 파라미터:
  - `@ModelAttribute MaterialVo param` : 검색 조건(carrier, lotId, commandId, unit, areaName, bayName, from, to, fabSite 등) 바인딩.
  - `HttpServletRequest request` : `page`, `rows`, `fabN`, `levelN`, `machineTypes` 등 동적 파라미터 읽기 및 세션 처리.
- 반환: `ModelAndView` (view: `jsonView`) — jqGrid 표준 응답(`page`, `total`, `records`, `rows`).
- 동작 설명(Korean):
  1. 현재 시각 기준 `yyyyMMddHHmmss`로 `strCurTime`, 그리고 10분 전 `strBeforeTenMinTime`을 계산하여 `from/to` 기본값으로 사용.
  2. jqGrid의 `page`(기본 1), `rows`(기본 100) 파라미터를 받아 페이징 정보 구성.
  3. `fabSite` 세션 처리(파라미터 우선, 없으면 세션값 사용).
  4. `fabN`(`fab1, fab2, ...`) 파라미터를 순회하여 다중 Fab 선택을 List로 수집. `fab1=ALL`이면 전체 Fab 목록을 적용.
  5. `levelN` 파라미터를 순회하여 다중 Level 선택을 List로 수집.
  6. `machineTypes` 파라미터(콤마 구분 문자열)를 split하여 List로 수집. 첫 토큰이 `ALL`이면 비우기(전체 의미).
  7. `areaName`, `bayName` 미지정 시 `ALL`로 보정.
  8. `pageNum`, `rowNum` 세팅 후 `MaterialService.getDataList(param)` 호출하여 결과 List 획득.
  9. `Paging` 객체로 jqGrid 페이지 메타정보(`page`, `total`, `records`) 계산 후 결과(`rows`)와 함께 `jsonView`로 반환.

---

## 2. MaterialService (Interface)

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/mat/service/MaterialService.java`
- 목적(Purpose): Carrier 위치 이력 조회 서비스의 계약(Interface). Controller가 구현체에 의존하지 않도록 추상화.

### 인터페이스 시그니처

```java
public interface MaterialService
```

- Spring 어노테이션 없음(인터페이스). 구현체에서 `@Service`로 등록됨.

### Public 메서드

#### 1) `getDataList`

- 시그니처: `public List<Map> getDataList(MaterialVo matVo) throws Exception`
- 추가 어노테이션: `@SuppressWarnings("rawtypes")`
- 파라미터: `MaterialVo matVo` — 검색 조건 일체(Fab, MachineType, 시간범위, Carrier, LotId 등).
- 반환: `List<Map>` — 로그 행 단위의 Map 컬렉션.
- 동작 설명(Korean): MaterialVo에 담긴 조건을 기반으로 Carrier 위치 이력 로그 데이터를 조회하여 반환.

---

## 3. MeterialServiceImpl (구현체, 클래스명에 오타 "Meterial")

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/mat/service/impl/MeterialServiceImpl.java`
- 목적(Purpose): `MaterialService` 구현체. 사용자 입력 조건을 사내 풀텍스트(로그 검색) 쿼리 문자열로 변환(`getQueryParser`)한 뒤, `MaterialDAO`를 통해 실제 DB(또는 로그 검색엔진)에 질의하여 결과를 반환.

### 클래스 시그니처 및 어노테이션

```java
@Service("materialService")
public class MeterialServiceImpl implements MaterialService
```

- `@Service("materialService")` : 빈 이름 `materialService`로 등록. 클래스 파일명/타입명은 오타("Meterial")이지만 빈 이름은 정상(`materialService`)이므로 Controller의 `@Resource(name="materialService")` 주입과 정합.

### 주입 의존성

| 필드 | 타입 | 주입 방식 | 용도 |
|---|---|---|---|
| `Client` | `MaterialDAO` | `@Resource(name = "materialDAO")` | 풀텍스트/DB 질의 실행 |
| `log` | `Log` | `LogFactory` | 로깅 |

### Public 메서드

#### 1) `getDataList` (override)

- 시그니처: `public List<Map> getDataList(MaterialVo matVo) throws Exception`
- 추가 어노테이션: `@SuppressWarnings("rawtypes")`, `@Override`
- 파라미터: `MaterialVo matVo`
- 반환: `List<Map>`
- 동작 설명(Korean):
  1. `pageNum`과 `rowNum`으로 `offset`, `limit` 계산.
  2. `getQueryParser(matVo)`로 풀텍스트 쿼리 문자열 생성.
  3. 결과 쿼리 뒤에 `| limit <offset> <limit>` 및 `| sort _time` 절(Common 상수 사용)을 덧붙임.
  4. `Client.dbExecuteQuery(matVo.getFabSite(), resultQuery)`로 Fab Site별 DB 접속/조회 위임.
  5. 결과 List 반환.

#### 2) `getQueryParser` (public이지만 내부적으로만 호출됨)

- 시그니처: `public String getQueryParser(MaterialVo matVo)`
- 파라미터: `MaterialVo matVo`
- 반환: `String` — 완성된 풀텍스트 검색 쿼리.
- 동작 설명(Korean):
  1. `matVo == null`이면 null 반환.
  2. `Common.sFulltext_Arg0_key1` 포맷을 사용해 시간범위(`from`~`to`)와 메서드 키(`method="createCarrierLocationHistory"`)로 1차 검색식 구성.
  3. 선택적 조건 AND 결합:
     - `carrier` → `(CARRIER="...")`
     - `lotId` → `(LOTID="...")`
     - `commandId` → `(TRANSPORTCOMMANDID="...")`
     - `unit` → 언더바(`_`) 또는 하이픈(`-`) 포함 시 토큰별 `CURRENTUNITNAME` 조건을 OR/AND로 묶음, 단일이면 단일 등식.
     - `areaName` (값이 ALL이 아니면) → `(AREANAME="...")`
     - `bayName` (값이 ALL이 아니면) → `(BAYNAME="...")`
     - `machineType` 리스트 → `search in MACHINETYPE, "x", "y" ...` 형태의 sub 쿼리 구성(ALL 포함 시 비움).
     - `machineName` 리스트 → `(CURRENTMACHINENAME="..." OR ...)`.
  4. `fab` 리스트를 순회하여 `getTableFromFab(fabSite, fab)`로 실제 테이블명을 콤마 결합 후 `from <tables>`로 추가.
  5. `subMachineTypeQuery`를 본 쿼리에 합치고, 출력 필드(`_time, TIME_EX, CARRIER, LOTID, TRANSPORTCOMMANDID, CURRENTMACHINENAME, MACHINETYPE, CURRENTUNITNAME`)를 `fields` 절로 지정.

#### 3) `getTableFromFab` (private 헬퍼)

- 시그니처: `private String getTableFromFab(String fabSite, String fab)`
- 동작 설명(Korean): Fab Site와 Fab 식별자에 따라 실제 조회 대상 테이블 상수를 매핑.
  - `M14` → `TS_MATERIAL_M14A`
  - `M15` → `M15A/M15B`에 따라 `TS_MATERIAL_M15A/B`
  - `M11` → `M11A/M11B`에 따라 `TS_MATERIAL_M11A/B`
  - `C2` → `C2/C2F`에 따라 `TS_MATERIAL_C2/C2F`
  - `IC` → `M14A/M16A/M16B`에 따라 `TS_MATERIAL_M14A/M16A/M16B`
  - 외 default → null
  - 주의: 각 case에 `break`가 없으나 모두 `return` 분기여서 fall-through 시점에 매칭 없으면 다음 case로 흘러갈 수 있음(잠재적 이슈, 아래 이슈 섹션 참조).

---

## 4. MaterialDAO

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/mat/dao/MaterialDAO.java`
- 목적(Purpose): 풀텍스트/DB 질의 실행을 담당. `DBManager`를 통해 Fab Site별 접속을 생성하여 쿼리를 실행하고 결과 List를 반환.

### 클래스 시그니처 및 어노테이션

```java
@Repository("materialDAO")
public class MaterialDAO
```

- `@Repository("materialDAO")` : DAO 빈 이름 `materialDAO`로 등록.

### 주입 의존성

- 명시적 DI 없음. 내부적으로 `new DBManager(fabSite)`를 직접 생성하여 사용.
- `log` : `LogFactory.getLog(MaterialDAO.class)`

### SQL 매퍼 ID / 쿼리 정보

- 본 DAO는 **MyBatis 매퍼 ID를 사용하지 않는다.** 대신 `DBManager#executeQuery(String queryStmt)`에 풀텍스트 형식의 쿼리 문자열(서비스 레이어에서 동적으로 조립된 것)을 직접 전달하여 실행한다.
- 쿼리 목적: Fab Site별 Material(Carrier 위치 이력) 로그 테이블(`TS_MATERIAL_*`)에 대해 시간범위/조건 기반 조회(`method="createCarrierLocationHistory"`).

### Public 메서드

#### 1) `MaterialDAO()` — 기본 생성자

- 시그니처: `public MaterialDAO()`
- 동작 설명: 빈 생성자. Spring 컨테이너에서 인스턴스화 시 사용.

#### 2) `dbExecuteQuery`

- 시그니처: `public List<Map> dbExecuteQuery(String fabSite, String queryStmt) throws Exception`
- 추가 어노테이션: `@SuppressWarnings("rawtypes")`
- 파라미터:
  - `fabSite` : Fab Site 식별자(접속 대상 결정).
  - `queryStmt` : 실행할 풀텍스트 쿼리 문자열.
- 반환: `List<Map>` — 결과 행 리스트.
- 동작 설명(Korean):
  1. `new DBManager(fabSite)`로 Fab Site용 DBManager 생성.
  2. `dbManager.executeQuery(queryStmt)` 호출하여 결과 획득.
  3. 예외 발생 시 warn 로그 출력 후 null 가능 결과 반환.
  4. `finally`에서 `dbManager` 참조를 null로 정리.
  5. (주석 처리된 ThreadPool/Callable 기반 비동기 실행 코드가 남아있음 — 현재는 동기 호출 사용.)

#### 3) `dbExecuteQueryStop`

- 시그니처: `public void dbExecuteQueryStop() throws Exception`
- 파라미터: 없음.
- 반환: void.
- 동작 설명(Korean): 진행 중인 쿼리를 중단(`dbManager.executeQueryStop`). 멤버 `dbManager`가 null이 아니면 stop 호출 후 정리.

---

## 5. MaterialVo

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/mat/vo/MaterialVo.java`
- 목적(Purpose): Carrier 위치 이력 조회 화면의 검색 조건과 페이징 정보를 담는 단순 DTO/Form Bean.
- 클래스 시그니처: `public class MaterialVo` (Spring 어노테이션 없음, POJO).

### 필드 표

| 필드명 | 타입 | 역할 |
|---|---|---|
| `fabSite` | `String` | Fab Site 식별자(M14, M15, M11, C2, IC 등). 2022.6.15 추가. |
| `pageNum` | `String` | 현재 페이지 번호(jqGrid `page`). |
| `rowNum` | `String` | 한 페이지에 출력할 행 수(jqGrid `rows`). |
| `areaName` | `String` | 검색 조건: Area 이름(ALL 등). |
| `bayName` | `String` | 검색 조건: Bay 이름(ALL 등). |
| `machineType` | `List<String>` | Machine Type 다중 선택(ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT 등). |
| `machineName` | `List<String>` | Machine Name 다중 선택. |
| `fab` | `List<String>` | 조회 대상 Fab 다중 선택(ALL/M14A/M14B 등). |
| `level` | `List<String>` | 로그 Level 다중 선택(ALL/DEBUG/INFO/FINE/WELL/WARN/ERROR/FATAL). |
| `carrier` | `String` | 검색 조건: Carrier ID. |
| `lotId` | `String` | 검색 조건: Lot ID. |
| `commandId` | `String` | 검색 조건: Transport Command ID. |
| `unit` | `String` | 검색 조건: Current Unit Name(언더바/하이픈 구분으로 다중 표현 가능). |
| `from` | `String` | 검색 시작 시각(`yyyyMMddHHmmss`). |
| `to` | `String` | 검색 종료 시각(`yyyyMMddHHmmss`). |

- 위 모든 필드는 표준 Getter/Setter를 가진다.

---

## 데이터 흐름

```
[Browser/JSP: mat/carrierLocLogList.jsp]
        │  (1) GET mat/carrierLocLogList
        ▼
MaterialController#carrierLocLogList
        │  - Common.FabSites, Common.Levels, Common.getFabList(...) 로 화면 옵션 구성
        │  - 세션 기반 fabSite 결정 후 모델에 param/params 세팅
        ▼
View: mat/carrierLocLogList.jsp (조회 화면 렌더)

        │  (2) AJAX POST/GET /mat/ajax/getCarrierLocLogList.do
        ▼
MaterialController#getList
        │  - page/rows, fabN, levelN, machineTypes, areaName, bayName, from, to 정규화
        │  - param(MaterialVo) 구성
        ▼
MaterialService(=MeterialServiceImpl)#getDataList
        │  - getQueryParser(matVo)로 풀텍스트 쿼리 동적 조립
        │     · 시간범위 + method="createCarrierLocationHistory" 기본
        │     · carrier/lotId/commandId/unit/areaName/bayName AND 결합
        │     · machineType / machineName / fab 리스트 처리
        │     · getTableFromFab(fabSite, fab)으로 TS_MATERIAL_* 테이블명 결정
        │  - "| limit offset rows | sort _time" 부가
        ▼
MaterialDAO#dbExecuteQuery(fabSite, queryStmt)
        │  - new DBManager(fabSite)
        │  - dbManager.executeQuery(queryStmt) (MyBatis 매퍼 ID 미사용, 동적 쿼리 직접 전달)
        ▼
DBManager → Fab Site별 데이터소스(로그 저장소/풀텍스트 엔진)
        │
        ▼
List<Map> 결과 → Service → Controller (Paging으로 메타 계산)
        │
        ▼
View: jsonView (jqGrid 응답 JSON: page/total/records/rows)
```

요약:
1. Controller(`MaterialController`)는 화면 진입과 AJAX 데이터 요청을 분리하여 처리하며, 모든 다중선택 파라미터(`fabN`, `levelN`, `machineTypes`)와 세션 기반 `fabSite`를 정규화한다.
2. Service(`MeterialServiceImpl`)는 VO를 풀텍스트 쿼리로 변환하고, Fab → 실제 테이블명 매핑을 수행한다.
3. DAO(`MaterialDAO`)는 MyBatis 매퍼 ID가 아닌, 서비스에서 조립한 풀텍스트 쿼리 문자열을 `DBManager`에 직접 전달하여 실행한다.
4. 결과는 jqGrid 표준 포맷(JSON)으로 클라이언트에 반환된다.

---

## 부록: 발견된 이슈 / 주의 사항

- 클래스명 오타: `MeterialServiceImpl` (정상 표기는 `MaterialServiceImpl`). 단, Spring 빈 이름은 `@Service("materialService")`로 정확히 지정되어 있어 주입 자체에는 문제가 없음.
- `MeterialServiceImpl#getTableFromFab`의 `switch`문에는 `break`가 누락되어 있다. 각 case 내부에서 모두 `return`을 하므로 일치하는 분기에서는 문제 없으나, 예컨대 `case sFABSITE_M15`에서 `fab`이 `M15A/M15B` 어디에도 해당하지 않으면 `return` 없이 다음 `case sFABSITE_M11`로 fall-through하여 잘못된 테이블을 반환할 가능성이 있다(잠재적 버그).
- `TotalService totService`는 Controller에 주입되어 있지만 현재 메서드 본문에서 호출되지 않는다(과거 bay/machine name 조회 로직이 주석 처리됨).
- `MaterialController#getList`에는 사용되지 않는 옛 변수 초기화 블록과 다수의 주석 코드가 남아있다.
- DAO는 MyBatis 매퍼 ID를 사용하지 않으며, 동적 쿼리 문자열을 `DBManager.executeQuery`로 직접 실행한다. SQL 인젝션 관점에서는 사용자 입력이 `"..."` 리터럴 안에 그대로 삽입되므로, 입력 검증/이스케이프 정책에 의존한다.
- DAO에서 `dbManager`를 인스턴스 필드로 두는 동시에 메서드 내에서 매번 새로 할당하므로, 동시 호출 환경(다중 사용자)에서 `dbExecuteQueryStop`이 다른 쿼리를 중단시킬 수 있는 동시성 위험이 있다(현재 코드는 빈 객체를 prototype 단위로 쓰지 않으므로 잠재적 이슈).
