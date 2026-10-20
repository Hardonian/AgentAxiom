# Public API reference

## Core data

- `Turn`, `Scenario`, `Invocation`, and `Transcript` in `agentaxiom.models` are the versioned evidence record. `Scenario.prompt_hash` is a deterministic SHA-256 of all turns.
- `Contract` defines output, tool, grounding, safety, latency, and cost requirements. `evaluate_contract(transcript, contract)` returns `ContractResult`; it never calls a model.
- `ComparisonPolicy` defines accepted differences. `compare(baseline, candidate, policy)` returns `ComparisonResult`.

## Execution

- `ReplayRunner(client, policy).replay(recorded, contract)` stays offline without a client. Live replay requires all of `live_verification=True`, a positive `max_live_calls`, a positive `max_live_cost_usd`, and a positive `max_cost_per_call_usd`.
- `minimize_conversation(recorded, still_fails)` removes turns while the caller’s predicate remains true.
- `write_bundle(directory, transcript, result)` writes sanitized evidence and a checksum manifest. `verify_bundle(directory)` verifies it.

## Integrations

- `GeminiVertexClient` is optional (`pip install 'agentaxiom[vertex]'`).
- `export_gcs` and `export_bigquery` are optional (`pip install 'agentaxiom[export]'`).
- The Cloud Run service supports `GET /healthz`, `POST /evaluate`, and `POST /compare`.

All public APIs use dataclasses and return data; no default operation makes a network request.
