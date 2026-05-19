# 07. Tran (반송 이력) 영역

`com.skhynix.supply.tran` 패키지는 MCS의 반송(이송) 로그 조회 기능을 담당한다. "tran"은 transfer를 의미하며, 반송(이송) 단위에 따라 Job(상위 작업) / Cmd(하위 명령) 두 가지 변형이 있고, 각각에 대한 정상 이력과 실패 이력을 별도 화면으로 제공한다. 데이터 소스는 fab site/fab 별로 다른 splunk style 테이블(`TS_TRANSPORT_*`)을 가리키며 모든 서비스는 동일한 `TranService` 인터페이스를 다형성으로 구현해 `DataList` 조회 메서드를 노출한다.

본 문서는 `tran/` 하위 15개 파일과 부수적으로 `test/controller/TestController.java` 1개 파일까지 총 16개 파일을 다룬다.

---

## 엔드포인트 요약

| URL | HTTP | Controller | Method | View | 설명 |
|---|---|---|---|---|---|
| `tran/returnLogList` | GET/POST | `TranController` | `returnLogList` | `tran/returnLogList` | 반송 이력 조회 화면 |
| `tran/ajax/getReturnLogList` | GET/POST | `TranController` | `getReturnLogList` | `jsonView` | 반송 이력 그리드 데이터 |
| `tran/ajax/getTranJobHistoryDetail` | GET/POST | `TranController` | `getTranJobHistoryDetail` | `jsonView` | 반송 이력 상세(Job + Command 분리) |
| `tran/ajax/getReasonList` | GET/POST | `TranController` | `getReasonList` | `jsonView` | Reason 코드 룩업 리스트 |
| `tran/returnCmdFailLogList` | GET/POST | `TranCmdFailController` | `returnCmdFailLogList` | `tran/returnCmdFailLogList` | Command 실패 이력 화면 |
| `tran/ajax/getReturnCmdFailLogList` | GET/POST | `TranCmdFailController` | `getReturnCmdFailLogList` | `jsonView` | Command 실패 그리드 데이터 |
| `tran/pop/reasonPop` | GET/POST | `TranCmdFailController` | `machineNamePop` | `tran/pop/reasonPop` | Reason 선택 팝업 |
| `tran/returnCmdLogList` | GET/POST | `TranCmdHistoryController` | `returnCmdLogList` | `tran/returnCmdLogList` | 반송 CMD 이력 화면 |
| `tran/ajax/getReturnCmdLogList` | GET/POST | `TranCmdHistoryController` | `getReturnCmdLogList` | `jsonView` | 반송 CMD 이력 그리드 데이터 |
| `tran/returnJobFailLogList` | GET/POST | `TranJobFailController` | `tranJobFail` | `tran/returnJobFailLogList` | Job 실패 이력 화면 |
| `tran/ajax/getReturnJobFailLogList` | GET/POST | `TranJobFailController` | `getReturnJobFailLogList` | `jsonView` | Job 실패 그리드 데이터 |
| `tran/returnJobLogList` | GET/POST | `TranJobHistoryController` | `returnLogList` | `tran/returnJobLogList` | 반송 Job 이력 화면 |
| `tran/ajax/getReturnJobLogList` | GET/POST | `TranJobHistoryController` | `getReturnJobLogList` | `jsonView` | 반송 Job 이력 그리드 데이터 |
| `/i18n.do` | GET | `TestController` | `i18n` | `i18n` | 로케일/메시지 테스트 |
| `/monitoring.do` | GET | `TestController` | `monitoring` | `monitoring` | 모니터링 테스트 화면 |
| `/tmp.do` | GET | `TestController` | `tmp` | `tmp` | 임시(ThreadPool 실험) 화면 |

---

## tran 하위 영역 구성

반송 도메인은 동일한 원천 데이터 위에서 다음 4가지 시각으로 나뉘어 화면이 구성된다.

