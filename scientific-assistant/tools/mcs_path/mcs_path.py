# -*- coding: utf-8 -*-
"""MCS 로그 → 캐리어 이동 경로 그림 (표준 라이브러리만 · 폐쇄망에서 그대로 돈다).

    python mcs_path.py 로그.txt                      그림(HTML · SVG) + LLM 에 줄 요약(TXT)
    python mcs_path.py 로그.txt --carrier ABCD1234   캐리어가 여럿이면 고른다 (안 주면 줄이 제일 많은 것)
    python mcs_path.py 로그.txt --list               로그에 있는 캐리어만 보기
    python mcs_path.py 로그.txt -o 경로.html

읽는 것 — 주피터 노트북(.ipynb, 표를 찍어 둔 칸), HTML 표, CSV · TSV, JSON(행 목록), 원본 로그 줄.
열 이름은 MCS 로그 조회 결과 그대로(TIME_EX · MESSAGENAME · MACHINENAME · UNITNAME · CARRIER · TEXT …).
열이 빠져도 TEXT(XML) 안의 값으로 채운다.

나중에 LLM 에 붙일 때 쓰는 세 가지 (데모스에는 아직 안 붙였다)
    t = trace(rows, carrier)      행(dict) 목록 → 경로
    render_svg(t)                 그림 한 장 (SVG 글)
    facts_text(t)                 LLM 에 줄 요약 — 시각 · 장소 · 걸린 시간은 여기 적힌 것만 말하게 한다
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser

__all__ = ["read_rows", "rows_from_text", "trace", "render_svg", "facts_text", "render_html", "carriers"]

# ═════════════════════════════════════════════════════════════════════
# 1. 읽기 — 파일 → 행(dict) 목록
# ═════════════════════════════════════════════════════════════════════


class _Tables(HTMLParser):
    """HTML 안의 <table> 들을 [[(tag, 글), ...], ...] 로 (표 안의 표는 무시)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._rows, self._row, self._cell, self._depth = [], None, None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._rows = []
        elif self._depth == 1:
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th") and self._row is not None:
                self._cell = [tag, []]
            elif tag == "br" and self._cell is not None:
                self._cell[1].append("\n")

    def handle_endtag(self, tag):
        if tag == "table":
            if self._depth == 1 and self._rows is not None:
                self.tables.append(self._rows)
                self._rows = None
            self._depth = max(0, self._depth - 1)
        elif self._depth == 1:
            if tag in ("td", "th") and self._cell is not None and self._row is not None:
                self._row.append((self._cell[0], "".join(self._cell[1]).strip()))
                self._cell = None
            elif tag == "tr" and self._row is not None:
                if self._row and self._rows is not None:
                    self._rows.append(self._row)
                self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell[1].append(data)


def _rows_from_html(text):
    p = _Tables()
    p.feed(text)
    p.close()
    out = []
    for rows in p.tables:
        head, body = None, []
        for cells in rows:
            if all(tag == "th" for tag, _ in cells) and not body:
                head = [x for _, x in cells]           # 머리줄이 여러 줄이면 마지막
            elif any(tag == "td" for tag, _ in cells):
                body.append([x for _, x in cells])
        if not head or not body:
            continue
        for vals in body:
            h = head
            if len(vals) != len(h):
                continue
            row = {k: v for k, v in zip(h, vals) if k != ""}   # pandas 번호 칸은 뺀다
            out.append(row)
    return out


def _notebook_text(nb):
    parts = []
    for c in nb.get("cells", []):
        src = c.get("source", "")
        parts.append(src if isinstance(src, str) else "".join(src))
        for o in c.get("outputs", []) or []:
            data = o.get("data") or {}
            for key in ("text/html", "text/plain"):
                v = data.get(key)
                if v:
                    parts.append(v if isinstance(v, str) else "".join(v))
            if o.get("text"):
                v = o["text"]
                parts.append(v if isinstance(v, str) else "".join(v))
    return "\n".join(parts)


_LOG_START = re.compile(r"(?m)^(?=\[\s*\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2})")


def rows_from_text(text):
    """글 → 행 목록. 노트북 · JSON · HTML 표 · CSV · 원본 로그 줄 순서로 알아본다."""
    s = text.lstrip("﻿ \t\r\n")
    if s[:1] in "[{":
        try:
            data = json.loads(s)
        except ValueError:
            data = None
        if isinstance(data, dict) and "cells" in data:
            return rows_from_text(_notebook_text(data))
        if isinstance(data, dict):
            for k in ("rows", "data", "result", "records"):
                if isinstance(data.get(k), list):
                    data = data[k]
                    break
        if isinstance(data, list) and data and all(isinstance(r, dict) for r in data):
            return [{str(k): ("" if v is None else str(v)) for k, v in r.items()} for r in data]
    if re.search(r"<table\b", text, re.I):
        rows = _rows_from_html(text)
        if rows:
            return rows
    first = next((ln for ln in s.splitlines() if ln.strip()), "")
    if re.search(r"\b(MESSAGENAME|CARRIER|TIME_EX)\b", first, re.I) and ("\t" in first or "," in first):
        rd = csv.DictReader(io.StringIO(s), delimiter="\t" if "\t" in first else ",")
        return [{(k or "").strip(): (v or "") for k, v in r.items()} for r in rd]
    chunks = [c.strip() for c in _LOG_START.split(text)]
    return [{"TEXT": c} for c in chunks if c and c.startswith("[")]


def read_rows(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return rows_from_text(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return rows_from_text(raw.decode("latin-1"))


# ═════════════════════════════════════════════════════════════════════
# 2. 한 줄 → 사건
# ═════════════════════════════════════════════════════════════════════

_TIME = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})[ T_]+(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d{1,6}))?")
_SP_CLOSE = re.compile(r"<\s*/\s*([\w:.-]+)\s*>")
_SP_EMPTY = re.compile(r"<\s*([\w:.-]+)\s*/\s*>")
_SP_OPEN = re.compile(r'<\s*([\w:.-]+)((?:\s+[\w:.-]+\s*=\s*"[^"]*")*)\s*>')
_LEAF = re.compile(r"<([\w:.-]+)>([^<>]*)</\1>")
_ATTR = re.compile(r'\b([A-Za-z_][\w.-]*)\s*=\s*"([^"]*)"')
_ATTR_SKIP = {"DESTINATION", "ORIGINATION", "SEQUENCE_NAME", "TID", "version", "encoding"}
_SAME_SKIP = {"TIME", "EVENT_TIME", "TRANSACTIONID", "CONVERSATIONID", "GTXN_ID", "GTXN_SEQ", "SEQUENCE_NO"}


def _time(s):
    m = _TIME.search(s or "")
    if not m:
        return None
    y, mo, d, h, mi, se, frac = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(se), int((frac or "0").ljust(6, "0")[:6]))
    except ValueError:
        return None


def _fields(text):
    """'< TAG > 값 < /TAG >' 처럼 띄어 쓴 XML 에서 값만 뽑는다 (잎 태그 + 속성, 먼저 나온 것)."""
    t = _SP_CLOSE.sub(r"</\1>", text or "")
    t = _SP_EMPTY.sub(r"<\1/>", t)
    t = _SP_OPEN.sub(lambda m: "<" + m.group(1) + m.group(2) + ">", t)
    f = {}
    for k, v in _LEAF.findall(t):
        v = html.unescape(v).strip()
        if v:
            f.setdefault(k, v)
    for k, v in _ATTR.findall(t):
        v = html.unescape(v).strip()
        if v and k not in _ATTR_SKIP:
            f.setdefault(k, v)
    return f


def parse_event(row, i=0):
    R = {str(k).strip().upper(): ("" if v is None else str(v)) for k, v in row.items()}

    def col(*names):
        for n in names:
            v = R.get(n, "").strip()
            if v and v.lower() not in ("nan", "none", "null", "nat"):
                return v
        return ""

    text = R.get("TEXT", "")
    f = _fields(text)
    return {
        "i": i,
        "t": _time(col("TIME_EX", "_TIME", "TIME", "EVENT_TIME")) or _time(text),
        "name": col("MESSAGENAME") or f.get("MESSAGENAME") or f.get("Command") or col("COMMAND"),
        "carrier": (col("CARRIER", "CARRIERID", "CARRIER_ID") or f.get("CARRIERID") or f.get("CARRIER_ID")
                    or f.get("CARRIERNAME") or "").upper(),
        "machine": col("MACHINENAME") or f.get("MACHINENAME", ""),
        "unit": col("UNITNAME") or f.get("UNITNAME", ""),
        "op": col("OPERATION_NAME"),
        "f": f,
    }


def _who(e):
    n, op = e["name"], e["op"]
    if n.startswith("MCSMHS_"):
        return "MCS→MES"
    if n.startswith("MHSMCS_"):
        return "MES→MCS"
    if n.startswith("UI-"):
        return "화면"
    if "Sender" in op or op.endswith(".send"):
        return "MCS→장비"
    if "Listener" in op or op.endswith("onMsg"):
        return "장비→MCS"
    return ""


# 사건 이름 → 한국어 (값이 없으면 괄호째 빠진다)
_KO = {
    "MHSMCS_CHANGED_DEVICE_INFO_EVENT": "설비 {DEVICE_ID} 상태 {DEVICE_STATE} · 포트 {SUB_DEVICE_ID} 에 있음",
    "STORAGE-CARRIERIDREAD": "ID 읽음 ({CARRIERLOC})",
    "STORAGE-CARRIERWAITIN": "입고 대기 ({CARRIERLOC})",
    "MCSMHS_CARRIER_LOCATION_CHANGED_EVENT": "위치 보고 {SUB_LOCATION_ID} · {CARRIER_STATE}",
    "MCSMHS_MATERIAL_DEST_REQ": "MES 에 목적지 물어봄",
    "MHSMCS_MATERIAL_DEST_REP": "목적지 받음 → {DESTINATION_ID} ({DESTINATION_TYPE} {DESTINATION_FLOOR})",
    "MCSMHS_TRANSPORT_JOB_CREATED_EVENT": "반송 작업 생성 → {DESTINATION_ID}",
    "MCSMHS_TRANSPORT_JOB_CHANGED_EVENT": "목적지 변경 → {DESTINATION_ID}",
    "MCSMHS_TRANSPORT_JOB_STARTED_EVENT": "반송 시작 → {DESTINATION_ID}",
    "MCSMHS_TRANSFER_COMPLETED_EVENT": "구간 완료 {DEVICE_ID} {DETAIL_DESTINATION_ID}",
    "MCSMHS_TRANSPORT_JOB_COMPLETED_EVENT": "반송 작업 완료 ({LOCATION_ID})",
    "STORAGE-CARRIERTRANSFER": "스토커에 이동 명령 {SOURCEUNIT} → {DESTUNIT}",
    "STORAGE-CARRIERTRANSFERREPLY": "스토커 명령 응답 (HCACK {HCACK})",
    "STORAGE-TRANSFERINITIATED": "스토커 이동 시작",
    "STORAGE-CARRIERTRANSFERRING": "크레인이 옮기는 중 ({CARRIERLOC})",
    "STORAGE-CARRIERWAITOUT": "출고 대기 ({CARRIERLOC})",
    "STORAGE-TRANSFERCOMPLETED": "스토커 이동 완료 ({CARRIERLOC})",
    "STORAGE-CARRIERREMOVED": "스토커에서 빠짐",
    "RAIL-STAGECOMMAND": "OHT 미리 부름 → {DESTPORT}",
    "RAIL-STAGEREPLY": "OHT 부름 응답",
    "RAIL-CARRIERTRANSFER": "OHT 반송 명령 {SOURCEUNIT} → {DESTUNIT}",
    "RAIL-CARRIERTRANSFERREPLY": "OHT 명령 응답 (HCACK {HCACK})",
    "RAIL-VEHICLEACQUIRESTARTED": "OHT {VEHICLEID} 집기 시작 ({TRANSFERPORT})",
    "RAIL-CARRIERINSTALLED": "OHT {VEHICLEID} 에 실림",
    "RAIL-VEHICLEACQUIRECOMPLETED": "OHT {VEHICLEID} 집기 완료",
    "RAIL-VEHICLEDEPOSITSTARTED": "OHT {VEHICLEID} 내려놓기 시작 ({TRANSFERPORT})",
    "RAIL-CARRIERREMOVED": "OHT 에서 내림 ({CARRIERLOC})",
    "RAIL-VEHICLEDEPOSITCOMPLETED": "OHT {VEHICLEID} 내려놓기 완료",
    "RAIL-TRANSFERCOMPLETED": "OHT 반송 완료 ({DESTPORT})",
    "INV-CARRIERINSTALLED": "선반 등록 ({CARRIERLOC})",
    "UI-CARRIER": "화면 갱신 {UNITNAME} · {STATE}",
}
# 그림 · 요약에 올리는 사건 (1 = 꼭, 2 = 자리 나면)
_KEY = {
    "MHSMCS_CHANGED_DEVICE_INFO_EVENT": 1, "MHSMCS_MATERIAL_DEST_REP": 1,
    "MCSMHS_TRANSPORT_JOB_CREATED_EVENT": 1, "MCSMHS_TRANSPORT_JOB_CHANGED_EVENT": 1,
    "MCSMHS_TRANSPORT_JOB_COMPLETED_EVENT": 1, "RAIL-CARRIERINSTALLED": 1, "RAIL-CARRIERREMOVED": 1,
    "STORAGE-CARRIERIDREAD": 2, "STORAGE-CARRIERWAITIN": 2, "STORAGE-TRANSFERINITIATED": 2,
    "STORAGE-CARRIERWAITOUT": 2, "RAIL-STAGECOMMAND": 2, "RAIL-CARRIERTRANSFER": 2,
    "RAIL-VEHICLEACQUIRESTARTED": 2, "RAIL-VEHICLEDEPOSITSTARTED": 2, "STORAGE-CARRIERTRANSFERRING": 2,
}


