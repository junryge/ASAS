"""
demos_v1/routes_ppt.py - PPT 설계 모드 API

엔드포인트:
- GET  /api/ppt/templates        : 테마 목록
- GET  /api/ppt/models           : 선택 가능 모델 목록 (사내 API + 로컬 GGUF)
- POST /api/ppt/from-md          : MD 텍스트 → .pptx
- POST /api/ppt/from-md-file     : .md 파일 → .pptx
- POST /api/ppt/from-blocks      : outline JSON → .pptx
- POST /api/ppt/from-llm         : 주제/MD + 모델 선택 → LLM이 디자인 JSON → .pptx
- POST /api/ppt/preview-outline  : MD 파싱 미리보기
- GET  /api/ppt/download/<id>    : .pptx 다운로드
"""
import os
import json
import re
import requests
from flask import request, jsonify, send_file

from demos_v1.ppt_builder import (
    md_to_pptx_file, render_outline_to_pptx, save_pptx, get_pptx_path,
    parse_md_to_outline, list_templates, DEFAULT_THEME, THEME_PRESETS,
)
from demos_v1.models import ENV_CONFIG
from demos_v1.config import API_TOKEN


# ============================================================
# LLM 디자인 시스템 프롬프트
# ============================================================
_DESIGN_SYSTEM_PROMPT = """너는 PowerPoint 디자인 디렉터다. 사용자 입력(MD 또는 주제)을
받아서 **발표용 슬라이드를 직접 기획·요약·디자인** 한다. 출력은 **오직 유효한 JSON** 만
(앞뒤 설명·코드블록 X).

==== 🚨 가장 중요한 원칙 — 절대 복사 금지 🚨 ====
너는 **요약하는 디자이너**다. 받은 텍스트를 그대로 슬라이드에 박지 마라.

❌ **나쁜 예 (절대 하지 마)**:
  - 사용자가 "FREE_FLOW_SPEED는 DOUBLE 타입이고 RailEdge.getVelocity()로
    HID별 평균을 구한다" 라고 하면, 그 문장 그대로 textbox 에 박기 → ❌
  - MD 표를 그대로 옮겨 적기 → ❌
  - 코드 블록 그대로 textbox 에 옮기기 → ❌
  - 긴 설명문 그대로 박기 → ❌

✅ **좋은 예 (이렇게 해)**:
  - "FREE_FLOW_SPEED 추가 - 1분 평균속도" (한 줄로 압축, 카드 형태로)
  - 표 → 카드 도형 2~3개로 핵심만 (각 카드 텍스트 5~10자)
  - 코드 → "데이터 흐름 변경" 같은 도식 (원+화살표)
  - 긴 설명 → 키워드 3~5개만 (각 도형 안에 1~3 단어)

규칙:
1. **각 textbox/도형 안의 텍스트는 최대 30자**. 절대 문장 통째로 X
2. 슬라이드는 5~8장. 입력이 길어도 늘리지 마라
3. 코드 블록은 무시하거나 "코드 변경" 한 단어로
4. 표는 항목명만 추출해서 카드 도형으로
5. 청중이 발표 들으며 1초만에 이해해야 함

==== 출력 스키마 ====
{
  "meta": {"title": "...", "subtitle": "..."},
  "slides": [
    {
      "type": "custom",
      "title": "슬라이드 제목 (선택)",
      "shapes": [
        {"shape": "<type>", "x": <inch>, "y": <inch>, "w": <inch>, "h": <inch>,
         "fill": "#RRGGBB", "line": "#RRGGBB", "line_width": 1.5,
         "text": "...", "font_size": 18, "font_color": "#RRGGBB",
         "bold": false, "italic": false, "align": "center"}
      ]
    }
  ]
}

도형 종류 (shape):
  rect, rounded_rect, circle, oval, triangle, diamond, pentagon, hexagon,
  star, arrow_right, arrow_left, arrow_up, arrow_down, chevron, callout,
  cloud, line, textbox

캔버스: {CANVAS} (가로). 좌표는 inch 단위.

==== 슬라이드 구성 — 자동 기획 (사용자가 시키지 않아도 너가 결정) ====
사용자가 raw MD나 주제만 던졌을 때, 너가 알아서 다음 패턴으로 5~8장 기획한다:

**1번 슬라이드 — 표지**
  - MD 제목/주제에서 큰 제목 textbox 추출
  - 날짜·부제 있으면 추가
  - 액센트 도형 1~2개로 장식

**2번 슬라이드 — 핵심 요약**
  - MD 전체에서 가장 중요한 3가지를 카드 그리드로
  - 또는 "한 줄 정리" 큰 statement

**3~N번 — 본문 (자동으로 어떻게 시각화할지 판단)**
  너가 MD 섹션을 분석해서 가장 잘 어울리는 시각화를 고른다:
  - 필드/항목 추가 → 좌우 비교 카드 (서로 다른 색)
  - 데이터 흐름·프로세스 → 원/사각형 + 화살표 (좌→우 가로 배치)
  - 파일·대상 목록 → 카드 그리드
  - 비교 (전후, A vs B) → 좌우 분할
  - 단계 → 번호 매긴 사각형 + 화살표
  - 통계·수치 → 거대 숫자 + 작은 라벨

**마지막 슬라이드 — 마무리**
  - 핵심 메시지 한 줄 또는 "다음 단계" 요약

==== 자동 기획 예시 (MD 입력 → 너가 알아서 기획) ====
입력: "OHT 시스템에 FREE_FLOW_SPEED, HID_VALUE 두 필드 추가. 파일 2개 수정.
       데이터 소스는 RailEdge.getVelocity() / DataSet.getHidVehicleCountMap().
       기존 FunctionType.HID_INOUT 스위치로 제어"

너의 자동 기획:
  1) 표지 — "HID_INOUT 필드 추가" + 날짜
  2) 추가 필드 좌우 카드 — FREE_FLOW_SPEED (파랑) / HID_VALUE (초록)
  3) 데이터 흐름 — 원 3개 (UDP수신 → 처리 → 전송) + 화살표
  4) 수정 파일 2개 카드 — 실시간 vs 배치
  5) 핵심 변경 요약 — 카드 3개 (필드 추가 / 흐름 / 스위치)
  6) 마무리 — 한 줄 정리

이렇게 사용자가 슬라이드 구성을 안 시켜도 알아서 디자인한다.

좋은 시각화 예시:
- 데이터 흐름 → 원 3개 + 화살표 2개 (좌→우 배치)
- 비교 → 좌우 카드 2개 (다른 색)
- 수치 강조 → 거대한 숫자 + 작은 라벨
- 핵심 3~4가지 → 카드 그리드 + 아이콘(별/체크) 도형
- 단계 → 단계별 사각형 + 숫자

==== JSON 규칙 ====
1. 응답 전체가 유효한 JSON 객체. 다른 텍스트 절대 금지.
2. 좌표 (x, y) 는 도형의 좌상단. (x+w) ≤ {CW}, (y+h) ≤ {CH}
3. 도형끼리 겹치지 말고 충분한 여백 (최소 0.2인치)
4. 슬라이드당 도형 5~12개 권장. 너무 많으면 어수선
5. 한글 OK. font_size 는 12~80 사이 (제목 32~60, 본문 14~22)
6. 입력 길어도 **JSON 출력은 최대한 짧게** — 핵심만
"""


