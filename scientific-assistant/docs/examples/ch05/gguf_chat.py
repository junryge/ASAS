"""
Chapter 5 — 로컬 GGUF 모델을 로드해 CLI 에서 대화하는 데모.

scientific-assistant/demos_v1/gguf.py 의 find_gguf_files() / load_gguf_model()
패턴을 독립 실행 가능하게 추린 학습용 코드.

사용:
    # 자동 감지 (프로젝트 폴더의 *.gguf 검색)
    python gguf_chat.py

    # 경로 직접 지정
    python gguf_chat.py --model /path/to/Qwen2.5-7B-Q4_K_M.gguf

    # CPU 강제 / 컨텍스트 축소 (메모리 부족 시)
    python gguf_chat.py --model model.gguf --n-gpu-layers 0 --n-ctx 8192
"""
import argparse
import glob
import os
import sys
import time


def project_root():
    """demos_v1 가 보이는 상위 폴더를 프로젝트 루트로 간주."""
    here = os.path.dirname(os.path.abspath(__file__))
    for up in (os.path.join(here, "..", "..", ".."), here):
        if os.path.isdir(os.path.join(up, "demos_v1")):
            return os.path.abspath(up)
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def find_gguf_files():
    """gguf.py 와 동일한 3개 경로에서 *.gguf 검색 (mmproj 제외)."""
    root = project_root()
    patterns = [
        os.path.join(root, "*.gguf"),
        os.path.join(root, "models", "*.gguf"),
        os.path.join(root, "model", "*.gguf"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    files = [f for f in files if "mmproj" not in os.path.basename(f).lower()]
    out = []
    for f in files:
        out.append({"path": f, "name": os.path.basename(f),
                    "size_gb": round(os.path.getsize(f) / 1e9, 1)})
    out.sort(key=lambda x: x["size_gb"], reverse=True)
    return out


def pick_model(arg_model):
    if arg_model:
        if not os.path.isfile(arg_model):
            sys.exit(f"❌ 파일 없음: {arg_model}")
        return arg_model
    found = find_gguf_files()
    if not found:
        sys.exit("❌ *.gguf 파일을 찾지 못했습니다. --model 로 경로를 지정하세요.\n"
                 "   탐색 경로: 프로젝트 루트, ./models, ./model")
    print("=== 감지된 GGUF ===")
    for i, f in enumerate(found):
        print(f"  [{i}] {f['name']} ({f['size_gb']} GB)")
    if len(found) == 1:
        print(f"→ 자동 선택: {found[0]['name']}")
        return found[0]["path"]
    while True:
        raw = input("모델 번호 선택: ").strip()
        if raw.isdigit() and 0 <= int(raw) < len(found):
            return found[int(raw)]["path"]


def load_model(path, n_ctx, n_gpu_layers, n_batch):
    try:
        from llama_cpp import Llama
    except ImportError:
        sys.exit("❌ llama-cpp-python 미설치 → pip install llama-cpp-python")

    print(f"\n모델 로딩 중: {os.path.basename(path)} "
          f"(n_ctx={n_ctx}, n_gpu_layers={n_gpu_layers})...")
    t0 = time.time()
    kwargs = dict(model_path=path, n_ctx=n_ctx,
                  n_gpu_layers=n_gpu_layers, n_batch=n_batch, verbose=False)
    # Qwen3 계열은 flash_attn 가속
    if "qwen3" in os.path.basename(path).lower():
        try:
            llama = Llama(**kwargs, flash_attn=True)
            print("  ⚡ flash_attn=True")
        except TypeError:
            llama = Llama(**kwargs)
    else:
        try:
            llama = Llama(**kwargs)
        except TypeError:
            kwargs.pop("n_batch")
            llama = Llama(**kwargs)
    print(f"  ✅ 로드 완료 ({time.time() - t0:.1f}s)\n")
    return llama


def is_qwen(path):
    return "qwen" in os.path.basename(path).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="GGUF 경로 (생략 시 자동 감지)")
    ap.add_argument("--n-ctx", type=int, default=8192)
    ap.add_argument("--n-gpu-layers", type=int, default=99,
                    help="99=전부 GPU, 0=전부 CPU, 중간=하이브리드")
    ap.add_argument("--n-batch", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=0.5)
    ap.add_argument("--max-tokens", type=int, default=1024)
    args = ap.parse_args()

    path = pick_model(args.model)
    llama = load_model(path, args.n_ctx, args.n_gpu_layers, args.n_batch)

    history = []
    print("'quit' 종료, 'reset' 히스토리 초기화\n")
    while True:
        try:
            q = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() == "quit":
            break
        if q.lower() == "reset":
            history.clear()
            print("  (히스토리 초기화)")
            continue

        content = q
        # Qwen3 reasoning 끄기 (토큰/시간 절약)
        if is_qwen(path):
            content = q + "\n\n/no_think"
        history.append({"role": "user", "content": content})

        t0 = time.time()
        resp = llama.create_chat_completion(
            messages=history,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        dt = time.time() - t0
        answer = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        gen = usage.get("completion_tokens", 0)
        speed = f"{gen / dt:.1f} tok/s" if dt > 0 and gen else ""
        history.append({"role": "assistant", "content": answer})
        print(f"\n답변 ({dt:.1f}s, {speed}):\n{answer}\n")

    print("👋 종료")


if __name__ == "__main__":
    main()
