#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — LLM 판단·리포트 (독립)

지식은 전부 스킬 4종 + 페르소나에 있다. 이 모듈은 그것을 로드해 주입만 한다.
도메인 규칙을 여기에 새로 쓰지 않는다 (스킬이 단일 출처).

  · m16_hub_일반_v3.5.md
  · m16_hub_임계값_v3.5.md
  · m16_hub_카파시_v3.5.md
  · m16_hub_결과해석_도메인_고객인용V3.5.md
  · 페르소나_통합.txt

데모스(demos_v1) 를 import 하지 않는다. OpenAI 호환 chat/completions 직접 호출.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from lp_client import load_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 스킬 규칙(페르소나 §용어 표준)과 동일 — LLM이 어겨도 여기서 결정적으로 제거.
# ★순서가 중요하다: 긴 표현을 먼저 지워야 짧은 규칙이 조각을 남기지 않는다
#   (예 '리프터 역방향 카운트' 를 먼저 잡아야 '카운트' 가 홀로 안 남는다).
_FORBIDDEN = [
    # 리프터 — '역방향'·'카운트' 두 단어는 어디에도 노출 금지
    ("리프터 역방향 카운트", "리프터 정체"),
    ("리프터 역방향", "리프터 정체"),
    ("역방향 카운트", "정체"),
    ("리프터 막힘", "리프터 정체"),
    ("리프터막힘", "리프터 정체"),
    ("막힌 리프터", "정체 리프터"),
    ("막힌 곳", "정체 구간"),
    ("역방향", "정체"),
    ("역증가", "정체"),
    ("역류", "밀림"),
    ("광역정체", "정체"),
    # 정체 표현
    ("물류 정체", "반송 정체"),
    ("물류 이동", "반송"),
    ("적체", "정체"),
    # Storage
    ("저장공간 사용률", "Storage 사용률"),
    ("저장공간 포화", "Storage FULL"),
    ("저장포화", "Storage FULL"),
    ("저장창고", "Storage"),
    ("저장공간", "Storage"),
    ("저장율", "Storage 사용률"),
    ("100% 포화", "100% FULL"),
    ("포화 상태", "FULL 상태"),
    ("만석", "FULL"),
    # 용어
    ("M16 허브룸", "M16 HUBROOM"),
    ("허브룸", "HUBROOM"),
    ("반송카", "OHT"),
    ("진원지", "시작 영역"),
    ("감독관 의견", "에이전트 의견"),
    ("감독관의견", "에이전트 의견"),
    ("감독관 제언", "에이전트 제언"),
    # 과장 표현
    ("치솟았습니다", "상승했습니다"),
    ("치솟음", "상승"),
    ("급증", "상승"),
]

# 한 글자짜리는 통짜 치환하면 엉뚱한 말이 깨진다 — '큐' 는 '디스크큐' 같은
# 조어 안에, '짐' 은 '짐작' 안에 들어 있다. 앞은 한글이 아니어야 하고, 뒤는
# **조사이거나 낱말 끝**일 때만 바꾼다 (큐가·짐이 는 바꾸고 짐작 은 놔둔다).
_JOSA = r"(?=이|가|은|는|을|를|의|와|과|도|만|에|으로|로|부터|까지|[^가-힣]|$)"
_FORBIDDEN_RE = [
    (r"(?<![가-힣A-Za-z])큐" + _JOSA, "Queue"),
    (r"(?<![가-힣])짐" + _JOSA, "Carrier"),
]

# 바꿔 넣은 말에 붙는 조사를 받침에 맞게 고친다.
#   저장공간이 → Storage이(X) → Storage가(O)
#   진원지는   → 시작 영역는(X) → 시작 영역은(O)
_OPEN = ("Storage", "Carrier", "Queue", "OHT")            # 모음으로 끝남
_CLOSED = ("HUBROOM", "FULL", "시작 영역")                 # 받침으로 끝남
_TO_OPEN = [("이", "가"), ("은", "는"), ("을", "를"), ("과", "와"), ("으로", "로")]


def _fix_josa(text: str) -> str:
    import re
    for w in _OPEN:
        for closed, open_ in _TO_OPEN:
            text = re.sub(re.escape(w) + closed + r"(?![가-힣])", w + open_, text)
    for w in _CLOSED:
        for closed, open_ in _TO_OPEN:
            text = re.sub(re.escape(w) + open_ + r"(?![가-힣])", w + closed, text)
    return text

_skills_cache: dict | None = None


def load_skills(cfg: dict | None = None) -> dict:
    """스킬 4종 + 페르소나 로드 (캐시)."""
    global _skills_cache
    if _skills_cache is not None:
        return _skills_cache

    cfg = cfg or load_config()
    lc = cfg.get("llm", {})
    # 폴더 안 skills/ 가 있으면 그것부터 (완전 자립 배포용), 없으면 config 경로
    local = os.path.join(BASE_DIR, "skills")
    if os.path.isdir(local) and any(n in os.listdir(local) for n in lc.get("skills", [])):
        sdir = local
    else:
        sdir = lc.get("skills_dir", "../m16_hub_skills")
        if not os.path.isabs(sdir):
            sdir = os.path.normpath(os.path.join(BASE_DIR, sdir))

    out = {"dir": sdir, "skills": {}, "persona": "", "missing": []}
    for name in lc.get("skills", []):
        p = os.path.join(sdir, name)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                out["skills"][name] = f.read()
        else:
            out["missing"].append(name)

    pn = lc.get("persona", "페르소나_통합.txt")
    pp = os.path.join(sdir, pn)
    if os.path.isfile(pp):
        with open(pp, "r", encoding="utf-8") as f:
            out["persona"] = f.read()
    else:
        out["missing"].append(pn)

    _skills_cache = out
    return out


def scrub(text: str) -> str:
    """스킬 금지어 결정적 제거 + 용어 표준 적용.

    ★raw 컬럼명(M16HUB.QUE.LFT.3F_LFT_REVERSALCNT 등)은 ASCII 라 훼손되지
      않는다 — 페르소나도 '컬럼명은 그대로, 읽는 문장만 변환' 이라고 못박는다.
    """
    import re
    for a, b in _FORBIDDEN:
        text = text.replace(a, b)
    for pat, b in _FORBIDDEN_RE:
        text = re.sub(pat, b, text)
    text = re.sub(r"\s*카운트\s*", " ", text)
    text = _fix_josa(text)
    return re.sub(r"[ \t]{2,}", " ", text)


