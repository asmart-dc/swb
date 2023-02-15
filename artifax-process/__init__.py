import os
import logging

from azure.identity import DefaultAzureCredential
import azure.functions as func

from shared.processor import ArtifaxProcessor


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Parse request body
    req_body = req.get_json()
    endpoint = req_body['endpoint']
    raw_filename = req_body['filename']

    # Get environment variables
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_raw_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    filesystem_structured_name = os.environ["DATALAKE_GEN_2_STRUCTURED_CONTAINER_NAME"]
    directory_name = os.environ["DATALAKE_GEN_2_ARTIFAX_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Artifax processor
    entity = ArtifaxProcessor(
        endpoint, raw_filename, datalake_name, filesystem_raw_name,
        filesystem_structured_name, directory_name, azure_credential
    ).process()

    return func.HttpResponse(entity)


