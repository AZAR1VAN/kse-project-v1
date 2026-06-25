"""Спеціалізовані агенти-інтерпретатори. Кожен ґрунтується на детермінованих метриках,
а текст-інтерпретацію бере з `claude` CLI (з детермінованим fallback-шаблоном).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import claude_cli

GROUNDING = (
    "Відповідай УКРАЇНСЬКОЮ мовою. Поле summary — це готовий висновок для користувача "
    "(1–2 речення), а НЕ опис твоїх дій. Інтерпретуй ЛИШЕ надані числа, не вигадуй значень."
)


@dataclass
class AgentOutput:
    agent: str
    metrics: dict
    claims: dict
    source: str  # "claude_cli" | "deterministic_fallback"


def _interpret(prompt: str, schema: dict, fallback: dict, use_llm: bool) -> tuple[dict, str]:
    if use_llm and claude_cli.available():
        res = claude_cli.call(prompt, schema=schema)
        if res["ok"]:
            claims = res.get("structured")
            if not claims:
                try:
                    claims = json.loads(res["text"])
                except (json.JSONDecodeError, TypeError):
                    claims = {**fallback, "summary": res["text"][:400] or fallback["summary"]}
            return claims, "claude_cli"
    return fallback, "deterministic_fallback"


def _prompt(region: str, body: str, question: str | None) -> str:
    q = f"\nПитання користувача: {question}" if question else ""
    return f"Регіон: {region}. {body}{q}\n{GROUNDING}"


# ---- агенти ----

def summary_agent(ctx: dict, question, use_llm) -> AgentOutput:
    m = ctx["summary"]
    body = (f"KPI періоду: усього тривог={m['total']}, у середньому {m['mean_per_day']}/день, "
            f"найбільший день={m['busiest_day']} ({m['busiest_count']} тривог).")
    fb = {"summary": f"За період зафіксовано {m['total']} тривог, у середньому {m['mean_per_day']} на день; "
                     f"пік — {m['busiest_day']} ({m['busiest_count']}).", "confidence_self": 0.6}
    schema = {"type": "object", "properties": {"summary": {"type": "string"},
              "confidence_self": {"type": "number"}}, "required": ["summary"]}
    claims, src = _interpret(_prompt(ctx["region"], body, question), schema, fb, use_llm)
    return AgentOutput("SummaryAgent", m, claims, src)


def trend_agent(ctx: dict, question, use_llm) -> AgentOutput:
    m = ctx["trend"]
    body = (f"Тренд кількості тривог: нахил={m['slope']}/день, попередня оцінка напряму='{m['direction']}', "
            f"точок зміни режиму={m['n_change_points']}.")
    fb = {"summary": f"Тренд показує {m['direction']} (нахил {m['slope']}/день).",
          "trend": _dir_to_enum(m["direction"]), "confidence_self": 0.6}
    schema = {"type": "object", "properties": {"summary": {"type": "string"},
              "trend": {"type": "string", "enum": ["increasing", "decreasing", "flat"]},
              "confidence_self": {"type": "number"}}, "required": ["summary", "trend"]}
    claims, src = _interpret(_prompt(ctx["region"], body, question), schema, fb, use_llm)
    return AgentOutput("TrendAgent", m, claims, src)


def anomaly_agent(ctx: dict, question, use_llm) -> AgentOutput:
    m = ctx["anomaly"]
    body = (f"Виявлено {m['count']} аномальних днів (сплесків). Найзначніші дати: {', '.join(m['top']) or '—'}.")
    fb = {"summary": f"Виявлено {m['count']} сплесків; найзначніші: {', '.join(m['top']) or '—'}.",
          "confidence_self": 0.6}
    schema = {"type": "object", "properties": {"summary": {"type": "string"},
              "confidence_self": {"type": "number"}}, "required": ["summary"]}
    claims, src = _interpret(_prompt(ctx["region"], body, question), schema, fb, use_llm)
    return AgentOutput("AnomalyAgent", m, claims, src)


def forecast_agent(ctx: dict, question, use_llm) -> AgentOutput:
    m = ctx["forecast"]
    body = (f"Прогноз ({m['method']}) на {m['horizon']} днів: середнє очікуване={m['mean_yhat']}/день "
            f"(нещодавнє середнє={m['recent_mean']}), MAE бектесту={m['mae']}.")
    fb = {"summary": f"Очікувано близько {m['mean_yhat']} тривог/день у наступні {m['horizon']} днів "
                     f"(нещодавнє середнє {m['recent_mean']}).", "confidence_self": 0.6}
    schema = {"type": "object", "properties": {"summary": {"type": "string"},
              "confidence_self": {"type": "number"}}, "required": ["summary"]}
    claims, src = _interpret(_prompt(ctx["region"], body, question), schema, fb, use_llm)
    return AgentOutput("ForecastAgent", m, claims, src)


def seasonality_agent(ctx: dict, question, use_llm) -> AgentOutput:
    m = ctx["seasonality"]
    body = (f"Сезонність: пікові години доби={m['peak_hours']}, пікові дні тижня (0=Пн)={m['peak_weekdays']}.")
    fb = {"summary": f"Найбільше тривог у години {m['peak_hours']} та дні тижня {m['peak_weekdays']}.",
          "confidence_self": 0.6}
    schema = {"type": "object", "properties": {"summary": {"type": "string"},
              "confidence_self": {"type": "number"}}, "required": ["summary"]}
    claims, src = _interpret(_prompt(ctx["region"], body, question), schema, fb, use_llm)
    return AgentOutput("SeasonalityAgent", m, claims, src)


def _dir_to_enum(direction: str) -> str:
    return {"зростання": "increasing", "спад": "decreasing"}.get(direction, "flat")


AGENTS = {
    "SummaryAgent": summary_agent,
    "TrendAgent": trend_agent,
    "AnomalyAgent": anomaly_agent,
    "ForecastAgent": forecast_agent,
    "SeasonalityAgent": seasonality_agent,
}
