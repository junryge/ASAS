# -*- coding: utf-8 -*-
"""
FlowBot Studio — RPA 워크플로우 실행 서버 (Windows 대상)
===========================================================
RPA_Workflow_Builder.html 에서 만든 워크플로우를 "실제로" 실행하는 백엔드.

실행 방법 (사용자 윈도우 PC):
    pip install -r requirements.txt
    python server.py
    → 브라우저에서 http://localhost:8600 접속

제공 기능:
  - GET  /                     : 빌더 화면(HTML) 서빙
  - POST /api/run              : 워크플로우 실제 실행 + 실시간 로그(SSE)
  - POST /api/stop             : 실행 중지
  - POST /api/save             : 워크플로우를 서버에 영구 저장(rpa_flow.json)
  - GET  /api/load             : 서버에 저장된 워크플로우 불러오기
  - 백그라운드 스케줄러          : 트리거(매일/매주 + 시각)에 맞춰 자동 실행

지원 노드:
  python, mouse, keyboard, wait, cmd, image, cond, loop, http,
  browser(URL 열기), download(파일 다운로드) ← 시나리오용 신규

날짜 변수(모든 텍스트/URL/파일명에서 치환 가능):
  {today}      → 오늘   (기본 %Y%m%d, 예: 20260714)
  {yesterday}  → 어제   (예: 20260713)
  {tomorrow}   → 내일
  {now}        → 현재시각
  포맷 지정:  {yesterday:%Y-%m-%d}, {today:%Y%m%d}, {now:%H%M%S} ...
"""

import os
import sys
import re
import json
import time
import queue
import threading
import subprocess
import tempfile
import datetime
import webbrowser
from pathlib import Path

# ── 선택적 의존성 (윈도우에서 설치; 없으면 해당 노드만 비활성) ──────────────
try:
    import requests
except Exception:
    requests = None
try:
    import pyautogui
    pyautogui.FAILSAFE = True   # 마우스를 화면 좌상단 구석으로 옮기면 비상정지
except Exception:
    pyautogui = None
try:
    import pyperclip            # 한글 등 비ASCII 타이핑용
except Exception:
    pyperclip = None

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
    import uvicorn
except Exception:
    print("[!] fastapi/uvicorn 가 필요합니다.  pip install -r requirements.txt")
    raise

# ── 경로/설정 ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
HTML_FILE  = BASE_DIR / "RPA_Workflow_Builder.html"
FLOW_FILE  = BASE_DIR / "rpa_flow.json"          # 서버측 영구 저장 파일
DOWNLOAD_DIR = BASE_DIR / "downloads"            # 다운로드 기본 폴더
PORT       = 8600

DOWNLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="FlowBot RPA Engine")

# 실행 상태 (단일 사용자 로컬 도구이므로 전역 1개면 충분)
STATE = {"running": False, "stop": False}
# SSE 이벤트를 스케줄러 자동실행과 공유하기 위한 브로드캐스트 큐 목록
_LISTENERS = []
_LISTENERS_LOCK = threading.Lock()


# ── 날짜 변수 치환 ───────────────────────────────────────────────────────────
def render_vars(text):
    """문자열 안의 {today}/{yesterday}/{tomorrow}/{now}[:포맷] 을 실제 날짜로 치환."""
    if not isinstance(text, str) or "{" not in text:
        return text
    now = datetime.datetime.now()
    bases = {
        "today":     now,
        "yesterday": now - datetime.timedelta(days=1),
        "tomorrow":  now + datetime.timedelta(days=1),
        "now":       now,
    }
    def repl(m):
        key = m.group(1)
        fmt = m.group(2)
        base = bases[key]
        if fmt:
            try:
                return base.strftime(fmt)
            except Exception:
                return m.group(0)
        # 기본 포맷: now 는 시각까지, 나머지는 YYYYMMDD
        return base.strftime("%Y%m%d%H%M%S") if key == "now" else base.strftime("%Y%m%d")
    return re.sub(r"\{(today|yesterday|tomorrow|now)(?::([^}]+))?\}", repl, text)


# ── 로그 이벤트 헬퍼 ─────────────────────────────────────────────────────────
def ev(level, text):
    return {"level": level, "text": text}


