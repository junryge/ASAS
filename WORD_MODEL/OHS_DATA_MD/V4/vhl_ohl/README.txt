HID_VHL_OHT.py — 5 FAB 병목 HID 구간 찾기 (따로 실행)  2026-10-01
============================================================

■ 무엇

  기존 수집 데이터와 별개입니다. 로그프레소에서 차량 보고를 직접 받아
  50초마다 보고 · 미보고 · JAM · HT_STOP 을 새로 계산하고,
  알람(경계 · 위험 · 초위험)일 때 멈춘 차가 많은 HID 구역을 저장합니다.
  경계 이상인 1분은 그 시각 문제맵(HTML 지도)도 바로 만듭니다 (아래 ■ 문제맵).
  다른 .py 파일은 필요 없습니다 (이 파일 하나 — 예전 HID_PROBLEM_MAP.py 를 합침).

■ 실행 — run_oht.py (HID_VHL_OHT.py + Rule_hid.py 같이)  ★운영은 이걸로

  python run_oht.py                     실시간 (Ctrl+C 로 멈춤) — 옵션은 HID_VHL_OHT.py 와 같다 (--no-problem-map 등)
  python HID_VHL_OHT.py                 이것도 똑같다 — Rule_hid.py 가 옆에 있으면 스스로 연결해서 바로 적재

  50초마다   로그프레소에서 차량 보고를 받아 판정 (HID_VHL_OHT)
  1분 끝나면 그 분 한 줄 → CSV            HID_BOTTLENECK\{FAB}\HID_BOTTLENECK_{FAB}_YYYYMMDD.csv
                       → 바로 같은 줄 + FAB   로그프레소 AMHS_VHL_OHT (Rule_hid, CSV 쓰자마자 그 자리에서, 1분에 한 줄 · FAB 마다)
                                            로그: [Rule_hid] 적재 OK → AMHS_VHL_OHT  M16HUB 2026-09-29 08:13 초위험
                       → 경계 이상이면   문제맵 HTML
  · CSV 에 새로 생긴 줄만 넣는다. 다시 켜도 이미 쓴 분은 CSV · AMHS_VHL_OHT 둘 다 다시 안 넣는다.
  · 적재가 실패해도 CSV · 판정 · 문제맵은 계속 돈다 (재시도 → 한 번 다시 넣기 → 그래도 안 되면 로그에 남김)

  AMHS_VHL_OHT 한 줄 (CSV 한 줄 + FAB, HT_STOP 은 숨김이라 없음)
    datetime 'YYYY-MM-DD HH:MM' · fab_name (M16HUB …) · alarm_kr · alarm_en · hid_zone · hid_section
    oht_report · oht_missing · oht_jam · zone_stop · zone_vhl · vhl_max · zone_occ · hid_zone_2 · hid_zone_3
    예) json "{datetime = '2026-09-29 08:13', fab_name = 'M16HUB', alarm_kr = '초위험', alarm_en = 'CRITICAL',
              hid_zone = '33', hid_section = 'BR06', oht_report = '133', oht_missing = '137', oht_jam = '11', …}" | import AMHS_VHL_OHT

  적재 설정 — config.json (압축에 들어 있음, Rule_LO 운영 config 와 같은 서버)
    config.json      "enabled": true · "logpresso_base": "http://10.40.42.167:8888/logpresso"
                     "hid_table_name": "AMHS_VHL_OHT" · "hid_only_alarm": false
    api_key.txt      적재용 키 (Rule_LO 와 같은 키) — 없으면 판정용 hdi_api_key.txt 를 쓴다
    · config.json 이 없거나 enabled=false 면 적재만 안 하고 CSV · 문제맵은 그대로 돈다
    · config.json 에 더 넣을 수 있는 것 (안 넣어도 됨)
        "hid_enabled": false               Rule_hid 만 끔
        "hid_table_name": "AMHS_VHL_OHT"   테이블 이름
        "hid_only_alarm": true             경계 이상 줄만 (기본 = 정상 포함 1분마다 다)
        "hid_api_key_file": "api_key_hid.txt"   이 테이블 권한이 있는 키를 따로 쓸 때
  시험 — python Rule_hid.py          설정 · 키 · 테이블 확인 (안 넣음)
         python Rule_hid.py --write  AMHS_VHL_OHT 에 fab_name='DIAG_TEST' 한 줄 시험으로 넣기
         HTTP 500 이면 Rule_LO 때와 같음 — 키 권한 · 테이블 없음 · 주소 중 하나

