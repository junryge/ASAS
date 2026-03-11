# -*- coding: utf-8 -*-
"""
Demos - pandas 데이터 분석 데모
M14 공정 평가 CSV 파일을 읽고 기본 통계, 시계열 추이, 상관관계, 병목 탐색, 군집 분석을 수행합니다.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# ==============================================================
# 1. CSV 파일 읽기
# ==============================================================
# 파일명은 실제 업로드된 파일명과 동일하게 지정합니다.
csv_path = "M14_20260115_평가.CSV"

# 인코딩이 UTF-8이라고 가정하고, 첫 번째 행을 헤더로 사용합니다.
df = pd.read_csv(csv_path, encoding="utf-8")

# ==============================================================
# 2. 전체 행/열 확인 (데이터가 정상적으로 로드됐는지 점검)
# ==============================================================
print("데이터 차원 (행, 열) :", df.shape)
print("\n컬럼 리스트 (앞 20개만 표시)")
print(df.columns[:20].tolist())

# ==============================================================
# 3. 결측치(NA) 확인
# ==============================================================
na_counts = df.isna().sum()
print("\n결측치 개수 (0보다 큰 컬럼만 표시)")
print(na_counts[na_counts > 0])

# ==============================================================
# 4. 기본 통계 요약 (수치형 컬럼에 한함)
# ==============================================================
# pandas의 describe()는 count, mean, std, min, 25%, 50%, 75%, max을 반환합니다.
numeric_desc = df.describe().T  # 전치(transpose)해서 컬럼이 행이 되게 정렬
print("\n수치형 컬럼 통계 요약 (앞 10개만 표시)")
print(numeric_desc.head(10))

# ==============================================================
# 5. 전체 통계 요약을 파일로 저장
# ==============================================================
numeric_desc.to_csv("M14_통계요약.csv", encoding="utf-8")
print("\n통계 요약이 'M14_통계요약.csv'로 저장되었습니다.")

# ==============================================================
# 6. datetime 변환 및 인덱스 설정
# ==============================================================
df["CURRTIME"] = pd.to_datetime(df["CURRTIME"], format="%Y%m%d%H%M")
df = df.set_index("CURRTIME")

# 숫자형 컬럼 강제 변환 (문자형이 섞여 있을 경우 대비)
num_cols = df.select_dtypes(include=["float64", "int64"]).columns
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

# ==============================================================
# 7. 시계열 추이 (5분 평균 리샘플링)
# ==============================================================
df_resampled = df.resample("5T").mean()

fig, ax1 = plt.subplots(figsize=(12, 5))

ax1.plot(df_resampled.index, df_resampled["TOTALCNT"],
         label="TOTALCNT", color="steelblue")
ax1.set_ylabel("TOTALCNT", color="steelblue")
ax1.tick_params(axis="y", labelcolor="steelblue")

ax2 = ax1.twinx()
ax2.plot(df_resampled.index, df_resampled["M14.QUE.OHT.OHTUTIL"],
         label="OHT Util", color="darkorange")
ax2.set_ylabel("OHT Util (%)", color="darkorange")
ax2.tick_params(axis="y", labelcolor="darkorange")

plt.title("시간대별 TOTALCNT & OHT Util (5분 평균)")
fig.legend(loc="upper left")
plt.tight_layout()
plt.savefig("M14_시계열추이.png", dpi=150)
plt.show()

# ==============================================================
# 8. 상관관계 히트맵 및 주요 변수 추출
# ==============================================================

# 상관관계 분석을 위한 주요 변수 선택
corr_variables = [
    'TOTALCNT',
    'M14.QUE.ALL.CURRENTQCNT',
    'M14.QUE.OHT.OHTUTIL',
    'M14.QUE.LOAD.AVGLOADTIME',
    'M14.QUE.ALL.TRANSPORT4MINOVERCNT',
    'M14.QUE.ALL.TRANSPORT4MINOVERRATIO',
    'M14B.QUE.ALL.CURRENTQCNT',
    'M14B.QUE.OHT.OHTUTIL',
    'M14.QUE.SENDFAB.VERTICALQUEUECOUNT',
    'M14.QUE.CNV.TOTALCNVCURRENTQCNT',
]

corr_matrix = df[corr_variables].corr()

# 상관관계 히트맵 (하삼각 마스크 적용)
plt.figure(figsize=(14, 12))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdBu_r', center=0,
            fmt='.3f', square=True, linewidths=0.5,
            xticklabels=[v.split('.')[-1] if '.' in v else v for v in corr_variables],
            yticklabels=[v.split('.')[-1] if '.' in v else v for v in corr_variables])
plt.title("주요 변수 간 상관관계 행렬 (하삼각)")
plt.tight_layout()
plt.savefig("M14_상관관계.png", dpi=150)
plt.show()

# TOTALCNT와 상관이 높은 변수 출력
top_corr = corr_matrix["TOTALCNT"].abs().sort_values(ascending=False)
print("\nTOTALCNT와 가장 높은 상관을 보이는 변수")
print(top_corr[1:])  # 자기 자신 제외

# ==============================================================
# 9. 병목 탐색 - OHT Util vs. Transport Overrun
# ==============================================================
plt.figure(figsize=(7, 5))
sns.regplot(x="M14.QUE.OHT.OHTUTIL",
            y="M14.QUE.ALL.TRANSPORT4MINOVERCNT",
            data=df,
            scatter_kws={"alpha": 0.5},
            line_kws={"color": "red"})
plt.xlabel("OHT Util (%)")
plt.ylabel("4분 초과 운송 건수")
plt.title("OHT Util vs. 4분 초과 운송 건수")
plt.tight_layout()
plt.savefig("M14_병목분석.png", dpi=150)
plt.show()

# 상관계수
corr_oht_over = np.corrcoef(
    df["M14.QUE.OHT.OHTUTIL"].dropna(),
    df["M14.QUE.ALL.TRANSPORT4MINOVERCNT"].dropna()
)[0, 1]
print(f"\nOHT Util <-> Transport Overrun 상관계수 = {corr_oht_over:.3f}")

# ==============================================================
# 10. 군집 분석 - 시스템 운영 상태 구분 (K-means, k=3)
# ==============================================================
# 분석에 사용할 변수 (핵심 KPI)
features = [
    "TOTALCNT",
    "M14.QUE.ALL.CURRENTQCNT",
    "M14.QUE.OHT.OHTUTIL",
    "M14.QUE.ALL.TRANSPORT4MINOVERCNT",
    "M14.QUE.LOAD.AVGLOADTIME",
]

X = df[features].dropna()

# 표준화
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# K-means (k=3) - 3가지 상태(저부하/정상/과부하) 가정
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
clusters = kmeans.fit_predict(X_scaled)

# 결과를 원본 DF에 저장
df["운영_상태"] = np.nan
df.loc[X.index, "운영_상태"] = clusters

# 각 군집 평균값 확인
cluster_summary = df.groupby("운영_상태")[features].mean()
print("\n--- 군집별 평균 KPI ---")
print(cluster_summary)

# 군집 시각화
plt.figure(figsize=(10, 5))
sns.scatterplot(x="TOTALCNT", y="M14.QUE.OHT.OHTUTIL",
                hue="운영_상태", data=df, palette="Set2", alpha=0.7)
plt.title("TOTALCNT vs. OHT Util - 군집(운영 상태) 구분")
plt.tight_layout()
plt.savefig("M14_군집분석.png", dpi=150)
plt.show()

# ==============================================================
# 11. 특정 서브셋(M14 구역) 평균/표준편차 비교
# ==============================================================
m14_cols = [c for c in df.columns if c.startswith("M14")]
m14_stats = df[m14_cols].describe().loc[["mean", "std"]]
print("\n--- M14 구역 변수 평균/표준편차 ---")
print(m14_stats)

print("\n분석 완료!")
