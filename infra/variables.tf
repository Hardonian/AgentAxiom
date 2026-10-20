variable "project_id" { type = string }
variable "region" { type = string, default = "us-central1" }
variable "image" { type = string, description = "Immutable Cloud Run image digest." }
variable "evidence_bucket_name" { type = string }
variable "dataset_id" { type = string, default = "agentaxiom" }
variable "retention_days" { type = number, default = 30 }
variable "alert_notification_channel" { type = string, default = "" }
