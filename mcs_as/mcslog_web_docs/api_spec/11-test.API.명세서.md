# 11. test 모듈 API 명세서

> 대상 컨트롤러: `com.skhynix.supply.test.controller.TestController`
> 작성 기준 소스: `mcs_as/mcslog_web_src/src/main/java/com/skhynix/supply/test/controller/TestController.java`
> 공통 예외 처리: `com.skhynix.supply.common.error.ExceptionControllerAdvice`

---

## 1. API 개요

### 1.1 모듈 용도
`test` 모듈(`TestController`)은 SK hynix MCS Log 조회 시스템의 **개발 보조용(Test/Debug) 컨트롤러**입니다.
다음과 같은 개발 단계 점검 목적으로 작성되어 있습니다.

- 국제화(i18n) 메시지 리소스 동작 확인 (`/i18n.do`)
- 시스템 모니터링 화면 표시 (`/monitoring.do`)
- 임시 스크래치 화면 및 ThreadPool/Callable 비동기 로직 시험용 코드의 잔존 (`/tmp.do`)

소스 헤더 주석상 작성자는 "강병민"(2021-10-07)이며, 다른 업무 컨트롤러(`alarm`, `mat`, `res`, `secs`, `tot`, `tran` 등)와 달리 **`@RequestMapping` 어노테이션에 `method = RequestMethod.GET` 이 명시적으로 지정**되어 있다는 점이 특징입니다(타 컨트롤러는 method 명시 없이 매핑하는 패턴이 일반적).

### 1.2 운영 노출 위험 (중요)
- 본 모듈은 **개발/테스트 보조 용도**이며, 비즈니스 검증이나 권한 검사가 없습니다.
- 운영(PROD) 환경에 그대로 노출되면 다음과 같은 위험이 있습니다.
  - 인증 없이 누구나 `/i18n.do`, `/monitoring.do`, `/tmp.do` 호출 가능
  - `/tmp.do` 는 사실상 빈 JSP를 반환하는 dummy 엔드포인트로 정찰(reconnaissance)에 악용될 여지
  - `/monitoring.do` 가 시스템 상태/스레드 풀 등 내부 정보를 노출하는 화면일 경우 정보 유출 가능
- **운영 배포 시 라우팅 비활성화, 시큐리티 화이트리스트 제외, 또는 컨트롤러 자체를 빌드 프로파일(dev only)로 분리할 것을 강력히 권장**합니다.

---

## 2. API 목록

| No | HTTP Method | URL | 핸들러 메서드 | 반환(View) | 용도 |
|----|-------------|----------------------|---------------|--------------|--------------------------------|
| 1  | GET         | `/i18n.do`           | `i18n()`      | `i18n` (JSP) | i18n(다국어) 메시지 리소스 점검 |
| 2  | GET         | `/monitoring.do`     | `monitoring()`| `monitoring` (JSP) | 모니터링 화면 진입 |
| 3  | GET         | `/tmp.do`            | `tmp()`       | `tmp` (JSP)  | 임시/스크래치 화면 |

> `produces` 지정이 없으므로 응답 Content-Type 은 JSP 렌더링 결과(HTML, 보통 `text/html;charset=UTF-8`)입니다.
> JSON 을 반환하는 엔드포인트는 없습니다.

---

## 3. 상세 API 명세

### 3.1 `/i18n.do` — 국제화 메시지 리소스 점검

#### 3.1.1 Request

- **URL**: `/i18n.do`
- **HTTP Method**: `GET` (명시적으로 `RequestMethod.GET` 지정)
- **Headers**: 특별한 요구 헤더 없음. `Accept-Language` 헤더가 있을 경우 Spring `Locale` 객체에 반영됨.
- **Request Parameters / Path Variables**: 없음.

**Request Elements (메서드 시그니처)**

| 파라미터 | 타입 | 출처 | 설명 |
|----------|------|------|------|
| `locale` | `java.util.Locale` | Spring `RequestMappingHandler` (자동 주입) | 클라이언트 Locale |
| `request` | `HttpServletRequest` | Servlet 컨테이너 | 요청 객체. `SessionLocaleResolver` 로 세션 로케일 해석에 사용 |
| `model` | `org.springframework.ui.Model` | Spring | JSP 전달용 Model |

**curl 예시**

```bash
curl -X GET 'http://<HOST>:<PORT>/<CONTEXT>/i18n.do' \
     -H 'Accept-Language: ko-KR'
```

#### 3.1.2 Response

- **반환 형식**: JSP View Name `"i18n"` (→ `/WEB-INF/views/i18n.jsp` 렌더링)
- **응답 Content-Type**: `text/html` (JSP 디폴트)
- **HTTP Status**: 정상 시 `200 OK`

**Model 전달 키**

| 키 | 값 산출 방식 | 설명 |
|----|--------------|------|
| `siteCount` | `messageSource.getMessage("msg.first", null, locale)` | 메시지 프로퍼티 `msg.first` 값 |
| `siteLang`  | `Common.getLocale()` | 시스템 공통 `Common` 유틸이 반환하는 현재 로케일 |

