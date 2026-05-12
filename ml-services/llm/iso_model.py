# =========================================================
# LIQUIDITY STRESS INDEX
# PURE ISOLATION FOREST VERSION
# =========================================================

import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score
)

import matplotlib.pyplot as plt
import seaborn as sns

# =========================================================
# 1. LOAD DATA
# =========================================================

df = pd.read_csv("all_df_date.csv")

# =========================================================
# 2. DATE
# =========================================================

df["date"] = pd.to_datetime(df["date"])

df = (
    df
    .sort_values("date")
    .reset_index(drop=True)
)

# =========================================================
# 3. FIX BROKEN COLUMN
# =========================================================

df["Flag_Perespros"] = (
    df["Flag_PeresprosMAD_score_CBR"]
)

df["MAD_score_CBR"] = 0

df = df.drop(
    columns=["Flag_PeresprosMAD_score_CBR"]
)

# =========================================================
# 4. REMOVE TRASH COLUMN
# =========================================================

if "Unnamed: 0" in df.columns:

    df = df.drop(
        columns=["Unnamed: 0"]
    )

# =========================================================
# 5. FIX OBJECT COLUMNS
# =========================================================

df["Flag_Demand"] = (
    df["Flag_Demand"]
    .astype(str)
    .map({
        "True": 1,
        "False": 0,
        "1": 1,
        "0": 0,
        "nan": 0
    })
    .fillna(0)
    .astype(int)
)

# =========================================================
# 6. FEATURES
# =========================================================

FEATURES = [

    # =========================
    # M1
    # =========================
    "mad_score_ruonia",
    "mad_score_spread",
    "flag_end_period",

    # =========================
    # M2
    # =========================
    "MAD_score_rate_spread",
    "MAD_score_cover",
    "Flag_Demand",
    "MAD_score_repo_volume",

    # =========================
    # M4
    # =========================
    "Tax_Week_Flag",
    "End_of_Month_Flag",
    "End_of_Quarter_Flag",
    "Seasonal_Factor",

    # =========================
    # M3
    # =========================
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
    "MAD_score_cover_m3",

    # =========================
    # M5
    # =========================
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "Flag_Budget_Drain",
    "Flag_Treasury_Placement_Drop",
]

# =========================================================
# 7. FILL NANS
# =========================================================

df[FEATURES] = (
    df[FEATURES]
    .fillna(0)
)

# =========================================================
# 8. FINAL MATRIX
# =========================================================

X = df[FEATURES]

print("\nDATA SHAPE")
print(X.shape)

# =========================================================
# 9. ISOLATION FOREST
# =========================================================

iso = IsolationForest(

    n_estimators=500,

    contamination=0.05,

    max_samples="auto",

    random_state=42,

    n_jobs=-1

)

iso.fit(X)

# =========================================================
# 10. ANOMALY SCORES
# =========================================================

df["anomaly_score"] = (
    iso.score_samples(X)
)

# =========================================================
# 11. ANOMALY LABELS
# =========================================================
# -1 = anomaly
#  1 = normal

df["iforest_label"] = (
    iso.predict(X)
)

# =========================================================
# 12. CONVERT LABELS
# =========================================================
# anomaly = 1
# normal = 0

df["stress_label"] = (
    df["iforest_label"]
    .map({
        -1: 1,
         1: 0
    })
)

# =========================================================
# 13. LSI 0-100
# =========================================================
# Чем ниже anomaly_score,
# тем выше stress

score_min = df["anomaly_score"].min()
score_max = df["anomaly_score"].max()

df["LSI"] = 100 * (
    1 - (
        (df["anomaly_score"] - score_min)
        /
        (score_max - score_min)
    )
)

# =========================================================
# 14. LSI STATUS
# =========================================================

def get_status(x):

    if x < 40:
        return "GREEN"

    elif x < 70:
        return "YELLOW"

    return "RED"

df["LSI_STATUS"] = (
    df["LSI"]
    .apply(get_status)
)