def build_system_prompt(cfg: dict | None = None) -> str:
    """페르소나 + 스킬 4종을 시스템 프롬프트로 조립."""
    cfg = cfg or load_config()
    sk = load_skills(cfg)
    parts = [
        "당신은 SK하이닉스 M16 HUBROOM 반송 관제 분석 에이전트다.",
        "아래 페르소나와 지식문서(스킬)의 규칙을 최우선으로 따른다. "
        "도메인 판단은 반드시 이 문서들에 근거하고, 문서에 없는 호기·방향·설비를 지어내지 마라.",
        # ★ 이 모델은 그냥 두면 영어로 추론·답변한다. 출력 언어를 못박는다.
        "★출력 언어: 반드시 한국어. 영어 문장·영어 서술 금지 "
        "(설비·raw 컬럼명 같은 고유명사는 원문 그대로 써도 된다).",
        "★추론 과정을 출력하지 마라. 'Thinking Process', 'Analyze the Request' 같은 "
        "서술을 쓰지 말고 요구된 형식만 바로 출력한다.",
        "",
        "═══════ 페르소나 ═══════",
        sk["persona"],
    ]
    for name, body in sk["skills"].items():
        parts += ["", f"═══════ 스킬: {name} ═══════", body]
    if sk["missing"]:
        parts += ["", f"(경고: 다음 문서를 찾지 못함 — {', '.join(sk['missing'])})"]
    return "\n".join(parts)


def _api_key(cfg: dict) -> str:
    """LLM API 키 — 이 폴더의 자체 키 파일만 본다.

    ★데모스 TOKEN.TXT 를 참조하지 않는다 (완전 독립).
    우선순위: config.llm.api_key_file (이 폴더 내부) → 환경변수.
    """
    lc = cfg.get("llm", {})
    path = lc.get("api_key_file", "token.txt")
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    # 폴더 밖 경로는 거부 — 독립성 보장
    if os.path.commonpath([os.path.abspath(path), BASE_DIR]) != BASE_DIR:
        print(f"[LLM] ⚠️ api_key_file 이 폴더 밖을 가리킴 — 무시: {path}")
    elif os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                k = f.read().strip()
            if k:
                k.encode("ascii")          # 한글 플레이스홀더 방어
                return k
        except UnicodeEncodeError:
            print(f"[LLM] ⚠️ {path} 에 비영문 문자 — 실제 키로 교체하세요")
        except Exception as e:
            print(f"[LLM] ⚠️ 키 파일 읽기 실패: {e}")

    return os.getenv(lc.get("api_key_env", "GAIA_API_KEY"), "").strip()


