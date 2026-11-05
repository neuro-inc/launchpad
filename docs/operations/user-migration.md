# Migrating Launchpad users

`scripts/migrate-users.py` downloads users from one Launchpad Apolo App into a
reviewable JSON file, then uploads that file to another App's `launchpad` realm.
Run it with the repository's Python environment (Python 3.12 or later). It uses
the existing `apolo-sdk` dependency and the standard library; no new dependencies
are added. The SDK uses your existing Apolo login.

## How Launchpad manages users

Users live in Keycloak, not Launchpad's application database. The chart currently
deploys Keycloak 26.3.0 and initializes realm `launchpad`, including the `admin`
user and the `frontend` client role `admin`.

`launchpad/auth/dependencies.py:auth_required` builds the application user from
the JWT: email becomes the user ID; names come from `name`; the application's
`groups` field actually contains `resource_access.frontend.roles`. App ownership
is also keyed by email. Preserving email and client roles is therefore essential.
`launchpad/auth/api.py` separately forwards actual groups and realm roles to
downstream applications. Keycloak UUIDs are regenerated for new users; downstream
applications that key their accounts by the JWT `sub` need separate handling.

The script resolves the supplied App UUID with `client.apps.get()`, then calls
`client.apps.get_output()` in that App's cluster, organization, and project. It
reads the URL from `keycloak_config.web_app_url.external_url` and resolves the
`keycloak_config.auth_admin_password.key` secret with `client.secrets.get()` in
the same context. This is the Keycloak **server** administrator password, distinct
from `admin_user.password`, which belongs to the Launchpad realm user.
The ingress helper reports port 80 even for HTTPS endpoints; the script uses
HTTPS's default port in that case and preserves other explicit ports.

The chart fixes the Keycloak server administrator username to `admin`. The script
authenticates it with `admin-cli` against `master`, then operates only on realm
`launchpad`. Your Apolo account must be able to read the App and its Keycloak secret.
Administrator credentials and Apolo tokens remain in memory and are never saved
in the JSON, CSV, or console output. Resolving each App's own context supports
source and destination Apps in different accessible projects without changing
the persisted Apolo context. SDK calls were checked against installed SDK 26.3.0;
the repository currently declares 26.8.1.

## Passwords

Plaintext user passwords cannot be extracted. Keycloak stores salted password
hashes; the online credential endpoint explicitly removes `secretData` from its
response. See the [Keycloak 26.3.0 credential endpoint implementation](https://github.com/keycloak/keycloak/blob/26.3.0/services/src/main/java/org/keycloak/services/resources/admin/UserResource.java).

Existing passwords **can be preserved without knowing their plaintext** using a
server-side CLI export containing hashed credentials. With all source Keycloak
nodes stopped and the same database configuration available to the export process:

```sh
/opt/bitnami/keycloak/bin/kc.sh export \
  --realm launchpad --dir /secure/export --users realm_file
```

This produces `launchpad-realm.json`, which can be partially imported into an
existing target realm with compatible credential providers. Treat this file as a
secret: it may include password hashes, OTP secrets, and client secrets. It needs
review before import to retain the target's client URLs and credentials. The
online script deliberately does not automate stopping servers or importing that
file. See [Keycloak's import/export guide](https://www.keycloak.org/server/importExport).

The upload command generates independent 32-character passwords using
`secrets`, with uppercase, lowercase, digits, and punctuation. The CSV contains
`username,email,password`; it is created exclusively with permissions `0600`,
flushed to disk **before** the target import, and never printed to the terminal.
An existing CSV is never overwritten. Check that the target password policy
accepts these passwords; Keycloak validates them during import.

Passwords are permanent by default so Launchpad's password-token endpoint remains
usable. `--temporary-passwords` adds `UPDATE_PASSWORD`; users must complete browser
login and change their password before direct-grant login will work. Existing
source required actions remain in place either way.

## Usage

Download from the source App; no target App is accessed and no passwords are generated:

```sh
.venv/bin/python scripts/migrate-users.py download \
  --source-app-id SOURCE_APP_UUID \
  --output launchpad-users.json
```

Manually review `launchpad-users.json`. It contains user profiles, attributes,
role assignments/definitions, group trees/memberships, the user-profile schema,
realm defaults, and source App ID/URL. Each user's `_migration` section records
credential types and unsupported account features, without credential secrets.
You can remove user entries or adjust their metadata before uploading. Keep
the role/group definitions consistent with any edited assignments. The JSON is
created with mode `0600` and cannot overwrite an existing file. It contains
personal data; treat it accordingly.

Upload the reviewed file; only the target App is accessed:

```sh
.venv/bin/python scripts/migrate-users.py upload \
  --target-app-id TARGET_APP_UUID \
  --input launchpad-users.json \
  --passwords-csv /secure/launchpad-passwords.csv
```

Add `--dry-run` to upload for target compatibility checks without importing or
writing the password CSV. Otherwise, upload performs the import after preflight.
It consumes the reviewed JSON directly and never refetches the source.

Use `--source-keycloak-url` on download or `--target-keycloak-url` on upload to
override the endpoint, including for localhost HTTP port-forwards. Credentials
still come from the specified App's Apolo secret. All other connections require
HTTPS; TLS certificates are verified and redirects refused. Matching source and
target App IDs or Keycloak URLs are rejected.

## What is copied and checked

The script paginates through users and group memberships and fetches each full
user representation. It copies username, email, names, enabled/email-verified
flags, creation timestamp, multivalued custom attributes, required actions,
federated identity links, direct realm and client role assignments, group
memberships, group trees/attributes/role assignments, and role definitions including
composites and role attributes. Native Keycloak partial import resolves roles by
client/name and groups by path, rather than copying source IDs.

Target clients and identity providers must already be configured under matching
names/aliases. Their URLs, secrets, scopes, and token mappers are target-specific
and are not copied; review them for equivalent behavior. User-profile schemas,
default role/groups, and any shared role/group definitions must agree. Preflight
rejects differences to prevent silent attribute loss or changed inherited access.
Missing role definitions and group trees are imported together with the users.

Existing target users matched by username or email are reported and skipped,
including the usual target `admin` account. Their metadata, roles, and passwords
are retained, and they have no CSV row. Use `--existing-users fail` if every source
user must be new. There is no overwrite mode: Keycloak's native partial-import
overwrite deletes and recreates users, which would risk existing target accounts.

For new users, upload preflight refuses external user-storage accounts (LDAP/custom
federation), service accounts, non-password credentials such as OTP/WebAuthn,
and users with client consents. It also refuses organization-enabled realms.
These need a separate migration or a reviewed server export; they are never
silently downgraded to ordinary password-only accounts. Password history is not
available online and is not migrated. Sessions, login-failure counters, events,
revoked tokens, application data, and existing app installations are not copied.

Keep source user/role/group changes paused during download: an online scan is not
a consistent database snapshot. Subsequent source changes do not affect the
reviewed file. Keep target user/role/group changes paused during upload. The script submits one partial import
with `SKIP` collision handling, then reads back user metadata, memberships, and
role/group definitions. If another process creates a user during import, the
script reports the skipped user as a failure because its generated CSV password
is not active. It does not verify passwords by logging in as users.

If import or verification fails, keep the CSV and inspect the target before
rerunning. A failed/timeout response may follow a committed import. The script
does not retry writes, roll back accounts, or reset existing passwords. CSV rows
record generated credentials, not a guarantee of successful import. Reruns use
the normal existing-user policy and a new CSV path; retain the original CSV for
users already imported. Store and distribute the CSV as a password document.

Offline check:

```sh
python3 scripts/test_migrate_users.py
```
