resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  resource_group_name  = var.resource_group_name != "" ? var.resource_group_name : "${var.name_prefix}-tfstate-rg"
  storage_account_name = var.storage_account_name != "" ? var.storage_account_name : substr(replace("${var.name_prefix}tf${random_string.suffix.result}", "-", ""), 0, 24)
}

resource "azurerm_resource_group" "this" {
  name     = local.resource_group_name
  location = var.location
}

resource "azurerm_storage_account" "this" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "this" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}
