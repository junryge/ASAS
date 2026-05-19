# 09. 설정 파일 (Config)

## 빌드/배포 메모

이 프로젝트는 **Spring MVC 4.2 + MyBatis + Apache Tiles 3 + 다국어(i18n) + DBCP2 데이터소스** 기반의 Java 웹 애플리케이션(`spotlight-music` / `Sk하이닉스 MCSLog`)이다.

- 웹 컨테이너: Servlet 3.0 (`web.xml` 기준 `web-app_3_0.xsd`)
- DI/MVC: Spring 4.2 (root + DispatcherServlet 분리 컨텍스트)
- 뷰: JSP + Apache Tiles 3 (`org.springframework.web.servlet.view.tiles3.*`)
- 다국어: `ReloadableResourceBundleMessageSource` + `SessionLocaleResolver` + `LocaleChangeInterceptor(paramName="lang")`, 지원 로케일은 `ko / en / zh` 3종
- DataSource: `org.apache.commons.dbcp2.BasicDataSource` (commons-dbcp2 2.1.1). 별도로 JNDI(`jdbc/springDBPool`) 룩업도 정의돼 있으나 현재는 주석 처리(레퍼런스용)
- 환경 분리(profile separation): `connectionInfo.properties`(기본) / `connectionInfo-DEV.properties` / `connectionInfo-REAL.properties` 의 세 가지 환경별 DB 접속 정보 파일을 두며, 모든 호스트/비밀번호는 **Jasypt ENC(...) 암호화** 처리(키: `db.encrypt_key=bngSys`)
- 글로벌 인터셉터: `com.skhynix.supply.common.logger.LoggerInterceptor` (`/**` 매핑)
- 컴포넌트 스캔 기준 패키지: `com.skhynix.supply.*`

---

## 데이터소스

### 1) `src/main/resources/datasource/dbcpdatasource.properties`

**용도**: 로컬 개발용 MySQL 접속 정보 및 DBCP2 커넥션 풀 파라미터를 정의한다. `dbcpdatasource.xml`에서 `<context:property-placeholder>` 로 로드된다.

| Key | Value |
|---|---|
| `db.driverClassName` | `com.mysql.jdbc.Driver` |
| `db.url` | `jdbc:mysql://localhost:3306/spotlight?useSSL=true` |
| `db.username` | `spotlight` |
| `db.password` | `***` (원본은 8자리 평문, 마스킹 처리) |
| `db.initialSize` | `5` |
| `db.maxTotal` | `10` |
| `db.maxIdle` | `3` |

> 경고: 비밀번호가 평문으로 저장돼 있어 운영 배포 전 외부화/암호화가 필요하다.

### 2) `src/main/resources/datasource/dbcpdatasource.xml`

**용도**: Apache Commons DBCP2 의 `BasicDataSource` 빈을 정의한다. 위 `.properties` 값을 placeholder로 주입한다.

- 네임스페이스: `beans`, `context`
- 빈
  - `(context:property-placeholder)` location = `classpath:/datasource/dbcpdatasource.properties`
  - `dataSource` : `org.apache.commons.dbcp2.BasicDataSource`, `destroy-method="close"`
    - 프로퍼티: `driverClassName / url / username / password / initialSize / maxTotal / maxIdle`

### 3) `src/main/resources/datasource/dbcpdatasource_jndi.xml`

**용도**: JNDI 룩업 방식의 DataSource 설정 샘플(전 영역 주석). WAS(Tomcat/JBoss/WebLogic 등) 의 `context.xml`에 등록된 `jdbc/springDBPool` 을 가져오는 방법을 레퍼런스로 보관한다.

- 네임스페이스: `beans`, `context`, `p`, `jee`
- 활성 빈: **없음** (모두 주석)
- 주석 내 권장 패턴
  - `<jee:jndi-lookup id="dataSource" jndi-name="jdbc/springDBPool" resource-ref="true" />`
  - 또는 `org.springframework.jndi.JndiObjectFactoryBean` 사용
- `web.xml` 에 동반되어야 할 `<resource-ref>` 예시 포함 (`res-ref-name = jdbc/springDBPool`)

> `root-context.xml` 에서 이 파일이 `import` 되지만 실제로는 빈이 정의되어 있지 않으므로 활성 DataSource는 `dbcpdatasource.xml`의 `dataSource` 빈만이다.

---

## web.xml

### `src/main/webapp/WEB-INF/web.xml`

**용도**: 서블릿 3.0 표준 웹 배포 디스크립터. 루트 Spring 컨텍스트, DispatcherServlet, 인코딩 필터, JNDI 리소스 참조를 정의한다.

- `display-name`: `spotlight-music`

