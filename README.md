# Launchpad

Launchpad is a FastAPI-based application service that manages application deployments and authentication through Keycloak integration. It serves as a platform for launching and managing various applications (vLLM, Postgres, embeddings, OpenWebUI) within the Apolo platform ecosystem.

## Table of Contents

- [API Usage](#api-usage)
  - [Authentication](#authentication)
  - [Managing App Templates](#managing-app-templates)
  - [Managing App Instances](#managing-app-instances)
- [Development](#development)

## API Usage

### Authentication

Before using the API, you need to obtain an access token. Launchpad uses OAuth2 with Keycloak for authentication.

#### Method 1: Using the helper script

```bash
ACCESS_TOKEN=$(./scripts/get-token.sh \
    -u "your-username@example.com" \
    -p "your-password" \
    -l "https://your-launchpad.example.com" | grep -A1 "Access Token:" | tail -n1)
```

#### Method 2: Direct authentication with curl

```bash
LAUNCHPAD_URL="https://your-launchpad.example.com"
USERNAME="your-username@example.com"
PASSWORD="your-password"
SCOPE="openid profile email offline_access"

TOKEN_RESPONSE=$(curl -s -X POST "${LAUNCHPAD_URL}/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\",\"scope\":\"$SCOPE\"}")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.refresh_token')
```

### Managing App Templates

App templates define the configuration and metadata for applications that can be installed.

#### List available app templates

```bash
curl -X GET "${LAUNCHPAD_URL}/api/v1/apps" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" | jq '.'
```

#### Import a template from Apps API

This endpoint fetches a template from the Apolo Apps API and adds it to your Launchpad's template pool.

```bash
curl -X POST "${LAUNCHPAD_URL}/api/v1/apps/templates/import" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
  "template_name": "vscode",
  "template_version": "v25.8.0",
  "name": "vscode-dev",
  "verbose_name": "VS Code Development Environment",
  "description_short": "Cloud-based VS Code IDE",
  "is_internal": false,
  "is_shared": false,
  "default_inputs": {
    "preset": {
      "name": "cpu-medium"
    },
    "vscode_specific": {
      "override_code_storage_mount": null
    },
    "networking": {
      "ingress_http": {
        "auth": {
          "type": "custom_auth",
          "middleware": {
            "type": "app-instance-ref",
            "instance_id": "your-instance-id",
            "path": "$.auth_middleware"
          }
        }
      }
    }
  }
}'
```

**Parameters:**
- `template_name` (required): The template name from Apps API
- `template_version` (required): The template version from Apps API
- `name` (optional): Custom name for the template (defaults to template_name)
- `verbose_name` (optional): User-friendly display name
- `description_short` (optional): Short description
- `description_long` (optional): Long description
- `logo` (optional): URL to the template's logo
- `documentation_urls` (optional): List of documentation URLs
- `external_urls` (optional): List of external URLs
- `tags` (optional): Tags for categorization
- `is_internal` (optional, default: false): Whether template is internal (not visible to end users)
- `is_shared` (optional, default: true): Whether apps from this template can be shared by multiple users
- `default_inputs` (optional): Default inputs to merge with user-provided inputs when installing

### Managing App Instances

#### Install an app from a template

Once a template is in your pool, you can install it:

```bash
curl -X POST "${LAUNCHPAD_URL}/api/v1/apps/openwebui" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" | jq '.'
```

This endpoint is idempotent - calling it multiple times will return the existing installation if it already exists.

#### Install a generic app with custom configuration

For one-off installations without pre-importing a template:

```bash
curl -X POST "${LAUNCHPAD_URL}/api/v1/apps/install" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
  "template_name": "jupyter",
  "template_version": "1.0.0",
  "inputs": {
    "displayName": "My Jupyter Lab",
    "preset": {"name": "gpu-small"}
  },
  "name": "my-jupyter-lab",
  "verbose_name": "My Jupyter Lab",
  "description_short": "Personal Jupyter Lab instance",
  "is_shared": false
}'
```

#### Import an externally installed app

If you have an app that was installed directly through the Apps API, you can link it to Launchpad:

```bash
curl -X POST "${LAUNCHPAD_URL}/api/v1/apps/import" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
  "app_id": "8a5e3b46-02ef-41a8-b6c2-26f2e1a78bb9",
  "name": "custom-app",
  "verbose_name": "Custom App",
  "description_short": "An externally installed app",
  "is_internal": false
}'
```

**Parameters:**
- `app_id` (required): The app ID from Apps API
- All other parameters are optional and follow the same pattern as template import

#### List all installed app instances (Admin only)

```bash
curl -X GET "${LAUNCHPAD_URL}/instances" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" | jq '.'
```

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed development instructions, including:
- Setup and installation
- Code quality tools
- Testing
- Running the application
- Database migrations
- Architecture overview
