from __future__ import annotations

import pandas as pd

from modules.m5_treasury.features import build_m5_features
from modules.m5_treasury.signals import calculate_m5_signals


def test_m5_functions_return_expected_columns():
    df = pd.DataFrame(
        [
            {"observation_date": "2026-04-01", "federal_budget_and_extrabudgetary_funds_balances_bln_rub": 500.0, "eks_deposit_placement_volume_bln_rub": 100.0},
            {"observation_date": "2026-04-10", "federal_budget_and_extrabudgetary_funds_balances_bln_rub": 150.0, "eks_deposit_placement_volume_bln_rub": 60.0},
            {"observation_date": "2026-05-10", "federal_budget_and_extrabudgetary_funds_balances_bln_rub": 120.0, "eks_deposit_placement_volume_bln_rub": 55.0},
        ]
    )
    features = build_m5_features(df)
    signals = calculate_m5_signals(features)
    assert {"cbr_weekly_delta_bln_rub", "cbr_monthly_delta_bln_rub", "roskazna_weekly_delta_bln_rub"}.issubset(features.columns)
    assert {"MAD_score_CBR", "MAD_score_Roskazna", "Flag_Budget_Drain", "Budget_Drain_Score"}.issubset(signals.columns)
