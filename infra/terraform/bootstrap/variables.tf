variable "subscription_id" {
  description = "Azure subscription used for the remote-state bootstrap resources."
  type        = string
}

variable "location" {
  description = "Azure region for the bootstrap resource group and storage account."
  type        = string
  default     = "southeastasia"
}

variable "name_prefix" {
  description = "Prefix applied to bootstrap resources."
  type        = string
  default     = "ragapp"
}

variable "resource_group_name" {
  description = "Optional explicit resource group name for Terraform state."
  type        = string
  default     = ""
}

variable "storage_account_name" {
  description = "Optional explicit storage account name for Terraform state."
  type        = string
  default     = ""
}

variable "container_name" {
  description = "Blob container used for Terraform state."
  type        = string
  default     = "tfstate"
}