def _fmt(tpl, f):
    s = re.sub(r"\{(\w+)\}", lambda m: f.get(m.group(1), ""), tpl)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s+·\s*$|\s*→\s*$", "", s.strip())
    return re.sub(r"\s{2,}", " ", s).strip()


def _ko(e):
    tpl = _KO.get(e["name"])
    if tpl:
        return _fmt(tpl, e["f"])
    if re.search(r"ABORT|CANCEL|FAIL", e["name"]):
        return "중단 · 취소 " + e["name"]
    return e["name"]


# ═════════════════════════════════════════════════════════════════════
# 3. 사건들 → 경로
# ═════════════════════════════════════════════════════════════════════

TYPE_KO = {"stocker": "스토커", "oht": "OHT", "zfs": "ZFS", "eqp": "설비", "etc": "기타"}


def _type_word(w):
    w = (w or "").upper()
    if "STOCKER" in w or w in ("STK", "STB"):
        return "stocker"
    if "ZFS" in w:
        return "zfs"
    if "OHT" in w or "RAIL" in w or "VEHICLE" in w:
        return "oht"
    if "EQP" in w or "EQUIP" in w or "TOOL" in w or "PORT" in w:
        return "eqp"
    return ""


def _role(unit, machine, ty):
    """자리 이름 → (무엇, 짧은 이름)."""
    if ":" in unit and ty == "eqp":
        return "포트", unit.split(":", 1)[1]
    u = unit.upper()
    rest = unit[len(machine):] if machine and u.startswith(machine.upper()) and len(unit) > len(machine) else unit
    rest = rest.lstrip("_-:.") or unit
    R = rest.upper()
    if ty == "oht" or re.fullmatch(r"V\d{3,}", u):
        return "차량", unit
    if re.fullmatch(r"(RM|CRANE|SC)\d*", R):
        return "크레인", rest
    if re.fullmatch(r"[AM]?_?IN\d*", R) or re.fullmatch(r"[AM]I\d+", R):
        return "입고 포트", rest
    if re.fullmatch(r"[AM]?_?OUT\d*", R) or re.fullmatch(r"[AM]O\d+", R):
        return "출고 포트", rest
    if ty in ("zfs", "stocker"):
        return "선반", rest
    if ty == "eqp":
        return "포트", rest
    return "자리", unit


def _sec(a, b):
    return (b - a).total_seconds()


def dur(sec):
    """초 → '2분 4초' (1초 미만은 소수 한 자리)."""
    if sec is None:
        return ""
    if sec < 1:
        return "%.1f초" % max(0.0, sec)
    s = int(round(sec))
    if s < 60:
        return "%d초" % s
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%d시간 %d분" % (h, m) if m else "%d시간" % h
    return "%d분 %d초" % (m, s) if s else "%d분" % m


def hms(t):
    return t.strftime("%H:%M:%S") if t else ""


def carriers(rows):
    """로그에 있는 캐리어와 줄 수 (많은 순)."""
    evs = (parse_event(r, i) for i, r in enumerate(rows))
    return Counter(e["carrier"] for e in evs if e["carrier"]).most_common()


