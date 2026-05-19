# mcslog_web_src 코드 문서

SK hynix MCS(Material Control System) 로그 조회/분석 웹 애플리케이션의 소스 문서입니다.
원본 소스: `mcs_as/mcslog_web_src/src/main/`

## 한눈에 보기

- 빌드: Java EE Web App (Spring MVC 4.2)
- 패키지 루트: `com.skhynix.supply`
- 화면: JSP + Apache Tiles 3 + jQuery + SlickGrid
- DB 접근: 자체 작성한 `DBManager` (DBCP DataSource 기반, raw SQL 실행)
- 다국어: 한/영/중 메시지 번들 + LocaleChangeInterceptor
- 환경 분리: `connectionInfo-DEV.properties`, `connectionInfo-REAL.properties`

## 디렉터리 구조 (요약)

```
src/main/
├── java/com/skhynix/supply/
│   ├── alarm/   알람 리포트 로그
│   ├── common/  공통 유틸 (DB, 로깅, 예외, 풀)
│   ├── mat/     자재(캐리어 위치) 로그
│   ├── res/     자원 이력 (Crane/Machine/Port/Shelf/Storage/Vehicle)
│   ├── secs/    SECS / EI 통신 로그
│   ├── test/    개발용 테스트 컨트롤러
│   ├── tot/     통합 모니터링 / 분석
│   └── tran/    이송(Transfer) Cmd/Job 이력 및 실패
├── resources/datasource/   DBCP 데이터소스 설정
└── webapp/
    ├── WEB-INF/
    │   ├── views/   JSP 화면
    │   ├── spring/  Spring 설정
    │   ├── prop/    환경별 접속 정보
    │   ├── messages/ 다국어 메시지
    │   └── tiles/   Tiles 레이아웃
    ├── resources/   CSS/JS/이미지 (앱 자산)
    └── styles/      SlickGrid / jQuery UI 자산
```

## 문서 구성

| 파일 | 다루는 범위 |
|-----|-----|
| [00-architecture.md](00-architecture.md) | 전체 아키텍처, 요청 흐름, 레이어 책임 |
| [01-common.md](01-common.md) | `common/` 패키지 (DBManager, ConnectionInfoPool, 로거, 예외 등) |
| [02-alarm.md](02-alarm.md) | 알람 리포트 로그 모듈 |
| [03-mat.md](03-mat.md) | 자재(캐리어) 위치 로그 모듈 |
| [04-res.md](04-res.md) | 자원 이력 (6종) 모듈 |
| [05-secs.md](05-secs.md) | SECS / EI 통신 로그 모듈 |
| [06-tot.md](06-tot.md) | 통합 모니터링 / 분석 모듈 |
| [07-tran.md](07-tran.md) | 이송 명령/작업 이력 + 실패, 테스트 컨트롤러 |
| [08-views-jsp.md](08-views-jsp.md) | 모든 JSP/JSPF 화면 목록 및 역할 |
| [09-config.md](09-config.md) | web.xml, Spring XML, 데이터소스/메시지/환경 설정 |

## 모듈별 패턴

모든 비즈니스 모듈은 동일한 4-레이어 구조를 따릅니다.

```
Controller  →  Service (interface)  →  ServiceImpl  →  DAO  →  DBManager  →  DB
   (URL)         (계약)                (쿼리 조립)    (실행)   (커넥션)
```

- **Controller**: `@Controller` + `@RequestMapping`. 화면 진입, AJAX 응답(`ModelAndView`/JSON)
- **Service**: 인터페이스만 정의
- **ServiceImpl**: `@Service`. 쿼리 문자열을 직접 조립 (MyBatis 사용 안 함)
- **DAO**: `@Repository`. `DBManager`로 실행만 담당
- **VO**: 화면 ↔ 서비스 간 파라미터/결과 객체 (getter/setter)

## 빠르게 코드를 읽고 싶다면

1. `01-common.md` 의 `Common`, `DBManager`, `ConnectionInfoPool` 먼저
2. `02-alarm.md` 로 모듈 1개의 전체 흐름 파악
3. 나머지 모듈은 거의 동일한 패턴 — 차이점만 확인
