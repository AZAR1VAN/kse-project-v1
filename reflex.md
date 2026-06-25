# Reflection (reflex.md)

**What went wrong.** The first version over-engineered the task: it added a multi-agent LLM layer (Orchestrator → Agents → Judge via the Claude CLI) to interpret forecasts, even though forecasting only needs ready algorithms. The LLM "judge" over-flagged valid numbers as hallucinations (confidence dropped to 0.38/rejected), some agents replied in English instead of Ukrainian, and early on the log sat in the wrong folder while the GitHub push was skipped.

**How I adjusted.** I questioned why an LLM was forecasting, clarified that prediction was already algorithmic, and asked it to drop the LLM layer and ship a simple, step-by-step time-series dashboard.

**Why the final version is better.** It is fully deterministic and reproducible (Prophet, STL, IsolationForest, KMeans), simpler and dependency-light, resilient to messy data, well-visualized with Plotly, tested (pytest + Playwright screenshots), documented, and committed to GitHub.
