#!/bin/bash

set +o errexit
set -o pipefail
set -o nounset
set -o xtrace # For debugging

#####################
# DEPLOY ARM TEMPLATE

echo "Deploying to Subscription: $AZURE_SUBSCRIPTION_ID"

# Create resource group
resource_group_name="$PROJECT-$DEPLOYMENT_ID-$ENV_NAME-rg"
echo "Creating resource group: $resource_group_name"
az group create --name "$resource_group_name" --location "$AZURE_LOCATION" --tags Environment="$ENV_NAME"

# By default, set all KeyVault permissions to deployer
# Retrieve KeyVault User Id
kv_owner_object_id=$(az ad signed-in-user show --output json | jq -r '.id')

# Validate arm template
echo "Validating deployment"
arm_output=$(az deployment group validate \
    --resource-group "$resource_group_name" \
    --template-file "./infra/main.bicep" \
    --parameters @"./infra/main.parameters.${ENV_NAME}.json" \
    --parameters project="${PROJECT}" keyvault_owner_object_id="${kv_owner_object_id}" deployment_id="${DEPLOYMENT_ID}" sql_server_password="${AZURESQL_SERVER_PASSWORD}" \
    --output json)

# Deploy arm template
echo "Deploying resources into $resource_group_name"
arm_output=$(az deployment group create \
    --resource-group "$resource_group_name" \
    --template-file "./infra/main.bicep" \
    --parameters @"./infra/main.parameters.${ENV_NAME}.json" \
    --parameters project="${PROJECT}" deployment_id="${DEPLOYMENT_ID}" keyvault_owner_object_id="${kv_owner_object_id}" sql_server_password="${AZURESQL_SERVER_PASSWORD}" \
    --output json)

if [[ -z $arm_output ]]; then
    echo >&2 "ARM deployment failed."
    exit 1
fi

# RETRIEVE KEYVAULT INFORMATION
echo "Retrieving KeyVault information from the deployment."

kv_name=$(echo "$arm_output" | jq -r '.properties.outputs.keyvault_name.value')
kv_dns_name=https://${kv_name}.vault.azure.net/

# Store in KeyVault
az keyvault secret set --vault-name "$kv_name" --name "kvUrl" --value "$kv_dns_name"
az keyvault secret set --vault-name "$kv_name" --name "subscriptionId" --value "$AZURE_SUBSCRIPTION_ID"

# CONFIGURE ADLS GEN2

# Retrieve storage account and key
azure_storage_account=$(echo "$arm_output" | jq -r '.properties.outputs.storage_account_name.value')
azure_storage_key=$(az storage account keys list \
    --resource-group "$resource_group_name" \
    --account-name "$azure_storage_account" \
    --output json |
    jq -r '.[0].value')

# Create file systems
file_systems=("landing" "raw" "structured" "curated" "sandbox" "logs" "reference")
for file_system in "${file_systems[@]}"; do
    echo "Creating ADLS Gen2 File system: $file_system"
    az storage container create --name "$file_system" --account-name "$azure_storage_account" --account-key "$azure_storage_key"
done

# Add source system folders
for file_system in raw structured; do
  sources=("artifax" "spektrix" "access")
  for folder in "${sources[@]}"; do
      echo "Creating folder: $folder"
      az storage fs directory create -n "provider/$folder" -f "$file_system" --account-name "$azure_storage_account" --account-key "$azure_storage_key"
  done
done
az storage fs directory create -n "provider/spektrix/reports" -f "landing" --account-name "$azure_storage_account" --account-key "$azure_storage_key"
az storage fs directory create -n "adf" -f "logs" --account-name "$azure_storage_account" --account-key "$azure_storage_key"

# Set Keyvault secrets
az keyvault secret set --vault-name "$kv_name" --name "datalakeAccountName" --value "$azure_storage_account"
az keyvault secret set --vault-name "$kv_name" --name "datalakeKey" --value "$azure_storage_key"
az keyvault secret set --vault-name "$kv_name" --name "datalakeurl" --value "https://$azure_storage_account.dfs.core.windows.net"

###################
# SQL

