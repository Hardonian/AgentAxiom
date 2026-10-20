from __future__ import annotations

import html
import json
import re
import tempfile
from hashlib import sha256
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import ContractResult
from .models import Transcript


DEFAULT_SECRET_PATTERNS = [r"(?i)(api[_-]?key|authorization|token|password)\s*[:=]\s*[^\s,]+", r"AIza[\w-]{20,}"]

def redact(value: Any, patterns: list[str] = DEFAULT_SECRET_PATTERNS) -> Any:
    """Redact values recursively without breaking otherwise-valid JSON evidence."""
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if re.search(r"(?i)(api[_-]?key|authorization|token|password|secret)", key) else redact(item, patterns)) for key, item in value.items()}
    if isinstance(value, list): return [redact(item, patterns) for item in value]
    if isinstance(value, str):
        for pattern in patterns: value = re.sub(pattern, "[REDACTED]", value)
    return value

def write_bundle(directory: str | Path, transcript: Transcript, result: ContractResult, extra: dict[str, Any] | None = None) -> Path:
    target = Path(directory); target.mkdir(parents=True, exist_ok=True)
    payload = redact({"transcript": transcript.to_dict(), "result": asdict(result), "extra": extra or {}})
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    _atomic_write(target / "evidence.json", encoded)
    _atomic_write(target / "manifest.json", json.dumps({"schema_version": transcript.schema_version, "evidence_id": transcript.evidence_id, "files": {"evidence.json": sha256(encoded.encode()).hexdigest()}}, indent=2))
    status = "PASS" if result.passed else "FAIL"
    body = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    _atomic_write(target / "index.html", f"<!doctype html><meta charset=utf-8><title>AgentAxiom {status}</title><h1>{status}: {html.escape(result.contract)}</h1><pre>{body}</pre>")
    return target


def verify_bundle(directory: str | Path) -> bool:
    target = Path(directory)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    evidence = (target / "evidence.json").read_bytes()
    return sha256(evidence).hexdigest() == manifest["files"]["evidence.json"]


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.flush()
        temp_path = Path(handle.name)
    temp_path.replace(path)
