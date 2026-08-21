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
  GET  /api/sessions         세션 전체
  PUT  /api/sessions         세션 전체 저장 (한도는 서버가 강제)
  GET  /api/sessions/md?id=  세션 하나를 Markdown 으로
  /v1/*                      게이트웨이 원시 프록시 (토큰은 서버만 안다)
"""
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer

from . import config, docs, llm, sessions, settings

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
    "Access-Control-Max-Age": "86400",
}


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

    @classmethod
    def init(cls, base_dir):
        cls.base_dir = base_dir
        cls.static_dir = base_dir / "static"
        cls.data_dir = base_dir / "data"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.doc_store = docs.DocStore(cls.data_dir / "docs.json")
        cls.sess_store = sessions.SessionStore(cls.data_dir / "sessions.json")
        cls.settings = settings.Settings(cls.data_dir / "settings.json")

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
            return self._json(200, App.settings.all())

        if path == "/api/docs":
            return self._json(200, {"docs": App.doc_store.list(),
                                    "budget": App.settings.get("docBudget")})

        if path == "/api/sessions":
            return self._json(200, {"sessions": App.sess_store.get_all()})

        if path == "/api/sessions/md":
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1]
                                      if "?" in self.path else "")
            sid = (q.get("id") or [""])[0]
            for s in App.sess_store.get_all():
                if s.get("id") == sid:
                    md = App.sess_store.to_markdown(s).encode("utf-8")
                    return self._send(200, md, "text/markdown; charset=utf-8")
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
            ok = App.sess_store.put_all(self._body().get("sessions"))
            return self._json(200 if ok else 400, {"ok": ok})
        return self._err(404, "알 수 없는 경로: " + self.path)

    def do_POST(self):
        path = self.path.split("?", 1)[0]

        if path == "/api/settings":
            return self._json(200, App.settings.update(self._body()))

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
        st = App.settings.all()
        persona = str(b.get("persona", ""))
        q = str(b.get("q", ""))
        hist = b.get("history") or []
        keep = int(st.get("keepMsgs", 12))
        hist_txt = "\n".join(str(m.get("content", "")) for m in hist[-keep:]
                             if isinstance(m, dict))
        seg = {
            "persona": docs.est_tokens(persona.strip()),
            "docs": docs.est_tokens(
                App.doc_store.context(q, int(st.get("docBudget", 6000)))),
            "rules": docs.est_tokens(llm.RULES_TEXT) + 40,
            "history": docs.est_tokens(hist_txt),
            "input": docs.est_tokens(q),
        }
        seg["total"] = sum(seg.values())
        seg["limit"] = int(st.get("ctxLimit", 32768))
        seg["pct"] = min(999, round(seg["total"] / max(1, seg["limit"]) * 100))
        return self._json(200, seg)

    # ── LLM 대화 ─────────────────────────────────────────────────────────
    def _api_chat(self, b):
        if not App.gateway:
            return self._err(503, "게이트웨이가 연결되지 않았습니다. run.py 로 실행하세요.")
        text = str(b.get("text", "")).strip()
        if not text:
            return self._err(400, "text 가 비었습니다")
        persona = str(b.get("persona", ""))
        history = b.get("history") or []
        model = str(b.get("model") or App.model)
        st = App.settings.all()
        try:
            temp = float(b.get("temperature", st.get("temperature", 0.8)))
        except (TypeError, ValueError):
            temp = 0.8

        msgs = llm.build_messages(persona, text, history, App.doc_store, st)
        t0 = time.time()

        if not b.get("stream"):
            reply, err = App.gateway.chat(model, temp, msgs)
            ms = int((time.time() - t0) * 1000)
            if reply is None:
                self._say("ERR  /api/chat  {}ms  {}".format(ms, err[:160]))
                return self._err(502, err)
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
                chunk({kind: payload})
                n += 1
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self._say("200  /api/chat  {}  {}ms  (stream, {}이벤트)".format(
            model, int((time.time() - t0) * 1000), n))

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
