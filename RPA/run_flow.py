# -*- coding: utf-8 -*-
"""
FlowBot RPA — 단독 실행 스크립트 (웹 UI / 서버 없이 동작)
============================================================
브라우저(웹 화면)가 보안정책으로 00시에 종료돼도, 이 파이썬 프로세스는
살아남아 워크플로우를 그대로 실행한다.

사용법 (윈도우 CMD):
    python run_flow.py            → 스케줄러 모드 (config.json 의 run_times 에 자동 실행)
    python run_flow.py --now      → 지금 즉시 1회 실행 (테스트용)
    python run_flow.py --now --flow 다른파일.json

읽는 파일 (이 스크립트와 같은 폴더):
    rpa_flow.json   워크플로우 (빌더에서 저장한 그 파일 그대로)
    config.json     비밀번호 / 실행시각 / 재시도 / 화면유지 설정

로그:
    화면 출력 + run_flow.log 파일에 기록
"""

import os
import re
import sys
import json
import time
import base64
import shutil
import datetime
import tempfile
import argparse
import threading
import subprocess
import webbrowser
from pathlib import Path

# ── 선택적 의존성 ────────────────────────────────────────────────────────────
try:
    import requests
except Exception:
    requests = None
try:
    import pyautogui
    pyautogui.FAILSAFE = True      # 마우스를 화면 좌상단 구석으로 옮기면 비상정지
except Exception:
    pyautogui = None
try:
    import pyperclip               # 한글 등 비ASCII 타이핑용
except Exception:
    pyperclip = None

BASE_DIR    = Path(__file__).resolve().parent
FLOW_FILE   = BASE_DIR / "rpa_flow.json"
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE    = BASE_DIR / "run_flow.log"
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

CONFIG = {}
if CONFIG_FILE.exists():
    try:
        CONFIG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[!] config.json 을 읽지 못했습니다(주석/문법 확인): {e}")

STATE = {"running": False, "fatal": False, "last_pos": None}


# ── 로그 ─────────────────────────────────────────────────────────────────────
def log(text):
    line = f"{datetime.datetime.now():%H:%M:%S}  {text}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n")
    except Exception:
        pass


# ── 날짜 변수 치환  {today} {yesterday} {tomorrow} {now} [:포맷] ──────────────
def render_vars(text):
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
        key, fmt = m.group(1), m.group(2)
        base = bases[key]
        if fmt:
            try:
                return base.strftime(fmt)
            except Exception:
                return m.group(0)
        return base.strftime("%Y%m%d%H%M%S") if key == "now" else base.strftime("%Y%m%d")
    return re.sub(r"\{(today|yesterday|tomorrow|now)(?::([^}]+))?\}", repl, text)


# ── 크롬/엣지 실행파일 찾기 ──────────────────────────────────────────────────
def find_browser(kind):
    kind = (kind or "chrome").lower()
    cfg = CONFIG.get(kind + "_path")
    if cfg and os.path.exists(cfg):
        return cfg
    if kind == "chrome":
        names = ["chrome"]
        paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                 os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]
    elif kind == "edge":
        names = ["msedge"]
        paths = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    else:
        return None
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    for p in paths:
        if os.path.exists(p):
            return p
    return None


# ── 노드별 실행 ──────────────────────────────────────────────────────────────
def node_summary(node):
    c = node.get("config") or {}
    t = node.get("type")
    if t == "python":   return c.get("name", "스크립트")
    if t == "mouse":    return f"({c.get('x')}, {c.get('y')})"
    if t == "keyboard": return render_vars(str(c.get("value", "")))
    if t == "wait":     return f"sleep({c.get('seconds')})"
    if t == "cmd":      return "$ " + render_vars(str(c.get("command", "")))
    if t == "image":    return str(c.get("target", ""))
    if t == "http":     return f"{c.get('method')} {c.get('url')}"
    if t == "browser":  return render_vars(str(c.get("url", "")))
    if t == "download":
        url = render_vars(str(c.get("url", "")))
        return render_vars(str(c.get("filename", ""))) or os.path.basename(url.split("?")[0])
    return t


