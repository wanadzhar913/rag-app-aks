variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "southeastasia"
}

variable "name_prefix" {
  description = "Prefix applied to all Azure resources."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name format."
  type        = string
}

variable "github_oidc_subject" {
  description = "GitHub OIDC subject allowed to push images, for example repo:owner/name:ref:refs/heads/main."
  type        = string
}

variable "kubernetes_version" {
  description = "AKS version."
  type        = string
  default     = "1.31.1"
}

variable "node_count" {
  description = "Default AKS node count."
  type        = number
  default     = 2
}

variable "node_vm_size" {
  description = "AKS node pool VM size."
  type        = string
  default     = "Standard_D4s_v5"
}

variable "vnet_cidr" {
  description = "CIDR range for the shared virtual network."
  type        = string
}

variable "aks_subnet_cidr" {
  description = "CIDR range for the AKS subnet."
  type        = string
}

variable "postgresql_subnet_cidr" {
  description = "CIDR range for the delegated PostgreSQL subnet."
  type        = string
}

variable "gateway_subnet_cidr" {
  description = "CIDR range for the S3 gateway VM subnet."
  type        = string
}

variable "postgresql_admin_username" {
  description = "Administrator username for Azure Database for PostgreSQL."
  type        = string
  default     = "ragadmin"
}

variable "postgresql_admin_password" {
  description = "Administrator password for Azure Database for PostgreSQL."
  type        = string
  sensitive   = true
}

variable "postgresql_database_name" {
  description = "Application database name."
  type        = string
  default     = "rag_app_db"
}

variable "postgresql_sku_name" {
  description = "SKU for PostgreSQL Flexible Server."
  type        = string
  default     = "B_Standard_B2s"
}

variable "s3_bucket_name" {
  description = "Default bucket/container name used by the application."
  type        = string
  default     = "documents"
}

variable "gateway_admin_username" {
  description = "Admin username for the S3 gateway VM."
  type        = string
  default     = "azureuser"
}

variable "gateway_ssh_public_key" {
  description = "SSH public key allowed onto the S3 gateway VM."
  type        = string
}

variable "s3_gateway_private_ip" {
  description = "Static private IP address assigned to the S3 gateway VM."
  type        = string
}

variable "allowed_ingress_cidrs" {
  description = "Optional source CIDRs for the public ingress controller load balancer."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Extra Azure tags."
  type        = map(string)
  default     = {}
}
