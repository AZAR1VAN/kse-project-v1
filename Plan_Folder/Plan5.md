# Plan 5 — Web UI (R5)

1. `app/_shared.py`: `@st.cache_data load_data()`, `sidebar_filters()` (регіон select, період date_input) повертає `(region, start, end)`; спільні хелпери Plotly. → *verify:* імпортується, фільтри віддають значення.
2. `Home.py`: заголовок/опис проблеми; виклик `sidebar_filters`; KPI (всього тривог, сер. тривалість, активних регіонів). → *verify:* стартує, показує KPI.
3. Сторінки 1–5: кожна бере відфільтровані дані → відповідний модуль `analysis` → Plotly-графік(и) + `st.dataframe`. → *verify:* кожна рендериться без винятків.
4. Сторінка 6 (мультиагент): форма/кнопка → `orchestrator.analyze(region,start,end)`; рендер findings (expander на агента) + бейдж confidence + статус `source`. Прогрес `st.spinner`. → *verify:* повертає звіт; працює і в fallback.
5. `.streamlit/config.toml`: тема, `runOnSave`. → *verify:* застосунок не падає на старті.
6. Прогнати `streamlit run` у фоні; зафіксувати порт для R6. → *verify:* HTTP 200 на `/`.
