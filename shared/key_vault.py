from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError


class KeyVault:
    def __init__(self, azure_credential, kv_name):
        self.key_vault_name = kv_name
        self.key_vault_uri = f"https://{self.key_vault_name}.vault.azure.net"
        self.client = SecretClient(vault_url=self.key_vault_uri, credential=azure_credential)

    def get_key_vault_secret(self, secret_name):
        try:
            kv_secret = self.client.get_secret(secret_name)
            return kv_secret.value
        except ResourceNotFoundError as e:
            print(e.message)
