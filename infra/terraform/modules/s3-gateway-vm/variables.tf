variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "allowed_cidrs" {
  type = list(string)
}

variable "admin_username" {
  type = string
}

variable "ssh_public_key" {
  type = string
}

variable "private_ip_address" {
  type = string
}

variable "storage_account_name" {
  type = string
}

variable "storage_account_key" {
  type      = string
  sensitive = true
}

variable "blob_endpoint" {
  type = string
}

variable "default_bucket_name" {
  type = string
}

variable "s3_access_key" {
  type = string
}

variable "s3_secret_key" {
  type      = string
  sensitive = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
