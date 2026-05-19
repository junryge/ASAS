# 01. common 패키지 문서

본 문서는 `src/main/java/com/skhynix/supply/common/` 하위 14개 파일에 대한 설명입니다. 모든 식별자는 영문 원형 그대로 두고, 설명은 한국어로 작성되어 있습니다.

대상 파일 (총 14개):

1. `common/Common.java`
2. `common/DBManager.java`
3. `common/EncryptTest.java`
4. `common/FabVo.java`
5. `common/MachineVo.java`
6. `common/McslogCommon.java`
7. `common/Paging.java`
8. `common/ThreadPool.java`
9. `common/connection/ConnectionInfo.java`
10. `common/connection/ConnectionInfoPool.java`
11. `common/enumLEVEL.java`
12. `common/enumTYPE.java`
13. `common/error/ExceptionControllerAdvice.java`
14. `common/logger/LoggerInterceptor.java`

---

## Common.java

- 파일 경로: `common/Common.java`
- 목적: MCSLOG 웹 애플리케이션 전반에서 사용되는 전역 상수(쿼리 키워드, 컬럼명, FAB/FAB-SITE 이름, Logpresso 테이블명 등)와 FAB Site 관련 유틸리티를 모아 둔 정적 클래스입니다. Locale 정보 조회와 세션 기반 FAB Site 선택 로직도 함께 보관합니다.

### 클래스 시그니처

```java
public class Common
```

### 주요 정적 상수 (대표 그룹만 발췌)