■ 폴더 (이 파일 옆에)

  run_oht.py                              ★실행 — HID_VHL_OHT.py + Rule_hid.py 같이
  HID_VHL_OHT.py                          판정 · CSV · 문제맵
  Rule_hid.py                             CSV 새 줄 → 로그프레소 AMHS_VHL_OHT
  config.json · api_key.txt               적재 설정 (압축에 있음) · 적재 키 (Rule_LO 의 것, 없으면 hdi_api_key.txt)
  HID_REF_M16HUB.csv                 문서의 HID 구간 번호 (HID_ZONE 칸 고를 때만 씀)
  HID_CONFIG.json                         FAB 별 경계 · 위험 · 초위험 기준 (없으면 기본값으로 만들어짐)
  hdi_api_key.txt                         로그프레소 키 (첫 줄)
  OHT_MAP\                                월드모델파생의 OHT_MAP 폴더 그대로 복사
      MAP\M14A\HID_Zone_Master_M14A_A.csv     → M14
      MAP\M14B\HID_Zone_Master_M14B_A.csv     → M14B
      MAP\M16A\HID_Zone_Master_M16A_A.csv     → M16A
      MAP\M16A\HID_Zone_Master_M16A_BR.csv    → M16HUB
      MAP\M16B\HID_Zone_Master_M16B_B.csv     → M16B
      cache\*_layout_cache.json
  oht3d\                                  월드모델파생 static\js\oht3d 그대로 (oht3d.js · three.module.min.js) — 문제맵 아이소메트리
  HID_MAP_SETTINGS.json                   문제맵 표시 기본값 (OHT 크기 · 색 · 테마 · 히트맵, 없으면 만들어짐)
  (어느 FAB 맵이 없으면 그 FAB 만 빠지고 나머지는 돕니다)

■ 서버 · 테이블

  10.40.42.167:8888   oht_data_m16br (M16HUB) · oht_data_m16a (M16A) · oht_data_m16b (M16B)
  10.40.42.27:8888    oht_data_m14a (M14) · oht_data_m14b (M14B)
  remote 없이 먼저 조회하고 안 되면 remote 로 — 되는 쪽을 기억합니다.

■ 돌릴 FAB — HID_CONFIG.json 의 "RUN_FABS"

  "RUN_FABS": ["M16HUB"],                                   ← 지금은 M16HUB 만 (실시간 · --test)
  "RUN_FABS": ["M14", "M14B", "M16A", "M16B", "M16HUB"],    ← 다섯 다 돌릴 때
  · 적은 FAB 만 맵을 읽고 로그프레소를 조회합니다 (나머지 FAB 은 CSV 도 안 생김)
  · 이것만은 고친 뒤 프로그램을 다시 켜야 적용됩니다 (기준 숫자는 켠 채로 바로 적용)
  · 과거 판정은 명령에 적은 FAB (ALL 이면 다섯 다) — RUN_FABS 와 상관없음

