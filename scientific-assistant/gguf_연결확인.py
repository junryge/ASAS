#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gguf_연결확인.py — 집에서 GGUF 연결이 살아 있는지 **코드끼리 붙여** 본다.

    python gguf_연결확인.py

무엇을 보나
  demos_v1/routes_openai.py (진짜)  →  HTTP  →  avatar_2d 게이트웨이 (진짜)
  llama-cpp 와 flask 만 가짜다. 그 둘은 이 확인의 대상이 아니다 —
  **우리가 쓴 코드끼리 말이 통하는가**를 본다.

  GPU 도, 모델 파일도, 서버도 필요 없다. 코드를 고친 뒤 여기부터 돌린다.

llama-cpp 빌드 세 가지를 흉내 낸다
  json_schema 를 아는 빌드 / json_object+schema 만 아는 빌드 /
  response_format 을 아예 모르는 빌드 — 어느 쪽이든 답이 와야 한다.

진짜 모델로 확인하려면
  1) python app.py                      (GGUF 를 올린다)
  2) curl http://127.0.0.1:10009/v1/models
  3) cd real_time_amhs/avatar_2d && python run.py --gguf
"""
import json, os, sys, threading, types, time
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
AV   = os.path.join(ROOT, "real_time_amhs", "avatar_2d")
if not os.path.isdir(os.path.join(ROOT, "demos_v1")):
    sys.exit("demos_v1 이 안 보인다. 이 파일을 app.py 옆에 두고 돌리세요: " + ROOT)

# ── 1. flask 를 가짜로 세운다 (라우트 함수만 꺼내 쓴다) ──────────────
ROUTES = {}
class _Resp:
    def __init__(self, body, mimetype=None, headers=None):
        self.body, self.mimetype, self.headers = body, mimetype, headers or {}
def _jsonify(o): return ("json", o)
class _Req:
    _body = {}
    def get_json(self, silent=False): return self._body
flask = types.ModuleType("flask")
flask.jsonify = _jsonify
flask.Response = _Resp
flask.request = _Req()
sys.modules["flask"] = flask

# ── 2. demos_v1 을 최소한만 세운다 (진짜 routes_openai.py 를 읽는다) ──
sys.path.insert(0, ROOT)
utils = types.ModuleType("demos_v1.utils")
utils.gguf_model = None
utils.gguf_loaded_path = None
utils.BASE_DIR = ROOT
models = types.ModuleType("demos_v1.models")
models.ENV_CONFIG = {
    "gguf-0": {"url": "python://llama-cpp-python", "model": "Qwen3-14B-Q4_K_M",
               "name": "LOCAL (Qwen3-14B-Q4_K_M)",
               "_gguf_path": "/models/Qwen3-14B-Q4_K_M.gguf", "_size_gb": 9.0},
    "gguf-1": {"url": "python://llama-cpp-python", "model": "gemma-3-12b",
               "name": "LOCAL (gemma-3-12b)",
               "_gguf_path": "/models/gemma-3-12b.gguf", "_size_gb": 7.3},
    "dev":    {"url": "http://dev/v1", "model": "gpt-x", "name": "DEV"},
}
pkg = types.ModuleType("demos_v1"); pkg.__path__ = [os.path.join(ROOT, "demos_v1")]
gg  = types.ModuleType("demos_v1.gguf")
LOADED = {"path": None}
def load_gguf_model(p, **k):
    LOADED["path"] = p; utils.gguf_loaded_path = p; utils.gguf_model = FAKE; return True
def _inject_no_think_for_qwen3(msgs, path):
    return msgs
gg.load_gguf_model = load_gguf_model
gg._inject_no_think_for_qwen3 = _inject_no_think_for_qwen3
for n, m in (("demos_v1", pkg), ("demos_v1.utils", utils),
             ("demos_v1.models", models), ("demos_v1.gguf", gg)):
    sys.modules[n] = m

# ── 3. 가짜 llama 모델 ────────────────────────────────────────────────
class Fake:
    last = None
    know = "json_object"          # 이 빌드가 아는 모양
    ctx  = 32768                  # 이 모델의 n_ctx
    def n_ctx(self): return Fake.ctx
    def tokenize(self, b, add_bos=True):
        return [0] * (len(b.decode("utf-8", "replace")) * 2)   # 글자당 2토큰
    def create_chat_completion(self, messages=None, **kw):
        rf = kw.get("response_format")
        if rf is not None:
            t = rf.get("type")
            if t != Fake.know or (Fake.know == "json_object" and "schema" in rf
                                  and not Fake.allow_schema):
                raise ValueError("unsupported response_format: %r" % (rf,))
        Fake.last = dict(kw); Fake.last["messages"] = messages
        # 아바타가 기대하는 JSON 한 덩이
        txt = ('{"emotion":"smile","intensity":0.8,"motion":"nod",'
               '"text":"로컬 GGUF 로 붙었어요."}')
        if kw.get("stream"):
            def g():
                for i in range(0, len(txt), 17):
                    yield {"choices": [{"delta": {"content": txt[i:i+17]}}]}
            return g()
        return {"choices": [{"message": {"role": "assistant", "content": txt},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 22,
                          "total_tokens": 33}}
Fake.allow_schema = True
FAKE = Fake()

import importlib
ro = importlib.import_module("demos_v1.routes_openai")

class FakeApp:
    def route(self, rule, methods=None):
        def deco(fn): ROUTES[(rule, tuple(methods or ["GET"]))] = fn; return fn
        return deco
ro.register_openai_routes(FakeApp())
print("등록된 라우트:", sorted(r for r, _ in ROUTES))

def _find(rule):
    for (r, _m), fn in ROUTES.items():
        if r == rule: return fn
    raise KeyError(rule)

# ── 4. 그 라우트를 진짜 HTTP 로 내보낸다 ──────────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.rstrip("/") != "/v1/models": return self.send_error(404)
        kind, obj = _find("/v1/models")()
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions": return self.send_error(404)
        n = int(self.headers.get("Content-Length") or 0)
        _Req._body = json.loads(self.rfile.read(n) or b"{}")
        # 토큰을 보냈는지 기록 (없어야 한다)
        SEEN["auth"] = self.headers.get("Authorization")
        out = _find("/v1/chat/completions")()
        if isinstance(out, _Resp):                      # 스트리밍
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream"); self.end_headers()
            for chunk in out.body:
                self.wfile.write(chunk.encode()); self.wfile.flush()
            return
        kind, obj = out if isinstance(out, tuple) and out[0] == "json" else ("json", out)
        code = 200
        if isinstance(obj, tuple):                       # (payload, status)
            obj, code = obj
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

SEEN = {}
srv = HTTPServer(("127.0.0.1", 10009), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)

# ── 5. 진짜 아바타 코드로 붙어 본다 ───────────────────────────────────
# ★아바타는 회사 배포본에 없을 수 있다. 없으면 서버 쪽만 확인하고 끝낸다.
if not os.path.isdir(AV):
    print("\n  (avatar_2d 가 없어 서버 쪽만 확인했습니다 — /v1 문은 정상입니다)")
    srv.shutdown()
    sys.exit(0)
sys.path.insert(0, AV)
import importlib.util
def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sys.modules[name] = m; sp.loader.exec_module(m); return m

runpy_ = load("avrun", os.path.join(AV, "run.py"))
from avatar import llm as avllm, config as avcfg
from avatar.server import build_opener

up = "http://127.0.0.1:10009/v1"
op = build_opener(up)

print("\n[1] 모델 목록 (토큰 없이)")
ms = runpy_.fetch_models(up, "", op)
print("    ", ms)
assert ms == ["gemma-3-12b", "Qwen3-14B-Q4_K_M"] or set(ms) == {"gemma-3-12b", "Qwen3-14B-Q4_K_M"}, ms

print("\n[2] 한 번에 (Gateway.chat)")
gw = avllm.Gateway(up, "", op, timeout=20)
res, err = gw.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role": "user", "content": "안녕"}])
print("     결과:", res, "  오류:", err)
assert err is None and res["text"] == "로컬 GGUF 로 붙었어요.", (res, err)
assert res["emotion"] == "smile" and res["motion"] == "nod", res
print("     Authorization 헤더:", SEEN.get("auth"))
assert SEEN.get("auth") is None, "토큰 없는데 Authorization 을 보냈다"
print("     모델 로드 요청:", LOADED["path"])
assert LOADED["path"] == "/models/Qwen3-14B-Q4_K_M.gguf"
print("     response_format 전달:", Fake.last.get("response_format"))

print("\n[3] 스트리밍 (Gateway.chat_stream)")
evs = list(gw.chat_stream("gemma-3-12b", 0.7, [{"role": "user", "content": "안녕"}]))
kinds = [k for k, _ in evs]
print("     이벤트:", kinds)
fin = [v for k, v in evs if k == "final"]
assert fin and fin[0]["text"] == "로컬 GGUF 로 붙었어요.", fin
assert "emo" in kinds and "text" in kinds, kinds
print("     최종:", fin[0])
print("     모델 갈아끼움:", LOADED["path"])
assert LOADED["path"] == "/models/gemma-3-12b.gguf"

print("\n[4] 모델 이름을 안 줘도 (지금 올라온 것)")
_Req._body = {}
gw2 = avllm.Gateway(up, "", op, timeout=20)
r2, e2 = gw2.chat("", 0.7, [{"role": "user", "content": "hi"}])
print("     결과:", r2["text"], " 오류:", e2)

print("\n[5] 없는 모델 → 404 로 알려 준다")
r3, e3 = gw2.chat("없는모델", 0.7, [{"role": "user", "content": "hi"}])
print("     오류:", str(e3)[:90])
assert e3 and "404" in str(e3), e3

print("\n[6] 이 빌드가 json_schema 를 모를 때 — 한 계단씩 낮춘다")
Fake.last = None
r6, e6 = gw2.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role":"user","content":"hi"}])
print("     쓰인 response_format:", Fake.last.get("response_format"))
assert e6 is None and r6["text"], (r6, e6)
assert Fake.last["response_format"]["type"] == "json_object", Fake.last
assert "schema" in Fake.last["response_format"], "스키마까지 버렸다"

print("\n[7] schema 도 모르는 더 구형 빌드")
Fake.allow_schema = False; Fake.last = None
r7, e7 = gw2.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role":"user","content":"hi"}])
print("     쓰인 response_format:", Fake.last.get("response_format"))
assert e7 is None and r7["text"], (r7, e7)
assert Fake.last["response_format"] == {"type": "json_object"}, Fake.last

print("\n[8] response_format 을 아예 모르는 빌드 → 그래도 답이 온다")
Fake.know = None; Fake.last = None
r8, e8 = gw2.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role":"user","content":"hi"}])
print("     쓰인 response_format:", Fake.last.get("response_format"))
assert e8 is None and r8["text"] == "로컬 GGUF 로 붙었어요.", (r8, e8)
assert Fake.last.get("response_format") is None, Fake.last

print("\n[9] 지금 올라온 모델이 목록 맨 앞이다 (갈아끼움 방지)")
import urllib.request as _u
utils.gguf_loaded_path = "/models/gemma-3-12b.gguf"
ids = [m["id"] for m in json.loads(_u.urlopen(up + "/models").read())["data"]]
print("     목록:", ids, " (올라온 것: gemma-3-12b)")
assert ids[0] == "gemma-3-12b", ids
utils.gguf_loaded_path = "/models/Qwen3-14B-Q4_K_M.gguf"
ids = [m["id"] for m in json.loads(_u.urlopen(up + "/models").read())["data"]]
print("     목록:", ids, " (올라온 것: Qwen3-14B-Q4_K_M)")
assert ids[0] == "Qwen3-14B-Q4_K_M", ids

print("\n[10] 컨텍스트에 맞춰 max_tokens 를 줄인다")
Fake.ctx = 8192; Fake.last = None
gw3 = avllm.Gateway(up, "", op, timeout=20)
r10, e10 = gw3.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role":"user","content":"가"*3000}])
mt = Fake.last["max_tokens"]
print("     n_ctx 8192 · 프롬프트 6000토큰 → max_tokens =", mt, "(예전엔 4096 고정)")
assert e10 is None, e10
assert mt < 4096 and mt <= 8192 - 6000, mt

print("\n[11] 프롬프트가 컨텍스트를 넘으면 조용히 안 자른다")
r11, e11 = gw3.chat("Qwen3-14B-Q4_K_M", 0.7, [{"role":"user","content":"가"*6000}])
print("     오류:", str(e11)[:100])
assert e11 and "400" in str(e11), e11
Fake.ctx = 32768

srv.shutdown()
print("\n=== 전부 통과 ===")
