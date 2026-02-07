variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Firestore"
  type        = string
  default     = "nam5"
}
