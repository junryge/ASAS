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

# 1) 키 2개 넣기 (둘 다 이 폴더 안 — 데모스와 무관)
echo "<로그프레소 API 키>" > api_key.txt
echo "<GaiA LLM API 키>"   > token.txt

# 2) 접속 확인
python lp_query.py --ping

# 3) ★ 실제 컬럼 확인 (추측 금지 — 아래 '확인 필요' 참고)
python lp_query.py --schema
python lp_query.py --schema -t ATLAS_BOTTLENECK_ANOMALY
python lp_query.py --schema -t ATLAS_QUEUE_ANOMALY

# 4) 관제 시작
python server.py            # → http://localhost:8700/
```

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
| `lp_query.py` | LPQL 빌더 + CLI 조회 + **AMOS 2개 테이블 조인** |
| `sentinel.py` | 감지 → 케이스 생성/병합 → 등급 → 에스컬레이션 |
| `llm_client.py` | 스킬 4종 + 페르소나 주입 → LLM 판단·리포트 (+금지어 스크럽) |
| `report.py` | 구간 리포트 + 피드백 저장 → 임계치 자동 보정 |
| `server.py` | 독립 Flask + 폴링 스레드 + REST API |
| `static/dashboard.html` | 관제 화면 (**오프닝 화면 없음** — 바로 진입) |
| `fixtures/` | 오프라인 검증용 샘플 (실제 스키마 아님) |

---

## 데이터 흐름

```
test_table3 (기존 데이터)
        +
ATLAS_BOTTLENECK_ANOMALY  ─┐  search MCP_NM == "BR"
ATLAS_QUEUE_ANOMALY       ─┘  시각(분) 조인
        ↓
BOTTLENECK_downward/upward_anomaly_cols
QUEUE_downward/upward_anomaly_cols        ← AMOS 4개 컬럼 추가
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
2. **ATLAS 두 테이블의 컬럼명** — `BOTTLENECK_downward_anomaly_cols` 등 4개가 그 이름 그대로인지.
   다르면 `config.amos.bottleneck.downward_col` 등을 교체.
3. **시각 컬럼 형식** — 조인 키는 `_time`(ATLAS) ↔ `datetime`(기존) 을 **분 단위**로 맞춘다.
   형식이 다르면 조인 0건 경고가 대시보드에 뜬다.
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
