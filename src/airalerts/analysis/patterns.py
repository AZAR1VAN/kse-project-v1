"""Рівень 5 — патерни та кластеризація регіонів."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data import preprocess as pp


def region_features(df: pd.DataFrame) -> pd.DataFrame:
    """Профіль кожного регіону: середньоденна к-сть + розподіли годин(24) і днів тижня(7)."""
    rows = {}
    for region in pp.regions(df):
        sub = df[df["region"] == region]
        daily = pp.daily_counts(df, region)
        hours = pp.hourly_profile(df, region)
        wd = pp.weekday_profile(df, region)
        hours = hours / hours.sum() if hours.sum() else hours
        wd = wd / wd.sum() if wd.sum() else wd
        rows[region] = {
            "mean_daily": float(daily.mean()) if len(daily) else 0.0,
            "total": int(len(sub)),
            **{f"h{h}": float(hours.get(h, 0)) for h in range(24)},
            **{f"wd{d}": float(wd.get(d, 0)) for d in range(7)},
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def cluster_regions(features: pd.DataFrame, k: int | None = None) -> dict:
    """KMeans на стандартизованих профілях; k за silhouette (2..5)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    feat_cols = [c for c in features.columns if c != "total"]
    X = StandardScaler().fit_transform(features[feat_cols].values)
    n = len(features)
    if n < 3:
        return {"labels": {r: 0 for r in features.index}, "k": 1, "silhouette": float("nan")}

    best = None
    for kk in range(2, min(5, n - 1) + 1):
        labels = KMeans(n_clusters=kk, n_init=10, random_state=0).fit_predict(X)
        score = silhouette_score(X, labels)
        if best is None or score > best[0]:
            best = (score, kk, labels)
    if k is not None:
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X)
        best = (silhouette_score(X, labels), k, labels)
    score, kk, labels = best
    return {
        "labels": dict(zip(features.index, [int(x) for x in labels])),
        "k": int(kk),
        "silhouette": round(float(score), 3),
    }


def peak_hours(df: pd.DataFrame, region: str | None = None, top: int = 3) -> list:
    """Топ годин доби за кількістю тривог."""
    prof = pp.hourly_profile(df, region)
    return [int(h) for h in prof.sort_values(ascending=False).head(top).index]


def analyze(df: pd.DataFrame) -> dict:
    """Зведені метрики рівня 5."""
    feats = region_features(df)
    clusters = cluster_regions(feats)
    return {
        "features": feats,
        "clusters": clusters["labels"],
        "k": clusters["k"],
        "silhouette": clusters["silhouette"],
        "peak_hours": peak_hours(df),
    }
