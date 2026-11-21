APP_SECRET_KEYS = {
    "FRONTEND": "launchpad-frontend-session",
    "LAUNCHPAD": "launchpad-admin-pswd",
    "KEYCLOAK": "keycloak-admin-pswd",
    "KEYCLOAK_DB": "keycloak-db-pswd",
    "KEYCLOAK_ISOLATED_DB": "keycloak-isolated-db-pswd",
    "LAUNCHPAD_ISOLATED_DB": "launchpad-isolated-db-pswd",
}

# Keep synchronized with AUTH_RESPONSE_HEADERS in launchpad/auth/__init__.py.
AUTH_RESPONSE_HEADERS = (
    "X-Auth-Request-Email",
    "X-Auth-Request-Preferred-Username",
    "X-Auth-Request-Groups",
    "X-Auth-Request-Roles",
)
