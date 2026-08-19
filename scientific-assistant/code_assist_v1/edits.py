"""code_assist_v1/edits.py — 모델이 내놓은 수정을 실제 파일에 반영한다.

왜 이게 있나
    코딩 '에이전트' 인데 읽기만 됐다. 모델이 코드를 뱉으면 사람이 눈으로
    골라 손으로 붙여 넣었다 — 그건 채팅이다. 읽기(첨부) → 제안 → 적용까지
    돌아야 에이전트다.

무엇을 조심했나
    ‼️모델 출력은 못 믿는다. 경로가 워크스페이스 밖을 가리킬 수도 있고,
      SEARCH 가 원본과 미묘하게 다를 수도 있고, 여러 군데에 걸릴 수도 있다.
      **애매하면 적용하지 않는다.** 엉뚱한 자리를 고쳐 놓는 것보다 "못
      하겠다" 가 낫다 — 사람이 알아채지 못하는 손상이 제일 나쁘다.
"""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field

# ```edit:경로 ... ``` / ```write:경로 ... ```
_BLOCK = re.compile(
    r"^[ \t]*```[ \t]*(edit|write)[ \t]*:[ \t]*(?P<path>[^\n`]+?)[ \t]*\n"
    r"(?P<body>.*?)"
    r"^[ \t]*```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_SR = re.compile(
    r"^<{5,9} SEARCH[ \t]*\n(?P<search>.*?)"
    r"^={5,9}[ \t]*\n(?P<replace>.*?)"
    r"^>{5,9} REPLACE[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Edit:
    kind: str                  # 'edit' | 'write'
    path: str
    search: str = ""
    replace: str = ""
    content: str = ""

    # 적용 결과
    ok: bool = False
    reason: str = ""
    diff: str = ""


@dataclass
class ApplyResult:
    edits: list[Edit] = field(default_factory=list)

    @property
    def applied(self) -> int:
        return sum(1 for e in self.edits if e.ok)

    @property
    def failed(self) -> int:
        return sum(1 for e in self.edits if not e.ok)

    def to_json(self) -> dict:
        return {
            "applied": self.applied,
            "failed": self.failed,
            "edits": [
                {"kind": e.kind, "path": e.path, "ok": e.ok,
                 "reason": e.reason, "diff": e.diff}
                for e in self.edits
            ],
        }


def parse_edits(text: str) -> list[Edit]:
    """모델 답변에서 수정 블록을 뽑는다. 형식이 어긋나면 그냥 안 뽑는다."""
    out: list[Edit] = []
    for m in _BLOCK.finditer(text or ""):
        kind = m.group(1)
        path = m.group("path").strip().strip("`").strip()
        body = m.group("body")
        if not path:
            continue
        if kind == "write":
            out.append(Edit(kind="write", path=path, content=body))
            continue
        found = list(_SR.finditer(body))
        if not found:
            # edit 라고 해 놓고 SEARCH/REPLACE 가 없다 — 통짜로 덮어쓰는 건
            # 위험하다(모델이 파일 일부만 적어 놓고 전체인 척할 수 있다).
            out.append(Edit(kind="edit", path=path,
                            ok=False, reason="SEARCH/REPLACE 형식이 아니다"))
            continue
        for sr in found:
            out.append(Edit(kind="edit", path=path,
                            search=sr.group("search"),
                            replace=sr.group("replace")))
    return out


def _diff(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}", n=2,
    ))


def _norm(s: str) -> str:
    """줄 끝 공백·개행 방식만 맞춘다 (탭/들여쓰기는 건드리지 않는다)."""
    return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n"))


def _hits(haystack: str, needle: str) -> list[int]:
    """**줄 단위로** 딱 맞는 자리들. 줄 한가운데 걸리는 건 세지 않는다.

    ★그냥 부분 문자열로 찾으면 안 된다. 8칸 들여쓴 '        deep()' 안에
      4칸 들여쓴 '    deep()' 이 들어 있다 — 파이썬에서 이 둘은 뜻이 다른
      코드인데 매칭돼 버린다. 실제로 그렇게 통과했다.
      시작은 줄머리여야 하고, 끝도 줄끝이어야 한다.
    """
    if not needle:
        return []
    out, i = [], 0
    while True:
        i = haystack.find(needle, i)
        if i < 0:
            return out
        starts_line = i == 0 or haystack[i - 1] == "\n"
        end = i + len(needle)
        ends_line = (needle.endswith("\n") or end == len(haystack)
                     or haystack[end] == "\n")
        if starts_line and ends_line:
            out.append(i)
        i += 1


def _find_once(haystack: str, needle: str) -> tuple[int, str] | tuple[None, str]:
    """딱 한 번 나오는 자리를 찾는다. 없거나 여러 번이면 거절 사유를 준다.

    ★'여러 번 나오면 첫 번째' 로 하고 싶은 유혹이 있는데, 그러면 모델이
      짧은 SEARCH 를 줬을 때 엉뚱한 자리를 고친다. 사람이 알아채기 힘든
      손상이라 거절이 맞다.
    """
    hits = _hits(haystack, needle)
    if len(hits) == 1:
        return hits[0], ""
    if len(hits) > 1:
        return None, f"SEARCH 가 {len(hits)}군데에 걸린다 — 더 길게 잡아야 한다"

    # 줄 끝 공백/개행 차이만 다른 경우는 맞춰서 한 번 더
    # (앞쪽 들여쓰기는 건드리지 않는다 — 그건 뜻이 다른 코드다)
    hn, nn = _norm(haystack), _norm(needle)
    hits2 = _hits(hn, nn)
    if len(hits2) == 1:
        return -1, "ws"          # 정규화본에서 찾음 (호출부가 처리)
    if len(hits2) > 1:
        return None, f"SEARCH 가 {len(hits2)}군데에 걸린다 — 더 길게 잡아야 한다"
    return None, "SEARCH 가 파일 내용과 다르다"


