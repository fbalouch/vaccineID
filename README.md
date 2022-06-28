# Vaccine credentials for all! An example of a cloud native microservice built with Angular, Azure, Docker, "Distroless" container images, Flask, Gunicorn, Kubernetes, Nginx, OpenAPI, and Python.

 1. [Overview](#overview)
 2. [Contents](#contents)
 3. [Prerequisites](#prerequisites)
 4. [Setup](#setup)
 5. [Deploy](#deploy)
 6. [Test](#test)

## Overview

VaccineID demonstrates an example application built with Microsoft Identity platform, using Azure Active Directory (AAD) for authentication and authorization, AAD workload identity federation for Kubernetes, Azure Cosmos DB role based access using AAD, and Microsoft Authentication Library (MSAL) for Angular and Python. This project includes an OpenAPI specification, a Python implementation of the API, Kubernetes deployment with "distroless" container images, and a front-end Angular single page application. VaccineID allows healthcare providers to quickly and securely integrate digital immunization credentials for their patients.

![VaccineID](./img/vaccineID.png)

![Topology](./img/vaccineID-topology.png)

## [OpenAPI Spec](https://vaccine-id.balouchtech.com/spec.html)

## Contents

The following files contain configuration parameters required to deploy VaccineID in your environment.

| Directory/file                      | Description                                  |
|-------------------------------------|----------------------------------------------|
| `nginx/spa/src/app/auth-config.ts`  | AAD parameters for Angular SPA client.       |
| `k8s/vaccine-id.yaml`               | AAD and app parameters for Kubernetes app.   |

## Prerequisites

- An active **Azure** subscription with **Azure Active Directory**, **Azure Cosmos DB**, and **Azure CLI**. See [How to get an Azure Active Directory tenant](https://docs.microsoft.com/azure/active-directory/develop/quickstart-create-new-tenant) for details.
- **Docker** for building images. See [Docker](https://www.docker.com/) for details.
- **Kubernetes** cluster with **AAD Workload Identity** federation. See [Kubernetes](https://kubernetes.io/) and [Workload Identity](https://azure.github.io/azure-workload-identity/docs/introduction.html) for details.

## Setup

### Step 1. Create a Cosmos DB Container

1. Navigate to the [Azure portal](https://portal.azure.com) and select **Azure Cosmos DB** service.
2. Create a new Azure Cosmos account, or select an existing account for **Core (SQL)**.
3. Open the **Data Explorer** pane, and select **New Container**. Next, provide the following details:
   - Use `vaccine-id` as the Database id.
   - Use `patients` as the Container id.
   - Use `id` as the Partition key value.
4. Select **OK** to create the Container.

### Step 2. Register AAD application for the K8s app (vaccine-id)

1. Navigate to the [Azure portal](https://portal.azure.com) and select **Azure Active Directory** service.
2. Select **App registrations**.
3. Select **New registration**.
4. In the **Register an application page** that appears, enter your application's registration information:
   - In the **Name** section, enter a meaningful application name that will be displayed to users of the app, for example `vaccine-id`.
   - Under **Supported account types**, select **Accounts in this organizational directory only**.
5. Select **Register** to create the application.
6. In the app's registration screen, find and note the **Application (client) ID** and **Object ID**. You will need these in later steps.
7. Establish federated identity credential between the AAD application and a Kubernetes service account. See [Workload Identity](https://azure.github.io/azure-workload-identity/docs/quick-start.html) for details.
```console
   cat <<EOF > body.json
   {
   "name": "kubernetes-federated-credential",
   "issuer": "<K8S_OIDC_ISSUER_URL>",
   "subject": "system:serviceaccount:vaccine-id:vaccine-id-sa",
   "description": "Kubernetes service account federated credential for vaccine-id-sa service account in vaccine-id namespace.",
   "audiences": [
      "api://AzureADTokenExchange"
   ]
   }
   EOF

   az rest --method POST --uri "https://graph.microsoft.com/beta/applications/<APPLICATION_OBJECT_ID>/federatedIdentityCredentials" --body @body.json
```

### Step 3. Setup Cosmos DB Role based access control

1. Create a custom role definition or use the `Cosmos DB Built-in Data Contributor` role. See [How to Setup RBAC](https://docs.microsoft.com/en-us/azure/cosmos-db/how-to-setup-rbac) for more details. Following data actions are required for the role:
```
    Microsoft.DocumentDB/databaseAccounts/readMetadata
    Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*
    Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*
```
1. Assign role definition to K8s client app (vaccine-id), created in setup step 2. Make sure to use the AAD application **Object ID** as found in the Enterprise applications for principal id.
```console
   resourceGroupName='<ResourceGroup>'
   accountName='<CosmosAccount>'
   RoleDefinitionId = '<roleDefinitionId>'
   principalId = '<aadPrincipalId>'

   az cosmosdb sql role assignment create --account-name $accountName --resource-group $resourceGroupName --scope "/" --principal-id $principalId --role-definition-id $RoleDefinitionId
```

### Step 4. Register AAD application for the API (vaccine-id-api)

1. Navigate to the [Azure portal](https://portal.azure.com) and select **Azure Active Directory** service.
2. Select **App registrations**.
3. Select **New registration**.
3. In the **Register an application page** that appears, enter your application's registration information:
   - In the **Name** section, enter a meaningful application name that will be displayed to users of the app, for example `vaccine-id-api`.
   - Under **Supported account types**, select **Accounts in this organizational directory only**.
4. Select **Register** to create the application.
5. In the app's registration screen, click on **Expose an API** to the left to open the page where you can declare the parameters to expose this app as an API for which client applications can obtain [access tokens](https://docs.microsoft.com/azure/active-directory/develop/access-tokens) for. The first thing that we need to do is to declare a unique [resource](https://docs.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow) URI that the clients will be using to obtain access tokens for this API. To declare a resource URI, follow the following steps:
   - Click `Set` next to the **Application ID URI** to generate a URI that is unique for this app.
   - Accept the proposed Application ID URI (api://{clientId}) by selecting **Save**.
6. All APIs have to publish a minimum of one [scope](https://docs.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow#request-an-authorization-code) for the clients to obtain an access token successfully. To publish a scope, follow steps:
   - Select **Add a scope** button to open the **Add a scope** screen and enter the values as indicated below:
      - For **Scope name**, use `Patients.Admin`.
      - Select **Admins and users** options for **Who can consent?**
      - For **Admin consent display name** type `Access vaccine-id-api`
      - For **Admin consent description** type `Allows the app to access vaccine-id-api as the signed-in user.`
      - For **User consent display name** type `Access vaccine-id-api`
      - For **User consent description** type `Allow the application to access vaccine-id-api on your behalf.`
      - Keep **State** as **Enabled**
      - Click on the **Add scope** button on the bottom to save this scope.
7. On the left side menu, select the **Manifest**.
   - Set `accessTokenAcceptedVersion` property to `2`
8.  Click on **Save**.

### Step 4. Register AAD application for the Angular client app (vaccine-id-spa)

1. Navigate to the [Azure portal](https://portal.azure.com) and select the **Azure Active Directory** service.
2. Select **App registrations**.
3. Select **New registration**.
3. In the **Register an application page** that appears, enter your application's registration information:
   - In the **Name** section, enter a meaningful application name that will be displayed to users of the app, for example `vaccine-id-spa`.
   - Under **Supported account types**, select **Accounts in this organizational directory only**.
   - In the **Redirect URI (optional)** section, select **Single-page application** in the combo-box and enter your apps URI, for example: `https://vaccine-id.example.com:8443/`.
4. Select **Register** to create the application.
5. In the app's registration screen, find and note the **Application (client) ID**. You will need this in step 2 of deploying.
6. In the app's registration screen, click on the **API permissions** in the left to open the page where we add access to the APIs that your application needs.
   - Click **Add a permission** button and then ensure that the **My APIs** tab is selected.
   - In the list of APIs, select the API `vaccine-id-api`.
   - In the **Delegated permissions** section, select the **Patients.Admin** in the list. Use the search box if necessary.
   - Click **Add permissions** button at the bottom.
7. Optionally, click **Grant admin consent for...** to pre-grant users in your directory to use the app. Otherwise this consent will be needed on first login to app.

## Deploy 

### Step 1. Clone or download this repository

```console
    git clone https://github.com/fbalouch/vaccineID.git
```

or download and extract the repository .zip file.

### Step 2. Update Angular SPA client configuration (auth-config.ts), replace following with your details.
```console
   aad_tenant_id
   vaccine_id_api_scope
   vaccine_id_spa_aad_application_client_id
```

### Step 3. Build NGINX image

```console
    cd nginx
    docker build -t vaccine-id-nginx:v1.0 .
```

### Step 4. Build API image

```console
    cd api
    docker build -t vaccine-id-api:v1.0 .
```

### Step 5. Tag and push images to your image repository, accessible by Kubernetes nodes.

### Step 6. Update Kubernetes manifest (vaccine-id.yaml), replace image URLs and following with your details.
```console
   aad_tenant_id
   cosmos_db_name
   cosmos_db_url
   vaccine_id_aad_application_client_id
   vaccine_id_api_aad_application_client_id
```

### Step 7. Deploy to Kubernetes

```console
    cd k8s
    kubectl apply -f vaccine-id.yaml
```

## Test

### Step 1. Create test user with access to app
1. Navigate to the [Azure portal](https://portal.azure.com) and select **Azure Active Directory** service.
1. Select **Users**.
2. Select **New user** and then either **Create new user** or **Invite external user**.
3. Once user is created, navigate back to **Azure Active Directory** service.
4. Select **Enterprise applications** then find and select the AAD application for the API (vaccine-id-api).
5. Select **Properties** on left and then set **Assignment required?** to `Yes`. This will require users be assigned this app in order to get access.
6. Select **Users and groups** then **Add user/group**.
7. Select and add your new or invited user.