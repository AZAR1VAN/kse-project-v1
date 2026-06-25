"""Рівень 1 — описова статистика."""
from __future__ import annotations

import pandas as pd

from ..data import preprocess as pp


def summary(df: pd.DataFrame) -> dict:
    """Ключові KPI по набору подій."""
    counts = pp.daily_counts(df)
    busiest_day = counts.idxmax() if len(counts) else None
    return {
        "total_alerts": int(len(df)),
        "total_regions": int(df["region"].nunique()),
        "date_start": df["started_at"].min(),
        "date_end": df["started_at"].max(),
        "avg_duration_min": round(float(df["duration_min"].mean()), 1),
        "median_duration_min": round(float(df["duration_min"].median()), 1),
        "busiest_day": (busiest_day, int(counts.max())) if busiest_day is not None else None,
        "busiest_region": pp.region_totals(df).index[0] if len(df) else None,
    }


def top_regions(df: pd.DataFrame, n: int = 10) -> pd.Series:
    return pp.region_totals(df).head(n)
