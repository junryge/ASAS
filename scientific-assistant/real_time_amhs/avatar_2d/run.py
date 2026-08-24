#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 2D 감정캐릭터 × LLM  —  실행 진입점   (Python 3.8+, 표준 라이브러리만)
=============================================================================

 파이썬이 앱의 중심이다.
   avatar/config.py    스케줄·FAB·알람 등급·의상·배경·사원증 등 모든 설정
   avatar/llm.py       프롬프트 조립 · response_format 폴백 · 스트리밍 파싱
   avatar/docs.py      참고 자료 보관 + 검색 주입
   avatar/sessions.py  세션 보관 (서버 디스크 — 어느 PC 에서 접속해도 같다)
   avatar/server.py    HTTP 서버 (static/ + /api/* + /v1 프록시)
   static/             index.html · app.css · app.js · assets/ (그림 파일)
   data/               런타임 저장소 (settings.json · sessions.json · docs.json)

 실행하면
   1) token.txt 에서 토큰을 읽고
   2) 엔드포인트를 고르게 하고
   3) /v1/models 로 모델 목록을 받아 고르게 한 다음
   4) 앱을 띄운다. 브라우저 설정은 자동으로 채워진다.

 [실행]                python run.py
 [선택 건너뛰기]       python run.py --upstream http://hcp.llm.skhynix.com --model <모델명>
 [token.txt]           같은 폴더에 두면 자동. 다른 곳이면 --token-file <경로>
 [외부 접속]           기본 0.0.0.0:8585. 혼자만 쓰려면 --local-only
=============================================================================
"""
import argparse
import json
import os
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from avatar import __version__                      # noqa: E402
from avatar import config as cfgmod                 # noqa: E402
from avatar.server import App, Handler, Server, build_opener, lan_ips  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  토큰 / 선택 메뉴
# ═══════════════════════════════════════════════════════════════════════════
def read_token(token_file):
    candidates = []
    if token_file:
        candidates.append(Path(token_file))
    candidates += [BASE_DIR / "token.txt", Path.cwd() / "token.txt"]
    for p in candidates:
        try:
            if p.is_file():
                tok = p.read_text(encoding="utf-8-sig").strip()
                if tok:
                    return tok, str(p)
        except Exception:
            pass
    tok = (os.environ.get("LLM_TOKEN") or os.environ.get("OPENAI_API_KEY") or "").strip()
    return tok, ("환경변수" if tok else "")


def mask(t):
    return (t[:6] + "..." + t[-4:]) if len(t) > 12 else (t or "(없음)")


def ask(prompt, default):
    try:
        v = input(prompt).strip()
    except EOFError:
        print(prompt + str(default) + "   (기본값)")
        return default
    except KeyboardInterrupt:
        print("")
        sys.exit(0)
    return v or default


def choose_endpoint(preset):
    if preset:
        base = preset.strip().rstrip("/")
        return base if base.endswith("/v1") else base + "/v1"

    print("  ── API 엔드포인트 ────────────────────────────────────")
    for i, (url, label) in enumerate(cfgmod.ENDPOINTS, 1):
        print("   [{}] {:<34} {}".format(i, url, label))
    print("   [{}] 직접 입력".format(len(cfgmod.ENDPOINTS) + 1))
    print("")
    sel = ask("  번호 선택 [1] : ", "1")
    if sel.isdigit() and 1 <= int(sel) <= len(cfgmod.ENDPOINTS):
        base = cfgmod.ENDPOINTS[int(sel) - 1][0]
    elif sel.isdigit() and int(sel) == len(cfgmod.ENDPOINTS) + 1:
        base = ask("  주소 입력 (예: http://hcp.llm.skhynix.com) : ",
                   cfgmod.ENDPOINTS[0][0])
    else:
        base = sel
    base = base.strip().rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def fetch_models(upstream, token, opener):
    print("")
    print("  모델 목록 조회 중 ...  {}".format(upstream + "/models"))
    req = urllib.request.Request(
        upstream.rstrip("/") + "/models",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=30) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        print("")
        print("  [!] 모델 목록 실패 : HTTP {}".format(e.code))
        if e.code in (401, 403):
            print("      토큰이 잘못됐거나 만료됐습니다. token.txt 를 확인하세요.")
        elif e.code == 404:
            print("      이 엔드포인트에 /v1/models 가 없습니다. 주소를 확인하세요.")
        if body.strip():
            print("      " + body.replace("\n", " "))
        return []
    except Exception as e:  # noqa: BLE001
        print("")
        print("  [!] 연결 실패 : {}".format(e))
        print("      사내망(VPN) 연결 상태와 주소를 확인하세요.")
        return []

    if isinstance(raw, dict):
        raw = raw.get("data", raw)
    if not isinstance(raw, list):
        return []
    out = []
    for m in raw:
        mid = (m.get("id") or m.get("model") or m.get("name")) \
            if isinstance(m, dict) else str(m)
        if mid:
            out.append(str(mid))
    return sorted(set(out), key=str.lower)


def choose_model(models, preset):
    if preset:
        return preset
    if not models:
        return ask("  모델 이름을 직접 입력 : ", "gpt-4o-mini")
    print("")
    print("  ── 모델 ({}개) ──────────────────────────────────────".format(len(models)))
    for i, m in enumerate(models, 1):
        print("   [{:>2}] {}".format(i, m))
    print("")
    sel = ask("  번호 선택 [1] : ", "1")
    if sel.isdigit() and 1 <= int(sel) <= len(models):
        return models[int(sel) - 1]
    return sel


# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="2D 감정캐릭터 서버 (파이썬 중심)")
    ap.add_argument("--port", type=int, default=8585, help="포트 (기본 8585)")
    ap.add_argument("--host", default="0.0.0.0",
                    help="바인드 주소 (기본 0.0.0.0 = 외부 접속 허용)")
    ap.add_argument("--local-only", action="store_true", help="127.0.0.1 로만 바인드")
    ap.add_argument("--token-file", default="",
                    help="토큰 파일 경로 (기본: 같은 폴더 token.txt)")
    ap.add_argument("--upstream", default="", help="엔드포인트 지정 시 선택 화면 생략")
    ap.add_argument("--model", default="", help="모델 지정 시 선택 화면 생략")
    ap.add_argument("--no-browser", action="store_true", help="브라우저 자동 실행 안 함")
    ap.add_argument("--sentinel", default="",
                    help="관제(real_time_amhs) 서버 주소 (기본 http://127.0.0.1:8989)")
    args = ap.parse_args()
    if args.sentinel:
        from avatar import config as _cfg
        _cfg.SENTINEL["url"] = args.sentinel.rstrip("/")

    if not (BASE_DIR / "static" / "index.html").is_file():
        print("\n  [!] static/index.html 이 없습니다. 압축을 통째로 풀었는지 확인하세요.")
        print("      현재 폴더: {}\n".format(BASE_DIR))
        sys.exit(1)

    print("")
    print("  ══ 2D 감정캐릭터 서버 ({}) ═══════════════════".format(__version__))
    print("")

    token, src = read_token(args.token_file)
    if not token:
        print("  [!] 토큰을 찾을 수 없습니다.")
        print("      이 폴더에 token.txt 를 두거나  --token-file <경로> 로 지정하세요.")
        print("      폴더: {}\n".format(BASE_DIR))
        sys.exit(1)
    print("  토큰   {}   ({})".format(mask(token), src))
    print("")

    upstream = choose_endpoint(args.upstream)
    opener = build_opener(upstream)
    models = fetch_models(upstream, token, opener)
    model = choose_model(models, args.model)

    App.init(BASE_DIR)
    App.connect(upstream, token, model, models)

    host = "127.0.0.1" if args.local_only else args.host
    url = "http://localhost:{}/".format(args.port)
    print("")
    print("  ┌──────────────────────────────────────────────────────")
    print("  │  앱        {}".format(url))
    if host not in ("127.0.0.1", "localhost"):
        for ip in lan_ips():
            print("  │  외부      http://{}:{}/".format(ip, args.port))
    print("  │  엔드포인트 {}".format(upstream))
    print("  │  모델      {}".format(model))
    print("  │  토큰      {}".format(mask(token)))
    print("  │  저장소    {}".format(App.data_dir))
    print("  └──────────────────────────────────────────────────────")
    print("")
    print("  브라우저가 열리면 바로 대화하면 됩니다. (설정은 자동으로 채워집니다)")
    if host not in ("127.0.0.1", "localhost"):
        print("  다른 PC에서는 위 '외부' 주소로 접속하세요.")
        print("  윈도우 방화벽에서 python.exe 의 {} 포트 인바운드 허용이 필요할 수 있습니다."
              .format(args.port))
    print("  종료: Ctrl+C")
    print("")

    try:
        httpd = Server((host, args.port), Handler)
    except OSError as e:
        print("  [!] {}:{} 를 열 수 없습니다: {}".format(host, args.port, e))
        print("      다른 포트로:  python run.py --port 8686\n")
        sys.exit(1)

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  종료합니다.\n")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
