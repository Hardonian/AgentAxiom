from __future__ import annotations

import html
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import ContractResult
from .models import Transcript


DEFAULT_SECRET_PATTERNS = [r"(?i)(api[_-]?key|authorization|token|password)\s*[:=]\s*[^\s,]+", r"AIza[\w-]{20,}"]

def redact(value: Any, patterns: list[str] = DEFAULT_SECRET_PATTERNS) -> Any:
    raw = json.dumps(value, default=str)
    for pattern in patterns:
        raw = re.sub(pattern, "[REDACTED]", raw)
    return json.loads(raw)

def write_bundle(directory: str | Path, transcript: Transcript, result: ContractResult, extra: dict[str, Any] | None = None) -> Path:
    target = Path(directory); target.mkdir(parents=True, exist_ok=True)
    payload = redact({"transcript": transcript.to_dict(), "result": asdict(result), "extra": extra or {}})
    (target / "evidence.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    status = "PASS" if result.passed else "FAIL"
    body = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    (target / "index.html").write_text(f"<!doctype html><title>AgentAxiom {status}</title><h1>{status}: {html.escape(result.contract)}</h1><pre>{body}</pre>", encoding="utf-8")
    return target
