# MVP latest recalculation path

This MVP path uses `data/processed/all_newdf.csv` and PCA reconstruction error to calculate LSI without requiring PostgreSQL.

## Run

```bash
cd ml-services
PYTHONPATH=. python -m pipeline.latest_recalculation
```

## Smoke test

```bash
cd ml-services
PYTHONPATH=. python scripts/smoke_ml_services.py
```

## Produced files

- `data/processed/snapshots/latest_snapshot.csv`
- `data/processed/dashboard/m1_dashboard.csv`
- `data/processed/dashboard/m2_dashboard.csv`
- `data/processed/dashboard/m3_dashboard.csv`
- `data/processed/dashboard/m4_dashboard.csv`
- `data/processed/dashboard/m5_dashboard.csv`
- `data/processed/dashboard/lsi_dashboard.csv`
- `data/processed/lsi/lsi_history_pca.csv`

## Current model

LSI is calculated with PCA reconstruction error:

1. Load numeric module signals from `all_newdf.csv`.
2. Convert booleans to 0/1 and fill missing values with neutral zeroes.
3. Scale features with `RobustScaler`.
4. Fit PCA with up to 6 components.
5. Reconstruct the input matrix.
6. Compute per-row mean squared reconstruction error.
7. Scale error to 0-100 by the 99th percentile and clip to `[0, 100]`.
8. Split feature-level reconstruction errors into M1-M5 module contributions.

## Important limitation

The supplied dataset does not contain an explicit calendar date column. The pipeline currently uses the row id / `Unnamed: 0` as `date` for history output. Add a real `date` column when available.

The column `Flag_PeresprosMAD_score_CBR` is ambiguous and looks like a merged column name. The MVP treats it as `M3_Flag_Perespros`; `M5_MAD_score_CBR` remains a neutral fallback until the dataset is fixed.
