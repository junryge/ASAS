---
name: data-analysis
description: Analyze data, create visualizations, and compute statistics. TRIGGER when the user asks to analyze data, create charts, compute statistics, explore a dataset, or generate visualizations.
---
# Data Analysis

Analyze datasets, compute statistics, and create visualizations to extract insights.

## Steps

1. **Load the data** - Read the dataset (CSV, JSON, database, API). Inspect the first few rows to understand structure, types, and quality.
2. **Assess data quality** - Check for:
   - Missing values and their distribution
   - Data types (numeric, categorical, datetime)
   - Outliers and anomalies
   - Duplicate rows
3. **Compute descriptive statistics** - Calculate relevant metrics: mean, median, standard deviation, percentiles, correlations.
4. **Explore relationships** - Identify patterns, trends, groupings, and correlations in the data.
5. **Visualize findings** - Create appropriate charts and plots.
6. **Summarize insights** - Present key findings in clear, non-technical language.

## Quick Start Examples

### Python (pandas + matplotlib)
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load and inspect
df = pd.read_csv("data.csv")
print(df.shape)
print(df.dtypes)
print(df.describe())
print(df.isnull().sum())

# Group and aggregate
summary = df.groupby("category").agg(
    count=("id", "count"),
    avg_value=("value", "mean"),
    total=("value", "sum")
).sort_values("total", ascending=False)

# Visualize
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

summary["total"].plot(kind="bar", ax=axes[0], title="Total by Category")
axes[0].set_ylabel("Total Value")

df["value"].hist(bins=30, ax=axes[1], title="Value Distribution")
axes[1].set_xlabel("Value")

plt.tight_layout()
plt.savefig("analysis.png", dpi=150)
plt.show()
```

### Time Series Analysis
```python
df["date"] = pd.to_datetime(df["date"])
daily = df.resample("D", on="date")["value"].sum()

# Rolling average
daily.rolling(7).mean().plot(title="7-Day Rolling Average")
plt.savefig("trend.png", dpi=150)
```

### Correlation Analysis
```python
import seaborn as sns

corr = df.select_dtypes(include="number").corr()
sns.heatmap(corr, annot=True, cmap="coolwarm", center=0)
plt.title("Correlation Matrix")
plt.tight_layout()
plt.savefig("correlations.png", dpi=150)
```

## Visualization Selection Guide

| Data Type | Chart Type |
|---|---|
| Distribution of one variable | Histogram, box plot |
| Comparison across categories | Bar chart, grouped bar |
| Trend over time | Line chart, area chart |
| Relationship between two variables | Scatter plot |
| Proportions of a whole | Pie chart (use sparingly), stacked bar |
| Correlation matrix | Heatmap |
| Geographic data | Choropleth map |

## Rules

- Always inspect the data before analysis -- never assume structure or quality
- Handle missing values explicitly (drop, fill, or flag -- explain the choice)
- Use appropriate statistical methods (do not use mean for skewed distributions; use median)
- Label all chart axes, include titles, and use readable formatting
- Save visualizations to files so the user can view them
- State assumptions and limitations of the analysis
- For large datasets, work with samples first, then scale to the full dataset
- Present numbers with appropriate precision (do not report 12 decimal places)
