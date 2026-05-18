resource "azurerm_key_vault" "this" {
  name                          = substr(var.name_prefix, 0, 24)
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  purge_protection_enabled      = true
  soft_delete_retention_days    = 7
  enable_rbac_authorization     = true
  public_network_access_enabled = true
  tags                          = var.tags
}
