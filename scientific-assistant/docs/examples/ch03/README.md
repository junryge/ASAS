# Chapter 3 — 예제 코드

`api_config.json` 의 모델 7종을 자유롭게 갈아끼우는 학습 도구들.

## 파일

| 파일 | 용도 |
|------|------|
| `multi_model_chat.py` | CLI에서 모델을 골라 대화 |
| `model_probe.py` | 등록된 전 모델을 ping 해 살아있는지 확인 |
| `api_config.sample.json` | 신규 모델 추가/비활성화 예시 포함 샘플 |

## 사용

```bash
# 0) 의존성
pip install requests

# 1) 한 모델 골라 대화
python multi_model_chat.py
python multi_model_chat.py --temperature 0.1 --max-tokens 2048

# 2) 전체 헬스체크
python model_probe.py

# 3) 특정 모델만 ping
python model_probe.py qwen3-coder-30b
python model_probe.py qwen3-coder-480b "파이썬 fizzbuzz 한 줄"

# 4) 샘플 설정 시험
cp api_config.sample.json api_config.json   # 같은 폴더에 복사해서 실험
python multi_model_chat.py                   # sample 의 모델 목록이 뜸
```

## 탐색 경로

- `api_config.json` → 같은 폴더 우선, 없으면 프로젝트 루트 (`scientific-assistant/api_config.json`)
- `token.txt` → 같은 폴더 우선, 없으면 프로젝트 루트

> 운영 `api_config.json` 을 망가뜨리지 않으려면, 이 폴더에 **로컬 사본**을 두고 실험하는 것을 권장한다.

## 입력 명령어 (multi_model_chat.py)

| 입력 | 동작 |
|------|------|
| `quit` | 종료 |
| `reset` | 대화 히스토리 초기화 |
| `switch` | 모델 다시 선택 |
| (그 외 문장) | 질문으로 전송 |
