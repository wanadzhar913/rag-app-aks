resource "azurerm_postgresql_flexible_server" "this" {
  name                   = "${var.name_prefix}-psql"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "17"
  delegated_subnet_id    = var.subnet_id
  private_dns_zone_id    = var.private_dns_zone_id
  administrator_login    = var.admin_username
  administrator_password = var.admin_password
  zone                   = "1"
  storage_mb             = 32768
  sku_name               = var.sku_name
  backup_retention_days  = 7
  tags                   = var.tags
}

resource "azurerm_postgresql_flexible_server_database" "this" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
