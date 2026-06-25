# Дослідження: ОРКЕСТРАТОР (Orchestrator)

> Контекст проєкту: веб-застосунок (Streamlit + Python) для аналізу часових рядів попереджень
> про повітряну тривогу в Україні. Архітектура мультиагентності: **Оркестратор → Агенти → Суддя**.
>
> **КРИТИЧНЕ ОБМЕЖЕННЯ:** усе LLM-міркування агентів і судді йде **виключно через CLI `claude`**
> (вже автентифікований: `/home/root1/.local/bin/claude`), що викликається як підпроцес у headless-режимі.
> **НЕ** використовуємо Anthropic API і **НЕ** використовуємо API-ключ. Детерміновану статистику
> обчислює Python, а LLM лише **інтерпретує/валідує** вже готові числа (grounding).

---

## Роль

Оркестратор — це центральний координатор. Він **не рахує** статистику сам і **не виносить вердиктів**
сам; він керує потоком даних між компонентами:

1. **Приймає запит** користувача зі Streamlit-форми: `region` (область), `date_range` (діапазон дат),
   необов'язкове вільне `question` (питання користувача).
2. **Вирішує, яких агентів запускати** (роутинг) — залежно від запиту й питання.
3. **Готує grounding-метрики** детерміновано в Python (тренд, аномалії/сплески, сезонність, статистика)
   і передає їх кожному агентові як «джерело істини».
4. **Запускає агентів**: кожен агент отримує свої Python-метрики + короткий запит на LLM-інтерпретацію
   (через CLI `claude`), і повертає структурований результат `AgentOutput`.
5. **Збирає всі результати** в компактний пакет і **передає Судді** на крос-перевірку.
6. **Повертає консолідований звіт** (verified report) у Streamlit для відображення.

Оркестратор також відповідає за **бюджет токенів/контексту** (context discipline): метрики передаються
до LLM у згорнутому, агрегованому вигляді (не сирий часовий ряд), а резюме агентів обмежені за довжиною.

Принцип «LLM-as-judge»: числа — детерміновані (Python), вердикт про якість/несуперечливість — окремий
крок Судді. Це знижує ризик галюцинацій, бо LLM ніколи не «вигадує» статистику — він лише пояснює надане.

---

## Протокол виклику агентів

### Перелік агентів (приклад для домену тривог)

| Агент | Python-метрики (grounding) | Завдання LLM (через `claude`) |
|---|---|---|
| `TrendAgent` | нахил лінії тренду (slope), знак, p-value, % зміни | пояснити напрям/силу тренду словами |
| `AnomalyAgent` | список дат-сплесків (z-score / IQR), значення, поріг | проінтерпретувати сплески, можливі причини-гіпотези |
| `SeasonalityAgent` | години/дні з піками, амплітуда, періодограма | описати добові/тижневі патерни |
| `SummaryAgent` | агреговані KPI (всього, середнє/день, max-день) | стислий людський підсумок періоду |

Набір агентів **модульний**: роутер обирає підмножину.

### Роутинг (яких агентів запускати)

```
def select_agents(query) -> list[str]:
    agents = ["SummaryAgent"]                  # завжди
    if query.wants_trend or query.question is None:
        agents.append("TrendAgent")
    if query.wants_anomalies or "сплеск"/"аномал" in question:
        agents.append("AnomalyAgent")
    if query.wants_seasonality or "годин"/"день тижня" in question:
        agents.append("SeasonalityAgent")
    return agents
```

Якщо `question` порожнє — запускаємо повний дефолтний набір (Summary+Trend+Anomaly).

### Послідовність виконання (псевдокод оркестратора)

```
def run(query):
    series = load_series(query.region, query.date_range)     # CSV Vadimkin (MIT)
    metrics = compute_metrics(series)                         # детерміновано, Python
    agent_names = select_agents(query)

    agent_outputs = []
    for name in agent_names:
        m = metrics[name]                                     # підмножина метрик для агента
        interpretation = llm_interpret(name, m, query.question)  # через claude CLI (з fallback)
        agent_outputs.append(AgentOutput(
            agent=name, metrics=m, claims=interpretation, source=interpretation.source
        ))

    verified = judge(agent_outputs, metrics)                  # Суддя (див. judge_research.md)
    return build_report(query, agent_outputs, verified)
```

