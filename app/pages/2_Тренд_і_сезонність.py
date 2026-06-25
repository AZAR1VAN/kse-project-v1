"""Рівень 2 — тренд і сезонність (STL)."""
import _shared as sh
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Тренд і сезонність", page_icon="📈", layout="wide")
st.title("📈 Тренд і сезонність (STL)")

region, start, end = sh.sidebar_filters()
res = sh.decomposition_res(region, start, end)
if res is None:
    st.warning("Для декомпозиції потрібно щонайменше 15 днів даних.")
    st.stop()

s = sh.series(region, start, end)
comp = res["components"]

c1, c2, c3 = st.columns(3)
c1.metric("Нахил тренду /день", res["trend_slope"])
c2.metric("Напрям", res["trend_direction"])
c3.metric("Точок зміни режиму", res["n_change_points"])

st.subheader("Факт і тренд")
fig = go.Figure()
fig.add_scatter(x=s.index, y=s.values, name="Факт", line=dict(color="lightgray"))
fig.add_scatter(x=comp["trend"].index, y=comp["trend"].values, name="Тренд", line=dict(color="crimson"))
for cp in res["change_points"]:
    fig.add_vline(x=cp, line=dict(dash="dot", color="orange"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Сезонна компонента (тижнева, перші 8 тижнів)")
seas = comp["seasonal"].iloc[:56]
st.plotly_chart(px.line(x=seas.index, y=seas.values, labels={"x": "Дата", "y": "Сезонність"}),
                use_container_width=True)

st.subheader("Залишки (resid)")
st.plotly_chart(px.line(x=comp["resid"].index, y=comp["resid"].values,
                        labels={"x": "Дата", "y": "Залишок"}), use_container_width=True)