def run_node(node):
    t = node.get("type")
    c = dict(node.get("config") or {})

    # ---- Python 스크립트 ----
    if t == "python":
        code = render_vars(c.get("code", "") or "")
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            p = subprocess.run([sys.executable, tmp], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
            for ln in (p.stdout or "").rstrip().splitlines():
                log("   │ " + ln)
            for ln in (p.stderr or "").rstrip().splitlines():
                log("   │ " + ln)
            if p.returncode == 0:
                log(f"   ✓ [{c.get('name','스크립트')}] 실행 완료")
            else:
                STATE["fatal"] = True
                log(f"   ✗ 종료 코드 {p.returncode}")
        except Exception as e:
            STATE["fatal"] = True
            log(f"   ✗ 실행 오류: {e}")
        finally:
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except Exception: pass

    # ---- 마우스 ----
    elif t == "mouse":
        if pyautogui is None:
            log("   ✗ pyautogui 미설치"); return
        action = c.get("action", "click")
        if (c.get("source", "") or "xy").lower() == "found":
            pos = STATE.get("last_pos")
            if not pos:
                STATE["fatal"] = True
                log("   ✗ 직전에 찾은 이미지 위치가 없습니다"); return
            x, y = pos
        else:
            x, y = int(c.get("x", 0)), int(c.get("y", 0))
        try:
            pyautogui.moveTo(x, y, duration=0.2)
            if action == "click":    pyautogui.click(x, y)
            elif action == "double": pyautogui.doubleClick(x, y)
            elif action == "right":  pyautogui.rightClick(x, y)
            log(f"   ✓ 마우스 {action} → ({x}, {y})")
        except Exception as e:
            log(f"   ✗ 마우스 오류: {e}")

    # ---- 키보드 ----
    elif t == "keyboard":
        if pyautogui is None:
            log("   ✗ pyautogui 미설치"); return
        mode = c.get("mode", "type")
        value = render_vars(c.get("value", "") or "")
        try:
            if mode == "hotkey":
                keys = [k.strip() for k in value.split("+") if k.strip()]
                pyautogui.hotkey(*keys)
                log(f"   ✓ 단축키 [{value}]")
            else:
                if any(ord(ch) > 127 for ch in value) and pyperclip is not None:
                    pyperclip.copy(value)
                    pyautogui.hotkey("ctrl", "v")
                    log(f'   ✓ 붙여넣기 입력: "{value}"')
                else:
                    pyautogui.write(value, interval=0.02)
                    log(f'   ✓ 입력: "{value}"')
        except Exception as e:
            log(f"   ✗ 키보드 오류: {e}")

    # ---- 대기 ----
    elif t == "wait":
        try:    secs = float(c.get("seconds", 1))
        except Exception: secs = 1.0
        log(f"   … {secs}초 대기")
        time.sleep(secs)

    # ---- CMD ----
    elif t == "cmd":
        cmd = render_vars(c.get("command", "") or "")
        try:
            enc = "cp949" if os.name == "nt" else "utf-8"
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               encoding=enc, errors="replace", timeout=300)
            for ln in (p.stdout or "").rstrip().splitlines():
                log("   │ " + ln)
            for ln in (p.stderr or "").rstrip().splitlines():
                log("   │ " + ln)
            log(f"   ✓ 프로세스 종료 (return {p.returncode})")
        except Exception as e:
            log(f"   ✗ CMD 오류: {e}")

    # ---- 이미지 인식 ----
    elif t == "image":
        if pyautogui is None:
            log("   ✗ pyautogui 미설치"); return
        mode = c.get("mode", "find")
        target = render_vars(c.get("target", "") or "")
        if mode == "capture":
            try:
                path = str(DOWNLOAD_DIR / (Path(target).name or f"screenshot_{render_vars('{now}')}.png"))
                pyautogui.screenshot(path)
                log(f"   ✓ 화면 캡처 → {path}")
            except Exception as e:
                log(f"   ✗ 캡처 오류: {e}")
            return
        # 저장파일의 base64 이미지를 임시 PNG 로 복원해 매칭
        tmp_img, search = None, target
        data = c.get("imageData", "") or ""
        if isinstance(data, str) and data.startswith("data:"):
            try:
                raw = base64.b64decode(data.split(",", 1)[1])
                with tempfile.NamedTemporaryFile("wb", suffix="_" + (Path(target).name or "t.png"),
                                                 delete=False) as f:
                    f.write(raw); tmp_img = f.name
                search = tmp_img
            except Exception as e:
                log(f"   │ 이미지 디코드 실패: {e}")
        if not search or (tmp_img is None and not os.path.exists(search)):
            STATE["fatal"] = True
            log(f"   ✗ 기준 이미지가 없습니다: {target}")
            return
        try:    conf = float(c.get("confidence", 0.8))
        except Exception: conf = 0.8
        loc = None
        try:
            try:
                loc = pyautogui.locateCenterOnScreen(search, confidence=conf)
            except TypeError:
                loc = pyautogui.locateCenterOnScreen(search)
        except Exception as e:
            log(f"   │ 이미지 탐색 오류: {e}")
        if tmp_img and os.path.exists(tmp_img):
            try: os.unlink(tmp_img)
            except Exception: pass
        if loc:
            x, y = int(loc[0]), int(loc[1])
            STATE["last_pos"] = (x, y)
            action = (c.get("action", "") or "move").lower()
            try:
                if action in ("move", "click", "double"):
                    pyautogui.moveTo(x, y, duration=0.3)
                if action == "click":    pyautogui.click(x, y)
                elif action == "double": pyautogui.doubleClick(x, y)
            except Exception as e:
                log(f"   │ 이동/클릭 오류: {e}")
            log(f"   ✓ 매칭 → {action} → ({x}, {y})")
        else:
            STATE["fatal"] = True
            log(f"   ✗ 화면에서 이미지를 찾지 못함: {target}")

    # ---- HTTP ----
    elif t == "http":
        if requests is None:
            log("   ✗ requests 미설치"); return
        method = (c.get("method", "GET") or "GET").upper()
        url = render_vars(c.get("url", "") or "")
        try:
            r = requests.request(method, url, timeout=30, verify=False)
            log(f"   ✓ 응답 {r.status_code} ({len(r.content)} bytes)")
        except Exception as e:
            log(f"   ✗ HTTP 오류: {e}")

    # ---- 브라우저 열기 ----
    elif t == "browser":
        url = render_vars(c.get("url", "") or "")
        which = (c.get("browser", "") or "chrome").lower()
        try:
            opened = False
            if which in ("chrome", "edge"):
                path = find_browser(which)
                if path:
                    subprocess.Popen([path, url]); opened = True
                    log(f"   ✓ {which} 로 열기: {url}")
                else:
                    log(f"   │ {which} 실행파일을 못 찾음 — 기본 브라우저 사용")
            if not opened:
                webbrowser.open(url)
                log(f"   ✓ 브라우저 열기: {url}")
        except Exception as e:
            log(f"   ✗ 브라우저 오류: {e}")

    # ---- 파일 다운로드 (Jupyter 자동 로그인 포함) ----
    elif t == "download":
        if requests is None:
            STATE["fatal"] = True
            log("   ✗ requests 미설치"); return
        from urllib.parse import unquote, urlparse
        try: requests.packages.urllib3.disable_warnings()
        except Exception: pass
        url = requests.utils.requote_uri(render_vars(c.get("url", "") or ""))
        save_dir = render_vars(c.get("save_dir", "") or "") or str(DOWNLOAD_DIR)
        filename = render_vars(c.get("filename", "") or "") or \
                   unquote(os.path.basename(url.split("?")[0])) or "download.bin"
        password = render_vars(c.get("password", "") or "") or CONFIG.get("jupyter_password", "")
        try:
            os.makedirs(save_dir, exist_ok=True)
            sess = requests.Session()
            if password:
                try:
                    pu = urlparse(url)
                    login_url = f"{pu.scheme}://{pu.netloc}/login"
                    rg = sess.get(login_url, verify=False, timeout=30)
                    mx = re.search(r'name="_xsrf"[^>]*value="([^"]+)"', rg.text)
                    data = {"password": password}
                    if mx: data["_xsrf"] = mx.group(1)
                    sess.post(login_url, data=data, verify=False, timeout=30)
                    log("   │ Jupyter 로그인 시도 완료")
                except Exception as e:
                    log(f"   │ 로그인 오류: {e}")
            log(f"   │ GET {url}")
            with sess.get(url, stream=True, timeout=60, verify=False) as r:
                r.raise_for_status()
                if "text/html" in r.headers.get("Content-Type", "").lower():
                    STATE["fatal"] = True
                    log("   ✗ 실패: CSV 가 아니라 HTML(로그인 페이지)을 받았습니다 — 비밀번호 확인")
                    return
                dest = os.path.join(save_dir, filename)
                total = 0
                with open(dest, "wb") as fp:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            fp.write(chunk); total += len(chunk)
                log(f"   ✓ 다운로드 완료 → {dest} ({total:,} bytes)")
        except Exception as e:
            STATE["fatal"] = True
            log(f"   ✗ 다운로드 오류: {e}")

    else:
        log(f"   ✗ 알 수 없는 노드 타입: {t}")


