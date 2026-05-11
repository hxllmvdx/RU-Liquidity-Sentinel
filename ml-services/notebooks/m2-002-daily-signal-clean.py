# %% [markdown]
# # M2 — Repo Auctions: Daily Signal Table
#
# Input: repo_module_daily_features.csv from m2-001.
# Output: wide signal-only table with one row per date.
# Days without auctions stay present and receive neutral 0 signal values.
# MAD is calculated on auction days only, then merged back to the daily panel.
# This avoids artificial MAD explosions caused by long zero-only calendar stretches.

# %%
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

# %%
# Config
PROCESSED_DIR = Path("../../data/processed")
FEATURES_PATH = PROCESSED_DIR / "repo_module_daily_features.csv"
SIGNALS_OUTPUT_PATH = PROCESSED_DIR / "repo_module_daily_signals.csv"
DASHBOARD_OUTPUT_PATH = PROCESSED_DIR / "repo_module_dashboard.csv"
SUMMARY_OUTPUT_PATH = PROCESSED_DIR / "repo_m2_signal_summary.csv"
COVER_RATE_CHART_PATH = PROCESSED_DIR / "repo_m2_cover_ratio_dashboard.png"
RATE_SPREAD_CHART_PATH = PROCESSED_DIR / "repo_m2_rate_spread_dashboard.png"
MAD_CHART_PATH = PROCESSED_DIR / "repo_m2_mad_scores_dashboard.png"
VOLUME_CHART_PATH = PROCESSED_DIR / "repo_m2_volume_dashboard.png"

for candidate in [
    Path("../../data/processed/repo_module_daily_features.csv"),
    Path("/mnt/data/repo_module_daily_features.csv"),
]:
    if not FEATURES_PATH.exists() and candidate.exists():
        FEATURES_PATH = candidate
        PROCESSED_DIR = candidate.parent
        SIGNALS_OUTPUT_PATH = PROCESSED_DIR / "repo_module_daily_signals.csv"
        DASHBOARD_OUTPUT_PATH = PROCESSED_DIR / "repo_module_dashboard.csv"
        SUMMARY_OUTPUT_PATH = PROCESSED_DIR / "repo_m2_signal_summary.csv"
        COVER_RATE_CHART_PATH = (
            PROCESSED_DIR / "repo_m2_cover_ratio_rate_dashboard.png"
        )
        MAD_CHART_PATH = PROCESSED_DIR / "repo_m2_mad_scores_dashboard.png"
        VOLUME_CHART_PATH = PROCESSED_DIR / "repo_m2_volume_dashboard.png"

MODULE_ID = "M2_REPO"
MAD_WINDOW_DAYS = 1095  # approx. 3 years
MAD_MIN_OBSERVATIONS = 20
EXPANDING_MIN_OBSERVATIONS = 10
MAD_PLOT_CLIP_ABS = (
    10.0  # clipping is used only for charts, never for exported dataset
)
DEMAND_THRESHOLD = 2.0
MAD_ALERT_ABS_THRESHOLD = 2.0
DENOMINATOR_FLOORS = {"cover": 0.05, "rate_spread": 0.05, "volume": 1.0}

# %%
# Helpers