- **Tran (`TranController` / `TranServiceImpl`, bean `tranService`)**
  - "반송 이력" 통합 화면. method=`createTransportJobHistory` 조건으로 조회하며, 행을 클릭하면 동일 `TransportJobId`에 대한 Job + Command 상세 타임라인(`getTranJobHistoryDetail`)을 호출한다.
  - 상세 조회는 from/to 차이가 1시간을 초과하면 `sFulltext_From_TRAN` 프로시저, 1시간 이하면 `sTable_From_TRAN` 프로시저로 분기된다.
  - 부가적으로 `getReasonList`(memlookup `reasonList`)를 통해 사유 코드를 제공한다.

- **TranCmd (`TranCmdHistoryController` / `TranCmdHistoryServiceImpl`, bean `tranCmdHistoryService`)**
  - 반송 명령(Command) 단위 이력. method=`createTransportCommandHistory`. State / TransportCommandId / Transport·From·To Unit(언더바·하이픈 분해 후 AND) 등 Cmd 고유 필터가 추가된다.

- **TranJob (`TranJobHistoryController` / `TranJobHistoryServiceImpl`, bean `tranJobHistoryService`)**
  - 반송 작업(Job) 단위 이력. method=`createTransportJobHistory`. LotId 및 State 필터가 핵심.

- **Fail 계열**
  - `TranCmdFailController` + `TranCmdFailServiceImpl` (bean `tranCmdFailService`): method=`createTransportCommandFailHistory`. 입력 VO는 `TranCmdFailVo`(transportCmdId · reason 보유).
  - `TranJobFailController` + `TranJobFailServiceImpl` (bean `jobFailService`): method=`createTransportJobFailHistory`. 입력 VO는 `TranJobFailVo`(lotId · transportJobId · reason 보유).
  - 실패 화면들은 정상 이력과 달리 STATE / Unit 등을 사용하지 않고 Reason 기반 필터에 집중된다.

분리 의도는 (1) 동일한 transport 도메인이지만 splunk method 식별자가 다르고 각 화면이 요구하는 컬럼(`fields ...`)과 필터셋이 다르므로, 한 서비스에 모으면 메서드/쿼리가 비대해진다, (2) Cmd vs Job, 정상 vs 실패의 UI/엑셀 다운로드 컬럼 구성을 독립적으로 진화시키기 위한 것으로 보인다. 한편 모든 구현체가 `TranService`라는 단일 인터페이스(`getDataList(TranVo)`, `getDataList(TranCmdFailVo)`, `getDataList(TranJobFailVo)`, `getTranJobHistoryDetail`, `getReasonList`)를 구현해 컨트롤러에서 `@Resource(name="…")`로 빈만 바꿔 끼우면 되도록 설계되어 있다(자기 영역이 아닌 오버로드는 `// TODO Auto-generated method stub` 후 `return null`).

---

## Controller 상세

### tran/controller/TranController.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/controller/TranController.java`
- 목적: 반송(이송) 통합 이력 조회 컨트롤러. 메인 그리드 + JobHistory 상세 + Reason 룩업.
- 클래스 시그니처: `@Controller public class TranController`
- 주입: `@Resource(name="tranService") private TranService tranService;`

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `returnLogList` | `tran/returnLogList` | `@ModelAttribute TranVo param`, `HttpServletRequest` | `ModelAndView`(`tran/returnLogList`) | 화면 진입. `fabsites`/`fabs` 셀렉트 박스 데이터 세팅, fab site 세션 동기화(`Common.getFabSite` / `Common.setFabSite`), 기본 fab(`Common.getBasicFabList("tran", …)`)을 param에 주입. |
| `getReturnLogList` | `tran/ajax/getReturnLogList` | `@ModelAttribute TranVo param`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 그리드 ajax. `page`/`rows` 기본값 1/100, 시간 미지정 시 최근 10분 자동 세팅, fab/transport·from·to MachineType 멀티 파싱(콤마 split, ALL이면 clear), area/bay null이면 ALL, state 단일 추가, `Paging` 적용 후 `tranService.getDataList(param)` 호출. |
| `getTranJobHistoryDetail` | `tran/ajax/getTranJobHistoryDetail` | `@ModelAttribute TranVo param`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 상세 조회. 결과를 method=`Common.METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY` 여부로 `commandListRow` / `historyListRow` 두 리스트로 분리하여 view에 전달. |
| `getReasonList` | `tran/ajax/getReasonList` | `@ModelAttribute FabVo param`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | Reason 코드 리스트(메모리 룩업). fabSite는 `Common.setFabSite(request, fabSite)`로 결정. |

