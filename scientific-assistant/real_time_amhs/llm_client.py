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

# 스킬 규칙과 동일한 금지어 — LLM이 어겨도 여기서 결정적으로 제거
_FORBIDDEN = [
    ("리프터 역방향 카운트", "리프터막힘"),
    ("리프터 역방향", "리프터막힘"),
    ("역방향 카운트", "정체"),
    ("역방향", "정체"),
    ("역증가", "정체"),
    ("역류", "밀림"),
    ("광역정체", "정체"),
]

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
    """스킬 금지어 결정적 제거 (raw 컬럼명은 ASCII 라 훼손되지 않음)."""
    import re
    for a, b in _FORBIDDEN:
        text = text.replace(a, b)
    text = re.sub(r"\s*카운트\s*", " ", text)
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
         json_prefill: bool = False):
    """OpenAI 호환 호출 → (text, None) 또는 (None, error).

    json_prefill=True 면 assistant 턴을 '{' 로 미리 채워 JSON 만 나오게 유도한다
    (사고 모델이 평문 추론을 먼저 쓰는 것을 막는다).
    """
    cfg = cfg or load_config()
    lc = cfg.get("llm", {})
    if not lc.get("enabled", True):
        return None, "LLM 비활성 (config.llm.enabled=false)"

    model = lc.get("model", "gaia-Qwen3.5-397B-A17B")
    msgs = messages
    # ★ Qwen3 계열은 사고(reasoning) 모델이다. 그냥 부르면 사고 토큰만 쓰다
    #   max_tokens 에 걸려 본문이 빈 응답으로 온다. 데모스와 같은 방식으로 사고를 끈다.
    if lc.get("no_think", True) and "qwen3" in str(model).lower():
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
    # ★ JSON 프리필 — assistant 턴을 '{' 로 미리 채워 모델이 그 뒤를 이어 쓰게 만든다.
    #   이 게이트웨이는 /no_think 를 안 듣고 'Thinking Process: …' 평문 추론을 먼저 쓴다.
    #   프리필하면 추론을 건너뛰고 바로 JSON 을 뱉으므로 토큰·시간이 크게 줄고 파싱이 안정된다.
    if json_prefill:
        payload["messages"] = list(payload["messages"]) + [
            {"role": "assistant", "content": "{"}]
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
        if json_prefill and not txt.lstrip().startswith("{"):
            txt = "{" + txt            # 프리필한 '{' 는 응답에 안 실려 온다
        return scrub(txt), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _inject_no_think(messages: list[dict]) -> list[dict]:
    """Qwen3 계열 사고 비활성 — 마지막 user 메시지에 '/no_think' 를 붙인다.

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
{{"실제이상":"예|아니오","판단":"한국어 한 문장 원인 진단(200자 이내)","확신도":0~100 정수,"근거":["근거1","근거2"],"조치":["조치1","조치2"]}}

'실제이상' = 지금 대응이 필요한 진짜 이상이면 "예", 일시적 변동이라 넘어가도 되면 "아니오".
규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
데이터에 없는 호기×방향을 지어내지 마라."""

    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}], cfg, max_tokens=800)
    if err:
        return None, err
    return _parse_json(txt), None


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

    head = f"""M16 BR 구간 {(row.get('datetime') or '')[11:16]} 시점 데이터다.

- 점수: {score:.0f}점 ({grade.get('emoji','')} {grade.get('level','')}) / 최고 구역: {area}
- AMOS HID 구역: {', '.join(zones) or '없음'}
- AMOS QUEUE 지표: {' / '.join(items) or '없음'}
- 발동 사유: {summarize_reason(reason, area) or reason or '없음'}"""

    if light:
        user = head + """

지금 대응이 필요한 진짜 이상인가?

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{' 여야 하고 JSON 만 출력한다.
{"실제이상":"예|아니오","판단":"한국어 한 문장(200자 이내)","확신도":0~100 정수}"""
        max_tok = int((cfg.get("llm", {}).get("per_minute") or {}).get("light_max_tokens", 400))
    else:
        user = head + f"""
- 전이 경로: {(row.get('propagation_chain') or '').strip() or '없음'}
- 운영자 용량변경: {(row.get('maxcapa_change') or '').strip() or '없음'}

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{{' 여야 하고 JSON 만 출력한다.
{{"실제이상":"예|아니오","판단":"한국어 한 문장 원인 진단(200자 이내)","확신도":0~100 정수,"근거":["근거1(100자 이내)","근거2"],"조치":["조치1(100자 이내)","조치2"]}}

'실제이상' = 지금 대응이 필요한 진짜 이상이면 "예", 일시적 변동이면 "아니오".
규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
데이터에 없는 호기×방향을 지어내지 마라."""
        max_tok = int((cfg.get("llm", {}).get("per_minute") or {}).get("full_max_tokens", 900))

    pm = cfg.get("llm", {}).get("per_minute") or {}
    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}], cfg, max_tokens=max_tok,
                    json_prefill=pm.get("json_prefill", True))
    if err:
        return None, err
    res = _parse_json(txt)
    if not res:
        return None, f"JSON 파싱 실패: {str(txt)[:150]}"
    res["실제이상"] = _yes_no(res.get("실제이상"))
    if not res["실제이상"] and not (res.get("판단") or "").strip():
        return None, f"판단 내용 없음: {str(txt)[:150]}"
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
(사건별 원인을 인과로 — Storage FULL → 리프터막힘 → Queue 밀림 → 반송지연 연쇄로 짚는다. 3~5줄)

## 다음 구간 예측 · 선제 조치 제안
(이 추세가 이어질 때 다음 구간에 무엇이 우려되는지 + 지금 할 선제 조치. 3~5줄)

규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
표를 만들지 말고 문장으로. 데이터에 없는 호기×방향을 지어내지 마라."""

    return chat([{"role": "system", "content": build_system_prompt(cfg)},
                 {"role": "user", "content": user}], cfg, max_tokens=1500)


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
_RE_JUDGE = re.compile(r'"?판단"?\s*[:=]\s*"([^"]{2,200})"')


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
