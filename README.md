# E-Commerce Platform POC

An ecommerce application deployed on Azure.

This repository is a runnable starter for:

`GitHub -> GitHub Actions -> ACR -> GitOps repository -> Argo CD -> private AKS`

It contains five Flask services under `services/`, a browser storefront under `frontend/`, Dockerfiles for each runtime, Terraform for VNet, ACR, private AKS, Key Vault Workload Identity, SQL, Redis, Service Bus, APIM, Front Door, and WAF, and a copy-ready Helm chart under `gitops/helm/ecommerce`. The Argo CD application manifest is under `gitops/argocd`.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/product/requirements.txt
SERVICE_NAME=product python services/product/app.py
curl http://localhost:8080/healthz
```

To run the storefront, start the product service on port 8080 and the frontend on port 3000:

```bash
cd frontend
BACKEND_URL=http://localhost:8080 python app.py
```

Then open `http://localhost:3000`.

Build one image with `docker build -t product-service:local services/product`.

## Terraform

Bootstrap the remote state storage once while signed in with Azure CLI:

```bash
az login
./scripts/bootstrap-terraform-backend.sh
```

The script creates an Azure Storage account and private Terraform state container, then grants your Azure identity `Storage Blob Data Contributor`. The GitHub Actions Entra service principal also needs that role on the state storage account:

```bash
az role assignment create \
	--assignee <github-oidc-client-id> \
	--role "Storage Blob Data Contributor" \
	--scope "$(az storage account show --name ecompocstate20260916 --resource-group ecommerce-tfstate-rg --query id -o tsv)"
```

The backend is configured in `terraform/backend.tf` and uses Azure AD authentication rather than storage access keys. Do not commit a local state file or storage access key.

```bash
cd terraform
terraform init
terraform fmt -check -recursive
terraform validate
export TF_VAR_subscription_id=$(az account show --query id -o tsv)
export TF_VAR_tenant_id=$(az account show --query tenantId -o tsv)
export TF_VAR_sql_admin_password=$(openssl rand -hex 16)
terraform plan
```

The configuration creates the core platform resources and private endpoints. Review it before applying to a shared subscription; these Azure resources incur costs, and private AKS requires network access to the cluster from an approved administration path. The application is a single-replica, in-memory POC: orders and carts are not durable, and it is not production-ready without authentication, persistence, and payment controls.

### SQL password in Key Vault

For the first deployment, generate the password locally and apply Terraform. Then store the same value in the newly created private Key Vault:

```bash
export TF_VAR_sql_admin_password=$(openssl rand -hex 16)
terraform apply
az keyvault secret set --vault-name "$(terraform output -raw key_vault_name)" --name sql-admin-password --value "$TF_VAR_sql_admin_password"
```

For later plans and applies, retrieve it without printing it:

```bash
export TF_VAR_sql_admin_password=$(az keyvault secret show --vault-name "$(terraform output -raw key_vault_name)" --name sql-admin-password --query value -o tsv)
terraform plan
```

The Managed Redis access key is also stored in Key Vault for the cart service. If
the Redis secret is missing after the first apply, retrieve the key from Azure
and write it while connected to the private Key Vault network:

```bash
redis_key=$(az redisenterprise database list-keys \
	--resource-group ecommerce-poc-rg \
	--cluster-name ecommerce-poc-redis \
	--database-name default \
	--query primaryKey -o tsv)
az keyvault secret set --vault-name ecommercepockv \
	--name redis-primary-access-key --value "$redis_key"
unset redis_key
```

The Terraform GitHub Actions workflow performs this retrieval automatically. Because the Key Vault has private network access disabled, configure that workflow on a self-hosted runner with VNet/private-endpoint access, and set the repository variable `SQL_KEY_VAULT_NAME` plus optional `SQL_KEY_VAULT_SECRET_NAME`.

## GitHub Actions setup

Create an Entra application/service principal and a federated credential restricted to this repository and the `main` branch. Grant it `AcrPush` on the ACR resource. Add these Actions secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

No Azure client secret is used. GitHub Actions authenticates to Azure with OIDC.

To update a separate GitOps repository, set `GITOPS_REPOSITORY` to its `owner/repository` value and add `GITHUB_PUSH_TOKEN`: a fine-grained PAT or GitHub App token with `Contents: Read and write` permission on that repository. This token authenticates the GitHub checkout and push; it is separate from Azure credentials and local Git credentials.

Copy `gitops/` into the GitOps repository, replace `YOUR_ORG/ecommerce-gitops` in `gitops/argocd/application.yaml`, set `workloadIdentity.clientId` to the Terraform `workload_identity_client_id` output, and install the application in Argo CD. The workflow updates the five image tags in `helm/ecommerce/values.yaml` after pushing images.

## Validation

```bash
./validation.sh
python3 -m compileall -q services
helm template ecommerce gitops/helm/ecommerce
```

The existing Gateway API examples remain available under `kubernetes-gateway-api/`.
