import os
import logging

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.artifax import ArtifaxRequest


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
    filesystem_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    directory_name = os.environ["DATALAKE_GEN_2_ROOT_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Artifax processor
    entity, filename = ArtifaxRequest(
        keyvault_name, datalake_name, filesystem_name, directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ).process()

    return func.HttpResponse(f"Resp: {entity}, {filename}")


