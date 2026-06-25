"""Спільні утиліти Streamlit: дані, фільтри, кешовані обчислення (без LLM)."""
from __future__ import annotations

import pathlib
import sys

# src/ на шляху імпорту (запуск: `streamlit run app/Home.py` з кореня проєкту)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from airalerts.data import loader, preprocess as pp  # noqa: E402

ALL = "Уся Україна"


@st.cache_data(show_spinner="Завантаження даних про тривоги…")
def get_data() -> pd.DataFrame:
    return pp.clean(loader.load())


def sidebar_filters():
    """Глобальні фільтри (регіон, період) у бічній панелі."""
    df = get_data()
    st.sidebar.header("Фільтри")
    region = st.sidebar.selectbox("Регіон", [ALL] + pp.regions(df))
    dmin = df["started_at"].min().date()
    dmax = df["started_at"].max().date()
    default_start = (df["started_at"].max() - pd.Timedelta(days=365)).date()
    default_start = max(default_start, dmin)
    rng = st.sidebar.date_input("Період", (default_start, dmax), min_value=dmin, max_value=dmax)
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        start, end = rng
    else:
        start, end = default_start, dmax
    st.sidebar.caption("Дані: Vadimkin/ukrainian-air-raid-sirens-dataset (MIT), час UTC.")
    return region, start, end


@st.cache_data
def events(region, start, end) -> pd.DataFrame:
    return pp.filter_events(get_data(), region, start, end)


@st.cache_data
def series(region, start, end) -> pd.Series:
    return pp.daily_counts(events(region, start, end))


@st.cache_data
def decomposition_res(region, start, end):
    from airalerts.analysis import decomposition
    s = series(region, start, end)
    return decomposition.analyze(s) if len(s) >= 15 else None


@st.cache_data
def anomaly_res(region, start, end):
    from airalerts.analysis import anomaly
    s = series(region, start, end)
    return anomaly.detect(s) if len(s) >= 15 else None


@st.cache_data
def forecast_res(region, start, end, horizon):
    from airalerts.analysis import forecast
    s = series(region, start, end)
    return forecast.forecast(s, horizon=horizon) if len(s) >= 15 else None


@st.cache_data(show_spinner="Кластеризація регіонів…")
def patterns_res(_token: str):
    from airalerts.analysis import patterns
    return patterns.analyze(get_data())


@st.cache_data
def insights_res(region, start, end):
    from airalerts.analysis import insights
    return insights.report(get_data(), region, start, end)
