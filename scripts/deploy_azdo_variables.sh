#!/bin/bash

#######################################################
# Deploys Azure DevOps Variable Groups
#
# Prerequisites:
# - User is logged in to the azure cli
# - Correct Azure subscription is selected
# - Correct Azure DevOps Project selected
#######################################################

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace # For debugging

# Create vargroup
vargroup_name="${PROJECT}-release-$ENV_NAME"
if vargroup_id=$(az pipelines variable-group list -o tsv | grep "$vargroup_name" | awk '{print $3}'); then
    echo "Variable group: $vargroup_name already exists. Deleting..."
    az pipelines variable-group delete --id "$vargroup_id" -y
fi
echo "Creating variable group: $vargroup_name"
az pipelines variable-group create \
    --name "$vargroup_name" \
    --authorize "true" \
    --variables \
        azureLocation="$AZURE_LOCATION" \
        rgName="$RESOURCE_GROUP_NAME" \
        adfName="$DATAFACTORY_NAME" \

    --output json

# Create vargroup - for secrets
vargroup_secrets_name="${PROJECT}-secrets-$ENV_NAME"
if vargroup_secrets_id=$(az pipelines variable-group list -o tsv | grep "$vargroup_secrets_name" | awk '{print $3}'); then
    echo "Variable group: $vargroup_secrets_name already exists. Deleting..."
    az pipelines variable-group delete --id "$vargroup_secrets_id" -y
fi
echo "Creating variable group: $vargroup_secrets_name"
vargroup_secrets_id=$(az pipelines variable-group create \
    --name "$vargroup_secrets_name" \
    --authorize "true" \
    --output json \
    --variables foo="bar" | jq -r .id)  # Needs at least one secret

az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "subscriptionId" --value "$AZURE_SUBSCRIPTION_ID"
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "kvUrl" --value "$KV_URL"
# sql server
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "sqlsrvrName" --value "$SQL_SERVER_NAME"
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "sqlsrvrUsername" --value "$SQL_SERVER_USERNAME"
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "sqlsrvrPassword" --value "$SQL_SERVER_PASSWORD"
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "sqlDwDatabaseName" --value "$SQL_DW_DATABASE_NAME"
# Datalake
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "datalakeAccountName" --value "$AZURE_STORAGE_ACCOUNT"
az pipelines variable-group variable create --group-id "$vargroup_secrets_id" \
    --secret "true" --name "datalakeKey" --value "$AZURE_STORAGE_KEY"

# Delete dummy vars
az pipelines variable-group variable delete --group-id "$vargroup_secrets_id" --name "foo" -y