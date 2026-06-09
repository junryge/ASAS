# 🔮 헤르메스 사용법 (Hermes Usage Guide)

LLM API 기반으로 **헤르메스를 쓰는 법**을 단계별로 정리했습니다.
바로 체험하려면 같은 폴더의 **[DEMO.html](DEMO.html)** 을 브라우저로 여세요. (키만 넣으면 동작)

---

## 0. 헤르메스가 뭔가요? (한 문단)

평범한 LLM은 대화가 끝나면 다 잊습니다. **헤르메스**는 그 위에 얹는 얇은 레이어로,
대화에서 **기억할 사실/선호를 저장**하고, **재사용할 절차를 스킬로 학습**하며, 모호하면 **되묻습니다**.
모델을 바꾸지 않고, **좋은 기억·절차를 컨텍스트로 떠먹여** 쓸수록 잘 맞게 만듭니다.
네이티브 함수콜이 필요 없고(**텍스트 프로토콜**), 폐쇄망/GGUF/어떤 OpenAI 호환 API에서도 동작합니다.

---

## 1. 가장 빠른 체험 — DEMO.html

1. `DEMO.html` 을 브라우저로 연다. (더블클릭이면 끝. 서버 불필요)
2. 오른쪽 **LLM API 설정**에 입력하고 **저장**:
   - **API 주소**: OpenAI 호환 엔드포인트의 `/v1` (예: `http://common.llm.skhynix.com/v1`)
   - **API 키**: Bearer 토큰 (없으면 비워둠)
   - **모델명**: 예 `Qwen3.6-35B-A3B`
   - gemma 계열이면 **"system을 첫 user에 합치기"** 체크 (gemma는 system 역할 미지원)
3. **연결 테스트** → ✅ 나오면 준비 완료.
4. 채팅에 이렇게 말해보세요:
   > 나는 M16 FAB의 OHT 반송 정체를 분석해. 답은 표로 줘.
   - 오른쪽 **MEMORY**에 "담당 업무"가, **USER**에 "표 선호"가 쌓입니다.
   - 다음 질문부터 자동 반영돼서, "표로 줘"라고 안 해도 표로 답합니다.

> DEMO.html은 **백엔드 없이** 브라우저에서 직접 LLM API를 호출하고 헤르메스 프로토콜을 처리하는
> **클라이언트 재현본**입니다. 실제 서비스 통합은 아래 2장(Python 엔진)을 쓰세요.

---

## 2. 실제 서비스에 붙이기 (Python 엔진)

### 2-1. 라우트 한 줄 등록
```python
from flask import Flask
from hermes import register_hermes_routes

app = Flask(__name__)
register_hermes_routes(app)   # /api/hermes/* 등록 (메인 /api/chat 은 그대로)
```

### 2-2. 채팅 흐름에 감싸기 (3 지점)
```
[전송 전]  POST /api/hermes/prep  {user_id, query}
            → {system_addon}   ← 기억+스킬+지침. 이걸 system_prompt 앞에 합쳐 LLM 호출
[LLM 호출]  네 기존 /api/chat (OpenAI 호환) 그대로 — system_prompt 에 addon 합친 것만 다름
[응답 후]  POST /api/hermes/post  {user_id, answer, user_message, session_id}
            → {clean, memory_results, pending_skills, questions}
              · clean          : 블록 제거된 표시용 본문
              · memory_results : 자동 저장된 기억
              · pending_skills : 승인 대기 스킬 → 사용자 OK 시 confirm
              · questions      : 되묻기 질문
[스킬 승인] POST /api/hermes/skill/confirm  {user_id, spec}
```

### 2-3. 라우트 없이 직접 호출
```python
from hermes import engine
addon   = engine.build_system_prompt(user_id, query)   # system_prompt 에 합칠 문자열
res     = engine.apply_response(user_id, llm_answer)    # 블록 처리 결과(dict)
ok, msg = engine.confirm_skill(user_id, res["pending_skills"][0])
```

### 2-4. 저장 위치
```bash
export HERMES_DATA_DIR=/path/to/data   # 없으면 ./hermes_data
# 구조: <DATA>/agents/<user_id>/ {MEMORY.md, USER.md, skills/, sessions/, counters.json}
```

