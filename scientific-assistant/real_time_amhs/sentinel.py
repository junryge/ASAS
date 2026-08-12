#!/usr/bin/env python3
"""
AMHS Sentinel_M16BR — 실시간 관제 코어 (독립)

로그프레소 폴링 → 이상감지 → 케이스 생성/갱신 → 심각도 라우팅/에스컬레이션.
데모스(demos_v1) 어떤 모듈도 import 하지 않는다.

정책 (config.json policy):
  · 감지는 항상 실시간이다.
  · "이상 없음" 판정은 케이스를 닫지 않고 재확인 예약만 갱신한다.
  · 종결 후에도 억제 창(suppression window) 동안 재발은 같은 케이스로 묶인다.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta

from lp_client import load_config
from lp_query import fetch_amos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ────────────────────────────── 등급 ──────────────────────────────
def grade(score: float, cfg: dict | None = None) -> dict:
    """점수 → 등급 밴드. 임계 미만은 정상(무알람)."""
    cfg = cfg or load_config()
    g = cfg.get("grade", {})
    for b in g.get("bands", []):
        if b["min"] <= score <= b["max"]:
            return b
    return {"level": "정상", "emoji": "🟢", "severity": "정상", "min": 0, "max": g.get("normal_max", 49)}


def alarm_floor(cfg: dict | None = None) -> int:
    """알람 최소 점수 (피드백 보정 반영)."""
    cfg = cfg or load_config()
    bands = cfg.get("grade", {}).get("bands", [])
    base = min((b["min"] for b in bands), default=50)
    return max(1, min(100, base + _threshold_nudge(cfg)))


def _threshold_nudge(cfg: dict) -> int:
    """리포트 피드백 누적 → 임계 점수 보정 (±10 제한)."""
    fb = cfg.get("feedback", {})
    path = os.path.join(BASE_DIR, fb.get("store", "data/feedback.jsonl"))
    if not os.path.isfile(path):
        return 0
    step, n = fb.get("threshold_nudge", 2), fb.get("apply_last_n", 20)
    delta = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for rec in [json.loads(l) for l in f.read().splitlines() if l.strip()][-n:]:
                v = rec.get("verdict")
                if v == "과다탐지":
                    delta += step
                elif v == "누락":
                    delta -= step
    except Exception:
        return 0
    return max(-10, min(10, delta))


# ────────────────────────────── 시각 파싱 ──────────────────────────────
def _row_dt(row: dict) -> datetime | None:
    s = (row.get("datetime") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    d, t = (row.get("date") or "").strip(), (row.get("time") or "").strip()
    if d and t:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(f"{d} {t}", fmt)
            except ValueError:
                continue
    return None


def _score(row: dict) -> float:
    try:
        return float(row.get("unified_risk_score") or 0)
    except (TypeError, ValueError):
        return 0.0


# 룰 코드 → 한글명 (스킬 규칙: 답변에 룰 코드 노출 금지)
# 실제 표기는 두 가지 — reason 은 'R-A_sus', signals 는 'RA_sus'
_RULE_KR = [
    (r"R-?A_sus\b", "반송지연 지속"),
    (r"R-?B_fast\b", "Queue 상승"),
    (r"R-?A\b", "반송지연"),
    (r"R-?B\b", "Queue 누적"),
    (r"R-?C\b", "리프터막힘"),
    (r"R-?D\b", "Storage FULL"),
    (r"MAXCAPA", "운영자 용량변경"),
    (r"SORT", "소터대기"),
    (r"SLA", "4분초과"),
]


def _reason_blocks(txt: str) -> list[tuple[str, str]]:
    """'발동:' 뒤의 `영역[룰,룰,…]` 을 (영역, 블록) 목록으로 뽑는다.

    ★닫는 ']' 가 없어도 끝까지 읽는다. reason 은 길어지면 잘려서 들어오는
      경우가 있는데(룰마다 괄호 안에 수치가 붙어 금방 길어진다), 예전에는
      '[…]' 를 못 찾아 요약이 빈 문자열이 되고 → 호출부가 **원문을 그대로**
      화면에 뿌렸다. 그래서 화면에 이런 게 튀어나왔다:
        hot_area=M16HUB; S3확정; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=6.30분…
      룰 코드도 금지어('역증가')도 그대로 노출됐다.
    """
    import re
    seg = txt.split("발동:", 1)[1] if "발동:" in txt else txt
    return [(m.group(1), m.group(2))
            for m in re.finditer(r"([A-Za-z0-9_]+)\s*\[([^\]]*)(?:\]|$)", seg)]


def _rule_names(block: str) -> list[str]:
    """룰 코드 블록 → 한글 이름 목록. R-A' 처럼 프라임이 붙어도 잡는다."""
    import re
    names, seen = [], set()
    for code, kr in _RULE_KR:                      # 긴 코드부터 매칭
        if re.search(r"R?-?" + code + r"\b", block) and kr not in seen:
            seen.add(kr)
            names.append(kr)
    return names