- **Context Param**
  - `contextConfigLocation` :
    - `/WEB-INF/spring/root-context.xml`
    - `/WEB-INF/spring/message-context.xml`

- **Listener**
  - `org.springframework.web.context.ContextLoaderListener`

- **Servlet**
  - `appServlet` → `org.springframework.web.servlet.DispatcherServlet`
    - `contextConfigLocation` = `/WEB-INF/spring/appServlet/servlet-context.xml`
    - `load-on-startup = 1`
    - 매핑: `/`

- **Filter**
  - `CharacterEncodingFilter` : `org.springframework.web.filter.CharacterEncodingFilter`
    - `encoding = utf-8`, `forceEncoding = true`
    - 매핑: `/*`

- **Resource Ref**
  - `jdbc/springDBPool` (`javax.sql.DataSource`, `Container` 인증) — JNDI 방식 사용 대비

- **Welcome Files / Error Pages**: 선언 없음 (Spring 컨트롤러 라우팅에 위임)

- **참고(주석)**: 정적 리소스용 default 서블릿 매핑(`*.css/*.js/...`) 블록이 주석으로 보관됨. 현재는 `servlet-context.xml`의 `<default-servlet-handler/>` + `<resources>` 가 대체.

---

## Spring Context

### 1) `src/main/webapp/WEB-INF/spring/root-context.xml`

**용도**: 비-MVC 영역의 공통 빈(트랜잭션, JDBC 템플릿, 메시지 리소스 번들, multipart, JSON 뷰)을 등록하는 루트 ApplicationContext.

- 네임스페이스: `beans`, `tx`, `c`, `p`, `util`
- Imports
  - `classpath:/datasource/dbcpdatasource.xml`
  - `classpath:/datasource/dbcpdatasource_jndi.xml`
- 빈 목록
  - `transactionManager` : `DataSourceTransactionManager` (dataSource-ref=`dataSource`)
  - `<tx:annotation-driven transaction-manager="transactionManager"/>`
  - `jdbcTemplate` : `org.springframework.jdbc.core.JdbcTemplate`
  - `namedParamJdbcTemplate` : `NamedParameterJdbcTemplate`
  - `messageSource` : `ResourceBundleMessageSource`, basename = `messages/titleMessages`
  - `multipartResolver` : `CommonsMultipartResolver`
  - `jsonView` : `net.sf.json.spring.web.servlet.view.JsonView`
  - `beanNameResolver` : `BeanNameViewResolver`, `order=0` (JsonView 등 빈 이름 기반 뷰 우선)

> 참고: MyBatis SqlSessionFactory 빈은 이 XML에는 보이지 않는다(별도 모듈/스캐너로 구성됐을 가능성). MyBatis Mapper 빈은 컴포넌트 스캔 또는 별도 설정으로 동작한다.

### 2) `src/main/webapp/WEB-INF/spring/appServlet/servlet-context.xml`

**용도**: DispatcherServlet 전용 컨텍스트. 컴포넌트 스캔, 뷰 리졸버(JSP + Tiles), 정적 리소스, 인터셉터, multipart 를 설정한다.

- 네임스페이스 기본: `mvc` (그 외 `beans`, `context`, `p`)
- 주요 요소
  - `<annotation-driven />`
  - `<resources mapping="/resources/**" location="/resources/" />`
  - `<context:component-scan base-package="com.skhynix.supply.*" />`
  - `<view-controller>` 2건
    - path `tot/main` → view `main`
    - path `tot/index` → view `index`
  - `<default-servlet-handler/>`
- 빈
  - `multipartResolver` : `CommonsMultipartResolver`
    - `maxUploadSize = 1099511627776` (1 TiB)
    - `maxInMemorySize = 1048576` (1 MiB)
  - `InternalResourceViewResolver` (익명) : prefix `/WEB-INF/views/`, suffix `.jsp`
  - `tilesViewResolver` : `UrlBasedViewResolver` → `TilesView`, `order=1`
  - `tilesConfigurer` : `TilesConfigurer`, definitions = `/WEB-INF/tiles/tiles-layout.xml`
- 인터셉터
  - `LoggerInterceptor` (`com.skhynix.supply.common.logger.LoggerInterceptor`), 매핑 `/**`
  - `localeChangeInterceptor` : `LocaleChangeInterceptor`, paramName=`lang` (※ `<interceptor>` 블록 외부에서 `<beans:bean>`만 선언돼 있어 인터셉터 체인에 등록되지 않을 가능성이 있음 — 확인 권장)

### 3) `src/main/webapp/WEB-INF/spring/message-context.xml`

**용도**: 다국어 메시지 소스 및 로케일 리졸버(기본값 zh) 설정. `web.xml`의 루트 ContextLoaderListener 가 로드한다.

