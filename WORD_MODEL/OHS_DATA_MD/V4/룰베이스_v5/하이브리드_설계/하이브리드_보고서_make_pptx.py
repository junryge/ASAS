#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""표준 라이브러리만으로 .pptx 직접 생성 — 하이브리드 정체예측 고객 보고 (8슬라이드)."""
import sys
import zipfile
from xml.sax.saxutils import escape

EMU = 914400
W, H = 12192000, 6858000  # 16:9

# ---- 색 ----
TEAL = "0F766E"; NAVY = "0F172A"; BLUE = "2563EB"; GRAY = "6B7280"; LIGHT = "F1F5F9"
GREEN = "059669"; RED = "DC2626"; WHITE = "FFFFFF"; DARK = "1E293B"
ORANGE = "D97706"; PINK = "DB2777"; YELLOW = "FEF3C7"; MINT = "D1FAE5"


def inch(v): return int(v * EMU)


_sp_id = [10]
def nid():
    _sp_id[0] += 1
    return _sp_id[0]


def run(text, sz=1800, color=DARK, bold=False, italic=False):
    b = ' b="1"' if bold else ''
    i = ' i="1"' if italic else ''
    return (f'<a:r><a:rPr lang="ko-KR" sz="{sz}"{b}{i} dirty="0">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r>')


def para(runs, align="l", bullet=False, space_after=400, line=None):
    al = f' algn="{align}"' if align != "l" else ''
    bu = '<a:buChar char="•"/>' if bullet else '<a:buNone/>'
    indent = ' marL="228600" indent="-228600"' if bullet else ''
    sp = f'<a:spcAft><a:spcPts val="{space_after}"/></a:spcAft>'
    ln = f'<a:lnSpc><a:spcPct val="{line}"/></a:lnSpc>' if line else ''
    if isinstance(runs, str):
        runs = [run(runs)]
    return f'<a:p><a:pPr{al}{indent}>{ln}{sp}{bu}</a:pPr>{"".join(runs)}</a:p>'


def textbox(x, y, w, h, paras, fill=None, anchor="t"):
    sid = nid()
    fillxml = (f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>')
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="tb{sid}"/>
<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{inch(x)}" y="{inch(y)}"/><a:ext cx="{inch(w)}" cy="{inch(h)}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fillxml}</p:spPr>
<p:txBody><a:bodyPr wrap="square" anchor="{anchor}" lIns="91440" tIns="45720" rIns="91440" bIns="45720"><a:normAutofit/></a:bodyPr>
<a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>'''


def rect(x, y, w, h, color, round_=False):
    sid = nid()
    geom = 'roundRect' if round_ else 'rect'
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="r{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{inch(x)}" y="{inch(y)}"/><a:ext cx="{inch(w)}" cy="{inch(h)}"/></a:xfrm>
<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
<a:solidFill><a:srgbClr val="{color}"/></a:solidFill></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'''


