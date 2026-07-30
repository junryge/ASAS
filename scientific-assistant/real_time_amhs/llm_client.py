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
         json_prefill: bool = False, prefill: str | None = None):
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
        if pre and not txt.lstrip().startswith(pre.strip()[:8]):
            txt = pre + txt            # 프리필은 응답에 안 실려 오므로 되붙인다
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
    floor = min((b["min"] for b in cfg.get("grade", {}).get("bands", [])), default=50)
    rule = (f'★판정 규칙(반드시 따른다): 스코어 {floor:.0f}점 미만은 정상이므로 '
            f'"실제이상"은 "아니오" 다. {floor:.0f}점 이상일 때만 "예" 를 쓸 수 있다.\n'
            f'  현재 스코어 {score:.0f}점 → '
            + ('판단해서 예/아니오 중 하나.' if score >= floor
               else f'{floor:.0f}점 미만이므로 반드시 "아니오".'))

    head = f"""M16 BR 구간 {(row.get('datetime') or '')[11:16]} 시점 데이터다.

- 점수: {score:.0f}점 ({grade.get('emoji','')} {grade.get('level','')}) / 최고 구역: {area}
- AMOS HID 구역: {', '.join(zones) or '없음'}
- AMOS QUEUE 지표: {' / '.join(items) or '없음'}
- 발동 사유: {summarize_reason(reason, area) or reason or '없음'}"""

    if light:
        user = head + "\n\n" + rule + """

지금 대응이 필요한 진짜 이상인가?

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{' 여야 하고 JSON 만 출력한다.
★'판단'은 200자 이내로 요약하라. 길게 늘려 쓰지 말고 핵심만 한 문장.
{"실제이상":"예|아니오","판단":"200자 이내 한국어 요약","확신도":0~100 정수}"""
        max_tok = int((cfg.get("llm", {}).get("per_minute") or {}).get("light_max_tokens", 400))
    else:
        user = head + f"""
- 전이 경로: {(row.get('propagation_chain') or '').strip() or '없음'}
- 운영자 용량변경: {(row.get('maxcapa_change') or '').strip() or '없음'}

{rule}

★출력 규칙: 한국어로만. 추론 과정을 쓰지 마라('Thinking Process' 금지).
첫 글자가 '{{' 여야 하고 JSON 만 출력한다.
★'판단'은 200자 이내로 요약하라. 길게 늘려 쓰지 말고 핵심 원인만 한 문장.
근거·조치는 각 항목 100자 이내로 짧게.
{{"실제이상":"예|아니오","판단":"200자 이내 한국어 요약 원인 진단","확신도":0~100 정수,"근거":["근거1","근거2"],"조치":["조치1","조치2"]}}

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
(사건별 원인을 인과로 — Storage FULL → 리프터막힘 → Queue 밀림 → 반송지연 연쇄로 짚는다. 3~5줄)

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
- 수집 {mat['minutes']}분 · 점수 50 이상(정체) {mat['risk_minutes']}분
- 등급 분포: {lv}
- 하루 최고: {(pk.get('time') or '-')} {pk.get('emoji','')} {pk.get('level','정상')} {pk.get('score',0)}점 ({pk.get('area','-')})
- 정체 집중: {mat.get('busy','없음')}

■ ③ 사건목록 (점수 50+ · 간격 60분 · 시각=최고점)
{inc_tbl}

■ ④ AMOS 이상감지
{amos_tbl}

■ 사건별 발동사유 (원문 — 4번 상세 분석의 근거)
{reasons}

★③ 사건목록·④ AMOS 표만 근거로 쓴다. 분단위 데이터를 직접 나열하지 마라.
★섹션 번호·제목은 페르소나에 정의된 1~5 를 그대로 쓴다 (시스템이 제목을 인식한다).
★④ 표를 2번 섹션에 그대로 옮기고 마지막에 빈 '실제 발생여부' 컬럼을 붙인다.
  구간·항목의 <br> 은 지우지 마라.
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
    # ★영문으로 나온 섹션만 한국어로 다시 받는다 (섹션 단위 재요청 → 실패 시 통계 문장)
    md = _koreanize_sections(md, mat, cfg, sysmsg, mx)
    # ★모델이 빼먹은 섹션(주로 마지막 5. 에이전트 제안)을 채운다
    md = _ensure_day_sections(md, mat)
    return md, None


_DAY_SECTIONS = (
    (1, "## 1. 한 줄 총평:등급(50~70 🟠 경계/ 71~84 🔴 위험 / 85~100 ⛔ 초위험)"),
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


def _koreanize_sections(md: str, mat: dict, cfg: dict, sysmsg: dict, mx: int) -> str:
    """섹션별로 한글 비율을 보고, 영문으로 쓴 섹션만 한국어로 다시 받는다.

    이 모델은 간헐적으로 한 섹션(주로 4번 상세 분석·5번 제안)을 영어로 써 버린다.
    보고서 전체를 버리면 아까우니 그 섹션만 골라 재작성시키고, 재작성도 영문이면
    통계 기반 한국어 문장으로 대체한다. 표(2번)는 손대지 않는다.
    """
    secs = _split_sections(md)
    out, fixed = [], []
    for head, body in secs:
        if not body or _is_korean(head + "\n" + body):
            out.append((head, body))
            continue
        name = head.lstrip("# ").strip() or "본문"
        ko, err = chat([sysmsg, {"role": "user", "content":
                        f"""아래는 M16 BR 반송 보고서의 '{name}' 섹션인데 영어로 잘못 작성됐다.