- Imports: `dbcpdatasource.xml`, `dbcpdatasource_jndi.xml`
- 빈
  - `messageSource` : `ReloadableResourceBundleMessageSource`
    - basenames: `/WEB-INF/messages/message`
    - `defaultEncoding=UTF-8`
    - `cacheSeconds=60`
  - `localeResolver` : `SessionLocaleResolver`
    - `defaultLocale = zh`

### 4) `src/main/webapp/WEB-INF/spring/message-context-ko.xml`

**용도**: 위 `message-context.xml`과 동일하지만 `defaultLocale = ko` 인 한국어 기본 변종. 배포 환경별 교체 사용을 가정.

- 빈 구성은 `message-context.xml` 과 동일
- 차이: `localeResolver.defaultLocale = ko`

### 5) `src/main/webapp/WEB-INF/spring/message-context-zh.xml`

**용도**: 중국어 기본 변종. 내용은 `message-context.xml` 과 동일(이미 `defaultLocale=zh`)하여 별칭/백업 역할.

- 차이: `localeResolver.defaultLocale = zh`

> 운영에서는 사이트별로 위 3개 message-context*.xml 중 하나를 `web.xml`의 `contextConfigLocation` 에 지정해 기본 로케일을 결정한다. 사용자는 `?lang=ko|en|zh` 파라미터로 세션 로케일 변경(LocaleChangeInterceptor) 가능.

---

## i18n 메시지

i18n 동작 방식
- 메시지 번들: `WEB-INF/messages/message[_<locale>].properties`
- 로딩 빈: `ReloadableResourceBundleMessageSource` (UTF-8, 60초 캐시)
- 로케일 결정: `SessionLocaleResolver` (기본 ko 또는 zh — 사이트별 message-context*.xml 선택)
- 로케일 변경: 모든 요청에서 `?lang=` 파라미터로 변경 가능(`LocaleChangeInterceptor`)

각 파일은 모두 동일한 키 셋(약 **45개 키 + 빈 줄 포함 57라인**)을 가지며 값만 언어별로 다르다.

| 파일 | 경로 | 키 개수 | 비고 |
|---|---|---|---|
| `message.properties` | `WEB-INF/messages/message.properties` | 45 | 디폴트 폴백 (값은 ko와 동일) |
| `message_ko.properties` | `WEB-INF/messages/message_ko.properties` | 45 | 한국어 |
| `message_en.properties` | `WEB-INF/messages/message_en.properties` | 45 | 영어 |
| `message_zh.properties` | `WEB-INF/messages/message_zh.properties` | 45 | 중국어 슬롯 — **실제 내용은 영어와 동일** (zh 번역 누락) |

키 카테고리
- 사이트 타이틀: `site`, `site.count`, `msg.first`
- 공통 버튼/UI: `site.common.button.* (home/prev/next/popupclose/close/apply/help)`, `site.common.count`, `site.common.page`, `site.common.page.prev`, `site.common.filter`, `site.common.summary.desc01`, `site.common.error.msg01`
- 도움말: `site.common.help.msg01 ~ msg07`
- 로그 메뉴: `site.logList`, `site.eiLogList`, `site.alarmReportLogList`, `site.carrierLocLogList`, `site.craneLogList`, `site.machineLogList`, `site.portLogList`, `site.shelfLogList`, `site.storageLogList`, `site.vehicleLogList`, `site.secsLogList`, `site.totalLogList`, `site.totalNewLogList`, `site.returnCmdFailLogList`, `site.returnCmdLogList`, `site.returnJobFailLogList`, `site.returnJobLogList`, `site.returnLogList`
- 헤더/대시보드: `site.header.dashboard`, `site.header.dashboard.elapsedAnalysis`, `site.header.dashboard.compressAnalysis`, `site.header.dashboard.monitor`, `site.header.tot.totalLogList`
- 에러 페이지: `site.errorPage`, `site.errorPage.description`, `site.errorPage.head01~03`, `site.errorPage.data01~03`

언어별 샘플 (대표 키)

| Key | ko | en | zh |
|---|---|---|---|
| `site` | `Sk하이닉스 MCSLog` | `SkHynix MCSLog` | `SkHynix MCSLog` |
| `site.count` | `개수: {0}` | `Count: {0}` | `Count: {0}` |
| `msg.first` | `첫번째` | `First` | `First` |
| `site.logList` | `로그조회` | `LogView` | `LogView` |
| `site.header.dashboard` | `대시보드` | `Dashboard` | `Dashboard` |
| `site.errorPage` | `이용에 불편을 드려 죄송합니다.` | `We are sorry for the inconvenience.` | `We are sorry for the inconvenience.` |