■ 알람 기준 — HID_CONFIG.json 에서 FAB 마다 따로 (그 50초 구간의 FAB 전체 값 — 과거 구간 안 끌고 옴)

  ★ FAB 마다 따로 설정해야 합니다. 처음 숫자는 M16HUB 9월 데이터 · 메신저로 정한 기본값이라,
    M14 · M14B · M16A · M16B 는 며칠 돌려 보고 그 FAB 칸을 각각 고쳐야 합니다.
  · 미보고 = 최근 100분 안에 보고한 차량 수 − 그 50초에 보고한 차량 수 (자동, 따로 넣지 않음)
    전체 차량에는 50초 구간 2개 이상에서 보인 차만 셉니다
    (9/22 10:03 처럼 한 구간만 보고 차량이 455대로 튀어도 미보고가 부풀지 않음)

  넷 중 하나라도 맞으면 그 단계 (초위험 → 위험 → 경계 순으로 봄)
    1. missing + JAM : 같은 50초 구간에 2개가 같이 기준 이상 (한쪽만 넘으면 안 걸림)
    2. missing_ONLY  : 미보고 1개만 기준 이상이면 됨
    3. HT_STOP       : 1개만 기준 이상이면 됨
    4. ZONE_STOP     : HID 구역 하나 안에 멈춘 차(미보고 + JAM + HT)가 기준 이상이면 됨 (= 줄의 ZONE_STOP 칸)

  "M16HUB": {
    "경계":   {"missing": 10, "JAM": 10, "missing_ONLY": 0,   "HT_STOP": 0,  "ZONE_STOP": 10},
    "위험":   {"missing": 0,  "JAM": 0,  "missing_ONLY": 30,  "HT_STOP": 10, "ZONE_STOP": 0},
    "초위험": {"missing": 0,  "JAM": 0,  "missing_ONLY": 100, "HT_STOP": 30, "ZONE_STOP": 0}
  }

  config 파일 2개 — 쓸 파일을 HID_CONFIG.json 이름으로 복사하면 됨 (프로그램은 HID_CONFIG.json 만 읽음)
    HID_CONFIG_BIG_ZONE.json   위 기본값 (= 처음 HID_CONFIG.json)
                                  경계 = 미보고 10 + JAM 10 같이, 또는 한 구역에 멈춘 차 10대 이상
                                  9/12: 14:29 HID 4 에 16대 → 경계 (구역 조건 없을 때보다 17분 먼저), 9/29: 08:06 경계
    HID_CONFIG_FINE_ZONE.json     경계 미보고 6 + JAM 10 같이 / 구역 멈춘 차 10
                                  위험 미보고 단독 15 / HT_STOP 5 / 구역 멈춘 차 20
                                  초위험 미보고 단독 50 / HT_STOP 20
                                  9/12: 14:29 경계 · 14:31 위험(HID 4 에 20대) · 14:48 초위험, 9/29: 08:05 위험 · 08:10 초위험
    ★ 구역 조건은 원본 데이터 이틀치로만 확인 — 9월을 다시 돌려 오탐을 보고 정하세요
  · 9월 M16HUB (메신저 확인 사건 8건): 8건 다 잡음, 경계 이상 알람 분의 92% 가 사건 구간 (오탐 8%)
    예전 기준(7+10 · HT 1 / 30+20 · HT 10 / 50+30 · HT 30)은 86% / 14%
  · 예전 HID_CONFIG.json 을 그대로 두면 그 숫자를 쓰고 빠진 칸(missing_ONLY · ZONE_STOP)은 0(끔)으로 채웁니다
    → 새 기준을 쓰려면 이 압축의 HID_CONFIG.json 으로 바꾸세요
  · 숫자 0 = 그 조건 끔
  · 고치면 다시 켜지 않아도 다음 50초 구간부터 적용 (로그에 "HID_CONFIG.json 바뀜")
  · 파일이 깨지면 이전 설정으로 계속 돌고 로그에 이유를 남깁니다
  · 예) 전조를 더 일찍: 경계 missing · JAM 을 낮춤 (대신 평소 알람이 늘어남)
  · 예) 위험이 너무 자주: 위험 missing_ONLY 를 올림
  · 자세한 설명은 HID_BOTTLENECK_COLUMNS.html 3장 · 7장, 그림은 HID_BOTTLENECK_ARCHITECTURE.html