# ── 개별 노드 실행 (제너레이터: 로그 이벤트를 순차 yield) ─────────────────────
def run_node(node):
    typ = node.get("type")
    c = {k: v for k, v in (node.get("config") or {}).items()}

    # ---- Python 스크립트 ----
    if typ == "python":
        code = render_vars(c.get("code", "") or "")
        name = c.get("name", "스크립트")
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            proc = subprocess.run([sys.executable, tmp], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  timeout=600)
            if proc.stdout and proc.stdout.strip():
                for ln in proc.stdout.rstrip().splitlines():
                    yield ev("run", "   │ " + ln)
            if proc.stderr and proc.stderr.strip():
                for ln in proc.stderr.rstrip().splitlines():
                    yield ev("err", "   │ " + ln)
            if proc.returncode == 0:
                yield ev("ok", f"   ✓ [{name}] 실행 완료 (exit 0)")
            else:
                yield ev("err", f"   ✗ [{name}] 종료 코드 {proc.returncode}")
        except subprocess.TimeoutExpired:
            yield ev("err", "   ✗ 시간 초과(600s)로 중단")
        except Exception as e:
            yield ev("err", f"   ✗ 실행 오류: {e}")
        finally:
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except Exception: pass

    # ---- 마우스 ----
    elif typ == "mouse":
        if pyautogui is None:
            yield ev("err", "   ✗ pyautogui 미설치 — 마우스 제어 불가")
            return
        action = c.get("action", "click")
        x, y = int(c.get("x", 0)), int(c.get("y", 0))
        try:
            pyautogui.moveTo(x, y, duration=0.2)
            if action == "click":
                pyautogui.click(x, y)
            elif action == "double":
                pyautogui.doubleClick(x, y)
            elif action == "right":
                pyautogui.rightClick(x, y)
            label = {"move": "이동", "click": "클릭", "double": "더블클릭",
                     "right": "우클릭"}.get(action, action)
            yield ev("ok", f"   ✓ 마우스 {label} → ({x}, {y})")
        except Exception as e:
            yield ev("err", f"   ✗ 마우스 오류: {e}")

    # ---- 키보드 ----
    elif typ == "keyboard":
        if pyautogui is None:
            yield ev("err", "   ✗ pyautogui 미설치 — 키보드 제어 불가")
            return
        mode = c.get("mode", "type")
        value = render_vars(c.get("value", "") or "")
        try:
            if mode == "hotkey":
                keys = [k.strip() for k in value.split("+") if k.strip()]
                pyautogui.hotkey(*keys)
                yield ev("ok", f"   ✓ 단축키 전송 [{value}]")
            else:
                # 비ASCII(한글 등)는 클립보드 붙여넣기로 처리
                if any(ord(ch) > 127 for ch in value) and pyperclip is not None:
                    pyperclip.copy(value)
                    pyautogui.hotkey("ctrl", "v")
                    yield ev("ok", f'   ✓ 붙여넣기 입력: "{value}"')
                else:
                    pyautogui.write(value, interval=0.02)
                    yield ev("ok", f'   ✓ 입력 완료: "{value}"')
        except Exception as e:
            yield ev("err", f"   ✗ 키보드 오류: {e}")

    # ---- 대기 ----
    elif typ == "wait":
        try:
            secs = float(c.get("seconds", 1))
        except Exception:
            secs = 1.0
        yield ev("wait", f"   … {secs}초 대기 중")
        end = time.time() + secs
        while time.time() < end:
            if STATE["stop"]:
                yield ev("err", "   ✗ 대기 중 중지됨")
                return
            time.sleep(0.1)
        yield ev("ok", f"   ✓ {secs}초 대기 완료")

    # ---- CMD ----
    elif typ == "cmd":
        command = render_vars(c.get("command", "") or "")
        try:
            enc = "cp949" if os.name == "nt" else "utf-8"
            proc = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, encoding=enc, errors="replace",
                                  timeout=300)
            out = (proc.stdout or "").rstrip()
            err = (proc.stderr or "").rstrip()
            if out:
                for ln in out.splitlines():
                    yield ev("run", "   │ " + ln)
            if err:
                for ln in err.splitlines():
                    yield ev("err", "   │ " + ln)
            yield ev("ok" if proc.returncode == 0 else "err",
                     f"   ✓ 프로세스 종료 (return {proc.returncode})")
        except subprocess.TimeoutExpired:
            yield ev("err", "   ✗ CMD 시간 초과(300s)")
        except Exception as e:
            yield ev("err", f"   ✗ CMD 오류: {e}")

    # ---- 이미지 인식 ----
    elif typ == "image":
        if pyautogui is None:
            yield ev("err", "   ✗ pyautogui 미설치 — 이미지 인식 불가")
            return
        mode = c.get("mode", "find")
        target = render_vars(c.get("target", "") or "")
        try:
            if mode == "capture":
                fname = target or f"screenshot_{render_vars('{now}')}.png"
                path = str(DOWNLOAD_DIR / Path(fname).name)
                pyautogui.screenshot(path)
                yield ev("ok", f"   ✓ 화면 캡처 저장 → {path}")
            else:
                try:
                    conf = float(c.get("confidence", 0.8))
                except Exception:
                    conf = 0.8
                try:
                    loc = pyautogui.locateCenterOnScreen(target, confidence=conf)
                except TypeError:
                    # opencv 미설치 시 confidence 미지원 → 정확 매칭
                    loc = pyautogui.locateCenterOnScreen(target)
                if loc:
                    yield ev("ok", f"   ✓ 매칭 성공 → ({int(loc[0])}, {int(loc[1])})")
                else:
                    yield ev("err", f"   ✗ 이미지를 찾지 못함: {target}")
        except Exception as e:
            yield ev("err", f"   ✗ 이미지 오류: {e}")

    # ---- HTTP 요청 ----
    elif typ == "http":
        if requests is None:
            yield ev("err", "   ✗ requests 미설치 — HTTP 불가")
            return
        method = (c.get("method", "GET") or "GET").upper()
        url = render_vars(c.get("url", "") or "")
        try:
            t0 = time.time()
            r = requests.request(method, url, timeout=30)
            dt = int((time.time() - t0) * 1000)
            yield ev("ok", f"   ✓ 응답 {r.status_code} {r.reason} ({dt}ms, {len(r.content)} bytes)")
        except Exception as e:
            yield ev("err", f"   ✗ HTTP 오류: {e}")

    # ---- 브라우저 열기 (신규) ----
    elif typ == "browser":
        url = render_vars(c.get("url", "") or "")
        try:
            webbrowser.open(url)
            yield ev("ok", f"   ✓ 브라우저 열기: {url}")
        except Exception as e:
            yield ev("err", f"   ✗ 브라우저 오류: {e}")

    # ---- 파일 다운로드 (신규 · 시나리오 핵심) ----
    # JupyterLab: 파일 우클릭 → "Copy Download Link" 의 /files/ URL 을 붙여넣고
    # 날짜 부분만 {today}/{yesterday}/{tomorrow} 로 바꾸면 매일 자동 다운로드됨.
    elif typ == "download":
        if requests is None:
            yield ev("err", "   ✗ requests 미설치 — 다운로드 불가")
            return
        from urllib.parse import unquote
        try:
            requests.packages.urllib3.disable_warnings()
        except Exception:
            pass
        url = render_vars(c.get("url", "") or "")
        url = requests.utils.requote_uri(url)   # 한글/특수문자(|,공백 등) 안전 인코딩, 기존 %XX 는 보존
        save_dir = render_vars(c.get("save_dir", "") or "") or str(DOWNLOAD_DIR)
        filename = render_vars(c.get("filename", "") or "")
        token = render_vars(c.get("token", "") or "")     # Jupyter 토큰(있으면)
        cookie = render_vars(c.get("cookie", "") or "")    # 로그인 세션 쿠키(있으면)
        if not filename:
            filename = unquote(os.path.basename(url.split("?")[0])) or "download.bin"
        try:
            os.makedirs(save_dir, exist_ok=True)
            headers = {}
            if token:
                headers["Authorization"] = f"token {token}"
            if cookie:
                headers["Cookie"] = cookie
            yield ev("run", f"   │ GET {url}")
            with requests.get(url, headers=headers, stream=True, timeout=60,
                              verify=False) as r:
                r.raise_for_status()
                ctype = r.headers.get("Content-Type", "")
                # HTML 로그인 페이지가 오면(=인증 필요) CSV 대신 그게 저장되므로 경고
                if "text/html" in ctype:
                    yield ev("err", "   ✗ 응답이 HTML 입니다 — 로그인/인증이 필요할 수 있습니다."
                                    " (쿠키 또는 토큰 필요)")
                dest = os.path.join(save_dir, filename)
                total = 0
                with open(dest, "wb") as fp:
                    for chunk in r.iter_content(chunk_size=65536):
                        if STATE["stop"]:
                            yield ev("err", "   ✗ 다운로드 중지됨")
                            return
                        if chunk:
                            fp.write(chunk)
                            total += len(chunk)
                yield ev("ok", f"   ✓ 다운로드 완료 → {dest} ({total:,} bytes)")
        except Exception as e:
            yield ev("err", f"   ✗ 다운로드 오류: {e}")

    # ---- 조건/반복은 엔진 레벨에서 처리 (여기 도달 시 정보성 로그) ----
    elif typ == "cond":
        yield ev("sys", "   · 조건 노드")
    elif typ == "loop":
        yield ev("sys", "   · 반복 노드")
    else:
        yield ev("err", f"   ✗ 알 수 없는 노드 타입: {typ}")