Агенти **між собою не спілкуються** і не залежать один від одного → можна виконувати їх паралельно
(`concurrent.futures.ThreadPoolExecutor`), бо кожен виклик `claude` — це окремий незалежний підпроцес.
Загальний таймаут на агента = таймаут підпроцесу (нижче).

---

## Виклик claude CLI (підтверджено)

> Усе нижче **перевірено емпірично** на цій машині (`claude --help` + два smoke-тести).

### Підтверджені прапорці

- `-p, --print` — headless/неінтерактивний режим (друкує відповідь і виходить). **Обов'язковий.**
- `--output-format <format>` — `text` (типово), **`json`** (єдиний результат), `stream-json`.
  Працює лише разом із `--print`.
- `--model <model>` — модель/аліас (`opus`, `sonnet`, …); за замовчуванням `claude-opus-4-8`.
  Для агентів-інтерпретаторів економно ставити `--model sonnet` (швидше/дешевше); Суддю краще тримати
  на `--model opus` для точніших перевірок.
- `--json-schema <schema>` — JSON Schema для **структурованого виводу** (валідований). Дуже корисно
  для агентів і Судді, щоб одразу отримати машинно-читаний об'єкт.
- `--append-system-prompt <text>` — додати системну інструкцію (напр. «Ти статистичний валідатор…»).

### Точна команда, яку використовуємо

Простий текстовий результат:

```bash
claude -p "<PROMPT>" --output-format json
```

Структурований результат (рекомендовано для агентів/судді):

```bash
claude -p "<PROMPT>" \
  --model sonnet \
  --output-format json \
  --json-schema '{"type":"object","properties":{"summary":{"type":"string"},"trend":{"type":"string","enum":["increasing","decreasing","flat"]},"confidence":{"type":"number"}},"required":["summary","trend"]}'
```

### Як парсити stdout

CLI друкує **один рядок JSON**. Розбір через `json.loads(stdout)`. Релевантні поля (підтверджено):

| Поле | Призначення |
|---|---|
| `result` | **головний текст відповіді LLM** (рядок). Це поле парсимо для текстового виводу. |
| `structured_output` | присутнє, якщо передано `--json-schema`; **готовий об'єкт** за схемою (напр. `{"trend":"increasing","confidence":1}`). Беремо його замість парсингу `result`. |
| `is_error` | `false`/`true` — чи була помилка. Перевіряти **перед** використанням `result`. |
| `subtype` | `"success"` за успіху. |
| `duration_ms` | тривалість (для метрик/логів). |
| `session_id` | ід сесії (для дебагу/логів). |

Приклад фактичного виводу smoke-тесту:
`{"type":"result","subtype":"success","is_error":false,...,"result":"OK","session_id":"...","duration_ms":3645,...}`

### Обгортка-виклик у Python (підтверджений патерн)

```python
import json, subprocess, shutil

CLAUDE_BIN = shutil.which("claude") or "/home/root1/.local/bin/claude"
CLAUDE_TIMEOUT_S = 90   # рекомендований таймаут підпроцесу (див. нижче)

def call_claude(prompt: str, *, model: str = "sonnet", schema: dict | None = None) -> dict:
    cmd = [CLAUDE_BIN, "-p", prompt, "--model", model, "--output-format", "json"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=CLAUDE_TIMEOUT_S, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout"}
    if proc.returncode != 0:
        return {"ok": False, "reason": f"exit:{proc.returncode}", "stderr": proc.stderr[:500]}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "bad_json", "raw": proc.stdout[:500]}
    if payload.get("is_error"):
        return {"ok": False, "reason": "cli_error", "raw": payload}
    return {
        "ok": True,
        "text": payload.get("result", ""),
        "structured": payload.get("structured_output"),
        "duration_ms": payload.get("duration_ms"),
    }
```

### Рекомендований таймаут підпроцесу

- Емпірична латентність: ~**3.6 с** (простий промпт, JSON) і ~**12 с** (промпт + `--json-schema`).
- Перший виклик («холодний») може бути повільнішим; модель `opus` повільніша за `sonnet`.
- **Рекомендація: `timeout=90` с** на один виклик агента/судді (запас на холодний старт і чергу).
  Для Судді на `opus` можна `timeout=120`. Streamlit має показати спінер під час очікування.
- Завжди ловимо `subprocess.TimeoutExpired` і переходимо у Fallback (нижче). Ніколи не блокуємо UI назавжди.

