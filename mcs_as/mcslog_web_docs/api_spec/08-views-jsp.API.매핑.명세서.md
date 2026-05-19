# SK hynix MCS Log 조회 시스템 — JSP 화면별 API 호출 매핑 명세서

본 문서는 `mcslog_web_src/src/main/webapp/` 하위 38개 JSP/JSPF 파일이
서버측 컨트롤러(또는 외부 자원)와 어떻게 연결되어 있는지(ajax 호출, form action,
페이지 이동, iframe 임베드 등)를 정리한 매핑 명세서이다.

---

## 1. 개요

### 1.1 화면 분류

| 구분 | 파일 (개수) | 설명 |
|---|---|---|
| 진입점(redirect) | `index.jsp` (1) | `/tot/main` 으로 리다이렉트 |
| 레이아웃/공통 partial | `WEB-INF/views/layouts/layout.jsp`, `layouts/header.jsp`, `common-header.jspf`, `common-taglib.jspf` (4) | Tiles 레이아웃, GNB, 공통 헤더/태그 |
| 공통 UI 부품 | `common/paging.jsp`, `common/slickGridPager.jsp` (2) | 페이징 partial |
| 에러 페이지 | `common/error/errorPage.jsp` (1) | 시스템 에러 |
| 유틸/실험용 | `i18n.jsp`, `monitoring.jsp`, `tmp.jsp` (3) | i18n 데모, JVM 메모리 모니터, 빈 페이지 |
| 알람 로그 리스트 | `alarm/alarmReportLogList.jsp` (1) | Alarm Report 로그 |
| EI/SECS 로그 리스트 | `ei/eiLogList.jsp`, `secs/secsLogList.jsp` (2) | EI / SECS 로그 |
| EI 팝업 | `ei/pop/textAreaPop.jsp`, `ei/pop/textDetailPop.jsp` (2) | 텍스트 상세 팝업 |
| Material 로그 | `mat/carrierLocLogList.jsp` (1) | Carrier Location 로그 |
| Resource 로그 리스트 | `res/craneLogList.jsp`, `res/machineLogList.jsp`, `res/portLogList.jsp`, `res/shelfLogList.jsp`, `res/storageLogList.jsp`, `res/vehicleLogList.jsp` (6) | 설비/Port/Shelf/Crane/Vehicle/Storage 로그 |
| Total 로그/분석 | `tot/main.jsp`, `tot/totalLogList.jsp`, `tot/totalNewLogList.jsp`, `tot/monitor.jsp`, `tot/compressAnalysis.jsp`, `tot/elapsedAnalysis.jsp` (6) | 통합 로그 / Logpresso 대시보드 |
| Total 팝업 | `tot/pop/machineNamePop.jsp`, `tot/pop/filterPop.jsp` (2) | 머신명 선택, 필터 설정 |
| Transport 로그 리스트 | `tran/returnLogList.jsp`, `tran/returnJobLogList.jsp`, `tran/returnCmdLogList.jsp`, `tran/returnJobFailLogList.jsp`, `tran/returnCmdFailLogList.jsp` (5) | Transport Return/Job/Cmd 로그 (성공/실패) |
| Transport 팝업 | `tran/pop/reasonPop.jsp` (1) | Reason 선택 |
| **합계** | **38** |  |

### 1.2 공통 호출 패턴

* **로그 리스트 조회 ajax**: 거의 모든 *List.jsp 가 `<도메인>/ajax/get<XXX>LogList.do` 형태의 endpoint 를 `POST $.ajax({ url, data: param })` 으로 호출한다.
* **검색 폼 직렬화**: `$content.find("#searchForm").serializeObject()` 로 검색 파라미터를 jQuery serialize 후 `data:` 로 전달.
* **취소 호출**: 일부 화면(`totalLogList`, `eiLogList`, `secsLogList`)은 `getXxxStop.do` 또는 `getEiQueryStop.do` 로 조회 중단 ajax 호출.
* **머신명 팝업 공용**: `tot/pop/machineNamePop.do` 는 6개 res/tran/alarm/mat/tot/tot-new JSP 에서 공용으로 `openPopup()` 으로 호출된다.
* **페이지 이동**: GNB 및 화면 내부 navigation 은 `header.jsp` 에 정의된 `movePage(url)` (라인 337) 을 호출 — 내부적으로 `$.ajax({url, type:'post', dataType:'html', data:{uuid}})` 로 partial HTML 을 받아 `#contentList` 에 append (탭 방식 SPA).
* **외부 대시보드**: `tot/monitor.jsp`, `tot/compressAnalysis.jsp`, `tot/elapsedAnalysis.jsp` 는 Logpresso 대시보드(`http://10.25.210.120:8888/...`) 를 `<iframe>` 으로 임베드.

---

## 2. 화면별 API 호출 매핑

### 2.1 진입점 / 공통 partial

#### 2.1.1 `index.jsp`

* 화면 종류: redirect
* 공통 partial 포함: 없음

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 |
|---|---|---|---|---|
| `tot/main` | GET | 6 | `response.sendRedirect(...)` | 진입 시 메인 페이지로 redirect |