def chat(messages: list[dict], cfg: dict | None = None,
         max_tokens: int | None = None, temperature: float | None = None,
         json_prefill: bool = False, prefill: str | None = None,
         extra: dict | None = None):
    """OpenAI 호환 호출 → (text, None) 또는 (None, error).

    json_prefill=True 면 assistant 턴을 '{' 로 미리 채워 JSON 만 나오게 유도한다
    (사고 모델이 평문 추론을 먼저 쓰는 것을 막는다).

    extra 는 payload 에 그대로 얹는 게이트웨이 옵션이다. 프롬프트로 부탁하는
    대신 서버 기능으로 강제할 때 쓴다 —
      · response_format={"type":"json_object"}  → JSON 이외 출력 자체를 막는다
      · chat_template_kwargs={"enable_thinking": False} → 템플릿에서 사고 차단
      · reasoning_effort="low" (gpt-oss 계열)
    게이트웨이가 모르는 키를 받으면 400 을 내므로, 호출부가 400 을 보고
    옵션을 하나씩 빼면서 재시도한다 (analysis._call_stage).
    """
    cfg = cfg or load_config()
    lc = cfg.get("llm", {})
    if not lc.get("enabled", True):
        return None, "LLM 비활성 (config.llm.enabled=false)"

    model = lc.get("model", "gaia-Qwen3.5-397B-A17B")
    msgs = messages
    # ★ 사고(reasoning) 모델은 그냥 부르면 사고 토큰만 쓰다 max_tokens 에 걸려
    #   본문이 비거나 추론문만 온다. 그래서 '/no_think' 를 넣어 사고를 끈다.
    #   ※ 예전엔 이름에 'qwen3' 가 있을 때만 넣었다. 그러다 gaia-GLM-5.2(1차),
    #     gaia-lst-gpt-oss-120b(3차) 처럼 이름이 다른 사고 모델이 통째로
    #     빠져나가 JSON 대신 추론문을 뱉고 단계가 전부 실패했다.
    #     이제 게이트웨이의 사고 모델 계열을 모두 포함한다 (config 로 조정 가능).
    if lc.get("no_think", True) and _is_reasoning_model(model, lc):
        msgs = _inject_no_think(messages)

    payload = {
        "model": model,
        "messages": msgs,
        "temperature": temperature if temperature is not None else lc.get("temperature", 0.2),
        "max_tokens": max_tokens or lc.get("max_tokens", 2048),
        "stream": False,
    }
    # 서버가 지원하면 템플릿 수준에서도 사고를 끈다 (vLLM/Qwen 계열)
    if lc.get("disable_thinking_kwarg", False):
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    # 호출부가 지정한 게이트웨이 옵션 (response_format 등) — 위 기본값보다 우선
    if isinstance(extra, dict):
        payload.update(extra)
    # ★ JSON 프리필 — assistant 턴을 미리 채워 모델이 그 뒤를 이어 쓰게 만든다.
    #   이 게이트웨이는 /no_think 를 안 듣고 추론을 먼저 쓴다.
    #   '{' 만 넣으면 모델이 JSON 이 아니라 그 뒤에 산문을 이어 쓰므로
    #   **첫 키까지** 넣어 값부터 채우게 못박는다.
    pre = prefill if prefill is not None else (
        (lc.get("json_prefill_text") or '{"실제이상": "') if json_prefill else "")
    if pre:
        payload["messages"] = list(payload["messages"]) + [
            {"role": "assistant", "content": pre}]
    headers = {"Content-Type": "application/json"}
    key = _api_key(cfg)
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(
        lc.get("url"), method="POST", headers=headers,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    try:
        with urllib.request.urlopen(req, timeout=lc.get("timeout_s", 90)) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        choices = data.get("choices") or []
        if not choices:
            return None, f"빈 응답: {str(data)[:200]}"
        msg = choices[0].get("message") or {}
        fin = choices[0].get("finish_reason")
        txt = _strip_think(msg.get("content") or "")
        if not txt:
            # 사고만 하고 본문을 못 낸 경우 — reasoning 필드에서라도 건져본다
            for k in ("reasoning_content", "reasoning", "thinking"):
                txt = _strip_think(msg.get(k) or "")
                if txt:
                    break
        if not txt:
            # ★ 조용히 빈 문자열을 돌려주면 안 된다 (예전엔 여기서 파서 폴백이
            #   {"확신도":0} 을 만들어 '오류 없는 빈 판단' 이 CSV 에 쌓였다)
            usage = data.get("usage") or {}
            return None, (f"본문 없는 응답 (finish_reason={fin}, "
                          f"max_tokens={payload['max_tokens']}, "
                          f"완료토큰={usage.get('completion_tokens')}) — "
                          f"사고 토큰만 쓰고 잘렸을 가능성. max_tokens 를 올리거나 "
                          f"config.llm.no_think 를 확인하세요")
        # 프리필은 보통 응답에 안 실려 오므로 되붙인다. 단, 모델이 프리필을
        # 통째로 다시 쓴 경우엔 붙이면 안 된다 ('{"구간": "' + '{"구간":"…' = 깨진 JSON).
        # 공백 차이('{"구간": "' vs '{"구간":"')로 못 알아보던 버그가 있어
        # 공백을 지우고 비교한다.
        if pre:
            _sq = lambda t: "".join(str(t).split())
            if not _sq(txt).startswith(_sq(pre)[:12]):
                txt = pre + txt
        return scrub(txt), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# 사고(reasoning) 모델 이름 조각 — 하나라도 들어 있으면 '/no_think' 를 넣는다.
# config.llm.reasoning_models 로 갈아끼울 수 있다.
_REASONING_HINTS = ("qwen3", "qwen3.5", "qwen3.6", "glm", "gpt-oss", "gaia", "deepseek", "r1")


def _is_reasoning_model(model: str, lc: dict | None = None) -> bool:
    hints = (lc or {}).get("reasoning_models")
    if not isinstance(hints, (list, tuple)) or not hints:
        hints = _REASONING_HINTS
    m = str(model or "").lower()
    return any(str(h).lower() in m for h in hints)


def _inject_no_think(messages: list[dict]) -> list[dict]:
    """사고 비활성 — 마지막 user 메시지에 '/no_think' 를 붙인다.

    데모스(demos_v1/gguf.py `_inject_no_think_for_qwen3`) 와 같은 방식.
    사고를 끄지 않으면 max_tokens 를 사고에 다 써버려 본문이 비어 온다.
    """
    out = [dict(m) for m in messages]
    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") == "user" and isinstance(out[i].get("content"), str):
            if "/no_think" not in out[i]["content"]:
                out[i]["content"] = out[i]["content"].rstrip() + "\n\n/no_think"
            return out
    return out


# ── JSON 강제 호출 ────────────────────────────────────────────────
# 사고 모델은 '/no_think' 를 무시하고 본문에 추론을 쓰다가 max_tokens 에 걸려
# JSON 을 못 끝낸다(1분 판단의 '판단' 이 문장 중간에 끊기던 원인). 부탁 대신
# 게이트웨이 기능으로 막는다. 이 키를 모르는 게이트웨이는 400 을 내므로
# 옵션을 한 단계씩 빼며 다시 부른다 — 400 은 즉답이라 사실상 공짜다.
_JSON_TIER: dict = {}


def _json_opts(model: str) -> list:
    full = {"response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False}}
    if "gpt-oss" in str(model).lower():
        full["reasoning_effort"] = "low"
    return [full, {"response_format": full["response_format"]}, None]


def chat_json(messages: list[dict], cfg: dict | None = None,
              max_tokens: int | None = None, prefill: str | None = None):
    """JSON 응답 전용 호출 → (text, error).

    게이트웨이가 response_format 을 받으면 프리필은 필요 없다(오히려 GLM·
    gpt-oss 에서는 프리필 뒤에 코드펜스를 다시 열거나 프리필 안에 영어 추론을
    써서 JSON 을 깨뜨렸다). 옵션이 안 먹는 게이트웨이에서만 프리필로 물러난다.
    """
    cfg = cfg or load_config()
    model = (cfg.get("llm") or {}).get("model", "")
    tiers = _json_opts(model)
    i = min(int(_JSON_TIER.get(model, 0)), len(tiers) - 1)
    while True:
        extra = tiers[i]
        txt, err = chat(messages, cfg, max_tokens=max_tokens,
                        prefill=(prefill if extra is None else None), extra=extra)
        if err and extra is not None and ("HTTP 400" in str(err) or "HTTP 422" in str(err)):
            i += 1                       # 옵션을 모르는 게이트웨이 — 한 단계 빼고 재시도
            continue
        if not err or not ("HTTP 400" in str(err) or "HTTP 422" in str(err)):
            _JSON_TIER[model] = i        # 모델 자체가 400 인 경우는 학습하지 않는다
        return txt, err


_THINK_RE = re.compile(r"<think>[\s\S]*?</think>|<think>[\s\S]*$", re.I)


def _strip_think(text: str) -> str:
    """<think>…</think> 사고 블록 제거. 닫히지 않은 채 잘린 경우도 버린다."""
    return _THINK_RE.sub("", str(text or "")).strip()


# ────────────────────────── 관제용 프롬프트 ──────────────────────────
def judge_case(case: dict, cfg: dict | None = None):
    """케이스 1건에 대한 LLM 판단 → {"판단","확신도","근거","조치"}."""
    cfg = cfg or load_config()
    ev = case.get("evidence", {})
    user = f"""아래는 실시간으로 감지된 반송 정체 케이스다. 스킬 규칙에 따라 판단하라.

- 설비/위치: {case.get('area')} / {case.get('location')}
- 최고 점수: {case.get('peak_score'):.0f}점 ({case.get('emoji')} {case.get('level')})
- 감지 시각: {case.get('peak_at', '')[11:16]}
- 이상감지 구간(HID): {', '.join(ev.get('zones', [])) or '없음'}
- 이상감지 항목(raw 컬럼): {' / '.join(ev.get('items', [])) or '없음'}
- 발동 사유: {ev.get('reason') or '없음'}
- 전이 영역: {', '.join(ev.get('affected', [])) or '없음'}
- 유입 신호: {ev.get('flow') or '없음'}
- 운영자 용량변경: {ev.get('maxcapa') or '없음'}

다음 JSON 만 출력하라 (설명·코드펜스 금지):
{{"실제이상":"예|아니오","판단":"200자 이내 한국어 요약 원인 진단","확신도":0~100 정수,"근거":["근거1","근거2"],"조치":["조치1","조치2"]}}

'실제이상' = 지금 대응이 필요한 진짜 이상이면 "예", 일시적 변동이라 넘어가도 되면 "아니오".
규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
데이터에 없는 호기×방향을 지어내지 마라."""

    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}], cfg, max_tokens=900,
                    json_prefill=True)
    if err:
        return None, err
    res = _parse_json(txt)
    if not res:
        return None, f"JSON 파싱 실패: {str(txt)[:150]}"
    res["실제이상"] = _yes_no(res.get("실제이상"))
    return res, None


