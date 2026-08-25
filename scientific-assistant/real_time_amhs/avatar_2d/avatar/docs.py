# -*- coding: utf-8 -*-
"""
참고 자료 (MD/TXT) — 서버측 보관 + 검색 주입.

파일을 통째로 프롬프트에 넣으면 컨텍스트가 터진다.
예산(docBudget)을 넘으면 헤딩/빈줄 기준으로 문단을 쪼개고,
질문과 겹치는 단어가 많은 문단부터 예산이 찰 때까지 채워 넣는다.
(기존 app.js 의 docsContext 를 그대로 파이썬으로 옮긴 것)
"""
import json
import os
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

        q = (query or "").lower()
        terms = re.findall(r"[가-힣A-Za-z0-9]{2,}", q)
        # ★컬럼 이름은 통째로도 본다 — 'M16HUB.STRATE.STB.3F_STORAGE_UTIL' 을
        #   조각(3f/storage/util)으로만 쪼개면 엉뚱한 FAB 절이 이긴다.
        #   길이가 점수라, 통째 일치가 확실히 앞선다.
        terms += [t for t in re.findall(r"[a-z0-9][a-z0-9_.]{3,}", q)
                  if ("_" in t or "." in t)]
        for c in chunks:
            low = c["t"].lower()
            for w in terms:
                if w in low:
                    # 컬럼 이름 통째 일치(_ · . 포함)는 크게 — 'storage','util'
                    # 같은 조각이 여러 번 걸린 엉뚱한 절이 이기면 안 된다
                    c["score"] += len(w) * (5 if ("_" in w or "." in w) else 1)
        chunks.sort(key=lambda c: -c["score"])
        # ★겹치는 낱말이 하나도 없으면 **안 넣는다.** 예전엔 점수 0 인 문단이
        #   그대로 실려서, "안녕" 같은 잡담에도 분석 문서가 붙어 예산을 먹었다.
        hit = [c for c in chunks if c["score"] > 0]
        if not hit:
            return ""
        chunks = hit

        out = ""
        for c in chunks:
            if len(out) + len(c["t"]) + len(c["name"]) + 8 > budget:
                continue
            out += "### " + c["name"] + "\n" + c["t"] + "\n\n"
            if len(out) > budget * 0.96:
                break
        return out or chunks[0]["t"][:budget]


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

# ── 기본 참고 자료 시드 ──────────────────────────────────────────────
# ★데이터 분석 스킬을 새로 쓰지 않는다. 데모스(scientific-skills)에 이미
#   있으니 그대로 가져와 참고 자료로 등록한다. 자료는 질문과 겹치는 것만
#   골라 주입되므로(context), 평소 프롬프트를 늘리지 않는다.
SEED_DOCS = {
    "데이터분석_탐색적분석(EDA).md": "exploratory-data-analysis",
    "데이터분석_통계검정.md": "statistical-analysis",
    "데이터분석_검정선택가이드.md": ("statistical-analysis",
                                     "references/test_selection_guide.md"),
    "데이터분석_가정점검.md": ("statistical-analysis",
                               "references/assumptions_and_diagnostics.md"),
}

# 현장 자료 — real_time_amhs 안팎에 이미 있는 md 를 그대로 등록한다.
#   (경로, 등록 이름). 스킬 저장소에도 있지만 **참고 자료로도** 둔다 —
#   자료 탭에서 사람이 켜고 끄고 지울 수 있어야 하고, 질문에 따라 스킬이
#   아니라 자료 쪽에서 걸리는 편이 나을 때가 있다.
SEED_LOCAL = [
    ("docs/FAB별_위험도_스코어.md", "관제_FAB별_위험도_스코어.md"),
    ("../m16_hub_skills/m16_hub_임계값_v3.5.md", "관제_임계값.md"),
    ("../m16_hub_skills/m16_hub_카파시_v3.5.md", "관제_룰과_점수산식.md"),
    ("../m16_hub_skills/m16_hub_결과해석_도메인_고객인용V3.5.md", "관제_결과해석과_용어표준.md"),
    ("../m16_hub_skills/m16_hub_일반_v3.5.md", "관제_실행과_사용법.md"),
    ("m16_hub_skills/m16_hub_임계값_v3.5.md", "관제_임계값.md"),
    ("m16_hub_skills/m16_hub_카파시_v3.5.md", "관제_룰과_점수산식.md"),
    ("m16_hub_skills/m16_hub_결과해석_도메인_고객인용V3.5.md", "관제_결과해석과_용어표준.md"),
    ("m16_hub_skills/m16_hub_일반_v3.5.md", "관제_실행과_사용법.md"),
]


