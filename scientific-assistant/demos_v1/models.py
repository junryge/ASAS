"""
demos_v1/models.py - MODEL_REGISTRY, API_MODEL_TIERS, ENV_CONFIG, FALLBACK_CHAINS

★API 모델은 게이트웨이(/v1/models)가 주는 것만 쓴다 (2026-09-28).
  예전엔 api_config.json 의 "models" 와 이 파일의 기본값에 모델을 하나씩 등록했다. 게이트웨이의
  모델이 바뀔 때마다 손으로 고쳐야 했고, 없어진 모델이 목록에 남아 고르면 실패했다.
  이제 데모스가 켜질 때 GET {게이트웨이}/v1/models 를 읽어 그 목록만 등록하고, 목록을 달라는
  요청(/api/config · /api/code/models)이 오면 5분이 지났을 때 다시 읽는다. 데모스 본창 ·
  개인 에이전트 창 · 코딩 어시스턴트 · UIO 가 모두 이 목록을 쓴다.
  api_config.json 의 "models" · "api_model_tiers" · "fallback_chains" · "default_model_priority"
  는 더 이상 읽지 않는다 (남아 있어도 무시한다).

  게이트웨이 주소: 환경변수 LLM_GATEWAY_BASE > api_config.json "llm_gateway": {"base_url": …}
                  > 기본 http://hcp.llm.skhynix.com
  토큰: TOKEN.TXT (다른 API 호출과 같은 것). "llm_gateway": {"token_file": "…"} 로 바꿀 수 있다.
  먼저 고를 모델: "llm_gateway": {"default_model": "<모델 id>"} — 없으면 게이트웨이가 준 순서.

★여러 모듈이 `from demos_v1.models import ENV_CONFIG` 로 **같은 dict** 를 들고 있다. 그래서
  다시 읽을 때 새 dict 로 바꾸지 않고 그 안을 고친다. gguf-N(로컬 모델) 항목은 그대로 둔다.
★게이트웨이에 못 닿으면 마지막으로 읽은 목록을 그대로 쓴다 (처음부터 못 닿으면 API 모델 없음).
"""
import os
import re
import threading
import time

from demos_v1.config import _EXT_CONFIG, API_TOKEN
from demos_v1.utils import BASE_DIR as _ROOT_DIR  # api_config.json / TOKEN.TXT 가 있는 경로

# ============================================
# 설정
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "scientific-skills")
TOKEN_FILE = os.path.join(BASE_DIR, "TOKEN.TXT")
PROMPTS_DIR = os.path.join(BASE_DIR, "saved-prompts")
os.makedirs(PROMPTS_DIR, exist_ok=True)

_GW = _EXT_CONFIG.get("llm_gateway") or {}
GATEWAY_BASE = (os.getenv("LLM_GATEWAY_BASE") or _GW.get("base_url") or "http://hcp.llm.skhynix.com").strip().rstrip("/")
if GATEWAY_BASE.endswith("/v1"):
    GATEWAY_BASE = GATEWAY_BASE[:-3]
GATEWAY_TIMEOUT = float(_GW.get("timeout_s", 6))
GATEWAY_REFRESH_S = float(_GW.get("refresh_s", 300))
GATEWAY_DEFAULT_MODEL = str(_GW.get("default_model") or "").strip()

# ── 지금 쓰는 목록 (다른 모듈이 같은 객체를 들고 있다 — 새로 만들지 말고 안을 고친다) ──
MODEL_REGISTRY: dict = {}            # 키 → {env_id, model, url, name, capabilities, context_window, tier, …}
ENV_CONFIG: dict = {}                # env_id → {url, model, name, token}   (+ 부팅 때 gguf-N)
ENV_TO_REGISTRY: dict = {}           # env_id → 키
API_MODEL_TIERS: dict = {"large": [], "medium": [], "small": []}
FALLBACK_CHAINS: dict = {}           # 키 → [다음에 시도할 키, …]
DEFAULT_MODEL_PRIORITY: list = []    # 기본으로 고를 순서 (키)
GATEWAY_STATUS: dict = {"base": GATEWAY_BASE, "count": 0, "error": "", "fetched_at": 0.0,
                        "tried_at": 0.0, "skipped": []}

_LOCK = threading.Lock()

