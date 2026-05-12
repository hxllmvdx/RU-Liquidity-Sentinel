from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from common.database import Database
from repositories import LSIRepository


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_lsi_history_context(days: int = 30) -> dict[str, Any]:
    try:
        db = Database()
        db.connect()
        try:
            repo = LSIRepository(db)
            latest = repo.get_latest_lsi()
            if latest is not None:
                to_date = latest["calculation_date"]
                from_date = to_date - timedelta(days=days)
                rows = repo.get_lsi_history(from_date, to_date, limit=days + 10, offset=0)
                if rows:
                    start = float(rows[0]["lsi"])
                    end = float(rows[-1]["lsi"])
                    peak_row = max(rows, key=lambda x: float(x["lsi"]))
                    trough_row = min(rows, key=lambda x: float(x["lsi"]))
                    status = str(rows[-1].get("status", "unknown"))
                    trend = "растёт" if end > start + 2 else "снижается" if end < start - 2 else "стабилен"
                    return {
                        "available": True,
                        "summary": (
                            f"История LSI за последние {len(rows)} наблюдений: текущее значение {end:.2f}, статус {status}, тренд {trend}. "
                            f"Пик {float(peak_row['lsi']):.2f} был {peak_row['calculation_date'].isoformat()}, "
                            f"минимум {float(trough_row['lsi']):.2f} был {trough_row['calculation_date'].isoformat()}."
                        ),
                        "rows": [
                            {
                                "date": row["calculation_date"].isoformat(),
                                "lsi": float(row["lsi"]),
                                "status": str(row.get("status", "unknown")),
                                "confidence": float(row.get("confidence", 0.0) or 0.0),
                            }
                            for row in rows[-30:]
                        ],
                    }
        finally:
            db.close()
    except Exception:
        pass

    path = _repo_root() / "data" / "processed" / "dashboard" / "lsi_dashboard.csv"
    if not path.exists():
        return {"available": False, "summary": "История LSI пока не сформирована.", "rows": []}
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns or "LSI" not in df.columns:
        return {"available": False, "summary": "Файл истории LSI пустой или имеет неверную структуру.", "rows": []}
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["LSI"] = pd.to_numeric(df["LSI"], errors="coerce")
    df = df.dropna(subset=["date", "LSI"]).sort_values("date")
    cutoff = df["date"].max() - pd.Timedelta(days=days)
    recent = df[df["date"] >= cutoff].copy()
    if recent.empty:
        recent = df.tail(min(days, len(df))).copy()
    start = float(recent.iloc[0]["LSI"])
    end = float(recent.iloc[-1]["LSI"])
    peak_row = recent.loc[recent["LSI"].idxmax()]
    trough_row = recent.loc[recent["LSI"].idxmin()]
    status = str(recent.iloc[-1].get("status", "unknown"))
    trend = "растёт" if end > start + 2 else "снижается" if end < start - 2 else "стабилен"
    summary = (
        f"История LSI за последние {len(recent)} наблюдений: текущее значение {end:.2f}, статус {status}, тренд {trend}. "
        f"Пик {float(peak_row['LSI']):.2f} был {peak_row['date'].date().isoformat()}, "
        f"минимум {float(trough_row['LSI']):.2f} был {trough_row['date'].date().isoformat()}."
    )
    return {
        "available": True,
        "summary": summary,
        "rows": [
            {
                "date": row["date"].date().isoformat(),
                "lsi": float(row["LSI"]),
                "status": str(row.get("status", "unknown")),
                "confidence": float(row.get("confidence", 0.0)),
            }
            for _, row in recent.tail(30).iterrows()
        ],
    }