def seed_local_docs(store, base_dir):
    """real_time_amhs 안팎의 현장 md 를 참고 자료로 등록한다."""
    rt = os.path.dirname(str(base_dir))            # real_time_amhs
    have = {d["name"] for d in store.list()}
    done = []
    for rel, name in SEED_LOCAL:
        if name in have:
            continue
        path = os.path.normpath(os.path.join(rt, rel))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
        except OSError:
            continue
        if store.add(name, body):
            have.add(name)
            done.append(name)
    return done

# ★원문이 영어라 한국어 질문과 겹치는 낱말이 없다 — 그대로 두면 등록만 되고
#   **한 번도 안 걸린다.** 문서 앞에 한글 색인을 붙여 두면 "이상치 봐줘",
#   "분포 어때" 같은 질문에 그 문단이 걸린다. (context 는 겹치는 낱말로 고른다)
SEED_INDEX = {
    "데이터분석_탐색적분석(EDA).md":
        "탐색적 데이터 분석 EDA 절차 — 파일 구조·행·컬럼 파악, 결측치·빠진 값, "
        "이상치·튀는 값, 분포·히스토그램, 요약통계 평균 중앙값 최대 최소, "
        "상관관계, 시계열 추이·구간, 데이터 품질 점검, 표본 확인, 다음 분석 제안. "
        "CSV·표 데이터를 처음 받았을 때 무엇부터 볼지.",
    "데이터분석_통계검정.md":
        "통계 검정 선택과 보고 — 가설 검정, 유의성, p값, 효과크기, 신뢰구간, "
        "표본 수·검정력, 평균 비교, 비율 비교, 상관·회귀, 정규성, 결과 쓰는 법.",
    "데이터분석_검정선택가이드.md":
        "어떤 검정을 쓸지 고르는 표 — 자료 종류(연속·범주·순위), 집단 수, "
        "짝지음 여부, 정규성 만족 여부에 따른 검정 선택.",
    "데이터분석_가정점검.md":
        "검정 전에 확인할 가정 — 정규성, 등분산, 독립성, 이상치 영향, "
        "잔차 진단, 가정이 깨졌을 때의 대안(비모수·변환).",
}


def _skills_dir(base_dir):
    """avatar_2d → real_time_amhs → scientific-assistant/scientific-skills.
    현장에서 real_time_amhs 만 풀어 쓰는 경우를 위해 동봉본도 본다."""
    rt = os.path.dirname(str(base_dir))
    for d in (os.path.join(os.path.dirname(rt), "scientific-skills"),
              os.path.join(rt, "analysis_skills"),
              os.path.join(rt, "scientific-skills")):
        if os.path.isdir(d):
            return d
    return ""


