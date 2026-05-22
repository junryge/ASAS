"""
Chapter 3 — api_config.json 에 등록된 모든 모델을 한 번씩 ping 해서
어떤 모델이 살아있는지 표로 출력한다.

사용:
    python model_probe.py                          # 전체 모델 헬스체크
    python model_probe.py <model_key>              # 한 모델만 호출 (기본 질문)
    python model_probe.py <model_key> "질문 내용"   # 한 모델 + 직접 질문
"""
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

DEFAULT_QUESTION = "Reply with the single word: pong."


def _read_first(paths, label):
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    sys.exit(f"❌ {label} not found. searched: {paths}")


def load_config():
    return json.loads(_read_first(SEARCH_PATHS, "api_config.json"))


def load_token():
    return _read_first(TOKEN_PATHS, "token.txt").strip()


def short_host(url):
    try:
        host = url.split("//", 1)[1].split("/", 1)[0]
        return host.split(".")[0]
    except Exception:
        return url[:18]


def call_one(info, token, question, max_tokens=64, timeout=60):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": info["model"],
        "messages": [{"role": "user", "content": question}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    t0 = time.time()
    try:
        r = requests.post(info["url"], headers=headers, json=payload, timeout=timeout)
        dt = time.time() - t0
    except requests.RequestException as e:
        return False, time.time() - t0, f"NETERR: {e}"
    if r.status_code != 200:
        return False, dt, f"{r.status_code} {r.text[:120]}"
    try:
        answer = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return False, dt, f"PARSE: {e}"
    return True, dt, answer[:120]


def probe_all(cfg, token):
    models = cfg.get("models", {})
    if not models:
        sys.exit("❌ models is empty in api_config.json")

    print(f"\n{'STATUS':<6}  {'KEY':<22}  {'HOST':<10}  {'TIME':>6}  RESULT")
    print("-" * 80)
    ok = 0
    for key, info in models.items():
        success, dt, msg = call_one(info, token, DEFAULT_QUESTION)
        tag = "[ok ]" if success else "[fail]"
        if success:
            ok += 1
        print(f"{tag:<6}  {key:<22}  {short_host(info['url']):<10}  {dt:5.1f}s  {msg}")
    print("-" * 80)
    print(f"요약: {ok}/{len(models)} 정상")
    return ok, len(models)


def probe_one(cfg, token, key, question):
    models = cfg.get("models", {})
    if key not in models:
        print(f"❌ '{key}' 모델 없음. 사용 가능 키:")
        for k in models:
            print(f"   - {k}")
        sys.exit(1)
    info = models[key]
    print(f"\n→ {key}  ({info['model']})")
    print(f"  url={info['url']}")
    print(f"  question: {question}\n")
    success, dt, msg = call_one(info, token, question, max_tokens=512, timeout=120)
    tag = "OK" if success else "FAIL"
    print(f"[{tag}] {dt:.1f}s")
    print(f"answer: {msg}")
    sys.exit(0 if success else 1)


def main():
    cfg = load_config()
    token = load_token()

    args = sys.argv[1:]
    if not args:
        ok, total = probe_all(cfg, token)
        sys.exit(0 if ok == total else 1)

    key = args[0]
    question = args[1] if len(args) > 1 else DEFAULT_QUESTION
    probe_one(cfg, token, key, question)


if __name__ == "__main__":
    main()