def trace(rows, carrier=None, now=None):
    """now — 조회한 시각 (없으면 로그 마지막 줄). '지금 여기 N분째' 를 이 시각으로 센다."""
    evs = [e for e in (parse_event(r, i) for i, r in enumerate(rows)) if e["t"] is not None and e["name"]]
    cnt = Counter(e["carrier"] for e in evs if e["carrier"])
    if not cnt:
        raise ValueError("캐리어 ID 가 든 줄을 못 찾았습니다 — CARRIER 열이나 TEXT 안의 CARRIERID 가 있어야 합니다")
    carrier = (carrier or "").strip().upper() or cnt.most_common(1)[0][0]
    evs = [e for e in evs if e["carrier"] == carrier]
    if not evs:
        raise ValueError("캐리어 %s 줄이 없습니다 — 로그에 있는 것: %s"
                         % (carrier, ", ".join(k for k, _ in cnt.most_common(8))))
    evs.sort(key=lambda e: (e["t"], e["i"]))

    # 같은 사건이 2초 안에 또 찍힌 줄 (보내기 로그가 두 번 남는 것 등)
    last_same = {}
    for e in evs:
        key = (e["name"], tuple(sorted((k, v) for k, v in e["f"].items() if k not in _SAME_SKIP)))
        prev = last_same.get(key)
        e["dup"] = bool(prev and _sec(prev, e["t"]) <= 2)
        last_same[key] = e["t"]
        e["who"], e["ko"] = _who(e), _ko(e)

    # ── 장비 종류: 메시지 머리 → 값 안의 종류 → 설비 보고 → 이름 앞 4글자가 같은 장비
    mtype = {}
    for e in evs:
        if e["name"].startswith("STORAGE-") and e["machine"]:
            mtype.setdefault(e["machine"], "stocker")
        elif e["name"].startswith("RAIL-") and e["machine"]:
            mtype.setdefault(e["machine"], "oht")
    for e in evs:
        f = e["f"]
        for a, b in (("SOURCE_ID", "SOURCE_TYPE"), ("DESTINATION_ID", "DESTINATION_TYPE")):
            ty = _type_word(f.get(b))
            if f.get(a) and ty:
                mtype.setdefault(f[a], ty)
    for e in evs:
        if e["name"].startswith("MHSMCS_CHANGED_DEVICE_INFO") and e["f"].get("DEVICE_ID"):
            mtype.setdefault(e["f"]["DEVICE_ID"], "eqp")

    # ── 자리 → 장비 (화면 · 위치 보고가 확실하다)
    unit_m, vehicles = {}, {}
    for e in evs:
        f = e["f"]
        if e["name"].startswith("UI-") and e["unit"] and e["machine"]:
            unit_m.setdefault(e["unit"], e["machine"])
        if e["name"].endswith("LOCATION_CHANGED_EVENT") and f.get("SUB_LOCATION_ID") and f.get("LOCATION_ID"):
            unit_m.setdefault(f["SUB_LOCATION_ID"], f["LOCATION_ID"])
        if e["name"].startswith("RAIL-") and f.get("VEHICLEID"):
            vehicles.setdefault(f["VEHICLEID"], e["machine"])
    known = set(mtype) | set(unit_m.values())

    def machine_of(unit, fallback=""):
        if unit in unit_m:
            return unit_m[unit]
        if unit in vehicles:
            return vehicles[unit]
        best, bl = "", 0
        for m in known:
            n = len(os.path.commonprefix([m.upper(), unit.upper()]))
            if n >= 5 and n > bl:
                best, bl = m, n
        return best or fallback

    def type_of(m):
        if m in mtype:
            return mtype[m]
        for k, ty in mtype.items():
            if len(os.path.commonprefix([k.upper(), m.upper()])) >= 4:
                return ty
        return "etc"

    # ── 위치 관측 (시각, 자리, 장비, 상태)
    obs = []
    for e in evs:
        n, f = e["name"], e["f"]
        if n.startswith("UI-") and e["unit"]:
            st = f.get("STATE", "")
            if st.upper() == "MOVING":          # 떠나는 중이라는 화면 갱신 — 새 자리가 아니다
                continue
            obs.append((e["t"], e["unit"], e["machine"] or machine_of(e["unit"]), st, e))
        elif n.endswith("LOCATION_CHANGED_EVENT") and (f.get("SUB_LOCATION_ID") or f.get("LOCATION_ID")):
            u = f.get("SUB_LOCATION_ID") or f.get("DETAIL_LOCATION_ID") or f["LOCATION_ID"]
            obs.append((e["t"], u, f.get("LOCATION_ID") or machine_of(u), f.get("CARRIER_STATE", ""), e))
        elif f.get("CARRIERLOC"):
            u = f["CARRIERLOC"]
            obs.append((e["t"], u, machine_of(u, e["machine"]), "", e))
        elif (n.startswith("MHSMCS_CHANGED_DEVICE_INFO") and f.get("DEVICE_ID")
              and "OCC" in f.get("SUB_DEVICE_LOAD_STATE", "").upper()):
            d = f["DEVICE_ID"]
            obs.append((e["t"], "%s:%s" % (d, f.get("SUB_DEVICE_ID", "")) if f.get("SUB_DEVICE_ID") else d, d, "", e))

    seen_units = {o[1] for o in obs}

    def canon(u):                               # 포트의 OP · LP 자리는 한 포트로
        m = re.match(r"^(.*)_(OP|LP|BP|IP)$", u)
        return m.group(1) if m and m.group(1) in seen_units else u

    stays = []
    for t, u, m, st, e in obs:
        cu = canon(u)
        if stays and stays[-1]["unit"] == cu:
            s = stays[-1]
            s["last"] = t
            if u not in s["raw"]:
                s["raw"].append(u)
            continue
        stays.append({"unit": cu, "machine": m or machine_of(cu), "first": t, "last": t, "raw": [u]})
    # 깜빡임(A → B → A, B 가 1.5초 미만) 은 A 로 합친다
    k = 1
    while k < len(stays) - 1:
        a, b, c = stays[k - 1], stays[k], stays[k + 1]
        if a["unit"] == c["unit"] and _sec(b["first"], c["first"]) < 1.5:
            a["last"] = c["last"]
            a["raw"] += [x for x in c["raw"] if x not in a["raw"]]
            del stays[k:k + 2]
            k = max(1, k - 1)
        else:
            k += 1

    for i, s in enumerate(stays):
        s["type"] = type_of(s["machine"]) if s["unit"] not in vehicles else "oht"
        s["role"], s["short"] = _role(s["unit"], s["machine"], s["type"])
        s["leave"] = stays[i + 1]["first"] if i + 1 < len(stays) else None
        s["dwell"] = _sec(s["first"], s["leave"]) if s["leave"] else None

    def find(suffix, lo, hi, **match):
        for e in evs:
            if lo <= e["t"] <= hi and e["name"].endswith(suffix) and all(e["f"].get(a) == b for a, b in match.items()):
                return e
        return None

    for s in stays:                              # 차량: 주행 = 집기 끝 → 내려놓기 시작
        if s["role"] == "차량":
            hi = s["leave"] or evs[-1]["t"]
            acq = find("VEHICLEACQUIRECOMPLETED", s["first"], hi, VEHICLEID=s["unit"])
            dep = find("VEHICLEDEPOSITSTARTED", s["first"], hi, VEHICLEID=s["unit"])
            s["drive"] = _sec(acq["t"] if acq else s["first"], dep["t"]) if dep else None

    # ── 장비 단위로 묶기 · 장비 사이를 어떻게 건넜나
    legs = []
    for i, s in enumerate(stays):
        if legs and legs[-1]["machine"] == s["machine"]:
            legs[-1]["stays"].append(i)
        else:
            legs.append({"machine": s["machine"], "type": s["type"], "stays": [i]})
    for L in legs:
        a, b = stays[L["stays"][0]], stays[L["stays"][-1]]
        L["first"], L["last"], L["leave"] = a["first"], b["last"], b["leave"]
        L["dwell"] = _sec(a["first"], b["leave"]) if b["leave"] else None

    links = []
    for L, N in zip(legs, legs[1:]):
        a, b = stays[L["stays"][-1]], stays[N["stays"][0]]
        gap = _sec(a["last"], b["first"])
        if b["role"] == "차량":
            acq = find("VEHICLEACQUIRESTARTED", a["first"], b["first"], VEHICLEID=b["unit"])
            links.append({"kind": "acquire", "l1": "OHT 집기" if acq else "OHT 에 실림",
                          "l2": dur(_sec(acq["t"], b["first"])) if acq else "", "sec": _sec(acq["t"], b["first"]) if acq else 0})
        elif a["role"] == "차량":
            dep = find("VEHICLEDEPOSITSTARTED", a["first"], b["first"], VEHICLEID=a["unit"])
            links.append({"kind": "deposit", "l1": "내려놓기" if dep else "OHT 에서 내림",
                          "l2": dur(_sec(dep["t"], b["first"])) if dep else "", "sec": _sec(dep["t"], b["first"]) if dep else 0})
        elif gap > 15:
            links.append({"kind": "gap", "l1": "위치 기록 없음", "l2": dur(gap), "sec": gap})
        else:
            links.append({"kind": "plain", "l1": "옮김", "l2": dur(gap) if gap >= 1 else "", "sec": gap})

    # ── 캐리어 정보 · 반송 작업 · 목적지
    info = {}
    for e in evs:
        f = e["f"]
        for key, names in (("kind", ("CARRIER_TYPE", "CARRIERTYPE")), ("sub", ("CARRIER_SUB_TYPE",)),
                           ("lot", ("LOT_ID", "LOTID")), ("qty", ("WAFER_QTY",)), ("prio", ("PRIORITY",)),
                           ("job", ("MCS_JOB_ID", "COMMANDID")), ("step", ("STEPID", "OPERATION_ID"))):
            for n in names:
                if f.get(n) and key not in info:
                    info[key] = f[n]
    if "kind" not in info:
        for e in evs:
            ty = e["f"].get("TYPE", "")
            if e["name"].startswith("UI-") and ty and ty != "ALL":
                info["kind"] = ty
                break

    dests, job = [], {}
    for e in evs:
        n, f = e["name"], e["f"]
        if n.endswith("MATERIAL_DEST_REP") and f.get("DESTINATION_ID"):
            dests.append((e["t"], f["DESTINATION_ID"], "MES 답"))
        if "TRANSPORT_JOB_" in n:
            if f.get("DESTINATION_ID"):
                dests.append((e["t"], f["DESTINATION_ID"], n))
            if n.endswith("CREATED_EVENT"):
                job = {"id": f.get("MCS_JOB_ID", ""), "created": e["t"]}
            elif job is not None:
                for word, key in (("STARTED", "started"), ("COMPLETED", "completed"), ("ABORT", "stopped"),
                                  ("CANCEL", "stopped"), ("FAIL", "stopped")):
                    if word in n:
                        job[key] = e["t"]
                        job.setdefault("id", f.get("MCS_JOB_ID", ""))
    dest_seq = []
    for t, d, why in dests:
        if not dest_seq or dest_seq[-1][1] != d:
            dest_seq.append((t, d, why))

    # ── 지금 상태 (조회 시각 now, 없으면 로그 마지막 줄 기준)
    end = evs[-1]["t"]
    if now is not None and now > end:
        end = now
    last = stays[-1] if stays else None
    place = _place(last) if last else "위치 모름"
    done = bool(job.get("completed") and job["completed"] >= job.get("created", job["completed"]))
    for e in evs:                                # 목적지 id 도 장비로 알아 둔다 (이름 앞글자로 종류 추정)
        for k in ("DESTINATION_ID", "SOURCE_ID", "LOCATION_ID", "DEVICE_ID"):
            if e["f"].get(k):
                known.add(e["f"][k])

    heading = None                               # 가는 곳 — 끝나지 않았을 때만
    if not done and last is not None and dest_seq:
        final = dest_seq[-1][1]
        dm, du = final, ""
        nxt = next((e for e in reversed(evs) if e["name"] == "RAIL-CARRIERTRANSFER" and e["f"].get("DESTUNIT")), None)
        if last["role"] == "차량" and nxt is not None:
            du = nxt["f"]["DESTUNIT"]
            dm = machine_of(du) or final
        else:
            for e in reversed(evs):
                if e["f"].get("DESTINATION_ID") == final and e["f"].get("DETAIL_DESTINATION_ID"):
                    du = e["f"]["DETAIL_DESTINATION_ID"]
                    break
        if dm and dm != last["machine"]:
            ty = type_of(dm)
            role, short = _role(du, dm, ty) if du and du != dm else ("", "")
            heading = {"machine": dm, "type": ty, "unit": du or dm, "role": role, "short": short, "final": final}

    def _hd():
        if not heading:
            return dest_seq[-1][1] if dest_seq else "?"
        return " ".join(x for x in (TYPE_KO[heading["type"]], heading["machine"], heading["role"], heading["short"]) if x)

    since = _sec(last["first"], end) if last else 0
    if done:
        status = {"code": "done", "ko": "반송 완료", "where": place,
                  "detail": "도착 %s · 반송 작업 완료 %s" % (hms(last["first"]), hms(job["completed"]))}
    elif job.get("stopped"):
        status = {"code": "stopped", "ko": "반송 중단", "where": place, "detail": "중단 %s" % hms(job["stopped"])}
    elif last and last["role"] == "차량":
        status = {"code": "moving", "ko": "이동 중", "where": place,
                  "detail": "가는 곳 %s · 실린 지 %s" % (_hd(), dur(since))}
    elif last and last["role"] == "크레인":
        status = {"code": "moving", "ko": "이동 중", "where": place, "detail": "크레인이 옮기는 중 · %s째" % dur(since)}
    elif job.get("created"):
        status = {"code": "waiting", "ko": "반송 대기", "where": place,
                  "detail": "가는 곳 %s · 여기서 %s째" % (_hd(), dur(since))}
    else:
        status = {"code": "idle", "ko": "머무는 중", "where": place,
                  "detail": "%s 부터 · 반송 작업 없음" % hms(last["first"]) if last else ""}
    status["at"] = end

    # 기록이 끊긴 구간 앞 자리는 본 만큼만 머문 것으로 (끊긴 시간을 머문 시간으로 세지 않는다)
    for L, lk in zip(legs, links):
        if lk["kind"] == "gap":
            stays[L["stays"][-1]]["gap_after"] = True
    for s in stays:
        if s["leave"] is None:
            s["until"] = s["last"] if done else end
            s["ongoing"] = not done
            s["since"] = _sec(s["first"], end)
        else:
            s["until"] = s["last"] if s.get("gap_after") else s["leave"]
        s["dwell"] = _sec(s["first"], s["until"]) if s["leave"] is not None else None
    for L in legs:
        L["until"] = stays[L["stays"][-1]]["until"]
        L["dwell"] = _sec(L["first"], L["until"]) if L["leave"] is not None else None

    # ── 눈여겨볼 것
    notes = []
    if len({d for _, d, _ in dest_seq}) > 1:
        chain = " → ".join(d for _, d, _ in dest_seq)
        t_ch = dest_seq[-1][0]
        after = " (작업 생성 %s 뒤)" % dur(_sec(job["created"], t_ch)) if job.get("created") and t_ch >= job["created"] else ""
        notes.append("목적지 변경: %s · %s%s" % (chain, hms(t_ch), after))
    for e in evs:
        f = e["f"]
        if e["name"].startswith("MHSMCS_CHANGED_DEVICE_INFO") and f.get("DEVICE_STATE", "UP").upper() != "UP":
            notes.append("설비 %s 상태 %s 보고 (%s)" % (f.get("DEVICE_ID", "?"), f["DEVICE_STATE"], hms(e["t"])))
        if e["name"].endswith("REPLY") and (f.get("HCACK", "0") not in ("0", "4") or f.get("RESULTCODE", "0") not in ("0", "4")):
            notes.append("%s 응답 이상 HCACK=%s RESULTCODE=%s (%s)" % (e["name"], f.get("HCACK", "-"), f.get("RESULTCODE", "-"), hms(e["t"])))
        if re.search(r"ABORT|CANCEL|FAIL", e["name"]):
            notes.append("%s (%s)" % (e["name"], hms(e["t"])))
    for L, lk, N in zip(legs, links, legs[1:]):
        if lk["kind"] == "gap":
            why = ""
            if not job.get("created") or job["created"] > N["first"]:
                why = " — 반송 작업 없이 들어옴"
            notes.append("%s %s → %s %s 사이 %s 는 MCS 위치 기록이 없음%s"
                         % (TYPE_KO[L["type"]], L["machine"], TYPE_KO[N["type"]], N["machine"], lk["l2"], why))
    waits = [s for s in stays if s["dwell"] and s["role"] not in ("차량", "크레인")]
    if waits:
        w = max(waits, key=lambda s: s["dwell"])
        if w["dwell"] >= 60:
            notes.append("가장 오래 머문 곳: %s %s %s %s %s" % (TYPE_KO[w["type"]], w["machine"], w["role"], w["short"], dur(w["dwell"])))

    key = [e for e in evs if e["name"] in _KEY and not e["dup"]]
    return {
        "carrier": carrier, "carriers": cnt.most_common(), "rows": len(rows), "events": evs,
        "t0": evs[0]["t"], "t1": end, "t_last": evs[-1]["t"], "now": now, "stays": stays, "legs": legs,
        "links": links, "info": info, "job": job, "dests": dest_seq, "status": status, "notes": notes,
        "key": key, "heading": heading, "fab": _fab(evs),
    }


def _fab(evs):
    fab = floor = ""
    for e in evs:
        f = e["f"]
        fab = fab or f.get("Factory") or f.get("Facility") or f.get("CARRIERSHOPNAME") or ""
        floor = floor or f.get("CURRENT_FLOOR") or ""
    return {"fab": fab, "floor": floor}


def _place(s):
    if s is None:
        return ""
    r = s["role"] + (" " + s["short"] if s["short"].isdigit() else "")
    tail = "" if s["short"].isdigit() else " " + s["short"]
    if s["role"] == "차량":
        return "OHT %s (%s)" % (s["unit"], s["machine"])
    return "%s %s %s%s" % (TYPE_KO[s["type"]], s["machine"], r, tail)


def _stay_time(s, t):
    """자리 아래 넷째 줄 — 머문 시간을 무엇을 했는지와 함께."""
    if s["leave"] is None:
        if t["status"]["code"] == "done":
            return "도착 · 완료"
        return "지금 여기 · %s째" % dur(s["since"]) if s.get("since", 0) >= 1 else "지금 여기"
    if s["role"] == "차량":
        return "주행 " + dur(s["drive"]) if s.get("drive") else "실려 " + dur(s["dwell"])
    if s["role"] == "크레인":
        return "이동 " + dur(s["dwell"])
    if s.get("gap_after") and s["dwell"] < 1:
        return "한 번 보임"
    return "대기 " + dur(s["dwell"])


