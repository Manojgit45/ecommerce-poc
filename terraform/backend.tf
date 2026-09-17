terraform {
  backend "azurerm" {
    resource_group_name  = "ecommerce-tfstate-rg"
    storage_account_name = "ecompocstate20260916"
    container_name       = "tfstate"
    key                  = "ecommerce-poc.tfstate"
    use_azuread_auth     = true
  }
}
