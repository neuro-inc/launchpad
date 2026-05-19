# keycloak-procore-idp

`keycloak-procore-idp` is a custom Keycloak 26.x Identity Provider SPI that brokers Procore OAuth2 users into Keycloak. Launchpad keeps trusting only Keycloak, while Keycloak uses Procore strictly as an external Authorization Code authentication source.

The project targets Java 21, Maven, official Keycloak containers, and Keycloak Identity Brokering with the First Broker Login flow.

## Architecture

### Trust boundary

- Launchpad trusts only Keycloak.
- Keycloak remains the only OIDC issuer for Launchpad.
- Procore access tokens stay inside the Keycloak server-side brokering flow.
- Launchpad never receives Procore access or refresh tokens.

### Request flow

1. User opens Launchpad.
2. Launchpad redirects the browser to Keycloak.
3. Keycloak starts identity brokering with `kc_idp_hint=procore` or a normal broker selection flow.
4. `ProcoreIdentityProvider` redirects the user to `https://login.procore.com/oauth/authorize`.
5. Procore returns the browser to `/realms/apolo/broker/procore/endpoint`.
6. Keycloak validates broker state and redirect context through built-in brokering logic in `AbstractOAuth2IdentityProvider`.
7. Keycloak exchanges the authorization code at `https://login.procore.com/oauth/token`.
8. The provider fetches `https://api.procore.com/rest/v1.0/me`.
9. The provider maps Procore data into `BrokeredIdentityContext`.
10. Keycloak runs First Broker Login, links or creates the local user, and issues normal Keycloak OIDC tokens to Launchpad.

### Data mapping

Validated Procore `/me` response fields:

- `id` -> federated identity external id -> `procore_user_id`
- `login` -> username -> email -> `procore_login`
- `name` -> optional display name split into first and last name when present
- constant `procore` -> `identity_source`

### Security choices

- Authorization Code flow only.
- No custom JWT issuance.
- No custom session handling.
- No custom refresh-token persistence.
- HTTPS-only provider endpoint configuration validation.
- Short outbound HTTP timeouts.
- Token and client secret values are never written to logs.
- Token storage is disabled by default in the provider config.

## Project Tree

```text
keycloak-procore-idp/
├── Dockerfile
├── README.md
├── examples
│   ├── helm
│   │   └── values.yaml
│   ├── keycloak
│   │   └── identity-provider-configuration.md
│   └── kubernetes
│       ├── deployment-snippet.yaml
│       └── secret.yaml
├── pom.xml
└── src
    └── main
        ├── java
        │   └── com
        │       └── apolo
        │           └── keycloak
        │               └── procore
        │                   ├── ProcoreHttpClient.java
        │                   ├── ProcoreIdentityProvider.java
        │                   ├── ProcoreIdentityProviderConfig.java
        │                   ├── ProcoreIdentityProviderFactory.java
        │                   ├── ProcoreTokenResponse.java
        │                   └── ProcoreUserProfile.java
        └── resources
            └── META-INF
                └── services
                    └── org.keycloak.broker.provider.IdentityProviderFactory
```

## Source Files

### `ProcoreIdentityProviderFactory`

- Registers provider id `procore`.
- Exposes Keycloak Admin Console config fields.
- Creates `ProcoreIdentityProviderConfig`.
- Instantiates the provider for brokering flows.

### `ProcoreIdentityProvider`

- Extends `AbstractOAuth2IdentityProvider<ProcoreIdentityProviderConfig>`.
- Reuses built-in Keycloak broker callback, state validation, and user linking.
- Calls Procore `/me` after token exchange.
- Builds `BrokeredIdentityContext`.
- Sets user attributes for later protocol mapping.

### `ProcoreIdentityProviderConfig`

- Wraps `OAuth2IdentityProviderConfig`.
- Applies secure defaults.
- Enforces required settings.
- Validates HTTPS endpoint configuration.

### `ProcoreHttpClient`

- Uses Keycloak `SimpleHttp`.
- Applies short connect and read timeouts.
- Supports token exchange and `/me` retrieval logic.
- Parses error payloads without logging secrets.

### `ProcoreTokenResponse`

- Strongly typed parser for Procore token responses.

### `ProcoreUserProfile`

- Strongly typed parser for Procore `/me` responses.

## Build Instructions

### Local Maven build

```bash
mvn -B -DskipTests package
```

Expected artifact:

```text
target/keycloak-procore-idp.jar
```

### Container build

```bash
docker build -t registry.example.com/apolo/keycloak-procore:26.6.1 .
```

The Dockerfile builds the provider jar first, then copies it into the official Keycloak image and runs:

```bash
/opt/keycloak/bin/kc.sh build
```

## Deployment Instructions

### Keycloak container integration

The provider is deployable in the officially supported pattern:

```dockerfile
FROM quay.io/keycloak/keycloak:26.6.1
COPY target/keycloak-procore-idp.jar /opt/keycloak/providers/
RUN /opt/keycloak/bin/kc.sh build
```

### Kubernetes

1. Build and push the custom Keycloak image.
2. Update the Keycloak deployment to use the custom image.
3. Create the Kubernetes Secret from `examples/kubernetes/secret.yaml`.
4. Configure the Procore identity provider in the Keycloak Admin Console using `examples/keycloak/identity-provider-configuration.md`.
5. Add user attribute protocol mappers to the `apolo-launchpad` client.