# ═════════════════════════════════════════════════════════════════════
# 4. LLM 에 줄 요약
# ═════════════════════════════════════════════════════════════════════

def facts_text(t, max_sub=8):
    st, info = t["status"], t["info"]
    head = " · ".join(x for x in (info.get("kind", "") + (" " + info["sub"] if info.get("sub") else ""),
                                  "LOT " + info["lot"] if info.get("lot") else "",
                                  info["qty"] + "매" if info.get("qty") else "") if x.strip())
    L = ["[MCS 캐리어 이동 — 로그에서 뽑은 사실만]",
         "캐리어 %s%s" % (t["carrier"], " · " + head if head else ""),
         "지금: %s — %s · %s" % (st["ko"], st["where"], st["detail"]),
         "로그 범위: %s ~ %s (%s · %d줄 중 이 캐리어 %d줄)%s" % (
             t["t0"].strftime("%Y-%m-%d %H:%M:%S"), hms(t["t_last"]), dur(_sec(t["t0"], t["t_last"])), t["rows"],
             len(t["events"]), " · 기준 시각 %s" % hms(t["t1"]) if t["t1"] > t["t_last"] else ""),
         "", "경로 (장비 순서)"]
    stays, key = t["stays"], t["key"]
    for n, L_ in enumerate(t["legs"], 1):
        a, b = stays[L_["stays"][0]], stays[L_["stays"][-1]]
        if b["leave"] is None and st["code"] != "done":
            span = hms(a["first"]) + " 부터 지금까지 (%s째)" % dur(_sec(a["first"], t["t1"]))
        elif b["leave"] is None:
            span = hms(a["first"]) + " 도착"
        elif L_["dwell"] < 1:
            span = hms(a["first"]) + " 에 보임"
        else:
            span = "%s ~ %s" % (hms(a["first"]), hms(b["until"]))
        extra = " (%s)" % dur(L_["dwell"]) if L_["dwell"] and L_["dwell"] >= 1 else ""
        if len(L_["stays"]) == 1:
            s = a
            what = s["role"] + " " + s["short"]
            if s["role"] == "차량" and s.get("drive"):
                extra = " (%s · 주행 %s)" % (dur(s["dwell"]), dur(s["drive"])) if s["dwell"] else ""
            L.append("%d. %s %s %s — %s%s" % (n, TYPE_KO[L_["type"]], L_["machine"], what, span, extra))
            subs = [e for e in key if s["first"] <= e["t"] < (s["leave"] or datetime.max) and e["name"] not in _LOC_ONLY]
            if subs:
                L.append("   " + " · ".join("%s %s" % (hms(e["t"]), e["ko"]) for e in subs[:max_sub]))
        else:
            L.append("%d. %s %s — %s%s" % (n, TYPE_KO[L_["type"]], L_["machine"], span, extra))
            for i in L_["stays"]:
                s = stays[i]
                L.append("   · %s %s %s (%s ~ %s)" % (s["role"], s["short"], _stay_time(s, t), hms(s["first"]), hms(s["until"]) if s["leave"] else "지금"))
                subs = [e for e in key if s["first"] <= e["t"] < (s["leave"] or datetime.max) and e["name"] not in _LOC_ONLY]
                if subs:
                    L.append("     " + " · ".join("%s %s" % (hms(e["t"]), e["ko"]) for e in subs[:max_sub]))
        if n <= len(t["links"]):
            lk = t["links"][n - 1]
            L.append("   → %s %s" % (lk["l1"], lk["l2"]))
    if t.get("heading"):
        h = t["heading"]
        L.append("   → 가는 곳: %s (도착 기록은 아직 없음)" % " ".join(
            x for x in (TYPE_KO[h["type"]], h["machine"], h["role"], h["short"]) if x))
    job = t["job"]
    if job.get("created"):
        parts = ["생성 " + hms(job["created"])]
        if job.get("started"):
            parts.append("시작 " + hms(job["started"]))
        if job.get("completed"):
            parts.append("완료 %s (%s)" % (hms(job["completed"]), dur(_sec(job["created"], job["completed"]))))
        if job.get("stopped"):
            parts.append("중단 " + hms(job["stopped"]))
        L += ["", "반송 작업 %s: %s%s" % (job.get("id") or info.get("job", ""), " → ".join(parts),
                                       " · 우선순위 " + info["prio"] if info.get("prio") else "")]
    if t["notes"]:
        L += ["", "눈여겨볼 것"] + ["- " + x for x in t["notes"]]
    return "\n".join(L)


_LOC_ONLY = {"MCSMHS_CARRIER_LOCATION_CHANGED_EVENT", "UI-CARRIER"}


# ═════════════════════════════════════════════════════════════════════
# 5. 그림 — FAB 안에서 캐리어가 OHT 에 매달려 가는 모습 (옆에서 본 그림)
#    천장 레일 · OHT · 스토커(포트 · 크레인 · 선반) · ZFS 선반 · 설비. 색은 장비 종류 하나만 뜻한다.
# ═════════════════════════════════════════════════════════════════════

_LIGHT = {"stocker": "#2a78d6", "oht": "#eb6834", "zfs": "#1baf7a", "eqp": "#eda100", "etc": "#898781"}
_DARK = {"stocker": "#3987e5", "oht": "#d95926", "zfs": "#199e70", "eqp": "#c98500", "etc": "#898781"}
_INK_L = ("--ink:#0b0b0b;--ink2:#52514e;--mute:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--surf:#fcfcfb;"
          "--good:#0ca30c;--crit:#d03b3b;--foup:#3b3f46;--rail:#a9a8a0;--wall:#f3f2ee")
_INK_D = ("--ink:#ffffff;--ink2:#c3c2b7;--mute:#898781;--grid:#2c2c2a;--axis:#383835;--surf:#1a1a19;"
          "--good:#0ca30c;--crit:#d03b3b;--foup:#e6e5df;--rail:#5d5c57;--wall:#212120")


def _e(s):
    return html.escape(str(s), quote=True)


def _tw(s, fs, bold=False):
    """글자 폭 어림 (브라우저에서 잰 값 · 넓은 글꼴 기준이라 좁은 글꼴에서는 조금 남는다)."""
    up, dg, lo, pu = (0.74, 0.70, 0.62, 0.40) if bold else (0.66, 0.64, 0.55, 0.34)
    w = 0.0
    for ch in str(s):
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or 0x4E00 <= o <= 0x9FFF:
            w += fs
        elif ch in "MW@%":
            w += fs * (up + 0.18)
        elif ch.isupper():
            w += fs * up
        elif ch.isdigit():
            w += fs * dg
        elif ch == " ":
            w += fs * 0.32
        elif ch in "·:.,;|!il'()[]":
            w += fs * pu
        elif ch.islower():
            w += fs * lo
        else:
            w += fs * 0.64
    return w


def _clip(s, fs, width, bold=False):
    s = str(s)
    if _tw(s, fs, bold) <= width:
        return s
    while s and _tw(s + "…", fs, bold) > width:
        s = s[:-1]
    return s + "…"


def _style(u):
    lt = ";".join("--c-%s:%s" % kv for kv in _LIGHT.items())
    dk = ";".join("--c-%s:%s" % kv for kv in _DARK.items())
    d = "%s;%s" % (_INK_D, dk)
    return (
        "#{u}{{{il};{lt};font-family:system-ui,-apple-system,'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif}}"
        "#{u}[data-theme=dark],:root[data-theme=dark] #{u}:not([data-theme=light]){{{d}}}"
        "@media (prefers-color-scheme:dark){{:root:not([data-theme=light]) #{u}:not([data-theme=light]),"
        "svg#{u}:root:not([data-theme=light]){{{d}}}}}"
        "#{u} text{{fill:var(--ink);font-size:12px}}"
        "#{u} .t2{{fill:var(--ink2)}}#{u} .mu{{fill:var(--mute)}}#{u} .b{{font-weight:600}}"
        "#{u} .h1{{font-size:20px;font-weight:700}}#{u} .h2{{font-size:13px;font-weight:600}}"
        "#{u} .s11{{font-size:11px}}#{u} .s14{{font-size:14px}}#{u} .num{{font-variant-numeric:tabular-nums}}"
        "#{u} .bg{{fill:var(--surf)}}#{u} .hair{{stroke:var(--grid);stroke-width:1}}"
        "#{u} .rt{{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}}"
        "#{u} .dash{{stroke-dasharray:7 6}}"
        "#{u} .pill{{fill:var(--surf);stroke:var(--ink2);stroke-width:1}}"
        "#{u} .badge circle{{fill:var(--ink)}}#{u} .badge text{{fill:var(--surf);font-size:11px;font-weight:700}}"
        "#{u} .badge.on circle{{fill:var(--c-oht)}}"
        "#{u}.playing .still{{display:none}}#{u}:not(.playing) .anim{{display:none}}"
    ).format(u=u, il=_INK_L, lt=lt, d=d)


def _c(ty):
    return "var(--c-%s)" % ty


def _arrow_at(x, y, ang, css, size=9):
    ca, sa = math.cos(ang), math.sin(ang)
    p1 = (x - size * ca + size * 0.55 * sa, y - size * sa - size * 0.55 * ca)
    p2 = (x - size * ca - size * 0.55 * sa, y - size * sa + size * 0.55 * ca)
    return '<path d="M%.1f %.1fL%.1f %.1fL%.1f %.1fz" style="fill:%s"/>' % (x, y, p1[0], p1[1], p2[0], p2[1], css)


def _poly(pts, css, dash=False, opacity=1.0, arrow=True):
    pts = [p for i, p in enumerate(pts) if i == 0 or abs(p[0] - pts[i - 1][0]) + abs(p[1] - pts[i - 1][1]) > 0.1]
    if len(pts) < 2:
        return ""
    d = "M" + "L".join("%.1f %.1f" % (x, y) for x, y in pts)
    out = '<path d="%s" class="rt%s" style="stroke:%s;opacity:%s"/>' % (d, " dash" if dash else "", css, opacity)
    if arrow:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        out += '<g style="opacity:%s">%s</g>' % (opacity, _arrow_at(x2, y2, math.atan2(y2 - y1, x2 - x1), css))
    return out


def _bez(p0, p1, p2, p3, k):
    m = 1 - k
    return (m ** 3 * p0[0] + 3 * m * m * k * p1[0] + 3 * m * k * k * p2[0] + k ** 3 * p3[0],
            m ** 3 * p0[1] + 3 * m * m * k * p1[1] + 3 * m * k * k * p2[1] + k ** 3 * p3[1])


_WID = {"stocker": 236, "eqp": 150, "zfs": 176, "etc": 132, "rail": 30}


