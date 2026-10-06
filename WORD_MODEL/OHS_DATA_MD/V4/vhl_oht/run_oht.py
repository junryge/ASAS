# -*- coding: utf-8 -*-
"""
run_oht.py — HID_VHL_OHT.py + Rule_hid.py (+ OHT_MAP_INDEX.py) 같이 돌리기

    python run_oht.py                     실시간 (계속 돈다, Ctrl+C 로 멈춤)
    python run_oht.py --no-problem-map    실시간인데 문제맵은 안 만듦
    (HID_VHL_OHT.py 의 옵션을 그대로 넘긴다)

  50초마다  HID_VHL_OHT 가 로그프레소에서 차량 보고를 받아 판정
  1분 끝나면 그 분 한 줄 → CSV  (HID_BOTTLENECK/{FAB}/HID_BOTTLENECK_{FAB}_YYYYMMDD.csv)
                          → 같은 줄 + FAB → 로그프레소 AMHS_VHL_OHT  (Rule_hid)
                          → 경계 이상이면 문제맵 (HID_BOTTLENECK/PROBLEM_MAP/…)
                          → 문제맵 경로 → ../m16a_hubroom_event_prediction/oht_map/OHT_MAP_YYYYMMDD.csv
                                          (OHT_MAP_INDEX — 다운로드 화면용 목록)
  돌릴 FAB 은 HID_CONFIG.json 의 RUN_FABS. 적재 · 목록 설정은 config.json (Rule_LO 와 같은 파일).
  다시 켜도 이미 CSV 에 쓴 분은 다시 안 넣는다 (CSV · AMHS_VHL_OHT · 목록 중복 없음).
  영문 등급은 정상 NONE · 경계 WARNING · 위험 CRITICAL · 초위험 EMERGENCY (ALARM_EN_NEW)
"""
import sys

import HID_VHL_OHT as HID
import Rule_hid

# ★ 영문 등급 (2026-10 변경) — HID_VHL_OHT.py 는 그대로 두고 여기서 바꿔 끼운다
#   CSV ALARM_EN · 문제맵 파일 이름 · 로그프레소 alarm_en 이 모두 이 이름으로 나간다
ALARM_EN_NEW = {"정상": "NONE", "경계": "WARNING", "위험": "CRITICAL", "초위험": "EMERGENCY"}


def _rename_alarm_en():
    """HID 안의 한글→영문 사전(ALARM_EN_OF 등)과 영문→한글 사전 값을 새 이름으로 바꾼다."""
    kr = set(ALARM_EN_NEW)
    en = {"NORMAL", "WARNING", "DANGER", "CRITICAL", "NONE", "EMERGENCY"}   # 예전 · 새 영문 이름
    done = []
    for name, d in list(vars(HID).items()):
        if not isinstance(d, dict) or not d:
            continue
        if set(d) <= kr and set(d.values()) <= en:          # 한글 → 영문 (색 등 다른 사전은 안 건드림)
            for k in d:
                d[k] = ALARM_EN_NEW[k]
            done.append(name)
        elif set(d) <= en and set(d.values()) <= kr:        # 영문 → 한글
            new = {ALARM_EN_NEW[v]: v for v in d.values()}
            d.clear()
            d.update(new)
            done.append(name)
    HID.log.info(f"  영문 등급: " + " · ".join(f"{k} {v}" for k, v in ALARM_EN_NEW.items())
                 + (f"  ({', '.join(done)})" if done else "  (⚠ 바꿀 사전을 못 찾음 — 예전 이름 그대로)"))

try:
    import OHT_MAP_INDEX as MAP_INDEX
except Exception as _e:                               # 없거나 깨져도 본 기능은 그대로 돈다
    MAP_INDEX = None
    print(f"[run_oht] OHT_MAP_INDEX 불러오기 실패 — 문제맵 목록 CSV 없이 진행: {_e}")


def _hook_map_index():
    """문제맵을 만들 때마다 바로 목록 CSV 에 넣는다 (HID_VHL_OHT.py 는 그대로)."""
    if MAP_INDEX is None or not MAP_INDEX.ENABLED:
        return
    try:
        n = MAP_INDEX.sync()                          # 켤 때 — 그동안 만들어진 맵 전부 (빠진 것만)
        HID.log.info(f"  문제맵 목록 → {MAP_INDEX.INDEX_DIR}" + (f"  ({n}개 추가)" if n else ""))
    except Exception as e:
        HID.log.warning(f"  문제맵 목록 정리 실패 — 계속 진행: {e}")
    orig = HID.problem_map

    def problem_map(*a, **kw):
        res = orig(*a, **kw)
        try:
            MAP_INDEX.sync_recent()
        except Exception as e:
            HID.log.warning(f"  문제맵 목록 추가 실패 — 다음 맵 때 같이 넣는다: {e}")
        return res

    HID.problem_map = problem_map


def main():
    _rename_alarm_en()
    Rule_hid.start()
    if Rule_hid.upload_rows not in HID.SAVE_HOOKS:
        HID.SAVE_HOOKS.append(Rule_hid.upload_rows)   # CSV 에 1분 줄을 쓸 때마다 → AMHS_VHL_OHT
    _hook_map_index()
    try:
        HID.main()                                    # 50초마다 판정 (옵션은 HID_VHL_OHT.py 와 같다)
    except KeyboardInterrupt:
        HID.log.info("멈춤 (Ctrl+C)")
    finally:
        Rule_hid.stop()                               # 남은 줄 다 보내고 끝


if __name__ == "__main__":
    main()