같은 내용·같은 마크다운 구조(굵게·목록·표 그대로)로 **한국어로만** 다시 써라.
헤딩 줄({head.strip()}) 은 다시 쓰지 말고 본문만. 설명·서론·추론과정 없이 본문만.

{body}"""}], cfg, max_tokens=min(mx, 1600))
        if not err and ko and _is_korean(ko):
            out.append((head, scrub(ko.strip())))
            fixed.append(name + "(재작성)")
        else:
            rep = _ko_section_fallback(head, mat)
            out.append((head, rep))
            fixed.append(name + "(통계문장 대체)")
    if fixed:
        print(f"  📝 [리포트] 영문 섹션 한국어 보정 — {', '.join(fixed)}")
    return "\n".join(((h + "\n\n" if h else "") + (b + "\n" if b else "")) for h, b in out).strip()


def _ko_section_fallback(head: str, mat: dict) -> str:
    """재작성까지 실패한 섹션을 통계 기반 한국어 문장으로 채운다."""
    h = str(head or "")
    incs = mat.get("incidents") or []
    pk = mat.get("peak") or {}
    if "4." in h or "상세" in h:
        if not incs:
            return "해당 없음"
        return "\n\n".join(
            f"**이벤트 #{r['번호']} ({r['시각']} 발생)** — {r['시작영역']} "
            f"{r['최고점수']}점 {r['최고등급']}, {r['구간']} {r['지속분']}분 지속."
            for r in incs)
    if "5." in h or "제안" in h:
        if not incs:
            return "- 현행 감시 유지 (특이 추세 없음)."
        return f"- 정체 집중 구간({mat.get('busy','–')}) 재발 여부를 다음 주기에 확인 필요."
    if "1." in h or "총평" in h:
        if not incs:
            return f"금일 점수 50 이상 사건 없음 (최고 {pk.get('score',0)}점, 정상 운영)."
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
        head = f"금일 점수 50 이상 사건 없음 (최고 {pk.get('score',0)}점, 정상 운영)."

    L = [f"# 📅 {mat['date_ko']} M16 BR 반송 이벤트 발생 확인건", "",
         "## 1. 한 줄 총평:등급(50~70 🟠 경계/ 71~84 🔴 위험 / 85~100 ⛔ 초위험)", "",
         head, "",
         "## 2. AMOS 이상 감지 내역", ""]
    L.append(_amos_table_md(mat))

    L += ["", "## 3. 실제 이상 발생내역", "",
          "2번 표의 실제 발생여부를 체크하면 아래에 행이 자동 생성됩니다.", "",
          "## 4. 위험 이벤트 상세 분석 (도메인 세분화)", ""]
    if b.get("상세"):
        L.append(b["상세"])
    elif incs:
        for r in incs:
            L.append(f"**이벤트 #{r['번호']} ({r['시각']} 발생)** — {r['시작영역']} "
                     f"{r['최고점수']}점 {r['최고등급']}, {r['구간']} {r['지속분']}분 지속.")
            L.append("")
    else:
        L.append("해당 없음")

    L += ["", "## 5. 에이전트 제안", ""]
    if b.get("제안"):
        L.append(b["제안"])
    elif incs:
        L.append(f"- 정체 집중 구간({mat.get('busy','–')}) 재발 여부를 다음 주기에 확인 필요.")
    else:
        L.append("- 현행 감시 유지 (특이 추세 없음).")
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
