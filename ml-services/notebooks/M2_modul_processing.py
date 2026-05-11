import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path


class RepoAuctionModule:
    def __init__(self,demand_threshold: float = 2.0,):
        self.demand_threshold = demand_threshold
    @staticmethod
    def rolling_mad_score(series: pd.Series, window: str = "1095D") -> pd.Series:
        def _mad_zscore(x):
            x = pd.Series(x).dropna()
            if len(x) == 0:
                return np.nan

            median = x.median()
            mad = np.median(np.abs(x - median))

            if mad == 0:
                return np.nan

            last_value = x.iloc[-1]

            return (last_value - median) / (1.4826 * mad)

        return series.rolling(window=window, min_periods=5).apply(_mad_zscore, raw=False)

    def preprocess(self,df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        repo = df.copy()
        repo["auction_date"] = pd.to_datetime(repo["auction_date"])
        repo = repo.set_index("auction_date")
        repo = repo.drop(
            columns=[
                'source_code',
                'observation_date',
                'published_at',
                'demand_volume_mln_rub',
                'deal_volume_mln_rub',
                'min_declared_rate_percent',
                'max_declared_rate_percent',
                'deal_volume_within_limit_mln_rub',
                'weighted_average_rate_within_limit_percent',
                'first_leg_date',
                'second_leg_date',
                'unit',
                'raw',
                'loaded_at'
            ],
            errors='ignore'
        )
        
        repo = repo[repo.index >= "2013-01-01"]
        repo = repo.sort_index()
        repo["key_rate_percent"] = (repo["key_rate_percent"].ffill())
        repo = repo[repo["term_days"] == 7].copy()
        numeric_cols = [
            "key_rate_percent",
            "demand_volume_bln_rub",
            "placement_volume_bln_rub",
            "cover_ratio",
            "cutoff_rate_percent",
            "weighted_average_rate_percent",
        ]

        for col in numeric_cols:
            repo[col] = pd.to_numeric(repo[col],errors="coerce")

        rate_cols = [
            "cutoff_rate_percent",
            "weighted_average_rate_percent",
        ]

        for col in rate_cols:
            repo[col] = (repo[col].interpolate(method="linear",limit=1))
        
        if "rate_spread_to_key_rate_percent" not in repo.columns:
            repo["rate_spread_to_key_rate_percent"] = (repo["cutoff_rate_percent"]- repo["key_rate_percent"])

        repo["Flag_Demand"] = (repo["cover_ratio"] > self.demand_threshold).astype(int)
        repo["MAD_score_cover"] = (self.rolling_mad_score(repo["cover_ratio"]))
        repo["MAD_score_rate_spread"] = (self.rolling_mad_score(repo["rate_spread_to_key_rate_percent"]))
        signals = repo[
            [
                "MAD_score_cover",
                "MAD_score_rate_spread",
                "Flag_Demand",
            ]
        ].copy()

        dashboard = repo[
            [
                "cover_ratio",
                "cutoff_rate_percent",
                "key_rate_percent",
            ]
        ].copy()

        return signals, dashboard


BASE_DIR = Path(__file__).resolve().parents[2]

csv_path = (
    BASE_DIR
    / "data"
    / "raw"
    / "cbr"
    / "repo"
    / "cbr_repo_2002-11-21_2026-05-05.csv"
)

df = pd.read_csv(csv_path)

module = RepoAuctionModule()
signals_df, dashboard_df = module.preprocess(df)
print(signals_df.info())
print(signals_df.head())

processed_path = (
    BASE_DIR
    / "data"
    / "processed"
)

processed_path.mkdir(
    parents=True,
    exist_ok=True
)

signals_df.to_csv(
    processed_path
    / "repo_module_signals.csv"
)
