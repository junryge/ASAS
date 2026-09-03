# -*- coding: utf-8 -*-
"""
HTTP 서버 — 정적 파일(static/) + 앱 API(/api/*) + LLM 프록시(/v1/*).

  GET  /api/config           앱 시작 설정 (모델 + 스케줄/FAB/의상/배경 전부)
  GET  /api/settings         서버측 설정 (자료 예산 등)
  POST /api/settings         설정 변경
  POST /api/chat             LLM 대화 (프롬프트 조립은 파이썬이. stream 가능)
  POST /api/ctx              컨텍스트 사용량 추정
  GET  /api/docs             자료 목록
  POST /api/docs             {op:add|toggle|delete|clear, ...}
  POST /api/costume          의상 그림 저장 (브라우저에서 끌어다 놓은 png)
  GET  /api/sessions         세션 전체
  PUT  /api/sessions         세션 전체 저장 (한도는 서버가 강제)
  GET  /api/sessions/md?id=  세션 하나를 Markdown 으로
  /v1/*                      게이트웨이 원시 프록시 (토큰은 서버만 안다)
"""
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer

from . import commands, config, csvdata, docs, harness, llm, mcp_client, \
    sentinel, sessions, settings, skills, terms

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
    "Access-Control-Max-Age": "86400",
}


# ── 의상 그림 저장 ────────────────────────────────────────────────────────
# 브라우저에서 그림을 끌어다 놓으면 예전엔 data URL 로 **메모리에만** 들고
# 있었다. 새로고침하면 사라지고, config.py 에 적어 둔 의상과도 이어지지 않아
# 같은 그림인데 칩이 두 개가 됐다. 여기서 static/assets/ 에 파일로 남긴다.
#
# ★핸들러 밖의 함수로 둔다 — 소켓을 띄우지 않고 테스트할 수 있어야 한다.
_IMG_MAGIC = ((b"\x89PNG\r\n\x1a\n", ".png"),
              (b"\xff\xd8\xff", ".jpg"),
              (b"RIFF", ".webp"))
IMG_MAX = 12 * 1024 * 1024


def save_costume_image(static_dir, filename, data):
    """끌어다 놓은 그림을 assets/ 에 저장한다.

    반환 {ok, src, slot, bytes} 또는 {error, code}.
    slot 은 config.COSTUMES 에서 그 src 를 쓰는 자리(없으면 -1) — 미리 적어 둔
    의상의 그림을 채운 것이면 새 칩을 만들지 말라는 뜻이다.
    """
    import base64
    data = str(data or "")
    if data[:5] == "data:" and "," in data:
        data = data.split(",", 1)[1]
    try:
        blob = base64.b64decode(data, validate=True)
    except Exception:                                  # noqa: BLE001
        return {"error": "그림 데이터를 읽지 못했습니다", "code": 400}
    if not blob:
        return {"error": "빈 파일입니다", "code": 400}
    if len(blob) > IMG_MAX:
        return {"error": "그림이 너무 큽니다 (최대 12MB)", "code": 413}

    # ★확장자를 믿지 않는다 — 앞머리(매직 바이트)로 실제 형식을 본다.
    #   evil.png 라고 이름만 바꾼 스크립트가 assets 에 남으면 안 된다.
    ext = next((e for magic, e in _IMG_MAGIC if blob.startswith(magic)), "")
    if not ext:
        return {"error": "png · jpg · webp 만 넣을 수 있습니다", "code": 400}

    # ★파일명은 **바탕이름만** 쓰고 글자도 추린다. 브라우저가 준 이름을 그대로
    #   쓰면 '../../avatar/config.py' 같은 것이 들어온다.
    stem = os.path.splitext(os.path.basename(str(filename or "")))[0]
    stem = re.sub(r"[^A-Za-z0-9가-힣._-]", "_", stem).strip("._-")[:40] or "costume"
    assets = os.path.join(str(static_dir or ""), "assets")
    try:
        os.makedirs(assets, exist_ok=True)
        dest = os.path.join(assets, stem + ext)
        # 정말 assets 안인지 다시 본다 (심볼릭 링크·상대경로 방어)
        if os.path.dirname(os.path.realpath(dest)) != os.path.realpath(assets):
            return {"error": "잘못된 파일 이름입니다", "code": 400}
        with open(dest, "wb") as f:
            f.write(blob)
    except OSError as e:
        return {"error": f"저장하지 못했습니다: {e}", "code": 500}

    src = "assets/" + stem + ext
    slot = next((i for i, c in enumerate(config.COSTUMES)
                 if c.get("src") == src), -1)
    return {"ok": True, "src": src, "slot": slot, "bytes": len(blob)}