**부수 효과 (로그 출력)**

핸들러는 다음 정보를 SLF4J/Apache Commons Logging 으로 출력합니다.

- `Welcome i18n! The client locale is {locale}.`
- `Session locale is {sessionLocale}.`
- `site.title : {messageSource.getMessage("site.title", ...)}`
- `site.count : {messageSource.getMessage("site.count", new String[]{"첫번째"}, ...)}`
- `not.exist : {messageSource.getMessage("not.exist", null, "default text", locale)}` (존재하지 않는 키의 기본값 처리 확인용)

#### 3.1.3 Error

- 컨트롤러 내 명시적 `try/catch` 없음.
- 모든 미처리 예외는 공통 `ExceptionControllerAdvice#exception(Exception e)` 으로 위임.
  - View: `common/error/errorPage`
  - Model: `name`(예외 클래스 SimpleName), `message`(예외 메시지)
  - 스택트레이스는 서버 로그에 `printStackTrace()` 됨.

#### 3.1.4 Examples

요청:
```http
GET /i18n.do HTTP/1.1
Host: localhost:8080
Accept-Language: ko-KR
```

응답(개념):
```http
HTTP/1.1 200 OK
Content-Type: text/html;charset=UTF-8

<!-- i18n.jsp 렌더링 결과 (siteCount, siteLang 활용) -->
```

---

### 3.2 `/monitoring.do` — 모니터링 화면 진입

#### 3.2.1 Request

- **URL**: `/monitoring.do`
- **HTTP Method**: `GET` (명시적 `RequestMethod.GET`)
- **Headers**: 특별한 요구 헤더 없음.
- **Request Parameters / Path Variables**: 없음.

**Request Elements (메서드 시그니처)**

| 파라미터 | 타입 | 출처 | 설명 |
|----------|------|------|------|
| `locale`  | `Locale` | Spring | 클라이언트 Locale (실제 핸들러 내부 사용 안 됨) |
| `request` | `HttpServletRequest` | Servlet | 요청 객체 (실제 핸들러 내부 사용 안 됨) |
| `model`   | `Model` | Spring | Model (실제 핸들러 내부 사용 안 됨) |

> 시그니처 상 파라미터는 주입받지만, **핸들러 본문은 단순히 view name 만 반환**합니다.

**curl 예시**

```bash
curl -X GET 'http://<HOST>:<PORT>/<CONTEXT>/monitoring.do'
```

#### 3.2.2 Response

- **반환 형식**: JSP View Name `"monitoring"` (→ `/WEB-INF/views/monitoring.jsp` 렌더링)
- **Model 전달 키**: 없음 (컨트롤러에서 `model.addAttribute` 호출 없음). 단, JSP 내부에서 자체 화면을 구성할 수 있음.
- **HTTP Status**: 정상 시 `200 OK`

**부수 효과 (로그 출력)**

- `monitoring : Start!!!`

#### 3.2.3 Error

- 컨트롤러 내 명시적 `try/catch` 없음.
- 미처리 예외는 공통 `ExceptionControllerAdvice` 가 `common/error/errorPage` 로 포워딩.

#### 3.2.4 Examples

요청:
```http
GET /monitoring.do HTTP/1.1
Host: localhost:8080
```

응답(개념):
```http
HTTP/1.1 200 OK
Content-Type: text/html;charset=UTF-8

<!-- monitoring.jsp 렌더링 결과 -->
```

---

### 3.3 `/tmp.do` — 임시/스크래치 화면

#### 3.3.1 Request

- **URL**: `/tmp.do`
- **HTTP Method**: `GET` (명시적 `RequestMethod.GET`)
- **Headers**: 특별한 요구 헤더 없음.
- **Request Parameters / Path Variables**: 없음.

**Request Elements (메서드 시그니처)**

| 파라미터 | 타입 | 출처 | 설명 |
|----------|------|------|------|
| `locale`  | `Locale` | Spring | 사용되지 않음 |
| `request` | `HttpServletRequest` | Servlet | 사용되지 않음 (주석 처리된 ThreadPool 시험 코드가 사용했던 흔적만 존재) |
| `model`   | `Model` | Spring | 사용되지 않음 |

> 핸들러 본문에는 **`ThreadPool.getInstance().executor.submit(Callable<List<Map>>)` 형태의 비동기 작업 20회 실행 시험 코드가 주석 처리되어 잔존**합니다. 현재는 빈 동작.

**curl 예시**

```bash
curl -X GET 'http://<HOST>:<PORT>/<CONTEXT>/tmp.do'
```

#### 3.3.2 Response

- **반환 형식**: JSP View Name `"tmp"` (→ `/WEB-INF/views/tmp.jsp` 렌더링)
- **Model 전달 키**: 없음 (컨트롤러에서 `model.addAttribute` 호출 없음).
- **HTTP Status**: 정상 시 `200 OK`
- **실질 응답 내용**: 거의 빈 JSP. 사실상 dummy.

