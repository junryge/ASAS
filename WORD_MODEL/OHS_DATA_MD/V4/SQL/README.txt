================================================================
AWS_IDC_DATA_HIS 분단위 피벗 SQL (4종) — 사용법
================================================================

[공통]
 - 테이블 : AWS_IDC_DATA_HIS (Oracle)
 - 결과   : 분당 1행, CRT_TM + 265개 IDC 컬럼
 - 분당 1행 보장 : MAX + GROUP BY CRT_TM 로 같은 분 중복 자동 합침
 - 인덱스 권장 : (CRT_TM, IDC_NM) — 없으면 풀스캔 (수십초~분)


[★★★ 04_DATA폴더_자동저장.sql] — 가장 추천
  SQL 안에서 SPOOL 로 CSV 자동 저장. 날짜 3줄만 수정 → 끝.
  Excel 안 거쳐서 따옴표/시간 깨짐 없음.

  ▶ 사용법
    1) 파일 열고 맨 위 DEFINE 3줄 수정:
         DEFINE start_dt = '2026-05-15 00:00:00'
         DEFINE end_dt   = '2026-05-16 00:00:00'
         DEFINE outfile  = 'C:\DATA\2026_05_15_idc.csv'

    2) 실행
       - SQL*Plus:
           sqlplus user/pass@dsn @04_DATA폴더_자동저장.sql
       - SQLcl:
           sql user/pass@dsn @04_DATA폴더_자동저장.sql
       - SQL Developer:
           파일 열고 F5 (스크립트 실행 — 한 줄 실행 X)

    3) outfile 경로에 CSV 자동 저장
       → 그대로 hubroom_predictor.py 입력으로 사용:
           python ..\hubroom_predictor.py C:\DATA\2026_05_15_idc.csv -o .\predict_tobe


[01_날짜범위.sql]  — 바인드변수 :start_dt, :end_dt
  Python (oracledb/cx_Oracle) 코드에서 호출용:
    cur.execute(sql, start_dt='2026-05-01 00:00:00',
                     end_dt  ='2026-05-02 00:00:00')

[02_하루치_바인드변수.sql]  — :target_date 한 개만
    cur.execute(sql, target_date='2026-05-15')
  → 2026-05-15 00:00:00 ~ 2026-05-16 00:00:00 (미포함)

[03_하드코딩_바로실행.sql]  — SQL Developer 에서 결과 그리드 보기용
  WHERE 절 날짜 두 줄 수정 → F5
  ※ 결과를 CSV 로 저장하려면 04번 추천 (수동 export 는 Excel 함정 위험)


[CSV 저장 후 ★주의]
 - Excel 로 절대 열지 말 것 — 따옴표 떨어지고 시간 00:00→0:00 깨짐
 - 확인은 메모장으로만
 - git add 시 그대로 add (가공 X)


[hubroom_predictor.py 와 호환]
 - 첫 컬럼명 CRT_TM
 - 나머지 265개 컬럼명이 hubroom_predictor.py 가 기대하는 IDC 이름과 동일
 - 자동 quoting 으로 쉼표 들어간 값도 안전
================================================================
