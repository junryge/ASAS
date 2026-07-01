"""rag_server/chunker.py — 프론트매터 분리 + 마크다운 청킹.

demos_v1/knowledge.py 의 프론트매터 파싱 방식과 동일.
청킹: 헤더(#~###) 1차 → 문단(빈 줄) 2차 → hard split + overlap.
각 청크에 heading_path(예: "임계값 > SLA") 부여해 출처 맥락 유지.
"""
import re

_HEADER_RE = re.compile(r"^(#{1,4})\s+(.*)$")


def parse_frontmatter(content):
    """('---' 프론트매터, 본문) 분리 → (meta dict, body)."""
    meta = {}
    body = content or ""
    if body.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", body, re.DOTALL)
        if m:
            fm = m.group(1)
            body = body[m.end():]
            for line in fm.split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip('"').strip("'")
    return meta, body


def _hard_split(text, size, overlap):
    out = []
    i, n = 0, len(text)
    while i < n:
        out.append(text[i:i + size])
        if i + size >= n:
            break
        i += max(1, size - overlap)
    return out


def chunk_markdown(body, size=1000, overlap=180, min_size=200):
    """본문 → [{"heading": str, "text": str}] 리스트."""
    lines = (body or "").split("\n")
    # 1) 헤더 기준 섹션 분할 (heading_path 추적)
    sections = []
    stack = []          # (level, title)
    cur = {"heading": "", "lines": []}

    def _flush():
        txt = "\n".join(cur["lines"]).strip()
        if txt:
            sections.append({"heading": cur["heading"], "text": txt})

    for ln in lines:
        m = _HEADER_RE.match(ln.strip())
        if m:
            _flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            cur = {"heading": " > ".join(t for _, t in stack), "lines": []}
        else:
            cur["lines"].append(ln)
    _flush()
    if not sections:
        sections = [{"heading": "", "text": (body or "").strip()}]

    # 2) 섹션이 크면 문단/하드 분할 + overlap
    chunks = []
    for sec in sections:
        text = sec["text"]
        if len(text) <= size:
            chunks.append({"heading": sec["heading"], "text": text})
            continue
        # 문단(빈 줄) 경계로 누적
        paras = re.split(r"\n\s*\n", text)
        buf = ""
        for p in paras:
            p = p.strip()
            if not p:
                continue
            if len(p) > size:                      # 한 문단이 너무 큼 → 하드 분할
                if buf:
                    chunks.append({"heading": sec["heading"], "text": buf}); buf = ""
                for piece in _hard_split(p, size, overlap):
                    chunks.append({"heading": sec["heading"], "text": piece})
            elif len(buf) + len(p) + 2 <= size:
                buf = (buf + "\n\n" + p) if buf else p
            else:
                chunks.append({"heading": sec["heading"], "text": buf})
                buf = p
        if buf:
            chunks.append({"heading": sec["heading"], "text": buf})

    # 3) min_size 미만 조각은 앞 청크에 병합
    merged = []
    for c in chunks:
        if merged and len(c["text"]) < min_size and merged[-1]["heading"] == c["heading"] \
                and len(merged[-1]["text"]) + len(c["text"]) <= size + min_size:
            merged[-1]["text"] += "\n\n" + c["text"]
        else:
            merged.append(c)
    return merged
