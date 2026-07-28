# AMHS Sentinel — LLM 실시간 관제 (데모스와 완전 독립)

M16 HUBROOM 반송 정체를 로그프레소에서 실시간으로 읽어 **감지 → 케이스 → 에스컬레이션 →
리포트 → 피드백 학습** 까지 돌리는 독립 시스템.

> **독립성**: `demos_v1` 을 단 한 줄도 import 하지 않는다. 별도 프로세스·별도 포트(8700).
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
python server.py            # → http://localhost:8700/ 자동 오픈
```

브라우저 자동 실행을 끄려면 `config.server.auto_open: false` 또는 `NO_BROWSER=1`.

사내망 밖(개발 PC)에서는 로그프레소에 닿지 않으므로 fixture 로 UI 를 볼 수 있다:

```bash
LP_OFFLINE=1 python server.py
```

---

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
| `graphs.py` | **구간 그래프 SVG** — 점수 + reason 지표 (발동이벤트_요약 규칙) |
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

## 실시간 관제 · 리포트 (분리된 두 경로)

| | 실시간 관제 | 리포트 · 피드백 |
|---|---|---|
| 조회 | 최신 구간만 (`duration=`) | **날짜로 직접 조회** (`from=/to=`) |
| 주기 | 수집 주기마다 자동 (기본 1분) | 사용자가 날짜/구간 지정 시 |
| 데이터 | 기본 + AMOS 4컬럼 | 기본 + AMOS 4컬럼 (동일) |
| 판단 | 감지 즉시 **LLM 자동 판단** | 구간 요약 리포트 |
| 근거 | 실시간 케이스 저장소 | 저장소와 무관 — 조회 결과로 새로 구성 |

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