class App:
    """서버 전역 상태 — run.py 가 채운다."""
    upstream = ""
    token = ""
    model = ""
    models = []
    timeout = 180
    opener = None
    base_dir = None      # dist/
    static_dir = None    # dist/static
    data_dir = None      # dist/data

    doc_store = None
    sess_store = None
    settings = None
    gateway = None

    skill_store = None
    mcp_hub = None       # 외부 도구 (MCP) — 질문에 걸릴 때만 띄운다

    @classmethod
    def init(cls, base_dir):
        cls.base_dir = base_dir
        cls.static_dir = base_dir / "static"
        cls.data_dir = base_dir / "data"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.doc_store = docs.DocStore(cls.data_dir / "docs.json")
        cls.sess_store = sessions.SessionStore(cls.data_dir / "sessions.json")
        cls.settings = settings.Settings(cls.data_dir / "settings.json")
        cls.skill_store = skills.SkillStore(cls.data_dir / "skills")
        # 도메인 지식을 스킬로 심는다 (있으면 안 건드림).
        # ★현장 스킬(m16_hub_skills)을 먼저 — 룰 한글명·용어 표준·임계값이
        #   거기 있다. 우리가 새로 쓰면 두 벌이 어긋난다.
        for nm in skills.seed_hub_skills(cls.skill_store, base_dir):
            sys.stdout.write("  스킬 시드: {} (현장 스킬)\n".format(nm))
        # 데이터 분석 방법은 데모스(scientific-skills)에 이미 있다 —
        # 새로 쓰지 말고 참고 자료로 등록해 둔다.
        for nm in docs.seed_docs(cls.doc_store, base_dir):
            sys.stdout.write("  참고 자료 시드: {}\n".format(nm))
        for nm in docs.seed_local_docs(cls.doc_store, base_dir):
            sys.stdout.write("  참고 자료 시드: {} (현장 자료)\n".format(nm))
        nm = docs.seed_column_dict(cls.doc_store, base_dir)
        if nm:
            sys.stdout.write("  참고 자료 시드: {} (감시 컬럼 뜻·임계)\n".format(nm))
        for nm in skills.seed_analysis_skills(cls.skill_store, base_dir):
            sys.stdout.write("  스킬 시드: {} (데이터 분석)\n".format(nm))
        if skills.seed_pio(cls.skill_store, base_dir):
            sys.stdout.write("  스킬 시드: pio-error (PIO 반송실패 해석)\n")
        if skills.seed_fab_score(cls.skill_store, base_dir):
            sys.stdout.write("  스킬 시드: fab-score (FAB별 위험도 스코어)\n")
        cls.mcp_hub = cls._make_hub(base_dir)
        sentinel.init(cls.data_dir)      # 알람 이력 (data/alarms.json)
        # ★브라우저가 열려 있을 때만 보면 감시가 아니다. 창을 닫아도, 아무도
        #   안 봐도 서버가 계속 본다 — 밤에 떴다 사라진 알람도 이력에 남는다.
        sec = float(config.SENTINEL.get("watch_sec", sentinel.WATCH_SEC) or 0)
        if sec > 0:
            sentinel.start_watch(sec, say=lambda s: sys.stdout.write(s + "\n"))
        else:
            sys.stdout.write("  상시 감시 꺼짐 (config.SENTINEL.watch_sec=0)\n")
        cls.uploads_dir = cls.data_dir / "uploads"
        cls.uploads_dir.mkdir(parents=True, exist_ok=True)
        cls.uploads = {}                 # {이름: {"summary","numbers"}} 분석 캐시

    @classmethod
    def _make_hub(cls, base_dir):
        """config.MCP_SERVERS → Hub. 여기서는 **띄우지 않는다** — 질문에
        걸릴 때 처음 뜬다. 안 물어보면 프로세스가 하나도 안 생긴다."""
        # 서버 스크립트 경로는 real_time_amhs 기준이다 (base_dir 은 avatar_2d)
        root = os.path.dirname(str(base_dir))
        srv = []
        for s in (getattr(config, "MCP_SERVERS", None) or []):
            s = dict(s)
            s["cwd"] = s.get("cwd") or root
            # ★바깥 환경변수가 이긴다. 요청관리가 다른 PC 에 있을 때
            #   (사내에서는 대개 그렇다) 코드를 고치게 만들면 안 된다 —
            #   run.py --qa 나 QA_BASE 환경변수로 준다.
            env = dict(s.get("env") or {})
            for k in list(env):
                if os.environ.get(k):
                    env[k] = os.environ[k]
            s["env"] = env
            # ★http 로 붙는 서버(위키)는 주소가 env 가 아니라 url 이다.
            #   같은 이유로 바깥 환경변수가 이겨야 한다 — 위키가 다른 PC 에
            #   떠 있을 때 코드를 고치게 만들면 안 된다.
            if s.get("url"):
                u = (os.environ.get("{}_MCP_URL".format(s["key"].upper()))
                     or s["url"]).strip()
                # ★끄는 길을 하나 열어 둔다. 안 떠 있는 서버 때문에 대화가
                #   느려질 때, 코드를 고치지 않고 바로 뗄 수 있어야 한다.
                if u.lower() in ("off", "none", "no", "0", ""):
                    s["enabled"] = False
                    s["off_reason"] = "실행 옵션(--wiki off)으로 껐습니다"
                    sys.stdout.write("  [i] MCP '{}' 끔 (요청대로)\n"
                                     .format(s.get("name") or s["key"]))
                s["url"] = u
            srv.append(s)
        # ★스크립트가 실제로 있는지 **켤 때** 본다. avatar_2d 를
        #   real_time_amhs 밖에 풀면 qa/mcp_server.py 가 없다 — 그러면
        #   물어볼 때마다 조용히 실패하고, 사용자는 "왜 안 되지" 만 반복한다.
        for s in srv:
            a = list(s.get("args") or [])
            if not a or not str(a[0]).endswith(".py"):
                continue
            path = a[0] if os.path.isabs(a[0]) \
                else os.path.join(s.get("cwd") or root, a[0])
            if os.path.isfile(path):
                s["args"] = [os.path.abspath(path)] + a[1:]
                continue
            s["enabled"] = False
            s["off_reason"] = "서버 파일이 없습니다: {}".format(path)
            sys.stdout.write(
                "  [!] MCP '{}' 끔 — 파일이 없습니다: {}\n"
                "      avatar_2d 를 real_time_amhs **안에** 두고 실행하세요.\n"
                .format(s.get("name") or s["key"], path))
        # ★화면(설정 → 외부 도구)에서 고친 값이 **마지막에** 얹힌다.
        #   코드 기본값 → 환경변수 → 화면. 사람이 화면에서 끈 것을 재시작이
        #   되살리면, 껐던 이유(느리다)를 또 겪는다.
        saved = App.settings.get("mcp") or {}
        for s in srv:
            v = saved.get(s["key"])
            if not isinstance(v, dict):
                continue
            if v.get("url") and s.get("url"):
                # ★화면에서 저장한 값이 코드 기본값을 이긴다. 그게 맞는데,
                #   **이기고 있다는 사실이 보여야** 한다. 실제로 겪었다:
                #   기본값을 8020 으로 되돌렸는데도 화면에 예전에 넣어 둔
                #   8100 이 남아 있어서 계속 HTML 404 가 났다. 코드를 아무리
                #   고쳐도 안 바뀌니 원인을 못 찾는다.
                if str(v["url"]) != s["url"]:
                    s["url_default"] = s["url"]
                s["url"] = str(v["url"])
            if "enabled" in v:
                # 파일이 없어서 꺼진 것은 화면이 못 켠다 — 켜 봐야 안 된다
                if v["enabled"] and s.get("off_reason", "").startswith("서버 파일"):
                    pass
                else:
                    s["enabled"] = bool(v["enabled"])
                    if not v["enabled"]:
                        s["off_reason"] = "화면에서 껐습니다"
        live = [s for s in srv if s.get("enabled", True)]
        for s in live:
            # ★어느 주소를 볼지 **켤 때 찍는다**. 안 찍으면 127.0.0.1 을 보고
            #   있는 줄 모르고 "왜 안 되지" 만 반복한다 (실제로 그랬다).
            addr = (s.get("url") or (s.get("env") or {}).get("QA_BASE")
                    or "(기본값)")
            sys.stdout.write("  MCP: {} → {}{}\n".format(
                s.get("name") or s["key"], addr,
                "  ※위키 쪽에서 mcp_server.py 를 띄워 둬야 붙는다"
                if s.get("transport") == "http" else ""))
        if live:
            sys.stdout.write("  MCP 서버 {}개 등록 (질문에 걸리면 그때 띄운다)\n"
                             .format(len(live)))
        return mcp_client.Hub(srv)

    @classmethod
    def connect(cls, upstream, token, model, models):
        cls.upstream, cls.token = upstream, token
        cls.model, cls.models = model, models
        cls.opener = build_opener(upstream)
        cls.gateway = llm.Gateway(upstream, token, cls.opener, cls.timeout)