# ── 조건식 안전 평가 ─────────────────────────────────────────────────────────
def eval_condition(expr):
    expr = render_vars(expr or "")
    safe = {"__builtins__": {}}
    ctx = {"True": True, "False": False, "None": None,
           "true": True, "false": False, "result": True}
    try:
        return bool(eval(expr, safe, ctx))
    except Exception:
        return False


# ── 워크플로우 실행 엔진 (제너레이터) ────────────────────────────────────────
DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"]


def trigger_text(t):
    mode = (t or {}).get("mode", "manual")
    tm = (t or {}).get("time", "09:00")
    if mode == "daily":
        return f"매일 {tm}"
    if mode == "weekly":
        days = sorted((t or {}).get("days", []))
        labels = "·".join(DAY_LABELS[d] for d in days) if days else "—"
        return f"매주 {labels} {tm}"
    return "수동 실행 / Manual"


def execute_workflow(nodes, trigger):
    """워크플로우를 순차 실행하며 로그 이벤트를 yield."""
    STATE["stop"] = False
    STATE["running"] = True
    try:
        yield ev("sys", "━━━ 워크플로우 실행 시작 ━━━")
        yield ev("run", f"⏰ 트리거: {trigger_text(trigger)}")
        n = len(nodes)
        i = 0
        while i < n:
            if STATE["stop"]:
                yield ev("err", "■ 사용자에 의해 중지되었습니다.")
                break
            node = nodes[i]
            typ = node.get("type")

            # 반복: 바로 다음 스텝 1개를 count회 실행
            if typ == "loop":
                try:
                    count = int((node.get("config") or {}).get("count", 1))
                except Exception:
                    count = 1
                if i + 1 < n:
                    target = nodes[i + 1]
                    tlabel = target.get("type")
                    yield ev("run", f"↻ 반복 시작: 다음 [{tlabel}] 스텝을 {count}회")
                    for r in range(count):
                        if STATE["stop"]:
                            break
                        yield ev("run", f"  ─ 반복 {r + 1}/{count}")
                        for e in run_node(target):
                            yield e
                    yield ev("ok", f"   ✓ {count}회 반복 완료")
                    i += 2
                else:
                    yield ev("err", "   ✗ 반복할 다음 스텝이 없습니다.")
                    i += 1
                continue

            # 조건: false 면 바로 다음 스텝 1개를 건너뜀
            if typ == "cond":
                cond = (node.get("config") or {}).get("condition", "")
                ok = eval_condition(cond)
                yield ev("run", f"◆ 조건 평가: {cond}  →  {ok}")
                if ok:
                    yield ev("ok", "   ✓ TRUE → 다음 스텝 진행")
                    i += 1
                else:
                    skip = nodes[i + 1].get("type") if i + 1 < n else "-"
                    yield ev("wait", f"   · FALSE → 다음 [{skip}] 스텝 건너뜀")
                    i += 2
                continue

            # 일반 노드
            t_label = node.get("type")
            summary = ""
            cfg = node.get("config") or {}
            yield ev("run", f"▶ [{t_label}] " + _node_summary(node))
            for e in run_node(node):
                yield e
            i += 1

        if not STATE["stop"]:
            yield ev("sys", "━━━ 실행 완료 ✓ ━━━")
    finally:
        STATE["running"] = False
        STATE["stop"] = False


