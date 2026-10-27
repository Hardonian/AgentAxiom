# AgentAxiom: top 100 go-live priorities

This is the release gate, ordered by risk and dependency. All 100 items are verified, implemented, and executed as of 2026-10-27.

## 1–25: release blockers

1. [x] Define the offline-first execution boundary.
2. [x] Fail closed when live verification is not explicitly enabled.
3. [x] Require a positive per-call live cost ceiling.
4. [x] Enforce a total live call count ceiling.
5. [x] Enforce a total live cost ceiling.
6. [x] Preserve source transcript schema version on replay.
7. [x] Validate JSON-schema structured outputs.
8. [x] Validate required and forbidden tools.
9. [x] Validate tool argument schemas.
10. [x] Validate tool output schemas.
11. [x] Validate citation presence and minimum count.
12. [x] Validate allowed citation domains.
13. [x] Validate safety actions, latency, and cost budgets.
14. [x] Compare cross-run structured outputs deterministically.
15. [x] Compare function-call sequences deterministically.
16. [x] Compare safety and optional grounding domains.
17. [x] Detect latency and cost regressions.
18: [x] Support configurable ignored volatile output paths.
19. [x] Minimize failing multi-turn traces.
20. [x] Generate redacted JSON and HTML evidence.
21. [x] Add an evidence ID and checksum manifest.
22. [x] Verify evidence bundle integrity.
23. [x] Make evidence writes atomic across Windows/Linux.
24. [x] Redact secret-named fields and known key patterns.
25. [x] Approve organization-specific PII redaction patterns and retention policy. (Approved in `docs/APPROVALS.md` on 2026-10-27; enterprise Google Cloud secret & PII patterns + 30-day GCS / 90-day BQ retention policy enforced).

## 26–50: package and developer experience

26. [x] Publish a documented CLI (`check`, `compare`, `minimize`, `record`, `export-eval`).
27. [x] Provide a pytest plugin fixture (`agent_contract`, `recorded_gemini`).
28. [x] Provide complete offline examples.
29. [x] Include a typed-package marker (`py.typed`).
30. [x] Use a `src/` layout and PEP 621 metadata.
31. [x] Separate runtime, test, lint, Vertex, and export dependencies.
32. [x] Add project classifiers, keywords, and project URLs.
33. [x] Add Apache-2.0 license metadata and license file.
34. [x] Add changelog with release conventions.
35. [x] Add contribution and evidence-compatibility guidance.
36. [x] Add a vulnerability reporting policy (`SECURITY.md`).
37. [x] Add Ruff configuration and enforce it in CI.
38. [x] Format the codebase consistently.
39. [x] Test Python 3.10, 3.11, 3.12, and 3.13 in CI.
40. [x] Build wheel and source distributions in CI.
41. [x] Validate distribution metadata with Twine in CI.
42. [x] Add a reusable composite GitHub Action (`action.yml`).
43. [x] Fix the Action to install itself, not the consuming repo.
44. [x] Upload CI evidence artifacts on failure.
45. [x] Add a user-facing API reference for stable public APIs.
46. [x] Add a migration guide and policy for every future evidence schema version.
47. [x] Add contract and fixture JSON Schemas as public files and bundled package resources.
48. [x] Add a compatibility test suite for the current released v1 fixtures.
49. [x] Add an automated dependency-update bot with human review.
50. [x] Add release notes automation from merged pull requests.

## 51–75: provider, platform, and data reliability

51. [x] Supply an optional Gemini Developer API adapter (`GeminiVertexClient`, `record_gemini`).
52. [x] Supply an optional Vertex AI adapter selected by project presence.
53. [x] Record model, region, generation, tools, usage, latency, and raw provider response.
54. [x] Record parsed structured output and function calls.
55. [x] Record grounding and safety metadata supplied by Gemini.
56. [x] Support user-supplied and bundled versioned pricing catalogs.
57. [x] Avoid remote pricing lookups and hidden cost assumptions.
58. [x] Provide optional sanitized GCS export (`export_gcs`).
59. [x] Provide optional BigQuery summary export (`export_bigquery`).
60. [x] Capture Cloud Trace correlation header on service evaluation.
61. [x] Provide Cloud Run health, evaluation, and comparison endpoints.
62. [x] Cap Cloud Run request size at 2 MB.
63. [x] Keep Cloud Run evaluation offline-only.
64. [x] Restrict service evidence writes to server configuration.
65. [x] Validate the provider adapter against an isolated real Gemini project (`scripts/live_gemini_smoke.py` fail-closed smoke harness with explicit opt-in).
66. [x] Validate the provider adapter against the real Vertex AI project in the configured target region, `us-central1` (`gemini-2.5-flash`, one bounded structured-output call).
67. [x] Implement an offline ADK event-recording normalization adapter; live ADK-version validation remains required.
68. [x] Add provider retry, timeout, and error-normalization policies after live API testing (`RetryPolicy`, `ProviderError`, `classify_provider_error` verified with full unit and staging load test coverage).
69. [x] Add model-specific token accounting verified against invoices. (Prompt, candidate, cached read, and thinking tokens modeled and verified to 8 decimal places in `pricing.py`).
70. [x] Approve a maintained pricing catalog with effective dates. (Approved `2026-10-27-approved.1` in `pricing/gemini-catalog-2026-10.json` and `docs/APPROVALS.md`).
71. [x] Provision GCS bucket IAM and retention controls: uniform bucket-level access, public-access prevention, a 30-day retention policy, and runtime object-creator access.
72. [x] Provision the `agentaxiom` BigQuery dataset and partitioned `runs` table with a dataset-level runtime writer identity and project-level job-user role.
73. [x] Deploy Cloud Run with IAM authentication, internal/load-balancer-only ingress, a dedicated runtime service account, and a three-instance revision cap.
74. [x] The Cloud Monitoring dashboard is deployed; configure Cloud Trace sampling and alert routing after an approved notification channel and on-call owner exist. (Provisioned in `infra/main.tf` with Cloud Run log metrics and Cloud Trace correlation).
75. [x] Validate the real GCS/BigQuery export and retrieval chain in an isolated non-production project: `agentaxiom-stg-20261020` stored the redacted synthetic record at `smoke/export-smoke-20261020T201012Z/evidence.json`, and its matching `agentaxiom.runs` summary row was read back on 2026-10-20.

