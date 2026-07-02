#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ctx_compress.py — 폐쇄망용 LLM 컨텍스트 압축 엔진 (단일파일, stdlib only)

headroomlabs-ai/headroom 의 압축 알고리즘을 순수 파이썬으로 재구현한 것.
Rust 코어 / 프록시 / 인증 / telemetry 같은 배관은 다 걷어내고,
실제 압축 알고리즘만 원본 로직 그대로 옮겼다.

핵심 개념
---------
- 타입 판별(content type)로 내용을 보고 알맞은 압축기로 라우팅
- JSON 배열 → 컬럼형(csv-schema)으로 접기 + 행 드롭 시 CCR 센티넬
- 로그 → 레벨 점수 + 스택트레이스/요약 보존 + 보수적 중복제거
- 코드 → AST로 시그니처/독스트링만 남기고 본문 접기 (파이썬 완전, 그 외 정규식)
- 동적 k → Kneedle(bigram 커버리지 무릎점) + diversity + zlib 검증
- CCR(가역) → 날린 원본을 해시로 보관, 필요하면 retrieve 로 복구

인터페이스
----------
    from ctx_compress import compress, retrieve

    compressed, refs = compress(text)      # 압축본 문자열 + 복구용 ref 맵
    original = retrieve(ref_id, refs)      # 마커의 ref_id 로 원본 되찾기

    # 세부 제어가 필요하면:
    eng = CompressEngine(bias=1.0)
    result = eng.compress(text)            # CompressResult (메타데이터 포함)

의존성: 파이썬 표준 라이브러리만. (json, re, ast, hashlib, zlib, dataclasses)
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ════════════════════════════════════════════════════════════════════════
# 0. 공통 유틸
# ════════════════════════════════════════════════════════════════════════

def _short_hash(text: str, length: int = 8) -> str:
    """내용 기반 짧은 해시. CCR ref id 로 사용."""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:length]


def _rough_tokens(text: str) -> int:
    """대략적 토큰 수 추정. tiktoken 없이 폐쇄망에서 쓰려고 근사.
    영어 ~4자/토큰, 한글/CJK 는 글자당 토큰에 가까워서 보정."""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u3000" <= ch <= "\u9fff" or "\uac00" <= ch <= "\ud7a3")
    ascii_like = len(text) - cjk
    return int(ascii_like / 4) + cjk + 1


# ════════════════════════════════════════════════════════════════════════
# 1. CCR (가역 압축) — 날린 원본을 해시로 보관하고 마커로 참조
# ════════════════════════════════════════════════════════════════════════
#
# 원본 headroom 은 행 드롭 시 {"_ccr_dropped": "<<ccr:HASH N_rows>>"} 센티넬을
# 박고 원본을 CompressionStore 에 저장한다. 우리는 프로세스 전역 상태 없이,
# compress() 가 refs 딕셔너리를 돌려주고 그걸로 retrieve 하는 방식으로 간다.
# (DEMOS 에선 이 refs 를 세션에 들고 있으면 됨)

CCR_MARKER_RE = re.compile(r"<<ccr:([0-9a-f]{4,16})(?:\s+([^>]*))?>>")
CCR_SENTINEL_KEY = "_ccr_dropped"


class CCRStore:
    """압축 과정에서 버린 원본 조각을 해시로 보관하는 저장소."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def stash(self, original: str, note: str = "") -> str:
        """원본을 저장하고 마커 문자열을 돌려준다."""
        h = _short_hash(original)
        self._store[h] = original
        if note:
            return f"<<ccr:{h} {note}>>"
        return f"<<ccr:{h}>>"

    def get(self, ref_id: str) -> str | None:
        return self._store.get(ref_id)

    def as_dict(self) -> dict[str, str]:
        return dict(self._store)

    def __len__(self) -> int:
        return len(self._store)


def retrieve(ref_id: str, refs: dict[str, str]) -> str | None:
    """마커에서 뽑은 ref_id 로 원본을 복구. 없으면 None.

    ref_id 는 '<<ccr:ab12 ...>>' 의 'ab12' 부분. 마커 문자열째로 넘겨도
    알아서 파싱한다."""
    m = CCR_MARKER_RE.search(ref_id)
    if m:
        ref_id = m.group(1)
    return refs.get(ref_id)


def find_markers(text: str) -> list[str]:
    """압축본 안의 모든 CCR ref_id 를 뽑는다."""
    return [m.group(1) for m in CCR_MARKER_RE.finditer(text)]


# ════════════════════════════════════════════════════════════════════════
# 2. 타입 판별 (content_detector 재구현)
# ════════════════════════════════════════════════════════════════════════

class ContentType(Enum):
    JSON_ARRAY = "json_array"
    SOURCE_CODE = "source_code"
    SEARCH_RESULTS = "search"
    BUILD_OUTPUT = "build"       # 로그/빌드 출력
    GIT_DIFF = "diff"
    TABULAR = "tabular"
    PLAIN_TEXT = "text"


@dataclass
class DetectionResult:
    content_type: ContentType
    confidence: float
    metadata: dict = field(default_factory=dict)


_SEARCH_RESULT_RE = re.compile(r"^[^\s:]+:\d+:")
_MD_SEP_CELL_RE = re.compile(r"^:?-{2,}:?$")
_DIFF_HEADER_RE = re.compile(
    r"^(diff --git|diff --combined |diff --cc |--- a/"
    r"|@@\s+-\d+,\d+\s+\+\d+,\d+\s+@@)"
)
_DIFF_CHANGE_RE = re.compile(r"^[+-][^+-]")

# 언어별 코드 패턴 (원본 그대로)
_CODE_PATTERNS = {
    "python": [
        re.compile(r"^\s*(def|class|import|from|async def)\s+\w+"),
        re.compile(r"^\s*@\w+"),
        re.compile(r'^\s*"""'),
        re.compile(r"^\s*if __name__\s*=="),
    ],
    "javascript": [
        re.compile(r"^\s*(function|const|let|var|class|import|export)\s+"),
        re.compile(r"^\s*(async\s+function|=>\s*\{)"),
        re.compile(r"^\s*module\.exports"),
    ],
    "typescript": [
        re.compile(r"^\s*(interface|type|enum|namespace)\s+\w+"),
        re.compile(r":\s*(string|number|boolean|any|void)\b"),
    ],
    "go": [
        re.compile(r"^\s*(func|type|package|import)\s+"),
        re.compile(r"^\s*func\s+\([^)]+\)\s+\w+"),
    ],
    "rust": [
        re.compile(r"^\s*(fn|struct|enum|impl|mod|use|pub)\s+"),
        re.compile(r"^\s*#\["),
    ],
    "java": [
        re.compile(r"^\s*(public|private|protected)\s+(class|interface|enum)"),
        re.compile(r"^\s*@\w+"),
        re.compile(r"^\s*package\s+[\w.]+;"),
    ],
}