def apply_edits(
    edits: list[Edit],
    root: str,
    safe_join,
    dry_run: bool = False,
) -> ApplyResult:
    """수정들을 워크스페이스에 반영한다.

    safe_join(root, *parts) -> str | None : 워크스페이스 밖이면 None.
    dry_run 이면 파일을 건드리지 않고 diff 만 만든다(미리보기).
    """
    res = ApplyResult(edits=list(edits))
    # 같은 파일에 여러 수정이 오면 순서대로 쌓아 올린다
    buf: dict[str, str] = {}

    for e in res.edits:
        if e.reason and not e.ok:      # 파싱 단계에서 이미 거절됨
            continue

        rel = e.path.strip().replace("\\", "/").lstrip("/")
        parts = [p for p in rel.split("/") if p and p != "."]
        if ".." in parts or not parts:
            e.reason = "워크스페이스 밖 경로"
            continue
        full = safe_join(root, *parts)
        if not full:
            e.reason = "워크스페이스 밖 경로"
            continue
        rel = "/".join(parts)

        if rel in buf:
            before = buf[rel]
        elif os.path.isfile(full):
            try:
                with open(full, "r", encoding="utf-8") as f:
                    before = f.read()
            except Exception as ex:
                e.reason = f"읽기 실패: {ex}"
                continue
        else:
            before = None          # 새 파일

        if e.kind == "write":
            after = e.content
        else:
            if before is None:
                e.reason = "없는 파일은 edit 할 수 없다 (write 를 쓰라)"
                continue
            idx, why = _find_once(before, e.search)
            if idx is None:
                e.reason = why
                continue
            if why == "ws":
                # 줄 끝 공백만 다른 경우 — 정규화본에서 바꾼 뒤 되돌린다
                after = _norm(before).replace(_norm(e.search), _norm(e.replace), 1)
            else:
                after = before[:idx] + e.replace + before[idx + len(e.search):]

        if before is not None and after == before:
            e.ok, e.reason = True, "바뀐 것 없음"
            continue

        e.diff = _diff(rel, before or "", after)
        buf[rel] = after
        e.ok = True
        e.reason = "미리보기" if dry_run else ("새 파일" if before is None else "적용")

    if not dry_run:
        changed = []
        for rel, text in buf.items():
            full = safe_join(root, *rel.split("/"))
            if not full:
                continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            new_file = not os.path.isfile(full)
            with open(full, "w", encoding="utf-8") as f:
                f.write(text)
            changed.append({"path": rel, "new": new_file})
        if changed:
            record_changes(root, changed, [e for e in res.edits if e.ok])

    return res


# ── 무엇이 바뀌었나 ──
# ★프로젝트를 통째로 다시 받는 건 낭비다. 300개짜리 프로젝트에서 두 파일을
#   고쳤으면 그 둘만 받으면 된다. 그러려면 '무엇이 언제 바뀌었나' 를 알아야
#   하는데, 파일 mtime 만으로는 '내가 고친 것' 과 '올릴 때부터 있던 것' 을
#   구분할 수 없다. 그래서 적용할 때 직접 남긴다.
CHANGES_FILE = ".edits.json"
_MAX_CHANGES = 500


def changes_path(root: str) -> str:
    return os.path.join(root, CHANGES_FILE)


def read_changes(root: str) -> list[dict]:
    p = changes_path(root)
    if not os.path.isfile(p):
        return []
    try:
        import json
        with open(p, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def record_changes(root: str, changed: list[dict], edits: list) -> None:
    """방금 적용한 수정을 기록. 실패해도 적용 자체를 되돌리지는 않는다."""
    import json
    from datetime import datetime
    try:
        log = read_changes(root)
        stamp = datetime.now().isoformat(timespec="seconds")
        by_path = {}
        for e in edits:
            by_path.setdefault(e.path, []).append(e.kind)
        for c in changed:
            log.append({
                "path": c["path"],
                "at": stamp,
                "kind": "새 파일" if c["new"] else "수정",
                "ops": by_path.get(c["path"], []),
            })
        if len(log) > _MAX_CHANGES:
            log = log[-_MAX_CHANGES:]
        tmp = changes_path(root) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)
        os.replace(tmp, changes_path(root))
    except Exception as e:
        print(f"[edits] 변경 기록 실패(적용은 됨): {e}")


def changed_files(root: str) -> list[dict]:
    """지금까지 바뀐 파일 목록 (같은 파일은 마지막 것으로 합친다).

    ★같은 파일을 다섯 번 고쳤다고 목록에 다섯 번 나오면 못 읽는다.
      대신 몇 번 고쳤는지를 센다.
    """
    seen: dict[str, dict] = {}
    for r in read_changes(root):
        p = r.get("path")
        if not p:
            continue
        cur = seen.get(p)
        if cur is None:
            seen[p] = {**r, "count": 1}
        else:
            cur["count"] += 1
            cur["at"] = r.get("at") or cur["at"]
            if r.get("kind") == "새 파일":
                cur["kind"] = "새 파일"
    out = list(seen.values())
    # 존재하지 않는 파일(지운 것)은 뺀다 — 받을 게 없다
    out = [r for r in out if os.path.isfile(os.path.join(root, *r["path"].split("/")))]
    out.sort(key=lambda r: r.get("at") or "", reverse=True)
    return out