# ── 워크플로우 실행 (실패 시 처음부터 재시도) ────────────────────────────────
def execute_flow(flow):
    nodes = flow.get("nodes", [])
    max_retries = int(CONFIG.get("max_retries", 0)) if CONFIG.get("retry_on_fail") else 0
    STATE["running"] = True
    try:
        attempt = 0
        while True:
            STATE["fatal"] = False
            log("━━━ 워크플로우 실행 시작 ━━━" if attempt == 0
                else f"━━━ 처음부터 다시 시도 ({attempt}/{max_retries}) ━━━")
            for node in nodes:
                if STATE["fatal"]:
                    break
                log(f"▶ [{node.get('type')}] {node_summary(node)}")
                try:
                    run_node(node)
                except Exception as e:
                    STATE["fatal"] = True
                    log(f"   ✗ 노드 오류: {e}")
                if STATE["fatal"]:
                    log("   ✗ 이 스텝에서 실패 — 중단")
                    break
            if STATE["fatal"] and attempt < max_retries:
                attempt += 1
                log("⟳ 실패 감지 — 5초 후 처음부터 다시 시도")
                time.sleep(5)
                continue
            log("━━━ 최종 실패 (재시도 소진) ━━━" if STATE["fatal"] else "━━━ 실행 완료 ✓ ━━━")
            return not STATE["fatal"]
    finally:
        STATE["running"] = False
        STATE["fatal"] = False


