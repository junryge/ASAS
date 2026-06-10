"""
Chapter 5 — 하이브리드 폴백 데모.

1순위: 사내 LLM API (http://common.llm.skhynix.com)
2순위: API 실패 시 로컬 GGUF 자동 로드

사용:
    # 정상: 사내 API 사용
    python hybrid_fallback.py "파이썬 quicksort 짜줘"

    # 사내 API 다운 상황 시뮬레이션 → 로컬 GGUF 폴백
    python hybrid_fallback.py "파이썬 quicksort 짜줘" --force-local

    # 로컬 GGUF 경로/옵션 지정
    python hybrid_fallback.py "..." --gguf model.gguf --n-gpu-layers 0
"""
import argparse
import glob
import os
import sys

import requests


API_URL = os.environ.get("LLM_BASE_URL", "http://common.llm.skhynix.com")
API_MODEL = os.environ.get("LLM_MODEL", "Qwen3-Coder-30B-A3B-Instruct")


def project_root():
    here = os.path.dirname(os.path.abspath(__file__))
    for up in (os.path.join(here, "..", "..", ".."), here):
        if os.path.isdir(os.path.join(up, "demos_v1")):
            return os.path.abspath(up)
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def load_token():
    here = os.path.dirname(__file__) or "."
    for d in (here, project_root()):
        for n in ("token.txt", "TOKEN.TXT"):
            p = os.path.join(d, n)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return f.read().strip()
    return ""


def try_remote(question, token, timeout=30):
    """사내 API 호출. 성공 시 (answer, None), 실패 시 (None, 이유)."""
    if not token:
        return None, "token.txt 없음"
    try:
        resp = requests.post(
            f"{API_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"model": API_MODEL,
                  "messages": [{"role": "user", "content": question}],
                  "max_tokens": 1024, "temperature": 0.3},
            timeout=timeout,
        )
    except requests.RequestException as e:
        return None, f"네트워크 오류: {e}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text[:120]}"
    return resp.json()["choices"][0]["message"]["content"], None


def find_local_gguf():
    root = project_root()
    files = []
    for sub in ("*.gguf", "models/*.gguf", "model/*.gguf"):
        files.extend(glob.glob(os.path.join(root, sub)))
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    files.sort(key=lambda f: os.path.getsize(f), reverse=True)
    return files[0] if files else None


def try_local(question, gguf_path, n_ctx, n_gpu_layers):
    """로컬 GGUF 폴백."""
    path = gguf_path or find_local_gguf()
    if not path:
        return None, "로컬 GGUF 파일 없음 (--gguf 로 지정 가능)"
    try:
        from llama_cpp import Llama
    except ImportError:
        return None, "llama-cpp-python 미설치"

    print(f"  [LOCAL] 로딩: {os.path.basename(path)} ...")
    kwargs = dict(model_path=path, n_ctx=n_ctx,
                  n_gpu_layers=n_gpu_layers, n_batch=512, verbose=False)
    try:
        llama = Llama(**kwargs)
    except TypeError:
        kwargs.pop("n_batch")
        llama = Llama(**kwargs)

    content = question
    if "qwen" in os.path.basename(path).lower():
        content += "\n\n/no_think"
    resp = llama.create_chat_completion(
        messages=[{"role": "user", "content": content}],
        temperature=0.3, max_tokens=1024,
    )
    return resp["choices"][0]["message"]["content"], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--force-local", action="store_true",
                    help="사내 API 를 건너뛰고 바로 로컬 폴백 (다운 시뮬레이션)")
    ap.add_argument("--gguf", help="로컬 GGUF 경로 (생략 시 자동 감지)")
    ap.add_argument("--n-ctx", type=int, default=4096)
    ap.add_argument("--n-gpu-layers", type=int, default=99)
    args = ap.parse_args()

    print(f"[Q] {args.question}\n")

    answer = None
    if not args.force_local:
        token = load_token()
        print("① 사내 API 시도...")
        answer, reason = try_remote(args.question, token)
        if answer:
            print("   ✅ 사내 API 성공\n")
            print("[A · remote]\n" + answer)
            return
        print(f"   ⚠️ 사내 API 실패: {reason}")
    else:
        print("① 사내 API 건너뜀 (--force-local)")

    print("② 로컬 GGUF 폴백...")
    answer, reason = try_local(args.question, args.gguf,
                               args.n_ctx, args.n_gpu_layers)
    if answer:
        print("   ✅ 로컬 폴백 성공\n")
        print("[A · local]\n" + answer)
    else:
        sys.exit(f"   ❌ 폴백도 실패: {reason}")


if __name__ == "__main__":
    main()
