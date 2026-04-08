#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_sender.py - OHT 데이터 전송

sim_server에서 레이아웃을 받아 실제 존재하는 노드로 차량을 이동시킵니다.

사용법:
    python data_sender.py              → 메뉴 선택
    python data_sender.py paste        → 붙여넣기 모드
    python data_sender.py file [파일]  → 파일 모드 (기본: oht_5v_data.txt, 5분 이동)
"""

import json
import math
import os
import sys
import time
import random
import urllib.request
import urllib.error

SERVER_URL = "http://localhost:10003"
INTERVAL   = 0.5

# 5대 차량 시작 위치 (SAMPLE_MESSAGES 기준)
INIT_VEHICLES = [
    {"id": "V00795", "cur": 12340, "next": 12341, "dist": 14, "state": 1, "isFull": 1,
     "equipId": "4PDMV608", "equipNo": "36073", "src": "4ABL3301A_OUT04", "dst": "4ANZ19-701", "vel": 90},
    {"id": "V00564", "cur": 2115,  "next": 2116,  "dist": 9,  "state": 1, "isFull": 1,
     "equipId": "4PDD0270", "equipNo": "7449",  "src": "4ANZ25-205",      "dst": "4KCW3301_3", "vel": 50},
    {"id": "V00975", "cur": 6033,  "next": 3294,  "dist": 0,  "state": 1, "isFull": 1,
     "equipId": "6PDB1402", "equipNo": "34128", "src": "4EPR5301_3",      "dst": "4ANZ03-302", "vel": 50},
    {"id": "V00313", "cur": 1071,  "next": 1072,  "dist": 0,  "state": 1, "isFull": 1,
     "equipId": "6PDN4064", "equipNo": "21980", "src": "4CSC1603_3",      "dst": "4AFZ47-328", "vel": 50},
    {"id": "V00649", "cur": 1448,  "next": 1449,  "dist": 0,  "state": 1, "isFull": 1,
     "equipId": "4NDNA076", "equipNo": "17160", "src": "4ALFE001_AO31",   "dst": "4AFZ15-160", "vel": 50},
]


def fetch_layout():
    """sim_server 에서 레이아웃(노드, 엣지) 가져와서 인접맵 + 엣지거리 구축"""
    print(f"sim_server 레이아웃 로딩: {SERVER_URL}/api/layout")
    with urllib.request.urlopen(f"{SERVER_URL}/api/layout", timeout=10) as resp:
        data = json.loads(resp.read())

    nodes = set()
    for n in data.get("nodes", []):
        nodes.add(n["no"])

    adj = {}        # {from: [to, ...]}
    edge_dist = {}  # {(from, to): 거리(100mm 단위)}
    node_xy = {}    # {no: (x, y)}

    for n in data.get("nodes", []):
        node_xy[n["no"]] = (n["x"], n["y"])

    for e in data.get("edges", []):
        f, t = e["from"], e["to"]
        adj.setdefault(f, []).append(t)
        if f in node_xy and t in node_xy:
            dx = node_xy[t][0] - node_xy[f][0]
            dy = node_xy[t][1] - node_xy[f][1]
            dist_coord = math.sqrt(dx*dx + dy*dy)
            # 100mm 단위로 변환 (coord * 1000mm / 100)
            edge_dist[(f, t)] = int(dist_coord * 10)

    print(f"  노드: {len(nodes)}개  엣지: {len(edge_dist)}개")

    # 시작 노드 존재 여부 확인
    for v in INIT_VEHICLES:
        cur_ok = v["cur"] in nodes
        nxt_ok = v["next"] in nodes
        print(f"  {v['id']}: node {v['cur']}({'OK' if cur_ok else 'X'}) → {v['next']}({'OK' if nxt_ok else 'X'})")

    return nodes, adj, edge_dist


def make_message(v):
    """OHT 메시지 생성"""
    return (
        f"2,OHT,{v['id']},{v['state']},{v['isFull']},0000,1,"
        f"{v['cur']},{v['dist']},{v['next']},"
        f"4,4,{v['equipId']},{v['dst']},00000000,0000,"
        f"{v['src']},{v['dst']},{v['vel']},0,0"
    )


def send(messages):
    payload = json.dumps({"messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_URL}/api/oht-raw",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"status": "fail", "error": str(e)}


def clean_line(line):
    line = line.strip()
    if line.startswith('"'):
        line = line.lstrip('"')
    if line.endswith('",') or line.endswith('"'):
        line = line.rstrip(',').rstrip('"')
    return line.strip()


# ============================================================
# 자동 모드: 레이아웃 기반 이동
# ============================================================
def auto_mode():
    # sim_server 연결 대기
    while True:
        try:
            nodes, adj, edge_dist = fetch_layout()
            break
        except Exception as e:
            print(f"sim_server 연결 실패: {e}")
            print("2초 후 재시도...")
            time.sleep(2)

    # 차량 상태 복사
    vehicles = []
    for v in INIT_VEHICLES:
        vv = dict(v)
        # 현재 엣지의 최대 거리 (100mm 단위)
        vv["edge_max"] = edge_dist.get((vv["cur"], vv["next"]), 100)
        vehicles.append(vv)

    print()
    print(f"자동 이동 시작 ({INTERVAL}초 간격)")
    print("Ctrl+C 종료")
    print("-" * 50)

    tick = 0
    while True:
        messages = []

        for v in vehicles:
            # 이동거리 증가 (100mm 단위, 매 틱 +5)
            v["dist"] += 5

            # 다음 노드 도달
            if v["dist"] >= v["edge_max"]:
                v["dist"] = 0
                v["cur"] = v["next"]
                # 다음 노드 선택 (레이아웃 기반)
                neighbors = adj.get(v["cur"], [])
                if neighbors:
                    v["next"] = random.choice(neighbors)
                    v["edge_max"] = edge_dist.get((v["cur"], v["next"]), 100)
                # 다음 노드가 없으면 제자리

            messages.append(make_message(v))

        result = send(messages)
        tick += 1

        status = result.get("status", "?")
        updated = result.get("updated", [])

        if tick % 10 == 0 or tick <= 3:
            v0 = vehicles[0]
            print(f"[tick {tick:3d}] {status} {len(updated)}대  "
                  f"{v0['id']}: {v0['cur']}→{v0['next']} dist={v0['dist']}/{v0['edge_max']}")

        time.sleep(INTERVAL)


# ============================================================
# 붙여넣기 모드
# ============================================================
def paste_mode():
    print("붙여넣기 모드: OHT 메시지 붙여넣고 빈 줄에서 엔터 → 전송!")
    print("q = 종료")
    print("-" * 50)

    count = 0
    while True:
        print(f"\n[{count+1}] 메시지 붙여넣기:")

        messages = []
        while True:
            try:
                line = input()
            except EOFError:
                return

            if line.strip().lower() == "q":
                return

            cleaned = clean_line(line)
            if not cleaned:
                break

            if "2,OHT," in cleaned:
                idx = cleaned.index("2,OHT,")
                messages.append(cleaned[idx:])

        if not messages:
            continue

        result = send(messages)
        count += 1

        status = result.get("status", "?")
        updated = result.get("updated", [])
        print(f"  {status} updated={updated} ({len(messages)}대)")
        for m in messages:
            f = m.split(",")
            print(f"    {f[2]}: node={f[7]} dist={f[8]} → {f[9]}")


# ============================================================
# 파일 모드: TXT 파일에서 읽어 레이아웃 기반 5분 이동
# ============================================================
DEFAULT_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oht_5v_data.txt")
FILE_MODE_DURATION = 300  # 5분 = 300초

def parse_raw_line(line):
    """raw OHT 메시지에서 차량 정보 추출"""
    fields = line.strip().split(",")
    if len(fields) < 19 or fields[1] != "OHT":
        return None
    return {
        "id": fields[2],
        "state": int(fields[3]),
        "isFull": int(fields[4]),
        "cur": int(fields[7]),
        "dist": int(fields[8]),
        "next": int(fields[9]),
        "equipId": fields[12],
        "src": fields[16],
        "dst": fields[17],
        "vel": int(fields[18]),
    }


def file_mode(filepath=None):
    """TXT 파일에서 5대 데이터 읽어 레이아웃 기반 5분 이동"""
    if filepath is None:
        filepath = DEFAULT_DATA_FILE

    # 파일 읽기
    print(f"데이터 파일: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and "2,OHT," in l]

    if not lines:
        print("오류: OHT 메시지가 없습니다")
        return

    vehicles = []
    for line in lines:
        v = parse_raw_line(line)
        if v:
            vehicles.append(v)
    print(f"  차량 {len(vehicles)}대 로드")

    # sim_server 레이아웃 가져오기
    while True:
        try:
            nodes, adj, edge_dist = fetch_layout()
            break
        except Exception as e:
            print(f"sim_server 연결 실패: {e}")
            print("2초 후 재시도...")
            time.sleep(2)

    # 엣지 최대 거리 설정
    for v in vehicles:
        v["edge_max"] = edge_dist.get((v["cur"], v["next"]), 100)

    total_ticks = int(FILE_MODE_DURATION / INTERVAL)
    print()
    print(f"파일 모드: {len(vehicles)}대 × {FILE_MODE_DURATION}초 ({total_ticks} ticks)")
    print("Ctrl+C 종료")
    print("-" * 50)

    start_time = time.time()
    tick = 0
    while tick < total_ticks:
        messages = []

        for v in vehicles:
            v["dist"] += 5

            if v["dist"] >= v["edge_max"]:
                v["dist"] = 0
                v["cur"] = v["next"]
                neighbors = adj.get(v["cur"], [])
                if neighbors:
                    v["next"] = random.choice(neighbors)
                    v["edge_max"] = edge_dist.get((v["cur"], v["next"]), 100)

            messages.append(make_message(v))

        result = send(messages)
        tick += 1

        elapsed = time.time() - start_time
        remaining = FILE_MODE_DURATION - elapsed

        if tick % 10 == 0 or tick <= 3:
            v0 = vehicles[0]
            print(f"[tick {tick:3d}/{total_ticks}] 남은시간 {int(remaining)}초  "
                  f"{v0['id']}: {v0['cur']}→{v0['next']} dist={v0['dist']}/{v0['edge_max']}")

        if remaining <= 0:
            break

        time.sleep(INTERVAL)

    print(f"\n완료! {tick} ticks, {int(time.time()-start_time)}초 경과")


# ============================================================
def main():
    print("=" * 50)
    print(f"OHT data_sender → {SERVER_URL}")
    print("=" * 50)

    if len(sys.argv) > 1 and sys.argv[1] == "paste":
        paste_mode()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "file":
        fp = sys.argv[2] if len(sys.argv) > 2 else None
        file_mode(fp)
        return

    print()
    print("  1. 자동 (레이아웃 기반 이동, 무한)")
    print("  2. 붙여넣기 (직접 입력)")
    print("  3. 파일 (TXT에서 읽어 5분 이동)")
    print()
    try:
        sel = input("선택 (1/2/3): ").strip()
    except EOFError:
        return

    print()
    if sel == "2":
        paste_mode()
    elif sel == "3":
        file_mode()
    else:
        auto_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료.")
