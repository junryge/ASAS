"""
hermes/memory.py — 장기 메모리 (선언적 사실)

- MEMORY.md(환경/프로젝트 사실), USER.md(사용자 선호). 항목 구분자 "§"
- add / replace / remove / read  (replace/remove 는 짧은 고유 부분문자열 target)
- 인젝션 차단, 저장소당 상한, snapshot() = 시스템 프롬프트 주입용
"""
from __future__ import annotations
import os

from . import store

_STORES = {
    "memory": ("MEMORY.md", "기억된 사실 (환경·프로젝트)"),
    "user":   ("USER.md",   "사용자 선호"),
}


def _path(user_id: str, store_name: str) -> str:
    return os.path.join(store.user_dir(user_id), _STORES[store_name][0])


def _valid(store_name: str) -> bool:
    return store_name in _STORES


def read_items(user_id: str, store_name: str) -> list[str]:
    if not _valid(store_name):
        return []
    raw = store.read_text(_path(user_id, store_name))
    return [s.strip() for s in raw.split(store.ITEM_SEP) if s.strip()]


def _save(user_id: str, store_name: str, items: list[str]) -> None:
    body = ("\n" + store.ITEM_SEP + "\n").join(items)
    store.atomic_write(_path(user_id, store_name), body)


def add(user_id: str, store_name: str, text: str) -> tuple[bool, str]:
    text = (text or "").strip()
    if not _valid(store_name):
        return False, f"알 수 없는 저장소: {store_name}"
    if not text:
        return False, "빈 내용"
    if store.looks_injected(text):
        return False, "인젝션 의심 패턴 — 저장 거부"
    items = read_items(user_id, store_name)
    if text in items:
        return True, "이미 존재 (스킵)"
    new_items = items + [text]
    if len(store.ITEM_SEP.join(new_items)) > store.MAX_STORE_CHARS:
        return False, f"{store_name} 저장소 {store.MAX_STORE_CHARS}자 초과 — 거부"
    _save(user_id, store_name, new_items)
    return True, "저장됨"


def replace(user_id: str, store_name: str, target: str, text: str) -> tuple[bool, str]:
    target, text = (target or "").strip(), (text or "").strip()
    if not _valid(store_name):
        return False, f"알 수 없는 저장소: {store_name}"
    if not target or not text:
        return False, "target/text 필요"
    if store.looks_injected(text):
        return False, "인젝션 의심 패턴 — 거부"
    items = read_items(user_id, store_name)
    idxs = [i for i, it in enumerate(items) if target in it]
    if not idxs:
        return False, f"대상 못 찾음: {target!r}"
    if len(idxs) > 1:
        return False, f"대상 모호({len(idxs)}개): {target!r}"
    items[idxs[0]] = text
    if len(store.ITEM_SEP.join(items)) > store.MAX_STORE_CHARS:
        return False, f"{store.MAX_STORE_CHARS}자 초과 — 거부"
    _save(user_id, store_name, items)
    return True, "교체됨"


def remove(user_id: str, store_name: str, target: str) -> tuple[bool, str]:
    target = (target or "").strip()
    if not _valid(store_name):
        return False, f"알 수 없는 저장소: {store_name}"
    if not target:
        return False, "target 필요"
    items = read_items(user_id, store_name)
    idxs = [i for i, it in enumerate(items) if target in it]
    if not idxs:
        return False, f"대상 못 찾음: {target!r}"
    if len(idxs) > 1:
        return False, f"대상 모호({len(idxs)}개): {target!r}"
    items.pop(idxs[0])
    _save(user_id, store_name, items)
    return True, "삭제됨"


def snapshot(user_id: str) -> str:
    blocks = []
    for sname, (_f, label) in _STORES.items():
        items = read_items(user_id, sname)
        if items:
            blocks.append(f"=== {label} ===\n" + "\n".join("- " + it for it in items))
    return "\n\n".join(blocks)