- 서버/버전 정보: `sSERVER`, `sFAB_SITE`, `sBUILD_VER ("1.92")`, `searchDelayTime (15000ms)`
- 문자/기호 상수: `CR`, `LF`, `sCRLF`, `sPipeLine`, `sDoubleQuotation`, `sComma`, `sCommaOrigin`, `sEquals`, `sEqual_1`, `sSpace`, `sLeftParenthesis`, `sRightParenthesis`, `sMinus`, `sUnderbar`, `sSlash`, `sAsterisk`, `sPlus`, `sEmpty`
- Logpresso 쿼리 키워드: `sParallel (" parallel=t")`, `sOrder`, `sAsc`, `sProc`, `sTable`, `sTable_From`, `sFulltext*`, `sSearch_0/1/not/in`, `sFulltext`, `sGetMachineQuery ("memlookup name=machine_list")`, `sAnd`, `sOr`, `sFields`, `sFrom*`, `sSort`, `sEval`
- 컬럼명 상수: `sALL`, `sACCESSMODE`, `sALARMID`, `sALARMCODE`, `sALARMTEXT`, `sBANNED`, `sBATCHTYPE`, `sLEVEL`, `sTRANSPORTFAB`, `sSOURCEFAB`, `sDESTFAB`, `sTYPE`, `sMACHINETYPE`, `sSOURCEMACHINETYPE`, `sSOURCEMACHINETYPE2`, `sDESTTYPE`, `sDESTTYPE2`, `sINOUTTYPE`, `sIDREADSTATE`, `sCRANENAME`, `sCONNECTIONSTATE`, `sCONTROLSTATE`, `sCURRENTMACHINENAME`, `sCURRENTUNITNAME`, `sCOMMAND`, `sCREATEUSER`, `sAREANAME`, `sSOURCEAREANAME`, `sSOURCEUNITNAME`, `sDESTAREANAME`, `sDESTUNITNAME`, `sBAYNAME`, `sBATCHID`, `sSOURCEBAYNAME`, `sDESTBAYNAME`, `sNOTDESIGNATED`, `sMACHINENAME`, `sDESTMACHINENAME`, `sSOURCEMACHINENAME`, `sSTATE`, `sFULLSTATE`, `sSHELFNAME`, `sSUBSTATE`, `sSTEPID`, `sPROCESSNAME`, `sPROCESSINGSTATE`, `sTRANSPORTCOMMANDID`, `sTRANSPORTAREANAME`, `sTRANSPORTBAYNAME`, `sTRANSPORTTYPE`, `sTRANSPORTTYPE2`, `sTRANSPORTMACHINENAME`, `sTRANSPORTUNITNAME`, `sTRANSFERPORTNAME`, `sTHREADNAME`, `sTRANSACTIONID`, `sGTXN_ID`, `sTRANSPORTJOBID`, `sTRANSPORTUNITACCESSIBLE`, `sTSCSTATE`, `sTIME_EX`, `s_TIME`, `sMESSAGENAME`, `sMANUAL`, `sMETHOD`, `sCOMMSGNAME`, `sCRANEAVAILABLE`, `sOPERATIONNAME`, `sOCCUPIED`, `sPORTNAME`, `sCARRIER`, `sCOMMANDID`, `sUNIT`, `sTEXT`, `sLOTID`, `sREASON`, `sVEHICLENAME`, `sPRIORITY`, `sPROCESSID`, `sDESCRIPTION`, `sFIXEDROUTE`, `sCOMPLETED`, `sCANCELED`, `sTRANS_JOBSTART`, `sTRANS_JOBEND`, `sKey`, `sXML`, `sSECS ("SECSII")`, `sRESULTCODE`, `sHOST`
- MACHINE TYPE: `sSTB`, `sSTOCKER`, `sCONVEYOR`, `sLIFTER`, `sOHT`, `sPROCESS`, `sINTERAILSEMITS`, `sRETICLE`, `sINTERLAYER`, `sPODZIPTOWER`, `sZIPTOWER`
- LEVEL: `sWELL`, `sWARN`, `sERROR`, `sDEBUG`, `sINFO`, `sFINE`, `sFATAL`, `sTIME`, `sRECV`, `sSEND`
- FAB SITE (final): `sFABSITE_IC`, `sFABSITE_M11`, `sFABSITE_M14`, `sFABSITE_M15`, `sFABSITE_C2`
- FAB(SHOPNAME): `sFAB_M11A/B`, `sFAB_M14A/B`, `sFAB_M15A/B`, `sFAB_M16A/B`, `sFAB_C2`, `sFAB_C2F`
- 테이블명 상수 (Site/Fab 별): `sTS_DATA_*`, `sTS_DATA_VIEW_*`, `sTS_TRANSPORT_*`, `sTS_ALARM_*`, `sTS_MATERIAL_*`, `sTS_RESOURCE_*`, `sTS_JOB_COMPLETED_*`, `sSECS_DATA_*`, `sEI_DATA_*`, `sCS_DATA_*`, `sDS_DATA_*` (M14A/B, M16A/B, M15A/B, M11A/B, C2, C2F 각각)
- 프로시저 호출 템플릿: `sFulltext_From_TRAN ("TRANS_JOB_HISTORY_FULLTEXT(%s, %s, %s)")`, `sTable_From_TRAN ("TRANS_JOB_HISTORY_DETAIL(%s, %s, %s)")`, `sCOMPLETED_CARRIER_FROM_TO`, `sCOMPLETED_CARRIER_FROM_TO_CARRIER`, `sCARRIER_STEP_ELAPSED_TIME`
- 메서드 식별 상수: `METHOD_INFO_CREATE_TRANSPORT_JOB_HISTORY`, `METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY`
- 런타임 리스트: `public static List<String> Levels`, `public static List<String> FabSites`

### static 초기화 블록

`spring/message-context.xml` 파일을 읽어 `defaultLocale="zh"` 가 포함되어 있으면 서버를 C2 사이트로 판정하고 `sSERVER`, `sFAB_SITE`를 `sFABSITE_C2`로 설정합니다. 그 외에는 기본값으로 `sFABSITE_IC`를 사용합니다. 그리고 `Levels`, `FabSites` 리스트를 초기화합니다.

### 메서드

```java
static List<String> getLevelList()
```
로그 레벨 문자열 리스트(`DEBUG`, `INFO`, `FINE`, `WELL`, `WARN`, `ERROR`, `FATAL`)를 생성하여 반환합니다(패키지-private).

```java
public static List<String> getFabSiteList(String server)
```
현재 서버가 C2가 아니면 `IC, M15, M11, C2` 전체를 반환하고, C2 서버면 `C2`만 반환합니다.

```java
public static String getFabSite(HttpServletRequest request)
```
세션에 저장된 `FAB_SITE` 속성을 반환하며, 비어 있으면 `Common.sFAB_SITE`로 초기화한 후 반환합니다. 사이드이펙트: 세션 attribute 수정.