def summarize_reason(reason: str, area: str = "") -> str:
    """reason 원문에서 발동 룰을 뽑아 한글 한 줄로. 룰 코드는 노출하지 않는다.

    예) 'hot_area=M16HUB; S3확정; 발동: M16HUB[R-A_sus,R-C,R-D(STB=100.0%)]; M14[R-A_sus]'
        → 'M16HUB 반송지연 지속 · 리프터막힘 · Storage FULL'

    ★어떤 경우에도 원문(룰 코드·영문 컬럼명·'역증가' 같은 금지어)을 돌려주지
      않는다. 못 알아본 룰이 있어도 한글로 '이상 감지' 라고만 말한다.
      원문이 필요하면 호출부가 따로 갖고 있는 reason_raw 를 쓴다(툴팁).
    """
    txt = reason or ""
    if not txt:
        return ""

    blocks = _reason_blocks(txt)
    block = ""
    if area:
        block = next((b for a, b in blocks if a.upper() == area.upper()), "")
    if not block and blocks:
        block = blocks[0][1]
    if not block:
        # 대괄호 형식이 아예 아니다 — 문장 전체에서 룰 코드를 찾아본다
        block = txt.split("발동:", 1)[-1]

    names = _rule_names(block)
    head = f"{area} " if area else ""
    if not names:
        # 룰 코드를 하나도 못 알아봤다(새 룰이거나 형식이 바뀜).
        # 원문을 뱉지 말고 한글로만 알린다.
        return (head + "이상 감지").strip()
    return head + " · ".join(names)


def reason_metrics(reason: str, area: str = "") -> list[dict]:
    """발동한 룰 → **실제 raw 지표 컬럼명**. 화면 '실제지표' 칸에 쓴다.

    한글 요약("반송지연 지속 · 리프터막힘")만 보면 '무슨 숫자를 보고 그렇게
    판단했나' 를 알 수 없다. 룰마다 대응하는 실제 컬럼을 같이 보여준다.
        반송지연  → M16HUB.QUE.TIME.AVGTOTALTIME1MIN
        리프터막힘 → M16HUB.QUE.LFT.3F_LFT_REVERSALCNT
        Storage FULL → M16HUB.STRATE.STB.3F_STORAGE_UTIL 등

    매핑은 report_graphs.parse_reason_metrics 하나만 쓴다 (리포트 그래프가
    'reason 이 실제로 발동시킨 컬럼' 을 고를 때 쓰는 것과 같은 표).
    area 를 주면 그 영역 블록만 본다 — 요약 문구와 칸이 어긋나지 않게.

    반환 [{"col","raw","label","unit"}, …] (등장 순서, 중복 제거)
    """
    txt = reason or ""
    if not txt:
        return []
    try:
        from report_graphs import parse_reason_metrics
    except Exception:
        return []
    if area:
        blk = next((b for a, b in _reason_blocks(txt) if a.upper() == area.upper()), "")
        if blk:
            txt = f"발동: {area}[{blk}]"
    try:
        return parse_reason_metrics(txt)
    except Exception:
        return []


def hid_zones(tokens: str) -> list[str]:
    """HID_32_FROM_SUM_A → HID32 (순서 보존·중복 제거)."""
    out, seen = [], set()
    for tok in (tokens or "").replace(",", " ").split():
        parts = tok.split("_")
        if len(parts) >= 2 and parts[0].upper() == "HID" and parts[1].isdigit():
            z = f"HID{parts[1]}"
            if z not in seen:
                seen.add(z)
                out.append(z)
    return out


