#!/bin/bash

# Azure Setup Script for Secure Search Deployment
# Run this to set up Azure resources for the deployment

set -e

echo "🚀 Setting up Azure resources for secure search deployment..."

# Variables
RESOURCE_GROUP="secure-search-rg"
ACR_NAME="securesearchacr$(date +%s)"  # Unique ACR name
LOCATION="eastus"

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

# Create Azure Container Registry
echo "🐳 Creating Azure Container Registry: $ACR_NAME"
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --location $LOCATION

# Enable admin user for ACR (for GitHub Actions)
echo "👤 Enabling ACR admin user..."
az acr update --name $ACR_NAME --admin-enabled true

# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Create service principal for GitHub Actions
echo "🔑 Creating service principal for GitHub Actions..."
SP_NAME="secure-search-github-sp"
SP_JSON=$(az ad sp create-for-rbac --name $SP_NAME --role contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP --sdk-auth)

echo ""
echo "✅ Azure setup completed!"
echo ""
echo "📋 GitHub Secrets to configure:"
echo "================================"
echo "AZURE_CREDENTIALS:"
echo "$SP_JSON"
echo ""
echo "ACR_LOGIN_SERVER: $ACR_LOGIN_SERVER"
echo "ACR_USERNAME: $ACR_USERNAME"
echo "ACR_PASSWORD: $ACR_PASSWORD"
echo "AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo ""
echo "POSTGRES_PASSWORD: $(openssl rand -base64 32)"
echo "DB_SERVER_API_KEY: $(openssl rand -base64 32)"
echo ""
echo "🔗 Add these secrets to your GitHub repository:"
echo "   Repository → Settings → Secrets and variables → Actions"
echo ""
echo "🚀 After adding secrets, push to main branch to deploy!"
echo ""
echo "💰 Estimated monthly cost: ~$30-50 USD"
echo "   - Container Instances: ~$25-40/month"
echo "   - Container Registry: ~$5/month"