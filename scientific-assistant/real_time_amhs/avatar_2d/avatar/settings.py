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
    # MCP 서버별 켜기/끄기·주소 — {서버열쇠: {"enabled": bool, "url": str}}
    # ★코드(config.MCP_SERVERS)가 아니라 여기가 사람이 화면에서 고친 값이다.
    #   재시작해도 남아야 한다 — 느려서 껐는데 다시 켜지면 또 겪는다.
    DICT_KEYS = ("mcp",)

    def __init__(self, path):
        self.path = path
        self.data = dict(config.DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        try:
            if self.path.is_file():
                saved = json.loads(self.path.read_text(encoding="utf-8")) or {}
                for k in self.KEYS + self.TEXT_KEYS + self.DICT_KEYS:
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
            for k in self.DICT_KEYS:
                if not isinstance(patch.get(k), dict):
                    continue
                # ★통째로 갈아끼우지 않고 **덮어쓴다**. 화면이 한 서버만
                #   보내도 나머지 서버 설정이 날아가면 안 된다.
                cur = dict(self.data.get(k) or {})
                for kk, vv in patch[k].items():
                    if not isinstance(vv, dict):
                        continue
                    one = dict(cur.get(str(kk)[:40]) or {})
                    if "enabled" in vv:
                        one["enabled"] = bool(vv["enabled"])
                    if "url" in vv:
                        u = str(vv["url"] or "")[:300]
                        # 빈 값 = 저장해 둔 것을 지우고 코드 기본값으로
                        one.pop("url", None) if not u else one.update(url=u)
                    cur[str(kk)[:40]] = one
                self.data[k] = cur
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.data, ensure_ascii=False),
                                     encoding="utf-8")
            except Exception:
                pass
            return dict(self.data)
