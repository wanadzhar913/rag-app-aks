variable "subscription_id" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "github_repository" {
  type = string
}

variable "github_oidc_subject" {
  type = string
}

variable "postgresql_admin_password" {
  type      = string
  sensitive = true
}

variable "gateway_ssh_public_key" {
  type = string
}
