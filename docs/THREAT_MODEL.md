# Threat model

| Asset | Main risk | Control |
| --- | --- | --- |
| Prompts and responses | Sensitive data in evidence | Offline defaults, recursive redaction, restricted exports, retention policy |
| Cloud Run evaluator | Unauthenticated use or path writes | Cloud Run IAM, ingress restriction, request cap, server-owned evidence directory |
| Live provider budget | Unexpected spend | Explicit opt-in, total and per-call ceilings, CI prohibition |
| Evidence integrity | Tampering or partial writes | SHA-256 manifest and atomic writes |
| Export credentials | Data exfiltration | Workload identity, least privilege, no credentials in fixtures |

Residual risks require owner approval: project-specific PII redaction, third-party tool behavior, model-provider retention, and access reviews.
