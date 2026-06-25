# Task 1 — Foundation (R1)

## Опис
Підготувати каркас проєкту: пакет `airalerts`, файл залежностей (без AGPL), `.gitignore`, README-заглушку, ініціалізацію git і віддалений `origin`.

## Обсяг
- `requirements.txt`: streamlit, plotly, pandas, numpy, requests, statsmodels, scikit-learn, prophet, ruptures, pytest.
- `src/airalerts/__init__.py` та підпакети `data/`, `analysis/`, `agents/` з `__init__.py`.
- `.gitignore`: `__pycache__/`, `.venv/`, `*.pyc`, `data_cache/`, `graphify-out/`, `/tmp` скріншоти, `.streamlit/secrets*`.
- `git init`, `git add`, перший коміт; `git remote add origin https://github.com/AZAR1VAN/kse-project-v1.git`.

## Критерії готовності
- `pip install -r requirements.txt` (у venv) проходить без помилок.
- `python -c "import airalerts"` працює (PYTHONPATH=src).
- `git status` чистий після коміту; `origin` налаштований.
- Жодна залежність не є AGPL.
