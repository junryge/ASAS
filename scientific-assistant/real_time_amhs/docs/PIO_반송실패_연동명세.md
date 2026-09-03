---
name: pio-error
description: PIO 반송실패(DEPOSITED) 해석 — 12경로 실패건수를 어떻게 읽나. 설비 지표와 무엇이 다른지, 10분 합 구간표, 경로별 평소 수준, 빈칸과 0의 차이, 최대 10분 지연. reason 의 PIO(경로=N건/10분,합M) 과 pio_10min_cnt·*_PIOERROR_DEPOSITED 컬럼을 볼 때 쓴다.
---

# PIO 반송실패 데이터 — 연동 명세

> 룰베이스 예측 시스템이 매분 수집하는 **PIO 반송실패(DEPOSITED) 12경로 데이터**를
> 다른 시스템에 넘기기 위한 명세.
>
> **원천** ICASTAR · `STA_TRANS_TIMEOUT_FAIL_HIS` **단위** 경로 × 1분 × 실패건수 **주기** 60초
>
> 통계는 2026-09-01 00:00 ~ 09-03 08:14 운영 실측 **3,375분** 기준.

| 항목 | 값 |
|---|---|
| 감시 경로 | **12개** (FAB 간 반송 구간) |
| 집계 단위 | **1분** · 60초마다 갱신 |
| 권장 판단 창 | **10분** — 1분 값은 대부분 0/1 이라 그대로 못 씀 |
| 말할 때 단위 | **개** — 사람에게 보여 줄 때는 "6개/10분" 이라고 쓴다 (원문 reason 은 "…=4건" 으로 오지만 그대로 옮기지 않는다) |

---

## 1. 무엇을 재는 값인가

FAB 사이를 오가는 반송에서 **물건을 넣으려다 실패한 건수**입니다.
ICASTAR 의 반송 타임아웃 이력에서 `FAIL_TYP = 'DEPOSIT'` 인 것만 셉니다.

### 기존 설비 지표와 무엇이 다른가

설비 지표(큐 길이·반송시간·가동률)는 **밀리는 중**을 봅니다 — 아직 실패는 아닙니다.
PIO 는 **이미 실패한 결과**입니다. 둘이 같이 오르면 확실한 정체이고,
어느 **구간**에서 실패했는지까지 나오므로 조치 지점이 바로 잡힙니다.

실측으로 두 지표의 상관계수는 **+0.22** — 거의 겹치지 않습니다. 서로 못 보는 것을 채워 줍니다.

### 12개 경로 — 판정 기준과 3일 실측

경로는 `FAC_ID` · `FAB_ID` · `PORT_NM 앞글자` 조합으로 정해집니다.

| 경로 (GUBUN) | 구간 | FAC_ID | FAB_ID | PORT_NM | 3일 합계 | 10분 p95 | 10분 최대 |
|---|---|---|---|---|---:|---:|---:|
| **M14A&lt;-M14B** | M14B → M14A 리프터 | M14 | M14B | `4ALF%` | 1,483 | 12 | 81 |
| **M16HUB&lt;-M16A** | M16A → 허브 리프터 | M16 | M16A | `6ABL%` | 1,034 | 12 | 33 |
| **M16A-&gt;M16B** | M16A → M16B 리프터 | M16 | M16A | `6ALF%` | 336 | 3 | 6 |
| M16HUB-&gt;MLUD | 허브 → MLUD | M16 | M16HUB | `6FIOB%` | 36 | 0 | 8 |
| M16B-&gt;M16A | M16B → M16A 리프터 | M16 | M16B | `6ALF%` | 13 | 0 | 2 |
| M16HUB&lt;-M14B | M14B → 허브 리프터 | M14 | M14B | `4ABLD%` | 8 | 0 | 2 |
| M16HUB-&gt;M14B | 허브 → M14B 리프터 | M16 | M16HUB | `4ABLD%` | 7 | 0 | 2 |
| M16HUB-&gt;M14A | 허브 → M14A 컨베이어 | M16 | M16HUB | `4AFC%` | 0 | 0 | 0 |
| M16HUB&lt;-M14A | M14A → 허브 컨베이어 | M14 | M14A | `4AFC%` | 0 | 0 | 0 |
| M16HUB-&gt;M16A | 허브 → M16A 리프터 | M16 | M14B | `6ABL%` | 0 | 0 | 0 |
| M14A-&gt;M14B | M14A → M14B 리프터 | M14 | M14A | `4ALF%` | 0 | 0 | 0 |
| M14A-&gt;M10A | M14A → M10A 리프터 | M14 | M10A | `4ABL%` | 0 | 0 | 0 |

