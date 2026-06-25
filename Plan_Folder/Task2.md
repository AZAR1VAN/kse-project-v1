# Task 2 — Data layer (R2)

## Опис
Завантажити та закешувати історичний CSV Vadimkin, нормалізувати події тривог і побудувати часові ряди для аналізу. Ґрунт: `Docs/data_agent_research.md`.

## Обсяг
- `data/loader.py`: завантаження `volunteer_data_en.csv` з raw URL у `data_cache/`, локальний кеш (не качати повторно), повернення `pandas.DataFrame`.
- `data/preprocess.py`:
  - парс `started_at`/`finished_at` як UTC; для `naive=True`/відсутнього кінця — `finished_at = started_at + 30 хв`;
  - `duration_min`; фільтр інвалідних (кінець < початок);
  - білдери рядів: `daily_counts(region|all)`, `hourly_profile`, `weekday_profile`, `region_totals`, `daily_duration`.

## Критерії готовності
- `loader.load()` повертає непорожній df з колонками `region, started_at, finished_at`.
- Повторний виклик читає з кешу (без мережі).
- `preprocess.daily_counts(df)` повертає безперервний денний ряд (reindex по датах, нулі для днів без тривог).
- Юніт-тест на синтетичних даних проходить.
