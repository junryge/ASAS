# -*- coding: utf-8 -*-
"""LLM 주소·모델이 맞는지 확인한다 — 404 가 왜 나는지 짚어 준다.

쓰는 법
    python llm_주소확인.py
    python llm_주소확인.py http://hcp.llm.skhynix.com/v1 gaia-Qwen3.5-397B-A17B

토큰은 화면에 안 찍는다. 아래 순서로 찾는다.
    ① 환경변수 LLM_API_KEY
    ② ../avatar_2d/token.txt
    ③ config.json 의 llm.api_key_file 이 가리키는 파일

표준 라이브러리만 쓴다 (폐쇄망).
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # real_time_amhs


def find_key():
    v = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if v:
        return v.strip(), "환경변수"
    for p, why in ((os.path.join(ROOT, "avatar_2d", "token.txt"), "avatar_2d/token.txt"),
                   (os.path.join(ROOT, "token.txt"), "token.txt")):
        if os.path.isfile(p):
            try:
                s = open(p, encoding="utf-8").read().strip()
                if s:
                    return s, why
            except OSError:
                pass
    try:
        cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
        f = (cfg.get("llm") or {}).get("api_key_file")
        if f:
            p = f if os.path.isabs(f) else os.path.join(ROOT, f)
            if os.path.isfile(p):
                s = open(p, encoding="utf-8").read().strip()
                if s:
                    return s, os.path.basename(p)
    except Exception:      # noqa: BLE001
        pass
    return "", "(못 찾음)"


def cfg_default():
    """config.json 에서 주소·모델을 읽어 위키가 쓸 꼴로 바꾼다."""
    try:
        cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
    except Exception:      # noqa: BLE001
        return "", ""
    lc = cfg.get("llm") or {}
    url = str(lc.get("url") or "")
    # 관제는 전체 주소를 적어 둔다 — 위키는 base 만 받는다
    base = url.split("/chat/completions")[0].rstrip("/")
    return base, str(lc.get("model") or "")


def call(base, model, key, timeout=30):
    """(성공?, 설명)"""
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "max_tokens": 8,
                       "messages": [{"role": "user", "content": "1+1은?"}]}
                      ).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=body, headers=h)
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(req, timeout=timeout) as r:
            json.loads(r.read().decode("utf-8"))
        return True, "OK"
    except urllib.error.HTTPError as e:
        return False, "HTTP {} · {}".format(
            e.code, e.read().decode("utf-8", "replace")[:200].replace("\n", " "))
    except Exception as e:      # noqa: BLE001
        return False, "{}: {}".format(type(e).__name__, e)


def models(base, key, timeout=20):
    url = base.rstrip("/") + "/models"
    h = {}
    if key:
        h["Authorization"] = "Bearer " + key
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [m.get("id") for m in (d.get("data") or []) if m.get("id")], ""
    except urllib.error.HTTPError as e:
        return [], "HTTP {}".format(e.code)
    except Exception as e:      # noqa: BLE001
        return [], "{}: {}".format(type(e).__name__, e)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else ""
    model = sys.argv[2] if len(sys.argv) > 2 else ""
    d_base, d_model = cfg_default()
    base = (base or d_base).rstrip("/")
    model = model or d_model
    key, key_src = find_key()

    print("=" * 62)
    print("  주소 : {}".format(base or "(없음)"))
    print("  모델 : {}".format(model or "(없음)"))
    print("  토큰 : {} ({}자)".format(key_src, len(key)))
    print("=" * 62)
    if not base:
        print("\n  config.json 을 못 읽었다. 주소를 인자로 줘라:")
        print("    python llm_주소확인.py http://hcp.llm.skhynix.com/v1 <모델명>")
        return 1

    # ── ① 후보 주소를 차례로 두들긴다 ────────────────────────────────
    cands, seen = [], set()
    for b in (base,
              base + "/v1",
              base[: -len("/v1")].rstrip("/") if base.endswith("/v1") else base,
              base.split("/chat/completions")[0].rstrip("/")):
        b = b.rstrip("/")
        if b and b not in seen:
            seen.add(b)
            cands.append(b)

    print("\n[1] 주소 후보를 하나씩 불러 본다")
    good = None
    for b in cands:
        ok, why = call(b, model, key)
        print("   {:<48} {}".format(b + "/chat/completions",
                                    "✅ OK" if ok else "❌ " + why))
        if ok and good is None:
            good = b

    # ── ② 모델 목록 ──────────────────────────────────────────────────
    print("\n[2] 이 서버가 아는 모델")
    ms, err = models(good or base, key)
    if err:
        print("   못 받음 ({}) — /models 를 안 여는 게이트웨이일 수 있다".format(err))
    else:
        for m in ms[:20]:
            print("   {} {}".format("→" if m == model else " ", m))
        if model and ms and model not in ms:
            print("\n   ★ '{}' 은 이 목록에 없다 — 모델명이 404 의 원인이다".format(model))

    # ── ③ 결론 ───────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    if good:
        print("  위키 [설정] 에 이렇게 넣어라")
        print("     API Base URL : {}".format(good))
        print("     모델명        : {}".format(model))
        print("     API Key      : {} 의 내용".format(key_src))
    else:
        print("  전부 실패했다. 위 오류를 보고 판단한다:")
        print("    HTTP 404  → 주소 끝이 /v1 인지 · 모델명이 목록에 있는지")
        print("    HTTP 401/403 → 토큰 문제")
        print("    HTTP 400  → 모델명 오타")
        print("    Timeout/URLError → 이 PC 에서 그 주소가 안 열린다 (방화벽·프록시)")
    print("=" * 62)
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
