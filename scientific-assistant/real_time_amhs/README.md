# AMHS Sentinel_M16BR — LLM 실시간 관제 (데모스와 완전 독립)

M16 HUBROOM 반송 정체를 로그프레소에서 실시간으로 읽어 **감지 → 케이스 → 에스컬레이션 →
리포트 → 피드백 학습** 까지 돌리는 독립 시스템.

> **독립성**: `demos_v1` 을 단 한 줄도 import 하지 않는다. 별도 프로세스·별도 포트(8989).
> 데모스가 죽어도 관제는 돈다. 반대도 마찬가지.
>
> **지식 출처**: 도메인 규칙을 이 폴더에 새로 쓰지 않는다.
> `../m16_hub_skills/` 의 **스킬 4종 + 페르소나**가 단일 출처이고, `llm_client.py` 는 로드해 주입만 한다.

---

## 빠른 시작

```bash
cd real_time_amhs
pip install -r requirements.txt      # requests, flask

# 1) 키 2개 넣기 (둘 다 이 폴더 안 — 데모스와 무관)
echo "<로그프레소 API 키>" > api_key.txt
echo "<GaiA LLM API 키>"   > token.txt

# 2) ★기본 점검 — 주소·키·접속·기본 테이블 한 번에
python lp_query.py --check

# 3) ★ 실제 컬럼 확인 (추측 금지 — 아래 '확인 필요' 참고)
python lp_query.py --schema
python lp_query.py --schema -t ATLAS_BOTTLENECK_ANOMALY
python lp_query.py --schema -t ATLAS_QUEUE_ANOMALY

# 4) ★데이터 확보 (관제 없이 수집만 — 먼저 이것부터)
python collect.py                  # 오늘 00:00 ~ 현재까지
python collect.py --date 20260727  # 그 날 하루치
python collect.py --loop           # 1분마다 계속 수집
python collect.py --list           # 확보된 날짜 목록

# 5) 관제 시작 — 켜면 오늘 하루치를 자동 확보하고 대시보드가 열린다
python server.py            # → http://localhost:8989/ 자동 오픈
                            #   외부(사내망)에서도 http://<이PC IP>:8989/ 로 접속
```

브라우저 자동 실행을 끄려면 `config.server.auto_open: false` 또는 `NO_BROWSER=1`.

사내망 밖(개발 PC)에서는 로그프레소에 닿지 않으므로 fixture 로 UI 를 볼 수 있다:

```bash
LP_OFFLINE=1 python server.py
```

---

## 데이터 출처 — 로그프레소 / 주피터 CSV

`config.json` 의 `source.mode` 로 고른다.

| mode | 받는 곳 | 비고 |
|---|---|---|
| `logpresso` (기본) | 로그프레소 + AMOS 2개 테이블 조인 | 90컬럼 |
| `jupyter` | 예측 잡이 떨궈 놓는 날짜별 발동이벤트 CSV | **143컬럼** — 룰별 점수(`*_pts_*`) 45개 포함 |

주피터 모드는 로그프레소를 아예 안 쓴다. 매 폴링마다 그 날짜 파일을 통째로
받아 넣되, 이미 있는 시각은 건너뛰므로 **증분 수집이 공짜로 된다** — 중간에
빠진 분도 다음 주기에 저절로 메워진다.

```bash
# ① 브라우저에서 복사한 URL 로 설정값 뽑기 (세션용 _xsrf 는 자동으로 떼어냄)
python jupyter_csv.py --url "http://…/predict_tobe/20260811_발동이벤트.csv?_xsrf=…"
#   → {"base_url": "http://…", "path": "/files/…/{day}_발동이벤트.csv"}

# ② config.json 의 source.mode 를 "jupyter" 로, 위 두 값을 넣는다
#    비밀번호는 셋 중 아무 데나 —
#      source.jupyter.password        (편함. 단 config.json 은 깃에 올라간다)
#      jupyter_password.txt           (.gitignore 됨)
#      환경변수 JUPYTER_PASSWORD

# ③ 접속·로그인 확인 (저장 안 함)
python jupyter_csv.py --check

# ④ 한 번 받아보기
python jupyter_csv.py 20260811
```

### 과거 채우기 (백필)

```bash
python jupyter_csv.py --backfill 30                  # 최근 30일
python jupyter_csv.py --backfill 20260801 20260811   # 그 구간
```

화면에서도 된다 — **과거 데이터 조회 탭 → `과거 채우기` 드롭다운**.

이미 저장된 날도 다시 받는다. 같은 시각은 건너뛰지만, **컬럼이 모자란 옛
파일은 이 참에 헤더가 넓어진다**. 파일이 없는 날(404)은 건너뛰고 계속한다.

### 컬럼이 늘어나면 파일을 넓힌다

