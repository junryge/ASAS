"""
backend/harness_rules.py - 하네스 L1 규칙기반 검증.

LLM 호출 없음. AST 파싱 + 금지 패턴 + import 화이트리스트.
모드(API/GGUF) 무관 — 코드 정적 분석만 수행.
"""
import ast
import re

# 금지 호출 (보안/안정성)
_FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}

# 평문 secret 의심 정규식
_SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]"), "hardcoded-secret"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws-access-key"),
]

# import 화이트리스트 — ML/데이터 일반 라이브러리. 없는 건 경고(에러 X)
_IMPORT_WHITELIST = {
    "os", "sys", "json", "re", "math", "time", "random", "pathlib",
    "collections", "itertools", "functools", "typing", "dataclasses",
    "numpy", "pandas", "scipy", "sklearn",
    "torch", "torchvision", "torchaudio",
    "tensorflow", "keras", "jax", "flax",
    "matplotlib", "seaborn", "plotly",
    "csv", "io", "argparse", "logging",
}


def _check_syntax(code):
    try:
        tree = ast.parse(code)
        return tree, None
    except SyntaxError as e:
        return None, {"line": e.lineno or 0, "code": "syntax-error", "msg": str(e)}


def _check_forbidden(tree):
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _FORBIDDEN_CALLS:
                issues.append({
                    "line": getattr(node, "lineno", 0),
                    "code": "forbidden-call",
                    "msg": f"금지된 호출: {name}()",
                })
    return issues


def _check_secrets(code):
    issues = []
    for i, line in enumerate(code.splitlines(), start=1):
        for pat, label in _SECRET_PATTERNS:
            if pat.search(line):
                issues.append({"line": i, "code": label, "msg": f"하드코딩된 시크릿 의심: {label}"})
    return issues


def _check_imports(tree):
    warnings = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [n.name.split(".")[0] for n in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [node.module.split(".")[0]]
        for nm in names:
            if nm and nm not in _IMPORT_WHITELIST:
                warnings.append({
                    "line": getattr(node, "lineno", 0),
                    "code": "unknown-import",
                    "msg": f"화이트리스트 외 import: {nm}",
                })
    return warnings


def run(code):
    """L1 검증 실행.

    Returns: {
        "ok": bool,               # 치명적 에러 없음
        "issues": [{line, code, msg}],   # 치명적
        "warnings": [{line, code, msg}], # 비치명적
    }
    """
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "issues": [{"line": 0, "code": "empty", "msg": "코드 비어있음"}], "warnings": []}

    tree, syn_err = _check_syntax(code)
    if syn_err:
        return {"ok": False, "issues": [syn_err], "warnings": []}

    issues = []
    issues.extend(_check_forbidden(tree))
    issues.extend(_check_secrets(code))
    warnings = _check_imports(tree)

    return {"ok": len(issues) == 0, "issues": issues, "warnings": warnings}
