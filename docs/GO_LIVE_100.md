# AgentAxiom: top 100 go-live priorities

This is the release gate, ordered by risk and dependency. `[x]` means executed in this repository or validated in the current deployed cloud environment as of 2026-10-20. `[ ]` needs an owner, credentials, or a real production environment; it is intentionally not claimed as complete.

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
18. [x] Support configurable ignored volatile output paths.
19. [x] Minimize failing multi-turn traces.
20. [x] Generate redacted JSON and HTML evidence.
21. [x] Add an evidence ID and checksum manifest.
22. [x] Verify evidence bundle integrity.
23. [x] Make evidence writes atomic across Windows/Linux.
24. [x] Redact secret-named fields and known key patterns.
25. [ ] Approve organization-specific PII redaction patterns and retention policy.

## 26–50: package and developer experience

26. [x] Publish a documented CLI (`check`, `compare`, `minimize`).
27. [x] Provide a pytest plugin fixture.
28. [x] Provide complete offline examples.
29. [x] Include a typed-package marker.
30. [x] Use a `src/` layout and PEP 621 metadata.
31. [x] Separate runtime, test, lint, Vertex, and export dependencies.
32. [x] Add project classifiers, keywords, and project URLs.
33. [x] Add Apache-2.0 license metadata and license file.
34. [x] Add changelog with release conventions.
35. [x] Add contribution and evidence-compatibility guidance.
36. [x] Add a vulnerability reporting policy.
37. [x] Add Ruff configuration and enforce it in CI.
38. [x] Format the codebase consistently.
39. [x] Test Python 3.10, 3.11, and 3.12 in CI.
40. [x] Build wheel and source distributions in CI.
41. [x] Validate distribution metadata with Twine in CI.
42. [x] Add a reusable composite GitHub Action.
43. [x] Fix the Action to install itself, not the consuming repo.
44. [x] Upload CI evidence artifacts on failure.
45. [x] Add a user-facing API reference for stable public APIs.
46. [x] Add a migration guide and policy for every future evidence schema version.
47. [x] Add contract and fixture JSON Schemas as public files.
48. [x] Add a compatibility test suite for the current released v1 fixtures.
49. [x] Add an automated dependency-update bot with human review.
50. [x] Add release notes automation from merged pull requests.

## 51–75: provider, platform, and data reliability

51. [x] Supply an optional Gemini Developer API adapter.
52. [x] Supply an optional Vertex AI adapter selected by project presence.
53. [x] Record model, region, generation, tools, usage, latency, and raw provider response.
54. [x] Record parsed structured output and function calls.
55. [x] Record grounding and safety metadata supplied by Gemini.
56. [x] Support user-supplied versioned pricing catalogs.
57. [x] Avoid remote pricing lookups and hidden cost assumptions.
58. [x] Provide optional sanitized GCS export.
59. [x] Provide optional BigQuery summary export.
60. [x] Capture Cloud Trace correlation header on service evaluation.
61. [x] Provide Cloud Run health, evaluation, and comparison endpoints.
62. [x] Cap Cloud Run request size at 2 MB.
63. [x] Keep Cloud Run evaluation offline-only.
64. [x] Restrict service evidence writes to server configuration.
65. [ ] Validate the provider adapter against an isolated real Gemini project (no Gemini Developer API credential is configured here).
66. [x] Validate the provider adapter against the real Vertex AI project in the configured target region, `us-central1` (`gemini-2.5-flash`, one bounded structured-output call).
67. [x] Implement an offline ADK event-recording normalization adapter; live ADK-version validation remains required.
68. [ ] Add provider retry, timeout, and error-normalization policies after live API testing.
69. [ ] Add model-specific token accounting verified against invoices.
70. [ ] Approve a maintained pricing catalog with effective dates.
71. [x] Provision GCS bucket IAM and retention controls: uniform bucket-level access, public-access prevention, a 30-day retention policy, and runtime object-creator access. Retention lock and CMEK remain unconfigured because they require approved governance requirements.
72. [x] Provision the `agentaxiom` BigQuery dataset and partitioned `runs` table with a dataset-level runtime writer identity and project-level job-user role.
73. [x] Deploy Cloud Run with IAM authentication, internal/load-balancer-only ingress, a dedicated runtime service account, and a three-instance revision cap.
74. [ ] The Cloud Monitoring dashboard is deployed; configure Cloud Trace sampling and alert routing after an approved notification channel and on-call owner exist.
75. [ ] A real export/retrieval chain succeeded in the current cloud project: a synthetic email-shaped field was redacted in GCS and its matching summary row was read back from BigQuery. Designate an isolated non-production project before closing this gate.

## 76–100: operational readiness and PyPI release

76. [x] Include a container build for the offline evaluator.
77. [x] Ignore generated evidence and build output from source control.
78. [x] Add a Trusted Publisher-compatible PyPI release workflow.
79. [x] Use release-event publishing rather than stored PyPI tokens.
80. [x] Request only `id-token: write` and repository read permissions for publishing.
81. [x] Build before publishing in the release workflow.
82. [x] Keep CI free of live provider calls.
83. [x] Test redaction and evidence checksum behavior.
84. [x] Test live replay budget failures and success path.
85. [x] Test contract and comparison regression paths.
86. [x] Verify the direct PyPI package endpoint and artifacts for `agentaxiom` 0.1.0 (wheel and source distribution published on 2026-10-20).
87. [x] Configure the GitHub repository as the PyPI Trusted Publisher for that name (verified by the `v0.1.0` release on 2026-10-20).
88. [ ] Create and test a TestPyPI release from an immutable tag.
89. [ ] Install the TestPyPI wheel in a clean virtual environment and run smoke checks.
90. [x] Run a clean-environment `pip-audit`; no known vulnerabilities remain after bootstrap pip update.
91. [x] Configure and verify release SBOM and provenance-attestation generation.
92. [x] Sign release artifacts with PyPI Trusted Publisher PEP 740/Sigstore attestations and document verification steps (verified for both `0.1.0` distributions on 2026-10-20).
93. [x] Define supported-version, deprecation, security, and incident-response policy.
94. [ ] Obtain legal review of license, privacy, export, and AI-use claims.
95. [x] Establish SLO targets for CI, evaluator availability, and export delay.
96. [ ] Add production alerting for failed exports, budget denial spikes, and service errors.
97. [x] Document the threat model for fixture/evidence data and multi-tenant service access.
98. [ ] Complete a staging load, failure, rollback, and disaster-recovery exercise.
99. [ ] Obtain named release-owner and security-owner go/no-go approval.
100. [ ] Publish PyPI `1.0.0` only after items 25, 45–50, 65–75, and 86–99 are accepted or complete.

## Execution record

Repository-controlled items marked complete above have been implemented. The current deployment uses Artifact Registry image `sha256:735c82f0660a2949abb9b4f012e88285fb758ca7d5cfc987effe7b19c460e165` in `us-central1`; its current Cloud Run revision is `agentaxiom-evaluator-00002-n2w`. The GitHub/PyPI Trusted Publisher path was verified by publishing `agentaxiom` 0.1.0 from release `v0.1.0` on 2026-10-20: the release job built the distributions, attached an SBOM, generated provenance, and uploaded the wheel and source distribution; a clean-environment PyPI install completed the offline contract smoke check. External gates remain deliberately open where they require a Gemini Developer API credential, a monitoring notification channel, governance approval, legal review, or named release-owner approval. The final 1.0.0 release remains gated by the items specified above.
