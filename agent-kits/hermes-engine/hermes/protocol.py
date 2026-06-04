"""
hermes/protocol.py — 텍스트 프로토콜 파싱 (네이티브 툴콜 대체)

모델 답변 안의 펜스 블록을 파싱한다.
  ```hermes:memory   store/action/target/text
  ```hermes:skill    action/name/when/body (or find/replace)
  ```hermes:ask      - 질문들

parse_blocks(text) -> (clean_text, [block, ...])
"""
from __future__ import annotations
import re

_FENCE_RE = re.compile(
    r"```[ \t]*hermes:(memory|skill|ask)[ \t]*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _parse_kv(body: str) -> dict:
    out: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    multiline_keys = ("body", "text")
    while i < len(lines):
        m = re.match(r"^([a-zA-Z_]+)\s*:\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1).strip().lower(), m.group(2)
        if key in multiline_keys:
            if val.strip() in ("", "|", "|-", ">"):
                collected = lines[i + 1:]
                stripped = [c[2:] if c.startswith("  ") else c for c in collected]
                out[key] = "\n".join(stripped).strip()
                break
            out[key] = val.strip()
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
            qs.append(s)
    return [q for q in qs if q][:5]


def parse_blocks(text: str) -> tuple[str, list[dict]]:
    if not text:
        return "", []
    blocks: list[dict] = []

    def _repl(m):
        kind, body = m.group(1).lower(), m.group(2)
        if kind == "memory":
            kv = _parse_kv(body)
            blocks.append({"kind": "memory",
                           "store": (kv.get("store") or "memory").strip().lower(),
                           "action": (kv.get("action") or "add").strip().lower(),
                           "target": kv.get("target", "").strip(),
                           "text": kv.get("text", "").strip()})
        elif kind == "skill":
            kv = _parse_kv(body)
            blocks.append({"kind": "skill",
                           "action": (kv.get("action") or "create").strip().lower(),
                           "name": (kv.get("name") or "").strip(),
                           "when": (kv.get("when") or "").strip(),
                           "body": kv.get("body", "").strip(),
                           "find": kv.get("find", ""),
                           "replace": kv.get("replace", "")})
        elif kind == "ask":
            blocks.append({"kind": "ask", "questions": _parse_ask(body)})
        return ""

    clean = _FENCE_RE.sub(_repl, text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, blocks
