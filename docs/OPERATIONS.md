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
