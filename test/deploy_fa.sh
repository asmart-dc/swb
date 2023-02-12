PROJECT="fidwh"
ENV_NAME="dev"
DEPLOYMENT_ID="ltmli"
resource_group_name="fidwh-ltmli-dev-rg"

# Validate arm template
echo "Validating deployment"
az deployment group create \
  --resource-group "$resource_group_name" \
  --template-file "./infra/modules/function_app.bicep" \
  --parameters project="${PROJECT}" deployment_id="${DEPLOYMENT_ID}" env="${ENV_NAME}" \
  --output json

