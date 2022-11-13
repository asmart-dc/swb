#!/bin/bash

# initialise optional variables.

DEPLOYMENT_ID=${DEPLOYMENT_ID:-}
if [ -z "$DEPLOYMENT_ID" ]
then
    export DEPLOYMENT_ID="$(random_str 5)"
    echo "No deployment id [DEPLOYMENT_ID] specified, defaulting to $DEPLOYMENT_ID"
fi

AZURE_LOCATION=${AZURE_LOCATION:-}
if [ -z "$AZURE_LOCATION" ]
then
    export AZURE_LOCATION="ukwest"
    echo "No resource group location [AZURE_LOCATION] specified, defaulting to $AZURE_LOCATION"
fi

AZURE_SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID:-}
if [ -z "$AZURE_SUBSCRIPTION_ID" ]
then
    export AZURE_SUBSCRIPTION_ID=$(az account show --output json | jq -r '.id')
    echo "No Azure subscription id [AZURE_SUBSCRIPTION_ID] specified. Using default subscription id."
fi

AZURESQL_SERVER_PASSWORD=${AZURESQL_SERVER_PASSWORD:-}
if [ -z "$AZURESQL_SERVER_PASSWORD" ]
then
    export AZURESQL_SERVER_PASSWORD="$(openssl rand -base64 16)"
    # export AZURESQL_SERVER_PASSWORD="$(makepasswd --chars 16)"
fi