Example manifests:

- Deployment snippet: [examples/kubernetes/deployment-snippet.yaml](/Users/tymoshv/MyProjects/Apolo/procore/examples/kubernetes/deployment-snippet.yaml)
- Secret: [examples/kubernetes/secret.yaml](/Users/tymoshv/MyProjects/Apolo/procore/examples/kubernetes/secret.yaml)
- Helm values: [examples/helm/values.yaml](/Users/tymoshv/MyProjects/Apolo/procore/examples/helm/values.yaml)

## Example Keycloak Configuration

See:

- [examples/keycloak/identity-provider-configuration.md](/Users/tymoshv/MyProjects/Apolo/procore/examples/keycloak/identity-provider-configuration.md)

That file includes:

- Admin Console setup
- `kc_idp_hint=procore`
- recommended user attribute protocol mappers
- token claim mapping for `procore_user_id` and `identity_source`

## Local Development

1. Install Java 21 and Maven 3.9+.
2. Build the jar with `mvn -B -DskipTests package`.
3. Copy `target/keycloak-procore-idp.jar` into a local Keycloak 26.x container at `/opt/keycloak/providers/`.
4. Run `/opt/keycloak/bin/kc.sh build`.
5. Start Keycloak and configure the `procore` identity provider in realm `apolo`.

Example local container flow:

```bash
docker run --rm -it \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -v "$(pwd)/target/keycloak-procore-idp.jar:/opt/keycloak/providers/keycloak-procore-idp.jar" \
  quay.io/keycloak/keycloak:26.6.1 \
  start-dev
```

Then rebuild the optimized image form when you move from local testing to production.

## End-to-End Flow

1. Launchpad redirects the user to Keycloak authorization.
2. Launchpad optionally sends `kc_idp_hint=procore`.
3. Keycloak starts the Procore broker.
4. Procore authenticates the user and sends `code` back to Keycloak.
5. Keycloak validates broker state and callback context.
6. Keycloak exchanges the code for a Procore access token.
7. `ProcoreIdentityProvider` calls `/rest/v1.0/me`.
8. The provider maps:
   - `id` -> federated user id
   - `login` -> username and email
   - `name` -> first and last name when present
   - `identity_source=procore`
9. Keycloak runs First Broker Login:
   - create new user, or
   - link existing user, or
   - continue account linking flow
10. Keycloak issues OIDC tokens for `apolo-launchpad`.
11. Launchpad receives only Keycloak-issued tokens and builds its session from them.

## Example Logs

The provider logs configuration and profile flow safely:

```text
DEBUG [com.apolo.keycloak.procore.ProcoreIdentityProvider] Initialized Procore identity provider with config {authorizationUrl=https://login.procore.com/oauth/authorize, tokenUrl=https://login.procore.com/oauth/token, meUrl=https://api.procore.com/rest/v1.0/me, clientIdConfigured=true}
DEBUG [com.apolo.keycloak.procore.ProcoreIdentityProvider] Resolved Procore identity for subject=15464862 login=vt781309@gmail.com
WARN  [com.apolo.keycloak.procore.ProcoreHttpClient] Procore profile request failed with status=401 error=invalid_token
```

No log line contains:

- `client_secret`
- `access_token`
- `refresh_token`

## Testing Instructions

### Compile test

```bash
mvn -B -DskipTests package
```

### Functional broker test

1. Configure the `procore` IDP in Keycloak realm `apolo`.
2. Configure First Broker Login flow for the provider.
3. Add `procore_user_id` and `identity_source` user attribute mappers to `apolo-launchpad`.
4. Start Launchpad login with `kc_idp_hint=procore`.
5. Complete Procore authentication.
6. Confirm in Keycloak Admin Console:
   - federated identity is linked
   - local user has `procore_user_id`
   - local user has `procore_login`
   - local user has `identity_source=procore`
7. Decode the Keycloak access token and verify:
   - `email`
   - `preferred_username`
   - `procore_user_id`
   - `identity_source=procore`

## Troubleshooting

### Provider does not show in Admin Console

- Verify the jar exists in `/opt/keycloak/providers/`.
- Verify `META-INF/services/org.keycloak.broker.provider.IdentityProviderFactory` is present in the jar.
- Re-run `/opt/keycloak/bin/kc.sh build`.

### Login redirects to Keycloak but not Procore

- Verify the identity provider alias is `procore`.
- Verify Launchpad sends `kc_idp_hint=procore` only when desired.
- Verify the Procore provider is enabled in realm `apolo`.

### Callback returns an OAuth error

- Verify the Procore application redirect URI exactly matches the Keycloak broker callback:
  - `/realms/apolo/broker/procore/endpoint`
- Verify the external hostname and reverse proxy headers are correct in Keycloak.

### User is authenticated in Procore but not linked in Keycloak

- Verify First Broker Login flow is configured.
- Verify username and email collision handling in realm settings.
- Verify the imported user has the expected brokered attributes.

### Token claims are missing in Launchpad

- The provider only sets Keycloak user attributes.
- Add Keycloak protocol mappers on the `apolo-launchpad` client or its client scope.

## Notes On Keycloak Version

This project is pinned to Keycloak `26.6.1`, which is the latest 26.x API/documentation release visible in official Keycloak documentation and GitHub release metadata as of May 18, 2026.