■ 저장  HID_BOTTLENECK\{FAB}\HID_BOTTLENECK_{FAB}_YYYYMMDD.csv   (FAB 마다 폴더 · 파일 따로, 실시간 1분마다 한 줄)

  날짜, 시간, HID_ZONE, {FAB}_OHT_report, {FAB}_OHT_missing, {FAB}_OHT_JAM, ALARM_KR, ALARM_EN, HID_section,   (15칸)
  ALARM_KR = 정상 / 경계 / 위험 / 초위험,  ALARM_EN = NORMAL / WARNING / DANGER / CRITICAL (같은 판정, 글자만 영문)
  ★HT_STOP 은 판정(위험 · 초위험 조건)에만 쓰고 CSV · 문제맵 · 히트맵 · 로그에는 안 보입니다 (숨김)
  ZONE_STOP, ZONE_VHL, VHL_MAX, ZONE_OCC, HID_ZONE_2, HID_ZONE_3
    시간          HH:MM (1분)
    report        그 50초에 보고한 차량 수 (데이터 값)
    missing/JAM   FAB 전체 값 — 그 분이 끝날 때까지 끝난 마지막 50초 구간
    ALARM_KR      경계 / 위험 / 초위험 / 정상
    ALARM_EN      WARNING / DANGER / CRITICAL / NORMAL
    HID_ZONE      병목 HID 구역 번호 = 문서(병목 HID 구간 찾기)의 "HID 4 · HID 33" 과 같은 번호,  알람 아니면 0
                  마스터 ZONE_ID · ZONE_ID2 중 문서 번호와 맞는 칸을 시작할 때 자동으로 고릅니다
                  (같이 넣은 HID_REF_M16HUB.csv 로 맞춰 봄 — 시작 로그 "HID_ZONE = … 일치 …%")
                  고정하려면 파일 위  HID_ZONE_COL = "ZONE_ID"  또는  "ZONE_ID2"
    HID_section   그 구역의 Bay_Zone,  알람 아니면 0
    ZONE_STOP     병목 1위 구역 안 멈춘 차 (미보고 + JAM + HT, 한 대 한 번)
    ZONE_VHL      그 구역 안 전체 차량 (보고 차 + 미보고 차의 끊기기 직전 위치)
    VHL_MAX       마스터 Vehicle_Max (그 구역 정원)
    ZONE_OCC      점유율 % = ZONE_VHL / VHL_MAX × 100   (VHL_MAX 가 0 이면 0)
    HID_ZONE_2/3  2위 · 3위 구역 (HID_ZONE 과 같은 번호) — 어디로 번지는지
      → ZONE_STOP · ZONE_VHL · 점유율은 그 분의 마지막 50초 구간 값. 알람 아니면 0.
        ALARM · 숫자 · 구역 칸은 모두 같은 50초 구간 값 (그 분에 구간이 2개면 더 높은 단계 구간) — 줄 숫자로 ALARM 을 다시 계산할 수 있습니다 (단, HT_STOP 은 숨김이라 HT_STOP 으로 걸린 위험 · 초위험은 줄 숫자에 안 보임).
    데이터가 없는 분은 숫자 0 · ALARM 정상

  예) 2026-09-29,08:05,0,252,18,5,0,정상,0,0,0,0,0,0,0
      2026-09-29,08:06,33,256,14,10,1,경계,BR06,10,24,(정원),(점유율),35,28
      2026-09-29,08:12,30,174,96,41,6,초위험,BR05,27,27,(정원),(점유율),34,33

■ 실행

  python HID_VHL_OHT.py --test     맵 읽기 + 최근 10분 한 번 판정 (저장 안 함) ← 먼저
  python HID_VHL_OHT.py --map      주소 → HID 구역표를 HID_BOTTLENECK\ZONE_TABLE_{FAB}.csv 로 (확인용)
  python HID_VHL_OHT.py M16HUB 20260929              과거 판정 — FAB 하루
  python HID_VHL_OHT.py M16HUB 20260912 20260929     과거 판정 — FAB 날짜 ~ 날짜 (하루씩 CSV)
  python HID_VHL_OHT.py ALL 20260912 20260929        FAB 5개 다
      → HID_BOTTLENECK\PAST\{FAB}\HID_BOTTLENECK_{FAB}_YYYYMMDD.csv   (FAB · 날짜별, 다시 돌리면 덮어씀)
      → HID_BOTTLENECK\PAST\SUMMARY_{FAB|ALL}_{시작}_{끝}.csv     (FAB · 날짜별 정상 · 경계 · 위험 · 초위험 분 수)
  python HID_VHL_OHT.py --range 202609290750 202609290830 --fab M16HUB   분 단위 구간 (검증용)
  python HID_VHL_OHT.py            계속 돈다 (Ctrl+C)

  50초마다 로그에 FAB 5개 상태가 한 줄로 나옵니다 — 어느 FAB 가 안 되는지 바로 보입니다.
    [08:07:30] M14 정상(보고 … ) · M14B 맵 없음 · M16A 조회 실패 · M16B 연결 안 됨 · M16HUB 경계(…)
      맵 없음      OHT_MAP 에 그 FAB HID_Zone_Master / layout_cache 가 없음 (시작 로그에 파일 이름)
      조회 실패    로그프레소가 오류를 돌려줌 (바로 위 줄에 이유)
      연결 안 됨   서버에 못 붙음
      데이터 없음  조회는 됐는데 그 구간 보고가 0

