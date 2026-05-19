# 아키텍처 개요

## 시스템 정체성

**MCS Log 조회/분석 웹 애플리케이션** — SK hynix 반도체 팹 내 MCS(Material Control System)가 생성하는 대용량 로그를 운영자가 검색·모니터링·분석할 수 있는 사내 웹 도구.

조회 대상 로그는 자재 운반(이송 명령/작업), 자원(크레인·차량·포트·셸프·창고), SECS/EI 통신, 알람 등이며, 화면은 모두 "조건 검색 → 표 출력(SlickGrid)" 형태가 기본.

## 기술 스택

| 구분 | 사용 기술 |
|-----|---------|
| 언어/플랫폼 | Java EE, Servlet 3.0 |
| 프레임워크 | Spring MVC 4.2, Spring Tx |
| 뷰 | JSP + Apache Tiles 3 + JSTL |
| 프론트엔드 | jQuery, SlickGrid, jQuery UI, Semantic UI |
| 로그 검색 엔진(주 데이터 소스) | **Logpresso** (`com.logpresso.client.Logpresso`) |
| 보조 DataSource | Apache DBCP (`jdbc/springDBPool` JNDI) |
| 빌드/배포 | WAR (web.xml 기반) |
| 다국어 | 한/영/중 (`message_ko/en/zh.properties` + `LocaleChangeInterceptor`) |
| JSON | net.sf.json (`JsonView`) |
| 파일 업로드 | Commons FileUpload (최대 1TB) |

## 핵심 사실 — Logpresso 기반

**일반적인 JDBC/MyBatis 패턴이 아닙니다.** 비즈니스 데이터는 모두 Logpresso(로그 검색 엔진)에 적재되어 있고, 다음 경로로 조회합니다.

```
ServiceImpl
   │
   │ (1) 화면 검색 조건 → Logpresso 쿼리 문자열 조립
   │     예: "table mcslog FAB=M14 ALARMCODE=...  | search ...  | order ..."
   ▼
DAO.dbExecuteQuery(fabSite, queryStmt)
   │
   ▼
DBManager(fabSite)
   │
   │ (2) ConnectionInfoPool 에서 host/port/계정 조회
   │ (3) Logpresso.connect(primary) → 실패 시 secondary 폴백
   │ (4) createQuery → startQuery → waitUntil(limit) → getResult
   │ (5) Common.searchDelayTime(=15s) 후 자동 cancel 예약
   │
   ▼
List<Map> (rows)
```

- **쿼리 문자열은 ServiceImpl이 직접 String concat으로 조립**합니다. MyBatis Mapper XML 없음.
- **트랜잭션은 사실상 사용 안 함** (조회 전용). `tx:annotation-driven`은 선언만 되어 있음.
- **JDBC `dataSource` / `jdbcTemplate`** 빈은 root-context.xml에 선언되어 있으나 실제 사용처는 거의 없음 (메시지 컨텍스트 또는 일부 메타 조회용).
- **타임아웃**: 모든 쿼리는 `Common.searchDelayTime` (15초) 후 강제 취소.
- **결과 크기 상한**: `limit = 10000` (UI에서 조회 가능 최대 행수).

## 요청 처리 흐름

```
브라우저
   │
   │ HTTP GET/POST  /alarm/alarmReportLogList ...
   ▼
CharacterEncodingFilter (UTF-8 강제)
   │
   ▼
DispatcherServlet ("appServlet", url-pattern: /)
   │
   ├── LoggerInterceptor       (요청 진입/종료 로깅)
   └── LocaleChangeInterceptor (?lang=ko|en|zh 파라미터 처리)
   │
   ▼
Controller (@RequestMapping)
   │
   ├── 화면 진입 → ModelAndView → InternalResourceViewResolver / TilesViewResolver → JSP
   │
   └── AJAX 데이터 요청 → Service → DAO → DBManager(Logpresso) → JSON 응답
                                                                 (jsonView 또는 @ResponseBody)
```

## 뷰 해석 우선순위

1. `tilesViewResolver` (order=1) — Tiles 정의가 있는 view 이름 우선
2. `beanNameResolver` (order=0) → `jsonView` 빈 이름이 매칭되면 JSON 응답
3. `InternalResourceViewResolver` (default) — `/WEB-INF/views/{name}.jsp`

## 환경 분리

`webapp/WEB-INF/prop/` 아래 환경별 properties:

- `connectionInfo.properties` (베이스)
- `connectionInfo-DEV.properties` (개발)
- `connectionInfo-REAL.properties` (운영)

`ConnectionInfoPool`이 fabSite(M14 / M15 / M11 / C2 / IC)별 Logpresso 접속 정보를 로딩합니다. `Common.sFAB_SITE`(기본 "IC")가 디폴트 사이트.

## 레이어 책임 표

| 레이어 | 책임 | 안 하는 일 |
|------|----|----------|
| Controller | URL 매핑, 파라미터 바인딩, 화면 이름 또는 JSON 리턴 | 비즈니스 로직, 쿼리 조립 |
| Service (interface) | 메소드 시그니처 계약 | (구현 없음) |
| ServiceImpl | 검색 조건 검증, **Logpresso 쿼리 문자열 조립**, 결과 후가공 | DB 커넥션 관리 |
| DAO | `DBManager` 생성/실행/정리 | 쿼리 조립 |
| DBManager | Logpresso 연결, 쿼리 실행/취소, primary↔secondary 폴백 | 쿼리 의미 해석 |
| VO | 검색 조건/결과 행 데이터 | 검증 |

## 공통 인프라

- **Common.java** — 거대한 상수 모음 (200+ String 상수, 컬럼명/연산자/구분자). 쿼리 조립 시 자주 import됨.
- **ConnectionInfoPool** — fabSite별 `ConnectionInfo` 캐시.
- **LoggerInterceptor** — 모든 요청에 대해 진입/종료 로깅.
- **ExceptionControllerAdvice** — `@ControllerAdvice`로 전역 예외 → 에러 페이지.
- **Paging** — 페이지네이션 계산 유틸.
- **ThreadPool** — 비동기 쿼리 실행용 (현재 대부분 주석 처리 상태).

## 알아둘 만한 코딩 컨벤션 / 흔적

- 변경 이력 주석이 코드에 자주 박혀 있음 — 예: `// 2021. 3.31 X0122410 추가`
- 사번(X0122410, hgJeon 등)이 작성자 표기로 사용
- 한글 주석 활발 (영어 혼용)
- 일부 사소한 타이포가 운영 코드에 남아 있음 — 예: `MeterialServiceImpl` (Material 오타)
- `Common.sBUILD_VER = "1.92"` 로 빌드 버전 관리

## 보안 / 운영 메모

- 비밀번호류는 `connectionInfo*.properties`, `dbcpdatasource.properties` 에 평문. 외부 노출 금지.
- 모든 요청에 대해 UTF-8 강제 인코딩.
- 멀티파트 업로드 한도 1TB(`maxUploadSize=1099511627776`) — 비정상적으로 큼. 필요 시 축소 검토.
- 쿼리 자동 취소(15초)로 폭주 방지하나, 동시 사용자 폭주 시 Logpresso 부하 주의.
