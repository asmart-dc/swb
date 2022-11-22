param project string
@allowed([
  'dev'
  'stg'
  'prod'
])
param env string
param location string = resourceGroup().location
param deployment_id string
param contributor_principal_id string
param storage_sku_name string = 'Standard_LRS'

var storage_blob_data_contributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')

resource datalake 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: '${project}st${env}${deployment_id}'
  location: location
  tags: {
    Environment: env
  }
  sku: {
    name: storage_sku_name
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    isHnsEnabled: true
    accessTier: 'Hot'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    encryption: {
      keySource: 'Microsoft.Storage'
      services: {
        file: {
          enabled: true
        }
        blob: {
          enabled: true
        }
      }
    }
  }
}

resource datalake_roleassignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(datalake.id)
  scope: datalake
  properties: {
    roleDefinitionId: storage_blob_data_contributor
    principalId: contributor_principal_id
    principalType: 'ServicePrincipal'
  }
}

output storage_account_name string = datalake.name