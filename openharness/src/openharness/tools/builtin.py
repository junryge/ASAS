"""Built-in tools for the harness.

Provides essential tools: file read/write, shell exec, search, web fetch.
"""

from __future__ import annotations

import os
import subprocess
import glob as glob_mod
from pathlib import Path

from ..engine.models import Tool
from ..engine.registry import ToolRegistry


# ── File Tools ──

def _read_file(payload: str) -> str:
    """Read a file and return its contents."""
    path = payload.strip()
    if not path:
        return "Error: no file path provided"
    p = Path(path).expanduser()
    if not p.is_file():
        return f"Error: file not found: {path}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        if len(lines) > 200:
            return "\n".join(lines[:200]) + f"\n... ({len(lines)} total lines)"
        return content
    except OSError as e:
        return f"Error reading file: {e}"


def _write_file(payload: str) -> str:
    """Write content to a file. Format: filepath\\n---\\ncontent"""
    parts = payload.split("\n---\n", 1)
    if len(parts) < 2:
        return "Error: format is 'filepath\\n---\\ncontent'"
    filepath, content = parts[0].strip(), parts[1]
    p = Path(filepath).expanduser()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {filepath}"
    except OSError as e:
        return f"Error writing file: {e}"


def _list_dir(payload: str) -> str:
    """List directory contents."""
    path = (payload.strip() or ".").strip()
    p = Path(path).expanduser()
    if not p.is_dir():
        return f"Error: not a directory: {path}"
    entries = sorted(p.iterdir())
    lines = []
    for e in entries[:100]:
        prefix = "d " if e.is_dir() else "f "
        lines.append(f"{prefix}{e.name}")
    if len(entries) > 100:
        lines.append(f"... ({len(entries)} total)")
    return "\n".join(lines) if lines else "(empty directory)"


# ── Search Tools ──

def _glob_search(payload: str) -> str:
    """Search for files matching a glob pattern."""
    pattern = payload.strip()
    if not pattern:
        return "Error: no pattern provided"
    matches = sorted(glob_mod.glob(pattern, recursive=True))
    if not matches:
        return f"No files matching: {pattern}"
    result = "\n".join(matches[:50])
    if len(matches) > 50:
        result += f"\n... ({len(matches)} total matches)"
    return result


def _grep_search(payload: str) -> str:
    """Search file contents for a pattern. Format: pattern [path]

    Pure Python implementation (works on Windows/Linux/Mac).
    """
    parts = payload.strip().split(None, 1)
    if not parts:
        return "Error: no search pattern"
    pattern = parts[0]
    search_path = parts[1] if len(parts) > 1 else "."

    import re
    EXTENSIONS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".js", ".ts", ".html", ".css"}
    matched_files: list[str] = []

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    root = Path(search_path).expanduser()
    if not root.exists():
        return f"Error: path not found: {search_path}"

    try:
        for fpath in root.rglob("*"):
            if len(matched_files) >= 50:
                break
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() not in EXTENSIONS:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                if regex.search(text):
                    matched_files.append(str(fpath))
            except OSError:
                continue
    except Exception:
        return f"Search error for: {pattern}"

    if matched_files:
        result = f"Found in {len(matched_files)} files:\n" + "\n".join(matched_files[:30])
        if len(matched_files) > 30:
            result += f"\n... ({len(matched_files)} total)"
        return result
    return f"No matches for: {pattern}"


# ── Shell Tool ──

def _shell_exec(payload: str) -> str:
    """Execute a shell command and return output."""
    cmd = payload.strip()
    if not cmd:
        return "Error: no command provided"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            cwd=os.getcwd(),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        return output[:5000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (30s)"


# ── Utility Tools ──

def _echo(payload: str) -> str:
    """Echo input back."""
    return payload


def _word_count(payload: str) -> str:
    """Count words, lines, and characters in input."""
    words = len(payload.split())
    lines = payload.count("\n") + (1 if payload else 0)
    chars = len(payload)
    return f"Words: {words}, Lines: {lines}, Characters: {chars}"


# ── Registration ──

BUILTIN_TOOLS = [
    Tool("read", "Read a file and return its contents", _read_file, "file"),
    Tool("write", "Write content to a file (filepath\\n---\\ncontent)", _write_file, "file"),
    Tool("ls", "List directory contents", _list_dir, "file"),
    Tool("glob", "Search for files matching a glob pattern", _glob_search, "search"),
    Tool("grep", "Search file contents for a pattern", _grep_search, "search"),
    Tool("shell", "Execute a shell command", _shell_exec, "shell", requires_permission=True),
    Tool("echo", "Echo input back", _echo, "utility"),
    Tool("word-count", "Count words, lines, and characters", _word_count, "utility"),
]


def register_builtin_tools(registry: ToolRegistry) -> int:
    """Register all built-in tools. Returns count of registered tools."""
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    return len(BUILTIN_TOOLS)
