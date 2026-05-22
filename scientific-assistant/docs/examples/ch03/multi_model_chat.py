"""
Chapter 3 — api_config.json 의 모델을 CLI에서 골라 채팅하는 데모.

기능:
- 같은 폴더 또는 프로젝트 루트의 api_config.json 을 읽어 모델 목록을 표시
- 사용자가 번호를 선택하면 해당 모델로 대화 루프 시작
- temperature, max_tokens 를 명령줄/환경변수로 조정 가능
- 'quit' 입력 시 종료, 'reset' 입력 시 대화 히스토리 초기화

사용:
    python multi_model_chat.py
    python multi_model_chat.py --temperature 0.2 --max-tokens 2048
"""
import argparse
import json
import os
import sys
import time

import requests


SEARCH_PATHS = (
    "api_config.json",
    os.path.join("..", "..", "..", "api_config.json"),
)
TOKEN_PATHS = (
    "token.txt",
    "TOKEN.TXT",
    os.path.join("..", "..", "..", "token.txt"),
    os.path.join("..", "..", "..", "TOKEN.TXT"),
)


def _read_first_existing(paths, label):
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read(), os.path.abspath(p)
    sys.exit(f"❌ {label} 을(를) 찾지 못했습니다. 탐색 경로: {paths}")


def load_config():
    raw, path = _read_first_existing(SEARCH_PATHS, "api_config.json")
    cfg = json.loads(raw)
    print(f"[CONFIG] {path}  ({len(cfg.get('models', {}))}개 모델)")
    return cfg


def load_token():
    raw, path = _read_first_existing(TOKEN_PATHS, "token.txt")
    print(f"[TOKEN ] {path}")
    return raw.strip()


def pick_model(models):
    keys = list(models.keys())
    print("\n=== 사용 가능 모델 ===")
    for i, k in enumerate(keys):
        info = models[k]
        print(f"  [{i}] {k:<22} → {info.get('name', k):<28} "
              f"({info.get('cost_tier', '-')}/p{info.get('priority', '-')})")
    while True:
        raw = input("\n모델 번호 선택: ").strip()
        if raw.isdigit() and 0 <= int(raw) < len(keys):
            return keys[int(raw)], models[keys[int(raw)]]
        print("  ⚠️  유효한 번호를 입력하세요.")


def chat_loop(model_key, model_info, token, temperature, max_tokens):
    url = model_info["url"]
    model_name = model_info["model"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    history = []
    print(f"\n▶ {model_key} ({model_name}) — temperature={temperature}, "
          f"max_tokens={max_tokens}")
    print("  'quit' 종료, 'reset' 대화 초기화, 'switch' 모델 다시 선택\n")

    while True:
        try:
            q = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not q:
            continue
        if q.lower() == "quit":
            return None
        if q.lower() == "reset":
            history.clear()
            print("  (히스토리 초기화)")
            continue
        if q.lower() == "switch":
            return "switch"

        history.append({"role": "user", "content": q})
        payload = {
            "model": model_name,
            "messages": history,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        t0 = time.time()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=180)
        except requests.RequestException as e:
            history.pop()
            print(f"  ❌ 네트워크 오류: {e}")
            continue
        dt = time.time() - t0
        if resp.status_code != 200:
            history.pop()
            print(f"  ❌ {resp.status_code}: {resp.text[:300]}")
            continue
        answer = resp.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": answer})
        print(f"\n답변 ({dt:.1f}s):\n{answer}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temperature", type=float,
                    default=float(os.getenv("LLM_TEMPERATURE", "0.3")))
    ap.add_argument("--max-tokens", type=int,
                    default=int(os.getenv("LLM_MAX_TOKENS", "1024")))
    args = ap.parse_args()

    cfg = load_config()
    token = load_token()
    models = cfg.get("models", {})
    if not models:
        sys.exit("❌ api_config.json 에 models 가 비어있습니다.")

    while True:
        key, info = pick_model(models)
        result = chat_loop(key, info, token, args.temperature, args.max_tokens)
        if result != "switch":
            break

    print("👋 종료")


if __name__ == "__main__":
    main()
