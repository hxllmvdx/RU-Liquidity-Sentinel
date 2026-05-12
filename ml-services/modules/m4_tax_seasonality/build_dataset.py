from __future__ import annotations

from pathlib import Path

import pandas as pd


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_csv(path: Path, cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date"] + cols)
    df = pd.read_csv(path)
    if "date" not in df.columns:
        return pd.DataFrame(columns=["date"] + cols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    keep = ["date"] + [c for c in cols if c in df.columns]
    return df[keep]


def _read_tax_events() -> pd.Series:
    files = sorted(_repo_root().glob("data/raw/nalog/calendar/*.csv"))
    if not files:
        return pd.Series(dtype="datetime64[ns]")
    df = pd.read_csv(files[-1])
    if "date" not in df.columns:
        return pd.Series(dtype="datetime64[ns]")
    kind_col = "day_type" if "day_type" in df.columns else "metric_name"
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if kind_col in df.columns:
        event_mask = df[kind_col].astype(str).str.contains("event|tax_event", case=False, na=False)
        dates = df.loc[event_mask, "date"].dropna()
    else:
        dates = df["date"].dropna()
    return dates.drop_duplicates()


def build_m4_daily_dataset(
    m1_daily: pd.DataFrame,
    m2_daily: pd.DataFrame,
    m5_daily: pd.DataFrame,
    date_from: str = "2021-01-01",
    date_to: str | None = None,
    persist_csv: bool = True,
) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    df = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})

    event_dates = _read_tax_events()
    if not event_dates.empty:
        marked: set[pd.Timestamp] = set()
        for event_date in event_dates:
            for ts in pd.date_range(event_date - pd.Timedelta(days=1), event_date + pd.Timedelta(days=1), freq="D"):
                marked.add(pd.Timestamp(ts).normalize())
        df["Tax_Week_Flag"] = df["date"].isin(sorted(marked)).astype(int)
        calendar_status = "ok"
    else:
        df["Tax_Week_Flag"] = 0
        calendar_status = "fallback"

    df["End_of_Month_Flag"] = (((df["date"] + pd.offsets.MonthEnd(0)) - df["date"]).dt.days < 3).astype(int)
    df["End_of_Quarter_Flag"] = (((df["date"] + pd.offsets.QuarterEnd(0)) - df["date"]).dt.days < 3).astype(int)

    m1 = m1_daily.copy()
    m2 = m2_daily.copy()
    m5 = m5_daily.copy()
    for frame in [m1, m2, m5]:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    merge_cols = ["date"]
    for frame, cols in [
        (m1, ["MAD_score_RUONIA", "MAD_score_spread"]),
        (m2, ["MAD_score_rate_spread", "MAD_score_cover", "MAD_score_repo_volume"]),
        (m5, ["MAD_score_CBR", "MAD_score_Roskazna"]),
    ]:
        existing = ["date"] + [c for c in cols if c in frame.columns]
        df = df.merge(frame[existing], on="date", how="left")
        merge_cols.extend([c for c in cols if c in frame.columns])

    df["day_type"] = (
        df["Tax_Week_Flag"].astype(str)
        + df["End_of_Month_Flag"].astype(str)
        + df["End_of_Quarter_Flag"].astype(str)
    )
    mad_cols = [c for c in merge_cols if c != "date"]
    if mad_cols:
        avg_by_type = df.groupby("day_type")[mad_cols].mean(numeric_only=True)
        tax_stress_by_type = avg_by_type.mean(axis=1).fillna(0.0)
        max_stress = float(tax_stress_by_type.max()) if not tax_stress_by_type.empty else 0.0
        alpha = 0.4 / max_stress if max_stress > 0 else 0.0
        seasonal_by_type = (1 + alpha * tax_stress_by_type).clip(1.0, 1.4)
        seasonal_by_type.loc["000"] = 1.0
        df["Seasonal_Factor"] = df["day_type"].map(seasonal_by_type).fillna(1.0)
    else:
        df["Seasonal_Factor"] = 1.0
        calendar_status = "fallback"

    df["M4_status"] = calendar_status
    df = df[["date", "Tax_Week_Flag", "End_of_Month_Flag", "End_of_Quarter_Flag", "Seasonal_Factor", "M4_status"]]
    df["date"] = df["date"].dt.date

    out = _repo_root() / "data" / "processed" / "m4" / "m4_daily_signals.csv"
    if persist_csv:
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    return df
