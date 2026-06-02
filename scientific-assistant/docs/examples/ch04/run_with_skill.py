"""
Chapter 4 — SKILL.md 한 개를 system prompt 로 끼워서 사내 LLM 을 호출한다.

사용:
    python run_with_skill.py <skill_path_or_id> "질문..."

예시:
    # 같은 폴더의 my-skill-semicon-fab
    python run_with_skill.py my-skill-semicon-fab "OHT가 N7 베이에서 멈춰요"

    # 프로젝트 루트의 scientific-skills/ 안 스킬
    python run_with_skill.py rdkit "벤젠 SMILES?"

    # 절대/상대 경로 직접 지정
    python run_with_skill.py ../../../scientific-skills/biopython "DNA 역상보 함수"

옵션:
    --no-skill        스킬 없이 그냥 호출 (비교용)
    --model MODEL_ID  api_config.json 의 키 (기본: qwen3-coder-30b)
    --show-prompt     실제 보내는 system prompt 출력
"""
import argparse
import json
import os
import re
import sys

import requests


PROJECT_ROOT_CANDIDATES = (
    os.path.join("..", "..", ".."),  # docs/examples/ch04 → 프로젝트 루트
    ".",
)
TOKEN_NAMES = ("token.txt", "TOKEN.TXT")
DEFAULT_MODEL_KEY = "qwen3-coder-30b"
FALLBACK_URL = "http://common.llm.skhynix.com/v1/chat/completions"
FALLBACK_MODEL = "Qwen3-Coder-30B-A3B-Instruct"


def _project_root():
    for c in PROJECT_ROOT_CANDIDATES:
        if os.path.isdir(os.path.join(c, "demos_v1")):
            return os.path.abspath(c)
    return None


def load_token():
    here = os.path.dirname(__file__) or "."
    candidates = []
    for d in (here, _project_root() or "."):
        for n in TOKEN_NAMES:
            candidates.append(os.path.join(d, n))
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    sys.exit(f"❌ token.txt 를 찾지 못했습니다. 탐색: {candidates}")


def load_api_config():
    root = _project_root()
    if not root:
        return None
    p = os.path.join(root, "api_config.json")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_model(model_key):
    """api_config.json 의 키 → (url, model_id). 없으면 폴백."""
    cfg = load_api_config()
    if cfg and model_key in cfg.get("models", {}):
        info = cfg["models"][model_key]
        return info["url"], info["model"]
    return FALLBACK_URL, FALLBACK_MODEL


def resolve_skill_path(arg):
    """다음 순서로 탐색.
       ① arg 가 디렉터리 또는 파일 경로면 그대로 사용
       ② docs/examples/ch04/<arg>  (같은 폴더 하위)
       ③ scientific-skills/<arg>   (프로젝트 루트)
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        arg,
        os.path.join(here, arg),
    ]
    root = _project_root()
    if root:
        candidates.append(os.path.join(root, "scientific-skills", arg))

    for c in candidates:
        if os.path.isfile(c):
            return c
        skill_md = os.path.join(c, "SKILL.md")
        if os.path.isfile(skill_md):
            return skill_md
    sys.exit(f"❌ 스킬을 찾지 못했습니다. 탐색: {candidates}")


def strip_frontmatter(text):
    """YAML --- 블록을 제거하고 본문만 반환."""
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, flags=re.DOTALL)
    if m:
        return text[m.end():]
    return text


def call_llm(system_prompt, question, url, model, token,
             max_tokens=1024, temperature=0.2, timeout=180):
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    resp = requests.post(
        url, headers=headers, timeout=timeout,
        json={"model": model, "messages": messages,
              "max_tokens": max_tokens, "temperature": temperature},
    )
    if resp.status_code != 200:
        sys.exit(f"❌ API {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill", help="스킬 폴더/ID 또는 SKILL.md 경로")
    ap.add_argument("question", help="질문 문자열")
    ap.add_argument("--no-skill", action="store_true",
                    help="스킬 없이 호출 (비교용)")
    ap.add_argument("--model", default=DEFAULT_MODEL_KEY,
                    help=f"api_config.json 의 키 (기본 {DEFAULT_MODEL_KEY})")
    ap.add_argument("--show-prompt", action="store_true",
                    help="실제 system prompt 출력")
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    token = load_token()
    url, model = resolve_model(args.model)
    print(f"[MODEL ] {args.model} → {model}  @  {url}")

    if args.no_skill:
        system_prompt = ""
        print("[SKILL ] (없음 — 비교용)")
    else:
        skill_path = resolve_skill_path(args.skill)
        print(f"[SKILL ] {skill_path}")
        with open(skill_path, "r", encoding="utf-8") as f:
            raw = f.read()
        system_prompt = strip_frontmatter(raw)
        if args.show_prompt:
            print("\n----- SYSTEM PROMPT -----")
            print(system_prompt)
            print("------- END -------\n")

    print(f"\n[Q] {args.question}\n")
    answer = call_llm(system_prompt, args.question, url, model, token,
                      max_tokens=args.max_tokens,
                      temperature=args.temperature)
    print("[A]\n" + answer)


if __name__ == "__main__":
    main()
