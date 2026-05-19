# 08. JSP 뷰 화면 문서

본 문서는 MCSLOG Web 애플리케이션의 모든 JSP/JSPF 뷰 파일 38개를 디렉터리별로 정리한 문서입니다. Spring MVC + Apache Tiles 기반의 단일 페이지 스타일(GNB 메뉴 클릭 → AJAX 로 partial JSP 로드 → 탭 컨테이너에 삽입) 로 동작합니다.

## 화면 맵

| URL (Controller endpoint) | JSP 파일 | 설명 |
|---|---|---|
| `/` (root) | `webapp/index.jsp` | `/tot/main` 로 리다이렉트 |
| `/tot/main` | `tot/main.jsp` | 메인 컨테이너 (탭/콘텐츠 영역) |
| `/i18n.do` | `i18n.jsp` | 다국어(메시지) 테스트 페이지 |
| `/monitoring` | `monitoring.jsp` | JVM 메모리 모니터링 페이지 |
| `/alarm/alarmReportLogList.do` | `alarm/alarmReportLogList.jsp` | Alarm Report 로그 조회 |
| `/ei/eiLogList.do` | `ei/eiLogList.jsp` | EI(Equipment Interface) 로그 조회 |
| `/ei/pop/textAreaPop.do` | `ei/pop/textAreaPop.jsp` | EI 다중 텍스트 영역 팝업 |
| `/ei/pop/textDetailPop.do` | `ei/pop/textDetailPop.jsp` | EI 텍스트 상세 팝업 |
| `/mat/carrierLocLogList.do` | `mat/carrierLocLogList.jsp` | Carrier 위치 로그 조회 |
| `/res/machineLogList.do` | `res/machineLogList.jsp` | 장비(Machine) 로그 |
| `/res/portLogList.do` | `res/portLogList.jsp` | Port 로그 |
| `/res/shelfLogList.do` | `res/shelfLogList.jsp` | Shelf 로그 |
| `/res/craneLogList.do` | `res/craneLogList.jsp` | Crane 로그 |
| `/res/vehicleLogList.do` | `res/vehicleLogList.jsp` | Vehicle(OHT 등) 로그 |
| `/res/storageLogList.do` | `res/storageLogList.jsp` | Storage Full 로그 |
| `/secs/secsLogList.do` | `secs/secsLogList.jsp` | SECS 통신 로그 |
| `/tot/totalLogList.do` | `tot/totalLogList.jsp` | 통합(Total) 로그 조회 |
| `/totNew/totalNewLogList.do` | `tot/totalNewLogList.jsp` | 신규 통합 로그(Carrier elapsed) |
| `/tot/dashboard/elapsedAnalysis.do` | `tot/elapsedAnalysis.jsp` | Logpresso 대시보드 iframe |
| `/tot/dashboard/compressAnalysis.do` | `tot/compressAnalysis.jsp` | Logpresso 대시보드 iframe |
| `/tot/dashboard/monitor.do` | `tot/monitor.jsp` | Logpresso 모니터 대시보드 iframe |
| `/tot/pop/filterPop.do` | `tot/pop/filterPop.jsp` | 컬럼/필터 설정 팝업 |
| `/tot/pop/machineNamePop.do` | `tot/pop/machineNamePop.jsp` | Machine Name 선택 팝업 |
| `/common/pop/settingPop.do` | `common/pop/settingPop.jsp` | Line(FAB) 설정 팝업 |
| `/tran/returnLogList.do` | `tran/returnLogList.jsp` | Return 로그(요약) |
| `/tran/returnJobLogList.do` | `tran/returnJobLogList.jsp` | Transport Job 이력 로그 |
| `/tran/returnCmdLogList.do` | `tran/returnCmdLogList.jsp` | Transport Command 이력 로그 |
| `/tran/returnJobFailLogList.do` | `tran/returnJobFailLogList.jsp` | Transport Job 실패 로그 |
| `/tran/returnCmdFailLogList.do` | `tran/returnCmdFailLogList.jsp` | Transport Command 실패 로그 |
| `/tran/pop/reasonPop.do` | `tran/pop/reasonPop.jsp` | Fail Reason 선택 팝업 |
| (error mapping) | `common/error/errorPage.jsp` | 시스템 에러 페이지 |
| (Tiles layout) | `layouts/layout.jsp` | Tiles 메인 레이아웃 정의 |
| (Tiles header) | `layouts/header.jsp` | 상단 GNB 헤더 + 탭/페이지이동 스크립트 |
| (partial, common) | `common/paging.jsp` | 간이 페이징 컴포넌트 |
| (partial, common) | `common/slickGridPager.jsp` | SlickGrid 페이저(이전/다음/리프레시) |
| (partial) | `common-header.jspf` | 공통 CSS/JS(슬릭그리드, jQuery, semantic UI 등) |
| (partial) | `common-taglib.jspf` | 공통 JSTL/Spring taglib 선언 |
| (test) | `tmp.jsp` | TMP 라벨만 출력하는 테스트 페이지 |

