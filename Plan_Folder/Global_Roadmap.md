# Global Roadmap — Аналіз часових рядів повітряних тривог в Україні

> Сформовано **оркестратором** на основі досліджень агентів у `Docs/` (data, trend, anomaly, forecast, pattern, orchestrator, judge).

## Мета продукту
Веб-застосунок (Streamlit), що дає **багаторівневий аналіз** історичних повітряних тривог в Україні (тренди, сезонність, аномалії, прогноз, регіональні патерни) з **перевіреними суддею** текстовими висновками від мультиагентної системи **Оркестратор → Агенти → Суддя**.

## Підтверджені вхідні факти з Docs
- **Дані** (`data_agent_research.md`): `raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/volunteer_data_en.csv`, колонки `region, started_at, finished_at, naive`, UTC, ~101 969 рядків, 25 регіонів, 2022-02-25 → 2026-06-25.
- **Аналіз** (`trend/anomaly/forecast/pattern`): STL(period=7, robust), MAD z-score (3.5) + IsolationForest(contamination=0.02), Prophet(weekly, interval_width=0.80) + seasonal-naive fallback + backtest MAE(14д), KMeans+StandardScaler+silhouette.
- **Мультиагент** (`orchestrator/judge`): `claude -p "<prompt>" --output-format json`, парсити поле `result` (або `structured_output` з `--json-schema`), перевіряти `is_error`; timeout 90с (суддя 120с); смоук-тест пройшов; graceful fallback на детерміновані правила.

## Мілстоуни
| ID | Назва | Мета | Артефакт | Джерело в Docs |
|----|-------|------|----------|----------------|
| R1 | Foundation | Каркас репо, залежності, git+origin, лог | `requirements.txt`, `.gitignore`, git repo | — |
| R2 | Data layer | Завантаження+препроцес CSV → часові ряди | `src/airalerts/data/*` | data_agent |
| R3 | Analysis core | Рівні 1–5 детермінованого аналізу | `src/airalerts/analysis/*` | trend/anomaly/forecast/pattern |
| R4 | Авто-висновки (без LLM) | Детерміновані текстові висновки з метрик | `src/airalerts/analysis/insights.py` | *(LLM-шар прибрано за рішенням замовника — див. log.md)* |
| R5 | Web UI | Streamlit multipage дашборд | `app/*` | — |
| R6 | Test & verify | pytest + Playwright скріншоти | `tests/*`, скріншоти | — |
| R7 | Docs & ship | README, фіналізація Plan_Folder, коміт+пуш | README, git push | — |

Кожен мілстоун має `Task{N}.md` (опис+критерії готовності) і `Plan{N}.md` (кроки з verify).

## Послідовність і залежності
R1 → R2 → R3 → R4 → R5 → R6 → R7. R4 залежить від R3 (метрики як ґрунт для агентів). R5 залежить від R2–R4. R6 верифікує R2–R5.
