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
         max_tokens: int | None = None, temperature: float | None = None):
    """OpenAI 호환 호출 → (text, None) 또는 (None, error)."""
    cfg = cfg or load_config()
    lc = cfg.get("llm", {})
    if not lc.get("enabled", True):
        return None, "LLM 비활성 (config.llm.enabled=false)"

    payload = {
        "model": lc.get("model", "gaia-Qwen3.5-397B-A17B"),
        "messages": messages,
        "temperature": temperature if temperature is not None else lc.get("temperature", 0.2),
        "max_tokens": max_tokens or lc.get("max_tokens", 2048),
        "stream": False,
    }
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
        return scrub(choices[0].get("message", {}).get("content") or ""), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


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
{{"판단":"한 문장 원인 진단","확신도":0~100 정수,"근거":["근거1","근거2"],"조치":["조치1","조치2"]}}

규칙: 룰 코드 대신 한글명. 부등호 대신 말로. '역방향'·'카운트'·'역증가'·'역류' 금지.
데이터에 없는 호기×방향을 지어내지 마라."""

    txt, err = chat([{"role": "system", "content": build_system_prompt(cfg)},
                     {"role": "user", "content": user}], cfg, max_tokens=800)
    if err:
        return None, err
    return _parse_json(txt), None


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


def _parse_json(text: str) -> dict:
    """코드펜스/잡음 섞인 응답에서 JSON 추출."""
    import re
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"판단": (text or "")[:300], "확신도": 0, "근거": [], "조치": []}


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