def _scene(t, width=960):
    """장면 배치 · 캐리어가 지나간 길 · 움직임(시각별 자리)을 계산한다."""
    stays, legs, links, st, evs = t["stays"], t["legs"], t["links"], t["status"], t["events"]
    M = 24
    stations, trans, pend = [], [], []
    for li, L in enumerate(legs):
        if L["type"] == "oht":
            pend.append(li)
            continue
        if stations or pend:
            if not stations:
                stations.append({"kind": "rail", "type": "rail", "machine": "", "stays": []})
            trans.append({"kind": "oht" if pend else links[li - 1]["kind"], "legs": pend, "link": links[li - 1]})
            pend = []
        stations.append({"kind": "real", "type": L["type"], "machine": L["machine"], "stays": list(L["stays"])})
    hd = t.get("heading")
    if pend or (hd and st["code"] in ("waiting", "moving")):
        if not stations:
            stations.append({"kind": "rail", "type": "rail", "machine": "", "stays": []})
        if hd:
            stations.append({"kind": "ghost", "type": hd["type"], "machine": hd["machine"], "stays": [], "hd": hd})
        else:
            stations.append({"kind": "rail", "type": "rail", "machine": "", "stays": []})
        trans.append({"kind": "oht" if pend else "plan", "legs": pend, "link": None, "ongoing": True})

    def manual(si, first):
        s = stations[si]
        if s["type"] != "stocker" or not s["stays"]:
            return False
        st_ = stays[s["stays"][0 if first else -1]]
        return st_["role"] == ("입고 포트" if first else "출고 포트") and st_["short"].upper().startswith("M")

    ws = [_WID.get(s["type"], 132) for s in stations]
    gs = [{"oht": 210, "gap": 150, "plan": 180}.get(tr["kind"], 120)
          + (120 if tr["kind"] not in ("oht", "plan") and manual(i + 1, True) else 0)
          + (60 if tr["kind"] not in ("oht", "plan") and manual(i, False) else 0) for i, tr in enumerate(trans)]
    need = sum(ws) + sum(gs)
    W = max(width, int(need + 2 * M + 24))
    spare = W - 2 * M - need
    x = M + (spare * 0.06 if gs else spare / 2)
    if gs:
        gs = [g + spare * 0.88 / len(gs) for g in gs]
    for i, (s, w) in enumerate(zip(stations, ws)):
        s["x0"], s["w"], s["cx"] = x, w, x + w / 2
        x += w + (gs[i] if i < len(gs) else 0)

    Y0 = 132
    G = {"W": W, "M": M, "CEIL": Y0, "RAIL": Y0 + 34}
    RAIL = G["RAIL"]
    G["RET"] = RET = RAIL + 29                    # 집게가 다 올라간 자리 = 실린 FOUP 윗면
    G["CARRY"] = CARRY = RET + 15                 # 실린 FOUP 가운데
    G["SHELF"] = SHELF = RAIL + 124               # ZFS 선반 윗면
    G["ROOF"] = ROOF = RAIL + 160                 # 스토커 지붕
    G["FLOOR"] = FLOOR = RAIL + 362
    G["EQ_TOP"] = EQ_TOP = FLOOR - 120
    G["MID"] = MID = (ROOF + FLOOR) / 2

    pos = {}
    for si, s in enumerate(stations):
        cx, ty, ids = s["cx"], s["type"], s["stays"]
        oht_in = si > 0 and trans[si - 1]["kind"] in ("oht", "plan")
        oht_out = si < len(trans) and trans[si]["kind"] in ("oht", "plan")
        rack = 0
        for k, i in enumerate(ids):
            r, sh = stays[i]["role"], stays[i]["short"].upper()
            if ty == "stocker":
                if r == "입고 포트":
                    side = sh.startswith("M") and not (k == 0 and oht_in)
                    p = (s["x0"] - 24, FLOOR - 101, "side") if side else (cx - 74, ROOF - 17, "roof")
                elif r == "출고 포트":
                    side = sh.startswith("M") and not (k == len(ids) - 1 and oht_out)
                    p = (s["x0"] + s["w"] + 24, FLOOR - 101, "side") if side else (cx + 74, ROOF - 17, "roof")
                elif r == "크레인":
                    p = (cx, MID, "crane")
                else:
                    p = (cx - 72 if rack % 2 == 0 else cx + 72, FLOOR - 43 - 30 * (rack // 2 % 4), "rack")
                    rack += 1
            elif ty == "zfs":
                p = (cx + (k - (len(ids) - 1) / 2) * 38, SHELF - 11, "slot")
            else:
                p = (cx + (k - (len(ids) - 1) / 2) * 42, EQ_TOP - 17, "top")
            pos[i] = p
        if s["kind"] == "ghost":
            s["entry"] = {"stocker": (cx - 74, ROOF - 17, "roof"), "zfs": (cx, SHELF - 11, "slot")}.get(ty, (cx, EQ_TOP - 17, "top"))
        elif s["kind"] == "rail":
            s["entry"] = (cx, CARRY, "rail")
        else:
            s["entry"] = pos[ids[0]]
        s["exit"] = pos[ids[-1]] if ids else s["entry"]

    def inner(s, pa, pb):
        if s["type"] != "stocker":
            return [pa[:2], pb[:2]]
        cx, top = s["cx"], ROOF + 16

        def way(p):
            if p[2] == "roof":
                return [(p[0], top), (cx, top)]
            if p[2] in ("side", "rack"):
                return [(cx, p[1])]
            return []
        return [pa[:2]] + way(pa) + list(reversed(way(pb))) + [pb[:2]]

    for si, tr in enumerate(trans):
        A_, B_ = stations[si], stations[si + 1]
        P, Q = A_["exit"], B_["entry"]
        if tr["kind"] == "plan" and A_["type"] == "stocker" and P[2] != "roof":
            out = (A_["cx"] + 74, ROOF - 17, "roof")
            top = ROOF + 16
            way = [(A_["cx"], P[1])] if P[2] in ("side", "rack") else []
            tr["pre"] = [P[:2]] + way + [(A_["cx"], top), (out[0], top), out[:2]]
            P = out
        if tr["kind"] in ("oht", "plan") or (tr["kind"] == "gap" and Q[2] != "side"):
            tr["path"] = [P[:2], (P[0], CARRY), (Q[0], CARRY), Q[:2]]
        elif tr["kind"] == "gap":                   # 사람이 옮긴 듯한 길 — 몸통 옆으로 나와 바닥을 지나 포트 밑에서 올라간다
            fx = Q[0] - 14
            if P[2] == "side":
                pts = [P[:2], (P[0] + 14, P[1]), (P[0] + 14, FLOOR - 16)]
            else:
                ex = max(P[0], A_["x0"] + A_["w"]) + 18
                pts = [P[:2], (P[0], P[1] - 28), (ex, P[1] - 28), (ex, FLOOR - 16)]
            tr["path"] = pts + [(fx, FLOOR - 16), (fx, Q[1])]
        else:
            tr["path"] = [P[:2], Q[:2]]
        tr["P"], tr["Q"] = P, Q

    # ── 움직임 (초 · 로그 첫 줄부터): FOUP 자리, OHT 자리 · 집게 높이
    t0 = t["t0"]

    def S(tt):
        return round(_sec(t0, tt), 3)

    fk, ok, marks = [], [], []

    def along(pts, ta, tb):
        marks.extend([ta, tb])
        L = [0.0]
        for p1, p2 in zip(pts, pts[1:]):
            L.append(L[-1] + math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
        tot = L[-1] or 1.0
        fk.append((ta, pts[0][0], pts[0][1]))
        for p, ln in zip(pts[1:], L[1:]):
            fk.append((ta + (tb - ta) * ln / tot, p[0], p[1]))

    def ev_t(suffix, veh, lo, hi):
        for e in evs:
            if e["name"].endswith(suffix) and e["f"].get("VEHICLEID") == veh and lo <= e["t"] <= hi:
                return e["t"]
        return None

    oht_static = None
    for si, s in enumerate(stations):
        ids = s["stays"]
        for k, i in enumerate(ids):
            a = stays[i]
            fk.append((S(a["first"]), pos[i][0], pos[i][1]))
            marks.extend([S(a["first"]), S(a["last"])])
            if k + 1 < len(ids):
                b = stays[ids[k + 1]]
                along(inner(s, pos[i], pos[ids[k + 1]]), S(a["last"]), S(b["first"]))
        if si >= len(trans):
            break
        tr, N = trans[si], stations[si + 1]
        P, Q = tr["P"], tr["Q"]
        Pst = stays[ids[-1]] if ids else None
        Qst = stays[N["stays"][0]] if N["stays"] else None
        if tr["kind"] in ("gap", "plain", "move"):
            if Pst and Qst:
                along(tr["path"], S(Pst["last"]), S(Qst["first"]))
            continue
        if tr["kind"] != "oht":
            continue
        V = stays[legs[tr["legs"][0]]["stays"][0]]
        veh = tr["veh"] = V["unit"]
        lo = Pst["first"] if Pst else V["first"]
        acq = ev_t("VEHICLEACQUIRESTARTED", veh, lo, V["first"])
        sl = S(V["first"])
        sa = S(acq) if acq else sl - 5
        call = next((e["t"] for e in reversed(evs) if e["name"] in ("RAIL-CARRIERTRANSFER", "RAIL-STAGECOMMAND")
                     and e["t"] <= (acq or V["first"]) and e["t"] >= lo), None)
        sc = min(S(call) if call else sa - 15, sa - 1)
        up = sa + 0.45 * (sl - sa)
        marks.extend([sc, sa, up, sl])
        tr["t_pick"] = sl - sa
        if Pst is not None:
            ok.extend([(sc, P[0] - 320, RET, veh), (sa, P[0], RET, veh), (up, P[0], P[1] - 15, veh), (sl, P[0], RET, veh)])
            fk.extend([(up, P[0], P[1]), (sl, P[0], CARRY)])
        else:
            ok.append((sl, P[0], RET, veh))
            fk.append((sl, P[0], CARRY))
        dep = ev_t("VEHICLEDEPOSITSTARTED", veh, V["first"], Qst["first"] if Qst else t["t1"])
        if Qst is not None:
            sq = S(Qst["first"])
            sd = S(dep) if dep else max(sl, sq - 6)
            down = sd + 0.6 * (sq - sd)
            marks.extend([sd, down, sq, sq + 20])
            fk.extend([(sd, Q[0], CARRY), (down, Q[0], Q[1])])
            ok.extend([(sd, Q[0], RET, veh), (down, Q[0], Q[1] - 15, veh), (sq, Q[0], RET, veh),
                       (sq + 20, Q[0] + 320, RET, veh), (sq + 20.01, None, RET, veh)])
            tr["t_drive"], tr["t_drop"] = sd - sl, sq - sd
            oht_static = {"x": Q[0], "grip": RET, "carry": False, "veh": veh, "moving": False}
        else:
            se = S(t["t1"])
            xn = P[0] + (Q[0] - P[0]) * 0.55
            fk.append((se, xn, CARRY))
            ok.append((se, xn, RET, veh))
            tr["now_x"], tr["t_drive"] = xn, se - sl
            oht_static = {"x": xn, "grip": RET, "carry": True, "veh": veh, "moving": True,
                          "dir": 1 if Q[0] >= P[0] else -1}
    fk.sort(key=lambda k: k[0])
    ok.sort(key=lambda k: k[0])
    last = stays[-1] if stays else None
    if last is not None and last["role"] == "차량" and oht_static and oht_static["moving"]:
        foup = (oht_static["x"], CARRY)
    elif last is not None and last["unit"] in [stays[i]["unit"] for i in pos]:
        foup = pos[len(stays) - 1][:2]
    else:
        foup = fk[-1][1:3] if fk else (M, CARRY)
    steps = [[S(s["first"]), S(s["until"])] for s in stays]
    return {"G": G, "stations": stations, "trans": trans, "pos": pos, "fk": fk, "ok": ok, "marks": sorted(set(round(m, 3) for m in marks)),
            "oht": oht_static, "foup": foup, "steps": steps, "end": S(t["t1"])}


def render_svg(t, width=960, sc=None):
    sc = sc or _scene(t, width)
    G, stations, trans, pos = sc["G"], sc["stations"], sc["trans"], sc["pos"]
    W, M, CEIL, RAIL, RET, CARRY = G["W"], G["M"], G["CEIL"], G["RAIL"], G["RET"], G["CARRY"]
    SHELF, ROOF, FLOOR, EQ_TOP, MID = G["SHELF"], G["ROOF"], G["FLOOR"], G["EQ_TOP"], G["MID"]
    stays, st, info = t["stays"], t["status"], t["info"]
    u = "mp" + hashlib.md5(("%s|%s" % (t["carrier"], t["t0"])).encode("utf-8")).hexdigest()[:8]
    sc["id"] = u
    P = []

    # ── 머리: 캐리어 · 상태 · 지금 위치
    P.append('<text x="%d" y="38" class="h1">캐리어 %s</text>' % (M, _e(t["carrier"])))
    badge = {"done": ("✓", "var(--good)"), "stopped": ("!", "var(--crit)")}.get(st["code"], ("●", "var(--c-oht)"))
    btxt = "%s %s" % (badge[0], st["ko"])
    bw = _tw(btxt, 12, True) + 26
    P.append('<rect x="%.1f" y="18" width="%.1f" height="26" rx="13" style="fill:%s;fill-opacity:.12;stroke:%s;stroke-width:1.2"/>'
             '<text x="%.1f" y="35.5" text-anchor="middle" class="b">%s</text>' % (W - M - bw, bw, badge[1], badge[1], W - M - bw / 2, _e(btxt)))
    meta = [info.get("kind", ""), info.get("sub", ""), "LOT " + info["lot"] if info.get("lot") else "",
            info["qty"] + "매" if info.get("qty") else "", "우선순위 " + info["prio"] if info.get("prio") else "",
            "작업 " + (t["job"].get("id") or info.get("job", "")) if (t["job"].get("id") or info.get("job")) else ""]
    P.append('<text x="%d" y="62" class="t2">%s</text>' % (M, _e(_clip(" · ".join(x for x in meta if x), 12, W - 2 * M))))
    x = M
    P.append('<text x="%d" y="88" class="mu">지금</text>' % x)
    x += _tw("지금", 12) + 10
    P.append('<text x="%.1f" y="88" class="s14 b">%s</text>' % (x, _e(st["where"])))
    x += _tw(st["where"], 14, True) + 10
    P.append('<text x="%.1f" y="88" class="t2">%s</text>' % (x, _e(_clip("· " + st["detail"], 12, W - M - x))))
    P.append('<line x1="%d" x2="%d" y1="104.5" y2="104.5" class="hair"/>' % (M, W - M))

    # ── FAB 틀: 천장 · 레일 · 바닥
    fab = t.get("fab") or {}
    where = " · ".join(x for x in ((fab.get("fab") + " FAB") if fab.get("fab") else "", fab.get("floor", "")) if x) or "FAB"
    P.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" style="fill:var(--wall);stroke:var(--grid)"/>'
             % (M - 8, CEIL - 12, W - 2 * M + 16, FLOOR - CEIL + 24))
    P.append('<text x="%d" y="%d" class="t2 s11 b">%s</text>' % (M + 4, CEIL + 5, _e(where + " · 옆에서 본 그림")))
    P.append('<text id="%s-clock" x="%d" y="%d" text-anchor="end" class="t2 s11 num">%s</text>'
             % (u, W - M - 4, CEIL + 5, _e("로그 %s ~ %s" % (hms(t["t0"]), hms(t["t_last"])))))
    for hx in range(M + 50, W - M - 20, 120):
        P.append('<line x1="%d" x2="%d" y1="%d" y2="%d" style="stroke:var(--axis);stroke-width:1.5"/>' % (hx, hx, CEIL + 10, RAIL - 4))
    P.append('<rect x="%d" y="%d" width="%d" height="8" rx="3" style="fill:var(--rail)"/>' % (M, RAIL - 4, W - 2 * M))
    P.append('<text x="%d" y="%d" class="mu s11">OHT 레일</text>' % (M + 6, RAIL + 18))
    P.append('<rect x="%d" y="%d" width="%d" height="10" style="fill:var(--grid)"/>' % (M - 8, FLOOR, W - 2 * M + 16))
    P.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" style="stroke:var(--axis);stroke-width:1.5"/>' % (M - 8, W - M + 8, FLOOR, FLOOR))

    def foup_at(x, y, faded=False):
        op = ' opacity=".28"' if faded else ""
        return ('<g transform="translate(%.1f %.1f)"%s><rect x="-14" y="-11" width="28" height="22" rx="4" style="fill:var(--foup)"/>'
                '<rect x="-8" y="-15" width="16" height="5" rx="1.5" style="fill:var(--foup)"/></g>' % (x, y, op))

    down_dev = {e["f"].get("DEVICE_ID") for e in t["events"]
                if e["name"].startswith("MHSMCS_CHANGED_DEVICE_INFO") and e["f"].get("DEVICE_STATE", "UP").upper() != "UP"}

    # ── 장비
    for si, s in enumerate(stations):
        ty, cx, x0, w = s["type"], s["cx"], s["x0"], s["w"]
        if ty == "rail":
            continue
        ghost = s["kind"] == "ghost"
        c = _c(ty)
        dash = ";stroke-dasharray:6 5" if ghost else ""
        P.append('<g%s>' % (' opacity=".55"' if ghost else ""))
        used = [pos[i] for i in s["stays"]] + ([s["entry"]] if ghost else [])
        if ty == "stocker":
            P.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" style="fill:%s;fill-opacity:.09;stroke:%s;stroke-width:1.6%s"/>'
                     % (x0, ROOF, w, FLOOR - ROOF, c, c, dash))
            for yy in range(ROOF + 32, FLOOR - 6, 30):
                for xa, xb in ((x0 + 10, cx - 28), (cx + 28, x0 + w - 10)):
                    P.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:%s;stroke-width:1.2;opacity:.35"/>' % (xa, xb, yy, yy, c))
            for k, (fx, fy) in enumerate(((cx - 90, ROOF + 32), (cx - 58, ROOF + 92), (cx + 60, ROOF + 62), (cx + 92, ROOF + 152),
                                          (cx - 90, ROOF + 152))):
                P.append(foup_at(fx, fy - 12, True))
            P.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:%s;stroke-width:3"/>' % (cx, cx, ROOF + 8, FLOOR - 3, c))
            P.append('<rect x="%.1f" y="%.1f" width="30" height="16" rx="3" style="fill:%s"/>' % (cx - 15, MID + 12, c))
            if not any(q[2] == "crane" for q in used):
                P.append('<text x="%.1f" y="%.1f" class="mu s11">크레인</text>' % (cx + 20, MID + 24))
            for p in used:
                if p[2] == "roof":
                    P.append('<rect x="%.1f" y="%d" width="50" height="6" rx="1.5" style="fill:%s"/>' % (p[0] - 25, ROOF - 6, c))
                elif p[2] == "side":
                    P.append('<rect x="%.1f" y="%d" width="54" height="6" rx="1.5" style="fill:%s"/>' % (p[0] - 27, FLOOR - 90, c))
                    P.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:%s;stroke-width:2"/>' % (p[0], p[0], FLOOR - 84, FLOOR, c))
        elif ty == "zfs":
            for hx in (x0 + 10, x0 + w - 10):
                P.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:%s;stroke-width:1.6;opacity:.55%s"/>' % (hx, hx, RAIL + 4, SHELF, c, dash))
            P.append('<rect x="%.1f" y="%d" width="%.1f" height="6" rx="2" style="fill:%s"/>' % (x0 + 4, SHELF, w - 8, c))
            taken = {round(p[0]) for p in used}
            n = int((w - 16) // 38)
            for k in range(n):
                sx = cx + (k - (n - 1) / 2) * 38
                if all(abs(sx - tx) > 12 for tx in taken) and k % 2 == 0:
                    P.append(foup_at(sx, SHELF - 11, True))
        else:
            P.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="6" style="fill:%s;fill-opacity:.10;stroke:%s;stroke-width:1.6%s"/>'
                     % (cx - 70, EQ_TOP, 140, FLOOR - EQ_TOP, c, c, dash))
            if ty == "eqp":
                P.append('<rect x="%.1f" y="%d" width="46" height="28" rx="3" style="fill:none;stroke:%s;stroke-width:1.2"/>' % (cx - 54, EQ_TOP + 22, c))
                P.append('<rect x="%.1f" y="%d" width="60" height="6" rx="2" style="fill:%s;opacity:.5"/>' % (cx - 30, FLOOR - 40, c))
            for p in used:
                P.append('<rect x="%.1f" y="%d" width="54" height="6" rx="1.5" style="fill:%s"/>' % (p[0] - 27, EQ_TOP - 6, c))
            if s["machine"] in down_dev:
                P.append('<circle cx="%.1f" cy="%d" r="5" style="fill:var(--crit)"/>' % (cx + 22, EQ_TOP + 30))
                P.append('<text x="%.1f" y="%d" class="s11 b">DOWN</text>' % (cx + 31, EQ_TOP + 34))
        # 이름표
        name = [("가는 곳 · " if ghost else "") + TYPE_KO.get(ty, ""), s["machine"]]
        ny = SHELF + 50 if ty == "zfs" else FLOOR + 30
        P.append('<text x="%.1f" y="%d" text-anchor="middle"><tspan class="t2">%s </tspan><tspan style="font-weight:700">%s</tspan></text>'
                 % (cx, ny, _e(name[0]), _e(name[1])))
        P.append('</g>')

    # ── 캐리어가 지나간 길 (누가 옮겼는지 색으로)
    for si, s in enumerate(stations):
        ids = s["stays"]
        for a_, b_ in zip(ids, ids[1:]):
            pa, pb = pos[a_], pos[b_]
            if s["type"] == "stocker":
                top = ROOF + 16
                way = lambda p: [(p[0], top), (s["cx"], top)] if p[2] == "roof" else ([(s["cx"], p[1])] if p[2] in ("side", "rack") else [])
                pts = [pa[:2]] + way(pa) + list(reversed(way(pb))) + [pb[:2]]
            else:
                pts = [pa[:2], pb[:2]]
            P.append(_poly(pts, _c(s["type"])))
    for tr in trans:
        kind, pts = tr["kind"], tr["path"]
        if tr.get("pre"):
            P.append(_poly(tr["pre"], _c("stocker"), dash=True, opacity=0.6))
        if kind == "oht" and tr.get("ongoing") and tr.get("now_x") is not None:
            nx = tr["now_x"]
            P.append(_poly(pts[:2] + [(nx, CARRY)], _c("oht"), arrow=False))
            P.append(_poly([(nx, CARRY)] + pts[2:], _c("oht"), dash=True, opacity=0.6))
        elif kind == "oht":
            P.append(_poly(pts, _c("oht")))
            (px, py), (qx, qy) = pts[0], pts[-1]
            mx = (px + qx) / 2
            P.append(_arrow_at(mx + 6 * (1 if qx >= px else -1), CARRY, 0 if qx >= px else math.pi, _c("oht"), 10))
        elif kind == "plan":
            P.append(_poly(pts, _c("oht"), dash=True, opacity=0.6))
        elif kind == "gap":
            P.append(_poly(pts, "var(--mute)", dash=True))
        else:
            P.append(_poly(pts, "var(--ink2)"))

    last_i = len(stays) - 1
    now_tag = {"done": "✓ 도착 · ", "stopped": "! 중단 · "}.get(st["code"], "지금 · ")

    def tag(x, y, anchor, n, text, cur=False, bold=False):
        """번호 동그라미 + 이름. cur 이면 지금 자리 — 멈춰 있을 때 알약 테두리 · '도착/지금' 을 붙인다."""
        full = (now_tag + text) if cur else text
        w_ = 22 + _tw(full, 11, cur or bold) + (12 if cur else 0)
        x0_ = x - w_ / 2 if anchor == "middle" else (x - w_ if anchor == "end" else x)
        out = []
        if cur:
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="22" rx="11" class="pill still" style="stroke:var(--ink);stroke-width:1.4"/>'
                       % (x0_ - 3, y - 16, w_ + 6))
        bx = x0_ + 8 + (3 if cur else 0)
        if n:
            out.append('<g class="badge" data-step="%d"><circle cx="%.1f" cy="%.1f" r="8.5"/><text x="%.1f" y="%.1f" text-anchor="middle">%d</text></g>'
                       % (n, bx, y - 5, bx, y - 1, n))
        tx = bx + 13 if n else x0_
        cls = "s11" + (" b" if cur or bold else " t2")
        if cur:
            out.append('<text x="%.1f" y="%.1f" class="%s still">%s</text>' % (tx, y, cls, _e(full)))
            out.append('<text x="%.1f" y="%.1f" class="s11 t2 anim">%s</text>' % (tx, y, _e(text)))
        else:
            out.append('<text x="%.1f" y="%.1f" class="%s">%s</text>' % (tx, y, cls, _e(text)))
        return "".join(out)

    # ── 길 위 글자 (건넌 방법 · 걸린 시간)
    veh_step = {}
    for i, s in enumerate(stays):
        if s["role"] == "차량":
            veh_step[s["unit"]] = veh_step.get(s["unit"]) or i + 1
    for tr in trans:
        P0, Q0 = tr["path"][0], tr["path"][-1]
        if tr["kind"] == "gap":
            lk = tr["link"]
            if tr["Q"][2] == "side":
                xs = [q[0] for q in tr["path"] if abs(q[1] - (FLOOR - 16)) < 1]
                mx, ly = (min(xs) + max(xs)) / 2 if xs else (P0[0] + Q0[0]) / 2, FLOOR - 24
            else:
                mx, ly = (P0[0] + Q0[0]) / 2, CARRY + 22
            P.append('<text x="%.1f" y="%.1f" text-anchor="middle" class="t2 s11">%s <tspan class="b">%s</tspan></text>'
                     % (mx, ly, _e(lk["l1"]), _e(lk["l2"])))
        elif tr["kind"] in ("oht", "plan"):
            mx = (P0[0] + Q0[0]) / 2
            if tr["kind"] == "oht":
                n = veh_step.get(tr.get("veh"))
                if tr.get("ongoing"):
                    P.append(tag(tr.get("now_x", mx), CARRY + 44, "middle", n,
                                 "OHT %s · 달리는 중 · 실린 지 %s" % (tr.get("veh", ""), dur(tr.get("t_drive", 0))), cur=True))
                else:
                    drive = ("주행 " + dur(tr["t_drive"])) if tr.get("t_drive") else "주행"
                    P.append(tag(mx, CARRY + 32, "middle", n, "OHT %s · %s" % (tr.get("veh", ""), drive), bold=True))
            else:
                P.append('<text x="%.1f" y="%.1f" text-anchor="middle" class="t2 s11 b">갈 곳</text>' % (mx, CARRY + 22))
            if tr.get("t_pick") is not None and tr["kind"] == "oht" and tr["P"][2] != "rail":
                P.append('<text x="%.1f" y="%.1f" class="t2 s11">집기 %s</text>' % (P0[0] + 10, CARRY + 22, dur(tr["t_pick"])))
            if tr.get("t_drop") is not None:
                P.append('<text x="%.1f" y="%.1f" class="t2 s11">내려놓기 %s</text>' % (Q0[0] + 10, CARRY + 22, dur(tr["t_drop"])))

    # ── 자리 이름 (번호 · 포트 · 선반) — 지금 자리는 알약
    for i, p in pos.items():
        s = stays[i]
        name = (s["role"] + " " + s["short"]).strip()
        cur = i == last_i
        n = i + 1
        if p[2] == "roof":
            right = p[0] > [x for x in stations if i in x["stays"]][0]["cx"]
            P.append(tag(p[0] + (30 if right else -30), ROOF - 8, "start" if right else "end", n, name, cur))
        elif p[2] == "side":
            P.append(tag(p[0] + 16, p[1] - 24, "end", n, name, cur))
        elif p[2] == "slot":
            P.append(tag(p[0], SHELF + 26, "middle", n, name, cur))
        elif p[2] == "top":
            P.append(tag(p[0] + 30, EQ_TOP - 8, "start", n, name, cur))
        elif p[2] == "rack":
            P.append(tag(p[0], p[1] + 30, "middle", n, name, cur))
        elif p[2] == "crane":
            P.append(tag(p[0] + 20, p[1] + 25, "start", n, name, cur))
    for s in stations:
        if s["kind"] == "ghost":
            hd = s["hd"]
            p = s["entry"]
            P.append('<rect x="%.1f" y="%.1f" width="32" height="28" rx="5" style="fill:none;stroke:var(--ink2);stroke-width:1.4;stroke-dasharray:4 3"/>'
                     % (p[0] - 16, p[1] - 16))
            nm = " ".join(x for x in (hd["role"], hd["short"]) if x)
            if nm:
                yy = SHELF + 24 if s["type"] == "zfs" else (ROOF - 8 if p[2] == "roof" else EQ_TOP - 8)
                P.append('<text x="%.1f" y="%d" text-anchor="middle" class="t2 s11">%s</text>' % (p[0], yy, _e(nm)))

    # ── OHT · 집게 · 캐리어 (움직이는 것들 — 그림에는 마지막 모습)
    o = sc["oht"]
    ox = o["x"] if o else -200
    speed = ""
    if o and o.get("moving"):
        dx = -o.get("dir", 1)
        speed = "".join('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:var(--c-oht);stroke-width:2;stroke-linecap:round;opacity:.55"/>'
                        % (dx * 32, dx * (46 + 6 * k), RAIL + 9 + 7 * k, RAIL + 9 + 7 * k) for k in range(3))
    P.append('<g id="%s-hoist" transform="translate(%.1f 0)" style="display:none">'
             '<line x1="-8" x2="-8" y1="%d" y2="%d" style="stroke:var(--ink2);stroke-width:1.3"/>'
             '<line x1="8" x2="8" y1="%d" y2="%d" style="stroke:var(--ink2);stroke-width:1.3"/>'
             '<rect x="-13" y="%d" width="26" height="4" rx="1" style="fill:var(--ink2)"/></g>'
             % (u, ox, RAIL + 27, RET, RAIL + 27, RET, RET - 3))
    P.append('<g id="%s-oht" transform="translate(%.1f 0)"%s><g class="still">%s</g>'
             '<circle cx="-13" cy="%d" r="4" style="fill:var(--ink2)"/><circle cx="13" cy="%d" r="4" style="fill:var(--ink2)"/>'
             '<rect x="-25" y="%d" width="50" height="24" rx="6" style="fill:var(--c-oht);stroke:var(--surf);stroke-width:1.5"/>'
             '<rect x="-17" y="%d" width="34" height="6" rx="2" style="fill:var(--surf);opacity:.6"/>'
             '<text id="%s-ohtlab" x="0" y="%d" text-anchor="middle" class="s11 b">%s</text></g>'
             % (u, ox, "" if o else ' style="display:none"', speed, RAIL - 1, RAIL - 1, RAIL + 4, RAIL + 9,
                u, RAIL - 12, _e("OHT " + o["veh"]) if o else "OHT"))
    fx, fy = sc["foup"]
    P.append('<g id="%s-foup" transform="translate(%.1f %.1f)"><rect x="-14" y="-11" width="28" height="22" rx="4" '
             'style="fill:var(--foup);stroke:var(--surf);stroke-width:1.5"/><rect x="-8" y="-15" width="16" height="5" rx="1.5" '
             'style="fill:var(--foup)"/><line x1="-8" x2="8" y1="2" y2="2" style="stroke:var(--surf);stroke-width:1;opacity:.6"/></g>'
             % (u, fx, fy))
    # ── 단계 목록
    y = FLOOR + 72
    P.append('<text x="%d" y="%d" class="h2">지나온 길</text>' % (M, y))
    P.append('<text x="%.1f" y="%d" class="mu s11">%s</text>' % (M + _tw("지나온 길", 13, True) + 10, y, _e("번호는 그림 속 자리 · 로그 %d줄" % t["rows"])))
    lx = W - M
    types = [ty for ty in ("stocker", "oht", "zfs", "eqp", "etc") if any(s["type"] == ty for s in stays)]
    items = [(ty, TYPE_KO[ty]) for ty in types] + ([("gap", "위치 기록 없음")] if any(tr["kind"] == "gap" for tr in trans) else [])
    for ty, name in reversed(items):
        lx -= _tw(name, 11)
        P.append('<text x="%.1f" y="%d" class="t2 s11">%s</text>' % (lx, y, name))
        lx -= 18
        if ty == "gap":
            P.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" style="stroke:var(--mute);stroke-width:2.5;stroke-dasharray:4 3"/>' % (lx, lx + 13, y - 4, y - 4))
        else:
            P.append('<rect x="%.1f" y="%d" width="12" height="4" rx="2" style="fill:%s"/>' % (lx, y - 6, _c(ty)))
        lx -= 12
    cols = 2 if len(stays) > 3 else 1
    per = (len(stays) + cols - 1) // cols
    colw = (W - 2 * M) / cols
    for i, s in enumerate(stays):
        cx0 = M + colw * (i // per)
        ry = y + 26 + 24 * (i % per)
        if s["role"] == "차량":
            what = "OHT %s (%s)" % (s["unit"], s["machine"])
        else:
            what = "%s %s %s%s" % (TYPE_KO[s["type"]], s["machine"], s["role"], (" " + s["short"]) if s["short"] else "")
        P.append('<g class="badge" data-step="%d"><circle cx="%.1f" cy="%.1f" r="9"/><text x="%.1f" y="%.1f" text-anchor="middle">%d</text></g>'
                 % (i + 1, cx0 + 9, ry - 4, cx0 + 9, ry, i + 1))
        P.append('<text x="%.1f" y="%.1f" class="mu s11 num">%s</text>' % (cx0 + 26, ry, hms(s["first"])))
        P.append('<text x="%.1f" y="%.1f">%s <tspan class="t2">— %s</tspan></text>'
                 % (cx0 + 86, ry, _e(_clip(what, 12, colw - 200)), _e(_stay_time(s, t))))
    H = int(y + 26 + 24 * max(per, 1) + 4)
    title = "캐리어 %s 이동 — %s · %s" % (t["carrier"], " → ".join(
        "%s %s" % (TYPE_KO[L["type"]], L["machine"]) for L in t["legs"]), st["ko"])
    return ('<svg xmlns="http://www.w3.org/2000/svg" id="%s" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
            '<title>%s</title><style>%s</style><rect class="bg" x="0" y="0" width="%d" height="%d"/>%s</svg>'
            % (u, W, H, W, H, _e(title), _e(title), _style(u), W, H, "".join(P)))


def anim_data(t, sc):
    """HTML 에서 움직일 때 쓰는 값 (초는 로그 첫 줄부터)."""
    t0 = t["t0"]
    return {"id": sc["id"], "fk": [[round(a, 3), round(x, 1), round(y, 1)] for a, x, y in sc["fk"]],
            "ok": [[round(a, 3), None if x is None else round(x, 1), round(g, 1), v] for a, x, g, v in sc["ok"]],
            "steps": sc["steps"], "end": sc["end"], "marks": sc["marks"], "sod": t0.hour * 3600 + t0.minute * 60 + t0.second + t0.microsecond / 1e6}


# ═════════════════════════════════════════════════════════════════════
# 6. 한 장짜리 HTML (그림 · 요약 · 로그 표)
# ═════════════════════════════════════════════════════════════════════

_PAGE_CSS = """
:root{--bg:#f9f9f7;--surf:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--mute:#898781;--line:#e1e0d9;--btn:#fff}
:root[data-theme=dark]{--bg:#0d0d0d;--surf:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--mute:#898781;--line:#2c2c2a;--btn:#232322}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0d0d0d;--surf:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--mute:#898781;--line:#2c2c2a;--btn:#232322}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 system-ui,-apple-system,'Segoe UI','Malgun Gothic',sans-serif}
main{max-width:1000px;margin:0 auto;padding:16px}
.bar{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin:0 0 10px}
button{font:inherit;font-size:13px;color:var(--ink);background:var(--btn);border:1px solid var(--line);border-radius:8px;padding:5px 12px;cursor:pointer}
figure{margin:0;background:var(--surf);border:1px solid var(--line);border-radius:12px;overflow-x:auto;overflow-y:hidden}
figure svg{display:block;width:100%;height:auto;min-width:640px}
#play{font-weight:600}
figcaption{padding:8px 14px;border-top:1px solid var(--line);color:var(--ink2);font-size:13px}
details{margin:16px 0;background:var(--surf);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;word-break:break-all;font:12.5px/1.6 ui-monospace,Consolas,'D2Coding',monospace;margin:10px 0 0;color:var(--ink)}
h2{font-size:15px;margin:22px 0 6px}
.opt{color:var(--ink2);font-size:13px}
.wrap{overflow-x:auto;background:var(--surf);border:1px solid var(--line);border-radius:12px;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{border-bottom:1px solid var(--line);padding:5px 10px;text-align:left;vertical-align:top;white-space:nowrap}
td.ko{white-space:normal;min-width:240px}
th{color:var(--ink2);font-weight:600;position:sticky;top:0;background:var(--surf)}
tr.dim td{color:var(--mute)}
body.hide tr.dim{display:none}
.sw{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:0}
"""

_PAGE_JS = """
(function(){
var R=document.documentElement,svg=document.querySelector('figure svg'),name=svg.getAttribute('data-name')||'carrier';
function cur(){return R.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}
function lab(){document.getElementById('theme').textContent=cur()==='dark'?'밝게 보기':'어둡게 보기'}
document.getElementById('theme').onclick=function(){R.dataset.theme=cur()==='dark'?'light':'dark';lab()};lab();
function text(){var s=svg.cloneNode(true);s.setAttribute('data-theme',cur());return new XMLSerializer().serializeToString(s)}
function save(blob,fn){var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=fn;document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},500)}
document.getElementById('svg').onclick=function(){save(new Blob([text()],{type:'image/svg+xml'}),name+'.svg')};
document.getElementById('png').onclick=function(){var img=new Image(),w=+svg.getAttribute('width'),h=+svg.getAttribute('height');
img.onload=function(){var c=document.createElement('canvas');c.width=w*2;c.height=h*2;var g=c.getContext('2d');g.scale(2,2);g.drawImage(img,0,0,w,h);c.toBlob(function(b){save(b,name+'.png')})};
img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(text())};
var cb=document.getElementById('hideui');cb.onchange=function(){document.body.classList.toggle('hide',cb.checked)};
/* ▶ 움직여 보기 — 로그 시각대로 캐리어 · OHT 를 옮긴다 (오래 기다린 구간은 짧게, 움직인 구간은 길게) */
var A=JSON.parse(document.getElementById('anim').textContent),u=A.id;
var F=document.getElementById(u+'-foup'),O=document.getElementById(u+'-oht'),Ho=document.getElementById(u+'-hoist'),
C=document.getElementById(u+'-clock'),OL=document.getElementById(u+'-ohtlab'),HL=Ho.querySelectorAll('line'),HG=Ho.querySelector('rect');
var keep={f:F.getAttribute('transform'),o:O.getAttribute('transform'),od:O.style.display,c:C.textContent,ol:OL.textContent};
function at(K,s){if(!K.length)return null;if(s<=K[0][0])return K[0];for(var i=0;i<K.length-1;i++){var a=K[i],b=K[i+1];
if(s<b[0]){if(a[1]===null||b[1]===null)return a;var p=(s-a[0])/Math.max(1e-6,b[0]-a[0]);return[s,a[1]+(b[1]-a[1])*p,a[2]+(b[2]-a[2])*p,a[3]]}}return K[K.length-1]}
var ts=[0,A.end].concat(A.marks);
ts=ts.filter(function(x){return x>=0&&x<=A.end}).sort(function(a,b){return a-b});
var map=[[0,0]],acc=0;
for(var i=0;i<ts.length-1;i++){var a=ts[i],b=ts[i+1],d=b-a;if(d<=0)continue;
var fa=at(A.fk,a+1e-4),fb=at(A.fk,b-1e-4),oa=A.ok.length&&a>=A.ok[0][0]?at(A.ok,a+1e-4):null,ob=A.ok.length&&b>=A.ok[0][0]?at(A.ok,b-1e-4):null;
var mv=(fa&&fb&&Math.abs(fa[1]-fb[1])+Math.abs(fa[2]-fb[2])>0.5)||(oa&&ob&&oa[1]!==null&&ob[1]!==null&&Math.abs(oa[1]-ob[1])+Math.abs(oa[2]-ob[2])>0.5);
var L=Math.log(1+d)/Math.LN10;acc+=mv?Math.min(2.6,Math.max(0.6,0.6+1.0*L)):Math.min(0.9,Math.max(0.12,0.15+0.35*L));map.push([b,acc])}
function real(tau){for(var i=0;i<map.length-1;i++){var a=map[i],b=map[i+1];if(tau<b[1])return a[0]+(b[0]-a[0])*(tau-a[1])/Math.max(1e-6,b[1]-a[1])}return A.end}
function clock(s){var x=Math.floor(A.sod+s)%86400;function z(n){return(n<10?'0':'')+n}return z(Math.floor(x/3600))+':'+z(Math.floor(x/60)%60)+':'+z(x%60)}
function draw(s){var f=at(A.fk,s);if(f)F.setAttribute('transform','translate('+f[1].toFixed(1)+' '+f[2].toFixed(1)+')');
var o=A.ok.length&&s>=A.ok[0][0]?at(A.ok,s):null;
if(o&&o[1]!==null){O.style.display='';Ho.style.display='';O.setAttribute('transform','translate('+o[1].toFixed(1)+' 0)');
Ho.setAttribute('transform','translate('+o[1].toFixed(1)+' 0)');for(var j=0;j<HL.length;j++)HL[j].setAttribute('y2',o[2].toFixed(1));
HG.setAttribute('y',(o[2]-3).toFixed(1));if(o[3])OL.textContent='OHT '+o[3]}else{O.style.display='none';Ho.style.display='none'}
C.textContent='▶ '+clock(s);
for(var k=0;k<A.steps.length;k++){var on=s>=A.steps[k][0]&&s<=A.steps[k][1]+0.05,bs=svg.querySelectorAll('[data-step="'+(k+1)+'"]');for(var m=0;m<bs.length;m++)bs[m].classList.toggle('on',on)}}
var raf=0,btn=document.getElementById('play');
function rest(){cancelAnimationFrame(raf);svg.classList.remove('playing');F.setAttribute('transform',keep.f);O.setAttribute('transform',keep.o);
O.style.display=keep.od;Ho.style.display='none';C.textContent=keep.c;OL.textContent=keep.ol;
var bs=svg.querySelectorAll('.badge.on');for(var m=0;m<bs.length;m++)bs[m].classList.remove('on');btn.textContent='▶ 움직여 보기'}
function play(){cancelAnimationFrame(raf);svg.classList.add('playing');btn.textContent='■ 멈춤';var st=performance.now();
(function tick(now){var tau=(now-st)/1000;if(tau>=acc){draw(A.end);raf=0;setTimeout(function(){if(!raf)rest()},1600);return}
draw(real(tau));raf=requestAnimationFrame(tick)})(st)}
btn.onclick=function(){svg.classList.contains('playing')?rest():play()};
window.mcsPlay={play:play,rest:rest,draw:draw,real:real,total:function(){return acc}};
if(location.hash!=='#still')setTimeout(play,700);
})();
"""


def render_html(t, svg=None, sc=None, width=960):
    sc = sc or _scene(t, width)
    svg = svg or render_svg(t, width, sc)
    anim = json.dumps(anim_data(t, sc), ensure_ascii=False).replace("</", "<\\/")
    name = "캐리어_%s_경로" % re.sub(r"[^\w.-]", "_", t["carrier"])
    svg = svg.replace("<svg ", '<svg data-name="%s" ' % _e(name), 1)
    legs = " → ".join("%s %s" % (TYPE_KO[L["type"]], L["machine"]) for L in t["legs"])
    cap = "%s: %s · %s · %s" % (t["carrier"], legs, dur(_sec(t["t0"], t["t1"])), t["status"]["ko"])
    mtype = {s["machine"]: s["type"] for s in t["stays"]}
    trs = []
    for e in t["events"]:
        ty = mtype.get(e["machine"], "")
        sw = '<span class="sw" style="background:%s"></span>' % _LIGHT[ty] if ty else ""
        dim = e["name"].startswith("UI-") or e["dup"]
        trs.append('<tr%s><td>%s</td><td>%s</td><td>%s%s</td><td>%s</td><td class="ko">%s</td></tr>'
                   % (' class="dim"' if dim else "", _e(e["t"].strftime("%H:%M:%S.%f")[:12]), _e(e["who"]), sw,
                      _e(e["machine"] or "-"), _e(e["name"]), _e(e["ko"])))
    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>캐리어 %s 이동 경로</title><style>%s</style></head><body class=\"hide\"><main>"
            "<div class=\"bar\"><button id=\"play\">▶ 움직여 보기</button><button id=\"theme\"></button><button id=\"svg\">SVG 저장</button><button id=\"png\">PNG 저장</button></div>"
            "<figure>%s<figcaption>%s</figcaption></figure>"
            "<details open><summary>LLM 에 줄 요약 (그림과 같은 사실)</summary><pre>%s</pre></details>"
            "<h2>이 캐리어 로그 %d줄</h2><label class=\"opt\"><input type=\"checkbox\" id=\"hideui\" checked> 화면 갱신(UI) · 같은 줄 반복은 숨기기</label>"
            "<div class=\"wrap\"><table><thead><tr><th>시각</th><th>방향</th><th>장비</th><th>메시지</th><th>뜻</th></tr></thead><tbody>%s</tbody></table></div>"
            "</main><script type=\"application/json\" id=\"anim\">%s</script><script>%s</script></body></html>"
            % (_e(t["carrier"]), _PAGE_CSS, svg, _e(cap), _e(facts_text(t)), len(t["events"]), "".join(trs), anim, _PAGE_JS))


