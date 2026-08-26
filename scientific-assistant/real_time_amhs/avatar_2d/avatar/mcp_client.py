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

PROTO = "2025-06-18"


class McpError(Exception):
    """규격 오류 — 서버가 JSON-RPC error 를 돌려줬거나 끊겼다."""


class Client:
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
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params=None):
        with self._lock:
            self._id += 1
            mid = self._id
            self._write({"jsonrpc": "2.0", "id": mid, "method": method,
                         "params": params or {}})
            while True:
                line = self.proc.stdout.readline()
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
    if kind == "any":
        # 여러 규칙을 차례로 시도한다 (코드명 먼저, 없으면 사람 이름 …)
        for one in spec.get("of") or []:
            v = _arg_of(text, one)
            if v is not None:
                return v
    return None


class Hub:
    """config.MCP_SERVERS 를 보고 필요한 것만 띄워 쓴다.

    · 질문에 걸리는 서버가 없으면 **아무것도 안 띄운다** (평소엔 비용 0).
    · 한 번 띄운 서버는 살려 두고 다시 쓴다. 죽으면 다음 질문에 다시 띄운다.
    · 서버가 죽어 있어도 대화는 계속돼야 한다 — 실패는 글로 적어 넘긴다.
    """

    def __init__(self, servers=None, say=None):
        self.servers = [s for s in (servers or []) if s.get("enabled", True)]
        self._live = {}
        self._lock = threading.RLock()
        self._say = say or (lambda *_a: None)

    def matched(self, text):
        """이 질문에 걸리는 서버 목록 (화면 계측·시험용)."""
        return [s for s in self.servers
                if _hits(text, s.get("when"), s.get("when_re"))]

    def _client(self, s):
        with self._lock:
            c = self._live.get(s["key"])
            if c is not None and c.proc.poll() is None:
                return c
            if c is not None:
                c.close()
                self._live.pop(s["key"], None)
            c = Client(s.get("command") or sys.executable,
                       s.get("args"), s.get("env"), s.get("cwd"),
                       s.get("timeout", 20))
            self._live[s["key"]] = c
            self._say("     ↳ MCP 연결: {} ({} {})".format(
                s.get("name") or s["key"], c.server.get("name") or "?",
                c.server.get("version") or ""))
            return c

    def gather(self, text):
        """질문에 걸리는 서버들을 불러 근거 글을 만든다 → (글, 부른 도구 수)."""
        out, used = [], 0
        for s in self.matched(text):
            lines = []
            try:
                c = self._client(s)
            except Exception as e:  # noqa: BLE001
                out.append("[{}] 붙지 못했다 ({}). 이 자료는 확인 못 한다."
                           .format(s.get("name") or s["key"], e))
                continue
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
                txt, bad = c.call(call["tool"], args)
                used += 1
                if txt:
                    lines.append("· {}{}\n{}".format(
                        call.get("label") or call["tool"],
                        " (실패)" if bad else "", txt))
            if lines:
                out.append("[{}]\n".format(s.get("name") or s["key"])
                           + "\n".join(lines))
        return "\n\n".join(out), used

    def close(self):
        with self._lock:
            for c in self._live.values():
                c.close()
            self._live.clear()
