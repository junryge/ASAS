#!/usr/bin/env bash
# hubroom_배치 — 원본 61개(4/1~5/31)를 hubroom_predictor 로 일괄 처리
# =================================================================
# 결과: predict_tobe/{날짜}_발동이벤트.csv (매분 unified_risk_score) + _사건단위.csv
# 사용: bash hubroom_배치.sh <원본폴더> <predict_tobe출력폴더> <hubroom_predictor.py경로>
set -e
RAW="${1:-./RAW}"
OUT="${2:-./predict_tobe}"
PRED="${3:-../hubroom_predictor.py}"

mkdir -p "$OUT"
shopt -s nullglob
files=("$RAW"/M16A_HUBROOM_PR_202604*.CSV "$RAW"/M16A_HUBROOM_PR_202605*.CSV \
       "$RAW"/M16A_HUBROOM_PR_202604*.csv "$RAW"/M16A_HUBROOM_PR_202605*.csv)
echo "대상 원본 ${#files[@]}개 → $OUT"
i=0
for f in "${files[@]}"; do
  i=$((i+1))
  echo "[$i/${#files[@]}] $(basename "$f")"
  python3 "$PRED" "$f" -o "$OUT"
done
echo "완료. 생성 파일:"
ls "$OUT"/*_발동이벤트.csv 2>/dev/null | wc -l
