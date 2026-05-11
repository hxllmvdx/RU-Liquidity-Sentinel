from __future__ import annotations

import pandas as pd

from modules.m3_ofz.features import build_m3_features
from modules.m3_ofz.signals import calculate_m3_signals


def test_m3_functions_return_expected_columns():
    df = pd.DataFrame(
        [
            {"auction_date": "2026-05-01", "ofz_issue": "26242", "offer_volume_bln_rub": 100.0, "demand_volume_bln_rub": 120.0, "placement_volume_bln_rub": 90.0, "yield_curve_spread_bp": 5.0},
            {"auction_date": "2026-05-08", "ofz_issue": "26243", "offer_volume_bln_rub": 100.0, "demand_volume_bln_rub": 80.0, "placement_volume_bln_rub": 70.0, "yield_curve_spread_bp": 8.0},
        ]
    )
    features = build_m3_features(df)
    signals = calculate_m3_signals(features)
    assert {"cover_ratio", "yield_spread", "placement_to_offer_ratio", "cover_ratio_clipped"}.issubset(features.columns)
    assert {"MAD_score_cover", "Flag_Nedospros", "Flag_Perespros", "Stress_Score", "Stress_Flag"}.issubset(signals.columns)
