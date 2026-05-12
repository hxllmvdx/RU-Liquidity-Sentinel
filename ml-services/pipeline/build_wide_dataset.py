from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from modules.m1_reserves.build_dataset import build_m1_daily_dataset
from modules.m4_tax_seasonality.build_dataset import build_m4_daily_dataset


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()
    return df


def _apply_decay(df: pd.DataFrame, source_flag_col: str, value_cols: list[str], max_days: int, decay: float) -> pd.DataFrame:
    frame = df.copy()
    if source_flag_col not in frame.columns:
        return frame
    flag = pd.to_numeric(frame[source_flag_col], errors="coerce").fillna(0).astype(int)
    event_index = flag.where(flag > 0).replace(0, pd.NA)
    last_event_row = event_index.ffill()
    distance = (pd.Series(range(len(frame))) - last_event_row).astype("float")
    distance = distance.where(last_event_row.notna())
    for col in value_cols:
        if col not in frame.columns:
            continue
        raw = pd.to_numeric(frame[col], errors="coerce")
        decayed = raw.copy()
        for idx in range(len(frame)):
            if pd.notna(raw.iloc[idx]) and raw.iloc[idx] != 0:
                continue
            d = distance.iloc[idx]
            if pd.isna(d) or d <= 0 or d > max_days:
                continue
            prev = idx - int(d)
            if prev < 0:
                continue
            prev_value = raw.iloc[prev]
            if pd.isna(prev_value) or prev_value == 0:
                continue
            decayed.iloc[idx] = float(prev_value) * (decay ** float(d))
        frame[col] = decayed.fillna(0.0)
    return frame


def build_m2_daily_dataset(date_from: str = "2021-01-01", date_to: str | None = None, persist_csv: bool = True) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    calendar = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})
    feat = _read_csv(repo_root() / "data" / "processed" / "repo_module_daily_features.csv")
    sig = _read_csv(repo_root() / "data" / "processed" / "repo_module_daily_signals.csv")
    df = calendar.merge(feat, on="date", how="left").merge(sig, on=["date"], how="left", suffixes=("", "_sig"))
    out = pd.DataFrame({
        "date": df["date"].dt.date,
        "cover_ratio": pd.to_numeric(df.get("cover_ratio_volume_weighted"), errors="coerce"),
        "rate_spread": pd.to_numeric(df.get("rate_spread_volume_weighted"), errors="coerce"),
        "repo_volume": pd.to_numeric(df.get("total_placement_volume_bln_rub"), errors="coerce"),
        "MAD_score_cover": pd.to_numeric(df.get("MAD_score_cover"), errors="coerce").fillna(0.0),
        "MAD_score_rate_spread": pd.to_numeric(df.get("MAD_score_rate_spread"), errors="coerce").fillna(0.0),
        "MAD_score_repo_volume": pd.to_numeric(df.get("MAD_score_repo_volume"), errors="coerce").fillna(0.0),
        "Flag_Demand": df.get("Flag_Demand", False).fillna(False).astype(int),
        "has_auction": df.get("has_auction", False).fillna(False).astype(int),
    })
    out = _apply_decay(out, "has_auction", ["MAD_score_cover", "MAD_score_rate_spread", "MAD_score_repo_volume"], max_days=2, decay=0.65)
    out["M2_status"] = "ok" if not feat.empty else "missing"
    path = repo_root() / "data" / "processed" / "m2" / "m2_daily_signals.csv"
    if persist_csv:
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
    return out


def build_m3_daily_dataset(date_from: str = "2021-01-01", date_to: str | None = None, persist_csv: bool = True) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    calendar = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})
    sig = _read_csv(repo_root() / "data" / "processed" / "ofz_auction_signals_daily.csv")
    if not sig.empty:
        sig = sig[(sig["date"] >= pd.Timestamp(date_from)) & (sig["date"] <= end_ts)]
    df = calendar.merge(sig, on="date", how="left")
    out = pd.DataFrame({
        "date": df["date"].dt.date,
        "cover_ratio": pd.to_numeric(df.get("cover_ratio"), errors="coerce"),
        "yield_spread": pd.to_numeric(df.get("yield_curve_spread_bp"), errors="coerce"),
        "MAD_score_cover": pd.to_numeric(df.get("MAD_score_cover"), errors="coerce").fillna(0.0),
        "MAD_score_yield_spread": pd.to_numeric(df.get("MAD_score_yield_spread"), errors="coerce").fillna(0.0),
        "Flag_Nedospros": df.get("Flag_Nedospros", 0).fillna(0).astype(int),
        "Flag_Perespros": df.get("Flag_Perespros", 0).fillna(0).astype(int),
        "has_auction": df.get("has_auction", 0).fillna(0).astype(int),
    })
    out = _apply_decay(out, "has_auction", ["MAD_score_cover", "MAD_score_yield_spread"], max_days=3, decay=0.75)
    out["M3_status"] = "ok" if not sig.empty else "fallback"
    path = repo_root() / "data" / "processed" / "m3" / "m3_daily_signals.csv"
    if persist_csv:
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
    return out