_LOG_LEVEL_RE = re.compile(r"\b(ERROR|FAIL|FAILED|FATAL|CRITICAL)\b", re.IGNORECASE)
_LOG_WARN_RE = re.compile(r"\b(WARN|WARNING)\b", re.IGNORECASE)
_LOG_INFO_RE = re.compile(r"\b(INFO|DEBUG|TRACE)\b", re.IGNORECASE)
_LOG_HINT_RES = [
    _LOG_LEVEL_RE, _LOG_WARN_RE, _LOG_INFO_RE,
    re.compile(r"^\s*\d{4}-\d{2}-\d{2}"),
    re.compile(r"^\s*\[\d{2}:\d{2}:\d{2}\]"),
    re.compile(r"^={3,}|^-{3,}"),
    re.compile(r"^\s*PASSED|^\s*FAILED|^\s*SKIPPED"),
    re.compile(r"^npm ERR!|^yarn error|^cargo error"),
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"^\w*(Error|Exception):"),
    re.compile(r"^\s*at\s+[\w.$]+\("),
]


def detect_content_type(content: str) -> DetectionResult:
    """내용 타입 판별. 원본 우선순위(JSON→diff→search→log→표→코드→일반) 유지."""
    if not content or not content.strip():
        return DetectionResult(ContentType.PLAIN_TEXT, 0.0)

    r = _detect_json(content)
    if r:
        return r
    r = _detect_diff(content)
    if r and r.confidence >= 0.7:
        return r
    r = _detect_search(content)
    if r and r.confidence >= 0.6:
        return r
    r = _detect_log(content)
    if r and r.confidence >= 0.5:
        return r
    r = _detect_tabular(content)
    if r and r.confidence >= 0.6:
        return r
    r = _detect_code(content)
    if r and r.confidence >= 0.5:
        return r
    return DetectionResult(ContentType.PLAIN_TEXT, 0.5)


def _detect_json(content: str) -> DetectionResult | None:
    content = content.strip()
    if not content.startswith("["):
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        if parsed and all(isinstance(x, dict) for x in parsed):
            return DetectionResult(ContentType.JSON_ARRAY, 1.0,
                                   {"item_count": len(parsed), "is_dict_array": True})
        return DetectionResult(ContentType.JSON_ARRAY, 0.8,
                               {"item_count": len(parsed), "is_dict_array": False})
    return None


def _detect_diff(content: str) -> DetectionResult | None:
    lines = content.split("\n")[:500]
    header = sum(1 for ln in lines if _DIFF_HEADER_RE.match(ln))
    change = sum(1 for ln in lines if _DIFF_CHANGE_RE.match(ln))
    if header == 0:
        return None
    conf = min(1.0, 0.5 + header * 0.2 + change * 0.05)
    return DetectionResult(ContentType.GIT_DIFF, conf,
                           {"header_matches": header, "change_lines": change})


def _detect_search(content: str) -> DetectionResult | None:
    lines = [ln for ln in content.split("\n")[:100] if ln.strip()]
    if not lines:
        return None
    hits = sum(1 for ln in lines if _SEARCH_RESULT_RE.match(ln))
    ratio = hits / len(lines)
    if ratio < 0.5:
        return None
    return DetectionResult(ContentType.SEARCH_RESULTS, min(1.0, 0.4 + ratio * 0.6),
                           {"match_lines": hits})


def _detect_log(content: str) -> DetectionResult | None:
    lines = [ln for ln in content.split("\n")[:200] if ln.strip()]
    if not lines:
        return None
    hits = 0
    for ln in lines:
        if any(rx.search(ln) for rx in _LOG_HINT_RES):
            hits += 1
    ratio = hits / len(lines)
    if ratio < 0.25:
        return None
    return DetectionResult(ContentType.BUILD_OUTPUT, min(1.0, 0.3 + ratio), {"hint_lines": hits})