# ────────────────────────────── 케이스 ──────────────────────────────
class CaseStore:
    """활성/확인/종결 케이스 관리. 파일에 원자적 저장."""

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.path = os.path.join(BASE_DIR, self.cfg.get("storage", {}).get("cases", "data/cases.json"))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()
        self.cases: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cases, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ── 조회 ──
    def active(self) -> list[dict]:
        return [c for c in self.cases if c["status"] != "종결"]

    def by_id(self, cid: str) -> dict | None:
        return next((c for c in self.cases if c["id"] == cid), None)

    def _match(self, area: str, now: datetime) -> dict | None:
        """같은 설비/위치의 케이스를 억제 창 안에서만 매칭.

        활성 케이스라도 마지막 감지가 억제 창보다 오래됐으면 별개 사건으로 본다
        (예: 10:27 사건과 15:40 사건은 같은 M16HUB 라도 다른 케이스).
        """
        win = timedelta(minutes=self.cfg.get("policy", {}).get("suppression_window_min", 30))
        for c in reversed(self.cases):
            if c["area"] != area:
                continue
            ref = c.get("closed_at") if c["status"] == "종결" else c.get("last_seen", c["opened_at"])
            if ref and now - datetime.fromisoformat(ref) <= win:
                return c            # 억제 창 안 → 같은 케이스로 병합/재개
            if c["status"] != "종결":
                self._stale_close(c, ref)   # 창 넘긴 활성 케이스는 자동 종료
        return None

    def _stale_close(self, c: dict, ref: str | None) -> None:
        """억제 창을 넘겨 갱신이 끊긴 활성 케이스를 자동 종료."""
        end = datetime.fromisoformat(ref) if ref else datetime.now()
        c["status"] = "종결"
        c["closed_at"] = end.isoformat()
        self._tl(c, end, "자동종결", "억제 창 경과 후 추가 감지 없음 — 자동 종료")

    # ── 감지 반영 ──
    def ingest(self, area: str, dt: datetime, score: float, row: dict) -> dict:
        """감지 1건을 케이스에 반영 (신규 생성 또는 갱신)."""
        with self._lock:
            g = grade(score, self.cfg)
            c = self._match(area, dt)
            if c is None:
                c = {
                    "id": f"C{dt.strftime('%Y%m%d%H%M%S')}-{area}",
                    "area": area,
                    "location": (row.get("hot_area") or area).strip(),
                    "opened_at": dt.isoformat(),
                    "status": "활성",
                    "peak_score": score,
                    "peak_at": dt.isoformat(),
                    "level": g["level"],
                    "severity": g["severity"],
                    "emoji": g["emoji"],
                    "acked_at": None,
                    "closed_at": None,
                    "recheck_at": None,
                    "timeline": [],
                    "escalations": [],
                    "llm": None,
                    "evidence": {},
                }
                self.cases.append(c)
                self._tl(c, dt, "감지", f"{g['emoji']} {g['level']} {score:.0f}점 최초 감지")
                c["_new"] = True                    # 자동 LLM 판단 대상 표시
            else:
                # 이미 반영한 시각이면 아무것도 하지 않는다 (재폴링 시 중복 방지)
                if c.get("last_seen") and dt <= datetime.fromisoformat(c["last_seen"]) \
                        and score <= c["peak_score"]:
                    return c
                if c["status"] == "종결":
                    c["status"] = "활성"
                    c["closed_at"] = None
                    self._tl(c, dt, "재발", f"억제 창 내 재발 — 같은 케이스로 병합 ({score:.0f}점)")
                    c["_new"] = True

            is_peak = score >= c["peak_score"]
            if score > c["peak_score"]:
                c["peak_score"] = score
                c["peak_at"] = dt.isoformat()
                g2 = grade(score, self.cfg)
                if g2["level"] != c["level"]:
                    self._tl(c, dt, "상향", f"{c['level']} → {g2['level']} ({score:.0f}점)")
                    c["_new"] = True            # 등급 상향 → LLM 재판단
                c.update(level=g2["level"], severity=g2["severity"], emoji=g2["emoji"])

            c["last_seen"] = dt.isoformat()
            # 근거 데이터는 최고점 시점 기준 (AMOS 이상감지 시각 = 사건 최고점 시각)
            if is_peak or not c.get("evidence"):
                c["evidence"] = self._evidence(row)
            self._reschedule(c, dt)
            self.save()
            return c

    def _evidence(self, row: dict) -> dict:
        """근거 데이터 · DB 스냅샷 — 원본 컬럼 그대로 (한글 라벨 붙이지 않음)."""
        bott = " ".join(x for x in (row.get("BOTTLENECK_downward_anomaly_cols", ""),
                                    row.get("BOTTLENECK_upward_anomaly_cols", "")) if x)
        queue = [x for x in " ".join(
            y for y in (row.get("QUEUE_downward_anomaly_cols", ""),
                        row.get("QUEUE_upward_anomaly_cols", "")) if y).split() if x]
        raw_reason = (row.get("reason") or "").strip()
        area = (row.get("hot_area") or "").strip()
        return {
            "zones": hid_zones(bott),
            "items": queue,
            "reason": summarize_reason(raw_reason, area),   # 원문 fallback 금지
            "reason_raw": raw_reason,
            "chain": (row.get("propagation_chain") or "").strip(),
            "flow": (row.get("flow_signals") or "").strip(),
            "maxcapa": (row.get("maxcapa_signals") or "").strip(),
            "affected": [a for a in (row.get("affected_areas") or "").replace(";", " ").split() if a],
        }

    def _tl(self, c: dict, dt: datetime, kind: str, text: str) -> None:
        c["timeline"].append({"at": dt.isoformat(), "kind": kind, "text": text})

    def _routing(self, level: str) -> dict:
        for r in self.cfg.get("policy", {}).get("routing", []):
            if r["level"] == level:
                return r
        return {}

    def _reschedule(self, c: dict, now: datetime) -> None:
        mins = self._routing(c["level"]).get("recheck_min", 5)
        c["recheck_at"] = (now + timedelta(minutes=mins)).isoformat()

    # ── 운영자 액션 ──
    def ack(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            now = datetime.now()
            c["acked_at"] = now.isoformat()
            c["status"] = "확인"
            self._tl(c, now, "확인", f"{who} 확인 처리" + (f" — {note}" if note else ""))
            self._reschedule(c, now)
            self.save()
            return c

    def mark_normal(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        """'이상 없음' — 케이스를 닫지 않고 재확인 예약만 갱신 (정책)."""
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            now = datetime.now()
            self._tl(c, now, "이상없음", f"{who} 이상 없음 판정 — 재확인 예약 갱신" + (f" — {note}" if note else ""))
            self._reschedule(c, now)
            self.save()
            return c

    def close(self, cid: str, who: str = "운영자", note: str = "") -> dict | None:
        with self._lock:
            c = self.by_id(cid)
            if not c:
                return None
            if self.cfg.get("policy", {}).get("close_requires_ack") and not c.get("acked_at"):
                return {"error": "확인 처리 후에 종결할 수 있습니다", "case": c}
            now = datetime.now()
            c["status"] = "종결"
            c["closed_at"] = now.isoformat()
            win = self.cfg.get("policy", {}).get("suppression_window_min", 30)
            self._tl(c, now, "종결", f"{who} 종결" + (f" — {note}" if note else "")
                     + f" (억제 창 {win}분: 재발 시 같은 케이스로 병합)")
            self.save()
            return c

    # ── 에스컬레이션 ──
    def check_escalations(self, now: datetime | None = None) -> list[dict]:
        """미확인 경과 시간에 따른 에스컬레이션 발생분 반환."""
        now = now or datetime.now()
        fired = []
        with self._lock:
            for c in self.cases:
                if c["status"] != "활성" or c.get("acked_at"):
                    continue
                r = self._routing(c["level"])
                elapsed = (now - datetime.fromisoformat(c["opened_at"])).total_seconds() / 60
                for mins, key in ((5, "unack_5m"), (15, "unack_15m")):
                    if elapsed >= mins and key not in [e["stage"] for e in c["escalations"]]:
                        targets = r.get(key, [])
                        if not targets:
                            continue
                        e = {"stage": key, "at": now.isoformat(), "targets": targets}
                        c["escalations"].append(e)
                        self._tl(c, now, "에스컬레이션", f"미확인 {mins}분 → {', '.join(targets)}")
                        fired.append({"case": c["id"], **e})
            if fired:
                self.save()
        return fired

    def due_rechecks(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        return [c for c in self.active()
                if c.get("recheck_at") and datetime.fromisoformat(c["recheck_at"]) <= now]


# ────────────────────────────── 폴링 ──────────────────────────────
def catch_up_range(cfg: dict | None = None) -> tuple[str, str, int]:
    """가져올 구간을 정한다 — 저장된 마지막 시각 ~ 현재.

    · 오늘 저장분이 없으면 오늘 00:00:00 부터 (서버를 늦게 켜도 하루치가 채워진다)
    · 있으면 그 시각부터 (중간에 멈췄던 구간을 메운다)
    반환 (from_dt, to_dt, 빈구간_분)
    """
    cfg = cfg or load_config()
    now = datetime.now()
    day = now.strftime("%Y%m%d")

    last = None
    try:
        from store_csv import last_time
        last = last_time(day, cfg)
    except Exception:
        pass

    start = last if last else now.replace(hour=0, minute=0, second=0, microsecond=0)
    gap = max(0, int((now - start).total_seconds() // 60))
    return start.strftime("%Y%m%d%H%M%S"), now.strftime("%Y%m%d%H%M%S"), gap


def source_mode(cfg: dict | None = None) -> str:
    """데이터를 어디서 받나 — "logpresso"(기본) 또는 "jupyter".

    config.source.mode 로 고른다. jupyter 는 예측 잡이 떨궈 놓는 날짜별
    발동이벤트 CSV 를 그대로 받아 쓴다 (로그프레소·AMOS 조인 불필요).
    """
    cfg = cfg or load_config()
    src = cfg.get("source") or {}
    mode = str(src.get("mode") or "logpresso").strip().lower()
    if mode == "jupyter" and not ((src.get("jupyter") or {}).get("enabled", True)):
        return "logpresso"
    return mode if mode in ("logpresso", "jupyter") else "logpresso"


def scan_once(store: CaseStore, rows: list[dict] | None = None,
              cfg: dict | None = None) -> dict:
    """1회 스캔 — 로그프레소 조회 → 임계 초과분을 케이스에 반영."""
    cfg = cfg or load_config()
    warn, saved, gap = None, None, None
    if rows is None:
        if source_mode(cfg) == "jupyter":
            # ── 주피터 CSV 경로 — 로그프레소를 거치지 않는다 ──
            #   예측 잡이 그 날짜 파일을 계속 갱신하므로, 매 주기 통째로 받아
            #   append_rows 로 넣는다. 이미 있는 시각은 건너뛰므로 결과적으로
            #   증분 수집이 되고, 중간에 빠진 분도 다음 주기에 저절로 메워진다.
            from jupyter_csv import fetch_day
            r = fetch_day("", cfg, verbose=False)
            if not r.get("ok"):
                return {"ok": False, "error": r.get("error"),
                        "detected": 0, "rows": 0, "source": "jupyter"}
            saved = {"written": r["written"], "skipped": r["skipped"],
                     "files": r.get("files") or []}
            gap = None
            # ★방금 파싱한 행을 그대로 쓴다. CSV 를 다시 읽으면 파일명 날짜와
            #   행의 날짜가 어긋날 때(자정 전후, 파일에 전날 꼬리가 섞인 경우)
            #   엉뚱한 빈 날짜를 보게 된다.
            rows = r.get("data") or []
        else:
            # 마지막 저장 시각 ~ 현재까지 (없으면 오늘 00:00부터) — 빈 구간을 메운다
            start, end, gap = catch_up_range(cfg)
            # 기존 데이터 + AMOS 4개 컬럼(ATLAS 2개 테이블 조인)
            rows, err = fetch_amos(from_dt=start, to_dt=end)
            if err and not err.get("warn"):
                return {"ok": False, "error": err.get("reason"),
                        "detected": 0, "rows": 0}
            if err:
                warn = err.get("reason")   # 조인 경고는 감지를 막지 않는다

            # 가져온 데이터를 날짜별 CSV 에 한 줄씩 누적 (나중에 그대로 열어볼 수 있게)
            try:
                from store_csv import append_rows
                saved = append_rows(rows, cfg)
            except Exception as e:
                print(f"[CSV] ⚠️ 저장 실패: {e}")

    floor = alarm_floor(cfg)
    touched = []
    for row in rows:
        dt, sc = _row_dt(row), _score(row)
        if dt is None or sc < floor:
            continue
        area = (row.get("hot_area") or "").strip() or "UNKNOWN"
        touched.append(store.ingest(area, dt, sc, row)["id"])

    fired = store.check_escalations()
    return {
        "ok": True,
        "rows": len(rows),
        "detected": len(touched),
        "cases": sorted(set(touched)),
        "escalations": fired,
        "alarm_floor": floor,
        "active": len(store.active()),
        "amos_warn": warn,
        "saved": saved,
        "gap_min": gap,            # 이번에 메운 빈 구간(분)
        "source": source_mode(cfg),
        "all_rows": rows,          # 정상 포함 전체 — 화면 피드용
    }


if __name__ == "__main__":
    cfg = load_config()
    st = CaseStore(cfg)
    print(f"알람 임계 : {alarm_floor(cfg)}점 (기본 50 + 피드백 보정 {_threshold_nudge(cfg):+d})")
    res = scan_once(st, cfg=cfg)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    for c in st.active():
        print(f"  {c['emoji']} {c['id']} {c['severity']} peak={c['peak_score']:.0f} "
              f"status={c['status']} zones={c['evidence'].get('zones')}")
