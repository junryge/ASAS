"""
backend/elements_gguf.py - GGUF 경로 5대 요소 (집용).

API 모듈 import 안 함 (완전 독립). 단일 GGUF 모델로 순차 실행.
gguf.py 의 gguf_chat 만 사용.
"""
import json
import re

import gguf
from . import harness_rules


def _chat(messages, temperature=0.4, max_tokens=900):
    """GGUF 단일 채팅. 오류 시 빈 문자열 반환 (호출자가 빈 응답 처리)."""
    text, err = gguf.gguf_chat(messages, temperature=temperature, max_tokens=max_tokens)
    if err:
        raise RuntimeError(err)
    return text or ""


def _safe_json(text, fallback):
    if not isinstance(text, str):
        return fallback
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = m.group(1) if m else text
    s, e = candidate.find("{"), candidate.rfind("}")
    if s >= 0 and e > s:
        candidate = candidate[s:e + 1]
    try:
        return json.loads(candidate)
    except (ValueError, TypeError):
        return fallback


class Nanabot:
    """GGUF 나노봇 — 단일 모델이 4단을 순차 실행."""

    def stages(self, requirement, type_label, lang_label, fw_label):
        # elements_api.Nanabot.stages 와 동일 프롬프트 (단일 모델이므로 import 안 하고 복사)
        fw_str = f" + {fw_label}" if fw_label and "추천" not in fw_label else ""
        ctx = f"[{type_label}] {lang_label}{fw_str}"
        return [
            {
                "id": 1, "name": "Analyzer",
                "sys": "당신은 소프트웨어 요구사항 분석가입니다. 다음을 짧고 명확히 추출: 핵심 의도/입력/출력/제약/성공 기준. 마크다운 불릿, 1200자 이내.",
                "user": f"요구사항:\n{requirement}\n\n프로젝트: {ctx}",
            },
            {
                "id": 2, "name": "Architect",
                "sys": "시스템 아키텍트로서 1-2개 구조 제안 + 핵심 모듈 나열. 1200자 이내.",
                "needs": [0],
                "user_fmt": "분석 결과:\n{}\n\n구조 설계를 제안.",
            },
            {
                "id": 3, "name": "Writer",
                "sys": "기술 문서 작가. 분석+설계 통합해 MD 작성 (개요/입출력/모듈/시그니처/검증). 1800자 이내.",
                "needs": [0, 1],
                "user_fmt": "분석:\n{}\n\n설계:\n{}\n\n통합 MD 작성.",
            },
            {
                "id": 4, "name": "Reviewer",
                "sys": "시니어 리뷰어. MD 검토해 개선점만 짧게 (800자 이내).",
                "needs": [2],
                "user_fmt": "MD:\n{}\n\n개선점 나열.",
            },
        ]

    def run_stage(self, stage, outputs):
        if "user" in stage:
            user_msg = stage["user"]
        else:
            user_msg = stage["user_fmt"].format(*[outputs[i] for i in stage["needs"]])
        text = _chat(
            [{"role": "system", "content": stage["sys"]}, {"role": "user", "content": user_msg}],
            temperature=0.4, max_tokens=900,
        )
        return text, "gguf-local"


class Context:
    def parse(self, requirement, csv_uri=None):
        sys_prompt = (
            "요구사항을 JSON으로 변환. 스키마: "
            '{"intent": str, "inputs": [str], "outputs": [str], '
            '"constraints": [str], "success_criteria": [str]}'
        )
        user = f"요구사항:\n{requirement}" + (f"\n\n데이터: {csv_uri}" if csv_uri else "")
        text = _chat(
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.2, max_tokens=800,
        )
        parsed = _safe_json(text, fallback={
            "intent": requirement[:200], "inputs": [], "outputs": [],
            "constraints": [], "success_criteria": [],
        })
        parsed["_model"] = "gguf-local"
        return parsed


class Hermes:
    def generate(self, md_spec, lang="Python", fw=""):
        sys_prompt = (
            f"{lang} 코드 생성기. 설계 MD 기반 단일 파일 코드 작성. 한국어 주석. "
            "코드만 코드펜스로 출력." + (f" 프레임워크: {fw}" if fw else "")
        )
        user = f"설계 MD:\n{md_spec}\n\n단일 파일 {lang} 코드 작성."
        text = _chat(
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.3, max_tokens=2400,
        )
        m = re.search(r"```(?:\w+)?\s*(.*?)```", text, re.S)
        code = m.group(1).strip() if m else text.strip()
        return {"code": code, "rationale": "", "_model": "gguf-local"}


class Harness:
    def validate(self, code, run_l2=True):
        l1 = harness_rules.run(code)
        result = {"layer1": l1, "layer2": None, "layer3_needed": False}
        if not l1["ok"] or not run_l2:
            result["verdict"] = "fail-l1" if not l1["ok"] else "skipped-l2"
            return result

        sys_prompt = (
            "시니어 리뷰어. 다음 JSON만 응답: "
            '{"category":"code-bug"|"design-flaw"|"none","severity":"NONE"|"LOW"|"MED"|"HIGH",'
            '"fix_hint":str,"confidence":float}'
        )
        user = f"코드:\n```\n{code}\n```\nL1 경고:\n{json.dumps(l1.get('warnings', []), ensure_ascii=False)}"
        text = _chat(
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.2, max_tokens=600,
        )
        parsed = _safe_json(text, fallback={
            "category": "none", "severity": "NONE",
            "fix_hint": "", "confidence": 0.0,
        })
        parsed["_model"] = "gguf-local"
        result["layer2"] = parsed
        sev = parsed.get("severity", "NONE")
        conf = float(parsed.get("confidence", 0.0) or 0.0)
        result["layer3_needed"] = (sev == "HIGH") or (conf < 0.6)
        result["verdict"] = "pass" if sev == "NONE" else f"fail-{parsed.get('category', 'unknown')}"
        return result