주석 처리된 `tran/ajax/returnLogDetailList` 메서드가 존재(하위 코드 대체로 사용 안 함).

### tran/controller/TranCmdFailController.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/controller/TranCmdFailController.java`
- 목적: 반송 Command 실패 이력 조회 + Reason 선택 팝업.
- 클래스 시그니처: `@Controller public class TranCmdFailController`
- 주입: `@Resource(name="tranCmdFailService") private TranService tranService;` (인터페이스 타입은 `TranService`지만 실제 빈은 `TranCmdFailServiceImpl`)

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `returnCmdFailLogList` | `tran/returnCmdFailLogList` | `@ModelAttribute TranCmdFailVo param`, `HttpServletRequest` | `ModelAndView`(`tran/returnCmdFailLogList`) | 화면 진입. fab site/fabs 세팅 후 view 이동. |
| `getReturnCmdFailLogList` | `tran/ajax/getReturnCmdFailLogList` | `@ModelAttribute TranCmdFailVo param`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 그리드 ajax. transport/from/to MachineType 멀티 파싱, area/bay null→ALL, `tranService.getDataList(TranCmdFailVo)` 호출. State는 사용하지 않는다(Fail 화면 특성). |
| `machineNamePop` | `tran/pop/reasonPop` | `@ModelAttribute TranCmdFailVo param`, `HttpServletRequest` | `ModelAndView`(`tran/pop/reasonPop`) | Reason 선택 팝업 진입. 메서드명은 보일러플레이트이며 실제 reason 팝업이다. |

### tran/controller/TranCmdHistoryController.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/controller/TranCmdHistoryController.java`
- 목적: 반송 Command 이력 조회 컨트롤러.
- 클래스 시그니처: `@Controller public class TranCmdHistoryController`
- 주입: `@Resource(name="tranCmdHistoryService") private TranService tranService;`

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `returnCmdLogList` | `tran/returnCmdLogList` | `@ModelAttribute TranVo`, `HttpServletRequest` | `ModelAndView`(`tran/returnCmdLogList`) | 화면 진입. fab site/fabs 세팅. |
| `getReturnCmdLogList` | `tran/ajax/getReturnCmdLogList` | `@ModelAttribute TranVo`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 그리드 ajax. state는 `states` 콤마 문자열을 split하여 ALL 처리(다중 선택 지원), 그 외 필터링 로직은 `TranController`와 유사. |

### tran/controller/TranJobFailController.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/controller/TranJobFailController.java`
- 목적: 반송 Job 실패 이력 조회 컨트롤러.
- 클래스 시그니처: `@Controller public class TranJobFailController`
- 주입: `@Resource(name="jobFailService") private TranService jobFailService;`

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `tranJobFail` | `tran/returnJobFailLogList` | `@ModelAttribute TranJobFailVo`, `HttpServletRequest` | `ModelAndView`(`tran/returnJobFailLogList`) | 화면 진입. |
| `getReturnJobFailLogList` | `tran/ajax/getReturnJobFailLogList` | `@ModelAttribute TranJobFailVo`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 그리드 ajax. Fail 화면이라 state 처리 없음. `jobFailService.getDataList(TranJobFailVo)` 호출. |

### tran/controller/TranJobHistoryController.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/controller/TranJobHistoryController.java`
- 목적: 반송 Job 이력 조회 컨트롤러.
- 클래스 시그니처: `@Controller public class TranJobHistoryController`
- 주입: `@Resource(name="tranJobHistoryService") private TranService tranService;`

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `returnLogList` | `tran/returnJobLogList` | `@ModelAttribute TranVo`, `HttpServletRequest` | `ModelAndView`(`tran/returnJobLogList`) | 화면 진입. |
| `getReturnJobLogList` | `tran/ajax/getReturnJobLogList` | `@ModelAttribute TranVo`, `HttpServletRequest` | `ModelAndView`(`jsonView`) | 그리드 ajax. JobHistory용 컬럼 구성으로 service 위임. state 다중 처리는 컨트롤러에서 직접 split하지 않고 service에서 처리한다. |

---

## Service 상세

