import logging

from azure.storage.filedatalake import DataLakeServiceClient


class Datalake:
    def __init__(self, azure_credential, datalake_name, filesystem_name, directory_name):
        self.datalake_name = datalake_name
        self.datalake_uri = f"https://{datalake_name}.dfs.core.windows.net"
        self.client = DataLakeServiceClient(account_url=self.datalake_uri, credential=azure_credential)
        self.filesystem_name = filesystem_name
        self.directory_name = directory_name

    def upload_file_to_directory(self, directory_name, filename, data):
        logging.info(f"Creating new file: {directory_name}/{filename}")
        try:
            file_system_client = self.client.get_file_system_client(file_system=self.filesystem_name)
            directory_client = file_system_client.get_directory_client(directory_name)
            file_client = directory_client.create_file(filename)
            file_client.upload_data(data, overwrite=True, connection_timeout=1000)
        except Exception as e:
            raise

    def download_file_from_directory(self, filename):
        logging.info(f"Downloading file: {filename}")
        try:
            file_system_client = self.client.get_file_system_client(file_system=self.filesystem_name)
            directory_client = file_system_client.get_directory_client(self.directory_name)
            file_client = directory_client.get_file_client(filename)
            streamdownloader = file_client.download_file()
            file_reader = streamdownloader.readall()

            return file_reader
        except Exception as e:
            raise

    def list_directory_contents(self, directory_name):
        try:
            file_system_client = self.client.get_file_system_client(file_system=self.filesystem_name)
            files = file_system_client.get_paths(path=directory_name)

            return files
        except Exception as e:
            raise

    def directory_exists(self, directory_name):
        try:
            file_system_client = self.client.get_file_system_client(file_system=self.filesystem_name)
            directory_client = file_system_client.get_directory_client(directory_name)
            exists = directory_client.exists()

            return exists
        except Exception as e:
            raise

    def delete_file_from_directory(self, directory_name, filename):
        logging.info(f"Deleting file: {filename}")
        try:
            file_system_client = self.client.get_file_system_client(file_system=self.filesystem_name)
            directory_client = file_system_client.get_directory_client(directory_name)
            file_client = directory_client.get_file_client(filename)
            file_client.delete_file()
        except Exception as e:
            raise
