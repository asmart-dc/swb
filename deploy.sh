#!/bin/bash
set +o errexit
set -o pipefail
set -o nounset
# set -o xtrace # For debugging

. ./scripts/common.sh
. ./scripts/verify_prerequisites.sh
. ./scripts/init_environment.sh

project="fidwh"

###################
# DEPLOY FOR EACH ENVIRONMENT

for env_name in dev; do   #dev prod
    PROJECT=$project \
    DEPLOYMENT_ID=$DEPLOYMENT_ID \
    ENV_NAME=$env_name \
    AZURE_LOCATION=$AZURE_LOCATION \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    AZURESQL_SERVER_PASSWORD=$AZURESQL_SERVER_PASSWORD \
    bash -c "./scripts/deploy_infra.sh"
done