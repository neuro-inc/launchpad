#!/bin/sh
set -eu

if [ "${1:-}" = postgres ]; then
    # The official entrypoint skips init scripts once PG_VERSION exists.
    if [ -s "$PGDATA/PG_VERSION" ] && [ ! -f "$PGDATA/.launchpad-initialized" ]; then
        pg_ctl -D "$PGDATA" -o "-c listen_addresses=''" -w start
        trap 'pg_ctl -D "$PGDATA" -m fast -w stop' EXIT
        "$0"
        pg_ctl -D "$PGDATA" -m fast -w stop
        trap - EXIT
    fi
    # The entrypoint requires a bootstrap password, which init clears before TCP starts.
    export POSTGRES_PASSWORD="$(head -c 32 /dev/urandom | base64)"
    exec docker-entrypoint.sh "$@"
fi

for app in keycloak launchpad; do
    case "$app" in
        launchpad) password=${LAUNCHPAD_DB_PASSWORD:?Set LAUNCHPAD_DB_PASSWORD} ;;
        keycloak) password=${KEYCLOAK_DB_PASSWORD:?Set KEYCLOAK_DB_PASSWORD} ;;
    esac

    if [ "${1:-}" = ready ]; then
        PGPASSWORD="$password" psql -Xw -h 127.0.0.1 -U "$app" -d "$app" -Atqc 'SELECT 1'
        continue
    fi

    DB_APP="$app" DB_PASSWORD="$password" psql -Xw --host /var/run/postgresql --username postgres --dbname postgres --set ON_ERROR_STOP=1 --file - <<'SQL'
\getenv app_role DB_APP
\getenv app_password DB_PASSWORD
SELECT format('CREATE ROLE %I', :'app_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role') \gexec
ALTER ROLE :"app_role" LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD :'app_password';
SELECT format('CREATE DATABASE %I OWNER %I', :'app_role', :'app_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'app_role') \gexec
ALTER DATABASE :"app_role" OWNER TO :"app_role";
REVOKE ALL PRIVILEGES ON DATABASE :"app_role" FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC;
ALTER ROLE postgres PASSWORD NULL;
SQL
done

if [ "${1:-}" != ready ]; then
    touch "$PGDATA/.launchpad-initialized"
fi
