"""Детерміновані авто-висновки (без LLM): текстові спостереження з порахованих метрик."""
from __future__ import annotations

import pandas as pd

from ..data import preprocess as pp
from . import anomaly, decomposition, descriptive, forecast, patterns

MIN_DAYS = 15
_WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def report(df: pd.DataFrame, region: str = "Уся Україна", start=None, end=None,
           horizon: int = 30) -> dict:
    """Зібрати KPI + список текстових висновків (українською) із детермінованих метрик."""
    sub = pp.filter_events(df, region, start, end)
    series = pp.daily_counts(sub)
    kpi = descriptive.summary(sub)
    conclusions: list[str] = []

    if len(series) == 0:
        return {"kpi": kpi, "conclusions": ["Немає даних за обраний період/регіон."],
                "series": series, "n_days": 0}

    conclusions.append(
        f"За період зафіксовано {len(sub)} тривог у «{region}», у середньому "
        f"{series.mean():.1f} на день; найактивніший день — {series.idxmax():%Y-%m-%d} "
        f"({int(series.max())} тривог)."
    )

    if len(series) >= MIN_DAYS:
        dec = decomposition.analyze(series)
        conclusions.append(
            f"Тренд: {dec['trend_direction']} (нахил {dec['trend_slope']:+.4f}/день; "
            f"виявлено {dec['n_change_points']} точок зміни режиму)."
        )
        an = anomaly.detect(series)
        if an["count"]:
            conclusions.append(
                f"Виявлено {an['count']} аномальних днів-сплесків; найзначніші: "
                f"{', '.join(an['top']) or '—'}."
            )
        fc = forecast.forecast(series, horizon=horizon)
        conclusions.append(
            f"Прогноз ({fc['method']}) на {horizon} днів: очікувано ~{fc['mean_yhat']:.1f} тривог/день "
            f"(нещодавнє середнє {fc['recent_mean']:.1f}; MAE бектесту {fc['mae_backtest']})."
        )
    else:
        conclusions.append("Замало днів для тренду/прогнозу (потрібно ≥ 15).")

    peak_h = pp.hourly_profile(sub).sort_values(ascending=False).head(3).index.tolist()
    peak_wd = pp.weekday_profile(sub).sort_values(ascending=False).head(2).index.tolist()
    conclusions.append(
        f"Сезонність: піки о {', '.join(f'{h:02d}:00' for h in peak_h)}; "
        f"найактивніші дні тижня — {', '.join(_WD[d] for d in peak_wd)}."
    )

    if region == "Уся Україна":
        pat = patterns.analyze(df)
        conclusions.append(
            f"Регіони групуються у {pat['k']} кластери за профілем тривог "
            f"(silhouette {pat['silhouette']})."
        )

    return {"kpi": kpi, "conclusions": conclusions, "series": series, "n_days": int(len(series))}
