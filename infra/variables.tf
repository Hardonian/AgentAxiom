variable "project_id" {
  type        = string
  description = "The Google Cloud Platform project ID."
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "The Google Cloud region for resources."
}

variable "image" {
  type        = string
  description = "Immutable Cloud Run image digest."
}

variable "evidence_bucket_name" {
  type        = string
  description = "The globally unique name for the GCS evidence bucket."
}

variable "dataset_id" {
  type        = string
  default     = "agentaxiom"
  description = "The BigQuery dataset ID for run records."
}

variable "retention_days" {
  type        = number
  default     = 30
  description = "Retention period in days for evidence objects."
}

variable "alert_notification_channel" {
  type        = string
  default     = ""
  description = "Cloud Monitoring notification channel ID for alerts."
}
