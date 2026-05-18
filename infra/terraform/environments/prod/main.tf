module "platform" {
  source = "../../platform"

  subscription_id            = var.subscription_id
  tenant_id                  = var.tenant_id
  environment                = "prod"
  location                   = "southeastasia"
  name_prefix                = "ragapp"
  github_repository          = var.github_repository
  github_oidc_subject        = var.github_oidc_subject
  kubernetes_version         = "1.31.1"
  node_count                 = 3
  node_vm_size               = "Standard_D8s_v5"
  vnet_cidr                  = "10.40.0.0/16"
  aks_subnet_cidr            = "10.40.0.0/20"
  postgresql_subnet_cidr     = "10.40.16.0/24"
  gateway_subnet_cidr        = "10.40.17.0/24"
  postgresql_sku_name        = "GP_Standard_D4s_v5"
  postgresql_admin_password  = var.postgresql_admin_password
  gateway_ssh_public_key     = var.gateway_ssh_public_key
  s3_gateway_private_ip      = "10.40.17.10"
  allowed_ingress_cidrs      = []
  tags = {
    owner = "platform"
    tier  = "production"
  }
}

output "acr_login_server" {
  value = module.platform.acr_login_server
}

output "github_actions_client_id" {
  value = module.platform.github_actions_client_id
}

output "key_vault_uri" {
  value = module.platform.key_vault_uri
}

output "postgresql_fqdn" {
  value = module.platform.postgresql_fqdn
}

output "s3_gateway_endpoint_url" {
  value = module.platform.s3_gateway_endpoint_url
}