**부수 효과 (로그 출력)**

- `tmp : Start!!!`

#### 3.3.3 Error

- 컨트롤러 내 명시적 `try/catch` 없음.
- 미처리 예외는 공통 `ExceptionControllerAdvice` 가 `common/error/errorPage` 로 포워딩.
- (주석 코드 한정) 과거 ThreadPool 비동기 작업의 `future.get()` 예외는 `return null;` 로 처리되어 있어 NPE 위험이 있던 흔적 존재.

#### 3.3.4 Examples

요청:
```http
GET /tmp.do HTTP/1.1
Host: localhost:8080
```

응답(개념):
```http
HTTP/1.1 200 OK
Content-Type: text/html;charset=UTF-8

<!-- tmp.jsp 렌더링 결과 (거의 비어있음) -->
```

---

## 4. 자원 모델 (VO / DTO)

**VO 없음.**

- `TestController` 의 어떤 핸들러도 도메인 VO/DTO 를 파라미터 또는 응답으로 사용하지 않습니다.
- 서비스 계층(`@Autowired` Service) 의존성도 없으며, 주입받는 빈은 다음 두 가지로 한정됩니다.
  - `SessionLocaleResolver localeResolver`
  - `MessageSource messageSource`
- 응답은 모두 JSP View 이름(`String`) 반환.

---

## 5. 인증 및 권한

- `TestController` 자체에는 `@PreAuthorize`, `@Secured`, Spring Security 관련 어노테이션이 **전혀 없습니다**.
- 별도 인터셉터/필터 설정이 없는 한 **익명 접근이 가능**합니다.
- 본 모듈은 테스트/디버깅 목적이며, **운영 환경에서는 다음 중 하나의 조치를 적용할 것을 권장**합니다.
  1. URL 패턴(`/i18n.do`, `/monitoring.do`, `/tmp.do`) 을 운영 시큐리티 정책에서 차단(403/404).
  2. `@Profile("dev")` 또는 빌드 프로파일(dev only)로 분리하여 운영 빌드에서 제외.
  3. 컨트롤러 자체를 운영 배포 산출물에서 제거.

---

## 6. 비고 / 이슈

### 6.1 운영 노출 위험 재확인
- 인증/인가 없음 → 익명 호출 가능.
- 정찰성 페이지(`/tmp.do`, `/monitoring.do`)는 시스템 내부 정보 단서가 될 수 있음.
- 로그에 메시지 리소스 키 다수가 출력되어 운영 로그 노이즈 유발 가능.

### 6.2 빈/스크래치 페이지 경로
- `/WEB-INF/views/tmp.jsp` — 11 라인 가량의 거의 빈 JSP (dummy).
- `/WEB-INF/views/i18n.jsp` — 26 라인 가량. 메시지 리소스 점검용.
- `/WEB-INF/views/monitoring.jsp` — 125 라인 가량. 실제 모니터링 화면.

### 6.3 코드 품질 이슈
- `private static final org.slf4j.Logger logger = LoggerFactory.getLogger(TotalController.class);`
  - **`TestController` 인데 `TotalController.class` 로 로거가 잡혀 있음 → 로그 카테고리 오류**.
  - 운영 로그 추적 시 `TotalController` 로 식별되어 혼선을 줄 수 있음. 수정 권장.
- 두 가지 로깅 API(Apache Commons Logging `Log` 와 SLF4J `Logger`)가 **동일 클래스에서 혼용**되고 있음.
- `/tmp.do` 핸들러에 **대량 주석 처리된 ThreadPool/Callable 시험 코드 잔존** → 정리 권장.
- 타 컨트롤러는 `method` 명시 없이 매핑하지만, 본 컨트롤러는 모두 `RequestMethod.GET` 을 명시 → 일관성 차원에서 검토 가능.

### 6.4 예외 처리 위임
- 본 컨트롤러는 자체 예외 처리를 하지 않으므로, 모든 예외는 전역 `ExceptionControllerAdvice` 가 처리.
- 동작:
  ```java
  @ExceptionHandler(Exception.class)
  public ModelAndView exception(Exception e) {
      ModelAndView mav = new ModelAndView();
      mav.addObject("name", e.getClass().getSimpleName());
      mav.addObject("message", e.getMessage());
      e.printStackTrace();
      mav.setViewName("common/error/errorPage");
      return mav;
  }
  ```
- View: `common/error/errorPage`, Model 키: `name`, `message`.

### 6.5 결론
- `TestController` 는 운영 가치보다는 개발 편의 코드이며, **운영 빌드에서는 제거 또는 비활성**이 안전합니다.
- 잔존 시 최소한 시큐리티 화이트리스트에서 제외하고, 로거 카테고리 오류와 주석 코드 정리를 함께 권장합니다.
