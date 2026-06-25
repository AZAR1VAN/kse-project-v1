"""Рівень 5 — патерни та кластеризація регіонів (KMeans)."""
import _shared as sh
import pandas as pd
import plotly.express as px
import streamlit as st

from airalerts.data import preprocess as pp

st.set_page_config(page_title="Патерни", page_icon="🗺️", layout="wide")
st.title("🗺️ Патерни та кластери регіонів")
st.caption("Кластеризація використовує всю Україну (всі регіони), незалежно від фільтра регіону.")

sh.sidebar_filters()  # показати ту саму бічну панель
df_all = sh.get_data()
res = sh.patterns_res(str(df_all["started_at"].max().date()))

c1, c2 = st.columns(2)
c1.metric("Кількість кластерів", res["k"])
c2.metric("Silhouette", res["silhouette"])

cl = pd.Series(res["clusters"], name="cluster")
totals = pp.region_totals(df_all)
dfc = pd.DataFrame({"Регіон": cl.index, "Кластер": cl.values})
dfc["Тривог"] = dfc["Регіон"].map(totals).fillna(0).astype(int)
dfc = dfc.sort_values("Тривог")

st.subheader("Регіони за кластерами")
st.plotly_chart(
    px.bar(dfc, x="Тривог", y="Регіон", color=dfc["Кластер"].astype(str), orientation="h",
           labels={"color": "Кластер"}),
    use_container_width=True,
)

st.subheader("Пікові години доби (вся Україна)")
st.write("Найактивніші години:", ", ".join(f"{h:02d}:00" for h in res["peak_hours"]))