### tran/service/TranService.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/TranService.java`
- 목적: 반송 영역 5개 화면이 공유하는 단일 서비스 인터페이스. 각 구현체가 자기 책임 메서드만 실제 구현하고 나머지는 `null` 반환.
- 시그니처: `public interface TranService`

선언된 메서드:

| 메서드 | 설명 |
|---|---|
| `List<Map> getDataList(TranCmdFailVo cmdFailVo)` | CmdFail 그리드 데이터 |
| `List<Map> getDataList(TranVo tranVo)` | Tran/TranCmd/TranJob 그리드 데이터(오버로드) |
| `List<Map> getTranJobHistoryDetail(TranVo tranVo)` | 반송 이력 상세(Job+Command) |
| `List<Map> getDataList(TranJobFailVo jobfailVo)` | JobFail 그리드 데이터 |
| `List<Map> getReasonList(String fabSite)` | fab site별 Reason 룩업 |

### tran/service/impl/TranServiceImpl.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/impl/TranServiceImpl.java`
- 빈 이름: `@Service("tranService")`
- 주입: `@Resource(name="tranDAO") TranDAO Client;`
- 목적: 반송 통합 이력 조회 + JobHistory 상세 + Reason 룩업의 핵심 구현체.

주요 메서드:

| 메서드 | 설명 |
|---|---|
| `getDataList(TranVo)` | `getTranQueryParser`로 splunk 쿼리 생성 후 `\| limit offset rows` + `\| sort _time` 부착, `Client.dbExecuteQuery(fabSite, query)` 실행. |
| `getTranQueryParser(TranVo)` | method=`createTransportJobHistory` 베이스. carrier/transportJobId/lotId 단일 필터, transport·source·dest area/bay 단일 필터, transport·from·to MachineType은 `Common.sSearch_in`(`search in (col, "a", "b")` 패턴), MachineName은 OR 체인, state ALL이 아니면 `STATE="COMPLETED" OR STATE="CANCELED"`, fab list는 `getTableFromFab(fabSite, fab)`로 테이블명 콤마 조인 후 `from` 절 구성, 최종 `fields` 절로 출력 컬럼 고정. |
| `getTranJobHistoryDetail(TranVo)` | `getTranJobHistoryDetailQueryParser` → from/to 차이 > 1시간이면 `sFulltext_From_TRAN` 프로시저, 이하면 `sTable_From_TRAN` 프로시저(`sProc + ...`)로 분기. |
| `getReasonList(String fabSite)` | `memlookup name=reasonList \| fields REASON \| sort REASON` 실행. |
| `getTableFromFab(fabSite, fab)` private | fabSite(M14/M15/M11/C2/IC)와 fab 조합으로 `Common.sTS_TRANSPORT_*` 테이블 상수를 매핑. |
| `getDataList(TranCmdFailVo/TranJobFailVo)` | 인터페이스 충족용 stub, `return null`. |

### tran/service/impl/TranCmdFailServiceImpl.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/impl/TranCmdFailServiceImpl.java`
- 빈 이름: `@Service("tranCmdFailService")`
- 주입: `@Resource(name="tranDAO") TranDAO Client;`, `@Resource(name="totalService") private TotalService totService;` (선언만 되어 있고 본문에서는 사용되지 않음)
- 목적: Cmd 실패 그리드 데이터 제공.

주요 메서드:

| 메서드 | 설명 |
|---|---|
| `getDataList(TranCmdFailVo)` | 페이징 offset/limit 계산 후 `getCmdFailQueryParser` 결과에 `\| limit … \| sort _time` 부착하여 실행. |
| `getCmdFailQueryParser(TranCmdFailVo)` | method=`createTransportCommandFailHistory` 베이스. carrier/transportCmdId 단일 필터, reason 리스트는 1건이면 단일 `=`, N건이면 OR 그룹, area/bay/MachineType/MachineName 처리는 `TranServiceImpl`과 동일 패턴, 마지막에 fab 테이블 조인 후 `fields CARRIER, TRANSPORTJOBID, TRANSPORTCOMMANDID, …, REASON, PRIORITY, DESCRIPTION, TIME, SOURCEUNITNAME` 출력. |
| `getTableFromFab` private | TranServiceImpl과 동일한 매핑(중복 정의). |
| 기타 인터페이스 메서드 | stub `null`. |

