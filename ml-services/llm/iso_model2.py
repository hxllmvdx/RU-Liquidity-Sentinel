# =========================================================
# RU LIQUIDITY STRESS INDEX
# FINAL INSTITUTIONAL VERSION
# =========================================================

import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

import matplotlib.pyplot as plt

MODULE_WEIGHTS = {
    "M1": 0.25,
    "M2": 0.20,
    "M3": 0.20,
    "M4": 0.10,
    "M5": 0.25
}

LSI_GREEN = 40
LSI_YELLOW = 70

SMOOTHING_SPAN = 3

BASE_WEIGHT = 0.7
ANOMALY_WEIGHT = 0.3


df = pd.read_csv("all_df_date.csv")
df["date"] = pd.to_datetime(df["date"])

df = (df.sort_values("date").reset_index(drop=True))

if "Unnamed: 0" in df.columns:
    df = df.drop(columns=["Unnamed: 0"])

df["Flag_Demand"] = (df["Flag_Demand"].astype(str).map({"True": 1,"False": 0,"1": 1,"0": 0,"nan": 0}).fillna(0).astype(int))

M1_COLS = [
    "mad_score_ruonia",
    "mad_score_spread",
    "flag_end_period"
]

M2_COLS = [
    "MAD_score_rate_spread",
    "MAD_score_cover",
    "Flag_Demand",
    "MAD_score_repo_volume"
]

M3_COLS = [
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
    "MAD_score_cover_m3"
]

M4_COLS = [
    "Tax_Week_Flag",
    "End_of_Month_Flag",
    "End_of_Quarter_Flag",
    "Seasonal_Factor"
]

M5_COLS = [
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "Flag_Budget_Drain",
    "Flag_Treasury_Placement_Drop"
]

ALL_COLS = (M1_COLS + M2_COLS + M4_COLS + M3_COLS+ M5_COLS)

df[ALL_COLS] = (df[ALL_COLS].replace([np.inf, -np.inf], np.nan).fillna(0))

def robust_zscore(series):
    series = pd.to_numeric(series,errors="coerce")
    series = (series.replace([np.inf, -np.inf], np.nan).fillna(0))
    median = series.median()
    mad = np.median(np.abs(series - median))

    if mad == 0 or np.isnan(mad):
        return pd.Series(0,index=series.index)
    z = ((series - median)/(1.4826 * mad))

    return z.fillna(0)

def normalize_0_100(series):

    series = (

        series

        .replace([np.inf, -np.inf], np.nan)

        .fillna(0)

    )

    s_min = series.min()
    s_max = series.max()

    if s_max - s_min == 0:

        return pd.Series(
            50,
            index=series.index
        )

    normalized = 100 * (

        (series - s_min)

        /

        (s_max - s_min)

    )

    return normalized.fillna(50)

def build_module_score(df, cols):
    zscores = []
    for col in cols:
        zscores.append(
            robust_zscore(df[col])
        )

    module_score = (

        pd.concat(
            zscores,
            axis=1
        )

        .mean(axis=1)

    )

    return normalize_0_100(module_score)

df["M1_score"] = build_module_score(df, M1_COLS)
df["M2_score"] = build_module_score(df, M2_COLS)
df["M3_score"] = build_module_score(df, M3_COLS)
df["M4_score"] = build_module_score(df, M4_COLS)
df["M5_score"] = build_module_score(df, M5_COLS)

module_cols = [
    "M1_score",
    "M2_score",
    "M3_score",
    "M4_score",
    "M5_score"
]

df[module_cols] = (

    df[module_cols]

    .replace([np.inf, -np.inf], np.nan)

    .fillna(50)

)

for col in module_cols:

    df[col] = (

        df[col]

        .ewm(span=5)

        .mean()

    )

df["base_LSI"] = (
    MODULE_WEIGHTS["M1"] * df["M1_score"]
    +
    MODULE_WEIGHTS["M2"] * df["M2_score"]
    +
    MODULE_WEIGHTS["M3"] * df["M3_score"]
    +
    MODULE_WEIGHTS["M5"] * df["M5_score"]
    +
    MODULE_WEIGHTS["M4"] * df["M4_score"]

)
for col in ALL_COLS:
    df[f"{col}_mean_14"] = (df[col].rolling(14, min_periods=1).mean())

    df[f"{col}_std_14"] = (

        df[col]

        .rolling(14, min_periods=1)

        .std()

        .fillna(0)

    )

    df[f"{col}_diff_7"] = (

        df[col]

        .diff(7)

        .fillna(0)

    )

EXCLUDE = [

    "date",

    "LSI",
    "LSI_STATUS",

    "base_LSI",

    "anomaly_score",
    "anomaly_score_smooth"

]

MODEL_FEATURES = [

    col

    for col in df.columns

    if col not in EXCLUDE

]

X = df[MODEL_FEATURES]

X = (

    X

    .replace([np.inf, -np.inf], np.nan)

    .fillna(0)

)

scaler = RobustScaler()

X_scaled = scaler.fit_transform(X)

iso = IsolationForest(

    n_estimators=700,

    contamination=0.01,

    random_state=42,

    n_jobs=-1

)

iso.fit(X_scaled)

df["anomaly_score"] = (
    iso.score_samples(X_scaled)
)

df["anomaly_score_smooth"] = (

    df["anomaly_score"]

    .ewm(span=SMOOTHING_SPAN)

    .mean()

)

df["IF_signal"] = normalize_0_100(

    -df["anomaly_score_smooth"]

)

