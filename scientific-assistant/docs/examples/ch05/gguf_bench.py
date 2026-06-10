"""
Chapter 5 — GGUF 토큰 생성 속도(tok/s) 벤치마크.

같은 모델을 --n-gpu-layers 만 바꿔 두 번 돌리면 CPU vs GPU 효과를
정량으로 비교할 수 있다.

사용:
    # GPU 전부
    python gguf_bench.py --model model.gguf --n-gpu-layers 99

    # CPU 전부 (비교)
    python gguf_bench.py --model model.gguf --n-gpu-layers 0

    # 반복 측정
    python gguf_bench.py --model model.gguf --runs 3
"""
import argparse
import os
import sys
import time


DEFAULT_PROMPT = (
    "다음 작업을 수행하는 파이썬 함수를 작성하고 간단히 설명해줘: "
    "정수 리스트를 받아 짝수만 제곱해서 합을 반환."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="GGUF 경로")
    ap.add_argument("--n-ctx", type=int, default=4096)
    ap.add_argument("--n-gpu-layers", type=int, default=99)
    ap.add_argument("--n-batch", type=int, default=512)
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = ap.parse_args()

    if not os.path.isfile(args.model):
        sys.exit(f"❌ 파일 없음: {args.model}")

    try:
        from llama_cpp import Llama
    except ImportError:
        sys.exit("❌ llama-cpp-python 미설치 → pip install llama-cpp-python")

    print(f"모델: {os.path.basename(args.model)}")
    print(f"설정: n_ctx={args.n_ctx}, n_gpu_layers={args.n_gpu_layers}, "
          f"n_batch={args.n_batch}, max_tokens={args.max_tokens}")

    # --- 로드 시간 측정 ---
    t0 = time.time()
    kwargs = dict(model_path=args.model, n_ctx=args.n_ctx,
                  n_gpu_layers=args.n_gpu_layers, n_batch=args.n_batch,
                  verbose=False)
    try:
        llama = Llama(**kwargs)
    except TypeError:
        kwargs.pop("n_batch")
        llama = Llama(**kwargs)
    load_s = time.time() - t0
    print(f"\nload:   {load_s:.1f} s")

    prompt = args.prompt
    if "qwen" in os.path.basename(args.model).lower():
        prompt += "\n\n/no_think"

    speeds = []
    for r in range(args.runs):
        t0 = time.time()
        resp = llama.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=args.max_tokens,
        )
        dt = time.time() - t0
        usage = resp.get("usage", {})
        p_tok = usage.get("prompt_tokens", 0)
        g_tok = usage.get("completion_tokens", 0)
        tok_s = g_tok / dt if dt > 0 else 0
        speeds.append(tok_s)
        print(f"run {r + 1}: prompt={p_tok:>4} tok | "
              f"gen={g_tok:>4} tok in {dt:5.2f} s  →  {tok_s:6.1f} tok/s")

    if speeds:
        avg = sum(speeds) / len(speeds)
        print(f"\n평균 생성 속도: {avg:.1f} tok/s "
              f"({'GPU' if args.n_gpu_layers > 0 else 'CPU'} 기준)")


if __name__ == "__main__":
    main()