### tran/service/impl/TranCmdHistoryServiceImpl.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/impl/TranCmdHistoryServiceImpl.java`
- 빈 이름: `@Service("tranCmdHistoryService")`
- 주입: `@Resource(name="tranDAO") TranDAO Client;`
- 목적: 반송 Command 이력 그리드 데이터 제공.

주요 메서드:

| 메서드 | 설명 |
|---|---|
| `getDataList(TranVo)` | `getTranCmdHistoryQueryParser` 결과에 limit/sort 부착 후 실행. |
| `getTranCmdHistoryQueryParser(TranVo)` | method=`createTransportCommandHistory` 베이스. carrier/transportCommandId 단일 필터, state 다중 OR(첫 항목 ALL이면 미적용), transportUnit/fromUnit/toUnit은 `_`(언더바) 또는 `-`(하이픈)로 split해 AND 결합한 nested group 생성, area/bay/MachineType/MachineName 처리, fab 테이블 조인, `fields TRANSPORTCOMMANDID, TRANSPORTJOBID, STATE, CARRIER, …, TRANSPORTMACHINENAME, TRANSPORTTYPE2, TRANSPORTUNITNAME` 출력. |
| `getTableFromFab` private | 동일 매핑. |
| 기타 인터페이스 메서드 | stub `null`. |

### tran/service/impl/TranJobFailServiceImpl.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/impl/TranJobFailServiceImpl.java`
- 빈 이름: `@Service("jobFailService")`
- 주입: `@Resource(name="tranDAO") TranDAO Client;`
- 목적: Job 실패 그리드 데이터 제공.

주요 메서드:

| 메서드 | 설명 |
|---|---|
| `getDataList(TranJobFailVo)` | offset/limit 계산 → `getQueryParser` → limit/sort 부착 후 실행. |
| `getQueryParser(TranJobFailVo)` private | method=`createTransportJobFailHistory` 베이스. carrier/lotId/transportJobId 단일 필터, reason 리스트(1건 단일, N건 OR 그룹), area/bay/MachineType/MachineName 처리, fab 테이블 조인, `fields TIME, TRANSPORTJOBID, CARRIER, PRIORITY, DESCRIPTION, REASON, SOURCE*, DEST*, SOURCEUNITNAME` 출력. |
| `getTableFromFab` private | 동일 매핑. |
| 기타 인터페이스 메서드 | stub `null`. |

### tran/service/impl/TranJobHistoryServiceImpl.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/service/impl/TranJobHistoryServiceImpl.java`
- 빈 이름: `@Service("tranJobHistoryService")`
- 주입: `@Resource(name="tranDAO") TranDAO Client;`
- 목적: 반송 Job 이력 그리드 데이터 제공.

주요 메서드:

| 메서드 | 설명 |
|---|---|
| `getDataList(TranVo)` | `getTranJobHistoryQueryParser` 결과에 limit/sort 부착 후 실행. |
| `getTranJobHistoryQueryParser(TranVo)` | method=`createTransportJobHistory` 베이스. carrier/transportJobId/lotId 단일 필터, state 다중 OR 그룹(첫 항목 ALL이면 미적용), area/bay/MachineType/MachineName 처리, fab 테이블 조인, `fields TIME, TRANSPORTJOBID, STATE, FIXEDROUTE, LOTID, BATCHID, STEPID, PROCESSID, CARRIER, PRIORITY, DESCRIPTION, REASON, SOURCE*, DEST*, SOURCEUNITNAME, CREATEUSER, BATCHTYPE` 출력. |
| `getTableFromFab` private | 동일 매핑. |
| 기타 인터페이스 메서드 | stub `null`. |

---

## DAO

### tran/dao/TranDAO.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/dao/TranDAO.java`
- 시그니처: `@Repository("tranDAO") public class TranDAO`
- 의존: 필드 `DBManager dbManager`(`com.skhynix.supply.common.DBManager`)
- 본 영역은 전통적 mybatis mapper를 사용하지 않고 fab site별 DBManager 인스턴스에 splunk-style 쿼리 문자열을 그대로 전달한다(SQL mapper ID 개념 없음).

