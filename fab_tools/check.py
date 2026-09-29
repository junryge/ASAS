import sys, pandas as pd
folder, start, end = sys.argv[1:4]
d = pd.read_csv(f"{folder}/FAB_scores.csv.gz", parse_dates=["time"])
d = d[(d.time >= start) & (d.time < end)]

n = d.groupby("FAB").size().rename("분수")
grade = d.groupby(["FAB", "등급.FAB반송위험"]).size().unstack(fill_value=0).add_prefix("등급_")
valid = d.groupby("FAB")["품질.필수입력유효"].mean().round(3).rename("필수입력유효비율")
obs = d.groupby("FAB")["품질.파생값관측률"].mean().round(1).rename("파생값관측률평균")
out = pd.concat([n, valid, obs, grade], axis=1)

print("분 수(기대: 날짜수x1440):", n.to_dict())
print(out.to_string())
path = f"{folder}/데이터점검.csv"
out.to_csv(path, encoding="utf-8-sig")
print("\n저장:", path)
