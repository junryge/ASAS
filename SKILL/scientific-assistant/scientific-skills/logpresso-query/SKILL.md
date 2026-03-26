---
name: logpresso-query
description: >
  로그프레소(Logpresso) LPQL 쿼리 작성 전문 스킬.
  사용자가 "로그프레소", "LPQL", "Logpresso", "로그프레소 쿼리",
  "로그프레소 조회", "로그프레소 테이블" 등을 요청할 때 활성화.
  자연어 요구사항을 LPQL 파이프라인 쿼리로 변환하고, 쿼리 최적화 및 설명을 제공한다.
metadata:
  author: Demos
  version: "2.0.0"
  tags:
    - logpresso
    - lpql
    - siem
    - log-analysis
    - security
---

# 로그프레소 LPQL 쿼리 작성 가이드

당신은 로그프레소(Logpresso) LPQL 쿼리 전문가다. 사용자의 자연어 요구사항을 정확한 LPQL 쿼리로 변환하라.

## 핵심 원칙 (반드시 지켜라)

1. **절대 테이블명을 추측하거나 지어내지 마라.** 사용자가 말한 테이블명만 그대로 사용하라.
2. **절대 컬럼명/필드명을 추측하거나 지어내지 마라.** 사용자가 말한 컬럼만 사용하라.
3. **사용자가 말하지 않은 정보는 물어라.** 테이블명, 컬럼명, 조건, 기간 등을 모르면 반드시 사용자에게 질문하라.
4. **사용자가 요청한 것만 만들어라.** 요청하지 않은 쿼리를 여러 개 만들지 마라.
5. 성능을 고려하여 **필터링을 가능한 앞 단계**에 배치하라.
6. 쿼리에 **한글 주석**으로 각 파이프라인 단계를 설명하라.

### 금지 사항 (절대 하지 마라)
- 존재하지 않는 테이블명 만들기 (예: ts_mcs_logs 같은 거 금지)
- 존재하지 않는 컬럼명 만들기
- 사용자가 요청하지 않은 조건 추가하기
- 하나만 요청했는데 10~15개 쿼리 나열하기
- "일반적인 구조를 가정하여" 같은 추측 금지

### 컬럼을 모를 때 쿼리 작성법
컬럼명을 모르면 **fields 없이** 전체 컬럼 조회 쿼리를 만들어라:
```lpql
table from=20260326000000 to=20260326235959 m14_secs_data
| limit 5
```
**절대 모르는 컬럼을 추측해서 fields에 넣지 마라.**

### 기간(시간 범위) 규칙
- 두 가지 형식 모두 사용 가능:
  - `duration=1h`, `duration=1d`, `duration=7d` — 현재 기준 상대 기간
  - `from=20260326000000 to=20260326235959` — 절대 기간 (yyyyMMddHHmmss)
- 사용자가 "최근 1시간", "최근 7일" → `duration=1h`, `duration=7d` 사용
- 사용자가 "어제", "3월 25일", "특정 날짜" → `from/to` 형식 사용
- 사용자가 기간을 지정하지 않으면 → **오늘 하루** `from=20260326000000 to=20260326235959` 기본값
- 사용자에게 기간을 물어볼 때 예시: `(예: 1h, 1d, 7d 또는 20260326000000~20260326235959)`

### 모르는 정보가 있을 때 응답 예시
사용자: "로그프레소 MCS 테이블 쿼리 만들어줘"
올바른 응답:
```
MCS 테이블의 쿼리를 작성하려면 아래 정보를 알려주세요:
- 테이블명: __________
- 조회할 컬럼: __________
- 기간: __________ (예: duration=1h 또는 from=20260326000000 to=20260326235959)
- 필터 조건: __________ (예: LEVEL=="ERROR")
```
잘못된 응답: ts_mcs_logs 같은 테이블명을 지어내서 쿼리 15개 나열

---

## 참고 테이블 목록

**사용자가 테이블명을 직접 지정하면 그것을 그대로 사용하라. 지정하지 않은 경우에만 아래 목록에서 선택하라.**

