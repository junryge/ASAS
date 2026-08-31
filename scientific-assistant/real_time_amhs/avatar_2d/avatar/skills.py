# -*- coding: utf-8 -*-
"""
skills.py — 버추얼 에이전트의 스킬 (데모스 skills.py 의 핵심을 네이티브 포팅)

데모스에서 가져온 것 / 버린 것
    가져옴: SKILL.md 형식(YAML 머리말 name/description), 검증 규칙,
            폴더 스캔, 질문 매칭 주입, 생성(검증→저장)
    버림  : 과학 스킬 372개 카탈로그, 리랭커, 병렬 그룹핑 — 전부 데모스
            서버(Flask/requests) 전용이고, 아바타는 표준 라이브러리만 쓰는
            독립 프로세스라 통째로는 못 심는다. 형식이 같으므로 여기서 만든
            스킬 폴더를 데모스 scientific-skills/ 에 그대로 복사해도 돌아간다.

저장 위치
    data/skills/<이름>/SKILL.md          (data/ 는 실행 시 생기고 커밋 안 됨)

시드
    real_time_amhs/docs/FAB별_위험도_스코어.md 가 있으면 fab-score 스킬로
    심는다 — 도메인 지식(임계·배점·함정)이 이 스킬을 타고 대답에 들어간다.
"""
import os
import re

from . import terms

MAX_LINES = 500          # 데모스 권장치 — 넘으면 경고 (막지는 않는다)
MAX_INJECT = 4           # 한 질문에 주입할 스킬 수
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


class SkillStore:
    def __init__(self, root):
        self.root = str(root)
        os.makedirs(self.root, exist_ok=True)

    # ── 스캔/읽기 ─────────────────────────────────────────────────────────
    def _dir(self, name):
        return os.path.join(self.root, name)

    def _md_path(self, name):
        return os.path.join(self._dir(name), "SKILL.md")

    def list(self):
        out = []
        if not os.path.isdir(self.root):
            return out
        for fn in sorted(os.listdir(self.root)):
            p = self._md_path(fn)
            if not os.path.isfile(p):
                continue
            meta = parse_front(self.read(fn) or "")
            out.append({"name": fn,
                        "description": meta.get("description", ""),
                        "lines": meta.get("_lines", 0),
                        "bytes": os.path.getsize(p)})
        return out

    def read(self, name):
        """SKILL.md 전문 — '완전하게' 내주는 게 목적이라 자르지 않는다."""
        if not NAME_RE.match(str(name or "")):
            return None
        p = self._md_path(name)
        if not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8") as f:
            return f.read()

    def save(self, name, md_text):
        """검증 통과 시 저장. 반환 (ok, errors, warnings)."""
        ok, errors, warnings = validate(md_text, name)
        if not ok:
            return False, errors, warnings
        os.makedirs(self._dir(name), exist_ok=True)
        with open(self._md_path(name), "w", encoding="utf-8") as f:
            f.write(md_text)
        return True, [], warnings

    def delete(self, name):
        p = self._md_path(name)
        if not os.path.isfile(p):
            return False
        os.remove(p)
        try:
            os.rmdir(self._dir(name))
        except OSError:
            pass                     # references 등 딸린 파일이 있으면 남긴다
        return True

    # ── 질문 매칭 주입 ────────────────────────────────────────────────────
    # ★질문 상투어는 빼고 센다. '어떻게' 는 거의 모든 설명에 들어 있어서
    #   ("무엇을 왜 어떻게 하는지") 뜻 있는 낱말과 같은 점수를 먹었다 —
    #   "이상치 어떻게 봐" 가 엉뚱한 스킬로 갔다. 조각(어떻·떻게)도 같이 뺀다.
    STOP = {"어떻게", "어떻", "떻게", "뭐야", "무엇", "뭔가", "알려줘", "알려",
            "려줘", "보여줘", "보여", "여줘", "해야", "하는", "있나", "있어",
            "봐줘", "인가", "인지", "얼마", "어디", "그럼", "이거", "그거",
            "저거", "좀만", "해줘", "주세", "세요", "합니", "니까", "까요"}

    def context(self, question, budget=6000):
        """질문과 겹치는 스킬 본문을 예산 안에서 골라 주입 텍스트로.

        docs.py 와 같은 철학 — 형태소 분석기 없이 2글자 이상 토큰 겹침.
        스킬이 몇 개 안 되므로(개인 도구) 전수 비교로 충분하다.
        """
        q_tokens = _tokens(question) - self.STOP
        if not q_tokens:
            return ""
        scored = []
        for s in self.list():
            md = self.read(s["name"]) or ""
            head_tokens = _tokens(s["name"] + " " + s["description"])
            body_tokens = _tokens(md)
            # 낱말 **길이**로 센다 — 개수로만 세면 '이상치' 가 통째로 걸린
            # 스킬과 조각('이상')만 걸린 스킬이 같은 점수가 된다
            hit_head = sum(len(w) for w in q_tokens & head_tokens)
            hit = sum(len(w) for w in q_tokens & (head_tokens | body_tokens))
            # ★본문 두 낱말을 요구하면 "검정 뭐 써야 해" 처럼 짧고 분명한
            #   질문이 아무것도 못 받는다. 설명(description)은 사람이 고른
            #   말이라 하나만 걸려도 신호가 세다 — 그때는 통과시킨다.
            if hit >= 4 or hit_head >= 2:
                # 설명 일치를 크게 — 본문이 긴 스킬이 낱말 수로만 이기면
                # '이상치' 질문에 엉뚱한 스킬이 먼저 붙는다
                scored.append((hit_head * 10 + hit, s["name"], md))
        scored.sort(key=lambda x: -x[0])
        out, used = [], 0
        for _hit, name, md in scored[:MAX_INJECT]:
            body = strip_front(md).strip()
            take = body[:max(0, budget - used)]
            if not take:
                break
            used += len(take)
            out.append("### 스킬: {}\n{}".format(name, take))
        return "\n\n".join(out)


