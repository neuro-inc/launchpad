#!/bin/sh
set -eu

psql -Xw --username postgres --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 --single-transaction --file - <<'SQL'
\getenv app_role DB_USER
\getenv app_password DB_PASSWORD
\getenv app_db POSTGRES_DB
CREATE ROLE :"app_role" LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD :'app_password';
ALTER DATABASE :"app_db" OWNER TO :"app_role";
REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC;
ALTER ROLE postgres PASSWORD NULL;
SQL