def _median_abs_deviation(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if len(x) == 0:
        return np.nan
    med = float(x.median())
    return float((x - med).abs().median())


def historical_mad_scores(
    df: pd.DataFrame,
    value_col: str,
    date_col: str = "date",
    window_days: int = MAD_WINDOW_DAYS,
    min_observations: int = MAD_MIN_OBSERVATIONS,
    expanding_min_observations: int = EXPANDING_MIN_OBSERVATIONS,
    denominator_floor: float = 0.05,
    invert: bool = False,
) -> pd.DataFrame:
    """Calculate no-lookahead rolling MAD score over event observations only.

    For each row, only previous observations are used. If rolling history is too short,
    expanding history is used. If history is still insufficient, the signal is neutral 0.
    """
    work = df[[date_col, value_col]].copy()
    work[date_col] = pd.to_datetime(
        work[date_col], errors="coerce"
    ).dt.normalize()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = (
        work.dropna(subset=[date_col])
        .sort_values(date_col)
        .reset_index(drop=True)
    )

    scores = []
    qualities = []
    medians = []
    mads = []

    for _, row in work.iterrows():
        current_date = row[date_col]
        current_value = row[value_col]
        if pd.isna(current_value):
            scores.append(0.0)
            qualities.append("missing_input_neutral_zero")
            medians.append(np.nan)
            mads.append(np.nan)
            continue

        history_start = current_date - pd.Timedelta(days=window_days)
        rolling_hist = work[
            (work[date_col] < current_date) & (work[date_col] >= history_start)
        ][value_col].dropna()
        expanding_hist = work[work[date_col] < current_date][value_col].dropna()

        if len(rolling_hist) >= min_observations:
            hist = rolling_hist
            quality = "ok_rolling"
        elif len(expanding_hist) >= expanding_min_observations:
            hist = expanding_hist
            quality = "expanding_fallback"
        else:
            scores.append(0.0)
            qualities.append("not_enough_history_neutral_zero")
            medians.append(np.nan)
            mads.append(np.nan)
            continue

        median = float(hist.median())
        mad = _median_abs_deviation(hist)
        denominator = max(
            float(mad) if pd.notna(mad) else 0.0, denominator_floor
        )
        score = (float(current_value) - median) / denominator
        if invert:
            score = -score
        score = float(score)

        scores.append(score)
        qualities.append(quality)
        medians.append(median)
        mads.append(mad)

    out = work[[date_col, value_col]].copy()
    out[f"{value_col}_mad_score"] = scores
    out[f"{value_col}_mad_quality"] = qualities
    out[f"{value_col}_rolling_median"] = medians
    out[f"{value_col}_rolling_mad"] = mads
    return out


def _auction_plot_series(
    df: pd.DataFrame,
    value_col: str,
    output_col: str,
    clip_upper: float | None = None,
) -> pd.DataFrame:
    """Return copy where no-auction days are NaN for charts only.

    The exported daily tables still keep no-auction rows as neutral zeros.
    Charts should not draw these zeros as a continuous line, otherwise the
    plot turns into unreadable vertical spikes.
    """
    plot_df = df.sort_values("date").copy()
    plot_df[output_col] = np.where(
        plot_df["has_auction"].astype(bool), plot_df[value_col], np.nan
    )
    if clip_upper is not None:
        plot_df[output_col] = pd.to_numeric(
            plot_df[output_col], errors="coerce"
        ).clip(upper=clip_upper)
    return plot_df


def plot_cover_ratio(df: pd.DataFrame, output_path: Path) -> None:
    """Dashboard chart: cover ratio only on auction days.

    No-auction days are shown as gaps. Extreme cover-ratio values are clipped
    only for visualization; source values in CSV are not modified.
    """
    plot_df = _auction_plot_series(
        df,
        value_col="cover_signal_raw",
        output_col="cover_ratio_plot",
        clip_upper=10.0,
    )

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(
        plot_df["date"],
        plot_df["cover_ratio_plot"],
        linewidth=1.1,
        label="Cover ratio, auction days only, clipped at 10",
    )
    ax.axhline(
        DEMAND_THRESHOLD,
        linestyle="--",
        linewidth=1,
        label="Demand threshold > 2.0",
    )

    flags = plot_df[plot_df["Flag_Demand"].astype(bool)]
    flags = flags.dropna(subset=["cover_ratio_plot"])
    if not flags.empty:
        ax.scatter(
            flags["date"], flags["cover_ratio_plot"], s=18, label="Flag_Demand"
        )

    ax.set_title("M2 Repo: cover ratio on auction days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cover ratio")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.show()


def plot_rate_spread(df: pd.DataFrame, output_path: Path) -> None:
    """Dashboard chart: rate spread only on auction days."""
    plot_df = _auction_plot_series(
        df,
        value_col="rate_spread_signal_raw",
        output_col="rate_spread_plot",
        clip_upper=None,
    )

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(
        plot_df["date"],
        plot_df["rate_spread_plot"],
        linewidth=1.1,
        label="Rate spread, pp, auction days only",
    )
    ax.axhline(0, linestyle="--", linewidth=1, label="0 pp")

    ax.set_title("M2 Repo: rate spread on auction days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Rate spread, pp")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.show()


def plot_mad_scores(df: pd.DataFrame, output_path: Path) -> None:
    """Dashboard chart: smoothed MAD scores for M2.

    Exported CSV keeps full, unclipped MAD values. For charts only, values are
    clipped to keep the visualization readable.
    """
    plot_df = df.sort_values("date").copy()
    plot_df["MAD_score_cover_plot"] = plot_df["MAD_score_cover"].clip(
        -MAD_PLOT_CLIP_ABS, MAD_PLOT_CLIP_ABS
    )
    plot_df["MAD_score_rate_spread_plot"] = plot_df[
        "MAD_score_rate_spread"
    ].clip(-MAD_PLOT_CLIP_ABS, MAD_PLOT_CLIP_ABS)
    plot_df["MAD_score_cover_30d"] = (
        plot_df["MAD_score_cover_plot"].rolling(30, min_periods=1).mean()
    )
    plot_df["MAD_score_rate_spread_30d"] = (
        plot_df["MAD_score_rate_spread_plot"].rolling(30, min_periods=1).mean()
    )

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(
        plot_df["date"],
        plot_df["MAD_score_cover_30d"],
        linewidth=1.8,
        label="MAD cover, 30d mean",
    )
    ax.plot(
        plot_df["date"],
        plot_df["MAD_score_rate_spread_30d"],
        linewidth=1.8,
        label="MAD rate spread, 30d mean",
    )
    ax.axhline(
        MAD_ALERT_ABS_THRESHOLD,
        linestyle="--",
        linewidth=1,
        label="+2 MAD alert",
    )
    ax.axhline(
        -MAD_ALERT_ABS_THRESHOLD,
        linestyle="--",
        linewidth=1,
        label="-2 MAD alert",
    )

    ax.set_title("M2 Repo: smoothed MAD stress signals")
    ax.set_xlabel("Date")
    ax.set_ylabel("MAD score, chart-clipped, 30d mean")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.show()


def plot_repo_volume(df: pd.DataFrame, output_path: Path) -> None:
    """Dashboard chart: weekly aggregated repo auction volume."""
    plot_df = df.sort_values("date").copy()
    weekly_volume = (
        plot_df.set_index("date")["total_auction_volume_bln_rub"]
        .resample("W")
        .sum()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(15, 5))
    ax.bar(
        weekly_volume["date"],
        weekly_volume["total_auction_volume_bln_rub"],
        width=5,
        label="Weekly auction volume",
    )

    ax.set_title("M2 Repo: weekly auction volume")
    ax.set_xlabel("Date")
    ax.set_ylabel("Volume, bln RUB")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.show()


def build_signal_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build one-row-per-day signal table.

    This is intentionally a wide signal table, not a long table.
    It prevents row multiplication where each date is repeated for every signal.

    Output contains only final signals used by the M2 module. Raw features and
    diagnostics stay in the separate dashboard table.
    """
    out = df[
        [
            "date",
            "MAD_score_cover",
            "MAD_score_rate_spread",
            "MAD_score_repo_volume",
            "Flag_Demand",
        ]
    ].copy()

    out.insert(1, "module_id", MODULE_ID)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date.astype(
        str
    )

    for col in [
        "MAD_score_cover",
        "MAD_score_rate_spread",
        "MAD_score_repo_volume",
    ]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    out["Flag_Demand"] = out["Flag_Demand"].fillna(False).astype(bool)

    return out


# %%
# Load daily features
if not FEATURES_PATH.exists():
    raise FileNotFoundError(
        f"Daily features not found: {FEATURES_PATH}. Run m2-001-daily-feature-panel.py first."
    )

daily = pd.read_csv(FEATURES_PATH)
daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.normalize()
daily = daily.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

for col in daily.columns:
    if col != "date" and col != "Flag_Demand":
        daily[col] = pd.to_numeric(daily[col], errors="coerce").fillna(0.0)
daily["Flag_Demand"] = (
    daily.get("Flag_Demand", False).fillna(False).astype(bool)
)

print("Loaded daily features:", FEATURES_PATH)
print("Shape:", daily.shape)
print("Date range:", daily["date"].min(), "->", daily["date"].max())
print("Auction days:", int(daily["has_auction"].sum()))
print("No-auction days:", int((daily["has_auction"] == 0).sum()))

# %%
# Build raw signal features
# Prefer 7-day repo features when a 7-day auction exists; otherwise use same-day volume-weighted all-tenor feature.
daily["cover_signal_raw"] = np.where(
    daily["repo_7d_cover_ratio"] > 0,
    daily["repo_7d_cover_ratio"],
    daily["cover_ratio_volume_weighted"],
)
daily["rate_spread_signal_raw"] = np.where(
    daily["repo_7d_rate_spread"] != 0,
    daily["repo_7d_rate_spread"],
    daily["rate_spread_volume_weighted"],
)
daily["volume_signal_raw"] = daily["total_auction_volume_bln_rub"]

# No-auction days must remain neutral.
no_auction = daily["has_auction"].eq(0)
daily.loc[
    no_auction,
    ["cover_signal_raw", "rate_spread_signal_raw", "volume_signal_raw"],
] = 0.0

# Flag only when auction happened.
daily["Flag_Demand"] = daily["has_auction"].eq(1) & daily[
    "cover_signal_raw"
].gt(DEMAND_THRESHOLD)

# %%
# MAD normalization on auction days only, then merge back to daily panel
auction_days = daily[daily["has_auction"].eq(1)].copy()

cover_mad = historical_mad_scores(
    auction_days,
    value_col="cover_signal_raw",
    denominator_floor=DENOMINATOR_FLOORS["cover"],
    invert=False,
)
rate_mad = historical_mad_scores(
    auction_days,
    value_col="rate_spread_signal_raw",
    denominator_floor=DENOMINATOR_FLOORS["rate_spread"],
    invert=False,
)
volume_mad = historical_mad_scores(
    auction_days,
    value_col="volume_signal_raw",
    denominator_floor=DENOMINATOR_FLOORS["volume"],
    invert=False,
)

daily = daily.merge(
    cover_mad[
        ["date", "cover_signal_raw_mad_score", "cover_signal_raw_mad_quality"]
    ],
    on="date",
    how="left",
)
daily = daily.merge(
    rate_mad[
        [
            "date",
            "rate_spread_signal_raw_mad_score",
            "rate_spread_signal_raw_mad_quality",
        ]
    ],
    on="date",
    how="left",
)
daily = daily.merge(
    volume_mad[
        ["date", "volume_signal_raw_mad_score", "volume_signal_raw_mad_quality"]
    ],
    on="date",
    how="left",
)

# Final exported signals: no-auction/missing history = neutral zero.
# Important: do NOT clip exported MAD values. Clipping is allowed only for charts.
daily["MAD_score_cover"] = daily["cover_signal_raw_mad_score"].fillna(0.0)
daily["MAD_score_rate_spread"] = daily[
    "rate_spread_signal_raw_mad_score"
].fillna(0.0)
daily["MAD_score_repo_volume"] = daily["volume_signal_raw_mad_score"].fillna(
    0.0
)

daily["MAD_score_cover_quality"] = daily["cover_signal_raw_mad_quality"].fillna(
    "no_auction_neutral_zero"
)
daily["MAD_score_rate_spread_quality"] = daily[
    "rate_spread_signal_raw_mad_quality"
].fillna("no_auction_neutral_zero")
daily["MAD_score_repo_volume_quality"] = daily[
    "volume_signal_raw_mad_quality"
].fillna("no_auction_neutral_zero")

# Enforce neutral no-auction rows.
daily.loc[
    no_auction,
    ["MAD_score_cover", "MAD_score_rate_spread", "MAD_score_repo_volume"],
] = 0.0
daily.loc[
    no_auction,
    [
        "MAD_score_cover_quality",
        "MAD_score_rate_spread_quality",
        "MAD_score_repo_volume_quality",
    ],
] = "no_auction_neutral_zero"

# %%
# Diagnostics
summary = pd.DataFrame(
    [
        {"metric": "rows", "value": len(daily)},
        {"metric": "auction_days", "value": int(daily["has_auction"].sum())},
        {
            "metric": "no_auction_days",
            "value": int((daily["has_auction"] == 0).sum()),
        },
        {
            "metric": "Flag_Demand_days",
            "value": int(daily["Flag_Demand"].sum()),
        },
        {
            "metric": "MAD_score_cover_nulls",
            "value": int(daily["MAD_score_cover"].isna().sum()),
        },
        {
            "metric": "MAD_score_rate_spread_nulls",
            "value": int(daily["MAD_score_rate_spread"].isna().sum()),
        },
        {
            "metric": "exported_mad_max_abs_unclipped",
            "value": float(
                daily[
                    [
                        "MAD_score_cover",
                        "MAD_score_rate_spread",
                        "MAD_score_repo_volume",
                    ]
                ]
                .abs()
                .max()
                .max()
            ),
        },
        {"metric": "chart_mad_clip_abs", "value": MAD_PLOT_CLIP_ABS},
    ]
)
print(summary)
print("\nMAD cover quality:")
print(daily["MAD_score_cover_quality"].value_counts(dropna=False))
print("\nMAD rate spread quality:")
print(daily["MAD_score_rate_spread_quality"].value_counts(dropna=False))

# %%
# Export wide signal-only table and dashboard table
signals = build_signal_table(daily)

# Extra assertion: signal table contains only one row per date and only final signal columns.
expected_signal_cols = [
    "date",
    "module_id",
    "MAD_score_cover",
    "MAD_score_rate_spread",
    "MAD_score_repo_volume",
    "Flag_Demand",
]
signals = signals[expected_signal_cols].copy()
if list(signals.columns) != expected_signal_cols:
    raise AssertionError(
        "Signal output must contain only wide signal table columns"
    )
if signals["date"].duplicated().any():
    raise AssertionError("Signal output must contain exactly one row per date")

# Dashboard table is separate and can contain raw features and diagnostics.
dashboard_cols = [
    "date",
    "has_auction",
    "has_7d_repo",
    "cover_signal_raw",
    "rate_spread_signal_raw",
    "total_auction_volume_bln_rub",
    "MAD_score_cover",
    "MAD_score_rate_spread",
    "MAD_score_repo_volume",
    "Flag_Demand",
]
dashboard = daily[dashboard_cols].copy()

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
signals.to_csv(SIGNALS_OUTPUT_PATH, index=False)
dashboard.to_csv(DASHBOARD_OUTPUT_PATH, index=False)
summary.to_csv(SUMMARY_OUTPUT_PATH, index=False)

# Charts are intentionally generated from the wide dashboard table, not from the signal-only long table.
plot_cover_ratio(dashboard, COVER_RATE_CHART_PATH)
plot_rate_spread(dashboard, RATE_SPREAD_CHART_PATH)
plot_mad_scores(dashboard, MAD_CHART_PATH)
plot_repo_volume(dashboard, VOLUME_CHART_PATH)

print("Saved signal-only table:", SIGNALS_OUTPUT_PATH)
print("Saved dashboard table:", DASHBOARD_OUTPUT_PATH)
print("Saved summary:", SUMMARY_OUTPUT_PATH)
print("Saved cover ratio chart:", COVER_RATE_CHART_PATH)
print("Saved rate spread chart:", RATE_SPREAD_CHART_PATH)
print("Saved MAD chart:", MAD_CHART_PATH)
print("Saved volume chart:", VOLUME_CHART_PATH)
print("Signal shape:", signals.shape)
print("Signal columns:", list(signals.columns))
print("Unique signal dates:", signals["date"].nunique())
