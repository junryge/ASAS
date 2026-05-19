"""
backend/elements_api.py - API 경로 5대 요소 (회사용).

각 요소는 독립 클래스. 자기 모델 id를 받아 backend.api_client.call_model 로 호출.
요소 간 병렬은 호출자(routes_elements.py / ralph_orchestrator.py)가 책임.
"""
import json
import re

from . import api_client, harness_rules


def _safe_json(text, fallback):
    """LLM 출력에서 JSON 추출. 실패 시 fallback."""
    if not isinstance(text, str):
        return fallback
    # 코드펜스 안의 JSON 우선
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = m.group(1) if m else text
    # 첫 { ~ 마지막 } 추출
    s, e = candidate.find("{"), candidate.rfind("}")
    if s >= 0 and e > s:
        candidate = candidate[s:e + 1]
    try:
        return json.loads(candidate)
    except (ValueError, TypeError):
        return fallback


# =====================================================================
# 나노봇 — 4단 체인 (Analyzer → Architect → Writer → Reviewer)
# =====================================================================
class Nanabot:
    DEFAULT_TIER = "medium"

    def __init__(self, model_id=None):
        self.model_id = model_id or api_client.resolve_default(self.DEFAULT_TIER)

    def stages(self, requirement, type_label, lang_label, fw_label):
        fw_str = f" + {fw_label}" if fw_label and "추천" not in fw_label else ""
        ctx = f"[{type_label}] {lang_label}{fw_str}"
        return [
            {
                "id": 1, "name": "Analyzer",
                "sys": "당신은 소프트웨어 요구사항 분석가입니다. 사용자 요구사항을 분석해 다음을 짧고 명확하게 추출:\n- 핵심 의도\n- 입력 형식\n- 출력 형식\n- 주요 제약\n- 성공 기준\n마크다운 불릿. 1200자 이내.",
                "user": f"요구사항:\n{requirement}\n\n프로젝트: {ctx}",
            },
            {
                "id": 2, "name": "Architect",
                "sys": "당신은 시스템 아키텍트입니다. 분석 결과를 받아 1-2개 적합한 구조를 제안하고 핵심 모듈을 나열. 1200자 이내, 마크다운.",
                "needs": [0],
                "user_fmt": "분석 결과:\n{}\n\n위를 기반으로 구조 설계를 제안하세요.",
            },
            {
                "id": 3, "name": "Writer",
                "sys": "당신은 기술 문서 작가입니다. 분석과 설계를 종합해 구현 가이드 MD 작성. 섹션: 개요 / 입출력 명세 / 모듈 구조 / 핵심 함수 시그니처 / 검증 방법. 한국어 주석. 1800자 이내.",
                "needs": [0, 1],
                "user_fmt": "분석:\n{}\n\n설계:\n{}\n\n위를 통합해 완성된 MD 설계도를 작성하세요.",
            },
            {
                "id": 4, "name": "Reviewer",
                "sys": "당신은 시니어 코드 리뷰어입니다. MD 설계도를 검토해 모호한 부분, 누락, 테스트 가능성을 짚으세요. 개선점만 짧게 (800자 이내).",
                "needs": [2],
                "user_fmt": "검토할 MD:\n{}\n\n위 MD를 검토하여 개선점만 짧게 나열.",
            },
        ]

    def run_stage(self, stage, outputs):
        if "user" in stage:
            user_msg = stage["user"]
        else:
            user_msg = stage["user_fmt"].format(*[outputs[i] for i in stage["needs"]])
        text, used, _ = api_client.call_model(
            self.model_id,
            [{"role": "system", "content": stage["sys"]}, {"role": "user", "content": user_msg}],
            temperature=0.4,
            max_tokens=900,
        )
        return text, used


