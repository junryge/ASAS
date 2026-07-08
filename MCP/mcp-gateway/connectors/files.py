# -*- coding: utf-8 -*-
"""파일 커넥터 — config.yaml files.roots 별칭 밑으로만 접근 허용 (경로 탈출 차단)."""
import logging
from pathlib import Path

log = logging.getLogger("gateway.files")


def register(mcp, cfg: dict) -> None:
    fc = cfg.get("files", {}) or {}
    roots = {alias: Path(p).resolve() for alias, p in (fc.get("roots") or {}).items()}
    max_read = int(fc.get("max_read_bytes", 1_048_576))

    def _resolve(root: str, rel: str) -> Path | dict:
        if root not in roots:
            return {"error": f"등록되지 않은 root: {root}", "allowed": list(roots)}
        p = (roots[root] / rel.lstrip("/\\")).resolve()
        try:
            p.relative_to(roots[root])
        except ValueError:
            return {"error": "root 밖 경로 접근 차단됨"}
        return p

    @mcp.tool()
    def fs_roots() -> dict:
        """접근 가능한 파일 root 별칭 목록을 반환한다."""
        return {a: str(p) for a, p in roots.items()}

    @mcp.tool()
    def fs_list(root: str, path: str = "") -> dict:
        """root 별칭 아래 디렉터리 내용을 나열한다."""
        p = _resolve(root, path)
        if isinstance(p, dict):
            return p
        if not p.is_dir():
            return {"error": f"디렉터리 아님: {path}"}
        items = []
        for c in sorted(p.iterdir()):
            items.append({
                "name": c.name,
                "type": "dir" if c.is_dir() else "file",
                "size": c.stat().st_size if c.is_file() else None,
            })
        return {"path": str(p), "items": items}

    @mcp.tool()
    def fs_read(root: str, path: str) -> dict:
        """root 별칭 아래 텍스트 파일을 읽는다 (max_read_bytes 제한)."""
        p = _resolve(root, path)
        if isinstance(p, dict):
            return p
        if not p.is_file():
            return {"error": f"파일 없음: {path}"}
        if p.stat().st_size > max_read:
            return {"error": f"파일이 {max_read} bytes 초과"}
        try:
            return {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")}
        except OSError as e:
            return {"error": str(e)}

    @mcp.tool()
    def fs_write(root: str, path: str, content: str) -> dict:
        """root 별칭 아래에 텍스트 파일을 쓴다 (생성/덮어쓰기). 감사 로그 기록됨."""
        p = _resolve(root, path)
        if isinstance(p, dict):
            return p
        log.info("fs_write %s (%d bytes)", p, len(content))
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"path": str(p), "written": len(content)}
        except OSError as e:
            return {"error": str(e)}

    @mcp.tool()
    def fs_search(root: str, pattern: str, path: str = "") -> dict:
        """root 아래에서 파일명 glob 패턴으로 검색한다 (예: *.csv, **/*.log)."""
        p = _resolve(root, path)
        if isinstance(p, dict):
            return p
        if not p.is_dir():
            return {"error": f"디렉터리 아님: {path}"}
        hits = [str(h.relative_to(roots[root])) for h in list(p.glob(pattern))[:200]]
        return {"matches": hits, "count": len(hits)}
