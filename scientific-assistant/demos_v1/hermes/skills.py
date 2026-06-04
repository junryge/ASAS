"""
demos_v1/hermes/skills.py — 자기학습 개인 스킬 (생성/patch/회상)

- 개인 스킬: demos_data/agents/<user>/skills/<name>/SKILL.md  (공용 355+개와 동일 형식)
- 공용 스킬 경로 쓰기 차단 (개인 디렉토리 밖 거부)
- 이름 규칙: 클래스 수준만 (세션 산물/일회성 이름 거부)
- usage.json: {name: {use_count, last_used, state, pinned, created}}
- 회상: BM25 (개인 스킬 대상). 인덱스(이름+설명)만 주입, 본문은 매칭 시 로드
"""
from __future__ import annotations
import os
import re
import time
import math

from demos_v1.hermes import store

# 이름: 소문자/숫자/하이픈, 2~40자, 하이픈으로 끝/시작 금지
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# 세션 산물/일회성 이름 패턴 거부
_BAD_NAME_RE = re.compile(
    r"(오늘|today|temp|tmp|test|fix-?\d|수정|어제|에러|error-|bug-\d|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _skills_dir(user_id: str) -> str:
    d = os.path.join(store.user_dir(user_id), "skills")
    os.makedirs(d, exist_ok=True)
    return d


def _skill_md(user_id: str, name: str) -> str:
    return os.path.join(_skills_dir(user_id), name, "SKILL.md")


def _usage_path(user_id: str) -> str:
    return os.path.join(store.user_dir(user_id), "usage.json")


def _load_usage(user_id: str) -> dict:
    return store.read_json(_usage_path(user_id), {})


def _save_usage(user_id: str, usage: dict) -> None:
    store.write_json(_usage_path(user_id), usage)


def valid_name(name: str) -> tuple[bool, str]:
    name = (name or "").strip().lower()
    if not store.safe_id(name):
        return False, "잘못된 이름(경로 문자 포함)"
    if not _NAME_RE.match(name):
        return False, "이름은 소문자/숫자/하이픈만 (예: lpql-join-pattern)"
    if len(name) < 2 or len(name) > 40:
        return False, "이름 길이 2~40자"
    if _BAD_NAME_RE.search(name):
        return False, "일회성/세션 산물 이름 거부 — 재사용 가능한 클래스 이름으로"
    return True, name


def _frontmatter(name: str, when: str) -> str:
    desc = (when or name).replace("\n", " ").strip().strip('"')
    return f"---\nname: {name}\ndescription: {desc}\nsource: personal\n---\n\n"


def create(user_id: str, name: str, when: str, body: str) -> tuple[bool, str]:
    ok, res = valid_name(name)
    if not ok:
        return False, res
    name = res
    if store.looks_injected(body) or store.looks_injected(when):
        return False, "인젝션 의심 — 거부"
    path = _skill_md(user_id, name)
    if os.path.isfile(path):
        return False, f"이미 존재: {name} (patch 사용)"
    content = _frontmatter(name, when) + (body or "").strip() + "\n"
    store.atomic_write(path, content)
    usage = _load_usage(user_id)
    usage[name] = {"use_count": 0, "last_used": 0, "state": "active",
                   "pinned": False, "created": time.time()}
    _save_usage(user_id, usage)
    return True, f"스킬 생성: {name}"


def patch(user_id: str, name: str, find: str, replace: str) -> tuple[bool, str]:
    ok, res = valid_name(name)
    if not ok:
        return False, res
    name = res
    path = _skill_md(user_id, name)
    if not os.path.isfile(path):
        return False, f"스킬 없음: {name}"
    if not find:
        return False, "find 필요"
    if store.looks_injected(replace):
        return False, "인젝션 의심 — 거부"
    text = store.read_text(path)
    if find not in text:
        return False, f"패치 대상 못 찾음: {find[:40]!r}"
    text = text.replace(find, replace, 1)
    store.atomic_write(path, text)
    return True, f"스킬 패치: {name}"


def edit(user_id: str, name: str, when: str, body: str) -> tuple[bool, str]:
    ok, res = valid_name(name)
    if not ok:
        return False, res
    name = res
    path = _skill_md(user_id, name)
    if not os.path.isfile(path):
        return False, f"스킬 없음: {name}"
    if store.looks_injected(body):
        return False, "인젝션 의심 — 거부"
    store.atomic_write(path, _frontmatter(name, when) + (body or "").strip() + "\n")
    return True, f"스킬 교체: {name}"


def delete(user_id: str, name: str) -> tuple[bool, str]:
    ok, res = valid_name(name)
    if not ok:
        return False, res
    name = res
    sd = os.path.join(_skills_dir(user_id), name)
    if not os.path.isdir(sd):
        return False, f"스킬 없음: {name}"
    import shutil
    try:
        shutil.rmtree(sd)
    except OSError as e:
        return False, f"삭제 실패: {e}"
    usage = _load_usage(user_id)
    usage.pop(name, None)
    _save_usage(user_id, usage)
    return True, f"스킬 삭제: {name}"


def _parse_meta(path: str) -> tuple[str, str]:
    """SKILL.md frontmatter 에서 name, description."""
    text = store.read_text(path)
    name = desc = ""
    m = re.match(r"---\s*\n(.*?)\n---", text, re.DOTALL)
    if m:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        dm = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        if nm:
            name = nm.group(1).strip()
        if dm:
            desc = dm.group(1).strip()
    return name, desc


def list_skills(user_id: str, include_archived: bool = True) -> list[dict]:
    sd = _skills_dir(user_id)
    usage = _load_usage(user_id)
    out = []
    if not os.path.isdir(sd):
        return out
    for name in sorted(os.listdir(sd)):
        path = os.path.join(sd, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        u = usage.get(name, {})
        if not include_archived and u.get("state") == "archived":
            continue
        _n, desc = _parse_meta(path)
        out.append({
            "name": name,
            "description": desc,
            "use_count": u.get("use_count", 0),
            "last_used": u.get("last_used", 0),
            "state": u.get("state", "active"),
            "pinned": u.get("pinned", False),
        })
    return out


def index_text(user_id: str) -> str:
    """시스템 프롬프트 주입용 — 개인 스킬 인덱스(이름+설명)만. 본문 X."""
    items = [s for s in list_skills(user_id) if s["state"] != "archived"]
    if not items:
        return ""
    lines = "\n".join(f"- {s['name']}: {s['description']}" for s in items)
    return "=== 내 개인 스킬 (필요 시 본문 요청) ===\n" + lines


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[가-힣]{2,}|[a-z0-9_]{2,}", (text or "").lower())


def recall(user_id: str, query: str, top_k: int = 2) -> list[dict]:
    """BM25 로 개인 스킬 검색 → 본문 포함 반환. 회상 시 usage 갱신."""
    items = [s for s in list_skills(user_id) if s["state"] != "archived"]
    if not items or not (query or "").strip():
        return []
    docs = []
    for s in items:
        path = _skill_md(user_id, s["name"])
        docs.append(_tokenize(s["name"] + " " + s["description"] + " " + store.read_text(path)))
    q_terms = _tokenize(query)
    if not q_terms:
        return []
    N = len(docs)
    avgdl = sum(len(d) for d in docs) / max(1, N)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    k1, b = 1.5, 0.75
    scored = []
    for i, d in enumerate(docs):
        tf: dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        dl = len(d) or 1
        for t in q_terms:
            if t not in tf:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        scored.append((s, i))
    scored.sort(reverse=True)
    usage = _load_usage(user_id)
    out = []
    for s, i in scored[:top_k]:
        if s <= 0:
            break
        name = items[i]["name"]
        out.append({"name": name, "description": items[i]["description"],
                    "score": round(s, 3), "body": store.read_text(_skill_md(user_id, name))})
        u = usage.setdefault(name, {"use_count": 0, "last_used": 0, "state": "active", "pinned": False})
        u["use_count"] = u.get("use_count", 0) + 1
        u["last_used"] = time.time()
    if out:
        _save_usage(user_id, usage)
    return out


def set_pinned(user_id: str, name: str, pinned: bool) -> bool:
    usage = _load_usage(user_id)
    if name not in usage:
        return False
    usage[name]["pinned"] = bool(pinned)
    _save_usage(user_id, usage)
    return True
