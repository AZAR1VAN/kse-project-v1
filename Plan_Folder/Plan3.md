# Plan 3 — Analysis core (R3)

1. `descriptive.py`: `summary(df)`, `top_regions(df, n)`, `hour_weekday_heatmap(df)`, `duration_stats(df)`. → *verify:* лічильники збігаються з `len(df)`.
2. `decomposition.py`: `stl_decompose(series, period=7)` → namedtuple/ dict (trend, seasonal, resid); `trend_slope(trend)`; `change_points(series)` (ruptures, опц., try/except). → *verify:* на синтетичному ряді з лінійним зростанням `trend_slope > 0`.
3. `anomaly.py`: `residual_anomalies(resid, thr=3.5)` (MAD z-score); `iforest_anomalies(features, contamination=0.02)`; `detect(series)` що поєднує. → *verify:* вставлений сплеск (×5) позначається як аномалія.
4. `forecast.py`: `forecast(series, horizon=30)` через Prophet; `_seasonal_naive` fallback у try/except (якщо prophet недоступний/падає); `backtest_mae(series, h=14)`. → *verify:* `len(result.forecast) == horizon`; fallback повертає валідний ряд.
5. `patterns.py`: `region_features(df)`; `cluster_regions(features, k=None)` (silhouette по 2..5); `peak_hours(df)`. → *verify:* ≥2 кластери, лейбли для всіх регіонів.
6. `tests/test_analysis.py` з синтетичними рядами для всіх п'яти. → *verify:* `pytest tests/test_analysis.py` зелений.
