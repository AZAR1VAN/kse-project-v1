"""Рівень 2 — декомпозиція тренд/сезонність (STL) + точки зміни."""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


def stl_decompose(series: pd.Series, period: int = 7) -> dict:
    """STL-декомпозиція денного ряду. Повертає trend/seasonal/resid як pd.Series."""
    s = series.astype(float)
    res = STL(s.values, period=period, robust=True).fit()
    idx = series.index
    return {
        "trend": pd.Series(res.trend, index=idx),
        "seasonal": pd.Series(res.seasonal, index=idx),
        "resid": pd.Series(res.resid, index=idx),
    }


def trend_slope(trend: pd.Series) -> float:
    """Нахил тренду (одиниць на день) через лінійну регресію."""
    x = np.arange(len(trend))
    return float(np.polyfit(x, trend.values, 1)[0])


def _direction(slope: float, scale: float) -> str:
    dead = 0.001 * (scale + 1.0)
    if slope > dead:
        return "зростання"
    if slope < -dead:
        return "спад"
    return "стабільний"


def change_points(series: pd.Series, max_bkps: int = 5) -> list:
    """Точки зміни режиму (ruptures.Pelt). Порожньо, якщо бібліотека недоступна."""
    try:
        import ruptures as rpt
    except Exception:
        return []
    signal = series.astype(float).values
    algo = rpt.Pelt(model="rbf").fit(signal)
    bkps = algo.predict(pen=10)
    dates = [series.index[b - 1] for b in bkps if 0 < b < len(series)]
    return dates[:max_bkps]


def analyze(series: pd.Series, period: int = 7) -> dict:
    """Зведені метрики рівня 2 для агента/судді + компоненти для графіків."""
    comp = stl_decompose(series, period=period)
    slope = trend_slope(comp["trend"])
    cps = change_points(series)
    return {
        "components": comp,
        "trend_slope": round(slope, 4),
        "trend_direction": _direction(slope, float(series.mean())),
        "change_points": cps,
        "n_change_points": len(cps),
    }
