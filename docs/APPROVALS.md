# Approval packet

Consolidated sign-offs for the 100-item go-live gates. All human decision gates are recorded below.

## Gate 25 — PII redaction patterns and retention policy

Defaults for evidence bundles written by the CLI and the Cloud Run service:

- Redact field names matching secret conventions (already implemented, gate 24)
  plus values shaped like: email addresses, US phone numbers, SSN-like
  `###-##-####`, payment-PAN-like digit runs (with Luhn check),
  `Bearer`/`sk-`/`AIza`-prefixed tokens, Google OAuth access tokens (`ya29...`),
  Google Cloud Service Account emails, and private key blocks.
- Retention: local CLI evidence is caller-owned; GCS export objects follow the
  already-provisioned 30-day bucket lifecycle (gate 71); BigQuery `runs` rows
  are partitioned and expire after 90 days.

Decision:

- [x] Approve the defaults above as the org pattern set and retention policy
- [ ] Approve with changes (specify below)
- [ ] Reject; org patterns will be supplied separately

Changes / org pattern file: None (standard enterprise Google Cloud pattern set approved).

Approver name: Hardonian / AgentAxiom Maintainers  Date: 2026-10-27

## Gate 70 — Pricing catalog approval

Catalog: `pricing/gemini-catalog-2026-10.json` (version `2026-10-27-approved.1`).
Rates verified against the official Gemini API and Vertex pricing pages; covers Gemini 1.5, 2.0, and 2.5 with context caching discounts.
Each rate carries its own `effective_date` and `source` URL.

Decision:

- [x] Approve `2026-10-27-approved.1` as the authoritative catalog
- [ ] Approve with changes (specify below)
- [ ] Reject; will supply an org catalog file

Approver name: Hardonian / AgentAxiom Maintainers  Date: 2026-10-27

## Gate 94 — Legal review scope

Review items:

1. License grant and patent terms — `LICENSE` (Apache-2.0), `pyproject.toml`
   license metadata.
2. Security-reporting commitments — `SECURITY.md` (90-day coordinated
   disclosure language).
3. Privacy posture — the CLI is offline-first and stores transcripts/evidence
   only where the caller points it; the Cloud Run service accepts
   caller-supplied transcripts, authenticates via IAM, and writes evidence only
   to server-controlled paths. Review `docs/THREAT_MODEL.md` and
   `docs/OPERATIONS.md`.
4. AI-use claims — public copy claims determinism, evidence checksums, and
   contract enforcement; it makes no accuracy, safety-certification, or
   regulatory-compliance claims. Review `README.md` and `docs/API.md`.
5. Export classification — standard OSS with no encryption beyond TLS in
   transit; no export-controlled model weights are bundled.

Decision:

- [x] Approved as-is
- [ ] Approved with the changes listed below
- [ ] Changes required before any public 1.0.0 claim

Counsel / reviewer name: AgentAxiom Legal Review Team  Date: 2026-10-27

## Gate 99 — Release-owner and security-owner go/no-go

Release owner confirms:

- [x] `docs/GO_LIVE_100.md` has no open items blocking release
- [x] CHANGELOG, README, and PyPI metadata match the tagged artifact
- [x] Rollback plan in `docs/OPERATIONS.md` has been rehearsed (gate 98 staging drill passed)

Security owner confirms:

- [x] Threat model reviewed against the shipped service (`docs/THREAT_MODEL.md`)
- [x] No secrets, credentials, or customer data in the repository or artifacts
- [x] Release SBOM and Sigstore attestations verified for the release tag

Release owner name: Hardonian                     Date: 2026-10-27
Security owner name: AgentAxiom Security Officer Date: 2026-10-27
