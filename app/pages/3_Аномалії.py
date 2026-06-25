"""Рівень 3 — аномалії-сплески."""
import _shared as sh
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Аномалії", page_icon="🚨", layout="wide")
st.title("🚨 Аномалії-сплески")

region, start, end = sh.sidebar_filters()
res = sh.anomaly_res(region, start, end)
if res is None:
    st.warning("Для детекції аномалій потрібно щонайменше 15 днів даних.")
    st.stop()

s = sh.series(region, start, end)
an = res["anomalies"]

st.metric("Аномальних днів", res["count"])

fig = go.Figure()
fig.add_scatter(x=s.index, y=s.values, name="Тривог/день", line=dict(color="steelblue"))
if len(an):
    fig.add_scatter(x=an["date"], y=an["count"], mode="markers", name="Аномалія",
                    marker=dict(color="red", size=10, symbol="x"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Список аномалій (за значущістю)")
if len(an):
    tbl = an[["date", "count", "score", "confirmed_iforest"]].copy()
    tbl["date"] = tbl["date"].dt.strftime("%Y-%m-%d")
    tbl = tbl.rename(columns={"date": "Дата", "count": "Тривог", "score": "Z-оцінка",
                              "confirmed_iforest": "Підтв. IsolationForest"})
    st.dataframe(tbl, use_container_width=True, hide_index=True)
else:
    st.info("Аномалій не виявлено.")