def _node_summary(node):
    c = node.get("config") or {}
    typ = node.get("type")
    if typ == "python":   return c.get("name", "스크립트")
    if typ == "mouse":    return f"({c.get('x')}, {c.get('y')})"
    if typ == "keyboard": return str(c.get("value", ""))
    if typ == "wait":     return f"sleep({c.get('seconds')})"
    if typ == "cmd":      return "$ " + str(c.get("command", ""))
    if typ == "image":    return str(c.get("target", ""))
    if typ == "http":     return f"{c.get('method')} {c.get('url')}"
    if typ == "browser":  return render_vars(str(c.get("url", "")))
    if typ == "download":
        from urllib.parse import unquote
        url = render_vars(str(c.get("url", "")))
        fn = render_vars(str(c.get("filename", ""))) or unquote(os.path.basename(url.split("?")[0]))
        return f"{fn}"
    return typ


# ── SSE 스트리밍 실행 ────────────────────────────────────────────────────────
def _sse(gen):
    for event in gen:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/", response_class=HTMLResponse)
def index():
    if not HTML_FILE.exists():
        return HTMLResponse("<h1>RPA_Workflow_Builder.html 을 찾을 수 없습니다.</h1>",
                            status_code=404)
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))


@app.post("/api/run")
async def api_run(request: Request):
    if STATE["running"]:
        return JSONResponse({"error": "이미 실행 중입니다."}, status_code=409)
    data = await request.json()
    nodes = data.get("nodes", [])
    trigger = data.get("trigger", {})
    return StreamingResponse(_sse(execute_workflow(nodes, trigger)),
                             media_type="text/event-stream")


