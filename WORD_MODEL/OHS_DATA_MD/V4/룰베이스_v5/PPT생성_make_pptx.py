#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""표준 라이브러리만으로 .pptx (OOXML) 직접 생성 — 작업 보고 5슬라이드."""
import zipfile
from xml.sax.saxutils import escape

EMU = 914400
W, H = 12192000, 6858000  # 16:9 widescreen (13.333 x 7.5")

# ---- 색 ----
NAVY = "1F2937"; BLUE = "2563EB"; GRAY = "6B7280"; LIGHT = "F3F4F6"
GREEN = "059669"; RED = "DC2626"; WHITE = "FFFFFF"; DARK = "111827"

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
    fillxml = (f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
               if fill else '<a:noFill/>')
    body = "".join(paras)
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="tb{sid}"/>
<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{inch(x)}" y="{inch(y)}"/><a:ext cx="{inch(w)}" cy="{inch(h)}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fillxml}</p:spPr>
<p:txBody><a:bodyPr wrap="square" anchor="{anchor}" lIns="91440" tIns="45720" rIns="91440" bIns="45720"><a:normAutofit/></a:bodyPr>
<a:lstStyle/>{body}</p:txBody></p:sp>'''

def rect(x, y, w, h, color):
    sid = nid()
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="r{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{inch(x)}" y="{inch(y)}"/><a:ext cx="{inch(w)}" cy="{inch(h)}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
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

# ---- 헬퍼: 본문 헤더 바 + 제목 ----
def header(title, num):
    return [
        rect(0, 0, 13.333, 1.05, NAVY),
        textbox(0.55, 0.12, 11, 0.8, [para([run(title, 2600, WHITE, True)])], anchor="ctr"),
        textbox(12.3, 0.32, 0.8, 0.5, [para([run(f"0{num}", 2000, BLUE, True)], align="r")]),
    ]

def kv_line(label, value, lc=BLUE, vc=DARK):
    return para([run(label + "  ", 1500, lc, True), run(value, 1500, vc)],
                bullet=True, space_after=300, line=110000)

slides = []

# ── 슬라이드 1: 표지 ──
s1 = [
    rect(0, 0, 13.333, 7.5, NAVY),
    rect(0, 4.55, 13.333, 0.06, BLUE),
    textbox(0.9, 1.9, 11.5, 1.2, [para([run("M16A HUBROOM 이벤트 예측", 4000, WHITE, True)])]),
    textbox(0.9, 3.15, 11.5, 0.7, [para([run("반도체 FAB AMHS 반송 정체 사전 예측 — 작업 보고", 2000, "9CA3AF")])]),
    textbox(0.9, 4.8, 11.5, 1.6, [
        para([run("1.  룰베이스 고도화  (hubroom_predictor.py)", 1700, WHITE)], space_after=250),
        para([run("2.  운영로그 파서 V2", 1700, WHITE)], space_after=250),
        para([run("3.  리프터 주변 HID 파악", 1700, WHITE)], space_after=250),
    ]),
    textbox(0.9, 6.6, 11.5, 0.5, [para([run("2026-06-16   ·   검증기간 2026-04 ~ 05 (56일)", 1300, "6B7280")])]),
]
slides.append(s1)

# ── 슬라이드 2: 룰베이스 고도화 ──
s2 = header("1. 룰베이스 고도화 — hubroom_predictor.py", 1) + [
    textbox(0.55, 1.25, 12.2, 0.85, [para([
        run("8개 영역을 ", 1500, GRAY), run("매분", 1500, DARK, True),
        run(" 룰 평가 → 위험 점수·등급 산출. 메신저 등록보다 ", 1500, GRAY),
        run("평균 30~60분 먼저", 1500, BLUE, True), run(" 정체 예측.", 1500, GRAY)],
        line=120000, space_after=200)]),
    textbox(0.55, 2.15, 7.4, 4.2, [
        para([run("v6 핵심 개선", 1700, NAVY, True)], space_after=350),
        kv_line("사건 진동 흡수", "점수 잠깐 하락 후 재상승도 같은 사건 (gap 60분)"),
        kv_line("5단계 등급", "관심100 / 주의120 / 경계130 / 위험160 / 발동220"),
        kv_line("노이즈 차단", "점수 100 미만은 사건 기록 X (모니터링만)"),
        kv_line("장애유형 라벨", "HUB-FAB정체 / HUB-리프터역증가 등 자동"),
        kv_line("지속성·재발생", "지속 N분 / 재발 N회 컬럼"),
    ]),
    # 성과 카드
    textbox(8.25, 2.15, 4.5, 4.2, [
        para([run("검증 결과 (4~5월)", 1600, NAVY, True)], align="ctr", space_after=400),
        para([run("75%", 4400, GREEN, True)], align="ctr", space_after=100),
        para([run("위험 등급(160+) 정밀도", 1300, GRAY)], align="ctr", space_after=500),
        para([run("+32분", 3200, BLUE, True)], align="ctr", space_after=100),
        para([run("평균 사전 예측 리드타임", 1300, GRAY)], align="ctr", space_after=400),
        para([run("하루 0.5건 — 알람 피로도 낮음", 1300, GRAY)], align="ctr"),
    ], fill=LIGHT),
]
slides.append(s2)

# ── 슬라이드 3: 운영로그 파서 V2 ──
s3 = header("2. 운영로그 파서 V2", 2) + [
    textbox(0.55, 1.25, 12.2, 0.7, [para([
        run("운영자 메신저 채팅 → 구조화된 장애 목록(Episode) = 룰베이스 채점용 ", 1500, GRAY),
        run("정답지", 1500, BLUE, True)], line=120000)]),
    textbox(0.55, 2.0, 12.2, 0.75, [para([
        run('"Deadlock 으로 OHT 정체중입니다"', 1500, DARK, italic=True),
        run("   →   ", 1500, GRAY),
        run("Episode: 18:34 / 정체·병목 / OHT", 1500, GREEN, True)])], fill=LIGHT, anchor="ctr"),
    textbox(0.55, 3.05, 12.2, 3.2, [
        kv_line("카테고리 6종", "fault / action / recovery / rollback / cancel / normal"),
        kv_line("장애유형 7종", "정체·병목 / 브릿지 / 리프터 / CNV / MLUD / 통신·에러 / 기타"),
        kv_line("Episode 묶기", "장애 1건에 여러 채팅 = 1건으로 (거품 제거)"),
        kv_line("제외 처리", "orphan(선행 fault 없는 복구), CAPA변경(운영자 조치)"),
    ]),
    textbox(0.55, 6.35, 12.2, 0.8, [para([
        run("효과:  ", 1500, NAVY, True),
        run("메신저 62건 메시지 → 실제 장애 4건(예시 5/25). 과대 카운트 제거로 룰베이스 성능을 정확히 측정.", 1500, DARK)],
        line=115000)], fill=LIGHT),
]
slides.append(s3)

# ── 슬라이드 4: 리프터 주변 HID 파악 ──
s4 = header("3. 리프터 주변 HID 파악", 3) + [
    textbox(0.55, 1.25, 12.2, 0.7, [para([
        run("R-C 룰(리프터 ", 1500, GRAY), run("역증가", 1500, DARK, True),
        run(" 감지)이 단순 카운트를 넘어 ", 1500, GRAY),
        run("문제 리프터를 개별 ID로 특정.", 1500, BLUE, True)], line=120000)]),
    textbox(0.55, 2.1, 12.2, 3.0, [
        kv_line("감지 신호", "M16HUB 리프터 역증가 개수(rev_count) + 20분 트렌드"),
        kv_line("개별 HID 파악", "rev_lids = 역증가 리프터 ID 목록"),
        kv_line("임계", "역증가 ≥ 4개 → R-C 발동"),
    ]),
    textbox(0.55, 4.5, 12.2, 0.85, [para([
        run("실측 예시:  ", 1500, NAVY, True),
        run("역증가 5개 → 6ABL6021, 6ABL6031, 6ABL6032, 6ABL0112, 6ABL0121", 1500, RED, True)])], fill=LIGHT, anchor="ctr"),
    textbox(0.55, 5.65, 12.2, 1.3, [
        para([run("활용", 1600, NAVY, True)], space_after=250),
        para([run('"리프터 정체" 막연한 알람이 아니라 ', 1500, DARK),
              run("어느 리프터(HID)가 문제인지 즉시 지목", 1500, BLUE, True),
              run(" → 해당 설비만 점검. (분석도구: 한줄분석 / 웹분석기 / LLM 스킬 연동)", 1500, DARK)],
             line=120000)]),
]
slides.append(s4)

# ── 슬라이드 5: 종합 ──
s5 = header("종합", 4) + [
    textbox(0.55, 1.5, 12.2, 3.0, [
        para([run("작업", 1500, WHITE, True), run("                          산출물", 1500, WHITE, True),
              run("                                          상태", 1500, WHITE, True)], space_after=0)], fill=NAVY),
    textbox(0.7, 2.05, 12.0, 3.0, [
        para([run("룰베이스 고도화", 1500, DARK, True),
              run("        hubroom_predictor.py v6 (5등급·진동흡수·유형라벨)", 1450, GRAY),
              run("     ✅ 검증완료", 1450, GREEN, True)], space_after=450, line=110000),
        para([run("운영로그 파서", 1500, DARK, True),
              run("           운영로그_파서_v2.py (정답지 생성)", 1450, GRAY),
              run("                          ✅ 적용", 1450, GREEN, True)], space_after=450, line=110000),
        para([run("리프터 HID 파악", 1500, DARK, True),
              run("        R-C 룰 rev_lids 개별 ID + 분석도구", 1450, GRAY),
              run("                  ✅ 운영중", 1450, GREEN, True)], space_after=450, line=110000),
    ]),
    textbox(0.55, 5.5, 12.2, 1.4, [
        para([run("핵심 성과", 1700, NAVY, True)], space_after=250),
        para([run("메신저보다 30~60분 빠른 예측", 1600, BLUE, True),
              run("   ·   ", 1600, GRAY),
              run("위험 등급 정밀도 75%", 1600, GREEN, True),
              run("   ·   ", 1600, GRAY),
              run("문제 설비 HID 단위 지목", 1600, RED, True)], align="ctr")], fill=LIGHT, anchor="ctr"),
]
slides.append(s5)

# ============================================================
# OOXML 패키지 작성
# ============================================================
N = len(slides)

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
''' + "".join(
    f'<Override PartName="/ppt/slides/slide{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
    for i in range(N)) + '</Types>'

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''

