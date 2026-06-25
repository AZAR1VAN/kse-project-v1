# Plan 4 — Авто-висновки (R4) *(переосмислено: без LLM)*

1. Додати `data/preprocess.filter_events(df, region, start, end)` (регіон + діапазон дат, end включно).
   → *verify:* фільтрує події коректно.
2. `analysis/insights.py::report(...)`: фільтр → денний ряд → KPI (`descriptive`) → тренд (`decomposition`)
   → аномалії (`anomaly`) → прогноз (`forecast`) → сезонність (профілі) → кластери (`patterns`, лише для
   «Уся Україна»). Повернути `{kpi, conclusions, series, n_days}`. → *verify:* на Києві видає 5–6 висновків.
3. Видалити пакет `src/airalerts/agents/` і `tests/test_agents.py` (LLM-шар). → *verify:* `grep -r claude src`
   нічого не знаходить; тести зелені.
4. Зафіксувати зміну обсягу в `log.md` і `Global_Roadmap.md`. → *verify:* записи наявні.
