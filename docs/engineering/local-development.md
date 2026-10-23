# Local development

Docker Compose runs PostgreSQL and Keycloak on your computer.
The Python backend and Next.js frontend run on the host for source editing.
The backend still connects to Apolo through a dedicated development profile.

## Prerequisites

Install Python 3.13, Poetry, Node.js 22, npm, Docker Compose, and the Apolo CLI.
Install the native `libmagic` library for backend file detection.

```bash
# macOS
brew install libmagic
# Debian or Ubuntu
sudo apt-get install libmagic1
```

Set `FONTAWESOME_NPM_AUTH_TOKEN` through your secret manager before installing frontend dependencies.
The committed `frontend/.npmrc` reads this variable.
Do not put registry credentials in Git or command arguments.

Run these commands from the repository root:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install
(cd frontend && npm ci)
```

## Select Apolo access

Use a separate profile for a disposable development project.
If necessary, authenticate with the development API:

```bash
apolo --config-path "$HOME/.apolo-dev" config login https://api.dev.apolo.us/api/v1
apolo --config-path "$HOME/.apolo-dev" config show
export APOLO_CONFIG="$HOME/.apolo-dev"
```

Check the username, cluster, organization, and project before starting the backend.
The launcher uses this profile and prints its selected context without credentials.
It rejects `APOLO_PASSED_CONFIG` and `NEURO_PASSED_CONFIG` to prevent conflicting credential sources.
Unset these variables if your shell inherited them.

## Start the services

Start the containers:

```bash
make local-up
```

Compose binds PostgreSQL to `127.0.0.1:15432` and Keycloak to `127.0.0.1:18081`.
Named volumes preserve both databases between restarts.
The committed passwords are local test credentials.
Do not expose these services to other computers.

Start the backend in the same shell:

```bash
make local-backend
```

The backend applies database migrations before serving requests on `127.0.0.1:8080`.
The local launcher enables HTTP Keycloak access and allows the local frontend origin through CORS.
Production configuration remains separate.
The launcher does not seed templates or install Apps during startup.

Run the setup command from the repository root in another terminal:

```bash
make local-setup
```

The command creates `frontend/.env.local` with private file permissions and a random session secret.
Repeated runs preserve the existing file and session secret.
Git ignores this file.
If the file already exists, check that its values match these local settings:

```dotenv
NEXT_PUBLIC_ENVIRONMENT=local
NEXT_PUBLIC_SITE_URL=http://dev.localhost:8080
NEXTAUTH_URL=http://dev.localhost:13000
```

Start the frontend from the repository root:

```bash
make local-frontend
```

Open [Launchpad](http://dev.localhost:13000).
Use `developer` with password `local-development` to sign in.
This account has the frontend `admin` and `user` roles.

`NEXT_PUBLIC_SITE_URL` supplies the backend discovery origin in local mode.
The frontend derives `http://dev-api.localhost:8080` from `http://dev.localhost:8080`.
`NEXTAUTH_URL` supplies the browser origin and registered OAuth callback.
Use these exact hostnames and ports to match the imported Keycloak realm.
Your browser and host resolver must map `*.localhost` to loopback addresses.

Keycloak administration is available at [the local admin console](http://localhost:18081/admin).
Use `admin` with password `local-development`.
Keycloak imports `scripts/local_development/realm.json` only when the realm does not exist.
Restarting the container does not replace an existing realm.
See [Keycloak realm import](https://www.keycloak.org/server/importExport) for import behavior.

## Verify the stack

Check frontend and backend health:

```bash
curl --fail http://dev.localhost:13000/api/health
curl --fail http://dev-api.localhost:8080/ping
```

Sign in through the browser and open the Apps page.
A fresh database has no templates or installed Apps.
Sign out and confirm that the protected Apps page requests authentication again.
Backend API documentation is available at [Swagger UI](http://dev-api.localhost:8080/openapi/v1/docs).

Run the repository checks from the repository root in another terminal:

```bash
make lint
make test-unit
make test-integration
(cd frontend && npm run lint)
```

Integration tests start their own PostgreSQL containers.

## Apolo integration limits

The local stack supports portal development, local data, and Keycloak authentication.
App operations use the selected remote Apolo project and can change its resources.
The local launcher does not deploy Kubernetes ingress or authentication middleware.
It uses `local-development` as its middleware name.
Shared App cookies and ingress require an HTTPS deployment.
End-to-end App installation and shared App access require deployed Launchpad infrastructure.
Use the [frontend development setup](../../frontend/README.md#local-development-setup) with a deployed backend for those workflows.

## Stop or reset

Stop both host processes with `Ctrl+C`.
Stop the containers from the repository root:

```bash
make local-down
```

To delete local database data and reimport the realm, remove this Compose project's volumes:

```bash
docker compose -f scripts/local_development/compose.yaml down --volumes
```

This reset deletes local Launchpad records, Keycloak users, and Keycloak configuration.
It does not delete remote Apolo resources.