#### 2.1.2 `WEB-INF/views/common-header.jspf`

* 화면 종류: partial (공통 CSS/JS include)
* API 호출: 없음. CSS·JS 정적 자원 로드만 수행 (jQuery, jQuery UI, SlickGrid, semantic UI, prettify, `common.js`).
* 정적 자원 경로 예: `/styles/css/common.css`, `/styles/slickGrid/slick.grid.js`, `/styles/js/common/common.js?v=<%=Common.sBUILD_VER%>`.

#### 2.1.3 `WEB-INF/views/common-taglib.jspf`

* 화면 종류: partial (JSTL/Spring taglib 선언)
* API 호출: 없음. `c`, `fn`, `spring` prefix 선언만 포함.

#### 2.1.4 `WEB-INF/views/i18n.jsp`

* 화면 종류: i18n 데모 페이지
* API 호출:

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/i18n.do?lang=ko` | GET | 11 | `<a href>` 링크 | 언어 변경 (ko) |
| `/i18n.do?lang=en` | GET | 12 | `<a href>` 링크 | 언어 변경 (en) |
| `/i18n.do?lang=jp` | GET | 13 | `<a href>` 링크 | 언어 변경 (jp) |
| `/i18n.do?lang=zh` | GET | 14 | `<a href>` 링크 | 언어 변경 (zh) |

#### 2.1.5 `WEB-INF/views/monitoring.jsp`

* 화면 종류: 유틸 (JVM 메모리 모니터)
* API 호출: 없음. `java.lang.management.ManagementFactory` 를 통해 서버측 JVM 메모리 정보를 직접 출력.

#### 2.1.6 `WEB-INF/views/tmp.jsp`

* 화면 종류: 빈 페이지 (임시/테스트)
* API 호출: 없음. 본문은 "TMP" 텍스트만 출력.

---

### 2.2 layouts/

#### 2.2.1 `WEB-INF/views/layouts/layout.jsp`

* 화면 종류: Tiles 레이아웃 root
* API 호출: 없음. `<tiles:insertAttribute name="header|body|footer" />` 만 수행.

#### 2.2.2 `WEB-INF/views/layouts/header.jsp`

* 화면 종류: GNB 헤더 partial + 공용 페이지 이동 함수(`movePage`) 정의

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/alarm/alarmReportLogList.do` | GET→ajax | 19, 30, 35 | `movePage()` | Alarm 메뉴 GNB |
| `/res/machineLogList.do` | GET→ajax | 49, 60, 65 | `movePage()` | Resource > Machine |
| `/res/portLogList.do` | GET→ajax | 71 | `movePage()` | Resource > Port |
| `/res/shelfLogList.do` | GET→ajax | 77 | `movePage()` | Resource > Shelf |
| `/res/craneLogList.do` | GET→ajax | 83 | `movePage()` | Resource > Crane |
| `/res/vehicleLogList.do` | GET→ajax | 89 | `movePage()` | Resource > Vehicle |
| `/res/storageLogList.do` | GET→ajax | 95 | `movePage()` | Resource > Storage |
| `/mat/carrierLocLogList.do` | GET→ajax | 109, 119, 124 | `movePage()` | Material > Carrier Loc |
| `/tran/returnLogList.do` | GET→ajax | 137, 147, 152 | `movePage()` | Transport > Return |
| `/tran/returnJobLogList.do` | GET→ajax | 158 | `movePage()` | Transport > Return Job |
| `/tran/returnCmdLogList.do` | GET→ajax | 164 | `movePage()` | Transport > Return Cmd |
| `/tran/returnJobFailLogList.do` | GET→ajax | 170 | `movePage()` | Transport > Return Job Fail |
| `/tran/returnCmdFailLogList.do` | GET→ajax | 176 | `movePage()` | Transport > Return Cmd Fail |
| `/totNew/totalNewLogList.do` | GET→ajax | 182 | `movePage()` | Total New |
| `/tot/dashboard/elapsedAnalysis.do` | GET→ajax | 195, 205, 210 | `movePage()` | Dashboard > Elapsed |
| `/tot/dashboard/compressAnalysis.do` | GET→ajax | 216 | `movePage()` | Dashboard > Compress |
| `/tot/dashboard/monitor.do` | GET→ajax | 222 | `movePage()` | Dashboard > Monitor |
| `/tot/totalLogList.do` | GET→ajax | 235, 245, 250 | `movePage()` | Log List > Total |
| `/secs/secsLogList.do` | GET→ajax | 256 | `movePage()` | Log List > SECS |
| `/ei/eiLogList.do` | GET→ajax | 262 | `movePage()` | Log List > EI |
| `(인자 url)` | POST | 354 | `$.ajax({url, type:'post', dataType:'html', data:{uuid}})` | `movePage(url)` 의 ajax 본체 — partial HTML 을 받아 `#contentList` 에 append (탭 SPA 핵심) |

