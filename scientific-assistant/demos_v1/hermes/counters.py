"""
demos_v1/hermes/counters.py — 백그라운드 리뷰 트리거용 카운터

counters.json: {turns_since_memory, iters_since_skill}
- turns_since_memory: 유저 턴마다 +1, 임계 10 → 메모리 리뷰
- iters_since_skill: 스킬/툴 단계마다 +1, skill_manage 실호출 시 0 리셋, 임계 5 → 스킬 리뷰
"""
from __future__ import annotations
import os

from demos_v1.hermes import store

TURN_THRESHOLD = 10
SKILL_THRESHOLD = 5


def _path(user_id: str) -> str:
    return os.path.join(store.user_dir(user_id), "counters.json")


def load(user_id: str) -> dict:
    d = store.read_json(_path(user_id), {})
    d.setdefault("turns_since_memory", 0)
    d.setdefault("iters_since_skill", 0)
    return d


def save(user_id: str, d: dict) -> None:
    store.write_json(_path(user_id), d)


def bump_turn(user_id: str) -> dict:
    d = load(user_id)
    d["turns_since_memory"] += 1
    d["iters_since_skill"] += 1
    save(user_id, d)
    return d


def reset_skill(user_id: str) -> None:
    d = load(user_id)
    d["iters_since_skill"] = 0
    save(user_id, d)


def reset_memory(user_id: str) -> None:
    d = load(user_id)
    d["turns_since_memory"] = 0
    save(user_id, d)


def due(user_id: str) -> dict:
    """임계 도달 여부. {memory: bool, skill: bool}"""
    d = load(user_id)
    return {
        "memory": d["turns_since_memory"] >= TURN_THRESHOLD,
        "skill": d["iters_since_skill"] >= SKILL_THRESHOLD,
    }
