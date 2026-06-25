# Дослідження: СУДДЯ (Judge / LLM-as-Judge)

> Контекст: мультиагентна система **Оркестратор → Агенти → Суддя** у застосунку аналізу часових рядів
> повітряних тривог (Streamlit + Python).
>
> **КРИТИЧНЕ ОБМЕЖЕННЯ:** LLM-міркування Судді виконується **виключно через CLI `claude`**
> (headless, підпроцес; `/home/root1/.local/bin/claude`). **НЕ** через Anthropic API і **НЕ** через
> API-ключ. Детерміновані метрики обчислені в Python і виступають «джерелом істини» (ground truth).

---

## Роль

Суддя — це **контролер якості та несуперечливості**. Він не довіряє словам агента «на віру», а
звіряє кожне твердження (claim) агента з **фактично обчисленими Python-метриками**:

- чи відповідає заявлений «висхідний тренд» знаку нахилу (slope) у метриках;
- чи існує заявлена дата-сплеск у списку аномалій;
- чи числа в тексті агента збігаються з числами в `metrics_ground_truth`;
- чи немає «вигаданих» (галюцинованих) фактів, яких немає в метриках.

На основі цих перевірок Суддя:

1. призначає **оцінку впевненості (confidence) 0–1** кожному висновку агента;
2. **позначає суперечності/галюцинації** (contradictions, hallucinations);
3. формує **фінальний верифікований звіт** (verified report) для UI.

Реалізується у двох взаємозамінних варіантах:
- **LLM-Суддя** — викликає `claude` зі структурованою схемою виводу;
- **Детермінований (rule-based) Суддя** — fallback на чистому Python (без LLM).

Обидва приймають однаковий вхід (`metrics_ground_truth` + `agent_outputs`) і дають однаковий формат виходу.

---

## Рубрика валідації

Кожен висновок агента проходить набір перевірок. Для кожної перевірки — статус
`pass` / `fail` / `unsupported` (твердження ні підтверджується, ні спростовується метриками).

### R1. Узгодженість напряму тренду (sign-match)

