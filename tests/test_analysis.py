import numpy as np
import pandas as pd

from airalerts.analysis import anomaly, decomposition, forecast, patterns


def _series(n=140, base=10.0, slope=0.0, spike_at=None, spike=0.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")
    weekly = 3 * np.sin(np.arange(n) * 2 * np.pi / 7)
    vals = base + slope * np.arange(n) + weekly + rng.normal(0, 1, n)
    vals = np.clip(vals, 0, None)
    if spike_at is not None:
        vals[spike_at] += spike
    return pd.Series(vals.round(), index=idx)


def test_decomposition_detects_upward_trend():
    s = _series(slope=0.5)
    res = decomposition.analyze(s)
    assert res["trend_slope"] > 0
    assert res["trend_direction"] == "зростання"
    assert set(res["components"]) == {"trend", "seasonal", "resid"}


def test_anomaly_catches_spike():
    spike_at = 100
    s = _series(spike_at=spike_at, spike=80)
    res = anomaly.detect(s)
    spike_date = s.index[spike_at].strftime("%Y-%m-%d")
    assert spike_date in res["anomaly_dates"]
    assert res["count"] >= 1


def test_forecast_returns_horizon_points():
    s = _series(n=120)
    res = forecast.forecast(s, horizon=21)
    assert len(res["forecast"]) == 21
    assert res["method"] in {"prophet", "seasonal_naive"}
    assert {"ds", "yhat", "yhat_lower", "yhat_upper"} <= set(res["forecast"].columns)


def test_seasonal_naive_fallback_shape():
    s = _series(n=60)
    fc = forecast._seasonal_naive(s, 10)
    assert len(fc) == 10
    assert (fc["yhat_lower"] <= fc["yhat_upper"]).all()


def test_patterns_clusters_distinct_regions():
    # 6 регіонів у 3 групах за годиною піку
    frames = []
    rng = np.random.default_rng(1)
    for i, peak in enumerate([2, 2, 14, 14, 20, 20]):
        n = 300
        starts = pd.Timestamp("2023-01-01", tz="UTC") + pd.to_timedelta(
            rng.integers(0, 120, n), unit="D"
        ) + pd.to_timedelta((peak + rng.integers(-1, 2, n)) % 24, unit="h")
        frames.append(pd.DataFrame({"region": f"R{i}", "started_at": starts}))
    df = pd.concat(frames, ignore_index=True)
    df["finished_at"] = df["started_at"] + pd.Timedelta(minutes=30)
    df["duration_min"] = 30.0
    res = patterns.analyze(df)
    assert res["k"] >= 2
    assert len(res["clusters"]) == 6
