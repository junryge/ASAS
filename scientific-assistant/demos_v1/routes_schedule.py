"""
demos_v1/routes_schedule.py — ⏰ 예약 작업 (매일 HH:MM / N분 간격 프롬프트 실행)

"매일 07:00 어제자 반송 이상 요약 만들어 둬" 같은 것을 데모스가 스스로 돌린다.
결과는 markdown 파일로 쌓이고 UI 팝업( /예약 )에서 바로 읽는다.

설계
    - 저장:  demos_data/schedules/<user_id>/jobs.json           (작업 정의)
             demos_data/schedules/<user_id>/results/<job_id>/<ts>.md  (실행 결과)
    - 실행:  데몬 스레드가 30초마다 due 검사 → API 환경(ENV_CONFIG)으로 1회 완성 호출.
             GGUF(로컬) 환경은 제외한다 — 메인은 API 이고, 백그라운드 스레드가
             단일 GGUF 락을 잡으면 채팅이 밀린다.
    - 스킬:  작업에 스킬 이름을 달면 SKILL.md 본문을 시스템 프롬프트로 앞에 붙인다.
    - 시간:  서버 로컬 시간 기준. daily 는 하루 1회(그 시각 이후 첫 검사에서 실행).

엔드포인트
    GET    /api/schedules?user_id=            작업 목록
    POST   /api/schedules                     작업 생성/수정 {user_id, job}
    DELETE /api/schedules/<jid>?user_id=      삭제
    POST   /api/schedules/<jid>/toggle        켜기/끄기
    POST   /api/schedules/<jid>/run           지금 실행 (백그라운드)
    GET    /api/schedules/<jid>/results       결과 파일 목록
    GET    /api/schedules/<jid>/result?f=     결과 파일 내용
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime

from flask import jsonify, request

from demos_v1.utils import BASE_DIR

SCHED_DIR = os.path.join(BASE_DIR, "demos_data", "schedules")
CHECK_SEC = 30                 # due 검사 주기
MAX_RESULTS_PER_JOB = 60       # 작업당 결과 보관 수
SKILL_CHARS_CAP = 12000        # 스킬 1개당 시스템 프롬프트 상한

_lock = threading.Lock()
_worker_started = False
_running: set[str] = set()     # 동시 중복 실행 방지 (job_id)


# ────────────────────────── 저장소 ──────────────────────────
def _safe(v: str) -> str:
    v = (v or "").strip()
    return v if v and "/" not in v and "\\" not in v and ".." not in v else ""


def _user_dir(uid: str) -> str:
    d = os.path.join(SCHED_DIR, uid)
    os.makedirs(d, exist_ok=True)
    return d


def _jobs_path(uid: str) -> str:
    return os.path.join(_user_dir(uid), "jobs.json")


def _load_jobs(uid: str) -> list[dict]:
    p = _jobs_path(uid)
    if not os.path.isfile(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _save_jobs(uid: str, jobs: list[dict]) -> None:
    p = _jobs_path(uid)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def _results_dir(uid: str, jid: str) -> str:
    d = os.path.join(_user_dir(uid), "results", jid)
    os.makedirs(d, exist_ok=True)
    return d


# ────────────────────────── 실행 ──────────────────────────
def _api_envs() -> dict:
    """예약 실행에 쓸 수 있는 환경 — API 만 (GGUF 로컬 제외)."""
    try:
        from demos_v1.models import ENV_CONFIG
    except Exception:
        return {}
    return {k: v for k, v in ENV_CONFIG.items()
            if not str(k).startswith("gguf")
            and not str(v.get("url", "")).startswith("python://")}


def _complete(env_id: str, messages: list[dict], max_tokens: int = 3000) -> tuple[str, str]:
    """1회 완성 호출 → (본문, 오류). 채팅 경로와 같은 게이트웨이·토큰을 쓴다."""
    envs = _api_envs()
    if env_id not in envs:
        # 지정 env 가 없으면 쓸 수 있는 첫 API env
        if not envs:
            return "", "사용 가능한 API 환경이 없습니다"
        env_id = next(iter(envs))
    cfg = envs[env_id]
    try:
        from demos_v1.config import API_TOKEN
    except Exception:
        API_TOKEN = ""
    headers = {"Content-Type": "application/json"}
    key = cfg.get("token") or API_TOKEN
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        from demos_v1.llm_compat import chat_post
        r = chat_post(cfg["url"], headers=headers, json={
            "model": cfg["model"], "messages": messages,
            "temperature": 0.3, "max_tokens": max_tokens, "stream": False,
        }, timeout=300, verify=False)
        if r.status_code >= 400:
            return "", f"HTTP {r.status_code}: {r.text[:300]}"
        # r.json() 은 Content-Type 에 charset 이 없으면 latin-1 로 잘못 읽을 수 있다
        data = json.loads(r.content.decode("utf-8", "replace"))
        txt = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
        # 추론 모델 <think> 제거
        txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip()
        return txt, ""
    except Exception as e:
        return "", f"{type(e).__name__}: {e}"


def _skill_system(names: list[str]) -> str:
    """작업에 달린 스킬들의 SKILL.md 를 시스템 프롬프트로."""
    if not names:
        return ""
    parts = []
    try:
        from demos_v1.skills import load_skill_content
    except Exception:
        return ""
    for n in names[:5]:
        try:
            body = load_skill_content(n) or ""
        except Exception:
            body = ""
        if body:
            parts.append(f"═══ 스킬: {n} ═══\n{body[:SKILL_CHARS_CAP]}")
    return "\n\n".join(parts)


def _run_job(uid: str, job: dict) -> None:
    """작업 1회 실행 → 결과 md 저장 + last_run 갱신. 스레드에서 돈다."""
    jid = job.get("id", "")
    if jid in _running:
        return
    _running.add(jid)
    started = datetime.now()
    try:
        msgs = []
        sys_p = _skill_system(job.get("skills") or [])
        if sys_p:
            msgs.append({"role": "system", "content": sys_p})
        msgs.append({"role": "user", "content": job.get("prompt", "")})
        body, err = _complete(job.get("env", ""), msgs,
                              int(job.get("max_tokens") or 3000))
        took = (datetime.now() - started).total_seconds()

        ts = started.strftime("%Y%m%d_%H%M%S")
        head = (f"# ⏰ {job.get('name','예약 작업')}\n\n"
                f"- 실행: {started:%Y-%m-%d %H:%M:%S} ({took:.0f}초)\n"
                f"- 모델: {job.get('env','auto')}\n"
                f"- 프롬프트: {job.get('prompt','')[:200]}\n\n---\n\n")
        content = head + (body if body else f"❌ 실행 실패: {err}")
        rd = _results_dir(uid, jid)
        with open(os.path.join(rd, f"{ts}.md"), "w", encoding="utf-8") as f:
            f.write(content)
        # 보관 수 초과분 삭제 (오래된 것부터)
        files = sorted(f for f in os.listdir(rd) if f.endswith(".md"))
        for old in files[:-MAX_RESULTS_PER_JOB]:
            try:
                os.remove(os.path.join(rd, old))
            except OSError:
                pass

        with _lock:
            jobs = _load_jobs(uid)
            for j in jobs:
                if j.get("id") == jid:
                    j["last_run"] = started.isoformat(timespec="seconds")
                    j["last_status"] = "ok" if body else f"error: {err[:160]}"
                    j["run_count"] = int(j.get("run_count") or 0) + 1
            _save_jobs(uid, jobs)
        print(f"  ⏰ [예약] {uid}/{job.get('name')} → "
              f"{'완료' if body else '실패: ' + err[:80]} ({took:.0f}초)")
    finally:
        _running.discard(jid)


def _is_due(job: dict, now: datetime) -> bool:
    if not job.get("enabled", True):
        return False
    last = job.get("last_run") or ""
    if job.get("mode") == "interval":
        every = max(1, int(job.get("every_min") or 60))
        if not last:
            return True
        try:
            return (now - datetime.fromisoformat(last)).total_seconds() >= every * 60
        except ValueError:
            return True
    # daily HH:MM — 그 시각이 지났고, 오늘 아직 안 돌았으면 due
    hhmm = str(job.get("time") or "07:00")
    try:
        h, m = int(hhmm[:2]), int(hhmm[3:5])
    except (ValueError, IndexError):
        h, m = 7, 0
    if (now.hour, now.minute) < (h, m):
        return False
    return not last.startswith(now.strftime("%Y-%m-%d"))


def _worker():
    while True:
        time.sleep(CHECK_SEC)
        try:
            now = datetime.now()
            if not os.path.isdir(SCHED_DIR):
                continue
            for uid in os.listdir(SCHED_DIR):
                if not _safe(uid):
                    continue
                for job in _load_jobs(uid):
                    if _is_due(job, now):
                        threading.Thread(target=_run_job, args=(uid, job),
                                         daemon=True).start()
        except Exception as e:
            print(f"  ⏰ [예약] 워커 오류(계속): {e}")


# ────────────────────────── 라우트 ──────────────────────────
def register_schedule_routes(app) -> None:
    global _worker_started
    if not _worker_started:
        threading.Thread(target=_worker, daemon=True).start()
        _worker_started = True

    def _uid():
        return _safe(request.args.get("user_id", "")
                     or (request.get_json(silent=True) or {}).get("user_id", ""))

    @app.route("/api/schedules", methods=["GET"])
    def api_sched_list():
        uid = _uid()
        if not uid:
            return jsonify({"jobs": [], "envs": list(_api_envs().keys())})
        return jsonify({"jobs": _load_jobs(uid),
                        "envs": [{"id": k, "name": v.get("name", k)}
                                 for k, v in _api_envs().items()]})

    @app.route("/api/schedules", methods=["POST"])
    def api_sched_save():
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        j = (request.get_json(silent=True) or {}).get("job") or {}
        if not str(j.get("prompt") or "").strip():
            return jsonify({"error": "prompt 가 비어 있습니다"}), 400
        job = {
            "id": _safe(str(j.get("id") or "")) or uuid.uuid4().hex[:10],
            "name": str(j.get("name") or "예약 작업")[:80],
            "prompt": str(j.get("prompt"))[:8000],
            "env": str(j.get("env") or ""),
            "skills": [s for s in (j.get("skills") or []) if _safe(str(s))][:5],
            "mode": "interval" if j.get("mode") == "interval" else "daily",
            "time": str(j.get("time") or "07:00")[:5],
            "every_min": max(1, min(int(j.get("every_min") or 60), 24 * 60)),
            "max_tokens": max(256, min(int(j.get("max_tokens") or 3000), 8192)),
            "enabled": bool(j.get("enabled", True)),
        }
        with _lock:
            jobs = _load_jobs(uid)
            for i, old in enumerate(jobs):
                if old.get("id") == job["id"]:
                    job["last_run"] = old.get("last_run")
                    job["last_status"] = old.get("last_status")
                    job["run_count"] = old.get("run_count")
                    jobs[i] = job
                    break
            else:
                if len(jobs) >= 20:
                    return jsonify({"error": "예약 작업은 20개까지"}), 400
                jobs.append(job)
            _save_jobs(uid, jobs)
        return jsonify({"ok": True, "job": job})

    @app.route("/api/schedules/<jid>", methods=["DELETE"])
    def api_sched_delete(jid):
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        with _lock:
            jobs = [j for j in _load_jobs(uid) if j.get("id") != jid]
            _save_jobs(uid, jobs)
        return jsonify({"ok": True})

    @app.route("/api/schedules/<jid>/toggle", methods=["POST"])
    def api_sched_toggle(jid):
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        with _lock:
            jobs = _load_jobs(uid)
            for j in jobs:
                if j.get("id") == jid:
                    j["enabled"] = not j.get("enabled", True)
                    _save_jobs(uid, jobs)
                    return jsonify({"ok": True, "enabled": j["enabled"]})
        return jsonify({"error": "없는 작업"}), 404

    @app.route("/api/schedules/<jid>/run", methods=["POST"])
    def api_sched_run(jid):
        uid = _uid()
        if not uid:
            return jsonify({"error": "user_id 필요"}), 400
        job = next((j for j in _load_jobs(uid) if j.get("id") == jid), None)
        if not job:
            return jsonify({"error": "없는 작업"}), 404
        if jid in _running:
            return jsonify({"ok": True, "already": True})
        threading.Thread(target=_run_job, args=(uid, job), daemon=True).start()
        return jsonify({"ok": True, "started": True})

    @app.route("/api/schedules/<jid>/results", methods=["GET"])
    def api_sched_results(jid):
        uid = _uid()
        if not uid or not _safe(jid):
            return jsonify({"files": []})
        rd = _results_dir(uid, jid)
        files = sorted((f for f in os.listdir(rd) if f.endswith(".md")), reverse=True)
        return jsonify({"files": [{"name": f,
                                   "size": os.path.getsize(os.path.join(rd, f))}
                                  for f in files[:MAX_RESULTS_PER_JOB]],
                        "running": jid in _running})

    @app.route("/api/schedules/<jid>/result", methods=["GET"])
    def api_sched_result(jid):
        uid = _uid()
        fn = request.args.get("f", "")
        if not uid or not _safe(jid) or not re.fullmatch(r"[0-9_]+\.md", fn or ""):
            return jsonify({"error": "잘못된 요청"}), 400
        p = os.path.join(_results_dir(uid, jid), fn)
        if not os.path.isfile(p):
            return jsonify({"error": "없는 파일"}), 404
        with open(p, encoding="utf-8") as f:
            return jsonify({"name": fn, "content": f.read()})