def _preprocess_md_for_llm(md: str, max_chars: int = 4000,
                            aggressive: bool = True) -> str:
    """LLM에 보내기 전 MD 전처리.

    aggressive=True (기본): 본문/긴 단락도 다 줄이고 **섹션 헤더 + 핵심 키워드만**
      남김. 작은 LLM (26B 이하) 이 복사할 텍스트 자체가 거의 없게 만듦.
    aggressive=False: 코드·긴 표만 제거 (소프트 모드).
    """
    if not md:
        return ""
    text = md
    # 1) frontmatter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    # 2) 코드 블록 → 한 마디
    text = re.sub(r"```[\w]*\n.*?```", "[코드: 1단어로 요약]",
                  text, flags=re.DOTALL)
    # 3) 표 → 헤더만 + 핵심 항목명
    def _shrink_table(m):
        block = m.group(0)
        rows = [r.strip() for r in block.split("\n") if r.strip().startswith("|")]
        if len(rows) <= 2:
            return block
        # 헤더 + 첫 컬럼만 추출 (항목명만)
        if aggressive:
            items = []
            for r in rows[2:7]:  # 본문 첫 5행만
                cells = [c.strip() for c in r.strip("|").split("|")]
                if cells and cells[0]:
                    # 백틱·코드 제거
                    nm = re.sub(r"[`*]", "", cells[0])
                    items.append(nm[:30])  # 30자 컷
            return "[표 항목]: " + ", ".join(items) if items else "[표 있음]"
        else:
            kept = rows[:2] + rows[2:5] + ["| ... |"]
            return "\n".join(kept)
    text = re.sub(r"(?:^\|.*\|\s*\n)+", _shrink_table, text, flags=re.MULTILINE)
    # 4) 인라인 코드 줄임
    text = re.sub(r"`[^`\n]{40,}`", "`(코드)`", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)  # 짧은 인라인 코드는 백틱만 제거
    # 5) aggressive: 본문 단락도 짧게 (불릿 한 줄로 요약)
    if aggressive:
        # 5a) 긴 줄 (80자 초과) → 80자에서 컷
        lines = []
        for ln in text.split("\n"):
            stripped = ln.strip()
            if not stripped:
                lines.append("")
                continue
            # 헤더는 그대로
            if stripped.startswith("#"):
                lines.append(ln)
                continue
            # 불릿/번호는 80자 컷
            if re.match(r"^\s*[-*+]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
                if len(stripped) > 80:
                    lines.append(ln[:ln.find(stripped) + 80] + "...")
                else:
                    lines.append(ln)
                continue
            # 일반 본문 줄: 60자 초과면 첫 60자만
            if len(stripped) > 60:
                lines.append(ln[:60].rstrip() + "...")
            else:
                lines.append(ln)
        text = "\n".join(lines)
    # 6) 연속 빈줄 압축
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # 7) 최종 길이 컷
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...생략, 위에서 핵심만 추출해 디자인...]"
    return text


                            # (가로, 세로) inch