# 대화에 못 쓰는 모델(임베딩 · 재정렬 · 음성)은 목록에 올리지 않는다
_NON_CHAT = re.compile(r"embed|rerank|(^|[-_/])(bge|e5|gte)[-_]|whisper|(^|[-_])(tts|stt)([-_]|$)", re.I)
_VISION = re.compile(r"(^|[-_./])(vl|vlm|vision|llava|pixtral|internvl)(\d|[-_.]|$)", re.I)
_SIZE = re.compile(r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*[bB](?![A-Za-z])")     # 397B 는 잡고 A17B(활성) 는 뺀다


def _resolve_model_token(info):
    """모델 전용 토큰. 키를 코드/config 에 박지 않는다 — token_file 에서 읽는다."""
    t = (info.get("token") or "").strip()
    if t:
        return t
    tf = (info.get("token_file") or "").strip()
    if tf:
        for base in (_ROOT_DIR, BASE_DIR, os.getcwd()):
            p = os.path.join(base, tf)
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8-sig") as f:
                        return f.read().strip()
                except Exception:
                    pass
    return ""


def _gateway_token():
    """게이트웨이 토큰 — llm_gateway.token_file 이 있으면 그것, 없으면 TOKEN.TXT."""
    return _resolve_model_token({"token_file": _GW.get("token_file", "")}) or API_TOKEN


def _slug(mid):
    s = re.sub(r"[^a-z0-9]+", "-", str(mid).lower()).strip("-")[:60] or "model"
    if s.startswith(("gguf-", "spark-")):               # 화면이 머리글자로 로컬·스파크를 가른다
        s = "api-" + s
    return s


def _size_b(mid):
    nums = [float(x) for x in _SIZE.findall(str(mid))]
    return max(nums) if nums else None


def _tier(mid):
    b = _size_b(mid)
    if b is None:
        return "medium"
    return "large" if b >= 34 else "medium" if b >= 24 else "small"


def _ctx(item):
    if isinstance(item, dict):
        for k in ("max_model_len", "context_length", "context_window", "max_context_length"):
            v = item.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return int(v)
    return 128000


def build_registry(items, base=None, token=""):
    """게이트웨이 /v1/models 의 목록 → (MODEL_REGISTRY, 뺀 모델 id 목록). 순서는 게이트웨이 순서."""
    base = (base or GATEWAY_BASE).rstrip("/")
    reg, skipped, seen = {}, [], set()
    for it in items or []:
        mid = (it.get("id") or it.get("model") or it.get("name")) if isinstance(it, dict) else it
        mid = str(mid or "").strip()
        if not mid or mid in seen:
            continue
        seen.add(mid)
        if _NON_CHAT.search(mid):
            skipped.append(mid)
            continue
        key = _slug(mid)
        n = 2
        while key in reg:
            key = f"{_slug(mid)}-{n}"
            n += 1
        tier = _tier(mid)
        vision = bool(_VISION.search(mid))
        caps = {"text", "vision"} if vision else {"text", "analysis", "code"}
        caps.add({"large": "large", "medium": "medium", "small": "fast"}[tier])
        reg[key] = {
            "env_id": key,
            "model": mid,
            "url": f"{base}/v1/chat/completions",
            "name": mid,
            "capabilities": caps,
            "context_window": _ctx(it),
            "tier": tier,
            "priority": {"large": 1, "medium": 2, "small": 3}[tier],
            "cost_tier": {"large": "high", "medium": "medium", "small": "low"}[tier],
            "token": token,
            "source": "gateway",
        }
    return reg, skipped


def _apply(reg):
    """새 목록을 **같은 객체들 안에** 넣는다 (gguf-N 은 그대로, API 가 앞)."""
    if reg == MODEL_REGISTRY:
        return
    MODEL_REGISTRY.clear()
    MODEL_REGISTRY.update(reg)
    gguf = [(k, v) for k, v in ENV_CONFIG.items() if str(k).startswith("gguf-")]
    ENV_CONFIG.clear()
    for v in reg.values():
        ENV_CONFIG[v["env_id"]] = {"url": v["url"], "model": v["model"], "name": v["name"], "token": v.get("token", "")}
    for k, v in gguf:
        ENV_CONFIG[k] = v
    ENV_TO_REGISTRY.clear()
    ENV_TO_REGISTRY.update({v["env_id"]: k for k, v in reg.items()})

    keys = list(reg)                                     # 게이트웨이가 준 순서
    text = [k for k in keys if "vision" not in reg[k]["capabilities"]]
    vis = [k for k in keys if "vision" in reg[k]["capabilities"]]
    order = text + vis                                   # 기본은 글 모델부터
    if GATEWAY_DEFAULT_MODEL:
        want = [k for k in order if GATEWAY_DEFAULT_MODEL in (k, reg[k]["model"])]
        order = want + [k for k in order if k not in want]
    DEFAULT_MODEL_PRIORITY[:] = order

    API_MODEL_TIERS.clear()
    for t in ("large", "medium", "small"):
        API_MODEL_TIERS[t] = [k for k in keys if reg[k]["tier"] == t and "vision" not in reg[k]["capabilities"]]
    FALLBACK_CHAINS.clear()
    for k in keys:
        pool = [x for x in (vis + text if k in vis else text) if x != k]
        FALLBACK_CHAINS[k] = pool[:3]


def _fetch():
    import requests
    token = _gateway_token()
    if not token:
        raise RuntimeError("TOKEN.TXT 가 비어 있습니다")
    r = requests.get(f"{GATEWAY_BASE}/v1/models", headers={"Authorization": f"Bearer {token}"},
                     timeout=GATEWAY_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} {r.text[:120]}")
    data = r.json()
    if isinstance(data, dict):
        data = data.get("data", data.get("models", []))
    if not isinstance(data, list):
        raise RuntimeError("모델 목록 형식이 이상합니다")
    return data


_BG = {"on": False}


def refresh_models(force=False, wait=True):
    """게이트웨이에서 모델 목록을 다시 읽는다. 5분(refresh_s) 안이면 그냥 둔다.
    못 읽으면 마지막 목록을 그대로 두고, 목록이 빈 동안은 1분에 한 번만 다시 시도한다.
    wait=False: 목록이 이미 있으면 기다리지 않는다 — 지금 목록으로 답하고 뒤에서 새로 읽는다
    (화면이 게이트웨이 응답을 기다리며 멈추지 않게. 목록이 비었을 때만 그 자리에서 읽는다)."""
    now = time.time()
    st = GATEWAY_STATUS
    if not force and not wait and st["count"] and now - st["fetched_at"] >= GATEWAY_REFRESH_S:
        if not _BG["on"]:
            _BG["on"] = True

            def _run():
                try:
                    refresh_models(force=True)
                finally:
                    _BG["on"] = False
            threading.Thread(target=_run, name="gateway-models", daemon=True).start()
        return st
    with _LOCK:
        st = GATEWAY_STATUS
        if not force:
            if st["count"] and now - st["fetched_at"] < GATEWAY_REFRESH_S:
                return st
            if not st["count"] and now - st["tried_at"] < 60:
                return st
        st["tried_at"] = now
        try:
            tf = (_GW.get("token_file") or "").strip()
            reg, skipped = build_registry(_fetch(), token=_gateway_token() if tf else "")
        except Exception as e:                                   # noqa: BLE001 — 게이트웨이 탓에 앱이 죽으면 안 된다
            st["error"] = f"{type(e).__name__}: {e}"[:300]
            print(f"  ⚠️  게이트웨이 모델 목록을 못 읽음 ({GATEWAY_BASE}): {st['error']}")
            return st
        _apply(reg)
        st.update(count=len(reg), error="", fetched_at=now, skipped=skipped)
        return st


def pick_env(kind="default"):
    """자동 선택용 env_id. kind: default · large · small · vision.
    그 종류가 없으면 가까운 것(→ 기본 글 모델)으로, 아무것도 없으면 빈 글."""
    keys = [k for k in DEFAULT_MODEL_PRIORITY if k in MODEL_REGISTRY]
    if not keys:
        return ""
    reg = MODEL_REGISTRY
    text = [k for k in keys if "vision" not in reg[k]["capabilities"]]
    vis = [k for k in keys if "vision" in reg[k]["capabilities"]]
    if kind == "vision":
        cand = vis + text
    elif kind == "large":
        cand = [k for k in text if reg[k].get("tier") == "large"] + text + vis
    elif kind == "small":
        cand = ([k for k in text if reg[k].get("tier") == "small"]
                + [k for k in text if reg[k].get("tier") == "medium"] + text + vis)
    else:
        cand = keys
    return reg[cand[0]]["env_id"]


def env_name(env_id):
    return ENV_CONFIG.get(env_id, {}).get("name") or env_id or "(모델 없음)"


# 켜질 때 한 번 읽는다 (시험 등에서 네트워크를 쓰지 않으려면 LLM_GATEWAY_OFF=1)
if os.getenv("LLM_GATEWAY_OFF", "").strip() not in ("1", "true", "yes"):
    _st = refresh_models(force=True)
    if _st["count"]:
        print(f"  🌐 게이트웨이 모델 {_st['count']}개 등록 ({GATEWAY_BASE}/v1/models)"
              + (f" · 대화용 아님 {len(_st['skipped'])}개 뺌" if _st["skipped"] else ""))

# Reranker 기능 플래그 (bge-reranker 엔드포인트 안정화 후 활성화)
RERANKER_ENABLED = False