def _detect_tabular(content: str) -> DetectionResult | None:
    lines = [ln for ln in content.split("\n")[:100] if ln.strip()]
    if len(lines) < 2:
        return None
    # 마크다운 표: 헤더 + 구분선
    if "|" in lines[0]:
        cells = [c.strip() for c in lines[1].strip("|").split("|")]
        if cells and all(_MD_SEP_CELL_RE.match(c) for c in cells if c):
            return DetectionResult(ContentType.TABULAR, 0.9, {"kind": "markdown"})
    # CSV/TSV: 구분자 일관성
    for delim in (",", "\t"):
        counts = [ln.count(delim) for ln in lines[:20]]
        if counts[0] >= 1 and len(set(counts)) == 1:
            return DetectionResult(ContentType.TABULAR, 0.75,
                                   {"kind": "csv", "delimiter": delim})
    return None


def _detect_code(content: str) -> DetectionResult | None:
    lines = content.split("\n")[:100]
    best_lang, best_hits = None, 0
    for lang, patterns in _CODE_PATTERNS.items():
        hits = sum(1 for ln in lines for rx in patterns if rx.match(ln))
        if hits > best_hits:
            best_lang, best_hits = lang, hits
    if best_hits < 2:
        return None
    conf = min(1.0, 0.4 + best_hits * 0.1)
    return DetectionResult(ContentType.SOURCE_CODE, conf, {"language": best_lang})


# ════════════════════════════════════════════════════════════════════════
# 3. 동적 k 계산 (adaptive_sizer 재구현) — Kneedle + diversity + zlib
# ════════════════════════════════════════════════════════════════════════

def _simhash(text: str) -> int:
    """64비트 simhash. near-duplicate 감지용."""
    v = [0] * 64
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        tokens = [text]
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8", "replace")).hexdigest(), 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= (1 << i)
    return out


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def count_unique_simhash(items, threshold: int = 3) -> int:
    """simhash 해밍거리 기준으로 대충 유니크한 항목 수를 센다."""
    sigs: list[int] = []
    for it in items:
        s = _simhash(it)
        if all(_hamming(s, prev) > threshold for prev in sigs):
            sigs.append(s)
    return len(sigs)


def compute_unique_bigram_curve(items) -> list[int]:
    """항목을 순서대로 추가하며 누적 유니크 bigram 수 곡선을 만든다."""
    seen: set[str] = set()
    curve: list[int] = []
    for it in items:
        words = re.findall(r"\w+", it.lower())
        for i in range(len(words) - 1):
            seen.add(words[i] + " " + words[i + 1])
        if not words:
            seen.add(it)
        curve.append(len(seen))
    return curve


def find_knee(curve: list[int]) -> int | None:
    """Kneedle: [0,1] 정규화 후 y=x 대각선에서 편차 최대인 지점."""
    n = len(curve)
    if n < 3:
        return None
    y0, yn = curve[0], curve[-1]
    if yn == y0:
        return None
    max_diff, knee = -1.0, None
    for i in range(n):
        x_norm = i / (n - 1)
        y_norm = (curve[i] - y0) / (yn - y0)
        diff = y_norm - x_norm
        if diff > max_diff:
            max_diff, knee = diff, i
    # 편차가 너무 작으면 무릎 없음으로 간주
    if max_diff < 0.05:
        return None
    return knee


def _validate_with_zlib(items, k: int, effective_max: int) -> int:
    """상위 k개의 zlib 압축률로 정보 포화 검증. 너무 중복이면 k 줄임."""
    if k >= len(items) or k < 1:
        return k
    kept = "\n".join(items[:k]).encode("utf-8", "replace")
    if len(kept) < 64:
        return k
    ratio = len(zlib.compress(kept, 6)) / len(kept)
    # 압축률 매우 낮음(=반복 많음) → k 축소
    if ratio < 0.25:
        return max(1, int(k * 0.7))
    return k


def compute_optimal_k(items, bias: float = 1.0, min_k: int = 3, max_k: int | None = None) -> int:
    """정보 포화 기반 최적 보존 개수. 원본 3단 로직 유지."""
    n = len(items)
    effective_max = max_k if max_k is not None else n

    # Tier 1: 빠른 경로
    if n <= 8:
        return n
    unique_count = count_unique_simhash(items)
    if unique_count <= 3:
        return min(max(min_k, unique_count), effective_max)

    # Tier 2: Kneedle on bigram curve
    curve = compute_unique_bigram_curve(items)
    knee = find_knee(curve)
    diversity_ratio = unique_count / n

    if knee is None:
        keep_fraction = 0.3 + 0.7 * diversity_ratio
        knee = max(min_k, int(n * keep_fraction))
    else:
        if diversity_ratio > 0.7:
            floor = max(min_k, int(n * (0.3 + 0.7 * diversity_ratio)))
            knee = max(knee, floor)

    k = max(min_k, int(knee * bias))
    k = min(k, effective_max)

    # Tier 3: zlib 검증
    k = _validate_with_zlib(items, k, effective_max)
    return max(min_k, min(k, effective_max))