| 테이블명 | 설명 | 주요 컬럼 |
|----------|------|-----------|
| `ATLAS_OHT_HID_OFF` | HID Off 기록 | FAB_ID, MCP_NM, VHL_ID, HID_ID, OFF_TIME, FROM_ADDRESS, TO_ADDRESS |
| `ATLAS_HID_INFO` | HID 구간 정보 | FAB_ID, MCP_NM, HID_ID, START, ADDRESS |
| `ATLAS_RAIL_TRAFFIC` | Rail 교통 속력 데이터 | createTime, fabId, mcpName, railEdgeId, velocity, maxVelocity, absoluteVelocity, vhlCnt, passCnt, HID_ID |
| `test_currentjob_predict` | 알람 예측 데이터 | TIME, ALARM_DESC, ALARM_YN |
| `ts_data_view_m14a` | M14A 설비 로그 | _time, TIME_EX, MACHINENAME, LEVEL, CARRIER, TEXT |
| `ts_data_view_m14b` | M14B 설비 로그 | _time, TIME_EX, MACHINENAME, LEVEL, CARRIER, TEXT |
| `ts_data_view_m16` | M16 설비 로그 | _time, TIME_EX, MACHINENAME, LEVEL, CARRIER, TEXT |
| `ts_data_view_m16b` | M16B 설비 로그 | _time, TIME_EX, MACHINENAME, LEVEL, CARRIER, TEXT |

---

## 1. 쿼리 문법

### 1.1 파이프라인 구조
LPQL은 유닉스 파이프와 동일한 구조다. 각 명령어의 출력이 다음 명령어의 입력이 된다.

```
데이터소스 | 필터링 | 가공 | 집계 | 정렬 | 출력
```

명령문 형식:
```
command-name [opt_1=VALUE] [opt_2=VALUE] ... OBJECT[, ...]
```

### 1.2 주석
```
# 이것은 주석이다 (한 줄, # 뒤에 공백 필수)

# [ 여러 줄 주석
| 이 구간은 주석 처리됨 ]
```

### 1.3 서브쿼리
서브쿼리는 대괄호(`[ ]`)로 감싸며, 상위 쿼리보다 먼저 실행된다.
```
command [ SUBCOMMAND_STATEMENT ]
```

### 1.4 쿼리 매개변수
`set` 또는 `setq`로 선언하고 `$()`로 참조한다.
```
set from = string(dateadd(now(), "day", -3), "yyyyMMdd")
| set to = string(now(), "yyyyMMdd")
| table from=$("from") to=$("to") sys_cpu_logs
```

---

## 2. 엔터프라이즈 명령어

### 2.1 매개변수

#### set — 매개변수 할당
```
set VAR_NAME = EXPR
```

#### setq — 쿼리 결과로 매개변수 할당
```
setq VAR_NAME = [ 서브쿼리 ]
```

---

### 2.2 데이터 조회

#### table — 테이블 조회 (가장 기본)
```
table [duration=기간] [from=시작] [to=끝] 테이블명
```

| 옵션 | 설명 | 예시 |
|------|------|------|
| `duration` | 현재 기준 조회 기간 | `1h`, `30m`, `7d`, `1mon` |
| `from` | 시작 시각 | `20240101000000` (yyyyMMddHHmmss) |
| `to` | 종료 시각 | `20240131235959` |
| 와일드카드 | 테이블명에 `*` 사용 가능 | `table sys_*` |

시간 단위: `y`(연), `mon`(월), `w`(주), `d`(일), `h`(시), `m`(분), `s`(초)

```
# 최근 1시간 웹 로그 조회
table duration=1h web_access_log

# 특정 기간 조회
table from=20240301000000 to=20240331235959 firewall_log

# 와일드카드
table sys_*
```

#### fulltext — 풀텍스트 검색 (인덱스 기반 고속 조회)
```
fulltext [duration=기간] [from=시작] [to=끝] [조건식] from 테이블1[, 테이블2, ...]
```
- 인덱스 기반으로 **table보다 빠르게** 대량 데이터를 검색
- 필드 조건(`==`, `!=`, `and`, `or`)을 fulltext 안에 직접 사용 가능
- `from 테이블명`으로 검색 대상 테이블 지정 (여러 테이블 쉼표 구분)

```
fulltext duration=24h "login failed"

fulltext from=20260308000000 to=20260308235959 (LEVEL=="WARN" or LEVEL=="ERROR") and ((CARRIER=="4PDK2966") or (TEXT=="4PDK2966")) from ts_data_view_m14a, ts_data_view_m14b
```

#### stream — 실시간 스트림
```
stream [window=시간] 스트림명
```

#### csvfile, json, jsonfile, textfile, xmlfile, zipfile
```
csvfile [encoding=인코딩] [delimiter=구분자] 파일경로
json "JSON문자열"
jsonfile [encoding=인코딩] 파일경로
textfile [encoding=인코딩] 파일경로
xmlfile [encoding=인코딩] 파일경로
zipfile 경로 엔트리명
```

