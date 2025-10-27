# Geo-Locator API (FastAPI + Azure AD + Google Maps)

## Overview
A production-ready FastAPI microservice that integrates with **Microsoft Azure Active Directory (Azure AD)** for authentication and **Google Maps API** for geolocation services.  

## Overview
A production-ready FastAPI microservice that integrates with **Microsoft Azure Active Directory (Azure AD)** for authentication and **Google Maps API** for geolocation services.  

## Prerequisites (Filled)

Before you begin, make sure you have the following accounts, tools, and resources configured.

## Google Maps API Setup

1. Visit [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project → enable **Geocoding API**.
3. Create an API key under **APIs & Services → Credentials**.
4. Restrict key usage to IPs or domains (security best practice).
5. Add key to `.env` as:
   ```
   GOOGLE_MAPS_API_KEY=<your_api_key>
   ```


### Accounts & Cloud Resources
- **Azure subscription** — required to create ACR, AKS and Key Vault. Create one at https://portal.azure.com/.
- **Google Cloud project** — enable **Geocoding API** and create an API Key: https://console.cloud.google.com/.


### CLI / Local Tools (install and verify)
- **Docker** (Docker Desktop) — `docker --version`. https://www.docker.com/products/docker-desktop/
- **Docker Buildx** — usually included with Docker Desktop; verify with `docker buildx version`.
- **Azure CLI** — `az --version`. Install: https://learn.microsoft.com/cli/azure/install-azure-cli
- **Git** — `git --version`.
- **Python 3.11+** — for local development, tests, and linting.

### Accounts & Service Principals
- **Azure AD user** with rights to create resources (or ask cloud admin).
- **Service Principal** for CI/CD to push images to ACR.

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
APP_SERVICE_NAME=<your-app-service-name>
```
Same keys we need to update in Azure Key Vault(`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `GOOGLE_MAPS_API_KEY`, `AZURE_EXPOSED_API_AUDIENCE`,)


### Recommended Azure resources to create (high level)
- **Resource Group**
- **Azure Container Registry (ACR)**
- **AKS**
- **Azure Key Vault** for secrets

---

## FastAPI Project Creation

### Folder structure
```
geo-locator/
├── app/
│   ├── main.py
│   ├── services/
│   │   └── geo_services.py
│   ├── config/
│   │   └── config.py
│   ├── auth.py/
│   │   └── azure_auth.py
│   ├── utils/
│   │    ├── cache.py
│   │    └── logger.py
│   ├── tests/
│   ├── test_main.py
│   └── test_auth.py
├── requirements.txt
├── logs/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env
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

## Deploy to Azure Kubernetes Service (AKS)

### Create AKS Cluster and Attach ACR
```bash
az group create --name $RESOURCE_GROUP --location eastus
az aks create --resource-group $RESOURCE_GROUP --name geo-locator-aks --node-count 2 --enable-managed-identity --generate-ssh-keys
az aks update -n geo-locator-aks -g $RESOURCE_GROUP --attach-acr $ACR_NAME
az aks get-credentials --resource-group $RESOURCE_GROUP --name geo-locator-aks
```

### Deploy Secrets using Azure Key Vault
```bash
az keyvault create --name geoLocatorKeyVault --resource-group $RESOURCE_GROUP --location eastus

az keyvault secret set --vault-name geoLocatorKeyVault --name "AZURE-TENANT-ID" --value "<tenant-id>"
az keyvault secret set --vault-name geoLocatorKeyVault --name "AZURE-CLIENT-ID" --value "<client-id>"
az keyvault secret set --vault-name geoLocatorKeyVault --name "GOOGLE-MAPS-API-KEY" --value "<maps-key>"
az keyvault secret set --vault-name geoLocatorKeyVault --name "AZURE-CLIENT-SECRET" --value "<client-secret>"

az aks enable-addons --addons azure-keyvault-secrets-provider --name geo-locator-aks --resource-group $RESOURCE_GROUP

PRINCIPAL_ID=$(az aks show -g $RESOURCE_GROUP -n geo-locator-aks --query identityProfile.kubeletidentity.clientId -o tsv)
az keyvault set-policy -n geoLocatorKeyVault --secret-permissions get --spn $PRINCIPAL_ID
```

---

### Kubernetes Deployment Files

#### `deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: geo-locator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: geo-locator
  template:
    metadata:
      labels:
        app: geo-locator
    spec:
      containers:
        - name: geo-locator
          image: <ACR_NAME>.azurecr.io/geo-locator-api:latest
          ports:
            - containerPort: 8000
          env:
            - name: AZURE_TENANT_ID
              valueFrom:
                secretKeyRef:
                  name: geo-locator-secrets
                  key: AZURE-TENANT-ID
            - name: GOOGLE_MAPS_API_KEY
              valueFrom:
                secretKeyRef:
                  name: geo-locator-secrets
                  key: GOOGLE-MAPS-API-KEY
---
apiVersion: v1
kind: SecretProviderClass
metadata:
  name: azure-keyvault-secrets
spec:
  provider: azure
  parameters:
    keyvaultName: geoLocatorKeyVault
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: <MANAGED_IDENTITY_CLIENT_ID>
    tenantId: <AZURE_TENANT_ID>
    objects: |
      array:
        - |
          objectName: AZURE-TENANT-ID
          objectType: secret
        - |
          objectName: AZURE-CLIENT-ID
          objectType: secret
        - |
          objectName: GOOGLE-MAPS-API-KEY
          objectType: secret
```

#### `service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: geo-locator-service
spec:
  type: LoadBalancer
  selector:
    app: geo-locator
  ports:
    - port: 80
      targetPort: 8000
```

---


## 🧩 Azure DevOps CI/CD Pipeline (ACR → AKS)

### Required Service Connections
- **Docker Registry (ACR)** – for build & push
- **Azure Resource Manager** – to access AKS cluster
- **Kubernetes Service Connection** – for deployment

### Example Azure DevOps pipeline (`azure-pipelines.yml`)
```yaml
trigger:
  branches:
    include:
      - main

variables:
  acrName: '<ACR_NAME>'
  imageName: 'geo-locator-api'

pool:
  vmImage: 'ubuntu-latest'

steps:
- checkout: self

- task: Docker@2
  displayName: Build and Push Docker Image
  inputs:
    command: buildAndPush
    containerRegistry: '<ACR_SERVICE_CONNECTION>'
    repository: '$(acrName)/$(imageName)'
    dockerfile: 'Dockerfile'
    tags: |
      $(Build.BuildId)

- task: KubernetesManifest@1
  displayName: Deploy to AKS
  inputs:
    action: deploy
    kubernetesServiceConnection: '<AKS_SERVICE_CONNECTION>'
    manifests: 'k8s/deployment.yaml'
    containers: |
      $(acrName).azurecr.io/$(imageName):$(Build.BuildId)
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
- Store secrets and environment variables (`AZURE_TENANT_ID`, `ACR_NAME`) securely.
- Link to **Azure Key Vault**.

### Pipelines
- **Build (CI)**: Lint, test, build, and push Docker image to ACR.
- **Release (CD)**: Deploy image to staging.

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

---

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Microsoft Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/)
- [Azure AD Integration Guide](https://learn.microsoft.com/en-us/azure/active-directory/develop/)
- [Azure DevOps Pipelines](https://learn.microsoft.com/en-us/azure/devops/pipelines/)
- [Google Maps API](https://developers.google.com/maps/documentation/geocoding)

---