로그프레소(90컬럼)로 만들어진 그날 파일에 주피터(143컬럼) 행이 들어오면
`_widen()` 이 헤더를 넓혀 파일을 다시 쓴다 (기존 행은 새 컬럼이 빈칸).
예전에는 `DictWriter(extrasaction="ignore")` 가 새 컬럼을 **아무 말 없이
버렸다** — 룰별 점수 45개가 통째로 사라진다. 확장하면 로그가 남는다.

```
[CSV] 🔧 컬럼 확장 90→143개 (20260812_TOTAL.CSV) — 새 컬럼 53개 stage, …
```

### 비밀번호·키는 저장소에 두지 않는다

`config.json` 은 깃에 올라간다. 비밀은 아래 두 곳 중 하나에 둔다 (`.gitignore` 됨).

```
real_time_amhs/token.txt               LLM(GAIA) API 키
real_time_amhs/api_key.txt             로그프레소 API 키
real_time_amhs/jupyter_password.txt    주피터 비밀번호
```

환경변수도 된다 — `GAIA_API_KEY` · `LP_API_KEY` · `JUPYTER_PASSWORD`.
코드는 **config → 키 파일 → 환경변수** 순으로 찾는다.

`tests/test_secrets.py` 가 이걸 강제한다. 실제로 두 번 새어 나가서 넣었다 —
`config.json` 에 직접 넣은 것 한 번, 그리고 **테스트용 가짜 서버의 기본값**에
딸려 들어간 것 한 번(`os.environ.get("MOCK_PW", "실제비번")` — 눈에 잘 안 띈다).
그래서 대입문만 보지 않고 **그 줄의 모든 문자열**을 본다. 걸리면 파일·줄번호만
알려주고 **값은 찍지 않는다** (실패 로그에 비밀이 남으면 안 되니까).

받은 원본은 `data/raw/{day}_발동이벤트.csv` 로 그대로 남는다 (파싱이 이상할 때
원본과 대조하려고). 화면 상단 표시도 `주피터 CSV` 로 바뀐다.

## 회귀 테스트 (설치 필요 없음)

실시간 관제라 조용히 망가지면 안 된다. **한 번 잡은 버그를 케이스로 박아둔다.**

```bash
cd real_time_amhs
python -m unittest discover -s tests -t .        # 83개, 0.3초, 네트워크·LLM 불필요
python -m unittest tests.test_reason -v          # 하나만 자세히
```

무엇을 지키는가 — 전부 실제로 화면에서 터졌던 것들이다.

| 파일 | 지키는 것 |
|---|---|
| `test_reason.py` | reason 원문(룰 코드·`역증가`·영문 컬럼)이 화면에 새지 않는다. 닫는 `]` 가 잘려 와도 한글 요약이 나온다. 실제지표 칸이 비지 않는다 |
| `test_llm_json.py` | 추론문 뒤에 붙은 JSON·잘린 JSON을 건져낸다. 산문을 JSON으로 받지 않는다. `response_format` 400이면 옵션을 빼며 재시도하되 `Invalid model name` 400은 바로 모델 교체. 503(nginx HTML)은 한 줄로 줄이고 일시장애로 분류 |
| `test_forecast.py` | 판정 규칙(`_decide`)이 실시간·채점 **양쪽에서 같다**. 스파이크 1분에 경보 안 나간다. 적중/오보/놓침을 정확히 센다. 다지표가 선행 시간을 늘리고 `require_for_warn` 이 오보를 줄인다 |
| `test_contrib.py` | 평소가 0인 지표(MAD 0)가 z 폭주로 100%를 먹지 않는다. 상시 포화를 스파이크와 구분한다. 화면에 '추정'임을 반드시 밝힌다 |
| `test_amos_block.py` | **2번 AMOS 표가 비어도 3번 수동 기입은 항상 있다.** 무관한 문서엔 안 붙는다. `amos_block.py` 와 데모스 `amos_report.py` 가 **같은 코드**인지 검사 |
| `test_text.py` | LLM 판단이 문장 중간에서 안 끊긴다. 일일 리포트에 원문이 안 샌다 |
| `test_secrets.py` | **저장소에 실제 비밀번호·키가 들어가면 실패한다.** config 의 비밀 칸이 비어 있는지, 키 파일이 `.gitignore` 됐는지도 검사 |
| `test_jupyter.py` | 주피터 로그인→내려받기→저장. 또 받아도 중복이 안 쌓인다. 143컬럼이 안 깎인다. **저장 폴더가 바뀌거나 파일이 지워져도 행을 조용히 버리지 않는다.** 컬럼이 늘면 파일을 넓힌다. 백필은 없는 날을 건너뛰고 계속한다 |

옛 버그를 일부러 되살려 그물이 실제로 잡는지 확인했다 (변이 5종 → 전부 FAILED).

## 구성

