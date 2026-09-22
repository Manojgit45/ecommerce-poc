resource "azurerm_api_management" "main" {
  name                = "${var.name_prefix}-apim"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  publisher_name      = var.apim_publisher_name
  publisher_email     = var.apim_publisher_email
  sku_name            = "Developer_1"
}

resource "azurerm_api_management_api" "ecommerce" {
  name                  = "ecommerce-api"
  resource_group_name   = azurerm_resource_group.main.name
  api_management_name   = azurerm_api_management.main.name
  revision              = "1"
  display_name          = "E-commerce API"
  description           = "Public API facade for the AKS ecommerce application."
  path                  = "ecommerce"
  protocols             = ["https"]
  service_url           = var.apim_backend_url
  subscription_required = false
}

locals {
  ecommerce_api_operations = {
    meta = {
      method       = "GET"
      url_template = "/meta"
    }
    products = {
      method       = "GET"
      url_template = "/products"
    }
    checkout = {
      method       = "POST"
      url_template = "/checkout"
    }
  }
}

resource "azurerm_api_management_api_operation" "ecommerce" {
  for_each            = local.ecommerce_api_operations
  operation_id        = each.key
  api_name            = azurerm_api_management_api.ecommerce.name
  api_management_name = azurerm_api_management.main.name
  resource_group_name = azurerm_resource_group.main.name
  display_name        = title(each.key)
  method              = each.value.method
  url_template        = each.value.url_template
}

