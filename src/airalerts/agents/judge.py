"""Суддя (LLM-as-Judge з детермінованою верифікацією).

Принцип з дослідження: числа > думка LLM. Перевірки R1–R5 детерміновані й завжди
застосовуються як «стеля» довіри. Це водночас і самостійний rule-based fallback.
"""
from __future__ import annotations

import re

from .agents import AgentOutput, _dir_to_enum

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")

WEIGHTS = {"SummaryAgent": 1.0, "TrendAgent": 1.0, "ForecastAgent": 0.8,
           "AnomalyAgent": 0.9, "SeasonalityAgent": 0.7}


def _numbers(text: str) -> list[float]:
    return [float(x) for x in _NUM.findall(text or "")]


def _metric_values(metrics: dict) -> list[float]:
    vals = []
    for v in metrics.values():
        if isinstance(v, (int, float)):
            vals.append(float(v))
        elif isinstance(v, (list, tuple)):
            vals += [float(x) for x in v if isinstance(x, (int, float))]
    return vals


def _matches_any(num: float, values: list[float], rel_tol: float = 0.05) -> bool:
    for v in values:
        if abs(num - v) <= max(abs(v) * rel_tol, 1.0):
            return True
    return False


def _judge_one(ao: AgentOutput, pool: list[float] | None = None) -> dict:
    checks, contradictions, hallucinations = {}, [], []
    conf = 1.0
    summary = ao.claims.get("summary", "")

    if ao.agent == "TrendAgent":
        claimed = ao.claims.get("trend") or _dir_to_enum(ao.metrics.get("direction", ""))
        actual = _dir_to_enum(ao.metrics.get("direction", ""))
        ok = claimed == actual
        checks["R1_trend_sign"] = "pass" if ok else "fail"
        if not ok:
            conf -= 0.40
            contradictions.append(f"Заявлено '{claimed}', але напрям метрик '{actual}'.")

    if ao.agent == "AnomalyAgent":
        real = set(ao.metrics.get("all_dates", ao.metrics.get("top", [])))
        for d in _DATE.findall(summary):
            ok = d in real
            checks[f"R2_spike_{d}"] = "pass" if ok else "fail"
            if not ok:
                conf -= 0.35
                hallucinations.append(f"Дата-сплеск {d} відсутня у списку аномалій.")

    if ao.agent == "SeasonalityAgent":
        peaks = set(int(x) for x in ao.metrics.get("peak_hours", []))
        mentioned = {int(n) for n in _numbers(summary) if 0 <= n <= 23}
        if mentioned and not (mentioned & peaks):
            conf -= 0.15
            checks["R5_seasonality"] = "fail"
            contradictions.append("Згадані години не збігаються з піковими.")
        else:
            checks["R5_seasonality"] = "pass"

    # R3: числова відповідність — лише «статистичні» числа (float або >31), проти пулу всіх метрик.
    # Малі цілі (≤31: лічильники/години/дні тижня) і роки в датах не караємо — це джерело хибних спрацювань.
    values = pool if pool is not None else _metric_values(ao.metrics)
    for tok in _NUM.findall(summary):
        num = float(tok)
        is_year = ("." not in tok) and 1900 < num < 2100
        statistic_like = ("." in tok) or abs(num) > 31
        if is_year or not statistic_like:
            continue
        if values and not _matches_any(num, values):
            conf -= 0.25
            hallucinations.append(f"Число {tok} не звіряється з метриками.")
            checks["R3_number_match"] = "fail"
    checks.setdefault("R3_number_match", "pass")

    if ao.source == "deterministic_fallback":
        conf -= 0.10

    conf = max(0.0, min(1.0, conf))
    verdict = "verified" if conf >= 0.75 else "partial" if conf >= 0.40 else "rejected"
    return {
        "agent": ao.agent,
        "confidence": round(conf, 2),
        "verdict": verdict,
        "claim_summary": summary,
        "checks": checks,
        "contradictions": contradictions,
        "hallucinations": hallucinations,
        "source": ao.source,
    }


def judge(agent_outputs: list[AgentOutput], metric_pool: list[float] | None = None,
          mode_llm: bool = False) -> dict:
    """Звести висновки агентів у верифікований звіт (детерміновані перевірки — авторитетні)."""
    findings = [_judge_one(ao, metric_pool) for ao in agent_outputs]
    num = sum(WEIGHTS.get(f["agent"], 0.7) * f["confidence"] for f in findings)
    den = sum(WEIGHTS.get(f["agent"], 0.7) for f in findings) or 1.0
    overall = num / den
    has_contra = any(f["contradictions"] for f in findings)
    if has_contra:
        overall = min(overall, 0.74)  # стеля за наявності прямої суперечності
    overall = round(overall, 2)
    return {
        "mode": "llm" if mode_llm else "rule_based",
        "overall_confidence": overall,
        "overall_verdict": "verified" if overall >= 0.75 else "partial" if overall >= 0.40 else "rejected",
        "findings": findings,
        "flags": {
            "has_contradictions": has_contra,
            "has_hallucinations": any(f["hallucinations"] for f in findings),
            "any_rejected": any(f["verdict"] == "rejected" for f in findings),
        },
    }