---

## 루트 / 테스트 페이지

### `webapp/index.jsp`
- 역할: 진입(landing) 페이지. `response.sendRedirect("tot/main")` 으로 메인 화면(`/tot/main`)으로 강제 리다이렉트.
- 종류: 일반 진입 JSP (라우팅 only).

### `WEB-INF/views/i18n.jsp`
- 역할: Spring i18n 기능 점검용 페이지. `?lang=ko/en/jp/zh` 링크로 언어 변경 후 `spring:message` 키 출력 확인.
- 종류: 테스트 페이지.
- 호출 URL: `/i18n.do?lang=…`

### `WEB-INF/views/monitoring.jsp`
- 역할: JVM Heap / Non-Heap / Memory Pool 사용량을 `ManagementFactory.getMemoryMXBean` 으로 출력하는 모니터링 페이지.
- 종류: 운영 모니터링 페이지(서버 사이드 렌더링).

### `WEB-INF/views/tmp.jsp`
- 역할: "TMP" 텍스트만 보여주는 임시/디버그용 페이지.
- 종류: 테스트 페이지.

---

## 공통 partial / taglib

### `WEB-INF/views/common-header.jspf`
- 역할: 모든 화면이 include 하는 공통 CSS/JS 번들 선언. `common.css, layout.css, btn01.css, board01.css, table01.css, semantic.css, slick.grid.css` 등 스타일과 `jquery-1.9.1, jquery-ui, slick.*`(SlickGrid), `semantic.min.js`, `prettify.js` 등을 로드.
- 종류: partial (jspf).

### `WEB-INF/views/common-taglib.jspf`
- 역할: 공통 JSTL/Spring taglib 선언(`c`, `fn`, `spring`).
- 종류: partial (jspf).

---

## 공통 화면 partial - `common/`

### `WEB-INF/views/common/error/errorPage.jsp`
- 역할: 시스템 에러 발생시 안내 페이지. "이용에 불편을 드려 죄송합니다", 시스템명/담당자/전화번호 영역과 이전/홈 버튼 노출.
- 종류: error page.
- 호출 URL: 정적(JS 없음).

### `WEB-INF/views/common/paging.jsp`
- 역할: 간이 페이지 네비게이션 partial. `rowNum` selector(100/200/500/1000) + 이전/다음 버튼. `param.searchFunc` 으로 호출자 화면의 검색 함수명을 받음.
- 종류: partial.

### `WEB-INF/views/common/pop/settingPop.jsp`
- 역할: Line(FAB Site) 설정 팝업. machineType select(M14FAB/M14AFAB/M14BFAB) 및 적용/닫기 버튼. 머신 리스트 조회 ajax 포함.
- 종류: popup.
- 호출 URL: `/common/pop/settingPop.do` (서빙), 내부 ajax `/tot/ajax/getMachineList.do`.

### `WEB-INF/views/common/slickGridPager.jsp`
- 역할: SlickGrid 전용 페이저 partial. 이전/다음 버튼, reload(refresh/append) 모드 선택, rows 수(200~5000), 현재 페이지/총 건수/조회시간 표시.
- 종류: partial.

---

## 알람 - `alarm/`