> 이슈: `message_zh.properties` 가 `message_en.properties` 와 100% 동일하여 중국어 번역이 누락돼 있음. 또한 `site.errorPage.data03 = 02-1234-5678` 등 플레이스홀더(샘플) 값이 그대로 남아있음.

---

## 환경별 설정

세 파일 모두 Jasypt `ENC(...)` 로 암호화된 DB 호스트/비밀번호를 담는다. 복호화 마스터 키는 `db.encrypt_key=bngSys` 로 동일하며, 환경별로 IC/M15 의 primary/secondary 호스트 암호문이 다르다 (m11, c2(wuxi)는 세 환경 동일).

키 목록(공통)
- `db.encrypt_key` (마스터 키)
- `db.host_primary_ic`, `db.host_secondary_ic` (IC 팹)
- `db.host_primary_m11`, `db.host_secondary_m11` (M11)
- `db.host_primary_m15`, `db.host_secondary_m15` (M15)
- `db.host_primary_c2`, `db.host_secondary_c2`, `db.host_third_c2` (Wuxi C2, 3대)
- `db.pw` (공통 DB 비밀번호, 암호화)

| Key | connectionInfo.properties | connectionInfo-DEV.properties | connectionInfo-REAL.properties |
|---|---|---|---|
| `db.encrypt_key` | `bngSys` | `bngSys` | `bngSys` |
| `db.host_primary_ic` | `ENC(***)` | `ENC(***)` (DEV 전용 값) | `ENC(***)` (기본과 동일) |
| `db.host_secondary_ic` | `ENC(***)` | `ENC(***)` (DEV 전용 값) | `ENC(***)` (기본과 동일) |
| `db.host_primary_m11` | `ENC(***)` | `ENC(***)` (3 환경 동일) | `ENC(***)` (3 환경 동일) |
| `db.host_secondary_m11` | `ENC(***)` | `ENC(***)` (3 환경 동일) | `ENC(***)` (3 환경 동일) |
| `db.host_primary_m15` | `ENC(***)` | `ENC(***)` (DEV 전용 값) | `ENC(***)` (REAL 전용 값) |
| `db.host_secondary_m15` | `ENC(***)` | `ENC(***)` (DEV 전용 값) | `ENC(***)` (REAL 전용 값) |
| `db.host_primary_c2` | `ENC(***)` | 동일 | 동일 |
| `db.host_secondary_c2` | `ENC(***)` | 동일 | 동일 |
| `db.host_third_c2` | `ENC(***)` | 동일 | 동일 |
| `db.pw` | `ENC(***)` | `ENC(***)` (동일) | `ENC(***)` (동일) |

> 모든 `ENC(...)` 토큰과 평문 마스터키는 보안상 문서에서 마스킹(***)으로 표기했다. 원본 파일은 그대로 보존됨. 운영 배포 시 마스터키(`bngSys`)를 환경변수/시크릿 매니저로 외부화하는 것을 권장.

> 환경 전환 방식: 빌드/배포 시 `connectionInfo-DEV.properties` 또는 `connectionInfo-REAL.properties` 를 `connectionInfo.properties` 로 치환(또는 우선순위 로드)하여 적용한다.

---

## Tiles 레이아웃

### `src/main/webapp/WEB-INF/tiles/tiles-layout.xml`

**용도**: Apache Tiles 정의. `servlet-context.xml`의 `tilesConfigurer` 에서 로드된다.

- DTD: Tiles Configuration 2.0 PUBLIC, SYSTEM 경로는 환경별 절대/상대 path 후보가 주석으로 남아있음 (`deploy/tiles-config_2_0.dtd`, `deploy/mcslog/...`, `deploy/M15/...`, `deploy/plan/WEB-INF/dtd/...`, `deploy/M14/...`, `deploy/DEV/...`). 현재 활성: `"deploy/tiles-config_2_0.dtd"`.
- 참조 DTD 파일: `src/main/webapp/WEB-INF/dtd/tiles-config_2_0.dtd` (Apache Tiles 표준 DTD, 본 문서에서는 deep-dive 생략)

정의된 Tile

| name | template | put-attribute |
|---|---|---|
| `default` | `/WEB-INF/views/layouts/layout.jsp` | `header = /WEB-INF/views/layouts/header.jsp`, `body = ""`, `footer = ""` |
| `tot/main` | (extends `default`) | `body = /WEB-INF/views/tot/main.jsp` |

> 컨트롤러/뷰컨트롤러에서 반환되는 뷰 이름이 위 정의 이름과 일치하면 `TilesView`(order=1) 가 우선 매핑하고, 일치하지 않으면 `InternalResourceViewResolver` 가 `/WEB-INF/views/<name>.jsp` 로 폴백한다.
