"""Optional GCS and BigQuery evidence sinks."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .contracts import ContractResult
from .evidence import redact
from .models import Transcript


def export_gcs(bucket: str, prefix: str, transcript: Transcript, result: ContractResult) -> str:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise ImportError("Install AgentAxiom's export extra: pip install -e '.[export]'") from exc
    name = f"{prefix.strip('/')}/{transcript.scenario.name}/evidence.json"
    payload = redact({"transcript": transcript.to_dict(), "result": asdict(result)})
    storage.Client().bucket(bucket).blob(name).upload_from_string(
        json.dumps(payload, default=str), content_type="application/json"
    )
    return f"gs://{bucket}/{name}"


def export_bigquery(table: str, transcript: Transcript, result: ContractResult) -> None:
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise ImportError("Install AgentAxiom's export extra: pip install -e '.[export]'") from exc
    row: dict[str, Any] = {
        "scenario": transcript.scenario.name,
        "prompt_hash": transcript.scenario.prompt_hash,
        "model": transcript.invocation.model,
        "region": transcript.invocation.region,
        "passed": result.passed,
        "violations": json.dumps(result.violations),
        "latency_ms": transcript.invocation.latency_ms,
        "cost_usd": transcript.invocation.estimated_cost_usd,
        "recorded_at": transcript.invocation.timestamp,
    }
    errors = bigquery.Client().insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"BigQuery export failed: {errors}")
