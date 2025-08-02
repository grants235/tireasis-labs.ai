#!/bin/bash

# Azure VM Setup Script for Secure Search Deployment (Bare Metal)
# This replaces container deployment with a cheaper VM approach

set -e

echo "🚀 Setting up Azure VM for bare-metal secure search deployment..."

# Variables
RESOURCE_GROUP="secure-search-vm-rg"
VM_NAME="secure-search-vm"
LOCATION="eastus"
VM_SIZE="Standard_B2s"  # 2 vCPU, 4GB RAM - ~$15/month
ADMIN_USERNAME="azureuser"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install it first:"
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login to Azure (if not already logged in)
echo "🔐 Checking Azure login status..."
az account show &> /dev/null || az login

# Get subscription info
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
echo "📋 Using subscription: $SUBSCRIPTION_ID"

# Create resource group
echo "📁 Creating resource group: $RESOURCE_GROUP"
az group create --name $RESOURCE_GROUP --location $LOCATION

# Generate SSH key pair if it doesn't exist
if [ ! -f ~/.ssh/azure_vm_key ]; then
    echo "🔑 Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_vm_key -N "" -C "azure-vm-key"
fi

# Create Network Security Group and rules
echo "🛡️ Creating Network Security Group..."
az network nsg create \
    --resource-group $RESOURCE_GROUP \
    --name ${VM_NAME}-nsg

# Allow SSH (22)
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name ${VM_NAME}-nsg \
    --name AllowSSH \
    --protocol tcp \
    --priority 1000 \
    --destination-port-range 22 \
    --access allow

# Allow DB Server API (8001)
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name ${VM_NAME}-nsg \
    --name AllowDBServer \
    --protocol tcp \
    --priority 1010 \
    --destination-port-range 8001 \
    --access allow

# Allow PostgreSQL (5432) - only from within VM
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name ${VM_NAME}-nsg \
    --name AllowPostgreSQL \
    --protocol tcp \
    --priority 1020 \
    --destination-port-range 5432 \
    --source-address-prefix 10.0.0.0/24 \
    --access allow

# Create virtual network
echo "🌐 Creating virtual network..."
az network vnet create \
    --resource-group $RESOURCE_GROUP \
    --name ${VM_NAME}-vnet \
    --address-prefix 10.0.0.0/16 \
    --subnet-name ${VM_NAME}-subnet \
    --subnet-prefix 10.0.0.0/24 \
    --network-security-group ${VM_NAME}-nsg

# Create public IP
echo "🌍 Creating public IP..."
az network public-ip create \
    --resource-group $RESOURCE_GROUP \
    --name ${VM_NAME}-ip \
    --dns-name secure-search-vm-$(date +%s)

# Create VM
echo "💻 Creating VM: $VM_NAME ($VM_SIZE)"
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --image Ubuntu2204 \
    --size $VM_SIZE \
    --admin-username $ADMIN_USERNAME \
    --ssh-key-values ~/.ssh/azure_vm_key.pub \
    --vnet-name ${VM_NAME}-vnet \
    --subnet ${VM_NAME}-subnet \
    --public-ip-address ${VM_NAME}-ip \
    --nsg ${VM_NAME}-nsg \
    --storage-sku Standard_LRS

# Get VM info
VM_IP=$(az vm show -d --resource-group $RESOURCE_GROUP --name $VM_NAME --query publicIps --output tsv)
VM_FQDN=$(az network public-ip show --resource-group $RESOURCE_GROUP --name ${VM_NAME}-ip --query dnsSettings.fqdn --output tsv)

# Create service principal for GitHub Actions
echo "🔑 Creating service principal for GitHub Actions..."
SP_NAME="secure-search-vm-github-sp"
SP_JSON=$(az ad sp create-for-rbac --name $SP_NAME --role contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP --sdk-auth)

echo ""
echo "✅ Azure VM setup completed!"
echo ""
echo "🖥️  VM Details:"
echo "================================"
echo "VM Name: $VM_NAME"
echo "Public IP: $VM_IP"
echo "FQDN: $VM_FQDN"
echo "SSH Command: ssh -i ~/.ssh/azure_vm_key $ADMIN_USERNAME@$VM_IP"
echo ""
echo "📋 GitHub Secrets to configure:"
echo "================================"
echo "AZURE_CREDENTIALS:"
echo "$SP_JSON"
echo ""
echo "VM_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "VM_NAME: $VM_NAME"
echo "VM_ADMIN_USERNAME: $ADMIN_USERNAME"
echo "VM_SSH_PRIVATE_KEY:"
echo "$(cat ~/.ssh/azure_vm_key)"
echo ""
echo "POSTGRES_PASSWORD: $(openssl rand -base64 32)"
echo "DB_SERVER_API_KEY: $(openssl rand -base64 32)"
echo ""
echo "🔗 Add these secrets to your GitHub repository:"
echo "   Repository → Settings → Secrets and variables → Actions"
echo ""
echo "🚀 After adding secrets, push to main branch to deploy!"
echo ""
echo "💰 Estimated monthly cost: ~$15 USD (vs $30-50 for containers)"
echo "   - VM (Standard_B2s): ~$15/month"
echo "   - Storage: ~$2/month"
echo "   - Bandwidth: ~$1-5/month"
echo ""
echo "🔧 Next steps:"
echo "1. Add the GitHub secrets above"
echo "2. Push code to trigger deployment"
echo "3. Access your service at: http://$VM_FQDN:8001"