"""Препроцесинг подій тривог і побудова часових рядів (Рівень 0).

Схема входу (Vadimkin volunteer_data_en.csv): region, started_at, finished_at, naive.
Часи в UTC. Якщо кінець відсутній / naive=True → finished_at = started_at + 30 хв.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_DURATION = pd.Timedelta(minutes=30)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Нормалізувати події: UTC-часи, заповнення кінця, тривалість, фільтр інвалідних."""
    out = df.copy()
    out["started_at"] = pd.to_datetime(out["started_at"], utc=True, errors="coerce")
    out["finished_at"] = pd.to_datetime(out["finished_at"], utc=True, errors="coerce")
    out = out.dropna(subset=["region", "started_at"])

    missing_end = out["finished_at"].isna() | (out["finished_at"] < out["started_at"])
    out.loc[missing_end, "finished_at"] = out.loc[missing_end, "started_at"] + DEFAULT_DURATION

    out["duration_min"] = (out["finished_at"] - out["started_at"]).dt.total_seconds() / 60.0
    out["region"] = out["region"].astype(str).str.strip()
    return out.reset_index(drop=True)


def _filter_region(df: pd.DataFrame, region: str | None) -> pd.DataFrame:
    if region and region != "Уся Україна":
        return df[df["region"] == region]
    return df


def regions(df: pd.DataFrame) -> list[str]:
    """Відсортований список регіонів."""
    return sorted(df["region"].unique().tolist())


def daily_counts(df: pd.DataFrame, region: str | None = None) -> pd.Series:
    """Безперервний денний ряд кількості тривог (нулі для днів без подій)."""
    sub = _filter_region(df, region)
    days = sub["started_at"].dt.floor("D")
    counts = days.value_counts().sort_index()
    if counts.empty:
        return counts.astype(int)
    full = pd.date_range(counts.index.min(), counts.index.max(), freq="D", tz="UTC")
    return counts.reindex(full, fill_value=0).astype(int)


def daily_duration(df: pd.DataFrame, region: str | None = None) -> pd.Series:
    """Безперервний денний ряд сумарної тривалості тривог (хвилини)."""
    sub = _filter_region(df, region)
    days = sub["started_at"].dt.floor("D")
    dur = sub.groupby(days)["duration_min"].sum().sort_index()
    if dur.empty:
        return dur
    full = pd.date_range(dur.index.min(), dur.index.max(), freq="D", tz="UTC")
    return dur.reindex(full, fill_value=0.0)


def hourly_profile(df: pd.DataFrame, region: str | None = None) -> pd.Series:
    """Розподіл тривог за годиною доби (0..23)."""
    sub = _filter_region(df, region)
    prof = sub["started_at"].dt.hour.value_counts().sort_index()
    return prof.reindex(range(24), fill_value=0).astype(int)


def weekday_profile(df: pd.DataFrame, region: str | None = None) -> pd.Series:
    """Розподіл тривог за днем тижня (0=Пн .. 6=Нд)."""
    sub = _filter_region(df, region)
    prof = sub["started_at"].dt.weekday.value_counts().sort_index()
    return prof.reindex(range(7), fill_value=0).astype(int)


def region_totals(df: pd.DataFrame) -> pd.Series:
    """Кількість тривог по регіонах (спадання)."""
    return df["region"].value_counts()


def hour_weekday_matrix(df: pd.DataFrame, region: str | None = None) -> pd.DataFrame:
    """Матриця «день тижня × година» з кількістю тривог (для heatmap)."""
    sub = _filter_region(df, region)
    m = (
        sub.assign(h=sub["started_at"].dt.hour, wd=sub["started_at"].dt.weekday)
        .pivot_table(index="wd", columns="h", values="region", aggfunc="count", fill_value=0)
    )
    return m.reindex(index=range(7), columns=range(24), fill_value=0).astype(int)
