output "service_account_email" {
  value = google_service_account.sa.email
}

output "service_account_key_path" {
  value = local_file.sa_key.filename
}
