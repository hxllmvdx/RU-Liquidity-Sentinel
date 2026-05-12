from __future__ import annotations

from pathlib import Path

import pandas as pd

from normalization.mad_normalizer import rolling_mad_score


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _latest_file(pattern: str) -> Path | None:
    files = sorted(_repo_root().glob(pattern))
    return files[-1] if files else None


def _read_ruonia() -> pd.DataFrame:
    path = _latest_file("data/raw/cbr/ruonia/*.csv")
    if path is None:
        return pd.DataFrame(columns=["date", "ruonia"])
    df = pd.read_csv(path)
    date_col = "observation_date" if "observation_date" in df.columns else "date"
    value_col = "rate_percent" if "rate_percent" in df.columns else "metric_value"
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[date_col]).copy()
    return (
        df.groupby(df[date_col].dt.normalize(), as_index=False)[value_col]
        .mean()
        .rename(columns={date_col: "date", value_col: "ruonia"})
    )


def _read_reserves() -> pd.DataFrame:
    path = _latest_file("data/raw/cbr/reserves/*.csv")
    if path is None:
        return pd.DataFrame(columns=["date", "cbr_reserves_actual", "cbr_reserves_required"])
    df = pd.read_csv(path)
    date_col = "observation_date" if "observation_date" in df.columns else "date"
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    for col in ["actual_avg_balances", "required_reserves"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[date_col]).copy()
    grouped = df.groupby(df[date_col].dt.normalize(), as_index=False).agg(
        actual_avg_balances=("actual_avg_balances", "mean"),
        required_reserves=("required_reserves", "mean"),
    )
    return grouped.rename(
        columns={
            date_col: "date",
            "actual_avg_balances": "cbr_reserves_actual",
            "required_reserves": "cbr_reserves_required",
        }
    )


def build_m1_daily_dataset(
    date_from: str = "2021-01-01",
    date_to: str | None = None,
    persist_csv: bool = True,
) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    calendar = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})
    reserves = _read_reserves()
    ruonia = _read_ruonia()

    df = calendar.merge(reserves, on="date", how="left")
    df = df.merge(ruonia, on="date", how="left")
    if "cbr_reserves_actual" in df.columns:
        df["cbr_reserves_actual"] = df["cbr_reserves_actual"].ffill()
    if "cbr_reserves_required" in df.columns:
        df["cbr_reserves_required"] = df["cbr_reserves_required"].ffill()
    if "ruonia" in df.columns:
        df["ruonia"] = df["ruonia"].ffill(limit=5)

    df["spread"] = df["cbr_reserves_actual"] - df["cbr_reserves_required"]
    df["MAD_score_spread"] = rolling_mad_score(df["spread"], window="365D").fillna(0.0)
    df["MAD_score_RUONIA"] = rolling_mad_score(df["ruonia"], window="365D").fillna(0.0)
    days_to_month_end = ((df["date"] + pd.offsets.MonthEnd(0)) - df["date"]).dt.days
    df["Flag_EndOfPeriod"] = days_to_month_end.le(3).astype(int)

    available = int(df[["cbr_reserves_actual", "cbr_reserves_required", "ruonia"]].notna().any(axis=1).sum())
    if available == 0:
        status = "missing"
    elif available < len(df) * 0.5:
        status = "fallback"
    else:
        status = "ok"
    df["M1_status"] = status
    df["date"] = df["date"].dt.date

    out = _repo_root() / "data" / "processed" / "m1" / "m1_daily_signals.csv"
    if persist_csv:
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    return df
