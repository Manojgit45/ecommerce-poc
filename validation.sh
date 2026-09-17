#!/usr/bin/env bash
set -euo pipefail

# Output header
echo "resourceGroup,vmssName,instanceId,computerName,privateIp,provisioningState,powerState"

# Get all RGs
for RG in $(az group list --query "[].name" -o tsv); do
  # Get VMSS names in this RG
  VMSS_LIST=$(az vmss list -g "$RG" --query "[].name" -o tsv 2>/dev/null || true)

  [ -z "${VMSS_LIST:-}" ] && continue

  for VMSS in $VMSS_LIST; do
    # VM instances JSON
    INSTANCES_JSON=$(az vmss list-instances -g "$RG" -n "$VMSS" -o json)

    # NICs JSON (contains private IP + vm reference)
    NICS_JSON=$(az network nic list -g "$RG" --query "[?contains(id, '/virtualMachineScaleSets/${VMSS}/')]" -o json)

    # Join with jq on VM resource ID
    jq -rn \
      --arg rg "$RG" \
      --arg vmss "$VMSS" \
      --argjson vms "$INSTANCES_JSON" \
      --argjson nics "$NICS_JSON" '
      # Build map: vmId -> privateIp
      ($nics
        | map({
            key: (.virtualMachine.id // "" | ascii_downcase),
            value: (.ipConfigurations[0].privateIPAddress // "")
          })
        | from_entries) as $ipByVm
      |
      $vms[]
      | . as $vm
      | ($vm.id // "" | ascii_downcase) as $vmId
      | [
          $rg,
          $vmss,
          ($vm.instanceId // ""),
          ($vm.osProfile.computerName // ""),
          ($ipByVm[$vmId] // ""),
          ($vm.provisioningState // ""),
          (($vm.instanceView.statuses // [] | map(.displayStatus) | join(" | ")))
        ]
      | @csv
      '
  done
done