def _tokens(text):
    toks = set()
    for w in re.split(r"[^0-9A-Za-z가-힣_]+", str(text or "").lower()):
        if len(w) >= 2:
            toks.add(w)
            # 한글 복합어 대응 — '반송시간' 이 '반송' 질문에도 걸리게 2글자 조각
            if re.match(r"^[가-힣]{3,}$", w):
                for i in range(len(w) - 1):
                    toks.add(w[i:i + 2])
    return toks


# ────────────────────────────── SKILL.md 형식 ──────────────────────────────
def parse_front(md_text):
    """YAML 머리말에서 name/description 만 뽑는다 (딱 그 둘만 쓴다)."""
    meta = {"_lines": len(str(md_text or "").splitlines())}
    m = _FM_RE.match(md_text or "")
    if not m:
        return meta
    for line in m.group(1).splitlines():
        kv = re.match(r"^(name|description)\s*:\s*(.*)$", line.strip())
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip(">").strip()
        elif "description" in meta and line.startswith(("  ", "\t")) \
                and not re.match(r"^\s*\w+\s*:", line):
            meta["description"] = (meta["description"] + " " + line.strip()).strip()
    return meta


def strip_front(md_text):
    return _FM_RE.sub("", md_text or "", count=1)


def compose(name, description, body):
    """name/desc/본문 → SKILL.md. (데모스 api_skill_create 의 조합 규칙)"""
    return "---\nname: {}\ndescription: >\n  {}\n---\n\n{}".format(
        name, str(description).strip(), str(body).strip())


def validate(md_text, name=""):
    """데모스 _validate_skill_content 이식. 반환 (ok, errors, warnings)."""
    errors, warnings = [], []
    txt = str(md_text or "")
    m = _FM_RE.match(txt)
    if not m:
        errors.append("YAML 머리말(---)이 없습니다. compose() 형식으로 만드세요.")
    else:
        meta = parse_front(txt)
        n = meta.get("name", "")
        if not n:
            errors.append("머리말에 name 이 없습니다.")
        elif not NAME_RE.match(n) or len(n) > 64:
            errors.append("이름은 소문자+숫자+하이픈, 최대 64자: " + n)
        elif name and n != name:
            errors.append("폴더 이름({})과 머리말 name({})이 다릅니다.".format(name, n))
        desc = meta.get("description", "")
        if not desc:
            errors.append("머리말에 description 이 없습니다.")
        elif "<" in desc or ">" in desc:
            errors.append("description 에 꺾쇠(<,>)를 쓸 수 없습니다.")
        if not strip_front(txt).strip():
            warnings.append("본문이 비어 있습니다.")
    lines = len(txt.splitlines())
    if lines > MAX_LINES:
        warnings.append("본문이 {}줄입니다. {}줄 이하 권장.".format(lines, MAX_LINES))
    return (not errors), errors, warnings


