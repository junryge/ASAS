#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_sender.py - OHT 데이터 전송

사용법:
    python data_sender.py             → 메뉴 선택
    python data_sender.py play        → 1번: TXT 재생 (5분 이동)
    python data_sender.py paste       → 2번: 붙여넣기
    python data_sender.py udp [포트]  → 3번: UDP 실시간 수신 (기본 9000)
    python data_sender.py pipe        → 파이프 입력 (cat data.txt | python data_sender.py pipe)
"""

import json
import os
import socket
import sys
import time
import urllib.request
import urllib.error

SERVER_URL = "http://localhost:10003"
INTERVAL   = 0.5
DEFAULT_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oht_5v_data.txt")
UDP_PORT = 9000
UDP_BUFFER_SIZE = 4096


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


def extract_oht_messages(text):
    """텍스트에서 OHT 메시지 추출 (어떤 포맷이든 2,OHT, 패턴 찾기)"""
    messages = []
    for line in text.split("\n"):
        cleaned = clean_line(line)
        if "2,OHT," in cleaned:
            idx = cleaned.index("2,OHT,")
            messages.append(cleaned[idx:])
    return messages


# ============================================================
# 1번: TXT 파일 재생 모드
# ============================================================
def play_mode(filepath=None):
    """TXT에서 이동 데이터를 읽어 0.5초 간격으로 전송"""
    if filepath is None:
        filepath = DEFAULT_DATA_FILE

    if not os.path.exists(filepath):
        print(f"오류: 파일 없음 → {filepath}")
        print(f"  python generate_5min_data.py  ← 먼저 실행")
        return

    print(f"데이터 파일: {filepath}")
    batches = []
    current_batch = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
            elif "2,OHT," in stripped:
                current_batch.append(stripped)
        if current_batch:
            batches.append(current_batch)

    if not batches:
        print("오류: OHT 메시지가 없습니다")
        return

    total_ticks = len(batches)
    vehicles_per_tick = len(batches[0])
    duration = total_ticks * INTERVAL
    print(f"  {vehicles_per_tick}대 × {total_ticks}틱 = {duration:.0f}초 ({duration/60:.1f}분)")
    print("Ctrl+C 종료")
    print("-" * 50)

    start_time = time.time()
    for tick, batch in enumerate(batches):
        result = send(batch)
        elapsed = time.time() - start_time
        remaining = duration - elapsed

        if tick % 10 == 0 or tick < 3:
            f = batch[0].split(",")
            status = result.get("status", "?")
            print(f"[{tick+1:3d}/{total_ticks}] {status} 남은시간 {int(remaining)}초  "
                  f"{f[2]}: {f[7]}→{f[9]} dist={f[8]}")

        time.sleep(INTERVAL)

    print(f"\n재생 완료! {total_ticks}틱, {int(time.time()-start_time)}초")


# ============================================================
# 2번: 붙여넣기 모드
# ============================================================
def paste_mode():
    print("붙여넣기 모드: OHT 메시지 붙여넣고 빈 줄에서 엔터 → 전송!")
    print("q = 종료")
    print("-" * 50)
    print()
    print("메시지 포맷:")
    print("  2,OHT,차량ID,상태,적재,에러,온라인,현재노드,거리,다음노드,...")
    print()

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
# 3번: UDP 실시간 수신 모드
# ============================================================
def udp_mode(port=UDP_PORT):
    """
    UDP로 들어오는 실시간 OHT 데이터를 받아서 sim_server에 전송

    MCS에서 UDP로 VHL_STATE_REPORT 메시지를 보내면 자동으로 파싱해서 전달.
    한 패킷에 메시지 1건 또는 여러건(줄바꿈 구분) 모두 지원.

    테스트:
      echo "2,OHT,V00795,1,1,0000,1,12340,14,12341,4,4,4PDMV608,4ANZ19-701,00000000,0000,4ABL3301A_OUT04,4ANZ19-701,90,0,0" | nc -u localhost 9000
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    print(f"UDP 수신 대기: 0.0.0.0:{port}")
    print(f"  → MCS에서 이 포트로 OHT 메시지 전송하면 자동 파싱")
    print()
    print("테스트 방법 (다른 터미널에서):")
    print(f'  echo "2,OHT,V00795,1,1,0000,1,12340,14,12341,4,4,ID,DST,00000000,0000,SRC,DST,90,0,0" | nc -u localhost {port}')
    print()
    print("Ctrl+C 종료")
    print("-" * 50)

    count = 0
    total_msgs = 0
    while True:
        data, addr = sock.recvfrom(UDP_BUFFER_SIZE)
        text = data.decode("utf-8", errors="ignore")
        messages = extract_oht_messages(text)

        if not messages:
            continue

        result = send(messages)
        count += 1
        total_msgs += len(messages)

        status = result.get("status", "?")
        if count <= 5 or count % 10 == 0:
            print(f"[{count}] {addr[0]}:{addr[1]} → {len(messages)}건 {status} (누적 {total_msgs}건)")
            for m in messages[:3]:
                f = m.split(",")
                print(f"    {f[2]}: node={f[7]} dist={f[8]} → {f[9]}")
            if len(messages) > 3:
                print(f"    ... 외 {len(messages)-3}건")


# ============================================================
# 파이프 모드: stdin에서 연속 읽기
# ============================================================
def pipe_mode():
    """
    파이프로 데이터를 받아서 전송
    사용: cat oht_data.txt | python data_sender.py pipe
    """
    print("파이프 모드: stdin에서 읽는 중...")
    print("-" * 50)

    buffer = []
    count = 0

    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            # 빈 줄 = 배치 전송
            if buffer:
                result = send(buffer)
                count += 1
                if count <= 3 or count % 10 == 0:
                    print(f"[{count}] {len(buffer)}건 전송 {result.get('status', '?')}")
                buffer = []
                time.sleep(INTERVAL)
        elif "2,OHT," in stripped:
            cleaned = clean_line(stripped)
            if "2,OHT," in cleaned:
                idx = cleaned.index("2,OHT,")
                buffer.append(cleaned[idx:])

    # 마지막 배치
    if buffer:
        send(buffer)
        count += 1

    print(f"\n완료! {count}배치 전송")


# ============================================================
def main():
    print("=" * 50)
    print(f"OHT data_sender → {SERVER_URL}")
    print("=" * 50)

    # 커맨드라인 모드
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "play":
            play_mode(sys.argv[2] if len(sys.argv) > 2 else None)
        elif mode == "paste":
            paste_mode()
        elif mode == "udp":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else UDP_PORT
            udp_mode(port)
        elif mode == "pipe":
            pipe_mode()
        else:
            print(f"알 수 없는 모드: {mode}")
            print("  play / paste / udp / pipe")
        return

    # 메뉴 선택
    print()
    print("  1. TXT 재생    (oht_5v_data.txt → 5분 이동)")
    print("  2. 붙여넣기    (OHT 메시지 직접 입력)")
    print("  3. UDP 수신    (MCS에서 실시간 데이터 수신)")
    print()
    try:
        sel = input("선택 (1/2/3): ").strip()
    except EOFError:
        return

    print()
    if sel == "2":
        paste_mode()
    elif sel == "3":
        try:
            port_input = input(f"UDP 포트 (기본 {UDP_PORT}): ").strip()
            port = int(port_input) if port_input else UDP_PORT
        except (EOFError, ValueError):
            port = UDP_PORT
        udp_mode(port)
    else:
        play_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료.")
