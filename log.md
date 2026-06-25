# Журнал проєкту (log.md)

> Обов'язковий журнал: запити користувача, початковий промпт, дії/активність асистента, відповіді. Дописується протягом усієї роботи.

---

## 2026-06-25 — Сесія 1

### Запит користувача (початковий промпт, дослівно по суті)
- **Обов'язково спочатку** логувати всі запити, початковий промпт, мою активність/дії та відповіді у файл `log.md` у теці проєкту.
- **Обов'язково спочатку** використати скіли: `andrej-karpathy-skills`, `graphify` (економія токенів), `playwright cli` (тести + скріншоти), та інші скіли з `/allskills/`.
- **Мета:** створити веб-застосунок, що вирішує проблему **аналізу часових рядів попереджень про повітряну тривогу в Україні**.
- Закомітити проєкт у `https://github.com/AZAR1VAN/kse-project-v1.git`.
- Має бути **багаторівнева система аналізу**. Алгоритм мультиагентності: **Оркестратор → Агенти → Суддя**.
- Створити **RoadMap** і **Tasks** (на кожен пункт RoadMap), і на основі Tasks сформувати **план**.
- Формат `Plan_Folder`: `Docs/*`, `Global_Roadmap.md`, `Task{N}.md` + `Plan{N}.md`.
- Зберегти результати дослідження/імплементації кожного агента, судді, оркестратора в `Plan_Folder/Docs`.
- Оркестратор має сформувати RoadMap/Task/Plan на основі файлів-досліджень агентів у `Docs`.
- Використовувати готові бібліотеки/модулі; запропонувати оптимальний стек (python тощо); використовувати готові компоненти, не генерувати код наявних у фреймворку компонентів; **не використовувати AGPL**.

### Уточнення користувача (AskUserQuestion)
1. Веб-стек → **Streamlit**.
2. Мультиагентність → **через Claude Code / `claude` CLI**, без Anthropic API key, без SDK (все вже автентифіковано через claude cli).
3. Дані → **історичний CSV Vadimkin** (MIT), без live-API і без Kaggle.

### Активність асистента (Phase 0 — планування)
- Дослідив `/home/root1/kse/project1/allskills/allskills/` (andrej-karpathy-skills, ponytail, graphify, playwright-skill, data-scientist, agent-squad, multi-agent-architect).
- Дослідив джерела даних (Vadimkin dataset — MIT; alerts_in_ua — MIT). Звірив схему CSV (oblast-level `volunteer_data_*.csv`, UTC, з 2022-02-25).
- Консультував skill `claude-api`: модель за замовч. `claude-opus-4-8`; патерни multi-agent + LLM-as-judge.
- Написав і **затвердив** план: `/home/root1/.claude/plans/rippling-riding-clarke.md`.

### Активність асистента (Phase 0 — виконання)
- Створив структуру тек `Plan_Folder/`, `Plan_Folder/Docs/`, `src/airalerts/{data,analysis,agents}`, `app/pages`, `tests`.
- Перевірив середовище: Python 3.12.3, uv, node v22.22.2, **claude CLI присутній**, git 2.43.0.
- Створив цей `log.md`.
- Спавн 3 дослідницьких субагентів (через Claude Code) → записали 7 файлів у `Docs/`: data, trend, anomaly, forecast, pattern, orchestrator, judge.
  - Підтверджено: дані ~101 969 рядків, 25 регіонів, колонки `region, started_at, finished_at, naive`; `claude -p ... --output-format json` (поле `result`), смоук-тест пройшов, timeout 90с.
- Оркестратор синтезував `Global_Roadmap.md` + `Task{1..7}.md`/`Plan{1..7}.md` на основі Docs. **Phase 0 завершено.**

### R1 — Foundation
- Створив `requirements.txt` (усі не-AGPL), `pyproject.toml` (pytest pythonpath=src), `__init__.py`, `.gitignore`, `data_cache/.gitkeep`.
- `uv venv` (py3.12) + встановлення залежностей; перевірено імпорти core + prophet — OK.
- git: коміт R1 `8bfd8ef` (поверх наявного Initial commit), origin = kse-project-v1; гілка `main`.
- Виключив `allskills/` з трекінгу (вкладені git-репо) + у `.gitignore`; лишилось 31 файл проєкту. **R1 завершено.**

### R2 — Data layer
- `data/loader.py` (кеш Vadimkin CSV) + `data/preprocess.py` (нормалізація, безперервні денні ряди, профілі годин/днів, heatmap, `filter_events`). Тест `test_preprocess.py` (3) зелений. Реальні дані: 101 969 подій, 25 регіонів. Коміт `ea70a18`. **R2 завершено.**

### R3 — Analysis core
- `analysis/{descriptive,decomposition,anomaly,forecast,patterns}.py`: STL(period=7), MAD z-score+IsolationForest, Prophet(+seasonal-naive fallback, backtest MAE), KMeans+silhouette. Тести `test_analysis.py` (5) + реальний смоук (Київ) зелені. Коміт `5a8e311`. **R3 завершено.**

### R4 — спершу мультиагент через claude CLI, далі ЗМІНА ОБСЯГУ
- Реалізував `agents/{claude_cli,agents,judge,orchestrator}.py` (Оркестратор→Агенти→Суддя через `claude -p ... --output-format json`). Реальний прогін: llm_used=True, 5 агентів паралельно, після виправлень overall=1.0/verified, висновки українською. Коміт `170bf0d`. Тести `test_agents.py` (4) зелені.
- **Запит користувача:** «Чому LLM для прогнозування, якщо є готові алгоритми? Зроби простий TSA-скрипт (pandas + графіки + алгоритмічний прогноз).»
  - **Уточнення:** прогноз ніколи не робив LLM — він алгоритмічний (Prophet); LLM лише писав інтерпретації + суддя валідував.
  - **Рішення користувача (AskUserQuestion):** «Повністю алгоритмічний, без LLM» — прибрати шар `claude` CLI зовсім.
- **Виконано:** видалив пакет `src/airalerts/agents/` і `tests/test_agents.py`; додав детермінований `analysis/insights.py` (текстові авто-висновки з метрик, без LLM). Тести (8) зелені. **R4 переосмислено → авто-висновки без LLM.**
  - Файли `Docs/orchestrator_research.md`, `Docs/judge_research.md` залишені як історичний запис дослідження (LLM-підхід), але в продукті не використовуються.
  - Оновив `Global_Roadmap.md`, `Task4.md`, `Plan4.md` під нову модель (авто-висновки без LLM).

### Запит користувача (2): розташування логу + push у GitHub
- Користувач: «Не бачу, щоб ти зберігав лог-файл, як я просив, та не бачу push у GitHub».
- **Дія:** перенесено `log.md` з `Plan_Folder/` у **корінь проєкту** (`/home/root1/kse/project1/log.md`), як просив користувач спочатку. Далі журнал ведеться в корені.
- **Дія:** виконується `git push -u origin main` у `https://github.com/AZAR1VAN/kse-project-v1.git` (результат — нижче).
