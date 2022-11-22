param project string
param env string
param location string = resourceGroup().location
param deployment_id string

param sql_server_username string = 'sqladmin'
@secure()
param sql_server_password string

var server_name = '${project}-sql-${env}-${deployment_id}'
var database_name = 'fidwh'
var database_collation = 'SQL_Latin1_General_CP1_CI_AS'

resource sql_server 'Microsoft.Sql/servers@2022-05-01-preview' = {
  name: server_name
  location: location
  tags: {
    Environment: env
  }
  properties: {
    administratorLogin: sql_server_username
    administratorLoginPassword: sql_server_password
    minimalTlsVersion: '1.2'
  }

    name: '${sql_server.name}/${database_name}'
    location: location
    tags: {
      Environment: env
    }
    sku: {
      name: ''
    }
    properties: {
      collation: database_collation
    }
  }

  resource firewall_rules 'firewallRules@2021-02-01-preview' = { --change
    name: 'AllowAllAzureIps'
    properties: {
      endIpAddress: '0.0.0.0'
      startIpAddress: '0.0.0.0'
    }
  }
}

output synapse_sql_pool_output object = {  --change
  name: sql_server.name
  username: sql_server_username
  synapse_pool_name: sql_server::synapse_dedicated_sql_pool.name
}