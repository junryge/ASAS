#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OHT_VHL_속도_예시.py — OHT VHL 속도 계산 흐름 튜토리얼

이 스크립트는 "데이터 → 처리 → 결과" 흐름을 단계별로 보여준다.
각 STEP 마다 (1) 어떤 데이터를, (2) 어떻게 사용하고, (3) 무엇이 나오는지 설명한다.

문서: WORD_MODEL/OHS_DATA_MD/OHT_VHL_속도_계산_20260422.md

실행:
    cd WORD_MODEL/WORLD_SIM
    python ../OHS_DATA_MD/OHT_VHL_속도_예시.py [VHL_ID]

기본 차량은 BV0103.

────────────────────────────────────────────────────────────
전체 흐름 한눈에:

  [원본 데이터]                    [처리]                [결과]
  ─────────────────────────────   ────────────────      ───────────
  M16A_BR_DATA/                   csv.DictReader        ZONE 속도 (A)
   ├─ LOGPRESSO_HID_INOUT.csv  ──┐                      차량 평균속도 (C)
   │   FREE_FLOW_SPEED 컬럼       │
   │   FROM_HIDID/TO_HIDID        ├─ vid 필터링
   │   _time, VHL_ID              │
   │                              │
   └─ 20260421.zip               │
        └─ oht_data_m16BR.csv ───┘── VelocityTracker ── 차량 순간속도 (B)
            VEHICLE, _time              ↑
            ADDRESS, NEXT_ADDRESS,     layout_cache.json
            DISTANCE                    (edges 길이)
────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import csv
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ── WORLD_SIM 의 VelocityTracker 사용
HERE = Path(__file__).resolve().parent
WORLD_SIM = HERE.parent / "WORLD_SIM"
sys.path.insert(0, str(WORLD_SIM))
from velocity_tracker import VelocityTracker  # noqa: E402

# ── 데이터 경로
DATA_DIR = HERE / "M16A_BR_DATA"
HID_CSV = DATA_DIR / "LOGPRESSO_HID_INOUT_20260421.csv"
ZIP_PATH = DATA_DIR / "20260421.zip"
OHT_CSV_NAME = "LOGPRESSO_oht_data_m16BR_20260421.csv"
LAYOUT_JSON = HERE.parent / "OHT_MAP" / "cache" / "M16A_BR_layout_cache.json"

DEFAULT_VID = "BV0103"


# ============================================================
# 공통 헬퍼
# ============================================================
def parse_time(s: str) -> datetime | None:
    """`'2026-04-21 14:00:00.873+0900'` 같은 문자열을 naive datetime 으로."""
    if not s:
        return None
    s = s.strip().strip('"')
    for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def fmt_speed(mpm: float | None) -> str:
    """m/min → '180.00 m/min (10.80 km/h)' (km/h 변환: × 0.06)."""
    if mpm is None:
        return "        None"
    return f"{mpm:7.2f} m/min ({mpm * 0.06:5.2f} km/h)"


def banner(step: str, title: str) -> None:
    print()
    print("━" * 72)
    print(f"[{step}] {title}")
    print("━" * 72)


# ============================================================
# STEP 0 — 단위 약속
# ============================================================
def step0_units() -> None:
    banner("STEP 0", "단위 약속 — 모든 계산을 시작하기 전에 알아두자")
    print("""
  ┌─ 거리 단위 ─────────────────────────────────
  │  UDP DISTANCE 컬럼,  layout_cache 의 edges 값 모두
  │  "dm" (데시미터, 1 dm = 100 mm = 0.1 m).  변환 상수 X.
  ├─ 시간 단위 ─────────────────────────────────
  │  _time 컬럼은 ISO + tz (예: '2026-04-21 14:00:00.873+0900').
  │  파싱 후 초(sec) 차분으로 사용.
  ├─ 속도 단위 ─────────────────────────────────
  │  계산 출력은 m/min.  km/h 가 필요하면 × 0.06.
  │    180 m/min = 10.80 km/h
  │    300 m/min = 18.00 km/h  (안전 상한)
  └─────────────────────────────────────────────""")


