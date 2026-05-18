variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "container_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
