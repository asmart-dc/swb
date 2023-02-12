import os

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.processor import SpektrixRequest


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Parse request body
    filename = req['filename']

    # Get environment variables
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    directory_name = os.environ["DATALAKE_GEN_2_ROOT_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Artifax processor
    filename = SpektrixRequest(
        keyvault_name, datalake_name, filesystem_raw_name, directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ).process()

    return func.HttpResponse(filename)