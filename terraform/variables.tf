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
  default = "centralus"
}

variable "name_prefix" {
  type    = string
  default = "ecommerce-poc"
}

variable "kubernetes_version" {
  type    = string
  default = null
}

variable "node_vm_size" {
  description = "VM size for the default AKS node pool."
  type        = string
  default     = "Standard_D2s_v7"
}

variable "jumpbox_vm_size" {
  description = "VM size for the private AKS administration jumpbox."
  type        = string
  default     = "Standard_D2s_v7"
}

variable "jumpbox_admin_username" {
  description = "Linux username for the private AKS administration jumpbox."
  type        = string
  default     = "azureadmin"
}

variable "jumpbox_ssh_public_key" {
  description = "SSH public key used to access the jumpbox through Azure Bastion."
  type        = string
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

variable "apim_backend_url" {
  description = "Public frontend hostname used by APIM to reach the ecommerce API proxy."
  type        = string
  default     = "http://ecommerce-poc-frontend.centralus.cloudapp.azure.com/api"
}
