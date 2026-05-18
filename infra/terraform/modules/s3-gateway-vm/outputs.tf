output "private_ip_address" {
  value = azurerm_network_interface.this.private_ip_address
}

output "endpoint_url" {
  value = "http://${azurerm_network_interface.this.private_ip_address}:9000"
}