### `WEB-INF/views/alarm/alarmReportLogList.jsp`
- 역할: Alarm Report 로그 조회 페이지. 좌측 Filter View(FAB / 머신 / 기간 / 알람타입 필터), 우측 SlickGrid 결과 그리드.
- 종류: 로그 리스트 페이지(partial 형태로 탭 안에 로드됨).
- 기능: filter view, SlickGrid 그리드, slickGridPager 페이징, machineNamePop 팝업 연동, reset 버튼.
- 호출 URL:
  - 그리드 조회 ajax: `/alarm/ajax/getAlarmReportLogList.do`
  - 머신 선택 팝업: `/tot/pop/machineNamePop.do`
- 컨트롤러: `com.skhynix.supply.alarm.controller.AlarmReportController` (`@RequestMapping("alarm/alarmReportLogList")`).

---

## EI(Equipment Interface) - `ei/`

### `WEB-INF/views/ei/eiLogList.jsp`
- 역할: EI 통신 로그 조회 페이지. FAB/머신/기간/조건 필터 + SlickGrid 결과 영역. 행 클릭 시 텍스트 팝업으로 상세 본문 표시.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, process 트리 조회, 조회 중단(stop), text 상세 팝업.
- 호출 URL:
  - 로그 조회 ajax: `/ei/ajax/getEiLogList.do`
  - 조회 중단 ajax: `/ei/ajax/getEiQueryStop.do`
  - SECS 보조: `/secs/ajax/getsecsLogList.do`
  - Process 트리: `filter/ajax/getSelectProcessList.do`, `filter/ajax/getProcessList.do`
  - 상세 팝업: `/ei/pop/textAreaPop.do` (구버전 `/ei/pop/textDetailPop.do`)
- 컨트롤러: `com.skhynix.supply.secs.controller.EiLogController` (`@RequestMapping("ei/eiLogList")`).

### `WEB-INF/views/ei/pop/textAreaPop.jsp`
- 역할: EI 다중 텍스트 영역(여러 row의 본문을 동적으로 textarea 로 누적 표시) 팝업. 윈도우 리사이즈 시 너비 자동 조정.
- 종류: popup.
- 호출 URL: `/ei/pop/textAreaPop.do`.
- 컨트롤러: `EiLogController#textAreaPop`.

### `WEB-INF/views/ei/pop/textDetailPop.jsp`
- 역할: EI 단일 로그 본문 상세 표시(prettyprint `<pre>`/`<textarea>`) 팝업. (현재는 주석 처리 영역도 다수)
- 종류: popup.
- 호출 URL: `/ei/pop/textDetailPop.do`.
- 컨트롤러: `EiLogController#textDetailPop`.

---

## 레이아웃 - `layouts/`

### `WEB-INF/views/layouts/layout.jsp`
- 역할: Apache Tiles 메인 레이아웃 정의. `tiles:insertAttribute` 로 header/body/footer 영역 합성.
- 종류: Tiles layout.

### `WEB-INF/views/layouts/header.jsp`
- 역할: 상단 GNB(메뉴) + 페이지 이동/탭 관리 JS 스크립트. Alarm/Resource/Material/Transport/LogList 메뉴 3-depth. `movePage(url)` 함수에서 ajax 로 partial JSP 를 받아 `#contentList` 에 append 하고 `createTab(uuid)` 으로 탭 생성.
- 종류: layout(헤더).
- 호출 URL: 메뉴의 각 `/alarm/...`, `/res/...`, `/mat/...`, `/tran/...`, `/tot/...`, `/secs/...`, `/ei/...` URL. 언어 변경: `/tot/main?lang=ko|zh`.

---

## 자재(Material) - `mat/`

### `WEB-INF/views/mat/carrierLocLogList.jsp`
- 역할: Carrier(부자재) 위치 변경 로그 조회. FAB/기간/Carrier ID 필터 + SlickGrid.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, machineNamePop 연동.
- 호출 URL:
  - 조회 ajax: `/mat/ajax/getCarrierLocLogList.do`
  - 머신 팝업: `/tot/pop/machineNamePop.do`
