param project string
@allowed([
  'dev'
  'stg'
  'prod'
])
param env string
param location string = resourceGroup().location
param deployment_id string

param app_name string = '${project}-fnapp-${env}-${deployment_id}'
param storage_sku_name string = 'Standard_LRS'
@allowed([
  'python'
])
param runtime string = 'python'

var function_app_name = app_name
var hosting_plan_name = app_name
var application_insights_name = app_name
var storage_account_name = '${project}st${env}${deployment_id}fnapp'
var function_worker_runtime = runtime
var linux_fx_version = 'python|3.10'

resource storage_account 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: storage_account_name
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
    isHnsEnabled: false
    accessTier: 'Hot'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    encryption: {
      keySource: 'Microsoft.Storage'
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
        queue: {
          enabled: true
        }
        table: {
          enabled: true
        }
      }
    }
  }
}

resource hosting_plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: hosting_plan_name
  location: location
  sku: {
    name: 'EP1'
    tier: 'ElasticPremium'
    family: 'EP'
  }
  kind: 'elastic'
  properties: {
    maximumElasticWorkerCount: 1
    reserved: true
  }
}

resource function_app 'Microsoft.Web/sites@2022-03-01' = {
  name: function_app_name
  location: location
  tags: {
    Environment: env
  }
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    reserved: true
    httpsOnly: true
    serverFarmId: hosting_plan.id
    siteConfig: {
      linuxFxVersion: linux_fx_version
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage_account_name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage_account.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage_account_name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage_account.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(function_app_name)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: application_insights.properties.InstrumentationKey
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: function_worker_runtime
        }
      ]
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
    }
  }
}

resource application_insights 'Microsoft.Insights/components@2020-02-02' = {
  name: application_insights_name
  location: location
  tags: {
    Environment: env
  }
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
  }
}

output function_app_name string = function_app.name
output function_app_principal_id string = function_app.identity.principalId
