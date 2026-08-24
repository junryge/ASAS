# -*- coding: utf-8 -*-
"""
참고 자료 (MD/TXT) — 서버측 보관 + 검색 주입.

파일을 통째로 프롬프트에 넣으면 컨텍스트가 터진다.
예산(docBudget)을 넘으면 헤딩/빈줄 기준으로 문단을 쪼개고,
질문과 겹치는 단어가 많은 문단부터 예산이 찰 때까지 채워 넣는다.
(기존 app.js 의 docsContext 를 그대로 파이썬으로 옮긴 것)
"""
import json
import re
import threading

from . import config

_LOCK = threading.Lock()


class DocStore:
    def __init__(self, path):
        self.path = path          # data/docs.json
        self.docs = []            # [{name, text, on}]
        self._load()

    def _load(self):
        try:
            if self.path.is_file():
                self.docs = json.loads(self.path.read_text(encoding="utf-8")) or []
        except Exception:
            self.docs = []

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.docs, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:
            pass

    # ── CRUD ─────────────────────────────────────────────────────────────
    def list(self):
        with _LOCK:
            return [{"name": d["name"], "on": d.get("on", True),
                     "chars": len(d["text"])} for d in self.docs]

    def add(self, name, text):
        text = str(text or "").replace("\r\n", "\n").strip()
        if not text:
            return False
        with _LOCK:
            # 총량 한도: 새 문서를 넣되 오래된 것부터 밀어낸다
            for d in self.docs:
                if d["name"] == name:
                    d["text"] = text
                    break
            else:
                self.docs.append({"name": name, "text": text, "on": True})
            while sum(len(d["text"]) for d in self.docs) > config.DOCS_BYTES \
                    and len(self.docs) > 1:
                self.docs.pop(0)
            self._save()
        return True

    def get(self, name):
        """이름으로 본문 — 채팅 첨부가 '방금 그 파일' 을 통째로 쓸 때."""
        with _LOCK:
            for d in self.docs:
                if d["name"] == name:
                    return d["text"]
        return None

    def toggle(self, name, on):
        with _LOCK:
            for d in self.docs:
                if d["name"] == name:
                    d["on"] = bool(on)
                    self._save()
                    return True
        return False

    def delete(self, name):
        with _LOCK:
            n = len(self.docs)
            self.docs = [d for d in self.docs if d["name"] != name]
            if len(self.docs) != n:
                self._save()
                return True
        return False

    def clear(self):
        with _LOCK:
            self.docs = []
            self._save()

    # ── 검색 주입 ─────────────────────────────────────────────────────────
    def context(self, query, budget):
        with _LOCK:
            act = [d for d in self.docs if d.get("on", True) and d["text"]]
        if not act:
            return ""
        whole = "\n\n".join("### " + d["name"] + "\n" + d["text"] for d in act)
        if len(whole) <= budget:
            return whole

        # 예산 초과 -> 문단 분해 + 질의어 겹침 점수순
        chunks = []
        for d in act:
            for c in re.split(r"\n(?=#{1,6}\s)|\n\s*\n", d["text"]):
                t = c.strip()
                if len(t) > 15:
                    chunks.append({"name": d["name"], "t": t, "score": 0})

        terms = re.findall(r"[가-힣A-Za-z0-9]{2,}", (query or "").lower())
        for c in chunks:
            low = c["t"].lower()
            for w in terms:
                if w in low:
                    c["score"] += len(w)
        chunks.sort(key=lambda c: -c["score"])

        out = ""
        for c in chunks:
            if len(out) + len(c["t"]) + len(c["name"]) + 8 > budget:
                continue
            out += "### " + c["name"] + "\n" + c["t"] + "\n\n"
            if len(out) > budget * 0.96:
                break
        return out or whole[:budget]


# ── 토큰 추정 (한글 0.72/자, 영숫자 3.6자당 1, 기타 0.45) ─────────────────
def est_tokens(s):
    if not s:
        return 0
    ko = latin = other = 0
    for ch in s:
        c = ord(ch)
        if (0xAC00 <= c <= 0xD7A3) or (0x3040 <= c <= 0x30FF) \
                or (0x4E00 <= c <= 0x9FFF) or (0x1100 <= c <= 0x11FF):
            ko += 1
        elif (48 <= c <= 57) or (65 <= c <= 90) or (97 <= c <= 122):
            latin += 1
        else:
            other += 1
    return round(ko * 0.72 + latin / 3.6 + other * 0.45)
