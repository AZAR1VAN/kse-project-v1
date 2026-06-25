"""Головна сторінка — опис проблеми, KPI та авто-висновки (без LLM)."""
import _shared as sh
import streamlit as st

st.set_page_config(page_title="Аналіз повітряних тривог", page_icon="🛡️", layout="wide")

st.title("🛡️ Аналіз часових рядів повітряних тривог в Україні")
st.markdown(
    "Багаторівневий **алгоритмічний** аналіз історичних повітряних тривог: описова статистика, "
    "тренд і сезонність (STL), аномалії-сплески, прогноз (Prophet) та кластеризація регіонів. "
    "Дані: волонтерський датасет Vadimkin (MIT), час UTC. Усі обчислення — детерміновані (без LLM)."
)

region, start, end = sh.sidebar_filters()
rep = sh.insights_res(region, start, end)
kpi = rep["kpi"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Усього тривог", f"{kpi['total_alerts']:,}".replace(",", " "))
c2.metric("Сер. тривалість, хв", kpi["avg_duration_min"])
c3.metric("Днів у періоді", rep["n_days"])
c4.metric("Найактивніший регіон", str(kpi["busiest_region"]))

st.subheader("Автоматичні висновки")
for c in rep["conclusions"]:
    st.markdown(f"- {c}")

st.info("Скористайтеся сторінками зліва: Огляд · Тренд і сезонність · Аномалії · Прогноз · Патерни.")