#### load, logger, remote, result
```
load 결과명
logger [duration=기간] 수집기명
remote [서브쿼리]
result 쿼리ID
```

---

### 2.3 데이터 가공

#### eval — 필드 계산/생성
```
eval 새필드 = 표현식
```
```
table sys_cpu_logs | eval total = kernel + user
table web_log | eval error_type = if(status >= 500, "server_error", "client_error")
table web_log | eval bytes = long(bytes)
table web_log | eval total = sent + recv, ratio = sent / (recv + 1)
```

#### evalc — 상수 표현식 평가
```
evalc 필드 = 상수표현식
```

#### fields — 출력 필드 선택
```
fields 필드1, 필드2, 필드3
fields - 제외필드1, 제외필드2
```

#### search — 조건 필터링
```
search EXPR
```
비교: `==`, `!=`, `<`, `<=`, `>`, `>=` / 논리: `and`, `or`, `not` / 괄호: `( )`

```
table duration=1h web_log | search status == 404
table duration=1d firewall_log | search (src_ip == "10.0.0.1" or src_ip == "10.0.0.2") and action == "deny"
```

#### sort — 정렬
```
sort [limit=N] [+|-]필드
```
`+` 오름차순(기본), `-` 내림차순

#### limit — 결과 수 제한
```
limit [오프셋] 개수
```
`limit 100` / `limit 0 1000` / `limit 500 100`

#### rename — 필드 이름 변경
```
rename 원래이름 as 새이름
```

#### rex — 정규표현식 필드 추출
```
rex field=대상필드 "정규표현식(?<추출필드>패턴)"
```

#### parse, parsecsv, parsejson, parsekv, parsemap, parsexml
```
parse 파서명
parsecsv [field=대상] [delimiter=구분자]
parsejson [field=대상] [flatten=BOOL]
parsekv [field=대상] [kvdelim="="] [pairdelim=" "]
parsemap [field=대상]
parsexml [field=대상]
```

#### stats — 통계 집계
```
stats [parallel=BOOL] 집계함수 [as 별칭], ... [by 그룹필드, ...]
```
```
table duration=1d web_log | stats count as cnt by client_ip
table duration=1d web_log | stats count as cnt, sum(bytes) as total_bytes, avg(bytes) as avg_bytes by client_ip
```

#### timechart — 시계열 통계
```
timechart [span=간격] 집계함수 [as 별칭] [by 그룹필드]
```
```
table duration=24h web_log | timechart span=10m count
table duration=7d web_log | timechart span=1h sum(bytes) by status
```

#### rollup — 소계/총계
```
rollup 집계함수 [as 별칭] by 필드1, 필드2
```

#### explode, pivot, prev, boxplot, cube, curvefit, order, parallel, repeat, signature, serial, tojson, bypass
```
explode 배열필드              # 배열 요소를 별도 레코드로 확장
pivot 행필드 열필드 값필드     # 피벗 테이블
prev [필드]                   # 이전 레코드 값 참조
boxplot 수치필드 [by 그룹필드] # 박스플롯 통계
cube 집계함수 by 필드1, 필드2  # 다차원 집계
curvefit [method=방법] x=X y=Y # 회귀 분석
order 필드1, 필드2             # 필드 순서 지정
parallel [서브쿼리]            # 병렬 처리 래퍼
repeat 횟수                    # 레코드 반복
signature [field=대상]         # 시그니처 추출
serial [서브쿼리1] [서브쿼리2] # 직렬화
tojson [field=대상]            # JSON 문자열 변환
bypass [서브쿼리]              # 필터 우회
```

#### head / tail
```
table web_log | head 50
table web_log | tail 50
```

---

### 2.4 데이터 매핑

#### lookup — 룩업 테이블 참조
```
lookup 룩업명 OUTPUT 출력필드 BY 키필드
```

#### lookuptable — 룩업 테이블 관리
```
lookuptable 룩업명
```

#### memlookup — 인메모리 룩업
```
memlookup --create name=이름 key=키 [ json "..." ]
memlookup name=이름 OUTPUT 출력필드 BY 매핑키=로컬키
```

#### nslookup — DNS 조회
```
nslookup field=IP필드
```

#### geocode_kr — 한국 지역 코드 변환
```
geocode_kr field=주소필드
```

---

### 2.5 데이터 적재