| 파일 | 역할 |
|---|---|
| `config.json` | 접속·정책·등급·평가주기 전부. **코드 수정 없이 여기만 고친다** |
| `api_key.txt` | 로그프레소 키 (직접 생성) |
| `token.txt` | LLM 키 (직접 생성). **데모스 TOKEN.TXT 와 무관 — 각자 관리** |
| `lp_client.py` | 로그프레소 HTTP 클라이언트 (`httpexport/query.csv`). 쓰기 쿼리 차단 |
| `lp_query.py` | LPQL 빌더 + CLI 조회 + **청크 분할 조회** + AMOS 2개 테이블 조인 |
| `sentinel.py` | 감지 → 케이스 생성/병합 → 등급 → 에스컬레이션 |
| `llm_client.py` | 스킬 4종 + 페르소나 주입 → LLM 판단·리포트 (+금지어 스크럽) |
| `report.py` | 구간 리포트 + 피드백 저장 → 임계치 자동 보정 |
| `server.py` | 독립 Flask + 폴링 스레드 + REST API + **대시보드 자동 실행** |
| `static/dashboard.html` | 관제 화면 (**오프닝 화면 없음** — 바로 진입) |
| `collect.py` | **데이터 확보** — 로그프레소 → 날짜 CSV (서버 없이 단독 실행) |
| `graphs.py` | **대시보드 구간 그래프 SVG** (다크) — 더블클릭 시 1시간 |
| `report_graphs.py` | **리포트 그래프** — `demos_v1/report_graphs.py` 독립 복사본 |
| `daily.py` | 하루 ③ 사건목록 · ④ AMOS 표 (스킬 발동이벤트_요약 과 같은 규칙) |
| `accuracy.py` | 1분 LLM 추론 + 사후검증 채점 + 빈 구간 메움 |
| `amos_block.py` | 리포트 인터랙티브 블록 — `demos_v1/amos_report.py` 독립 복사본 |
| `store_csv.py` | 날짜별 CSV 누적 저장 — `data/20260727_TOTAL.CSV` |
| `fixtures/` | 오프라인 검증용 샘플 (실제 스키마 아님) |

---

## 기본 조회 (이게 기본)

```
http://10.40.42.167:8888/logpresso/httpexport/query.csv?_apikey=<api_key.txt>&_q=<LPQL>
LPQL:  table from=... to=... test_table3 | sort _time
```

긴 구간은 **10분 청크로 끊어서** 조회하고, 한 청크가 **30MB를 넘으면 그 구간만 절반으로
재귀 분할**한 뒤 합친다 (로그프레소 export 가 대용량에서 끊기는 것 방지).

```bash
python lp_query.py --from 20260621000000 --to 20260621010101       # 청크 분할 자동
python lp_query.py --from ... --to ... --chunk-minutes 5           # 분할 단위 변경
python lp_query.py --recent 10m                                     # 최근 구간 단발
```

설정은 `config.query` — `chunk_minutes`(10), `max_bytes`(30MB), `sort_col`(`_time`),
`timeout_s`(300). 테이블에 `_time` 이 없으면 `sort_col` 을 `""` 로 비운다.

**전송은 `requests` 를 쓴다** (사내 스크립트와 동일 경로). 로그프레소 export 는
Content-Length 를 다 채우지 않고 끊는 경우가 있어 `urllib` 은 `IncompleteRead` 로
죽지만 `requests/urllib3` 은 견딘다. `requests` 가 없으면 urllib 로 폴백하되
끊긴 응답은 받은 만큼 살리고 잘린 마지막 행은 버린다.

API 키는 `api_key.txt` 또는 `config.json` 의 `"api_key"` 에 직접 넣어도 된다.

---

## 데이터 흐름

```
test_table3 (기존 데이터)
        +
ATLAS_BOTTLENECK_ANOMALY  ─┐  search MCP_NM == "BR"
ATLAS_QUEUE_ANOMALY       ─┘  EVENT_DT(분) 기준 조인
        ↓
두 테이블 모두 컬럼명이 downward_anomaly_cols / upward_anomaly_cols 로 같으므로
접두어를 붙여 구분해서 기본 데이터에 추가한다:

  ATLAS_BOTTLENECK_ANOMALY.downward_anomaly_cols → BOTTLENECK_downward_anomaly_cols
  ATLAS_BOTTLENECK_ANOMALY.upward_anomaly_cols   → BOTTLENECK_upward_anomaly_cols
  ATLAS_QUEUE_ANOMALY.downward_anomaly_cols      → QUEUE_downward_anomaly_cols
  ATLAS_QUEUE_ANOMALY.upward_anomaly_cols        → QUEUE_upward_anomaly_cols
        ↓
감지 (unified_risk_score ≥ 임계)
        ↓
케이스 (억제 창 내 같은 설비 = 같은 케이스)
        ↓
LLM 판단 / 구간 리포트  ← 스킬 4종
        ↓
피드백 → 임계치 보정 (다음 감지에 반영)
```

---

## 등급 · 심각도

스킬과 동일 기준. 50점 미만은 알람 없음(정상 운영).

