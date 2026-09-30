# Static hostname authentication: deployment and validation

Deployment requires database migration `0007`, applied by the existing startup
migration runner, and the Apps API static-hostname configuration and binding views.
Use a stable Launchpad instance ID across replicas. No broader cookie domain or
additional Keycloak callback registration is required. The handoff uses non-2xx
responses returned by [Traefik ForwardAuth](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/forwardauth/).

Run the regression checks with PostgreSQL through the existing Docker fixtures:

```bash
poetry run pytest tests/unit/test_hostnames.py tests/unit/test_auth_static_hostname.py tests/unit/test_auth_authorize_headers.py tests/unit/test_apps_api_client.py tests/unit/test_apps_service.py
poetry run pytest tests/integration/test_auth_alias_sessions.py tests/integration/test_auth_set_cookie.py
```

These checks cover the cross-domain cookie flow with a mocked Keycloak exchange,
grant replay and expiry, App binding changes, logout, and migration rollback.
After deploying, verify browser login, logout, and a hostname move through the
actual Traefik and Keycloak installation.

For the authentication flow and session rules, see the [architecture guide](../architecture/static-hostname-authentication.md).
