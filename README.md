# AgentAxiom

Evidence-first regression and contract testing for Gemini and Vertex AI agents.

> Turn an unreliable agent regression into a minimized, replayable, evidence-backed contract violation.

AgentAxiom records a scenario's prompt hash, model/provider identity, region, generation configuration, declared tools, usage, latency, cost, citations and safety metadata. It evaluates deterministic contracts against that record, so CI is offline by default. Live confirmations are opt-in and bounded by a hard call and cost budget.

## MVP capabilities

- JSON Schema output validation and required/forbidden tool-call contracts.
- Grounding/citation, safety action, cost, and latency assertions.
- Offline fixture replay with fail-closed live verification gates.
- Delta-debug conversation minimization for reproducible failing traces.
- Sanitized JSON and HTML evidence bundles.
- Pytest fixture, CLI, and GitHub Actions workflow.

## Quick start

```bash
pip install -e .
pytest
agentaxiom check fixture.json examples/contract.json --evidence-dir artifacts/quoted-answer
```

`fixture.json` uses the `Transcript` shape (scenario plus invocation). The evidence bundle emits `evidence.json` and `index.html`; secret-looking values are redacted before writing.

Try the included complete offline path:

```bash
python -m agentaxiom.cli check examples/fixture.json examples/contract.json
```

## Live provider boundary

The core deliberately has no implicit network path. Implement the small `AgentClient` protocol for Gemini/Vertex or ADK, then supply `ReplayPolicy(live_verification=True, max_live_calls=N, max_live_cost_usd=X)`. Calls without this explicit opt-in, or beyond either budget, raise `PermissionError`.

## Planned adapters and exports

The core is provider-neutral so Gemini, Vertex AI, ADK, Cloud Trace, Cloud Run, GCS, and BigQuery adapters can preserve each platform's native response metadata without weakening the evidence format. Optional package groups are reserved for the Google provider/export clients:

```bash
pip install -e '.[vertex,export]'
```

`GeminiVertexClient` in `agentaxiom.providers` is the optional recorder adapter; `export_gcs` and `export_bigquery` in `agentaxiom.exports` publish evidence to those sinks. Cloud Run can invoke the CLI or pytest suite directly, and the returned evidence record carries the IDs needed to correlate Cloud Trace spans supplied by the calling service.

## Cloud Run evaluator

The included container exposes an offline-only evaluator, suitable for a CI runner or a protected internal service:

```bash
docker build -t agentaxiom .
docker run -p 8080:8080 agentaxiom
# POST /evaluate with {"transcript": <fixture>, "contract": <contract>}
```

`GET /healthz` returns readiness. `POST /evaluate` never invokes a model; evidence writing is optional and defaults to ephemeral container storage.