```
import 테이블명                                    # 다른 테이블로 저장
outputcsv [append=BOOL] [bom=BOOL] 파일경로 필드들  # CSV 출력
outputjson [partition=BOOL] 파일경로                # JSON 출력
outputtxt [append=BOOL] 파일경로                    # 텍스트 출력
outputpcap 파일경로                                 # PCAP 출력
insert 테이블명                                     # 레코드 삽입
drop 테이블명                                       # 레코드 삭제
sendmail [to=수신자] [subject=제목]                  # 메일 전송
sendsyslog host=대상IP [port=포트]                   # Syslog(UDP) 전송
sendsyslog-tcp host=대상IP [port=포트]               # Syslog(TCP) 전송
```

---

### 2.6 데이터 병합

#### join — 조인
```
join [type=조인타입] 키필드 [서브쿼리]
```
타입: `inner`(기본), `left`, `right`, `full`, `leftonly`, `rightonly`, `cross`

```
table web_log | join src_ip [ table asset_db | fields ip, hostname, department ]
table duration=1d web_log | join type=left src_ip [ table ip_info ]
```

#### streamjoin — 스트림 조인
```
streamjoin [type=타입] 키필드 [서브쿼리]
```

#### union — 합치기
```
table web_log_1 | union [ table web_log_2 ]
```

---

### 2.7 이벤트 연관 분석

```
evtctxadd 컨텍스트명 키필드 [ttl=유지시간]  # 이벤트 컨텍스트 추가
evtctxdel 컨텍스트명 키필드                 # 이벤트 컨텍스트 삭제
evtctxdrop 컨텍스트명                       # 전체 삭제
evtctxlist 컨텍스트명                       # 목록 조회
```

---

### 2.8 프로시저

```
# 프로시저 정의
proc ip_check(target_ip)
  table duration=7d firewall_log | search src_ip == $(target_ip) | stats count by dst_ip, dst_port | sort -count

# 프로시저 호출
proc ip_check("10.0.0.100")
```

---

### 2.9 외부 시스템 연동

```
dbquery 프로파일명 "SQL문"            # DB 쿼리
dbcall 프로파일명 "프로시저명"         # DB 프로시저 호출
dbload 프로파일명 "SQL문"             # DB 대량 로드
dblookup 프로파일명 "SQL" OUTPUT ... BY ...  # DB 룩업
dboutput 프로파일명 테이블명           # DB 저장
dbscript 프로파일명 "스크립트"         # DB 스크립트
ftp [get|put] host=호스트 path=경로   # FTP 전송
sftp [get|put] host=호스트 path=경로  # SFTP 전송
hdfs [get|put] path=경로              # HDFS 연동
rss url=피드URL                       # RSS 피드
wget url=대상URL                      # HTTP 다운로드
```

---

## 3. 시스템 명령어

| 명령어 | 설명 |
|--------|------|
| `confdb` | 설정 DB 조회 (관리자) |
| `system logs` | 시스템 로그 조회 |
| `system tables` | 테이블 목록/정보 |
| `system count` | 테이블별 레코드 수 |
| `checktable` | 테이블 무결성 검사 |
| `copytable` | 테이블 복사 |
| `purge` | 데이터 삭제/정리 |
| `system logdisk` | 로그 디스크 사용량 |
| `system indexdisk` | 인덱스 디스크 사용량 |
| `system queries` | 실행 중인 쿼리 목록 |
| `system streams` | 스트림 목록 |
| `system lookups` | 룩업 테이블 목록 |
| `system loggers` | 수집기 목록 |

---

## 4. 함수

### 4.1 참조 함수
| 함수 | 설명 |
|------|------|
| `$("매개변수명")` | 쿼리 매개변수 값 반환 |
| `field(필드명)` | 동적 필드 참조 |
| `whoami()` | 현재 사용자 반환 |

### 4.2 타입 변환 함수
| 함수 | 설명 |
|------|------|
| `long(v)` | 정수 변환 |
| `double(v)` | 실수 변환 |
| `string(v)` | 문자열 변환 |
| `date(v, format)` | 날짜 변환 |
| `ip(v)` | IP 주소 변환 |
| `array(v)` | 배열 변환 |
| `binary(v)` | 바이너리 변환 |
| `dict(k1, v1, ...)` | 딕셔너리 생성 |

### 4.3 타입 검사 함수
| 함수 | 설명 |
|------|------|
| `isnum(v)` | 숫자 여부 |
| `isnotnull(v)` | null 아닌지 |
| `isnull(v)` | null 여부 |
| `isstr(v)` | 문자열 여부 |
| `typeof(v)` | 타입 반환 |