```java
public static String setFabSite(HttpServletRequest request, String fabSite)
```
유효한 FAB Site인 경우 세션의 `FAB_SITE` 속성을 갱신하고 반환합니다. 유효하지 않으면 기존 값을 반환합니다.

```java
public static String getFabSite(String fab)
```
fab 이름(M14A/B, M15A/B, M11A/B, M16A/B, C2/C2F)을 받아 어느 FAB Site에 속하는지 판단해 반환합니다. (주의: 내부에서 `==` 비교가 사용되어 실제 동작은 의도와 다를 수 있음)

```java
public static List<String> getFabList(String menu, String fabSite)
```
화면에 표시할 FAB 목록을 menu(`alarm`, `mat`, `res`, `ei`, `cs`, `ds` vs 그 외)와 fabSite 별로 다르게 반환합니다.

```java
public static List<String> getBasicFabList(String menu, String fabSite)
```
화면 로딩 시 기본 체크되는 FAB 목록을 반환합니다.

```java
public static String getColumnFromFab(String fabSite, String fab)
```
주어진 fabSite/fab 조합에 따라 쿼리에 들어갈 `, "FABNAME"` 형식의 컬럼 표현 문자열을 반환합니다. (`switch`에 `break`가 없어 fall-through 가능성 있음)

```java
public static Locale getLocale()
```
Spring의 `LocaleContextHolder.getLocale()`을 그대로 반환합니다.

### 의존성

- `com.skhynix.supply.common.connection.ConnectionInfoPool` (classpath 경로 산출용)
- `org.springframework.context.i18n.LocaleContextHolder`
- `javax.servlet.http.HttpServletRequest` / `HttpSession`

---

## DBManager.java

- 파일 경로: `common/DBManager.java`
- 목적: Logpresso 서버에 접속하여 쿼리를 실행/취소하고 결과를 `List<Map>` 형태로 반환하는 매니저 클래스입니다. FAB Site 별로 서로 다른 접속 정보를 사용합니다.

### 클래스 시그니처

```java
public class DBManager
```

### 필드

| 필드명 | 타입 | 역할 |
| --- | --- | --- |
| `fabSite` | `String` | 대상 FAB Site |
| `connectionInfo` | `ConnectionInfo` | 풀에서 가져온 접속 정보 |
| `queryId` | `int` | Logpresso 쿼리 ID |
| `client` | `Logpresso` | Logpresso 클라이언트 |
| `log` | `static final Log` | 로깅 |
| `timer` | `static ScheduledThreadPoolExecutor` | 쿼리 타임아웃 취소용 스케줄러 (size=1) |

### 내부 클래스

```java
private static class Canceller implements Runnable
```
지정된 `Logpresso` 클라이언트의 `queryId`에 대해 `stopQuery`를 호출하는 Runnable. `Common.searchDelayTime` 이후 강제 취소에 사용됩니다.

### 메서드

```java
public DBManager(String fabSite)
```
`ConnectionInfoPool.getConnectionInfo(fabSite)`로 접속 정보를 가져오고 `fabSite`를 저장합니다.

```java
public List<Map> executeQuery(String queryStmt) throws Exception
```
- Logpresso에 접속(`getConnect`)하여 쿼리를 `createQuery` → `startQuery`로 실행합니다.
- `Canceller`를 `Common.searchDelayTime(15s)` 후 동작하도록 스케줄링하여 타임아웃을 강제합니다.
- `waitUntil`로 결과 대기 후, 상태가 `CANCELLED`가 아니면 최대 10000건 결과를 `subList`로 잘라 반환합니다.
- 종료 시 `removeQuery`, `client.close()`로 자원을 정리합니다.
- 사이드이펙트: 외부 Logpresso 서버 통신, 로그 출력, 스케줄러 사용.

```java
private Logpresso getConnect()
```
`connectionInfo.getHostPrimary()`로 우선 접속을 시도하고 실패 시 `getHostSecondary()`로 재시도합니다. ID/PW/Port는 `ConnectionInfo`에서 가져옵니다.

```java
public void executeQueryStop()
```
실행 중인 쿼리를 `stopQuery` → `removeQuery` → `close()`로 즉시 중단합니다.

### 외부 호출

- Logpresso 서버 (host, port=8888, ID=`mcslogApp`, PW=암호화 properties에서 로드)
- 쿼리는 호출자가 만든 Logpresso 쿼리 DSL 문자열(예: `table from=... to=... ts_data_m15 | search ...`)

