# Public API reference

## Core data

- `Turn`, `Scenario`, `Invocation`, and `Transcript` in `agentaxiom.models` are the versioned evidence record.
  - `Turn` supports text content and multimodal parts (`Turn.parts` with GCS URIs and MIME types).
  - `Invocation` captures token usage (`input`, `output`, `cached`, `thoughts`), `thought_text`, safety ratings, grounding metadata, latency, and costs.
  - `Scenario.prompt_hash` is a deterministic SHA-256 of all turns.
- `Contract` defines rules evaluated deterministically without calling a model:
  - Output schema (JSON Schema Draft 2020-12).
  - Required and forbidden tool calls.
  - Per-tool argument and output schemas.
  - Context Caching assertions (`require_context_cache`, `min_cached_tokens`).
  - Thinking token limits (`max_thinking_tokens`).
  - Safety thresholds (`blocked_safety_categories`, `allowed_safety_actions`).
  - Grounding confidence and datastore source validation (`min_grounding_score`, `allowed_grounding_sources`, `allowed_citation_domains`).
  - Latency and cost ceilings (`max_latency_ms`, `max_cost_usd`).
- `evaluate_contract(transcript, contract)` returns `ContractResult`.
- `ComparisonPolicy` defines accepted differences. `compare(baseline, candidate, policy)` returns `ComparisonResult`.

## Google GenAI & Vertex AI Recording

- `record_gemini(client, scenario_name="...", metadata=None)` is a drop-in context manager for official `google.genai.Client`:
  ```python
  from google import genai
  from agentaxiom import record_gemini

  client = genai.Client()
  with record_gemini(client, scenario_name="billing-flow") as rec:
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents="Lookup order #1234",
      )
  transcript = rec.transcript
  ```
- `GeminiVertexClient` is the standalone client adapter supporting bounded retry policies and timeout configurations.
- `ADKRecorder` normalizes Google Agent Development Kit event streams into standard `Invocation` shapes.

## Sinks and GCP Integrations

- `export_vertex_evaluation(transcripts, path)`: Exports records into JSONL formatted for Vertex AI Gen AI Evaluation Service (`EvalTask`).
- `format_gcp_log_entry(transcript, result, project_id=None)`: Produces structured Google Cloud Logging JSON lines with trace context (`logging.googleapis.com/trace`).
- `export_gcs(bucket, prefix, transcript, result)`: Stores checksummed evidence bundles in Google Cloud Storage.
- `export_bigquery(table, transcript, result)`: Inserts evaluation records into a partitioned BigQuery table.
- The Cloud Run evaluator service exposes `GET /healthz`, `POST /evaluate`, and `POST /compare` with structured Cloud Logging on stdout.

## Execution

- `ReplayRunner(client, policy).replay(recorded, contract)` stays offline without a client. Live replay requires all of `live_verification=True`, a positive `max_live_calls`, a positive `max_live_cost_usd`, and a positive `max_cost_per_call_usd`.
- `minimize_conversation(recorded, still_fails)` delta-debugs traces to isolate the minimal failing turns.
- `write_bundle(directory, transcript, result)` writes sanitized evidence and a checksum manifest. `verify_bundle(directory)` verifies it.
- `PricingCatalog.from_json(path)` loads versioned model pricing including cached prompt read discounts and thinking tokens.

All public APIs use dataclasses and return data; no default operation makes a network request.
