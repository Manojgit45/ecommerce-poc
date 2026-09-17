output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "aks_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "workload_identity_client_id" {
  value = azurerm_user_assigned_identity.workload.client_id
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "service_bus_namespace" {
  value = azurerm_servicebus_namespace.main.name
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "sql_server_fqdn" {
  value = azurerm_mssql_server.main.fully_qualified_domain_name
}

output "front_door_hostname" {
  value = azurerm_cdn_frontdoor_endpoint.main.host_name
}

output "apim_gateway_url" {
  value = azurerm_api_management.main.gateway_url
}