PPTX_CANVAS = (10.0, 7.5)       # 4:3 — python-pptx 기본 슬라이드
BENTO_CANVAS = (13.333, 7.5)    # 16:9 — Bento 캔버스(1280×720)와 같은 비율


def _design_prompt(theme: str, canvas: tuple = PPTX_CANVAS) -> str:
    """디자인 시스템 프롬프트 완성 (캔버스 크기·액센트 컬러 채워 넣기).

    ★자리표시자를 안 채우면 모델이 '{CW}인치' 를 글자 그대로 읽는다.
    """
    accent = THEME_PRESETS.get(theme, THEME_PRESETS[DEFAULT_THEME])["accent"]
    accent_hex = f"#{accent[0]:02X}{accent[1]:02X}{accent[2]:02X}"
    cw, ch = float(canvas[0]), float(canvas[1])
    return (_DESIGN_SYSTEM_PROMPT
            .replace("{CANVAS}", f"{cw:g}인치 × {ch:g}인치")
            .replace("{CW}", f"{cw:g}").replace("{CH}", f"{ch:g}")
            + f"\n현재 테마 액센트 컬러: {accent_hex}\n")


def _call_llm_for_design(model_id: str, user_input: str, theme: str,
                         max_tokens: int = 8192,
                         canvas: tuple = PPTX_CANVAS) -> tuple[dict | None, str | None]:
    """선택된 모델로 디자인 JSON 생성. (design_dict, error_msg) 반환.

    ★캔버스 비율을 출력 형식에 맞춘다. pptx 는 4:3(10×7.5), Bento 는
      16:9(13.333×7.5) 다. 안 맞추면 넓은 화면 양옆이 통째로 비거나, 반대로
      도형이 화면 밖으로 나간다.
    """
    cfg = ENV_CONFIG.get(model_id)
    if not cfg:
        return None, f"모델을 찾을 수 없음: {model_id}"

    sys_prompt = _design_prompt(theme, canvas)

    # MD 전처리 (코드·긴 표 제거) — 작은 LLM 의 '복사 본능' 차단
    preprocessed = _preprocess_md_for_llm(user_input)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": preprocessed},
    ]

    url = cfg.get("url", "")
    is_gguf = url.startswith("python://")

    raw_text = ""
    if is_gguf:
        # 로컬 GGUF
        try:
            from demos_v1.gguf import gguf_chat
            from demos_v1 import utils as _u
            # 현재 로드된 모델이 요청 모델과 다르면 재로드
            target_path = cfg.get("_gguf_path")
            if target_path and (not _u.gguf_loaded_path
                                or _u.gguf_loaded_path != target_path):
                from demos_v1.gguf import load_gguf_model
                if not load_gguf_model(target_path):
                    return None, f"GGUF 로드 실패: {target_path}"
            text, err = gguf_chat(messages, temperature=0.3,
                                   max_tokens=max_tokens)
            if err:
                return None, f"GGUF 추론 오류: {err}"
            raw_text = text or ""
        except Exception as e:
            return None, f"GGUF 호출 예외: {e}"
    else:
        # 사내 API
        if not API_TOKEN:
            return None, "API_TOKEN 이 비어있음 (TOKEN.TXT 확인)"
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {API_TOKEN}"}
        payload = {
            "model": cfg.get("model", model_id),
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload,
                                  timeout=120, verify=False)
            if resp.status_code != 200:
                return None, f"API {resp.status_code}: {resp.text[:300]}"
            data = resp.json()
            raw_text = (data.get("choices", [{}])[0]
                            .get("message", {}).get("content", ""))
        except Exception as e:
            return None, f"API 호출 예외: {e}"

    if not raw_text:
        return None, "LLM 빈 응답"

    # JSON 추출 (간혹 코드펜스로 감싸는 모델 대응)
    txt = raw_text.strip()
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", txt)
    if m:
        txt = m.group(1)
    else:
        # 첫 { 부터 마지막 } 까지
        i = txt.find("{")
        j = txt.rfind("}")
        if i >= 0 and j > i:
            txt = txt[i:j + 1]

    try:
        design = json.loads(txt)
    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 실패: {e} | 원본: {raw_text[:300]}"

    if not isinstance(design, dict) or "slides" not in design:
        return None, f"스키마 어긋남 (slides 없음): {str(design)[:300]}"

    # 디버깅 정보 동봉 (라우트에서 응답에 포함)
    design["_debug"] = {
        "preprocessed_input": preprocessed[:1500],
        "raw_llm_response_preview": raw_text[:800],
    }
    return design, None


