"""
Chapter 2 헬스체크 스크립트.

서버(app.py 또는 hello_llm.py)가 정상 동작하는지 확인한다.

사용:
    python smoke_test.py            # 기본 포트 10009 (app.py)
    python smoke_test.py 10010      # hello_llm.py 용
"""
import sys
import json
import urllib.request


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10009
    base = f"http://localhost:{port}"

    # [1/2] 인덱스 페이지가 응답하는가
    print(f"[1/2] GET {base}/ ... ", end="", flush=True)
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            body = r.read()
        print(f"OK ({r.status}, {len(body)} bytes)")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    # [2/2] /api/chat 이 응답하는가
    print(f"[2/2] POST {base}/api/chat ... ", end="", flush=True)
    try:
        req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"message": "ping?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode("utf-8"))
        print(f"OK ({r.status})")
        preview = (j.get("reply") or j.get("error") or "")[:120]
        print("   응답:", preview)
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    print("✅ 헬스체크 통과")


if __name__ == "__main__":
    main()