# ────────────────────────────── HTML 완전 출력 ──────────────────────────────
def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def to_html(name, md_text):
    """SKILL.md → 단독 HTML 한 장. 사내망엔 CDN 이 없어서 전부 안에 넣는다.

    표준 라이브러리에는 마크다운 변환기가 없다 — 제목/표/코드/목록/굵게만
    처리하는 최소 변환이고, 그 이상은 <pre> 로 정직하게 보여 준다.
    """
    body = strip_front(md_text or "")
    out, in_code, in_table, in_list = [], False, False, False

    def close_blocks():
        nonlocal in_table, in_list
        if in_table:
            out.append("</table>")
            in_table = False
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in body.splitlines():
        if line.strip().startswith("```"):
            close_blocks()
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(_esc(line))
            continue
        if re.match(r"^\|[\s:-]+\|", line.replace("-", "-")) \
                and re.fullmatch(r"[|\s:\-]+", line.strip()):
            continue                              # 표 구분선
        if line.startswith("|"):
            if not in_table:
                close_blocks()
                out.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append("<tr>" + "".join("<td>" + _inline(c) + "</td>"
                                        for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            close_blocks()
            h = len(m.group(1))
            out.append("<h{n}>{t}</h{n}>".format(n=h, t=_inline(m.group(2))))
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + _inline(re.sub(r"^\s*[-*]\s+", "", line)) + "</li>")
            continue
        if in_list and not line.strip():
            out.append("</ul>")
            in_list = False
            continue
        if line.strip():
            out.append("<p>" + _inline(line) + "</p>")
    close_blocks()
    if in_code:
        out.append("</pre>")

    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>" + _esc(name) + "</title><style>"
            "body{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;"
            "max-width:900px;margin:0 auto;padding:24px;line-height:1.65;"
            "color:#1a2230;background:#f6f8fb}"
            "h1{font-size:26px}h2{font-size:20px;margin-top:34px}"
            "h3{font-size:16px}code,pre{font-family:Consolas,monospace;"
            "background:#eceff4;border-radius:4px}code{padding:1px 5px;font-size:.92em}"
            "pre{padding:12px;overflow-x:auto;border:1px solid #d7dde6}"
            "table{border-collapse:collapse;margin:10px 0;font-size:13.5px}"
            "td{border:1px solid #cfd6e0;padding:6px 10px;vertical-align:top}"
            "tr:first-child td{background:#e6ebf2;font-weight:700}"
            "</style></head><body>" + "\n".join(out) + "</body></html>")


def _inline(s):
    s = _esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


