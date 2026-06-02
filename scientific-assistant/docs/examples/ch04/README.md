# Chapter 4 — 예제 코드

스킬 시스템의 핵심을 손으로 만져볼 수 있는 학습 도구들.

## 파일

| 파일 | 용도 |
|------|------|
| `skill_selector_demo.py` | 스킬 자동 선택 알고리즘(`_score_query`) 시뮬레이터 |
| `run_with_skill.py` | SKILL.md 한 개를 system prompt로 끼워 사내 LLM 호출 |
| `my-skill-semicon-fab/SKILL.md` | 반도체 팹 도메인 샘플 커스텀 스킬 |

## 사용

```bash
# 0) 의존성
pip install requests

# 1) 스킬 매칭 점수 확인 (LLM 호출 없음)
python skill_selector_demo.py "OHT가 자꾸 N7 베이에서 멈춰요"
python skill_selector_demo.py "RDKit 으로 벤젠 SMILES 알려줘" --top 5 --verbose

# 2) 스킬을 끼워 실제 LLM 호출 (token.txt + api_config.json 필요)
python run_with_skill.py my-skill-semicon-fab "OHT가 N7 베이에서 멈춰요"

# 3) 스킬 없이 같은 질문 → 차이 비교
python run_with_skill.py my-skill-semicon-fab "OHT가 N7 베이에서 멈춰요" --no-skill

# 4) 프로젝트 루트의 기존 스킬도 호출 가능
python run_with_skill.py rdkit "벤젠 SMILES"
python run_with_skill.py biopython "DNA 역상보 함수"

# 5) 다른 모델로 시도
python run_with_skill.py my-skill-semicon-fab "MTBF·MTTR 차이?" --model qwen3-next-80b
```

## 탐색 규칙

- **`token.txt`** — 같은 폴더 우선, 없으면 프로젝트 루트
- **`api_config.json`** — 프로젝트 루트
- **스킬 경로** — ① 직접 경로 ② 같은 폴더 하위 ③ `scientific-skills/<id>` 순으로 자동 탐색

## 응답 비교 팁

같은 질문에 대해 `--no-skill` 과 일반 호출 결과를 나란히 두고 비교하면, 스킬이 **답변 구조·약어 풀이·검증 질문 제안** 에 미치는 영향을 명확히 볼 수 있다.
