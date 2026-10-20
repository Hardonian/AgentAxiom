# Operations and incident readiness

## SLO targets

- Offline evaluation success: 99.9% monthly, excluding invalid requests.
- `/healthz` availability: 99.9% monthly.
- GCS/BigQuery export delivery: 99% within 10 minutes after a successful invocation.
- CI contract feedback: 95% within 10 minutes.

## Alerts

Alert on Cloud Run 5xx rate, p95 latency, failed exports, and sustained live-budget denials. Route alerts to the named on-call owner and include evidence ID, trace ID, model, region, and error category—never raw prompt or response content.

## Rollback

Release immutable image tags. Roll back Cloud Run traffic to the preceding image revision, disable live verification by setting its call budget to zero, and preserve sanitized evidence bundles. Revoke compromised service accounts, then rotate impacted secrets outside AgentAxiom.

## Staging exercise

Before production, deploy the same image to a restricted staging project. Run offline checks, an opt-in bounded live confirmation, denied-budget test, malformed-request test, export permission denial test, Cloud Trace correlation test, and rollback. Record results against the go-live gate.

## Live adapter smoke test

The repository includes a deliberately tiny Vertex validation at `scripts/live_vertex_smoke.py`. It requires `AGENTAXIOM_LIVE_SMOKE=1` and an explicit `GOOGLE_CLOUD_PROJECT`, uses `gemini-2.5-flash` in `us-central1` (or `AGENTAXIOM_VERTEX_REGION`), sends one non-sensitive JSON instruction, caps output at 32 tokens, and declares no tools. It fails unless it receives the expected structured result. Run it only in an isolated project with billing and approved model access.

`scripts/live_export_smoke.py` similarly requires `AGENTAXIOM_EXPORT_SMOKE=1`, `AGENTAXIOM_EXPORT_BUCKET`, and `AGENTAXIOM_EXPORT_TABLE`; it exports a synthetic record containing an email-shaped value, which must be redacted in the resulting GCS evidence object and represented as one BigQuery summary row.
