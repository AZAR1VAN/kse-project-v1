"""Тонка обгортка над headless-викликом `claude` CLI (без Anthropic API / без ключа).

Підтверджено дослідженням: `claude -p "<prompt>" --output-format json` → JSON з полями
`result` (текст), `structured_output` (якщо передано --json-schema), `is_error`.
"""
from __future__ import annotations

import json
import shutil
import subprocess

CLAUDE_BIN = shutil.which("claude")
DEFAULT_TIMEOUT = 90


def available() -> bool:
    return CLAUDE_BIN is not None


def call(prompt: str, *, model: str = "sonnet", schema: dict | None = None,
         timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Викликати claude. Повертає {ok, text, structured, reason}."""
    if not CLAUDE_BIN:
        return {"ok": False, "reason": "not_found"}
    cmd = [CLAUDE_BIN, "-p", prompt, "--model", model, "--output-format", "json"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "reason": "not_found"}
    if proc.returncode != 0:
        return {"ok": False, "reason": f"exit:{proc.returncode}", "stderr": proc.stderr[:300]}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "bad_json"}
    if payload.get("is_error"):
        return {"ok": False, "reason": "cli_error"}
    return {
        "ok": True,
        "text": payload.get("result", ""),
        "structured": payload.get("structured_output"),
        "duration_ms": payload.get("duration_ms"),
    }
