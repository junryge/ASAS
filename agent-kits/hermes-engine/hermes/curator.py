"""
hermes/curator.py — 큐레이터 (앱 시작 시 밀린 정리 따라잡기)

cron 대신 "앱 켤 때 마지막 실행일 확인 후 오늘 안 했으면 1회 실행".
- 30일 미사용 → stale, 90일 미사용 → archived (파일 보존, 자동 삭제 금지)
- pinned 면제
"""
from __future__ import annotations
import os
import time
from datetime import datetime

from . import store, skills

STALE_DAYS = 30
ARCHIVE_DAYS = 90


def _curator_path(user_id: str) -> str:
    return os.path.join(store.user_dir(user_id), "curator.json")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _run_for_user(user_id: str, now: float | None = None) -> dict:
    now = now or time.time()
    usage = skills._load_usage(user_id)
    staled = archived = 0
    for name, info in usage.items():
        if info.get("pinned"):
            continue
        last = info.get("last_used", 0) or info.get("created", 0)
        if not last:
            continue
        age_days = (now - last) / 86400.0
        state = info.get("state", "active")
        if age_days >= ARCHIVE_DAYS and state != "archived":
            info["state"] = "archived"
            archived += 1
        elif age_days >= STALE_DAYS and state == "active":
            info["state"] = "stale"
            staled += 1
    if staled or archived:
        skills._save_usage(user_id, usage)
    return {"staled": staled, "archived": archived}


def maybe_run(user_id: str) -> dict:
    """오늘 아직 안 돌았으면 1회 실행."""
    if not store.safe_id(user_id):
        return {"ran": False, "staled": 0, "archived": 0}
    path = _curator_path(user_id)
    meta = store.read_json(path, {})
    if meta.get("last_run") == _today():
        return {"ran": False, "staled": 0, "archived": 0}
    res = _run_for_user(user_id)
    meta["last_run"] = _today()
    meta["last_result"] = res
    store.write_json(path, meta)
    res["ran"] = True
    return res


def run_all_users() -> dict:
    """모든 사용자 폴더에 대해 maybe_run. 앱 시작 시 1회 호출용."""
    total = {"users": 0, "ran": 0, "staled": 0, "archived": 0}
    root = store.AGENTS_ROOT
    if not os.path.isdir(root):
        return total
    for uid in os.listdir(root):
        if not os.path.isdir(os.path.join(root, uid)):
            continue
        total["users"] += 1
        r = maybe_run(uid)
        if r.get("ran"):
            total["ran"] += 1
            total["staled"] += r.get("staled", 0)
            total["archived"] += r.get("archived", 0)
    return total