- 컨트롤러: `com.skhynix.supply.mat.controller.MaterialController` (`@RequestMapping("mat/carrierLocLogList")`).

---

## 리소스(Resource) - `res/`

### `WEB-INF/views/res/machineLogList.jsp`
- 역할: 장비(Machine) 변경 이력 로그 조회.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, Carrier 보조조회, machineNamePop.
- 호출 URL:
  - 조회 ajax: `/res/ajax/getMachineLogList.do`
  - Carrier 보조: `/mat/ajax/getCarrierLocLogList.do`
  - 머신 팝업: `/tot/pop/machineNamePop.do`
- 컨트롤러: `ResMachineHistoryController`.

### `WEB-INF/views/res/portLogList.jsp`
- 역할: Port 로그 조회.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/res/ajax/getPortLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`.
- 컨트롤러: `ResPortHistoryController`.

### `WEB-INF/views/res/shelfLogList.jsp`
- 역할: Shelf 로그 조회.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/res/ajax/getShelfLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`.
- 컨트롤러: `ResShelfHistoryController`.

### `WEB-INF/views/res/craneLogList.jsp`
- 역할: Crane(스토커 크레인) 이력 로그 조회.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/res/ajax/getCraneLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`.
- 컨트롤러: `ResCraneHistoryController`.

### `WEB-INF/views/res/vehicleLogList.jsp`
- 역할: Vehicle(OHT 등 운반장비) 이력 로그 조회.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/res/ajax/getVehicleLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`.
- 컨트롤러: `ResVehicleHistoryController`.

### `WEB-INF/views/res/storageLogList.jsp`
- 역할: Storage Full(저장소 가득참) 이벤트 로그.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/res/ajax/getStorageLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`.
- 컨트롤러: `ResStorageFullHistoryController`.

---

## SECS 통신 - `secs/`

### `WEB-INF/views/secs/secsLogList.jsp`
- 역할: SECS-II 통신 로그 조회. FAB/장비/스트림+함수 필터, SlickGrid, 본문 텍스트 팝업.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, 조회 중단(Stop), 본문 팝업.
- 호출 URL:
  - 조회 ajax: `/secs/ajax/getsecsLogList.do`
  - 조회 중단: `/ei/ajax/getSecsQueryStop.do`
  - SECS FAB/리스트: `filter/ajax/getSecsFabList.do`, `filter/ajax/getSecsList.do`
  - 본문 팝업: `/ei/pop/textAreaPop.do`
- 컨트롤러: `com.skhynix.supply.secs.controller.SecsLogController` (`@RequestMapping("secs/secsLogList")`).

---

## 통합(Total) / 대시보드 - `tot/`

### `WEB-INF/views/tot/main.jsp`
- 역할: 단일 페이지 메인 컨테이너. 탭 마스터(`#tabList`)와 콘텐츠 컨테이너(`#contentList`), 우측 컨텍스트 메뉴(Copy selected/Copy checked/Copy column) 정의. 탭 페이징 reload(refresh/append) 토글 처리.
- 종류: 메인 컨테이너 페이지 (Tiles body로 결합).
- 호출 URL: 내부적으로 `getLogDetailGroup.do`, `settingPop.do`, 각 메뉴 페이지 URL.
- 컨트롤러: `TotalController#main` (`@RequestMapping("tot/main")`).

### `WEB-INF/views/tot/totalLogList.jsp`
- 역할: 모든 도메인 통합 로그(Total) 조회 화면. 가장 큰 화면으로 필터/조회/그리드/상세팝업/카리어 추적 등 다수 기능 결합.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, 컬럼 필터 팝업(filterPop), machineNamePop, 상세(LogDetail) 팝업, 조회 중단, Carrier 보조조회.
- 호출 URL:
  - 조회 ajax: `/tot/ajax/getTotalLogList.do`
  - 조회 중단: `/tot/ajax/getTotalLogListStop.do`
  - 상세: `/tot/ajax/getLogDetail.do`
  - 컬럼 필터 팝업: `/tot/pop/filterPop.do`
  - 머신 팝업: `/tot/pop/machineNamePop.do`
  - Carrier 보조: `/mat/ajax/getCarrierLocLogList.do`