# ════════════════════════════════════════════════════════════════════════
# 4. JSON 압축 (SmartCrusher 재구현) — dict배열 → 컬럼형 + CCR 센티넬
# ════════════════════════════════════════════════════════════════════════

@dataclass
class CrushResult:
    text: str
    strategy: str
    original_tokens: int
    compressed_tokens: int
    dropped: int = 0


def crush_json(content: str, ccr: CCRStore, bias: float = 1.0,
               max_rows: int | None = None) -> CrushResult:
    """dict 배열을 컬럼형(csv-schema 유사)으로 접는다.

    - 전 행이 같은 스키마면: 헤더 1줄 + 값 행들 (키 반복 제거)
    - 행이 너무 많으면 동적 k 로 자르고 버린 원본은 CCR 로 보관 + 센티넬
    - dict 배열이 아니면 그냥 canonical JSON 으로 재직렬화(공백 제거)만
    """
    orig_tokens = _rough_tokens(content)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)

    if not (isinstance(data, list) and data and all(isinstance(x, dict) for x in data)):
        # 배열-of-dict 아니면 공백만 제거
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return CrushResult(compact, "json-compact", orig_tokens, _rough_tokens(compact))

    # 공통 키 순서 수집 (등장 순서 보존)
    keys: list[str] = []
    seen_keys: set[str] = set()
    for row in data:
        for k in row.keys():
            if k not in seen_keys:
                seen_keys.add(k)
                keys.append(k)

    # 행 수 조절
    row_strs = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in data]
    keep_k = compute_optimal_k(row_strs, bias=bias, min_k=3, max_k=max_rows or len(data))

    dropped = 0
    kept_rows = data
    sentinel = None
    if keep_k < len(data):
        kept_rows = data[:keep_k]
        dropped_rows_data = data[keep_k:]
        dropped = len(dropped_rows_data)
        original_dropped = json.dumps(dropped_rows_data, ensure_ascii=False)
        marker = ccr.stash(original_dropped, note=f"{dropped}_rows_offloaded")
        sentinel = {CCR_SENTINEL_KEY: marker}

    # 컬럼형 렌더링: 헤더 + 값 행 (csv-schema 스타일)
    lines = ["#cols: " + " | ".join(keys)]
    for row in kept_rows:
        vals = []
        for k in keys:
            v = row.get(k, "")
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
            vals.append(str(v))
        lines.append(" | ".join(vals))
    if sentinel is not None:
        lines.append(json.dumps(sentinel, ensure_ascii=False))

    out = "\n".join(lines)
    # 접었는데 오히려 커지면 원본 compact 로 폴백
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if _rough_tokens(out) >= _rough_tokens(compact) and dropped == 0:
        return CrushResult(compact, "json-compact", orig_tokens, _rough_tokens(compact))

    return CrushResult(out, "json-columnar", orig_tokens, _rough_tokens(out), dropped)


# ════════════════════════════════════════════════════════════════════════
# 5. 로그 압축 (LogCompressor 재구현)
# ════════════════════════════════════════════════════════════════════════

class LogLevel(Enum):
    ERROR = "error"
    FAIL = "fail"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"
    UNKNOWN = "unknown"


@dataclass
class LogLine:
    line_number: int
    content: str
    level: LogLevel
    is_stack_trace: bool = False
    is_summary: bool = False
    score: float = 0.0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LogLine) and other.line_number == self.line_number

    def __hash__(self) -> int:
        return hash(self.line_number)


@dataclass
class LogConfig:
    max_total_lines: int = 200
    max_errors: int = 20
    max_warnings: int = 15
    max_stack_traces: int = 5
    stack_trace_max_lines: int = 15
    keep_first_error: bool = True
    keep_last_error: bool = True
    keep_summary_lines: bool = True
    dedupe_warnings: bool = True
    context_lines: int = 1


_STACK_RE = re.compile(r"^\s*(at\s+[\w.$]+\(|File \"|\s+\w+.*line \d+|Traceback)")
_SUMMARY_RE = re.compile(
    r"(\d+\s+(passed|failed|error|warning|skipped)|"
    r"^={3,}.*={3,}|test.*result|BUILD (SUCCESS|FAILURE)|"
    r"\d+ tests? run)", re.IGNORECASE)

_DIGIT_RE = re.compile(r"\d+")
_HEX_RE = re.compile(r"0x[0-9a-fA-F]+")
_PATH_RE = re.compile(r"/[\w/]+/")


