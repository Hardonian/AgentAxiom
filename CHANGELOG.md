# Changelog

All notable changes are documented here. This project follows Semantic Versioning.

## [1.0.0] - 2026-10-27

### Added

- All 100 go-live gates closed, audited, and approved (`docs/GO_LIVE_100.md`, `docs/APPROVALS.md`).
- Drop-in SDK recording: `record_gemini` context manager in `agentaxiom.recorder` to capture transcripts directly from `google.genai.Client` without modifying application loops.
- Gemini 2.0 / 2.5 Flash Thinking token budgeting: `max_thinking_tokens` in `Contract` and `thought_text` separation in `Invocation`.
- Vertex AI Context Caching contracts: `require_context_cache` and `min_cached_tokens` assertions in `Contract` to prevent silent prompt cache invalidation and billing regressions.
- Multimodal and GCS turn support: `Turn.parts` preserving GCS URIs (`gs://...`), MIME types, and structured parts.
- Vertex AI Grounding and datastore validation: `min_grounding_score` and `allowed_grounding_sources` supporting domain matching and Vertex Search `ragCorpora` datastore IDs.
- Vertex AI Safety category filtering: `blocked_safety_categories` checking against `MEDIUM` and `HIGH` probability ratings or blocked actions.
- Google Cloud Structured Logging: `format_gcp_log_entry` in `agentaxiom.exports` and integrated in `agentaxiom.service` with `logging.googleapis.com/trace` correlation for Cloud Run.
- Vertex AI Gen AI Evaluation export: `export_vertex_evaluation` and CLI command `agentaxiom export-eval` to export transcripts to JSONL for Vertex AI `EvalTask`.
- Google Cloud Build pipeline: `cloudbuild.yaml` running linting, offline tests, contract gates, wheel build, and container build for Artifact Registry.
- Bundled schemas and catalogs: `agentaxiom.schemas` and `agentaxiom.catalogs` packaged into the wheel distribution; accessible via `PricingCatalog.bundled()` and `agentaxiom.schemas.get_schema()`.
- Production container hardening: `Dockerfile` updated with non-root user (`USER nobody`), active `HEALTHCHECK` probe against `/healthz`, and `[export]` dependencies.
- Google secret redactions: added automatic detection and redaction for Google OAuth access tokens (`ya29...`), Service Account emails, and GCP private keys in `agentaxiom.evidence`.
- Pytest plugin enhancements: `@pytest.mark.agentaxiom` marker registration, flexible `agent_contract` supporting file paths and dicts, and `recorded_gemini` fixture.
- Provider retry, timeout, and error-normalization policies: `RetryPolicy`, `ProviderError`, `classify_provider_error`, and `call_with_retry` in `agentaxiom.providers`; `GeminiVertexClient` now accepts `timeout_s` and `retry_policy`.
- Approved Gemini pricing catalog (`2026-10-27-approved.1`) in `pricing/` covering Gemini 1.5, 2.0, and 2.5 with context caching discounts.
- Infrastructure alert policies for service 5xx errors, violation spikes, and export failures in `infra/main.tf`.
- Automated staging load, failure, and recovery drill script (`scripts/staging_drills.py`).

## [0.1.0] - 2026-10-20

### Added

- Initial public MVP, including contract validation, comparison, replay, minimization, redacted evidence bundles, optional exports, a pytest plugin, reusable GitHub Action, and an offline Cloud Run evaluator.
- Release, security, operations, migration, API, and threat-model guidance.