실제로 발생하는 경로는 **3개**에 집중돼 있고, **5개 경로는 3일간 0건**입니다 —
그 구간이 정상이라는 정보로 씁니다.

---

## 2. 가져가는 방법 — 세 가지

| 방식 | 형태 | 주기 | 언제 쓰나 |
|---|---|---|---|
| ① 발동이벤트 CSV | `{YYYYMMDD}_발동이벤트.csv` 의 12컬럼 | 1분 | 파일 공유가 되면 가장 간단 |
| ② `pio_state.json` | JSON (그날 전체) | 1분 · 약 200KB | 임의 시각 10분 합을 직접 계산할 때 |
| ③ DB 직접 조회 | Oracle 쿼리 | 자유 | 파일 공유 불가하거나 자체 주기로 돌릴 때 |

### ① 발동이벤트 CSV — 컬럼 이름

```
{경로}_PIOERROR_DEPOSITED        ← 12개, 값은 그 1분의 실패 건수

M16HUB->MLUD_PIOERROR_DEPOSITED
M16HUB->M14B_PIOERROR_DEPOSITED
M16HUB<-M14B_PIOERROR_DEPOSITED
M16HUB->M14A_PIOERROR_DEPOSITED
M16HUB<-M14A_PIOERROR_DEPOSITED
M16HUB->M16A_PIOERROR_DEPOSITED
M16HUB<-M16A_PIOERROR_DEPOSITED
M16A->M16B_PIOERROR_DEPOSITED
M16B->M16A_PIOERROR_DEPOSITED
M14A->M14B_PIOERROR_DEPOSITED
M14A<-M14B_PIOERROR_DEPOSITED
M14A->M10A_PIOERROR_DEPOSITED

같은 파일에 예측 시스템이 계산한 값도 있음
pio_10min_cnt      12경로 최근 10분 합계
pio_score          스코어에 더해진 값 (0/2/4/7/9/11)
```

> **값 읽을 때 주의**
> **빈칸**은 0 이 아니라 **아직 조회 안 된 분**입니다 (DB 지연·기입기 정지).
> 0 은 "조회했는데 실패가 없었다"는 뜻입니다. 둘을 반드시 구분하세요.
>
> 완료 시각(`COMPLT_TM`) 기준이라 **최대 10분까지 늦게 적재**될 수 있습니다.
> 최근 10분치는 값이 나중에 늘어날 수 있고, 예측 시스템도 그 구간을 매분 다시 씁니다.

### ② pio_state.json — 구조

```json
{
  "updated": "2026-09-03 04:18:44",
  "day":     "2026-09-02",
  "window_hint": 10,
  "paths":   ["M16HUB->MLUD", "...12개..."],
  "covered": [["2026-09-02 00:00", "2026-09-03 00:00"]],
  "minutes": {
    "2026-09-02 00:01": { "M16HUB<-M16A": 1 },
    "2026-09-02 10:57": { "M14A<-M14B": 9, "M16HUB<-M16A": 1 }
  }
}
```

| 필드 | 뜻 |
|---|---|
| `updated` | 마지막 갱신 시각 — **5분 이상 안 바뀌면 데이터가 멈춘 것** |
| `covered` | 조회가 완료된 구간 |
| `minutes` | 분 → {경로: 건수}. **0인 경로는 아예 없음** |

- `covered` 안에 있는 시각인데 `minutes` 에 없으면 → **실패 0건**
- `covered` 밖이면 → **미조회** (빈칸으로 처리)

### ③ DB 직접 조회 — 쿼리

