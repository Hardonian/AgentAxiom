"""Synthetic, explicitly enabled GCS and BigQuery export smoke test."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from agentaxiom.contracts import ContractResult
from agentaxiom.exports import export_bigquery, export_gcs
from agentaxiom.models import Invocation, Scenario, Transcript, Turn

if os.environ.get("AGENTAXIOM_EXPORT_SMOKE") != "1":
    raise SystemExit("Refusing export: set AGENTAXIOM_EXPORT_SMOKE=1 explicitly.")
bucket = os.environ.get("AGENTAXIOM_EXPORT_BUCKET")
table = os.environ.get("AGENTAXIOM_EXPORT_TABLE")
if not bucket or not table:
    raise SystemExit(
        "Refusing export: set AGENTAXIOM_EXPORT_BUCKET and AGENTAXIOM_EXPORT_TABLE explicitly."
    )

suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
transcript = Transcript(
    Scenario(f"export-smoke-{suffix}", [Turn("user", "synthetic export validation")]),
    Invocation(
        model="offline-smoke",
        region="us-central1",
        response_text="synthetic",
        raw_response={"contact_email": "synthetic.person@example.test"},
        latency_ms=1,
        estimated_cost_usd=0,
    ),
)
result = ContractResult(contract="export-smoke", passed=True, violations=[])
uri = export_gcs(bucket, "smoke", transcript, result)
export_bigquery(table, transcript, result)
print({"gcs_uri": uri, "scenario": transcript.scenario.name})
