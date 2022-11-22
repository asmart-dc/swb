param project string
param env string
param email_id string
param location string = resourceGroup().location
param deployment_id string
param keyvault_owner_object_id string
@secure()
param sql_server_password string
param enable_monitoring bool

module datafactory './modules/datafactory.bicep' = {
  name: 'datafactory_deploy_${deployment_id}'
  params: {
    project: project
    env: env
    location: location
    deployment_id: deployment_id
  }
}

module datalake './modules/datalake.bicep' = {
  name: 'storage_deploy_${deployment_id}'
  params: {
    project: project
    env: env
    location: location
    deployment_id: deployment_id
    contributor_principal_id: datafactory.outputs.datafactory_principal_id
  }
}

module keyvault './modules/keyvault.bicep' = {
  name: 'keyvault_deploy_${deployment_id}'
  params: {
    project: project
    env: env
    location: location
    deployment_id: deployment_id
    keyvault_owner_object_id: keyvault_owner_object_id
    datafactory_principal_id: datafactory.outputs.datafactory_principal_id
  }
  dependsOn: [
    datafactory
  ]
}