import os
import logging

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.processor import SpektrixProcessor


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Parse request body
    req_body = req.get_json()
    raw_filepath = req_body['filename']

    # Get environment variables
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    filesystem_structured_name = os.environ["DATALAKE_GEN_2_STRUCTURED_CONTAINER_NAME"]
    root_directory_name = os.environ["DATALAKE_GEN_2_SPEKTRIX_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Artifax processor
    filename = SpektrixProcessor(
        raw_filepath, datalake_name, filesystem_raw_name,
        filesystem_structured_name, root_directory_name, azure_credential
    ).process()

    return func.HttpResponse(filename)