### 의존성

- `com.logpresso.client.Logpresso`, `com.logpresso.client.Query`
- `ConnectionInfo`, `ConnectionInfoPool`
- `Common.searchDelayTime`

---

## EncryptTest.java

- 파일 경로: `common/EncryptTest.java`
- 목적: Jasypt `StandardPBEStringEncryptor`를 이용한 암/복호화 동작을 확인하는 단순 main 테스트 유틸리티입니다(운영 코드 아님).

### 클래스 시그니처

```java
public class EncryptTest
```

### 메서드

```java
public static void main(String[] args)
```
- 알고리즘 `PBEWithMD5AndDES`, 비밀번호 `"bngSys"`로 `StandardPBEStringEncryptor`를 초기화.
- 평문 `"10.192.227.59"`를 암호화하여 출력하고, 그 결과 및 사전 정의된 암호문 `"vqCjqeMHr6xCDeSjzjhAxmTIS7GLJc6r"`를 복호화하여 출력합니다.
- 사이드이펙트: 표준 출력. 예외는 `catch`만 하고 무시.

### 의존성

- `org.jasypt.encryption.pbe.StandardPBEStringEncryptor`

---

## FabVo.java

- 파일 경로: `common/FabVo.java`
- 목적: FAB Site 정보를 화면-컨트롤러 간 전달하는 단순 VO. (2022.6.16 X0122410 추가)

### 클래스 시그니처

```java
public class FabVo
```

### 필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `menu` | `String` | 현재 화면 메뉴 식별자 |
| `fabSite` | `String` | 선택된 FAB Site (IC/M11/M14/M15/C2 등) |

### 메서드

`getFabSite()`, `setFabSite(String)`, `getMenu()`, `setMenu(String)` — 표준 getter/setter.

---

## MachineVo.java

- 파일 경로: `common/MachineVo.java`
- 목적: Machine 관련 화면에서 필터 조건(타입, FAB, Area, Bay 등)을 전달하는 VO.

### 클래스 시그니처

```java
public class MachineVo
```

### 필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `fabSite` | `String` | FAB Site 코드 (2022.6.15 추가) |
| `machineType` | `List<String>` | 머신 타입 옵션 목록 |
| `selectFab` | `List<String>` | 선택된 FAB 목록 |
| `selectType` | `List<String>` | 선택된 타입 목록 (201223 hgJeon 추가) |
| `areaName` | `String` | Area 이름 |
| `bayName` | `String` | Bay 이름 |

### 메서드

각 필드에 대한 getter/setter를 모두 제공합니다.

---

## McslogCommon.java

- 파일 경로: `common/McslogCommon.java`
- 목적: `Common.java`의 이전 버전으로 추정되는 클래스로, **파일 전체가 주석 처리되어 있어 컴파일/실행되지 않는 사실상 비활성(deprecated) 파일**입니다. 과거 단일 FAB Site 운영 시 사용되던 상수/유틸 정의가 그대로 남아 있습니다.

### 현재 상태

- 모든 `package`/`import`/`class` 선언이 라인 주석(`//`)으로 처리됨.
- 같은 이름의 패키지에 `Common.java`가 활성 클래스로 존재하며, 본 파일의 내용은 그쪽으로 이관/대체된 것으로 보입니다.

### 참고용 원래 의도

- 상수 정의(서버/문자/컬럼/MACHINE TYPE/LEVEL/FAB/테이블), `getLevelList`, `getFabList`, `getBasicFabList`, `getColumnFromFab`, `getLocale`, `getFabABC`(주석)
- FAB_SITE 기본값을 빌드 시 코드로 토글(`sFABSITE_M11` 등)

### 결론

신규 개발 시에는 무시하고 **`Common.java`만 사용**하면 됩니다.

---

## Paging.java

- 파일 경로: `common/Paging.java`
- 목적: 게시판/리스트 페이지네이션 계산용 VO 겸 헬퍼 클래스. 전체 레코드 수와 현재 페이지에 따라 시작/끝/이전/다음 페이지 번호를 계산합니다.

### 클래스 시그니처

```java
public class Paging
```