# ────────────────── 1분 단위 스냅샷 판단 (정탐률 채점용) ──────────────────
def judge_snapshot(row: dict, score: float, grade: dict, area: str,
                   light: bool, cfg: dict | None = None):
    """수집한 그 1분에 대한 판단 → {"실제이상","판단","확신도","근거","조치"}.

    light=True(정상 구간)면 짧게 묻는다. 하루 1440번이라 정상 구간까지
    근거·조치를 다 받으면 낭비고, 채점에 필요한 건 '실제이상' 한 칸이다.
    """
    cfg = cfg or load_config()
    from sentinel import hid_zones, summarize_reason

    reason = (row.get("reason") or "").strip()
    bd = (row.get("BOTTLENECK_downward_anomaly_cols") or "").strip()
    bu = (row.get("BOTTLENECK_upward_anomaly_cols") or "").strip()
    qd = (row.get("QUEUE_downward_anomaly_cols") or "").strip()
    qu = (row.get("QUEUE_upward_anomaly_cols") or "").strip()
    zones = hid_zones(" ".join(x for x in (bd, bu) if x))
    items = " ".join(x for x in (qd, qu) if x).split()

    # ★ 등급 기준을 규칙으로 못박는다. 이게 없으면 29점(정상)인데도 '예' 가 나온다.
    from sentinel import grade_cuts
    floor = grade_cuts(cfg)[0]      # ★시스템별 컷 (정책 탭에서 FAB 마다 다르다)
    rule = (f'★판정 규칙(반드시 따른다): 스코어 {floor:.0f}점 미만은 정상이므로 '
            f'"실제이상"은 "아니오" 다. {floor:.0f}점 이상일 때만 "예" 를 쓸 수 있다.\n'
            f'  현재 스코어 {score:.0f}점 → '
            + ('판단해서 예/아니오 중 하나.' if score >= floor
               else f'{floor:.0f}점 미만이므로 반드시 "아니오".'))

    head = f"""M16 BR 구간 {(row.get('datetime') or '')[11:16]} 시점 데이터다.

- 점수: {score:.0f}점 ({grade.get('emoji','')} {grade.get('level','')}) / 최고 구역: {area}
- AMOS HID 구역: {', '.join(zones) or '없음'}
- AMOS QUEUE 지표: {' / '.join(items) or '없음'}
- 발동 사유: {summarize_reason(reason, area) or '없음'}"""

    # ★ALL 과 FAB 이 엇갈릴 때 그게 무슨 뜻인지 **계산해서** 붙인다.
    #   ALL 배점엔 흐름(30점)이 있고 FAB 배점엔 RA/RB/RC/RD(45점)가 있어,
    #   한쪽만 올라가는 일이 구조적으로 생긴다. 모델이 알 수 없는 구조라
    #   프롬프트로 알려 주지 않으면 "ALL 이 낮으니 정상" 으로 답한다.
    div = None
    try:
        import fab_score
        div = fab_score.divergence(row, cfg)
    except Exception:                                   # noqa: BLE001
        div = None                                      # 없으면 없는 대로 간다
    if div:
        head += ("\n\n★ALL 과 FAB 이 엇갈린다 ({}) — 반드시 반영해서 판단하라.\n"
                 "{}\n"
                 "  FAB 점수: {}").format(
            div["kind"], div["text"],
            " · ".join("{} {}점(경계 {})".format(x["fab"], x["score"], x["cut"])
                       for x in (div["hot"] + div["quiet"])) or "없음")

    if light:
        user = head + "\n\n" + rule + """

지금 대응이 필요한 진짜 이상인가?

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{' 여야 하고 JSON 만 출력한다.
★'판단'은 **완결된 문장**으로 쓴다. 160자 안에서 끝내라 — 중간에 끊기면 안 된다.
  빈 말("정상입니다") 대신 근거가 되는 수치·구역을 넣어라.
  예) "M16HUB 반송시간 2.7분으로 기준 이하, 저장율도 평시 수준이라 정상 운영입니다."
{"실제이상":"예|아니오","판단":"근거 수치를 포함한 완결 문장 (160자 이내)","확신도":0~100 정수}"""
        max_tok = int((cfg.get("llm", {}).get("per_minute") or {}).get("light_max_tokens", 400))
    else:
        user = head + f"""
- 전이 경로: {(row.get('propagation_chain') or '').strip() or '없음'}
- 운영자 용량변경: {(row.get('maxcapa_change') or '').strip() or '없음'}

{rule}

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{{' 여야 하고 JSON 만 출력한다.
★'판단'은 **완결된 문장**으로 쓴다. 160자 안에서 끝내라 — 중간에 끊기면 안 된다.
  '어느 구역에서 / 무엇이 / 어떤 수치라서' 가 다 들어가야 한다. 형용사로 늘리지 마라.
  예) "M16HUB STB 저장율 99.4%로 포화되어 리프터 반출이 막혔고, 반송시간이 6.3분
      (기준 9분)까지 올라 정체가 시작됐습니다."
근거·조치는 각 항목 80자 이내로 짧게.
{{"실제이상":"예|아니오","판단":"200자 이내 한국어 요약 원인 진단","확신도":0~100 정수,"근거":["근거1","근거2"],"조치":["조치1","조치2"]}}

'실제이상' = 지금 대응이 필요한 진짜 이상이면 "예", 일시적 변동이면 "아니오".
규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
데이터에 없는 호기×방향을 지어내지 마라."""
        max_tok = int((cfg.get("llm", {}).get("per_minute") or {}).get("full_max_tokens", 900))

    pm = cfg.get("llm", {}).get("per_minute") or {}
    # ★chat_json: response_format 으로 JSON 을 강제하고 사고 템플릿을 끈다.
    #   게이트웨이가 그걸 모르면 예전처럼 프리필로 물러난다.
    pre = ((cfg.get("llm", {}).get("json_prefill_text") or '{"실제이상": "')
           if pm.get("json_prefill", True) else None)
    txt, err = chat_json([{"role": "system", "content": build_system_prompt(cfg)},
                          {"role": "user", "content": user}], cfg,
                         max_tokens=max_tok, prefill=pre)
    if err:
        return None, err
    res = _parse_json(txt)
    if not res:
        return None, f"JSON 파싱 실패: {str(txt)[:150]}"
    res["실제이상"] = _yes_no(res.get("실제이상"))
    # ★ 실제이상이 없으면 채점도 못 하고 쓸모가 없다. 산문을 '판단' 으로 저장하지 말고
    #   오류로 남겨 원인이 보이게 한다 (모델이 JSON 대신 서술을 쓴 경우).
    if not res["실제이상"]:
        return None, f"실제이상(예/아니오) 없음 — 모델이 JSON 형식을 안 지켰습니다: {str(txt)[:150]}"
    # ★ 등급 기준은 코드에서도 강제한다. 프롬프트만 믿으면 29점인데 '예' 가 나온다.
    #   임계 미만은 정의상 정상이므로 '아니오' 로 확정하고, 무엇을 고쳤는지 남긴다.
    if score < floor and res["실제이상"] == "예":
        res["실제이상"] = "아니오"
        j = (res.get("판단") or "").strip()
        res["판단"] = (f"[{floor:.0f}점 미만 정상 — LLM 은 이상으로 봤음] " + j) if j else \
            f"스코어 {score:.0f}점으로 {floor:.0f}점 미만 정상 (LLM 은 이상으로 봤으나 규칙상 아니오)"
    return res, None


