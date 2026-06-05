================================================================
AWS_IDC_DATA_HIS 분단위 피벗 SQL (3종) — 사용법
================================================================

[공통]
 - 테이블 : AWS_IDC_DATA_HIS (Oracle)
 - 결과   : 분당 1행, CRT_TM + 265개 IDC 컬럼
 - 분당 1행 보장 : MAX + GROUP BY CRT_TM 로 같은 분 내 중복 행 자동 합침
 - 인덱스 권장 : (CRT_TM, IDC_NM) — 없으면 풀스캔 (수십초~분 단위)

[01_날짜범위.sql]  — 바인드변수 :start_dt, :end_dt
  Python cx_Oracle / oracledb / SQL*Plus 등:
    cur.execute(sql, start_dt='2026-05-01 00:00:00',
                     end_dt  ='2026-05-02 00:00:00')

[02_하루치_바인드변수.sql]  — :target_date 한 개만
    cur.execute(sql, target_date='2026-05-15')
  → 2026-05-15 00:00:00 ~ 2026-05-16 00:00:00 (미포함)

[03_하드코딩_바로실행.sql]  ★ SQL Developer/DBeaver 에서 가장 편함
  WHERE 절의 날짜 문자열 두 줄만 수정 후 F5
  바인드변수 입력창 안 뜸

[CSV 저장 시 ★주의]
 - SQL Developer 우클릭 → Export → CSV
 - 인코딩 : UTF-8
 - 따옴표 처리 : "필요시" (RFC 4180 표준)
 - Excel 로 절대 열지 말 것 (따옴표 떨어지고 시간이 00:00→0:00 으로 깨짐)
 - 저장 후 그대로 hubroom_predictor.py 입력으로 사용 가능:
     python hubroom_predictor.py 2026_05_XX.csv -o .\predict_tobe

[hubroom_predictor 와 호환]
 - 첫 컬럼명 CRT_TM (그대로 사용)
 - 나머지 265개 컬럼명이 hubroom_predictor.py 가 기대하는 IDC 이름과 동일
================================================================