### 상수/필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `nTotalCount` | `public static final int = 1000000` | 전체 row 수 상한 |
| `recordsPerPage` | `int` | 페이지당 레코드 수 |
| `firstPageNo` | `int` | 첫 페이지 번호 |
| `prevPageNo` | `int` | 이전 페이지 번호 |
| `startPageNo` | `int` | 페이징 구간 시작 페이지 |
| `currentPageNo` | `int` | 현재 페이지 번호 |
| `endPageNo` | `int` | 페이징 구간 끝 페이지 |
| `nextPageNo` | `int` | 다음 페이지 번호 |
| `finalPageNo` | `int` | 마지막 페이지 번호 |
| `numberOfRecords` | `int` | 전체 레코드 수 |
| `sizeOfPage` | `int` | 한 번에 표시되는 페이지 갯수(기본 10) |

### 메서드

```java
public Paging(int currentPageNo, int recordsPerPage)
```
현재 페이지, 페이지당 레코드 수 초기화. `sizeOfPage=10`, `recordsPerPage`가 0이면 5로 보정.

표준 getter/setter:
- `getRecordsPerPage` / `setRecordsPerPage(int)`
- `getFirstPageNo` / `setFirstPageNo(int)`
- `getPrevPageNo` / `setPrevPageNo(int)`
- `getStartPageNo` / `setStartPageNo(int)`
- `getCurrentPageNo` / `setCurrentPageNo(int)`
- `getEndPageNo` / `setEndPageNo(int)`
- `getNextPageNo` / `setNextPageNo(int)`
- `getFinalPageNo` / `setFinalPageNo(int)`
- `getNumberOfRecords` / `setNumberOfRecords(int)`

```java
public void makePaging()
```
- `numberOfRecords`가 0이면 즉시 반환.
- `currentPageNo`/`recordsPerPage` 기본값 보정(각각 1, 10).
- `finalPage = (numberOfRecords + recordsPerPage - 1) / recordsPerPage` 로 계산.
- `startPage = ((currentPageNo-1)/sizeOfPage)*sizeOfPage + 1`, `endPage = startPage + sizeOfPage - 1` 로 표시 구간 결정.
- 첫/이전/다음/끝 페이지 번호를 setter로 채워 넣습니다.

---

## ThreadPool.java

- 파일 경로: `common/ThreadPool.java`
- 목적: 과거에 사용되었던 공용 스레드 풀(Singleton, `ThreadPoolExecutor` 기반) 구현으로, **현재 파일 전체가 주석 처리되어 비활성** 상태입니다.

### 현재 상태

- 모든 코드가 라인 주석 처리되어 컴파일/사용되지 않습니다.
- DB 쿼리 타임아웃은 `DBManager`가 자체적으로 `ScheduledThreadPoolExecutor`를 보유하므로 본 클래스는 더 이상 필요 없습니다.

### 참고용 원래 시그니처

- `getInstance()` (Singleton, init=15/max=15/min=15/idle=15)
- `execute(Runnable work)`, `close()`, `printStatus()`, `getThreadPoolStatus()`, `getIdleThreadCount()`

신규 개발 시 사용하지 않습니다.

---

## connection/ConnectionInfo.java

- 파일 경로: `common/connection/ConnectionInfo.java`
- 목적: Logpresso 접속 정보(Primary/Secondary 호스트, 포트, ID, PW)를 담는 단순 VO. setter는 패키지-private이라 같은 패키지의 `ConnectionInfoPool`만 채울 수 있습니다.

### 클래스 시그니처

```java
public class ConnectionInfo
```

### 필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `hostPrimary` | `String` | 1차 호스트 |
| `hostSecondary` | `String` | 2차(백업) 호스트 |
| `logpressoPort` | `int` | Logpresso 포트 (기본 8888) |
| `logpressoID` | `String` | 접속 계정 (`mcslogApp`) |
| `logpressoPW` | `String` | 접속 비밀번호 (Jasypt 복호화 결과) |

### 메서드

- `public final String getHostPrimary()`
- `public final String getHostSecondary()`
- `public final int getLogpressoPort()`
- `public final String getLogpressoID()`
- `public final String getLogpressoPW()`
- `final void setHostPrimary(String)` (package-private)
- `final void setHostSecondary(String)` (package-private)
- `final void setLogpressoPort(int)` (package-private)
- `final void setLogpressoID(String)` (package-private)
- `final void setLogpressoPW(String)` (package-private)

---

