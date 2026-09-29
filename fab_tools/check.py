import sys, pandas as pd
folder, start, end = sys.argv[1:4]
d = pd.read_csv(f"{folder}/FAB_scores.csv.gz", parse_dates=["time"])
d = d[(d.time >= start) & (d.time < end)]
print("분 수(기대: 날짜수x1440):", d.groupby("FAB").size().to_dict())
print("\n등급 분포:")
print(d.groupby(["FAB","등급.FAB반송위험"]).size().unstack(fill_value=0))
print("\n필수입력 유효 비율:")
print(d.groupby("FAB")["품질.필수입력유효"].mean().round(3))
print("\n파생값 관측률 평균:")
print(d.groupby("FAB")["품질.파생값관측률"].mean().round(1))