# =========================================================
# 15. BASIC METRICS
# =========================================================

print("\n==============================")
print("ANOMALY DISTRIBUTION")
print("==============================")

print(
    df["stress_label"]
    .value_counts()
)

# =========================================================
# 16. FEATURE VARIANCE
# =========================================================

variance_df = pd.DataFrame({

    "feature": FEATURES,

    "variance": X.var().values

})

variance_df = (
    variance_df
    .sort_values(
        "variance",
        ascending=False
    )
)

print("\n==============================")
print("FEATURE VARIANCE")
print("==============================")

print(variance_df)

# =========================================================
# 17. FEATURE CORRELATION
# =========================================================

corr = X.corr()

plt.figure(figsize=(14,10))

sns.heatmap(
    corr,
    cmap="coolwarm",
    center=0
)

plt.title("Feature Correlation Matrix")

plt.tight_layout()
plt.show()

# =========================================================
# 18. TOP STRESS PERIODS
# =========================================================

top_stress = (
    df
    .sort_values(
        "LSI",
        ascending=False
    )
)

print("\n==============================")
print("TOP STRESS PERIODS")
print("==============================")

print(
    top_stress[
        [
            "date",
            "LSI",
            "LSI_STATUS",
            "anomaly_score"
        ]
    ].head(30)
)

# =========================================================
# 19. SUMMARY STATS
# =========================================================

print("\n==============================")
print("LSI SUMMARY")
print("==============================")

print(
    df["LSI"]
    .describe()
)

# =========================================================
# 20. STRESS COUNTS
# =========================================================

print("\n==============================")
print("STATUS COUNTS")
print("==============================")

print(
    df["LSI_STATUS"]
    .value_counts()
)

# =========================================================
# 21. LSI TIMESERIES
# =========================================================

plt.figure(figsize=(18,6))

plt.plot(
    df["date"],
    df["LSI"]
)

plt.axhline(
    40,
    linestyle="--"
)

plt.axhline(
    70,
    linestyle="--"
)

plt.title("Liquidity Stress Index")

plt.xlabel("Date")

plt.ylabel("LSI")

plt.tight_layout()

plt.show()

# =========================================================
# 22. ANOMALY SCORE DISTRIBUTION
# =========================================================

plt.figure(figsize=(10,6))

plt.hist(
    df["anomaly_score"],
    bins=50
)

plt.title("Isolation Forest Anomaly Score Distribution")

plt.xlabel("Anomaly Score")

plt.ylabel("Frequency")

plt.tight_layout()

plt.show()

# =========================================================
# 23. LSI DISTRIBUTION
# =========================================================

plt.figure(figsize=(10,6))

plt.hist(
    df["LSI"],
    bins=50
)

plt.title("LSI Distribution")

plt.xlabel("LSI")

plt.ylabel("Frequency")

plt.tight_layout()

plt.show()

# =========================================================
# 24. FEATURE IMPORTANCE PROXY
# =========================================================
# Используем среднее абсолютное значение
# как proxy importance

importance_proxy = pd.DataFrame({

    "feature": FEATURES,

    "importance_proxy": np.abs(X).mean().values

})

importance_proxy = (
    importance_proxy
    .sort_values(
        "importance_proxy",
        ascending=False
    )
)

print("\n==============================")
print("FEATURE IMPORTANCE PROXY")
print("==============================")

print(importance_proxy)

# =========================================================
# 25. CURRENT MARKET STATE
# =========================================================

latest = df.iloc[-1]

print("\n==============================")
print("CURRENT MARKET STATE")
print("==============================")

print(f"Date: {latest['date']}")
print(f"LSI: {latest['LSI']:.2f}")
print(f"Status: {latest['LSI_STATUS']}")
print(f"Anomaly Score: {latest['anomaly_score']:.4f}")

# =========================================================
# 26. SAVE RESULTS
# =========================================================

df.to_csv(
    "lsi_iforest_results.csv",
    index=False
)

print("\nSaved: lsi_iforest_results.csv")