class LogCompressor:
    """로그/빌드 출력 압축기. 원본 스코어링 로직 그대로."""

    def __init__(self, config: LogConfig | None = None) -> None:
        self.config = config or LogConfig()

    def compress(self, content: str, ccr: CCRStore, bias: float = 1.0) -> CrushResult:
        orig_tokens = _rough_tokens(content)
        raw_lines = content.split("\n")
        log_lines = self._parse_lines(raw_lines)
        if not log_lines:
            return CrushResult(content, "passthrough", orig_tokens, orig_tokens)

        selected = self._select_lines(log_lines, bias=bias)
        dropped = len(log_lines) - len(selected)

        out = self._format_output(log_lines, selected)
        if dropped > 0:
            marker = ccr.stash(content, note=f"{dropped}_lines_omitted")
            out = out + f"\n… {dropped} lines omitted {marker}"

        return CrushResult(out, "log", orig_tokens, _rough_tokens(out), dropped)

    def _parse_lines(self, lines: list[str]) -> list[LogLine]:
        result: list[LogLine] = []
        for i, ln in enumerate(lines):
            if not ln.strip():
                continue
            level = self._classify(ln)
            ll = LogLine(
                line_number=i,
                content=ln,
                level=level,
                is_stack_trace=bool(_STACK_RE.match(ln)),
                is_summary=bool(_SUMMARY_RE.search(ln)),
            )
            ll.score = self._score_line(ll)
            result.append(ll)
        return result

    def _classify(self, line: str) -> LogLevel:
        if _LOG_LEVEL_RE.search(line):
            # FAIL 계열과 ERROR 계열 구분
            if re.search(r"\bFAIL(ED)?\b", line, re.IGNORECASE):
                return LogLevel.FAIL
            return LogLevel.ERROR
        if _LOG_WARN_RE.search(line):
            return LogLevel.WARN
        if re.search(r"\bINFO\b", line):
            return LogLevel.INFO
        if re.search(r"\bDEBUG\b", line):
            return LogLevel.DEBUG
        if re.search(r"\bTRACE\b", line):
            return LogLevel.TRACE
        return LogLevel.UNKNOWN

    def _score_line(self, log_line: LogLine) -> float:
        """원본 점수표 그대로."""
        level_scores = {
            LogLevel.ERROR: 1.0,
            LogLevel.FAIL: 1.0,
            LogLevel.WARN: 0.5,
            LogLevel.INFO: 0.1,
            LogLevel.DEBUG: 0.05,
            LogLevel.TRACE: 0.02,
            LogLevel.UNKNOWN: 0.1,
        }
        score = level_scores.get(log_line.level, 0.1)
        if log_line.is_stack_trace:
            score += 0.3
        if log_line.is_summary:
            score += 0.4
        return min(1.0, score)

    def _select_lines(self, log_lines: list[LogLine], bias: float = 1.0) -> list[LogLine]:
        all_strings = [ln.content for ln in log_lines]
        adaptive_max = compute_optimal_k(
            all_strings, bias=bias, min_k=10, max_k=self.config.max_total_lines)

        errors, fails, warnings = [], [], []
        stack_traces: list[list[LogLine]] = []
        summaries: list[LogLine] = []
        current_stack: list[LogLine] = []

        for ll in log_lines:
            if ll.level == LogLevel.ERROR:
                errors.append(ll)
            elif ll.level == LogLevel.FAIL:
                fails.append(ll)
            elif ll.level == LogLevel.WARN:
                warnings.append(ll)
            if ll.is_stack_trace:
                current_stack.append(ll)
            elif current_stack:
                stack_traces.append(current_stack)
                current_stack = []
            if ll.is_summary:
                summaries.append(ll)
        if current_stack:
            stack_traces.append(current_stack)

        selected: list[LogLine] = []
        if errors:
            selected.extend(self._select_first_last(errors, self.config.max_errors))
        if fails:
            selected.extend(self._select_first_last(fails, self.config.max_errors))
        if warnings:
            if self.config.dedupe_warnings:
                warnings = self._dedupe_similar(warnings)
            selected.extend(warnings[: self.config.max_warnings])
        for stack in stack_traces[: self.config.max_stack_traces]:
            selected.extend(stack[: self.config.stack_trace_max_lines])
        if self.config.keep_summary_lines:
            selected.extend(summaries)

        selected = self._add_context(log_lines, selected)
        selected = sorted(set(selected), key=lambda x: x.line_number)

        if len(selected) > adaptive_max:
            selected = sorted(selected, key=lambda x: x.score, reverse=True)[:adaptive_max]
            selected = sorted(selected, key=lambda x: x.line_number)
        return selected

    def _select_first_last(self, lines: list[LogLine], max_count: int) -> list[LogLine]:
        if len(lines) <= max_count:
            return lines
        selected: list[LogLine] = []
        if self.config.keep_first_error and lines:
            selected.append(lines[0])
        if self.config.keep_last_error and lines and lines[-1] not in selected:
            selected.append(lines[-1])
        remaining = max_count - len(selected)
        if remaining > 0:
            cands = sorted((l for l in lines if l not in selected),
                           key=lambda x: x.score, reverse=True)
            selected.extend(cands[:remaining])
        return selected

    def _dedupe_similar(self, lines: list[LogLine]) -> list[LogLine]:
        """보수적 중복제거. 꼬리부분(숫자/hex/경로)만 정규화. 원본 방식."""
        seen: set[str] = set()
        deduped: list[LogLine] = []
        for line in lines:
            content = line.content
            split_at = next((i for i, c in enumerate(content) if c in (":", "=")), len(content))
            prefix = content[:split_at]
            suffix = content[split_at:]
            suffix = _DIGIT_RE.sub("N", suffix)
            suffix = _HEX_RE.sub("ADDR", suffix)
            suffix = _PATH_RE.sub("/PATH/", suffix)
            normalized = prefix + suffix
            if normalized not in seen:
                seen.add(normalized)
                deduped.append(line)
        return deduped

    def _add_context(self, all_lines: list[LogLine], selected: list[LogLine]) -> list[LogLine]:
        if self.config.context_lines <= 0:
            return selected
        by_num = {l.line_number: l for l in all_lines}
        chosen = set(selected)
        ctx = self.config.context_lines
        for ll in list(selected):
            for d in range(1, ctx + 1):
                for nb in (ll.line_number - d, ll.line_number + d):
                    if nb in by_num:
                        chosen.add(by_num[nb])
        return list(chosen)

    def _format_output(self, all_lines: list[LogLine], selected: list[LogLine]) -> str:
        selected = sorted(selected, key=lambda x: x.line_number)
        out_lines: list[str] = []
        prev_num = None
        for ll in selected:
            if prev_num is not None and ll.line_number > prev_num + 1:
                out_lines.append(f"  … ({ll.line_number - prev_num - 1} lines)")
            out_lines.append(ll.content)
            prev_num = ll.line_number
        return "\n".join(out_lines)