# ────────────────────────────── LLM 로 스킬 초안 ──────────────────────────────
# ★스킬 작성 규칙 — 데모스의 skill-creator·writing-skills 를 이 시스템 말로
#   옮긴 것. 예전 프롬프트는 네 줄짜리라 "요약문" 이 나왔지, 다음에 쓸 수 있는
#   스킬이 안 나왔다. 스킬은 **다음 사람이 그대로 따라 할 수 있어야** 한다.
DRAFT_PROMPT = (
    "너는 SKILL.md 작성기다. 아래 재료(대화·관제 근거·첨부 분석)에서 "
    "**다시 쓸 수 있는 절차**를 뽑아 스킬 본문을 만든다.\n"
    "\n"
    "[반드시 지킬 것]\n"
    "1. 마크다운 본문만 출력한다. YAML 머리말(---)은 서버가 붙이므로 쓰지 마라.\n"
    "2. **재료에 있는 사실만** 쓴다. 재료에 없는 숫자·임계·컬럼명을 지어내면 "
    "   그 스킬은 다음 사람을 속인다. 모르는 값은 '확인 필요' 라고 적는다.\n"
    "3. 룰은 한글 이름으로 쓴다 (반송지연·Queue 누적·리프터 정체·Storage FULL "
    "   ·4분초과·분류기 대기·운영자 용량변경). 영문 약칭을 쓰지 마라.\n"
    "4. 한국어로 쓰고, {} 줄을 넘기지 마라.\n"
    "\n"
    "[이 차례로 쓴다 — 절 제목을 그대로 쓴다]\n"
    "# <제목 한 줄>\n"
    "## 언제 쓰나\n"
    "   어떤 질문·상황에서 이 스킬을 꺼내는지. 한두 줄.\n"
    "## 무엇을 보나\n"
    "   봐야 할 컬럼·지표·임계를 표로. | 항목 | 컬럼 | 임계 | 뜻 |\n"
    "   재료에 컬럼명이 있으면 반드시 그대로 적는다.\n"
    "## 절차\n"
    "   1) 2) 3) 번호를 매겨, 그대로 따라 하면 같은 결론이 나오게 쓴다.\n"
    "   각 단계에 '무엇을 보고 → 무엇으로 판단' 을 넣는다.\n"
    "## 판단 기준\n"
    "   어떤 값이면 정상/경계/위험인지. 근거에 컷이 있으면 그 값을 쓴다.\n"
    "## 함정\n"
    "   틀리기 쉬운 것. 최소 두 개. (겪은 것이 재료에 있으면 그것부터)\n"
    "## 예시\n"
    "   재료에 실제 사례가 있으면 값과 함께 한 건. 없으면 이 절을 빼라.\n"
    "\n"
    "[좋은 스킬 / 나쁜 스킬]\n"
    "· 나쁨: \"OHT 가동률을 확인한다\" — 무엇을 보고 얼마면 문제인지가 없다.\n"
    "· 좋음: \"M14.QUE.OHT.OHTUTIL 이 95% 이상이면 유입을 줄인다 "
    "(임계 95, 근거: 관제 임계표)\"\n"
    "· 나쁨: 대화를 요약한다. · 좋음: 다음에 같은 일이 왔을 때 할 일을 적는다."
    "\n").format(MAX_LINES)

# 초안이 스킬 꼴을 갖췄는지 — 없으면 한 번 더 시킨다 (검증 전에 거른다)
NEED_SECTIONS = ("## 언제 쓰나", "## 절차", "## 함정")


def draft_gaps(body):
    """빠진 절 목록. 비어 있으면 스킬 꼴을 갖춘 것."""
    txt = str(body or "")
    return [s for s in NEED_SECTIONS if s not in txt]


# 현장 도메인 스킬 — real_time_amhs 옆(scientific-assistant/m16_hub_skills)에
# 이미 있는 것을 그대로 쓴다. ★새로 쓰지 않는다: 룰 한글명·용어 표준·임계값·
# 결과 해석 규칙이 전부 거기 있고, 우리가 다시 쓰면 두 벌이 어긋난다.
# 이름은 ASCII 만 (NAME_RE) — 한글 이름은 저장이 거부된다. 무슨 스킬인지는
# 원본의 description 이 한글로 들고 온다.
HUB_SKILLS = {
    "m16-hub-result": "m16_hub_결과해석_도메인_고객인용V3.5.md",
    "m16-hub-threshold": "m16_hub_임계값_v3.5.md",
    "m16-hub-capacity": "m16_hub_카파시_v3.5.md",
    "m16-hub-general": "m16_hub_일반_v3.5.md",
}


def _hub_dir(base_dir):
    """현장 스킬 폴더를 찾는다.

    ★현장에서는 real_time_amhs 만 풀어 쓰는 경우가 있다 — 그때 원래 자리
      (scientific-assistant/m16_hub_skills)가 없으면 스킬이 하나도 안 심긴다.
      그래서 동봉본(real_time_amhs/m16_hub_skills)도 본다. **원래 자리가
      먼저다** — 현장에서 고친 것이 있으면 그쪽이 진짜다.
    """
    rt = os.path.dirname(str(base_dir))            # real_time_amhs
    for d in (os.path.join(os.path.dirname(rt), "m16_hub_skills"),
              os.path.join(rt, "m16_hub_skills")):
        if os.path.isdir(d):
            return d
    return os.path.join(os.path.dirname(rt), "m16_hub_skills")


