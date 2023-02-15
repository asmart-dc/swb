import os

from azure.identity import DefaultAzureCredential

from shared.processor import ArtifaxRequest


def main(req: dict) -> list:

    # Parse request body
    endpoint = req['endpoint']
    api_secret = req['api_secret']
    client_secret = req['client_secret']

    # Get environment variables
    keyvault_name = os.environ["KEY_VAULT_RESOURCE_NAME"]
    datalake_name = os.environ["DATALAKE_GEN_2_RESOURCE_NAME"]
    filesystem_name = os.environ["DATALAKE_GEN_2_RAW_CONTAINER_NAME"]
    root_directory_name = os.environ["DATALAKE_GEN_2_ARTIFAX_DIRECTORY_NAME"]

    # Get authentication credential
    azure_credential = DefaultAzureCredential()

    # Run Artifax request
    artifax_file = ArtifaxRequest(
        keyvault_name, datalake_name, filesystem_name, root_directory_name,
        endpoint, api_secret, client_secret, azure_credential
    ).process()

    return artifax_file