def _auto_model() -> str:
    """모델을 안 고르면 우리가 고른다.

    ★"모델을 선택하세요" 는 사용자가 답을 아는 질문이 아니다. 쓸 수 있는
      것 중 하나를 잡아 준다. 사내 API 를 먼저 본다(집에서는 토큰이 없으니
      자동으로 GGUF 로 내려간다).
    """
    api, gguf = [], []
    for env_id, cfg in ENV_CONFIG.items():
        (gguf if str(cfg.get("url", "")).startswith("python://") else api
         ).append(env_id)
    if api and API_TOKEN:
        return api[0]
    if gguf:
        try:                              # 이미 올라와 있는 모델이 있으면 그걸
            from demos_v1 import utils as _u
            loaded = getattr(_u, "gguf_loaded_path", None)
            if loaded:
                for e in gguf:
                    if ENV_CONFIG[e].get("_gguf_path") == loaded:
                        return e
        except Exception:
            pass
        return gguf[0]
    return ""


def _llm_text(model_id: str, system: str, user: str,
              max_tokens: int = 4096) -> tuple[str, str]:
    """모델 한 번 부르기 → (본문, 오류). API·GGUF 갈래를 여기서 흡수한다."""
    cfg = ENV_CONFIG.get(model_id)
    if not cfg:
        return "", f"모델을 찾을 수 없음: {model_id}"
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    url = cfg.get("url", "")
    if url.startswith("python://"):
        try:
            from demos_v1.gguf import gguf_chat, load_gguf_model
            from demos_v1 import utils as _u
            target = cfg.get("_gguf_path")
            if target and getattr(_u, "gguf_loaded_path", None) != target:
                if not load_gguf_model(target):
                    return "", f"GGUF 로드 실패: {target}"
            text, err = gguf_chat(messages, temperature=0.3,
                                  max_tokens=max_tokens)
            return (text or ""), (f"GGUF 추론 오류: {err}" if err else "")
        except Exception as e:
            return "", f"GGUF 호출 예외: {e}"
    if not API_TOKEN:
        return "", "API_TOKEN 이 비어있음 (TOKEN.TXT 확인)"
    try:
        resp = requests.post(
            url, headers={"Content-Type": "application/json",
                          "Authorization": f"Bearer {API_TOKEN}"},
            json={"model": cfg.get("model", model_id), "messages": messages,
                  "temperature": 0.3, "max_tokens": max_tokens, "stream": False},
            timeout=120, verify=False)
        if resp.status_code != 200:
            return "", f"API {resp.status_code}: {resp.text[:200]}"
        return (resp.json().get("choices", [{}])[0]
                .get("message", {}).get("content", "")), ""
    except Exception as e:
        return "", f"API 호출 예외: {e}"


