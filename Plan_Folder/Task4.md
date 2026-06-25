# Task 4 — Multi-agent (R4)

## Опис
Реалізувати мультиагентну систему **Оркестратор → Агенти → Суддя** через `claude` CLI (без API key). Ґрунт: `Docs/orchestrator_research.md`, `Docs/judge_research.md`.

## Обсяг
- `agents/claude_cli.py`: `ask(prompt, *, schema=None, model=None, timeout=90)` — `subprocess.run(["claude","-p",prompt,"--output-format","json", ...])`; парс `result` (або `structured_output`); перевірка `is_error`; `ClaudeUnavailable` при таймауті/відсутності CLI.
- `agents/agents.py`: спеціалізовані агенти TrendAgent, AnomalyAgent, ForecastAgent, PatternAgent, DescriptiveAgent — кожен бере метрики свого рівня (R3), формує промпт «інтерпретуй ці числа», повертає `{metrics, interpretation, source}`; при `ClaudeUnavailable` — детермінований шаблон.
- `agents/judge.py`: для кожного агента звіряє твердження інтерпретації з реальними метриками (знак тренду, наявність дати-сплеску, узгодженість прогнозу), ставить confidence 0–1, позначає суперечності; детермінований fallback.
- `agents/orchestrator.py`: `analyze(region, start, end, question=None)` — рахує метрики (R3), диспетчеризує агентів, передає Судді, повертає консолідований звіт.

## Критерії готовності
- `orchestrator.analyze(...)` повертає звіт зі списком findings + confidence.
- Якщо в інтерпретацію підкласти невірне число — суддя знижує confidence/позначає.
- Працює і без `claude` CLI (fallback), і з ним.