echo "Retrieving SQL Server information from the deployment."
# Retrieve SQL creds
sql_server_name=$(echo "$arm_output" | jq -r '.properties.outputs.sql_server_output.value.name')
sql_server_username=$(echo "$arm_output" | jq -r '.properties.outputs.sql_server_output.value.username')
sql_dw_database_name=$(echo "$arm_output" | jq -r '.properties.outputs.sql_server_output.value.database_name')

# SQL Connection String
sql_dw_connstr_nocred=$(az sql db show-connection-string --client ado.net \
    --name "$sql_dw_database_name" --server "$sql_server_name" --output json |
    jq -r .)
sql_dw_connstr_uname=${sql_dw_connstr_nocred/<username>/$sql_server_username}
sql_dw_connstr_uname_pass=${sql_dw_connstr_uname/<password>/$AZURESQL_SERVER_PASSWORD}

# Store in Keyvault
az keyvault secret set --vault-name "$kv_name" --name "sqlsrvrName" --value "$sql_server_name"
az keyvault secret set --vault-name "$kv_name" --name "sqlsrvUsername" --value "$sql_server_username"
az keyvault secret set --vault-name "$kv_name" --name "sqlsrvrPassword" --value "$AZURESQL_SERVER_PASSWORD"
az keyvault secret set --vault-name "$kv_name" --name "sqldwDatabaseName" --value "$sql_dw_database_name"
az keyvault secret set --vault-name "$kv_name" --name "sqldwConnectionString" --value "$sql_dw_connstr_uname_pass"

####################
# DATA FACTORY

# Store in Keyvault
datafactory_name=$(echo "$arm_output" | jq -r '.properties.outputs.datafactory_name.value')
az keyvault secret set --vault-name "$kv_name" --name "adfName" --value "$datafactory_name"

####################
# FUNCTION APP

# Retrieve FA Key
function_app_name=$(echo "$arm_output" | jq -r '.properties.outputs.function_app_name.value')
azure_function_app_key=$(az functionapp keys list \
    --resource-group "$resource_group_name" \
    --name "$function_app_name" \
    --output json |
    jq -r '.functionKeys.default')

# Store in keyvault
az keyvault secret set --vault-name "$kv_name" --name "functionAppKey" --value "$azure_function_app_key"

####################
# AZDO Variable Groups
PROJECT=$PROJECT \
ENV_NAME=$ENV_NAME \
AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
RESOURCE_GROUP_NAME=$resource_group_name \
AZURE_LOCATION=$AZURE_LOCATION \
KV_URL=$kv_dns_name \
SQL_SERVER_NAME=$sql_server_name \
SQL_SERVER_USERNAME=$sql_server_username \
SQL_SERVER_PASSWORD=$AZURESQL_SERVER_PASSWORD \
SQL_DW_DATABASE_NAME=$sql_dw_database_name \
AZURE_STORAGE_KEY=$azure_storage_key \
AZURE_STORAGE_ACCOUNT=$azure_storage_account \
DATAFACTORY_NAME=$datafactory_name \
    bash -c "./scripts/deploy_azdo_variables.sh"

####################
# BUILD ENV FILE FROM CONFIG INFORMATION

env_file=".env.${ENV_NAME}"
echo "Appending configuration to .env file."
cat << EOF >> "$env_file"

# ------ Configuration from deployment on ${TIMESTAMP} -----------
RESOURCE_GROUP_NAME=${resource_group_name}
AZURE_LOCATION=${AZURE_LOCATION}
SQL_SERVER_NAME=${sql_server_name}
SQL_SERVER_USERNAME=${sql_server_username}
SQL_SERVER_PASSWORD=${AZURESQL_SERVER_PASSWORD}
SQL_DW_DATABASE_NAME=${sql_dw_database_name}
AZURE_STORAGE_ACCOUNT=${azure_storage_account}
AZURE_STORAGE_KEY=${azure_storage_key}
DATAFACTORY_NAME=$datafactory_name
KV_URL=${kv_dns_name}

EOF
echo "Completed deploying Azure resources $resource_group_name ($ENV_NAME)"