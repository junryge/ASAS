# -*- coding: utf-8 -*-
"""서윤이 MCP 서버에 붙는 쪽 — 표준 라이브러리만 쓴다 (폐쇄망).

왜 SDK 가 아닌가
    qa/mcp_server.py 머리말과 같은 이유다. 공식 mcp SDK 는 30개 남짓을 끌고
    오는데 폐쇄망 배포물에 넣을 수 없다. MCP 는 JSON-RPC 2.0 이라 직접 짠다.
    (규격은 공식 SDK 서버에 붙여 확인했다 — 우리 서버·SDK 서버 양쪽 통과.)

무엇을 하나
    Client  서버 하나를 stdio 로 띄우고 도구를 부른다.
    Hub     config.MCP_SERVERS 를 보고, **질문에 걸리는 서버만** 띄워서
            도구를 부르고, 결과를 서윤 프롬프트에 넣을 글로 만든다.

★이 파일 이름을 mcp.py 로 하지 않는다. avatar 패키지 안에 mcp.py 가 있으면
  나중에 누가 공식 SDK 를 깔았을 때 `from . import mcp` 와 헷갈린다 —
  이 프로젝트에서 config 모듈이 함수 이름에 가려 관제 주소를 못 읽은 적이
  있다. 같은 사고를 두 번 내지 않는다.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

PROTO = "2025-06-18"


class McpError(Exception):
    """규격 오류 — 서버가 JSON-RPC error 를 돌려줬거나 끊겼다."""


class _Tools:
    """transport 와 무관한 부분 — tools/list 와 tools/call.

    ★stdio 와 streamable-http 가 같은 규격을 쓴다. 여기를 두 벌로 두면
      한쪽만 고쳐서 어긋난다 (isError 처리처럼 미묘한 것이 있다).
    """

    def tools(self):
        return (self._rpc("tools/list") or {}).get("tools") or []

    def call(self, name, args=None):
        """도구 하나 → (글, 실패인가).

        ★없는 도구를 두 가지로 돌려준다: JSON-RPC error(우리 서버) 거나
          isError 결과(공식 SDK 서버). 둘 다 받아야 한다.
        """
        try:
            r = self._rpc("tools/call", {"name": name,
                                         "arguments": args or {}})
        except McpError as e:
            return str(e), True
        txt = "\n".join(c.get("text") or "" for c in (r.get("content") or [])
                        if c.get("type") == "text").strip()
        if not txt and r.get("structuredContent") is not None:
            txt = json.dumps(r["structuredContent"], ensure_ascii=False)
        return txt, bool(r.get("isError"))


class Client(_Tools):
    """MCP 서버 하나. stdio 로 자식 프로세스를 띄운다."""

    def __init__(self, command, args=None, env=None, cwd=None, timeout=20):
        self.timeout = float(timeout)
        self._id = 0
        self._lock = threading.RLock()
        e = dict(os.environ)
        e.update(env or {})
        self.proc = subprocess.Popen(
            [command] + list(args or []),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=e, cwd=cwd,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        self.server = {}
        self.proto = ""
        self._handshake()

    # ── 낮은 층 ──────────────────────────────────────────────────────────
    def _write(self, obj):
        if self.proc.poll() is not None or self.proc.stdin is None:
            raise McpError("서버가 이미 끝났다")
        try:
            self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError) as e:
            # ★같은 사고인데 예외 이름이 다르다:
            #     윈도우  OSError [Errno 22] Invalid argument
            #     리눅스  ValueError: I/O operation on closed file
            #   둘 다 안 잡으면 대화 한 줄이 통째로 실패한다.
            #   규격 오류로 바꿔 위에서 다시 붙게 한다.
            raise McpError("서버에 못 썼다 ({})".format(e))

    def _rpc(self, method, params=None):
        with self._lock:
            self._id += 1
            mid = self._id
            self._write({"jsonrpc": "2.0", "id": mid, "method": method,
                         "params": params or {}})
            while True:
                try:
                    line = self.proc.stdout.readline()
                except (OSError, ValueError) as e:
                    raise McpError("서버에서 못 읽었다 ({})".format(e))
                if not line:
                    raise McpError("서버가 끊겼다 ({})".format(method))
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue          # 서버가 흘린 잡음은 버린다
                if msg.get("id") != mid:
                    continue          # 알림·남의 응답은 지나친다
                if "error" in msg:
                    er = msg["error"] or {}
                    raise McpError("{} ({})".format(er.get("message"),
                                                    er.get("code")))
                return msg.get("result") or {}

    def _notify(self, method, params=None):
        with self._lock:
            self._write({"jsonrpc": "2.0", "method": method,
                         "params": params or {}})

    # ── 규격 ─────────────────────────────────────────────────────────────
    def _handshake(self):
        r = self._rpc("initialize", {
            "protocolVersion": PROTO,
            "capabilities": {},
            "clientInfo": {"name": "seoyun-avatar", "version": "1.0.0"}})
        self.server = r.get("serverInfo") or {}
        self.proto = r.get("protocolVersion") or ""
        self._notify("notifications/initialized")

    def alive(self):
        """아직 쓸 수 있나. ★transport 마다 뜻이 달라서 이름을 맞춰 둔다 —
        stdio 는 자식 프로세스가 살아 있나, http 는 마지막 요청이 닿았나."""
        return self.proc.poll() is None

    def where(self):
        return " ".join(self.proc.args) if hasattr(self.proc, "args") else ""

    def close(self):
        for f in (self.proc.stdin, self.proc.stdout):
            try:
                if f:
                    f.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            try:
                self.proc.kill()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class HttpClient(_Tools):
    """streamable-http 로 붙는 MCP 서버 (표준 라이브러리만).

    왜 필요한가
        LLM_WIKI_MCP(위키) 는 공식 SDK(FastMCP)로 짜여 있고 transport 가
        **streamable-http** 다. 자식 프로세스로 띄우는 stdio 로는 못 붙는다.
        위키 서버는 mcp 패키지·flask 를 끌고 오므로 아바타와 한 프로세스에
        넣을 수도 없다 — 그쪽은 그쪽대로 띄우고, 여기서는 붙기만 한다.

    ★응답이 두 가지로 온다
        같은 주소가 application/json 으로도, text/event-stream(SSE) 으로도
        답한다. FastMCP 는 **도구 결과를 SSE 로** 준다 — JSON 만 읽으면
        붙기는 하는데 도구가 통째로 안 된다.
    """

    # ★붙는 데 이보다 오래 걸리면 안 떠 있는 것으로 본다. 도구 호출은
    #   오래 걸릴 수 있어도(검색·본문), **안 뜬 서버를 20초씩 기다리는 것**은
    #   그냥 손해다. 그 20초 동안 이 대화는 멎어 있다.
    HANDSHAKE_S = 3.0

    def __init__(self, url, headers=None, timeout=20):
        self.url = str(url or "").strip()
        if not self.url:
            raise McpError("주소가 비어 있다")
        self.timeout = float(timeout)
        self.extra = dict(headers or {})
        self.session = ""
        self.server = {}
        self.proto = ""
        self._id = 0
        self._ok = True
        self._lock = threading.RLock()
        # ★사내 주소다 — 프록시를 타면 안 된다. 관제·월드모델에서 이미 밟은
        #   자리다: 회사 프록시가 사내 IP 를 못 찾아 407 을 돌려준다.
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}))
        self._handshake()

    # ── 낮은 층 ──────────────────────────────────────────────────────────
    @staticmethod
    def _sse(raw):
        """SSE 본문 → 데이터 덩어리들. 'data:' 줄만 모은다."""
        out = []
        for chunk in re.split(r"\r?\n\s*\r?\n", raw):
            body = []
            for ln in chunk.splitlines():
                if ln.startswith("data:"):
                    v = ln[5:]
                    body.append(v[1:] if v.startswith(" ") else v)
            if body:
                out.append("\n".join(body))
        return out

    def _messages(self, raw, ctype):
        raw = (raw or "").strip()
        if not raw:
            return []
        chunks = self._sse(raw) if "text/event-stream" in (ctype or "").lower() \
            else [raw]
        out = []
        for c in chunks:
            try:
                m = json.loads(c)
            except ValueError:
                continue          # 서버가 흘린 잡음(주석·하트비트)은 버린다
            out.extend(m if isinstance(m, list) else [m])
        return out

    def _post(self, payload):
        h = {"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self.proto:
            h["MCP-Protocol-Version"] = self.proto
        if self.session:
            h["Mcp-Session-Id"] = self.session
        h.update(self.extra)
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=h, method="POST")
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                sid = r.headers.get("mcp-session-id")
                if sid:
                    self.session = sid
                ctype = r.headers.get("Content-Type") or ""
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:  # noqa: BLE001
                pass
            hint = self._hint(e.code, body)
            if hint:
                self._ok = False
                raise McpError(hint)
            # ★세션이 만료되면 404/400 이 온다. 이건 '끊겼다' 로 알려야
            #   위에서 새로 붙어 다시 건다 (_looks_dead 가 그 말을 본다).
            if e.code in (400, 404):
                self.session = ""
                self._ok = False
                raise McpError("서버가 끊겼다 (HTTP {} {})".format(e.code, body))
            raise McpError("HTTP {} {}".format(e.code, body))
        except Exception as e:  # noqa: BLE001
            self._ok = False
            raise McpError("서버가 끊겼다 ({}: {})".format(type(e).__name__, e))
        self._ok = True
        return self._messages(raw, ctype)

    def _hint(self, code, body):
        """이 응답이 **엉뚱한 서버**에서 온 것인가 — 맞으면 그렇다고 말한다.

        ★실제로 겪었다. 위키는 프로세스가 **둘**이다:
              app.py         Flask 웹앱      기본 :8100
              mcp_server.py  FastMCP · MCP   기본 :8020
          웹앱 주소(:8100)를 MCP 로 넣으면 /mcp 가 없어서 Flask 가 HTML 404 를
          돌려준다. 그걸 "서버가 끊겼다 (HTTP 404 <!doctype html>...)" 라고만
          하면, 서버는 멀쩡히 떠 있는데 왜 안 되는지 알 길이 없다.
          MCP 서버는 JSON 만 준다 — HTML 이 오면 그 주소가 아닌 것이다.
        """
        b = str(body or "")
        if "<html" not in b.lower() and "<!doctype" not in b.lower():
            return ""
        return ("이 주소는 MCP 서버가 아닙니다 (HTML {} 이 왔습니다). "
                "위키는 프로세스가 둘입니다 — 웹앱(app.py · 기본 :8100)과 "
                "MCP 서버(mcp_server.py · 기본 :8020)는 다른 것입니다. "
                "위키 폴더에서 python mcp_server.py 를 띄우고 그 포트의 "
                "/mcp 를 넣으세요. 지금 보는 곳: {}".format(code, self.url))

    def _rpc(self, method, params=None):
        with self._lock:
            self._id += 1
            mid = self._id
            msgs = self._post({"jsonrpc": "2.0", "id": mid, "method": method,
                               "params": params or {}})
            for m in msgs:
                if m.get("id") != mid:
                    continue      # 알림·남의 응답은 지나친다
                if "error" in m:
                    er = m["error"] or {}
                    raise McpError("{} ({})".format(er.get("message"),
                                                    er.get("code")))
                return m.get("result") or {}
            raise McpError("응답이 없다 ({})".format(method))

    def _notify(self, method, params=None):
        with self._lock:
            try:
                self._post({"jsonrpc": "2.0", "method": method,
                            "params": params or {}})
            except McpError:
                # 알림은 202 로 빈 몸을 준다. 여기서 터뜨릴 이유가 없다.
                pass

    # ── 규격 ─────────────────────────────────────────────────────────────
    def _handshake(self):
        full, self.timeout = self.timeout, min(self.timeout, self.HANDSHAKE_S)
        try:
            r = self._rpc("initialize", {
                "protocolVersion": PROTO,
                "capabilities": {},
                "clientInfo": {"name": "seoyun-avatar", "version": "1.0.0"}})
        finally:
            self.timeout = full
        self.server = r.get("serverInfo") or {}
        self.proto = r.get("protocolVersion") or PROTO
        self._notify("notifications/initialized")

    def alive(self):
        return self._ok

    def where(self):
        return self.url

    def close(self):
        self.session = ""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# ── 여러 서버를 묶어 근거 글로 ────────────────────────────────────────────
def _hits(text, words, when_re=None):
    """질문에 이 서버를 부를 말이 들어 있나.

    ★when_re 도 본다. "AVGTOTALTIME1MIN 왜 썼어?" 처럼 **컬럼·룰 이름만**
      나오는 질문이 있다 — 그 답이 요청이력(보류 건)에 그대로 있는데,
      '요청' 이라는 낱말이 없다고 안 걸려서 못 찾아 줬다.
    """
    t = str(text or "")
    got = [w for w in (words or []) if w and w in t]
    if not got and when_re:
        m = re.search(when_re, t)
        if m:
            got = [m.group(0)]
    return got


def _arg_of(text, spec):
    """질문에서 인자 하나를 뽑는다. spec 은 config 의 'pick'/'pick_opt' 항목."""
    kind = spec.get("kind")
    if kind == "regex":
        m = re.search(spec["re"], text or "")
        if not m:
            return None
        v = m.group(spec.get("group", 1))
        return int(v) if spec.get("int") else v
    if kind == "oneof":
        # ★긴 것부터 본다. ["M14","M14B"] 순서면 "M14B" 질문에서 M14 가
        #   먼저 걸려 엉뚱한 FAB 을 찾는다.
        for v in sorted(spec.get("values") or [], key=len, reverse=True):
            if v in (text or ""):
                return v
        return None
    if kind == "text":
        # ★질문 그대로를 인자로. 위키 검색처럼 "무엇을 찾을지" 가 곧 질문인
        #   도구가 있다. 앞뒤 군말은 잘라 낸다 (BM25 라 긴 문장도 먹는다).
        t = re.sub(r"\s+", " ", str(text or "")).strip()
        t = t[:int(spec.get("max", 200))]
        return t or None
    if kind == "any":
        # 여러 규칙을 차례로 시도한다 (코드명 먼저, 없으면 사람 이름 …)
        for one in spec.get("of") or []:
            v = _arg_of(text, one)
            if v is not None:
                return v
    return None


def _connect(s):
    """설정 한 칸 → 붙은 클라이언트. transport 로 갈라진다.

    ★transport 를 안 적으면 stdio 다 (지금까지 쓰던 것들이 그대로 돈다).
    """
    if str(s.get("transport") or "stdio").lower() in ("http", "streamable-http"):
        return HttpClient(s.get("url"), s.get("headers"), s.get("timeout", 20))
    return Client(s.get("command") or sys.executable, s.get("args"),
                  s.get("env"), s.get("cwd"), s.get("timeout", 20))


def _looks_dead(msg):
    """이 실패가 '연결이 끊긴 것' 인가 (도구 자체의 실패가 아니라)."""
    m = str(msg or "")
    return any(w in m for w in ("못 썼다", "못 읽었다", "끊겼다", "이미 끝났다"))


class Hub:
    """config.MCP_SERVERS 를 보고 필요한 것만 띄워 쓴다.

    · 질문에 걸리는 서버가 없으면 **아무것도 안 띄운다** (평소엔 비용 0).
    · 한 번 띄운 서버는 살려 두고 다시 쓴다. 죽으면 다음 질문에 다시 띄운다.
    · 서버가 죽어 있어도 대화는 계속돼야 한다 — 실패는 글로 적어 넘긴다.
    """

    # ★같은 질문을 짧은 시간에 여러 번 묻는다. 화면의 컨텍스트 계측이
    #   **타이핑을 멈출 때마다**(500ms) /api/ctx 를 부르고, 보내면 대화가
    #   또 부른다 — 한 문장에 도구가 여러 번 돌아 눈에 띄게 느려졌다.
    #   같은 글은 이 시간 안에서 한 번만 실제로 조회한다.
    CACHE_S = 15.0

    # 조회가 안 걸린 질문에서 직전 결과를 들고 갈 범위.
    # ★무한정 들고 가면 안 된다 — 요청이력 이야기가 끝나고 한참 뒤에도
    #   그 글이 프롬프트에 남아 엉뚱한 답의 재료가 된다.
    CARRY_TURNS = 6      # 주고받은 메시지 수 (사람+서윤 = 2개가 한 번)
    CARRY_S = 900.0      # 15분

    # ★못 붙은 서버는 이 시간 동안 다시 안 두들긴다 (차단기).
    #   왜 필요한가: 화면의 컨텍스트 계측이 **타이핑을 멈출 때마다**(500ms)
    #   /api/ctx 를 부르고, 그때마다 조회가 돈다. 안 떠 있는 서버가 하나
    #   있으면 그 요청들이 전부 붙기를 기다리며 쌓인다 — 스레드가 계속
    #   늘고, 아바타 프로세스 전체가 무거워진다. 관제 감시 스레드까지
    #   느려지면 화면에는 엉뚱하게 "관제 연결 끊김" 이 뜬다.
    #   한 번 못 붙었으면 그 사실을 기억하고 즉시 실패로 답한다.
    RETRY_S = 30.0

    def __init__(self, servers=None, say=None):
        # ★꺼진 서버도 **들고 있는다**. 예전엔 여기서 걸러 버려서, 한 번 꺼진
        #   서버는 화면에서 다시 켤 방법이 없었다 (목록에 아예 없으니까).
        #   쓸 때(matched) 켜져 있나 본다.
        self.servers = list(servers or [])
        self._live = {}
        self._lock = threading.RLock()
        self._say = say or (lambda *_a: None)
        self._cache = {}          # {질문: (잰 시각, 글, 도구 수)}
        # ★한 번 조회한 것은 **그 대화 안에서 들고 간다.**
        #   증상: "7번 요청 뭐야?" 로 조회가 걸려 내용을 받아 놓고, 바로 다음
        #   "그럼 그건 언제 적용돼?" 에는 '요청'·'이력' 같은 낱말이 없어서
        #   서버가 아예 안 불리고 → 프롬프트에 MCP 칸이 통째로 빠졌다.
        #   서윤은 방금 자기가 읽은 내용을 못 보는 상태로 답해야 했다.
        #   {대화열쇠: (그때 history 길이, 잰 시각, 글)}
        self._carry = {}
        # {서버열쇠: (못 붙은 시각, 이유)} — RETRY_S 동안 다시 안 붙는다
        self._down = {}
        # ★서버마다 자물쇠 하나. 아바타 서버는 스레드로 도는데, 화면의
        #   컨텍스트 계측(/api/ctx)과 대화(/api/chat)가 **동시에** 같은 MCP
        #   프로세스를 쓴다. 한쪽이 "죽었네" 하고 닫는 순간 다른 쪽은 닫힌
        #   파이프에 쓴다 — 윈도우는 거기서 [Errno 22] Invalid argument 를
        #   낸다 (실제 증상). 한 서버의 조회는 한 번에 하나만 돌게 한다.
        self._srv_locks = {}

    def _srv_lock(self, key):
        with self._lock:
            lk = self._srv_locks.get(key)
            if lk is None:
                lk = self._srv_locks[key] = threading.RLock()
            return lk

    def _all_alive(self):
        """띄워 둔 서버가 전부 살아 있나.

        ★캐시가 **죽은 서버를 가리면 안 된다**. 서버가 끝났는데 15초 동안
          옛 답을 그대로 주면, 그 사이에 '요청이력은 이렇다' 고 말한다 —
          실은 아무것도 못 보고 있는데. 하나라도 죽었으면 캐시를 건너뛰고
          다시 붙어 본다 (그때 실패하면 실패라고 적어 넘긴다).
        """
        with self._lock:
            return all(c.alive() for c in self._live.values())

    def on(self):
        """지금 켜져 있는 서버들."""
        return [s for s in self.servers if s.get("enabled", True)]

    def find(self, key):
        for s in self.servers:
            if s["key"] == str(key):
                return s
        return None

    def matched(self, text):
        """이 질문에 걸리는 서버 목록 (화면 계측·시험용)."""
        return [s for s in self.on()
                if _hits(text, s.get("when"), s.get("when_re"))]

    # ── 화면에서 켜고 끄기 ───────────────────────────────────────────────
    def set_enabled(self, key, on):
        """켜기/끄기. ★끌 때는 **붙어 있던 것을 놓는다** — 안 놓으면 자식
        프로세스가 계속 떠 있고, 화면에는 꺼진 것으로 보인다."""
        s = self.find(key)
        if s is None:
            return False
        s["enabled"] = bool(on)
        if not s["enabled"]:
            self._drop(key)
        else:
            with self._lock:
                self._down.pop(key, None)      # 다시 붙어 볼 기회를 준다
        return True

    def set_url(self, key, url):
        """주소 바꾸기 (http 로 붙는 서버만). 바꾸면 다시 붙는다."""
        s = self.find(key)
        if s is None or not s.get("url"):
            return False
        u = str(url or "").strip().rstrip("/")
        if u and not u.endswith("/mcp"):
            u += "/mcp"                        # 빠뜨리기 쉽다 — 조용히 404 다
        s["url"] = u
        self._drop(key)
        return True

    def reconnect(self, key=None):
        """붙어 있던 것을 놓고 차단기를 푼다 — 다음 질문에 새로 붙는다."""
        for s in ([self.find(key)] if key else list(self.servers)):
            if s is not None:
                self._drop(s["key"])
        return True

    def _drop(self, key):
        with self._lock:
            c = self._live.pop(key, None)
            self._down.pop(key, None)
            # ★들고 다니던 직전 결과도 버린다. 안 버리면, 껐는데도 서윤이
            #   15분 동안 그 내용을 계속 말한다 — 틀려서 껐는데 계속 나온다.
            self._carry.clear()
            self._cache.clear()
        if c is not None:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass

    def _run_calls(self, s, c, text, lines):
        """한 서버의 도구들을 차례로 부른다 → 부른 횟수.
        ★_srv_lock 안에서만 부른다 (동시 접근이 파이프를 깬다)."""
        used = 0
        for call in s.get("calls") or []:
            args = dict(call.get("args") or {})
            for k, spec in (call.get("pick") or {}).items():
                v = _arg_of(text, spec)
                if v is None:
                    args = None
                    break
                args[k] = v
            if args is None:
                continue      # 질문에서 인자를 못 뽑았다 — 이 도구는 건너뛴다
            # ★있으면 좁히고, 없으면 그냥 전체를 본다. 이걸 required 로
            #   두면 안 된다 — 등록된 요청의 대상이 전부 'ALL' 이라
            #   FAB 이름으로만 좁히게 해 놨더니 **목록이 한 번도 안 나왔다**.
            #   건수만 오고 "그래서 그 5건이 뭔데" 에 답을 못 했다.
            for k, spec in (call.get("pick_opt") or {}).items():
                v = _arg_of(text, spec)
                if v is not None:
                    args[k] = v
            txt, bad = self._call_retry(s, c, call["tool"], args)
            c = self._live.get(s["key"], c)      # 다시 붙었을 수 있다
            used += 1
            if txt:
                lines.append("· {}{}\n{}".format(
                    call.get("label") or call["tool"],
                    " (실패)" if bad else "", self._fit(s, txt)))
            if not bad and txt and call.get("then"):
                used += self._run_then(s, c, call["then"], txt, lines)
                c = self._live.get(s["key"], c)
        return used

    def _run_then(self, s, c, then, prev, lines):
        """앞 결과에서 id 를 꺼내 **본문까지** 읽는다 → 부른 횟수.

        ★왜 필요한가. 위키 검색은 500자 조각만 준다. 그걸로 답하면 서윤이
          앞머리만 아는 상태가 된다 — 요청이력에서 그대로 겪은 일이다
          ("하기는 잘해.. 근데 상세한 내용을 물어보면 몰라"). 검색으로
          어느 쪽인지 찾았으면 그 쪽 본문을 읽어야 아는 것이다.
        """
        ids, used = self._ids_of(then, prev), 0
        for v in ids[:int(then.get("max", 2))]:
            txt, bad = self._call_retry(s, c, then["tool"],
                                        {then.get("arg", "id"): v})
            c = self._live.get(s["key"], c)
            used += 1
            if txt:
                lines.append("· {} #{}{}\n{}".format(
                    then.get("label") or then["tool"], v,
                    " (실패)" if bad else "", self._fit(s, txt)))
        return used

    @staticmethod
    def _ids_of(then, prev):
        """앞 도구가 준 JSON 에서 id 목록. JSON 이 아니면 빈 목록."""
        try:
            data = json.loads(prev)
        except ValueError:
            return []
        rows = data.get(then.get("list") or "results") if isinstance(data, dict) \
            else data
        if not isinstance(rows, list):
            return []
        only = then.get("only") or {}
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            if any(r.get(k) != v for k, v in only.items()):
                continue
            v = r.get(then.get("id") or "id")
            if v is not None and v not in out:
                out.append(v)
        return out

    @staticmethod
    def _fit(s, txt):
        """서버마다 정한 몫만큼만 싣는다 (0 이나 없으면 그대로).

        ★위키 본문은 길다. 통째로 넣으면 관제 근거·첨부가 밀려난다 —
          컨텍스트는 한정돼 있고, 밀려나는 쪽이 더 중요한 경우가 많다.
        """
        cap = int(s.get("budget") or 0)
        if cap <= 0 or len(txt) <= cap:
            return txt
        return txt[:cap] + "\n…(뒤가 잘렸다 · 전체 {}자)".format(len(txt))

    def _call_retry(self, s, c, tool, args):
        """도구 하나 — 파이프가 끊겼으면 **한 번만** 다시 붙어 재시도한다.

        ★윈도우에서 자식이 죽으면(인코딩·강제종료 등) 부모는 [Errno 22]
          Invalid argument 를 맞는다. 한 번 죽었다고 그 질문을 통째로
          버릴 이유가 없다 — 새로 띄우면 대개 그대로 된다.
        """
        txt, bad = c.call(tool, args)
        if not bad:
            return txt, bad
        if not _looks_dead(txt) or c.alive():
            return txt, bad          # 진짜 도구 실패다 — 다시 걸어도 같다
        self._say("     ↳ MCP 끊겨서 다시 붙는다 ({})".format(txt[:60]))
        try:
            with self._lock:
                self._live.pop(s["key"], None)
            c2 = self._client(s)
        except Exception as e:  # noqa: BLE001
            return "다시 붙지 못했다: {}".format(e), True
        return c2.call(tool, args)

    def _client(self, s):
        key = s["key"]
        # ★붙는 동안 **전체 자물쇠를 쥐고 있으면 안 된다.** 안 떠 있는 서버
        #   하나가 다른 서버 조회까지 통째로 세운다. 서버별 자물쇠로 좁힌다.
        with self._srv_lock(key):
            with self._lock:
                c = self._live.get(key)
                if c is not None and c.alive():
                    return c
                if c is not None:
                    c.close()
                    self._live.pop(key, None)
                bad = self._down.get(key)
            if bad and time.time() - bad[0] < self.RETRY_S:
                # 아직 쉬는 중이다 — 두들기지 않고 그때 이유를 그대로 준다
                raise McpError(bad[1])
            try:
                c = _connect(s)
            except Exception as e:                       # noqa: BLE001
                with self._lock:
                    self._down[key] = (time.time(), str(e))
                self._say("     ↳ MCP 못 붙었다: {} ({}) — {:.0f}초 쉬었다 다시"
                          .format(s.get("name") or key, str(e)[:80],
                                  self.RETRY_S))
                raise
            with self._lock:
                self._down.pop(key, None)
                self._live[key] = c
            self._say("     ↳ MCP 연결: {} ({} {}) — {}".format(
                s.get("name") or key, c.server.get("name") or "?",
                c.server.get("version") or "", c.where()))
            return c

    @staticmethod
    def _conv_key(history, text):
        """이 대화를 가리키는 열쇠 — **첫 사람 발화**.

        /api/chat 에 세션 id 가 안 넘어와서 history 로 짚는다. 첫 발화는
        대화가 이어져도 안 바뀌므로, 두 번째 질문부터도 같은 열쇠가 나온다.
        (첫 질문이면 history 가 비어 있으니 지금 질문이 곧 첫 발화다.)
        """
        import hashlib
        first = ""
        for m in history or []:
            if isinstance(m, dict) and m.get("role") == "user":
                t = str(m.get("content") or "").strip()
                if t:
                    first = t
                    break
        if not first:
            first = str(text or "").strip()
        if not first:
            return ""
        return hashlib.sha1(first.encode("utf-8", "replace")).hexdigest()[:16]

    def _recall(self, history, text):
        """조회가 안 걸렸을 때 들고 갈 직전 결과 (없으면 빈 글)."""
        key = self._conv_key(history, text)
        if not key:
            return ""
        with self._lock:
            hit = self._carry.get(key)
        if not hit:
            return ""
        at_len, when, got = hit
        if time.time() - when > self.CARRY_S:
            return ""
        if len(history or []) - at_len > self.CARRY_TURNS:
            return ""
        # ★방금 조회한 것처럼 말하면 안 된다. 어디서 온 글인지 밝힌다.
        return ("(아래는 **이 대화에서 조금 전에 조회해 둔** 요청이력이다. "
                "이번 질문으로 다시 조회하지는 않았다 — 이어지는 질문이라 "
                "그대로 들고 왔다. 내용은 그때 받은 그대로다.)\n" + got)

    def _remember(self, history, text, got):
        key = self._conv_key(history, text)
        if not key or not got:
            return
        with self._lock:
            self._carry[key] = (len(history or []), time.time(), got)
            if len(self._carry) > 32:      # 오래된 대화부터 버린다
                for k in sorted(self._carry,
                                key=lambda k: self._carry[k][1])[:16]:
                    self._carry.pop(k, None)

    def gather(self, text, use_cache=True, history=None):
        """질문에 걸리는 서버들을 불러 근거 글을 만든다 → (글, 부른 도구 수).

        ★같은 글이면 CACHE_S 안에서는 다시 안 조회한다 (계측 + 대화가
          같은 질문으로 두 번 부른다). 캐시로 준 것은 도구 수 0 으로 알린다 —
          "몇 번 돌았나" 를 부풀리면 안 된다.
        """
        key = str(text or "")
        now = time.time()
        if use_cache and self._all_alive():
            with self._lock:
                hit = self._cache.get(key)
                if hit and now - hit[0] < self.CACHE_S:
                    self._remember(history, text, hit[1])
                    return hit[1], 0
        out, used = [], 0
        for s in self.matched(text):
            lines = []
            # ★이 서버에 대한 조회는 한 번에 하나만 (위 _srv_locks 설명 참조)
            with self._srv_lock(s["key"]):
                try:
                    c = self._client(s)
                except Exception as e:  # noqa: BLE001
                    out.append("[{}] 붙지 못했다 ({}). 이 자료는 확인 못 한다."
                               .format(s.get("name") or s["key"], e))
                    continue
                used += self._run_calls(s, c, text, lines)
            if lines:
                out.append("[{}]\n".format(s.get("name") or s["key"])
                           + "\n".join(lines))
        got = "\n\n".join(out)
        if use_cache and got:
            with self._lock:
                self._cache[key] = (now, got, used)
                if len(self._cache) > 64:      # 오래된 것부터 버린다
                    for k in sorted(self._cache,
                                    key=lambda k: self._cache[k][0])[:32]:
                        self._cache.pop(k, None)
        if got:
            # ★실패한 조회는 기억하지 않는다. "붙지 못했다" 를 들고 다니면
            #   이어지는 질문마다 그 글이 따라와서, 서버가 멀쩡해진 뒤에도
            #   서윤이 계속 "요청이력을 확인할 수 없다" 고 말한다.
            #   판정 기준은 llm.py 의 mcp_failed 와 같은 것을 쓴다.
            if used and not ("실패" in got or "못 붙었다" in got):
                self._remember(history, text, got)
            return got, used
        # ★조회가 안 걸렸다. 여기서 빈 글을 주면 서윤은 **방금 자기가 읽은
        #   내용을 못 보는 채로** 답한다 ("그럼 언제 적용돼?" 처럼 이어지는
        #   질문에는 '요청'·'이력' 같은 낱말이 없어서 늘 안 걸린다).
        return self._recall(history, text), 0

    def status(self):
        """지금 MCP 가 어떤 상태인가 — 화면·진단용.

        ★"MCP 안 되는 것 같은데" 를 반복하지 않으려면, **눈으로 볼 수 있는
          자리**가 있어야 한다. 어떤 주소를 보는지, 붙었는지, 왜 못 붙었는지.
        """
        out = []
        # ★진단 화면은 차단기를 무시하고 **진짜로 두들긴다**. "30초 쉬는 중"
        #   이라고 답하면, 서버를 고쳐 놓고 눌러도 계속 안 된다고 나온다.
        with self._lock:
            self._down.clear()
        for s in self.servers:
            key = s["key"]
            c = self._live.get(key)
            alive = bool(c is not None and c.alive())
            trans = str(s.get("transport") or "stdio").lower()
            row = {"key": key, "name": s.get("name") or key,
                   "transport": trans,
                   # ★어느 자리를 보고 있는지가 진단의 반이다. stdio 는
                   #   스크립트, http 는 주소 — 빈 칸으로 두면 "왜 안 되냐" 를
                   #   또 처음부터 짚어야 한다.
                   "addr": s.get("url") or (s.get("env") or {}).get("QA_BASE") or "",
                   # 화면에서 저장한 값이 코드 기본값을 덮고 있으면 그 사실
                   "url_default": s.get("url_default") or "",
                   "script": (s.get("args") or [""])[0] if trans == "stdio" else "",
                   "started": c is not None, "alive": alive,
                   "enabled": bool(s.get("enabled", True)),
                   # 왜 꺼져 있나 (파일이 없다 / 사람이 껐다)
                   "off_reason": s.get("off_reason") or "",
                   "when": list(s.get("when") or [])[:40],
                   "server": (c.server if c else {}) or {},
                   "tools": [], "err": "", "ok": False}
            # ★꺼진 서버는 두들기지 않는다. 껐는데 화면을 열 때마다 붙으러
            #   가면, 끈 이유(느리다)가 그대로 남는다.
            if not row["enabled"]:
                row["err"] = row["off_reason"] or "꺼져 있습니다"
                out.append(row)
                continue
            # 실제로 한 번 두들겨 본다 — 떠 있다고 붙는다는 뜻은 아니다
            try:
                cc = c if alive else self._client(s)
                row["started"] = True
                row["alive"] = True
                row["server"] = cc.server
                row["tools"] = [t["name"] for t in cc.tools()]
                # 맛보기로 부를 도구는 서버마다 다르다 (설정에 적어 둔다)
                probe = s.get("probe") or ("qa_meta" if "qa_meta" in row["tools"]
                                           else "")
                txt, bad = cc.call(probe, s.get("probe_args")) if probe \
                    and probe in row["tools"] else ("", False)
                row["ok"] = not bad
                row["sample"] = (txt or "").splitlines()[:1]
                if bad:
                    row["err"] = txt[:200]
            except Exception as e:  # noqa: BLE001
                row["ok"] = False
                row["err"] = str(e)[:200]
            out.append(row)
        return {"ok": True, "servers": out,
                "on": sum(1 for r in out if r["enabled"]),
                "live": sum(1 for r in out if r.get("ok")),
                "none": not self.servers}

    def close(self):
        with self._lock:
            for c in self._live.values():
                c.close()
            self._live.clear()