# ============================================================
# STEP 1 — HID_INOUT 읽기 + ZONE 속도(A) 분석
# ============================================================
def step1_zone_speed(vid: str) -> None:
    banner("STEP 1", "HID_INOUT 읽기 → (A) ZONE 자유흐름속도 = FREE_FLOW_SPEED")
    print(f"""
  사용 파일 : {HID_CSV.name}
  사용 컬럼 : FROM_HIDID, TO_HIDID, FREE_FLOW_SPEED, VHL_ID, _time
  처리 방법 : csv.DictReader 로 한 줄씩 읽으며 두 가지 집계
              (1) 같은 ZONE(HID 19→13) 통과 건들의 FFS 분포
              (2) 차량 {vid} 의 통과 시계열
  기대 결과 : (1) 표준편차 작음 ⇒ ZONE 별 속성 임을 확인
              (2) 같은 차량이 여러 ZONE 통과 → ZONE 마다 FFS 다름""")

    same_zone: list[float] = []
    vid_rows: list[tuple[datetime, int, int, float]] = []

    with open(HID_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                fr = int(row["FROM_HIDID"]); to = int(row["TO_HIDID"])
                ffs = float(row["FREE_FLOW_SPEED"])
            except (ValueError, KeyError):
                continue
            if fr == 19 and to == 13:
                same_zone.append(ffs)
            if row.get("VHL_ID") == vid:
                t = parse_time(row.get("_time", ""))
                if t:
                    vid_rows.append((t, fr, to, ffs))

    print()
    if same_zone:
        avg = sum(same_zone) / len(same_zone)
        std = (sum((x - avg) ** 2 for x in same_zone) / len(same_zone)) ** 0.5
        print(f"  ▶ (1) ZONE 통계 (HID 19→13, n={len(same_zone)}):")
        print(f"        평균={avg:.2f} m/min   표준편차={std:.2f} m/min")
        print(f"        → 표준편차가 작음 → 차량 무관, ZONE 속성 임이 확인됨")

    if vid_rows:
        vid_rows.sort()
        print(f"\n  ▶ (2) 차량 {vid} HID 통과 (앞 6건, ZONE 별 FFS 가 다름에 주목):")
        print(f"        {'time':<26} {'HID':<10} FFS")
        for t, fr, to, ffs in vid_rows[:6]:
            print(f"        {str(t):<26} {fr:>2}→{to:<2}     {fmt_speed(ffs)}")


# ============================================================
# STEP 2 — layout_cache 로드 (B 단계 준비)
# ============================================================
def step2_load_layout() -> tuple[dict, dict]:
    banner("STEP 2", "layout_cache 로드 — VelocityTracker 의 그래프 입력")
    print(f"""
  사용 파일 : {LAYOUT_JSON.relative_to(HERE.parent)}
  사용 키   : 'edges' (구간 길이),  'adj' (인접 노드)
  처리 방법 : JSON 의 'a,b' → (a,b) 튜플로, str → int 로 변환
  쓰임      : VelocityTracker.update() 가 Case B/C 에서
              엣지 길이/BFS 경로 길이 계산에 사용""")

    with open(LAYOUT_JSON, "r", encoding="utf-8") as f:
        d = json.load(f)

    edge_map: dict[tuple[int, int], float] = {}
    for k, v in d.get("edges", {}).items():
        a, b = k.split(",")
        edge_map[(int(a), int(b))] = float(v)
    adj_map = {int(k): list(v) for k, v in d.get("adj", {}).items()}

    print(f"\n  ▶ 로드 완료: edges={len(edge_map):,}개, adj={len(adj_map):,}개 노드")
    sample_edge = next(iter(edge_map.items()))
    print(f"        예) edge {sample_edge[0]} → {sample_edge[1]:.0f} dm "
          f"({sample_edge[1] * 0.1:.1f} m)")
    return edge_map, adj_map


# ============================================================
# STEP 3 — OHT raw 읽기 + (B) 순간속도 계산
# ============================================================
def iter_oht_rows_for_vid(vid: str):
    """zip 안의 oht_data CSV 에서 vid 의 행을 시간순으로 yield."""
    rows: list[tuple[datetime, int, int, int]] = []
    with zipfile.ZipFile(str(ZIP_PATH), "r") as zf:
        with zf.open(OHT_CSV_NAME) as raw:
            text = (line.decode("utf-8", errors="replace") for line in raw)
            reader = csv.DictReader(text)
            for row in reader:
                if row.get("VEHICLE") != vid:
                    continue
                try:
                    addr = int(row["ADDRESS"]); nxt = int(row["NEXT_ADDRESS"])
                    dist = int(row["DISTANCE"])
                except (ValueError, KeyError):
                    continue
                t = parse_time(row.get("_time", ""))
                if not t:
                    continue
                rows.append((t, addr, nxt, dist))
    rows.sort()  # ★ 시간순 정렬은 필수 — VelocityTracker 는 단조 증가 시간 기대
    yield from rows


def step3_instant_speed(vid: str, edge_map: dict, adj_map: dict,
                        max_samples: int = 10) -> None:
    banner("STEP 3", "OHT raw 읽기 → (B) VelocityTracker 로 순간속도 계산")
    print(f"""
  사용 파일 : {ZIP_PATH.name} 안의 {OHT_CSV_NAME}
  사용 컬럼 : VEHICLE → vid,  _time → t,
              ADDRESS → curr_node,  NEXT_ADDRESS → next_node,
              DISTANCE → distance (dm)
  처리 방법 : 1. zip 풀어 OHT CSV 스트리밍 읽기 (메모리 절약)
              2. 차량 {vid} 의 행만 골라 시간순 정렬
              3. VelocityTracker.update(vid,t,curr,next,distance) 반복 호출
              4. 트래커 내부에서 Δdistance / Δt 자동 계산
                 - Case A: 같은 엣지 → distance 차분
                 - Case B: 자연 전환 → 이전 엣지 잔여 + 현재 distance
                 - Case C: 불연속 → BFS 로 경로 길이 추정
  공식      : speed [m/min] = Δdm × 6 / Δt_sec
              (계수 6 = 1dm/0.1m × 60s/min)
  주의      : 첫 행은 prev 가 없어 None.  실제 계산은 두 번째 행부터.""")

    tracker = VelocityTracker(edge_dist_map=edge_map, adj_map=adj_map)
    print(f"\n  ▶ 차량 {vid} 순간 속도 (앞 {max_samples} 샘플):")
    print(f"        {'time':<26} {'edge':<14} {'dist':>5}  speed")

    count = 0
    for t, addr, nxt, dist in iter_oht_rows_for_vid(vid):
        speed = tracker.update(vid, t, addr, nxt, dist)
        print(f"        {str(t):<26} {addr:>4}→{nxt:<6} {dist:>5}  {fmt_speed(speed)}")
        count += 1
        if count >= max_samples:
            break

    if count == 0:
        print(f"        (차량 {vid} 의 OHT raw 없음 — 다른 VID 로 시도)")
        return

    print("""
  ▶ 해석 가이드:
      * speed = None → 첫 관측이거나 갭 30s 초과 / 후진 / NaN
      * speed = 0    → 정지 또는 후진 보정
      * speed = 300  → MAX 클램프 (Δt 매우 짧고 Δdm 큼)
      * 정상 분포는 100~250 m/min (6~15 km/h)""")


# ============================================================
# STEP 4 — HID 통과 차분으로 (C) 평균속도
# ============================================================
def step4_avg_from_hid(vid: str) -> None:
    banner("STEP 4", "HID 통과시간 차분 → (C) OHT 평균속도 (보조 지표)")
    print(f"""
  사용 파일 : {HID_CSV.name}  (★ OHT raw 가 없을 때의 대안)
  사용 컬럼 : VHL_ID, _time, FROM_HIDID, TO_HIDID
  처리 방법 : 1. 차량 {vid} 의 HID 통과 행을 시간순 정렬
              2. 인접한 두 통과 사이 Δt 계산
              3. v_avg = path_length / Δt   (path 는 layout 으로 계산)
              4. Δt < 1s 인 동시각 행은 다중 ZONE 동시 기록이라 스킵
  주의      : path_length 는 실 운영에서 layout_cache 의
              엣지 길이 합으로 정확히 구해야 함.  여기선 데모로 250 m 가정.""")

    rows: list[tuple[datetime, int, int]] = []
    with open(HID_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("VHL_ID") != vid:
                continue
            t = parse_time(row.get("_time", ""))
            if not t:
                continue
            try:
                rows.append((t, int(row["FROM_HIDID"]), int(row["TO_HIDID"])))
            except (ValueError, KeyError):
                continue
    rows.sort()

    if len(rows) < 2:
        print(f"\n  (차량 {vid} 의 HID 통과 < 2건)")
        return

    ASSUMED_PATH_M = 250.0
    print(f"\n  ▶ 차량 {vid} 구간별 평균 속도 (가정 path={ASSUMED_PATH_M} m, 앞 6 구간):")
    print(f"        {'from→to':<10} {'Δt(s)':>8}  v_avg")

    shown = 0
    for i in range(1, len(rows)):
        t_prev, _, _ = rows[i - 1]
        t_now, fr, to = rows[i]
        dt = (t_now - t_prev).total_seconds()
        if dt < 1.0:
            continue  # 동시각 다중 HID 스킵
        v_avg = ASSUMED_PATH_M / dt * 60.0
        print(f"        {fr:>3}→{to:<3}    {dt:>8.2f}  {fmt_speed(v_avg)}")
        shown += 1
        if shown >= 6:
            break


# ============================================================
# STEP 5 — 어디에 어떻게 쓰나 (실제 코드와의 연동)
# ============================================================
def step5_integration() -> None:
    banner("STEP 5", "실제 시뮬레이터에서의 연동 — 어디에 어떻게 들어가나")
    print("""
  ▶ (B) VelocityTracker 의 호출처:
      WORD_MODEL/WORLD_SIM/world_model.py:191-224
        load_vehicles_from_frame() 안에서 매 프레임 호출

        velocity = self.velocity_tracker.update(
            vid, udp_time, current_node, next_node, distance
        )
        # None 이면 UI 에 "측정 불가" — 가짜값으로 메우지 않음

  ▶ (A) FREE_FLOW_SPEED 의 호출처:
      WORD_MODEL/WORLD_SIM/data_loader.py:625-657
        _load_hid_inout() 가 'speed' 필드로 읽음
        get_hid_speed_summary() 가 ZONE 별 평균/최저/최고로 집계

  ▶ (C) HID 통과 차분:
      현재 시뮬레이터엔 미사용.  본 예시처럼 외부 분석 스크립트에서만 활용.

  ▶ 정리:
      - 시뮬레이터 차량 속도 표시 = (B)
      - ZONE 통계 / 정의속도      = (A)
      - 보조 검증 / 백업 분석     = (C)""")


# ============================================================
# Entrypoint
# ============================================================
def main() -> None:
    vid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VID
    print(f"OHT VHL 속도 계산 흐름 튜토리얼 — 대상 차량: {vid}")
    print("문서: WORD_MODEL/OHS_DATA_MD/OHT_VHL_속도_계산_20260422.md")

    if not HID_CSV.exists():
        print(f"[에러] {HID_CSV} 없음", file=sys.stderr); sys.exit(1)
    if not LAYOUT_JSON.exists():
        print(f"[에러] {LAYOUT_JSON} 없음", file=sys.stderr); sys.exit(1)
    if not ZIP_PATH.exists():
        print(f"[에러] {ZIP_PATH} 없음", file=sys.stderr); sys.exit(1)

    step0_units()
    step1_zone_speed(vid)
    edge_map, adj_map = step2_load_layout()
    step3_instant_speed(vid, edge_map, adj_map)
    step4_avg_from_hid(vid)
    step5_integration()

    print()
    print("━" * 72)
    print("끝.  자세한 공식·케이스·가드 설명은 .md 문서 참조.")
    print("━" * 72)


if __name__ == "__main__":
    main()