# ════════════════════════════════════════════════════════════════════════
# 6. 코드 압축 (code_compressor) — 파이썬은 AST, 그 외는 정규식 시그니처
# ════════════════════════════════════════════════════════════════════════

def compress_python_code(content: str, ccr: CCRStore) -> CrushResult:
    """파이썬: AST 로 함수/클래스 시그니처 + 독스트링 첫줄만 남기고 본문 접기."""
    orig_tokens = _rough_tokens(content)
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)

    lines_out: list[str] = []
    dropped = 0

    def _first_docline(node) -> str | None:
        doc = ast.get_docstring(node, clean=True)
        if not doc:
            return None
        return doc.strip().split("\n", 1)[0]

    def _sig_args(args: ast.arguments) -> str:
        parts = [a.arg for a in args.args]
        if args.vararg:
            parts.append("*" + args.vararg.arg)
        if args.kwarg:
            parts.append("**" + args.kwarg.arg)
        return ", ".join(parts)

    def _walk(node, indent: int):
        nonlocal dropped
        pad = "    " * indent
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                lines_out.append(pad + ast.unparse(child))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deco = ["@" + ast.unparse(d) for d in child.decorator_list]
                for d in deco:
                    lines_out.append(pad + d)
                prefix = "async def" if isinstance(child, ast.AsyncFunctionDef) else "def"
                ret = ""
                if child.returns is not None:
                    ret = " -> " + ast.unparse(child.returns)
                lines_out.append(f"{pad}{prefix} {child.name}({_sig_args(child.args)}){ret}:")
                doc = _first_docline(child)
                if doc:
                    lines_out.append(f'{pad}    """{doc}"""')
                body_lines = len(child.body)
                lines_out.append(f"{pad}    ...  # ({body_lines} stmts)")
                dropped += 1
            elif isinstance(child, ast.ClassDef):
                deco = ["@" + ast.unparse(d) for d in child.decorator_list]
                for d in deco:
                    lines_out.append(pad + d)
                bases = ", ".join(ast.unparse(b) for b in child.bases)
                head = f"{pad}class {child.name}" + (f"({bases})" if bases else "") + ":"
                lines_out.append(head)
                doc = _first_docline(child)
                if doc:
                    lines_out.append(f'{pad}    """{doc}"""')
                _walk(child, indent + 1)
            elif isinstance(child, ast.Assign):
                # 모듈/클래스 레벨 상수는 살림 (짧은 것만)
                try:
                    txt = ast.unparse(child)
                except Exception:
                    txt = ""
                if txt and len(txt) <= 120:
                    lines_out.append(pad + txt)

    _walk(tree, 0)
    out = "\n".join(lines_out) if lines_out else content
    return CrushResult(out, "code-python-ast", orig_tokens, _rough_tokens(out), dropped)


_GENERIC_SIG_RES = [
    re.compile(r"^\s*(export\s+)?(async\s+)?function\s+\w+\s*\([^)]*\)"),
    re.compile(r"^\s*(pub\s+)?(async\s+)?fn\s+\w+\s*\([^)]*\)"),
    re.compile(r"^\s*func\s+(\([^)]*\)\s*)?\w+\s*\([^)]*\)"),
    re.compile(r"^\s*(public|private|protected).*\s+\w+\s*\([^)]*\)"),
    re.compile(r"^\s*(class|interface|struct|enum|impl|type)\s+\w+"),
    re.compile(r"^\s*(import|from|use|package|export)\s+"),
    re.compile(r"^\s*(const|let|var)\s+\w+\s*="),
]


def compress_generic_code(content: str, ccr: CCRStore) -> CrushResult:
    """파이썬 외 언어: 정규식으로 시그니처/선언 줄만 남긴다."""
    orig_tokens = _rough_tokens(content)
    lines = content.split("\n")
    kept: list[str] = []
    dropped = 0
    for ln in lines:
        if any(rx.match(ln) for rx in _GENERIC_SIG_RES):
            kept.append(ln.rstrip())
        elif ln.strip().startswith(("//", "#", "/*", "*")):
            # 주석은 첫 문장만 유지할 수도 있으나 일단 스킵
            dropped += 1
        else:
            dropped += 1
    if not kept:
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)
    out = "\n".join(kept) + (f"\n… {dropped} body lines omitted" if dropped else "")
    if dropped:
        marker = ccr.stash(content, note=f"{dropped}_body_lines")
        out += f" {marker}"
    return CrushResult(out, "code-generic-sig", orig_tokens, _rough_tokens(out), dropped)


