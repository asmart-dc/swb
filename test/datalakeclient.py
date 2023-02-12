import os

from azure.identity import DefaultAzureCredential

from shared.datalake import Datalake

datalake_name = "fidwhstdevltmli"
filesystem_structured_name = "structured"
directory_name = "provider/artifax"
endpoint = 'arrangements/room'
filename = 'room'
import_date = '2023/02/11'
dir_path = f"{directory_name}/{endpoint}/{filename}/{import_date}"

# Get authentication credential
azure_credential = DefaultAzureCredential()

datalake = Datalake(
    azure_credential, datalake_name, filesystem_structured_name, directory_name
)

if datalake.directory_exists(dir_path):
    files = datalake.list_directory_contents(dir_path)
    for file in files:
        filename = file.name.split('/')[-1]
        datalake.delete_file_from_directory(dir_path, filename)