## connection/ConnectionInfoPool.java

- 파일 경로: `common/connection/ConnectionInfoPool.java`
- 목적: FAB Site별 `ConnectionInfo`를 캐시(`HashMap`)로 관리하고, `prop/connectionInfo.properties` 파일(암호화된 속성)에서 호스트/비밀번호를 로드하여 인스턴스를 생성합니다.

### 클래스 시그니처

```java
public class ConnectionInfoPool
```

### 정적 필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `ENCRYPT_KEY` | `static String` | `prop/connectionInfo.properties` 에 정의된 `db.encrypt_key` |
| `Property` | `static Properties` | `EncryptableProperties`로 복호화 가능한 속성 객체 |
| `Connections` | `static HashMap<String, ConnectionInfo>` | FAB Site → ConnectionInfo 캐시 |

### static 초기화 블록

`classpath` 루트에서 `prop/connectionInfo.properties`를 찾아 두 번 로드합니다:
1. 평문으로 로드해 `db.encrypt_key` 값을 추출.
2. 그 키로 `StandardPBEStringEncryptor` (`PBEWithMD5AndDES`)를 만든 후, `EncryptableProperties`로 다시 로드하여 ENC(...) 포맷의 암호화 값이 자동 복호화되도록 합니다.

### 메서드

```java
public static ConnectionInfo getConnectionInfo(String fabSite)
```
캐시에 없으면 `createConnectionInfo`를 호출해 신규 생성/저장 후 반환. **주의**: HashMap에 동기화가 없습니다.

```java
private static ConnectionInfo createConnectionInfo(String fabSite)
```
- 포트=8888, ID=`mcslogApp` 고정 설정.
- `getPropertyNames(fabSite)`로 매핑된 primary/secondary 프로퍼티 키를 얻어 `Property`에서 값을 읽어 `ConnectionInfo`에 채웁니다.
- `db.pw` 도 함께 읽어 비밀번호로 사용.

```java
private static String[] getPropertyNames(String fabSite)
```
FAB Site별 host property key 쌍을 반환:
- `IC` → `db.host_primary_ic`, `db.host_secondary_ic`
- `M11` → `db.host_primary_m11`, `db.host_secondary_m11`
- `M15` → `db.host_primary_m15`, `db.host_secondary_m15`
- `C2` → 서버가 C2가 아니면 방화벽 회피용 `db.host_third_c2` 양쪽으로, C2 서버면 `db.host_primary_c2/db.host_secondary_c2`
- 그 외 → 빈 배열

### 외부 자원

- `classes` 디렉터리와 같은 레벨의 `prop/connectionInfo.properties`
- Jasypt PBE 알고리즘 `PBEWithMD5AndDES`

---

## enumLEVEL.java

- 파일 경로: `common/enumLEVEL.java`
- 목적: 로그 레벨 문자열을 enum으로 표현. UI 드롭다운 등에서 사용.

### 시그니처

```java
public enum enumLEVEL
```

### 상수

`ALL("ALL")`, `DEBUG("DEBUG")`, `INFO("INFO")`, `FINE("FINE")`, `WELL("WELL")`, `WARN("WARN")`, `ERROR("ERROR")`, `FATAL("FATAL")`

### 메서드

- `enumLEVEL(String sLevel)` — 생성자(default 가시성)
- `public String getLEVEL()` — 내부 문자열 반환

---

## enumTYPE.java

- 파일 경로: `common/enumTYPE.java`
- 목적: 머신 타입 enum.

### 시그니처

```java
public enum enumTYPE
```

### 상수

`ALL("ALL")`, `STOCKER("STOCKER")`, `STB("STB")`, `LIFTER("LIFTER")`, `CONVEYOR("CONVEYOR")`, `PROCESS("PROCESS")`, `OHT("OHT")`

### 메서드

- `enumTYPE(String sType)` — 생성자
- `public String getTYPE()` — 내부 문자열 반환

---

## error/ExceptionControllerAdvice.java

- 파일 경로: `common/error/ExceptionControllerAdvice.java`
- 목적: 모든 컨트롤러에서 발생하는 `Exception`을 전역으로 받아 공통 에러 페이지(`common/error/errorPage`)로 포워딩하는 Spring 전역 예외 처리기.

### 어노테이션 / 시그니처

