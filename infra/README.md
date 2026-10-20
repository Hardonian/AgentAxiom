# Google Cloud deployment

This Terraform root provisions a private, internal-load-balancer-only Cloud Run evaluator, a versioned public-access-prevented GCS evidence bucket, a protected partitioned BigQuery table, and an optional 5xx alert.

Before applying, create a staging GCP project; select an immutable image digest; choose a region compatible with BigQuery and storage residency; grant least-privilege roles to the deployment identity; set a tested retention value; and create a notification channel.

```bash
cd infra
terraform init
terraform plan -var project_id=PROJECT -var image=IMAGE@sha256:DIGEST -var evidence_bucket_name=UNIQUE_BUCKET
terraform apply
```

Do not apply this configuration to production until the staging exercise in [operations](../docs/OPERATIONS.md) is complete. Additional IAM bindings are deliberately not embedded: bind only the caller service accounts that need Cloud Run invocation, GCS writes, and BigQuery inserts.