def compress_code(content: str, ccr: CCRStore, language: str | None = None) -> CrushResult:
    if language == "python" or language is None:
        r = compress_python_code(content, ccr)
        if r.strategy != "passthrough":
            return r
    return compress_generic_code(content, ccr)


# ════════════════════════════════════════════════════════════════════════
# 7. 일반 텍스트 / 검색결과 / diff 압축 (가벼운 룰)
# ════════════════════════════════════════════════════════════════════════

def compress_search_results(content: str, ccr: CCRStore, bias: float = 1.0) -> CrushResult:
    """grep/ripgrep 결과: 파일별로 묶고 동적 k 로 라인 선택."""
    orig_tokens = _rough_tokens(content)
    lines = [ln for ln in content.split("\n") if ln.strip()]
    keep_k = compute_optimal_k(lines, bias=bias, min_k=10, max_k=len(lines))
    if keep_k >= len(lines):
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)
    kept = lines[:keep_k]
    dropped = len(lines) - keep_k
    marker = ccr.stash(content, note=f"{dropped}_matches")
    out = "\n".join(kept) + f"\n… {dropped} more matches {marker}"
    return CrushResult(out, "search", orig_tokens, _rough_tokens(out), dropped)


def compress_plain_text(content: str, ccr: CCRStore, bias: float = 1.0) -> CrushResult:
    """일반 텍스트: 빈 줄 축소 + 중복 문장/줄 제거. LLM 안 부름(룰만)."""
    orig_tokens = _rough_tokens(content)
    raw = content.split("\n")

    # 연속 빈 줄 → 1개로
    collapsed: list[str] = []
    blank = False
    for ln in raw:
        if not ln.strip():
            if not blank:
                collapsed.append("")
            blank = True
        else:
            collapsed.append(ln.rstrip())
            blank = False

    # 완전 중복 줄 제거(순서 보존, 짧은 줄 제외)
    seen: set[str] = set()
    deduped: list[str] = []
    dropped = 0
    for ln in collapsed:
        key = ln.strip()
        if len(key) > 20 and key in seen:
            dropped += 1
            continue
        if len(key) > 20:
            seen.add(key)
        deduped.append(ln)

    out = "\n".join(deduped)
    strategy = "text-dedupe" if dropped else "text-collapse"
    if _rough_tokens(out) >= orig_tokens:
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)
    return CrushResult(out, strategy, orig_tokens, _rough_tokens(out), dropped)


def compress_diff(content: str, ccr: CCRStore) -> CrushResult:
    """git diff: 헤더 + 변경(+/-)줄만 남기고 컨텍스트 줄 축소."""
    orig_tokens = _rough_tokens(content)
    lines = content.split("\n")
    kept: list[str] = []
    ctx_run = 0
    dropped = 0
    for ln in lines:
        if _DIFF_HEADER_RE.match(ln) or ln.startswith(("+++", "---", "@@")):
            kept.append(ln)
            ctx_run = 0
        elif ln.startswith(("+", "-")):
            kept.append(ln)
            ctx_run = 0
        else:
            # 컨텍스트 줄: 최대 1줄만 유지
            if ctx_run < 1:
                kept.append(ln)
            else:
                dropped += 1
            ctx_run += 1
    if dropped == 0:
        return CrushResult(content, "passthrough", orig_tokens, orig_tokens)
    out = "\n".join(kept)
    return CrushResult(out, "diff", orig_tokens, _rough_tokens(out), dropped)


# ════════════════════════════════════════════════════════════════════════
# 8. 통합 엔진 — 타입 보고 알맞은 압축기로 라우팅
# ════════════════════════════════════════════════════════════════════════

@dataclass
class CompressResult:
    text: str                       # 압축된 결과
    refs: dict[str, str]            # 복구용 ref 맵 (ref_id → 원본조각)
    content_type: str               # 판별된 타입
    strategy: str                   # 사용된 압축 전략
    original_tokens: int
    compressed_tokens: int
    dropped: int = 0

    @property
    def ratio(self) -> float:
        """압축률(0~1). 낮을수록 많이 줄인 것."""
        if self.original_tokens == 0:
            return 1.0
        return self.compressed_tokens / self.original_tokens

    @property
    def saved_tokens(self) -> int:
        return self.original_tokens - self.compressed_tokens