pres_rels = ['<Relationship Id="rIdM" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
             '<Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>']
for i in range(N):
    pres_rels.append(f'<Relationship Id="rIdS{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>')
PRES_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             + "".join(pres_rels) + '</Relationships>')

sldid = "".join(f'<p:sldId id="{256+i}" r:id="rIdS{i+1}"/>' for i in range(N))
PRESENTATION = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdM"/></p:sldMasterIdLst>
<p:sldIdLst>{sldid}</p:sldIdLst>
<p:sldSz cx="{W}" cy="{H}"/><p:notesSz cx="{H}" cy="{W}"/></p:presentation>'''

SLIDE_MASTER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1"
accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdL1"/></p:sldLayoutIdLst></p:sldMaster>'''

SM_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdL1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''

SLIDE_LAYOUT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2"
accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5"
accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sldLayout>'''

SL_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdSM" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''

def slide_rel():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdL" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''

def theme():
    accents = [BLUE, GREEN, RED, "F59E0B", "8B5CF6", "EC4899"]
    acc = "".join(f'<a:{n}><a:srgbClr val="{c}"/></a:{n}>'
                  for n, c in zip(["accent1","accent2","accent3","accent4","accent5","accent6"], accents))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
<a:themeElements><a:clrScheme name="Custom">
<a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>
{acc}<a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="6B7280"/></a:folHlink>
</a:clrScheme><a:fontScheme name="Custom">
<a:majorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Malgun Gothic"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:minorFont>
</a:fontScheme><a:fmtScheme name="Office">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme></a:themeElements></a:theme>'''

out = "/tmp/작업보고_PPT_20260616.pptx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CONTENT_TYPES)
    z.writestr("_rels/.rels", RELS)
    z.writestr("ppt/presentation.xml", PRESENTATION)
    z.writestr("ppt/_rels/presentation.xml.rels", PRES_RELS)
    z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
    z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", SM_RELS)
    z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
    z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", SL_RELS)
    z.writestr("ppt/theme/theme1.xml", theme())
    for i, shapes in enumerate(slides):
        z.writestr(f"ppt/slides/slide{i+1}.xml", slide_xml(shapes))
        z.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", slide_rel())

print("생성:", out, f"({N} 슬라이드)")
