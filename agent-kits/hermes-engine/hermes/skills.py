"""
hermes/skills.py — 자기학습 개인 스킬 (생성/patch/회상)

- 개인 스킬: <data>/agents/<user>/skills/<name>/SKILL.md
- 이름 규칙(클래스 수준만), 경로 차단
- usage.json, BM25 회상 (인덱스만 주입, 본문은 매칭 시)
"""
from __future__ import annotations
import os
import re
import time
import math

from . import store

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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


def _save_usage(user_id: str, u: dict) -> None:
    store.write_json(_usage_path(user_id), u)


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


def _fm(name: str, when: str) -> str:
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
    store.atomic_write(path, _fm(name, when) + (body or "").strip() + "\n")
    u = _load_usage(user_id)
    u[name] = {"use_count": 0, "last_used": 0, "state": "active", "pinned": False, "created": time.time()}
    _save_usage(user_id, u)
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
    store.atomic_write(path, text.replace(find, replace, 1))
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
    store.atomic_write(path, _fm(name, when) + (body or "").strip() + "\n")
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
    u = _load_usage(user_id)
    u.pop(name, None)
    _save_usage(user_id, u)
    return True, f"스킬 삭제: {name}"


def _meta(path: str) -> tuple[str, str]:
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
    u = _load_usage(user_id)
    out = []
    for name in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
        path = os.path.join(sd, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        info = u.get(name, {})
        if not include_archived and info.get("state") == "archived":
            continue
        _n, desc = _meta(path)
        out.append({"name": name, "description": desc,
                    "use_count": info.get("use_count", 0), "last_used": info.get("last_used", 0),
                    "state": info.get("state", "active"), "pinned": info.get("pinned", False)})
    return out


def index_text(user_id: str) -> str:
    items = [s for s in list_skills(user_id) if s["state"] != "archived"]
    if not items:
        return ""
    return "=== 내 개인 스킬 (필요 시 본문 요청) ===\n" + \
        "\n".join(f"- {s['name']}: {s['description']}" for s in items)


def _tok(text: str) -> list[str]:
    return re.findall(r"[가-힣]{2,}|[a-z0-9_]{2,}", (text or "").lower())


def recall(user_id: str, query: str, top_k: int = 2) -> list[dict]:
    items = [s for s in list_skills(user_id) if s["state"] != "archived"]
    q_terms = _tok(query)
    if not items or not q_terms:
        return []
    docs = [_tok(s["name"] + " " + s["description"] + " " + store.read_text(_skill_md(user_id, s["name"])))
            for s in items]
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
        s, dl = 0.0, len(d) or 1
        for t in q_terms:
            if t in tf:
                idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
                s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        scored.append((s, i))
    scored.sort(reverse=True)
    u = _load_usage(user_id)
    out = []
    for s, i in scored[:top_k]:
        if s <= 0:
            break
        name = items[i]["name"]
        out.append({"name": name, "description": items[i]["description"], "score": round(s, 3),
                    "body": store.read_text(_skill_md(user_id, name))})
        info = u.setdefault(name, {"use_count": 0, "last_used": 0, "state": "active", "pinned": False})
        info["use_count"] = info.get("use_count", 0) + 1
        info["last_used"] = time.time()
    if out:
        _save_usage(user_id, u)
    return out


def set_pinned(user_id: str, name: str, pinned: bool) -> bool:
    u = _load_usage(user_id)
    if name not in u:
        return False
    u[name]["pinned"] = bool(pinned)
    _save_usage(user_id, u)
    return True
