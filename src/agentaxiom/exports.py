"""Optional GCS, BigQuery, and Vertex AI evidence sinks and GCP logging formatters."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
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


def export_vertex_evaluation(
    records: Transcript | list[Transcript],
    output_path: str | Path,
) -> Path:
    """Exports transcripts to Vertex AI Gen AI Evaluation (EvalTask) compatible JSONL format."""
    transcripts = [records] if isinstance(records, Transcript) else records
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for t in transcripts:
            prompt_text = ""
            for turn in reversed(t.scenario.turns):
                if turn.role in {"user", "system"} and turn.effective_text:
                    prompt_text = turn.effective_text
                    break
            row = {
                "scenario": t.scenario.name,
                "prompt": prompt_text,
                "response": t.invocation.response_text or "",
                "model": t.invocation.model,
                "tool_calls": t.invocation.tool_calls,
                "token_usage": t.invocation.token_usage,
            }
            handle.write(json.dumps(row) + "\n")
    return target


def format_gcp_log_entry(
    transcript: Transcript,
    result: ContractResult,
    *,
    project_id: str | None = None,
    component: str = "agentaxiom-evaluator",
) -> dict[str, Any]:
    """Formats a structured Google Cloud Logging entry correlated with Cloud Trace."""
    severity = "INFO" if result.passed else "ERROR"
    trace_id = transcript.invocation.trace_id
    status_str = "PASSED" if result.passed else "FAILED"
    entry: dict[str, Any] = {
        "severity": severity,
        "message": f"Contract {status_str}: {result.contract} on scenario {transcript.scenario.name}",
        "component": component,
        "scenario": transcript.scenario.name,
        "model": transcript.invocation.model,
        "region": transcript.invocation.region,
        "contract": result.contract,
        "passed": result.passed,
        "violations": result.violations,
        "latency_ms": transcript.invocation.latency_ms,
        "estimated_cost_usd": transcript.invocation.estimated_cost_usd,
        "token_usage": transcript.invocation.token_usage,
    }
    if trace_id:
        if project_id:
            entry["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace_id}"
        else:
            entry["logging.googleapis.com/trace"] = trace_id
    return entry
