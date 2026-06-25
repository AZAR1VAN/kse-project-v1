"""Рівень 3 — детекція аномалій/сплесків."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import decomposition


def residual_anomalies(resid: pd.Series, thr: float = 3.5) -> pd.DataFrame:
    """Аномалії за робастним z-score (median + MAD) на залишках STL."""
    med = float(np.median(resid))
    mad = float(np.median(np.abs(resid - med)))
    if mad == 0:
        return pd.DataFrame(columns=["date", "value", "score"])
    z = 0.6745 * (resid - med) / mad
    mask = z.abs() >= thr
    return pd.DataFrame(
        {"date": resid.index[mask], "value": resid[mask].values, "score": z[mask].abs().round(2).values}
    )


def iforest_dates(series: pd.Series, contamination: float = 0.02) -> set:
    """Множина дат-аномалій за IsolationForest на (значення, різниця)."""
    from sklearn.ensemble import IsolationForest

    feats = np.column_stack([series.values, series.diff().fillna(0).values])
    labels = IsolationForest(contamination=contamination, random_state=0).fit_predict(feats)
    return set(series.index[labels == -1])


def detect(series: pd.Series, thr: float = 3.5) -> dict:
    """Поєднати MAD z-score (на STL-залишках) з IsolationForest. Повернути метрики."""
    comp = decomposition.stl_decompose(series)
    anomalies = residual_anomalies(comp["resid"], thr=thr)
    try:
        iforest = iforest_dates(series)
    except Exception:
        iforest = set()
    anomalies = anomalies.copy()
    anomalies["confirmed_iforest"] = anomalies["date"].isin(iforest)
    # фактична кількість тривог у ці дні (для зрозумілості)
    anomalies["count"] = [int(series.get(d, 0)) for d in anomalies["date"]]
    anomalies = anomalies.sort_values("score", ascending=False).reset_index(drop=True)
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in anomalies["date"]]
    return {
        "anomalies": anomalies,
        "anomaly_dates": dates,
        "count": int(len(anomalies)),
        "top": dates[:5],
    }