class CompressEngine:
    """컨텍스트 압축 엔진. 타입 판별 후 알맞은 압축기로 보낸다.

    bias: 압축 강도. 1.0=통계 신뢰, >1=보수적(덜 압축), <1=공격적(더 압축).
    min_tokens: 이 토큰 수 미만이면 압축 안 하고 통과(오버헤드 방지).
    """

    def __init__(self, bias: float = 1.0, min_tokens: int = 50,
                 log_config: LogConfig | None = None) -> None:
        self.bias = bias
        self.min_tokens = min_tokens
        self.log_compressor = LogCompressor(log_config)

    def compress(self, content: str) -> CompressResult:
        ccr = CCRStore()
        orig_tokens = _rough_tokens(content)

        # 너무 짧으면 그냥 통과
        if orig_tokens < self.min_tokens:
            return CompressResult(content, {}, "text", "passthrough-tiny",
                                  orig_tokens, orig_tokens)

        det = detect_content_type(content)
        ct = det.content_type

        if ct == ContentType.JSON_ARRAY:
            r = crush_json(content, ccr, bias=self.bias)
        elif ct == ContentType.BUILD_OUTPUT:
            r = self.log_compressor.compress(content, ccr, bias=self.bias)
        elif ct == ContentType.SOURCE_CODE:
            r = compress_code(content, ccr, language=det.metadata.get("language"))
        elif ct == ContentType.SEARCH_RESULTS:
            r = compress_search_results(content, ccr, bias=self.bias)
        elif ct == ContentType.GIT_DIFF:
            r = compress_diff(content, ccr)
        elif ct == ContentType.TABULAR:
            # 표는 JSON 컬럼형만큼 안전하지 않아 일반 텍스트 룰로
            r = compress_plain_text(content, ccr, bias=self.bias)
        else:
            r = compress_plain_text(content, ccr, bias=self.bias)

        # 압축이 손해면(오히려 늘거나 그대로) 원본 유지, ccr 버림
        if r.compressed_tokens >= orig_tokens and r.dropped == 0:
            return CompressResult(content, {}, ct.value, "passthrough-noloss",
                                  orig_tokens, orig_tokens)

        return CompressResult(r.text, ccr.as_dict(), ct.value, r.strategy,
                              orig_tokens, r.compressed_tokens, r.dropped)


# ════════════════════════════════════════════════════════════════════════
# 9. 간편 함수 — DEMOS 에서 바로 쓰는 진입점
# ════════════════════════════════════════════════════════════════════════

_DEFAULT_ENGINE = CompressEngine()


def compress(content: str, bias: float = 1.0) -> tuple[str, dict[str, str]]:
    """간편 압축. (압축본, refs) 튜플 반환.

    refs 는 {ref_id: 원본조각} 딕셔너리. 압축본 안의 <<ccr:ID>> 마커를
    retrieve(ID, refs) 로 되찾을 수 있다."""
    eng = _DEFAULT_ENGINE if bias == 1.0 else CompressEngine(bias=bias)
    r = eng.compress(content)
    return r.text, r.refs


def compress_detailed(content: str, bias: float = 1.0) -> CompressResult:
    """메타데이터까지 필요할 때. CompressResult 반환."""
    eng = _DEFAULT_ENGINE if bias == 1.0 else CompressEngine(bias=bias)
    return eng.compress(content)


# ════════════════════════════════════════════════════════════════════════
# 10. CLI / 셀프테스트
# ════════════════════════════════════════════════════════════════════════

def _demo() -> None:
    print("=" * 60)
    print("ctx_compress 셀프테스트")
    print("=" * 60)

    # 1) JSON 배열
    rows = [{"id": i, "level": "INFO", "msg": f"job {i} done", "ok": True} for i in range(50)]
    js = json.dumps(rows)
    r = compress_detailed(js)
    print(f"\n[JSON] {r.content_type}/{r.strategy}: "
          f"{r.original_tokens}→{r.compressed_tokens} tok "
          f"({r.ratio:.0%}), dropped={r.dropped}, refs={len(r.refs)}")

    # 2) 로그
    log = "\n".join(
        [f"2026-01-{i:02d} INFO starting task {i}" for i in range(1, 30)] +
        ["2026-01-30 ERROR connection refused: 0x7fff to /var/run/x/",
         "  at network.connect(socket.py:42)",
         "2026-01-30 ERROR connection refused: 0x8fff to /var/run/y/",
         "=== 1 passed, 2 failed ==="]
    )
    r = compress_detailed(log)
    print(f"[LOG]  {r.content_type}/{r.strategy}: "
          f"{r.original_tokens}→{r.compressed_tokens} tok "
          f"({r.ratio:.0%}), dropped={r.dropped}")

    # 3) 파이썬 코드
    code = '''
import os

class Worker:
    """작업 처리기."""
    def __init__(self, name):
        self.name = name
        self.count = 0

    def run(self, jobs):
        """잡을 순차 처리한다."""
        for j in jobs:
            self.count += 1
            print(j)
        return self.count
'''
    r = compress_detailed(code)
    print(f"[CODE] {r.content_type}/{r.strategy}: "
          f"{r.original_tokens}→{r.compressed_tokens} tok ({r.ratio:.0%})")

    # 4) CCR 복구 테스트
    r = compress_detailed(js)
    markers = find_markers(r.text)
    if markers:
        original = retrieve(markers[0], r.refs)
        ok = original is not None
        print(f"[CCR]  마커 {len(markers)}개, 복구 {'성공' if ok else '실패'}")
    else:
        print("[CCR]  이번 케이스는 드롭 없음(복구 대상 없음)")

    print("\n" + "=" * 60)
    print("셀프테스트 끝")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # 파일 압축: python ctx_compress.py <file> [bias]
        path = sys.argv[1]
        bias = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        res = compress_detailed(data, bias=bias)
        print(res.text)
        print(f"\n--- {res.content_type}/{res.strategy}: "
              f"{res.original_tokens}→{res.compressed_tokens} tok "
              f"({res.ratio:.0%}), dropped={res.dropped} ---", file=sys.stderr)
    else:
        _demo()
