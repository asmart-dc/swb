import os
import logging

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.processor import SpektrixRequest


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Parse request body
    req_body = req.get_json()
    landing_filename = req_body['filename']

    # Get environment variables
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_landing_name = os.environ["DATALAKE_GEN_2_LANDING_CONTAINER_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    root_directory_name = os.environ["DATALAKE_GEN_2_SPEKTRIX_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Spektrix request
    raw_filename = SpektrixRequest(
        landing_filename, datalake_name, filesystem_landing_name,
        filesystem_raw_name, root_directory_name, azure_credential
    ).process()

    return func.HttpResponse(raw_filename)