■ 주소 → HID 구역

  HID_Zone_Master 에는 구역 경계(IN/OUT 레인)만 있어서, 레이아웃을 따라가며
  구역마다 IN 레인에서 OUT 레인 전까지를 그 구역으로 봅니다.
  여러 구역에 걸리는 주소는 IN 에서 가장 가까운 구역 = 차가 마지막으로 들어간 구역.
  --map 으로 내보내서 현장 구역과 맞는지 한 번 봐 주세요.

■ 날짜별 과거 판정을 한 파일로 — HID_ALARM_MERGE.py  (과거 데이터 평가용)

  python HID_ALARM_MERGE.py                              전부 (FAB 5개 · 있는 날짜 다)
  python HID_ALARM_MERGE.py M16HUB 20260912 20260929     FAB · 날짜 구간
  python HID_ALARM_MERGE.py ALL 20260912 20260929        FAB 5개 · 날짜 구간

  한 번에 나오는 파일 (HID_BOTTLENECK\PAST\):
    {FAB}\HID_BOTTLENECK_{FAB}_{시작}_{끝}_MERGED.csv  ★FAB 마다 — 뽑은 CSV 와 칸 똑같이 날짜만 이어 붙인 한 파일
    MERGED_{FAB|ALL}_{시작}_{끝}.csv       ★평가용 — 전체 분 (정상 포함), FAB 모두 한 표
    ALARM_MERGED_{FAB|ALL}_{시작}_{끝}.csv   경계 · 위험 · 초위험 줄만
    ALARM_EVENTS_{FAB|ALL}_{시작}_{끝}.csv   이어진 알람 분 = 사건 하나 (시작 · 끝 · 최고 단계 · 시작/최다 HID_ZONE)

  칸 (합침 · 알람합침 같음) — FAB 칸을 붙이고 {FAB}_OHT_missing → OHT_missing 처럼 이름 통일
    FAB, 날짜, 시간, ALARM_KR, ALARM_EN, HID_ZONE, HID_section, OHT_report, OHT_missing, OHT_JAM,
    ZONE_STOP, ZONE_VHL, VHL_MAX, ZONE_OCC, HID_ZONE_2, HID_ZONE_3
  먼저 HID_VHL_OHT.py <FAB|ALL> <시작날짜> [끝날짜] 로 날짜별 과거 판정 파일을 만들어 두어야 합니다.

