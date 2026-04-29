"""
Chapter 2 헬스체크 스크립트.

두 가지 모드를 지원한다.

[A] 로컬 미니 서버 점검 (hello_llm.py / app.py)
    python smoke_test.py                # 기본 포트 10009 (app.py)
    python smoke_test.py --port 10010   # hello_llm.py

[B] 사내 LLM 엔드포인트 직접 점검 (token.txt 필요)
    python smoke_test.py --remote
    python smoke_test.py --remote --model Qwen3-Coder-30B-A3B-Instruct
    python smoke_test.py --remote --list   # 모델 목록만 출력

사내 엔드포인트 기본값: http://common.llm.skhynix.com
"""
import os
import sys
import json
import argparse
import urllib.request

import requests


REMOTE_BASE = os.environ.get("LLM_BASE_URL", "http://common.llm.skhynix.com")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "Qwen3-Coder-30B-A3B-Instruct")


def load_token():
    candidates = (
        "token.txt",
        "TOKEN.TXT",
        os.path.join("..", "..", "..", "token.txt"),
        os.path.join("..", "..", "..", "TOKEN.TXT"),
    )
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    return ""


def check_local(port):
    base = f"http://localhost:{port}"

    print(f"[1/2] GET {base}/ ... ", end="", flush=True)
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            body = r.read()
        print(f"OK ({r.status}, {len(body)} bytes)")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    print(f"[2/2] POST {base}/api/chat ... ", end="", flush=True)
    try:
        req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"message": "ping?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8"))
        print(f"OK ({r.status})")
        preview = (j.get("reply") or j.get("error") or "")[:200]
        print("   응답:", preview)
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_remote(model_id, list_only):
    token = load_token()
    if not token:
        print("FAIL: token.txt 가 없습니다.")
        return False

    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}

    print(f"[1/{2 if not list_only else 1}] GET {REMOTE_BASE}/v1/models ... ", end="", flush=True)
    try:
        r = requests.get(f"{REMOTE_BASE}/v1/models", headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        models = data.get("data", data) if isinstance(data, dict) else data
        names = [m.get("id", m) if isinstance(m, dict) else m for m in models]
        print(f"OK ({len(names)} models)")
        for i, n in enumerate(names):
            mark = " ← default" if n == model_id else ""
            print(f"   [{i:02d}] {n}{mark}")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    if list_only:
        return True

    print(f"[2/2] POST {REMOTE_BASE}/v1/chat/completions ({model_id}) ... ", end="", flush=True)
    try:
        r = requests.post(
            f"{REMOTE_BASE}/v1/chat/completions",
            headers=headers,
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "ping? 한 단어로 답해."}],
                "max_tokens": 32,
            },
            timeout=120,
        )
        if r.status_code != 200:
            print(f"FAIL: {r.status_code} {r.text[:200]}")
            return False
        answer = r.json()["choices"][0]["message"]["content"]
        print("OK")
        print("   응답:", answer[:200])
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=10009,
                    help="로컬 서버 포트 (기본 10009)")
    ap.add_argument("--remote", action="store_true",
                    help="사내 LLM 엔드포인트를 직접 점검")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"사용 모델 (기본: {DEFAULT_MODEL})")
    ap.add_argument("--list", action="store_true",
                    help="모델 목록만 조회 (--remote 와 함께 사용)")

    # 옛 사용법 호환:  python smoke_test.py 10010
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        sys.argv = [sys.argv[0], "--port", sys.argv[1]]

    args = ap.parse_args()

    if args.remote:
        ok = check_remote(args.model, args.list)
    else:
        ok = check_local(args.port)

    print("✅ 헬스체크 통과" if ok else "❌ 헬스체크 실패")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
