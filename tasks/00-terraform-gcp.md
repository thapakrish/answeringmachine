# Task 00: Terraform GCP Setup

- **Priority**: P0
- **Deps**: none
- **PRD**: FR-6.1, FR-6.2, FR-6.3, FR-6.4
- **Approach**: IaC only (no TDD). Must be repeatable and idempotent.

## Objective

Provision all GCP resources via Terraform. No one-off commands.

## Files to Create

```
infra/
  main.tf              # Provider config, project data source, API enablement
  firestore.tf         # Firestore database (Native mode)
  iam.tf               # Service account + IAM binding
  outputs.tf           # Output service account key path
  variables.tf         # project_id, region, environment
  terraform.tfvars     # Actual values (MUST be .gitignored)
  .gitignore           # *.tfstate, *.tfstate.backup, terraform.tfvars, *.json keys
```

## Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `google_project_service` | `firestore.googleapis.com` | Enable Firestore API |
| `google_firestore_database` | `(default)` | Native mode Firestore database |
| `google_service_account` | `answering-machine-sa` | Service account for firebase-admin |
| `google_project_iam_member` | `roles/datastore.user` | Firestore read/write permission |
| `google_service_account_key` | JSON key | Credentials for local dev |
| `local_file` | `service-account.json` | Write key to project root |

## Key Requirements

- **Idempotent**: `terraform apply` can be run multiple times without error
- **Repeatable**: any team member can run `terraform apply` from scratch
- **Secure**: `service-account.json` and `terraform.tfvars` in `.gitignore`
- **No one-off commands**: everything tracked in `.tf` files

## Variables

```hcl
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Firestore"
  type        = string
  default     = "us-central1"  # or "nam5" for multi-region
}
```

## Outputs

```hcl
output "service_account_email" {
  value = google_service_account.sa.email
}

output "service_account_key_path" {
  value = local_file.sa_key.filename
}
```

## Verification

```bash
cd infra
terraform init
terraform plan        # Review resources to be created
terraform apply       # Create resources
# Verify: Firestore visible in GCP Console
# Verify: service-account.json created in project root
# Verify: running apply again shows "No changes"
```

## .gitignore additions (project root)

```
service-account.json
infra/*.tfstate
infra/*.tfstate.backup
infra/.terraform/
infra/terraform.tfvars
```