- Заявлено `trend = increasing` ↔ у метриках `slope_sign = positive` (slope > 0).
- Заявлено `decreasing` ↔ `slope_sign = negative`. `flat` ↔ |slope| ≈ 0 (нижче порогу).
- Невідповідність знака → `fail` (**суперечність**: текст каже «зростання», а нахил від'ємний).

### R2. Існування заявленого сплеску (anomaly-exists)

- Кожну дату, названу агентом як «сплеск/пік», шукаємо у `metrics.anomalies[].date`.
- Дата є у списку → `pass`. Дати немає → `fail` (**галюцинація**: вигадана дата-сплеск).
- Якщо агент назвав дату, але вона не входить у діапазон запиту → `fail`.

### R3. Числова відповідність (number-match)

- Числа, згадані у `summary` агента (через regex/числовий парсинг), звіряємо з метриками з допуском.
- Допуск: відносна похибка ≤ 5 % (або абсолютна ≤ 1 для малих цілих).
- Розбіжність понад допуск → `fail` (**галюцинація/перекручення числа**).

### R4. Покриття без вигадок (no-fabrication / grounding)

- Висновок не повинен вводити сутностей, яких немає в метриках (напр. «через погоду» без підстав,
  конкретні причини як факт). Гіпотези дозволені, але мають бути марковані як гіпотеза, не як факт.
- Категоричне неґрунтоване твердження → `fail`.

### R5. Сезонність (за наявності `SeasonalityAgent`)

- Заявлені «пікові години / дні тижня» мають збігатися з `metrics.peak_hours` / `peak_weekdays`.
- Розбіжність → `fail`.

### Як LLM-Суддя застосовує рубрику (через `claude`)

Оркестратор формує промпт: `metrics_ground_truth` (числа) + `agent_outputs` (твердження) + текст
рубрики R1–R5 + інструкція «звір кожне твердження з числами; не довіряй тексту понад числа».
Виклик іде зі **структурованою схемою** (`--json-schema`), щоб одразу отримати машинний вердикт:

```bash
claude -p "<PROMPT з метриками, твердженнями і рубрикою>" \
  --model opus \
  --output-format json \
  --json-schema '<JUDGE_SCHEMA>'
```

`JUDGE_SCHEMA` (скорочено):

```json
{
  "type": "object",
  "properties": {
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "agent": {"type": "string"},
          "confidence": {"type": "number"},
          "checks": {"type": "object"},
          "contradictions": {"type": "array", "items": {"type": "string"}},
          "hallucinations": {"type": "array", "items": {"type": "string"}},
          "verdict": {"type": "string", "enum": ["verified", "partial", "rejected"]}
        },
        "required": ["agent", "confidence", "verdict"]
      }
    },
    "overall_confidence": {"type": "number"},
    "summary": {"type": "string"}
  },
  "required": ["findings", "overall_confidence"]
}
```

Парсинг — з поля `structured_output` (а не `result`). Якщо схема не повернулась — парсимо `result`
як JSON; якщо й це не вдалось → переходимо у детермінований fallback.

> **Захист від «м'якого» LLM-Судді:** результат LLM-Судді **додатково пропускаємо** через
> детерміновані перевірки R1–R3 (вони дешеві й абсолютно надійні). Якщо детермінована перевірка дає
> `fail`, а LLM поставив високу `confidence` — **знижуємо** confidence й примусово додаємо суперечність.
> Тобто числа завжди мають вищий пріоритет за думку LLM.

---

## Шкала впевненості

`confidence ∈ [0, 1]` для кожного висновку агента. Базова детермінована формула (застосовна і як
самостійна оцінка у fallback, і як «стеля» для оцінки LLM):

```
start = 1.0
- 0.40 за кожну провалену R1 (невідповідність знака тренду)   # найтяжче — суперечність
- 0.35 за кожну провалену R2 (вигадана дата-сплеск)           # галюцинація
- 0.25 за кожну провалену R3 (розбіжність числа)
- 0.20 за кожну провалену R4 (неґрунтоване твердження)
- 0.15 за кожну провалену R5 (сезонність)
- 0.10 якщо source == "deterministic_fallback" (інтерпретація без LLM)
confidence = clamp(start, 0.0, 1.0)
```

Категорії (verdict) за порогами:

| confidence | verdict | значення |
|---|---|---|
| ≥ 0.75 | `verified` | висновок підтверджено метриками |
| 0.40 – 0.74 | `partial` | частково підтверджено; є зауваження |
| < 0.40 | `rejected` | суперечності/галюцинації переважають — відхилити |

`overall_confidence` = середньозважене по агентах (ваги — за «важливістю» агента; Summary/Trend вищі).
Жодна провалена R1 (пряма суперечність) не дозволяє `overall` бути ≥ 0.75 — застосовуємо «стелю».

---

## Детермінований fallback

Повністю Python, **без LLM** — використовується, коли CLI `claude` недоступний/таймаут/помилка
(ті самі умови, що в `orchestrator_research.md` → «Fallback»). Дає той самий формат виходу.

```python
def judge_rule_based(metrics_truth, agent_outputs) -> dict:
    findings = []
    for ao in agent_outputs:
        checks, contradictions, hallucinations = {}, [], []
        conf = 1.0

        # R1: знак тренду
        if ao["agent"] == "TrendAgent":
            claimed = ao["claims"].get("trend")
            actual = sign_to_trend(metrics_truth["trend"]["slope_sign"])  # increasing/decreasing/flat
            checks["R1_trend_sign"] = "pass" if claimed == actual else "fail"
            if claimed != actual:
                conf -= 0.40
                contradictions.append(
                    f"Заявлено '{claimed}', але нахил вказує на '{actual}'.")

        # R2: існування сплесків
        if ao["agent"] == "AnomalyAgent":
            real_dates = {a["date"] for a in metrics_truth["anomalies"]}
            for d in extract_dates(ao["claims"]):
                ok = d in real_dates
                checks[f"R2_spike_{d}"] = "pass" if ok else "fail"
                if not ok:
                    conf -= 0.35
                    hallucinations.append(f"Дата-сплеск {d} відсутня у списку аномалій.")

        # R3: числова відповідність
        for num in extract_numbers(ao["claims"].get("summary", "")):
            if not matches_any_metric(num, metrics_truth, rel_tol=0.05):
                conf -= 0.25
                hallucinations.append(f"Число {num} не звіряється з метриками.")

        if ao.get("source") == "deterministic_fallback":
            conf -= 0.10

        conf = max(0.0, min(1.0, conf))
        verdict = ("verified" if conf >= 0.75
                   else "partial" if conf >= 0.40 else "rejected")
        findings.append({
            "agent": ao["agent"], "confidence": round(conf, 2),
            "checks": checks, "contradictions": contradictions,
            "hallucinations": hallucinations, "verdict": verdict,
        })

    overall = weighted_mean([f["confidence"] for f in findings])
    if any("R1" in c and v == "fail" for f in findings for c, v in f["checks"].items()):
        overall = min(overall, 0.74)          # стеля за наявності прямої суперечності
    return {"findings": findings, "overall_confidence": round(overall, 2),
            "summary": build_summary(findings), "mode": "rule_based"}
```

Допоміжні функції (`extract_dates`, `extract_numbers`, `matches_any_metric`, `sign_to_trend`,
`weighted_mean`) — чистий Python, детерміновані, без зовнішніх викликів. Цей самий код також
використовується як **другий шар перевірки поверх LLM-Судді** (числа > думка LLM).

---

## Формат фінального звіту

Об'єкт `verified_report`, який Оркестратор повертає у Streamlit:

```json
{
  "mode": "llm",
  "overall_confidence": 0.81,
  "overall_verdict": "verified",
  "findings": [
    {
      "agent": "TrendAgent",
      "verdict": "verified",
      "confidence": 0.85,
      "claim_summary": "Помірне зростання кількості тривог протягом року.",
      "checks": {"R1_trend_sign": "pass", "R3_number_match": "pass"},
      "contradictions": [],
      "hallucinations": []
    },
    {
      "agent": "AnomalyAgent",
      "verdict": "partial",
      "confidence": 0.55,
      "claim_summary": "Найбільші сплески у жовтні; згадано 2023-10-10.",
      "checks": {"R2_spike_2023-10-10": "pass", "R2_spike_2023-10-31": "fail"},
      "contradictions": [],
      "hallucinations": ["Дата-сплеск 2023-10-31 відсутня у списку аномалій."]
    }
  ],
  "judge_summary": "Тренд підтверджено метриками. У висновках про сплески — одна вигадана дата, тому довіра до AnomalyAgent знижена.",
  "flags": {
    "has_contradictions": false,
    "has_hallucinations": true,
    "any_rejected": false
  }
}
```

### Правила відображення в UI

- `mode`: `"llm"` (задіяно LLM-Суддю через `claude`) або `"rule_based"` (детермінований fallback) —
  показуємо користувачеві бейдж, щоб режим був прозорим.
- Висновки `rejected` — виділяти червоним; `partial` — жовтим; `verified` — зеленим.
- Перелічувати `contradictions` і `hallucinations` явним списком під відповідним агентом.
- `overall_confidence` — як головний індикатор довіри до всього звіту.
- Завжди показувати поряд **детерміновані числа** (ground truth), щоб користувач бачив джерело істини
  поруч з інтерпретацією LLM.
