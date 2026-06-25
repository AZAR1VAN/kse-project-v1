"""Оркестратор: data → метрики (детерміновано) → агенти (claude CLI / fallback) → Суддя → звіт."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd

from ..analysis import anomaly, decomposition, forecast
from ..data import preprocess as pp
from . import agents as ag
from . import claude_cli, judge

MIN_DAYS = 15  # мінімум для STL/прогнозу (≥ 2 тижневі періоди)


def _filter(df: pd.DataFrame, region: str | None, start, end) -> pd.DataFrame:
    sub = df
    if region and region != "Уся Україна":
        sub = sub[sub["region"] == region]
    if start is not None:
        sub = sub[sub["started_at"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        sub = sub[sub["started_at"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return sub


def build_context(df: pd.DataFrame, region: str, start, end, horizon: int = 30) -> dict:
    """Детерміновані метрики (grounding) для агентів."""
    sub = _filter(df, region, start, end)
    series = pp.daily_counts(sub)
    ctx = {"region": region, "n_days": int(len(series)), "n_events": int(len(sub))}

    busiest_day = series.idxmax() if len(series) else None
    ctx["summary"] = {
        "total": int(len(sub)),
        "mean_per_day": round(float(series.mean()), 2) if len(series) else 0.0,
        "busiest_day": busiest_day.strftime("%Y-%m-%d") if busiest_day is not None else "—",
        "busiest_count": int(series.max()) if len(series) else 0,
    }

    if len(series) >= MIN_DAYS:
        dec = decomposition.analyze(series)
        ctx["trend"] = {"slope": dec["trend_slope"], "direction": dec["trend_direction"],
                        "n_change_points": dec["n_change_points"]}
        ctx["_components"] = dec["components"]
        an = anomaly.detect(series)
        ctx["anomaly"] = {"count": an["count"], "top": an["top"],
                          "all_dates": an["anomaly_dates"]}
        ctx["_anomalies"] = an["anomalies"]
        fc = forecast.forecast(series, horizon=horizon)
        ctx["forecast"] = {"method": fc["method"], "mean_yhat": fc["mean_yhat"],
                           "recent_mean": fc["recent_mean"], "mae": fc["mae_backtest"],
                           "horizon": horizon}
        ctx["_forecast"] = fc["forecast"]
    else:
        ctx["trend"] = {"slope": 0.0, "direction": "стабільний", "n_change_points": 0}
        ctx["anomaly"] = {"count": 0, "top": [], "all_dates": []}
        ctx["forecast"] = {"method": "n/a", "mean_yhat": ctx["summary"]["mean_per_day"],
                           "recent_mean": ctx["summary"]["mean_per_day"], "mae": float("nan"),
                           "horizon": horizon}

    wd = pp.weekday_profile(sub)
    ctx["seasonality"] = {
        "peak_hours": pp.hourly_profile(sub).sort_values(ascending=False).head(3).index.tolist(),
        "peak_weekdays": wd.sort_values(ascending=False).head(2).index.tolist(),
    }
    ctx["series"] = series
    return ctx


def _metric_pool(metrics: dict) -> list[float]:
    """Зібрати всі числові значення з метрик (рекурсивно) — допустимі числа для перевірки R3."""
    pool: list[float] = []

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            pool.append(float(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(metrics)
    return pool


def select_agents(question: str | None) -> list[str]:
    """Роутер. Без питання — повний набір; з питанням — релевантні + завжди Summary/Trend."""
    if not question:
        return list(ag.AGENTS.keys())
    q = question.lower()
    chosen = ["SummaryAgent", "TrendAgent"]
    if any(w in q for w in ("сплеск", "аномал", "пік")):
        chosen.append("AnomalyAgent")
    if any(w in q for w in ("прогноз", "майбут", "очіку")):
        chosen.append("ForecastAgent")
    if any(w in q for w in ("годин", "день тижня", "сезон", "патерн")):
        chosen.append("SeasonalityAgent")
    return list(dict.fromkeys(chosen))


def analyze(df: pd.DataFrame, region: str = "Уся Україна", start=None, end=None,
            question: str | None = None, use_llm: bool = True, horizon: int = 30) -> dict:
    """Головна точка входу мультиагентного аналізу."""
    ctx = build_context(df, region, start, end, horizon=horizon)
    names = select_agents(question)
    funcs = [(n, ag.AGENTS[n]) for n in names]

    llm = use_llm and claude_cli.available()
    if llm:
        with ThreadPoolExecutor(max_workers=len(funcs)) as ex:
            outputs = list(ex.map(lambda nf: nf[1](ctx, question, True), funcs))
    else:
        outputs = [f(ctx, question, False) for _, f in funcs]

    used_llm = any(o.source == "claude_cli" for o in outputs)
    public_metrics = {k: ctx[k] for k in ("summary", "trend", "anomaly", "forecast", "seasonality")}
    pool = _metric_pool(public_metrics) + [float(ctx["n_days"]), float(horizon)]
    verified = judge.judge(outputs, metric_pool=pool, mode_llm=used_llm)
    return {
        "region": region,
        "period": [str(start) if start else None, str(end) if end else None],
        "question": question,
        "metrics": public_metrics,
        "agents": [asdict(o) for o in outputs],
        "verified": verified,
        "llm_used": used_llm,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
