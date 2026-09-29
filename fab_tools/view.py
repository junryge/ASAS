import sys, pandas as pd
folder, start, end = sys.argv[1:4]
d = pd.read_csv(f"{folder}/FAB_scores.csv.gz", parse_dates=["time"])
d = d[(d.time >= start) & (d.time < end)]

# 1) FAB별 요약
s = d.groupby("FAB")["점수.FAB반송위험"].agg(
    분수="count", 중앙값="median", 최고점="max",
    경고분=lambda z: int(z.ge(40).sum()), 위험분=lambda z: int(z.ge(70).sum()))
print(s.to_string())
s.to_csv(f"{folder}/평가구간_요약.csv", encoding="utf-8-sig")

# 2) 40점 이상 경보 분
a = d[d["점수.FAB반송위험"] >= 40]
print(a[["time", "FAB", "점수.FAB반송위험", "설명.주요위험"]].to_string())
a.to_csv(f"{folder}/경보_평가구간.csv", index=False, encoding="utf-8-sig")

# 3) 평가구간 전체 분 단위 점수 (핵심 컬럼 + 룰별 기여)
keep = ["time", "FAB", "점수.FAB반송위험", "등급.FAB반송위험", "점수.일반Sorter대기",
        "등급.일반Sorter대기", "설명.주요위험", "품질.필수입력유효", "품질.파생값관측률"]
keep += [c for c in d.columns if c.startswith("룰.")]
d[[c for c in keep if c in d.columns]].to_csv(
    f"{folder}/평가구간_전체점수.csv", index=False, encoding="utf-8-sig")

print(f"\n저장 위치: {folder}/ → 평가구간_요약.csv, 경보_평가구간.csv, 평가구간_전체점수.csv")