def build_opener(upstream):
    """사내 주소는 시스템 프록시를 타면 오히려 막히는 경우가 많아 우회한다."""
    host = urllib.parse.urlparse(upstream).hostname or ""
    internal = ("skhynix" in host) or host in ("localhost", "127.0.0.1")
    handlers = []
    if internal:
        handlers.append(urllib.request.ProxyHandler({}))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE           # 사내 자체서명 인증서 대응
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def lan_ips():
    ips = []
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sk.connect(("8.8.8.8", 80))
        ips.append(sk.getsockname()[0])
        sk.close()
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


UPLOAD_MAX = 6 * 1024 * 1024      # 첨부 CSV 한도 6MB (화면의 CSV_MAX 와 같은 값)


def _looks_csv(text):
    """확장자가 없어도 표면 표다 — 머리줄과 다음 줄의 칸 수가 같고 2칸 이상."""
    lines = [l for l in str(text or "").splitlines()[:5] if l.strip()]
    if len(lines) < 2:
        return False
    n = lines[0].count(",")
    return n >= 1 and all(l.count(",") == n for l in lines[1:])


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(App.static_dir), **kw)

    def log_message(self, fmt, *args):
        pass

    def _say(self, msg):
        sys.stdout.write("  " + msg + "\n")
        sys.stdout.flush()

    # ── 공통 응답 ─────────────────────────────────────────────────────────
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _err(self, code, msg):
        self._json(code, {"error": {"message": msg}})

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _mcp_op(self, b):
        """설정 → 외부 도구(MCP) 의 버튼들.

        op = on | off | url | reconnect
        ★고친 값은 **서버에 저장한다**(data/settings.json). 재시작하면
          되돌아가면, 느려서 껐던 사람이 그 일을 또 겪는다.
        """
        hub = App.mcp_hub
        if hub is None:
            return self._json(200, {"ok": False, "error": "MCP 가 없습니다"})
        op = str((b or {}).get("op") or "").strip()
        key = str((b or {}).get("key") or "").strip()
        if op == "reconnect":
            hub.reconnect(key or None)
            return self._json(200, dict(hub.status(), did="reconnect"))
        s = hub.find(key)
        if s is None:
            return self._json(200, {"ok": False,
                                    "error": "모르는 서버: {}".format(key)})
        if op in ("on", "off"):
            on = op == "on"
            # ★파일이 없어서 꺼진 것은 켜 봐야 안 된다. 켜졌다고 해 놓고
            #   물어볼 때마다 실패하면, 사람은 다른 데를 뒤진다.
            if on and str(s.get("off_reason") or "").startswith("서버 파일"):
                return self._json(200, {"ok": False, "error": s["off_reason"]})
            hub.set_enabled(key, on)
            s["off_reason"] = "" if on else "화면에서 껐습니다"
            App.settings.update({"mcp": {key: {"enabled": on}}})
        elif op == "url":
            if not s.get("url"):
                return self._json(200, {"ok": False,
                                        "error": "이 서버는 주소로 붙지 않습니다"
                                                 " (자식 프로세스로 띄웁니다)"})
            hub.set_url(key, (b or {}).get("url"))
            App.settings.update({"mcp": {key: {"url": s["url"]}}})
        elif op == "url_default":
            # ★저장해 둔 주소를 지우고 코드 기본값으로. 없으면 못 돌아간다 —
            #   화면에 한 번 넣은 값이 영영 남아서 "코드를 고쳐도 안 바뀐다".
            d = s.get("url_default") or ""
            if not d:
                return self._json(200, {"ok": False,
                                        "error": "이 서버는 기본값이 따로 없습니다"})
            hub.set_url(key, d)
            s.pop("url_default", None)
            App.settings.update({"mcp": {key: {"url": ""}}})
        else:
            return self._json(200, {"ok": False,
                                    "error": "모르는 동작: {}".format(op)})
        return self._json(200, dict(hub.status(), did=op))

    def _save_costume(self, b):
        r = save_costume_image(App.static_dir, b.get("filename") or b.get("name"),
                               b.get("data"))
        if r.get("error"):
            return self._err(r.pop("code", 400), r["error"])
        return self._json(200, r)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def end_headers(self):
        if getattr(self, "_no_store", False):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    # ── GET ──────────────────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path in ("/api/config", "/__config"):
            return self._json(200, config.public_config(
                App.model, App.models, App.upstream))

        if path == "/api/settings":
            d = App.settings.all()
            # ★사용자가 '뭘 가르쳤는지' 볼 수 있어야 한다 — 지금 실제로 쓰이는
            #   규칙과 기본값을 같이 준다 (되돌리기 버튼이 기본값을 알아야 한다)
            d["agentRules"] = llm.agent_rules(d)
            d["agentRulesDefault"] = llm.AGENT_RULES
            d["agentRulesCustom"] = bool(str(d.get("agentRules") or "").strip()
                                         and d["agentRules"] != llm.AGENT_RULES)
            return self._json(200, d)

        if path == "/api/mcp":
            # ★MCP 가 붙었나를 **눈으로 볼 자리**. 없으면 "왜 안 되지" 를
            #   콘솔 로그로만 짚어야 한다 — 현장에서는 그게 안 된다.
            #   두들겨 보느라 몇 초 걸릴 수 있다 (죽은 서버는 3초).
            hub = App.mcp_hub
            if hub is None:
                return self._json(200, {"ok": True, "servers": [], "none": True})
            try:
                return self._json(200, hub.status())
            except Exception as e:  # noqa: BLE001
                return self._json(200, {"ok": False, "servers": [],
                                        "error": "{}: {}".format(
                                            type(e).__name__, e)})

        if path == "/api/docs":
            return self._json(200, {"docs": App.doc_store.list(),
                                    "budget": App.settings.get("docBudget")})

        if path == "/api/sessions":
            return self._json(200, {"sessions": App.sess_store.get_all()})

        # ── 관제 (real_time_amhs) ────────────────────────────────────────
        if path == "/api/fab/status":
            # 브라우저 알람 폴링. 서버 캐시 5초라 관제 서버엔 그 주기로만 간다.
            # ★watching 을 같이 준다 — 서버가 정말 상시로 보고 있는지 화면이
            #   알아야 한다. 스레드가 죽었는데 화면만 멀쩡하면 '보고 있는 줄'
            #   알고 넘어간다.
            return self._json(200, dict(sentinel.watch(),
                                        watching=sentinel.watch_status()))

        if path == "/api/fab/chart":
            # 화면 그래프 — 점수 막대 + 실제 컬럼의 임계 대비 실측값
            return self._json(200, sentinel.chart())

        if path == "/api/fab/diagnose":
            d = sentinel.diagnose()
            d["text"] = sentinel.diagnose_text()
            return self._json(200, d)

        if path == "/api/alarms":
            cfg = sentinel.alarm_config(App.settings.all())
            return self._json(200, {"alarms": sentinel.history(cfg["keep"]),
                                    "hold_min": cfg["hold_min"],
                                    "config": cfg,
                                    "cols": sentinel.CSV_COLS})

        if path == "/api/alarms/csv":
            # 엑셀이 바로 여는 CSV (BOM). 파일이 아니라 지금 기록에서 만든다 —
            # 내용을 나중에 고쳐도 받는 파일은 최신 상태여야 한다.
            body = sentinel.history_csv().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="fab_alarms.csv"')
            self.send_header("Content-Length", str(len(body)))
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
            return

        # ── 스킬 ─────────────────────────────────────────────────────────
        if path == "/api/skills":
            return self._json(200, {"skills": App.skill_store.list()})

        if path in ("/api/skills/md", "/api/skills/html"):
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1]
                                      if "?" in self.path else "")
            name = (q.get("name") or [""])[0]
            md = App.skill_store.read(name)
            if md is None:
                return self._err(404, "스킬 없음: " + name)
            if path.endswith("/md"):
                # ★전문 그대로 — 자르지 않는다
                return self._send(200, md.encode("utf-8"),
                                  "text/markdown; charset=utf-8")
            return self._send(200, skills.to_html(name, md).encode("utf-8"),
                              "text/html; charset=utf-8")

        if path in ("/api/sessions/md", "/api/sessions/html"):
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1]
                                      if "?" in self.path else "")
            sid = (q.get("id") or [""])[0]
            for s in App.sess_store.get_all():
                if s.get("id") == sid:
                    md = App.sess_store.to_markdown(s)
                    if path.endswith("/md"):
                        return self._send(200, md.encode("utf-8"),
                                          "text/markdown; charset=utf-8")
                    # 세션 공유용 단독 HTML — 스킬과 같은 변환기를 쓴다
                    title = "대화 기록 " + str(s.get("ts") or "")
                    return self._send(200,
                                      skills.to_html(title, md).encode("utf-8"),
                                      "text/html; charset=utf-8")
            return self._err(404, "세션 없음")

        if path.startswith("/v1"):
            return self._relay("GET", path[3:] or "/models", None)

        if path in ("/", "/index.html"):
            self.path = "/index.html"
            self._no_store = True
        if path.endswith((".html", ".js", ".css")):
            self._no_store = True
        return super().do_GET()

    # ── POST / PUT ───────────────────────────────────────────────────────
    def do_PUT(self):
        if self.path.split("?", 1)[0] == "/api/sessions":
            b = self._body()
            ok = App.sess_store.put_all(b.get("sessions"),
                                        deleted=b.get("deleted"))
            # 병합 결과를 돌려준다 — 브라우저가 다른 PC 세션까지 바로 본다
            return self._json(200 if ok else 400,
                              {"ok": ok,
                               "sessions": App.sess_store.get_all() if ok else []})
        return self._err(404, "알 수 없는 경로: " + self.path)

    def do_POST(self):
        path = self.path.split("?", 1)[0]

        if path == "/api/settings":
            d = App.settings.update(self._body())
            d["agentRules"] = llm.agent_rules(d)
            d["agentRulesDefault"] = llm.AGENT_RULES
            d["agentRulesCustom"] = d["agentRules"] != llm.AGENT_RULES
            return self._json(200, d)

        if path == "/api/mcp":
            return self._mcp_op(self._body())

        if path == "/api/costume":
            return self._save_costume(self._body())

        if path == "/api/docs":
            b = self._body()
            op = b.get("op")
            if op == "add":
                ok = App.doc_store.add(str(b.get("name", ""))[:120],
                                       b.get("text", ""))
            elif op == "toggle":
                ok = App.doc_store.toggle(b.get("name"), b.get("on"))
            elif op == "delete":
                ok = App.doc_store.delete(b.get("name"))
            elif op == "clear":
                App.doc_store.clear()
                ok = True
            else:
                return self._err(400, "op 는 add|toggle|delete|clear")
            return self._json(200, {"ok": bool(ok),
                                    "docs": App.doc_store.list()})

        if path == "/api/skills":
            b = self._body()
            op = b.get("op")
            if op == "save":
                name = str(b.get("name", "")).strip()
                md = b.get("md") or skills.compose(
                    name, b.get("description", ""), b.get("body", ""))
                ok, errors, warnings = App.skill_store.save(name, md)
                return self._json(200 if ok else 400,
                                  {"ok": ok, "errors": errors,
                                   "warnings": warnings})
            if op == "delete":
                return self._json(200, {"ok": App.skill_store.delete(
                    str(b.get("name", "")).strip())})
            if op == "validate":
                ok, errors, warnings = skills.validate(b.get("md", ""))
                return self._json(200, {"ok": ok, "errors": errors,
                                        "warnings": warnings})
            return self._err(400, "op 는 save|delete|validate")

        if path == "/api/alarms":
            # 알람 기록에 사람이 남기는 내용 — 해제 사유·조치.
            # ★기록만 있고 '무엇을 했는지' 가 없으면 나중에 아무 도움이 안 된다.
            b = self._body()
            op = str(b.get("op") or "").strip()
            if op == "note":
                n = sentinel.note(str(b.get("id") or ""), b.get("text"))
                return self._json(200, {"ok": bool(n), "updated": n,
                                        "alarms": sentinel.history(200)})
            if op == "clear":
                n = sentinel.clear_note(str(b.get("fab") or ""), b.get("text"))
                return self._json(200, {"ok": True, "closed": n,
                                        "alarms": sentinel.history(200)})
            if op == "config":
                # 알람 동작 설정 — 관찰 유지(분) · 기록 보관 건수
                st = {}
                for k, src in (("alarmHoldMin", "hold_min"),
                               ("alarmKeep", "keep")):
                    if b.get(src) is not None:
                        st[k] = b.get(src)
                if st:
                    App.settings.update(st)
                cfg = sentinel.alarm_config(App.settings.all())
                sentinel.HOLD_MIN = cfg["hold_min"]     # 감시 로직이 바로 따른다
                sentinel.ALOG_MAX = cfg["keep"]
                self._say("     ↳ 알람 설정: 관찰 {}분 · 보관 {}건"
                          .format(cfg["hold_min"], cfg["keep"]))
                return self._json(200, {"ok": True, "config": cfg,
                                        "hold_min": cfg["hold_min"]})
            return self._err(400, "op 는 note/clear")

        if path == "/api/upload":
            # 큰 파일(특히 발동이벤트 CSV) — 자료함(300KB 캡)이 아니라 여기로.
            # 저장하고, CSV 면 그 자리에서 분석해 요약을 만들어 둔다.
            b = self._body()
            name = re.sub(r"[^\w가-힣.\- ]", "_", str(b.get("name") or ""))[:120]
            text = str(b.get("text") or "")
            if not name or not text:
                return self._err(400, "name/text 가 비었습니다")
            # ★서버도 막는다 — 브라우저를 거치지 않고 올릴 수도 있고,
            #   한도를 넘긴 파일은 여기서 분명히 거절해야 원인이 보인다.
            if len(text.encode("utf-8")) > UPLOAD_MAX:
                return self._err(413, "첨부 한도({}MB)를 넘었습니다: {:.1f}MB"
                                 .format(UPLOAD_MAX // (1024 * 1024),
                                         len(text.encode("utf-8")) / 1048576.0))
            try:
                (App.uploads_dir / name).write_text(text, encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                return self._err(500, "저장 실패: {}".format(e))
            if name.lower().endswith((".csv", ".tsv")):
                a = csvdata.analyze(name, text, self._cuts())
                App.uploads[name] = a
                self._say("200  /api/upload  {}  ({}자, 분석 {})".format(
                    name, len(text), "OK" if a["ok"] else "실패"))
                return self._json(200, {"ok": True, "name": name,
                                        "analyzed": a["ok"],
                                        "summary": a["summary"][:1200],
                                        "error": a["error"]})
            App.uploads[name] = {"ok": True, "summary": text[:8000],
                                 "numbers": set(), "rows": [], "error": ""}
            self._say("200  /api/upload  {}  ({}자)".format(name, len(text)))
            return self._json(200, {"ok": True, "name": name,
                                    "analyzed": False,
                                    "summary": "", "error": ""})

        if path == "/api/ctx":
            return self._api_ctx(self._body())

        if path == "/api/chat":
            return self._api_chat(self._body())

        if path.startswith("/v1"):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            body = self.rfile.read(n) if n else b"{}"
            return self._relay("POST", path[3:] or "/chat/completions", body)

        return self._err(404, "알 수 없는 경로: " + self.path)

    # ── 컨텍스트 계측 ────────────────────────────────────────────────────
    def _api_ctx(self, b):
        """컨텍스트 사용량 — ★대화가 실제로 쓰는 조립기로 잰다.

        예전엔 여기서 따로 계산했다. 그래서 **스킬은 아예 안 세고**(0),
        참고 자료는 스킬과 겹친 문단을 빼기 전 값이라, 화면 숫자가 실제로
        실리는 양과 달랐다 — "참고자료 MD 가 왜 등록이 안 되어 있지?" 가
        그 증상이다. 자료는 들어가고 있었는데 화면이 못 세고 있었다.
        """
        st = App.settings.all()
        persona = str(b.get("persona", ""))
        q = str(b.get("q", ""))
        hist = b.get("history") or []

        # 대화와 같은 재료 — 근거·첨부까지 그대로 (없으면 없는 대로)
        ev_text = ""
        if llm.is_data_question(q):
            ev = sentinel.evidence()
            ev_text = ev["text"] if ev["ok"] else ""
        attach = None
        aname = str(b.get("attach") or "").strip()
        if aname:
            up = self._upload_of(aname)
            if up is not None:
                attach = (aname, up["summary"])
            else:
                body = App.doc_store.get(aname)
                if body is not None:
                    attach = (aname, body)

        # ★계측은 실제 프롬프트를 그대로 만들어 재야 맞는다. MCP 도 마찬가지다 —
        #   여기서 빼면 화면 숫자가 실제로 실리는 양보다 적게 나온다.
        seg = llm.measure(persona, q, hist, App.doc_store, st,
                          skill_store=App.skill_store,
                          evidence_text=ev_text, attach=attach,
                          mcp_text=self._mcp_text(q, hist),
                          evidence_down=llm.is_data_question(q) and not ev_text)
        seg["limit"] = int(st.get("ctxLimit", 32768))
        seg["pct"] = min(999, round(seg["total"] / max(1, seg["limit"]) * 100))
        return self._json(200, seg)

    # ── LLM 대화 ─────────────────────────────────────────────────────────
    def _api_chat(self, b):
        text = str(b.get("text", "")).strip()
        if not text:
            return self._err(400, "text 가 비었습니다")
        history = b.get("history") or []
        model = str(b.get("model") or App.model)
        st = App.settings.all()
        try:
            temp = float(b.get("temperature", st.get("temperature", 0.8)))
        except (TypeError, ValueError):
            temp = 0.8

        # ── 슬래시 명령 — LLM 을 안 거치는 결정적 경로 (게이트웨이 없어도 됨)
        # ★붙어 있는 첨부의 **계산된 분석**을 재료로 같이 넘긴다. 이게 없으면
        #   "이 데이터로 스킬 만들어줘" 가 대화 요약만 보고 쓴다 — 데이터에서
        #   나온 스킬이 아니게 된다.
        extra = ""
        aname0 = str(b.get("attach") or "").strip()
        if aname0:
            up0 = self._upload_of(aname0)
            if up0 is not None:
                extra = "[첨부 분석: {}]\n{}".format(aname0, up0["summary"])
                q0 = csvdata.query(up0.get("rows") or [], text, self._cuts())
                if q0:
                    extra += "\n\n" + q0["lines"]
        cmd = commands.handle(text, App.skill_store, App.gateway, model,
                              history, temperature=0.3, extra=extra)
        if cmd is not None:
            self._say("200  /api/chat  (명령: {})".format(text.split()[0]))
            if b.get("stream"):
                return self._sse_oneshot(cmd)
            return self._json(200, {"reply": cmd})

        if not App.gateway:
            return self._err(503, "게이트웨이가 연결되지 않았습니다. run.py 로 실행하세요.")
        persona = str(b.get("persona", ""))

        # ── 데이터 질문이면 근거를 먼저 계산해 넣는다 (없으면 없다고) ──
        ev = {"ok": False, "text": "", "numbers": set()}
        if llm.is_data_question(text):
            # "어제 8시에 어땠어?" — 과거 시각이 읽히면 그 시각을 조회한다
            when = sentinel.parse_when(text)
            if when:
                ev = sentinel.evidence_at(*when)
                if ev["ok"]:
                    ev["fallback"] = sentinel.plain_status_at(*when)
            else:
                ev = sentinel.evidence()
            if not ev["ok"]:
                ev["text"] = ("관제 서버에서 데이터를 못 받았다 ({}). 수치는 "
                              "알 수 없다 — 반드시 '데이터를 못 본다' 고 "
                              "말하고, 숫자를 지어내지 마라.".format(ev["err"]))

        # ── 채팅 첨부 — 업로드(분석 요약) 먼저, 자료함(원문) 다음 ──
        attach = None
        aname = str(b.get("attach") or "").strip()
        if aname:
            up = self._upload_of(aname)
            if up is not None:
                # CSV 는 원문 대신 **계산된 분석 요약**을 넣는다. 수 MB 원문을
                # 자르면 못 본 구간을 지어낸다 — 요약의 숫자는 가드에 태운다.
                body = up["summary"]
                ev.setdefault("numbers", set())
                nums = set(ev.get("numbers") or set()) | set(
                    up.get("numbers") or set())
                # ★요약에 없는 것을 물으면(“14시엔?”, “M14B 최대는?”) 답할
                #   근거가 없었다. 질문에 맞춰 **원본 전 행을 다시 계산**해서
                #   붙인다 — 첨부가 붙어 있는 동안 매 질문마다 돈다.
                q = csvdata.query(up.get("rows") or [], text, self._cuts())
                if q:
                    body += "\n\n" + q["lines"]
                    nums |= set(q.get("numbers") or set())
                    self._say("     ↳ 첨부 재계산: {}행 기준".format(
                        len(up.get("rows") or [])))
                attach = (aname, body)
                ev["numbers"] = nums
                ev["ok"] = True
                ev["fallback"] = body
            else:
                body = App.doc_store.get(aname)
                if body is not None:
                    attach = (aname, body)

        # ★관제가 죽었는데 MCP(요청이력)에는 구체적인 숫자가 있으면, 모델은
        #   눈에 보이는 숫자를 집어 "요청이 올라와 있어요" 로 답해 버린다 —
        #   관제 상태를 물었는데 엉뚱한 걸 답하는 셈이다 (실제 증상).
        #   그래서 '지금 관제를 못 본다' 를 MCP 칸에도 박아 준다.
        down = llm.is_data_question(text) and not ev.get("ok")
        mcp = self._mcp_text(text, history)
        # ★MCP 로 받아온 글의 숫자도 **근거다.** 안 넣으면 나가기 직전 숫자
        #   가드가 그걸 '지어낸 수' 로 보고 **답을 통째로 버린다.**
        #   실제 증상: 위키의 연결 경로를 물었더니 호기명(4AFC3201·6ABL60)과
        #   층수(3F·6F·10F)가 관제 근거에 없다고 걸려서, 답이 엉뚱한 관제
        #   상태 요약("전체 17.0점 정상…")으로 바뀌어 나갔다.
        #   서윤은 제대로 읽어 왔는데 마지막 자리에서 지워지고 있었다.
        if mcp:
            ev["numbers"] = (set(ev.get("numbers") or set())
                             | sentinel.numbers_of(mcp))
        msgs = llm.build_messages(persona, text, history, App.doc_store, st,
                                  skill_store=App.skill_store,
                                  evidence_text=ev["text"], attach=attach,
                                  mcp_text=mcp,
                                  evidence_down=down)
        t0 = time.time()

        if not b.get("stream"):
            reply, err = App.gateway.chat(model, temp, msgs)
            ms = int((time.time() - t0) * 1000)
            if reply is None:
                self._say("ERR  /api/chat  {}ms  {}".format(ms, err[:160]))
                return self._err(502, err)
            # ── 분석 답도 루프를 태운다 ──
            # ★한 순간만 집어 말하고 끝내던 문제. 첨부를 두고 분석을 물었으면
            #   기간·행 수·분포·구간이 답에 있어야 한다. 없으면 그 지적을 붙여
            #   한 번 더 시킨다 (검사는 결정적 규칙 — LLM 을 또 부르지 않는다).
            reply = self._analysis_loop(reply, aname, text, msgs, model, temp,
                                        ev=ev)
            reply = self._guard(reply, ev)
            self._say("200  /api/chat  {}  {}ms".format(model, ms))
            return self._json(200, {"reply": reply})

        # ── SSE : 파싱된 이벤트를 그대로 흘려보낸다 ──────────────────────
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

        def chunk(obj):
            data = ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n") \
                .encode("utf-8")
            self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
            self.wfile.flush()

        n = 0
        try:
            for kind, payload in App.gateway.chat_stream(model, temp, msgs):
                if kind == "final":
                    # ★스트리밍이 **평소 경로**다 (브라우저는 stream 이 켜져
                    #   있다). 루프를 비스트리밍 쪽에만 달아 두면 실제로는
                    #   한 번도 안 돈다 — 실제로 그랬다. final 은 화면의
                    #   최종본이니 여기서 루프·가드를 같은 순서로 태운다.
                    payload = self._analysis_loop(payload, aname, text, msgs,
                                                  model, temp, ev=ev)
                    payload = self._guard(payload, ev)
                chunk({kind: payload})
                n += 1
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self._say("200  /api/chat  {}  {}ms  (stream, {}이벤트)".format(
            model, int((time.time() - t0) * 1000), n))

    def _mcp_text(self, text, history=None):
        """질문에 걸리는 MCP 서버를 불러 근거 글을 만든다 (없으면 빈 글).

        ★MCP 가 죽어도 대화는 계속돼야 한다. 여기서 예외가 새면 질문 하나가
          통째로 500 이 된다 — 외부 도구 하나 때문에 서윤이 입을 닫는다.
          그래서 무엇이 터지든 삼키고 빈 글을 준다.

        ★history 를 넘기는 이유: 이어지는 질문("그럼 언제 적용돼?")에는
          걸릴 낱말이 없어 조회가 안 된다. 그때 **조금 전에 조회해 둔 글을
          그대로 들고 간다** — 안 그러면 방금 읽은 내용을 잊은 채로 답한다.
        """
        hub = App.mcp_hub
        if hub is None or not text:
            return ""
        try:
            out, used = hub.gather(text, history=history)
        except Exception as e:  # noqa: BLE001
            self._say("     ↳ MCP 실패: {}".format(str(e)[:120]))
            return ""
        if used:
            self._say("     ↳ MCP 도구 {}회 · {}자".format(used, len(out)))
        elif out:
            # 조회는 안 걸렸는데 글이 있다 = 조금 전 결과를 그대로 들고 왔다
            self._say("     ↳ MCP 직전 조회 이어받음 · {}자".format(len(out)))
        else:
            hit = hub.matched(text)
            if hit:
                # ★걸렸는데 아무것도 안 나왔다 — 조용히 넘어가면 "왜 안 되지"
                #   가 된다. 콘솔에 남기고, 서윤도 "못 봤다" 고 말할 수 있게
                #   글로 넘긴다.
                # ★어느 서버인지 이름을 박는다. 예전엔 무조건 "요청이력" 이라고
                #   적었다 — 위키가 안 떠 있는데 서윤이 "요청관리 서버에 못
                #   붙었다" 고 말하면, 엉뚱한 서버를 붙잡고 고치게 된다.
                names = "·".join(s2.get("name") or s2["key"] for s2 in hit)
                self._say("     ↳ MCP 걸렸는데 결과 없음 ({} 서버 확인)"
                          .format(names))
                return ("[{}] 조회에 실패했다 — 서버에 못 붙었다. 이 자료는"
                        " **확인할 수 없다** 고 말하고, 내용을 지어내지 마라."
                        .format(names))
        return out

    def _upload_of(self, name):
        """업로드된 파일의 분석 캐시 — 서버 재시작 뒤에도 파일이 있으면 다시 분석."""
        a = App.uploads.get(name)
        if a is not None:
            return a
        p = App.uploads_dir / name
        text = None
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                text = None
        if text is None:
            # ★설정에 **등록해 둔 자료**도 분석 대상이다. 자료함은 원래
            #   키워드로 일부만 뽑아 넣는 곳이라, 표를 넣어도 계산을 못 했다.
            text = App.doc_store.get(name)
        if text is None:
            return None
        if name.lower().endswith((".csv", ".tsv")) or _looks_csv(text):
            a = csvdata.analyze(name, text, self._cuts())
        else:
            a = {"ok": True, "summary": text[:8000], "numbers": set(),
                 "rows": [], "error": ""}
        App.uploads[name] = a
        return a

    def _cuts(self):
        """등급 컷 — 관제 서버가 살아 있으면 거기 값, 아니면 60/71/85."""
        c = sentinel.columns()
        if c["ok"]:
            k = c["data"].get("cuts") or {}
            try:
                return (int(k["warn"]), int(k["danger"]), int(k["critical"]))
            except (KeyError, TypeError, ValueError):
                pass
        return (60, 71, 85)

    ANALYSIS_ASK = re.compile(r"분석|요약|어때|살펴|봐\s*줘|정리|추이|현황")

    def _analysis_checks(self, aname, ev):
        """이 답에 무엇이 들어 있어야 하나 — 재료에 따라 다르다.

        첨부(전 행 계산)가 있으면 하루치 분석의 요건을, 첨부 없이 관제 근거만
        있으면 '언제 · 몇 점 · 무슨 등급' 을 요구한다. 재료가 아예 없으면
        검사할 것도 없다 (지어내라고 다그치는 꼴이 된다).
        """
        if aname:
            up = self._upload_of(aname)
            if up is not None and (up.get("rows") or []):
                return [
                    harness.mentions_any(
                        ["기간", "~", "부터"], "기간",
                        "자료의 **기간**(시작~끝)을 첫머리에 말해 주세요."),
                    harness.mentions_any(
                        ["행", "분"], "분량",
                        "몇 행(몇 분)짜리 자료인지 말해 주세요."),
                    harness.mentions_any(
                        ["정상", "경계", "위험", "초위험"], "등급 분포",
                        "등급 분포(정상/경계/위험/초위험이 각각 몇 분)를 "
                        "말해 주세요."),
                    harness.mentions_any(
                        ["최고", "최대", "peak", "가장"], "최고점",
                        "최고점과 그 시각을 말해 주세요."),
                ]
            return []
        # 첨부 없이 "지금 어때?" — 근거가 살아 있을 때만 검사한다
        if not (ev or {}).get("ok") or not (ev or {}).get("text"):
            return []
        return [
            harness.mentions_any(
                [":"], "데이터 시각",
                "몇 시 몇 분 데이터인지 먼저 말해 주세요."),
            harness.mentions_any(
                ["정상", "경계", "위험", "초위험"], "등급",
                "지금이 정상/경계/위험/초위험 중 무엇인지 말해 주세요."),
            harness.mentions_any(
                ["점", "score", "스코어"], "점수",
                "점수를 숫자로 말해 주세요."),
        ]

    def _analysis_loop(self, reply, aname, question, msgs, model, temp, ev=None):
        """분석 답이 부실하면 이유를 붙여 한 번 더 — harness.run_loop.

        스트리밍·비스트리밍 **양쪽**에서 부른다. 검사는 결정적 규칙이라
        LLM 을 또 부르지 않는다 (다시 쓰라고 시킬 때만 한 번 더 부른다).
        """
        if not isinstance(reply, dict):
            return reply
        if not self.ANALYSIS_ASK.search(str(question or "")):
            return reply
        checks = self._analysis_checks(aname, ev)
        if not checks:
            return reply
        tried = [reply]

        def _gen(feedback):
            if not feedback:
                return json.dumps(tried[0], ensure_ascii=False)
            m = list(msgs) + [
                {"role": "assistant",
                 "content": json.dumps(tried[-1], ensure_ascii=False)},
                {"role": "user", "content":
                 feedback + "\n같은 근거만 쓰고, 숫자를 새로 지어내지 마세요."}]
            again, _e = App.gateway.chat(model, temp, m)
            if again:
                tried.append(again)
                return json.dumps(again, ensure_ascii=False)
            return ""

        res = harness.run_loop(_gen, checks, material="", max_rounds=2)
        gaps = res["verdict"].gaps_text() if res["verdict"] else ""
        if res["rounds"] > 1:
            self._say("     ↳ 분석 루프: {}회 · {}".format(
                res["rounds"], ("남은 것: " + gaps[:60]) if gaps else "다 채움"))
        # 다시 쓴 답이 검사를 통과했을 때만 바꾼다 — 통과 못 했으면 첫 답이
        # 낫다 (두 번째가 더 나빠질 수도 있다)
        return tried[-1] if (res["ok"] and len(tried) > 1) else tried[0]

    def _guard(self, reply, ev):
        """나가기 직전 검사 — ① 룰 코드·용어 ② 근거에 없는 숫자.

        ①은 근거·스킬을 이미 소독했는데도 필요하다. 모델은 **예전 대화**를
        보고 코드를 다시 꺼낸다 (대화 기록은 우리가 못 지운다). 마지막 자리에서
        한 번 더 바꾼다 — 사용자는 'R-D' 가 아니라 실제 컬럼을 봐야 한다.
        ②는 그럴듯한 거짓 숫자가 제일 위험하기 때문. 폴백은 질문 맥락을 따른다.
        """
        if isinstance(reply, dict) and reply.get("text"):
            reply = dict(reply, text=terms.clean(reply["text"]))
        if not ev.get("ok") or not isinstance(reply, dict):
            return reply
        ok, bad = sentinel.check_numbers(str(reply.get("text", "")),
                                         ev["numbers"])
        if ok:
            return reply
        self._say("     ↳ 숫자 가드: 근거에 없는 수 {} — 결정적 요약으로 대체"
                  .format(bad[:5]))
        fb = ev.get("fallback") or sentinel.plain_status()
        return {"text": ("방금 답에 근거에 없는 숫자가 섞여서 지웠어요. "
                         "계산된 값만 다시 말할게요 —\n" + fb),
                "emotion": "shy", "intensity": 0.6, "motion": "shake"}

    def _sse_oneshot(self, reply):
        """명령 응답을 스트리밍 모양으로 — 브라우저가 stream 을 켜 놨어도
        같은 경로로 받게 한다."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Transfer-Encoding", "chunked")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

        def chunk(obj):
            data = ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n") \
                .encode("utf-8")
            self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
            self.wfile.flush()
        try:
            chunk({"emo": {"emotion": reply["emotion"],
                           "intensity": reply["intensity"],
                           "motion": reply["motion"]}})
            chunk({"text": reply["text"]})
            chunk({"final": reply})
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ── /v1 원시 프록시 (모델 목록 등) ───────────────────────────────────
    def _chunk_raw(self, data):
        self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
        self.wfile.flush()

    def _relay(self, method, path, body):
        url = App.upstream.rstrip("/") + path
        model, stream = "", False
        if body:
            try:
                bj = json.loads(body.decode("utf-8"))
                model = bj.get("model", "")
                stream = bool(bj.get("stream"))
            except Exception:
                pass
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + App.token})
        t0 = time.time()
        try:
            r = App.opener.open(req, timeout=App.timeout)
            if stream:
                self.send_response(200)
                self.send_header("Content-Type",
                                 "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-transform")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("Transfer-Encoding", "chunked")
                for k, v in CORS_HEADERS.items():
                    self.send_header(k, v)
                self.end_headers()
                n = 0
                try:
                    for line in r:
                        if line:
                            self._chunk_raw(line)
                            n += 1
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    r.close()
                self._say("200  {}  {}  {}ms  (stream, {}줄)".format(
                    path, model or "-", int((time.time() - t0) * 1000), n))
                return
            with r:
                data = r.read()
            self._say("200  {}  {}  {}ms".format(
                path, model or "-", int((time.time() - t0) * 1000)))
            self._send(200, data)

        except urllib.error.HTTPError as e:
            data = e.read()
            self._say("{}  {}  {}ms".format(
                e.code, path, int((time.time() - t0) * 1000)))
            try:
                msg = json.loads(data.decode("utf-8")) \
                    .get("error", {}).get("message", "")
            except Exception:
                msg = data.decode("utf-8", "replace")[:300]
            if msg:
                self._say("     ↳ " + msg[:220])
            if e.code in (401, 403):
                self._say("     ↳ token.txt 의 토큰을 확인하세요.")
            elif e.code == 404:
                self._say("     ↳ 모델 이름 또는 엔드포인트를 확인하세요.")
            elif e.code == 429:
                self._say("     ↳ 사용량/한도 초과입니다.")
            self._send(e.code, data)
        except urllib.error.URLError as e:
            self._say("[x] 연결 실패: {}".format(e.reason))
            self._err(502, "연결 실패: {} (사내망/VPN 확인)".format(e.reason))
        except Exception as e:  # noqa: BLE001
            self._say("[x] {}".format(e))
            self._err(500, str(e))


class Server(ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[0]
        if exc in (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            return
        super().handle_error(request, client_address)
