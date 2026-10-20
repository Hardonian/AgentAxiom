# Changelog

All notable changes are documented here. This project follows Semantic Versioning.

## [Unreleased]

### Added

- Provider retry, timeout, and error-normalization policies: `RetryPolicy`, `ProviderError`, `classify_provider_error`, and `call_with_retry` in `agentaxiom.providers`; `GeminiVertexClient` now accepts `timeout_s` and `retry_policy` (go-live gate 68 groundwork; live validation pending gate 65).
- `PricingCatalog.from_json` loader with per-rate `effective_date`/`source` metadata and a draft Gemini price catalog in `pricing/` (go-live gate 70 approval packet).
- `docs/APPROVALS.md` consolidating the remaining human sign-off gates (25, 70, 94, 99).

## [0.1.0] - 2026-10-20

### Added

- Initial public MVP, including contract validation, comparison, replay, minimization, redacted evidence bundles, optional exports, a pytest plugin, reusable GitHub Action, and an offline Cloud Run evaluator.
- Release, security, operations, migration, API, and threat-model guidance.