# =====================================================================
# 컨텍스트 — 요구사항 파서
# =====================================================================
class Context:
    DEFAULT_TIER = "small"

    def __init__(self, model_id=None):
        self.model_id = model_id or api_client.resolve_default(self.DEFAULT_TIER)

    def parse(self, requirement, csv_uri=None):
        sys_prompt = (
            "당신은 요구사항을 구조화된 JSON으로 변환하는 파서입니다. "
            "다음 스키마로만 응답하세요 (코드펜스 안에 JSON):\n"
            '{"intent": str, "inputs": [str], "outputs": [str], '
            '"constraints": [str], "success_criteria": [str]}'
        )
        user = f"요구사항:\n{requirement}"
        if csv_uri:
            user += f"\n\n참고 데이터: {csv_uri}"
        text, used, _ = api_client.call_model(
            self.model_id,
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=800,
        )
        parsed = _safe_json(text, fallback={
            "intent": requirement[:200], "inputs": [], "outputs": [],
            "constraints": [], "success_criteria": [],
        })
        parsed["_model"] = used
        return parsed


# =====================================================================
# 헤르메스 — 코드 생성
# =====================================================================
class Hermes:
    DEFAULT_TIER = "large"

    def __init__(self, model_id=None):
        self.model_id = model_id or api_client.resolve_default(self.DEFAULT_TIER)

    def generate(self, md_spec, lang="Python", fw=""):
        sys_prompt = (
            f"당신은 {lang} 코드 생성기입니다. 주어진 설계 MD를 기반으로 실행 가능한 단일 파일 코드를 작성하세요. "
            "주석은 한국어. 외부 의존성 최소화. 코드만 코드펜스로 출력 (설명 금지)."
            f"{' 프레임워크: ' + fw if fw else ''}"
        )
        user = f"설계 MD:\n{md_spec}\n\n위 설계대로 단일 파일 {lang} 코드를 작성."
        text, used, _ = api_client.call_model(
            self.model_id,
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=2400,
        )
        # 코드펜스 추출
        m = re.search(r"```(?:\w+)?\s*(.*?)```", text or "", re.S)
        code = m.group(1).strip() if m else (text or "").strip()
        return {"code": code, "rationale": "", "_model": used}


# =====================================================================
# 하네스 — 검증 (L1 즉시 + L2 LLM)
# =====================================================================
class Harness:
    DEFAULT_TIER_L2 = "medium"

    def __init__(self, model_id_l2=None):
        self.model_id_l2 = model_id_l2 or api_client.resolve_default(self.DEFAULT_TIER_L2)

    def validate(self, code, run_l2=True):
        l1 = harness_rules.run(code)
        result = {"layer1": l1, "layer2": None, "layer3_needed": False}
        if not l1["ok"] or not run_l2:
            result["verdict"] = "fail-l1" if not l1["ok"] else "skipped-l2"
            return result

        sys_prompt = (
            "당신은 시니어 코드 리뷰어입니다. 코드를 분석해 다음 스키마 JSON만 응답:\n"
            '{"category": "code-bug"|"design-flaw"|"none", '
            '"severity": "NONE"|"LOW"|"MED"|"HIGH", '
            '"fix_hint": str, "confidence": float}'
        )
        user = f"코드:\n```\n{code}\n```\n\nL1 경고:\n{json.dumps(l1.get('warnings', []), ensure_ascii=False)}"
        text, used, _ = api_client.call_model(
            self.model_id_l2,
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=600,
        )
        parsed = _safe_json(text, fallback={
            "category": "none", "severity": "NONE",
            "fix_hint": "", "confidence": 0.0,
        })
        parsed["_model"] = used
        result["layer2"] = parsed

        sev = parsed.get("severity", "NONE")
        conf = float(parsed.get("confidence", 0.0) or 0.0)
        result["layer3_needed"] = (sev == "HIGH") or (conf < 0.6)
        result["verdict"] = "pass" if sev == "NONE" else f"fail-{parsed.get('category', 'unknown')}"
        return result
