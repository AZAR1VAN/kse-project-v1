import numpy as np
import pandas as pd

from airalerts.agents import claude_cli, judge, orchestrator
from airalerts.agents.agents import AgentOutput


def _events_df(region="Kyiv City", days=60, per_day=4, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    base = pd.Timestamp("2023-01-01", tz="UTC")
    for d in range(days):
        for _ in range(per_day + int(rng.integers(0, 3))):
            t = base + pd.Timedelta(days=d, hours=int(rng.integers(0, 24)))
            rows.append({"region": region, "started_at": t, "finished_at": t + pd.Timedelta(minutes=30)})
    df = pd.DataFrame(rows)
    df["duration_min"] = 30.0
    return df


def test_orchestrator_fallback_runs_without_llm():
    df = _events_df()
    rep = orchestrator.analyze(df, region="Kyiv City", use_llm=False)
    assert rep["llm_used"] is False
    assert rep["verified"]["mode"] == "rule_based"
    assert len(rep["agents"]) == 5
    assert 0.0 <= rep["verified"]["overall_confidence"] <= 1.0
    # детермінований fallback стабільний
    rep2 = orchestrator.analyze(df, region="Kyiv City", use_llm=False)
    assert rep["verified"]["overall_confidence"] == rep2["verified"]["overall_confidence"]


def test_judge_flags_wrong_trend_claim():
    ao = AgentOutput(
        "TrendAgent",
        {"direction": "спад", "slope": -0.5, "n_change_points": 0},
        {"summary": "Спостерігається чітке зростання тривог.", "trend": "increasing"},
        "deterministic_fallback",
    )
    res = judge.judge([ao])
    f = res["findings"][0]
    assert f["checks"]["R1_trend_sign"] == "fail"
    assert f["contradictions"]
    assert f["confidence"] <= 0.5
    assert res["overall_confidence"] <= 0.74  # стеля за суперечності


def test_judge_flags_hallucinated_spike_date():
    ao = AgentOutput(
        "AnomalyAgent",
        {"count": 2, "top": ["2023-05-01"], "all_dates": ["2023-05-01", "2023-06-02"]},
        {"summary": "Найбільший сплеск стався 2023-12-31."},
        "claude_cli",
    )
    res = judge.judge([ao])
    f = res["findings"][0]
    assert any("2023-12-31" in h for h in f["hallucinations"])
    assert f["confidence"] < 0.75


def test_claude_cli_unavailable_returns_not_ok(monkeypatch):
    monkeypatch.setattr(claude_cli, "CLAUDE_BIN", None)
    res = claude_cli.call("hi")
    assert res["ok"] is False and res["reason"] == "not_found"
    assert isinstance(claude_cli.available(), bool)