| 점수 | 등급 | 심각도 표기 |
|---|---|---|
| 50 ~ 70 | 🟠 경계 | 경계/주의(확인필요) |
| 71 ~ 84 | 🔴 위험 | 위험/경고(모니터링 필요) |
| 85 ~ 100 | ⛔ 초위험 | 초위험/심각(조치필요) |

## 데이터 저장 (직접 열어볼 수 있게)

수집한 데이터는 **날짜별 CSV 에 한 줄씩 누적**된다. 기본 컬럼 + AMOS 4개 컬럼이 합쳐진 상태 그대로다.

```
data/20260727_TOTAL.CSV
```

· **`server.py` 를 켜면 오늘 하루치(00:00~현재)를 통째로 먼저 확보한다.**
  서버가 꺼져 있던 중간 구간까지 메운다. 이후는 1분마다 증분 수집.
  화면 '누적 데이터'의 `오늘 하루 다시 훑기` 버튼으로 언제든 다시 채울 수 있다.
  (긴 구간은 10분 청크로 안전하게 나눠 조회)
· 같은 시각은 다시 안 쓴다 (재수집 중복 방지)
· 화면 '누적 데이터'에서 목록 확인 · 내려받기 · 그 날 리포트 실행
· 리포트는 이 CSV 를 먼저 읽고, 없을 때만 로그프레소를 재조회한다

## 실시간 관제 · 과거 데이터 조회 · 리포트 (분리된 세 경로)

| | 실시간 관제 | 과거 데이터 조회 | 리포트 · 피드백 |
|---|---|---|---|
| 조회 | 최신 구간만 (`duration=`) | **저장된 CSV 를 날짜로** (`/api/feed?day=`) | **날짜로 직접 조회** (`from=/to=`) |
| 주기 | 수집 주기마다 자동 (기본 1분) | 날짜 고를 때 1회 | 사용자가 날짜/구간 지정 시 |
| 데이터 | 기본 + AMOS 4컬럼 | 기본 + AMOS 4컬럼 (동일) | 기본 + AMOS 4컬럼 (동일) |
| 판단 | 감지 즉시 **LLM 자동 판단** | 저장 당시 판단 결과 그대로 | 구간 요약 리포트 |
| 근거 | 실시간 케이스 저장소 | `data/YYYYMMDD_TOTAL.CSV` | 저장소와 무관 — 조회 결과로 새로 구성 |

**과거 데이터 조회** 탭은 실시간 관제와 화면이 완전히 같다 (같은 표·같은 등급 필터·
같은 스코어 추이 스트립·같은 더블클릭 그래프). 다른 점은 **보는 날짜**뿐이다.

**날짜만 고르면 된다.** 저장된 CSV 가 있으면 그걸 읽고, **없으면 그 자리에서 서버가
로그프레소로 그 날짜를 확보한 뒤 보여준다** (별도 버튼을 누를 필요 없다).

* 날짜 입력칸 — 아무 날짜나 고르면 위 흐름대로 동작. 탭을 열면 최신 저장 날짜가 기본
* 드롭다운 — 이미 저장된 날짜 빠른 선택 (행수까지 표시, `data/YYYYMMDD_TOTAL.CSV`)
* `다시 확보` — 저장본이 있어도 서버에서 새로 가져오기 (재수집)
* `CSV` — 그 날 원본 파일 내려받기
* 확보 중에는 날짜 컨트롤이 잠긴다 (하루치는 몇 분 걸릴 수 있다)
* 로그프레소에도 기록이 없는 날짜면 "데이터 없음"으로 끝난다 — 다른 날 데이터를
  대신 보여주지 않는다

## 하루 사건 리포트 (데모스 개인 에이전트와 같은 형식)

리포트 탭에서 날짜를 고르고 `사건 보고서 생성` — **데모스 개인 에이전트의
'사건발생 보고서' 와 같은 5섹션**이 나온다.

```
# 📅 2026년 7월 28일 M16 BR 반송 이벤트 발생 확인건
## 1. 한 줄 총평:등급(50~70 🟠 경계/ 71~84 🔴 위험 / 85~100 ⛔ 초위험)
## 2. AMOS 이상 감지 내역          ← 체크박스 표 (실제 발생여부 O/X · 작업 여부 O/X)
## 3. 실제 이상 발생내역            ← O 선택 시 행 자동 생성 (시/분 분리 · 원복시간)
## 4. 위험 이벤트 상세 분석 (도메인 세분화)
## 5. 에이전트 제안
```

* `daily.py` 가 저장된 날짜 CSV 에서 **③ 사건목록 · ④ AMOS 표**를 만든다 —
  `m16_hub_skills/발동이벤트_요약.py` 와 **같은 규칙**(점수 50+ · 간격 60분 ·
  시각=최고점 · HID 4개마다 줄바꿈 · 심각도 병기). 스킬을 import 하지 않고 규칙만 따른다
* 그 두 표만 근거로 LLM 이 보고서를 쓴다 (5섹션 형식은 `페르소나_통합.txt` [B] 사건단위)
* `보고서 창으로 열기` → `/api/report/day.html?date=YYYYMMDD` —
  체크박스 표·수동 기입·저장 툴바가 들어간 인터랙티브 HTML (별도 창)
