# Task 3 — Analysis core (R3)

## Опис
Реалізувати детерміновані рівні аналізу 1–5. Ґрунт: `Docs/{trend,anomaly,forecast,pattern}_agent_research.md`. Кожна функція повертає і числові результати, і компактний словник метрик для агентів.

## Обсяг
- `analysis/descriptive.py` (Рівень 1): загальні лічильники, топ-регіони, heatmap «година × день тижня», розподіл тривалостей.
- `analysis/decomposition.py` (Рівень 2): `statsmodels` STL(period=7, robust=True) → trend/seasonal/resid; нахил тренду (`np.polyfit`); опц. change-points (`ruptures.Pelt`).
- `analysis/anomaly.py` (Рівень 3): MAD z-score (поріг 3.5) на залишках STL + `IsolationForest(contamination=0.02)`; список дат-аномалій із severity.
- `analysis/forecast.py` (Рівень 4): Prophet(weekly_seasonality, interval_width=0.80) → yhat/lower/upper на N днів; seasonal-naive fallback; backtest MAE(14д).
- `analysis/patterns.py` (Рівень 5): KMeans на StandardScaler-профілях регіонів; k за silhouette (2..5); опис кластерів; пікові години.

## Критерії готовності
- Кожен модуль повертає метрики як `dict` (для агентів) + об'єкти для графіків.
- Юніт-тести на синтетичних рядах: STL дає тренд; anomaly ловить вставлений сплеск; forecast повертає N точок; patterns дає ≥2 кластери.
