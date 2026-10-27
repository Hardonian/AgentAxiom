# AgentAxiom

**Evidence-first regression and contract testing for Gemini and Vertex AI agents.**

> *Turn flaky agent regressions into deterministic, minimized, replayable, evidence-backed contract violations.*

AgentAxiom brings reliable software engineering rigor to Google Cloud AI development. It records an agent scenario's prompt hash, model identity, region, generation parameters, declared tools, token usage (including **Context Caching** and **Thinking Tokens**), latency, estimated cost, citations, and safety metadata. It verifies deterministic contracts against that record, keeping CI fast, offline, and zero-dollar by default.

---

## Why Google Developers Choose AgentAxiom

1. **Zero-Touch SDK Recording (`google-genai`)**: Wrap `genai.Client` in a 2-line context manager. No framework rewrites.
2. **Context Caching Regression Gates**: Guarantee prompt cache hits on Vertex AI (`require_context_cache`, `min_cached_tokens`) to prevent silent 4x cost blowups.
3. **Thinking Budget Assertions**: Cap reasoning tokens (`max_thinking_tokens`) on Gemini 2.0/2.5 Flash Thinking models.
4. **Vertex AI Grounding & Safety Verification**: Assert on grounding confidence scores (`min_grounding_score`), approved datastores/corpora, and safety categories (`HARM_CATEGORY_*`).
5. **Full Google Cloud Pipeline**:
   - Ready-to-run **Google Cloud Build** pipeline (`cloudbuild.yaml`).
   - Native **Cloud Logging** structured logs with **Cloud Trace** deep-links.
   - Evidence exports to **Google Cloud Storage** and **BigQuery**.
   - Bridges directly to **Vertex AI Gen AI Evaluation Service** (`agentaxiom export-eval`).
   - Private, internal **Cloud Run** evaluator service.
6. **Automatic Google Secret Redaction**: Sanitizes Google OAuth tokens (`ya29...`), Service Account emails, GCP private keys, and API keys before evidence is written.

---

## Quick Start

### 1. Installation

```bash
pip install agentaxiom
# With Vertex AI and Google Cloud export dependencies:
pip install 'agentaxiom[vertex,export]'
```

### 2. Capture a Gemini Run in 2 Lines

```python
from google import genai
from agentaxiom import record_gemini

client = genai.Client()

with record_gemini(client, scenario_name="billing-agent") as rec:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Lookup invoice INV-9021 and calculate balance.",
        config={"tools": [lookup_invoice]}
    )

# Save offline fixture for CI regression testing
with open("tests/fixtures/billing_agent.json", "w") as f:
    f.write(json.dumps(rec.transcript.to_dict(), indent=2))
```

### 3. Define a Deterministic Contract (`contract.json`)

```json
{
  "name": "billing-contract",
  "required_tools": ["lookup_invoice"],
  "require_context_cache": true,
  "min_cached_tokens": 5000,
  "max_thinking_tokens": 1000,
  "min_grounding_score": 0.85,
  "allowed_grounding_sources": ["finance.corp.test"],
  "max_latency_ms": 2500,
  "max_cost_usd": 0.01
}
```

### 4. Run Offline in Pytest or CI

```python
def test_billing_agent(agent_contract):
    # Evaluates offline against the committed transcript fixture
    agent_contract("tests/fixtures/billing_agent.json", "contracts/contract.json")
```

Or via CLI:

```bash
agentaxiom check tests/fixtures/billing_agent.json contracts/contract.json --evidence-dir artifacts/billing
```

---

## Google Cloud Enterprise Integrations

### Google Cloud Build Pipeline

Run contract checks automatically on every pull request without calling live models:

```yaml
# cloudbuild.yaml
steps:
  - name: 'python:3.12-slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -e '.[test]'
        pytest -v --agentaxiom-evidence=agentaxiom-evidence
        agentaxiom check fixtures/agent.json contracts/contract.json

artifacts:
  objects:
    location: 'gs://${PROJECT_ID}-agentaxiom-builds/${BUILD_ID}'
    paths: ['agentaxiom-evidence/**']
```

### Vertex AI Evaluation Service Export

Export recorded transcripts directly to JSONL for Vertex AI Evaluation (`EvalTask`):

```bash
agentaxiom export-eval tests/fixtures/billing_agent.json --output eval_dataset.jsonl
```

### Cloud Run Evaluator Service

Deploy an internal Cloud Run evaluator service for centralized microservice or CI validation:

```bash
docker build -t agentaxiom .
docker run -p 8080:8080 agentaxiom
# POST /evaluate with {"transcript": <fixture>, "contract": <contract>}
```

Cloud Run emits structured JSON log entries correlated with **Google Cloud Trace**:
```json
{
  "severity": "INFO",
  "message": "Contract PASSED: billing-contract on scenario billing-agent",
  "logging.googleapis.com/trace": "projects/my-gcp-project/traces/4bf92f3577b34da...",
  "contract": "billing-contract",
  "passed": true
}
```

---

## CLI Reference

- `agentaxiom check <transcript> <contract>`: Evaluate a transcript against a contract offline.
- `agentaxiom compare <baseline> <candidate>`: Compare cross-run tool calls, latency, safety, and outputs.
- `agentaxiom minimize <failing_transcript> <contract> --output <min.json>`: Delta-debug multi-turn traces down to the minimal failing sequence.
- `agentaxiom record --model gemini-2.5-flash --prompt "..." --output <fixture.json>`: Record a live call to a fixture file.
- `agentaxiom export-eval <transcript> --output <dataset.jsonl>`: Export transcripts to Vertex AI Evaluation dataset format.
- `agentaxiom serve`: Launch the no-code web console locally.

---

## Release & Governance

See the prioritized [100-item go-live gate](docs/GO_LIVE_100.md) and [Public API Reference](docs/API.md) for full architecture and contract schema documentation.