---

## 3. LLM API 연동 핵심 (어떤 API든)

헤르메스는 **OpenAI 호환 chat completions** 면 무엇이든 됩니다.

```python
import requests
addon = engine.build_system_prompt(user_id, query)
system_prompt = (addon + "\n\n" + base_system_prompt).strip()

payload = {
    "model": "Qwen3.6-35B-A3B",
    "messages": [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": query},
    ],
    "temperature": 0.3, "max_tokens": 2048,
}
ans = requests.post("http://common.llm.skhynix.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {TOKEN}"}, json=payload).json()
answer = ans["choices"][0]["message"]["content"]

res = engine.apply_response(user_id, answer)   # 기억저장/스킬/되묻기 처리
show(res["clean"])                              # 블록 제거된 깔끔한 답만 사용자에게
```

> ⚠️ **gemma 계열 주의**: gemma는 채팅 템플릿에 `system` 역할이 없어 system 메시지를 보내면
> 서버가 HTTP 500을 냅니다. 이 경우 **system 내용을 첫 user 메시지 앞에 합쳐서** 보내세요.
> (DEMO.html 의 "system을 첫 user에 합치기" 체크가 같은 처리입니다.)

---

## 4. 헤르메스가 쓰는 텍스트 프로토콜 (모델 출력 블록)

모델이 답변 끝에 아래 펜스 블록을 내면 엔진이 파싱해 처리합니다.
(이 사용법은 `build_system_prompt` 가 시스템 프롬프트에 자동으로 넣어줍니다.)

````
```hermes:memory
store: memory          # memory(사실) | user(선호)
action: add            # add | replace | remove
text: 사용자는 M16 FAB의 OHT 반송 정체를 분석한다
```

```hermes:skill
action: create
name: oht-jam-triage
when: OHT 반송 정체 원인 추적 시
body: |
  1. 구간별 큐 길이 확인
  2. ...
```

```hermes:ask
- 대상 FAB은 M14인가요 M16인가요?
- 기간은?
```
````

---

## 5. 빌트인 스킬 4종 (자동 주입)

질문 키워드에 맞으면 상위 2개가 시스템 프롬프트에 자동으로 끼어듭니다. (학습 없이 기본 제공)

| 스킬 | 발동 키워드(일부) | 하는 일 |
|---|---|---|
| 🧭 task-planning | 만들·구현·설계·코드·분석·계획 | 다단계 작업 → 목표·계획·실행·자가점검 |
| 🐞 systematic-debugging | 오류·에러·버그·실패·exception | 재현→가설→최소수정→검증 |
| 📊 structured-data-analysis | 데이터·분석·반송·FAB·OHT·CSV | 컬럼/단위 확인→통계→이상치→시각화 |
| ✅ answer-verification | 보고서·결론·검증·요약 | 최종답 전 근거·누락 자가검증 |

자세한 스킬 설명: **[HERMES_SKILLS.html](HERMES_SKILLS.html)** / 전체 기능: **[HERMES_FEATURES.html](HERMES_FEATURES.html)**

---

## 6. 자주 묻는 것

- **Q. 모델이 블록을 안 내요.** → 작은 모델은 프로토콜을 잘 못 따릅니다. 컨텍스트 큰 API 모델(예: Qwen3.6-35B)에서 잘 동작합니다.
- **Q. 답에 ```hermes:... 블록이 그대로 보여요.** → `apply_response`(또는 DEMO의 파싱)가 블록을 제거한 `clean` 을 화면에 쓰세요. 원문(answer)을 그대로 보여주면 안 됩니다.
- **Q. 기억이 안 쌓여요.** → 사용자가 역할·담당·도구·선호를 "드러내야" 저장됩니다. 잡담만으론 저장 안 합니다(의도된 동작).
- **Q. 폐쇄망인데 되나요?** → 됩니다. 외부망/MCP/게이트웨이 불필요. LLM 엔드포인트 하나만 있으면 됩니다.

---

문의/통합 예제: `examples/app_min.py`, 프론트 클라이언트: `static/hermes-client.js`