def _extract_json(raw: str):
    """모델이 코드펜스나 잡담을 붙여도 JSON 만 꺼낸다."""
    txt = (raw or "").strip()
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", txt)
    if m:
        txt = m.group(1)
    else:
        i, j = txt.find("{"), txt.rfind("}")
        if i >= 0 and j > i:
            txt = txt[i:j + 1]
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def _call_llm_for_outline(model_id: str, text: str,
                          title_hint: str = "") -> tuple[dict | None, str]:
    """모델에게 **무슨 내용인지만** 받는다 → 블록 목록.

    ★도형 좌표를 시키지 않는다. 작은 모델은 겹치거나 화면 밖으로 나가는
      걸 잘 낸다. 배치는 우리 렌더러가 한다.
    """
    from demos_v1 import auto_deck as ad
    body = _preprocess_md_for_llm(text, max_chars=6000, aggressive=False)
    raw, err = _llm_text(model_id, ad.AUTO_SYSTEM_PROMPT, body)
    if err:
        return None, err
    if not raw.strip():
        return None, "LLM 빈 응답"
    obj = _extract_json(raw)
    if obj is None:
        return None, f"JSON 파싱 실패 (앞부분: {raw.strip()[:120]})"
    outline = ad.normalize_outline(obj, title_hint=title_hint)
    if outline is None:
        return None, "쓸 만한 슬라이드가 없었음"
    return outline, ""


