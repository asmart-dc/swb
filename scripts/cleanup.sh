#!/bin/bash

set +o errexit
set +o pipefail
set -o nounset
# set -o xtrace # For debugging

###################
# PARAMETERS
#
# RESOURCE_GROUP_NAME_PREFIX
prefix="fidwh"

echo "!! WARNING: !!"
echo "THIS SCRIPT WILL DELETE ALL RESOURCES PREFIXED WITH $prefix"

if [[ -n $prefix ]]; then

    printf "\nSERVICE PRINCIPALS:\n"
    az ad sp list --query "[?contains(appDisplayName,'$prefix')].displayName" -o tsv --show-mine

    printf "\nRESOURCE GROUPS:\n"
    az group list --query "[?contains(name,'$prefix') && ! contains(name,'dbw')].name" --output tsv

    printf "\nEND OF SUMMARY\n"

    read -r -p "Do you wish to DELETE above resources? [y/N]" response
    case "$response" in
        [yY][eE][sS]|[yY])
            echo "Deleting resource groups that start with '$prefix' in the name..."
            [[ -n $prefix ]] &&
                az group list --query "[?contains(name,'$prefix') && ! contains(name,'dbw')].name" -o tsv |
                xargs -I % az group delete --verbose --name % -y
            ;;
        *)
            exit
            ;;
    esac
fi