```sql
SELECT GUBUN,
       TO_CHAR(GROUP1, 'YYYY-MM-DD HH24:MI') AS GROUP1,
       SUM(CASE WHEN FT = 'DEPOSIT' THEN 1 ELSE 0 END) AS DEPOSITED_FAIL_CNT
FROM (
    SELECT TO_DATE(SUBSTR(A.COMPLT_TM, 1, 12), 'YYYYMMDDHH24MI') AS GROUP1,
           UPPER(TRIM(A.FAIL_TYP)) AS FT,
           CASE
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16HUB' AND UPPER(TRIM(A.PORT_NM)) LIKE '6FIOB%' THEN 'M16HUB->MLUD'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16HUB' AND UPPER(TRIM(A.PORT_NM)) LIKE '4ABLD%' THEN 'M16HUB->M14B'
             WHEN A.FAC_ID='M14' AND A.FAB_ID='M14B'   AND UPPER(TRIM(A.PORT_NM)) LIKE '4ABLD%' THEN 'M16HUB<-M14B'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16HUB' AND UPPER(TRIM(A.PORT_NM)) LIKE '4AFC%'  THEN 'M16HUB->M14A'
             WHEN A.FAC_ID='M14' AND A.FAB_ID='M14A'   AND UPPER(TRIM(A.PORT_NM)) LIKE '4AFC%'  THEN 'M16HUB<-M14A'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M14B'   AND UPPER(TRIM(A.PORT_NM)) LIKE '6ABL%'  THEN 'M16HUB->M16A'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16A'   AND UPPER(TRIM(A.PORT_NM)) LIKE '6ABL%'  THEN 'M16HUB<-M16A'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16A'   AND UPPER(TRIM(A.PORT_NM)) LIKE '6ALF%'  THEN 'M16A->M16B'
             WHEN A.FAC_ID='M16' AND A.FAB_ID='M16B'   AND UPPER(TRIM(A.PORT_NM)) LIKE '6ALF%'  THEN 'M16B->M16A'
             WHEN A.FAC_ID='M14' AND A.FAB_ID='M14A'   AND UPPER(TRIM(A.PORT_NM)) LIKE '4ALF%'  THEN 'M14A->M14B'
             WHEN A.FAC_ID='M14' AND A.FAB_ID='M14B'   AND UPPER(TRIM(A.PORT_NM)) LIKE '4ALF%'  THEN 'M14A<-M14B'
             WHEN A.FAC_ID='M14' AND A.FAB_ID='M10A'   AND UPPER(TRIM(A.PORT_NM)) LIKE '4ABL%'  THEN 'M14A->M10A'
           END AS GUBUN
    FROM STA_TRANS_TIMEOUT_FAIL_HIS A
    WHERE A.COMPLT_TM >= :t_from        -- YYYYMMDDHH24MISS 문자열
      AND A.COMPLT_TM <  :t_to
      AND A.FAC_ID IN ('M14', 'M16')
)
WHERE GUBUN IS NOT NULL
GROUP BY GUBUN, GROUP1
ORDER BY GROUP1, GUBUN
```

- 접속: `10.40.41.103:1521/ICASTARPP` (계정은 별도 전달)
- 구간을 **문자열로 비교**해야 인덱스를 탑니다
- 하루를 통으로 조회하면 느리니 **10~15분 단위**로 자르는 것을 권합니다

---

## 3. 받는 쪽에서 임계를 어떻게 잡나

1분 값은 대부분 0 또는 1 이라 그대로 쓸 수 없습니다. **최근 10분 합계**로 보십시오.

| 지표 | 평균 | 중앙 | p90 | p95 | p99 | 최대 |
|---|---:|---:|---:|---:|---:|---:|
| 1분 총합 (12경로) | 0.9 | 0 | 2 | 3 | 6 | 13 |
| **10분 총합 (12경로)** | **8.6** | 7 | 16 | 20 | 40 | **89** |

### 참고 — 예측 시스템이 쓰는 구간표

같은 데이터로 스코어를 만들 때 쓰는 기준입니다. 그대로 쓰셔도 되고 조정하셔도 됩니다.

| 10분 총합 | 3일 중 해당 | 의미 | 스코어 가산 |
|---|---:|---|---:|
| 0 ~ 15 | 3,002분 (88.9%) | 평소 수준 | — |
| 16 ~ 25 | 274분 (8.1%) | 조금 많음 | +1점 |
| 26 ~ 40 | 65분 (1.9%) | 확실히 많음 | +2점 |
| 41 ~ 60 | 22분 (0.7%) | 이상 | +3점 |
| 61 ~ 80 | 6분 (0.2%) | 심각 | +4점 |
| 81 이상 | 6분 (0.2%) | 최고 | +5점 |

