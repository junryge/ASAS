"""
demos_v1/router.py - classify_and_route, classify_format_and_style, build_orchestration_prompt
"""
import re
from demos_v1.config import API_TOKEN
from demos_v1.models import ENV_CONFIG
from demos_v1.skills import SKILL_DESC_KO

def build_orchestration_prompt(query, skill_ids, loaded_skills_content):
    """멀티에이전트 오케스트레이션 프롬프트 생성

    [Expert 역할] 각 스킬을 전문가로 취급
    [Synthesizer 역할] 여러 전문가 지식을 조합하는 지시문
    """
    if len(loaded_skills_content) <= 1:
        return ""  # 단일 스킬이면 오케스트레이션 불필요

    expert_names = [f"[{SKILL_DESC_KO.get(sid, sid)}]" for sid in skill_ids if sid in loaded_skills_content]

    orchestration = f"""
[멀티에이전트 오케스트레이션 모드]
현재 {len(expert_names)}명의 전문가 지식이 로드되었습니다: {', '.join(expert_names)}

당신은 이 전문가들의 지식을 조합하여 최적의 답변을 생성하는 통합 전문가입니다.

[오케스트레이션 원칙]
1. 각 SKILL의 전문 지식을 해당 영역에 맞게 활용
2. 서로 다른 SKILL 간의 시너지를 찾아 조합 (예: biopython + matplotlib → 서열분석+시각화)
3. 답변을 하나의 통합된 흐름으로 제시 (분절되지 않게)
4. 각 SKILL에서 가져온 핵심 기법/코드를 명시하되, 자연스럽게 녹여내기
"""
    return orchestration


# ===================== 멀티에이전트 라우터: 작업 분류 & 모델 자동 선택 =====================
VISION_SIGNALS = [
    "이미지", "사진", "그림 분석", "사진 속", "보이는", "스크린샷",
    "screenshot", "그림에서", "화면", "figure", "diagram", "차트 읽",
    "이 그림", "이 사진", "이미지에서", "사진에서", "이미지를", "사진을",
    "이미지 속", "보여주는", "캡처", "화면에",
]
COMPLEX_SIGNALS = [
    "분석", "비교", "설계", "아키텍처", "최적화", "리팩토링", "구현해줘",
    "전체 코드", "시스템 설계", "파이프라인", "종합", "심층", "상세히",
    "비교 분석", "장단점", "트레이드오프", "벤치마크",
]
PPT_SIGNALS = [
    "ppt", "피피티", "파워포인트", "슬라이드", "발표자료", "프레젠테이션",
    "발표 만들", "deck", "피치덱",
]
DATA_SIGNALS = [
    "데이터 분석", "csv 분석", "통계 분석", "회귀", "상관관계",
    "데이터셋", "데이터프레임", "pandas", "히스토그램", "분포",
]
SIMPLE_MAX_LEN = 50  # 이 길이 이하의 짧은 질문은 간단한 Q&A로 간주


