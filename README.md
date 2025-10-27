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
├── tests/
│   ├── test_main.py
│   └── test_auth.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env
├── LICENSE
└── README.md
```

### Install dependencies (local)
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt    # download dependencies
```


## Running Tests

Unit tests use **pytest** and **httpx.AsyncClient**.

Run all tests:
```bash
pytest -v --disable-warnings
```

### Local Testing (Bypass Azure AD Authentication)

During **local testing**, you may disable Azure AD token validation temporarily in `main.py` to test API responses without real tokens.

Example:
```python
# For production (with Azure AD)
@limiter.limit(RATE_LIMIT)
async def my_location(request: Request, user=Depends(azure_auth_dependency)):
    return JSONResponse(content=latest_location)

# For local testing (without Azure AD)
@limiter.limit(RATE_LIMIT)
async def my_location(request: Request):  # Auth disabled for local testing
    return JSONResponse(content=latest_location)
```

**Important:** This should only be used in local or development environments.  
Do **not** commit or deploy with authentication removed.

---


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

## 🚀 Deploy to Azure App Service (Web App for Containers)

### 1) Create App Service Plan (Linux) & Web App
```bash
# create App Service plan (Linux)
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --is-linux --sku S1

# create web app for containers
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $APP_SERVICE_NAME --deployment-container-image-name ${ACR_NAME}.azurecr.io/geo-locator-api:1.0.0
```

### 2) Configure ACR access
Grant the web app access to ACR via a managed identity or service principal. Simplest approach for quick setup (not recommended for prod long-term) — enable admin user on ACR and set credentials in App Settings.

Better approach: use a managed identity and grant `AcrPull` role.

Example (managed identity approach):
```bash
# assign managed identity to web app
az webapp identity assign -g $RESOURCE_GROUP -n $APP_SERVICE_NAME

# get principal id
PRINCIPAL_ID=$(az webapp show -g $RESOURCE_GROUP -n $APP_SERVICE_NAME --query identity.principalId -o tsv)

# assign AcrPull role to the managed identity
az role assignment create --assignee $PRINCIPAL_ID --role AcrPull --scope $(az acr show -n $ACR_NAME -g $RESOURCE_GROUP --query id -o tsv)
```

### 3) Configure App Settings (environment vars & Key Vault references)
Set environment variables (from `.env`) in App Settings:
```bash
az webapp config appsettings set -g $RESOURCE_GROUP -n $APP_SERVICE_NAME --settings   AZURE_TENANT_ID=$AZURE_TENANT_ID   AZURE_CLIENT_ID=$AZURE_CLIENT_ID   AZURE_EXPOSED_API_AUDIENCE=$AZURE_EXPOSED_API_AUDIENCE   GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
```

For secrets, use Key Vault integration or reference Key Vault secrets in App Service.

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

## 🧩 Azure DevOps CI/CD Pipeline (App Service)

### Service connections required
- **Azure Resource Manager** (for deploying to App Service)
- **Docker Registry (ACR)** (for build & push permissions)

### Example Azure DevOps pipeline (`azure-pipelines.yml`)
```yaml
trigger:
  branches:
    include:
      - main

variables:
  imageName: 'geo-locator-api'
  acrName: '<ACR_NAME>'

pool:
  vmImage: 'ubuntu-latest'

steps:
- checkout: self

# Build and push image to ACR
- task: Docker@2
  displayName: Build and push image
  inputs:
    command: buildAndPush
    containerRegistry: '<ACR_SERVICE_CONNECTION>'
    repository: '$(acrName)/$(imageName)'
    dockerfile: 'Dockerfile'
    tags: |
      $(Build.BuildId)

# Deploy to staging slot (green)
- task: AzureWebApp@1
  displayName: Deploy to staging slot
  inputs:
    azureSubscription: '<AZURE_SERVICE_CONNECTION>'
    appName: '<APP_SERVICE_NAME>'
    deployToSlotOrASE: true
    resourceGroupName: '<RESOURCE_GROUP>'
    slotName: 'staging'
    imageName: '$(acrName).azurecr.io/$(imageName):$(Build.BuildId)'

# Optional: Manual approval gate before swapping to production

# Swap staging to production
- task: AzureCLI@2
  displayName: Swap slots to production
  inputs:
    azureSubscription: '<AZURE_SERVICE_CONNECTION>'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      az webapp deployment slot swap -g <RESOURCE_GROUP> -n <APP_SERVICE_NAME> --slot staging --target-slot production
```
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