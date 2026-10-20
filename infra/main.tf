terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

provider "google" { project = var.project_id, region = var.region }

resource "google_storage_bucket" "evidence" {
  name                        = var.evidence_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  retention_policy { retention_period = var.retention_days * 86400 }
  versioning { enabled = true }
}

resource "google_bigquery_dataset" "agentaxiom" {
  dataset_id                 = var.dataset_id
  location                   = var.region
  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "runs" {
  dataset_id          = google_bigquery_dataset.agentaxiom.dataset_id
  table_id            = "runs"
  deletion_protection = true
  time_partitioning { type = "DAY", field = "recorded_at" }
  schema = jsonencode([
    { name = "scenario", type = "STRING", mode = "REQUIRED" },
    { name = "prompt_hash", type = "STRING", mode = "REQUIRED" },
    { name = "model", type = "STRING", mode = "REQUIRED" },
    { name = "region", type = "STRING", mode = "REQUIRED" },
    { name = "passed", type = "BOOL", mode = "REQUIRED" },
    { name = "violations", type = "STRING", mode = "NULLABLE" },
    { name = "latency_ms", type = "FLOAT", mode = "NULLABLE" },
    { name = "cost_usd", type = "FLOAT", mode = "NULLABLE" },
    { name = "recorded_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

resource "google_cloud_run_v2_service" "evaluator" {
  name     = "agentaxiom-evaluator"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  template {
    containers {
      image = var.image
      env { name = "AGENTAXIOM_EVIDENCE_DIR", value = "/tmp/agentaxiom-evidence" }
      resources { limits = { cpu = "1", memory = "512Mi" } }
    }
    scaling { max_instance_count = 3 }
  }
}

resource "google_monitoring_alert_policy" "service_errors" {
  count        = var.alert_notification_channel == "" ? 0 : 1
  display_name = "AgentAxiom Cloud Run errors"
  combiner     = "OR"
  conditions {
    display_name = "5xx responses"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.\"response_code_class\"=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "300s"
      aggregations { alignment_period = "60s", per_series_aligner = "ALIGN_RATE" }
    }
  }
  notification_channels = [var.alert_notification_channel]
}
