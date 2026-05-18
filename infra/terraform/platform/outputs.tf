output "resource_group_name" {
  description = "Environment resource group."
  value       = local.resource_group_name
}

output "aks_cluster_name" {
  description = "AKS cluster name."
  value       = module.aks.name
}

output "acr_login_server" {
  description = "Azure Container Registry login server."
  value       = module.acr.login_server
}

output "postgresql_fqdn" {
  description = "Private PostgreSQL Flexible Server host name."
  value       = module.postgresql.fqdn
}

output "postgresql_database_name" {
  description = "Application database name."
  value       = module.postgresql.database_name
}

output "key_vault_name" {
  description = "Azure Key Vault name."
  value       = module.key_vault.name
}

output "key_vault_uri" {
  description = "Azure Key Vault URI."
  value       = module.key_vault.vault_uri
}

output "s3_gateway_endpoint_url" {
  description = "Internal S3-compatible endpoint backed by Azure Blob."
  value       = module.s3_gateway.endpoint_url
}

output "s3_access_key" {
  description = "S3 access key exposed by the gateway."
  value       = module.blob_storage.account_name
  sensitive   = true
}

output "s3_secret_key" {
  description = "S3 secret key exposed by the gateway."
  value       = module.blob_storage.primary_access_key
  sensitive   = true
}

output "github_actions_client_id" {
  description = "User-assigned managed identity client ID for GitHub Actions."
  value       = azurerm_user_assigned_identity.github_actions.client_id
}

output "external_secrets_client_id" {
  description = "User-assigned managed identity client ID for External Secrets."
  value       = azurerm_user_assigned_identity.external_secrets.client_id
}
