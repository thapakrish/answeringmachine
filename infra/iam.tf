resource "google_service_account" "sa" {
  project      = var.project_id
  account_id   = "answering-machine-sa"
  display_name = "AnsweringMachine Service Account"
}

resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.sa.email}"
}

resource "google_service_account_key" "sa_key" {
  service_account_id = google_service_account.sa.name
}

resource "local_file" "sa_key" {
  content  = base64decode(google_service_account_key.sa_key.private_key)
  filename = "${path.module}/../service-account.json"

  file_permission = "0600"
}
