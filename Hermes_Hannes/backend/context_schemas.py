"""
backend/context_schemas.py - 프로젝트 타입별 컨텍스트 스키마.

- SCHEMAS: 타입(ml/data/web/cli/automation/general) 별로
    - required: 필수 슬롯 키 목록
    - widgets:  슬롯 키 → 위젯 종류 (file / input / textarea)
    - json_shape: 파서가 만들어야 할 출력 JSON 모양 (LLM 프롬프트에 주입)
- system_prompt(project_type, dataset_meta): 파서용 system 프롬프트 합성.
- check_missing(project_type, slots, parsed): 파서 응답에서 빠진 필수 필드 판정.

UI(SLOT_TEMPLATES)와 동일 키를 사용. 키 변경 시 양쪽 동시 수정.
"""

SCHEMAS = {
    "ml": {
        "required": ["requirement", "dataset", "metric"],
        "widgets": {
            "requirement": "textarea",
            "dataset": "file",
            "metric": "input",
            "input_shape": "input",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "dataset": str|null, '
            '"metric": {"name": str, "target": float}|null, '
            '"input_shape": str|null, "constraints": [str], "success_criteria": [str]}'
        ),
    },
    "data": {
        "required": ["requirement", "dataset"],
        "widgets": {
            "requirement": "textarea",
            "dataset": "file",
            "group_by": "input",
            "output_format": "input",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "dataset": str|null, "group_by": [str], '
            '"output_format": str|null, "constraints": [str]}'
        ),
    },
    "web": {
        "required": ["requirement", "endpoints"],
        "widgets": {
            "requirement": "textarea",
            "endpoints": "textarea",
            "auth": "input",
            "schema_text": "textarea",
            "schema_file": "file",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "endpoints": [{"path": str, "method": str}], '
            '"auth": str|null, "request_schema": str|null, "response_schema": str|null}'
        ),
    },
    "cli": {
        "required": ["requirement", "args"],
        "widgets": {
            "requirement": "textarea",
            "args": "textarea",
            "io_format": "input",
            "example_input": "file",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "args": [{"flag": str, "type": str, "required": bool}], '
            '"stdin_format": str|null, "stdout_format": str|null}'
        ),
    },
    "automation": {
        "required": ["requirement", "trigger"],
        "widgets": {
            "requirement": "textarea",
            "trigger": "input",
            "target_system": "input",
            "schedule": "input",
            "config_file": "file",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "trigger": str, "target_system": str|null, '
            '"schedule": str|null, "actions": [str]}'
        ),
    },
    "general": {
        "required": ["requirement"],
        "widgets": {
            "requirement": "textarea",
            "freeform_note": "textarea",
            "attachments": "file",
        },
        "json_shape": (
            '{"intent": str, "inputs": [str], "outputs": [str], '
            '"constraints": [str], "success_criteria": [str]}'
        ),
    },
}


def get_schema(project_type):
    return SCHEMAS.get(project_type, SCHEMAS["general"])


def system_prompt(project_type, dataset_meta=None):
    s = get_schema(project_type)
    parts = [
        "당신은 사용자 요구사항을 구조화 JSON으로 변환하는 파서입니다.",
        f"프로젝트 타입: {project_type}",
        f"출력 JSON 스키마: {s['json_shape']}",
        "추가 필드:",
        f'  - missing_required: 비어있는 필수 키 배열 (필수 키: {s["required"]})',
        '  - inferred_from_freeform: [{"field": str, "value": any, "source": "freeform_note"}] — '
        'freeform_note에서 추론해 채운 필드 기록',
        "우선순위: 구조화 슬롯 값 > freeform_note 추론 > 빈 값.",
        "freeform_note에 단서가 있으면 적극적으로 슬롯을 채우세요.",
        "응답은 단일 JSON 객체. 코드펜스 ```json ... ``` 안에 출력.",
    ]
    if dataset_meta:
        parts.append(
            f"데이터셋 메타: columns={dataset_meta.get('columns')}, rows≈{dataset_meta.get('rows')}"
        )
    return "\n".join(parts)


def user_prompt(slots, dataset_meta=None):
    """슬롯값들을 LLM 입력 텍스트로 변환."""
    lines = ["[입력 슬롯]"]
    for k, v in slots.items():
        if v is None or v == "":
            continue
        lines.append(f"- {k}: {v}")
    if dataset_meta:
        lines.append("[데이터셋 파일 메타]")
        for k, v in dataset_meta.items():
            lines.append(f"- {k}: {v}")
    lines.append("\n위 정보를 위 JSON 스키마로 변환하세요.")
    return "\n".join(lines)


def check_missing(project_type, slots, parsed):
    """파서 응답이 missing_required를 안 줬을 때를 대비한 폴백 검증."""
    s = get_schema(project_type)
    missing = []
    for key in s["required"]:
        slot_val = slots.get(key)
        if slot_val not in (None, "", [], {}):
            continue
        # parsed에서 보조 키 매핑 — 슬롯 키와 JSON 키가 다를 수 있어 느슨 매칭
        if parsed.get(key) not in (None, "", [], {}):
            continue
        # ml의 metric → parsed.metric.target 류
        if key == "metric" and isinstance(parsed.get("metric"), dict):
            if parsed["metric"].get("target") is not None:
                continue
        if key == "endpoints" and parsed.get("endpoints"):
            continue
        if key == "args" and parsed.get("args"):
            continue
        missing.append(key)
    return missing