def classify_and_route(query, history, uploaded_files_list):
    """작업 유형을 분류하고 최적 모델(env_id)을 자동 선택하는 휴리스틱 라우터

    Returns:
        (env_id, route_reason): 선택된 환경 ID와 선택 이유
    """
    q = query.lower() if query else ""
    has_images = any(f.get("type") == "image" for f in uploaded_files_list)
    has_csv = any(f.get("ext", "").lower() in ("csv", "tsv", "xlsx") for f in uploaded_files_list)
    has_vision_kw = any(kw in q for kw in VISION_SIGNALS)

    # 만약 온라인 모델용 토큰이 없으면, 강제로 로컬 GGUF 모델 중에서 자동 선택
    if not API_TOKEN:
        gguf_envs = {k: v for k, v in ENV_CONFIG.items() if str(k).startswith("gguf-")}
        if not gguf_envs:
            return "common", "토큰 없음 & 로컬 모델 없음 → 실패 예상"
        
        vl_ggufs = [k for k, v in gguf_envs.items() if "vl" in v["name"].lower()]
        normal_ggufs = [k for k, v in gguf_envs.items() if "vl" not in v["name"].lower()]
        
        if has_images and vl_ggufs:
            return vl_ggufs[0], f"로컬 이미지 분석 → {ENV_CONFIG[vl_ggufs[0]]['name']}"
        elif normal_ggufs:
            complex_count = sum(1 for kw in COMPLEX_SIGNALS if kw in q)
            if complex_count >= 2 or len(q) > 200:
                return normal_ggufs[0], f"로컬 복잡한 분석 → {ENV_CONFIG[normal_ggufs[0]]['name']}"
            else:
                return normal_ggufs[-1], f"로컬 간단한 요청 → {ENV_CONFIG[normal_ggufs[-1]]['name']}"
        else:
            first_key = list(gguf_envs.keys())[0]
            return first_key, f"로컬 기본 모델 → {ENV_CONFIG[first_key]['name']}"

    # 1순위: 이미지 첨부 → VL 모델
    if has_images:
        # 복잡한 분석 요청 → 대형 VL
        if any(kw in q for kw in COMPLEX_SIGNALS) or len(q) > 200:
            return "vl-large", "이미지+복잡 분석 → VL-235B"
        # 보통 요청 → 중형 VL
        elif len(q) > SIMPLE_MAX_LEN:
            return "vl-medium", "이미지 분석 → VL-72B"
        # 간단한 요청 → 소형 VL
        else:
            return "vl-fast", "간단 이미지 → VL-30B"

    # 비전 키워드는 있지만 이미지가 없는 경우 (이미지 업로드 유도)
    if has_vision_kw and not has_images:
        return "vl-medium", "비전 키워드 감지 → VL-72B (이미지 업로드 권장)"

    # 2순위: PPT 생성 → 중형 모델
    if any(kw in q for kw in PPT_SIGNALS):
        return "common", "PPT 생성 → 120B"

    # 3순위: 복잡한 분석/코드/데이터 → 대형 모델
    complex_count = sum(1 for kw in COMPLEX_SIGNALS if kw in q)
    if complex_count >= 2 or (complex_count >= 1 and len(q) > 200):
        return "prod", "복잡한 분석 → 397B"

    # 4순위: 데이터 분석 (CSV 로드 + 분석 키워드)
    if has_csv or any(kw in q for kw in DATA_SIGNALS):
        return "prod", "데이터 분석 → 397B"

    # 5순위: 코드 작성 요청 (중간~긴 쿼리)
    code_kw = ["코드", "함수", "클래스", "구현", "작성", "코딩", "스크립트", "프로그래밍"]
    if any(kw in q for kw in code_kw) and len(q) > 80:
        return "prod", "코드 작성 → 397B"

    # 6순위: 간단한 Q&A → 빠른 모델
    if len(q) <= SIMPLE_MAX_LEN:
        return "dev", "간단 Q&A → GLM-5"

    # 기본값: 중형 모델
    return "common", "일반 요청 → 120B"


