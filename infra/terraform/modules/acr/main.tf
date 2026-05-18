resource "azurerm_container_registry" "this" {
  name                = substr(var.name_prefix, 0, 50)
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = var.tags
}