■ 문제맵 — HID_VHL_OHT.py 안에 합침 (실시간 CSV 를 쓰다가 경계 이상이면 그 1분 지도를 바로 만든다)

  python HID_VHL_OHT.py                            실시간 — 1분 줄 CSV + ALARM 경계 이상인 분마다 문제맵
  python HID_VHL_OHT.py --no-problem-map           실시간인데 문제맵은 안 만듦
  python HID_VHL_OHT.py M16HUB 20260929 --problem-map    과거 판정 + 경계 이상 분마다 문제맵
  python HID_VHL_OHT.py --map-at M16HUB 202609291348     그 1분만 로그프레소에서 판정해서 문제맵 하나 (여러 시각 가능, 정상도 만듦)
    → HID_BOTTLENECK\PROBLEM_MAP\{FAB}_{YYYYMMDD}\PROBLEM_MAP_{FAB}_{YYYYMMDD}_{HHMM}_{ALARM}.html   브라우저로 열기
       (ALARM = WARNING 경계 · DANGER 위험 · CRITICAL 초위험 · NORMAL 정상)
  · 몇 단계부터 만들지: HID_VHL_OHT.py 맨 위 설정 MAP_MIN_LEVEL = "경계" ("위험" · "초위험" 으로 바꿀 수 있음)
  · 판정 · 숫자는 CSV 그 줄과 똑같고, OHT 차량은 그 줄과 같은 50초 구간 (판정에 쓴 데이터 그대로 +
    방향 · 적재 · 점만 그 50초를 한 번 더 조회). 지도가 실패해도 판정 · CSV 는 계속 돈다 (로그에 남김)
  · 경계 이상인 분마다 파일 하나 (약 0.9MB) — 큰 사건 하나에 10~20개쯤

  지도 한 장에 나오는 것
    · 왼쪽 위 ALARM 칸: 경계 / 위험 / 초위험 / 정상 크게 + 1위 HID · Bay + 숫자, 세 단계 중 지금 단계 표시
    · 1위 구역(HID_ZONE) = ALARM 색 (경계 노랑 · 위험 빨강 · 초위험 자주), 2 · 3위 구역 = 파랑,
      라벨 "1위 HID 33 · BR06 · 초위험"
    · 맵 모양 = 월드모델파생 2D 맵 그대로 (MAP_THEMES · ⚙ 설정 기본값을 가져옴)
      HMI 테마(밝은 바탕 · 검은 레일) · HID 존 진입(실선)/진출(점선) 초록 · HID 라벨 초록 상자 — ⚙ 에서 다크로
    · OHT 차량 = 그 시각 위치, 월드모델파생과 같은 삼각형(꼭짓점 = 진행 방향) · 같은 색
      공차 초록 · 적재 하늘 · OBS 주황 · 정지 회색 · JAM 빨강, 안의 검은 점 = 들고 감 · 흰 점 = 가지러 감
      ✕ = 미보고 (끊기기 직전 위치). 그 1분 줄과 같은 50초 구간의 차량 (차량 수 = 그 줄의 report · JAM · missing)
      방향 · 적재 · 점은 월드모델파생 쿼리와 같은 칸(NEXT_ADDRESS · STOCK_INFO · VEHICLE_EXECUTE_CYCLE · DESTINATION)을 그 50초만 한 번 더 받음
      차량에 마우스를 올리면 차량 ID · 상태 · 주소 · HID
    · 보기 3가지 (월드모델파생과 같음): [▭ 2D] [◈ 유사 3D] [⬢ 아이소메트리]
      유사 3D = 2D 를 등각으로 눕힘 (월드모델파생 mapProjPoint 그대로)
      아이소메트리 = 월드모델파생 3D 뷰어(oht3d.js + three.js r169) 그대로 — 안의 '아이소/원근' 단추로 원근 3D,
        드래그 회전 · 휠 줌 · 크기 단추. 열면 1위 구역으로 날아감
      ★oht3d 폴더(oht3d.js · three.module.min.js)를 HID_VHL_OHT.py 옆에 두면 HTML 안에 넣어 준다 →
        HTML 하나만 보내도 인터넷 · 서버 없이 아이소메트리가 열림 (그래서 파일이 약 0.9MB)
        oht3d 폴더가 없으면 2D · 유사 3D 만 됨 (월드모델파생 static/js/oht3d 폴더를 그대로 복사해도 됨)
    · 🔥 히트맵 (세 보기 다, 월드모델파생 '히트맵 비전' 그대로)
      정체 무리 = 12 m 안에 멈춘 차가 몰린 곳. 대수대로 노랑 → 주황 → 빨강 → 짙은 적 (20대 이상이 제일 짙음)
      무리 위에 'N대'(종류가 섞이면 JAM 4 · 미보고 2 …) 와 그 HID 구역 이름
      2D · 유사 3D = 뿌연 원 (drawJamBlobs) · 아이소메트리 = 정체 지점 돔 + 이름표, 레일 원활 ↔ 정체 색
      정체 판정 '몇 대 이상' = 월드모델파생 ⚙ 기본값 (JAM 1 · OBS 0 · 멈춘 차 0 · 미보고 3, 0 = 안 봄 — HT_STOP 은 숨김이라 히트맵에 안 들어감)
      아이소메트리 레일 색은 차량 속도로 칠함 — 속도 = 앞 50초 구간 위치에서 지금 위치까지 레일을 따라 간 거리 ÷ 50초
    · ⚙ 설정 (지도 오른쪽 위): OHT 크기 · 레일 굵기 · 문제 구역 굵기 · 글자 크기 · 점 크기 · 테마 · 차량 색
      히트맵 켜기/끄기 · 정체 판정 '몇 대 이상' 도 여기서
      → 그 브라우저에 저장. 모든 지도의 기본값은 HID_MAP_SETTINGS.json (없으면 만듦, vehicleRadius = OHT 크기)
    · 오른쪽: 구역 이름 · Bay, 그 1분 숫자, 판정 근거 (HID_CONFIG.json 의 어느 조건에 걸렸나)
    · 열면 전체 맵 · ◎ 문제 구역 단추 = 1~3위 구역으로 확대 · 휠 확대 · 드래그 이동 · 더블클릭 전체
    · ⚠ 지도에 없는 구역 / HID_section 이 지도와 다름 → HID_Zone_Master 확인
