resource "azurerm_network_security_group" "this" {
  name                = "${var.name_prefix}-s3gw-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  security_rule {
    name                       = "allow-s3proxy"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "9000"
    source_address_prefixes    = var.allowed_cidrs
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "this" {
  name                = "${var.name_prefix}-s3gw-nic"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.private_ip_address
  }
}

resource "azurerm_network_interface_security_group_association" "this" {
  network_interface_id      = azurerm_network_interface.this.id
  network_security_group_id = azurerm_network_security_group.this.id
}

resource "azurerm_linux_virtual_machine" "this" {
  name                = "${var.name_prefix}-s3gw"
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = "Standard_B2s"
  admin_username      = var.admin_username
  network_interface_ids = [
    azurerm_network_interface.this.id,
  ]
  disable_password_authentication = true
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tpl", {
    storage_account_name = var.storage_account_name
    storage_account_key  = var.storage_account_key
    blob_endpoint        = var.blob_endpoint
    default_bucket_name  = var.default_bucket_name
    s3_access_key        = var.s3_access_key
    s3_secret_key        = var.s3_secret_key
  }))
  tags = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}