# 부정은 어디에 있어도 먼저 잡는다 ('이상없음' 이 '이상' 으로 읽혀 예가 되면 안 된다)
_NEG = ("없", "아니", "아뇨", "불필요", "불요", "정상", "no", "false")
_POS = ("예", "네", "yes", "y", "true", "1", "이상", "필요", "위험", "맞", "있")


def _yes_no(v) -> str:
    """모델이 '예.' / 'YES' / '이상 있음' / '이상없음' 처럼 답해도 예/아니오로 정규화.

    여기서 못 읽으면 그 행은 채점 대상에서 빠져 영구히 '대기' 로 남으므로
    최대한 관대하게 읽는다. 그래도 못 읽으면 빈 값 → 사후검증이 '판정불가'로 못박는다.
    """
    s = str(v or "").strip().lower().replace(" ", "")
    if not s:
        return ""
    if s in ("0", "1"):                 # 숫자로 답하는 경우
        return "아니오" if s == "0" else "예"
    if any(t in s for t in _NEG):
        return "아니오"
    if any(s.startswith(t) for t in _POS):
        return "예"
    return ""


def make_report(cases: list[dict], span: str, cfg: dict | None = None):
    """구간 리포트 → 마크다운 본문."""
    cfg = cfg or load_config()
    if not cases:
        lines = "이 구간에 임계 점수 이상 사건이 없었다 (정상 운영)."
    else:
        lines = "\n".join(
            f"- {c.get('peak_at','')[11:16]} | {c.get('area')} | {c.get('peak_score'):.0f}점 "
            f"{c.get('emoji')} {c.get('level')} | 구간 {', '.join(c.get('evidence',{}).get('zones',[])) or '-'} "
            f"| 항목 {' / '.join(c.get('evidence',{}).get('items',[])) or '-'} "
            f"| 사유 {c.get('evidence',{}).get('reason') or '-'}"
            for c in cases)

    user = f"""아래는 {span} 구간에 감지된 반송 정체 사건 목록이다.

{lines}

스킬 규칙에 따라 관제 리포트를 마크다운으로 작성하라. 구성:

## 주요 발견
(사건별 원인을 인과로 — Storage FULL → 리프터 정체 → Queue 밀림 → 반송지연 연쇄로 짚는다. 3~5줄)

## 다음 구간 예측 · 선제 조치 제안
(이 추세가 이어질 때 다음 구간에 무엇이 우려되는지 + 지금 할 선제 조치. 3~5줄)

규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
표를 만들지 말고 문장으로. 데이터에 없는 호기×방향을 지어내지 마라.
★한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
★'## 주요 발견' 으로 바로 시작한다. 인사말·서론·설명 없이 마크다운 본문만."""

    # ★ 리포트도 같은 문제를 겪는다 — 이 모델은 마크다운 앞에 'Thinking Process: …'
    #   산문을 붙인다. 첫 헤딩을 프리필해 그 뒤부터 쓰게 만들고, 그래도 앞에 뭐가
    #   붙으면 첫 '## ' 앞을 잘라낸다.
    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}], cfg,
                    max_tokens=int(cfg.get("llm", {}).get("report_max_tokens", 1800)),
                    prefill="## 주요 발견\n")
    if err:
        return None, err
    return _strip_preamble(txt), None