> ※ `movePage(url)` 자체는 컨트롤러에서 partial JSP HTML 을 받아 동적 삽입한다.
>   따라서 위 GNB 링크들의 실제 호출 형태는 GET 가 아니라 **POST → fragment HTML** 이다.

---

### 2.3 common/

#### 2.3.1 `WEB-INF/views/common/error/errorPage.jsp`

* 화면 종류: error
* API 호출: 없음. 정적 안내 페이지 (Home/이전 페이지 버튼의 href 는 `"#"` placeholder).
* 공통 partial: `common-header.jspf`, `common-taglib.jspf` include.

#### 2.3.2 `WEB-INF/views/common/paging.jsp`

* 화면 종류: partial (페이징 nav)
* API 호출: 없음.
* 인자로 받은 `${param.searchFunc}` 함수명을 prev/next 버튼의 `javascript:` href 로 인라인 호출 (라인 19~20).
* `select#rowNum` 셀렉트는 `100/200/500/1000` 옵션 제공 (페이지 사이즈).

#### 2.3.3 `WEB-INF/views/common/slickGridPager.jsp`

* 화면 종류: partial (SlickGrid pager)
* API 호출: 없음. `reload`(refresh/append), `rows`(200~5000) 셀렉트 박스만 표시.
* 호출자 화면들이 `$content.find("#rows"), #pageTxt, #rowCount, #laptime` 에 직접 접근하여 갱신.
* import 된 화면: 16개 로그 리스트 JSP 전부 (`<c:import url="/WEB-INF/views/common/slickGridPager.jsp" />`).

#### 2.3.4 `WEB-INF/views/common/pop/settingPop.jsp`

* 화면 종류: popup (환경설정 — machineName)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/ajax/getMachineList.do` | POST | 66~80 | `$.ajax` | 머신명 목록 조회. data: `{ machineType }` |

---

### 2.4 alarm/

#### 2.4.1 `WEB-INF/views/alarm/alarmReportLogList.jsp`

* 화면 종류: list
* 공통 partial: `slickGridPager.jsp` (라인 304)

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 494 | `openPopup(url, 600, 610, callback)` | 머신명 선택 팝업 |
| `/alarm/ajax/getAlarmReportLogList.do` | POST | 737, 745 | `$.ajax` | Alarm Report 로그 조회. data: `param = serializeObject()` |

---

### 2.5 ei/

#### 2.5.1 `WEB-INF/views/ei/eiLogList.jsp`

* 화면 종류: list
* 공통 partial: `slickGridPager.jsp` (라인 366)

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/ei/ajax/getEiQueryStop.do` | POST | 605~612 | `$.ajax` | 조회 cancel |
| `/secs/ajax/getsecsLogList.do` | (주석) | 623 | — | (주석 처리됨, machineBtn 코드) |
| `/ei/pop/textAreaPop.do` | window.open | 767, 782 | `window.open(popupURL, ...)` | 텍스트 상세 팝업 |
| `/ei/pop/textDetailPop.do` | (주석) | 766 | — | 구버전 텍스트 상세(대체됨) |
| (텍스트 팝업) | window.open | 805 | `window.open(url, ...)` | 800x600 텍스트 상세 |
| `filter/ajax/getSelectProcessList.do` | POST | 912, 914 | `$.ajax` | Log/Fab 타입별 Process list. data: `{ selectType, selectFab }` |
| `filter/ajax/getProcessList.do` | GET | 937, 939 | `$.ajax` | Process list. data: `{ fabSite }` |
| `/ei/ajax/getEiLogList.do` | POST | 985~990 | `$.ajax` | EI 로그 조회. data: `serializeObject()` (fab/level/process/text/machine 등) |

#### 2.5.2 `WEB-INF/views/ei/pop/textAreaPop.jsp`

* 화면 종류: popup (텍스트 영역 다중 표시)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`
* API 호출: 없음. opener 에서 호출하는 `detailTextArea(textMap, gridCount, rowIdx, popupKey)` / `detailTextFindFocus(...)` 함수만 노출.

#### 2.5.3 `WEB-INF/views/ei/pop/textDetailPop.jsp`

* 화면 종류: popup (텍스트 상세 — 구버전)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`
* API 호출: 없음. opener 가 `detailTextFindFocus(popOption)` 호출. **eiLogList.jsp / secsLogList.jsp 에서는 textAreaPop 으로 대체됨** (라인 766 주석 참고).

---

### 2.6 mat/

#### 2.6.1 `WEB-INF/views/mat/carrierLocLogList.jsp`

* 화면 종류: list
* 공통 partial: `slickGridPager.jsp` (라인 303)

| URL | HTTP | 호출 위치(라인) | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 480 | `openPopup(url, 600, 610, cb)` | 머신명 선택 팝업 |
| `/mat/ajax/getCarrierLocLogList.do` | POST | 724~726 | `$.ajax` | Carrier Location 로그 조회. data: `serializeObject()` |

---

### 2.7 res/