# ═════════════════════════════════════════════════════════════════════
# 7. 명령줄
# ═════════════════════════════════════════════════════════════════════

def _main(argv=None):
    import argparse
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="MCS 로그 → 캐리어 이동 경로 그림")
    ap.add_argument("log", help="MCS 로그 (노트북 · HTML 표 · CSV · JSON · 원본 로그)")
    ap.add_argument("--carrier", help="캐리어 ID (안 주면 줄이 제일 많은 것)")
    ap.add_argument("-o", "--out", help="HTML 파일 (SVG · TXT 는 같은 이름으로)")
    ap.add_argument("--list", action="store_true", help="로그에 있는 캐리어만 보기")
    ap.add_argument("--now", help="조회 시각 '2026-09-30 09:50:30' 또는 now (안 주면 로그 마지막 줄)")
    a = ap.parse_args(argv)
    rows = read_rows(a.log)
    if not rows:
        print("표나 로그 줄을 못 읽었습니다: %s" % a.log)
        return 2
    if a.list:
        for c, n in carriers(rows):
            print("%-16s %5d줄" % (c, n))
        return 0
    try:
        now = datetime.now() if (a.now or "").lower() == "now" else _time(a.now or "")
        t = trace(rows, a.carrier, now=now)
    except ValueError as ex:
        print(ex)
        return 2
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.log)),
                                "캐리어_%s_경로.html" % re.sub(r"[^\w.-]", "_", t["carrier"]))
    base = os.path.splitext(out)[0]
    sc = _scene(t)
    svg = render_svg(t, sc=sc)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_html(t, svg, sc))
    with open(base + ".svg", "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg)
    facts = facts_text(t)
    with open(base + ".txt", "w", encoding="utf-8-sig") as fh:
        fh.write(facts + "\n")
    print(facts)
    print("\n그림: %s\n      %s.svg\n요약: %s.txt" % (out, base, base))
    if len(t["carriers"]) > 1:
        print("(이 로그의 다른 캐리어: %s — --carrier 로 고르세요)" % ", ".join(c for c, _ in t["carriers"][1:6]))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
