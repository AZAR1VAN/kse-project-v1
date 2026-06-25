# Plan 4 — Multi-agent (R4)

1. `claude_cli.py`: `ask()` через `subprocess.run([...], capture_output=True, text=True, timeout=...)`; `json.loads(stdout)`; повернути `result`/`structured_output`; виключення `ClaudeUnavailable` (FileNotFoundError/TimeoutExpired/is_error). → *verify:* `ask("Reply OK")` повертає текст; неіснуючий бінар → fallback-виключення.
2. `agents.py`: базовий клас `Agent` (name, level, `run(metrics) -> Finding`); підкласи з власним промптом. `Finding = {agent, claim, metrics, interpretation, source}`; `source ∈ {"claude","fallback"}`. → *verify:* кожен агент повертає Finding на тестових метриках.
3. `judge.py`: `validate(finding) -> {confidence, issues}` з правилами: тренд (знак нахилу), аномалія (дата у списку), прогноз (yhat у межах ist. діапазону), патерни (кількість кластерів). `judge_all(findings) -> Report`. → *verify:* підкладене невірне твердження → confidence < 0.5 + issue.
4. `orchestrator.py`: `analyze(...)`: побудувати ряд (R2) → метрики (R3) → агенти (R4) → суддя → `Report{findings, verified, generated_at, source}`. Стислі резюме у звіті. → *verify:* повертає несуперечливий звіт на реальному зрізі (Київська обл., 90 днів).
5. `tests/test_agents.py`: fallback-режим (без CLI) детермінований і стабільний; суддя ловить невідповідність. → *verify:* `pytest tests/test_agents.py` зелений.