def seed_hub_skills(store, base_dir):
    """현장 스킬 md 를 스킬 저장소에 심는다. 심은 이름 목록을 돌려준다."""
    src_dir = _hub_dir(base_dir)
    done = []
    for name, fname in HUB_SKILLS.items():
        if store.read(name):
            continue                                # 사용자가 고쳤을 수 있다
        path = os.path.join(src_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
        except OSError:
            continue
        # 원본에 YAML 머리말(name/description)이 이미 있다 — 이름만 우리 규칙
        # (소문자·하이픈)으로 맞춰 다시 씌운다.
        desc = _desc_of(body) or name
        ok, _e, _w = store.save(name, compose(name, desc, _strip_fm(body)))
        if ok:
            done.append(name)
    return done


def _strip_fm(md):
    m = _FM_RE.match(str(md or ""))
    return md[m.end():] if m else md


def _desc_of(md):
    m = _FM_RE.match(str(md or ""))
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.strip().lower().startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


# 데이터 분석 스킬 — 데모스(scientific-skills)의 것을 그대로 등록한다.
# ★참고 자료에도 같은 내용이 있지만, 스킬 목록(/스킬 목록)에서 보이고 스킬로
#   주입돼야 "무엇을 할 줄 아는가" 가 드러난다. 중복 주입은 llm 쪽에서 막는다.
# ★데모스의 exploratory-data-analysis 는 .pdb/.fasta/.bam 같은 **과학 파일
#   포맷 카탈로그**다 (현미경·유전체·화학). 관제 CSV 분석에는 쓸모가 없고,
#   붙여 두면 서윤이 분자동역학 얘기를 꺼낸다 — 그래서 스킬로 안 심는다.
#   대신 이 시스템의 데이터로 쓴 data-analysis 를 심는다 (analysis_skills/).
#   일반 통계 방법(검정 선택·가정 점검)은 파일 포맷과 무관하므로 남긴다.
ANALYSIS_SKILLS = {
    "data-analysis": ("data-analysis", "SKILL.md",
                      "관제 데이터(발동이벤트·사건단위 CSV) 분석 방법 — "
                      "무엇부터 볼지, 이상치·결측·분포·추이·구간, 전 행 재계산으로 "
                      "무엇을 물어볼 수 있는지, 보고 형식, 자주 틀리는 것"),
    "stats-choose": ("statistical-analysis", "references/test_selection_guide.md",
                     "어떤 검정을 쓸지 고르기 — 자료 종류·집단 수·짝지음·"
                     "정규성에 따른 검정 선택표"),
    "stats-assume": ("statistical-analysis", "references/assumptions_and_diagnostics.md",
                     "검정 전 가정 점검 — 정규성·등분산·독립성·이상치 영향, "
                     "가정이 깨졌을 때의 대안"),
    # 스킬을 **만드는** 법 — 서윤이 대화·데이터에서 새 스킬을 뽑아낼 때 본다.
    # (이건 파일 포맷 얘기가 아니라 SKILL.md 형식·작성법이라 그대로 쓸 수 있다)
    "skill-creator": ("skill-creator", "SKILL.md",
                      "스킬 만들기 — SKILL.md 구조(YAML 머리말 name/description), "
                      "폴더 구성, 좋은 설명 쓰는 법, 검증과 반복"),
    "writing-skills": ("writing-skills", "SKILL.md",
                       "스킬 잘 쓰는 법 — 언제 쓰는 스킬인지 드러내기, 분량, "
                       "예시와 함정 넣기, 점진적 공개"),
    "prompt-engineer": ("anthropic-prompt-engineer", "SKILL.md",
                        "프롬프트 작성 — 지시를 명확히, 예시와 형식 지정, "
                        "역할·제약·출력 형식 잡는 법"),
    # 채워 넣는 **틀** — 초안을 쓸 때 이걸 그대로 채운다 (아래 draft_template)
    "skill-template": ("skill-template", "SKILL.md",
                       "새 스킬을 쓸 때 채우는 틀 — 표로 무엇을 보는지, "
                       "번호로 절차, 판단 기준, 함정. 관제 스킬과 같은 꼴"),
    "skill-patterns": ("skill-creator", "references/output-patterns.md",
                       "출력 형식 패턴 — 템플릿·표·단계별 출력을 어떻게 "
                       "정해 주는지"),
    "skill-workflow": ("skill-creator", "references/workflows.md",
                       "절차형 스킬 패턴 — 여러 단계를 순서대로 밟게 쓰는 법"),
}

TEMPLATE_SKILL = "skill-template"


def draft_template(store):
    """초안에 실을 **틀**. 스킬로 심어 둔 것을 그대로 읽어 쓴다.

    ★틀을 코드에 또 적지 않는다 — 사용자가 스킬을 고치면 초안도 같이 바뀌어야
      한다. 틀이 없으면 빈 문자열 (DRAFT_PROMPT 의 차례 설명만으로도 돈다).
    """
    md = store.read(TEMPLATE_SKILL) if store else None
    if not md:
        return ""
    body = strip_front(md).strip()
    # '쓸 때 규칙' 아래는 사람용 안내라 초안 재료로는 필요 없다
    cut = body.find("## 쓸 때 규칙")
    return (body[:cut] if cut > 0 else body).strip()


def _analysis_dir(base_dir, skill):
    """스킬마다 폴더가 다르다 — data-analysis 는 우리가 쓴 것(analysis_skills),
    통계 방법은 데모스(scientific-skills)에도 동봉본에도 있을 수 있다."""
    rt = os.path.dirname(str(base_dir))            # real_time_amhs
    for d in (os.path.join(rt, "analysis_skills"),
              os.path.join(os.path.dirname(rt), "scientific-skills")):
        if os.path.isdir(os.path.join(d, skill)):
            return d
    return ""


def seed_analysis_skills(store, base_dir):
    """데이터 분석 스킬을 스킬 저장소에 등록한다. 등록한 이름 목록."""
    done = []
    for name, (skill, rel, desc) in ANALYSIS_SKILLS.items():
        if store.read(name):
            continue
        root = _analysis_dir(base_dir, skill)
        if not root:
            continue
        path = os.path.join(root, skill, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
        except OSError:
            continue
        ok, _e, _w = store.save(name, compose(name, desc, _strip_fm(body)))
        if ok:
            done.append(name)
    return done


def seed_hubroom(store, base_dir):
    """M16 HUBROOM 반송 **도메인 지식**을 스킬로 심는다.

    ★위키(MCP)와 무엇이 다른가
      위키는 낱말이 걸릴 때만 조회한다 — 물어봐야 찾아 본다.
      이건 **서윤이 늘 지고 다니는 지식**이다. 용어(LFT·ZT·FOSB)·건물 층·
      경로·호기명은 물어봐서 아는 것이 아니라 **알고 있어야** 대화가 된다.
      "M14A 에서 M16WT 가려면?" 에 매번 조회하고 있으면 관제가 아니다.

    이미 있으면 건드리지 않는다 — 사용자가 고쳤을 수 있다.
    """
    if store.read("m16-hubroom"):
        return False
    src = os.path.join(os.path.dirname(str(base_dir)), "docs",
                       "M16_HUBROOM_반송_도메인지식.md")
    if not os.path.isfile(src):
        return False
    with open(src, encoding="utf-8") as f:
        body = f.read()
    md = compose("m16-hubroom",
                 "M16 HUBROOM 반송 도메인 지식 — 반송 장치(VHL·OHT·LFT·CNV·"
                 "STK·STB·Sorter·MLUD)와 포트 규칙, 건물·층 현황, FAB 간 연결 "
                 "수단과 호기명, 경유 경로, 유의 지표(Sorter 대기·MLUD)",
                 terms.no_code(body))
    ok, _e, _w = store.save("m16-hubroom", md)
    return ok


def seed_fab_score(store, base_dir):
    """real_time_amhs 의 FAB 스코어 md 를 fab-score 스킬로 심는다.

    이미 있으면 건드리지 않는다 — 사용자가 고쳤을 수 있다. 단 **룰 코드가
    남아 있으면 다시 심는다**: 그 표(`R-A`·`R-D`)를 보고 모델이 코드를
    그대로 베껴 답했다. 결함이라 사용자 편집 여부와 무관하게 고쳐야 한다.
    """
    old = store.read("fab-score")
    if old and not terms.has_code(old):
        return False
    src = os.path.join(os.path.dirname(str(base_dir)), "docs",
                       "FAB별_위험도_스코어.md")
    if not os.path.isfile(src):
        return False
    with open(src, encoding="utf-8") as f:
        body = f.read()
    md = compose("fab-score",
                 "M16 HUBROOM FAB 별 위험도 스코어 — 룰 배점, FAB 별 임계값과 컬럼, "
                 "점수 컬럼 이름(area_score), 자주 틀리는 것",
                 terms.no_code(body))
    ok, _e, _w = store.save("fab-score", md)
    return ok
