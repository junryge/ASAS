# -*- coding: utf-8 -*-
"""서버측 설정 (data/settings.json) — 자료 예산·컨텍스트 한도·대화 기록 수 등."""
import json
import threading

from . import config

_LOCK = threading.Lock()


class Settings:
    # alarmHoldMin/alarmKeep — 알람 기록 창의 [설정] 에서 고친다.
    # ★코드에만 있으면 "왜 60분이나 안 꺼지냐" 를 아무도 못 고친다.
    KEYS = ("docBudget", "ctxLimit", "keepMsgs", "temperature",
            "alarmHoldMin", "alarmKeep")
    # ★문자열 설정은 숫자 변환을 타면 안 된다 (agentRules 는 프롬프트 본문)
    TEXT_KEYS = ("agentRules",)

    def __init__(self, path):
        self.path = path
        self.data = dict(config.DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        try:
            if self.path.is_file():
                saved = json.loads(self.path.read_text(encoding="utf-8")) or {}
                for k in self.KEYS + self.TEXT_KEYS:
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
            for k in self.TEXT_KEYS:
                if k in patch:
                    # 빈 문자열 = 기본값으로 되돌리기 (llm.agent_rules 가 판단)
                    self.data[k] = str(patch[k] or "")[:20000]
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.data, ensure_ascii=False),
                                     encoding="utf-8")
            except Exception:
                pass
            return dict(self.data)
