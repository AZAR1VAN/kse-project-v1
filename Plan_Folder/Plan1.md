# Plan 1 — Foundation (R1)

1. Створити `requirements.txt` зі стеком (Streamlit/Plotly/pandas/numpy/requests/statsmodels/scikit-learn/prophet/ruptures/pytest). → *verify:* файл існує, лише не-AGPL.
2. Створити `pyproject.toml`/`setup.cfg` мінімальний АБО покладатися на `PYTHONPATH=src` + `pytest.ini`. Обрано: `pyproject.toml` з `[tool.pytest.ini_options] pythonpath=["src"]`. → *verify:* pytest бачить пакет.
3. Створити `__init__.py` у `airalerts` та підпакетах. → *verify:* `python -c "import airalerts"`.
4. Створити `.gitignore`. → *verify:* кеш/venv ігноруються.
5. Створити `data_cache/.gitkeep`.
6. Створити venv через `uv venv`, встановити залежності `uv pip install -r requirements.txt`. → *verify:* установка успішна.
7. `git init -b work`, додати файли, коміт; `git remote add origin <repo>`. → *verify:* `git log` має коміт, `git remote -v` показує origin.
