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

module function_app './modules/function_app.bicep' = {
  name: 'function_app_deploy_${deployment_id}'
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
    function_app_principal_id: function_app.outputs.function_app_principal_id
  }
}

module sql_server './modules/sql_server.bicep' = {
  name: 'sql_server_deploy_${deployment_id}'
  params: {
    project: project
    env: env
    location: location
    deployment_id: deployment_id
    sql_server_password: sql_server_password
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
    function_app_principal_id: function_app.outputs.function_app_principal_id
  }
  dependsOn: [
    datafactory
  ]
}

output storage_account_name string = datalake.outputs.storage_account_name
output sql_server_output object = sql_server.outputs.sql_server_output
output keyvault_name string = keyvault.outputs.keyvault_name
output keyvault_resource_id string = keyvault.outputs.keyvault_resource_id
output datafactory_name string = datafactory.outputs.datafactory_name
output function_app_name string = function_app.outputs.function_app_name