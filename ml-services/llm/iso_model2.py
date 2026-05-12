import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import matplotlib.pyplot as plt
import joblib
MODULE_WEIGHTS = {
    "M1": 0.30,
    "M2": 0.25,
    "M3": 0.20,
    "M4": 0.15,
    "M5": 0.10
}

LSI_GREEN = 40
LSI_YELLOW = 70
SMOOTHING_SPAN = 3
BASE_WEIGHT = 0.6
ANOMALY_WEIGHT = 0.4

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
    series = (series.replace([np.inf, -np.inf], np.nan).fillna(0))
    s_min = series.min()
    s_max = series.max()
    if s_max - s_min == 0:
        return pd.Series(50,index=series.index)

    normalized = 100 * ((series - s_min)/(s_max - s_min))
    return normalized.fillna(50)

def build_module_score(df, cols):
    zscores = []
    for col in cols:
        zscores.append(robust_zscore(df[col]))

    module_score = (
        pd.concat(zscores,axis=1).mean(axis=1))

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

    df[module_cols].replace([np.inf, -np.inf], np.nan).fillna(50))

for col in module_cols:
    df[col] = (df[col].ewm(span=5).mean())

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
    df[f"{col}_std_14"] = (df[col].rolling(14, min_periods=1).std().fillna(0))
    df[f"{col}_diff_7"] = (df[col].diff(7).fillna(0))

EXCLUDE = [
    "date",
    "LSI",
    "LSI_STATUS",
    "base_LSI",
    "anomaly_score",
    "anomaly_score_smooth"
]

MODEL_FEATURES = [col for col in df.columns if col not in EXCLUDE]

X = df[MODEL_FEATURES]

X = (X.replace([np.inf, -np.inf], np.nan).fillna(0))

scaler = RobustScaler()
X_scaled = scaler.fit_transform(X)
iso = IsolationForest(
    n_estimators=700,
    contamination=0.01,
    random_state=42,
    n_jobs=-1
)

iso.fit(X_scaled)
joblib.dump(iso,"iso_model.pkl")
joblib.dump(scaler,"scaler.pkl")
joblib.dump(MODEL_FEATURES,"features.pkl")