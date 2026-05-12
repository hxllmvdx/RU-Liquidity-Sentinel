import pandas as pd
import numpy as np
import joblib

iso = joblib.load("iso_model.pkl")

scaler = joblib.load("scaler.pkl")

MODEL_FEATURES = joblib.load("features.pkl")

SMOOTHING_SPAN = 3

BASE_WEIGHT = 0.6

ANOMALY_WEIGHT = 0.4

MODULE_WEIGHTS = {
    "M1": 0.30,
    "M2": 0.25,
    "M3": 0.20,
    "M4": 0.15,
    "M5": 0.10
}

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

    normalized = (
        100 *
        (
            (series - s_min)
            /
            (s_max - s_min)
        )
    )

    return normalized.fillna(50)

# =========================================================
# PREDICT FUNCTION
# =========================================================

def predict_lsi(input_df):

    input_df = (
        input_df[MODEL_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    X_scaled = scaler.transform(input_df)

    anomaly_score = (
        iso.score_samples(X_scaled)
    )

    anomaly_score = pd.Series(
        anomaly_score
    )

    anomaly_score_smooth = (
        anomaly_score
        .ewm(span=SMOOTHING_SPAN)
        .mean()
    )

    IF_signal = normalize_0_100(
        -anomaly_score_smooth
    )

    lsi = IF_signal.clip(0, 100)

    return lsi