def classify_format_and_style(query, history, uploaded_files_list, skill_ids):
    """채팅 내용을 분석하여 최적의 출력형식과 작성 스타일을 자동 선택

    Returns:
        (format_id, style_value, reason): 출력형식, 스타일 텍스트, 선택 이유
    """
    q = query.lower() if query else ""
    has_csv = any(f.get("ext", "").lower() in ("csv", "tsv", "xlsx") for f in uploaded_files_list)
    has_code_file = any(f.get("ext", "").lower() in ("py", "js", "java", "c", "cpp", "go", "rs", "html", "css") for f in uploaded_files_list)
    has_image = any(f.get("type") == "image" for f in uploaded_files_list)

    # 비전/이미지 키워드
    vision_kw = ["이미지", "사진", "그림", "스크린샷", "screenshot", "화면", "figure",
                 "diagram", "차트 읽", "캡처", "보이는", "보여주는"]
    has_vision_kw = any(kw in q for kw in vision_kw)

    # 스킬 기반 힌트
    data_skills = {"exploratory-data-analysis", "statistical-analysis", "matplotlib",
                   "seaborn", "plotly", "polars", "statsmodels", "scikit-learn"}
    debug_skills = {"debugging", "agent-debugger", "agent-error-detective"}
    writing_skills = {"scientific-writing", "literature-review", "peer-review",
                      "research-grants", "clinical-reports"}
    knowledge_skills = {"knowledge-search", "logpresso-search"}
    has_data_skill = bool(set(skill_ids) & data_skills)
    has_debug_skill = bool(set(skill_ids) & debug_skills)
    has_writing_skill = bool(set(skill_ids) & writing_skills)
    has_knowledge_skill = bool(set(skill_ids) & knowledge_skills)

    # === 출력형식 분류 ===
    fmt = "code"  # 기본값

    # 이미지 분석 요청 → 코드 아닌 분석/설명으로 (최우선)
    if has_image or has_vision_kw:
        # 이미지 + 코드 요청이 명시적이면 코드
        code_explicit = any(kw in q for kw in ["코드", "코딩", "구현", "스크립트", "import", "def "])
        if code_explicit:
            fmt = "code"
        else:
            fmt = "analysis"

    # 도메인 지식 조회 (knowledge-search) → 코드가 아닌 설명/보고 형식
    elif has_knowledge_skill:
        code_explicit = any(kw in q for kw in ["코드", "코딩", "구현", "스크립트", "import", "def "])
        if code_explicit:
            fmt = "code"
        else:
            fmt = "report"

    # 보고서/리포트 요청
    elif any(kw in q for kw in ["보고서", "리포트", "report", "요약해줘", "요약 작성", "정리해줘",
                 "문서 작성", "문서화", "보고", "브리핑", "개요"]) or has_writing_skill:
        fmt = "report"

    # 데이터 분석 요청
    elif has_csv or has_data_skill or any(kw in q for kw in ["분석해줘", "분석해 줘", "데이터 분석", "인사이트", "통계 분석", "상관관계", "추세"]):
        fmt = "analysis"

    # LLM/아키텍처 설계 요청
    elif any(kw in q for kw in ["llm", "rag", "아키텍처", "시스템 설계", "트레이드오프", "모델 라우팅"]):
        fmt = "analysis"

    # 단계별 설명 요청
    elif any(kw in q for kw in ["방법", "어떻게", "절차", "과정", "단계별", "step by step",
                                 "가르쳐", "알려줘", "설명해", "튜토리얼", "가이드"]):
        fmt = "step-by-step"

    # 디버깅/코드 수정
    elif has_debug_skill or has_code_file or any(kw in q for kw in ["에러", "error", "버그", "bug", "수정", "고쳐", "안돼", "안되", "traceback", "exception", "오류"]):
        fmt = "code-fix"

    # 코드 작성 요청
    elif any(kw in q for kw in ["코드", "함수", "클래스", "구현", "작성", "코딩", "스크립트",
                                 "만들어", "프로그래밍", "import", "def ", "class "]):
        fmt = "code"

    # 일반 질문/대화 → 단계별 (코드보다 설명 우선)
    elif not any(kw in q for kw in ["코드", "코딩", "구현", "함수", "클래스"]):
        fmt = "step-by-step"

    # === 스타일 분류 ===
    style = ""  # 기본값: 없음 (시스템 기본)

    # 이미지 분석 모드
    if (has_image or has_vision_kw) and fmt == "analysis":
        style = "이미지 내용을 자연어로 설명하세요. 코드 없이 분석 결과만 제시. 핵심 내용→세부 관찰→해석 순서."

    # 디버깅 모드
    elif fmt == "code-fix" or has_debug_skill:
        style = "에러 원인 분석 중심. traceback 해석, 재현 조건, 해결책 순서."

    # 도메인 지식 조회 모드
    elif has_knowledge_skill:
        style = "문서 내용을 구조화하여 설명. 표(table), 필드별 설명, 핵심 요약 순서. raw 데이터는 표로 변환."

    # LLM 설계 모드
    elif "agent-llm-architect" in skill_ids or any(kw in q for kw in ["llm", "rag", "아키텍처", "시스템 설계"]):
        style = "설계 의사결정 중심. 요구사항→옵션 비교→트레이드오프→권장안→실행계획 순서."

    # 데이터 분석 모드
    elif fmt == "analysis" or has_data_skill:
        style = "데이터 스토리텔링. 숫자→의미→액션 순서로 해석."

    # 학술/논문 모드
    elif has_writing_skill or any(kw in q for kw in ["논문", "학술", "연구", "인용", "레퍼런스", "paper"]):
        style = "학술적 톤. 정확한 용어, 인용, 근거 제시."

    # 실용적 모드 (기본 코드 작성)
    elif fmt in ("code", "code-fix"):
        style = "실전에서 바로 활용 가능하게. 핵심 요점과 구체적 방법 위주. 선택된 출력형식에 맞춰 답변하세요."

    reason = f"형식:{fmt}"
    if style:
        reason += " / 스타일 자동"

    return fmt, style, reason

