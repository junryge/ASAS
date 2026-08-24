# -*- coding: utf-8 -*-
"""
세션 저장 — 서버 디스크 (data/sessions.json).

브라우저 localStorage 대신 서버가 보관하므로, 다른 PC 에서 접속해도
같은 세션 목록이 보인다. 보관 한도(최근 30개 / 1.2MB)는 여기서 강제한다.
"""
import json
import threading

from . import config

_LOCK = threading.Lock()


class SessionStore:
    def __init__(self, path):
        self.path = path            # data/sessions.json
        self.sessions = []          # [{id, ts, title, msgs:[{who,text,tag,meta}]}]
        self._load()

    def _load(self):
        try:
            if self.path.is_file():
                self.sessions = json.loads(self.path.read_text(encoding="utf-8")) or []
        except Exception:
            self.sessions = []

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.sessions, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:
            pass

    def get_all(self):
        with _LOCK:
            return self.sessions

    def put_all(self, sessions, deleted=None):
        """브라우저가 보낸 목록을 서버 목록과 **병합**한다.

        ★교체가 아니라 병합이다. 예전에는 통째 교체여서, 두 PC 가 같이
          쓰면 나중에 저장한 쪽이 먼저 쪽의 세션을 조용히 지웠다 —
          "다른 컴에서 쓴 세션이 안 보인다" 의 실제 원인.
          · 같은 id 는 보낸 쪽이 이긴다 (자기 세션의 최신 상태니까)
          · 서버에만 있는 세션은 남긴다 (다른 PC 의 것)
          · 지우기는 deleted 로 명시해야 지워진다 — 병합에서 빠진 것을
            삭제로 해석하면 남의 세션을 또 지우게 된다
        """
        if not isinstance(sessions, list):
            return False
        drop = {str(x) for x in (deleted or []) if x}
        incoming = {s["id"]: s for s in sessions
                    if isinstance(s, dict) and "id" in s}
        with _LOCK:
            merged = dict(incoming)
            for s in self.sessions:
                sid = s.get("id")
                if sid and sid not in merged:
                    merged[sid] = s
            rows = [s for sid, s in merged.items() if sid not in drop]
            # 최신 세션이 먼저 — ts('YYYY-MM-DD HH:MM…') 는 문자열 정렬로 충분
            rows.sort(key=lambda s: str(s.get("ts") or ""), reverse=True)
            out, acc = [], 0
            for s in rows[:config.SESS_MAX]:
                sz = len(json.dumps(s, ensure_ascii=False))
                if acc + sz > config.SESS_BYTES:
                    break
                out.append(s)
                acc += sz
            self.sessions = out
            self._save()
        return True

    @staticmethod
    def to_markdown(s):
        out = "# 대화 기록 — {}\n\n".format(s.get("ts", ""))
        for m in s.get("msgs", []):
            if m.get("who") == "me":
                out += "**나**\n\n{}\n\n".format(m.get("text", ""))
            elif m.get("who") == "ai":
                tag = m.get("tag") or ""
                out += "**캐릭터**{}\n\n{}\n\n".format(
                    " *({})*".format(tag) if tag else "", m.get("text", ""))
        return out