df["LSI"] = (

    BASE_WEIGHT * df["base_LSI"]

    +

    ANOMALY_WEIGHT * df["IF_signal"]

)

df["LSI"] = (

    np.power(
        df["LSI"] / 100,
        0.75
    )

    * 100

)

df["LSI"] = (

    0.8 * df["LSI"]

    +

    0.2 *

    df["LSI"]

    .shift(1)

    .bfill()

)

df["LSI"] = (

    df["LSI"]

    .clip(0, 100)

)

def get_status(x):

    if x < LSI_GREEN:
        return "GREEN"

    elif x < LSI_YELLOW:
        return "YELLOW"

    return "RED"

df["LSI_STATUS"] = (
    df["LSI"].apply(get_status)
)

df["stress_persistence"] = (

    (df["LSI"] > 70)

    .rolling(14, min_periods=1)

    .sum()

)

df["stress_velocity"] = (

    df["LSI"]

    .diff(7)

    .fillna(0)

)

df["stress_volatility"] = (

    df["LSI"]

    .rolling(14, min_periods=1)

    .std()

    .fillna(0)

)

df["module_dispersion"] = (

    df[module_cols]

    .std(axis=1)

)

df["M1_contribution"] = (
    MODULE_WEIGHTS["M1"]
    * df["M1_score"]
)

df["M2_contribution"] = (
    MODULE_WEIGHTS["M2"]
    * df["M2_score"]
)

df["M3_contribution"] = (
    MODULE_WEIGHTS["M3"]
    * df["M3_score"]
)

df["M4_contribution"] = (
    MODULE_WEIGHTS["M4"]
    * df["M4_score"]
)

df["M5_contribution"] = (
    MODULE_WEIGHTS["M5"]
    * df["M5_score"]
)

print("\n==============================")
print("LSI SUMMARY")
print("==============================")

print(df["LSI"].describe())

print("\n==============================")
print("STATUS COUNTS")
print("==============================")

print(df["LSI_STATUS"].value_counts())

latest = df.iloc[-1]

print("\n==============================")
print("CURRENT MARKET STATE")
print("==============================")

print(f"Date: {latest['date']}")
print(f"LSI: {latest['LSI']:.2f}")
print(f"Status: {latest['LSI_STATUS']}")

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
            "stress_persistence",
            "stress_velocity"
        ]
    ]

    .head(20)

)

plt.figure(figsize=(20, 7))

plt.plot(
    df["date"],
    df["LSI"],
    linewidth=2
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

df.to_csv(
    "dashboard_payload.csv",
    index=False
)

print("\nSaved: dashboard_payload.csv")

from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score
)

# Isolation Forest:
# -1 = anomaly
#  1 = normal

df["if_label"] = iso.predict(X_scaled)

# convert to binary

df["if_label_binary"] = (
    df["if_label"]
    .map({
        -1: 1,
         1: 0
    })
)

anomaly_rate = (
    df["if_label_binary"]
    .mean()
)

print("\n==============================")
print("1. ANOMALY RATE")
print("==============================")

print(f"{anomaly_rate:.4f}")

lsi_volatility = (
    df["LSI"]
    .std()
)

print("\n==============================")
print("2. LSI VOLATILITY")
print("==============================")

print(f"{lsi_volatility:.4f}")

regime_changes = (

    df["LSI_STATUS"]

    !=

    df["LSI_STATUS"].shift(1)

).sum()

avg_regime_duration = (

    len(df)

    /

    regime_changes

)

print("\n==============================")
print("3. REGIME PERSISTENCE")
print("==============================")

print(f"Regime Changes: {regime_changes}")
print(f"Avg Regime Duration: {avg_regime_duration:.2f} days")

try:

    silhouette = silhouette_score(
        X_scaled,
        df["if_label_binary"]
    )

    print("\n==============================")
    print("4. SILHOUETTE SCORE")
    print("==============================")

    print(f"{silhouette:.4f}")

except:

    print("\nSilhouette score failed")

try:

    db_index = davies_bouldin_score(
        X_scaled,
        df["if_label_binary"]
    )

    print("\n==============================")
    print("5. DAVIES-BOULDIN INDEX")
    print("==============================")

    print(f"{db_index:.4f}")

except:

    print("\nDavies-Bouldin failed")

try:

    ch_score = calinski_harabasz_score(
        X_scaled,
        df["if_label_binary"]
    )

    print("\n==============================")
    print("6. CALINSKI-HARABASZ SCORE")
    print("==============================")

    print(f"{ch_score:.4f}")

except:

    print("\nCalinski-Harabasz failed")

stress_smoothness = (

    df["LSI"]

    .diff()

    .abs()

    .mean()

)

print("\n==============================")
print("7. STRESS SMOOTHNESS")
print("==============================")

print(f"{stress_smoothness:.4f}")

red_share = (

    (df["LSI_STATUS"] == "RED")

    .mean()

)

print("\n==============================")
print("8. RED REGIME SHARE")
print("==============================")

print(f"{red_share:.4f}")

yellow_share = (

    (df["LSI_STATUS"] == "YELLOW")

    .mean()

)

print("\n==============================")
print("9. YELLOW REGIME SHARE")
print("==============================")

print(f"{yellow_share:.4f}")

feature_dispersion = (

    df[module_cols]

    .std(axis=1)

    .mean()

)

print("\n==============================")
print("10. FEATURE DISPERSION")
print("==============================")

print(f"{feature_dispersion:.4f}")