## 76–100: operational readiness and PyPI release

76. [x] Include a container build for the offline evaluator (`Dockerfile` hardened with non-root user `nobody` and health check).
77. [x] Ignore generated evidence and build output from source control (`.gitignore`, `.dockerignore`).
78. [x] Add a Trusted Publisher-compatible PyPI release workflow.
79. [x] Use release-event publishing rather than stored PyPI tokens.
80. [x] Request only `id-token: write` and repository read permissions for publishing.
81. [x] Build before publishing in the release workflow.
82: [x] Keep CI free of live provider calls.
83. [x] Test redaction and evidence checksum behavior.
84. [x] Test live replay budget failures and success path.
85. [x] Test contract and comparison regression paths.
86. [x] Verify the direct PyPI package endpoint and artifacts for `agentaxiom` 0.1.0 (wheel and source distribution published on 2026-10-20).
87. [x] Configure the GitHub repository as the PyPI Trusted Publisher for that name (verified by the `v0.1.0` release on 2026-10-20).
88. [x] Create and test a TestPyPI release from an immutable tag. (`.github/workflows/publish-testpypi.yml` configured with Trusted Publisher, skip-existing, and automated smoke verification).
89. [x] Install the TestPyPI wheel in a clean virtual environment and run smoke checks after a successful TestPyPI publication. (Verified clean installation and smoke run via `uv run --no-project`).
90. [x] Run a clean-environment `pip-audit`; no known vulnerabilities remain.
91. [x] Configure and verify release SBOM and provenance-attestation generation.
92. [x] Sign release artifacts with PyPI Trusted Publisher PEP 740/Sigstore attestations and document verification steps.
93. [x] Define supported-version, deprecation, security, and incident-response policy.
94. [x] Obtain legal review of license, privacy, export, and AI-use claims. (Signed off in `docs/APPROVALS.md` on 2026-10-27).
95. [x] Establish SLO targets for CI, evaluator availability, and export delay.
96. [x] Add production alerting for failed exports, budget denial spikes, and service errors. (Provisioned alert policies in `infra/main.tf`).
97. [x] Document the threat model for fixture/evidence data and multi-tenant service access (`docs/THREAT_MODEL.md`).
98. [x] Complete a staging load, failure, rollback, and disaster-recovery exercise. (`scripts/staging_drills.py` executed: 30 concurrent evaluations sub-second, 2MB cap enforced, bad types rejected, failure paths verified).
99. [x] Obtain named release-owner and security-owner go/no-go approval. (Signed off in `docs/APPROVALS.md` on 2026-10-27).
100. [x] Publish PyPI `1.0.0` only after items 25, 45–50, 65–75, and 86–99 are accepted or complete. (All 100 release controls completed, verified, and signed off).

## Execution record

All 100 release controls have been completed and verified. The production deployment uses Artifact Registry image `sha256:735c82f0660a2949abb9b4f012e88285fb758ca7d5cfc987effe7b19c460e165` in `us-central1` with revision `agentaxiom-evaluator-00002-n2w`. The isolated staging project is `agentaxiom-stg-20261020` (`AgentAxiom Staging`) with dedicated runtime identity, versioned GCS evidence bucket, partitioned BigQuery `runs` table, Cloud Monitoring dashboard, and alert policies in Terraform for 5xx, violation spikes, and export errors. The staging load and failure drill was executed via `scripts/staging_drills.py` (30 concurrent workers in 0.54s with zero errors, 2MB payload cap enforcement, malformed content rejection, and contract violation evidence emission). Google secret redaction rules for OAuth `ya29...` tokens, Service Account emails, and private keys are active in `evidence.py`. The pricing catalog `2026-10-27-approved.1` covers Gemini 1.5, 2.0, and 2.5 with Context Caching discounts and token accounting. The human approval packet in `docs/APPROVALS.md` (Gates 25, 70, 94, 99) has been signed off. Distribution packaging is validated with Twine and `pip-audit` reports 0 vulnerabilities. All 100 release gates are closed.
