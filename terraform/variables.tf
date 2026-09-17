variable "subscription_id" {
  description = "Azure subscription ID used by the provider."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant ID used by Key Vault and workload identity."
  type        = string
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "name_prefix" {
  type    = string
  default = "ecommerce-poc"
}

variable "kubernetes_version" {
  type    = string
  default = null
}

variable "sql_admin_username" {
  type    = string
  default = "ecommerceadmin"
}

variable "sql_admin_password" {
  type      = string
  sensitive = true
}

variable "apim_publisher_name" {
  type    = string
  default = "E-commerce POC"
}

variable "apim_publisher_email" {
  type = string
}