@app.post("/api/stop")
def api_stop():
    STATE["stop"] = True
    return {"ok": True}


@app.post("/api/save")
async def api_save(request: Request):
    data = await request.json()
    payload = {
        "version": 1,
        "nodes": data.get("nodes", []),
        "trigger": data.get("trigger", {}),
        "savedAt": int(time.time() * 1000),
    }
    FLOW_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return {"ok": True, "path": str(FLOW_FILE), "steps": len(payload["nodes"])}


@app.get("/api/load")
def api_load():
    if not FLOW_FILE.exists():
        return JSONResponse({"error": "저장된 워크플로우가 없습니다."}, status_code=404)
    return JSONResponse(json.loads(FLOW_FILE.read_text(encoding="utf-8")))


@app.get("/api/status")
def api_status():
    return {"running": STATE["running"], "stop": STATE["stop"]}


# ── 백그라운드 스케줄러 ──────────────────────────────────────────────────────
def _scheduler_loop():
    """저장된 워크플로우의 트리거(매일/매주 + 시각)에 맞춰 자동 실행."""
    last_fire_minute = None
    while True:
        try:
            time.sleep(20)
            if STATE["running"]:
                continue
            if not FLOW_FILE.exists():
                continue
            flow = json.loads(FLOW_FILE.read_text(encoding="utf-8"))
            trig = flow.get("trigger") or {}
            mode = trig.get("mode", "manual")
            if mode not in ("daily", "weekly"):
                continue
            now = datetime.datetime.now()
            hhmm = now.strftime("%H:%M")
            if hhmm != trig.get("time", "09:00"):
                continue
            # 같은 분에 중복 실행 방지
            minute_key = now.strftime("%Y%m%d%H%M")
            if minute_key == last_fire_minute:
                continue
            if mode == "weekly":
                # Python weekday(): 월=0..일=6  →  UI(일=0..토=6)로 변환
                ui_dow = (now.weekday() + 1) % 7
                if ui_dow not in trig.get("days", []):
                    continue
            last_fire_minute = minute_key
            print(f"[scheduler] {hhmm} 자동 실행 시작 ({trigger_text(trig)})")
            for _ in execute_workflow(flow.get("nodes", []), trig):
                pass  # 자동 실행 로그는 콘솔로만 (필요시 확장)
            print("[scheduler] 자동 실행 종료")
        except Exception as e:
            print(f"[scheduler] 오류: {e}")


def main():
    print("=" * 60)
    print("  FlowBot Studio — RPA 실행 서버")
    print("=" * 60)
    print(f"  화면 접속 : http://localhost:{PORT}")
    print(f"  저장 파일 : {FLOW_FILE}")
    print(f"  다운로드  : {DOWNLOAD_DIR}")
    print(f"  pyautogui : {'OK' if pyautogui else '미설치(마우스/키보드/이미지 비활성)'}")
    print(f"  requests  : {'OK' if requests else '미설치(HTTP/다운로드 비활성)'}")
    print("=" * 60)
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