def seed_docs(store, base_dir):
    """데모스의 데이터 분석 스킬 md 를 참고 자료로 등록한다. 등록한 이름 목록."""
    root = _skills_dir(base_dir)
    if not root:
        return []
    have = {d["name"] for d in store.list()}
    done = []
    for name, src in SEED_DOCS.items():
        if name in have:
            continue                       # 사용자가 지웠거나 고쳤을 수 있다
        skill, rel = (src, "SKILL.md") if isinstance(src, str) else src
        path = os.path.join(root, skill, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
        except OSError:
            continue
        head = ("<!-- 데모스 scientific-skills/{}/{} 에서 가져옴 -->\n"
                "## 무엇에 쓰나 (한글 색인)\n{}\n\n"
                .format(skill, rel, SEED_INDEX.get(name, "")))
        if store.add(name, head + body):
            done.append(name)
    return done


# ── 컬럼 사전 ─────────────────────────────────────────────────────────
# ★"이 데이터가 무엇인지" 에 답하려면 컬럼의 뜻이 있어야 한다. 새로 쓰지 않고
#   real_time_amhs/fab_score.py 의 WATCH(FAB별 감시 컬럼·임계) 를 그대로 편다.
#   CSV 를 분석할 때 이 사전과 합쳐야 "AVGTOTALTIME1MIN 이 9분을 넘었다" 를
#   "M16HUB 반송지연 임계 초과" 로 읽을 수 있다.
COLDICT_NAME = "관제_컬럼사전.md"


def _fab_score_mod(base_dir):
    """real_time_amhs/fab_score.py 를 불러온다 (없으면 None)."""
    import importlib
    import sys as _sys
    rt = os.path.dirname(str(base_dir))            # real_time_amhs
    if rt not in _sys.path:
        _sys.path.insert(0, rt)
    try:
        return importlib.import_module("fab_score")
    except Exception:                              # noqa: BLE001
        return None


def build_column_dict(base_dir):
    """감시 컬럼 → FAB · 룰(한글) · 임계 · 단위 표. 못 만들면 ''."""
    fs = _fab_score_mod(base_dir)
    if fs is None or not getattr(fs, "WATCH", None):
        return ""
    ko = {r["code"]: r["label"] for r in getattr(fs, "RULES", [])}
    L = ["# 관제 컬럼 사전 (AMOS 컬럼이 무슨 뜻인가)",
         "",
         "CSV·데이터에 나오는 컬럼 이름의 뜻과 임계값입니다. 컬럼 이름, 지표, "
         "무슨 뜻, 무엇을 재는지, 임계, 기준값, 단위, 어느 FAB 인지를 여기서 찾습니다.",
         "",
         ]
    # ★FAB 마다 절을 나눈다. 표 하나로 두면 덩어리가 커서 예산에 안 들어가
    #   통째로 버려진다 — 등록해 놓고 한 번도 안 걸리는 자료가 된다.
    for fab in sorted(fs.WATCH):
        L += ["", "## {} 감시 컬럼".format(fab),
              "| 룰 | 지표 | AMOS 컬럼 | 임계 | 단위 |",
              "|---|---|---|---|---|"]
        for code, conds in fs.WATCH[fab].items():
            for c in conds or []:
                thr = c.get("thr")
                L.append("| {} | {} | `{}` | {} | {} |".format(
                    ko.get(code, code), c.get("label") or "",
                    c.get("amos") or "", "" if thr is None else thr,
                    c.get("unit") or ""))
    L += ["", "## 점수 컬럼 (unified_risk_score · area_score)",
          "- `unified_risk_score` — 전체 위험도(1~100). 등급 컷 60/71/85 "
          "(경계/위험/초위험).",
          "- `{FAB}_score` · `area_score` — 영역 점수(최대 50). 룰 배점의 합.",
          "- `hot_area` — 가장 높은 영역, `stage_name` — 단계, `reason` — 발동 룰."]
    return "\n".join(L)


def seed_column_dict(store, base_dir):
    """컬럼 사전을 참고 자료로 등록한다 (이미 있으면 그대로 둔다)."""
    if any(d["name"] == COLDICT_NAME for d in store.list()):
        return ""
    body = build_column_dict(base_dir)
    if not body:
        return ""
    return COLDICT_NAME if store.add(COLDICT_NAME, body) else ""