### Дисципліна контексту (context discipline)

- У промпт **не вкладаємо сирий часовий ряд** — лише агреговані метрики (кілька чисел, ≤ 1–2 КБ).
- Просимо коротку відповідь: `--json-schema` з полем `summary` (≤ 2–3 речення) тримає вивід компактним.
- Резюме кожного агента, що йде до Судді, обмежуємо (напр. ≤ 80 слів), щоб контекст Судді лишався малим.

---

## Формат повідомлень

### Запит → Оркестратор (`OrchestratorQuery`)

```json
{
  "region": "Київська область",
  "date_range": ["2023-01-01", "2023-12-31"],
  "question": "Чи зростала кількість тривог і коли були найбільші сплески?"
}
```

### Оркестратор → Агент (вхід)

```json
{
  "agent": "TrendAgent",
  "metrics": {"slope_per_day": 0.42, "slope_sign": "positive",
              "pct_change": 18.7, "p_value": 0.003, "n_points": 365},
  "question": "Чи зростала кількість тривог...",
  "grounding_note": "Інтерпретуй ЛИШЕ надані числа. Не вигадуй значень."
}
```

### Агент → Оркестратор (`AgentOutput`) — компактний

```json
{
  "agent": "TrendAgent",
  "metrics": {"slope_per_day": 0.42, "slope_sign": "positive", "pct_change": 18.7},
  "claims": {
    "summary": "Спостерігається помірне зростання кількості тривог протягом року.",
    "trend": "increasing",
    "confidence_self": 0.8
  },
  "source": "claude_cli"
}
```

Поле `source` має значення `"claude_cli"` (LLM відповів) або `"deterministic_fallback"`
(шаблонна інтерпретація — див. нижче). Суддя враховує `source` при оцінці.

### Оркестратор → Суддя (вхід)

```json
{
  "metrics_ground_truth": { "...повний набір детермінованих метрик..." },
  "agent_outputs": [ { "...AgentOutput 1..." }, { "...AgentOutput 2..." } ]
}
```

### Оркестратор → UI (фінально) — повертає об'єднання `agent_outputs` + `verified_report`
(структуру `verified_report` див. у `judge_research.md`).

---

## Fallback

**Мета:** застосунок повинен працювати, навіть якщо CLI `claude` недоступний, відповів помилкою або
вийшов за таймаут. Жоден збій LLM не повинен «ламати» сторінку — метрики все одно детерміновані.

### Коли спрацьовує Fallback

- `claude` не знайдено (`shutil.which` повернув `None`);
- `subprocess.TimeoutExpired` (перевищено `CLAUDE_TIMEOUT_S`);
- ненульовий код виходу або `is_error: true`;
- невалідний JSON у stdout.

### Поведінка агента у Fallback (детермінована шаблонна інтерпретація)

Агент **не падає** — він формує інтерпретацію з готового шаблону на основі своїх Python-метрик:

```python
def templated_trend(m) -> dict:
    if m["slope_sign"] == "positive":
        verdict = "increasing"; word = "зростання"
    elif m["slope_sign"] == "negative":
        verdict = "decreasing"; word = "спадання"
    else:
        verdict = "flat"; word = "стабільність"
    return {
        "summary": f"Тренд показує {word} (нахил {m['slope_per_day']:.2f}/день, "
                   f"зміна {m['pct_change']:.1f}%).",
        "trend": verdict,
        "confidence_self": 0.6,        # нижча самовпевненість без LLM
    }
```

Результат повертається з `source="deterministic_fallback"`. Числа ідентичні — змінюється лише текст
пояснення (шаблон замість LLM).

### Поведінка Судді у Fallback

Якщо LLM-Суддя недоступний — Оркестратор викликає **правило-базований (rule-based) Суддю**, який
звіряє claims агента з `metrics_ground_truth` детерміновано (див. `judge_research.md` → «Детермінований
fallback»). Він так само видає `confidence` (0–1) і прапорці суперечностей, але без LLM.

### Прозорість для користувача

У звіті обов'язково позначаємо режим: `mode: "llm"` або `mode: "fallback"`, щоб користувач бачив,
чи були задіяні LLM-інтерпретації, чи лише детерміновані шаблони. Часткова деградація допустима:
частина агентів може бути на LLM, частина — на fallback (за таймаутом окремого виклику).