```java
@ControllerAdvice
public class ExceptionControllerAdvice
```

### 메서드

```java
@ExceptionHandler(Exception.class)
public ModelAndView exception(Exception e)
```
- `ModelAndView`에 `name`(예외 클래스 단순명)과 `message`(예외 메시지)를 담아 뷰 `common/error/errorPage`를 반환.
- 사이드이펙트: `e.printStackTrace()`로 콘솔에 스택 출력.

### 의존성

- `org.springframework.web.bind.annotation.ControllerAdvice`, `ExceptionHandler`
- `org.springframework.web.servlet.ModelAndView`

### 메타

- 작성일: 2017. 3. 14.
- 작성자: 박민호

---

## logger/LoggerInterceptor.java

- 파일 경로: `common/logger/LoggerInterceptor.java`
- 목적: 모든 컨트롤러 요청의 시작/종료 시점을 DEBUG 레벨로 로깅하는 Spring MVC `HandlerInterceptor`.

### 시그니처

```java
public class LoggerInterceptor extends HandlerInterceptorAdapter
```

### 필드

| 필드 | 타입 | 역할 |
| --- | --- | --- |
| `log` | `protected Log` | `LogFactory.getLog(LoggerInterceptor.class)` |

### 메서드

```java
@Override
public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception
```
DEBUG가 활성화되어 있으면 `START` 구분선과 `Request URI`를 출력하고, 부모 `preHandle`을 호출해 결과를 반환합니다.

```java
@Override
public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) throws Exception
```
DEBUG 활성 시 `END` 구분선을 출력합니다.

### 의존성

- `org.apache.commons.logging.Log/LogFactory`
- `org.springframework.web.servlet.handler.HandlerInterceptorAdapter`
- 별도 `@Component` 어노테이션은 없으며, Spring XML(`servlet-context.xml` 또는 dispatcher 설정) 의 `<mvc:interceptors>` 에 직접 등록되어 사용될 가능성이 높습니다.

---

## 관계도

```
[XML / Properties]
  spring/message-context.xml ──► Common (static init: server/site 판정)
  prop/connectionInfo.properties ──► ConnectionInfoPool (Jasypt 복호화)
                                        │
                                        ▼
                                  ConnectionInfo (Primary/Secondary host)
                                        │
                                        ▼
[Service 계층]              DBManager(fabSite) ──Logpresso── 외부 Logpresso 서버
        │                         ▲
        │  쿼리 문자열(Common.s* 사용) │
        ▼                         │
  각 도메인 Service (alarm/material/transport/...)
        │
        ▼
[Controller 계층]
  - HandlerInterceptor 로 LoggerInterceptor 가 모든 요청을 감싸 DEBUG 로깅
  - 예외 발생 시 ExceptionControllerAdvice 가 가로채 errorPage 로 포워딩
  - 화면 입력은 FabVo / MachineVo 로 바인딩
  - 결과 리스트는 Paging 으로 페이징 계산
  - 코드값 목록은 enumLEVEL / enumTYPE 사용
```

- `Common` 은 거의 모든 Service/Controller 에서 import 되어 쿼리 키워드·테이블명·FAB Site 판정에 사용됩니다.
- `DBManager` 는 각 Service 에서 `new DBManager(fabSite)` 형태로 생성되어 Logpresso 쿼리를 실행하며, `ConnectionInfoPool` 을 통해 환경별 접속 정보를 받습니다.
- `FabVo` / `MachineVo` 는 Controller `@ModelAttribute` 바인딩과 화면 ↔ Service 간 파라미터 전달용으로 사용됩니다.
- `Paging` 은 리스트 화면(Controller) 에서 결과를 잘라 페이징할 때 사용됩니다.
- `enumLEVEL`, `enumTYPE` 은 화면 드롭다운 옵션이나 필터 비교 시 코드값으로 사용됩니다.
- `LoggerInterceptor`, `ExceptionControllerAdvice` 는 Spring MVC 인프라 레벨에서 모든 컨트롤러를 감싸는 cross-cutting 컴포넌트입니다.
- `EncryptTest` 와 `McslogCommon`, `ThreadPool` 은 운영 코드 흐름에 포함되지 않는 보조/레거시 파일입니다(`McslogCommon`, `ThreadPool` 은 전체 주석 처리, `EncryptTest` 는 main 도구).