def make_day_report(mat: dict, cfg: dict | None = None):
    """하루 사건 리포트 — 데모스 개인 에이전트 '사건발생 보고서' 와 같은 5섹션.

    형식은 페르소나_통합.txt [B] 사건단위 에 이미 정의돼 있고 시스템 프롬프트로
    들어간다. 여기서는 그 스킬이 요구하는 **③ 사건목록 · ④ AMOS 표만 근거로** 준다.
    """
    cfg = cfg or load_config()
    pk = mat.get("peak") or {}

    def table(rows, cols):
        if not rows:
            return "(없음)"
        out = ["| " + " | ".join(cols) + " |",
               "|" + "|".join(["---"] * len(cols)) + "|"]
        for r in rows:
            out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
        return "\n".join(out)

    inc_tbl = table(mat.get("incidents") or [],
                    ["번호", "시각", "구간", "지속분", "최고등급", "최고점수", "시작영역"])
    amos_tbl = table(mat.get("amos") or [],
                     ["번호", "이상감지 시간", "이상감지 구간", "심각도", "이상감지 항목"])

    reasons = "\n".join(
        f"- {r['번호']}번 {r['시각']} {r['시작영역']} {r['최고점수']}점 발동사유: "
        + (r.get("발동사유") or "없음")
        for r in (mat.get("incidents") or [])) or "(사건 없음)"

    lv = ", ".join(f"{k} {v}분" for k, v in (mat.get("by_level") or {}).items()) or "없음"

    user = f"""[B] 사건단위 = 이벤트 발생 확인건 보고서를 작성하라.

date = {mat['day']}  ({mat['date_ko']})

■ 하루 통계
- 수집 {mat['minutes']}분 · 점수 {_fl(mat)} 이상(정체) {mat['risk_minutes']}분
- 등급 분포: {lv}
- 하루 최고: {(pk.get('time') or '-')} {pk.get('emoji','')} {pk.get('level','정상')} {pk.get('score',0)}점 ({pk.get('area','-')})
- 정체 집중: {mat.get('busy','없음')}

■ ③ 이벤트목록 (점수 {_fl(mat)}+ · 간격 60분 · 시각=최고점)
{inc_tbl}

■ ④ AMOS 이상감지
{amos_tbl}

■ 사건별 발동사유 (원문 — 4번 상세 분석의 근거)
{reasons}

★③ 사건목록·④ AMOS 표만 근거로 쓴다. 분단위 데이터를 직접 나열하지 마라.
★섹션 번호·제목은 페르소나에 정의된 1~5 를 그대로 쓴다 (시스템이 제목을 인식한다).
★④ 표를 2번 섹션에 그대로 옮기고 마지막에 빈 '실제 발생여부' 컬럼을 붙인다.
  구간·항목의 <br> 은 지우지 마라.
★4번은 사건마다 아래 골격 그대로 (굵게·불릿 유지):
**이벤트 #N (HH:MM 발생)**
- **현상**: (어디서 시작·몇 분 지속·등급/점수)
- **원인**: (어느 지표가 어떻게 움직였나 — 실측값 기준)
- **인과**: (그 원인이 어떤 순서로 정체를 만들었나)
- **영향**: (반송/대기에 준 영향 + 시사점)
★5번은 아래 두 불릿만:
- **공통 근본 원인**: (사건들의 공통 원인 1가지)
- **구체 조치**: (지금 할 조치)
★한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
★'# 📅 ' 로 바로 시작한다. 인사말·서론 없이 마크다운 본문만."""

    llm = cfg.get("llm", {}) or {}
    mx = int(llm.get("day_report_max_tokens", 4000))
    sysmsg = {"role": "system", "content": build_system_prompt(cfg)}
    txt, err = chat([sysmsg, {"role": "user", "content": user}], cfg, max_tokens=mx,
                    prefill=f"# 📅 {mat['date_ko']} M16 BR 반송 이벤트 발생 확인건\n\n")
    if err:
        return None, err
    md = _strip_preamble(txt, heading="# ")
    md = _strip_reasoning(md)              # 제목~첫 섹션 사이 추론/서론 제거
    # ★영문·추론으로 오염된 섹션만 통계 기반 한국어로 대체 (LLM 재호출 안 함 — 추론 누출 방지)
    md = _sanitize_sections(md, mat)
    # ★모델이 빼먹은 섹션(주로 마지막 5. 에이전트 제안)을 채운다
    md = _ensure_day_sections(md, mat)
    return md, None


# 이 reasoning 모델이 산문으로 흘리는 추론 마커 — 한 줄이라도 있으면 그 섹션은 통계로 대체
_REASON_MARKERS = (
    "사용자의 요청", "사용자 요청", "사용자 지시", "주요 제약", "규칙 확인",
    "섹션별 규칙", "용어 표준", "결정:", "해석:", "페르소나 규칙", "충돌 발생",
    "Thinking", "Analyze the Request", "출력 형식", "라고 함", "라는 뜻",
    "하는 것이 맞음", "포함해야 함", "출력해야 함",
)


def _strip_reasoning(md: str) -> str:
    """제목(# ) 과 첫 섹션(## ) 사이에 낀 서론·추론을 제거한다.

    이 모델은 프리필한 제목 뒤에 곧바로 '사용자의 요청은…' 같은 추론을 쏟아낸다.
    정상 보고서라면 제목과 '## 1.' 사이는 비어 있어야 하므로 그 사이를 지운다.
    """
    import re as _re
    lines = str(md or "").splitlines()
    h1 = next((i for i, l in enumerate(lines) if _re.match(r"^#\s+\S", l)), None)
    s2 = next((i for i, l in enumerate(lines) if _re.match(r"^##\s+\S", l)), None)
    if h1 is not None and s2 is not None and s2 > h1 + 1:
        lines = lines[:h1 + 1] + [""] + lines[s2:]
    return "\n".join(lines)


def _sanitize_sections(md: str, mat: dict) -> str:
    """섹션별로 한글 여부·추론 마커를 보고, 오염된 섹션만 통계 문장으로 갈아끼운다.
    LLM 을 다시 부르지 않는다 — 재호출이 추론을 다시 흘리던 문제를 없앤다. 2번 표는 손대지 않는다."""
    def dirty(text: str) -> bool:
        if any(m in text for m in _REASON_MARKERS):
            return True
        return not _is_korean(text)

    out, fixed = [], []
    for head, body in _split_sections(md):
        h = head.lstrip("# ").strip()
        # 2번 AMOS 표·3번 안내문은 표/고정문구라 건드리지 않는다
        if not body or "2." in h or "3." in h or not dirty(head + "\n" + body):
            out.append((head, body))
            continue
        out.append((head, _ko_section_fallback(head, mat)))
        fixed.append(h[:14] or "본문")
    if fixed:
        print(f"  📝 [리포트] 오염 섹션 한국어 통계로 대체 — {', '.join(fixed)}")
    return "\n".join(((h + "\n\n" if h else "") + (b + "\n" if b else "")) for h, b in out).strip()


_DAY_SECTIONS = (
    (1, "## 1. 한 줄 총평:등급(60~70 🟠 경계/ 71~84 🔴 위험 / 85~100 ⛔ 초위험)"),
    (2, "## 2. AMOS 이상 감지 내역"),
    (3, "## 3. 실제 이상 발생내역"),
    (4, "## 4. 위험 이벤트 상세 분석 (도메인 세분화)"),
    (5, "## 5. 에이전트 제안"),
)


def _ensure_day_sections(md: str, mat: dict) -> str:
    """1~5 섹션이 다 있는지 확인하고, 없는 섹션을 통계 내용으로 채워 넣는다.

    이 모델은 토큰이 길어지면 마지막 '5. 에이전트 제안' 을 그냥 안 쓰고 끝낸다.
    보고서 형식(개인 에이전트와 동일한 5섹션)은 어떤 경우에도 지켜져야 한다.
    """
    import re as _re
    t = str(md or "").rstrip()
    heads = [ln for ln in t.splitlines() if _re.match(r"^#{1,3}\s+\S", ln)]
    added = []
    for num, head in _DAY_SECTIONS:
        if any(_re.match(rf"^#{{1,3}}\s*{num}\s*[.)]", h.lstrip("# ").strip()) or
               _re.match(rf"^{num}\s*[.)]", h.lstrip("# ").strip()) for h in heads):
            continue
        body = _amos_table_md(mat) if num == 2 else (
            "2번 표의 실제 발생여부를 체크하면 아래에 행이 자동 생성됩니다."
            if num == 3 else _ko_section_fallback(head, mat))
        t += f"\n\n{head}\n\n{body}"
        added.append(str(num))
    if added:
        print(f"  📝 [리포트] 빠진 섹션 보완 — {', '.join(added)}번")
    return t


