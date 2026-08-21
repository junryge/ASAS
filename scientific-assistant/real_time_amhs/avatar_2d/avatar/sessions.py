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

    def put_all(self, sessions):
        """브라우저가 보낸 전체 목록을 한도에 맞춰 저장한다."""
        if not isinstance(sessions, list):
            return False
        out, acc = [], 0
        for s in sessions[:config.SESS_MAX]:
            if not isinstance(s, dict) or "id" not in s:
                continue
            sz = len(json.dumps(s, ensure_ascii=False))
            if acc + sz > config.SESS_BYTES:
                break
            out.append(s)
            acc += sz
        with _LOCK:
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