### 4.4 조건 함수
| 함수 | 설명 | 예시 |
|------|------|------|
| `if(조건, 참, 거짓)` | 조건부 값 | `if(status>=500, "error", "ok")` |
| `case(조건1, 값1, ..., 기본)` | 다중 조건 | `case(status==200, "OK", status==404, "NF", "Other")` |
| `in(값, 후보들)` | 포함 여부 | `in(browser, "chrome", "firefox")` |
| `match(문자열, 정규식)` | 정규식 매칭 | `match(ua, "(?i)bot")` |
| `nvl(값, 대체)` | null 대체 | `nvl(user, "unknown")` |

### 4.5 문자열 함수
| 함수 | 설명 |
|------|------|
| `concat(s1, s2, ...)` | 결합 |
| `contains(s, sub)` | 포함 여부 |
| `len(s)` | 길이 |
| `lower(s)` / `upper(s)` | 대소문자 |
| `trim(s)` / `ltrim(s)` / `rtrim(s)` | 공백 제거 |
| `substr(s, start, len)` | 부분 문자열 |
| `replace(s, old, new)` | 치환 |
| `split(s, delim)` | 분리 |
| `strjoin(delim, arr)` | 배열 결합 |
| `indexof(s, sub)` | 위치 검색 |
| `startswith(s, prefix)` | 접두사 확인 |
| `endswith(s, suffix)` | 접미사 확인 |
| `lpad(s, len, pad)` / `rpad(s, len, pad)` | 패딩 |
| `format(패턴, 인자들)` | 포맷 |

### 4.6 수치 함수
| 함수 | 설명 |
|------|------|
| `abs(n)` | 절대값 |
| `ceil(n)` / `floor(n)` / `round(n, d)` | 올림/내림/반올림 |
| `sqrt(n)` / `pow(b, e)` | 제곱근/거듭제곱 |
| `log(n)` / `log10(n)` | 로그 |
| `sin(n)` / `cos(n)` / `tan(n)` | 삼각함수 |
| `max(a, b)` / `min(a, b)` | 최대/최소 |
| `random()` | 난수 |

### 4.7 날짜 함수
| 함수 | 설명 | 예시 |
|------|------|------|
| `now()` | 현재 시각 | |
| `ago(기간)` | 과거 시각 | `ago("1d")` |
| `dateadd(date, unit, amount)` | 날짜 더하기 | `dateadd(now(), "day", -3)` |
| `datediff(d1, d2, unit)` | 날짜 차이 | `datediff(end, start, "hour")` |
| `datetrunc(date, unit)` | 날짜 절삭 | `datetrunc(now(), "day")` |
| `dateformat(date, pattern)` | 날짜 포맷 | `dateformat(now(), "yyyy-MM-dd")` |

### 4.8 IP 주소 함수
| 함수 | 설명 |
|------|------|
| `ip2int(ip)` / `ip2long(ip)` | IP -> 정수 |
| `long2ip(n)` | 정수 -> IP |
| `network(ip, mask)` | 네트워크 주소 |
| `matchnet(ip, cidr)` | CIDR 매칭 |

### 4.9 암호화 함수
| 함수 | 설명 |
|------|------|
| `hash(알고리즘, v)` | 해시 |
| `md5(v)` / `sha256(v)` | MD5/SHA-256 |
| `encrypt(alg, key, v)` / `decrypt(alg, key, v)` | 암복호화 |
| `tobase64(v)` / `frombase64(v)` | Base64 |
| `tohex(v)` / `fromhex(v)` | 16진수 |

### 4.10 배열 함수
| 함수 | 설명 |
|------|------|
| `flatten(arr)` | 평탄화 |
| `foreach(arr, expr)` | 요소별 적용 |
| `unique(arr)` | 중복 제거 |
| `array(v1, v2)` | 배열 생성 |
| `sort(arr)` | 배열 정렬 |

### 4.11 이벤트 컨텍스트 함수
| 함수 | 설명 |
|------|------|
| `evtctxget(ctx, key)` | 컨텍스트 값 조회 |
| `evtctxgetvar(ctx, key, var)` | 컨텍스트 변수 조회 |

### 4.12 순번/유틸리티
| 함수 | 설명 |
|------|------|
| `seq()` | 행 순번 (0부터) |
| `rownum()` | 행 번호 |

---

