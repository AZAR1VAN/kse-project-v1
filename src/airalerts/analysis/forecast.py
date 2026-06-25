"""Рівень 4 — прогноз кількості тривог (Prophet + seasonal-naive fallback)."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)


def _to_prophet_df(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"ds": series.index.tz_localize(None), "y": series.astype(float).values})


def _seasonal_naive(series: pd.Series, horizon: int, period: int = 7) -> pd.DataFrame:
    last = series.astype(float).values[-period:]
    yhat = [last[i % period] for i in range(horizon)]
    future = pd.date_range(series.index[-1].tz_localize(None) + pd.Timedelta(days=1), periods=horizon, freq="D")
    resid_std = float(np.std(series.astype(float).values[-period * 4:])) or 1.0
    return pd.DataFrame(
        {"ds": future, "yhat": yhat, "yhat_lower": np.clip(np.array(yhat) - resid_std, 0, None),
         "yhat_upper": np.array(yhat) + resid_std}
    )


def _prophet_forecast(series: pd.Series, horizon: int) -> pd.DataFrame:
    from prophet import Prophet

    m = Prophet(weekly_seasonality=True, daily_seasonality=False, interval_width=0.80)
    m.fit(_to_prophet_df(series))
    future = m.make_future_dataframe(periods=horizon)
    fc = m.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(horizon)
    fc[["yhat", "yhat_lower", "yhat_upper"]] = fc[["yhat", "yhat_lower", "yhat_upper"]].clip(lower=0)
    return fc.reset_index(drop=True)


def backtest_mae(series: pd.Series, h: int = 14) -> float:
    """MAE seasonal-naive на останніх h днях (швидка перевірка якості)."""
    if len(series) <= h + 7:
        return float("nan")
    train, test = series.iloc[:-h], series.iloc[-h:]
    pred = _seasonal_naive(train, h)["yhat"].values
    return round(float(np.mean(np.abs(pred - test.astype(float).values))), 2)


def forecast(series: pd.Series, horizon: int = 30) -> dict:
    """Прогноз на horizon днів. Prophet з graceful fallback на seasonal-naive."""
    method = "prophet"
    try:
        fc = _prophet_forecast(series, horizon)
    except Exception:
        method = "seasonal_naive"
        fc = _seasonal_naive(series, horizon)
    return {
        "forecast": fc,
        "method": method,
        "horizon": horizon,
        "mae_backtest": backtest_mae(series),
        "mean_yhat": round(float(fc["yhat"].mean()), 1),
        "recent_mean": round(float(series.astype(float).tail(horizon).mean()), 1),
    }
