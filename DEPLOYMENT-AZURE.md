# Azure Deployment Guide - Secure Search DB Server

Deploy your secure search database server to Azure Container Instances with just a few simple steps!

## 🚀 Quick Start (5 minutes)

### 1. Set up Azure Resources

```bash
# Clone your repo and run the setup script
git clone your-repo
cd your-repo
chmod +x scripts/setup-azure.sh
./scripts/setup-azure.sh
```

The script will:
- Create a resource group
- Create an Azure Container Registry (ACR)
- Create a service principal for GitHub Actions
- Generate all the secrets you need

### 2. Configure GitHub Secrets

Copy the output from the setup script and add these secrets to your GitHub repository:

**Go to:** Repository → Settings → Secrets and variables → Actions

**Add these secrets:**
- `AZURE_CREDENTIALS` - JSON output from the script
- `ACR_LOGIN_SERVER` - Your ACR login server
- `ACR_USERNAME` - ACR username  
- `ACR_PASSWORD` - ACR password
- `AZURE_RESOURCE_GROUP` - Resource group name
- `POSTGRES_PASSWORD` - Strong database password
- `DB_SERVER_API_KEY` - Strong API key

### 3. Deploy!

```bash
# Push to main branch - deployment happens automatically!
git push origin main
```

That's it! 🎉

## 📡 Access Your Service

After deployment (takes ~3-5 minutes), your service will be available at:
```
http://secure-search-[run-number].eastus.azurecontainer.io:8001
```

### Test the API:
```bash
# Health check
curl http://your-service-url:8001/health

# Initialize a client
curl -X POST http://your-service-url:8001/initialize \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "context_params": {
      "public_key": "dGVzdF9rZXk=",
      "scheme": "CKKS",
      "poly_modulus_degree": 8192,
      "scale": 1099511627776
    },
    "embedding_dim": 384,
    "lsh_config": {
      "num_tables": 20,
      "hash_size": 16,
      "num_candidates": 100
    }
  }'
```

## 🏗️ Architecture

```
Internet → Azure Container Instance (Public IP:8001) → DB Server
        → Azure Container Instance (Private IP:5432) → PostgreSQL
```

### Security Features:
- **PostgreSQL**: Private IP only, not accessible from internet
- **DB Server**: Public IP for API access from your machine
- **TenSEAL**: Real homomorphic encryption running on AMD64
- **API Authentication**: Secure API key-based access

## 💰 Cost

Estimated monthly cost: **~$30-50 USD**
- DB Server container (2 CPU, 4GB RAM): ~$25-35/month
- PostgreSQL container (1 CPU, 2GB RAM): ~$15-20/month  
- Container Registry: ~$5/month
- Bandwidth: ~$1-5/month (depending on usage)

## 🔧 Management

### View logs:
```bash
# Login to Azure CLI
az login

# View DB server logs
az container logs --resource-group secure-search-rg --name secure-search-db-server

# View PostgreSQL logs  
az container logs --resource-group secure-search-rg --name secure-search-postgres
```

### Check status:
```bash
# List containers
az container list --resource-group secure-search-rg --output table

# Get service URL
az container show --resource-group secure-search-rg --name secure-search-db-server --query ipAddress.fqdn --output tsv
```

### Scale resources:
```bash
# Update DB server to more CPU/memory
az container create --resource-group secure-search-rg --name secure-search-db-server \
  --cpu 4 --memory 8 [other-params...] --replace
```

## 🛠️ Troubleshooting

### Common Issues:

1. **"Container failed to start"**
   - Check logs: `az container logs --resource-group secure-search-rg --name secure-search-db-server`
   - Usually environment variable or image issues

2. **"Database connection failed"**
   - PostgreSQL container might be starting up
   - Wait 1-2 minutes and try again

3. **"API key authentication failed"**  
   - Verify `DB_SERVER_API_KEY` secret is set correctly
   - Check you're using the right API key in requests

4. **"Out of memory errors"**
   - TenSEAL needs significant memory
   - Increase container memory in the workflow file

### Debug commands:
```bash
# Get container details
az container show --resource-group secure-search-rg --name secure-search-db-server

# Check container events
az container logs --resource-group secure-search-rg --name secure-search-db-server --follow

# Restart a container
az container restart --resource-group secure-search-rg --name secure-search-db-server
```

## 🔄 Updates

To update your deployment:
1. Make changes to your code
2. Push to main branch
3. GitHub Actions automatically builds and deploys
4. New containers replace old ones with zero downtime

## 🗑️ Cleanup

To delete everything and stop charges:
```bash
az group delete --name secure-search-rg --yes --no-wait
```

## 🚀 Advanced Options

### Custom Domain:
- Set up Azure Front Door or Application Gateway
- Configure SSL certificates
- Use custom domain instead of azurecontainer.io

### Monitoring:
- Enable Azure Monitor for containers
- Set up alerts for health checks  
- Configure log analytics workspace

### Scaling:
- Use Azure Container Apps for auto-scaling
- Set up load balancing for multiple instances
- Configure geo-replication

---

**Need help?** Check the container logs first, then open an issue in the repository!