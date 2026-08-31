#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_loader.py 패치 — Rail Cut 페어 매칭 (ABNORMAL/NORMAL)

로직: 시간순 재생하면서 활성 집합 관리
  - STATE=ABNORMAL → 활성 집합에 추가
  - STATE=NORMAL   → 활성 집합에서 제거
  - 매칭 안 되면 그냥 둠 (복구 없으면 계속 활성 / 복구만 있으면 무시)

적용 방법:
  1. DateDataLoader 클래스 안에 _get_active_rail_cuts 메서드 추가
  2. get_frame_at 메서드의 rail_cut 부분 한 줄 교체
"""

# ============================================================
# [1] DateDataLoader 클래스 안에 이 메서드 추가
# ============================================================

def _get_active_rail_cuts(self, target_time):
    """
    현재 시각까지 시간순 재생하면서 활성 차단만 반환.

    ABNORMAL → 활성 추가
    NORMAL   → 활성 제거
    매칭 안 된 ABNORMAL은 그대로 활성 유지 (복구 기록 없는 경우)
    매칭 안 된 NORMAL은 무시 (전날 차단의 복구 등)
    """
    active = {}  # (from_addr, to_addr) -> {ev, start_time}

    for t, ev in self.rail_cut_events:
        if t > target_time:
            break

        key = (ev.get('from_addr'), ev.get('to_addr'))
        state = (ev.get('state') or '').upper().strip()

        if state == 'ABNORMAL':
            active[key] = {'ev': ev, 'start_time': t}
        elif state == 'NORMAL':
            active.pop(key, None)
        # 그 외 state는 무시

    # 활성 이벤트에 경과 시간 메타 추가
    result = []
    for key, info in active.items():
        ev_copy = dict(info['ev'])
        ev_copy['start_time'] = info['start_time'].strftime('%H:%M:%S')
        elapsed_sec = int((target_time - info['start_time']).total_seconds())
        ev_copy['elapsed_sec'] = elapsed_sec
        ev_copy['elapsed_min'] = round(elapsed_sec / 60, 1)
        result.append(ev_copy)

    return result


# ============================================================
# [2] get_frame_at 메서드 안의 RAIL_CUT 블록 교체
# ============================================================

# 기존 코드 (삭제):
#
#   # RAIL_CUT: 현재까지 발생한 이벤트
#   rail_cuts = []
#   for t, ev in self.rail_cut_events:
#       if t <= target_time:
#           rail_cuts.append(ev)

# 새 코드 (교체):
#
#   # RAIL_CUT: 페어 매칭으로 현재 활성 차단만 반환
#   rail_cuts = self._get_active_rail_cuts(target_time)


# ============================================================
# 동작 예시 (4/16 데이터 기준)
# ============================================================
"""
타임라인:
  09:00:30  ABNORMAL  1470→15197   → active 추가
  09:56:00  ABNORMAL  8292→1765    → active 추가
  09:57:00  ABNORMAL  1761→1763    → active 추가
  12:54:00  NORMAL    1761→1763    → active 제거 ✓
  13:00:00  NORMAL    8292→1765    → active 제거 ✓
  16:01:00  ABNORMAL  1761→1763    → 재차 추가

target_time = 13:30 기준으로 조회하면:
  반환: [1470→15197 (270분째), ... ]
  제외: 8292→1765 (13:00 복구됨)
  제외: 1761→1763 (12:54 복구됨, 16:01 재발은 미래)

→ dashboard.html은 기존 버전 그대로 OK. 
  mapData.blockedEdges가 자동으로 올바른 집합으로 그려짐.
"""
