"""Рівень 1 — описовий огляд."""
import _shared as sh
import plotly.express as px
import streamlit as st

from airalerts.data import preprocess as pp

st.set_page_config(page_title="Огляд", page_icon="📊", layout="wide")
st.title("📊 Огляд")

region, start, end = sh.sidebar_filters()
df = sh.events(region, start, end)
s = sh.series(region, start, end)
if len(s) == 0:
    st.warning("Немає даних за обраний період/регіон.")
    st.stop()

st.subheader("Кількість тривог по днях")
st.plotly_chart(
    px.line(x=s.index, y=s.values, labels={"x": "Дата", "y": "Тривог/день"}),
    use_container_width=True,
)

st.subheader("Найактивніші регіони")
tr = pp.region_totals(df).head(12)
st.plotly_chart(
    px.bar(x=tr.values, y=tr.index, orientation="h",
           labels={"x": "Кількість тривог", "y": "Регіон"}).update_yaxes(autorange="reversed"),
    use_container_width=True,
)

st.subheader("Розподіл: день тижня × година доби")
m = pp.hour_weekday_matrix(df)
wd = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
st.plotly_chart(
    px.imshow(m.values, x=[f"{h:02d}" for h in m.columns], y=wd, aspect="auto",
              color_continuous_scale="YlOrRd",
              labels={"x": "Година", "y": "День тижня", "color": "Тривог"}),
    use_container_width=True,
)
