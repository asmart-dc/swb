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
var database_sku = 'GP_Gen5_2'
var auto_pause = 60

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

  resource sql_database 'databases@2022-05-01-preview' = {
    name: database_name
    location: location
    tags: {
      Environment: env
    }
    sku: {
      name: database_sku
    }
    properties: {
      collation: database_collation
      autoPauseDelay: auto_pause
    }
  }

  resource firewall_rules 'firewallRules@2022-05-01-preview' = {
    name: 'AllowAllAzureIps'
    properties: {
      endIpAddress: '0.0.0.0'
      startIpAddress: '0.0.0.0'
    }
  }
}

output sql_server_output object = {
  name: sql_server.name
  username: sql_server_username
  database_name: sql_server::sql_database.name
}