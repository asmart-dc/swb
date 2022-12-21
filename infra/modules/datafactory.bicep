param project string
@allowed([
  'dev'
  'stg'
  'prod'
])
param env string
param location string = resourceGroup().location
param deployment_id string
param adf_name string = '${project}-adf-${env}-${deployment_id}'
// repository params
param account_name string = 'factoryintl'
param devops_project string = 'Factory Intl Data Warehouse'
param repository_name string = 'factoryintl-dwh'
param collaboration_branch string = 'master'
param root_folder string = '/adf'

var azDevopsRepoConfiguration  = {
  accountName: account_name
  projectName: devops_project
  repositoryName: repository_name
  collaborationBranch: collaboration_branch
  rootFolder: root_folder
  type: 'FactoryVSTSConfiguration'
}

resource datafactory 'Microsoft.DataFactory/factories@2018-06-01' =  {
  name: adf_name
  location: location
   tags: {
     Environment: env
  }
  properties: {
    repoConfiguration: (env == 'dev') ? azDevopsRepoConfiguration : {}
  }
  identity: {
    type: 'SystemAssigned'
  }
}

output datafactory_principal_id string = datafactory.identity.principalId
output datafactory_name string = datafactory.name
