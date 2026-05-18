# Terraform (`infra/terraform`)

Infrastructure is split into:
- `bootstrap/`: creates Terraform remote state resources.
- `platform/`: provisions Azure platform + AKS add-ons.
- `environments/{dev,prod}/`: environment-specific composition/variables.
- `modules/`: reusable building blocks (network, AKS, ACR, storage, etc.).

## Azure services used
- **Resource Group** (`azurerm_resource_group`)
- **Virtual Network + Subnets** (`azurerm_virtual_network`, `azurerm_subnet`)
- **Private DNS Zone** for PostgreSQL private networking (`azurerm_private_dns_zone`)
- **Azure Kubernetes Service (AKS)** (`azurerm_kubernetes_cluster`)
- **Azure Container Registry (ACR)** (`azurerm_container_registry`)
- **Azure Storage Account + Blob Container** (`azurerm_storage_account`, `azurerm_storage_container`)
- **Azure Database for PostgreSQL Flexible Server** (`azurerm_postgresql_flexible_server`)
- **Azure Key Vault** (`azurerm_key_vault`)
- **User Assigned Managed Identity** (`azurerm_user_assigned_identity`)
- **Federated Identity Credential** for workload/GitHub OIDC (`azurerm_federated_identity_credential`)
- **Role Assignments (RBAC)** (`azurerm_role_assignment`)
- **Linux Virtual Machine** (S3 gateway host) (`azurerm_linux_virtual_machine`)

## Prerequisite: configure Azure CLI first
Before running Terraform, install and configure Azure CLI:

```bash
az version
az login
az account set --subscription "<subscription-id>"
```

Guide: https://learn.microsoft.com/en-us/cli/azure/get-started-with-azure-cli?view=azure-cli-latest

## Minimal commands
```bash
# Bootstrap remote state infra
cd infra/terraform/bootstrap
terraform init && terraform apply

# Deploy platform (example: dev)
cd ../environments/dev
terraform init && terraform apply
```