* **그래프도 개인 에이전트와 똑같다** — `report_graphs.py`(데모스
  `demos_v1/report_graphs.py` 독립 복사본)를 `'사건단위'` 질의로 부른다.
  개인 에이전트 보고서와 **같은 경로**를 타서 사건들을 한 그래프에 담고
  사건 구간 음영·사건 라벨·최고점 라벨까지 같게 그린다.
  `<div class="hub-report-graph">` 로 나오므로 `amos_block` 이
  `4. 위험 이벤트 상세` 아래로 옮긴다
* 저장분이 없는 날짜면 그 날짜를 로그프레소에서 먼저 확보한다
* LLM 이 실패해도 같은 5섹션 골격이 통계로 나온다 (관제가 멈추면 안 되므로)

`amos_block.py` · `report_graphs.py` 는 데모스 `demos_v1/amos_report.py` ·
`demos_v1/report_graphs.py` 의 **독립 복사본**이다 (import 하지 않는다).
개인 에이전트 보고서와 표·그래프가 똑같아야 하므로 데모스 쪽을 고치면
이 파일들도 같이 맞춘다.

```bash
python daily.py 20260728     # ③ 사건목록 · ④ AMOS 표만 확인
```

## 1분 LLM 추론 + 판단 일치 (정탐률)

수집 루프가 1분마다 데이터를 가져올 때마다 **그 1분에 대해 LLM 이 판단**하고,
`data/YYYYMMDD_LLM.CSV` 에 **1분 1행**으로 남긴다. `TOTAL.CSV` 와 `datetime` 으로
그대로 조인된다 — 한 줄에 *그때 데이터 → LLM 이 뭐라 했나 → 결과가 어땠나* 가 다 있다.

```
로그프레소 조회 → AMOS 조인 → 20260729_TOTAL.CSV 1행
                              ↓
                        LLM 추론 (그 1분)
                              ↓
                    20260729_LLM.CSV 1행
                              ↓
              검증 창 찬 과거 행 채점 → 같은 행에 판정 기록
```

* 정상(50점 미만) 구간은 **짧게** 묻는다 (예/아니오 + 한 줄). 하루 1440번이라 낭비를 줄인다
* 경계 이상은 지금까지처럼 **상세히** (근거·조치까지)
* LLM 추론은 별도 스레드 — **수집 루프는 절대 밀리지 않는다.**
  이전 추론이 안 끝났으면 그 분은 건너뛰고 `오류=지연스킵` 으로 남긴다
* **빠진 분을 메운다** — 최신 분을 먼저 판단하고(실시간 우선), 남은 자리로 최근 과거부터
  거꾸로 채운다. 한 폴링당 `max_per_cycle`(기본 3)건. 폴링이 한 번 밀려도 그 분이
  영구히 비지 않는다
* 기동 전 구간(`_bootstrap_today` 가 수집한 00:00~기동시각)은 자동 판단 대상이 아니다.
  필요하면 `빈 구간 메움` 으로 채운다

### ★ 사고(think) 모델 주의

`gaia-Qwen3.5-*` 는 **사고 모델**이다. 그냥 부르면 `<think>` 안에서 추론만 하다
`max_tokens` 에 걸려 **본문이 빈 응답**으로 온다. 그러면 판단이 전부 비어
`실제이상` 이 안 채워지고 채점도 안 된다.

그래서 `config.llm.no_think: true` 가 기본이고, 마지막 user 메시지에 `/no_think` 를
주입한다 (데모스 `_inject_no_think_for_qwen3` 와 같은 방식).

**그런데 이 게이트웨이(`hcp.llm.skhynix.com`)는 `/no_think` 를 듣지 않는다.**
`<think>` 태그도 안 쓰고 `Thinking Process: 1. **Analyze the Request:** …` 처럼
**평문으로 추론을 먼저 쓴다.** 그러다 `max_tokens` 를 다 써서 JSON 까지 못 간다.

그래서 두 가지를 더 한다:

1. **JSON 프리필** (`per_minute.json_prefill: true`) — assistant 턴을 `{` 로 미리
   채워 보내면 모델이 그 뒤를 이어 쓴다. 추론을 건너뛰므로 **빠르고 안정적이다**
   (backfill 이 느렸던 원인도 이것)
2. **견고한 JSON 추출** — 균형 잡힌 `{…}` 덩어리를 **뒤에서부터** 시도하고,
   JSON 이 잘렸으면 정규식으로 `실제이상`·`확신도`·`판단` 만이라도 건져낸다
   (채점에 필요한 건 `실제이상` 한 칸이다)

