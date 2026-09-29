import sys, pandas as pd
folder, start, end = sys.argv[1:4]
d = pd.read_csv(f"{folder}/FAB_scores.csv.gz", parse_dates=["time"])
d = d[(d.time >= start) & (d.time < end)]
print(d.groupby("FAB")["점수.FAB반송위험"].agg(["count","median","max"]))
a = d[d["점수.FAB반송위험"] >= 40]
print(a[["time","FAB","점수.FAB반송위험","설명.주요위험"]].to_string())
a.to_csv(f"{folder}/경보_평가구간.csv", index=False, encoding="utf-8-sig")
