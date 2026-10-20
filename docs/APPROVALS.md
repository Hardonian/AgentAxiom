# Approval packet

Four open go-live gates need a named human decision; everything else is either
complete or blocked on infrastructure. Reply with the decisions (or edit the
checkboxes and commit) and the corresponding gate in `docs/GO_LIVE_100.md` can
be closed. Nothing here is applied automatically.

## Gate 25 — PII redaction patterns and retention policy

Proposed defaults for evidence bundles written by the CLI and the Cloud Run
service:

- Redact field names matching secret conventions (already implemented, gate 24)
  plus values shaped like: email addresses, US phone numbers, SSN-like
  `###-##-####`, payment-PAN-like digit runs (with Luhn check), and
  `Bearer`/`sk-`/`AIza`-prefixed tokens.
- Retention: local CLI evidence is caller-owned; GCS export objects follow the
  already-provisioned 30-day bucket lifecycle (gate 71); BigQuery `runs` rows
  are partitioned and expire after 90 days.

Decision:

- [ ] Approve the defaults above as the org pattern set and retention policy
- [ ] Approve with changes (specify below)
- [ ] Reject; org patterns will be supplied separately

Changes / org pattern file: _______________________________

Approver name: ____________________  Date: ____________

## Gate 70 — Pricing catalog approval

Draft catalog: `pricing/gemini-catalog-2026-10.json` (version
`2026-10-20-draft.1`). Rates verified 2026-10-20 against the official Gemini
API and Vertex pricing pages; each rate carries its own `effective_date` and
`source` URL. Known limits are recorded in the file's `notes` (Pro >200K-token
tier is not modeled; announced Dec-2026/Jan-2027 increases require re-verification).

Approving flips `approval_status` to `approved` in a follow-up commit; the
catalog stays a local file — AgentAxiom never fetches pricing remotely
(gate 57).

Decision:

- [ ] Approve `2026-10-20-draft.1` as the authoritative catalog
- [ ] Approve with changes (specify below)
- [ ] Reject; will supply an org catalog file

Changes: _______________________________

Approver name: ____________________  Date: ____________

## Gate 94 — Legal review scope

Requested review items and the exact files counsel needs:

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

- [ ] Approved as-is
- [ ] Approved with the changes listed below
- [ ] Changes required before any public 1.0.0 claim

Changes: _______________________________

Counsel / reviewer name: ____________  Date: ____________

## Gate 99 — Release-owner and security-owner go/no-go

Two named owners sign off after reviewing the items each owns:

Release owner confirms:

- [ ] `docs/GO_LIVE_100.md` has no `[ ]` item except those explicitly deferred
      with a recorded reason
- [ ] CHANGELOG, README, and PyPI metadata match the tagged artifact
- [ ] Rollback plan in `docs/OPERATIONS.md` has been rehearsed (gate 98)

Security owner confirms:

- [ ] Threat model reviewed against the shipped service (`docs/THREAT_MODEL.md`)
- [ ] No secrets, credentials, or customer data in the repository or artifacts
- [ ] Release SBOM and Sigstore attestations verified for the release tag

Release owner name: ________________  Date: ____________
Security owner name: _______________  Date: ____________