| 응답 형태 | 결과 |
|---|---|
| 평문 추론 뒤에 JSON | ✅ 파싱 |
| ```json 코드펜스 | ✅ 파싱 |
| 프리필로 `{` 되붙인 형태 | ✅ 파싱 |
| 잘린 JSON | ✅ `실제이상` 건져냄 |
| 추론만 하고 JSON 없음 | ❌ 오류로 기록 (원인 표시) |

```bash
python llm_client.py --test     # 1분 판단과 같은 경로로 한 번 호출해 본다
```

`실제이상=예` 또는 `아니오` 가 나오면 정상. 안 나오면 오류 메시지에 원인이 찍힌다
(`본문 없는 응답 (finish_reason=length, max_tokens=400, 완료토큰=400)` 처럼).

| 설정 | 뜻 |
|---|---|
| `llm.no_think` | `/no_think` 주입 (기본 true). 사고 과정을 보려면 false + `max_tokens` 크게 |
| `llm.disable_thinking_kwarg` | 서버가 지원할 때만 true — `chat_template_kwargs.enable_thinking=false` 를 실어 보낸다 |
| `per_minute.light_max_tokens` | 정상 구간 응답 토큰 (기본 400) |
| `per_minute.full_max_tokens` | 경계 이상 응답 토큰 (기본 900) |

빈 응답은 **오류로 잡는다.** 예전엔 `_parse_json` 이 빈 텍스트를
`{"판단": "", "확신도": 0}` 으로 위장해 돌려줘서 '오류 없는 빈 판단' 이 CSV 에
쌓이고 원인을 찾을 수 없었다. 이제 `오류` 칸에 이유가 남는다.

### 채점 — 사후검증

LLM 을 다시 부르지 않는다. 저장된 `TOTAL.CSV` 의 분당 스코어만 읽어 판정한다.

| LLM `실제이상` | 판단 이후 창(20분) 안 실제 | 판정 |
|---|---|---|
| 예 | 임계(50점) 이상 **5분 연속 유지** or 등급 상승 | **적중** |
| 예 | 5분 안에 임계 아래로 회복 | **과다탐지** |
| 예 | 회복했지만 **운영자 조치 이력 있음** | **조치효과** (분모 제외) |
| 아니오 | 임계 넘어 5분 연속 | **누락** |
| 아니오 | 계속 임계 아래 | **적중** |

> ★ **이 값은 검증된 '정탐률'이 아니다.** LLM 판단이 이후 데이터 흐름과 일치했는지만 본다.
> 조치를 잘해서 빨리 풀린 건은 자동으로는 과다탐지로 보이므로 `조치효과` 로 빼고 분모에서 제외한다.
> 그래서 화면 이름도 **`LLM 판단 일치`** 이고, 사람이 눌러준 판정이 있으면 그게 최종이다.

### 화면

KPI 카드 `LLM 판단 일치` 를 **클릭하면 그 날 LLM CSV 내용이 그대로 뜬다.**

| 시각 | 점수 | 실제이상 | 확신도 | 판단 | 판정 | 판정근거 | 확인 |
|---|---|---|---|---|---|---|---|
| 08:05 | 41점 | 예 | 70% | 상승 추세 지속 | 적중 | 이후 9분 연속 50점 이상 유지 · 최고 88점 | 정탐 오탐 |
| 08:14 | 51점 | 예 | 80% | 리프터막힘 정체 | 과다탐지 | 5분 내 50점 아래로 회복 · 최고 44점 | 정탐 오탐 |
| 08:16 | 38점 | 아니오 | 60% | 회복 국면 | 적중 | 창 안 최고 31점 — 계속 50점 아래 | 정탐 오탐 |

* 날짜를 바꿔 과거 날짜의 판단도 볼 수 있고, CSV 원본을 내려받을 수 있다
* `채점 대기 17분` — LLM 판단은 끝났고 채점까지 남은 시간. **대기는 정상이다**
* `판정불가` — 채점할 수 없는 경우. 이유가 판정근거에 찍힌다
  (LLM 호출 실패 / '실제이상'을 예·아니오로 답하지 않음 / 검증 창 안에 수집 데이터 없음)
* `빈 구간 메움` — 수집은 됐는데 LLM 판단이 없는 분을 통째로 메운다.
  서버를 늦게 켰거나 오래 꺼져 있던 구간에 쓴다 (`python accuracy.py --backfill 20260729`)
* `정탐`/`오탐` 을 누르면 그게 최종 판정이 되어 자동 판정을 덮어쓴다
* 카드 숫자는 **표본 10건 전엔 퍼센트 대신 건수**(`적중 6 · 과다 2 · 누락 1`).
  어느 쪽으로 틀리는지가 보여야 임계를 올릴지 내릴지 판단할 수 있다

### config

```json
"llm": {
  "per_minute": { "enabled": true, "every_min": 1, "light_below": 50,
                  "skip_if_busy": true, "csv_suffix": "_LLM" },
  "accuracy":   { "enabled": true, "window_min": 20, "sustain_min": 5,
                  "recover_min": 5, "min_sample": 10, "floor": null }
}
```

| 값 | 뜻 |
|---|---|
| `every_min` | 1=매분 / 5=5분마다 / 0=끔(케이스 발생 시에만) |
| `light_below` | 이 점수 미만은 짧게 묻는다 |
| `window_min` | 검증 창(분) |
| `sustain_min` | 임계 이상이 이만큼 연속되면 '실제 이상이었다' |
| `recover_min` | 판단 직후 이 안에 회복되면 과다탐지 |
| `min_sample` | 이보다 적으면 퍼센트를 안 낸다 |

## 추이 스트립 (항상 보이는 그래프 · 지표 선택)

실시간 관제·과거 데이터 조회 두 탭 모두 표 위에 **하루치 추이**가 항상 떠 있다.
더블클릭할 필요 없이 계속 보인다.

**왼쪽 선택 상자로 볼 지표를 고른다. 기본은 스코어.**
값은 CSV 의 **실제 컬럼 값 그대로**이고, 화면에는 **AMOS 실제 컬럼명**이 같이 뜬다.
라벨·컬럼명은 `m16_hub_skills/발동이벤트_요약.py` 와 같은 표기를 쓴다.

```
M16HUB 리프터막힘 (회) [M16HUB.QUE.LFT.3F_LFT_REVERSALCNT]
M16HUB 반송시간 (분)  [M16HUB.QUE.TIME.AVGTOTALTIME1MIN]
M16A 소터대기 (건)    [M16A.SORTER.ABN.SORTERWAITCOUNTOVER]
```

* 스코어(`unified_risk_score`) — 0~100 고정, 등급 밴드(50/71/85), 경계 이상은 등급 색 점
* 나머지 지표 — 그 지표 값 범위에 맞춰 **자동 스케일**, 지표 고유 색
* 최고점 `▲6분` / `▲98.2%` 처럼 단위까지, 헤더에 `최고 … · 평균 …`
* X축 00:00~24:00 고정 — 아침부터 지금까지가 한눈에. 오늘이면 현재 시각 세로선
* 실시간 탭은 **수집 주기마다 다시 그린다** (등급 필터와 무관하게 항상 하루치 전체)
* 스트립을 **클릭하면 그 시각 구간 그래프**가 뜬다
* 실시간·과거 선택은 서로 독립 (한쪽을 바꿔도 다른 쪽은 그대로)

### 지표 묶음 — `AMOS 컬럼` / `CSV 컬럼` 버튼

선택 상자 왼쪽 버튼으로 **두 묶음을 갈아탄다.** 둘 다 값은 같은 CSV 에서 읽고,
**컬럼명 표기와 항목 구성만 다르다.**

| 묶음 | 표기 | 항목 |
|---|---|---|
| `AMOS 컬럼` (기본) | AMOS 실제 컬럼명 `M16HUB.QUE.LFT.3F_LFT_REVERSALCNT` | 20개 — 발동이벤트_요약 매핑 그대로 (4분초과율·소터대기 포함) |
| `CSV 컬럼` | 저장된 CSV 컬럼명 `M16HUB_rev_count` | 16개 — 점수 계열(`M16HUB_score`·`flow_score`·`hot_score`) 포함 |

묶음을 바꿔도 같은 지표가 있으면 그대로 유지되고, 없으면 그 묶음의 첫 항목(스코어)으로
넘어간다. 실시간·과거 탭의 묶음/지표 선택은 서로 독립이다.

목록은 `config.json` 의 `ui.metric_groups` 로 바꾼다.
그 날 CSV 에 값이 하나도 없는 항목·묶음은 자동으로 빠진다.

```json
"ui": { "metric_groups": [
  { "id":"amos", "name":"AMOS 컬럼", "desc":"발동이벤트_요약 기준", "metrics":[
    {"key":"unified_risk_score","raw":"unified_risk_score","label":"스코어",
     "unit":"점","color":"#3DDBE8","max":100,"bands":true},
    {"key":"M16HUB_rev_count","raw":"M16HUB.QUE.LFT.3F_LFT_REVERSALCNT",
     "label":"M16HUB 리프터막힘","unit":"회","color":"#FF6FB5"}
  ]},
  { "id":"csv", "name":"CSV 컬럼", "metrics":[
    {"key":"M16HUB_rev_count","raw":"M16HUB_rev_count",
     "label":"M16HUB 리프터막힘","unit":"회","color":"#FF6FB5"}
  ]}
]}
```

| 필드 | 뜻 |
|---|---|
| `id` / `name` / `desc` | 묶음 식별자 / 버튼 이름 / 버튼 툴팁 |
| `key` | **값이 들어있는 CSV 컬럼** (필수) — `M16HUB_rev_count` |
| `raw` | **화면에 보여줄 컬럼명** — 묶음에 따라 AMOS 명 또는 CSV 명 |
| `label` / `unit` | 화면에 보일 이름 / 단위 (발동이벤트_요약 과 같은 표기) |
| `color` | 선·면 색 |
| `max` | 축 상한 고정 (예: % 는 100). 없으면 데이터에 맞춰 자동 |
| `bands` | `true` 면 등급 밴드 + 0~100 고정 (스코어용) |

`ui.metric_groups` 가 없으면 예전 형식인 `ui.strip_metrics` 를, 그것도 없으면
코드 기본값을 쓴다.

**수집 주기**는 화면에서 바로 바꿀 수 있다(즉시 반영): 10초 / 30초 / **1분(기본)** / 5분 / 10분.

목록에는 **오늘 쌓인 전체 데이터**가 4등급(정상·경계·위험·초위험)으로 표시된다.
경계 이상은 케이스와 연결되고, 정상 행은 데이터만 보여준다(알람 없음).

**행을 더블클릭하면 그 시각 기준 1시간 구간 그래프**가 뜬다 (30분/1시간/2시간/6시간 선택).
`발동이벤트_요약`·`report_graphs` 와 같은 규칙으로 그린다:

**패널을 세로로 쌓아** 그린다 (지표를 겹치지 않는다):

```
┌ 스코어 패널 ── unified_risk_score, 등급 밴드(50/71/85), 사건·최고점 표시
├ 지표 패널 1 ── M16HUB 반송시간 (분)
│                M16HUB.QUE.TIME.AVGTOTALTIME1MIN    ← 실제 raw 컬럼
│                범위 3.82~19.32분                    ← 구간 실측 범위
│                (사건 시각에 실제 값 표시: 5.91분)
├ 지표 패널 2 ── M16HUB FAB저장율 (%) …
└ X축 (시각)
```

지표는 최고점 `reason` 에서 뽑는다 — 반송시간 / FAB저장율 / STB저장율 / 리프터 정체 /
4분초과율 / 분류기 대기 / OHT가동률. 각 패널은 자기 축을 가지며 실제 값이 그대로 찍힌다.

## 정책 (config.json `policy`)

- 감지는 **항상 실시간**. 평가 주기는 리포트 발행 주기일 뿐 감지를 늦추지 않는다.
- **“이상 없음” 판정은 케이스를 닫지 않는다** — 재확인 예약만 갱신.
- 종결 후에도 **억제 창**(기본 30분) 안의 재발은 같은 케이스로 병합.
- 종결은 확인 처리 후에만 가능(`close_requires_ack`).

## 피드백 학습

`과다탐지` 누적 → 임계 +2점 / `누락` 누적 → −2점 (최대 ±10).
최근 20건만 반영. 현재 보정값은 대시보드 “학습 반영 현황”에 표시된다.

---

## ★ 확인 필요 (모르는 것 — 추측하지 않았음)

아래는 사내망에서 `--schema` 를 돌려야 확정된다. 지금은 **발동이벤트 CSV 기준으로 가정**해 두었고,
다르면 `config.json` 만 고치면 된다. (스킬 규칙: 테이블·컬럼명을 추측하지 않는다)

1. **`test_table3` 실제 컬럼** — 특히 `datetime`, `unified_risk_score`, `hot_area`, `reason` 이
   그대로 있는지. 다르면 `config.amos.base_time_col` 과 `sentinel.py` 의 `_row_dt/_score` 매핑 확인.
2. ~~ATLAS 컬럼명~~ — 확인 완료. 원본은 `downward_anomaly_cols`/`upward_anomaly_cols`,
   시각은 `EVENT_DT`. `config.amos.*.src_downward/src_upward` 가 원본,
   `downward_col/upward_col` 이 CSV 에 저장될 이름이다.
3. ~~시각 컬럼 형식~~ — 확인 완료. `EVENT_DT`(예 `2026-07-27 0:00`) 기준으로 조인한다.
   `_time` 은 수집시각(밀리초·타임존 포함)이라 1분 밀리므로 쓰지 않는다.
4. **LLM API 키** — `real_time_amhs/token.txt` (또는 `GAIA_API_KEY` 환경변수).
   없으면 LLM 판단/리포트만 비활성되고 감지·케이스·통계 리포트는 정상 동작한다.

## 미구현 (규격 필요)

- **메신저 발송** — 사내 메신저 API 엔드포인트/인증 규격 필요
- **관제시스템 전송** — 수신 엔드포인트/포맷 규격 필요

두 버튼은 화면에 있으나 누르면 “규격 필요” 안내만 뜬다.

---

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/status` | 연결/지연/정책 |
| GET | `/api/kpi` | 상단 지표 |
| GET | `/api/cases` | 활성 케이스 (`?all=1` 전체) |
| POST | `/api/cases/<id>/ack \| normal \| close` | 확인 / 이상없음 / 종결 |
| POST | `/api/cases/<id>/judge` | LLM 판단 |
| POST | `/api/report` | 구간 리포트 (`{start,end}`) |
| POST | `/api/feedback` | 피드백 (`{report_id,verdict,missed,comment}`) |
| POST | `/api/query` | LPQL 조회 (읽기 전용) |
