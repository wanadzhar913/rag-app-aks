resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

locals {
  name_prefix         = "${var.name_prefix}-${var.environment}"
  resource_group_name = "${local.name_prefix}-rg"
  tags = merge(
    {
      environment = var.environment
      managed_by  = "terraform"
      project     = "rag-app"
    },
    var.tags,
  )
}

module "network" {
  source = "../modules/network"

  resource_group_name    = local.resource_group_name
  location               = var.location
  name_prefix            = local.name_prefix
  vnet_cidr              = var.vnet_cidr
  aks_subnet_cidr        = var.aks_subnet_cidr
  postgresql_subnet_cidr = var.postgresql_subnet_cidr
  gateway_subnet_cidr    = var.gateway_subnet_cidr
  tags                   = local.tags
}

module "acr" {
  source = "../modules/acr"

  resource_group_name = local.resource_group_name
  location            = var.location
  name_prefix         = replace("${local.name_prefix}${random_string.suffix.result}", "-", "")
  tags                = local.tags
}

module "blob_storage" {
  source = "../modules/blob-storage"

  resource_group_name = local.resource_group_name
  location            = var.location
  name_prefix         = replace("${local.name_prefix}${random_string.suffix.result}", "-", "")
  container_name      = var.s3_bucket_name
  tags                = local.tags
}

module "key_vault" {
  source = "../modules/key-vault"

  resource_group_name = local.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  name_prefix         = replace("${local.name_prefix}kv", "-", "")
  tags                = local.tags
}

module "postgresql" {
  source = "../modules/postgresql"

  resource_group_name = local.resource_group_name
  location            = var.location
  name_prefix         = local.name_prefix
  database_name       = var.postgresql_database_name
  admin_username      = var.postgresql_admin_username
  admin_password      = var.postgresql_admin_password
  sku_name            = var.postgresql_sku_name
  subnet_id           = module.network.postgresql_subnet_id
  private_dns_zone_id = module.network.postgresql_private_dns_zone_id
  tags                = local.tags
}

module "aks" {
  source = "../modules/aks"

  resource_group_name = local.resource_group_name
  location            = var.location
  name_prefix         = local.name_prefix
  kubernetes_version  = var.kubernetes_version
  subnet_id           = module.network.aks_subnet_id
  node_count          = var.node_count
  node_vm_size        = var.node_vm_size
  acr_id              = module.acr.id
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "external_secrets" {
  name                = "${local.name_prefix}-eso-mi"
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "external_secrets" {
  name                      = "${local.name_prefix}-eso"
  user_assigned_identity_id = azurerm_user_assigned_identity.external_secrets.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = module.aks.oidc_issuer_url
  subject                   = "system:serviceaccount:external-secrets:external-secrets"
}

resource "azurerm_role_assignment" "external_secrets_key_vault" {
  scope                = module.key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.external_secrets.principal_id
}

module "s3_gateway" {
  source = "../modules/s3-gateway-vm"

  resource_group_name  = local.resource_group_name
  location             = var.location
  name_prefix          = local.name_prefix
  subnet_id            = module.network.gateway_subnet_id
  allowed_cidrs        = [var.aks_subnet_cidr]
  admin_username       = var.gateway_admin_username
  ssh_public_key       = var.gateway_ssh_public_key
  private_ip_address   = var.s3_gateway_private_ip
  storage_account_name = module.blob_storage.account_name
  storage_account_key  = module.blob_storage.primary_access_key
  blob_endpoint        = module.blob_storage.primary_blob_endpoint
  default_bucket_name  = var.s3_bucket_name
  s3_access_key        = module.blob_storage.account_name
  s3_secret_key        = module.blob_storage.primary_access_key
  tags                 = local.tags
}

resource "azurerm_user_assigned_identity" "github_actions" {
  name                = "${local.name_prefix}-gha-mi"
  location            = var.location
  resource_group_name = local.resource_group_name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "github_actions" {
  name                      = "${local.name_prefix}-gha"
  user_assigned_identity_id = azurerm_user_assigned_identity.github_actions.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = var.github_oidc_subject
}

resource "azurerm_role_assignment" "github_actions_acr_push" {
  scope                = module.acr.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github_actions.principal_id
}

locals {
  aks_kube_admin = {
    host                   = module.aks.kube_admin_host
    username               = module.aks.kube_admin_username
    password               = module.aks.kube_admin_password
    client_certificate     = base64decode(module.aks.kube_admin_client_certificate)
    client_key             = base64decode(module.aks.kube_admin_client_key)
    cluster_ca_certificate = base64decode(module.aks.kube_admin_cluster_ca_certificate)
  }
}

provider "kubernetes" {
  host                   = local.aks_kube_admin.host
  username               = local.aks_kube_admin.username
  password               = local.aks_kube_admin.password
  client_certificate     = local.aks_kube_admin.client_certificate
  client_key             = local.aks_kube_admin.client_key
  cluster_ca_certificate = local.aks_kube_admin.cluster_ca_certificate
}

provider "helm" {
  kubernetes = local.aks_kube_admin
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true
  version          = "7.7.16"

  values = [
    yamlencode({
      configs = {
        params = {
          "server.insecure" = true
        }
      }
      server = {
        service = {
          type = "ClusterIP"
        }
      }
    })
  ]

  depends_on = [module.aks]
}

resource "helm_release" "external_secrets" {
  name             = "external-secrets"
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  namespace        = "external-secrets"
  create_namespace = true
  version          = "0.14.4"

  values = [
    yamlencode({
      installCRDs = true
      serviceAccount = {
        create = true
        name   = "external-secrets"
        annotations = {
          "azure.workload.identity/client-id" = azurerm_user_assigned_identity.external_secrets.client_id
        }
        labels = {
          "azure.workload.identity/use" = "true"
        }
      }
      podLabels = {
        "azure.workload.identity/use" = "true"
      }
    })
  ]

  depends_on = [module.aks, azurerm_federated_identity_credential.external_secrets]
}

resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  version          = "4.11.3"

  values = [
    yamlencode({
      controller = {
        service = merge(
          {
            type = "LoadBalancer"
          },
          length(var.allowed_ingress_cidrs) > 0 ? {
            loadBalancerSourceRanges = var.allowed_ingress_cidrs
          } : {}
        )
      }
    })
  ]

  depends_on = [module.aks]
}