- 컨트롤러: `TotalController#totalLogList` (`@RequestMapping("tot/totalLogList")`).

### `WEB-INF/views/tot/totalNewLogList.jsp`
- 역할: 신규(개선판) 통합 로그 + Carrier elapsed time 분석 화면. 달력 datepicker 적용.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, datepicker, machineNamePop, carrierElapsed 조회.
- 호출 URL:
  - 조회 ajax: `/totNew/ajax/totalNewLogList.do`
  - Carrier Elapsed: `/totNew/ajax/getCarrierElapsed.do`
  - 머신 팝업: `/tot/pop/machineNamePop.do`
- 컨트롤러: `TotalNewController#totalNewLogList` (`@RequestMapping("totNew/totalNewLogList")`).

### `WEB-INF/views/tot/elapsedAnalysis.jsp`
- 역할: 외부 Logpresso 대시보드(elapsed analysis)를 iframe 으로 임베드 한 분석 페이지.
- 종류: 대시보드 페이지(외부 iframe).
- 컨트롤러: `TotalController` (`tot/dashboard/elapsedAnalysis`).

### `WEB-INF/views/tot/compressAnalysis.jsp`
- 역할: 외부 Logpresso 대시보드(compress analysis)를 iframe 으로 임베드.
- 종류: 대시보드 페이지(외부 iframe).
- 컨트롤러: `TotalController` (`tot/dashboard/compressAnalysis`).

### `WEB-INF/views/tot/monitor.jsp`
- 역할: 외부 Logpresso 모니터 대시보드를 iframe 으로 임베드.
- 종류: 대시보드 페이지(외부 iframe).
- 컨트롤러: `TotalController` (`tot/dashboard/monitor`).

### `WEB-INF/views/tot/pop/filterPop.jsp`
- 역할: SlickGrid 컬럼/조건 필터 설정 팝업. 툴팁/화살표 등 커스텀 스타일 정의.
- 종류: popup.
- 컨트롤러: `TotalController#filterPop` (`@RequestMapping("tot/pop/filterPop")`).

### `WEB-INF/views/tot/pop/machineNamePop.jsp`
- 역할: Machine Type → Machine Name 단계 선택 팝업. 좌측은 후보 머신 테이블, 우측은 선택된 머신 누적 영역.
- 종류: popup.
- 기능: machineType 변경 시 ajax 로 머신 리스트 재조회.
- 호출 URL: 머신 리스트 ajax `/tot/ajax/getMachineList.do`.
- 컨트롤러: `TotalController#machineNamePop` (`@RequestMapping("tot/pop/machineNamePop")`). (Total New 전용 `totNew/pop/machineNamePop` 도 존재)

---

## 트랜스포트(Transport) - `tran/`

### `WEB-INF/views/tran/returnLogList.jsp`
- 역할: Return(반송) 로그 요약 조회 화면. Job 및 Cmd 이력 상세 보조 조회.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, machineNamePop, Job/Cmd 상세 ajax.
- 호출 URL: 머신 팝업 `/tot/pop/machineNamePop.do`, Job 상세 `/tran/ajax/getTranJobHistoryDetail.do` (Cmd 상세는 주석).
- 컨트롤러: `com.skhynix.supply.tran.controller.TranController` (`@RequestMapping("tran/returnLogList")`).

### `WEB-INF/views/tran/returnJobLogList.jsp`
- 역할: Transport Job 이력 로그 조회 화면. 그리드 행에서 totalLogList 로 이동 가능.
- 종류: 로그 리스트 페이지.
- 기능: filter view, SlickGrid, slickGridPager, machineNamePop, Total 화면 이동.
- 호출 URL: 조회 `/tran/ajax/getReturnJobLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`, 이동 `/tot/totalLogList.do?...`.
- 컨트롤러: `TranJobHistoryController` (`@RequestMapping("tran/returnJobLogList")`).