def build_m5_daily_dataset(date_from: str = "2021-01-01", date_to: str | None = None, persist_csv: bool = True) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    calendar = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})
    feat = _read_csv(repo_root() / "data" / "processed" / "m5_treasury_daily_features.csv")
    sig = _read_csv(repo_root() / "data" / "processed" / "m5_treasury_daily_signals.csv")
    df = calendar.merge(feat, on="date", how="left").merge(sig, on=["date"], how="left", suffixes=("", "_sig"))
    out = pd.DataFrame({
        "date": df["date"].dt.date,
        "cbr_eks_balance_bln_rub": pd.to_numeric(df.get("cbr_eks_balance_bln_rub"), errors="coerce"),
        "roskazna_deposit_placements_bln_rub": pd.to_numeric(df.get("roskazna_deposit_placements_bln_rub"), errors="coerce").fillna(0.0),
        "budget_drain_bln_rub": pd.to_numeric(df.get("budget_drain_bln_rub"), errors="coerce"),
        "MAD_score_CBR": pd.to_numeric(df.get("MAD_score_CBR"), errors="coerce").fillna(0.0),
        "MAD_score_Roskazna": pd.to_numeric(df.get("MAD_score_Roskazna"), errors="coerce").fillna(0.0),
        "Flag_Budget_Drain": df.get("Flag_Budget_Drain", False).fillna(False).astype(int),
    })
    out["has_update"] = (
        pd.to_numeric(df.get("has_cbr_update", 0), errors="coerce").fillna(0).astype(int)
        | pd.to_numeric(df.get("has_roskazna_event", 0), errors="coerce").fillna(0).astype(int)
    )
    out = _apply_decay(out, "has_update", ["MAD_score_CBR", "MAD_score_Roskazna"], max_days=4, decay=0.8)
    out = out.drop(columns=["has_update"])
    out["M5_status"] = "ok" if not feat.empty else "missing"
    path = repo_root() / "data" / "processed" / "m5" / "m5_daily_signals.csv"
    if persist_csv:
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, index=False)
    return out


def build_wide_lsi_dataset(
    date_from: str = "2021-01-01",
    date_to: str | None = None,
    persist_csv: bool = True,
) -> pd.DataFrame:
    end_ts = pd.Timestamp.today().normalize() if date_to is None else pd.Timestamp(date_to)
    calendar = pd.DataFrame({"date": pd.date_range(pd.Timestamp(date_from), end_ts, freq="D")})

    m1 = build_m1_daily_dataset(date_from=date_from, date_to=str(end_ts.date()), persist_csv=persist_csv)
    m2 = build_m2_daily_dataset(date_from=date_from, date_to=str(end_ts.date()), persist_csv=persist_csv)
    m3 = build_m3_daily_dataset(date_from=date_from, date_to=str(end_ts.date()), persist_csv=persist_csv)
    m5 = build_m5_daily_dataset(date_from=date_from, date_to=str(end_ts.date()), persist_csv=persist_csv)
    m4 = build_m4_daily_dataset(m1, m2, m5, date_from=date_from, date_to=str(end_ts.date()), persist_csv=persist_csv)

    frames = {"M1": m1, "M2": m2, "M3": m3, "M4": m4, "M5": m5}
    wide = calendar.copy()
    for module, frame in frames.items():
        f = frame.copy()
        f["date"] = pd.to_datetime(f["date"], errors="coerce")
        rename = {c: f"{module}_{c}" for c in f.columns if c != "date" and not c.startswith(f"{module}_")}
        f = f.rename(columns=rename)
        f[f"{module}_date"] = f["date"].dt.date.astype(str)
        wide = wide.merge(f, on="date", how="left")

    for module in ["M1", "M2", "M3", "M4", "M5"]:
        legacy_status = f"{module}_{module}_status"
        target_status = f"{module}_status"
        if legacy_status in wide.columns and target_status not in wide.columns:
            wide[target_status] = wide[legacy_status]

    bool_cols = [c for c in wide.columns if "Flag" in c or c.endswith("has_auction")]
    mad_cols = [c for c in wide.columns if "MAD_score" in c]
    for col in bool_cols:
        wide[col] = wide[col].fillna(0).astype(int)
    for col in mad_cols:
        wide[col] = pd.to_numeric(wide[col], errors="coerce").fillna(0.0)
    if "M4_Seasonal_Factor" in wide.columns:
        wide["M4_Seasonal_Factor"] = pd.to_numeric(wide["M4_Seasonal_Factor"], errors="coerce").fillna(1.0)
    for module in ["M1", "M2", "M3", "M4", "M5"]:
        status_col = f"{module}_status"
        if status_col not in wide.columns:
            wide[status_col] = "missing"
        else:
            wide[status_col] = wide[status_col].fillna("missing")
    status_cols = [c for c in wide.columns if c.endswith("_status")]
    wide["missing_modules"] = wide[status_cols].apply(
        lambda row: ",".join(sorted({col.split("_")[0] for col, value in row.items() if str(value) in {"missing", "fallback"}})),
        axis=1,
    )
    wide["snapshot_quality"] = (1.0 - wide["missing_modules"].str.split(",").apply(lambda items: len([x for x in items if x]) * 0.2)).clip(lower=0.1, upper=1.0)
    wide["source_summary"] = json.dumps({m: str(frames[m].shape[0]) for m in frames}, ensure_ascii=False)
    wide["date"] = wide["date"].dt.date

    out = repo_root() / "data" / "processed" / "lsi" / "lsi_wide_daily_dataset.csv"
    if persist_csv:
        out.parent.mkdir(parents=True, exist_ok=True)
        wide.to_csv(out, index=False)
    return wide


def main() -> None:
    df = build_wide_lsi_dataset()
    print(json.dumps({"rows": int(len(df)), "path": str(repo_root() / "data" / "processed" / "lsi" / "lsi_wide_daily_dataset.csv")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
