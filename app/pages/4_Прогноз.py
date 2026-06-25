"""Рівень 4 — алгоритмічний прогноз (Prophet)."""
import _shared as sh
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Прогноз", page_icon="🔮", layout="wide")
st.title("🔮 Прогноз кількості тривог")

region, start, end = sh.sidebar_filters()
horizon = st.sidebar.slider("Горизонт прогнозу (днів)", 7, 60, 30)
res = sh.forecast_res(region, start, end, horizon)
if res is None:
    st.warning("Для прогнозу потрібно щонайменше 15 днів даних.")
    st.stop()

s = sh.series(region, start, end)
fc = res["forecast"]

c1, c2, c3 = st.columns(3)
c1.metric("Метод", res["method"])
c2.metric("Сер. прогноз /день", res["mean_yhat"])
c3.metric("MAE бектесту (14 дн.)", res["mae_backtest"])

hist = s.tail(120)
fig = go.Figure()
fig.add_scatter(x=hist.index.tz_localize(None), y=hist.values, name="Історія", line=dict(color="steelblue"))
fig.add_scatter(x=fc["ds"], y=fc["yhat_upper"], line=dict(width=0), showlegend=False, hoverinfo="skip")
fig.add_scatter(x=fc["ds"], y=fc["yhat_lower"], fill="tonexty", fillcolor="rgba(220,20,60,0.2)",
                line=dict(width=0), name="Довірчий інтервал (80%)", hoverinfo="skip")
fig.add_scatter(x=fc["ds"], y=fc["yhat"], name="Прогноз", line=dict(color="crimson"))
st.plotly_chart(fig, use_container_width=True)
st.caption("Прогноз обчислено алгоритмічно (Prophet; резерв — seasonal-naive). Без LLM.")