> **경로별로 평소 수준이 다릅니다**
> `M14A<-M14B` 는 평소에도 10분에 **12건**(p95)까지 나오고, `M16HUB->MLUD` 는 평소 **0**입니다.
> 경로 단위로 경보를 낼 계획이면 위 경로 표의 **10분 p95** 를 기준으로 쓰십시오.

> **기준선을 자동으로 다시 계산하지 마십시오**
> 설비 상태가 나빠지면 실패가 늘어나는데, 최근 데이터로 평소치를 계속 갱신하면
> **기준선도 같이 올라가 악화를 못 잡습니다.**
> 실제로 9/1 → 9/3 사흘 동안 정상 대비 초과 건수가 **0.6 → 1.7 → 3.5건** 으로 늘었습니다
> (물량 증가 + 설비 정비가 겹친 기간). 기준선을 고정해 두었기 때문에 보인 것입니다.

---

## 4. 실제로 어떻게 움직이나 — 사례

3일간 10분 합계가 30건을 넘은 구간은 6번이었습니다.

| 구간 | 길이 | 10분 최고 | 주 경로 | 설비 지표 쪽 판단 |
|---|---:|---:|---|---|
| 09-01 22:53 | 1분 | 31 | M16HUB&lt;-M16A | M16A 신호 |
| 09-01 23:06~23:07 | 2분 | 33 | M16HUB&lt;-M16A | HUB-MLUD |
| **09-02 10:46~11:06** | 21분 | **89** | M14A&lt;-M14B | M14 SLA초과 · OHT 99% **(3단계 확정)** |
| **09-03 00:56~01:07** | 12분 | 59 | M14A&lt;-M14B | M14 SLA초과 **(3단계 확정)** |
| 09-03 06:35~06:36 | 2분 | 32 | M14A&lt;-M14B | M14 Sorter대기 |
| **09-03 07:28~07:48** | 21분 | 45 | M16HUB&lt;-M16A | M16A 큐누적 **(3단계 확정)** |

**읽는 법** — 길게 이어진 3개 구간은 설비 지표 쪽에서도 **3단계 확정**으로 같이 잡았습니다.
PIO 가 엉뚱한 곳에서 튀는 것이 아니라 같은 정체를 다른 방향에서 확인합니다.
1~2분짜리 짧은 급증은 설비 지표가 약하게만 반응했으니, **지속 시간**을 조건에 넣으면
(예: 3분 이상 연속) 짧은 튐을 걸러낼 수 있습니다.

---

## 5. 운영 시 알아 두실 것

| 항목 | 내용 |
|---|---|
| **지연** | 완료 시각 기준이라 **최대 10분** 늦게 들어옵니다. 실시간 판정은 1~2분 전까지를 기준으로 보거나, 최근 구간은 다시 계산하십시오. |
| **결측** | DB 접속이 끊기면 그 시간대는 **빈칸**입니다. 0 으로 처리하면 "실패가 없었다"로 오해합니다. `covered` / `updated` 로 확인하십시오. |
| **편중** | 12개를 다 받되 실제 신호는 3개 경로에서 나옵니다. 나머지는 0 이 정상이며, **0이 아닌 값이 나오면 그 자체로 이상**입니다. |
| **해석** | 3일 데이터에서 PIO 가 설비 지표보다 **먼저 오른 사례는 없었습니다.** 거의 동시에 움직입니다. 조기 경보가 아니라 **확증과 조치 지점**으로 쓰는 것이 맞습니다. |

---

**데이터** — ICASTAR `STA_TRANS_TIMEOUT_FAIL_HIS`, `FAIL_TYP='DEPOSIT'`, 경로별 1분 집계.
통계는 2026-09-01 00:00 ~ 09-03 08:14 운영 실측 3,375분에서 계산했습니다.

**요약** — 수집 주기 60초 · 경로 12개 · 권장 판단 창 10분.
연동 방식(CSV / JSON / DB)과 계정은 담당자와 협의해 정하십시오.