| 메서드 | 설명 |
|---|---|
| `TranDAO()` | 기본 생성자. |
| `List<Map> dbExecuteQuery(String fabSite, String queryStmt)` | `new DBManager(fabSite)` 생성 후 `executeQuery(queryStmt)` 실행. 예외 시 warn 로그, finally에서 `dbManager = null`. 주석 처리된 ThreadPool/Callable 기반 구현이 함께 존재(현재는 비활성). |
| `void dbExecuteQueryStop()` | 진행 중인 쿼리 중단(`dbManager.executeQueryStop()`). |

---

## VO

### tran/vo/TranVo.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/vo/TranVo.java`
- 용도: Tran / TranCmdHistory / TranJobHistory 컨트롤러·서비스의 입력 파라미터.

| 필드 | 타입 | 역할 |
|---|---|---|
| `fabSite` | String | fab site 코드(M14/M15/M11/C2/IC), 세션과 동기화 |
| `pageNum` | String | 페이지 번호 |
| `rowNum` | String | 페이지 당 행수 |
| `fab` | List<String> | 조회 대상 fab 리스트(M14A/M15A/...) |
| `fromAreaName` | String | source area, ALL or 단일 |
| `fromBayName` | String | source bay, ALL or 단일 |
| `fromUnit` | String | source unit(`_`/`-` split 가능) |
| `toAreaName` | String | dest area |
| `toBayName` | String | dest bay |
| `toUnit` | String | dest unit |
| `transportAreaName` | String | transport area |
| `transportBayName` | String | transport bay |
| `transportUnit` | String | transport unit |
| `fromMachineType` | List<String> | source machine type 멀티(ALL/STOCKER/STB/LIFTER/CONVEYOR/PROCESS/OHT) |
| `toMachineType` | List<String> | dest machine type 멀티 |
| `transportMachineType` | List<String> | transport machine type 멀티 |
| `fromMachineName` | List<String> | source machine 이름 멀티 |
| `toMachineName` | List<String> | dest machine 이름 멀티 |
| `transportMachineName` | List<String> | transport machine 이름 멀티 |
| `from` | String | 조회 시작 시각(yyyyMMddHHmmss) |
| `to` | String | 조회 종료 시각 |
| `carrier` | String | 캐리어 ID |
| `lotId` | String | LOT ID |
| `transportJobId` | String | 반송 Job ID |
| `transportCommandId` | String | 반송 Command ID |
| `state` | List<String> | 상태 멀티 |

### tran/vo/TranCmdFailVo.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/vo/TranCmdFailVo.java`
- 용도: Command 실패 이력 조회 입력.

`TranVo`와 동일한 fabSite/pageNum/rowNum/fab/Area/Bay/Unit/MachineType/MachineName/from/to/carrier 필드를 가지며, Command 실패 고유 필드는 다음과 같다.

| 필드 | 타입 | 역할 |
|---|---|---|
| `transportCmdId` | String | 반송 Command ID(실패 단위) |
| `reason` | List<String> | 실패 사유 멀티 |

(lotId/transportJobId/transportCommandId/state는 없음.)