### `WEB-INF/views/tran/returnCmdLogList.jsp`
- 역할: Transport Command 이력 로그 조회 화면.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/tran/ajax/getReturnCmdLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`, 이동 `/tot/totalLogList.do`.
- 컨트롤러: `TranCmdHistoryController` (`@RequestMapping("tran/returnCmdLogList")`).

### `WEB-INF/views/tran/returnJobFailLogList.jsp`
- 역할: Transport Job 실패(Fail) 로그 조회 화면.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/tran/ajax/getReturnJobFailLogList.do`, 머신 팝업 `/tot/pop/machineNamePop.do`, 이동 `/tot/totalLogList.do`.
- 컨트롤러: `TranJobFailController` (`@RequestMapping("tran/returnJobFailLogList")`).

### `WEB-INF/views/tran/returnCmdFailLogList.jsp`
- 역할: Transport Command 실패(Fail) 로그 조회 화면. Fail Reason 필터 팝업 사용.
- 종류: 로그 리스트 페이지.
- 호출 URL: 조회 `/tran/ajax/getReturnCmdFailLogList.do`, Reason 팝업 `/tran/pop/reasonPop.do`, 머신 팝업 `/tot/pop/machineNamePop.do`, 이동 `/tot/totalLogList.do`.
- 컨트롤러: `TranCmdFailController` (`@RequestMapping("tran/returnCmdFailLogList")`).

### `WEB-INF/views/tran/pop/reasonPop.jsp`
- 역할: Fail Reason 코드 선택 팝업. 좌측 후보 리스트(체크박스), 우측 선택 영역.
- 종류: popup.
- 호출 URL: Reason 목록 ajax `/tran/ajax/getReasonList.do`.
- 컨트롤러: `TranCmdFailController#reasonPop` (`@RequestMapping("tran/pop/reasonPop")`).

---

## 공통 컴포넌트

| 컴포넌트 | 역할 |
|---|---|
| `common-header.jspf` | 공통 CSS/JS 묶음 include. SlickGrid · jQuery 1.7/1.9 · jQuery UI · semantic UI · prettify · common.js 등을 한 번에 로드. 거의 모든 페이지의 첫줄 `@include` 대상. |
| `common-taglib.jspf` | JSTL `c`, `fn`, Spring `spring` taglib 선언. 모든 partial JSP의 시작부에 include. |
| `layouts/layout.jsp` | Apache Tiles 메인 레이아웃. `header / body / footer` 3개 attribute 를 `tiles:insertAttribute` 로 결합. |
| `layouts/header.jsp` | 상단 GNB 메뉴(Alarm / Resource / Material / Transport / LogList). `movePage(url)` 함수가 ajax 로 partial JSP 를 받아 탭/콘텐츠로 추가. `tabTitle` 매핑, 다국어 플래그 링크. |
| `common/paging.jsp` | rowNum select + 이전/다음 버튼만 있는 간이 페이지네이션. 부모에서 `param.searchFunc/prevPageNo/nextPageNo` 전달. |
| `common/slickGridPager.jsp` | SlickGrid 전용 페이저. reload(refresh/append) 모드, rows 선택, 페이지/건수/조회시간 표시. 모든 로그 리스트 JSP가 `<c:import>` 로 포함. |
| `common/pop/settingPop.jsp` | Line(FAB) 설정 팝업 공통. 머신 리스트 ajax 호출. |
| `common/error/errorPage.jsp` | 시스템 에러 표시 페이지. |

---

## 화면 공통 패턴

- 모든 로그 리스트 화면은 거의 동일 구조: `searchForm`(hidden `fabSite, type, page, machineName, filter, uuid`) → 좌측 `filter_view`(FAB/머신/조건) → 우측 SlickGrid + `slickGridPager.jsp` import.
- partial 로드: `header.jsp` 의 `movePage(url)` → ajax(`type:'post', dataType:'html'`) → 응답 HTML 을 `#contentList` 에 append → `moveTab(uuid)` 로 탭 전환. 모든 partial JSP 의 루트 `div` 가 `id="body_${param.uuid}"` 패턴을 사용.
- 머신 선택은 공용 팝업(`/tot/pop/machineNamePop.do`)을 거의 모든 로그 리스트에서 재사용.
- 조회/중단/상세 API 는 도메인별 `/<domain>/ajax/...` 네임스페이스로 통일.
