#!/bin/bash

set +o errexit
set -o pipefail
set -o nounset
# set -o xtrace # For debugging

. ./scripts/common.sh
. ./scripts/verify_prerequisites.sh
. ./scripts/init_environment.sh

project="fidwh" # CONSTANT - this is prefixed to all deployed resources


###################
# DEPLOY FOR EACH ENVIRONMENT

for env_name in prod; do   #dev prod
    PROJECT=$project \
    DEPLOYMENT_ID=$DEPLOYMENT_ID \
    ENV_NAME=$env_name \
    AZURE_LOCATION=$AZURE_LOCATION \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    AZURESQL_SERVER_PASSWORD=$AZURESQL_SERVER_PASSWORD \
    bash -c "./scripts/deploy_infra.sh"
done

###################
# Deploy AzDevOps Pipelines

# azure-pipelines-cd-release.yml pipeline require DEV_DATAFACTORY_NAME set, retrieve this value from .env.dev file
declare DEV_"$(grep -e '^DATAFACTORY_NAME' .env.dev | tail -1 | xargs)"

# Deploy all pipelines
PROJECT=$project \
AZDO_REPO=$AZDO_REPO \
AZDO_PIPELINES_BRANCH_NAME=$AZDO_PIPELINES_BRANCH_NAME \
DEV_DATAFACTORY_NAME=$DEV_DATAFACTORY_NAME \
    bash -c "./scripts/deploy_azdo_pipelines.sh"

####
print_style "DEPLOYMENT SUCCESSFUL
Details of the deployment can be found in local .env.* files.\n\n" "success"
