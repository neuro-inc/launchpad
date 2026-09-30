# Static hostname authentication

Launchpad resolves static hostnames through the Apps API's current binding and
applies the installed App's existing sharing and owner permissions. Detached,
inactive, or transferred bindings cannot authorize the previous App.

When a hostname is outside the cluster cookie domain, login starts on Launchpad's
own domain and uses the existing registered Keycloak callback. A nonce-bound,
single-use grant returns the browser to the hostname. Its `__Host-` session cookie
is opaque, Secure, HttpOnly, and host-only; access tokens remain in PostgreSQL.
Grants expire after one minute and sessions expire with their access tokens.
Logout revokes this user's issued alias grants and sessions across this Launchpad,
including sessions created by earlier logins. Expired records are removed when
another alias login starts.

The browser flow for a static hostname outside the cluster cookie domain is:

```mermaid
sequenceDiagram
    actor Browser
    participant Proxy as Traefik (static hostname)
    participant Launchpad
    participant Registry as Apps API
    participant Identity as Keycloak
    participant Database as PostgreSQL
    participant App

    Browser->>Proxy: GET https://static-hostname/
    Proxy->>Launchpad: GET /auth/authorize (forwarded host, URI, cookies)
    Launchpad->>Registry: Resolve and verify active hostname binding
    Registry-->>Launchpad: Current App ID
    Launchpad->>Database: Create pending login bound to App, hostname, and nonce hash
    Launchpad-->>Proxy: Redirect to /auth/static-hostname/start?login=... and set nonce cookie
    Proxy-->>Browser: Forward redirect and host-only nonce cookie

    Browser->>Launchpad: GET /auth/static-hostname/start?login=...
    Launchpad->>Database: Read unexpired pending login
    Launchpad->>Registry: Revalidate hostname binding and App ID
    Launchpad-->>Browser: Redirect to Keycloak using registered /auth/callback
    Browser->>Identity: Authenticate
    Identity-->>Browser: Redirect to Launchpad /auth/callback with authorization code
    Browser->>Launchpad: GET /auth/callback
    Launchpad->>Identity: Exchange code with PKCE
    Identity-->>Launchpad: Access token
    Launchpad-->>Browser: Set cluster token cookie and redirect to /auth/static-hostname/finish?login=...

    Browser->>Launchpad: GET /auth/static-hostname/finish?login=...
    Launchpad->>Database: Read pending login
    Launchpad->>Registry: Revalidate hostname binding and App ID
    Note over Launchpad: Validate token, expiry, and App owner/sharing permissions
    Launchpad->>Database: Store token server-side and hash of single-use grant
    Launchpad-->>Browser: Redirect to static hostname /_apolo/launchpad/{id}/handoff?grant=...

    Browser->>Proxy: GET handoff URL with nonce cookie
    Proxy->>Launchpad: GET /auth/authorize (forwarded callback URI and nonce)
    Launchpad->>Registry: Revalidate active hostname binding
    Launchpad->>Database: Atomically redeem grant using nonce, hostname, and App ID
    Database-->>Launchpad: Redemption succeeds once
    Launchpad-->>Proxy: Set opaque host-only session cookie, clear nonce, and redirect to /
    Proxy-->>Browser: Forward cookies and clean redirect

    Browser->>Proxy: GET / with session cookie
    Proxy->>Launchpad: GET /auth/authorize
    Launchpad->>Registry: Revalidate active hostname binding
    Launchpad->>Database: Retrieve token by session hash, hostname, and App ID
    Note over Launchpad: Validate token and App permissions
    Launchpad-->>Proxy: 200 with user identity headers
    Proxy->>App: Forward authorized request and identity headers
    App-->>Browser: App response through Traefik
```

Static binding resolution uses two requests: resolve the instance by hostname,
then verify its exact active static-hostname binding. Locally registered hosts
also require a hostname-configuration lookup to distinguish static aliases from
ordinary App URLs. A 404 from that configuration view means static hostnames are
unconfigured; other failures deny authorization with 503. Cookie-domain coverage
determines token transport and does not control binding validation.

Hostnames are normalized consistently across registry, OAuth, local App, and
session lookups: case and trailing DNS dots are normalized, and the default HTTPS
port is omitted. Non-default ports remain part of App URLs and session bindings.
Noncanonical browser origins redirect to the canonical origin before any nonce
cookie is set, preserving the request path and query. This keeps host-only cookies
on the same origin used by the handoff callback.
Pending logins and their nonce cookies share a five-minute lifetime; grants expire
after at most one minute. PostgreSQL stores hashes of
login, nonce, grant, and session values, plus the server-side access token. Only the
opaque session cookie is sent to the static hostname after login.

Missing or inactive bindings, App changes during login, invalid permissions, and
invalid or replayed grants deny access with 403. Apps API lookup failures return
503. Normal requests recheck the current binding, so a session for the previous
App cannot authorize a hostname after it moves. Launchpad logout deletes the
user's issued grants and sessions; an existing alias cookie then has no valid
server-side session.

For deployment requirements and regression checks, see the [operations guide](../operations/static-hostname-authentication.md).

## Implementation boundaries

- [Static hostname HTTP routes](../../launchpad/auth/static_hostname_api.py) own the
  start and finish endpoints, handoff handling, redirects, and host-only cookies.
- [Static hostname authentication service](../../launchpad/auth/static_hostname.py)
  owns persisted login, grant, session, and revocation operations.
- [Shared authentication dependencies](../../launchpad/auth/dependencies.py) own
  App resolution, permission checks, and token decoding.
- [General authentication routes](../../launchpad/auth/api.py) orchestrate
  authorization and retain the token, callback, and logout endpoints.

The [root router](../../launchpad/api.py) includes both authentication routers under
`/auth`, preserving the public endpoint paths.
