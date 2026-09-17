#!/usr/bin/env bash
set -euo pipefail

: "${KEY_VAULT_NAME:?Set KEY_VAULT_NAME to the private Key Vault name}"
SECRET_NAME="${SQL_SECRET_NAME:-sql-admin-password}"

az keyvault secret show \
  --vault-name "$KEY_VAULT_NAME" \
  --name "$SECRET_NAME" \
  --query value \
  -o tsv