def _detail_md(mat: dict) -> str:
    """4번 상세 분석 — 개인 에이전트 보고서와 같은 현상/원인/인과/영향 골격 (통계만으로)."""
    incs = mat.get("incidents") or []
    if not incs:
        return "해당 없음"
    try:
        from sentinel import summarize_reason
    except Exception:
        summarize_reason = None
    out = []
    for r in incs:
        # 룰 코드는 노출하지 않는다 (스킬 규칙) — 한글 발동사유로 바꿔 쓴다
        raw = str(r.get("발동사유") or "")
        cause = (summarize_reason(raw, r.get("시작영역", "")) if summarize_reason else "") \
            or "발동 지표 정보 없음"
        out.append(
            f"**이벤트 #{r['번호']} ({r['시각']} 발생)**\n"
            f"- **현상**: {r['시작영역']} 에서 시작되어 {r['지속분']}분 지속된 "
            f"{r['최고등급']} ({r['최고점수']}점) 이벤트입니다 (구간 {r['구간']}).\n"
            f"- **원인**: {cause}\n"
            f"- **인과**: 위 지표가 함께 움직이며 허브 반송 대기가 누적된 구간입니다.\n"
            f"- **영향**: {r['지속분']}분간 반송 지연이 이어졌습니다.")
    return "\n\n".join(out)


def _fl(mat: dict) -> int:
    """리포트 문구에 쓸 이벤트 판정 임계.

    ★'점수 50 이상' 처럼 박아 두면 안 된다 — 경계 하한을 60 으로 올린 뒤에도
      리포트 본문이 계속 50 이라고 말했다. day_material 이 넣어 준 값을 쓰고,
      없으면(옛 캐시) 그때 config 에서 읽는다.
    """
    v = mat.get("floor")
    if v:
        return int(v)
    try:
        from sentinel import grade_cuts
        return grade_cuts()[0]
    except Exception:
        return 60

def _advice_md(mat: dict) -> str:
    """5번 에이전트 제안 — 공통 근본 원인 + 구체 조치 두 불릿 (통계만으로)."""
    incs = mat.get("incidents") or []
    if not incs:
        return (f"- **공통 근본 원인**: 없음 (금일 점수 {_fl(mat)} 이상 이벤트 없음)."
                "\n- **구체 조치**: 현행 감시 유지.")
    return (f"- **공통 근본 원인**: 정체가 {mat.get('busy','–')} 에 집중돼 "
            "허브 저장·리프터 처리 여력이 부족했던 구간입니다.\n"
            "- **구체 조치**: 해당 시간대 상류 유입 속도 조절과 허브 저장 공간 확보를 "
            "점검하고, 같은 구간 재발 여부를 다음 주기에 확인합니다.")


def _amos_table_md(mat: dict) -> str:
    """2번 섹션의 AMOS 표 (마지막에 빈 '실제 발생여부' 컬럼 — 시스템이 체크박스로 바꾼다)."""
    amos = mat.get("amos") or []
    if not amos:
        return "금일 AMOS 이상감지 내역 없음"
    L = ["| 번호 | 이상감지 시간 | 이상감지 구간 | 심각도 | 이상감지 항목 | 실제 발생여부 |",
         "|---|---|---|---|---|---|"]
    for r in amos:
        L.append(f"| {r.get('번호','')} | {r.get('이상감지 시간','')} | "
                 f"{r.get('이상감지 구간','')} | {r.get('심각도','')} | "
                 f"{r.get('이상감지 항목','')} |  |")
    return "\n".join(L)


def _split_sections(md: str):
    """마크다운을 (헤딩줄, 본문) 목록으로 쪼갠다. 헤딩 앞 서두는 헤딩='' 로 들어간다."""
    import re as _re
    secs, head, buf = [], "", []
    for ln in str(md or "").splitlines():
        if _re.match(r"^#{1,3}\s+\S", ln):
            secs.append((head, "\n".join(buf).strip()))
            head, buf = ln, []
        else:
            buf.append(ln)
    secs.append((head, "\n".join(buf).strip()))
    return [s for s in secs if s[0] or s[1]]


def _ko_section_fallback(head: str, mat: dict) -> str:
    """재작성까지 실패한 섹션을 통계 기반 한국어 문장으로 채운다."""
    h = str(head or "")
    incs = mat.get("incidents") or []
    pk = mat.get("peak") or {}
    if "4." in h or "상세" in h:
        return _detail_md(mat)
    if "5." in h or "제안" in h:
        return _advice_md(mat)
    if "1." in h or "총평" in h:
        if not incs:
            return f"금일 점수 {_fl(mat)} 이상 이벤트 없음 (최고 {pk.get('score',0)}점, 정상 운영)."
        return (f"금일 총 {len(incs)}건 · 최고 {pk.get('emoji','')} {pk.get('level','')} "
                f"{pk.get('score',0)}점 ({pk.get('time','')} {pk.get('area','')}). "
                f"정체 {mat.get('risk_minutes',0)}분.")
    return "(한국어 재작성 실패 — 통계 요약만)"


def _is_korean(t: str, min_ratio: float = 0.25) -> bool:
    """한글 비율이 일정 수준 이상인가 — 영문 답변을 걸러낸다."""
    s = str(t or "")
    han = sum(1 for ch in s if "가" <= ch <= "힣")
    latin = sum(1 for ch in s if ("a" <= ch <= "z") or ("A" <= ch <= "Z"))
    if han + latin < 20:
        return True                                      # 표·숫자만 있는 짧은 줄은 통과
    return han / float(han + latin) >= min_ratio


