"""
demos_v1/hermes/protocol.py — 텍스트 프로토콜 파싱 (네이티브 툴콜 대체)

모델이 답변 안에 펜스 블록을 출력하면 파싱한다.

지원 블록 (펜스 언어 태그로 구분):
  ```hermes:memory   store/action/target/text  (YAML 유사 key: value, text 는 멀티라인)
  ```hermes:skill    action/name/when/body
  ```hermes:ask      - 질문1 / - 질문2  (불릿 리스트)

parse_blocks(text) -> (clean_text, [block, ...])
  - clean_text: 블록을 제거한 사용자 표시용 본문
  - block: {"kind": "memory|skill|ask", ...필드}
"""
from __future__ import annotations
import re

# ```hermes:<kind>\n ... \n```
_FENCE_RE = re.compile(
    r"```[ \t]*hermes:(memory|skill|ask)[ \t]*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _parse_kv(body: str) -> dict:
    """key: value 파싱. 'body:' 또는 'text:' 는 그 줄 이후 전체를 멀티라인으로."""
    out: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    multiline_keys = ("body", "text")
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-zA-Z_]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key = m.group(1).strip().lower()
        val = m.group(2)
        if key in multiline_keys:
            # 'key: |' 또는 'key:' 면 다음 줄들을 끝까지 수집
            rest = val.strip()
            if rest in ("", "|", "|-", ">"):
                collected = lines[i + 1:]
                # 공통 들여쓰기 제거
                stripped = [c[2:] if c.startswith("  ") else c for c in collected]
                out[key] = "\n".join(stripped).strip()
                break
            else:
                out[key] = rest
                i += 1
        else:
            out[key] = val.strip()
            i += 1
    return out


def _parse_ask(body: str) -> list[str]:
    qs = []
    for line in body.splitlines():
        s = line.strip()
        m = re.match(r"^[-*•]\s+(.+)$", s)
        if m:
            qs.append(m.group(1).strip())
        elif s and not qs:
            # 불릿 없이 한 줄만 적은 경우도 허용
            qs.append(s)
    return [q for q in qs if q][:5]


def parse_blocks(text: str) -> tuple[str, list[dict]]:
    if not text:
        return "", []
    blocks: list[dict] = []

    def _repl(m):
        kind = m.group(1).lower()
        body = m.group(2)
        if kind == "memory":
            kv = _parse_kv(body)
            blocks.append({
                "kind": "memory",
                "store": (kv.get("store") or "memory").strip().lower(),
                "action": (kv.get("action") or "add").strip().lower(),
                "target": kv.get("target", "").strip(),
                "text": kv.get("text", "").strip(),
            })
        elif kind == "skill":
            kv = _parse_kv(body)
            blocks.append({
                "kind": "skill",
                "action": (kv.get("action") or "create").strip().lower(),
                "name": (kv.get("name") or "").strip(),
                "when": (kv.get("when") or "").strip(),
                "body": kv.get("body", "").strip(),
                "find": kv.get("find", ""),
                "replace": kv.get("replace", ""),
            })
        elif kind == "ask":
            blocks.append({"kind": "ask", "questions": _parse_ask(body)})
        return ""  # 본문에서 블록 제거

    clean = _FENCE_RE.sub(_repl, text)
    # 블록 제거로 생긴 빈 줄 정리
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, blocks
