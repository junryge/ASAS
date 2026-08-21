# -*- coding: utf-8 -*-
"""서버측 설정 (data/settings.json) — 자료 예산·컨텍스트 한도·대화 기록 수 등."""
import json
import threading

from . import config

_LOCK = threading.Lock()


class Settings:
    KEYS = ("docBudget", "ctxLimit", "keepMsgs", "temperature")

    def __init__(self, path):
        self.path = path
        self.data = dict(config.DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        try:
            if self.path.is_file():
                saved = json.loads(self.path.read_text(encoding="utf-8")) or {}
                for k in self.KEYS:
                    if k in saved:
                        self.data[k] = saved[k]
        except Exception:
            pass

    def get(self, k, default=None):
        with _LOCK:
            return self.data.get(k, default)

    def all(self):
        with _LOCK:
            return dict(self.data)

    def update(self, patch):
        if not isinstance(patch, dict):
            return self.all()
        with _LOCK:
            for k in self.KEYS:
                if k in patch:
                    try:
                        self.data[k] = float(patch[k]) \
                            if k == "temperature" else int(patch[k])
                    except (TypeError, ValueError):
                        pass
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.data, ensure_ascii=False),
                                     encoding="utf-8")
            except Exception:
                pass
            return dict(self.data)