# ── 화면 유지 (절전/잠금 방지) ───────────────────────────────────────────────
def keepawake_loop():
    interval = int(CONFIG.get("keep_awake_interval", 60))
    dist = int(CONFIG.get("keep_awake_dist", 3))
    while True:
        try:
            time.sleep(max(5, interval))
            if pyautogui is None or STATE.get("running"):
                continue          # RPA 실행 중엔 절대 개입하지 않음
            x, y = pyautogui.position()
            pyautogui.moveTo(x + dist, y, duration=0.1)
            pyautogui.moveTo(x, y, duration=0.1)
            if CONFIG.get("keep_awake_click"):
                pos = CONFIG.get("keep_awake_click_pos")
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    pyautogui.click(int(pos[0]), int(pos[1]))
                else:
                    pyautogui.click()
        except Exception:
            pass


# ── 스케줄러 ─────────────────────────────────────────────────────────────────
def scheduler_loop(flow_path):
    times = CONFIG.get("run_times") or ["00:20"]
    log(f"스케줄러 시작 — 실행 시각: {', '.join(times)}")
    last = None
    while True:
        try:
            time.sleep(20)
            now = datetime.datetime.now()
            hhmm = now.strftime("%H:%M")
            if hhmm not in times:
                continue
            key = now.strftime("%Y%m%d%H%M")
            if key == last:
                continue
            last = key
            log(f"⏰ {hhmm} 자동 실행 시작")
            flow = json.loads(Path(flow_path).read_text(encoding="utf-8"))
            execute_flow(flow)
        except Exception as e:
            log(f"[스케줄러 오류] {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true", help="지금 즉시 1회 실행")
    ap.add_argument("--flow", default=str(FLOW_FILE), help="워크플로우 json 경로")
    args = ap.parse_args()

    print("=" * 62)
    print("  FlowBot RPA — 단독 실행 스크립트 (웹 없이 동작)")
    print("=" * 62)
    print(f"  워크플로우 : {args.flow}")
    print(f"  pyautogui  : {'OK' if pyautogui else '미설치(마우스/키보드/이미지 비활성)'}")
    print(f"  requests   : {'OK' if requests else '미설치(다운로드 비활성)'}")
    print(f"  실행 시각  : {', '.join(CONFIG.get('run_times') or ['00:20'])}")
    print(f"  재시도     : {'ON x' + str(CONFIG.get('max_retries', 0)) if CONFIG.get('retry_on_fail') else 'OFF'}")
    print(f"  화면유지   : {'ON' if CONFIG.get('keep_awake') else 'OFF'}")
    print("=" * 62)

    if not os.path.exists(args.flow):
        log(f"[!] 워크플로우 파일이 없습니다: {args.flow}")
        return

    if CONFIG.get("keep_awake"):
        threading.Thread(target=keepawake_loop, daemon=True).start()

    if args.now:
        flow = json.loads(Path(args.flow).read_text(encoding="utf-8"))
        execute_flow(flow)
        return

    scheduler_loop(args.flow)


if __name__ == "__main__":
    main()
