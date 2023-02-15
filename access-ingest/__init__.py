import os
import logging

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.processor import AccessRequest


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Parse request body
    req_body = req.get_json()
    endpoint = req_body['endpoint']
    api_secret = req_body['api_secret']
    client_secret = req_body['client_secret']

    # Get environment variables
    keyvault_name = os.environ["KEY_VAULT_RESOURCE_NAME"]
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    root_directory_name = os.environ["DATALAKE_GEN_2_ACCESS_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Access request
    raw_filename = AccessRequest(
        keyvault_name, datalake_name, filesystem_raw_name, root_directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ).process()

    return func.HttpResponse(raw_filename)
