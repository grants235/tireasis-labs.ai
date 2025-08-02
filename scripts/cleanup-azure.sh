#!/bin/bash

# Azure Cleanup Script
# Removes all resources created for the secure search deployment

set -e

RESOURCE_GROUP="secure-search-rg"

echo "🗑️ Cleaning up Azure resources..."
echo "This will delete ALL resources in resource group: $RESOURCE_GROUP"
echo ""
read -p "Are you sure? This cannot be undone! (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Deleting resource group and all resources..."
    az group delete --name $RESOURCE_GROUP --yes --no-wait
    
    echo "✅ Cleanup initiated!"
    echo "Resources are being deleted in the background."
    echo "This may take a few minutes to complete."
    echo ""
    echo "💰 Billing will stop once resources are fully deleted."
else
    echo "❌ Cleanup cancelled."
fi