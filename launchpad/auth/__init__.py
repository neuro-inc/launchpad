HEADER_X_FORWARDED_HOST = "x-forwarded-host"
HEADER_X_FORWARDED_URI = "x-forwarded-uri"

# Keep synchronized with AUTH_RESPONSE_HEADERS in
# .apolo/src/apolo_apps_launchpad/consts.py.
AUTH_RESPONSE_HEADERS = (
    "X-Auth-Request-Email",
    "X-Auth-Request-Preferred-Username",
    "X-Auth-Request-Groups",
    "X-Auth-Request-Roles",
)

(
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
) = AUTH_RESPONSE_HEADERS