def assemble_day_report(mat: dict, blocks: dict | None = None) -> str:
    """★5섹션 골격을 코드가 만든다 — 데모스 개인 에이전트 '사건발생 보고서' 와 동일.

    제목 · 2번 AMOS 표(+빈 '실제 발생여부' 컬럼) · 3번 안내문은 결정적으로 찍고,
    LLM 은 1번 총평 · 4번 상세분석 · 5번 제안 문장만 채운다. 이렇게 하면 모델이
    영문으로 쓰거나 표를 빼먹어도 보고서 형식이 절대 흐트러지지 않는다.
    """
    b = blocks or {}
    pk = mat.get("peak") or {}
    incs, amos = mat.get("incidents") or [], mat.get("amos") or []

    if b.get("총평"):
        head = b["총평"]
    elif incs:
        head = (f"금일 총 {len(incs)}건 · 최고 {pk.get('emoji','')} {pk.get('level','')} "
                f"{pk.get('score',0)}점 ({pk.get('time','')} {pk.get('area','')}). "
                f"정체 {mat.get('risk_minutes',0)}분.")
    else:
        head = f"금일 점수 {_fl(mat)} 이상 이벤트 없음 (최고 {pk.get('score',0)}점, 정상 운영)."

    L = [f"# 📅 {mat['date_ko']} M16 BR 반송 이벤트 발생 확인건", "",
         "## 1. 한 줄 총평:등급(60~70 🟠 경계/ 71~84 🔴 위험 / 85~100 ⛔ 초위험)", "",
         head, "",
         "## 2. AMOS 이상 감지 내역", ""]
    L.append(_amos_table_md(mat))

    L += ["", "## 3. 실제 이상 발생내역", "",
          "2번 표의 실제 발생여부를 체크하면 아래에 행이 자동 생성됩니다.", "",
          "## 4. 위험 이벤트 상세 분석 (도메인 세분화)", ""]
    L.append(b.get("상세") or _detail_md(mat))
    L += ["", "## 5. 에이전트 제안", "", b.get("제안") or _advice_md(mat)]
    return scrub("\n".join(L))


def _strip_preamble(md: str, heading: str = "## ") -> str:
    """마크다운 앞에 붙은 서술(추론 등)을 잘라낸다 — 첫 헤딩부터가 본문."""
    t = str(md or "")
    i = t.find(heading)
    return (t[i:] if i > 0 else t).strip()


def _json_candidates(t: str):
    """텍스트에서 균형 잡힌 {...} 덩어리를 모두 뽑는다 (뒤에 붙은 JSON 도 잡히게)."""
    out, depth, start, instr, esc = [], 0, -1, False, False
    for i, ch in enumerate(t):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(t[start:i + 1])
                start = -1
            elif depth < 0:
                depth = 0
    return out


_KEYS = ("실제이상", "판단", "확신도")


def _parse_json(text: str) -> dict:
    """코드펜스·평문 추론이 섞인 응답에서 JSON 추출.

    이 모델은 'Thinking Process: ...' 처럼 평문으로 추론을 먼저 쓰고 그 뒤에 JSON 을
    붙이는 경우가 있다. 그래서 앞에서부터 통째로 파싱하지 말고 **균형 잡힌 {...}
    후보를 뒤에서부터** 시도한다.
    """
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        d = json.loads(t)
        if isinstance(d, dict):
            return d
    except Exception:
        pass

    cands = _json_candidates(t)
    for c in reversed(cands):                     # 뒤에 있는 게 최종 답일 가능성이 높다
        try:
            d = json.loads(c)
        except Exception:
            continue
        if isinstance(d, dict) and any(k in d for k in _KEYS):
            return d
    for c in reversed(cands):                     # 키가 없더라도 dict 면 받는다
        try:
            d = json.loads(c)
            if isinstance(d, dict):
                return d
        except Exception:
            continue

    # JSON 이 아예 없거나 잘린 경우 — 본문에서 필요한 값만 건져낸다
    got = _salvage(t)
    return got or ({"판단": t[:300]} if t else {})


# 'JSON 이 없어도' 실제이상만은 건져낸다 (채점이 되려면 이 한 칸이 필요하다)
_RE_YES_NO = re.compile(r'"?실제이상"?\s*[:=]\s*"?\s*(예|아니오|아니요|yes|no)', re.I)
_RE_CONF = re.compile(r'"?확신도"?\s*[:=]\s*"?\s*(\d{1,3})')
# 닫는 따옴표가 없어도(잘린 응답) 판단을 건진다
_RE_JUDGE = re.compile(r'"?판단"?\s*[:=]\s*"([^"]{2,400})(?:"|$)')


def _salvage(t: str) -> dict:
    """잘린 응답에서 실제이상·확신도·판단을 정규식으로 건져낸다."""
    out = {}
    m = _RE_YES_NO.search(t)
    if m:
        out["실제이상"] = m.group(1)
    m = _RE_CONF.search(t)
    if m:
        try:
            out["확신도"] = int(m.group(1))
        except ValueError:
            pass
    m = _RE_JUDGE.search(t)
    if m:
        out["판단"] = m.group(1).strip()
    return out


if __name__ == "__main__":
    cfg = load_config()
    sk = load_skills(cfg)
    print(f"스킬 디렉터리: {sk['dir']}")
    for n, b in sk["skills"].items():
        print(f"  ✅ {n}  ({len(b):,}자)")
    print(f"  ✅ 페르소나 ({len(sk['persona']):,}자)" if sk["persona"] else "  ❌ 페르소나 없음")
    if sk["missing"]:
        print(f"  ❌ 누락: {sk['missing']}")
    print(f"시스템 프롬프트 총 {len(build_system_prompt(cfg)):,}자")
    print(f"모델: {cfg['llm']['model']} @ {cfg['llm']['url']}")
    _kf = cfg["llm"].get("api_key_file", "token.txt")
    print(f"API 키: {'있음' if _api_key(cfg) else f'없음 — real_time_amhs/{_kf} 에 넣으세요'}")
    print("금지어 스크럽 테스트:", scrub("3F 리프터 역방향 카운트 (LFT_REVERSALCNT) 증가"))

    # ── 실제 호출 점검 (python llm_client.py --test) ──
    import sys
    if "--test" in sys.argv:
        print()
        print("=" * 62)
        print("  LLM 호출 점검 — 1분 판단과 같은 경로로 한 번 부른다")
        print(f"  사고 끄기(no_think): {cfg['llm'].get('no_think', True)}")
        print("=" * 62)
        fake = {"datetime": "2026-07-29 08:11", "unified_risk_score": "88",
                "hot_area": "M16HUB", "reason": "발동: M16HUB[R-A_sus, R-C, R-D]",
                "BOTTLENECK_downward_anomaly_cols": "HID_35_FROM_SUM_A",
                "QUEUE_downward_anomaly_cols": "M16HUB.QUE.TIME.AVGTOTALTIME1MIN"}
        for light in (True, False):
            tag = "간단(정상 구간)" if light else "상세(경계 이상)"
            res, err = judge_snapshot(fake, 88.0,
                                      {"level": "초위험", "emoji": "⛔"}, "M16HUB", light, cfg)
            if err:
                print(f"  ❌ {tag}: {err}")
            else:
                print(f"  ✅ {tag}: 실제이상={res.get('실제이상')!r} "
                      f"확신도={res.get('확신도')} 판단={str(res.get('판단'))[:60]!r}")
        print()
        print("  실제이상 이 예/아니오 로 나오면 정상. 비어 있거나 오류가 나오면")
        print("  그 메시지를 그대로 알려주세요.")