#### 2.7.1 `WEB-INF/views/res/craneLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (304)
* 페이지 이동(breadcrumb): `/tot/totalLogList.do` (라인 7), `/res/machineLogList.do` (라인 11), `/res/craneLogList.do` (라인 15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 493 | `openPopup` | 머신명 팝업 |
| `/res/ajax/getCraneLogList.do` | POST | 692~694 | `$.ajax` | Crane 로그 조회. data: serializeObject |

#### 2.7.2 `WEB-INF/views/res/machineLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (306)
* breadcrumb: `/tot/totalLogList.do` (7), `/res/machineLogList.do` (11, 15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 484 | `openPopup` | 머신명 팝업 |
| `/mat/ajax/getCarrierLocLogList.do` | POST | 649 | `$.ajax` (간접) | 더블클릭/연관조회용 호출 |
| `/res/ajax/getMachineLogList.do` | POST | 734~736 | `$.ajax` | Machine 로그 조회 |

#### 2.7.3 `WEB-INF/views/res/portLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (335)
* breadcrumb: `/tot/totalLogList.do` (7), `/res/machineLogList.do` (11), `/res/portLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 512 | `openPopup` | 머신명 팝업 |
| `/res/ajax/getPortLogList.do` | POST | 766~775 | `$.ajax` | Port 로그 조회 |

#### 2.7.4 `WEB-INF/views/res/shelfLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (301)
* breadcrumb: `/tot/totalLogList.do` (7), `/res/machineLogList.do` (11), `/res/shelfLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 478 | `openPopup` | 머신명 팝업 |
| `/res/ajax/getShelfLogList.do` | POST | 733~735 | `$.ajax` | Shelf 로그 조회 |

#### 2.7.5 `WEB-INF/views/res/storageLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (292)
* breadcrumb: `/tot/totalLogList.do` (7), `/res/machineLogList.do` (11), `/res/storageLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 470 | `openPopup` | 머신명 팝업 |
| `/res/ajax/getStorageLogList.do` | POST | 710~712 | `$.ajax` | Storage 로그 조회 |

#### 2.7.6 `WEB-INF/views/res/vehicleLogList.jsp`

* 화면 종류: list / 공통 partial: `slickGridPager.jsp` (324)
* breadcrumb: `/tot/totalLogList.do` (7), `/res/machineLogList.do` (11), `/res/vehicleLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 500 | `openPopup` | 머신명 팝업 |
| `/res/ajax/getVehicleLogList.do` | POST | 743~745 | `$.ajax` | Vehicle 로그 조회 |

---

### 2.8 secs/

#### 2.8.1 `WEB-INF/views/secs/secsLogList.jsp`

* 화면 종류: list
* 공통 partial: `slickGridPager.jsp` (329)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/ei/ajax/getSecsQueryStop.do` | POST | 525~527 | `$.ajax` | 조회 cancel |
| `/secs/ajax/getsecsLogList.do` | POST | 543, 895~897 | `$.ajax` | SECS 로그 조회. data: serializeObject (filter/level/fab 등) |
| `/ei/pop/textAreaPop.do` | window.open | 687, 701 | `window.open(popupURL, "wFormx", ...)` | 텍스트 상세 팝업 (1200x800) |
| (텍스트 팝업) | window.open | 724 | `window.open(url, ...)` | 800x600 텍스트 상세 |
| `filter/ajax/getSelectProcessList.do` (추정) | POST | 824~825 | `$.ajax`  → `urlSecsName` | Process/Secs filter list. data: `param` |
| `filter/ajax/getProcessList.do` (추정) | POST | 848~849 | `$.ajax` → `urlSecsName` | Process/Secs filter list. data: `param` |

> ※ `urlSecsName` 변수는 EI 동일 패턴(`filter/ajax/getSelectProcessList.do`, `filter/ajax/getProcessList.do`)이다.

---

### 2.9 tot/

#### 2.9.1 `WEB-INF/views/tot/main.jsp`

* 화면 종류: tot 메인 (탭 SPA 컨테이너)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/totFAB/totalM14FabLogList.do` | GET→ajax | 36 (주석) | `movePage()` 옵션 | (FAB 셀렉트, 비활성화됨) |
| `/tot/totalLogList.do` | GET→ajax | 37 (주석), 125, 278 | `movePage()` | 초기 진입 시 자동 호출 / FAB 셀렉트 옵션 |
| `/tot/ajax/getLogDetailGroup.do` | POST | 297~299 | `$.ajax (async:false)` | 선택된 로그 XML/SECSII 다건 상세 조회. data: `{ key: [keys] }`, `traditional:true` |
| `/common/pop/settingPop.do` | popup | 329 | `openPopup(url, 600, 200, cb)` | 환경설정 팝업 |
| `/tot/main?lang=ko/zh` | GET | 23, 29 | `<a href>` | 언어 변경 |

#### 2.9.2 `WEB-INF/views/tot/totalLogList.jsp`

* 화면 종류: list (Total 통합 로그)
* 공통 partial: `slickGridPager.jsp` (597)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/filterPop.do` | popup | 1090~1091 | `openPopup(url, 600, 610, cb)` | Filter Setting 팝업 |
| `/tot/ajax/getTotalLogListStop.do` | POST | 1270~1272 | `$.ajax` | 조회 cancel |
| `/tot/pop/machineNamePop.do` | popup | 1289 | `openPopup(url, 600, 610, cb)` | 머신명 선택 팝업 |
| `/tot/ajax/getLogDetail.do` | POST | 1552~1554 (주석) | `$.ajax` | (사용안함 표시 주석) 단건 XML/SECSII 상세 |
| `/mat/ajax/getCarrierLocLogList.do` | POST | 1644 | `$.ajax` (간접) | drawGrid 내 url 변수(미사용 가능성) |
| `/tot/ajax/getTotalLogList.do` | POST | 1835~1839 | `$.ajax` | **메인 Total 로그 조회**. data: `serializeObject + machineTypes` |
| `filter/ajax/getCommMsgNameList.do` | GET | 1950~1953 | `$.ajax` | COMM MSG NAME 옵션 목록. data: `{ fabSite }` |
| `filter/ajax/getOperationNameList.do` | GET | 1971~1974 | `$.ajax` | OPERATION NAME 옵션 목록. data: `{ fabSite }` |
| `filter/ajax/getMessageNameList.do` | GET | 1992~1995 | `$.ajax` | MESSAGE NAME 옵션 목록. data: `{ fabSite }` |
| `location.href + "#"` | — | 868 | hash 변경 | 페이지 hash 강제 갱신 |
| `location.href.toString()` | — | 2013 | `_url_get_function(...)` | URL 파라미터로 검색 자동 실행 |

#### 2.9.3 `WEB-INF/views/tot/totalNewLogList.jsp`

* 화면 종류: list (Total New — Carrier Elapsed 그루핑)
* 공통 partial: `slickGridPager.jsp` (403)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 609 | `openPopup` | 머신명 팝업 |
| `/totNew/ajax/getCarrierElapsed.do` | POST | 761~767 | `$.ajax (async:false)` | 행 펼침(unfold) 상세 조회. data: `{ addQuery }` |
| `/totNew/ajax/totalNewLogList.do` | POST | 863~867 | `$.ajax` | **메인 Total New 로그 조회**. data: `serializeObject + machineTypes`, `traditional:true` |

#### 2.9.4 `WEB-INF/views/tot/monitor.jsp`

* 화면 종류: dashboard (iframe)
* API 호출: 없음 (외부 임베드).
* `<iframe src="http://10.25.210.120:8888/logpresso/dashboard/w194a717ecda549f4?apikey=...">` (라인 5)

#### 2.9.5 `WEB-INF/views/tot/compressAnalysis.jsp`

* 화면 종류: dashboard (iframe)
* `<iframe src="http://10.25.210.120:8888/logpresso/dashboard/w01449cd9b609dd1a?apikey=...">` (라인 5)

#### 2.9.6 `WEB-INF/views/tot/elapsedAnalysis.jsp`

* 화면 종류: dashboard (iframe)
* `<iframe src="http://10.25.210.120:8888/logpresso/dashboard/w3abd7581fd7a5595?apikey=...">` (라인 5)

#### 2.9.7 `WEB-INF/views/tot/pop/filterPop.jsp`

* 화면 종류: popup (검색 조건 설정)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`
* API 호출: 없음. 폼 입력값을 `serializeObject()` 후 `opener.callback(param)` 으로 전달 (라인 292~297).

#### 2.9.8 `WEB-INF/views/tot/pop/machineNamePop.jsp`

* 화면 종류: popup (머신명 선택)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/ajax/getMachineList.do` | POST | 158~163 | `$.ajax` | 머신명 목록 조회. data: `{ machineType }` |

---

### 2.10 tran/

#### 2.10.1 `WEB-INF/views/tran/returnLogList.jsp`

* 화면 종류: list (Transport Return)
* 공통 partial: `slickGridPager.jsp` (467)
* breadcrumb: `/tran/returnLogList.do` (7, 11, 15)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 803, 815, 827 | `openPopup` | 머신명 팝업 (Source/Dest/Carrier 3종) |
| `/tran/ajax/getTranJobHistoryDetail.do` | POST | 1048, 1060~1063 | `$.ajax` | 더블클릭 시 JobHistory + Cmd 상세 동시 조회. data: `{ fabSite, from, to, transportJobId }` |
| `/tot/totalLogList.do?carrier=...&text=...&from=...&to=...` | navigation | 1096 | `movePage(...)` | 행 더블클릭 시 Total 로그로 이동 (carrier 검색) |
| `/tran/ajax/getReturnLogList.do` | POST | 1380~1384 | `$.ajax` | **메인 Return 로그 조회**. data: `serializeObject` |

#### 2.10.2 `WEB-INF/views/tran/returnJobLogList.jsp`

* 화면 종류: list (Transport Return Job)
* 공통 partial: `slickGridPager.jsp` (514)
* breadcrumb: `/tran/returnLogList.do` (7, 11), `/tran/returnJobLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 776, 788, 800 | `openPopup` | 머신명 팝업 3종 |
| `/tot/totalLogList.do?...` | navigation | 1075 | `movePage(...)` | 행 더블클릭시 Total로 |
| `/tran/ajax/getReturnJobLogList.do` | POST | 1136, 1148~1151 | `$.ajax` | **메인 Return Job 로그 조회**. data: `serializeObject` |

#### 2.10.3 `WEB-INF/views/tran/returnCmdLogList.jsp`

* 화면 종류: list (Transport Return Cmd)
* 공통 partial: `slickGridPager.jsp` (541)
* breadcrumb: `/tran/returnLogList.do` (7, 11), `/tran/returnCmdLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 802, 814, 826 | `openPopup` | 머신명 팝업 3종 |
| `/tot/totalLogList.do?...` | navigation | 1089 | `movePage(...)` | 행 더블클릭시 Total로 |
| `/tran/ajax/getReturnCmdLogList.do` | POST | 1143, 1157~1160 | `$.ajax` | **메인 Return Cmd 로그 조회**. data: `serializeObject` |

#### 2.10.4 `WEB-INF/views/tran/returnJobFailLogList.jsp`

* 화면 종류: list (Transport Return Job Fail)
* 공통 partial: `slickGridPager.jsp` (470)
* breadcrumb: `/tran/returnLogList.do` (7, 11), `/tran/returnJobFailLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tot/pop/machineNamePop.do` | popup | 736, 748, 760 | `openPopup` | 머신명 팝업 3종 |
| `/tot/totalLogList.do?...` | navigation | 1017 | `movePage(...)` | 행 더블클릭시 Total로 |
| `/tran/ajax/getReturnJobFailLogList.do` | POST | 1080, 1092~1093 | `$.ajax` | **메인 Return Job Fail 로그 조회**. data: `serializeObject` |
| `/tran/pop/reasonPop.do` | popup | 1138 | `openPopup` | Reason 선택 팝업 |

#### 2.10.5 `WEB-INF/views/tran/returnCmdFailLogList.jsp`

* 화면 종류: list (Transport Return Cmd Fail)
* 공통 partial: `slickGridPager.jsp` (467)
* breadcrumb: `/tran/returnLogList.do` (7, 11), `/tran/returnCmdFailLogList.do` (15)

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tran/pop/reasonPop.do` | popup | 779 | `openPopup` | Reason 선택 팝업 |
| `/tot/pop/machineNamePop.do` | popup | 797, 809, 821 | `openPopup` | 머신명 팝업 3종 |
| `/tot/totalLogList.do?...` | navigation | 1058 | `movePage(...)` | 행 더블클릭시 Total로 |
| `/tran/ajax/getReturnCmdFailLogList.do` | POST | 1112, 1124~1125 | `$.ajax` | **메인 Return Cmd Fail 로그 조회**. data: `serializeObject` |

#### 2.10.6 `WEB-INF/views/tran/pop/reasonPop.jsp`

* 화면 종류: popup (Reason 선택)
* 공통 partial: `common-header.jspf`, `common-taglib.jspf`

| URL | HTTP | 라인 | 호출 방식 | 용도 / data |
|---|---|---|---|---|
| `/tran/ajax/getReasonList.do` | POST | 147~149 | `$.ajax` | Reason 목록 조회. data: `{}` |

---

## 3. 공통 호출 패턴

### 3.1 검색 ajax 패턴

대부분의 로그 리스트 JSP 가 다음 패턴을 따른다.

```javascript
var url = "<c:url value='/<도메인>/ajax/get<XXX>LogList.do' />";
var param = $content.find("#searchForm").serializeObject();
param['machineTypes'] = ...;          // 일부 화면만
$.ajax({
    url: url,
    type: 'post',
    data: param,
    traditional: true,                 // 일부 화면 (배열 전송)
    success: function(result){ /* SlickGrid에 result.rows 적재 */ }
});
```

* 전달 파라미터(공통): `from`, `to`, `fabSite`, `fab`, `level`, `machineName`, `machineType`(s), `carrier`, `unitName`, `commandId`, `command`, `operation_name`, `messageName`, `process`, `transactionId`, `text`, `thread`, `rowNum`, `reload`, `page` 등.

### 3.2 조회 취소(Stop) 패턴

| 화면 | URL |
|---|---|
| eiLogList | `/ei/ajax/getEiQueryStop.do` |
| secsLogList | `/ei/ajax/getSecsQueryStop.do` |
| totalLogList | `/tot/ajax/getTotalLogListStop.do` |

`#cancelBtn` 클릭 시 POST 호출. data 없음.

### 3.3 페이징 호출 패턴

* SlickGrid pager (`slickGridPager.jsp`) 의 prev/next 아이콘 클릭 시 각 화면의 `getLogList<uuid>(page)` 함수가 직접 호출됨 (서버 호출은 위 §3.1 동일).
* `paging.jsp` (구버전 partial) 는 `${param.searchFunc}(prev/nextPageNo)` 형태로 인라인 호출.

### 3.4 팝업 호출 패턴 (공통)

| 팝업 URL | 사용 화면 | 용도 |
|---|---|---|
| `/tot/pop/machineNamePop.do` | alarm, ei(주석), mat, res(6), tran(5), tot(2) — **총 14개 호출** | 머신명 다중 선택 (Source/Dest/Carrier 3개소 흔함) |
| `/tot/pop/filterPop.do` | tot/totalLogList | 검색 필터 조건 일괄 입력 |
| `/common/pop/settingPop.do` | tot/main | 환경설정 (machineName 기반) |
| `/tran/pop/reasonPop.do` | tran/returnCmdFailLogList, returnJobFailLogList | Reason 선택 |
| `/ei/pop/textAreaPop.do` | ei/eiLogList, secs/secsLogList | 텍스트 다중 영역 상세 (1200x800) |
| `/ei/pop/textDetailPop.do` | (주석 처리) | 구버전 단일 텍스트 상세 (대체됨) |

호출 방식은 거의 모두 `openPopup(url, width, height, callback)` (in `common.js`) 또는 `window.open(url, "wFormx", "width=...,height=...")`.

### 3.5 필터/룩업 데이터 호출 패턴

| URL | 호출 화면 | data | 비고 |
|---|---|---|---|
| `filter/ajax/getProcessList.do` | ei, secs | `{ fabSite }` | Process select 옵션 |
| `filter/ajax/getSelectProcessList.do` | ei, secs | `{ selectType, selectFab }` | Log+Fab 별 Process |
| `filter/ajax/getCommMsgNameList.do` | tot/totalLogList | `{ fabSite }` | COMM MSG select |
| `filter/ajax/getOperationNameList.do` | tot/totalLogList | `{ fabSite }` | OPERATION select |
| `filter/ajax/getMessageNameList.do` | tot/totalLogList | `{ fabSite }` | MESSAGE select |
| `/tot/ajax/getMachineList.do` | settingPop, machineNamePop | `{ machineType }` | 머신명 룩업 |

> 위 `filter/ajax/...` 은 상대 경로로 호출되며, 현재 페이지의 컨텍스트 경로 기준으로
> `${ctx}/<현재경로>/filter/ajax/...` 로 분기될 가능성이 있다.
> (`tot/` catch-all 라우팅이 흡수하는 경우 `TotalLogController#filter()` 류로 매핑됨)

### 3.6 페이지 이동(`movePage`) 패턴

* `header.jsp` 라인 337 정의. 인자 `url` 을 `POST $.ajax({dataType:'html', data:{uuid}})` 로 호출해
  partial HTML 을 받아 `#contentList` 에 append 한 뒤 탭으로 표시.
* breadcrumb (`<a class="location">`) 와 GNB 메뉴는 모두 `javascript:movePage('<c:url>')` 형태.
* tran 리스트 그리드 더블클릭 시 `movePage('/tot/totalLogList.do?carrier=...&text=...&from=...&to=...')` 로 Total 로그 이동.

---

## 4. 외부 자원 임베드

3개 dashboard JSP 는 사내 Logpresso 호스트의 대시보드를 iframe 으로 임베드한다.

| JSP | iframe src | apikey |
|---|---|---|
| `tot/monitor.jsp` (라인 5) | `http://10.25.210.120:8888/logpresso/dashboard/w194a717ecda549f4` | `db1d2335-49cf-e859-3519-1ca132922e38` |
| `tot/compressAnalysis.jsp` (라인 5) | `http://10.25.210.120:8888/logpresso/dashboard/w01449cd9b609dd1a` | (동일) |
| `tot/elapsedAnalysis.jsp` (라인 5) | `http://10.25.210.120:8888/logpresso/dashboard/w3abd7581fd7a5595` | (동일) |

* 공통 크기: 1880 × 850, scrolling=no
* api key 는 JSP 정적 텍스트에 노출됨 (보안 관점 비고: §5 참고).

---

## 5. 비고

### 5.1 유틸/실험용 화면
* `tmp.jsp`: 빈 페이지(본문 "TMP"). 라우팅 테스트용으로 추정.
* `i18n.jsp`: `/i18n.do?lang=ko/en/jp/zh` 4개 링크만 존재하는 다국어 데모.
* `monitoring.jsp`: 서버측 JVM 메모리 사용량(heap/non-heap, pool 별)을 직접 출력. ajax 없음.

### 5.2 팝업 대체
* `ei/eiLogList.jsp` (라인 766~767), `secs/secsLogList.jsp` (라인 687) 에서 구버전 `textDetailPop.do` 는 주석 처리되고
  `textAreaPop.do` 로 대체되었다. 새 팝업은 row 별 textarea 를 동적 append 하여 다건 표시 가능.

### 5.3 `tot/` catch-all 컨트롤러 흡수 대상
* JSP 에서 호출하는 다음 URL 들은 `tot/{query}` catch-all 매핑으로 `TotalLogController` 류에 흡수될 가능성이 있다 (백엔드 명세서 02-tot, 04-totNew 참조):
  - `filter/ajax/getCommMsgNameList.do`, `getOperationNameList.do`, `getMessageNameList.do`, `getProcessList.do`, `getSelectProcessList.do`

### 5.4 `paging.jsp` vs `slickGridPager.jsp`
* `paging.jsp` 는 어떤 JSP 에서도 `<c:import>` 또는 `include` 로 직접 참조되지 않는다 (전수 grep 결과). **사용되지 않는 leftover** 로 추정.
* 실제 사용되는 페이저는 `slickGridPager.jsp` 1종이며, 16개 로그 리스트 JSP 가 `<c:import>` 로 포함한다.

### 5.5 errorPage.jsp 미연결 버튼
* `errorPage.jsp` 의 "이전 페이지", "Home" 버튼은 `href="#"` placeholder 로만 존재 — 실제 동작 없음.

### 5.6 보안 관점
* 3개 dashboard iframe 의 apikey(`db1d2335-49cf-e859-3519-1ca132922e38`) 가 JSP 정적 텍스트에 평문으로 노출.
* `monitoring.jsp` 는 인증/권한 검사 없이 JVM 메모리 상세를 노출하므로 운영 환경 노출 시 정보 누설 위험.

### 5.7 URL 컨텍스트 패스 처리
* 거의 모든 ajax 호출 URL 은 `<c:url value='...' />` 로 컨텍스트 경로를 prefix 한다.
* 예외(상대경로 사용): `filter/ajax/getProcessList.do`, `filter/ajax/getCommMsgNameList.do`, `filter/ajax/getOperationNameList.do`, `filter/ajax/getMessageNameList.do`, `filter/ajax/getSelectProcessList.do`.
  이 경우 현재 페이지(`/tot/totalLogList.do`, `/ei/eiLogList.do` 등)의 부모 경로 기준 상대 URL 로 해석된다.

### 5.8 SPA-스러운 탭 동작
* `tot/main.jsp` 가 SPA shell 역할. 모든 GNB/메뉴/breadcrumb 의 `movePage()` 는 페이지 reload 없이 ajax 로 partial HTML 을 받아 `#contentList` 에 동적 삽입하고 `tab_list` 에 탭을 추가한다.
* 각 partial JSP 는 `<c:out value="${param.uuid}" />` 으로 자신만의 UUID 를 갖고 grid/event handler 변수를 namespacing 한다.

---

## 부록 A. 컨트롤러 매핑 요약 (참고)

| Ajax URL | 추정 컨트롤러 |
|---|---|
| `/alarm/ajax/getAlarmReportLogList.do` | `AlarmController` |
| `/ei/ajax/getEiLogList.do`, `getEiQueryStop.do`, `getSecsQueryStop.do` | `EiController` |
| `/ei/pop/textAreaPop.do`, `textDetailPop.do` | `EiController` (popup) |
| `/secs/ajax/getsecsLogList.do` | `SecsController` |
| `/mat/ajax/getCarrierLocLogList.do` | `MaterialController` |
| `/res/ajax/getCraneLogList.do` 등 6종 | `ResourceController` |
| `/tran/ajax/getReturn*LogList.do`, `getTranJobHistoryDetail.do`, `getReasonList.do` | `TransportController` |
| `/tot/ajax/getTotalLogList.do`, `getTotalLogListStop.do`, `getLogDetail.do`, `getLogDetailGroup.do`, `getMachineList.do` | `TotalLogController` |
| `/totNew/ajax/totalNewLogList.do`, `getCarrierElapsed.do` | `TotalNewController` |
| `/tot/pop/machineNamePop.do`, `filterPop.do` | `TotalLogController` (popup view) |
| `/tran/pop/reasonPop.do` | `TransportController` (popup view) |
| `/common/pop/settingPop.do` | `CommonController` (popup view) |
| `filter/ajax/getProcessList.do` 등 5종 | catch-all `tot/{query}` (TotalLogController 추정) |
| `/tot/main`, `/tot/totalLogList.do`, `/totNew/totalNewLogList.do` 등 navigation | `TotalLogController`, `TotalNewController` |
| `/tot/dashboard/elapsedAnalysis.do`, `compressAnalysis.do`, `monitor.do` | `TotalLogController` (view → iframe JSP forward) |
| `/i18n.do` | i18n controller |

---

## 부록 B. 매핑 통계

* 대상 JSP/JSPF: **38개** (전수)
* API 호출 발견 건수(라인 단위 grep 매치): **234건** (`$.ajax`/`window.open`/`movePage`/`<a href javascript:movePage>`/`<c:import>`/`<iframe>`/`location.href` 포함)
* ajax(`$.ajax({})`) 호출 블록: **약 35개**
* 고유 ajax endpoint: **약 25개**
* 고유 페이지 이동 endpoint: **약 18개**
* 외부 iframe 임베드: **3건** (Logpresso 대시보드 3종)
* 공용 머신명 팝업 호출 화면: **14개**
* `slickGridPager.jsp` import 화면: **16개**
