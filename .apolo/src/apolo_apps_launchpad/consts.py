APP_SECRET_KEYS = {
    "LAUNCHPAD": "launchpad-admin-pswd",
    "KEYCLOAK": "keycloak-admin-pswd",
    "KEYCLOAK_DB": "keycloak-db-pswd",
}

# Keep synchronized with AUTH_RESPONSE_HEADERS in launchpad/auth/__init__.py.
AUTH_RESPONSE_HEADERS = (
    "X-Auth-Request-Email",
    "X-Auth-Request-Preferred-Username",
    "X-Auth-Request-Groups",
    "X-Auth-Request-Roles",
)
