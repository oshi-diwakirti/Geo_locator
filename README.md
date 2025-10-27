# Geo-Locator API (FastAPI + Azure AD + Google Maps)

## Overview
A production-ready FastAPI microservice that integrates with **Microsoft Azure Active Directory (Azure AD)** for authentication and **Google Maps API** for geolocation services.  

## Overview
A production-ready FastAPI microservice that integrates with **Microsoft Azure Active Directory (Azure AD)** for authentication and **Google Maps API** for geolocation services.  

## Prerequisites (Filled)

Before you begin, make sure you have the following accounts, tools, and resources configured.

## Google Maps API Setup

1. Visit [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project → enable **Geocoding API** and **Maps JavaScript API**.
3. Create an API key under **APIs & Services → Credentials**.
4. Restrict key usage to IPs or domains (security best practice).
5. Add key to `.env` as:
   ```
   GOOGLE_MAPS_API_KEY=<your_api_key>
   ```

### Accounts & Cloud Resources
- **Azure subscription** — required to create ACR, App Service, Key Vault, and Application Insights. Create one at https://portal.azure.com/.
- **Google Cloud project** — enable **Geocoding API** and create an API Key: https://console.cloud.google.com/.

### CLI / Local Tools (install and verify)
- **Docker** (Docker Desktop) — `docker --version`. https://www.docker.com/products/docker-desktop/
- **Docker Buildx** — usually included with Docker Desktop; verify with `docker buildx version`.
- **Azure CLI** — `az --version`. Install: https://learn.microsoft.com/cli/azure/install-azure-cli
- **Git** — `git --version`.
- **Python 3.11+** — for local development, tests, and linting.

### Accounts & Service Principals
- **Azure AD user** with rights to create resources (or ask cloud admin).
- **Service Principal** for CI/CD to push images to ACR and manage App Service deployments.

Example: create a service principal with ACR push permission (replace placeholders):
```bash
az login
az group create -n myResourceGroup -l eastus
az acr create -n myRegistryName -g myResourceGroup --sku Standard
az ad sp create-for-rbac --name sp-geolocator --role acrpush --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/myResourceGroup/providers/Microsoft.ContainerRegistry/registries/myRegistryName
```

### Local environment (development)
Create a `.env` file in the project root with:
```
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_EXPOSED_API_AUDIENCE=<your-api-audience>
GOOGLE_MAPS_API_KEY=<your-google-api-key>
ACR_NAME=<your-acr-name>
RESOURCE_GROUP=<your-resource-group>
APP_SERVICE_PLAN=<your-app-service-plan>
APP_SERVICE_NAME=<your-app-service-name>
```

### Recommended Azure resources to create (high level)
- **Resource Group**
- **Azure Container Registry (ACR)**
- **App Service Plan** (Linux) and **Web App for Containers**
- **Azure Key Vault** for secrets
- **Application Insights / Log Analytics Workspace** for monitoring

---

## FastAPI Project Creation

### Folder structure
```
geo-locator/
├── app/
│   ├── main.py
│   ├── services.py
│   ├── auth.py
│   └── utils/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── LICENSE
├── README.md
└── run.py

```

### Install dependencies (local)
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt    # download dependencies
```

## Dockerization (Production Image Build)

1. Create a production-ready `Dockerfile` with FastAPI and Uvicorn.
2. Add `.dockerignore` for excluding unnecessary files.

### Build image
```bash
docker build -t geo-locator:1.0.0 .
```

### Test container locally
```bash
docker run -d -p 8000:8000 --env-file .env --name geo-locator geo-locator:1.0.0
# check logs
docker logs -f geo-locator
```

---

## Push to Azure Container Registry (ACR)

### Create resource group and ACR (example)
```bash
az login
az group create -n $RESOURCE_GROUP -l eastus
az acr create -n $ACR_NAME -g $RESOURCE_GROUP --sku Standard --admin-enabled false
az acr login --name $ACR_NAME
```

### Tag & push
```bash
docker tag geo-locator:1.0.0 ${ACR_NAME}.azurecr.io/geo-locator:1.0.0
docker push ${ACR_NAME}.azurecr.io/geo-locator:1.0.0
```

---


## Azure App Service — Container Deployment

1. Create App Service Plan:
   ```bash
   az appservice plan create -n geo-plan -g <RESOURCE_GROUP> --is-linux --sku B1
   ```
2. Create App Service (Docker-based):
   ```bash
   az webapp create -g <RESOURCE_GROUP> -p geo-plan -n geo-locator      --deployment-container-image-name <ACR_NAME>.azurecr.io/geo-locator:latest
   ```
3. Configure ACR authentication:
   ```bash
   az webapp config container set -n geo-locator -g <RESOURCE_GROUP>      --docker-custom-image-name <ACR_NAME>.azurecr.io/geo-locator:latest      --docker-registry-server-url https://<ACR_NAME>.azurecr.io
   ```
4. Set environment variables securely via Key Vault or App Settings.

---

## Blue-Green Deployment (Slot-Based)

1. Create a **staging slot** for zero-downtime deployment:
   ```bash
   az webapp deployment slot create -g <RESOURCE_GROUP> -n geo-locator --slot staging
   ```
2. Deploy the new container image to the `staging` slot:
   ```bash
   az webapp config container set -g <RESOURCE_GROUP> -n geo-locator --slot staging      --docker-custom-image-name <ACR_NAME>.azurecr.io/geo-locator:<tag>
   ```
3. Run health checks and validation on staging slot.
4. Perform **slot swap** after approval:
   ```bash
   az webapp deployment slot swap -g <RESOURCE_GROUP> -n geo-locator      --slot staging --target-slot production
   ```
5. Rollback by swapping back to the previous slot if issues occur.

---

## Monitoring & Observability

1. Enable **Application Insights** for App Service:
   ```bash
   az monitor app-insights component create --app geo-locator-insights --location eastus -g <RESOURCE_GROUP>
   az webapp config appsettings set -g <RESOURCE_GROUP> -n geo-locator      --settings APPINSIGHTS_INSTRUMENTATIONKEY=<INSIGHTS_KEY>
   ```
2. Configure Azure Monitor for alerts on metrics like:
   - High error rates (5xx)
   - High response time
   - CPU/memory thresholds
3. Integrate with Teams, PagerDuty, or email using **Action Groups**.

---

## Azure DevOps Project Setup

### Project & Repo
1. Create a new **Azure DevOps project**.
2. Create or import Git repository and push your source code.

### Service Connections
1. Create **Azure Resource Manager** service connection (App Service access).  
2. Create **Docker Registry** service connection (for ACR).

### Variable Groups
- Store secrets and environment variables (`AZURE_CLIENT_SECRET`, `GOOGLE_MAPS_API_KEY`) securely.
- Optionally link to **Azure Key Vault**.

### Pipelines
- **Build (CI)**: Lint, test, build, and push Docker image to ACR.
- **Release (CD)**: Deploy image to staging slot → run smoke tests → approve → swap slots.

### Approvals & Policies
- Add manual approval for production in **Environments**.
- Protect `main` branch with PR validation and build checks.

### Documentation
- Maintain **README.md** and detailed runbooks in **Project Wiki**.
- Include deployment, rollback, and monitoring steps.

---

## Summary of Production Workflow
1. Developer merges PR → CI builds & pushes new image to ACR.
2. CD pipeline deploys to **staging slot** → health checks run.
3. Approval required → swap staging to production.
4. Monitoring alerts team on issues → rollback if needed.

---

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Microsoft Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/)
- [Azure AD Integration Guide](https://learn.microsoft.com/en-us/azure/active-directory/develop/)
- [Azure DevOps Pipelines](https://learn.microsoft.com/en-us/azure/devops/pipelines/)
- [Google Maps API](https://developers.google.com/maps/documentation/geocoding)

---