# Plan 2 — Data layer (R2)

1. `data/loader.py`: константа RAW_URL; `load(force=False)` — якщо `data_cache/volunteer_data_en.csv` відсутній або `force`, завантажити через `requests`; інакше читати локально; `pandas.read_csv`. → *verify:* `df.shape[0] > 50000`, є колонки `region, started_at, finished_at`.
2. `data/preprocess.py`:
   - `clean(df)`: `pd.to_datetime(..., utc=True)`; заповнити `finished_at` = `started_at + 30min` де NaT/naive; `duration_min`; відкинути рядки де `finished_at < started_at`. → *verify:* немає NaT у часах, немає від'ємних тривалостей.
   - `daily_counts(df, region=None)`: фільтр за регіоном; `groupby(date).size()`; `reindex` повним діапазоном дат, `fillna(0)`. → *verify:* індекс безперервний, без пропусків.
   - `hourly_profile(df)`, `weekday_profile(df)`, `region_totals(df)`, `daily_duration(df)`. → *verify:* суми узгоджені з кількістю подій.
3. Тест `tests/test_preprocess.py` на маленькому синтетичному df: перевірити заповнення кінця, тривалість, безперервність денного ряду. → *verify:* `pytest tests/test_preprocess.py` зелений.