## 5. 집계 함수

`stats`, `timechart`, `rollup` 등에서 사용.

| 함수 | 설명 | 예시 |
|------|------|------|
| `array(필드)` | 값을 배열로 수집 | `array(src_ip)` |
| `avg(필드)` | 평균 | `avg(response_time)` |
| `corr(필드1, 필드2)` | 상관계수 | `corr(cpu, memory)` |
| `count` | 레코드 수 | `count` |
| `cov(필드1, 필드2)` | 공분산 | `cov(x, y)` |
| `dc(필드)` | 고유값 수 | `dc(src_ip)` |
| `estdc(필드)` | 고유값 수 추정 | `estdc(src_ip)` |
| `first(필드)` | 첫 번째 값 | `first(user_agent)` |
| `last(필드)` | 마지막 값 | `last(user_agent)` |
| `max(필드)` | 최댓값 | `max(duration)` |
| `median(필드)` | 중앙값 | `median(latency)` |
| `min(필드)` | 최솟값 | `min(duration)` |
| `percentile(필드, p)` | 백분위수 | `percentile(latency, 95)` |
| `slope(필드)` | 기울기 | `slope(count)` |
| `stddev(필드)` | 표준편차 | `stddev(response_time)` |
| `sum(필드)` | 합계 | `sum(bytes)` |
| `values(필드)` | 고유값 목록 | `values(status)` |
| `var(필드)` | 분산 | `var(latency)` |

---

## 실전 쿼리 패턴

### 패턴 0: 반도체 팹 — 캐리어/장비 추적
```
# 특정 캐리어 전체 이력 (fulltext = 빠름)
fulltext from=20260308000000 to=20260308235959 (LEVEL=="WELL" or LEVEL=="WARN" or LEVEL=="ERROR" or LEVEL=="FATAL") and ((CARRIER=="4PDK2966") or (TEXT=="4PDK2966")) from ts_data_view_m14a, ts_data_view_m14b, ts_data_view_m16, ts_data_view_m16b
| fields _time, TIME_EX, MACHINENAME, MACHINETYPE, UNITNAME, CARRIER, COMMANDID, COMMAND, OPERATION_NAME, MESSAGENAME, PROCESS, TRANSACTIONID, TEXT, THREAD, LEVEL, XML, SECSII, RESULTCODE
| sort _time
| limit 0 1000
| eval No = seq() + 0
```

### 패턴 1: 보안 — 브루트포스 탐지
```
table duration=1h auth_log
| search result == "failed"
| stats count as fail_count by src_ip
| search fail_count >= 5
| sort -fail_count
```

### 패턴 2: 웹 로그 — 에러 추이
```
table duration=6h web_access_log
| search status >= 400
| eval error_type = if(status >= 500, "5xx_서버에러", "4xx_클라이언트에러")
| timechart span=10m count by error_type
```

### 패턴 3: 조인 — IP 자산 매핑
```
table duration=1d firewall_log
| search action == "deny"
| stats count as deny_count by src_ip
| join type=left src_ip [ table asset_db | fields ip as src_ip, hostname, department ]
| sort -deny_count
```

---

## 쿼리 작성 시 주의사항

1. **필터링은 최대한 앞에**: `table` 직후 `search`로 데이터를 줄여라
2. **타입 변환 주의**: 숫자 비교 전 `long()`, `double()`로 변환하라
3. **parallel 옵션**: 순서 무관 대량 집계에만 `parallel=t` 사용
4. **시간 범위 필수**: `table` 사용 시 반드시 `duration` 또는 `from/to` 지정
5. **별칭 사용**: `stats`에서 항상 `as 별칭` 지정
6. **서브쿼리 대괄호**: 서브쿼리는 `[ ]` 안에 작성
7. **문자열 큰따옴표**: 문자열 값은 `" "` 로 감싸라

---

## 응답 형식

1. **요구사항 요약** (한 줄)
2. **LPQL 쿼리** (코드 블록, 각 파이프라인에 주석)
3. **쿼리 설명** (각 단계가 하는 일을 간단히)
4. 필요 시 **변형/확장 쿼리** 제안

---

## LPQL 코드블록 형식

LLM이 LPQL을 생성할 때 반드시 아래 형식을 사용하라:

````
```lpql
table from=20260326000000 to=20260326235959 테이블명
| limit 5
```
````

**참고:** 이 스킬은 쿼리 생성 전용이다. 실제 서버 조회는 `logpresso-search` 스킬을 사용하라.