def register_ppt_routes(app):
    """Flask 앱에 PPT 설계 모드 라우트 등록."""

    @app.route("/api/ppt/templates", methods=["GET"])
    def api_ppt_templates():
        """사용 가능한 테마 목록."""
        return jsonify({"ok": True, "templates": list_templates(),
                        "default": DEFAULT_THEME})

    @app.route("/api/ppt/models", methods=["GET"])
    def api_ppt_models():
        """LLM 디자인용 선택 가능한 모델 목록 (사내 API + 로컬 GGUF)."""
        items = []
        for env_id, cfg in ENV_CONFIG.items():
            url = cfg.get("url", "")
            is_gguf = url.startswith("python://")
            items.append({
                "id": env_id,
                "name": cfg.get("name", env_id),
                "model": cfg.get("model", ""),
                "kind": "GGUF" if is_gguf else "API",
                "size_gb": cfg.get("_size_gb"),
            })
        # GGUF → API 순으로 정렬, 그 안에서 이름순
        items.sort(key=lambda x: (x["kind"], x["name"]))
        return jsonify({"ok": True, "models": items})

    @app.route("/api/ppt/from-llm", methods=["POST"])
    def api_ppt_from_llm():
        """MD/주제 + 모델 선택 → LLM이 디자인 JSON → .bento.html (또는 .pptx).

        ★설계는 LLM 이 한다. 여기서 바뀐 건 '그 설계를 무엇으로 그리느냐'
          뿐이다 — format="bento"(기본) / "pptx".
        body: {"input": "...", "model": "...", "template": "...",
               "format": "bento|pptx", "theme": "dark|light|corporate|hynix"}
        """
        data = request.json or {}
        user_input = (data.get("input") or data.get("md") or
                      data.get("prompt") or "").strip()
        model_id = (data.get("model") or "").strip()
        template = (data.get("template") or DEFAULT_THEME).strip()
        fmt = str(data.get("format") or "bento").lower()
        if not user_input:
            return jsonify({"error": "입력이 비어있습니다."}), 400
        if not model_id:
            return jsonify({"error": "모델을 선택하세요."}), 400

        canvas = PPTX_CANVAS if fmt == "pptx" else BENTO_CANVAS
        design, err = _call_llm_for_design(model_id, user_input, template,
                                           canvas=canvas)
        if err:
            return jsonify({"error": err}), 500

        if fmt != "pptx":
            from demos_v1 import bento_builder as bb
            theme = (data.get("theme") or template or bb.DEFAULT_THEME)
            try:
                html, doc = bb.build_from_design(
                    design, theme=theme, canvas=canvas,
                    footer=(data.get("footer") or "").strip())
            except Exception as e:
                import traceback; traceback.print_exc()
                return jsonify({"error": f"렌더링 실패: {e}",
                                "design": design}), 500
            title = (design.get("meta") or {}).get("title") or "llm_design"
            info = _save_bento(html, title)
            slides = design.get("slides", [])
            print(f"[ppt] LLM→Bento: {info['filename']} · {len(doc['slides'])}장 "
                  f"· 모델 {model_id}")
            return jsonify({
                "ok": True, "format": "bento",
                "id": info["id"], "filename": info["filename"],
                "size": info["size"], "slide_count": len(doc["slides"]),
                "model": model_id, "template": template,
                "theme": theme if theme in bb.THEMES else bb.DEFAULT_THEME,
                "download_url": f"/api/ppt/bento/download/{info['id']}",
                "slides_summary": [
                    {"type": s.get("type", "?"), "title": s.get("title", "")}
                    for s in slides
                ],
                "_debug": design.get("_debug", {}),
            })

        # 렌더
        try:
            pptx_bytes = render_outline_to_pptx(design, template=template)
        except Exception as e:
            return jsonify({"error": f"렌더링 실패: {e}",
                            "design": design}), 500
        title = design.get("meta", {}).get("title", "llm_design")
        info = save_pptx(pptx_bytes, hint=title)
        slides = design.get("slides", [])
        return jsonify({
            "ok": True,
            "format": "pptx",
            "id": info["id"],
            "filename": info["filename"],
            "size": info["size"],
            "slide_count": len(slides),
            "model": model_id,
            "template": template,
            "download_url": f"/api/ppt/download/{info['id']}",
            "slides_summary": [
                {"type": s.get("type", "?"), "title": s.get("title", "")}
                for s in slides
            ],
            "_debug": design.get("_debug", {}),
        })

    # ══════════ 알아서 만들기 ══════════
    # ★"MD 문법을 알아야 하고, 탭을 고르고, 모델을 고르고" 는 도구가 사람한테
    #   일을 시키는 것이다. 붙여 넣고 버튼 하나면 나와야 한다.
    @app.route("/api/ppt/auto", methods=["POST"])
    def api_ppt_auto():
        """적은 내용 → 발표자료. 모델이 있으면 쓰고, 없거나 실패하면 규칙으로.

        body: {"text": "...", "theme": "...", "model": "자동|<모델ID>",
               "format": "bento|pptx", "title": "...", "footer": "..."}
        """
        from demos_v1 import auto_deck as ad
        from demos_v1 import bento_builder as bb
        data = request.json or {}
        text = (data.get("text") or data.get("input") or data.get("md") or "").strip()
        if not text:
            return jsonify({"error": "내용을 적어 주세요."}), 400
        fmt = str(data.get("format") or "bento").lower()
        hint = (data.get("title") or "").strip()

        model_id = (data.get("model") or "").strip()
        if model_id in ("", "auto", "자동"):
            model_id = _auto_model()

        outline, used, note = None, "규칙", ""
        if model_id:
            outline, why = _call_llm_for_outline(model_id, text, hint)
            if outline:
                used = "llm"
            else:
                note = why or "모델 응답을 쓸 수 없었습니다"
                print(f"[ppt] 알아서: LLM 실패 → 규칙으로 ({note})")
        if outline is None:
            # ★"모델이 안 붙어서 못 만들었습니다" 는 답이 아니다. 뭐라도 나와야
            #   한다. 대신 무엇으로 만들었는지는 정직하게 알린다.
            outline = ad.plain_to_outline(text, title_hint=hint)

        slides = outline.get("slides") or []
        title = (outline.get("meta") or {}).get("title") or hint or "발표자료"
        try:
            if fmt == "pptx":
                info = save_pptx(render_outline_to_pptx(
                    outline, template=(data.get("template") or DEFAULT_THEME)),
                    hint=title)
                dl = f"/api/ppt/download/{info['id']}"
            else:
                html, doc = bb.build(
                    slides, title=title,
                    theme=data.get("theme") or bb.DEFAULT_THEME,
                    footer=(data.get("footer") or "").strip())
                info = _save_bento(html, title)
                slides = doc["slides"]
                dl = f"/api/ppt/bento/download/{info['id']}"
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

        print(f"[ppt] 알아서: {info['filename']} · {len(slides)}장 · {used}"
              + (f" ({model_id})" if used == "llm" else ""))
        return jsonify({
            "ok": True, "format": "pptx" if fmt == "pptx" else "bento",
            "id": info["id"], "filename": info["filename"],
            "size": info["size"], "slide_count": len(slides),
            "used": used, "model": model_id if used == "llm" else "",
            "note": note, "download_url": dl,
            "slides_summary": [
                {"type": s.get("type", "content"), "title": s.get("title", "")}
                for s in (outline.get("slides") or [])
            ],
        })

    @app.route("/api/ppt/from-md", methods=["POST"])
    def api_ppt_from_md():
        """MD 텍스트 → .pptx 자동 생성."""
        data = request.json or {}
        md_text = (data.get("md") or data.get("markdown") or "").strip()
        title_hint = (data.get("title") or "").strip()
        template = (data.get("template") or DEFAULT_THEME).strip()
        if not md_text:
            return jsonify({"error": "MD 텍스트가 비어있습니다."}), 400
        try:
            info = md_to_pptx_file(md_text, title_hint=title_hint, template=template)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": info["slide_count"],
                "download_url": f"/api/ppt/download/{info['id']}",
                "slides_summary": [
                    {"type": s.get("type"), "title": s.get("title", "")}
                    for s in info.get("outline", {}).get("slides", [])
                ],
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/from-md-file", methods=["POST"])
    def api_ppt_from_md_file():
        """.md 파일 업로드 → .pptx 자동 생성."""
        if "file" not in request.files:
            return jsonify({"error": "파일이 첨부되지 않았습니다."}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "빈 파일입니다."}), 400
        if not f.filename.lower().endswith((".md", ".markdown", ".txt")):
            return jsonify({"error": ".md / .markdown / .txt 파일만 허용됩니다."}), 400
        raw = f.read()
        # 인코딩 자동 감지 (utf-8 → utf-8-sig → cp949 → euc-kr)
        md_text = None
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
            try:
                md_text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if md_text is None:
            return jsonify({"error": "파일 인코딩을 해석할 수 없습니다."}), 400
        title_hint = os.path.splitext(f.filename)[0]
        template = (request.form.get("template") or DEFAULT_THEME).strip()
        try:
            info = md_to_pptx_file(md_text, title_hint=title_hint, template=template)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": info["slide_count"],
                "download_url": f"/api/ppt/download/{info['id']}",
                "source_filename": f.filename,
                "slides_summary": [
                    {"type": s.get("type"), "title": s.get("title", "")}
                    for s in info.get("outline", {}).get("slides", [])
                ],
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/from-blocks", methods=["POST"])
    def api_ppt_from_blocks():
        """채팅 빌더 JSON (outline 형식) → .pptx 생성. Phase 3 UI 용."""
        data = request.json or {}
        outline = data.get("outline")
        if not outline or not isinstance(outline, dict):
            return jsonify({"error": "outline JSON 이 필요합니다."}), 400
        slides = outline.get("slides", [])
        if not slides:
            return jsonify({"error": "슬라이드가 비어있습니다."}), 400
        try:
            pptx_bytes = render_outline_to_pptx(outline)
            title = outline.get("meta", {}).get("title", "presentation")
            info = save_pptx(pptx_bytes, hint=title)
            return jsonify({
                "ok": True,
                "id": info["id"],
                "filename": info["filename"],
                "size": info["size"],
                "slide_count": len(slides),
                "download_url": f"/api/ppt/download/{info['id']}",
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

    @app.route("/api/ppt/preview-outline", methods=["POST"])
    def api_ppt_preview_outline():
        """MD 파싱만 해서 outline 구조 미리보기 (실제 .pptx 안 만듦)."""
        data = request.json or {}
        md_text = (data.get("md") or "").strip()
        if not md_text:
            return jsonify({"error": "MD 텍스트가 비어있습니다."}), 400
        try:
            outline = parse_md_to_outline(md_text)
            return jsonify({"ok": True, "outline": outline,
                           "slide_count": len(outline.get("slides", []))})
        except Exception as e:
            return jsonify({"error": f"파싱 실패: {e}"}), 500

    def _save_bento(html: str, hint: str) -> dict:
        """완성된 .bento.html 을 캐시에 저장 → {id, filename, path, size}.

        pptx 와 같은 폴더를 쓰되 확장자로 구분한다 (정리 규칙을 하나로).
        """
        import time, uuid
        from demos_v1.ppt_builder import PPT_CACHE_DIR
        bid = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        safe = re.sub(r"[^\w가-힣]+", "_", hint or "")[:40] or "발표자료"
        fname = f"{safe}_{bid}.bento.html"
        path = os.path.join(PPT_CACHE_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return {"id": bid, "filename": fname, "path": path,
                "size": os.path.getsize(path)}

    def _bento_path(bid: str) -> str | None:
        from demos_v1.ppt_builder import PPT_CACHE_DIR
        if not bid or "/" in bid or "\\" in bid or ".." in bid:
            return None
        for fn in os.listdir(PPT_CACHE_DIR):
            if bid in fn and fn.endswith(".bento.html"):
                return os.path.join(PPT_CACHE_DIR, fn)
        return None

    # ══════════ Bento (단일 HTML 발표자료) ══════════
    # ★.pptx 는 그대로 둔다 — 회사에 pptx 로 내야 하는 자리가 있다.
    #   Bento 는 '받는 사람이 아무것도 설치 안 해도 되는' 기본 출력이다.
    @app.route("/api/ppt/bento", methods=["POST"])
    def api_ppt_bento():
        """MD 또는 outline → .bento.html 한 파일.

        body: {"md": "...", 또는 "outline": {...},
               "theme": "dark|light|corporate|hynix",
               "title": "...", "footer": "..."}
        """
        from demos_v1 import bento_builder as bb
        data = request.json or {}
        outline = data.get("outline")
        if not outline:
            md = (data.get("md") or "").strip()
            if not md:
                return jsonify({"error": "md 또는 outline 이 필요합니다."}), 400
            try:
                outline = parse_md_to_outline(md)
            except Exception as e:
                return jsonify({"error": f"MD 파싱 실패: {e}"}), 400
        slides = outline.get("slides") or []
        if not slides:
            return jsonify({"error": "슬라이드가 비어있습니다."}), 400

        meta = outline.get("meta") or {}
        title = (data.get("title") or meta.get("title") or "발표자료").strip()
        try:
            html, doc = bb.build(
                slides, title=title,
                theme=data.get("theme") or bb.DEFAULT_THEME,
                footer=(data.get("footer") or "").strip(),
            )
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": f"변환 실패: {e}"}), 500

        info = _save_bento(html, title)
        print(f"[ppt] Bento 생성: {info['filename']} · {len(doc['slides'])}장 · "
              f"{info['size']:,}바이트")
        return jsonify({
            "ok": True, "id": info["id"], "filename": info["filename"],
            "size": info["size"], "slide_count": len(doc["slides"]),
            "theme": data.get("theme") or bb.DEFAULT_THEME,
            "download_url": f"/api/ppt/bento/download/{info['id']}",
            "slides_summary": [
                {"type": s.get("type", "content"), "title": s.get("title", "")}
                for s in slides
            ],
        })

    @app.route("/api/ppt/bento/themes", methods=["GET"])
    def api_ppt_bento_themes():
        from demos_v1 import bento_builder as bb
        return jsonify({"default": bb.DEFAULT_THEME, "themes": [
            {"id": k, "background": v["background"], "accent": v["accent"]}
            for k, v in bb.THEMES.items()]})

    @app.route("/api/ppt/bento/download/<bid>", methods=["GET"])
    def api_ppt_bento_download(bid):
        path = _bento_path(bid)
        if not path or not os.path.exists(path):
            return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
        return send_file(path, mimetype="text/html", as_attachment=True,
                         download_name=os.path.basename(path))

    @app.route("/api/ppt/download/<ppt_id>", methods=["GET"])
    def api_ppt_download(ppt_id):
        """저장된 .pptx 다운로드."""
        path = get_pptx_path(ppt_id)
        if not path or not os.path.exists(path):
            return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
        return send_file(
            path,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            as_attachment=True,
            download_name=os.path.basename(path),
        )

    print("[ppt] 라우트 등록 완료 (bento, from-md, from-md-file, from-blocks, preview-outline, download)")