### tran/vo/TranJobFailVo.java

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/tran/vo/TranJobFailVo.java`
- 용도: Job 실패 이력 조회 입력.

`TranVo`와 동일한 공통 필드 + Job 실패 고유 필드:

| 필드 | 타입 | 역할 |
|---|---|---|
| `carrier` | String | 캐리어 ID |
| `lotId` | String | LOT ID |
| `transportJobId` | String | 반송 Job ID(실패 단위) |
| `reason` | List<String> | 실패 사유 멀티 |

(state/transportCommandId 등 정상 이력 전용 필드는 없음.)

---

## test/controller/TestController.java (부록)

- 파일 경로: `/home/user/ASAS/mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/test/controller/TestController.java`
- 목적: i18n / 모니터링 / ThreadPool 임시 실험용. 운영 비즈니스 로직과는 무관하며 개발자 실습/검증을 위한 컨트롤러.
- 클래스 시그니처: `@Controller public class TestController`
- 주입:
  - `@Autowired SessionLocaleResolver localeResolver`
  - `@Autowired MessageSource messageSource`
  - `private static final org.slf4j.Logger logger = LoggerFactory.getLogger(TotalController.class);` (slf4j logger, 이름은 `TotalController`로 잘못 지정되어 있음)

| Method | @RequestMapping | Parameters | Return | 설명 |
|---|---|---|---|---|
| `i18n` | `/i18n.do` (GET) | `Locale locale`, `HttpServletRequest`, `Model` | `String "i18n"` | RequestMappingHandler가 넘긴 Locale과 `SessionLocaleResolver`로 풀어낸 Locale을 로깅하고 `MessageSource`로 다국어 메시지(`site.title` 등)를 출력. 모델에 `siteCount`, `siteLang` 적재 후 `i18n` jsp로 이동. |
| `monitoring` | `/monitoring.do` (GET) | 동일 | `String "monitoring"` | 단순히 monitoring view로 이동(로깅만 수행). |
| `tmp` | `/tmp.do` (GET) | 동일 | `String "tmp"` | ThreadPool에 20회 Callable을 submit하여 세션 ID / 스레드명을 로깅하는 코드가 주석 처리되어 있음. 현재는 단순 view 이동만. |

---

## 데이터 흐름

1. **사용자 → 화면 진입**: 사용자가 좌측 메뉴에서 반송/CMD/Job/Fail 화면을 클릭하면 각 컨트롤러의 화면 진입 메서드(`tran/return*LogList`)가 호출된다. 컨트롤러는 `Common.FabSites` / `Common.getFabList("tran", fabSite)`로 fab site 셀렉트 박스 데이터를 준비하고, 세션의 fabSite와 param.fabSite를 `Common.getFabSite` / `Common.setFabSite`로 동기화한 뒤 jsp 뷰를 반환한다.

2. **그리드 ajax 요청**: jsp의 jqGrid 등이 `tran/ajax/getReturn*LogList`로 ajax 호출을 보낸다. 컨트롤러는 `page`/`rows` 기본값(1/100), `from`/`to` 기본값(최근 10분), `fab*` / `*MachineType*` / `state` 등 멀티 셀렉트 파라미터를 콤마 분해해 VO에 채우고, area/bay null을 `Common.sALL`로 치환한 뒤 `Paging` 객체를 만들어 적절한 `TranService` 빈에 위임한다.

3. **서비스 → 쿼리 생성**: 각 ServiceImpl은 화면별 `get*QueryParser`로 splunk style 쿼리 문자열(`sFulltext_Arg0_key1` 포맷)을 조립한다. 공통 패턴은 (a) `from`/`to` 시간 범위 + method 식별자, (b) ID 계열 단일 필터(`=`), (c) reason/state 등 다중값 OR 그룹, (d) MachineType은 `Common.sSearch_in` (`search in (col, ...)`), MachineName은 OR 체인, (e) `getTableFromFab(fabSite, fab)`로 fab별 `TS_TRANSPORT_*` 테이블을 콤마 조인해 `from` 절을 만들고, (f) 마지막에 `fields` 절로 출력 컬럼을 고정.

4. **쿼리에 limit/sort 부착**: 서비스가 `\| limit offset rows`, `\| sort _time`을 덧붙여 최종 쿼리를 만든다.

5. **DAO 실행**: `TranDAO.dbExecuteQuery(fabSite, query)`가 fab site별 `DBManager` 인스턴스를 생성해 splunk(또는 동등 백엔드)에 질의하고 `List<Map>` 결과를 반환한다. fab site별 DB 분리는 멀티 fab 환경(M14/M15/M11/C2/IC) 지원의 핵심이다.

6. **응답**: 컨트롤러는 `Paging.nTotalCount`(쿼리 부수 효과로 채워지는 정적 카운트)를 받아 jqGrid 형식(`page`, `total`, `records`, `rows`)으로 모델에 담아 `jsonView`로 직렬화한다. 상세 보기는 `tran/ajax/getTranJobHistoryDetail`이 결과를 method 값(`createTransportCommandHistory` vs `createTransportJobHistory`)으로 분리해 `commandListRow` / `historyListRow` 두 리스트로 반환하여 화면에서 Job 타임라인 + Command 타임라인을 동시에 표시한다.
