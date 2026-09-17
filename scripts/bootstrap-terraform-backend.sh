#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${TFSTATE_RESOURCE_GROUP:-ecommerce-tfstate-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
STORAGE_ACCOUNT="${TFSTATE_STORAGE_ACCOUNT:-ecompocstate20260916}"
CONTAINER="${TFSTATE_CONTAINER:-tfstate}"

az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --output none

az storage container create \
  --name "$CONTAINER" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --output none

STORAGE_ID=$(az storage account show \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query id \
  --output tsv)

az role assignment create \
  --assignee-object-id "$(az ad signed-in-user show --query id --output tsv)" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_ID" \
  --output none 2>/dev/null || true

echo "Terraform backend ready: $RESOURCE_GROUP/$STORAGE_ACCOUNT/$CONTAINER"
