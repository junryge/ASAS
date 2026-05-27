# COL_SPLIT_40 — 월×영역 40분할 수집

총 40개 SQL (8 영역 × 5 개월) + 머지 스크립트.

## 파일 구성
| 영역 | 컬럼 | 월별 SQL 파일명 |
|---|---|---|
| M16HUB | 110 | COL_M16HUB_{ym}_CLOB.sql (5개) |
| M14 | 41 | COL_M14_{ym}_CLOB.sql (5개) |
| M14B | 42 | COL_M14B_{ym}_CLOB.sql (5개) |
| M16A | 37 | COL_M16A_{ym}_CLOB.sql (5개) |
| M16B | 16 | COL_M16B_{ym}_CLOB.sql (5개) |
| M16 | 11 | COL_M16_{ym}_CLOB.sql (5개) |
| M16_PKT | 4 | COL_M16_PKT_{ym}_CLOB.sql (5개) |
| M16_WT | 4 | COL_M16_WT_{ym}_CLOB.sql (5개) |

## 실행 (예: 1월)
```sql
SQL> @COL_M16_PKT_202601_CLOB.sql    -- 가장 작음
SQL> @COL_M16_WT_202601_CLOB.sql
SQL> @COL_M16_202601_CLOB.sql
SQL> @COL_M16B_202601_CLOB.sql
SQL> @COL_M16A_202601_CLOB.sql
SQL> @COL_M14_202601_CLOB.sql
SQL> @COL_M14B_202601_CLOB.sql
SQL> @COL_M16HUB_202601_CLOB.sql     -- 가장 큼
```

5개월 × 8영역 = 40번 실행.

## 출력
각 SQL → `D:\data\IDC_{영역}_{YYYYMM}.csv` (총 40개)

## 머지
```bash
python3 merge_split40.py [입력디렉토리=D:/data] [출력=ALL_MERGED.csv]
```
→ 시간(CRT_TM) 기준으로 8영역 가로 join + 5개월 세로 concat
→ 최종 1개 CSV 생성 (146일 × 1440분 × 265컬럼)