def slide_xml(shapes):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
{"".join(shapes)}
</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping
bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sld>'''


def header(title, num):
    return [
        rect(0, 0, 13.333, 1.05, TEAL),
        textbox(0.55, 0.12, 11, 0.8, [para([run(title, 2500, WHITE, True)])], anchor="ctr"),
        textbox(12.2, 0.3, 0.9, 0.5, [para([run(f"0{num}", 2000, MINT, True)], align="r")]),
    ]


def bullet(label, value, lc=TEAL):
    return para([run(label + "  ", 1500, lc, True), run(value, 1500, DARK)],
                bullet=True, space_after=320, line=115000)


def expert_card(x, color, name, role, metaphor):
    return [
        rect(x, 2.0, 3.9, 4.3, LIGHT, round_=True),
        rect(x, 2.0, 3.9, 0.7, color, round_=True),
        textbox(x, 2.05, 3.9, 0.6, [para([run(name, 1700, WHITE, True)], align="ctr")], anchor="ctr"),
        textbox(x + 0.25, 3.0, 3.4, 2.2, [
            para([run("역할", 1300, color, True)], space_after=150),
            para([run(role, 1450, DARK)], line=120000, space_after=400),
            para([run("비유", 1300, color, True)], space_after=150),
            para([run(metaphor, 1450, GRAY)], line=120000),
        ]),
    ]


def judge_row(y, combo, result, rc, hl=None):
    fill = hl or WHITE
    return [
        rect(0.55, y, 12.2, 0.72, fill, round_=True),
        textbox(0.8, y, 7.6, 0.72, [para([run(combo, 1400, DARK)])], anchor="ctr"),
        textbox(8.4, y, 4.1, 0.72, [para([run(result, 1450, rc, True)])], anchor="ctr"),
    ]


slides = []

# ── 1. 표지 ──
slides.append([
    rect(0, 0, 13.333, 7.5, NAVY),
    rect(0, 4.35, 13.333, 0.07, GREEN),
    textbox(0.9, 1.7, 11.5, 1.5, [para([run("정체 30분 사전예측", 4400, WHITE, True)])]),
    textbox(0.9, 2.95, 11.5, 0.9, [para([run("하이브리드 AI 시스템", 2800, "5EEAD4", True)])]),
    textbox(0.9, 4.6, 11.5, 1.0, [para([
        run("운영자가 정체를 알기 ", 1900, "CBD5E1"),
        run("30분 전", 1900, "5EEAD4", True),
        run(", AI가 미리 알린다", 1900, "CBD5E1")])]),
    textbox(0.9, 6.5, 11.5, 0.5, [para([run("M16A HUBROOM 반송 정체 예측  ·  2026-07", 1300, "64748B")])]),
])

# ── 2. 문제 ──
slides.append(header("1. 지금 무엇이 문제인가", 1) + [
    textbox(0.55, 1.5, 12.2, 2.6, [
        bullet("뒤늦은 발견", "정체가 나야 운영자가 알아채고 대응 → 이미 늦음"),
        bullet("규칙의 한계", "기존 룰(규칙)은 정해진 조건만 봐서 미묘한 전조를 놓침"),
        bullet("사전 예측 필요", "정체를 미리 안다면 30분 먼저 손 쓸 수 있음"),
    ]),
    rect(2.5, 4.7, 8.3, 1.5, MINT, round_=True),
    textbox(2.5, 4.7, 8.3, 1.5, [para([
        run("🎯  목표 :  정체 ", 2400, DARK, True),
        run("30분 전", 2400, GREEN, True),
        run(" 미리 경보", 2400, DARK, True)], align="ctr")], anchor="ctr"),
])

# ── 3. 3명의 전문가 ──
slides.append(header("2. 어떻게? — 3명의 전문가에게 묻는다", 2) + [
    textbox(0.55, 1.2, 12.2, 0.65, [para([
        run("한 명만 믿으면 틀릴 수 있다  →  ", 1550, GRAY),
        run("3명에게 묻고 합의한다", 1550, TEAL, True)])]),
    *expert_card(0.55, ORANGE, "룰베이스", "확실한 정체를 딱 잡음", "규정집 든 베테랑"),
    *expert_card(4.72, BLUE, "정상 AI", "평소와 다른 낌새를 먼저 챔", "눈치 빠른 신입"),
    *expert_card(8.88, PINK, "비정상 AI", "'진짜 정체 맞아?' 확인", "꼼꼼한 검수자"),
    textbox(0.55, 6.5, 12.2, 0.5, [para([
        run("→ 세 명의 판단을 ", 1400, GRAY),
        run("하이브리드 판정", 1400, TEAL, True),
        run("이 종합한다", 1400, GRAY)], align="ctr")]),
])

# ── 4. 핵심 아이디어 ──
slides.append(header("3. 핵심 아이디어 — 정상만 가르친다", 3) + [
    textbox(0.55, 1.5, 12.2, 2.5, [
        bullet("정상 학습", "AI에게 '정상 상태'만 잔뜩 보여줌 → 평소 모습을 익힘"),
        bullet("이상 감지", "운영 중 평소와 다르면 → AI가 '어? 이상한데?' 감지"),
        bullet("선행성", "이 낌새가 정체보다 30분 먼저 나타남"),
    ]),
    rect(2.0, 4.8, 9.3, 1.4, MINT, round_=True),
    textbox(2.0, 4.8, 9.3, 1.4, [para([
        run("평소를 알면, ", 2600, DARK, True),
        run("달라진 순간", 2600, GREEN, True),
        run("을 안다", 2600, DARK, True)], align="ctr")], anchor="ctr"),
])

# ── 5. 하이브리드 판정 ──
slides.append(header("4. 하이브리드 판정 — 3명이 합의하면 진짜", 4) + [
    rect(0.55, 1.25, 12.2, 0.6, TEAL, round_=True),
    textbox(0.8, 1.25, 7.6, 0.6, [para([run("룰베이스  +  정상 AI  +  비정상 AI", 1450, WHITE, True)])], anchor="ctr"),
    textbox(8.4, 1.25, 4.1, 0.6, [para([run("→  최종 판정", 1450, WHITE, True)])], anchor="ctr"),
    *judge_row(2.05, "위험  +  이상  +  정체", "🔴 확실 정체 · 즉시", RED, MINT),
    *judge_row(2.87, "위험  +  정상", "정체 (룰 근거)", DARK, LIGHT),
    *judge_row(3.69, "정상  +  이상  +  정체", "🟡 30분 전 조기경보 ⭐", ORANGE, YELLOW),
    *judge_row(4.51, "정상  +  이상  +  정체아님", "⚪ 무시 (설비작업 등)", GRAY, LIGHT),
    *judge_row(5.33, "정상  +  정상", "✅ 안전", GREEN, MINT),
    textbox(0.55, 6.4, 12.2, 0.6, [para([
        run("⭐ 룰은 아직 조용한데 AI 둘이 '곧 정체' → ", 1400, DARK),
        run("룰보다 30분 먼저 경보", 1400, ORANGE, True)], align="ctr")]),
])

# ── 6. 가치 ──
slides.append(header("5. 이 시스템의 가치", 5) + [
    textbox(0.55, 1.5, 12.2, 3.3, [
        bullet("⏱  선행 예측", "정체 30분 전 미리 알림 — 대응 시간 확보"),
        bullet("🎯  오탐 감소", "'정체 아닌 이상'(설비작업·센서)은 걸러냄"),
        bullet("🔍  설명 가능", "어느 지표가 왜 위험한지 근거 제시"),
        bullet("🛡  안전성", "3명 합의 구조 → 한 명이 틀려도 버팀"),
    ]),
    rect(1.5, 5.3, 10.3, 1.3, TEAL, round_=True),
    textbox(1.5, 5.3, 10.3, 1.3, [para([
        run("더 빠르고,  더 정확하고,  더 믿을 수 있게", 2400, WHITE, True)], align="ctr")], anchor="ctr"),
])

# ── 7. 진행 계획 ──
def plan_row(y, step, name, status, sc):
    return [
        textbox(0.7, y, 1.0, 0.6, [para([run(step, 1500, TEAL, True)], align="ctr")], anchor="ctr"),
        textbox(1.9, y, 8.0, 0.6, [para([run(name, 1500, DARK)])], anchor="ctr"),
        textbox(10.0, y, 2.7, 0.6, [para([run(status, 1450, sc, True)], align="ctr")], anchor="ctr"),
    ]
slides.append(header("6. 진행 계획", 6) + [
    rect(0.55, 1.3, 12.2, 0.6, NAVY, round_=True),
    textbox(0.7, 1.3, 1.0, 0.6, [para([run("단계", 1400, WHITE, True)], align="ctr")], anchor="ctr"),
    textbox(1.9, 1.3, 8.0, 0.6, [para([run("내용", 1400, WHITE, True)])], anchor="ctr"),
    textbox(10.0, 1.3, 2.7, 0.6, [para([run("상태", 1400, WHITE, True)], align="ctr")], anchor="ctr"),
    *plan_row(2.15, "1", "정상 데이터 준비", "✅ 완료", GREEN),
    *plan_row(2.90, "2", "정상 AI 학습", "🔄 진행", BLUE),
    *plan_row(3.65, "3", "30분 선행 검증", "⬜ 핵심", ORANGE),
    *plan_row(4.40, "4", "비정상 AI 학습", "⬜", GRAY),
    *plan_row(5.15, "5", "하이브리드 판정 완성", "⬜", GRAY),
    *plan_row(5.90, "6", "룰 + AI 병행 운영", "⬜", GRAY),
])

# ── 8. 요약 ──
slides.append([
    rect(0, 0, 13.333, 7.5, NAVY),
    rect(0, 0, 13.333, 1.05, TEAL),
    textbox(0.55, 0.12, 11, 0.8, [para([run("종합", 2500, WHITE, True)])], anchor="ctr"),
    textbox(0.9, 2.1, 11.5, 1.2, [para([
        run("룰베이스  +  정상 AI  +  비정상 AI  →  ", 2200, "CBD5E1"),
        run("하이브리드 판정", 2200, "5EEAD4", True)], align="ctr")]),
    rect(3.0, 3.7, 7.3, 1.5, "1E293B", round_=True),
    textbox(3.0, 3.7, 7.3, 1.5, [para([run("\"세 개가 합의하면 진짜다\"", 2600, WHITE, True)], align="ctr")], anchor="ctr"),
    textbox(0.9, 5.6, 11.5, 0.9, [para([
        run("= 정체 ", 2400, "CBD5E1"),
        run("30분 사전예측", 2400, "5EEAD4", True)], align="ctr")]),
])

# ============================================================
# OOXML 패키지
# ============================================================
N = len(slides)
CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
'<Default Extension="xml" ContentType="application/xml"/>'
'<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
'<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
'<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
'<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
+ "".join(f'<Override PartName="/ppt/slides/slide{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(N))
+ '</Types>')

RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
'</Relationships>')

CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"'
' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
'<dc:title>하이브리드 정체예측 — 고객 보고</dc:title><dc:creator>Hybrid AMHS</dc:creator>'
'<cp:lastModifiedBy>Hybrid AMHS</cp:lastModifiedBy>'
'<dcterms:created xsi:type="dcterms:W3CDTF">2026-07-02T00:00:00Z</dcterms:created>'
'<dcterms:modified xsi:type="dcterms:W3CDTF">2026-07-02T00:00:00Z</dcterms:modified></cp:coreProperties>')

APP = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"'
' xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
'<Application>Microsoft Office PowerPoint</Application><PresentationFormat>Widescreen</PresentationFormat>'
f'<Slides>{N}</Slides><AppVersion>16.0000</AppVersion></Properties>')

pres_rels = ['<Relationship Id="rIdM" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
             '<Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>']
for i in range(N):
    pres_rels.append(f'<Relationship Id="rIdS{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>')
PRES_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(pres_rels) + '</Relationships>')

sldid = "".join(f'<p:sldId id="{256+i}" r:id="rIdS{i+1}"/>' for i in range(N))
PRESENTATION = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
'<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdM"/></p:sldMasterIdLst>'
f'<p:sldIdLst>{sldid}</p:sldIdLst><p:sldSz cx="{W}" cy="{H}"/><p:notesSz cx="{H}" cy="{W}"/></p:presentation>')

SLIDE_MASTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
'<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
'</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1"'
' accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"'
' hlink="hlink" folHlink="folHlink"/>'
'<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdL1"/></p:sldLayoutIdLst>'
'<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400"><a:latin typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:titleStyle>'
'<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"><a:latin typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:bodyStyle>'
'<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"><a:latin typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>')

SM_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
'<Relationship Id="rIdL1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
'<Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
'</Relationships>')

SLIDE_LAYOUT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">'
'<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
'</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2"'
' accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5"'
' accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sldLayout>')

SL_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
'<Relationship Id="rIdSM" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
'</Relationships>')

SLIDE_REL = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
'<Relationship Id="rIdL" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
'</Relationships>')

_accents = [BLUE, GREEN, RED, "F59E0B", "8B5CF6", "EC4899"]
_acc = "".join(f'<a:{n}><a:srgbClr val="{c}"/></a:{n}>' for n, c in
               zip(["accent1","accent2","accent3","accent4","accent5","accent6"], _accents))
THEME = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">'
'<a:themeElements><a:clrScheme name="Custom">'
'<a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
'<a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>'
+ _acc + '<a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="6B7280"/></a:folHlink>'
'</a:clrScheme><a:fontScheme name="Custom">'
'<a:majorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:majorFont>'
'<a:minorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:minorFont>'
'</a:fontScheme><a:fmtScheme name="Office">'
'<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
'<a:lnStyleLst><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
'<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
'<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
'</a:fmtScheme></a:themeElements></a:theme>')

out = sys.argv[1] if len(sys.argv) > 1 else "하이브리드_보고서.pptx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CONTENT_TYPES)
    z.writestr("_rels/.rels", RELS)
    z.writestr("docProps/core.xml", CORE)
    z.writestr("docProps/app.xml", APP)
    z.writestr("ppt/presentation.xml", PRESENTATION)
    z.writestr("ppt/_rels/presentation.xml.rels", PRES_RELS)
    z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
    z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", SM_RELS)
    z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
    z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", SL_RELS)
    z.writestr("ppt/theme/theme1.xml", THEME)
    for i, shapes in enumerate(slides):
        z.writestr(f"ppt/slides/slide{i+1}.xml", slide_xml(shapes))
        z.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", SLIDE_REL)

print(f"생성: {out} ({N} 슬라이드)")
