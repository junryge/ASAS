"""
triggers.py — 부품 ① 오토메이션 ('시작' 버튼을 알아서 누른다)

폐쇄망 prod 엔 외부 cron 이 없을 수 있으니, stdlib threading 으로 내장 스케줄러를 돈다.
  - CronTrigger     : 표준 5필드 cron (분 시 일 월 요일). *, 리스트(,), 범위(-), 스텝(/) 지원.
                      일/요일 동시 지정시 표준 Vixie cron OR 시맨틱.
  - IntervalTrigger : N초마다
  - ManualTrigger   : 외부에서 fire()
  - Scheduler       : 백그라운드 스레드가 매초 틱, 발화 조건 맞으면 작업 실행.

triage: discover 단계에서 할 일을 추려 우선순위. (간단 함수 훅으로 제공)
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, Set


# ---------------------------------------------------------------------------
# cron 파서
# ---------------------------------------------------------------------------
def _parse_cron_field(field_str: str, lo: int, hi: int, dow: bool = False) -> Set[int]:
    """단일 cron 필드를 정수 집합으로. 요일(dow)은 7->0(일) 정규화."""
    result: Set[int] = set()
    for part in field_str.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            rng, step_s = part.split("/", 1)
            step = int(step_s)
        else:
            rng = part
        if rng == "*":
            start, end = lo, hi
        elif "-" in rng:
            a, b = rng.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(rng)
        for v in range(start, end + 1, step):
            if dow and v == 7:
                v = 0
            if lo <= v <= hi:
                result.add(v)
    return result


class CronTrigger:
    """표준 5필드: 'min hour dom month dow'  (예: '0 9 * * 1-5' = 평일 9시 정각)."""

    def __init__(self, expr: str):
        fields = expr.split()
        if len(fields) != 5:
            raise ValueError(f"cron 은 5필드여야 함: '{expr}'")
        self.expr = expr
        self.minute = _parse_cron_field(fields[0], 0, 59)
        self.hour = _parse_cron_field(fields[1], 0, 23)
        self.dom = _parse_cron_field(fields[2], 1, 31)
        self.month = _parse_cron_field(fields[3], 1, 12)
        self.dow = _parse_cron_field(fields[4], 0, 6, dow=True)
        self._dom_restricted = fields[2] != "*"
        self._dow_restricted = fields[4] != "*"

    def matches(self, dt: datetime) -> bool:
        if dt.minute not in self.minute:
            return False
        if dt.hour not in self.hour:
            return False
        if dt.month not in self.month:
            return False
        # 표준 cron: dom/dow 둘 다 제한이면 OR, 하나만 제한이면 AND
        cron_dow = dt.isoweekday() % 7   # 월1..일7 -> 월1..토6,일0
        dom_ok = dt.day in self.dom
        dow_ok = cron_dow in self.dow
        if self._dom_restricted and self._dow_restricted:
            return dom_ok or dow_ok
        return dom_ok and dow_ok


class IntervalTrigger:
    """N초마다 발화."""

    def __init__(self, seconds: float):
        self.seconds = float(seconds)
        self._last: Optional[float] = None

    def due(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        if self._last is None or (now - self._last) >= self.seconds:
            self._last = now
            return True
        return False


class ManualTrigger:
    """외부 fire() 호출시 1회 발화."""

    def __init__(self):
        self._fired = False

    def fire(self):
        self._fired = True

    def due(self) -> bool:
        if self._fired:
            self._fired = False
            return True
        return False


# ---------------------------------------------------------------------------
# Job + Scheduler
# ---------------------------------------------------------------------------
@dataclass
class Job:
    name: str
    action: Callable[[], None]           # 보통 loop.run 을 감싼 함수
    cron: Optional[CronTrigger] = None
    interval: Optional[IntervalTrigger] = None
    manual: Optional[ManualTrigger] = None
    enabled: bool = True
    last_fired_minute: Optional[str] = None
    run_count: int = 0

    def should_fire(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        if self.manual and self.manual.due():
            return True
        if self.interval and self.interval.due(now.timestamp()):
            return True
        if self.cron and self.cron.matches(now):
            # 같은 분 중복 발화 방지
            key = now.strftime("%Y%m%d%H%M")
            if key != self.last_fired_minute:
                self.last_fired_minute = key
                return True
        return False


class Scheduler:
    """백그라운드 스레드로 잡들을 돌린다. 폐쇄망 cron 대체."""

    def __init__(self, tick_seconds: float = 1.0,
                 on_error: Optional[Callable[[str, Exception], None]] = None):
        self.jobs: List[Job] = []
        self.tick = tick_seconds
        self.on_error = on_error
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def add_job(self, job: Job) -> Job:
        self.jobs.append(job)
        return job

    def cron(self, name: str, expr: str, action: Callable[[], None]) -> Job:
        return self.add_job(Job(name=name, action=action, cron=CronTrigger(expr)))

    def every(self, name: str, seconds: float, action: Callable[[], None]) -> Job:
        return self.add_job(Job(name=name, action=action,
                                interval=IntervalTrigger(seconds)))

    def manual(self, name: str, action: Callable[[], None]) -> Job:
        return self.add_job(Job(name=name, action=action, manual=ManualTrigger()))

    def fire(self, name: str) -> bool:
        for j in self.jobs:
            if j.name == name and j.manual:
                j.manual.fire()
                return True
        return False

    def _loop(self):
        while not self._stop.is_set():
            now = datetime.now()
            for job in list(self.jobs):
                try:
                    if job.should_fire(now):
                        job.run_count += 1
                        job.action()
                except Exception as e:
                    if self.on_error:
                        self.on_error(job.name, e)
            self._stop.wait(self.tick)

    def start(self, background: bool = True):
        """background=True 면 스레드로, False 면 현재 스레드 블로킹."""
        if background:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            self._loop()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.tick + 1)


# ---------------------------------------------------------------------------
# Triage — discover 단계 (할 일 추려 우선순위)
# ---------------------------------------------------------------------------
@dataclass
class TriageItem:
    key: str
    priority: int           # 낮을수록 먼저
    payload: dict = field(default_factory=dict)


def triage(items: List[TriageItem]) -> List[TriageItem]:
    """우선순위 정렬. (응급실 분류처럼 급한 것 먼저)"""
    return sorted(items, key=lambda x: x.priority)
